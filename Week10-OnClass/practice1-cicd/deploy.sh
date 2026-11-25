#!/usr/bin/env bash
set -euo pipefail

SHA="${1:?usage: deploy.sh <git-sha>}"
IMG="${IMAGE_REPO:?set IMAGE_REPO e.g. ghcr.io/owner/repo}:${SHA}"
NAME="api"
PORT="8000"

echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin
docker pull "$IMG"

PREV="$(docker inspect --format='{{.Config.Image}}' "$NAME" 2>/dev/null || true)"

docker rm -f "$NAME" 2>/dev/null || true
docker run -d --name "$NAME" -p "$PORT:$PORT" --restart unless-stopped "$IMG"

for _ in $(seq 1 10); do
  if curl -fsS "http://localhost:$PORT/healthz" >/dev/null; then
    echo "deploy OK: $IMG"
    exit 0
  fi
  sleep 2
done

echo "readiness failed, rolling back to ${PREV:-<none>}"
docker rm -f "$NAME" 2>/dev/null || true
if [ -n "$PREV" ]; then
  docker run -d --name "$NAME" -p "$PORT:$PORT" --restart unless-stopped "$PREV"
fi
exit 1