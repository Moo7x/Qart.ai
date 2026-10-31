"""Tool-calling chat for the agents, on AGENT_MODEL, with every call counted in the usage table.

The JSON-schema calls of extraction and explanations go through src/llm.py; agents need the
model to choose tools across several turns, so they call the chat API with `tools` here. The
model only chooses tools and writes short reasons; code runs the tools and checks every answer.
"""

import json
import time
from collections.abc import Callable
from typing import Any

from src import usage
from src.config import Settings

# A chat turn: messages and tool definitions in, the assistant message out (as a plain dict).
Chat = Callable[[list[dict[str, Any]], list[dict[str, Any]]], dict[str, Any]]


def openai_chat(settings: Settings, purpose: str, timeout: float) -> Chat:
    def chat(messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
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
            request: dict[str, Any] = {
                "model": settings.agent_model,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "temperature": 0,
            }
            response = client.chat.completions.create(**request)
            if response.usage is not None:
                tokens_in, tokens_out = (
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                )
            message = response.choices[0].message
            ok = True
            return {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in (message.tool_calls or [])
                ],
            }
        finally:
            usage.record(
                purpose,
                "openai",
                settings.agent_model,
                time.monotonic() - started,
                ok,
                tokens_in,
                tokens_out,
            )

    return chat


def tool(
    name: str, description: str, properties: dict[str, Any], required: list[str]
) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


def arguments(call: dict[str, Any]) -> dict[str, Any]:
    """A tool call's arguments; malformed JSON becomes an empty dict (the tool then refuses it)."""
    try:
        parsed = json.loads(call["function"]["arguments"] or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
