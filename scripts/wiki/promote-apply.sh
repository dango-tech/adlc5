#!/usr/bin/env bash
# Apply human-approved promotion manifest to wiki/entities|concepts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=wiki-lib.sh
source "${SCRIPT_DIR}/wiki-lib.sh"

WORKSPACE="."
FEATURE=""
WIKI_ROOT="wiki"
APPROVED=""

usage() {
  cat <<'EOF'
Usage: promote-apply.sh --feature NAME [--workspace DIR] [--approved PATH]

Default approved file: wiki/drafts/promote-{feature}/approved.json
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --feature) FEATURE="${2:?}"; shift 2 ;;
    --wiki-root) WIKI_ROOT="${2:?}"; shift 2 ;;
    --approved) APPROVED="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 1 ;;
  esac
done

[[ -n "$FEATURE" ]] || { echo "ERROR: --feature required" >&2; exit 1; }

WS="$(wiki_resolve_workspace "$WORKSPACE")"
WIKI="${WS}/${WIKI_ROOT}"
PROMO_DIR="${WIKI}/drafts/promote-${FEATURE}"
APPROVED="${APPROVED:-${PROMO_DIR}/approved.json}"

[[ -f "$APPROVED" ]] || { echo "ERROR: approved.json not found: ${APPROVED}" >&2; exit 1; }

STATE="${WS}/.adlc5/${FEATURE}/state.json"
[[ -f "$STATE" ]] || { echo "ERROR: canonical state missing: ${STATE}" >&2; exit 1; }
jq -e '.schema_version == "3.0" and .stage_status.implement == "completed"' "$STATE" >/dev/null 2>&1 \
  || { echo "ERROR: project-wiki promotion requires completed schema-v3 Implement state" >&2; exit 1; }
jq -e --arg feature "$FEATURE" '
  def human_approver:
    type == "string"
    and ((ascii_downcase == "user")
      or (ascii_downcase | test("^human:[[:space:]]*[^[:space:]]"))
      or (ascii_downcase | test("^github:[a-z0-9][a-z0-9-]{0,38}$"))
      or (ascii_downcase | test("^email:[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$")));
  .feature == $feature and (.approved_by | human_approver)
' "$APPROVED" >/dev/null 2>&1 \
  || { echo "ERROR: approved.json requires matching feature and human approved_by" >&2; exit 1; }

CANDIDATES="${WS}/.adlc5/${FEATURE}/memory/promotion-candidates.md"

export WIKI_WS="$WS" WIKI_ROOT_PATH="$WIKI" WIKI_APPROVED="$APPROVED"
export WIKI_CANDIDATES_PATH="$CANDIDATES" WIKI_FEATURE="$FEATURE"
python3 - <<'PY'
import json, os, pathlib, re, shutil

ws = pathlib.Path(os.environ["WIKI_WS"])
wiki = pathlib.Path(os.environ["WIKI_ROOT_PATH"])
feature = os.environ["WIKI_FEATURE"]
approved = json.loads(pathlib.Path(os.environ["WIKI_APPROVED"]).read_text(encoding="utf-8"))
candidates_path = pathlib.Path(os.environ["WIKI_CANDIDATES_PATH"])
candidates_text = candidates_path.read_text(encoding="utf-8") if candidates_path.exists() else ""
items = approved.get("candidates", [])
allowed_actions = {"promote_entity", "promote_concept", "reject", "investigate"}
workspace_root = ws.resolve()
wiki_root = wiki.resolve()
if wiki_root == workspace_root or not wiki_root.is_relative_to(workspace_root):
    raise SystemExit("ERROR: wiki root must stay inside the workspace")
allowed_roots = {
    "promote_entity": (wiki / "entities").resolve(),
    "promote_concept": (wiki / "concepts").resolve(),
}
if any(root == wiki_root or not root.is_relative_to(wiki_root) for root in allowed_roots.values()):
    raise SystemExit("ERROR: wiki entities/concepts roots must stay inside the wiki")

for item in items:
    if not isinstance(item, dict) or item.get("action") not in allowed_actions:
        raise SystemExit(f"ERROR: unknown promotion action: {item.get('action') if isinstance(item, dict) else item}")
    action = item["action"]
    if action in ("reject", "investigate"):
        continue
    target = item.get("target", "")
    dest = (ws / target).resolve()
    root = allowed_roots[action]
    if not target or dest == root or not dest.is_relative_to(root):
        raise SystemExit(f"ERROR: {action} target must stay under {root}: {target}")

def extract_section(cid):
    parts = re.split(r"(?:^|\n)###\s+", candidates_text, flags=re.MULTILINE)
    for p in parts[1:]:
        if p.strip().startswith(cid):
            return "### " + p.strip()
    return None

applied = 0
for item in items:
    action = item.get("action")
    target = item.get("target", "")
    cid = item.get("id", "")
    if action in ("reject", "investigate"):
        continue
    if not target:
        print(f"SKIP: no target for {cid}")
        continue
    dest = ws / target
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = extract_section(cid) or f"### {cid}\n\n(promoted from feature {feature})\n"
    if dest.exists():
        with open(dest, "a", encoding="utf-8") as f:
            f.write(f"\n\n## Promoted ({feature})\n\n{body}\n")
    else:
        tpl = wiki / "entities" / "_template.md"
        if tpl.exists() and "entities" in target:
            shutil.copy(tpl, dest)
        dest.write_text(body + "\n", encoding="utf-8")
    applied += 1
    print(f"APPLIED: {cid} -> {target}")

print(f"OK: applied {applied} candidate(s)")
PY

"${SCRIPT_DIR}/rebuild-index.sh" --workspace "$WS" --wiki-root "$WIKI_ROOT"
wiki_log_append "${WIKI}/log.md" "promote-apply" "${FEATURE}"

echo "OK: Promotion applied for ${FEATURE}"
