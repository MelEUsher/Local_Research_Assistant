"""Unit tests for the Google Search integration."""
import json
from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError

from search_service import GoogleSearchService


@pytest.fixture
def dummy_google_service(monkeypatch, sample_search_results):
    """Simulate the googleapiclient discovery response chain."""
    mock_service = MagicMock()
    mock_cse = MagicMock()
    mock_list = MagicMock()
    mock_list.execute.return_value = {"items": sample_search_results}
    mock_cse.list.return_value = mock_list
    mock_service.cse.return_value = mock_cse
    monkeypatch.setattr("search_service.build", MagicMock(return_value=mock_service))
    return mock_service


def test_search_returns_formatted_results(mock_valid_config, dummy_google_service):
    service = GoogleSearchService()
    results = service.search("ai research", num_results=2)

    assert len(results) == 2
    assert results[0]["title"] == "AI Overview"
    dummy_google_service.cse.return_value.list.assert_called_with(
        q="ai research",
        cx=service._cse_id,
        num=2,
    )


def test_format_results_for_llm_matches_expected_structure(mock_valid_config, dummy_google_service, sample_search_results):
    service = GoogleSearchService()
    formatted = service.format_results_for_llm(sample_search_results)

    assert "=== Search Results ===" in formatted
    assert "AI Overview" in formatted
    assert "URL: https://example.com/ai" in formatted


def test_search_raises_value_error_for_invalid_key(mock_valid_config, dummy_google_service):
    service = GoogleSearchService()
    error_payload = json.dumps({
        "error": {
            "errors": [
                {"reason": "keyInvalid", "message": "Bad API key"}
            ]
        }
    }).encode("utf-8")
    http_error = HttpError(MagicMock(status=403, reason="Forbidden"), error_payload)

    with patch.object(service, "_execute_cse_list", side_effect=http_error):
        with pytest.raises(ValueError) as excinfo:
            service.search("ai research")

    assert "invalid GOOGLE_API_KEY" in str(excinfo.value)


def test_search_raises_connection_error_for_network_issue(mock_valid_config, dummy_google_service):
    service = GoogleSearchService()

    with patch.object(service, "_execute_cse_list", side_effect=ConnectionError("no connection")):
        with pytest.raises(ConnectionError):
            service.search("ai research")


def test_test_connection_invokes_query(mock_valid_config, dummy_google_service):
    service = GoogleSearchService()
    service._execute_cse_list = MagicMock(return_value={})

    assert service.test_connection()
    service._execute_cse_list.assert_called_once_with(query="testing connection", num_results=1)
