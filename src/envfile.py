"""Load KEY=VALUE lines from the project's .env file into the environment (no extra library).

Used for local runs: put secrets such as LLM_API_KEY, RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID in
.env (gitignored; names listed in .env.example). Variables that already exist in the environment
win, so Replit Secrets are never overridden. Values are never logged or printed.
"""

import os
from collections.abc import MutableMapping
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"
QUOTES = "\"'"


def load_env_file(
    path: Path = ENV_FILE, environ: MutableMapping[str, str] | None = None
) -> list[str]:
    """Set variables from `path` that are not set yet; return their names (never the values)."""
    target = os.environ if environ is None else environ
    if not path.exists():
        return []
    loaded = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name, value = name.strip().removeprefix("export ").strip(), value.strip().strip(QUOTES)
        if name and value and name not in target:
            target[name] = value
            loaded.append(name)
    return loaded
