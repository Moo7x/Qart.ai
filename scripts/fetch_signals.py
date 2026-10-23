"""Refresh the Future Skills Radar snapshots from public sources.

Usage (from the repo root):  python scripts/fetch_signals.py
Writes data/snapshots/market_pulse.json and data/snapshots/skill_signals.json; HN threads are
cached in data/raw/hn/. The app only reads the snapshots, so it works offline afterwards.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.signals.pipeline import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
