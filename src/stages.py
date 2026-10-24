"""Measured stages of a long action, returned to the page so its activity panel shows what really
happened (which engine ran, how long each step took, which step failed and fell back)."""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


class Stages:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    @contextmanager
    def step(self, name: str, engine: str = "") -> Iterator[None]:
        started = time.monotonic()
        item: dict[str, Any] = {"name": name, "engine": engine, "outcome": "ok"}
        try:
            yield
        except Exception as exc:
            item["outcome"] = f"failed ({type(exc).__name__})"
            raise
        finally:
            item["seconds"] = round(time.monotonic() - started, 2)
            self.items.append(item)
