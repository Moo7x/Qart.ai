"""Publish person-specific proposals after ingestion, using the same pure comparison as replay."""

from sqlalchemy import Engine, select

from src.changes.engine import compare
from src.changes.store import baseline_cutoff, context_hash, save_change
from src.evidence.store import latest_observation_id, query_observations
from src.journey.store import ProfileData, profile_table
from src.match.engine import Scenario
from src.pack import load_pack


def refresh_proposals(
    engine: Engine,
    previous_cutoff: int,
    run_id: int | None = None,
    profile_id: str | None = None,
) -> None:
    """Internal enumeration only; there is no public endpoint listing people's profiles."""
    query = select(profile_table)
    if profile_id is not None:
        query = query.where(profile_table.c.id == profile_id)
    with engine.connect() as conn:
        profiles = list(conn.execute(query).mappings())
    latest = latest_observation_id(engine)
    after = query_observations(engine, through_id=latest)
    for row in profiles:
        before_cutoff = baseline_cutoff(engine, row["id"], previous_cutoff)
        if before_cutoff == latest:
            continue
        before = query_observations(engine, through_id=before_cutoff)
        profile = ProfileData.model_validate(row["data"])
        scenarios: tuple[Scenario, ...] = ("moderate", "fast")
        for scenario in scenarios:
            report = compare(
                load_pack(),
                profile,
                row["destination"],
                before,
                after,
                scenario,
                "live",
                "Your accepted evidence",
                "Latest collected evidence",
            )
            save_change(
                engine,
                {
                    "profile_id": row["id"],
                    "scenario": scenario,
                    "before_cutoff": before_cutoff,
                    "after_cutoff": latest,
                    "context_hash": context_hash(profile, row["destination"]),
                    "run_id": run_id,
                    "report": report.model_dump(mode="json"),
                },
            )
