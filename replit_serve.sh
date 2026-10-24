#!/bin/bash
# Starts the server only. Fails at once with a clear message if the build step did not run.
set -e
PY=.venv/bin/python
if [ ! -x "$PY" ] || [ ! -f web/dist/index.html ]; then
  echo "Build missing (.venv or web/dist): run 'bash replit_build.sh' first" >&2
  exit 1
fi
echo "==> Starting Qart.ai server on port 8000..."
exec "$PY" -m uvicorn src.app:app --host 0.0.0.0 --port 8000
