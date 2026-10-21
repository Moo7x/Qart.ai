"""Retrieval preparation (item 8): BM25 baseline, filters, RRF, hybrid interfaces, corpus,
Microsoft Learn candidates and the recall@5 evaluation."""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from eval.retrieval_eval import load_set, mean_recall, recall_at_k, run
from src.engine.catalogue import default_case_index, default_catalogue
from src.engine.planner import build_resources
from src.retrieval.bm25 import BM25Retriever, tokenize
from src.retrieval.corpus import build_corpus, build_onet_processed, load_onet_processed
from src.retrieval.hybrid import DenseRetriever, HybridRetriever, reciprocal_rank_fusion
from src.retrieval.models import Document, SearchFilters
from src.retrieval.mslearn import CANDIDATES_PATH, is_candidate, select_candidates
from src.retrieval.runpod_backends import RunPodBGEM3Embedder, RunPodBGEReranker


def doc(doc_id: str, text: str, **meta: Any) -> Document:
    return Document(
        id=doc_id,
        kind="course",
        title=doc_id,
        text=text,
        source="test source",
        url=f"https://example.test/{doc_id}",
        date="2026-10-21",
        metadata=meta,
    )


DOCS = [
    doc(
        "sql",
        "query ledger tables with SQL select joins",
        cost="free",
        hours=3.0,
        language="en",
        skills=["sql_basics"],
    ),
    doc(
        "paid_sql",
        "SQL for finance teams",
        cost="paid (Coursera)",
        hours=1.0,
        language="en",
        skills=["sql_basics"],
    ),
    doc(
        "forecast",
        "forecasting time series models",
        cost="free",
        hours=15.0,
        language="en",
        skills=["forecasting"],
    ),
    doc(
        "malay",
        "SQL asas untuk kewangan",
        cost="free",
        hours=2.0,
        language="ms",
        skills=["sql_basics"],
    ),
]


def bm25() -> BM25Retriever:
    retriever = BM25Retriever()
    retriever.index(DOCS)
    return retriever


# --- BM25 and filters -----------------------------------------------------------------------
def test_tokenize_drops_stop_words_and_punctuation() -> None:
    assert tokenize("How to use SQL, for the ledger?") == ["sql", "ledger"]


def test_bm25_ranks_matching_documents_with_source_and_date() -> None:
    results = bm25().search("SQL ledger")
    assert results[0].document_id == "sql"
    assert all(r.source and r.url and r.date for r in results)
    assert [r.rank for r in results] == list(range(1, len(results) + 1))
    assert bm25().search("photosynthesis") == []


def test_filters_free_hours_language_skills_and_kinds() -> None:
    retriever = bm25()
    free = {r.document_id for r in retriever.search("SQL", SearchFilters(free_only=True))}
    assert "paid_sql" not in free and "sql" in free
    short = {r.document_id for r in retriever.search("SQL", SearchFilters(max_hours=2))}
    assert short == {"paid_sql", "malay"}
    english = {r.document_id for r in retriever.search("SQL", SearchFilters(language="en"))}
    assert "malay" not in english
    tasks_only = retriever.search("SQL", SearchFilters(kinds=["onet_task"]))
    assert tasks_only == []
    skills = {r.document_id for r in retriever.search("SQL", SearchFilters(skills=["forecasting"]))}
    assert skills == set()


def test_filters_skip_documents_without_the_field() -> None:
    retriever = BM25Retriever()
    retriever.index([doc("task", "reconcile bank records")])  # no cost metadata
    assert retriever.search("reconcile", SearchFilters(free_only=True, max_hours=1))


# --- fusion and hybrid interfaces -----------------------------------------------------------
def test_reciprocal_rank_fusion_formula() -> None:
    fused = dict(reciprocal_rank_fusion([["a", "b"], ["b", "c"]], k=60))
    assert fused["b"] == pytest.approx(1 / 62 + 1 / 61)
    assert fused["a"] == pytest.approx(1 / 61)
    assert max(fused, key=lambda key: fused[key]) == "b"


class WordEmbedder:
    """Fake embedder for tests: counts of a tiny vocabulary (no model, no network)."""

    vocabulary = ("sql", "ledger", "forecast", "forecasting", "kewangan")

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[float(tokenize(t).count(w)) for w in self.vocabulary] for t in texts]


class LengthReranker:
    def score(self, query: str, passages: Sequence[str]) -> list[float]:
        return [-float(len(p)) for p in passages]  # prefers the shortest passage


def test_dense_and_hybrid_retrievers_work_with_any_backend() -> None:
    dense = DenseRetriever(WordEmbedder())
    dense.index(DOCS)
    assert dense.search("forecast forecasting")[0].document_id == "forecast"
    hybrid = HybridRetriever(BM25Retriever(), DenseRetriever(WordEmbedder()))
    hybrid.index(DOCS)
    assert hybrid.search("SQL ledger")[0].document_id == "sql"
    reranked = HybridRetriever(BM25Retriever(), DenseRetriever(WordEmbedder()), LengthReranker())
    reranked.index(DOCS)
    top = reranked.search("SQL", k=2)
    assert reranked.name == "hybrid-rrf+rerank" and top[0].retriever == "hybrid-rrf+rerank"


