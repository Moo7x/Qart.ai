"""Review Microsoft Learn course candidates: a person opens each one, then verifies or rejects it.

    python scripts/review_catalogue.py                   # list candidates still to review
    python scripts/review_catalogue.py --verify ID ...   # opened and fits: the planner may use it
    python scripts/review_catalogue.py --reject ID ...   # opened and does not fit: removed

Only verified entries are ever planned (src/pack.py `courses_for`). Verifying records today's date
as `checked`. Commit the changed data/packs/gbs_fa/courses_mslearn.yaml with the reviewer's name in
the message.
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.collectors.mslearn import OUT, write  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", nargs="+", default=[], metavar="ID")
    parser.add_argument("--reject", nargs="+", default=[], metavar="ID")
    args = parser.parse_args()
    data = yaml.safe_load(OUT.read_text(encoding="utf-8"))
    courses = data["courses"]
    known = {c["id"] for c in courses}
    unknown = [i for i in [*args.verify, *args.reject] if i not in known]
    if unknown:
        raise SystemExit(f"unknown ids: {', '.join(unknown)}")
    if not args.verify and not args.reject:
        todo = [c for c in courses if not c["verified"]]
        for c in todo:
            match = ", ".join(f"{k} {v}" for k, v in c.get("match", {}).items())
            print(f"{c['id']}\n  {c['title']} · {c['level']} · {c['minutes']} min · {match}")
            print(f"  {c['url']}")
        print(f"\n{len(todo)} to review, {len(courses) - len(todo)} verified")
        return
    today = f"{datetime.now(UTC):%Y-%m-%d}"
    for c in courses:
        if c["id"] in args.verify:
            c["verified"], c["checked"] = True, today
    data["courses"] = [c for c in courses if c["id"] not in args.reject]
    write(OUT, data)
    print(f"verified {len(args.verify)}, rejected {len(args.reject)}")


if __name__ == "__main__":
    main()
