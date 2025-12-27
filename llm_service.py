"""Ollama LLM integration using LangChain."""
import json
import socket
from urllib import error as _urllib_error, parse as _urllib_parse, request as _urllib_request

from config import OLLAMA_BASE_URL, OLLAMA_MODEL

try:
    from langchain_community.llms import Ollama
except ImportError:
    # Fallback for different LangChain versions
    from langchain_community.llms.ollama import Ollama


class OllamaLLMService:
    """Service for interacting with Ollama LLM."""
    
    def __init__(self, model_name: str = None, base_url: str = None):
        self.model_name = model_name or OLLAMA_MODEL
        self.base_url = base_url or OLLAMA_BASE_URL
        try:
            self.verify_connection()
        except ConnectionError as exc:
            raise ConnectionError(
                f"Unable to reach Ollama at {self.base_url}. {exc}"
            ) from exc
        except ValueError as exc:
            raise ValueError(
                f"Failed to verify model '{self.model_name}'. {exc}"
            ) from exc

        self.llm = Ollama(
            model=self.model_name,
            base_url=self.base_url
        )

    def verify_connection(self) -> bool:
        """Ensure the Ollama server is reachable and that the desired model exists."""
        models_url = _urllib_parse.urljoin(
            f"{self.base_url.rstrip('/')}/",
            "api/models"
        )

        try:
            with _urllib_request.urlopen(models_url, timeout=5) as response:
                raw = response.read().decode("utf-8")
        except _urllib_error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, ConnectionRefusedError):
                raise ConnectionError(
                    f"Could not connect to Ollama at {self.base_url}. Run 'ollama serve' and try again."
                ) from exc
            if isinstance(reason, socket.timeout):
                raise ConnectionError(
                    f"Connection to Ollama at {self.base_url} timed out. Ensure the service is running."
                ) from exc
            raise ConnectionError(
                f"Error connecting to Ollama at {self.base_url}: {exc}"
            ) from exc

        try:
            models = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Received an unexpected response while querying Ollama models."
            ) from exc

        if not isinstance(models, list):
            raise ValueError(
                "Ollama returned an unexpected model list structure; expected a JSON array."
            )

        model_names = {
            entry.get("name") or entry.get("id")
            for entry in models
            if isinstance(entry, dict)
        }
        if self.model_name not in model_names:
            raise ValueError(
                f"Model '{self.model_name}' was not found at {self.base_url}. Run 'ollama pull {self.model_name}' before retrying."
            )

        return True

    def summarize_search_results(
        self, 
        query: str, 
        search_results: str, 
        num_facts: int = 3
    ) -> str:
        """
        Summarize search results into structured facts.
        
        Args:
            query: Original research query
            search_results: Formatted search results
            num_facts: Number of facts to extract
        
        Returns:
            Summarized response with structured facts
        """
        prompt = f"""You are a research assistant. Based on the search results below, extract {num_facts} key facts related to the query: "{query}"

Format your response as follows:
1. Start with a brief summary (2-3 sentences)
2. Then list {num_facts} key facts, numbered 1-{num_facts}
3. Each fact should be concise but informative (1-2 sentences)
4. Cite sources when relevant

Search Results:
{search_results}

Response:"""
        
        try:
            response = self.llm.invoke(prompt)
            return response
        except (ConnectionError, OSError) as exc:
            raise ConnectionError(
                "Lost connection to Ollama while generating the summary. Run 'ollama serve' and try again."
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Error generating summary: {exc}") from exc

    def refine_query(self, research_request: str) -> str:
        """
        Refine the user's research request into a better search query.
        
        Args:
            research_request: Original natural language request
        
        Returns:
            Refined search query string
        """
        prompt = f"""Convert the following research request into a clear, concise search query optimized for web search.

Research Request: "{research_request}"

Provide only the search query (no explanation):"""
        
        try:
            refined = self.llm.invoke(prompt)
            # Clean up the response
            refined = refined.strip().strip('"').strip("'")
            return refined
        except (ConnectionError, OSError) as exc:
            raise ConnectionError(
                "Lost connection to Ollama while refining the query. Run 'ollama serve' and try again."
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Error refining query: {exc}") from exc
