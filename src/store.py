"""Tiny persistence for profiles, events, assumption versions, ingested snapshots and optimiser
proposals (Person A). Objects are stored as contract JSON; the database only indexes them.

Backend (select_backend): Postgres when DATABASE_URL is set (Replit's built-in Postgres; Replit
deployments don't keep runtime files reliably and may run several instances), otherwise a SQLite
file (QART_DB_PATH, default data/qart.sqlite). Same tables and behaviour on both: SQL is written
once with "?" placeholders and portable ON CONFLICT upserts; only the auto-increment column type
differs.

Every write that can change a recommendation (an event, a flag, a new assumption version, an
ingested snapshot) is appended to `changes`, so `changed_since` can name the latest cause without
trusting client clocks.
"""

import json
import os
import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from contextlib import AbstractContextManager, contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from src.contract import CompanyAssumptions, Event, OptimizerProposal, Profile

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "data" / "qart.sqlite"
DB_PATH_ENV = "QART_DB_PATH"
DATABASE_URL_ENV = "DATABASE_URL"
# Postgres advisory-lock key ("QART" in ASCII) so only one instance seeds an empty database.
SEED_LOCK_KEY = 0x51415254

# {serial} is the auto-increment primary key: SQLite and Postgres spell it differently.
SCHEMA_TEMPLATE = (
    "CREATE TABLE IF NOT EXISTS profiles (id TEXT PRIMARY KEY, body TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS events (seq {serial}, id TEXT NOT NULL UNIQUE, "
    "user_id TEXT NOT NULL, body TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS events_by_user ON events (user_id)",
    "CREATE TABLE IF NOT EXISTS assumptions (version INTEGER PRIMARY KEY, body TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, position INTEGER NOT NULL)",
    "CREATE TABLE IF NOT EXISTS proposals (id TEXT PRIMARY KEY, body TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS changes (seq {serial}, kind TEXT NOT NULL, ref TEXT NOT NULL, "
    "user_id TEXT)",
    "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS playbooks (version TEXT PRIMARY KEY, body TEXT NOT NULL)",
)
SERIAL_TYPE = {
    "sqlite": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "postgres": "BIGSERIAL PRIMARY KEY",
}
# Cleared by a demo reset: practice, evidence and assumption state. Optimiser state (proposals,
# playbook texts, the active version in settings) is kept on purpose: a run takes minutes and
# costs LLM calls, and the senior can roll back to playbook_v1 at any time.
TABLES = ("profiles", "events", "assumptions", "snapshots", "changes")

BackendKind = Literal["sqlite", "postgres"]


@dataclass(frozen=True)
class BackendChoice:
    kind: BackendKind
    target: str  # SQLite file path, or the Postgres URL (a secret: never log it)


def select_backend(env: Mapping[str, str]) -> BackendChoice:
    """Postgres if DATABASE_URL is set and non-empty, else SQLite at QART_DB_PATH or default."""
    url = env.get(DATABASE_URL_ENV, "").strip()
    if url:
        return BackendChoice("postgres", url)
    path = env.get(DB_PATH_ENV, "").strip()
    return BackendChoice("sqlite", path or str(DEFAULT_DB_PATH))


@dataclass(frozen=True)
class Change:
    seq: int
    kind: str  # event | flag | assumptions | snapshot
    ref: str
    user_id: str | None


class Cursor(Protocol):
    def fetchone(self) -> Any: ...

    def fetchall(self) -> list[Any]: ...


class Connection(Protocol):
    def execute(self, sql: str, params: Sequence[Any] = ...) -> Cursor: ...


