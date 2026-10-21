"""Retrieval corpus: verified courses + O*NET 31.0 task statements and detailed work activities.

Raw O*NET files (task_statements.csv, tasks_to_dwas.csv from the O*NET 31.0 database, CC BY 4.0)
live in gitignored data/raw/onet_31_0/. `build_onet_processed` keeps only the occupations our
roles are based on and writes a small committed file, data/processed/onet_tasks_dwas.json, with
source, URL and retrieval date.

Run:  python -m src.retrieval.corpus   (rebuilds the processed file from data/raw)
"""

import csv
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from src.engine.catalogue import REPO_ROOT, Catalogue, default_catalogue
from src.retrieval.models import Document

ONET_RAW_DIR = REPO_ROOT / "data" / "raw" / "onet_31_0"
ONET_PROCESSED_PATH = REPO_ROOT / "data" / "processed" / "onet_tasks_dwas.json"
ONET_SOURCE = "O*NET 31.0 Database (CC BY 4.0), U.S. Department of Labor/ETA"
ONET_DOWNLOAD_URL = "https://www.onetcenter.org/database.html"
ONET_SUMMARY_URL = "https://www.onetonline.org/link/summary/{code}"
ONET_RETRIEVED = "2026-10-21"
COURSE_LANGUAGE = "en"  # every catalogue course is in English (checked at retrieval)


def role_soc_codes(catalogue: Catalogue) -> list[str]:
    return sorted({b.code for role in catalogue.roles.values() for b in role.based_on})


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_onet_processed(
    raw_dir: Path = ONET_RAW_DIR,
    out_path: Path = ONET_PROCESSED_PATH,
    soc_codes: Iterable[str] | None = None,
    retrieved: str = ONET_RETRIEVED,
) -> dict[str, Any]:
    """Filter the raw O*NET task and task→DWA files to our occupations and write the result."""
    codes = set(soc_codes or role_soc_codes(default_catalogue()))
    tasks = [r for r in _read_csv(raw_dir / "task_statements.csv") if r["O*NET-SOC Code"] in codes]
    dwas: dict[str, list[dict[str, str]]] = {}
    for row in _read_csv(raw_dir / "tasks_to_dwas.csv"):
        if row["O*NET-SOC Code"] in codes:
            dwas.setdefault(row["Task ID"], []).append(
                {"id": row["DWA Element ID"], "name": row["DWA Element Name"]}
            )
    processed = {
        "source": ONET_SOURCE,
        "url": ONET_DOWNLOAD_URL,
        "files": ["task_statements.csv", "tasks_to_dwas.csv"],
        "retrieved": retrieved,
        "occupations": {r["O*NET-SOC Code"]: r["Title"] for r in tasks},
        "tasks": [
            {
                "task_id": r["Task ID"],
                "soc": r["O*NET-SOC Code"],
                "task": r["Task"],
                "task_type": r["Task Type"],
                "dwas": dwas.get(r["Task ID"], []),
            }
            for r in tasks
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(processed, ensure_ascii=False, indent=1) + "\n", "utf-8")
    return processed


def load_onet_processed(path: Path = ONET_PROCESSED_PATH) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def course_documents(catalogue: Catalogue) -> list[Document]:
    """Verified courses; the text adds the names and descriptions of the skills they cover."""
    documents = []
    for course in catalogue.courses.values():
        if not course.verified:
            continue
        skills = [catalogue.skills[k] for k in course.skills]
        skill_text = " ".join(f"{s.name}. {s.description}" for s in skills)
        documents.append(
            Document(
                id=course.id,
                kind="course",
                title=course.title,
                text=f"{course.provider}. {skill_text}",
                source=course.provider,
                url=course.url,
                date=course.retrieved,
                metadata={
                    "cost": course.cost,
                    "hours": float(course.hours),
                    "language": COURSE_LANGUAGE,
                    "skills": list(course.skills),
                },
            )
        )
    return documents


def onet_documents(processed: dict[str, Any]) -> list[Document]:
    """One document per task (task + its DWAs) and one per detailed work activity."""
    occupations: dict[str, str] = processed["occupations"]
    documents = []
    dwa_index: dict[str, tuple[str, list[str]]] = {}
    for task in processed["tasks"]:
        soc, names = task["soc"], [d["name"] for d in task["dwas"]]
        documents.append(
            Document(
                id=f"onet_task_{task['task_id']}",
                kind="onet_task",
                title=task["task"],
                text=f"{occupations[soc]}. {' '.join(names)}",
                source=f"{ONET_SOURCE}, {soc} {occupations[soc]}",
                url=ONET_SUMMARY_URL.format(code=soc),
                date=processed["retrieved"],
                metadata={"soc": soc, "task_type": task["task_type"]},
            )
        )
        for dwa in task["dwas"]:
            entry = dwa_index.setdefault(dwa["id"], (dwa["name"], []))
            if occupations[soc] not in entry[1]:
                entry[1].append(occupations[soc])
    for dwa_id, (name, titles) in sorted(dwa_index.items()):
        documents.append(
            Document(
                id=f"onet_dwa_{dwa_id}",
                kind="onet_dwa",
                title=name,
                text=f"Detailed work activity of: {', '.join(titles)}",
                source=ONET_SOURCE,
                url=ONET_DOWNLOAD_URL,
                date=processed["retrieved"],
            )
        )
    return documents


def build_corpus(
    catalogue: Catalogue | None = None, onet_path: Path = ONET_PROCESSED_PATH
) -> list[Document]:
    """Courses + O*NET documents. Course candidates (e.g. Microsoft Learn) are not included."""
    cat = catalogue or default_catalogue()
    return course_documents(cat) + onet_documents(load_onet_processed(onet_path))


if __name__ == "__main__":
    result = build_onet_processed()
    print(f"wrote {ONET_PROCESSED_PATH}: {len(result['tasks'])} tasks")