def test_runpod_backends_are_interfaces_only() -> None:
    with pytest.raises(NotImplementedError):
        RunPodBGEM3Embedder().embed(["x"])
    with pytest.raises(NotImplementedError):
        RunPodBGEReranker().score("q", ["p"])


# --- corpus ---------------------------------------------------------------------------------
def test_corpus_has_courses_and_onet_documents_with_sources() -> None:
    corpus = build_corpus()
    kinds = {d.kind for d in corpus}
    assert kinds == {"course", "onet_task", "onet_dwa"}
    assert all(d.source and d.url and d.date for d in corpus)
    processed = load_onet_processed()
    role_codes = {b.code for r in default_catalogue().roles.values() for b in r.based_on}
    assert set(processed["occupations"]) == role_codes
    assert "CC BY 4.0" in processed["source"] and processed["retrieved"] == "2026-10-21"


def test_build_onet_processed_filters_to_our_occupations(tmp_path: Path) -> None:
    (tmp_path / "task_statements.csv").write_text(
        "O*NET-SOC Code,Title,Task ID,Task,Task Type,Incumbents Responding,Date,Domain Source\n"
        "43-3031.00,Clerks,1,Reconcile records.,Core,1,08/2023,Incumbent\n"
        "11-1011.00,Chief Executives,2,Direct things.,Core,1,08/2023,Incumbent\n",
        encoding="utf-8",
    )
    (tmp_path / "tasks_to_dwas.csv").write_text(
        "O*NET-SOC Code,Title,Task ID,Task,DWA Element ID,DWA Element Name,Date,Domain Source\n"
        "43-3031.00,Clerks,1,Reconcile records.,4.A.1,Reconcile accounts.,07/2014,Analyst\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    result = build_onet_processed(tmp_path, out, ["43-3031.00"], "2026-10-21")
    assert [t["task_id"] for t in result["tasks"]] == ["1"]
    assert result["tasks"][0]["dwas"] == [{"id": "4.A.1", "name": "Reconcile accounts."}]
    assert json.loads(out.read_text(encoding="utf-8"))["retrieved"] == "2026-10-21"


# --- Microsoft Learn candidates (never used by the planner) ---------------------------------
def item(title: str, levels: list[str], roles: list[str], products: list[str]) -> dict[str, Any]:
    return {
        "uid": title.lower().replace(" ", "-"),
        "title": title,
        "type": "module",
        "url": "https://learn.microsoft.com/x",
        "duration_in_minutes": 30,
        "levels": levels,
        "roles": roles,
        "products": products,
    }


def test_mslearn_selection_rule() -> None:
    assert is_candidate(
        item("Analyze data in Excel", ["beginner"], ["business-user"], ["office-excel"])
    )
    assert is_candidate(item("Introduction to AI concepts", ["beginner"], ["business-user"], []))
    assert not is_candidate(
        item("Analyze data in Excel", ["advanced"], ["business-user"], ["office-excel"])
    )
    assert not is_candidate(item("Deploy Kubernetes", ["beginner"], ["developer"], ["azure"]))
    chosen = select_candidates(
        {"modules": [item("Finance basics", ["beginner"], ["business-analyst"], [])]}, "2026-10-21"
    )
    assert chosen[0]["status"] == "candidate" and chosen[0]["hours"] == 0.5


def test_mslearn_candidates_are_not_used_by_the_planner() -> None:
    data = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    assert data["candidates"] and all(c["status"] == "candidate" for c in data["candidates"])
    cat = default_catalogue()
    assert not any(course_id.startswith("mslearn:") for course_id in cat.courses)
    resources = build_resources(list(cat.skills), {}, cat, default_case_index(), set())
    assert not any(r.id.startswith("mslearn:") for r in resources)


# --- recall@5 evaluation --------------------------------------------------------------------
def test_recall_at_k_counts_hits() -> None:
    retriever = bm25()
    queries = [{"id": "x", "query": "SQL ledger", "relevant": ["sql", "forecast"]}]
    results = recall_at_k(retriever, queries, k=1)
    assert (results[0].hits, results[0].relevant) == (1, 2)
    assert mean_recall(results) == 0.5


def test_retrieval_eval_writes_its_section(tmp_path: Path) -> None:
    results = tmp_path / "RESULTS.md"
    recall = run(results_path=results)
    text = results.read_text(encoding="utf-8")
    assert 0.0 <= recall <= 1.0
    assert "bm25 (CPU baseline)" in text and "not run" in text
    assert len(load_set()) == text.count("| q")
