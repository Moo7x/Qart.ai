"""The resource scout: the exact part of a checked video or article that serves one skill.

    .venv/Scripts/python.exe -m src.agents.scout --cache [SKILL ...]   # pre-check the parts

One agent (AGENT_MODEL, character in data/agents/scout.character.yaml) with code tools:
* list_resources – the checked videos and articles the pack links to this skill;
* read_video     – captions cut into 30–90 s segments, ranked for the skill on RunPod;
* read_article   – the page text cut into passages, ranked the same way;
* finish         – up to three parts with a one-line reason each.
The agent only chooses what to read and writes the reasons. Code fetches, cuts and ranks, keeps
only parts a tool really returned, drops a reason that contains a number, and builds the link:
a YouTube link at the segment's start second, or an article link that opens at the passage
(#:~:text=). It finds and points; it never teaches. With no language model, or when the agent
fails, the best-ranked part of each resource is shown, labelled "ranking only".

YouTube often refuses caption requests from cloud servers, so the parts are pre-checked from a
normal connection (`--cache`) and stored as times, link anchors and reasons only (no caption or
article text) in data/agents/scout_cache.yaml; a live run that is refused uses them, labelled
with the date they were checked. Every step is written to the run as it happens for the window.
"""

import json
import re
import sys
import time
from datetime import UTC, datetime
from typing import Any

import httpx
import yaml
from sqlalchemy import Engine

from src import params
from src.agents import store
from src.agents.character import AGENTS_DIR, load_character
from src.agents.client import Chat, arguments, openai_chat, tool
from src.agents.segments import (
    Part,
    anchor_words,
    article_parts,
    article_text,
    caption_snippets,
    rank,
    video_id,
    video_parts,
)
from src.config import Settings
from src.http import client as http_client
from src.pack import load_pack
from src.resources import load_resources

CACHE = AGENTS_DIR / "scout_cache.yaml"
DIGIT = re.compile(r"\d")
EXCERPT_CHARS = 600  # of a part's text sent to the model; never stored

TOOLS = [
    tool("list_resources", "List the checked videos and articles for the skill.", {}, []),
    tool(
        "read_video",
        "Read a video's captions and get its best segments for the skill.",
        {"resource_id": {"type": "string"}},
        ["resource_id"],
    ),
    tool(
        "read_article",
        "Read an article and get its best passages for the skill.",
        {"resource_id": {"type": "string"}},
        ["resource_id"],
    ),
    tool(
        "finish",
        "Return up to three parts that best serve the skill, each with a one-line reason.",
        {
            "picks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"part_id": {"type": "string"}, "reason": {"type": "string"}},
                    "required": ["part_id", "reason"],
                    "additionalProperties": False,
                },
            }
        },
        ["picks"],
    ),
]


def load_cache() -> dict[str, Any]:
    if not CACHE.exists():
        return {"checked": None, "skills": {}}
    data: dict[str, Any] = yaml.safe_load(CACHE.read_text(encoding="utf-8")) or {}
    return {"checked": data.get("checked"), "skills": data.get("skills") or {}}


