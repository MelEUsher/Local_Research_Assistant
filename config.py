"""Configuration module for the research assistant."""
import os
from dotenv import load_dotenv

load_dotenv()

# Google Search API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "").strip()


def validate_google_credentials():
    """Ensure both Google Search credentials are populated before use."""
    missing = [
        name for name, value in (
            ("GOOGLE_API_KEY", GOOGLE_API_KEY),
            ("GOOGLE_CSE_ID", GOOGLE_CSE_ID),
        )
        if not value
    ]

    if missing:
        missing_vars = " and ".join(missing) if len(missing) == 2 else missing[0]
        raise ValueError(
            f"Missing Google Search credentials: {missing_vars}. "
            "Provide valid GOOGLE_API_KEY and GOOGLE_CSE_ID values in the environment or .env before starting the assistant."
        )

# Ollama Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


# Ensure credentials are validated as soon as the module is loaded.
validate_google_credentials()
