"""Report (and, for skills marked learn_hours_source "derived", apply) learn_hours from the
median hours of verified courses. Usage: python scripts/derive_learn_hours.py [--write]"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.engine.catalogue import default_catalogue  # noqa: E402
from src.engine.learn_hours import derived_hours  # noqa: E402

SKILLS_PATH = ROOT / "catalogue" / "skills.json"
STEPS = ("to_basic", "to_confident")


def cell(current: float, from_courses: float | None) -> str:
    """'15' or '15 (courses 12)' when verified courses give a median for this step."""
    return f"{current:g}" if from_courses is None else f"{current:g} (courses {from_courses:g})"


def main(write: bool) -> None:
    cat = default_catalogue()
    derived = derived_hours(cat.vocabulary, cat.courses.values())
    raw = json.loads(SKILLS_PATH.read_text(encoding="utf-8"))
    changed = 0
    print(f"{'skill':28} {'source':9} {'to_basic':>18} {'to_confident':>18}")
    for s in raw["skills"]:
        d, lh = derived[s["id"]], s["learn_hours"]
        cells = [cell(lh[k], d[k]) for k in STEPS]
        print(f"{s['id']:28} {s['learn_hours_source']:9} {cells[0]:>18} {cells[1]:>18}")
        if s["learn_hours_source"] != "derived":
            continue
        for key in STEPS:
            if d[key] is not None and d[key] != lh[key]:
                lh[key] = d[key]
                changed += 1
    if write and changed:
        SKILLS_PATH.write_text(
            json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    action = "written" if write else "would change (run with --write)"
    print(f"\n{changed} value(s) {action}; hand-set 'estimate' values are never overwritten.")


if __name__ == "__main__":
    main("--write" in sys.argv)
