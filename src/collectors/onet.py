"""O*NET database: the task statements and importance ratings behind the task crosswalk, and the
software employers ask for in each followed occupation (Technology Skills).

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
from typing import Any

import httpx

from src.collectors.base import CollectorResult, SourceState
from src.evidence.field import field_profile
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
# Technology Skills: the software examples O*NET lists per occupation, grouped by commodity
# (e.g. "Enterprise resource planning ERP software"). O*NET flags an example "Hot Technology" when
# it is often named in job postings, and "In Demand" when the postings for this occupation name it.
# Stored per occupation and commodity as one coded value (declared): 2 = an example is in demand
# for this occupation, 1 = an example is a hot technology, 0 = listed without either flag.
TECH_SERIES = "onet_technology"
TECH_UNIT = "employer demand in job postings (O*NET): 2 in demand, 1 hot technology, 0 listed"
TECH_FILE = "technology_skills.csv"
TECH_EXAMPLES_CITED = 5


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
    observations += _technology(archive, version, url)
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


def _technology(archive: zipfile.ZipFile, version: str, url: str) -> list[Observation]:
    """One row per followed occupation and software commodity; none if the release lacks it."""
    followed = {o.code for o in field_profile().soc_occupations}
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    try:
        handle = _member(archive, TECH_FILE)
    except StopIteration:
        return []
    with handle:
        for row in csv.DictReader(handle):
            soc = row["O*NET-SOC Code"]
            if soc not in followed:
                continue
            group = groups.setdefault(
                (soc, row["Commodity Code"]),
                {"title": row["Commodity Title"], "examples": [], "hot": False, "demand": False},
            )
            group["examples"].append(row["Example"])
            group["hot"] = group["hot"] or row.get("Hot Technology") == "Y"
            group["demand"] = group["demand"] or row.get("In Demand") == "Y"
    out = []
    for (soc, code), g in sorted(groups.items()):
        value = 2.0 if g["demand"] else 1.0 if g["hot"] else 0.0
        examples = "; ".join(g["examples"][:TECH_EXAMPLES_CITED])
        out.append(
            Observation(
                source_id=SOURCE_ID,
                series=TECH_SERIES,
                entity=f"{soc} {code}",
                geography="US",
                period=version,
                value=value,
                unit=TECH_UNIT,
                url=url,
                cited_span=f"O*NET {version} · {soc} · {g['title']}: {examples}",
                method_version=f"onet/{version}",
            )
        )
    return out


def collect(client: httpx.Client, state: SourceState) -> CollectorResult:
    found = latest_release(client)
    if found is None:
        return CollectorResult([], note="no CSV release found on the O*NET download page")
    major, minor = found
    version = f"{major}.{minor}"
    # A changed crosswalk must re-read the same release, so the linked tasks are part of the key.
    seen_key = f"{version}|tech|{','.join(sorted(load_pack().task_ids(), key=int))}"
    if state.get(STATE_KEY) == seen_key:
        return CollectorResult([], note=f"no new release since O*NET {version}")
    url = DOWNLOAD.format(major=major, minor=minor)
    response = client.get(url, follow_redirects=True)
    response.raise_for_status()
    observations, problems = parse_archive(response.content, version, url)
    state.set(STATE_KEY, seen_key)
    note = f"O*NET {version}: {len(observations)} linked tasks"
    return CollectorResult(observations, note=f"{note}; {problems}" if problems else note)
