"""Search routes (src/api_search.py): learning resources and O*NET work evidence for the app.

GET /api/search runs the SearchService (RunPod hybrid when configured and ready, BM25 otherwise;
the response says which). GET /api/resources/{skill_id} is the same search with a query built from
the skill's catalogue name and description, restricted to verified courses, so the result page
and the role cards can offer "learn more" links that carry a source and date.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.engine.catalogue import default_catalogue
from src.retrieval.corpus import build_corpus
from src.retrieval.models import DocumentKind, SearchFilters
from src.retrieval.service import SearchResponse, SearchService

router = APIRouter(prefix="/api", tags=["search"])

MAX_RESULTS = 10  # a page never needs more; keeps rerank calls small
MAX_QUERY_CHARS = 300


@lru_cache(maxsize=1)
def get_search() -> SearchService:
    """One service per process: the corpus is static, so it is indexed once."""
    return SearchService(build_corpus())


SearchDep = Annotated[SearchService, Depends(get_search)]


@router.get("/search")
def search(
    service: SearchDep,
    q: Annotated[str, Query(min_length=2, max_length=MAX_QUERY_CHARS)],
    kinds: Annotated[list[DocumentKind] | None, Query()] = None,
    skills: Annotated[list[str] | None, Query()] = None,
    free_only: bool = False,
    k: Annotated[int, Query(ge=1, le=MAX_RESULTS)] = 5,
) -> SearchResponse:
    filters = SearchFilters(kinds=kinds, skills=skills, free_only=free_only)
    return service.search(q, filters, k)


@router.get("/resources/{skill_id}")
def resources_for_skill(
    skill_id: str,
    service: SearchDep,
    k: Annotated[int, Query(ge=1, le=MAX_RESULTS)] = 3,
) -> SearchResponse:
    """Verified courses for one skill, found by searching with the skill's own description."""
    skill = default_catalogue().skills.get(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"unknown skill {skill_id!r}")
    query = f"{skill.name}: {skill.description}"
    return service.search(query, SearchFilters(kinds=["course"]), k)
