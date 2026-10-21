"""Documents, filters and results shared by every retriever."""

from typing import Literal

from pydantic import BaseModel

DocumentKind = Literal["course", "course_candidate", "onet_task", "onet_dwa"]
MetadataValue = str | float | bool | list[str]


class Document(BaseModel):
    """A searchable item with its source and date (no source → no claim)."""

    id: str
    kind: DocumentKind
    title: str
    text: str
    source: str
    url: str
    date: str  # retrieval or publication date (ISO)
    metadata: dict[str, MetadataValue] = {}


class SearchFilters(BaseModel):
    """Metadata filters. A filter only applies to documents that carry that field (an O*NET task
    has no cost, so `free_only` does not remove it); use `kinds` to search one kind only."""

    free_only: bool = False
    max_hours: float | None = None
    language: str | None = None
    kinds: list[DocumentKind] | None = None
    skills: list[str] | None = None  # keep documents tagged with at least one of these skills


class SearchResult(BaseModel):
    document_id: str
    kind: DocumentKind
    title: str
    score: float
    rank: int
    source: str
    url: str
    date: str
    retriever: str  # which backend produced the ranking (bm25, dense, hybrid-rrf, reranked)
