"""Review course candidates the automatic fit check left open: a person opens each, then decides.

    python scripts/review_catalogue.py                   # list candidates still to review
    python scripts/review_catalogue.py --verify ID ...   # opened and fits: the planner may use it
    python scripts/review_catalogue.py --reject ID ...   # opened and does not fit: removed

Only verified entries are ever planned (src/pack.py `courses_for`). Verifying records today's date
as `checked` and the fit check as done by a person. Candidates live in the files of
src/collectors/course_check.py CANDIDATE_FILES; commit the changed files with the reviewer's name
in the message.
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.collectors.course_check import CANDIDATE_FILES  # noqa: E402
from src.evidence.field import PACK_DIR  # noqa: E402


def _load(path: Path) -> tuple[str, dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    header = "".join(line + "\n" for line in text.splitlines() if line.startswith("#"))
    return header, yaml.safe_load(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", nargs="+", default=[], metavar="ID")
    parser.add_argument("--reject", nargs="+", default=[], metavar="ID")
    args = parser.parse_args()
    files = {PACK_DIR / name: _load(PACK_DIR / name) for name in CANDIDATE_FILES}
    known = {c["id"] for _, data in files.values() for c in data["courses"]}
    unknown = [i for i in [*args.verify, *args.reject] if i not in known]
    if unknown:
        raise SystemExit(f"unknown ids: {', '.join(unknown)}")
    if not args.verify and not args.reject:
        todo = [c for _, data in files.values() for c in data["courses"] if not c["verified"]]
        for c in todo:
            result = (c.get("fit_check") or {}).get("result", "not checked")
            print(f"{c['id']}\n  {c['title']} · {', '.join(c['covers'])} · automatic: {result}")
            print(f"  {c['url']}")
        print(f"\n{len(todo)} to review")
        return
    today = f"{datetime.now(UTC):%Y-%m-%d}"
    for path, (header, data) in files.items():
        for c in data["courses"]:
            if c["id"] in args.verify:
                c["verified"], c["checked"] = True, today
                c["fit_check"] = {"result": "fits", "by": "person", "quote": "", "checked": today}
        data["courses"] = [c for c in data["courses"] if c["id"] not in args.reject]
        path.write_text(
            header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
    print(f"verified {len(args.verify)}, rejected {len(args.reject)}")


if __name__ == "__main__":
    main()
