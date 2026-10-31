"""The one way the app builds an HTTP client: it names itself and always has a time budget.

Every outbound request (collectors, link and course checks, the resource scout, RunPod calls)
sends a User-Agent naming Qart.ai and what the request is for, so the sites we read can tell who
is asking. Callers that may receive a client (tests pass one with a mock transport) build one
here only when none is given.
"""

import httpx

USER_AGENT = "Qart.ai {purpose} (SDC Hackathon 2026; public data)"
DEFAULT_TIMEOUT_SECONDS = 5.0  # httpx's own default, kept for callers that never set one


def client(
    purpose: str,
    timeout: float | httpx.Timeout = DEFAULT_TIMEOUT_SECONDS,
    *,
    follow_redirects: bool = False,
) -> httpx.Client:
    """An HTTP client for one purpose, e.g. "evidence pipeline" or "link check"."""
    return httpx.Client(
        timeout=timeout,
        follow_redirects=follow_redirects,
        headers={"User-Agent": USER_AGENT.format(purpose=purpose)},
    )
