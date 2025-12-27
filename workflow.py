"""LangGraph workflow for research assistance."""
from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, END
from search_service import GoogleSearchService
from llm_service import OllamaLLMService
import re


class ResearchState(TypedDict):
    """State object for the research workflow."""
    original_query: str
    refined_query: str
    search_results: List[Dict[str, str]]
    formatted_results: str
    summary: str
    output: str


class ResearchWorkflow:
    """LangGraph workflow for research assistance."""
    
    def __init__(self):
        self.search_service = GoogleSearchService()
        self.llm_service = OllamaLLMService()
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
    
    def _refine_query_node(self, state: ResearchState) -> ResearchState:
        """Node: Refine the user's query for better search results."""
        print(f"🔍 Refining query: {state['original_query']}")
        refined = self.llm_service.refine_query(state['original_query'])
        state['refined_query'] = refined
        print(f"✅ Refined query: {refined}")
        return state
    
    def _fetch_sources_node(self, state: ResearchState) -> ResearchState:
        """Node: Fetch information from web sources."""
        print(f"🌐 Searching the web...")
        num_results = 5
        if not (1 <= num_results <= 10):
            raise ValueError("num_results for fetching sources must be between 1 and 10.")
        results = self.search_service.search(state['refined_query'], num_results=num_results)
        state['search_results'] = results
        state['formatted_results'] = self.search_service.format_results_for_llm(results)
        print(f"✅ Found {len(results)} search results")
        return state
    
    def _summarize_node(self, state: ResearchState) -> ResearchState:
        """Node: Summarize search results into structured facts."""
        print(f"📝 Summarizing results...")
        # Extract number of facts from original query if specified
        num_facts = self._extract_num_facts(state['original_query'])
        summary = self.llm_service.summarize_search_results(
            state['original_query'],
            state['formatted_results'],
            num_facts=num_facts
        )
        state['summary'] = summary
        print(f"✅ Summary generated")
        return state
    
    def _format_output_node(self, state: ResearchState) -> ResearchState:
        """Node: Format the final output."""
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
        return state
    
    def _extract_num_facts(self, query: str) -> int:
        """Extract the number of facts requested from the query."""
        # Look for patterns like "3 facts", "find 5 facts", etc.
        match = re.search(r'(\d+)\s*facts?', query.lower())
        if match:
            return int(match.group(1))
        return 3  # Default to 3
    
    def run(self, research_request: str) -> str:
        """
        Execute the research workflow.
        
        Args:
            research_request: Natural language research request
        
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
            "output": ""
        }
        
        final_state = self.graph.invoke(initial_state)
        return final_state['output']
