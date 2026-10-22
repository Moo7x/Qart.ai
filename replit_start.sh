#!/bin/bash
set -e

echo "==> Installing Python dependencies..."
pip install -r requirements.txt -q

echo "==> Building web app..."
# Vite 8 needs Node 20.19+ or 22.12+ (.replit selects the nodejs-22 module).
node -e 'const [a,b]=process.versions.node.split(".").map(Number); if(!((a===20&&b>=19)||(a===22&&b>=12)||a>22)){console.error("Node "+process.versions.node+" is too old for the web build: need 20.19+ or 22.12+ (check the nodejs module in .replit)");process.exit(1)}'
cd web
npm ci --silent  # installs exactly package-lock.json and never rewrites it
npm run build
cd ..

echo "==> Starting Qart.ai server on port 8000..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
