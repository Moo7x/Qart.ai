"""AI-for-this-skill resources: courses and videos that teach doing one skill's work *with AI*.

    .venv/Scripts/python.exe -m src.collectors.ai_resources [SKILL ...]   # ai_resources.yaml

A plan step "do it faster with AI" or "check and steer AI-run work" needs resources about the AI
version of the work, not the skill on its own. Five stages, each measured:

1. **Targets from evidence.** For each skill, the O*NET tasks linked to it in the followed
   occupations, ordered by automation-style AI use (observed in the Economic Index, else predicted
   by the task model). Two queries: the skill query (skill name + its top tasks) and the AI query
   ("using AI, Copilot or automation to" + the same tasks).
2. **Broad candidates.** Every Microsoft Learn module or path about AI, Copilot or automation
   (Catalog API), and YouTube videos found with "<skill> with AI" on trusted channels.
3. **Two relevance scores.** BGE-M3 (RunPod) shortlists AI_SHORTLIST candidates per skill;
   bge-reranker-v2-m3 scores each against both queries. A resource must serve both, so the
   ranking key is the lower of the two scores: a generic intro to the skill scores high on the
   skill query and low on the AI query, and drops.
4. **Quote-checked judgement.** For the AI_JUDGED best candidates, LLM_MODEL reads the page or the
   captions and must quote one sentence showing the skill's work and one showing AI or automation
   used on it; both quotes must be found word for word. Only then is the resource kept. These
   judgements are model labels (recorded as such), awaiting a human check.
5. **Learned ranker.** A logistic regression on the stage-3 features (both scores, provider trust,
   recency, length) is fitted to the labels with cross-validation; its precision at 3 is reported
   against the source's own order, dense similarity only, and the lower reranker score, so the
   ranking is chosen by measurement. Kept resources are ordered by the fitted probability.

Only metadata and the two checked quotes are stored (no page or caption text).
"""

import json
import math
import os
import re
import sys
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

import httpx
import numpy as np
import yaml

from src import http, llm, params
from src.agents.segments import caption_snippets
from src.collectors import mslearn, youtube
from src.collectors.course_check import quote_found, read_page
from src.config import REPO_ROOT, Settings, load_settings
from src.envfile import load_env_file
from src.evidence.field import PACK_DIR
from src.forecast import task_model
from src.pack import load_pack
from src.runpod_jobs import BACKGROUND_BUDGET_SECONDS, embed, rerank

OUT = PACK_DIR / "ai_resources.yaml"
PROGRESS = REPO_ROOT / "data" / "cache" / "ai_resources_progress.jsonl"  # gitignored
AI_TERMS = (
    "copilot",
    " ai ",
    "ai-",
    "artificial intelligence",
    "automat",
    "machine learning",
    "agent",
    "ai builder",
    "generative",
)
SYSTEM = (
    "You check whether a learning resource teaches doing one finance skill's work WITH AI or "
    "automation. Use only the text you are given. Answer two questions. teaches_skill: does it "
    "cover the skill's work (the tasks listed)? applies_ai: does it show AI, Copilot or "
    "automation being used for that work (not AI in general)? For each 'yes', copy one sentence "
    "from the text, word for word, that shows it; if you cannot, answer 'no'. Never use outside "
    "knowledge."
)
SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["teaches_skill", "skill_quote", "applies_ai", "ai_quote"],
    "properties": {
        "teaches_skill": {"type": "string", "enum": ["yes", "no"]},
        "skill_quote": {"type": "string"},
        "applies_ai": {"type": "string", "enum": ["yes", "no"]},
        "ai_quote": {"type": "string"},
    },
}
AI_WORDS = re.compile(
    r"\b(ai|copilot|automat\w*|agents?|agentic|machine learning|bots?|rpa|"
    r"artificial intelligence|generative|gpt|llm|intelligent)\b",
    re.I,
)
FINANCE_SOC_PREFIXES = ("13-", "43-", "11-3031")
FEATURES = ("skill_score", "ai_score", "trusted", "recent", "log_minutes")


