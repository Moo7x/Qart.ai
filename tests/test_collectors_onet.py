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
    assert len(first.observations) == linked - 1
    assert all(o.period == "31.0" and o.geography == "US" for o in first.observations)
    assert "99-9999.00" not in {o.entity.split()[1] for o in first.observations}
    values = [o.value for o in first.observations]
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