class _PostgresConnection:
    """Adapts a psycopg connection to the "?" placeholders used in this module."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def execute(self, sql: str, params: Sequence[Any] = ()) -> Cursor:
        cursor: Cursor = self._conn.execute(sql.replace("?", "%s"), tuple(params))
        return cursor


class Store:
    """Contract-object store. One connection per call keeps it safe under FastAPI's threadpool."""

    def __init__(self, path: Path | str, backend: BackendKind = "sqlite") -> None:
        self.backend: BackendKind = backend
        self.path = str(path)
        with self._connect() as conn:
            for statement in SCHEMA_TEMPLATE:
                conn.execute(statement.format(serial=SERIAL_TYPE[backend]))

    @contextmanager
    def _connect(self) -> Iterator[Connection]:
        if self.backend == "postgres":
            import psycopg  # imported lazily: SQLite-only runs and tests don't need the driver

            with psycopg.connect(self.path) as pg_conn:  # commits on success, closes on exit
                yield _PostgresConnection(pg_conn)
            return
        conn = sqlite3.connect(self.path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def seed_lock(self) -> AbstractContextManager[object]:
        """Serialise "seed if empty" across instances (Postgres advisory lock; no-op on SQLite)."""
        if self.backend != "postgres":
            return nullcontext()
        return self._advisory_lock()

    @contextmanager
    def _advisory_lock(self) -> Iterator[object]:
        with self._connect() as conn:
            conn.execute("SELECT pg_advisory_lock(?)", (SEED_LOCK_KEY,))
            try:
                yield conn
            finally:
                conn.execute("SELECT pg_advisory_unlock(?)", (SEED_LOCK_KEY,))

    def clear(self) -> None:
        with self._connect() as conn:
            for table in TABLES:
                conn.execute(f"DELETE FROM {table}")  # noqa: S608 (fixed table names)

    def is_empty(self) -> bool:
        with self._connect() as conn:
            count: int = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
        return count == 0

    def _log(self, conn: Connection, kind: str, ref: str, user_id: str | None) -> None:
        conn.execute(
            "INSERT INTO changes (kind, ref, user_id) VALUES (?, ?, ?)", (kind, ref, user_id)
        )

    # --- profiles ------------------------------------------------------------------------
    def upsert_profile(self, profile: Profile) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO profiles (id, body) VALUES (?, ?) "
                "ON CONFLICT (id) DO UPDATE SET body = excluded.body",
                (profile.id, profile.model_dump_json()),
            )

    def get_profile(self, user_id: str) -> Profile | None:
        with self._connect() as conn:
            row = conn.execute("SELECT body FROM profiles WHERE id = ?", (user_id,)).fetchone()
        return Profile.model_validate_json(row[0]) if row else None

    def list_profiles(self) -> list[Profile]:
        with self._connect() as conn:
            rows = conn.execute("SELECT body FROM profiles ORDER BY id").fetchall()
        return [Profile.model_validate_json(r[0]) for r in rows]

    # --- events --------------------------------------------------------------------------
    def add_event(self, event: Event, log: bool = True) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO events (id, user_id, body) VALUES (?, ?, ?)",
                (event.id, event.user_id, event.model_dump_json()),
            )
            if log:
                self._log(conn, "event", event.id, event.user_id)

    def get_event(self, event_id: str) -> Event | None:
        with self._connect() as conn:
            row = conn.execute("SELECT body FROM events WHERE id = ?", (event_id,)).fetchone()
        return Event.model_validate_json(row[0]) if row else None

    def replace_event(self, event: Event) -> None:
        """Store an updated event (used only to set flags) and log it as a change."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE events SET body = ? WHERE id = ?", (event.model_dump_json(), event.id)
            )
            self._log(conn, "flag", event.id, event.user_id)

    def events_for(self, user_id: str) -> list[Event]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT body FROM events WHERE user_id = ? ORDER BY seq", (user_id,)
            ).fetchall()
        return [Event.model_validate_json(r[0]) for r in rows]

    # --- assumptions (layer B, versioned) ------------------------------------------------
    def put_assumptions(self, assumptions: CompanyAssumptions, log: bool = True) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO assumptions (version, body) VALUES (?, ?)",
                (assumptions.version, assumptions.model_dump_json()),
            )
            if log:
                self._log(conn, "assumptions", str(assumptions.version), None)

    def assumptions(self, version: int | None = None) -> CompanyAssumptions | None:
        """A given version, or the latest when `version` is None."""
        query = "SELECT body FROM assumptions ORDER BY version DESC LIMIT 1"
        params: tuple[int, ...] = ()
        if version is not None:
            query, params = "SELECT body FROM assumptions WHERE version = ?", (version,)
        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()
        return CompanyAssumptions.model_validate_json(row[0]) if row else None

    # --- snapshots (which committed snapshots have been ingested) ------------------------
    def mark_snapshot_ingested(self, snapshot_id: str, log: bool = True) -> None:
        with self._connect() as conn:
            position = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
            conn.execute(
                "INSERT INTO snapshots (id, position) VALUES (?, ?) ON CONFLICT (id) DO NOTHING",
                (snapshot_id, position),
            )
            if log:
                self._log(conn, "snapshot", snapshot_id, None)

    def ingested_snapshot_ids(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id FROM snapshots ORDER BY position").fetchall()
        return [r[0] for r in rows]

    # --- optimiser proposals -------------------------------------------------------------
    def put_proposal(self, proposal: OptimizerProposal) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO proposals (id, body) VALUES (?, ?) "
                "ON CONFLICT (id) DO UPDATE SET body = excluded.body",
                (proposal.id, proposal.model_dump_json()),
            )

    def get_proposal(self, proposal_id: str) -> OptimizerProposal | None:
        with self._connect() as conn:
            row = conn.execute("SELECT body FROM proposals WHERE id = ?", (proposal_id,)).fetchone()
        return OptimizerProposal.model_validate_json(row[0]) if row else None

    def list_proposals(self) -> list[OptimizerProposal]:
        with self._connect() as conn:
            rows = conn.execute("SELECT body FROM proposals ORDER BY id").fetchall()
        return [OptimizerProposal.model_validate_json(r[0]) for r in rows]

    # --- settings and playbook versions ---------------------------------------------------
    def get_setting(self, key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return str(row[0]) if row else None

    def put_setting(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def put_playbook(self, version: str, body: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO playbooks (version, body) VALUES (?, ?) "
                "ON CONFLICT (version) DO UPDATE SET body = excluded.body",
                (version, body),
            )

    def get_playbook(self, version: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT body FROM playbooks WHERE version = ?", (version,)
            ).fetchone()
        return str(row[0]) if row else None

    def playbook_versions(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT version FROM playbooks").fetchall()
        return [str(r[0]) for r in rows]

    # --- change log ----------------------------------------------------------------------
    def last_change(self, user_id: str) -> Change | None:
        """The most recent change that affects this user's recommendation."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT seq, kind, ref, user_id FROM changes "
                "WHERE user_id = ? OR user_id IS NULL ORDER BY seq DESC LIMIT 1",
                (user_id,),
            ).fetchone()
        return Change(*row) if row else None


