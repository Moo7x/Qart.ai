"""What every collector returns, and the small key-value state a collector may keep between runs."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import httpx

from src.evidence.store import Observation


class SourceState(Protocol):
    """Remembered values for one source, e.g. the last release already ingested."""

    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str) -> None: ...


@dataclass
class CollectorResult:
    observations: list[Observation]
    note: str = ""  # shown in the run log, e.g. "no new release since 2026-06-26"


Collect = Callable[[httpx.Client, SourceState], CollectorResult]


class MemoryState:
    """In-memory SourceState for tests and one-off runs."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str) -> None:
        self.values[key] = value
