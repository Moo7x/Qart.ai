"""Playbook versions: which checking procedure the companion follows, and where its text lives.

playbook_v1 is the hand-written procedure committed in src/companion/playbooks/. Later versions come
from the optimiser; a senior approves one before it becomes active. Texts are kept in the store
(Replit does not keep files written at runtime); an approved version is also written to
src/companion/playbooks/ so it can be reviewed in git. The active version is a store setting; a
demo reset clears it, which means playbook_v1 again. Every event records the version that produced
it (companion_version), so evidence can always be traced to the procedure in force.
"""

import logging
import re
from pathlib import Path

from src.store import Store

_log = logging.getLogger(__name__)

PLAYBOOK_DIR = Path(__file__).resolve().parent / "playbooks"
BASE_VERSION = "playbook_v1"
ACTIVE_KEY = "active_playbook"
VERSION_PATTERN = re.compile(r"^playbook_v(\d+)$")


def playbook_file(version: str) -> Path:
    if not VERSION_PATTERN.match(version):
        raise ValueError(f"not a playbook version: {version!r}")
    return PLAYBOOK_DIR / f"{version}.md"


def read_playbook(version: str, store: Store | None = None) -> str:
    """The text of one version: the store first (runtime versions), then the committed file."""
    if store is not None:
        body = store.get_playbook(version)
        if body is not None:
            return body
    path = playbook_file(version)
    if not path.exists():
        raise KeyError(f"unknown playbook version {version!r}")
    return path.read_text(encoding="utf-8")


def active_playbook(store: Store) -> tuple[str, str]:
    """(version, text) the companion uses now; falls back to v1 if the active text is missing."""
    version = store.get_setting(ACTIVE_KEY) or BASE_VERSION
    try:
        return version, read_playbook(version, store)
    except KeyError:
        _log.warning("active playbook %s has no text; using %s", version, BASE_VERSION)
        return BASE_VERSION, read_playbook(BASE_VERSION, store)


def set_active(store: Store, version: str) -> None:
    read_playbook(version, store)  # refuse to activate a version without text
    store.put_setting(ACTIVE_KEY, version)


def version_number(version: str) -> int:
    match = VERSION_PATTERN.match(version)
    if match is None:
        raise ValueError(f"not a playbook version: {version!r}")
    return int(match.group(1))


def known_versions(store: Store) -> list[str]:
    files = [p.stem for p in PLAYBOOK_DIR.glob("playbook_v*.md")]
    names = {v for v in [*files, *store.playbook_versions()] if VERSION_PATTERN.match(v)}
    return sorted(names, key=version_number)


def next_version(store: Store) -> str:
    numbers = [version_number(v) for v in known_versions(store)]
    return f"playbook_v{max(numbers, default=1) + 1}"


def save_version(store: Store, version: str, body: str, write_file: bool = True) -> Path:
    """Keep a version in the store and, when asked and the disk is writable, as a file.

    The optimiser stores candidates without a file; approving one writes it (write_file), so the
    repository only gains versions a senior accepted.
    """
    store.put_playbook(version, body)
    path = playbook_file(version)
    if write_file:
        try:
            path.write_text(body, encoding="utf-8")
        except OSError as error:  # read-only deployment: the store copy is the one that counts
            _log.warning("could not write %s: %s", path, error)
    return path
