"""ILO exposure collector keeps the field's ISCO-08 groups, with the published gradient."""

import io
import zipfile
from xml.sax.saxutils import escape

import httpx

from src.collectors import ilo
from src.collectors.base import MemoryState

HEADER = ["ISCO_08", "Title", "taskID", "Task_ISCO", "score_2025", "source"]
HEADER += ["mean_score_2025", "SD_2025", "potential25"]
ROWS = [
    ["2411", "Accountants", "1", "Preparing financial statements;", "0.65", "predicted"],
    ["2411", "Accountants", "2", "Advising on taxation;", "0.465", "reconciled"],
    ["9999", "Not in the field", "1", "Anything;", "0.9", "predicted"],
]
SUMMARY = {"2411": ["0.51", "0.08", "Exposed: Gradient 3"], "9999": ["0.9", "0", "x"]}


def xlsx() -> bytes:
    """A minimal workbook: every cell is a shared string, as the real file stores text."""
    table = [HEADER] + [r + SUMMARY[r[0]] for r in ROWS]
    strings = sorted({v for row in table for v in row})
    index = {v: i for i, v in enumerate(strings)}
    shared = "".join(f"<si><t>{escape(v)}</t></si>" for v in strings)
    rows = "".join(
        f'<row r="{r + 1}">'
        + "".join(
            f'<c r="{chr(65 + c)}{r + 1}" t="s"><v>{index[v]}</v></c>' for c, v in enumerate(row)
        )
        + "</row>"
        for r, row in enumerate(table)
    )
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("xl/sharedStrings.xml", f"<sst {ns}>{shared}</sst>")
        z.writestr(
            "xl/worksheets/sheet1.xml", f"<worksheet {ns}><sheetData>{rows}</sheetData></worksheet>"
        )
    return out.getvalue()


def fake_github(downloads: list[str], sha: str = "abc") -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.github.com":
            return httpx.Response(
                200,
                json={
                    "sha": sha,
                    "download_url": "https://raw.example.test/scores.xlsx",
                    "html_url": "https://github.example.test/scores.xlsx",
                },
            )
        downloads.append(str(request.url))
        return httpx.Response(200, content=xlsx())

    return httpx.MockTransport(handler)


def test_collect_keeps_field_groups_with_gradient_and_task_scores_once() -> None:
    downloads: list[str] = []
    state = MemoryState()
    with httpx.Client(transport=fake_github(downloads)) as client:
        first = ilo.collect(client, state)
        second = ilo.collect(client, state)
    occupation = [o for o in first.observations if o.series == ilo.OCCUPATION_SERIES]
    tasks = [o for o in first.observations if o.series == ilo.TASK_SERIES]
    assert ("2411 Accountants", 0.51) in [(o.entity, o.value) for o in occupation]
    assert ilo.gradient_of(occupation[0].cited_span) == "Exposed: Gradient 3"
    assert sorted(o.value or 0.0 for o in tasks if o.entity.startswith("2411")) == [0.465, 0.65]
    assert any(o.entity.startswith("9999") for o in first.observations)  # all groups kept
    assert "not in the file" in first.note  # the other field groups are absent from this fixture
    assert second.observations == [] and len(downloads) == 1


def test_a_changed_file_is_read_again() -> None:
    downloads: list[str] = []
    state = MemoryState()
    with httpx.Client(transport=fake_github(downloads, "abc")) as client:
        ilo.collect(client, state)
    with httpx.Client(transport=fake_github(downloads, "def")) as client:
        ilo.collect(client, state)
    assert len(downloads) == 2
