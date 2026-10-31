"""The same CV is always read the same way.

A language model can link a CV sentence to a different skill on another run, even at temperature
0, so one CV could give two fits. The first model reading of a CV is stored, keyed by the CV text
after personal details are removed, the model name and a fingerprint of the instructions and the
skill list; the same CV then gets the same reading. A new model, new instructions or a new skill
list make a new key, so the CV is read again. Fallback readings (no model) are never stored.
Only the reading is stored: the scrubbed CV text itself is not kept, only its hash.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Engine, String, Table, Text, insert, select

from src.db import metadata

cache_table = Table(
    "cv_reading",
    metadata,
    Column("key", String(64), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("model", String(64), nullable=False),
    Column("reading", Text, nullable=False),  # JSON of the extraction answer
)


def key(scrubbed_text: str, model: str, fingerprint: str) -> str:
    return hashlib.sha256(f"{model}\n{fingerprint}\n{scrubbed_text}".encode()).hexdigest()


def get(engine: Engine, cache_key: str) -> dict[str, Any] | None:
    with engine.connect() as conn:
        row = conn.execute(
            select(cache_table.c.reading).where(cache_table.c.key == cache_key)
        ).first()
    return json.loads(row.reading) if row else None


def put(engine: Engine, cache_key: str, model: str, reading: dict[str, Any]) -> None:
    with engine.begin() as conn:
        if conn.execute(select(cache_table.c.key).where(cache_table.c.key == cache_key)).first():
            return
        conn.execute(
            insert(cache_table).values(
                key=cache_key,
                created_at=datetime.now(UTC),
                model=model,
                reading=json.dumps(reading),
            )
        )
