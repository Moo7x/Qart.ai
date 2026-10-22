"""Perturbed variants of practice cases for the OPTIMISATION set (PERSON_A Task A8).

Variants are for the optimiser and robustness checks only; they never go into the acceptance set
(eval/acceptance/ holds independently authored cases).

Each variant keeps the case's ground truth, so only changes that cannot alter the answer are used:
- shuffle the order of ledger and bank rows (a diagnoser must not rely on row order);
- rename row ids (L4 → L104, B6 → B106, ADJ-7 → ADJ-107) everywhere they appear;
- renumber document references (INV-1043 → INV-2043) everywhere they appear;
- swap synthetic counterparty names (Beans Co → Kacang Co, also in upper case).
Not used on purpose: changing amounts (would break transposition and FX errors) and shifting dates
(would break period cut-off items). After each change the variant is checked: same totals, and
every affected row still exists.

Run:  python -m eval.variants [--cases DIR | --git-ref origin/b/app] [--per-case N]
"""

import argparse
import json
import random
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "eval" / "optimisation" / "variants"  # gitignored: regenerated on demand
DEFAULT_PER_CASE = 3
ROW_ID_OFFSET = 100  # variant k adds k × 100 to row-id numbers
DOC_NUMBER_OFFSET = 1000  # variant k adds k × 1000 to document numbers
BASE_SEED = 2026  # declared: fixed seed so variants are reproducible
# Synthetic names only (no real people). Applied only when the name appears in the case.
NAME_SWAPS: tuple[tuple[str, str], ...] = (
    ("Beans Co", "Kacang Co"),
    ("Selamat Property", "Sentosa Property"),
    ("Kopi Kita", "Teh Tarik Kita"),
)
ROW_ID = re.compile(r"\b(L|B|ADJ-)(\d+)\b")
DOC_REF = re.compile(r"\b([A-Z]{2,4})-(\d{3,4})\b")


def _row_ids(case: dict[str, Any]) -> set[str]:
    rows = {r["row_id"] for r in case["ledger"]} | {r["row_id"] for r in case["bank"]}
    return rows | {a["id"] for a in case["ai_output"].get("proposed_adjustments", [])}


def _rename(text: str, k: int, known_rows: set[str], doc_refs: set[str]) -> str:
    def row(match: re.Match[str]) -> str:
        original = match.group(0)
        if original not in known_rows:
            return original
        return f"{match.group(1)}{int(match.group(2)) + k * ROW_ID_OFFSET}"

    def doc(match: re.Match[str]) -> str:
        original = match.group(0)
        if original not in doc_refs:
            return original
        return f"{match.group(1)}-{int(match.group(2)) + k * DOC_NUMBER_OFFSET}"

    text = DOC_REF.sub(doc, text)
    text = ROW_ID.sub(row, text)
    for old, new in NAME_SWAPS:
        text = text.replace(old, new).replace(old.upper(), new.upper())
    return text


def totals(case: dict[str, Any]) -> tuple[float, float]:
    return (
        round(sum(r["amount"] for r in case["ledger"]), 2),
        round(sum(r["amount"] for r in case["bank"]), 2),
    )


def make_variant(case: dict[str, Any], k: int) -> dict[str, Any]:
    """Variant number k (1, 2, …) of one case, with the same ground truth."""
    doc_refs = {d["doc_ref"] for d in case.get("documents", [])}
    text = _rename(json.dumps(case, ensure_ascii=False), k, _row_ids(case), doc_refs)
    renamed: dict[str, Any] = json.loads(text)
    rng = random.Random(f"{BASE_SEED}-{case['id']}-{k}")
    rng.shuffle(renamed["ledger"])
    rng.shuffle(renamed["bank"])
    renamed["id"] = f"{case['id']}_v{k}"
    renamed["variant_of"] = case["id"]
    check_variant(case, renamed)
    return renamed


def check_variant(original: dict[str, Any], variant: dict[str, Any]) -> None:
    """Raise if a variant could have a different answer."""
    if totals(original) != totals(variant):
        raise ValueError(f"{variant['id']}: totals changed")
    truth, new_truth = original.get("ground_truth"), variant.get("ground_truth")
    if truth is None or new_truth is None:
        raise ValueError(f"{variant['id']}: ground truth missing")
    same_answer = (
        truth["has_issue"] == new_truth["has_issue"]
        and truth["issue_types"] == new_truth["issue_types"]
        and truth["correct_decision"] == new_truth["correct_decision"]
    )
    if not same_answer:
        raise ValueError(f"{variant['id']}: ground truth changed")
    missing = set(new_truth["affected_rows"]) - _row_ids(variant)
    if missing:
        raise ValueError(f"{variant['id']}: affected rows {sorted(missing)} no longer exist")


def make_variants(cases: Sequence[dict[str, Any]], per_case: int) -> list[dict[str, Any]]:
    return [
        make_variant(case, k)
        for case in cases
        if case.get("mode") == "practice"  # check-ins and real-work cases are not perturbed
        for k in range(1, per_case + 1)
    ]


def load_cases_from_dir(directory: Path) -> list[dict[str, Any]]:
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(directory.glob("*.json"))
        if p.name != "index.json"
    ]


def load_cases_from_git(ref: str) -> list[dict[str, Any]]:
    """Read cases/*.json from a git ref (e.g. Person B's pushed branch) without checking it out."""
    names = subprocess.run(
        ["git", "ls-tree", "--name-only", f"{ref}:cases"],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
    ).stdout.split()
    cases = []
    for name in names:
        if not name.endswith(".json") or name == "index.json":
            continue
        text = subprocess.run(
            ["git", "show", f"{ref}:cases/{name}"],
            capture_output=True,
            text=True,
            check=True,
            cwd=REPO_ROOT,
            encoding="utf-8",
        ).stdout
        cases.append(json.loads(text))
    return cases


def write_variants(variants: Sequence[dict[str, Any]], out_dir: Path = OUTPUT_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for variant in variants:
        path = out_dir / f"{variant['id']}.json"
        path.write_text(json.dumps(variant, ensure_ascii=False, indent=1) + "\n", "utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=REPO_ROOT / "cases")
    parser.add_argument("--git-ref", default=None, help="read cases from this git ref instead")
    parser.add_argument("--per-case", type=int, default=DEFAULT_PER_CASE)
    args = parser.parse_args()
    cases = load_cases_from_git(args.git_ref) if args.git_ref else load_cases_from_dir(args.cases)
    variants = make_variants(cases, args.per_case)
    write_variants(variants)
    print(f"wrote {len(variants)} variants of {len(cases)} cases to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
