"""Configuration module for the research assistant."""
import os
from dotenv import load_dotenv

from config_validator import ConfigValidator

load_dotenv()

# Google Search API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "").strip()

# Ollama Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


def _build_validator() -> ConfigValidator:
    """Create a validator that reflects the loaded configuration values."""
    return ConfigValidator(
        google_api_key=GOOGLE_API_KEY,
        google_cse_id=GOOGLE_CSE_ID,
        ollama_base_url=OLLAMA_BASE_URL,
        ollama_model=OLLAMA_MODEL,
    )


def validate_config():
    """Return detailed validation results for the current configuration."""
    validator = _build_validator()
    google_issues = validator.validate_google_config()
    ollama_issues = validator.validate_ollama_config()
    issues = google_issues + ollama_issues

    return {
        "valid": not issues,
        "issues": issues,
        "details": {
            "google": google_issues,
            "ollama": ollama_issues,
        },
    }


def validate_google_credentials():
    """Ensure both Google Search credentials are populated before use."""
    validator = _build_validator()
    missing = validator.validate_google_config()

    if missing:
        raise ValueError(
            "Google Search configuration invalid: " + " ".join(missing)
        )
