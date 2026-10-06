#!/usr/bin/env bash
# Stub — Cursor SDK runner adapter. See ~/.cursor/skills-cursor/sdk/SKILL.md
set -euo pipefail
echo '{"status":"stub","message":"Integrate @cursor/sdk Agent.create + dispatch.sh gate loop"}' | jq .
exec "$(cd "$(dirname "$0")/../.." && pwd)/scripts/runner/dispatch.sh" "$@"
