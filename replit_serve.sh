#!/bin/bash
# A deployment's run step. QART_DEPLOY_ROLE picks what it does, so one repository serves both
# Replit deployments with the same .replit:
#   web (default)  start the server
#   pipeline       run the evidence pipeline once and exit (a Scheduled deployment)
# Fails at once with a clear message if the build step did not run.
set -e
PY=.venv/bin/python
if [ ! -x "$PY" ]; then
  echo "Build missing (.venv): run 'bash replit_build.sh' first" >&2
  exit 1
fi
if [ "${QART_DEPLOY_ROLE:-web}" = "pipeline" ]; then
  echo "==> Running the Qart.ai evidence pipeline (scheduled)..."
  exec "$PY" -m src.pipeline.run --trigger schedule
fi
if [ ! -f web/dist/index.html ]; then
  echo "Build missing (web/dist): run 'bash replit_build.sh' first" >&2
  exit 1
fi
echo "==> Starting Qart.ai server on port 8000..."
exec "$PY" -m uvicorn src.app:app --host 0.0.0.0 --port 8000