def targets(task_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per skill: its most AI-used linked tasks and the two queries built from them."""
    pack = load_pack()
    use = {
        (r["soc"], r["task"]): (r["observed"] if r["observed"] is not None else r["predicted"])
        for r in task_rows
    }
    from src.levels import load_levels

    levels = load_levels().skills
    out = {}
    for skill in pack.skills.values():
        tasks: dict[str, tuple[int, float]] = {}
        for soc, occupation in pack.tasks.occupations.items():
            # Finance and clerical occupations first: the person doing this work in a GBS finance
            # team, not the IT staff who build the system (declared order).
            finance = 0 if soc.startswith(FINANCE_SOC_PREFIXES) else 1
            for link in occupation.skills.get(skill.id, []):
                value = use.get((soc, str(link.task))) or 0.0
                best = tasks.get(link.text, (9, 0.0))
                tasks[link.text] = min(best, (finance, -value))
        ordered = sorted(tasks.items(), key=lambda kv: kv[1])
        top = [t for t, _ in ordered][: params.AI_TARGET_TASKS]
        meaning = levels[skill.id].anchors[2] if skill.id in levels else ""
        work = "; ".join(top) if top else meaning or skill.name
        out[skill.id] = {
            "name": skill.name,
            "tasks": top,
            "skill_query": f"{skill.name} in finance and accounting work. {meaning} {work}",
            "ai_query": (
                f"How finance and accounting staff use AI, Copilot or automation for "
                f"{skill.name.lower()}: {work}"
            ),
        }
    return out


def mslearn_pool(client: httpx.Client) -> list[dict[str, Any]]:
    """Microsoft Learn modules and paths about AI, Copilot or automation."""
    catalog = mslearn.fetch(client)
    pool = []
    for item in [*catalog.get("modules", []), *catalog.get("learningPaths", [])]:
        text = f" {item.get('title', '')} {item.get('summary', '')} ".lower()
        url = mslearn.TRACKING.sub("", item.get("url", ""))
        if not url.startswith("https://") or not any(term in text for term in AI_TERMS):
            continue
        pool.append(
            {
                "kind": "course",
                "id": item["uid"],
                "title": item["title"].strip(),
                "provider": "Microsoft Learn",
                "url": url,
                "minutes": int(item.get("duration_in_minutes") or 0),
                "published": str(item.get("last_modified", ""))[:10],
                "text": f"{item['title']}. {item.get('summary') or ''}",
                "trusted": 1.0,
            }
        )
    return [p for p in pool if p["minutes"] > 0]


def youtube_pool(client: httpx.Client, key: str, name: str) -> list[dict[str, Any]]:
    """Videos found with "<skill> with AI": a trusted channel, or a channel and video with real
    reach (AI_MIN_SUBSCRIBERS, AI_MIN_VIEWS; declared), of a teaching length."""
    try:
        ids = youtube.search(client, key, f"{name} with AI")
        if not ids:
            return []
        videos = client.get(
            f"{youtube.API}/videos",
            params={"part": "snippet,contentDetails,statistics", "id": ",".join(ids), "key": key},
        )
        videos.raise_for_status()
        items = videos.json().get("items", [])
        channel_ids = sorted({v["snippet"]["channelId"] for v in items})
        channels = client.get(
            f"{youtube.API}/channels",
            params={"part": "statistics", "id": ",".join(channel_ids), "key": key},
        )
        channels.raise_for_status()
    except httpx.HTTPStatusError:
        return []  # quota spent or the API refused: the courses still answer
    subscribers = {
        c["id"]: int(c["statistics"].get("subscriberCount", 0) or 0)
        for c in channels.json().get("items", [])
    }
    out = []
    for v in items:
        snip, stats = v["snippet"], v.get("statistics", {})
        minutes = youtube.minutes(v["contentDetails"]["duration"])
        trusted = snip["channelTitle"] in youtube.TRUSTED_CHANNELS
        reach = (
            subscribers.get(snip["channelId"], 0) >= params.AI_MIN_SUBSCRIBERS
            and int(stats.get("viewCount", 0) or 0) >= params.AI_MIN_VIEWS
        )
        if not (trusted or reach) or not (
            params.YOUTUBE_MIN_MINUTES <= minutes <= params.YOUTUBE_MAX_MINUTES
        ):
            continue
        out.append(
            {
                "kind": "video",
                "id": f"yt_ai_{v['id']}",
                "title": snip["title"],
                "provider": snip["channelTitle"],
                "url": f"https://www.youtube.com/watch?v={v['id']}",
                "minutes": minutes,
                "published": snip["publishedAt"][:10],
                "video": v["id"],
                "text": f"{snip['title']}. {snip.get('description', '')[:600]}",
                "trusted": 1.0 if trusted else 0.5,
            }
        )
    return out


def features(c: dict[str, Any], today: datetime) -> list[float]:
    try:
        age = (today - datetime.fromisoformat(c["published"]).replace(tzinfo=UTC)).days / 365
    except ValueError:
        age = 3.0
    return [
        c["skill_score"],
        c["ai_score"],
        c["trusted"],
        1.0 if age <= params.AI_RECENT_YEARS else 0.0,
        math.log1p(c["minutes"]),
    ]


_POOL = ThreadPoolExecutor(max_workers=4)


def _within(fn: Callable[[], str], seconds: float) -> str:
    """The text `fn` returns, or "" if it takes longer than `seconds` (a slow page or a caption
    request that hangs must not stall the whole job)."""
    try:
        return _POOL.submit(fn).result(timeout=seconds)
    except Exception:  # noqa: BLE001  timeout or fetch error: treated as no text
        return ""


STOP_WORDS = {"and", "with", "the", "for", "of", "in", "to"}


def skill_stems(name: str) -> list[str]:
    """The first five letters of each word of the skill's name (reconcil-, invoi-, cash)."""
    words = re.findall(r"[a-z]+", name.lower())
    return [w[:5] for w in words if len(w) >= 3 and w not in STOP_WORDS]


def judge(
    c: dict[str, Any],
    target: dict[str, Any],
    complete: llm.Complete,
    reader: Callable[[str], str],
    captions: Callable[[str], Any],
) -> dict[str, Any]:
    """Model label with both quotes checked against the text; the resource is kept only if both."""
    limit = params.AI_FETCH_SECONDS
    if c["kind"] == "video":
        text = _within(lambda: youtube.video_text(c["video"], captions), limit) or c["text"]
    else:
        text = _within(lambda: reader(c["url"]), limit)
    if not text.strip():
        return {"label": 0, "skill_quote": "", "ai_quote": ""}
    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": (
                f"Skill: {target['name']}. "
                f"Its tasks: {'; '.join(target['tasks']) or target['name']}"
                f"\n\nResource: {c['title']} ({c['provider']})\n\nText:\n"
                f"{text[: params.COURSE_CHECK_PAGE_CHARS]}"
            ),
        },
    ]
    answer = json.loads(complete(messages, SCHEMA))
    # One of the two quotes must name the skill itself (a word of its name): a general course
    # on AI in finance quotes AI, but not this skill's work.
    named = any(
        stem in f"{answer['skill_quote']} {answer['ai_quote']}".lower()
        for stem in skill_stems(target["name"])
    )
    skill_ok = (
        answer["teaches_skill"] == "yes" and quote_found(answer["skill_quote"], text) and named
    )
    # The AI quote must itself name AI or automation: a sentence that only describes the tool's
    # ordinary features is not evidence of AI used on the work.
    ai_ok = (
        answer["applies_ai"] == "yes"
        and quote_found(answer["ai_quote"], text)
        and bool(AI_WORDS.search(answer["ai_quote"]))
    )
    return {
        "label": int(skill_ok and ai_ok),
        "skill_quote": answer["skill_quote"] if skill_ok else "",
        "ai_quote": answer["ai_quote"] if ai_ok else "",
    }


