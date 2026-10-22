"""Runs the optimiser in a background thread so the request that starts it returns at once.

A run makes roughly 60–110 LLM calls (development set passes, revisions, one acceptance gate), so
it takes minutes. Only one run at a time per process; the status says what it is doing.
"""

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel

from src.contract import OptimizerProposal
from src.store import Store

_log = logging.getLogger(__name__)

JobState = Literal["idle", "running", "done", "failed"]


class OptimizerStatus(BaseModel):
    state: JobState = "idle"
    step: str = ""
    started_at: str | None = None
    finished_at: str | None = None
    proposal_id: str | None = None
    error: str | None = None


class OptimizerJob:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._status = OptimizerStatus()

    @property
    def status(self) -> OptimizerStatus:
        with self._lock:
            return self._status.model_copy()

    def _update(self, **changes: object) -> None:
        with self._lock:
            self._status = self._status.model_copy(update=changes)

    def start(self, store: Store, run: Callable[..., OptimizerProposal]) -> bool:
        """Start a run; False if one is already running."""
        with self._lock:
            if self._status.state == "running":
                return False
            self._status = OptimizerStatus(
                state="running", step="starting", started_at=_now(), finished_at=None
            )
        threading.Thread(target=self._work, args=(store, run), daemon=True).start()
        return True

    def _work(self, store: Store, run: Callable[..., OptimizerProposal]) -> None:
        try:
            proposal = run(store, progress=lambda step: self._update(step=step))
        except Exception as error:  # noqa: BLE001 (report any failure to the page)
            _log.exception("optimiser run failed")
            self._update(state="failed", error=str(error)[:300], finished_at=_now())
            return
        self._update(state="done", step="finished", proposal_id=proposal.id, finished_at=_now())


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


JOB = OptimizerJob()
