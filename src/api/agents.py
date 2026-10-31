"""Agents: the resource scout (video and article passages) and the progress check.

docs/PHASE2_PLAN.md A7, A8 and contract C6. Owner: A (p2-ai-experience). Registered in
src/app.py in Stage 0; routes are added here only.

A scout run starts in the background and returns its id at once; the agent window then reads
the run every second, so each step appears as it happens and no page waits on the model.
"""

import threading
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from src.agents import check, store
from src.agents.scout import run_scout
from src.api.evidence import get_engine, get_settings
from src.config import Settings
from src.pack import load_pack
from src.resources import load_resources

router = APIRouter(prefix="/api")


class ScoutIn(BaseModel):
    skill: str = Field(min_length=1, max_length=64)
    profile_id: str | None = Field(default=None, max_length=64)


class RunStarted(BaseModel):
    run_id: str


def _in_background(engine: Engine, settings: Settings, run_id: str, skill: str) -> None:
    try:
        run_scout(engine, settings, run_id, skill)
    except Exception:  # noqa: BLE001  the run itself records the failure for the window
        return


@router.post("/agents/scout", status_code=202)
def start_scout(
    body: ScoutIn,
    engine: Engine = Depends(get_engine),
    settings: Settings = Depends(get_settings),
) -> RunStarted:
    if body.skill not in load_pack().skills:
        raise HTTPException(status_code=422, detail="unknown skill")
    res = load_resources()
    if not res.videos_for(skill=body.skill) and not res.articles_for(skill=body.skill):
        raise HTTPException(status_code=422, detail="no checked video or article for this skill")
    agent_engine = f"{settings.agent_model} agent" if settings.llm_configured else "ranking only"
    run_id = store.start(engine, "scout", body.skill, body.profile_id, agent_engine)
    threading.Thread(
        target=_in_background, args=(engine, settings, run_id, body.skill), daemon=True
    ).start()
    return RunStarted(run_id=run_id)


class CheckIn(BaseModel):
    skill: str = Field(min_length=1, max_length=64)


class AnswerIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class DecideIn(BaseModel):
    accept: bool


def _checked(call: Any) -> dict[str, Any]:
    try:
        result: dict[str, Any] = call()
        return result
    except check.CheckError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/profiles/{profile_id}/checks", status_code=201)
def start_check(
    profile_id: str,
    body: CheckIn,
    engine: Engine = Depends(get_engine),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Progress check (C6): the first question about work the person did."""
    return _checked(lambda: check.start(engine, settings, profile_id, body.skill))


@router.post("/profiles/{profile_id}/checks/{session_id}/answer")
def answer_check(
    profile_id: str,
    session_id: str,
    body: AnswerIn,
    engine: Engine = Depends(get_engine),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """The next question, or the proposed level once there is enough to judge."""
    return _checked(lambda: check.answer(engine, settings, profile_id, session_id, body.text))


@router.post("/profiles/{profile_id}/checks/{session_id}/decide")
def decide_check(
    profile_id: str,
    session_id: str,
    body: DecideIn,
    engine: Engine = Depends(get_engine),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """The person accepts (the level becomes an agent_check claim) or declines (nothing changes)."""
    return _checked(lambda: check.decide(engine, settings, profile_id, session_id, body.accept))


@router.get("/agents/runs/{run_id}")
def agent_run(run_id: str, engine: Engine = Depends(get_engine)) -> dict[str, Any]:
    found = store.read(engine, run_id)
    if found is None or found["kind"] != "scout":  # a check holds the person's answers
        raise HTTPException(status_code=404, detail="unknown run")
    return found
