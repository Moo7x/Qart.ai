"""Catalogue of every O*NET occupation, and its BGE-M3 index built on RunPod.

Each row: title, description, job titles people report, the most important core tasks (O*NET),
and the closest ESCO occupation from the official ESCO–O*NET crosswalk (its ISCO-08 group is
looked up from the ESCO API when an occupation is first previewed). The catalogue is rebuilt
when a new O*NET release appears. Vectors are stored per (occupation, model, text hash), so only
new or changed texts are embedded again. This is what lets any CV job title be matched to a
standard occupation, beyond the finance pack.
"""

import csv
import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import Column, DateTime, Engine, String, Table, Text, delete, insert, select

from src.collectors.onet import DOWNLOAD, latest_release
from src.config import Settings
from src.db import metadata
from src.pack import load_pack
from src.runpod_jobs import BACKGROUND_BUDGET_SECONDS, embed

ESCO_CROSSWALK = (
    "https://esco.ec.europa.eu/system/files/2023-08/ONET_%28Occupations%29_0_updated.csv"
)
MODEL = "BAAI/bge-m3"
TOP_TASKS = 6  # core tasks kept per occupation for the evidence preview
MATCH_ORDER = {"exactMatch": 0, "closeMatch": 1, "narrowMatch": 2, "broadMatch": 3}

