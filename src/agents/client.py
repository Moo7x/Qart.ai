"""Tool-calling chat for the agents, on AGENT_MODEL, with every call counted in the usage table.

Both this and the JSON-schema calls of extraction and explanations go through `src/llm.py`
`create` (time budget, no retries, usage row); agents add `tools` so the model can choose
tools across several turns. The model only chooses tools and writes short reasons; code runs
the tools and checks every answer.
"""

import json
from collections.abc import Callable
from typing import Any

from src import llm
from src.config import Settings

# A chat turn: messages and tool definitions in, the assistant message out (as a plain dict).
Chat = Callable[[list[dict[str, Any]], list[dict[str, Any]]], dict[str, Any]]


def openai_chat(settings: Settings, purpose: str, timeout: float) -> Chat:
    def chat(messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        request = {"messages": messages, "tools": tools, "tool_choice": "auto", "temperature": 0}
        response = llm.create(
            settings, model=settings.agent_model, purpose=purpose, timeout=timeout, request=request
        )
        message = response.choices[0].message
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
