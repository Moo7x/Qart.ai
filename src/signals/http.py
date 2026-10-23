"""Polite JSON GET shared by every public-data fetcher (Hacker News, ATS job boards).

Timeout per request, a pause after each success, and retries with doubling backoff for errors
that may pass (timeouts, connection errors, 429 and 5xx). Other client errors (404 for a wrong
board token, 400, 401, 403) are raised at once: retrying them only adds load.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Politeness:
    timeout_s: float = 30.0
    retries: int = 3
    backoff_s: float = 2.0  # first retry wait; doubles each time
    pause_s: float = 0.5  # pause after each successful request


DEFAULT_POLITENESS = Politeness()


def retryable(exc: httpx.HTTPError) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    return True  # timeouts, connection and protocol errors


def get_json(
    client: httpx.Client,
    url: str,
    params: dict[str, Any] | None = None,
    polite: Politeness = DEFAULT_POLITENESS,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    wait = polite.backoff_s
    for attempt in range(1, polite.retries + 1):
        try:
            response = client.get(url, params=params, timeout=polite.timeout_s)
            response.raise_for_status()
            sleep(polite.pause_s)
            return response.json()
        except httpx.HTTPError as exc:
            if attempt == polite.retries or not retryable(exc):
                raise
            logger.warning("GET %s failed (%s); retrying in %.0f s", url, exc, wait)
            sleep(wait)
            wait *= 2
    raise AssertionError("unreachable")  # pragma: no cover
