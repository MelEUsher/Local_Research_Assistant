"""Test that fatal errors are surfaced immediately without retries."""
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

fatal_attempts = 0


@retry_with_backoff(max_retries=2, base_delay=0.1)
def fatal_failure():
    global fatal_attempts
    fatal_attempts += 1
    raise ValueError("Simulated fatal error")


def main():
    global fatal_attempts
    fatal_attempts = 0
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setLevel(logging.WARNING)
    retry_logger.addHandler(handler)

    start = time.time()
    try:
        fatal_failure()
    except ValueError:
        pass
    else:
        raise AssertionError("fatal_failure should have raised ValueError")
    duration = time.time() - start

    retry_logger.removeHandler(handler)
    handler.close()

    assert fatal_attempts == 1, f"Fatal errors should not retry; got {fatal_attempts} attempts"
    assert duration <= 0.2, f"Fatal errors should return quickly; took {duration:.2f}s"
    assert "Retry" not in buffer.getvalue()

    print("✓ Fatal errors fail fast without retries")


if __name__ == "__main__":
    main()
