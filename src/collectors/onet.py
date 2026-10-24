"""O*NET database: the task statements and importance ratings behind the task crosswalk.

The newest database release is found on the O*NET download page; its CSV archive (about 16 MB) is
read in memory and only the tasks linked in data/packs/gbs_fa/tasks.yaml are kept, each with its
importance rating (IM scale, 1–5) and verbatim wording. A release already read is not downloaded
again. Linked tasks missing from a new release, or reworded in it, are named in the run note so
the crosswalk can be reviewed; they are never silently relinked.
"""

import csv
import io
import re
import zipfile

import httpx

from src.collectors.base import CollectorResult, SourceState
from src.evidence.store import Observation
from src.pack import load_pack

SOURCE_ID = "onet_database"
DATABASE_PAGE = "https://www.onetcenter.org/database.html"
DOWNLOAD = "https://www.onetcenter.org/dl_files/database/db_{major}_{minor}_csv.zip"
RELEASE = re.compile(r"db_(\d+)_(\d+)_csv\.zip")
STATE_KEY = "release"
SERIES = "onet_task_importance"
UNIT = "importance (O*NET IM scale, 1–5)"
IMPORTANCE_SCALE = "IM"


def latest_release(client: httpx.Client) -> tuple[int, int] | None:
    """(major, minor) of the newest CSV release linked from the download page."""
    page = client.get(DATABASE_PAGE)
    page.raise_for_status()
    found = {(int(a), int(b)) for a, b in RELEASE.findall(page.text)}
    return max(found) if found else None


def _member(archive: zipfile.ZipFile, name: str) -> io.TextIOWrapper:
    path = next(n for n in archive.namelist() if n.endswith(f"/{name}") or n == name)
    return io.TextIOWrapper(archive.open(path), encoding="utf-8")


def parse_archive(data: bytes, version: str, url: str) -> tuple[list[Observation], str]:
    """Observations for the linked tasks, and a note on links this release does not support."""
    pack = load_pack()
    wanted = {
        (soc, str(link.task)): link.text
        for soc, occupation in pack.tasks.occupations.items()
        for links in occupation.skills.values()
        for link in links
    }
    archive = zipfile.ZipFile(io.BytesIO(data))
    statements: dict[tuple[str, str], dict[str, str]] = {}
    with _member(archive, "task_statements.csv") as handle:
        for row in csv.DictReader(handle):
            key = (row["O*NET-SOC Code"], row["Task ID"])
            if key in wanted:
                statements[key] = row
    ratings: dict[tuple[str, str], dict[str, str]] = {}
    with _member(archive, "task_ratings.csv") as handle:
        for row in csv.DictReader(handle):
            key = (row["O*NET-SOC Code"], row["Task ID"])
            if key in statements and row["Scale ID"] == IMPORTANCE_SCALE:
                ratings[key] = row
    observations = []
    for (soc, task), row in sorted(statements.items()):
        rating = ratings.get((soc, task))
        value = float(rating["Data Value"]) if rating else None  # missing stays missing
        observations.append(
            Observation(
                source_id=SOURCE_ID,
                series=SERIES,
                entity=f"{task} {soc}",
                geography="US",
                period=version,
                value=value,
                unit=UNIT,
                url=url,
                cited_span=(
                    f"O*NET {version} · {soc} {row['Title']} · task {task} ({row['Task Type']}): "
                    f"{row['Task']} · importance {rating['Data Value'] if rating else 'not rated'}"
                    f"{' (' + rating['Date'] + ')' if rating else ''}"
                ),
                method_version=f"onet/{version}",
            )
        )
    missing = sorted(task for (soc, task) in wanted if (soc, task) not in statements)
    reworded = sorted(
        key[1]
        for key, text in wanted.items()
        if key in statements and statements[key]["Task"] != text
    )
    notes = []
    if missing:
        notes.append(f"linked tasks not in this release: {', '.join(missing)}")
    if reworded:
        notes.append(f"linked tasks reworded in this release: {', '.join(reworded)}")
    return observations, "; ".join(notes)


def collect(client: httpx.Client, state: SourceState) -> CollectorResult:
    found = latest_release(client)
    if found is None:
        return CollectorResult([], note="no CSV release found on the O*NET download page")
    major, minor = found
    version = f"{major}.{minor}"
    # A changed crosswalk must re-read the same release, so the linked tasks are part of the key.
    seen_key = f"{version}|{','.join(sorted(load_pack().task_ids(), key=int))}"
    if state.get(STATE_KEY) == seen_key:
        return CollectorResult([], note=f"no new release since O*NET {version}")
    url = DOWNLOAD.format(major=major, minor=minor)
    response = client.get(url, follow_redirects=True)
    response.raise_for_status()
    observations, problems = parse_archive(response.content, version, url)
    state.set(STATE_KEY, seen_key)
    note = f"O*NET {version}: {len(observations)} linked tasks"
    return CollectorResult(observations, note=f"{note}; {problems}" if problems else note)
