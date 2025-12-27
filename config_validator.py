"""Helpers for validating configuration values."""
import os
import re
from typing import List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class ConfigValidator:
    """Validate configuration options for the research assistant."""

    GOOGLE_API_KEY_PREFIX = "AIza"
    GOOGLE_CSE_ID_PATTERN = re.compile(r"^([0-9a-f]+|\d{16}:[0-9A-Za-z_-]+)$", re.IGNORECASE)
    OLLAMA_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
    DEFAULT_OLLAMA_URL = "http://localhost:11434"

    def __init__(
        self,
        google_api_key: Optional[str] = None,
        google_cse_id: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
        ollama_model: Optional[str] = None,
    ):
        self.google_api_key = (google_api_key or os.getenv("GOOGLE_API_KEY", "")).strip()
        self.google_cse_id = (google_cse_id or os.getenv("GOOGLE_CSE_ID", "")).strip()
        self.ollama_base_url = (
            (ollama_base_url or os.getenv("OLLAMA_BASE_URL", "")).strip() or self.DEFAULT_OLLAMA_URL
        )
        self.ollama_model = (ollama_model or os.getenv("OLLAMA_MODEL", "")).strip() or ""

    def validate_google_config(self) -> List[str]:
        """Return configuration issues related to Google Search credentials."""
        issues = []
        if not self.google_api_key:
            issues.append("GOOGLE_API_KEY is missing.")
        elif not self.google_api_key.startswith(self.GOOGLE_API_KEY_PREFIX):
            issues.append(
                "GOOGLE_API_KEY looks malformed; it should start with 'AIza'."
            )

        if not self.google_cse_id:
            issues.append("GOOGLE_CSE_ID is missing.")
        elif not self.GOOGLE_CSE_ID_PATTERN.match(self.google_cse_id):
            issues.append(
                "GOOGLE_CSE_ID does not match the expected pattern (digits, colon, and ID suffix)."
            )

        return issues

    def validate_ollama_config(self) -> List[str]:
        """Return configuration issues related to Ollama settings."""
        issues = []
        if not self.ollama_base_url:
            issues.append("OLLAMA_BASE_URL is missing.")
        else:
            parsed = urlparse(self.ollama_base_url)
            if parsed.scheme not in {"http", "https"}:
                issues.append(
                    "OLLAMA_BASE_URL must start with http:// or https://."
                )
            if not parsed.netloc:
                issues.append("OLLAMA_BASE_URL is not a valid URL.")

        if not self.ollama_model:
            issues.append("OLLAMA_MODEL is missing.")
        elif not self.OLLAMA_MODEL_PATTERN.match(self.ollama_model):
            issues.append(
                "OLLAMA_MODEL contains unsupported characters; use letters, digits, dots, underscores, or hyphens."
            )

        return issues

    def validate_all(self) -> List[str]:
        """Run every validation rule and return any issues found."""
        return self.validate_google_config() + self.validate_ollama_config()

    def check_ollama_connection(self, timeout: float = 2.0) -> Tuple[bool, str]:
        """Optional helper that tries to reach the configured Ollama server."""
        if not self.ollama_base_url:
            return False, "OLLAMA_BASE_URL is not configured."

        request = Request(self.ollama_base_url)
        try:
            with urlopen(request, timeout=timeout) as response:
                return True, f"Connected to Ollama ({response.status})."
        except HTTPError as http_error:
            return True, (f"Reached Ollama but got HTTP {http_error.code}: {http_error.reason}.")
        except URLError as url_error:
            return False, f"Unable to reach Ollama: {url_error.reason}."
        except Exception as exc:  # pragma: no cover - best effort
            return False, f"Unexpected error connecting to Ollama: {exc}."

    def check_google_api_quota(self) -> Tuple[bool, str]:
        """Explain why we cannot check Google quota without hitting the API."""
        if not self.google_api_key:
            return False, "Cannot check quota without GOOGLE_API_KEY."

        return (
            False,
            "Quota checks require Google Search API calls, which are not executed by this validator."
        )
