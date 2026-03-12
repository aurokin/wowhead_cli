from __future__ import annotations

import random
import time
from typing import Any

import httpx

DEFAULT_RETRY_ATTEMPTS = 3
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def backoff_seconds(attempt: int) -> float:
    base = 0.35 * (2 ** (attempt - 1))
    jitter = random.uniform(0.0, 0.12)
    return min(4.0, base + jitter)


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
            response.close()
            time.sleep(backoff_seconds(attempt))
            continue

        response.raise_for_status()
        return response

    raise AssertionError("Unreachable retry loop exit.")