def precision_at(
    groups: list[list[dict[str, Any]]], key: Callable[[dict[str, Any]], float]
) -> float:
    """Mean share of judged resources in each skill's top AI_SHOWN by `key` that are labelled 1."""
    shares = []
    for group in groups:
        top = sorted(group, key=lambda c: -key(c))[: params.AI_SHOWN]
        if top:
            shares.append(sum(c["label"] for c in top) / len(top))
    return round(float(np.mean(shares)), 3) if shares else 0.0


def fit_ranker(judged: list[dict[str, Any]]) -> tuple[Any, dict[str, Any]]:
    """Logistic regression on the features; cross-validated AUC, or None when too few labels."""
    from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
    from sklearn.model_selection import cross_val_score  # type: ignore[import-untyped]

    x = np.array([c["features"] for c in judged])
    y = np.array([c["label"] for c in judged])
    if len(judged) < params.AI_MIN_LABELS or len(set(y.tolist())) < 2:
        return None, {"note": f"{len(judged)} labels, too few to fit"}
    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    folds = min(5, int(min(np.bincount(y))))
    auc = (
        float(np.mean(cross_val_score(model, x, y, cv=folds, scoring="roc_auc")))
        if folds >= 2
        else None
    )
    model.fit(x, y)
    return model, {
        "cv_auc": round(auc, 3) if auc is not None else None,
        "coefficients": dict(
            zip(FEATURES, (round(float(v), 3) for v in model.coef_[0]), strict=True)
        ),
    }


