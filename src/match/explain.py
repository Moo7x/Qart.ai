"""Plain-language explanation of one computed role result (OpenAI gpt-4o-mini, never numbers).

Code first turns the computed match, pathway and outlook into numbered facts (with their numbers).
The model may only rephrase those facts: it returns a few sentences, each citing the fact ids it
uses, under a strict JSON schema. Code then drops any sentence that contains a digit, cites no
fact or cites an unknown one, so a number on screen always comes from code, shown next to the
sentence through its cited facts. With no key, a failure or nothing left after the check, the
explanation is a labelled template built from the same facts.
"""

import json
import re
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from src.config import Settings
from src.match.engine import RoleMatch
from src.pathway.planner import Pathway

LLM_TIME_BUDGET_SECONDS = 15.0
MAX_SENTENCES = 5
MAX_SENTENCE_CHARS = 320
CACHE_SIZE = 256  # explanations kept in memory, so the same request is not paid for twice
DIGIT = re.compile(r"\d")

Complete = Callable[[list[dict[str, str]], dict[str, Any]], str]
_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()


def facts(
    match: RoleMatch, path: Pathway, outlook: list[dict[str, str]], scenario_label: str
) -> list[dict[str, str]]:
    """Computed results as short sentences with ids; the only material the model may use."""
    out = [
        {
            "id": "fit",
            "text": f"Fit for {match.title} is {match.fit:.0f} of 100 under {scenario_label}.",
        }
    ]
    for i, req in enumerate(match.requirements, 1):
        claimed = "not stated" if req.claimed is None else f"level {req.claimed}"
        out.append(
            {
                "id": f"skill{i}",
                "text": (
                    f"{req.skill_name}{' (essential)' if req.essential else ''}: you {claimed}, "
                    f"the role needs level {req.required}; it adds {req.contribution:.1f} fit "
                    f"points. {req.shift_reason}"
                ),
            }
        )
    if match.essential_gaps:
        out.append(
            {
                "id": "essentials",
                "text": "Essential skills still below the needed level: "
                + ", ".join(match.essential_gaps)
                + ". This makes it a longer route.",
            }
        )
    out.append(
        {
            "id": "pathway",
            "text": (
                f"The planned pathway has {len(path.steps)} free courses, {path.total_hours} hours "
                f"over about {path.weeks} weeks; projected fit afterwards {path.fit_after:.0f} "
                "(estimate from declared course rules)."
                + (
                    f" No verified course yet for: {', '.join(path.uncovered)}."
                    if path.uncovered
                    else ""
                )
            ),
        }
    )
    for i, item in enumerate(outlook, 1):
        out.append({"id": f"outlook{i}", "text": f"{item['text']} ({item['source']})"})
    return out


def schema(ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["sentences"],
        "properties": {
            "sentences": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["text", "facts"],
                    "properties": {
                        "text": {"type": "string"},
                        "facts": {"type": "array", "items": {"type": "string", "enum": ids}},
                    },
                },
            }
        },
    }


def messages(fact_list: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You explain a computed career-match result to the person it belongs to, in "
                f"plain, friendly English, in at most {MAX_SENTENCES} short sentences: why the "
                "role scores as it does, what the biggest gaps are, and what the evidence says "
                "about the role. Use only the facts given. Never write a digit or a number "
                "(the screen shows the numbers next to your sentences). Cite the ids of the "
                "facts each sentence uses. Do not invent skills, courses, jobs or causes; do "
                "not say a job will disappear; do not tell the person what to decide."
            ),
        },
        {"role": "user", "content": json.dumps(fact_list, ensure_ascii=False)},
    ]


def openai_complete(settings: Settings) -> Complete:
    def complete(msgs: list[dict[str, str]], json_schema: dict[str, Any]) -> str:
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=LLM_TIME_BUDGET_SECONDS,
            max_retries=0,
        )
        request: dict[str, Any] = {
            "model": settings.llm_model,
            "messages": msgs,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "role_explanation", "strict": True, "schema": json_schema},
            },
            "temperature": 0.2,
        }
        response = client.chat.completions.create(**request)
        return response.choices[0].message.content or ""

    return complete


def _validate(answer: dict[str, Any], by_id: dict[str, str]) -> tuple[list[dict[str, Any]], int]:
    kept, dropped = [], 0
    for item in answer.get("sentences", [])[:MAX_SENTENCES]:
        text = str(item.get("text", "")).strip()
        cited = [f for f in item.get("facts", []) if f in by_id]
        if not text or len(text) > MAX_SENTENCE_CHARS or DIGIT.search(text) or not cited:
            dropped += 1
            continue
        kept.append({"text": text, "facts": [{"id": f, "text": by_id[f]} for f in cited]})
    return kept, dropped


def _template(fact_list: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Fallback: the most telling facts themselves, as written by code."""
    by_id = {f["id"]: f["text"] for f in fact_list}
    chosen = ["fit", "essentials", "pathway", "outlook1"]
    return [
        {"text": by_id[i], "facts": [{"id": i, "text": by_id[i]}]} for i in chosen if i in by_id
    ]


def explain(
    fact_list: list[dict[str, str]], settings: Settings, complete: Complete | None = None
) -> dict[str, Any]:
    key = json.dumps([settings.llm_model, fact_list], sort_keys=True)
    if complete is None and key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    by_id = {f["id"]: f["text"] for f in fact_list}
    result: dict[str, Any]
    if settings.llm_configured or complete is not None:
        try:
            raw = (complete or openai_complete(settings))(messages(fact_list), schema(list(by_id)))
            sentences, dropped = _validate(json.loads(raw), by_id)
            if sentences:
                result = {
                    "sentences": sentences,
                    "engine": f"{settings.llm_model} (schema-constrained)",
                    "note": (
                        f"{dropped} sentence(s) removed by the no-numbers / cited-fact check"
                        if dropped
                        else ""
                    ),
                }
            else:
                result = {
                    "sentences": _template(fact_list),
                    "engine": "template (fallback)",
                    "note": "no model sentence passed the checks; computed facts shown instead",
                }
        except Exception as exc:  # noqa: BLE001  any model or parsing failure → labelled fallback
            result = {
                "sentences": _template(fact_list),
                "engine": "template (fallback)",
                "note": f"model unavailable ({type(exc).__name__}); computed facts shown instead",
            }
    else:
        result = {
            "sentences": _template(fact_list),
            "engine": "template (fallback)",
            "note": "no language model configured; computed facts shown instead",
        }
    # Only real model answers are cached: a fallback is retried next time, and tests that pass
    # their own `complete` never share state.
    if complete is None and result["engine"] != "template (fallback)":
        _cache[key] = result
        if len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return result
