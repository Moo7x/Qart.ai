"""Qart.ai backend package.

Fails early with a clear message on an old Python. The project is built and tested on 3.12;
older versions break later with confusing errors (e.g. datetime.UTC needs 3.11, and pinned
packages such as pandas 3 have no wheels for old Pythons).
"""

import sys

MIN_PYTHON = (3, 12)  # same as requires-python in pyproject.toml and the module in .replit

if sys.version_info < MIN_PYTHON:
    raise SystemExit(
        f"Qart.ai needs Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer; this is "
        f"{sys.version.split()[0]}. Create the venv with Python 3.12 "
        "(e.g. `py -3.12 -m venv .venv` on Windows, `python3.12 -m venv .venv` elsewhere)."
    )
