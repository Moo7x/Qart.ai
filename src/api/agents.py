"""Agents: the resource scout (video and article passages) and the progress check.

docs/PHASE2_PLAN.md A7, A8 and contract C6. Owner: A (p2-ai-experience). Registered in
src/app.py in Stage 0; routes are added here only.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api")
