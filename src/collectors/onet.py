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
# Release 31.0 renamed Technology Skills to Software Skills; retain the older archive name.
TECH_FILES = ("software_skills.csv", "technology_skills.csv")
# Related Occupations: for each occupation, the 20 occupations O*NET's analysts judged most related,
# in three tiers. Stored per followed occupation as the tier code (declared): 1 = Primary-Short
# (the top 5), 2 = Primary-Long (6th-10th), 3 = Supplemental (11th-20th). Used to check that a
# suggested move between jobs is one O*NET itself considers close.
RELATED_SERIES = "onet_related_occupation"
RELATED_UNIT = "relatedness tier (O*NET expert review): 1 top 5, 2 6th-10th, 3 11th-20th"
RELATED_FILE = "related_occupations.csv"
RELATED_TIER = {"Primary-Short": 1.0, "Primary-Long": 2.0, "Supplemental": 3.0}
# Emerging Tasks: task statements that workers wrote in and O*NET analysts accepted as new or as a
# revision of an existing task. Stored as 1 = new task, 0 = revision (declared coding).
EMERGING_SERIES = "onet_emerging_task"
EMERGING_UNIT = "1 = new task, 0 = revision of an existing task (worker write-ins, O*NET review)"
EMERGING_FILE = "emerging_tasks.csv"
# Every task statement of the followed occupations, with its importance where rated: the tasks the
# task-level AI-use model predicts for (src/forecast/task_model.py), not only the linked ones.
STATEMENT_SERIES = "onet_task_statement"
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
    observations += _statements(archive, version, url)
    observations += _related(archive, version, url)
    observations += _emerging(archive, version, url)
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


def _optional(archive: zipfile.ZipFile, name: str) -> io.TextIOWrapper | None:
    """A file that older releases may lack; None when it is not in the archive."""
    try:
        return _member(archive, name)
    except StopIteration:
        return None


def _statements(archive: zipfile.ZipFile, version: str, url: str) -> list[Observation]:
    """All task statements of the followed occupations, each with its importance where rated."""
    followed = field_profile().soc_codes()
    rows: dict[tuple[str, str], dict[str, str]] = {}
    with _member(archive, "task_statements.csv") as handle:
        for row in csv.DictReader(handle):
            if row["O*NET-SOC Code"] in followed:
                rows[(row["O*NET-SOC Code"], row["Task ID"])] = row
    importance: dict[tuple[str, str], str] = {}
    with _member(archive, "task_ratings.csv") as handle:
        for row in csv.DictReader(handle):
            key = (row["O*NET-SOC Code"], row["Task ID"])
            if key in rows and row["Scale ID"] == IMPORTANCE_SCALE:
                importance[key] = row["Data Value"]
    return [
        Observation(
            source_id=SOURCE_ID,
            series=STATEMENT_SERIES,
            entity=f"{task} {soc}",
            geography="US",
            period=version,
            value=float(importance[(soc, task)]) if (soc, task) in importance else None,
            unit=UNIT,
            url=url,
            cited_span=(
                f"O*NET {version} · {soc} {row['Title']} · task {task} ({row['Task Type']}): "
                f"{row['Task']}"
            ),
            method_version=f"onet/{version}",
        )
        for (soc, task), row in sorted(rows.items())
    ]


def _related(archive: zipfile.ZipFile, version: str, url: str) -> list[Observation]:
    """The occupations O*NET relates to each followed occupation, with the relatedness tier."""
    handle = _optional(archive, RELATED_FILE)
    if handle is None:
        return []
    followed = field_profile().soc_codes()
    out = []
    with handle:
        for row in csv.DictReader(handle):
            soc, related = row["O*NET-SOC Code"], row["Related O*NET-SOC Code"]
            tier = RELATED_TIER.get(row["Relatedness Tier"])
            if soc not in followed or tier is None:
                continue
            out.append(
                Observation(
                    source_id=SOURCE_ID,
                    series=RELATED_SERIES,
                    entity=f"{soc} {related}",
                    geography="US",
                    period=version,
                    value=tier,
                    unit=RELATED_UNIT,
                    url=url,
                    cited_span=(
                        f"O*NET {version} · {soc} {row['Title']} → {related} "
                        f"{row['Related Title']} · {row['Relatedness Tier']} #{row['Index']}"
                    ),
                    method_version=f"onet/{version}",
                )
            )
    return out


