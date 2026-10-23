"""Compare keyword, dense and reranked occupation matching on the labelled queries.

    .venv/Scripts/python.exe -m src.occupations.evaluate

Uses the stored catalogue and RunPod index (run the pipeline first) and real RunPod jobs, so it
is a manual measurement, not a test. Writes docs/RUNPOD_EVAL.md with top-1 / top-3 accuracy per
method (overall and for the Malay queries), job latencies and the cases each method got wrong.
"""

import statistics
import time
from datetime import UTC, datetime

import httpx
import yaml

from src.config import REPO_ROOT, load_settings
from src.db import make_engine
from src.envfile import load_env_file
from src.occupations.catalogue import catalogue, search_text
from src.occupations.detect import DENSE_CANDIDATES, _cached_vectors, bm25, dense_candidates
from src.runpod_jobs import BACKGROUND_BUDGET_SECONDS, embed, rerank

CASES = REPO_ROOT / "data" / "eval" / "occupation_titles.yaml"
REPORT = REPO_ROOT / "docs" / "RUNPOD_EVAL.md"
METHODS = ("bm25", "dense", "dense+rerank")


def main() -> None:
    load_env_file()  # the RunPod keys live in the local .env
    settings = load_settings()
    engine = make_engine(settings.database_url)
    rows = catalogue(engine)
    by_soc = {r["soc"]: r for r in rows}
    index = _cached_vectors(engine)
    cases = yaml.safe_load(CASES.read_text(encoding="utf-8"))["queries"]
    ranked: dict[str, list[list[str]]] = {m: [] for m in METHODS}
    times: dict[str, list[float]] = {"embed batch": [], "rerank": []}
    with httpx.Client(timeout=60) as client:
        started = time.monotonic()
        query_vectors = embed(settings, [c["q"] for c in cases], BACKGROUND_BUDGET_SECONDS, client)
        times["embed batch"].append(time.monotonic() - started)
        for case, qv in zip(cases, query_vectors, strict=True):
            ranked["bm25"].append([soc for soc, _ in bm25(rows, case["q"], 3)])
            dense = dense_candidates(qv, index, DENSE_CANDIDATES)
            ranked["dense"].append([soc for soc, _ in dense[:3]])
            started = time.monotonic()
            scores = rerank(
                settings, case["q"], [search_text(by_soc[s]) for s, _ in dense], 60.0, client
            )
            times["rerank"].append(time.monotonic() - started)
            order = sorted(zip([s for s, _ in dense], scores, strict=True), key=lambda x: -x[1])
            ranked["dense+rerank"].append([soc for soc, _ in order[:3]])

    def accuracy(method: str, k: int, only_ms: bool = False) -> str:
        picked = [
            (case, top)
            for case, top in zip(cases, ranked[method], strict=True)
            if not only_ms or case.get("lang") == "ms"
        ]
        hits = sum(any(s in case["ok"] for s in top[:k]) for case, top in picked)
        return f"{hits}/{len(picked)} ({100 * hits / len(picked):.0f}%)"

    lines = [
        "# RunPod occupation matching: measured comparison",
        "",
        f"Run {datetime.now(UTC):%Y-%m-%d %H:%M} UTC with `python -m src.occupations.evaluate` on "
        f"{len(rows)} O*NET 31.0 occupations and {len(cases)} team-labelled synthetic queries "
        "(`data/eval/occupation_titles.yaml`; a query counts as right when a listed code is "
        "returned). Models on RunPod: BAAI/bge-m3 (dense) and BAAI/bge-reranker-v2-m3 "
        f"(reranking the top {DENSE_CANDIDATES} dense candidates). Small diagnostic set, not a "
        "statistical guarantee; the labels were written before the run.",
        "",
        "| Method | Top-1 | Top-3 | Top-1, Malay queries | Top-3, Malay queries |",
        "|---|---|---|---|---|",
    ]
    for m in METHODS:
        lines.append(
            f"| {m} | {accuracy(m, 1)} | {accuracy(m, 3)} | {accuracy(m, 1, True)} | "
            f"{accuracy(m, 3, True)} |"
        )
    lines += [
        "",
        f"Latency: one batch job embedding all {len(cases)} queries took "
        f"{times['embed batch'][0]:.1f} s (including any cold start); reranking one query took "
        f"median {statistics.median(times['rerank']):.1f} s "
        f"(max {max(times['rerank']):.1f} s).",
        "",
        "## Misses (top-1 wrong)",
        "",
        "| Query | Expected | bm25 | dense | dense+rerank |",
        "|---|---|---|---|---|",
    ]
    for i, case in enumerate(cases):
        firsts = [ranked[m][i][0] if ranked[m][i] else "—" for m in METHODS]
        if any(f not in case["ok"] for f in firsts):
            marks = [f if f in case["ok"] else f"**{f}**" for f in firsts]
            lines.append(f"| {case['q']} | {', '.join(case['ok'])} | " + " | ".join(marks) + " |")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:12]))


if __name__ == "__main__":
    main()
