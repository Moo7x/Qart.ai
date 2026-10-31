"""Check that every course, video and article in the pack still opens (run before the pitch).

    python scripts/check_links.py

Prints each failing link with its status and exits with 1 when any fails. The scheduled pipeline
runs the same check and logs the result in its run history (src/pipeline/links.py).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline.links import catalogue_urls, check_urls, client  # noqa: E402


def main() -> None:
    items = catalogue_urls()
    with client() as http:
        failed = check_urls(items, http)
    broken = [f for f in failed if not f["blocked"]]
    blocked = [f for f in failed if f["blocked"]]
    for label, group in (
        ("BROKEN", broken),
        ("OPEN BY HAND (site refuses automated checks)", blocked),
    ):
        if group:
            print(label)
            for f in group:
                print(f"  {f['status']}\t{f['id']}\t{f['url']}")
    print(f"{len(items) - len(failed)} of {len(items)} links open, {len(broken)} broken")
    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
