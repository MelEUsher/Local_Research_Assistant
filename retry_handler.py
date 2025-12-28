"""Retry utilities for transient API operations."""
from __future__ import annotations

import functools
import time
from typing import Any, Callable, Tuple, TypeVar

from logger import logger


T = TypeVar("T")


class RateLimitError(RuntimeError):
    """Raised when an operation hits a rate limit that merits a retry."""


RETRYABLE_EXCEPTIONS: Tuple[type[BaseException], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
    RateLimitError,
)


def _should_retry(exception: BaseException) -> bool:
    return isinstance(exception, RETRYABLE_EXCEPTIONS)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorate an operation to retry with exponential backoff on transient failures."""

    if max_retries < 0:
        raise ValueError("max_retries must be zero or a positive integer")

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except BaseException as exc:  # pragma: no cover - we want to log all retryable errors
                    if not _should_retry(exc) or attempt >= max_retries:
                        raise

                    attempt += 1
                    delay = base_delay * (backoff_factor ** (attempt - 1))
                    logger.warning(
                        "Retry %d/%d for %s after %.2fs due to %s",
                        attempt,
                        max_retries,
                        func.__name__,
                        delay,
                        exc,
                    )
                    time.sleep(delay)

        return wrapper

    return decorator


__all__ = ["retry_with_backoff", "RateLimitError"]
