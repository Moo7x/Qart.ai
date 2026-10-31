"""O*NET collector keeps only linked tasks, reads a release once and reports broken links."""

import csv
import io
import zipfile

import httpx

from src.collectors import onet
from src.collectors.base import MemoryState
from src.pack import load_pack

PAGE = '<a href="/dl_files/database/db_30_2_csv.zip">30.2</a> <a href="db_31_0_csv.zip">31.0</a>'


def archive(reword: bool = False) -> bytes:
    """A tiny CSV release: every linked task except one, plus one unlinked task."""
    pack = load_pack()
    links = [
        (soc, link)
        for soc, occ in pack.tasks.occupations.items()
        for ls in occ.skills.values()
        for link in ls
    ]
    unique = {(soc, link.task): link.text for soc, link in links}
    kept = sorted(unique)[1:]  # drop the first linked task to test the "missing" note
    statements = io.StringIO()
    writer = csv.writer(statements)
    writer.writerow(["O*NET-SOC Code", "Title", "Task ID", "Task", "Task Type"])
    for i, (soc, task) in enumerate(kept):
        text = "Reworded task." if reword and i == 0 else unique[(soc, task)]
        writer.writerow([soc, "Occupation", task, text, "Core"])
    writer.writerow(["99-9999.00", "Unrelated", 1, "Not linked.", "Core"])
    ratings = io.StringIO()
    writer = csv.writer(ratings)
    writer.writerow(["O*NET-SOC Code", "Task ID", "Scale ID", "Data Value", "Date"])
    for soc, task in kept[1:]:  # the first kept task has no rating: missing stays missing
        writer.writerow([soc, task, "IM", "4.20", "08/2023"])
        writer.writerow([soc, task, "RT", "80.0", "08/2023"])
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("db_31_0_csv/task_statements.csv", statements.getvalue())
        z.writestr("db_31_0_csv/task_ratings.csv", ratings.getvalue())
    return out.getvalue()


def fake_onet(downloads: list[str], data: bytes) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/database.html":
            return httpx.Response(200, text=PAGE)
        if request.url.path.endswith("db_31_0_csv.zip"):
            downloads.append(request.url.path)
            return httpx.Response(200, content=data)
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_collect_keeps_linked_tasks_with_importance_once() -> None:
    downloads: list[str] = []
    state = MemoryState()
    with httpx.Client(transport=fake_onet(downloads, archive())) as client:
        first = onet.collect(client, state)
        second = onet.collect(client, state)
    linked = len({(s, t) for s, t in _linked()})
    tasks = [o for o in first.observations if o.series == onet.SERIES]
    assert len(tasks) == linked - 1
    assert all(o.period == "31.0" and o.geography == "US" for o in first.observations)
    assert "99-9999.00" not in {o.entity.split()[1] for o in tasks}
    values = [o.value for o in tasks]
    assert values.count(None) == 1 and 4.2 in values  # an unrated task is missing, not zero
    assert "linked tasks not in this release" in first.note
    assert second.observations == [] and second.note == "no new release since O*NET 31.0"
    assert len(downloads) == 1


def test_reworded_tasks_are_named_for_review() -> None:
    with httpx.Client(transport=fake_onet([], archive(reword=True))) as client:
        result = onet.collect(client, MemoryState())
    assert "linked tasks reworded in this release" in result.note


def _linked() -> list[tuple[str, int]]:
    pack = load_pack()
    return [
        (soc, link.task)
        for soc, occ in pack.tasks.occupations.items()
        for links in occ.skills.values()
        for link in links
    ]


