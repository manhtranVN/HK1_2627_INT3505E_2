#!/usr/bin/env bash
# Lab 4 — load test the Books API with Locust (3 scenarios), headless.
# No Postman UI needed. Run from anywhere:  bash run_lab4.sh
# Requirements: Python venv with deps (locust) installed; see README step 1.
set -euo pipefail
cd "$(dirname "$0")"

# Force UTF-8 so Windows cp1252 consoles don't choke on the non-ASCII path.
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8

PORT="${PORT:-5000}"
HOST="http://127.0.0.1:${PORT}"

# Pick the venv interpreter (Windows Git Bash vs Linux/macOS), else system python.
if   [ -x ".venv/Scripts/python.exe" ]; then PY=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ];         then PY=".venv/bin/python"
else PY="python"; fi

mkdir -p reports instance

# Start the Flask dev server in the background; always stop it on exit.
"$PY" -m app --port "$PORT" > reports/server.log 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

# Wait until /health responds (max ~10s).
for _ in $(seq 1 20); do
  curl -fsS "$HOST/health" >/dev/null 2>&1 && break
  sleep 0.5
done
curl -fsS "$HOST/health" >/dev/null || { echo "API did not start; see reports/server.log"; exit 1; }

run() {  # <name> <users> <spawn-rate> <duration>
  echo "=== Scenario $1: $2 users, spawn $3/s, $4 ==="
  # Locust exits non-zero when any request fails; that is expected here because
  # search_by_year injects ~1% client-side failures. Tolerate it so all runs execute.
  "$PY" -m locust -f performance/locustfile.py --headless -H "$HOST" \
    -u "$2" -r "$3" -t "$4" --html "reports/$1.html" --csv "reports/$1" --only-summary \
    || echo "(scenario $1: locust exit $? — non-zero expected when failures exist)"
}

run A 10  2  30s   # baseline (light)
run B 50  5  60s   # normal load
run C 200 50 30s   # spike