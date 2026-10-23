"""Database access: one SQLAlchemy Core layer for SQLite (local) and Postgres (Replit).

Tables are declared on `metadata` by the modules that own them and created with `create_all`.
Persistence happens only through this module's engine, so every query runs the same way on both
databases.
"""

from pathlib import Path

from sqlalchemy import Engine, MetaData, create_engine, text
from sqlalchemy.engine import make_url

metadata = MetaData()


def make_engine(database_url: str) -> Engine:
    """Create the engine; for SQLite, create the parent folder so a fresh checkout just works."""
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite" and url.database and url.database != ":memory:":
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(database_url)


def init_db(engine: Engine) -> None:
    """Create every table declared on `metadata` that does not exist yet."""
    metadata.create_all(engine)


def ping(engine: Engine) -> bool:
    """True when the database answers a trivial query (health check)."""
    with engine.connect() as connection:
        return bool(connection.execute(text("SELECT 1")).scalar_one() == 1)
