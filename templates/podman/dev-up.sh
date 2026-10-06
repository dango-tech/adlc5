#!/usr/bin/env bash
# Start Podman compose dev stack from repo root.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
COMPOSE="${ROOT}/templates/podman/compose.yaml"

cd "$ROOT"

if command -v podman-compose >/dev/null 2>&1; then
  podman-compose -f "$COMPOSE" up -d app
elif command -v podman >/dev/null 2>&1 && podman compose version >/dev/null 2>&1; then
  podman compose -f "$COMPOSE" up -d app
else
  echo "ERROR: install podman-compose or podman with compose support" >&2
  exit 1
fi

echo "Dev stack started. Smoke: podman compose -f templates/podman/compose.yaml run --rm smoke"
