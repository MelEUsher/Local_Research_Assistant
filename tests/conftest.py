import copy
import importlib
import importlib.util
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def _ensure_stub_module(name, initializer=None, package=False):
    """Create a stub module only when the real dependency is unavailable."""
    if name in sys.modules:
        return sys.modules[name]

    if importlib.util.find_spec(name) is not None:
        return importlib.import_module(name)

    module = types.ModuleType(name)
    if package:
        module.__path__ = []
    if initializer:
        initializer(module)
    sys.modules[name] = module
    return module


def _setup_langchain_stub():
    package = _ensure_stub_module("langchain_community", initializer=lambda m: setattr(m, "__path__", []), package=True)
    llms = _ensure_stub_module(
        "langchain_community.llms",
        initializer=lambda module: setattr(module, "__path__", []),
        package=True,
    )
    setattr(package, "llms", llms)
    setattr(llms, "Ollama", type("StubOllama", (), {}))
    ollama_submodule = _ensure_stub_module(
        "langchain_community.llms.ollama",
        initializer=lambda module: setattr(module, "__path__", []),
        package=True,
    )
    setattr(llms, "ollama", ollama_submodule)
    setattr(ollama_submodule, "Ollama", type("StubOllama", (), {}))


def _setup_langgraph_stub():
    package = _ensure_stub_module("langgraph", initializer=lambda m: setattr(m, "__path__", []), package=True)

    def graph_initializer(module):
        class FakeStateGraph:
            def __init__(self, state_type):
                self.nodes = {}
                self.entry = None

            def add_node(self, name, func):
                self.nodes[name] = func

            def set_entry_point(self, entry):
                self.entry = entry

            def add_edge(self, _from, _to):
                pass

            def compile(self):
                return self

            def invoke(self, state):
                order = ["refine_query", "fetch_sources", "summarize", "format_output"]
                current_state = state
                for node in order:
                    current_state = self.nodes[node](current_state)
                return current_state

        module.StateGraph = FakeStateGraph
        module.END = object()

    graph_module = _ensure_stub_module(
        "langgraph.graph",
        initializer=graph_initializer,
        package=True,
    )
    setattr(package, "graph", graph_module)


def _setup_googleapiclient_stub():
    package = _ensure_stub_module(
        "googleapiclient",
        initializer=lambda m: setattr(m, "__path__", []),
        package=True,
    )

    def discovery_initializer(module):
        class DummyClient:
            def cse(self):
                return self

            def list(self, **kwargs):
                return self

            def execute(self):
                return {}

        module.build = lambda *args, **kwargs: DummyClient()

    discovery_module = _ensure_stub_module("googleapiclient.discovery", initializer=discovery_initializer)
    setattr(package, "discovery", discovery_module)

    def errors_initializer(module):
        class FakeHttpError(Exception):
            def __init__(self, response, content):
                super().__init__("HttpError")
                self.content = content

        module.HttpError = FakeHttpError

    errors_module = _ensure_stub_module("googleapiclient.errors", initializer=errors_initializer)
    setattr(package, "errors", errors_module)


_setup_langchain_stub()
_setup_langgraph_stub()
_setup_googleapiclient_stub()


@pytest.fixture
def sample_search_results():
    """Provide consistent fake search results for use across tests."""
    return [
        {"title": "AI Overview", "link": "https://example.com/ai", "snippet": "A primer on AI."},
        {"title": "AI Ethics", "link": "https://example.com/ethics", "snippet": "Responsible AI practices."},
    ]


@pytest.fixture
def sample_state(sample_search_results):
    """Return a base research state dictionary used by workflow node tests."""
    return {
        "original_query": "Share 2 facts about artificial intelligence.",
        "refined_query": "artificial intelligence facts",
        "search_results": copy.deepcopy(sample_search_results),
        "formatted_results": "=== Search Results ===\n\nResult 1:\nTitle: AI Overview\n",
        "summary": "",
        "output": "",
    }


@pytest.fixture
def mock_google_search_service(monkeypatch, sample_search_results):
    """Replace GoogleSearchService with a controllable mock instance."""
    mock_service = MagicMock()
    mock_service.search.return_value = sample_search_results
    mock_service.format_results_for_llm.return_value = "Formatted search results stub."
    mock_service.test_connection.return_value = True
    monkeypatch.setattr("workflow.GoogleSearchService", MagicMock(return_value=mock_service))
    monkeypatch.setattr("search_service.GoogleSearchService", MagicMock(return_value=mock_service))
    return mock_service


@pytest.fixture
def mock_ollama_service(monkeypatch):
    """Provide a mock OllamaLLMService to avoid real API calls."""
    mock_service = MagicMock()
    mock_service.refine_query.return_value = "refined query stub"
    mock_service.summarize_search_results.return_value = "Structured summary stub."
    mock_service.verify_connection.return_value = True
    monkeypatch.setattr("workflow.OllamaLLMService", MagicMock(return_value=mock_service))
    monkeypatch.setattr("llm_service.OllamaLLMService", MagicMock(return_value=mock_service))
    return mock_service


