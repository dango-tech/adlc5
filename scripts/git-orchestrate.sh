#!/usr/bin/env bash
# ADLC5 git orchestration — isolation, workstreams, stacked PR manifest.
set -euo pipefail

FEATURE=""
ACTION=""
WORKSPACE="."
WORKSTREAM_ID=""
STORIES=""
PR_URL=""

usage() {
  cat <<'EOF'
Usage: ./scripts/git-orchestrate.sh --feature NAME --action ACTION [OPTIONS]

Actions:
  branch|worktree|current|skip   Git isolation (delegates to git-isolation.sh)
  add-workstream                 Add parallel workstream (--workstream-id, --stories id1,id2)
  record-pr                      Record PR in pr_stack (--workstream-id, --pr-url)

Options:
  --workspace DIR
  --branch-name NAME
  --base-branch NAME  (default: main)
EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature) FEATURE="${2:?}"; shift 2 ;;
    --action) ACTION="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --workstream-id) WORKSTREAM_ID="${2:?}"; shift 2 ;;
    --stories) STORIES="${2:?}"; shift 2 ;;
    --pr-url) PR_URL="${2:?}"; shift 2 ;;
    --branch-name) BRANCH_NAME="${2:?}"; shift 2 ;;
    --base-branch) BASE_BRANCH="${2:?}"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Unknown: $1" >&2; usage ;;
  esac
done

[[ -n "$FEATURE" && -n "$ACTION" ]] || usage
command -v jq >/dev/null || { echo "ERROR: jq required" >&2; exit 1; }

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="${WORKSPACE}/.adlc5/${FEATURE}/state.json"
BRANCH_NAME="${BRANCH_NAME:-feat/${FEATURE}}"
BASE_BRANCH="${BASE_BRANCH:-main}"

case "$ACTION" in
  branch|worktree|current|skip)
    OUT=$("${ROOT}/scripts/git-isolation.sh" \
      --feature "$FEATURE" \
      --action "$ACTION" \
      --branch-name "$BRANCH_NAME" \
      --base-branch "$BASE_BRANCH")
    ISOLATION=$(echo "$OUT" | jq -r '.git.isolation // .isolation // empty')
    BRANCH=$(echo "$OUT" | jq -r '.git.branch_name // .branch_name // empty')
    WT=$(echo "$OUT" | jq -r '.git.worktree_path // .worktree_path // empty')
    if [[ -f "$STATE" ]]; then
      jq --arg iso "$ISOLATION" --arg br "$BRANCH" --arg wt "$WT" \
        '.git.isolation=$iso | .git.branch_name=$br | .git.worktree_path=(if $wt=="null" or $wt=="" then null else $wt end)' \
        "$STATE" >"${STATE}.tmp" && mv "${STATE}.tmp" "$STATE"
    fi
    echo "$OUT"
    ;;
  add-workstream)
    [[ -n "$WORKSTREAM_ID" ]] || { echo "ERROR: --workstream-id required" >&2; exit 1; }
    [[ -f "$STATE" ]] || { echo "ERROR: state.json missing" >&2; exit 1; }
    IFS=',' read -ra STORY_ARR <<< "${STORIES:-}"
    STORY_JSON=$(printf '%s\n' "${STORY_ARR[@]}" | jq -R . | jq -s .)
    WS_BRANCH="feat/${FEATURE}/${WORKSTREAM_ID}"
    WT_PATH="${WORKSPACE}/.worktrees/${FEATURE}-${WORKSTREAM_ID}"
    mkdir -p "${WORKSPACE}/.worktrees"
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      git worktree add -B "$WS_BRANCH" "$WT_PATH" "$BASE_BRANCH" 2>/dev/null || \
        git worktree add "$WT_PATH" "$WS_BRANCH" 2>/dev/null || true
    fi
    jq --arg id "$WORKSTREAM_ID" --arg br "$WS_BRANCH" --arg wt "$WT_PATH" --argjson stories "$STORY_JSON" \
      '.git.workstreams += [{"id":$id,"branch":$br,"worktree_path":$wt,"stories":$stories}]' \
      "$STATE" >"${STATE}.tmp" && mv "${STATE}.tmp" "$STATE"
    echo "{\"status\":\"ok\",\"workstream\":\"${WORKSTREAM_ID}\",\"branch\":\"${WS_BRANCH}\"}" | jq .
    ;;
  record-pr)
    [[ -n "$WORKSTREAM_ID" && -n "$PR_URL" ]] || { echo "ERROR: --workstream-id and --pr-url required" >&2; exit 1; }
    [[ -f "$STATE" ]] || { echo "ERROR: state.json missing" >&2; exit 1; }
    jq --arg ws "$WORKSTREAM_ID" --arg url "$PR_URL" \
      '.git.pr_stack += [{"workstream_id":$ws,"pr_url":$url,"status":"open"}]' \
      "$STATE" >"${STATE}.tmp" && mv "${STATE}.tmp" "$STATE"
    echo "{\"status\":\"ok\",\"pr_url\":\"${PR_URL}\"}" | jq .
    ;;
  *)
    echo "ERROR: unknown action $ACTION" >&2
    usage
    ;;
esac
