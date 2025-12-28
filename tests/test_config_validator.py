"""Tests for configuration validation helpers."""
from unittest.mock import MagicMock, patch

import pytest

from config_validator import ConfigValidator


class DummyUrlResponse:
    """Minimal object that mimics urllib response context manager."""

    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestConfigValidator:
    """Test suite for ConfigValidator."""

    def test_validate_google_config_valid(self, mock_valid_config):
        validator = ConfigValidator()

        assert validator.validate_google_config() == []

    def test_validate_google_config_missing_api_key(self, mock_invalid_config):
        validator = ConfigValidator()
        issues = validator.validate_google_config()

        assert "GOOGLE_API_KEY is missing." in issues

    def test_validate_google_config_missing_cse_id(self, mock_valid_config):
        with patch.dict("os.environ", {"GOOGLE_CSE_ID": ""}, clear=False):
            validator = ConfigValidator()

        issues = validator.validate_google_config()

        assert "GOOGLE_CSE_ID is missing." in issues

    def test_validate_ollama_config_valid(self, mock_valid_config):
        validator = ConfigValidator()

        assert validator.validate_ollama_config() == []

    def test_validate_ollama_config_invalid_url(self, mock_valid_config):
        with patch.dict("os.environ", {"OLLAMA_BASE_URL": "ftp://bad-url"}, clear=False):
            validator = ConfigValidator()

        issues = validator.validate_ollama_config()

        assert "OLLAMA_BASE_URL must start with http:// or https://." in issues

    def test_validate_ollama_config_missing_model(self, mock_valid_config):
        with patch.dict("os.environ", {"OLLAMA_MODEL": ""}, clear=False):
            validator = ConfigValidator()

        issues = validator.validate_ollama_config()

        assert "OLLAMA_MODEL is missing." in issues

    def test_validate_all_reports_success(self, mock_valid_config):
        validator = ConfigValidator()

        assert validator.validate_all() == []

    def test_validate_all_reports_multiple_issues(self, mock_invalid_config):
        validator = ConfigValidator()
        issues = validator.validate_all()

        assert issues

    def test_check_ollama_connection_success(self, mock_valid_config):
        validator = ConfigValidator()
        with patch("config_validator.urlopen", MagicMock(return_value=DummyUrlResponse(status=200))):
            result, message = validator.check_ollama_connection()

        assert result
        assert "Connected to Ollama" in message

    def test_check_ollama_connection_failure(self, mock_valid_config):
        validator = ConfigValidator()
        with patch("config_validator.urlopen", MagicMock(side_effect=ValueError("boom"))):
            result, message = validator.check_ollama_connection()

        assert not result
        assert "Unexpected error connecting" in message
