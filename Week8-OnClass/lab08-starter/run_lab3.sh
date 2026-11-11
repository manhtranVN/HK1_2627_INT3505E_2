#!/usr/bin/env bash
# Lab 3 — run the Postman collection headless via Newman against a local Flask API.
# No Postman UI needed. Run from anywhere:  bash run_lab3.sh
# Requirements: Node 18+ (npx), Python venv with deps installed (see README step 1).
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-5000}"
BASE_URL="http://127.0.0.1:${PORT}"

# Pick the venv interpreter (Windows Git Bash vs Linux/macOS), else system python.
if   [ -x ".venv/Scripts/python.exe" ]; then PY=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ];         then PY=".venv/bin/python"
else PY="python"; fi

mkdir -p reports instance

# 1. Start the Flask API in the background; always stop it on exit.
"$PY" -m app --port "$PORT" > reports/server.log 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

# 2. Wait until /health responds (max ~10s).
for _ in $(seq 1 20); do
  curl -fsS "$BASE_URL/health" >/dev/null 2>&1 && break
  sleep 0.5
done
curl -fsS "$BASE_URL/health" >/dev/null || { echo "API did not start; see reports/server.log"; exit 1; }

# 3. Run Newman with CLI + JUnit reporters (exports reports/junit.xml).
npx --yes newman run books-api.postman_collection.json \
  -e postman/local.postman_environment.json \
  -r cli,junit --reporter-junit-export reports/junit.xml