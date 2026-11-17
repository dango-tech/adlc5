#!/usr/bin/env bash
# ADLC5 Git Isolation Script
# Performs branch creation or worktree setup for a new feature and outputs state JSON.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/git-isolation.sh [OPTIONS]

Options:
  --feature NAME        Kebab-case feature name (required)
  --action ACTION       branch | worktree | current | skip (required)
  --branch-name NAME    Branch name (default: feat/{feature})
  --base-branch BRANCH  Base branch (default: main)
  --worktree-dir PATH   Parent directory for worktrees (default: .worktrees)
EOF
  exit 1
}

FEATURE=""
ACTION=""
BRANCH_NAME=""
BASE_BRANCH="main"
WORKTREE_DIR=".worktrees"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature) FEATURE="$2"; shift 2 ;;
    --action) ACTION="$2"; shift 2 ;;
    --branch-name) BRANCH_NAME="$2"; shift 2 ;;
    --base-branch) BASE_BRANCH="$2"; shift 2 ;;
    --worktree-dir) WORKTREE_DIR="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; usage ;;
  esac
done

if [[ -z "$FEATURE" || -z "$ACTION" ]]; then
  echo "ERROR: --feature and --action are required" >&2
  usage
fi

if [[ -z "$BRANCH_NAME" ]]; then
  BRANCH_NAME="feat/${FEATURE}"
fi

# Detect Git
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if [[ "$ACTION" != "skip" ]]; then
    echo "ERROR: Not inside a git repository." >&2
    exit 1
  fi
fi

REPO_ROOT=""
if [[ "$ACTION" != "skip" ]]; then
  REPO_ROOT="$(git rev-parse --show-toplevel)"
fi

CURRENT_BRANCH=""
if [[ "$ACTION" != "skip" ]]; then
  CURRENT_BRANCH="$(git branch --show-current)"
fi

STATUS="completed"

case "$ACTION" in
  branch)
    git fetch origin 2>/dev/null || true
    if git rev-parse --verify "$BRANCH_NAME" >/dev/null 2>&1; then
      git switch "$BRANCH_NAME" >&2
    else
      git switch -c "$BRANCH_NAME" "$BASE_BRANCH" >&2
    fi
    ;;
  worktree)
    # Check if ignore file ignores worktree parent dir
    if [[ -f "${REPO_ROOT}/.gitignore" ]]; then
      if ! grep -q "^${WORKTREE_DIR}/" "${REPO_ROOT}/.gitignore"; then
        echo "${WORKTREE_DIR}/" >> "${REPO_ROOT}/.gitignore"
        echo "Added ${WORKTREE_DIR}/ to .gitignore" >&2
      fi
    fi
    mkdir -p "${REPO_ROOT}/${WORKTREE_DIR}"
    WORKTREE_TARGET="${REPO_ROOT}/${WORKTREE_DIR}/${BRANCH_NAME}"
    
    if git rev-parse --verify "$BRANCH_NAME" >/dev/null 2>&1; then
      git worktree add "$WORKTREE_TARGET" "$BRANCH_NAME" >&2
    else
      git worktree add "$WORKTREE_TARGET" -b "$BRANCH_NAME" "$BASE_BRANCH" >&2
    fi
    ;;
  current)
    BRANCH_NAME="$CURRENT_BRANCH"
    ;;
  skip)
    STATUS="waived"
    BRANCH_NAME="null"
    ;;
  *)
    echo "ERROR: Invalid action: $ACTION" >&2
    exit 1
    ;;
esac

COMPLETED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Output Git state JSON for the skill to capture and merge into state.json.
START_COMMIT=""
if [[ "$ACTION" == "worktree" ]]; then
  START_COMMIT="$(git -C "$WORKTREE_TARGET" rev-parse HEAD)"
elif [[ "$ACTION" != "skip" ]]; then
  START_COMMIT="$(git rev-parse HEAD)"
fi

jq -n --arg status "$STATUS" --arg isolation "$ACTION" --arg branch "$BRANCH_NAME" \
  --arg base "$BASE_BRANCH" --arg path "${WORKTREE_TARGET:-}" --arg root "$REPO_ROOT" \
  --arg commit "$START_COMMIT" --arg at "$COMPLETED_AT" \
  '{status:$status, isolation:$isolation, branch_name:($branch | select(. != "null") // null),
    base_branch:$base, worktree_path:($path | select(length > 0) // null),
    repository_root:($root | select(length > 0) // null),
    start_commit:($commit | select(length > 0) // null), completed_at:$at}'