catalogue_table = Table(
    "occupation_catalogue",
    metadata,
    Column("soc", String(16), primary_key=True),
    Column("title", String(256), nullable=False),
    Column("description", Text, nullable=False),
    Column("reported_titles", Text, nullable=False),  # JSON list
    Column("tasks", Text, nullable=False),  # JSON list of {task, text, importance}
    Column("esco_uri", String(128), nullable=True),
    Column("esco_title", String(256), nullable=True),
    Column("esco_match", String(32), nullable=True),
    Column("isco", String(8), nullable=True),  # filled lazily from the ESCO API
    Column("release", String(16), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
vector_table = Table(
    "occupation_vector",
    metadata,
    Column("soc", String(16), primary_key=True),
    Column("model", String(64), primary_key=True),
    Column("text_hash", String(64), nullable=False),
    Column("vector", Text, nullable=False),  # JSON list of floats (normalised)
)


def gbs_titles() -> dict[str, list[str]]:
    """Malaysian GBS role titles (TalentCorp, via the pack's role-to-occupation links) per SOC."""
    out: dict[str, list[str]] = {}
    pack = load_pack()
    for soc, title in [
        *((r.soc, r.title) for r in pack.current_roles.values()),
        *((r.soc, r.title) for r in pack.destination_roles.values()),
    ]:
        out.setdefault(soc, []).append(title)
    return out


def search_text(row: dict[str, Any]) -> str:
    """What is embedded and keyword-searched for one occupation."""
    titles = json.loads(row["reported_titles"])
    also = f" Also called: {', '.join(titles)}." if titles else ""
    gbs = gbs_titles().get(row["soc"], [])
    local = f" Malaysian GBS roles: {', '.join(gbs)}." if gbs else ""
    return f"{row['title']}.{also}{local} {row['description']}"


def _text_hash(text: str) -> str:
    return hashlib.sha256(f"{MODEL}|{text}".encode()).hexdigest()


def parse_onet(data: bytes, release: str) -> list[dict[str, Any]]:
    archive = zipfile.ZipFile(io.BytesIO(data))

    def rows(name: str) -> list[dict[str, str]]:
        path = next(n for n in archive.namelist() if n.endswith(f"/{name}"))
        with archive.open(path) as handle:
            return list(csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8")))

    titles: dict[str, list[str]] = {}
    for r in rows("sample_of_reported_titles.csv"):
        titles.setdefault(r["O*NET-SOC Code"], []).append(r["Reported Job Title"])
    importance = {
        (r["O*NET-SOC Code"], r["Task ID"]): float(r["Data Value"])
        for r in rows("task_ratings.csv")
        if r["Scale ID"] == "IM"
    }
    tasks: dict[str, list[dict[str, Any]]] = {}
    for r in rows("task_statements.csv"):
        if r["Task Type"] == "Core":
            key = (r["O*NET-SOC Code"], r["Task ID"])
            tasks.setdefault(key[0], []).append(
                {"task": r["Task ID"], "text": r["Task"], "importance": importance.get(key)}
            )
    out = []
    for r in rows("occupation_data.csv"):
        soc = r["O*NET-SOC Code"]
        top = sorted(tasks.get(soc, []), key=lambda t: -(t["importance"] or 0))[:TOP_TASKS]
        out.append(
            {
                "soc": soc,
                "title": r["Title"],
                "description": r["Description"],
                "reported_titles": json.dumps(titles.get(soc, [])),
                "tasks": json.dumps(top),
                "release": release,
            }
        )
    return out


def parse_esco(text: str) -> dict[str, tuple[str, str, str]]:
    """Best ESCO match per O*NET-SOC code: (uri, title, match type)."""
    reader = csv.reader(io.StringIO(text))
    best: dict[str, tuple[int, tuple[str, str, str]]] = {}
    header_seen = False
    for row in reader:
        if not header_seen:
            header_seen = bool(row) and row[0].startswith("O*NET Id")
            continue
        if len(row) < 7 or row[6] not in MATCH_ORDER:
            continue
        rank = MATCH_ORDER[row[6]]
        if row[0] not in best or rank < best[row[0]][0]:
            best[row[0]] = (rank, (row[3], row[4], row[6]))
    return {soc: value for soc, (_, value) in best.items()}


def current_release(engine: Engine) -> str | None:
    with engine.connect() as conn:
        return conn.execute(select(catalogue_table.c.release).limit(1)).scalar_one_or_none()


def refresh_catalogue(engine: Engine, client: httpx.Client) -> str:
    found = latest_release(client)
    if found is None:
        return "no O*NET release found"
    release = f"{found[0]}.{found[1]}"
    if current_release(engine) == release:
        return f"catalogue current (O*NET {release})"
    archive = client.get(DOWNLOAD.format(major=found[0], minor=found[1]), follow_redirects=True)
    archive.raise_for_status()
    rows = parse_onet(archive.content, release)
    crosswalk = client.get(ESCO_CROSSWALK, follow_redirects=True)
    crosswalk.raise_for_status()
    esco = parse_esco(crosswalk.content.decode("utf-8-sig"))
    now = datetime.now(UTC)
    with engine.begin() as conn:
        conn.execute(delete(catalogue_table))
        for row in rows:
            uri, title, match = esco.get(row["soc"], (None, None, None))
            conn.execute(
                insert(catalogue_table).values(
                    **row,
                    esco_uri=uri,
                    esco_title=title,
                    esco_match=match,
                    isco=None,
                    updated_at=now,
                )
            )
    return f"catalogue rebuilt: {len(rows)} occupations (O*NET {release})"


def catalogue(engine: Engine) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(select(catalogue_table)).mappings()]


def vectors(engine: Engine) -> dict[str, list[float]]:
    with engine.connect() as conn:
        rows = conn.execute(select(vector_table).where(vector_table.c.model == MODEL)).mappings()
        return {r["soc"]: json.loads(r["vector"]) for r in rows}


def build_index(engine: Engine, settings: Settings, client: httpx.Client) -> str:
    """Embed occupations whose text is new or changed, on RunPod, in background jobs."""
    rows = catalogue(engine)
    with engine.connect() as conn:
        known = {
            r["soc"]: r["text_hash"]
            for r in conn.execute(
                select(vector_table).where(vector_table.c.model == MODEL)
            ).mappings()
        }
    todo = [
        (r["soc"], search_text(r))
        for r in rows
        if known.get(r["soc"]) != _text_hash(search_text(r))
    ]
    if not todo:
        return f"occupation index current ({len(known)} vectors)"
    if not settings.runpod_configured:
        return f"RunPod not configured: {len(todo)} occupations not embedded; keyword search used"
    found = embed(settings, [text for _, text in todo], BACKGROUND_BUDGET_SECONDS, client)
    with engine.begin() as conn:
        for (soc, text), vector in zip(todo, found, strict=True):
            conn.execute(
                delete(vector_table).where(vector_table.c.soc == soc, vector_table.c.model == MODEL)
            )
            conn.execute(
                insert(vector_table).values(
                    soc=soc, model=MODEL, text_hash=_text_hash(text), vector=json.dumps(vector)
                )
            )
    return f"embedded {len(todo)} occupations on RunPod ({MODEL})"
