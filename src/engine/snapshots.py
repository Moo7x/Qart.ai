"""Layer A: dated external-evidence snapshots and their diff (Task A1).

Snapshots hold external evidence only. AI usage share is not proof of task replacement, so a diff
never changes skill weights: it only produces `suggested_assumption_reviews` that HR may act on
(layer B, a new CompanyAssumptions version).

Signals built from the Anthropic Economic Index (AEI) claude_ai file (data CC-BY):
- "SOC <code> <title>" · usage_pct: AEI `pct` in category soc_occupation = share (%) of the
  geography's Claude.ai conversations mapped to that occupation (GLOBAL and MYS).
- "SOC <code> <title>" · automation_pct / augmentation_pct: AEI collaboration buckets (GLOBAL only;
  country-level SOC rows publish `pct` only).
- "<GEO> overall" · automation_pct / augmentation_pct: country-level collaboration shares.
"""

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from src.contract import (
    AssumptionReview,
    ReviewTrigger,
    Signal,
    SignalChange,
    Snapshot,
    SnapshotDiff,
)
from src.engine import params

AEI_SOURCE = "Anthropic Economic Index (data CC-BY)"
AEI_URL = "https://huggingface.co/datasets/Anthropic/EconomicIndex"
AEI_LICENCE = "CC-BY (data), MIT (code); attribution: Anthropic Economic Index, release 2026-06-26"
REPLAY_LABEL = "historical data replay"
DIFF_NOTE = (
    "External evidence only (layer A). AI usage share is not proof of task replacement; a change "
    "suggests that HR reviews an assumption, it never changes weights by itself."
)
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


@dataclass(frozen=True)
class AeiRow:
    """One filtered AEI row (already restricted to the geographies and SOC codes we use)."""

    period: str  # YYYY-MM
    geo: str
    category: str  # soc_occupation | overall
    metric: str  # AEI metric_id
    value: float
    node_name: str
    soc_code: str | None  # e.g. "43-3031"; None for overall rows


METRIC_NAMES = {
    "pct": "usage_pct",
    "collaboration_bucket_automation_pct": "automation_pct",
    "collaboration_bucket_augmentation_pct": "augmentation_pct",
}


def _entity(row: AeiRow) -> str:
    return f"SOC {row.soc_code} {row.node_name}" if row.soc_code else f"{row.geo} overall"


def build_snapshot(
    rows: Iterable[AeiRow],
    period: str,
    release_date: str,
    retrieved_at: str,
    previous: Snapshot | None = None,
    triggers: Sequence[ReviewTrigger] = (),
) -> Snapshot:
    """One Snapshot for one monthly period (+ reviews against the previous period, if given)."""
    signals = [
        Signal(
            entity=_entity(r),
            metric=METRIC_NAMES[r.metric],
            geo=r.geo,
            value=r.value,
            period=r.period,
        )
        for r in rows
        if r.period == period and r.metric in METRIC_NAMES
    ]
    signals.sort(key=lambda s: (s.entity, s.metric, s.geo or ""))
    snapshot = Snapshot(
        id=f"snap_aei_{period.replace('-', '_')}",
        source=AEI_SOURCE,
        release_date=release_date,
        period=period,
        geo="MYS+GLOBAL",
        url=AEI_URL,
        retrieved_at=retrieved_at,
        signals=signals,
        licence=AEI_LICENCE,
        label=f"{REPLAY_LABEL}: period {period} from the {release_date} release",
    )
    if previous is not None:
        snapshot.suggested_assumption_reviews = diff(previous, snapshot, triggers)
    return snapshot


def _key(signal: Signal) -> tuple[str, str, str]:
    return (signal.entity, signal.metric, signal.geo or "")


def _soc(entity: str) -> str | None:
    return entity.split()[1] if entity.startswith("SOC ") else None


def compare_signals(before: Snapshot, after: Snapshot) -> list[SignalChange]:
    """Every signal in either snapshot, with absolute and relative change."""
    old = {_key(s): s.value for s in before.signals}
    new = {_key(s): s.value for s in after.signals}
    changes = []
    for key in sorted(old.keys() | new.keys()):
        a, b = old.get(key), new.get(key)
        change = None if a is None or b is None else round(b - a, params.SIGNAL_DECIMALS)
        relative = None if change is None or not a else round(change / a, params.SIGNAL_DECIMALS)
        significant = (
            change is not None
            and relative is not None
            and abs(relative) >= params.SIGNAL_REVIEW_RELATIVE_CHANGE
            and abs(change) >= params.SIGNAL_REVIEW_MIN_ABS_CHANGE
        )
        changes.append(
            SignalChange(
                entity=key[0],
                metric=key[1],
                geo=key[2] or None,
                before=a,
                after=b,
                change=change,
                relative_change=relative,
                significant=significant,
            )
        )
    return changes


def month_label(period: str) -> str:
    year, month = period.split("-")
    return f"{MONTHS[int(month) - 1]} {year}"


def _reason(change: SignalChange, before: Snapshot, after: Snapshot) -> str:
    direction = "rose" if (change.change or 0) > 0 else "fell"
    span = f"{month_label(before.period)}→{month_label(after.period)}"
    return (
        f"{change.metric} for {change.entity} ({change.geo}) {direction} "
        f"{change.before:.2f}→{change.after:.2f} ({span}, {before.source})"
    )


def diff(
    before: Snapshot, after: Snapshot, triggers: Sequence[ReviewTrigger]
) -> list[AssumptionReview]:
    """Assumptions HR should review, from significant changes matched to the review triggers."""
    reasons: dict[str, list[str]] = {}
    for change in compare_signals(before, after):
        if not change.significant:
            continue
        for trigger in triggers:
            matches = (
                _soc(change.entity) == trigger.soc_code
                and change.metric == trigger.metric
                and change.geo == trigger.geo
            )
            if matches:
                for assumption_id in trigger.assumption_ids:
                    reasons.setdefault(assumption_id, []).append(_reason(change, before, after))
    return [
        AssumptionReview(assumption_id=a, reason="; ".join(r)) for a, r in sorted(reasons.items())
    ]


def diff_report(
    before: Snapshot, after: Snapshot, triggers: Sequence[ReviewTrigger]
) -> SnapshotDiff:
    """Readable diff for the HR banner: every changed signal plus suggested reviews."""
    changes = [c for c in compare_signals(before, after) if c.change != 0]
    return SnapshotDiff(
        from_id=before.id,
        to_id=after.id,
        from_period=before.period,
        to_period=after.period,
        label=f"{REPLAY_LABEL}: {month_label(before.period)} → {month_label(after.period)}",
        changes=sorted(changes, key=lambda c: (not c.significant, c.entity, c.metric)),
        suggested_assumption_reviews=diff(before, after, triggers),
        note=DIFF_NOTE,
    )


def load_snapshots(directory: Path) -> list[Snapshot]:
    """All snapshots in a directory, oldest period first."""
    snapshots = [
        Snapshot.model_validate(json.loads(p.read_text(encoding="utf-8")))
        for p in directory.glob("snap_*.json")
    ]
    return sorted(snapshots, key=lambda s: s.period)
