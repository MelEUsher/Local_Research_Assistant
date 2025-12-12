"""Configuration module for the research assistant."""
import os
from dotenv import load_dotenv

load_dotenv()

# Google Search API
GOOGLE_API_KEY = ""
GOOGLE_CSE_ID = ""

# Ollama Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

