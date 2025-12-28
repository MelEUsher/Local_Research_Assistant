"""Utility for exporting research outputs."""
from __future__ import annotations

import datetime
import json
import os
import re
from typing import Optional


class ExportService:
    """Handles exporting research outputs to markdown or JSON."""

    def __init__(self, default_directory: str = "outputs"):
        self.default_directory = default_directory

    def save_to_markdown(
        self, result: str, filename: str, directory: Optional[str] = None
    ) -> str:
        """Write the markdown output to a sanitized file path."""
        target_dir = directory or self.default_directory
        self._ensure_directory(target_dir)
        safe_name = self._sanitize_name(filename)
        filename_with_ext = self._ensure_extension(safe_name, ".md")
        output_path = os.path.join(target_dir, filename_with_ext)
        try:
            with open(output_path, "w", encoding="utf-8") as file:
                file.write(result)
            return output_path
        except PermissionError as e:
            raise RuntimeError(
                f"Permission denied when writing to {output_path}. "
                "Check file permissions and try again."
            ) from e
        except OSError as e:
            raise RuntimeError(
                f"Failed to write export file to {output_path}: {e}"
            ) from e

    def save_to_json(
        self, state: dict, filename: str, directory: Optional[str] = None
    ) -> str:
        """Persist the workflow state to a JSON file."""
        target_dir = directory or self.default_directory
        self._ensure_directory(target_dir)
        safe_name = self._sanitize_name(filename)
        filename_with_ext = self._ensure_extension(safe_name, ".json")
        output_path = os.path.join(target_dir, filename_with_ext)
        try:
            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(state, file, ensure_ascii=False, indent=2)
            return output_path
        except PermissionError as e:
            raise RuntimeError(
                f"Permission denied when writing to {output_path}. "
                "Check file permissions and try again."
            ) from e
        except OSError as e:
            raise RuntimeError(
                f"Failed to write export file to {output_path}: {e}"
            ) from e

    def auto_generate_filename(self, query: str) -> str:
        """Generate a sanitized filename with a timestamp suffix."""
        safe_query = self._sanitize_name(query)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{safe_query}_{timestamp}"

    def _ensure_directory(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)

    def _sanitize_name(self, value: str) -> str:
        cleaned = (value or "").strip()
        cleaned = re.sub(r"\s+", "_", cleaned)
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", cleaned)
        cleaned = cleaned.strip("_")
        # Limit length to avoid filesystem issues (reserve 50 chars for timestamp/extension)
        max_length = 200
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length].rstrip("_")
        return cleaned or "result"

    def _ensure_extension(self, filename: str, extension: str) -> str:
        if not filename.lower().endswith(extension):
            filename = f"{filename}{extension}"
        return filename
