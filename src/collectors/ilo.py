"""ILO GenAI exposure index (Working Paper 140, 2025): potential exposure of field occupations.

The score file (one row per ISCO-08 task, 0 = current GenAI cannot do the task, 1 = it could do all
of it) is read from the authors' CC BY 4.0 repository. We keep, for the ISCO-08 groups the field
profile links to (data/packs/gbs_fa/field.yaml), the occupation's mean task score with the ILO's
exposure gradient, and each task's score. Exposure is technical potential, not a forecast of job
loss or adoption. The file is re-read only when its content (git blob sha) changes.

The .xlsx file is read with the standard library: it is a zip of XML parts, and only the shared
strings and the first worksheet are needed.
"""

import io
import re
import zipfile
from xml.etree import ElementTree

import httpx

from src.collectors.base import CollectorResult, SourceState
from src.evidence.field import field_profile
from src.evidence.store import Observation

SOURCE_ID = "ilo_genai_exposure_2025"
FILE = "Final_Scores_ISCO08_Gmyrek_et_al_2025.xlsx"
META = f"https://api.github.com/repos/pgmyrek/2025_GenAI_scores_ISCO08/contents/{FILE}"
STATE_KEY = "file"
METHOD_VERSION = "ilo/wp140-2025"
PUBLISHED = "2025-05-20"  # ILO Working Paper 140 publication date
OCCUPATION_SERIES = "ilo_occupation_exposure"
TASK_SERIES = "ilo_task_exposure"
SCORE_UNIT = "GenAI exposure score (0 = cannot, 1 = could do the task entirely)"
CITATION = "Gmyrek et al. (2025), ILO Working Paper 140"
# The gradient is written into the occupation's cited span as "· gradient: <label>".
GRADIENT = re.compile(r"· gradient: (.+)$")
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
COLUMN = re.compile(r"[A-Z]+")


def gradient_of(cited_span: str) -> str | None:
    match = GRADIENT.search(cited_span)
    return match.group(1) if match else None


def _column_index(ref: str) -> int:
    letters = COLUMN.match(ref)
    assert letters is not None
    index = 0
    for ch in letters.group(0):
        index = index * 26 + ord(ch) - 64
    return index - 1


def read_rows(data: bytes) -> list[dict[str, str]]:
    """First worksheet of an .xlsx file as dicts keyed by the header row (all values as text)."""
    archive = zipfile.ZipFile(io.BytesIO(data))
    strings = [
        "".join(t.text or "" for t in item.iter(f"{{{NS['m']}}}t"))
        for item in ElementTree.fromstring(archive.read("xl/sharedStrings.xml")).findall("m:si", NS)
    ]
    sheet = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    table: list[list[str]] = []
    for row in sheet.iterfind("m:sheetData/m:row", NS):
        values: list[str] = []
        for cell in row.iterfind("m:c", NS):
            index = _column_index(cell.get("r", "A1"))
            values += [""] * (index + 1 - len(values))
            raw = cell.find("m:v", NS)
            text = raw.text or "" if raw is not None else ""
            if cell.get("t") == "s" and text:
                text = strings[int(text)]
            elif cell.get("t") == "inlineStr":
                text = "".join(t.text or "" for t in cell.iter(f"{{{NS['m']}}}t"))
            values[index] = text
        table.append(values)
    header = table[0]
    return [dict(zip(header, r + [""] * (len(header) - len(r)), strict=True)) for r in table[1:]]


def _number(text: str) -> float | None:
    return float(text) if text not in ("", None) else None


def parse_scores(data: bytes, url: str) -> list[Observation]:
    observations = []
    seen: set[str] = set()
    for row in read_rows(data):
        isco = row["ISCO_08"].strip()
        if not isco:
            continue  # every ISCO-08 group is kept; field screens filter to the field's groups
        if isco not in seen:
            seen.add(isco)
            observations.append(
                Observation(
                    source_id=SOURCE_ID,
                    series=OCCUPATION_SERIES,
                    entity=f"{isco} {row['Title']}",
                    geography="GLOBAL",
                    period="2025",
                    value=_number(row["mean_score_2025"]),
                    unit="mean " + SCORE_UNIT + " of the occupation's tasks",
                    url=url,
                    cited_span=(
                        f"{CITATION} · ISCO-08 {isco} {row['Title']} · mean task score "
                        f"{row['mean_score_2025']} (SD {row['SD_2025']}) · gradient: "
                        f"{row['potential25']}"
                    ),
                    method_version=METHOD_VERSION,
                    published=PUBLISHED,
                )
            )
        observations.append(
            Observation(
                source_id=SOURCE_ID,
                series=TASK_SERIES,
                entity=f"{isco}.{row['taskID']} {row['Task_ISCO'].strip()}",
                geography="GLOBAL",
                period="2025",
                value=_number(row["score_2025"]),
                unit=SCORE_UNIT,
                url=url,
                cited_span=(
                    f"{CITATION} · ISCO-08 {isco} task {row['taskID']}: "
                    f"{row['Task_ISCO'].strip()} · score {row['score_2025']} ({row['source']})"
                ),
                method_version=METHOD_VERSION,
                published=PUBLISHED,
            )
        )
    return observations


def collect(client: httpx.Client, state: SourceState) -> CollectorResult:
    meta = client.get(META, headers={"Accept": "application/vnd.github+json"})
    meta.raise_for_status()
    info = meta.json()
    seen_key = f"{info['sha']}|all-groups"
    if state.get(STATE_KEY) == seen_key:
        return CollectorResult([], note="score file unchanged since last read")
    response = client.get(info["download_url"], follow_redirects=True)
    response.raise_for_status()
    observations = parse_scores(response.content, info["html_url"])
    groups = sum(o.series == OCCUPATION_SERIES for o in observations)
    missing = field_profile().isco_codes() - {o.entity.split()[0] for o in observations}
    note = f"{groups} ISCO-08 occupations, {len(observations) - groups} tasks"
    if missing:
        note += f"; not in the file: {', '.join(sorted(missing))}"
    state.set(STATE_KEY, seen_key)
    return CollectorResult(observations, note=note)