def test_technology_skills_are_kept_per_followed_occupation_with_demand_flags() -> None:
    import csv
    import io

    from src.collectors.onet import TECH_SERIES, parse_archive

    rows = [
        ("15-2051.01", "SAP", "43232203", "Enterprise resource planning ERP software", "Y", "Y"),
        ("15-2051.01", "Oracle", "43232203", "Enterprise resource planning ERP software", "Y", "N"),
        (
            "15-2051.01",
            "Tableau",
            "43232314",
            "Business intelligence and data analysis software",
            "Y",
            "N",
        ),
        ("29-1141.00", "Epic", "43231507", "Medical software", "Y", "Y"),  # not followed
    ]
    tech = io.StringIO()
    writer = csv.writer(tech)
    writer.writerow(
        [
            "O*NET-SOC Code",
            "Example",
            "Commodity Code",
            "Commodity Title",
            "Hot Technology",
            "In Demand",
        ]
    )
    writer.writerows(rows)
    base = zipfile.ZipFile(io.BytesIO(archive()))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name in base.namelist():
            z.writestr(name, base.read(name))
        z.writestr("db_31_0_csv/technology_skills.csv", tech.getvalue())
    observations, _ = parse_archive(out.getvalue(), "31.0", "https://example.org/db.zip")
    tech_rows = {o.entity: o for o in observations if o.series == TECH_SERIES}
    assert set(tech_rows) == {"15-2051.01 43232203", "15-2051.01 43232314"}
    assert tech_rows["15-2051.01 43232203"].value == 2.0  # in demand for this occupation
    assert tech_rows["15-2051.01 43232314"].value == 1.0  # hot technology only
    assert "SAP; Oracle" in tech_rows["15-2051.01 43232203"].cited_span


def _with(files: dict[str, str]) -> bytes:
    base = zipfile.ZipFile(io.BytesIO(archive()))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name in base.namelist():
            z.writestr(name, base.read(name))
        for name, text in files.items():
            z.writestr(f"db_31_0_csv/{name}", text)
    return out.getvalue()


def _csv(header: list[str], rows: list[list[str]]) -> str:
    text = io.StringIO()
    writer = csv.writer(text)
    writer.writerow(header)
    writer.writerows(rows)
    return text.getvalue()


def test_related_occupations_and_emerging_tasks_are_kept_for_followed_occupations() -> None:
    related = _csv(
        [
            "O*NET-SOC Code",
            "Title",
            "Related O*NET-SOC Code",
            "Related Title",
            "Relatedness Tier",
            "Index",
        ],
        [
            [
                "13-2011.00",
                "Accountants and Auditors",
                "13-2031.00",
                "Budget Analysts",
                "Primary-Short",
                "1",
            ],
            [
                "13-2011.00",
                "Accountants and Auditors",
                "43-3031.00",
                "Bookkeeping Clerks",
                "Supplemental",
                "14",
            ],
            [
                "99-9999.00",
                "Not followed",
                "13-2011.00",
                "Accountants and Auditors",
                "Primary-Short",
                "1",
            ],
        ],
    )
    emerging = _csv(
        [
            "O*NET-SOC Code",
            "Title",
            "Task",
            "Category",
            "Original Task ID",
            "Original Task",
            "Date",
            "Domain Source",
        ],
        [
            [
                "13-2011.00",
                "Accountants and Auditors",
                "Review AI-generated reconciliations.",
                "New",
                "",
                "",
                "08/2026",
                "Incumbent",
            ],
            [
                "99-9999.00",
                "Not followed",
                "Something else.",
                "New",
                "",
                "",
                "08/2026",
                "Incumbent",
            ],
        ],
    )
    observations, _ = onet.parse_archive(
        _with({"related_occupations.csv": related, "emerging_tasks.csv": emerging}),
        "31.0",
        "https://example.org/db.zip",
    )
    links = {o.entity: o.value for o in observations if o.series == onet.RELATED_SERIES}
    assert links == {"13-2011.00 13-2031.00": 1.0, "13-2011.00 43-3031.00": 3.0}
    new = [o for o in observations if o.series == onet.EMERGING_SERIES]
    assert len(new) == 1 and new[0].value == 1.0
    assert "Review AI-generated reconciliations." in new[0].cited_span


def test_task_statements_cover_every_task_of_the_followed_occupations() -> None:
    observations, _ = onet.parse_archive(archive(), "31.0", "https://example.org/db.zip")
    statements = [o for o in observations if o.series == onet.STATEMENT_SERIES]
    assert statements and all(o.entity.split()[1] != "99-9999.00" for o in statements)
    assert all(o.unit == onet.UNIT for o in statements)
