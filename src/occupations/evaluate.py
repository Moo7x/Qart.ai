"""Compare keyword, dense, hybrid and reranked occupation matching on labelled queries.

    .venv/Scripts/python.exe -m src.occupations.evaluate            # the development set
    .venv/Scripts/python.exe -m src.occupations.evaluate holdout    # the frozen hold-out set

Uses the stored catalogue and RunPod index (run the pipeline first) and real RunPod jobs, so it
is a manual measurement, not a test. It rewrites only its own set's section of
docs/RUNPOD_EVAL.md (between the markers), with top-1, top-3 and mean reciprocal rank per method,
overall and by query kind, the job latencies and the misses. The hold-out set was frozen before the
hybrid search was built, so its numbers are the ones to quote.
"""

import re
import statistics
import sys
import time
from datetime import UTC, datetime
from typing import Any

import httpx
import yaml

from src import http
from src.config import REPO_ROOT, load_settings
from src.db import make_engine
from src.envfile import load_env_file
from src.occupations.catalogue import catalogue, search_text
from src.occupations.detect import (
    DENSE_CANDIDATES,
    HYBRID_CANDIDATES,
    RERANK_CANDIDATES,
    _cached_vectors,
    bm25,
    dense_candidates,
    keyword_query,
    rrf,
)
from src.runpod_jobs import BACKGROUND_BUDGET_SECONDS, embed, rerank

SETS = {
    "dev": REPO_ROOT / "data" / "eval" / "occupation_titles.yaml",
    "holdout": REPO_ROOT / "data" / "eval" / "occupation_titles_holdout.yaml",
}
REPORT = REPO_ROOT / "docs" / "RUNPOD_EVAL.md"
METHODS = ("bm25", "dense", "dense+rerank", "hybrid", "hybrid+rerank")
RERANK_BUDGET_SECONDS = 60.0
SHOWN = 3


def _group(case: dict[str, Any]) -> str:
    return str(case.get("kind") or case.get("lang") or "en")


def mrr(ranked: list[str], ok: list[str]) -> float:
    """Reciprocal rank of the first accepted code in the top 3 (0 when none is there)."""
    return next((1.0 / i for i, soc in enumerate(ranked[:SHOWN], 1) if soc in ok), 0.0)


def _rank_all(
    cases: list[dict[str, Any]], settings: Any, engine: Any
) -> tuple[dict[str, list[list[str]]], dict[str, list[float]], int]:
    rows = catalogue(engine)
    by_soc = {r["soc"]: r for r in rows}
    index = _cached_vectors(engine)
    ranked: dict[str, list[list[str]]] = {m: [] for m in METHODS}
    times: dict[str, list[float]] = {"embed batch": [], "rerank": []}

    def reranked(client: httpx.Client, query: str, socs: list[str]) -> list[str]:
        started = time.monotonic()
        scores = rerank(
            settings, query, [search_text(by_soc[s]) for s in socs], RERANK_BUDGET_SECONDS, client
        )
        times["rerank"].append(time.monotonic() - started)
        return [s for s, _ in sorted(zip(socs, scores, strict=True), key=lambda x: -x[1])]

    with http.client("occupation evaluation", 60) as client:
        started = time.monotonic()
        vectors = embed(settings, [c["q"] for c in cases], BACKGROUND_BUDGET_SECONDS, client)
        times["embed batch"].append(time.monotonic() - started)
        for case, qv in zip(cases, vectors, strict=True):
            keyword = [s for s, _ in bm25(rows, keyword_query(case["q"]), HYBRID_CANDIDATES)]
            dense = [s for s, _ in dense_candidates(qv, index, HYBRID_CANDIDATES)]
            fused = [s for s, _ in rrf([dense, keyword])]
            ranked["bm25"].append(keyword[:SHOWN])
            ranked["dense"].append(dense[:SHOWN])
            ranked["hybrid"].append(fused[:SHOWN])
            ranked["dense+rerank"].append(
                reranked(client, case["q"], dense[:DENSE_CANDIDATES])[:SHOWN]
            )
            ranked["hybrid+rerank"].append(
                reranked(client, case["q"], fused[:RERANK_CANDIDATES])[:SHOWN]
            )
    return ranked, times, len(rows)


