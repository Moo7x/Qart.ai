"""The one place the app calls the language model (OpenAI chat completions, JSON-schema output).

Every caller gets the same behaviour: a strict JSON schema, a time budget, no retries (the caller
has a labelled fallback), and one usage row per call (src/usage.py) for the cost figures. The
model is `settings.llm_model` (gpt-4.1-mini) unless a caller names another, as agents do with
`settings.agent_model`.
"""

import time
from collections.abc import Callable
from typing import Any

from src import usage
from src.config import Settings

Complete = Callable[[list[dict[str, str]], dict[str, Any]], str]


def create(
    settings: Settings, *, model: str, purpose: str, timeout: float, request: dict[str, Any]
) -> Any:
    """One chat-completions call: a time budget, no retries, and one usage row (ok or not).

    Returns the SDK response. `request` holds everything but the model (messages, and either
    `response_format` or `tools`). Plain dicts are what the API takes; the SDK's TypedDicts add
    nothing checkable here.
    """
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=timeout,
        max_retries=0,
    )
    started = time.monotonic()
    ok, tokens_in, tokens_out = False, None, None
    try:
        response = client.chat.completions.create(model=model, **request)
        if response.usage is not None:
            tokens_in = response.usage.prompt_tokens
            tokens_out = response.usage.completion_tokens
        ok = True
        return response
    finally:
        usage.record(
            purpose, "openai", model, time.monotonic() - started, ok, tokens_in, tokens_out
        )


def openai_complete(
    settings: Settings,
    *,
    schema_name: str,
    purpose: str,
    timeout: float,
    temperature: float = 0.0,
    model: str | None = None,
) -> Complete:
    """A `complete(messages, json_schema) -> raw JSON text` function for one kind of call.

    Args:
        schema_name: the name the API shows for the response schema.
        purpose: the usage counter's label, e.g. "cv_extraction".
        timeout: seconds before the call gives up (the caller's time budget).
        temperature: sampling temperature; 0 for reading tasks.
        model: overrides `settings.llm_model`.
    """
    model_name = model or settings.llm_model

    def complete(msgs: list[dict[str, str]], json_schema: dict[str, Any]) -> str:
        request = {
            "messages": msgs,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": json_schema},
            },
            "temperature": temperature,
        }
        response = create(
            settings, model=model_name, purpose=purpose, timeout=timeout, request=request
        )
        return response.choices[0].message.content or ""

    return complete
