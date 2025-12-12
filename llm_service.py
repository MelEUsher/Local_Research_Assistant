"""Ollama LLM integration using LangChain."""
try:
    from langchain_community.llms import Ollama
except ImportError:
    # Fallback for different LangChain versions
    from langchain_community.llms.ollama import Ollama

from config import OLLAMA_BASE_URL, OLLAMA_MODEL


class OllamaLLMService:
    """Service for interacting with Ollama LLM."""
    
    def __init__(self, model_name: str = None, base_url: str = None):
        self.model_name = model_name or OLLAMA_MODEL
        self.base_url = base_url or OLLAMA_BASE_URL
        self.llm = Ollama(
            model=self.model_name,
            base_url=self.base_url
        )
    
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
        except Exception as e:
            raise Exception(f"Error generating summary: {str(e)}")
    
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
        except Exception as e:
            raise Exception(f"Error refining query: {str(e)}")

