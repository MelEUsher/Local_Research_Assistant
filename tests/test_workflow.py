"""Unit tests for the LangGraph research workflow."""
import copy

import pytest

from workflow import ResearchWorkflow


def test_full_workflow_returns_output(mock_google_search_service, mock_ollama_service):
    mock_ollama_service.summarize_search_results.return_value = "Fact summary stub."
    workflow = ResearchWorkflow()

    output = workflow.run("Explain the history of AI.")

    assert "Fact summary stub." in output
    assert "https://example.com/ai" in output
    mock_google_search_service.search.assert_called()
    mock_google_search_service.format_results_for_llm.assert_called()
    mock_ollama_service.refine_query.assert_called()
    mock_ollama_service.summarize_search_results.assert_called()


def test_nodes_update_state(mock_google_search_service, mock_ollama_service, sample_state):
    workflow = ResearchWorkflow()
    state = copy.deepcopy(sample_state)

    state = workflow._refine_query_node(state)
    assert state["refined_query"] == "refined query stub"

    state = workflow._fetch_sources_node(state)
    assert state["search_results"]
    assert state["formatted_results"]
    mock_google_search_service.search.assert_called()

    state = workflow._summarize_node(state)
    assert state["summary"] == mock_ollama_service.summarize_search_results.return_value

    state = workflow._format_output_node(state)
    assert "Research Results" in state["output"]
    assert state["output"].endswith("\n")


def test_extract_num_facts_detects_requested_amount(mock_google_search_service, mock_ollama_service):
    workflow = ResearchWorkflow()

    assert workflow._extract_num_facts("Share 5 facts about AI.") == 5
    assert workflow._extract_num_facts("Tell me more.") == 3


def test_summary_cache_prevents_duplicate_calls(mock_google_search_service, mock_ollama_service, sample_state):
    workflow = ResearchWorkflow()
    state1 = copy.deepcopy(sample_state)
    workflow._summarize_node(state1)

    state2 = copy.deepcopy(sample_state)
    workflow._summarize_node(state2)

    assert mock_ollama_service.summarize_search_results.call_count == 1


def test_fetch_sources_respects_cache(mock_google_search_service, mock_ollama_service, sample_state):
    workflow = ResearchWorkflow()
    state = copy.deepcopy(sample_state)

    workflow._fetch_sources_node(state)
    workflow._fetch_sources_node(state)

    assert mock_google_search_service.search.call_count == 1
