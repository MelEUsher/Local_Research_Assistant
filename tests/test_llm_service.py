"""Tests for the Ollama LLM service."""
import json
import pytest
from unittest.mock import MagicMock, patch
from urllib.error import URLError
from llm_service import OllamaLLMService


@pytest.fixture
def mock_valid_config(monkeypatch):
    """Mock valid configuration values."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:latest")


@pytest.fixture
def patch_urlopen():
    """Fixture to patch urlopen and control its return value."""
    def _setter(payload):
        patcher = patch("llm_service._urllib_request.urlopen")
        mock_open = patcher.start()
        mock_response = MagicMock()
        mock_response.read.return_value = payload.encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_open.return_value = mock_response
        return patcher
    return _setter


@pytest.fixture
def mock_ollama(monkeypatch):
    """Mock the Ollama class to avoid actual LLM calls."""
    mock = MagicMock()
    monkeypatch.setattr("llm_service.Ollama", lambda **kwargs: mock)
    return mock


def _valid_models_payload():
    """Return a valid Ollama 0.13.5+ API response payload."""
    return json.dumps({
        "models": [
            {"name": "llama3.2:latest", "model": "llama3.2:latest"}
        ]
    })


def test_refine_query_trims_quotes(mock_valid_config, patch_urlopen, mock_ollama):
    patch_urlopen(_valid_models_payload())
    service = OllamaLLMService()
    
    mock_ollama.invoke.return_value = '"test query"'
    result = service.refine_query("some request")
    assert result == "test query"

    mock_ollama.invoke.return_value = "'another query'"
    result = service.refine_query("some request")
    assert result == "another query"


def test_summarize_search_results_uses_llm(mock_valid_config, patch_urlopen, mock_ollama):
    patch_urlopen(_valid_models_payload())
    service = OllamaLLMService()
    
    mock_ollama.invoke.return_value = "Summary of results"
    result = service.summarize_search_results("query", "search results", num_facts=3)
    
    assert result == "Summary of results"
    assert mock_ollama.invoke.called


def test_refine_query_raises_on_connection_loss(mock_valid_config, patch_urlopen, mock_ollama):
    patch_urlopen(_valid_models_payload())
    service = OllamaLLMService()
    
    mock_ollama.invoke.side_effect = ConnectionError("Lost connection")
    
    with pytest.raises(ConnectionError, match="Lost connection to Ollama while refining the query"):
        service.refine_query("some request")


def test_summarize_search_results_wraps_generic_errors(mock_valid_config, patch_urlopen, mock_ollama):
    patch_urlopen(_valid_models_payload())
    service = OllamaLLMService()
    
    mock_ollama.invoke.side_effect = Exception("Something went wrong")
    
    with pytest.raises(RuntimeError, match="Error generating summary"):
        service.summarize_search_results("query", "results", num_facts=3)


def test_verify_connection_handles_various_payloads(mock_valid_config, patch_urlopen, mock_ollama):
    patch_urlopen(_valid_models_payload())
    service = OllamaLLMService()
    
    # Test with new Ollama 0.13.5+ API format using "model" field
    patch_urlopen(json.dumps({"models": [{"model": "llama3.2:latest"}]}))
    assert service.verify_connection()
    
    # Test with new Ollama 0.13.5+ API format using "name" field
    patch_urlopen(json.dumps({"models": [{"name": "llama3.2:latest"}]}))
    assert service.verify_connection()


def test_verify_connection_raises_on_url_error(mock_valid_config, mock_ollama):
    """Test that verify_connection raises ConnectionError on URLError."""
    with patch("llm_service._urllib_request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = URLError("Connection refused")
        
        with pytest.raises(ConnectionError, match="Error connecting to Ollama"):
            OllamaLLMService()