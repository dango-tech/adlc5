#!/usr/bin/env bash
# Build promotion packet from feature memory (Implement complete prerequisite).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADLC5_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
# shellcheck source=wiki-lib.sh
source "${SCRIPT_DIR}/wiki-lib.sh"

WORKSPACE="."
FEATURE=""
WIKI_ROOT="wiki"

usage() {
  cat <<'EOF'
Usage: promote-prepare.sh --feature NAME [--workspace DIR]

Reads .adlc5/{feature}/memory/promotion-candidates.md and writes:
  wiki/drafts/promote-{feature}/packet.md
  wiki/drafts/promote-{feature}/review-questions.json
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --feature) FEATURE="${2:?}"; shift 2 ;;
    --wiki-root) WIKI_ROOT="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 1 ;;
  esac
done

[[ -n "$FEATURE" ]] || { echo "ERROR: --feature required" >&2; exit 1; }

WS="$(wiki_resolve_workspace "$WORKSPACE")"
WIKI="${WS}/${WIKI_ROOT}"
FEATURE_DIR="${WS}/.adlc5/${FEATURE}"
CANDIDATES="${FEATURE_DIR}/memory/promotion-candidates.md"
PROMO_DIR="${WIKI}/drafts/promote-${FEATURE}"

STATE="${FEATURE_DIR}/state.json"
[[ -f "$STATE" ]] || { echo "ERROR: canonical state missing: ${STATE}" >&2; exit 1; }
jq -e '.schema_version == "3.0" and .stage_status.implement == "completed"' "$STATE" >/dev/null 2>&1 \
  || { echo "ERROR: project-wiki promotion requires completed schema-v3 Implement state" >&2; exit 1; }
mkdir -p "$PROMO_DIR"

wiki_render_template "${ADLC5_ROOT}/templates/wiki/drafts/promotion-packet-template.md" \
  "${PROMO_DIR}/packet.md" "$(wiki_git_short "$(wiki_git_head "$WS")")" "$FEATURE"

# Parse ### candidate-id sections into review-questions.json (minimal)
QUESTIONS_JSON="${PROMO_DIR}/review-questions.json"
export WIKI_CANDIDATES_PATH="$CANDIDATES" WIKI_PACKET_PATH="${PROMO_DIR}/packet.md"
export WIKI_QUESTIONS_JSON="$QUESTIONS_JSON" WIKI_WS="$WS" WIKI_FEATURE="$FEATURE"
python3 - <<'PY'
import json, os, re, pathlib, datetime

candidates_path = pathlib.Path(os.environ["WIKI_CANDIDATES_PATH"])
packet = pathlib.Path(os.environ["WIKI_PACKET_PATH"])
ws = pathlib.Path(os.environ["WIKI_WS"])
feature = os.environ["WIKI_FEATURE"]
questions_json = os.environ["WIKI_QUESTIONS_JSON"]

text = candidates_path.read_text(encoding="utf-8") if candidates_path.exists() else ""
sections = re.split(r"(?:^|\n)###\s+", text, flags=re.MULTILINE)
items = []
for sec in sections[1:]:
    lines = sec.strip().split("\n")
    cid = lines[0].strip()
    claim = ""
    evidence = []
    for line in lines[1:]:
        if line.strip().startswith("**Claim:**"):
            claim = line.split("**Claim:**", 1)[-1].strip()
        if "**Evidence:**" in line or "`" in line:
            evidence.extend(re.findall(r"`([^`]+)`", line))
    if not cid:
        continue
    items.append({
        "id": cid,
        "prompt": f"Accept '{claim[:80]}' as project truth?",
        "options": [
            {"id": "promote_entity", "label": "Promote to entity page"},
            {"id": "promote_concept", "label": "Promote as concept only"},
            {"id": "reject", "label": "Reject — keep feature-local"},
            {"id": "investigate", "label": "Needs investigation — challenges/"},
        ],
        "evidence": evidence,
        "claim": claim or cid,
    })
out = {
    "feature": feature,
    "packet": str(packet.relative_to(ws)),
    "prepared_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "questions": items,
}
pathlib.Path(questions_json).write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"OK: {len(items)} question(s) -> {questions_json}")
PY

if [[ -f "$CANDIDATES" ]]; then
  cat >>"${PROMO_DIR}/packet.md" <<EOF

## Source

\`\`\`
$(cat "$CANDIDATES")
\`\`\`
EOF
fi

cp "${ADLC5_ROOT}/templates/wiki/drafts/approved.json.example" "${PROMO_DIR}/approved.json.example"

wiki_log_append "${WIKI}/log.md" "promote-prepare" "${FEATURE}"

echo "OK: Promotion packet at ${PROMO_DIR}/"
echo "Next: @adlc5-project-wiki promote-review (AskQuestion), then edit approved.json, then promote-apply.sh"