def make_store(env: Mapping[str, str] | None = None) -> Store:
    """The store for this process: Postgres if DATABASE_URL is set, else SQLite."""
    choice = select_backend(os.environ if env is None else env)
    return Store(choice.target, backend=choice.kind)


# --- demo seed (synthetic data only) -----------------------------------------------------------
SYNTHETIC_TEAM_PATH = REPO_ROOT / "data" / "synthetic_team.json"
SEED_EVENT_HOUR = 9  # seeded history events are placed at 09:mm on their October 2026 day
SEED_SCENARIO = "assistive"


def expand_history(user_id: str, history: list[dict[str, Any]]) -> list[Event]:
    """Turn the compact `history` of data/synthetic_team.json into contract Events."""
    events = []
    for index, item in enumerate(history, start=1):
        evidence = [
            {"skill_id": skill_id, "outcome": outcome, "help_level": help_level}
            for skill_id, outcome, help_level in item["evidence"]
        ]
        all_success = all(e["outcome"] == "success" for e in evidence)
        case_id = item["case"]
        events.append(
            Event.model_validate(
                {
                    "id": f"ev_{user_id.removeprefix('u_')}_{index:03d}",
                    "user_id": user_id,
                    "case_id": case_id,
                    "mode": "checkin" if case_id.startswith("checkin_") else "practice",
                    "scenario": SEED_SCENARIO,
                    "timestamp": (
                        f"2026-10-{item['day']:02d}T{SEED_EVENT_HOUR:02d}:{index:02d}:00+08:00"
                    ),
                    "help_level_max": max(e["help_level"] for e in evidence),
                    "user_decision": "correct" if all_success else "sign_off",
                    "decision_correct": all_success,
                    "skills_evidence": evidence,
                    "session_id": f"{user_id}_{item['session']}",
                    "companion_version": "playbook_v1",
                }
            )
        )
    return events


def seed_demo(
    store: Store,
    assumptions_v1: CompanyAssumptions,
    first_snapshot_id: str | None,
    team_path: Path = SYNTHETIC_TEAM_PATH,
) -> int:
    """Reset the store to the synthetic demo state; returns the number of people seeded.

    Only the first (oldest) snapshot is ingested, so the golden journey can replay the newer one.
    """
    store.clear()
    people = json.loads(team_path.read_text(encoding="utf-8"))["people"]
    for person in people:
        profile = Profile.model_validate(person["profile"])
        store.upsert_profile(profile)
        for event in expand_history(profile.id, person["history"]):
            store.add_event(event, log=False)
    store.put_assumptions(assumptions_v1, log=False)
    if first_snapshot_id:
        store.mark_snapshot_ingested(first_snapshot_id, log=False)
    return len(people)
