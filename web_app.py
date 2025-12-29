"""Streamlit interface for the local research assistant."""
import time
from datetime import datetime
from typing import Callable, Dict, Optional

import streamlit as st

from export_service import ExportService
from workflow import ResearchWorkflow
from search_service import GoogleSearchService
from llm_service import OllamaLLMService
from logger import logger

EXAMPLE_QUERIES = [
    "Explain the current state of battery technology for electric aircraft.",
    "What are the best practices for securing a LangChain deployment?",
    "Summarize key takeaways from the latest AI governance white papers.",
    "Compare renewable energy incentives in Germany versus the United States.",
    "Outline how neural search differs from traditional keyword search.",
]

STAGE_SEQUENCE = ["Refining", "Searching", "Summarizing"]
DEFAULT_FACT_COUNT = 3
DEFAULT_SEARCH_RESULTS = 5
DEFAULT_PROGRESS = {stage: "Pending" for stage in STAGE_SEQUENCE}
STAGE_STATUS_COLORS = {
    "Pending": "#6c757d",
    "Running": "#f6a623",
    "Complete": "#1f77b4",
    "Failed": "#d32f2f",
}
CACHE_HIT_COLOR = "#0f9d58"
CACHE_MISS_COLOR = "#1f77b4"


class CacheTrackingDict(dict):
    """Dict wrapper that updates cache metrics when entries are inspected."""

    def __init__(self, base: Dict = None, metrics_supplier: Callable[[], Optional[Dict]] = None):
        super().__init__(base or {})
        self._metrics_supplier = metrics_supplier or (lambda: None)

    def _track_access(self, key):
        metrics = self._metrics_supplier()
        if not metrics:
            return
        hit = dict.__contains__(self, key)
        if hit:
            metrics["cache_hits"] += 1
        else:
            metrics["cache_misses"] += 1

    def __getitem__(self, key):
        self._track_access(key)
        return super().__getitem__(key)

    def get(self, key, default=None):
        self._track_access(key)
        return super().get(key, default)

    def __contains__(self, key):
        self._track_access(key)
        return super().__contains__(key)

    def set_metrics_supplier(self, supplier: Callable[[], Dict]):
        self._metrics_supplier = supplier


class SearchTelemetry:
    """Wraps the search service so we can track API calls and override result counts."""

    def __init__(
        self,
        base_service,
        metrics_supplier: Callable[[], Optional[Dict]],
        num_results_supplier: Callable[[], Optional[int]],
    ):
        self._base = base_service
        self._metrics_supplier = metrics_supplier
        self._num_results_supplier = num_results_supplier

    def search(self, query: str, num_results: int = DEFAULT_SEARCH_RESULTS):
        metrics = self._metrics_supplier()
        if metrics is not None:
            metrics["api_calls"]["google_search"] += 1
        override = self._num_results_supplier()
        actual = override if override is not None else num_results
        return self._base.search(query, num_results=actual)

    def format_results_for_llm(self, *args, **kwargs):
        return self._base.format_results_for_llm(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._base, name)


class LLMTelemetry:
    """Wraps the LLM service to track API calls and respect user fact counts."""

    def __init__(
        self,
        base_service,
        metrics_supplier: Callable[[], Optional[Dict]],
        num_facts_supplier: Callable[[], Optional[int]],
    ):
        self._base = base_service
        self._metrics_supplier = metrics_supplier
        self._num_facts_supplier = num_facts_supplier

    def summarize_search_results(self, query: str, search_results: str, num_facts: int = DEFAULT_FACT_COUNT):
        metrics = self._metrics_supplier()
        if metrics is not None:
            metrics["api_calls"]["llm_summarize"] += 1
        override = self._num_facts_supplier()
        actual_facts = override if override is not None else num_facts
        return self._base.summarize_search_results(
            query, search_results, num_facts=actual_facts
        )

    def refine_query(self, research_request: str):
        metrics = self._metrics_supplier()
        if metrics is not None:
            metrics["api_calls"]["llm_refine"] += 1
        return self._base.refine_query(research_request)

    def __getattr__(self, name):
        return getattr(self._base, name)