def _report(
    name: str,
    cases: list[dict[str, Any]],
    ranked: dict[str, list[list[str]]],
    times: dict[str, list[float]],
    occupations: int,
) -> list[str]:
    groups = sorted({_group(c) for c in cases})

    def score(method: str, group: str | None = None) -> tuple[str, str, str]:
        picked = [
            (c, top)
            for c, top in zip(cases, ranked[method], strict=True)
            if group is None or _group(c) == group
        ]
        n = len(picked)
        top1 = sum(bool(top) and top[0] in c["ok"] for c, top in picked)
        top3 = sum(any(s in c["ok"] for s in top[:SHOWN]) for c, top in picked)
        rr = statistics.fmean(mrr(top, c["ok"]) for c, top in picked)
        return (
            f"{top1}/{n} ({100 * top1 / n:.0f}%)",
            f"{top3}/{n} ({100 * top3 / n:.0f}%)",
            f"{rr:.2f}",
        )

    lines = [
        f"Run {datetime.now(UTC):%Y-%m-%d %H:%M} UTC with `python -m src.occupations.evaluate "
        f"{name}` on {occupations} O*NET 31.0 occupations and {len(cases)} queries "
        f"(`{SETS[name].relative_to(REPO_ROOT).as_posix()}`). Models on RunPod: BAAI/bge-m3 "
        f"(dense) and BAAI/bge-reranker-v2-m3. Hybrid = BM25 and dense top {HYBRID_CANDIDATES} "
        f"each, merged by reciprocal rank fusion, reranked top {RERANK_CANDIDATES}; dense+rerank "
        f"reranks the dense top {DENSE_CANDIDATES}. MRR counts the top 3. A small diagnostic "
        "set, not a statistical guarantee.",
        "",
        "| Method | Top-1 | Top-3 | MRR |",
        "|---|---|---|---|",
        *(f"| {m} | " + " | ".join(score(m)) + " |" for m in METHODS),
        "",
        "Top-1 by query kind (en = English, ms = Malay, mixed, typo):",
        "",
        "| Method | " + " | ".join(groups) + " |",
        "|---|" + "---|" * len(groups),
        *(f"| {m} | " + " | ".join(score(m, g)[0] for g in groups) + " |" for m in METHODS),
        "",
        f"Latency: one batch job embedding all {len(cases)} queries took "
        f"{times['embed batch'][0]:.1f} s (including any cold start); one rerank job took median "
        f"{statistics.median(times['rerank']):.1f} s (max {max(times['rerank']):.1f} s).",
        "",
        "Misses (top-1 wrong for hybrid+rerank):",
        "",
        "| Query | Expected | bm25 | dense | hybrid | hybrid+rerank |",
        "|---|---|---|---|---|---|",
    ]
    for i, case in enumerate(cases):
        firsts = {m: ranked[m][i][0] if ranked[m][i] else "—" for m in METHODS}
        if firsts["hybrid+rerank"] not in case["ok"]:
            marks = [
                f if f in case["ok"] else f"**{f}**"
                for f in (firsts[m] for m in ("bm25", "dense", "hybrid", "hybrid+rerank"))
            ]
            lines.append(f"| {case['q']} | {', '.join(case['ok'])} | " + " | ".join(marks) + " |")
    return lines


def write_section(report: str, name: str, lines: list[str]) -> str:
    """Replace this set's section between its markers, or append it."""
    start, end = f"<!-- results:{name} -->", f"<!-- end results:{name} -->"
    block = "\n".join([start, *lines, end])
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if pattern.search(report):
        return pattern.sub(lambda _: block, report)
    return report.rstrip() + "\n\n" + block + "\n"


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "dev"
    if name not in SETS:
        raise SystemExit(f"unknown set {name!r}; choose one of {', '.join(SETS)}")
    load_env_file()  # the RunPod keys live in the local .env
    settings = load_settings()
    engine = make_engine(settings.database_url)
    cases = yaml.safe_load(SETS[name].read_text(encoding="utf-8"))["queries"]
    ranked, times, occupations = _rank_all(cases, settings, engine)
    lines = _report(name, cases, ranked, times, occupations)
    REPORT.write_text(
        write_section(REPORT.read_text(encoding="utf-8"), name, lines), encoding="utf-8"
    )
    print("\n".join(lines[:10]))


if __name__ == "__main__":
    main()
