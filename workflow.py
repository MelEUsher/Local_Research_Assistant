"""LangGraph workflow for research assistance."""
from collections import deque
from typing import TypedDict, List, Dict, Tuple, Any, Optional, Callable
from langgraph.graph import StateGraph, END
from search_service import GoogleSearchService
from llm_service import OllamaLLMService
from logger import logger
from export_service import ExportService
import re


class ResearchState(TypedDict):
    """State object for the research workflow."""
    original_query: str
    refined_query: str
    search_results: List[Dict[str, str]]
    formatted_results: str
    summary: str
    output: str
    export_filename: str


class ResearchWorkflow:
    """LangGraph workflow for research assistance."""

    SUMMARY_CACHE_LIMIT = 50

    def __init__(
        self,
        export_service: Optional[ExportService] = None,
        ui_callbacks: Optional[Dict[str, Callable[..., None]]] = None,
        search_service_factory: Optional[Callable[[], GoogleSearchService]] = None,
        llm_service_factory: Optional[Callable[[], OllamaLLMService]] = None,
        source_cache: Optional[Dict[Tuple[str, int], Dict[str, Any]]] = None,
        summary_cache: Optional[Dict[Tuple[str, int, int], str]] = None,
    ):
        self._ui_callbacks = ui_callbacks or {}
        if search_service_factory:
            self.search_service = search_service_factory()
        else:
            self.search_service = GoogleSearchService()
        if llm_service_factory:
            self.llm_service = llm_service_factory()
        else:
            self.llm_service = OllamaLLMService()
        self._cache_enabled = True
        self._source_cache = source_cache if source_cache is not None else {}
        self._summary_cache = summary_cache if summary_cache is not None else {}
        self._summary_cache_order = deque()
        self.export_service = export_service
        self._last_state: Optional[ResearchState] = None
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow graph."""
        workflow = StateGraph(ResearchState)
        
        # Add nodes
        workflow.add_node("refine_query", self._refine_query_node)
        workflow.add_node("fetch_sources", self._fetch_sources_node)
        workflow.add_node("summarize", self._summarize_node)
        workflow.add_node("format_output", self._format_output_node)
        
        # Define the edges
        workflow.set_entry_point("refine_query")
        workflow.add_edge("refine_query", "fetch_sources")
        workflow.add_edge("fetch_sources", "summarize")
        workflow.add_edge("summarize", "format_output")
        workflow.add_edge("format_output", END)
        
        return workflow.compile()

    def _notify_ui(self, event: str, stage: str, exc: Optional[Exception] = None) -> None:
        """Invoke a UI callback if one was provided."""
        callback = self._ui_callbacks.get(event)
        if not callback:
            return
        try:
            if exc is not None:
                callback(stage, exc)
            else:
                callback(stage)
        except Exception as warning_exc:  # pragma: no cover - instrumentation errors shouldn't break workflow
            logger.warning(
                "UI callback '%s' for stage '%s' raised an exception: %s",
                event,
                stage,
                warning_exc,
                exc_info=True,
            )
    
    def _refine_query_node(self, state: ResearchState) -> ResearchState:
        """Node: Refine the user's query for better search results."""
        stage = "Refining"
        self._notify_ui("on_stage_start", stage)
        try:
            print(f"🔍 Refining query: {state['original_query']}")  # ADD THIS
            logger.info("Entering node refine_query for query: %s", state['original_query'])
            refined = self.llm_service.refine_query(state['original_query'])
            state['refined_query'] = refined
            print(f"✅ Refined query: {refined}")  # ADD THIS
            logger.info("Refined query ready")
            logger.debug("State after refine_query: refined_query=%s", state['refined_query'])
        except Exception as exc:
            self._notify_ui("on_stage_fail", stage, exc)
            raise
        else:
            self._notify_ui("on_stage_complete", stage)
            return state
    
    def _fetch_sources_node(self, state: ResearchState) -> ResearchState:
        """Node: Fetch information from web sources."""
        stage = "Searching"
        self._notify_ui("on_stage_start", stage)
        try:
            print(f"🌐 Searching the web...")  # ADD THIS
            logger.info("Entering node fetch_sources for query: %s", state['original_query'])
            num_results = 5
            if not (1 <= num_results <= 10):
                raise ValueError("num_results for fetching sources must be between 1 and 10.")
            cache_key = (state['original_query'], num_results)
            cached_entry = self._source_cache.get(cache_key) if self._cache_enabled else None
            if cached_entry:
                logger.info("Cache hit for fetch_sources: %s", cache_key)
                state['search_results'] = cached_entry['search_results']
                state['formatted_results'] = cached_entry['formatted_results']
                results = state['search_results']
            else:
                if self._cache_enabled:
                    logger.info("Cache miss for fetch_sources: %s", cache_key)
                results = self.search_service.search(state['refined_query'], num_results=num_results)
                state['search_results'] = results
                state['formatted_results'] = self.search_service.format_results_for_llm(results)
                if self._cache_enabled:
                    self._source_cache[cache_key] = {
                        "search_results": results,
                        "formatted_results": state['formatted_results']
                    }
            print(f"✅ Found {len(results)} search results")
            logger.info("Fetched %d search results for query: %s", len(results), state['original_query'])
            logger.debug("State after fetch_sources: num_results=%d, formatted_length=%d", 
                 len(state['search_results']), len(state['formatted_results']))
        except Exception as exc:
            self._notify_ui("on_stage_fail", stage, exc)
            raise
        else:
            self._notify_ui("on_stage_complete", stage)
            return state
    
    def _summarize_node(self, state: ResearchState) -> ResearchState:
        """Node: Summarize search results into structured facts."""
        stage = "Summarizing"
        self._notify_ui("on_stage_start", stage)
        try:
            print(f"📝 Summarizing results...")
            logger.info("Entering node summarize")
            # Extract number of facts from original query if specified
            num_facts = self._extract_num_facts(state['original_query'])
            formatted_hash = hash(state['formatted_results'])
            cache_key = (state['original_query'], num_facts, formatted_hash)
            cached_summary = self._summary_cache.get(cache_key) if self._cache_enabled else None
            if cached_summary:
                logger.info("Cache hit for summarize: %s", cache_key)
                summary = cached_summary
                self._touch_summary_cache_key(cache_key)
            else:
                if self._cache_enabled:
                    logger.info("Cache miss for summarize: %s", cache_key)
                summary = self.llm_service.summarize_search_results(
                    state['original_query'],
                    state['formatted_results'],
                    num_facts=num_facts
                )
                if self._cache_enabled:
                    self._store_summary_cache_entry(cache_key, summary)
            state['summary'] = summary
            print(f"✅ Summary generated")
            logger.info("Summary generated with %d facts", num_facts)
            logger.debug("State after summarize: summary_length=%d", len(state['summary']))
        except Exception as exc:
            self._notify_ui("on_stage_fail", stage, exc)
            raise
        else:
            self._notify_ui("on_stage_complete", stage)
            return state
    
    def _format_output_node(self, state: ResearchState) -> ResearchState:
        """Node: Format the final output."""
        logger.info("Entering node format_output")
        output = f"""# Research Results

## Original Query
{state['original_query']}

## Search Query Used
{state['refined_query']}

## Summary and Facts

{state['summary']}

## Sources
"""
        for i, result in enumerate(state['search_results'], 1):
            output += f"{i}. [{result['title']}]({result['link']})\n"
        
        state['output'] = output
        logger.debug("State after format_output: output_length=%d", len(state['output']))
        return state
    
    def _extract_num_facts(self, query: str) -> int:
        """Extract the number of facts requested from the query."""
        # Look for patterns like "3 facts", "find 5 facts", etc.
        match = re.search(r'(\d+)\s*facts?', query.lower())
        if match:
            return int(match.group(1))
        return 3  # Default to 3

    def _touch_summary_cache_key(self, key: Tuple[str, int, int]) -> None:
        """Mark a summary cache key as recently used."""
        try:
            self._summary_cache_order.remove(key)
        except ValueError:
            pass
        self._summary_cache_order.append(key)

    def _store_summary_cache_entry(self, key: Tuple[str, int, int], summary: str) -> None:
        """Add a summary to the cache and enforce the size limit."""
        self._summary_cache[key] = summary
        self._touch_summary_cache_key(key)
        while len(self._summary_cache_order) > self.SUMMARY_CACHE_LIMIT:
            oldest = self._summary_cache_order.popleft()
            self._summary_cache.pop(oldest, None)

    @property
    def last_state(self) -> Optional[ResearchState]:
        """Access the most recent workflow state."""
        return self._last_state
    
    def run(
        self, research_request: str, use_cache: bool = True, auto_export: bool = False
    ) -> str:
        """
        Execute the research workflow.

        Args:
            research_request: Natural language research request
            use_cache: Flag to enable or disable the in-memory cache.
            auto_export: If True, automatically save the final output to markdown.

        Returns:
            Formatted research results
        """
        cleaned_request = research_request.strip()
        if not cleaned_request:
            raise ValueError("Research request must not be empty or whitespace only.")
        if len(cleaned_request) < 3:
            raise ValueError("Research request must be at least 3 characters long.")
        if len(cleaned_request) > 500:
            raise ValueError("Research request must be at most 500 characters long.")

        initial_state: ResearchState = {
            "original_query": cleaned_request,
            "refined_query": "",
            "search_results": [],
            "formatted_results": "",
            "summary": "",
            "output": "",
            "export_filename": ""
        }
        
        logger.info("Starting research workflow for query: %s", cleaned_request)
        previous_cache_state = self._cache_enabled
        self._cache_enabled = use_cache
        try:
            final_state = self.graph.invoke(initial_state)
        finally:
            self._cache_enabled = previous_cache_state

        if auto_export:
            if not self.export_service:
                raise ValueError(
                    "Auto export requested but no ExportService is configured."
                )
            export_name = self.export_service.auto_generate_filename(cleaned_request)
            export_path = self.export_service.save_to_markdown(
                final_state["output"], export_name
            )
            final_state["export_filename"] = export_path
            logger.info("Exported results to %s", export_path)

        self._last_state = final_state
        logger.info("Workflow completed for query: %s", cleaned_request)
        logger.debug("Final output length: %d characters", len(final_state["output"]))
        return final_state["output"]
