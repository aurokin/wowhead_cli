from __future__ import annotations

import random
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

DEFAULT_RETRY_ATTEMPTS = 3
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def backoff_seconds(attempt: int) -> float:
    base = 0.35 * (2 ** (attempt - 1))
    jitter = random.uniform(0.0, 0.12)
    return float(min(4.0, base + jitter))


def retry_after_seconds(response: httpx.Response) -> float | None:
    raw_value = response.headers.get("Retry-After")
    if raw_value is None:
        return None
    value = raw_value.strip()
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        seconds = (retry_at - datetime.now(UTC)).total_seconds()
    return max(0.0, seconds)


def request_with_retries(
    client: httpx.Client,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
) -> httpx.Response:
    attempts = max(1, retry_attempts)
    for attempt in range(1, attempts + 1):
        try:
            response = client.get(url, params=params)
        except httpx.RequestError:
            if attempt >= attempts:
                raise
            time.sleep(backoff_seconds(attempt))
            continue

        if response.status_code in RETRYABLE_STATUS_CODES and attempt < attempts:
            sleep_seconds = retry_after_seconds(response) or backoff_seconds(attempt)
            response.close()
            time.sleep(sleep_seconds)
            continue

        response.raise_for_status()
        return response

    raise AssertionError("Unreachable retry loop exit.")