@pytest.fixture
def mock_valid_config():
    """Mock environment with valid configuration."""
    env = {
        "GOOGLE_API_KEY": "AIzaSyDfakekey123456789",
        "GOOGLE_CSE_ID": "1234567890123456:abcdefABCDEF",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "llama3.2"
    }
    config_mod = importlib.import_module("config")
    search_mod = importlib.import_module("search_service")
    llm_mod = importlib.import_module("llm_service")
    original_values = {
        "config": {
            "GOOGLE_API_KEY": config_mod.GOOGLE_API_KEY,
            "GOOGLE_CSE_ID": config_mod.GOOGLE_CSE_ID,
            "OLLAMA_BASE_URL": config_mod.OLLAMA_BASE_URL,
            "OLLAMA_MODEL": config_mod.OLLAMA_MODEL,
        },
        "search": {
            "GOOGLE_API_KEY": search_mod.GOOGLE_API_KEY,
            "GOOGLE_CSE_ID": search_mod.GOOGLE_CSE_ID,
        },
        "llm": {
            "OLLAMA_BASE_URL": llm_mod.OLLAMA_BASE_URL,
            "OLLAMA_MODEL": llm_mod.OLLAMA_MODEL,
        },
    }

    with patch.dict("os.environ", env):
        config_mod.GOOGLE_API_KEY = env["GOOGLE_API_KEY"]
        config_mod.GOOGLE_CSE_ID = env["GOOGLE_CSE_ID"]
        config_mod.OLLAMA_BASE_URL = env["OLLAMA_BASE_URL"]
        config_mod.OLLAMA_MODEL = env["OLLAMA_MODEL"]

        search_mod.GOOGLE_API_KEY = env["GOOGLE_API_KEY"]
        search_mod.GOOGLE_CSE_ID = env["GOOGLE_CSE_ID"]

        llm_mod.OLLAMA_BASE_URL = env["OLLAMA_BASE_URL"]
        llm_mod.OLLAMA_MODEL = env["OLLAMA_MODEL"]

        yield

    for key, original in original_values["config"].items():
        setattr(config_mod, key, original)
    for key, original in original_values["search"].items():
        setattr(search_mod, key, original)
    for key, original in original_values["llm"].items():
        setattr(llm_mod, key, original)


@pytest.fixture
def mock_invalid_config():
    """Mock environment with invalid configuration."""
    env = {
        "GOOGLE_API_KEY": "",
        "GOOGLE_CSE_ID": "",
        "OLLAMA_BASE_URL": "invalid-url",
        "OLLAMA_MODEL": ""
    }
    config_mod = importlib.import_module("config")
    search_mod = importlib.import_module("search_service")
    llm_mod = importlib.import_module("llm_service")
    original_values = {
        "config": {
            "GOOGLE_API_KEY": config_mod.GOOGLE_API_KEY,
            "GOOGLE_CSE_ID": config_mod.GOOGLE_CSE_ID,
            "OLLAMA_BASE_URL": config_mod.OLLAMA_BASE_URL,
            "OLLAMA_MODEL": config_mod.OLLAMA_MODEL,
        },
        "search": {
            "GOOGLE_API_KEY": search_mod.GOOGLE_API_KEY,
            "GOOGLE_CSE_ID": search_mod.GOOGLE_CSE_ID,
        },
        "llm": {
            "OLLAMA_BASE_URL": llm_mod.OLLAMA_BASE_URL,
            "OLLAMA_MODEL": llm_mod.OLLAMA_MODEL,
        },
    }

    with patch.dict("os.environ", env):
        config_mod.GOOGLE_API_KEY = env["GOOGLE_API_KEY"]
        config_mod.GOOGLE_CSE_ID = env["GOOGLE_CSE_ID"]
        config_mod.OLLAMA_BASE_URL = env["OLLAMA_BASE_URL"]
        config_mod.OLLAMA_MODEL = env["OLLAMA_MODEL"]

        search_mod.GOOGLE_API_KEY = env["GOOGLE_API_KEY"]
        search_mod.GOOGLE_CSE_ID = env["GOOGLE_CSE_ID"]

        llm_mod.OLLAMA_BASE_URL = env["OLLAMA_BASE_URL"]
        llm_mod.OLLAMA_MODEL = env["OLLAMA_MODEL"]

        yield

    for key, original in original_values["config"].items():
        setattr(config_mod, key, original)
    for key, original in original_values["search"].items():
        setattr(search_mod, key, original)
    for key, original in original_values["llm"].items():
        setattr(llm_mod, key, original)
