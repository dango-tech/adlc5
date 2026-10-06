#!/usr/bin/env bash
# Smoke test: init-campaign, init-task, campaign state, resolve-autoresearch-dir.
# Called from scripts/verify-install.sh after structural checks.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

CAMPAIGN="smoke-campaign-$$"

chmod +x "${SCRIPT_DIR}/init-campaign.sh" "${SCRIPT_DIR}/init-task.sh" \
  "${SCRIPT_DIR}/check-kill-switch.sh" 2>/dev/null || true

"${SCRIPT_DIR}/init-campaign.sh" --campaign "$CAMPAIGN" --workspace "$TMP" \
  --adlc5-feature demo-feature --spec-handoff .adlc5/demo-feature/spec-handoff.md

"${SCRIPT_DIR}/init-task.sh" --campaign "$CAMPAIGN" --task alpha --workspace "$TMP"

STATE="${TMP}/.autoresearch/${CAMPAIGN}/state.json"
TASK_STATE="${TMP}/.autoresearch/${CAMPAIGN}/tasks/alpha/state.json"

[[ -f "$STATE" ]] || { echo "FAIL: campaign state missing" >&2; exit 1; }
[[ -f "$TASK_STATE" ]] || { echo "FAIL: task state missing" >&2; exit 1; }

jq -e '.mode == "campaign" and .current_phase == "autoresearch-0-framing"' "$STATE" >/dev/null \
  || { echo "FAIL: campaign state shape" >&2; exit 1; }

jq -e '.tasks.alpha.path == "tasks/alpha"' "$STATE" >/dev/null \
  || { echo "FAIL: campaign tasks registry" >&2; exit 1; }

jq -e '.adlc5_feature == "demo-feature"' "$STATE" >/dev/null \
  || { echo "FAIL: adlc5_feature not set" >&2; exit 1; }

set +e
"${SCRIPT_DIR}/check-kill-switch.sh" --project "$CAMPAIGN" --task alpha --workspace "$TMP" >/dev/null
EC=$?
set -e
[[ "$EC" -eq 0 ]] || { echo "FAIL: check-kill-switch on fresh task expected 0 got $EC" >&2; exit 1; }

echo "autoresearch campaign smoke OK"
