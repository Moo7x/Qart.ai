"""Does the ranking reproduce the career moves TalentCorp lists? An external check of the score.

For each current role in roles.yaml, a synthetic person holds that role's typical skills at
VALIDATION_LEVEL ("working": handles the full task alone). The destination roles are ranked for
them, and the check asks whether the moves TalentCorp lists for that role (`transitions`, read
from the study, never an input to the score) appear in the top VALIDATION_TOP_K:

    hit rate = share of current roles with at least one listed move in the top K
    recall   = mean share of each role's listed moves found in the top K

TalentCorp's routes are expert judgement, not ground truth; agreement shows the skill-based score
lands where an independent expert view does. Run `python -m src.match.validation` for the live
numbers (with the forecast's outlook factor); the test checks the fit-only floor offline.
"""

from collections.abc import Callable, Sequence
from typing import Any

from src import params
from src.match.engine import Evidence, RoleMatch, rank_roles
from src.pack import Pack

Ranker = Callable[[Sequence[RoleMatch]], list[RoleMatch]]
NO_EVIDENCE = Evidence(automation_share={}, automation_period="", automation_source="")


def check(
    pack: Pack,
    evidence: Evidence = NO_EVIDENCE,
    reorder: Ranker | None = None,
    level: int = params.VALIDATION_LEVEL,
    top_k: int = params.VALIDATION_TOP_K,
) -> dict[str, Any]:
    per_role = []
    for role in pack.current_roles.values():
        listed = [t for t in role.transitions if t in pack.destination_roles]
        if not listed:
            continue
        ranked = rank_roles(pack, {s: level for s in role.typical_skills}, "moderate", evidence)
        if reorder is not None:
            ranked = reorder(ranked)
        top = [m.role_id for m in ranked[:top_k]]
        found = [t for t in listed if t in top]
        per_role.append({"role": role.id, "listed": listed, "top": top, "found": found})
    n = len(per_role)
    return {
        "roles": n,
        "hit_rate": round(sum(bool(r["found"]) for r in per_role) / n, 3) if n else 0.0,
        "recall": round(sum(len(r["found"]) / len(r["listed"]) for r in per_role) / n, 3)
        if n
        else 0.0,
        "top_k": top_k,
        "level": level,
        "per_role": per_role,
    }


def main() -> None:
    from src.config import load_settings
    from src.db import make_engine
    from src.envfile import load_env_file
    from src.evidence.store import query_observations
    from src.forecast import task_model
    from src.match import directions
    from src.match.evidence import automation_evidence
    from src.pack import load_pack

    load_env_file()
    engine = make_engine(load_settings().database_url)
    rows = query_observations(engine)
    _, task_rows = task_model.latest(engine)
    pack, evidence = load_pack(), automation_evidence(rows)
    forecasts = directions.forecasts(pack, rows, task_rows, "moderate")
    for label, result in (
        ("fit only", check(pack, evidence)),
        ("fit x outlook", check(pack, evidence, lambda m: directions.order(m, forecasts))),
    ):
        print(
            f"{label}: {result['hit_rate']:.0%} of {result['roles']} roles, recall "
            f"{result['recall']:.2f} (top {result['top_k']}, level {result['level']})"
        )
        for r in result["per_role"]:
            if not r["found"]:
                print(f"   miss: {r['role']} lists {r['listed']}, top {r['top']}")


if __name__ == "__main__":
    main()
