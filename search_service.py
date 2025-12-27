"""Google Search API integration for fetching web information."""
import json
from typing import List, Dict

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import GOOGLE_API_KEY, GOOGLE_CSE_ID, validate_google_credentials
from logger import logger


class GoogleSearchService:
    """Service for performing web searches using Google Custom Search API."""
    
    def __init__(self):
        validate_google_credentials()
        self.service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        # Keep a reference to the CSE ID to avoid relying on globals during execution.
        self._cse_id = GOOGLE_CSE_ID

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
            logger.info(
                "Searching the web for query '%s' with num_results=%d",
                query,
                num_results,
            )
            results = []
            # Google Custom Search API allows max 10 results per request
            max_per_request = min(num_results, 10)
            search_result = self._execute_cse_list(
                query=query,
                num_results=max_per_request,
            )
            
            items = search_result.get("items", [])
            
            for item in items:
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", "")
                })

            logger.info(
                "Search completed with %d results for query '%s'",
                len(results),
                query,
            )
            return results
        
        except HttpError as http_error:
            logger.exception("HTTP error occurred during search for query '%s'", query)
            self._handle_http_error(http_error, "performing a search")
        except (ConnectionError, TimeoutError, OSError) as network_error:
            logger.exception("Network error occurred during search for query '%s'", query)
            self._handle_network_error(network_error, "performing a search")

    def format_results_for_llm(self, results: List[Dict[str, str]]) -> str:
        """Format search results into a string suitable for LLM processing."""
        formatted = "=== Search Results ===\n\n"
        for i, result in enumerate(results, 1):
            formatted += f"Result {i}:\n"
            formatted += f"Title: {result['title']}\n"
            formatted += f"URL: {result['link']}\n"
            formatted += f"Summary: {result['snippet']}\n\n"
        return formatted

    def test_connection(self) -> bool:
        """Execute a minimal search request to verify Google Search credentials."""
        try:
            self._execute_cse_list(
                query="testing connection",
                num_results=1,
            )
        except HttpError as http_error:
            self._handle_http_error(http_error, "testing Google Search API credentials")
        except (ConnectionError, TimeoutError, OSError) as network_error:
            self._handle_network_error(network_error, "testing Google Search API credentials")
        return True

    def _execute_cse_list(self, query: str, num_results: int) -> Dict:
        return self.service.cse().list(
            q=query,
            cx=self._cse_id,
            num=num_results
        ).execute()

    def _handle_network_error(self, error: Exception, context: str):
        logger.error(
            "Network error while %s: %s", context, error, exc_info=True
        )
        raise ConnectionError(
            f"Network error while {context}; check connectivity and proxy settings."
        ) from error

    def _handle_http_error(self, http_error: HttpError, context: str):
        logger.error(
            "HTTP error while %s: %s", context, http_error, exc_info=True
        )
        reason, message = self._parse_http_error(http_error)
        base_message = f"Google Search API error while {context}"

        if reason == "keyInvalid":
            raise ValueError(
                f"{base_message}: invalid GOOGLE_API_KEY. "
                "Ensure the key is enabled for the Custom Search JSON API and matches your configuration."
            ) from http_error

        if reason == "cxInvalid":
            raise ValueError(
                f"{base_message}: invalid GOOGLE_CSE_ID. "
                "Verify the Custom Search Engine ID matches the value set in your environment."
            ) from http_error

        if reason in {"dailyLimitExceeded", "quotaExceeded"}:
            raise RuntimeError(
                f"{base_message}: quota exceeded ({reason}). "
                "Wait for quotas to reset or request additional quota in the Google Cloud console."
            ) from http_error

        raise RuntimeError(
            f"{base_message}: {message or 'unexpected response from Google Search API'}"
        ) from http_error

    @staticmethod
    def _parse_http_error(http_error: HttpError):
        content = getattr(http_error, "content", None)
        if isinstance(content, bytes):
            try:
                content = content.decode("utf-8")
            except UnicodeDecodeError:
                content = content.decode("utf-8", errors="ignore")

        if content:
            try:
                payload = json.loads(content)
            except (ValueError, TypeError):
                return None, content

            error_info = payload.get("error", {})
            errors = error_info.get("errors", [])

            if errors:
                first_error = errors[0]
                return first_error.get("reason"), first_error.get("message") or error_info.get("message")

            return error_info.get("code"), error_info.get("message")

        return None, str(http_error)
