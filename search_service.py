"""Google Search API integration for fetching web information."""
from typing import List, Dict
from googleapiclient.discovery import build
from config import GOOGLE_API_KEY, GOOGLE_CSE_ID


class GoogleSearchService:
    """Service for performing web searches using Google Custom Search API."""
    
    def __init__(self):
        if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
            raise ValueError(
                "GOOGLE_API_KEY and GOOGLE_CSE_ID must be set in environment variables"
            )
        self.service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
    
    def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Perform a web search and return results.
        
        Args:
            query: Search query string
            num_results: Number of results to return (max 10 per request)
        
        Returns:
            List of dictionaries containing 'title', 'link', and 'snippet'
        """
        try:
            results = []
            # Google Custom Search API allows max 10 results per request
            max_per_request = min(num_results, 10)
            
            search_result = self.service.cse().list(
                q=query,
                cx=GOOGLE_CSE_ID,
                num=max_per_request
            ).execute()
            
            items = search_result.get("items", [])
            
            for item in items:
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", "")
                })
            
            return results
        
        except Exception as e:
            raise Exception(f"Error performing search: {str(e)}")
    
    def format_results_for_llm(self, results: List[Dict[str, str]]) -> str:
        """Format search results into a string suitable for LLM processing."""
        formatted = "=== Search Results ===\n\n"
        for i, result in enumerate(results, 1):
            formatted += f"Result {i}:\n"
            formatted += f"Title: {result['title']}\n"
            formatted += f"URL: {result['link']}\n"
            formatted += f"Summary: {result['snippet']}\n\n"
        return formatted