class Scout:
    """One run: the tools, the parts they returned, and the steps written for the window."""

    def __init__(
        self,
        engine: Engine,
        settings: Settings,
        run_id: str,
        skill: str,
        http: httpx.Client,
        captions: Any = caption_snippets,
        resource_id: str | None = None,
    ) -> None:
        pack, res = load_pack(), load_resources()
        self.engine, self.settings, self.run_id, self.http = engine, settings, run_id, http
        self.skill, self.skill_name = skill, pack.skills[skill].name
        self.captions = captions
        self.resources = {v.id: ("video", v.title, v.url) for v in res.videos_for(skill=skill)}
        self.resources |= {a.id: ("article", a.title, a.url) for a in res.articles_for(skill=skill)}
        if resource_id in self.resources:  # the person asked about one video or article
            self.resources = {resource_id: self.resources[resource_id]}
        self.parts: dict[str, Part] = {}
        self.rank_engine = "none"
        self.cache = load_cache()
        self.cached_used = False

    def step(self, kind: str, text: str) -> None:
        store.step(self.engine, self.run_id, kind, text)

    def list_resources(self) -> list[dict[str, str]]:
        self.step(
            "tool",
            f"Listed {len(self.resources)} checked videos and articles for {self.skill_name}",
        )
        return [
            {"resource_id": r, "kind": k, "title": t} for r, (k, t, _) in self.resources.items()
        ]

    def _from_cache(self, resource_id: str) -> list[Part]:
        rows = [
            p for p in self.cache["skills"].get(self.skill, []) if p["resource_id"] == resource_id
        ]
        self.cached_used = self.cached_used or bool(rows)
        return [
            Part(
                f"{resource_id}#c{i}",
                resource_id,
                p["kind"],
                p.get("anchor", ""),
                p.get("start"),
                p.get("end"),
                1.0,
            )
            for i, p in enumerate(rows)
        ]

    def read(self, resource_id: str, kind: str) -> list[dict[str, Any]]:
        if self.resources.get(resource_id, ("",))[0] != kind:
            self.step("error", f"Refused: {resource_id} is not a checked {kind} for this skill")
            return []
        _, title, url = self.resources[resource_id]
        try:
            if kind == "video":
                vid = video_id(url)
                if vid is None:
                    raise ValueError("not a YouTube link")
                self.step("tool", f"Reading the captions of “{title}”")
                parts = video_parts(resource_id, self.captions(vid))
            else:
                self.step("tool", f"Reading the article “{title}”")
                parts = article_parts(resource_id, article_text(url, self.http))
        except Exception as exc:  # noqa: BLE001  refused captions, page down: say so, use the cache
            cached = self._from_cache(resource_id)
            note = f"the source did not answer ({type(exc).__name__})"
            if cached:
                self.step("note", f"{note}; using the parts checked on {self.cache['checked']}")
                self._keep(cached)
                return [
                    {"part_id": p.part_id, "start": p.start, "text": "(checked earlier)"}
                    for p in cached
                ]
            self.step("note", f"{note}; nothing to show for “{title}”")
            return []
        best, self.rank_engine = rank(self.settings, self.skill_name, parts, self.http)
        self.step(
            "result", f"Cut it into {len(parts)} parts and ranked them with {self.rank_engine}"
        )
        self._keep(best)
        return [
            {
                "part_id": p.part_id,
                "start": p.start,
                "score": p.score,
                "text": p.text[:EXCERPT_CHARS],
            }
            for p in best
        ]

    def _keep(self, parts: list[Part]) -> None:
        self.parts.update({p.part_id: p for p in parts})

    def picks(self, chosen: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Only parts a tool returned; a reason with a number is dropped (code writes numbers)."""
        out = []
        for pick in chosen[: params.SCOUT_TOP_SEGMENTS]:
            part = self.parts.get(str(pick.get("part_id", "")))
            if part is None:
                continue
            reason = str(pick.get("reason", "")).strip()
            out.append(self.result(part, "" if DIGIT.search(reason) else reason))
        return out

    def result(self, part: Part, reason: str) -> dict[str, Any]:
        kind, title, url = self.resources[part.resource_id]
        cached = part.part_id.split("#")[1].startswith("c")
        if cached and not reason:
            reason = next(
                (
                    p.get("reason", "")
                    for p in self.cache["skills"].get(self.skill, [])
                    if p["resource_id"] == part.resource_id and p.get("start") == part.start
                ),
                "",
            )
        return {
            "resource_id": part.resource_id,
            "kind": kind,
            "title": title,
            "url": part.link(url) if part.text or part.start is not None else url,
            "start": part.start,
            "end": part.end,
            "anchor": " ".join(anchor_words(part.text)) if kind == "article" else "",
            "score": part.score,
            "reason": reason,
            "source": f"checked on {self.cache['checked']}" if cached else "live",
        }

    def ranked_only(self) -> list[dict[str, Any]]:
        """Fallback: read the first resources and keep the best part of each."""
        for resource_id, (kind, _, _) in list(self.resources.items())[: params.SCOUT_MAX_RESOURCES]:
            self.read(resource_id, kind)
        best: dict[str, Part] = {}
        for part in self.parts.values():
            if part.resource_id not in best or part.score > best[part.resource_id].score:
                best[part.resource_id] = part
        return [self.result(p, "") for p in sorted(best.values(), key=lambda p: -p.score)]


def _agent(scout: Scout, chat: Chat) -> list[dict[str, Any]] | None:
    """The tool loop; None when the agent ends without valid picks."""
    character = load_character("scout")
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": character.system_prompt()},
        {
            "role": "user",
            "content": (
                f"Skill: {scout.skill_name}. List the resources, read up to "
                f"{params.SCOUT_MAX_RESOURCES} of the most promising, then call finish with up to "
                f"{params.SCOUT_TOP_SEGMENTS} parts that best serve this skill."
            ),
        },
    ]
    started = time.monotonic()
    for _ in range(params.AGENT_MAX_STEPS):
        if time.monotonic() - started > params.AGENT_TIME_BUDGET_SECONDS:
            scout.step("note", "Time budget reached; stopping the agent")
            return None
        reply = chat(messages, TOOLS)
        messages.append(reply)
        if not reply["tool_calls"]:
            scout.step("note", "The agent answered without choosing parts")
            return None
        for call in reply["tool_calls"]:
            name, args = call["function"]["name"], arguments(call)
            if name == "finish":
                chosen = args.get("picks", [])
                picks = scout.picks(chosen)
                if not picks:
                    scout.step(
                        "note",
                        f"The agent chose {len(chosen)} part(s), none of them returned by a tool",
                    )
                return picks or None
            if name == "list_resources":
                out: Any = scout.list_resources()
            elif name in ("read_video", "read_article"):
                out = scout.read(str(args.get("resource_id", "")), name.removeprefix("read_"))
            else:
                out = {"error": "unknown tool"}
            messages.append(
                {"role": "tool", "tool_call_id": call["id"], "content": json.dumps(out)}
            )
    scout.step("note", "Step limit reached; stopping the agent")
    return None


def run_scout(
    engine: Engine,
    settings: Settings,
    run_id: str,
    skill: str,
    http: httpx.Client | None = None,
    chat: Chat | None = None,
    captions: Any = caption_snippets,
    resource_id: str | None = None,
) -> dict[str, Any]:
    own = http is None
    client = http or http_client("resource scout", 20, follow_redirects=True)
    scout = Scout(engine, settings, run_id, skill, client, captions, resource_id)
    scout.step("think", f"Looking for the parts that serve {scout.skill_name}")
    agent_engine = "ranking only (no language model)"
    picks: list[dict[str, Any]] | None = None
    try:
        model = chat or (
            openai_chat(settings, "scout_agent", 20.0) if settings.llm_configured else None
        )
        if model is not None:
            agent_engine = f"{settings.agent_model} agent"
            try:
                picks = _agent(scout, model)
            except Exception as exc:  # noqa: BLE001  model down: the ranking alone still answers
                scout.step(
                    "note", f"The agent stopped ({type(exc).__name__}); showing the ranking only"
                )
            if picks is None:
                agent_engine = f"ranking only ({settings.agent_model} gave no valid picks)"
        if picks is None:
            picks = scout.ranked_only()
        result = {
            "skill": skill,
            "skill_name": scout.skill_name,
            "picks": picks,
            "engine": f"{agent_engine}; ranked by {scout.rank_engine}",
            "note": "Some parts come from an earlier check." if scout.cached_used else "",
        }
        scout.step("result", f"Done: {len(picks)} part(s) to open")
        store.finish(engine, run_id, "done", str(result["engine"]), result)
        return result
    except Exception as exc:  # noqa: BLE001  the window must always end, with the reason
        scout.step("error", f"The scout failed ({type(exc).__name__})")
        store.finish(
            engine,
            run_id,
            "failed",
            agent_engine,
            {"skill": skill, "picks": [], "note": str(exc)[:200]},
        )
        raise
    finally:
        if own:
            client.close()


def build_cache(settings: Settings, skills: list[str]) -> dict[str, Any]:
    """Run the scout for each skill on a scratch database and keep times, anchors and reasons."""
    from src.db import init_db, make_engine

    engine = make_engine("sqlite://")
    init_db(engine)
    out: dict[str, list[dict[str, Any]]] = {}
    for skill in skills:
        run_id = store.start(engine, "scout", skill, None, "cache")
        result = run_scout(engine, settings, run_id, skill)
        out[skill] = [
            {k: p[k] for k in ("resource_id", "kind", "start", "end", "anchor", "reason")}
            for p in result["picks"]
            if p["source"] == "live"
        ]
        print(f"{skill}: {len(out[skill])} part(s)")
    return {"checked": f"{datetime.now(UTC):%Y-%m-%d}", "skills": out}


def main() -> None:
    from src.config import load_settings
    from src.envfile import load_env_file

    load_env_file()
    if "--cache" not in sys.argv:
        raise SystemExit("usage: python -m src.agents.scout --cache [SKILL ...]")
    res = load_resources()
    skills = [a for a in sys.argv[1:] if a != "--cache"] or sorted(
        {s for v in res.videos for s in v.skills} | {s for a in res.articles for s in a.skills}
    )
    data = build_cache(load_settings(), skills)
    header = (
        "# Pre-checked scout parts: times, link anchors and reasons only (no caption or article"
        " text).\n"
    )
    CACHE.write_text(
        header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