def _emerging(archive: zipfile.ZipFile, version: str, url: str) -> list[Observation]:
    """New and revised task statements O*NET accepted for the followed occupations."""
    handle = _optional(archive, EMERGING_FILE)
    if handle is None:
        return []
    followed = field_profile().soc_codes()
    out = []
    with handle:
        for n, row in enumerate(csv.DictReader(handle)):
            soc = row["O*NET-SOC Code"]
            if soc not in followed:
                continue
            out.append(
                Observation(
                    source_id=SOURCE_ID,
                    series=EMERGING_SERIES,
                    entity=f"{soc} {n}",
                    geography="US",
                    period=version,
                    value=1.0 if row["Category"] == "New" else 0.0,
                    unit=EMERGING_UNIT,
                    url=url,
                    cited_span=(
                        f"O*NET {version} · {soc} {row['Title']} · {row['Category']} task "
                        f"({row['Date']}): {row['Task']}"
                    ),
                    method_version=f"onet/{version}",
                )
            )
    return out


def _technology(archive: zipfile.ZipFile, version: str, url: str) -> list[Observation]:
    """One row per followed occupation and software commodity; none if the release lacks it."""
    followed = {o.code for o in field_profile().soc_occupations}
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    handle = None
    for name in TECH_FILES:
        try:
            handle = _member(archive, name)
            break
        except StopIteration:
            continue
    if handle is None:
        return []
    with handle:
        reader = csv.DictReader(handle)
        # 31.0 replaced UNSPSC commodity columns with O*NET software elements, and renamed
        # Example to Workplace Example. Keep the original source's category id and exact name.
        software_elements = "Element ID" in (reader.fieldnames or [])
        code_column = "Element ID" if software_elements else "Commodity Code"
        title_column = "Element Name" if software_elements else "Commodity Title"
        example_column = "Workplace Example" if software_elements else "Example"
        for row in reader:
            soc = row["O*NET-SOC Code"]
            if soc not in followed:
                continue
            group = groups.setdefault(
                (soc, row[code_column]),
                {"title": row[title_column], "examples": [], "hot": False, "demand": False},
            )
            group["examples"].append(row[example_column])
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


EXTRA_SERIES = (TECH_SERIES, STATEMENT_SERIES, RELATED_SERIES, EMERGING_SERIES)


def collect(client: httpx.Client, state: SourceState) -> CollectorResult:
    found = latest_release(client)
    if found is None:
        return CollectorResult([], note="no CSV release found on the O*NET download page")
    major, minor = found
    version = f"{major}.{minor}"
    # A changed crosswalk must re-read the same release, so the linked tasks are part of the key.
    linked = ",".join(sorted(load_pack().task_ids(), key=int))
    seen_key = f"{version}|software-v1|related-emerging-statements|{linked}"
    if state.get(STATE_KEY) == seen_key:
        return CollectorResult([], note=f"no new release since O*NET {version}")
    url = DOWNLOAD.format(major=major, minor=minor)
    response = client.get(url, follow_redirects=True)
    response.raise_for_status()
    observations, problems = parse_archive(response.content, version, url)
    state.set(STATE_KEY, seen_key)
    count = {s: sum(row.series == s for row in observations) for s in EXTRA_SERIES}
    note = (
        f"O*NET {version}: {len(observations) - sum(count.values())} linked tasks, "
        f"{count[TECH_SERIES]} software categories, {count[STATEMENT_SERIES]} task statements, "
        f"{count[RELATED_SERIES]} related occupations, {count[EMERGING_SERIES]} emerging tasks"
    )
    return CollectorResult(observations, note=f"{note}; {problems}" if problems else note)