def _initialize_session_state() -> None:
    """Set defaults for the Streamlit session."""
    defaults = {
        "history": [],
        "last_result": "",
        "last_run_metrics": None,
        "query_input": "",
        "cache_enabled": True,
        "num_facts": DEFAULT_FACT_COUNT,
        "num_search_results": DEFAULT_SEARCH_RESULTS,
        "workflow_instance": None,
        "workflow_ready": False,
        "workflow_error": "",
        "progress_states": DEFAULT_PROGRESS.copy(),
        "last_error": "",
        "current_run_metrics": None,
        "source_cache": None,
        "summary_cache": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _handle_stage_start(stage: str) -> None:
    st.session_state.progress_states[stage] = "Running"
    logger.info("Workflow stage started: %s", stage)


def _handle_stage_complete(stage: str) -> None:
    st.session_state.progress_states[stage] = "Complete"
    logger.info("Workflow stage completed: %s", stage)


def _handle_stage_failure(stage: str, exc: Exception) -> None:
    st.session_state.progress_states[stage] = "Failed"
    logger.error("Workflow stage '%s' failed", stage, exc_info=True)


def _instrument_workflow():
    """Prepare instrumentation helpers used by the Streamlit UI."""

    logger.info("Configuring Streamlit instrumentation for ResearchWorkflow")
    metrics_supplier = lambda: st.session_state.current_run_metrics

    source_cache = st.session_state.source_cache
    if source_cache is None:
        source_cache = CacheTrackingDict(metrics_supplier=metrics_supplier)
        st.session_state.source_cache = source_cache
        logger.debug("Initialized source cache metrics tracker")
    else:
        source_cache.set_metrics_supplier(metrics_supplier)

    summary_cache = st.session_state.summary_cache
    if summary_cache is None:
        summary_cache = CacheTrackingDict(metrics_supplier=metrics_supplier)
        st.session_state.summary_cache = summary_cache
        logger.debug("Initialized summary cache metrics tracker")
    else:
        summary_cache.set_metrics_supplier(metrics_supplier)

    callbacks = {
        "on_stage_start": _handle_stage_start,
        "on_stage_complete": _handle_stage_complete,
        "on_stage_fail": _handle_stage_failure,
    }

    def search_factory():
        return SearchTelemetry(
            GoogleSearchService(),
            metrics_supplier,
            lambda: st.session_state.num_search_results,
        )

    def llm_factory():
        return LLMTelemetry(
            OllamaLLMService(),
            metrics_supplier,
            lambda: st.session_state.num_facts,
        )

    logger.info("Streamlit instrumentation configured")
    return callbacks, search_factory, llm_factory, source_cache, summary_cache


def _ensure_workflow_ready():
    """Instantiate the workflow once per session."""

    if st.session_state.workflow_instance:
        return
    try:
        callbacks, search_factory, llm_factory, source_cache, summary_cache = _instrument_workflow()
        workflow = ResearchWorkflow(
            export_service=ExportService(),
            ui_callbacks=callbacks,
            search_service_factory=search_factory,
            llm_service_factory=llm_factory,
            source_cache=source_cache,
            summary_cache=summary_cache,
        )
        st.session_state.workflow_instance = workflow
        st.session_state.workflow_ready = True
        st.session_state.workflow_error = ""
        logger.info("ResearchWorkflow initialized for Streamlit UI")
    except ConnectionError as exc:
        st.session_state.workflow_error = "Unable to connect to required services. Check Ollama/Google credentials."
        st.session_state.workflow_ready = False
        logger.error("Connection error initializing workflow", exc_info=True)
    except ValueError as exc:
        st.session_state.workflow_error = f"Configuration issue while initializing the workflow: {exc}"
        st.session_state.workflow_ready = False
        logger.error("Configuration error initializing workflow", exc_info=True)
    except Exception as exc:
        st.session_state.workflow_error = "Unexpected error while preparing the workflow."
        st.session_state.workflow_ready = False
        logger.error("Unexpected error initializing workflow", exc_info=True)


def _create_run_metrics(cache_enabled: bool) -> Dict:
    """Build a fresh metrics object before executing the workflow."""

    return {
        "cache_enabled": cache_enabled,
        "cache_hits": 0,
        "cache_misses": 0,
        "query_time": 0.0,
        "api_calls": {
            "google_search": 0,
            "llm_refine": 0,
            "llm_summarize": 0,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


def _record_history(entry: Dict) -> None:
    """Append a completed entry to the session history."""

    history = st.session_state.history
    history.append(entry)
    st.session_state.history = history[-20:]


def _reset_history():
    """Clear conversation state so the UI feels fresh."""

    st.session_state.history = []
    st.session_state.last_result = ""
    st.session_state.last_run_metrics = None
    st.session_state.progress_states = DEFAULT_PROGRESS.copy()
    st.session_state.last_error = ""
    logger.info("Streamlit conversation history cleared")


def _render_metrics_panel(metrics: Dict):
    """Show the most recent query metrics."""

    if not metrics:
        return
    hits = metrics["cache_hits"]
    misses = metrics["cache_misses"]
    total_api_calls = sum(metrics["api_calls"].values())
    cols = st.columns(3)
    cols[0].metric("Query time", f"{metrics['query_time']:.2f}s")
    cols[1].metric("API calls", total_api_calls)
    cols[2].markdown(
        f"<span style='color:{CACHE_HIT_COLOR};font-weight:bold;'>Cache hits: {hits}</span> "
        f"<span style='color:{CACHE_MISS_COLOR};font-weight:bold;'>Cache misses: {misses}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<small>Cache policy is {'enabled' if metrics['cache_enabled'] else 'disabled'}.</small>",
        unsafe_allow_html=True,
    )


def _render_progress():
    """Display the workflow stages with their current states."""

    cols = st.columns(len(STAGE_SEQUENCE))
    for column, stage in zip(cols, STAGE_SEQUENCE):
        status = st.session_state.progress_states.get(stage, "Pending")
        color = STAGE_STATUS_COLORS.get(status, "#6c757d")
        column.markdown(
            f"<div style='font-size:16px; font-weight:600;'>"
            f"<span style='color:{color};'>●</span> {stage}</div>"
            f"<div style='color:#5f6368;'>{status}</div>",
            unsafe_allow_html=True,
        )


def _render_sources(search_results):
    """List search results as clickable links."""

    if not search_results:
        return
    st.markdown("### Sources")
    for index, item in enumerate(search_results, 1):
        title = item.get("title") or "Untitled"
        link = item.get("link", "#")
        snippet = item.get("snippet", "")
        st.markdown(f"**{index}. [{title}]({link})**  ")
        if snippet:
            st.markdown(f"<small>{snippet}</small>", unsafe_allow_html=True)


def _render_history():
    """Show prior queries so the session feels conversational."""

    if not st.session_state.history:
        return
    st.markdown("## Conversation history")
    for entry in reversed(st.session_state.history):
        with st.expander(f"{entry['query']} ({entry['timestamp']})", expanded=False):
            st.markdown(entry["result"])
            sources = entry.get("sources") or []
            if sources:
                _render_sources(sources)
            entry_metrics = entry.get("metrics")
            if entry_metrics:
                st.markdown(
                    f"<small>Query time: {entry_metrics['query_time']:.2f}s | "
                    f"API calls: {sum(entry_metrics['api_calls'].values())}</small>",
                    unsafe_allow_html=True,
                )


def _handle_query_submission():
    """Run the workflow when the user submits a research query."""

    query = st.session_state.query_input.strip()
    if not query:
        st.warning("Please enter a research query.")
        return

    workflow = st.session_state.workflow_instance
    st.session_state.current_run_metrics = _create_run_metrics(st.session_state.cache_enabled)
    st.session_state.progress_states = DEFAULT_PROGRESS.copy()
    st.session_state.last_error = ""
    logger.info("Submitting research query via Streamlit: %s", query)

    try:
        with st.spinner("Refining query and gathering insights..."):
            start = time.perf_counter()
            result = workflow.run(
                query,
                use_cache=st.session_state.cache_enabled,
            )
            duration = time.perf_counter() - start
        st.session_state.current_run_metrics["query_time"] = duration
        st.session_state.last_run_metrics = dict(st.session_state.current_run_metrics)
        st.session_state.last_result = result
        sources = (workflow.last_state or {}).get("search_results", [])
        _record_history(
            {
                "query": query,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "result": result,
                "metrics": dict(st.session_state.current_run_metrics),
                "sources": sources,
            }
        )
        logger.info("Query completed in %.2fs", duration)
    except ConnectionError as exc:
        st.session_state.last_error = (
            "Connection failure. Ensure Ollama and Google Search services are reachable."
        )
        logger.error("Connection error running workflow", exc_info=True)
        st.error(st.session_state.last_error)
    except ValueError as exc:
        st.session_state.last_error = f"Validation error: {exc}"
        logger.error("Validation error running workflow", exc_info=True)
        st.error(st.session_state.last_error)
    except Exception as exc:
        st.session_state.last_error = "Unexpected error while executing the workflow."
        logger.error("Unexpected error running workflow", exc_info=True)
        st.error(st.session_state.last_error)
        st.exception(exc)


st.set_page_config(page_title="Local Research Assistant", layout="wide")
_initialize_session_state()
_ensure_workflow_ready()

with st.sidebar:
    st.header("Options")
    st.selectbox("Example queries", EXAMPLE_QUERIES, key="example_choice")
    if st.button("Load example query"):
        st.session_state.query_input = st.session_state.example_choice
    st.slider(
        "Facts to extract",
        min_value=1,
        max_value=10,
        key="num_facts",
        value=st.session_state.num_facts,
    )
    st.slider(
        "Search results",
        min_value=1,
        max_value=10,
        key="num_search_results",
        value=st.session_state.num_search_results,
    )
    st.checkbox("Enable caching", key="cache_enabled", value=st.session_state.cache_enabled)
    if st.button("Export latest result"):
        if st.session_state.last_result:
            export_service = ExportService()
            filename = export_service.auto_generate_filename(st.session_state.query_input or "result")
            path = export_service.save_to_markdown(st.session_state.last_result, filename)
            st.success(f"Results exported to `{path}`.")
        else:
            st.warning("Submit a query first before exporting.")
    if st.button("Clear conversation history"):
        _reset_history()
    st.markdown(
        f"<div style='color:{CACHE_HIT_COLOR};font-weight:600;'>Cache hits: "
        f"{(st.session_state.last_run_metrics or {}).get('cache_hits', 0)}</div>"
        f"<div style='color:{CACHE_MISS_COLOR};font-weight:600;'>Cache misses: "
        f"{(st.session_state.last_run_metrics or {}).get('cache_misses', 0)}</div>",
        unsafe_allow_html=True,
    )

st.title("Local Research Assistant")
st.caption("Submit a query, watch the workflow progress, and explore formatted, sourced answers.")

if not st.session_state.workflow_ready:
    st.error(f"Unable to connect to the workflow: {st.session_state.workflow_error}")
    st.stop()

if st.session_state.last_error:
    st.error(st.session_state.last_error)

_render_progress()

query_col, info_col = st.columns([3, 1])
with query_col:
    st.text_area("Research query", key="query_input", height=150)
    if st.button("Submit query"):
        _handle_query_submission()
    if st.session_state.last_result:
        st.download_button(
            "Download latest result",
            st.session_state.last_result,
            file_name="research_result.md",
            mime="text/markdown",
        )

with info_col:
    _render_metrics_panel(st.session_state.last_run_metrics or {})
    st.markdown("### Quick actions")
    st.write("- Use the sidebar to tune extraction parameters.")
    st.write("- Cache hits are green; misses are blue.")

if st.session_state.last_result:
    st.subheader("Formatted result")
    st.markdown(st.session_state.last_result)
    _render_sources((st.session_state.workflow_instance.last_state or {}).get("search_results", []))

_render_history()
