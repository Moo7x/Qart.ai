from src import params
from src.journey.store import SkillClaim
from src.match.engine import Evidence, score_role
from src.pack import load_pack
from src.pathway.planner import AiBasics, plan_pathway
from src.pathway.reskill import current_job_path, destination_path, mode_for, skill_pressure
from src.resources import load_resources

SOC = "43-3031.00"  # Bookkeeping, Accounting, and Auditing Clerks


def _task_rows(value: float) -> list[dict]:
    pack = load_pack()
    rows = []
    for soc, occupation in pack.tasks.occupations.items():
        for links in occupation.skills.values():
            for link in links:
                rows.append(
                    {
                        "soc": soc,
                        "task": str(link.task),
                        "observed": value,
                        "predicted": None,
                        "importance": 4.0,
                        "version_id": 1,
                    }
                )
    rows.append(
        {
            "soc": SOC,
            "task": "1",
            "observed": None,
            "predicted": value,
            "importance": 3.0,
            "version_id": 1,
        }
    )
    return rows


def test_mode_rules() -> None:
    high = params.INDUSTRY_USE_HIGH + 1
    assert mode_for("routine", high) == "oversee"
    assert mode_for("neutral", high) == "use_ai"
    assert mode_for("complement", 0.0) == "use_ai"
    assert mode_for("routine", 1.0) == "keep"
    assert mode_for("neutral", None) == "keep"


def test_pressure_falls_back_from_the_job_to_the_field_to_the_occupation() -> None:
    pack = load_pack()
    rows = _task_rows(60.0)
    linked = next(s for soc, o in pack.tasks.occupations.items() for s in o.skills)
    value, basis = skill_pressure(pack, SOC, linked, rows, 0.5)
    assert value == 30.0 and basis in {"observed", "observed_field"}
    value, basis = skill_pressure(pack, SOC, "cash_application", rows, 0.5)
    assert value == 30.0 and basis == "occupation"
    assert skill_pressure(pack, None, "cash_application", rows, 0.5) == (None, "none")


def test_without_a_destination_the_path_adapts_the_skills_the_person_has() -> None:
    pack, res = load_pack(), load_resources()
    claims = {"reconciliation": SkillClaim(level=2), "stakeholder_management": SkillClaim(level=2)}
    track, strengths = current_job_path(
        pack, res, SOC, claims, _task_rows(80.0), 0.5, 1, AiBasics(True, ""), []
    )
    modes = [n["mode"] for n in track["nodes"]]
    assert track["id"] == "path" and modes[0] == "basics"
    adapt = [n for n in track["nodes"] if n["mode"] != "basics"]
    assert {n["skill"] for n in adapt} | {s["skill"] for s in strengths} == set(claims)
    assert all(n["why"]["kind"] == "ai_trend" for n in adapt)


def test_with_a_destination_one_path_holds_adapt_and_learn_steps() -> None:
    pack, res = load_pack(), load_resources()
    role = pack.destination_roles["p2p_reporting_analyst"]
    claims = {r.skill: SkillClaim(level=5) for r in role.requires[:2]}
    evidence = Evidence(automation_share={}, automation_period="", automation_source="")
    match = score_role(pack, role, {k: c.level for k, c in claims.items()}, "moderate", evidence)
    path = plan_pathway(pack, match, claims, 6.0, "moderate", evidence, "working")
    track = destination_path(pack, res, match, path, [], [], SOC, claims, _task_rows(80.0), 0.5, 1)
    modes = {n["mode"] for n in track["nodes"]}
    assert track["id"] == "path" and "learn" in modes
    learned = {n["skill"] for n in track["nodes"] if n["mode"] == "learn"}
    assert not learned & set(claims)  # skills already met are adapted, not learned again
