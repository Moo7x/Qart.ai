"""Software evidence explains requirements, without changing scores or accepted snapshots."""

import io
import shutil
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.pack as pack_module
from src.collectors import onet
from src.collectors.base import MemoryState
from src.evidence.field import PACK_DIR
from src.evidence.store import Observation, insert_observations
from src.match.basis import requirement_basis
from src.pack import PackError, load_pack
from tests.test_api_journey import create
from tests.test_collectors_onet import archive, fake_onet

ERP = "Enterprise resource planning ERP software"
ROLE = "p2p_reporting_analyst"


def technology_row(value: float = 2.0, **changes: Any) -> dict[str, Any]:
    return {
        "source_id": onet.SOURCE_ID,
        "series": onet.TECH_SERIES,
        "entity": "15-2051.01 2.E.2.b",
        "geography": "US",
        "period": "31.0",
        "value": value,
        "unit": onet.TECH_UNIT,
        "url": "https://www.onetcenter.org/dl_files/database/db_31_0_csv.zip",
        "cited_span": f"O*NET 31.0 · 15-2051.01 · {ERP}: SAP; Oracle",
        "method_version": "onet/31.0",
        **changes,
    }


@pytest.mark.parametrize("value", [0.0, 1.0, 2.0])
def test_exact_mapped_category_explains_the_occupation_with_flag_scope(value: float) -> None:
    basis = requirement_basis(load_pack(), ROLE, "erp", [technology_row(value)])
    assert basis["kind"] == "onet_tech"
    assert "O*NET 31.0" in basis["source"] and "US" in basis["source"]
    if value == 2:
        assert "in demand in US postings for this occupation" in basis["text"]
    elif value == 1:
        assert "not necessarily in demand for this one" in basis["text"]
    else:
        assert "no job-posting demand flag" in basis["text"]


@pytest.mark.parametrize(
    "changes",
    [
        {"entity": "13-2011.00 2.E.2.b"},  # another occupation
        {"cited_span": f"O*NET 31.0 · 15-2051.01 · {ERP.lower()}: SAP"},
        {"series": "something_else"},
        {"value": None},
    ],
)
def test_unrelated_or_unusable_rows_leave_the_requirement_an_assumption(
    changes: dict[str, Any],
) -> None:
    basis = requirement_basis(load_pack(), ROLE, "erp", [technology_row(**changes)])
    assert basis["kind"] == "assumption"


def test_software_evidence_never_replaces_a_role_page_or_linked_task() -> None:
    pack = load_pack()
    for role in pack.destination_roles.values():
        for req in role.requires:
            before = requirement_basis(pack, role.id, req.skill)
            if before["kind"] != "assumption":
                assert requirement_basis(pack, role.id, req.skill, [technology_row()]) == before


@pytest.fixture
def pack_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    target = tmp_path / "pack"
    shutil.copytree(PACK_DIR, target)
    monkeypatch.setattr(pack_module, "PACK_DIR", target)
    load_pack.cache_clear()
    yield target
    load_pack.cache_clear()


def test_mapping_is_optional_and_a_missing_file_keeps_the_assumption(pack_dir: Path) -> None:
    (pack_dir / "technology.yaml").unlink()
    pack = load_pack()
    assert pack.technology == []
    assert requirement_basis(pack, ROLE, "erp", [technology_row()])["kind"] == "assumption"


@pytest.mark.parametrize(
    ("entries", "message"),
    [
        ([{"commodity": ERP, "skills": ["nonexistent"], "reason": "A reason"}], "unknown skill"),
        ([{"commodity": ERP, "skills": ["erp"], "reason": ""}], "needs skills and a reason"),
        ([{"commodity": ERP, "skills": ["erp"], "reason": "A reason"}] * 2, "duplicate"),
    ],
)
def test_invalid_mapping_fails_loudly(
    pack_dir: Path, entries: list[dict[str, Any]], message: str
) -> None:
    (pack_dir / "technology.yaml").write_text(
        yaml.safe_dump({"commodities": entries}), encoding="utf-8"
    )
    with pytest.raises(PackError, match=message):
        load_pack()


def test_release_31_software_filename_is_read_and_old_skip_key_is_migrated() -> None:
    import httpx

    csv_text = (
        "O*NET-SOC Code,Title,Workplace Example,Element ID,Element Name,Hot Technology,In Demand\n"
        f"15-2051.01,Business Intelligence Analysts,SAP,2.E.2.b,{ERP},Y,Y\n"
    )
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(archive())) as base, zipfile.ZipFile(out, "w") as z:
        for name in base.namelist():
            z.writestr(name, base.read(name))
        z.writestr("db_31_0_csv/software_skills.csv", csv_text)
    state = MemoryState()
    state.set("release", f"31.0|tech|{','.join(sorted(load_pack().task_ids(), key=int))}")
    downloads: list[str] = []
    with httpx.Client(transport=fake_onet(downloads, out.getvalue())) as client:
        first = onet.collect(client, state)
        second = onet.collect(client, state)
    assert len([o for o in first.observations if o.series == onet.TECH_SERIES]) == 1
    assert "1 software categories" in first.note
    assert second.observations == [] and len(downloads) == 1


def test_roles_and_plan_use_accepted_evidence_without_changing_fit(client: TestClient) -> None:
    old_id = create(client)
    before = client.get(f"/api/profiles/{old_id}/matches").json()["roles"]
    engine = cast(FastAPI, client.app).state.engine
    insert_observations(engine, [Observation(**technology_row())], run_id=None)
    # An existing profile must not silently jump to an unaccepted snapshot.
    old = client.get(f"/api/profiles/{old_id}/matches").json()["roles"]
    assert (
        next(r for r in old if r["role_id"] == ROLE)["requirement_basis"]["erp"]["kind"]
        == "assumption"
    )
    new_id = create(client)
    after = client.get(f"/api/profiles/{new_id}/matches").json()["roles"]
    assert [(r["role_id"], r["fit"]) for r in before] == [(r["role_id"], r["fit"]) for r in after]
    basis = next(r for r in after if r["role_id"] == ROLE)["requirement_basis"]["erp"]
    assert basis["kind"] == "onet_tech"
    client.post(f"/api/profiles/{new_id}/destination", json={"role_id": ROLE})
    tracks = client.get(f"/api/profiles/{new_id}/tracks").json()["tracks"]
    node = next(n for t in tracks for n in t["nodes"] if n.get("skill") == "erp")
    assert node["why"] == basis
