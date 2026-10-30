"""Usage counter: one row per language-model or GPU call, the measured input for cost per user.

Each row says what the call was for, which engine answered (openai, runpod), the model, the tokens
reported by the provider, how long it took and whether it succeeded. No prompt, answer or profile
content is stored.

Calls happen deep inside extraction, explanation and search, where no database engine is passed,
so the app binds its engine once at start-up (`bind`). Unbound (tests, scripts), `record` does
nothing. A failed write is logged and never breaks the call it describes.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Engine,
    Float,
    Integer,
    String,
    Table,
    func,
    insert,
    select,
)
from sqlalchemy.exc import SQLAlchemyError

from src.db import metadata

logger = logging.getLogger(__name__)

usage_table = Table(
    "usage_event",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("at", DateTime(timezone=True), nullable=False),
    Column("purpose", String(64), nullable=False),  # e.g. cv_extraction, occupation_rerank
    Column("engine", String(32), nullable=False),  # openai | runpod
    Column("model", String(64), nullable=False),
    Column("tokens_in", Integer, nullable=True),  # None when the provider reports no tokens
    Column("tokens_out", Integer, nullable=True),
    Column("seconds", Float, nullable=False),
    Column("ok", Boolean, nullable=False),
)

_bound: list[Engine] = []  # at most one engine: the app's or the pipeline's


def bind(engine: Engine) -> None:
    """Send later `record` calls to this engine's database."""
    _bound.clear()
    _bound.append(engine)


def unbind() -> None:
    _bound.clear()


def record(
    purpose: str,
    engine_name: str,
    model: str,
    seconds: float,
    ok: bool,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
) -> None:
    """Store one call. Does nothing when no engine is bound."""
    if not _bound:
        return
    try:
        with _bound[0].begin() as conn:
            conn.execute(
                insert(usage_table).values(
                    at=datetime.now(UTC),
                    purpose=purpose,
                    engine=engine_name,
                    model=model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    seconds=round(seconds, 3),
                    ok=ok,
                )
            )
    except SQLAlchemyError as exc:
        logger.warning("usage event not stored (%s)", type(exc).__name__)


def totals(engine: Engine) -> list[dict[str, Any]]:
    """Calls, failures, tokens and seconds per purpose, engine and model."""
    query = select(
        usage_table.c.purpose,
        usage_table.c.engine,
        usage_table.c.model,
        func.count().label("calls"),
        func.sum(1 - func.cast(usage_table.c.ok, Integer)).label("failed"),
        func.coalesce(func.sum(usage_table.c.tokens_in), 0).label("tokens_in"),
        func.coalesce(func.sum(usage_table.c.tokens_out), 0).label("tokens_out"),
        func.sum(usage_table.c.seconds).label("seconds"),
    ).group_by(usage_table.c.purpose, usage_table.c.engine, usage_table.c.model)
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(query).mappings()]
