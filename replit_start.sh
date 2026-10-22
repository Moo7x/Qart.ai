#!/bin/bash
set -e

echo "==> Installing Python dependencies..."
pip install -r requirements.txt -q

echo "==> Building web app..."
cd web
npm install --silent
npm run build
cd ..

echo "==> Starting Qart.ai server on port 8000..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
