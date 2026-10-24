"""Plain-language explanation of one computed role result (OpenAI gpt-4o-mini, never numbers).

Code first turns the computed match and pathway into numbered facts (with their numbers). The
model may only rephrase those facts: it returns a few sentences, each citing the fact ids it
uses, under a strict JSON schema. Code then drops any sentence that contains a number (digits or
words), a forecast or promise word, cites no fact or cites an unknown one, so a number on screen
always comes from code, shown next to the sentence through its cited facts. With no key, a
failure or nothing left after the check, the explanation is a labelled template of the facts.

Market evidence (the outlook) is not given to the model: in testing, gpt-4o-mini turned an
observed employment share into "expected to rise significantly". The outlook is shown in its own
words, with its sources, next to the explanation.
"""

import json
import re
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from src.config import Settings
from src.match.engine import RoleMatch
from src.pathway.planner import Pathway
from src.stages import Stages

LLM_TIME_BUDGET_SECONDS = 15.0
MAX_SENTENCES = 5
MAX_SENTENCE_CHARS = 320
CACHE_SIZE = 256  # explanations kept in memory, so the same request is not paid for twice
DIGIT = re.compile(r"\d")
# Numbers written as words count as numbers too ("forty-three out of one hundred").
NUMBER_WORD = re.compile(
    r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|"
    r"fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|"
    r"seventy|eighty|ninety|hundred|thousand|percent|per cent|half|quarter|dozen)\b",
    re.I,
)
# Sentences that forecast or promise are dropped: the facts are observations and estimates only.
FORECAST_WORD = re.compile(
    r"\b(will|expected|expect|forecast|predict\w*|guarantee\w*|promising|definitely|"
    r"certainly|surely|bright|secure)\b",
    re.I,
)

Complete = Callable[[list[dict[str, str]], dict[str, Any]], str]
_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()


def facts(match: RoleMatch, path: Pathway, scenario_label: str) -> list[dict[str, str]]:
    """Computed results as short sentences with ids; the only material the model may use."""
    out = [
        {
            "id": "fit",
            "text": f"Fit for {match.title} is {match.fit:.0f} of 100 under {scenario_label}.",
        }
    ]
    for i, req in enumerate(match.requirements, 1):
        # Levels are stored 0-4 and shown to people on the 1-5 scale the screens use.
        claimed = "not stated" if req.claimed is None else f"{req.claimed + 1} of 5"
        out.append(
            {
                "id": f"skill{i}",
                "text": (
                    f"{req.skill_name}{' (essential)' if req.essential else ''}: you {claimed}, "
                    f"the role needs {req.required + 1} of 5; it adds {req.contribution:.1f} fit "
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
                "role scores as it does, which skills help most, what the biggest gaps are and "
                "what the planned pathway covers. Use only the facts given. Never write a "
                "number, neither in digits nor in words (no 'forty', 'one', 'half', "
                "'percent'): the screen shows the numbers next to your sentences, so say "
                "'your strongest skill', 'a large gap', 'a few courses' instead. Name skills "
                "by name. Put the ids of the facts a sentence uses only in its 'facts' list, "
                "never in the text. Do not forecast or promise anything. AI-use figures "
                "describe how people use an AI chat assistant on these tasks, not how much of "
                "the work is automated. Do not invent skills, courses, jobs or causes; do not "
                "say a job will disappear; do not tell the person what to decide."
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
        # An id the model echoed into the text, e.g. "(fit)", is removed rather than shown.
        text = re.sub(r"\s*\((?:" + "|".join(map(re.escape, by_id)) + r")(?:,\s*\w+)*\)", "", text)
        banned = DIGIT.search(text) or NUMBER_WORD.search(text) or FORECAST_WORD.search(text)
        if not text or len(text) > MAX_SENTENCE_CHARS or banned or not cited:
            dropped += 1
            continue
        kept.append({"text": text, "facts": [{"id": f, "text": by_id[f]} for f in cited]})
    return kept, dropped


def _template(fact_list: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Fallback: the most telling facts themselves, as written by code."""
    by_id = {f["id"]: f["text"] for f in fact_list}
    chosen = ["fit", "essentials", "pathway"]
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
    stages = Stages()
    if settings.llm_configured or complete is not None:
        try:
            with stages.step("Write sentences from the computed facts", settings.llm_model):
                raw = (complete or openai_complete(settings))(
                    messages(fact_list), schema(list(by_id))
                )
            sentences, dropped = _validate(json.loads(raw), by_id)
            if sentences:
                result = {
                    "sentences": sentences,
                    "engine": f"{settings.llm_model} (schema-constrained)",
                    "note": (
                        f"{dropped} sentence(s) removed by the no-numbers, no-forecast and "
                        "cited-fact checks"
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
    result["stages"] = stages.items
    # Only real model answers are cached: a fallback is retried next time, and tests that pass
    # their own `complete` never share state.
    if complete is None and result["engine"] != "template (fallback)":
        _cache[key] = result
        if len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return result
