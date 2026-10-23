"""Fetch the public sources and write the two signal snapshots the app reads.

  Indeed AI Tracker CSV      → data/snapshots/market_pulse.json
  HN "Who is hiring?" (cache) → data/snapshots/skill_signals.json

Every snapshot carries source, source_url, license, attribution, data_as_of (the latest date in
the data, never the fetch date), fetched_at and caveats. Writes are atomic (temp file + rename);
if a source fails, its previous snapshot is kept and the error is logged. Only public data is
fetched: nothing about users or profiles is ever sent anywhere.

Extension point: a further source (e.g. arXiv research momentum, out of scope for v1) adds a
builder returning one snapshot dict and an entry in `run`.
"""

import json
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from src.signals import hn, indeed
from src.signals.compute import skill_signals
from src.signals.config import REPO_ROOT, SignalConfig, default_config

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = REPO_ROOT / "data" / "snapshots"
MARKET_PULSE = "market_pulse.json"
SKILL_SIGNALS = "skill_signals.json"
USER_AGENT = "Qart.ai signals pipeline (SDC hackathon; public data only)"


def write_atomic(path: Path, data: Mapping[str, Any]) -> None:
    """Write JSON to a temp file, then rename: readers never see a partial snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _envelope(
    source_key: str, cfg: SignalConfig, data_as_of: str, fetched_at: str
) -> dict[str, Any]:
    src = cfg.sources[source_key]
    return {
        "source": src.source,
        "source_url": src.source_url,
        "license": src.license,
        "attribution": src.attribution,
        "update_frequency": src.update_frequency,
        "data_as_of": data_as_of,
        "fetched_at": fetched_at,
        "caveats": list(src.caveats),
    }


def build_market_pulse(csv_text: str, cfg: SignalConfig, fetched_at: str) -> dict[str, Any]:
    means, latest = indeed.monthly_means(csv_text)
    series = [
        {
            "series": name,
            "country": country,
            "country_name": indeed.COUNTRY_NAMES.get(country, country),
            "points": [{"month": m, "share_pct": v} for m, v in sorted(months.items())],
        }
        for name, countries in sorted(means.items())
        for country, months in sorted(countries.items())
    ]
    countries = sorted({c for by_country in means.values() for c in by_country})
    default = (
        cfg.params.default_country if cfg.params.default_country in countries else countries[0]
    )
    return {
        **_envelope("indeed", cfg, latest, fetched_at),
        "countries": countries,
        "default_country": default,
        "default_country_label": cfg.params.default_country_label
        if default == cfg.params.default_country
        else f"{indeed.COUNTRY_NAMES.get(default, default)} (not Malaysia)",
        "covers_malaysia": "MY" in countries,
        "events": [e.model_dump() for e in cfg.events],
        "series": series,
    }


def build_skill_signals(
    posts_by_month: Mapping[str, Sequence[str]],
    latest_post_date: str,
    cfg: SignalConfig,
    fetched_at: str,
) -> dict[str, Any]:
    signals = skill_signals(posts_by_month, cfg.skills, cfg.params)
    months = sorted(posts_by_month)[-cfg.params.window_months :]
    latest_total = len(posts_by_month[months[-1]]) if months else 0
    envelope = _envelope("hn", cfg, latest_post_date, fetched_at)
    envelope["caveats"].append(
        f"Latest month: {latest_total} job posts in the thread ({months[-1] if months else '–'})."
    )
    return {
        **envelope,
        "months": months,
        "params": cfg.params.model_dump(),
        "series": [asdict(s) for s in signals],
    }


def latest_post_date(cache_dir: Path, month: str) -> str:
    """The newest job-post date in a cached month (YYYY-MM-DD); the month start if none."""
    thread = json.loads((cache_dir / f"{month}.json").read_text(encoding="utf-8"))
    dates = [c["created_at"][:10] for c in thread.get("children", []) if c.get("created_at")]
    return max(dates, default=f"{month}-01")


def window_start(now: datetime, months: int) -> str:
    """First month (YYYY-MM) of a window of `months` months ending with the current one."""
    index = now.year * 12 + now.month - 1 - (months - 1)
    return f"{index // 12}-{index % 12 + 1:02d}"


def run(
    out_dir: Path = SNAPSHOT_DIR,
    cache_dir: Path = hn.CACHE_DIR,
    cfg: SignalConfig | None = None,
    now: datetime | None = None,
    make_client: Callable[[], httpx.Client] | None = None,
) -> dict[str, str]:
    """Refresh both snapshots; returns {snapshot file: "ok" | "kept previous: <error>"}."""
    cfg = cfg or default_config()
    now = now or datetime.now(UTC)
    fetched_at = now.isoformat(timespec="seconds")
    make_client = make_client or (lambda: httpx.Client(headers={"User-Agent": USER_AGENT}))
    status: dict[str, str] = {}
    with make_client() as client:
        try:
            csv_url = cfg.sources["indeed"].csv_url or ""
            pulse = build_market_pulse(indeed.fetch_csv(csv_url, client), cfg, fetched_at)
            write_atomic(out_dir / MARKET_PULSE, pulse)
            status[MARKET_PULSE] = "ok"
        except Exception as exc:  # keep the previous snapshot; never write a partial one
            logger.error("market pulse refresh failed: %s", exc)
            status[MARKET_PULSE] = f"kept previous: {exc}"
        try:
            since = window_start(now, cfg.params.window_months)
            posts, fetched = hn.load_months(client, since, cache_dir, now)
            if not posts:
                raise ValueError("no 'Who is hiring?' threads found")
            latest = latest_post_date(cache_dir, max(posts))
            signals = build_skill_signals(posts, latest, cfg, fetched_at)
            write_atomic(out_dir / SKILL_SIGNALS, signals)
            status[SKILL_SIGNALS] = f"ok ({len(fetched)} month(s) fetched, {len(posts)} in window)"
        except Exception as exc:
            logger.error("skill signals refresh failed: %s", exc)
            status[SKILL_SIGNALS] = f"kept previous: {exc}"
    return status


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    status = run()
    for name, result in status.items():
        print(f"{name}: {result}")
    return 0 if all(v.startswith("ok") for v in status.values()) else 1