def run(
    settings: Settings,
    complete: llm.Complete,
    client: httpx.Client,
    key: str | None,
    only: set[str] | None = None,
    reader: Callable[[str], str] = read_page,
    captions: Callable[[str], Any] = caption_snippets,
) -> dict[str, Any]:
    from src.db import make_engine

    engine = make_engine(settings.database_url)
    version, task_rows = task_model.latest(engine)
    goals = {k: v for k, v in targets(task_rows).items() if not only or k in only}
    pool = mslearn_pool(client)
    today = datetime.now(UTC)

    def vectors(texts: list[str]) -> np.ndarray:
        out = np.array(embed(settings, texts, BACKGROUND_BUDGET_SECONDS, client))
        normed: np.ndarray = out / np.linalg.norm(out, axis=1, keepdims=True)
        return normed

    pool_vec = vectors([p["text"] for p in pool])
    groups: list[list[dict[str, Any]]] = []
    kept: dict[str, list[dict[str, Any]]] = {}
    lock = threading.Lock()

    def one(skill: str, target: dict[str, Any]) -> list[dict[str, Any]]:
        videos = youtube_pool(client, key, target["name"]) if key else []
        cands = pool + videos
        cand_vec = (
            np.vstack([pool_vec, vectors([v["text"] for v in videos])]) if videos else pool_vec
        )
        q = vectors([target["ai_query"]])[0]
        dense = cand_vec @ q
        # source_rank: the order the source itself gives (catalogue order, YouTube's search rank)
        short = [
            dict(cands[i], dense=float(dense[i]), source_rank=i if i < len(pool) else i - len(pool))
            for i in np.argsort(-dense)[: params.AI_SHORTLIST]
        ]
        texts = [s["text"] for s in short]
        skill_scores = rerank(
            settings, target["skill_query"], texts, BACKGROUND_BUDGET_SECONDS, client
        )
        ai_scores = rerank(settings, target["ai_query"], texts, BACKGROUND_BUDGET_SECONDS, client)
        for s, a, b in zip(short, skill_scores, ai_scores, strict=True):
            s["skill_score"], s["ai_score"] = float(a), float(b)
            s["features"] = features(s, today)
        judged = sorted(short, key=lambda s: -min(s["skill_score"], s["ai_score"]))[
            : params.AI_JUDGED
        ]
        for s in judged:
            s.update(judge(s, target, complete, reader, captions))
        keys = ("kind", "title", "provider", "label", "skill_score", "ai_score", "ai_quote")
        line = {
            "skill": skill,
            "tasks": target["tasks"],
            "videos_found": len(videos),
            "judged": [{k: c.get(k) for k in keys} for c in judged],
        }
        with lock:  # one line per finished skill, so a long run can be checked while it goes
            with PROGRESS.open("a", encoding="utf-8") as log:
                log.write(json.dumps(line, ensure_ascii=False) + chr(10))
            print(f"done {skill}", file=sys.stderr, flush=True)
        return judged

    with ThreadPoolExecutor(max_workers=params.AI_PARALLEL) as workers:
        futures = {skill: workers.submit(one, skill, target) for skill, target in goals.items()}
        for skill, future in futures.items():
            try:
                judged = future.result()
            except Exception as exc:  # noqa: BLE001  one skill failing never loses the others
                print(f"failed {skill}: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
                continue
            groups.append(judged)
            kept[skill] = [c for c in judged if c["label"] == 1]
    flat = [c for g in groups for c in g]
    model, ranker = fit_ranker(flat)
    score = (
        (lambda c: float(model.predict_proba([c["features"]])[0][1]))
        if model is not None
        else (lambda c: min(c["skill_score"], c["ai_score"]))
    )
    evaluation = {
        "skills": len(groups),
        "judged": len(flat),
        "kept": sum(len(v) for v in kept.values()),
        "precision_at_3": {
            "source_order": precision_at(groups, lambda c: -c["source_rank"]),
            "dense_only": precision_at(groups, lambda c: c["dense"]),
            "reranker_min": precision_at(groups, lambda c: min(c["skill_score"], c["ai_score"])),
            "learned_ranker": precision_at(groups, score),
        },
        "ranker": ranker,
        "labels": f"{settings.llm_model} judgement with both quotes verified",
        "task_model_version": version["id"] if version else None,
    }
    out = {
        "checked": f"{today:%Y-%m-%d}",
        "method": "src/collectors/ai_resources.py (targets from task evidence, BGE-M3 + "
        "bge-reranker-v2-m3 on RunPod, quote-checked judgement, logistic-regression ranker)",
        "evaluation": evaluation,
        "skills": {
            skill: {
                "tasks": goals[skill]["tasks"],
                "resources": [
                    {
                        k: c[k]
                        for k in (
                            "kind",
                            "id",
                            "title",
                            "provider",
                            "url",
                            "minutes",
                            "published",
                            "skill_quote",
                            "ai_quote",
                        )
                    }
                    | {"score": round(score(c), 3)}
                    for c in sorted(items, key=lambda c: -score(c))[: params.AI_SHOWN]
                ],
            }
            for skill, items in kept.items()
            if items
        },
    }
    skills: dict[str, Any] = out["skills"]  # type: ignore[assignment]
    out["skills"] = specific(skills, params.AI_MAX_SKILLS_PER_ITEM)
    OUT.write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return evaluation


def specific(skills: dict[str, Any], limit: int) -> dict[str, Any]:
    """Keep each resource only for the `limit` skills it scores highest on: a general course on
    AI in finance then stays where it fits best instead of filling every skill's step."""
    best: dict[str, list[tuple[float, str]]] = {}
    for skill, entry in skills.items():
        for r in entry["resources"]:
            best.setdefault(r["id"], []).append((r["score"], skill))
    allowed = {
        (rid, skill)
        for rid, pairs in best.items()
        for _, skill in sorted(pairs, reverse=True)[:limit]
    }
    out = {}
    for skill, entry in skills.items():
        kept = [r for r in entry["resources"] if (r["id"], skill) in allowed]
        if kept:
            out[skill] = {**entry, "resources": kept}
    return out


def main() -> None:
    load_env_file()
    settings = load_settings()
    if not (settings.llm_configured and settings.runpod_api_key and settings.runpod_endpoint_id):
        raise SystemExit("needs LLM_API_KEY and the RunPod endpoint")
    complete = llm.openai_complete(
        settings,
        schema_name="ai_resource_fit",
        purpose="ai_resource_check",
        timeout=params.COURSE_CHECK_LLM_SECONDS,
    )
    with http.client("ai resources", 120, follow_redirects=True) as client:
        print(
            json.dumps(
                run(
                    settings,
                    complete,
                    client,
                    os.environ.get("YOUTUBE_API_KEY"),
                    set(sys.argv[1:]) or None,
                ),
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
