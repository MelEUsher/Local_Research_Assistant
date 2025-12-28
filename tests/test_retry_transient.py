"""Test that retry decorator handles transient failures correctly."""
import io
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logger import logger as app_logger
from retry_handler import retry_with_backoff

retry_logger = app_logger
retry_logger.setLevel(logging.WARNING)

attempt_count = 0


@retry_with_backoff(max_retries=3, base_delay=0.1)
def flaky_connection():
    global attempt_count
    attempt_count += 1
    if attempt_count == 1:
        raise ConnectionError("Simulated connection failure")
    if attempt_count == 2:
        raise TimeoutError("Simulated timeout")
    return "success"


def main():
    global attempt_count
    attempt_count = 0
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setLevel(logging.WARNING)
    retry_logger.addHandler(handler)

    start = time.time()
    result = flaky_connection()
    duration = time.time() - start

    retry_logger.removeHandler(handler)
    handler.close()

    assert result == "success", f"Expected success, got {result!r}"
    assert attempt_count == 3, f"Expected 3 attempts, got {attempt_count}"
    assert duration >= 0.28, f"Expected at least 0.28s delay, got {duration:.2f}s"
    assert duration <= 0.8, f"Backoff took too long ({duration:.2f}s)"

    log_output = buffer.getvalue()
    assert "Retry 1/3" in log_output
    assert "Retry 2/3" in log_output
    assert "flaky_connection" in log_output

    print("✓ Retry decorator works correctly for transient errors")


if __name__ == "__main__":
    main()
