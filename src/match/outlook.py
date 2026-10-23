"""Role demand outlook (PLAN §4.3 step 4): evidence about demand, kept separate from fit.

role → its ISCO-08 group (field.yaml, via the ESCO–O*NET crosswalk) → the MASCO major group whose
share of employees DOSM publishes, with the backtest that says whether the trend is projected;
the DOSM job-ad share where DOSM names the role's occupation; TalentCorp's in-demand skills among
the role's requirements; and whether MyCOL 2024/2025 lists the occupation as critical. Every item
restates its source. Nothing here changes the fit score.
"""

import re
from typing import Any

from src.collectors.mycol import CRITICAL_SERIES, PERSISTENT_SERIES
from src.collectors.mycol import load_extraction as load_mycol
from src.evidence.field import field_profile
from src.evidence.signals import Signal
from src.pack import DestinationRole, Pack

Row = dict[str, Any]
# ISCO-08 / MASCO 2020 major group (first digit) → the DOSM occupation group the signals follow.
MAJOR_GROUP = {"2": "professionals", "3": "technicians", "4": "clerical"}
DIRECTION_TEXT = {
    "rising": "rising",
    "weakening": "weakening",
    "stable": "stable",
    "insufficient": "not enough evidence for a direction yet",
    "expert": "expert view",
}


def _squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def role_outlook(
    pack: Pack, role: DestinationRole, rows: list[Row], signals: list[Signal]
) -> list[dict[str, str]]:
    by_id = {s.id: s for s in signals}
    occupation = field_profile().occupation(role.soc)
    items: list[dict[str, str]] = []
    if occupation and occupation.isco:
        group = MAJOR_GROUP.get(occupation.isco[0])
        signal = by_id.get(f"dosm_share_{group}") if group else None
        if signal:
            items.append(
                {
                    "kind": "observed",
                    "text": (
                        f"{signal.title} in Malaysia (the major group of ISCO-08 "
                        f"{occupation.isco}): {signal.headline}; "
                        f"{DIRECTION_TEXT[signal.direction]}. {signal.note}"
                    ),
                    "source": "DOSM, wages by occupation (OpenDOSM API)",
                }
            )
    if occupation:
        ads = by_id.get(f"dosm_jmi_{occupation.name.lower().replace(' ', '_')}")
        if ads:
            items.append(
                {
                    "kind": "observed",
                    "text": f"{ads.title}: {ads.headline}. {ads.note}",
                    "source": "DOSM Job Market Insights",
                }
            )
    in_demand = {
        _squash(r["entity"])
        for r in rows
        if r["source_id"] == "talentcorp_gbs_2024" and r["series"] == "talentcorp_in_demand_skill"
    }
    named = [
        pack.skills[r.skill].name
        for r in role.requires
        if _squash(pack.skills[r.skill].name) in in_demand
    ]
    if in_demand:
        items.append(
            {
                "kind": "expert",
                "text": (
                    f"TalentCorp names {len(named)} of this role's skills among its 16 in-demand "
                    f"skills{': ' + ', '.join(named) if named else ''}."
                ),
                "source": "TalentCorp (2024) GBS study, PDF p. 25",
            }
        )
    items += _mycol(rows, occupation.isco if occupation else None)
    return items


def _mycol(rows: list[Row], isco: str | None) -> list[dict[str, str]]:
    listed = {
        r["entity"]: r
        for r in rows
        if r["source_id"] == "mycol_2024_2025" and r["series"] == CRITICAL_SERIES
    }
    if not listed:
        return []  # not collected in this snapshot: say nothing rather than "not listed"
    persistent = {
        r["entity"]
        for r in rows
        if r["source_id"] == "mycol_2024_2025" and r["series"] == PERSISTENT_SERIES
    }
    name = load_mycol()["field_links"].get(isco or "")
    source = "MyCOL 2024/2025 (TalentCorp, Ministry of Human Resources), PDF p. 2"
    if name and name in listed:
        extra = " It has been listed in every edition since 2015." if name in persistent else ""
        text = f"MyCOL lists {name} as a critical (hard-to-fill) occupation in Malaysia.{extra}"
    else:
        text = f"This occupation is not among the {len(listed)} critical occupations in MyCOL."
    return [{"kind": "expert", "text": text, "source": source}]
