"""Unit tests for the Ollama LLM capture logic."""
import json
from unittest.mock import MagicMock

import pytest

import llm_service as llm_service_module
from llm_service import OllamaLLMService, _urllib_error


class DummyResponse:
    """Minimal response that behaves like urllib response context manager."""

    def __init__(self, payload: str):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._payload.encode("utf-8")


@pytest.fixture
def patch_urlopen(monkeypatch):
    """Allow tests to replace urlopen behavior with success or failure."""

    def _setter(payload_or_exception):
        if isinstance(payload_or_exception, Exception):
            monkeypatch.setattr(
                "llm_service._urllib_request.urlopen",
                MagicMock(side_effect=payload_or_exception),
            )
        else:
            monkeypatch.setattr(
                "llm_service._urllib_request.urlopen",
                MagicMock(return_value=DummyResponse(payload_or_exception)),
            )

    return _setter


@pytest.fixture
def mock_ollama(monkeypatch):
    """Replace the Ollama client with a simple mock."""
    mock_llm = MagicMock()
    monkeypatch.setattr("llm_service.Ollama", MagicMock(return_value=mock_llm))
    return mock_llm


def _valid_models_payload():
    return json.dumps({"models": [{"name": llm_service_module.OLLAMA_MODEL}]})


def test_refine_query_trims_quotes(mock_valid_config, patch_urlopen, mock_ollama):
    patch_urlopen(_valid_models_payload())
    mock_ollama.invoke.return_value = ' "Refined AI query" '
    service = OllamaLLMService()

    refined = service.refine_query("Tell me about ai")

    assert refined == "Refined AI query"
    assert mock_ollama.invoke.called


def test_summarize_search_results_uses_llm(mock_valid_config, patch_urlopen, mock_ollama):
    patch_urlopen(_valid_models_payload())
    mock_ollama.invoke.return_value = "1. Fact"
    service = OllamaLLMService()

    summary = service.summarize_search_results("AI", "Formatted", num_facts=2)

    assert summary == "1. Fact"
    mock_ollama.invoke.assert_called()


def test_refine_query_raises_on_connection_loss(mock_valid_config, patch_urlopen, mock_ollama):
    patch_urlopen(_valid_models_payload())
    mock_ollama.invoke.side_effect = ConnectionError("lost")
    service = OllamaLLMService()

    with pytest.raises(ConnectionError):
        service.refine_query("AI overview")


def test_summarize_search_results_wraps_generic_errors(mock_valid_config, patch_urlopen, mock_ollama):
    patch_urlopen(_valid_models_payload())
    mock_ollama.invoke.side_effect = ValueError("bad response")
    service = OllamaLLMService()

    with pytest.raises(RuntimeError) as excinfo:
        service.summarize_search_results("AI", "formatted", num_facts=1)

    assert "Error generating summary" in str(excinfo.value)


def test_verify_connection_handles_various_payloads(mock_valid_config, patch_urlopen, mock_ollama):
    patch_urlopen(_valid_models_payload())
    service = OllamaLLMService()

    patch_urlopen(json.dumps([{"model": "llama3.2"}]))
    assert service.verify_connection()


def test_verify_connection_raises_on_url_error(mock_valid_config, patch_urlopen, mock_ollama):
    patch_urlopen(_valid_models_payload())
    service = OllamaLLMService()

    patch_urlopen(_urllib_error.URLError("refused"))
    with pytest.raises(ConnectionError):
        service.verify_connection()
