#!/usr/bin/env bash
# ADLC5 — initialize feature with unified state, memory, evidence log.
set -euo pipefail

FEATURE=""
WORKSPACE="."
MODE="auto"
INTERACTION="hitl"
SCOPE="epic"

usage() {
  cat <<'EOF'
Usage: ./scripts/init-feature.sh --feature NAME [OPTIONS]

Options:
  --workspace DIR       Project root (default: .)
  --mode MODE           greenfield | brownfield | auto (default: auto — detect via profile-repo.py)
  --scope TYPE          epic | increment | spike (default: epic)
  --interaction MODE    hitl | autonomous (default: hitl)
  --dry-run             Print actions without writing
EOF
  exit 1
}

DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature) FEATURE="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --mode) MODE="${2:?}"; shift 2 ;;
    --scope) SCOPE="${2:?}"; shift 2 ;;
    --interaction) INTERACTION="${2:?}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage ;;
    *) echo "Unknown: $1" >&2; usage ;;
  esac
done

[[ -n "$FEATURE" ]] || usage
[[ "$FEATURE" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || {
  echo "ERROR: feature name must be kebab-case" >&2
  exit 1
}

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/adlc5-dirs.sh
source "${ROOT}/scripts/lib/adlc5-dirs.sh"
if adlc5_inside_package "$ROOT" "$WORKSPACE"; then
  echo "ERROR: --workspace ${WORKSPACE} is inside the installed ADLC5 package ${ROOT}; pass your repository" >&2
  exit 2
fi

REPO_SIZE="unknown"
WIKI_ACTION="skip"
if [[ "$MODE" == "auto" ]]; then
  PROFILE_JSON="$("${ROOT}/scripts/profile-repo.py" --workspace "$WORKSPACE")"
  MODE="$(printf '%s' "$PROFILE_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["repo_profile"])')"
  REPO_SIZE="$(printf '%s' "$PROFILE_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["repo_size"])')"
  WIKI_ACTION="$(printf '%s' "$PROFILE_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["wiki"]["action"])')"
  echo "Repo profile: ${MODE} (${REPO_SIZE}) · wiki: ${WIKI_ACTION}"
fi

[[ "$MODE" == "greenfield" || "$MODE" == "brownfield" ]] || {
  echo "ERROR: --mode must be greenfield, brownfield, or auto" >&2
  exit 1
}

# Ensure repo-level context before feature SDD starts. Constitution files are
# create-only under .agents/ (legacy .agent/ yaml is copied when dest is missing);
# generated intelligence is safe to refresh from current source.
REPOSITORY_CONTEXT="${ROOT}/scripts/repository-context.py"
if [[ -f "$REPOSITORY_CONTEXT" ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] repo-spec init --workspace ${WORKSPACE}"
    echo "[dry-run] repo-index refresh --workspace ${WORKSPACE}"
  else
    python3 "$REPOSITORY_CONTEXT" repo-spec init --workspace "$WORKSPACE"
    python3 "$REPOSITORY_CONTEXT" repo-index refresh --workspace "$WORKSPACE"
  fi
fi
FEATURE_DIR="${WORKSPACE}/.adlc5/${FEATURE}"
NOW="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# Feature lifecycle state is worktree-local by design (parallel worktrees run
# different features). Two worktrees holding the SAME feature would diverge
# silently, so warn — never merge or symlink state automatically.
if [[ -f "${ROOT}/scripts/lib/worktree-context.sh" && ! -d "$FEATURE_DIR" ]]; then
  # shellcheck source=lib/worktree-context.sh
  source "${ROOT}/scripts/lib/worktree-context.sh"
  PEER_WORKTREES="$(adlc5_feature_peers "$WORKSPACE" "$FEATURE" || true)"
  if [[ -n "$PEER_WORKTREES" ]]; then
    echo "WARNING: feature '${FEATURE}' already has lifecycle state in another worktree:" >&2
    while IFS= read -r peer_wt; do
      [[ -n "$peer_wt" ]] && echo "  ${peer_wt}/.adlc5/${FEATURE}" >&2
    done <<EOF
${PEER_WORKTREES}
EOF
    echo "  Creating a second copy here means two diverging records of one feature." >&2
    echo "  Continue only if this is deliberate; otherwise work in that worktree instead." >&2
  fi
fi

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

mkdir_or_dry() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] mkdir -p $*"
  else
    mkdir -p "$@"
  fi
}

write_or_dry() {
  local path="$1"
  shift
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] write $path"
  else
    printf '%s\n' "$@" >"$path"
  fi
}

if [[ -f "${FEATURE_DIR}/state.json" && "$DRY_RUN" -eq 0 ]]; then
  echo "ERROR: ${FEATURE_DIR}/state.json already exists" >&2
  exit 1
fi

mkdir_or_dry \
  "${FEATURE_DIR}/memory/summaries" \
  "${FEATURE_DIR}/memory/context-packs" \
  "${FEATURE_DIR}/design" \
  "${FEATURE_DIR}/tasks/code-spec" \
  "${FEATURE_DIR}/evidence" \
  "${FEATURE_DIR}/docs"

EVIDENCE_LOG="${FEATURE_DIR}/evidence/events.jsonl"
INDEX_PATH="${FEATURE_DIR}/memory/INDEX.md"

STATE_JSON=$(cat <<EOF
{
  "schema_version": "3.0",
  "feature": "${FEATURE}",
  "current_stage": "specify",
  "current_step": "specify-0-git",
  "stage_status": {
    "specify": "in_progress",
    "plan": "pending",
    "tasks": "pending",
    "implement": "pending"
  },
  "scope": {
    "type": "${SCOPE}",
    "repo_profile": "${MODE}",
    "repo_size": "${REPO_SIZE}"
  },
  "git": {
    "isolation": "pending",
    "branch_name": "feat/${FEATURE}",
    "base_branch": "main",
    "worktree_path": null,
    "workstreams": [],
    "pr_stack": []
  },
  "scale_nfrs": {},
  "craftsmanship": {
    "architecture_review": "pending",
    "pattern_selection": "pending",
    "algorithm_review": "not_applicable",
    "pattern_opportunity": "pending"
  },
  "tasks": {
    "stories": [],
    "parallel_batches": []
  },
  "implement": {
    "current_substep": "implement-1-build",
    "story_status": {},
    "verification": { "status": "pending", "reports": {} },
    "integration": { "status": "pending" },
    "qa": { "status": "pending", "clearance_path": ".qa/${FEATURE}/deployment-clearance.md" },
    "pr": { "status": "pending", "url": null }
  },
  "memory": {
    "index_path": ".adlc5/${FEATURE}/memory/INDEX.md",
    "last_compacted": null,
    "context_budget_tokens": 8000,
    "context_pack_policy": "subagent_minimal"
  },
  "autopilot": {
    "mode": "${INTERACTION}",
    "endpoint": "pr_ready",
    "profile": "epic",
    "iteration": 0
  },
  "evidence": {
    "log_path": ".adlc5/${FEATURE}/evidence/events.jsonl"
  },
  "clarity": {
    "score": null,
    "threshold": 80,
    "history": []
  },
  "release": {
    "version": "0.1.0"
  },
  "policies_path": ".adlc5/${FEATURE}/policies.yaml",
  "persona": {
    "active": "analyst",
    "history": []
  },
  "created_at": "${NOW}",
  "updated_at": "${NOW}"
}
EOF
)

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] write ${FEATURE_DIR}/state.json"
else
  printf '%s\n' "$STATE_JSON" >"${FEATURE_DIR}/state.json"
fi

INDEX_MD=$(cat <<EOF
# ADLC5 Working Memory — ${FEATURE}

**Updated:** ${NOW}
**Current stage:** specify
**Current step:** specify-0-git
**Last compacted:** —

## Retrieval rule

Read this file first. Load only artifacts listed below for active work.

## Artifact index

| Path | Stage | Summary (≤120 chars) |
|------|-------|------------------------|
| .adlc5/${FEATURE}/spec-handoff.md | specify | Pending |
| .adlc5/${FEATURE}/design/ | plan | Pending |

## Summaries

| Summary | Path |
|---------|------|
| Specify | memory/summaries/specify.md |
| Plan | memory/summaries/plan.md |
| Tasks | memory/summaries/tasks.md |
| Implement | memory/summaries/implement.md |
EOF
)

write_or_dry "$INDEX_PATH" "$INDEX_MD"

if [[ "$DRY_RUN" -eq 0 ]]; then
  touch "$EVIDENCE_LOG"
  echo "{\"ts\":\"${NOW}\",\"event\":\"feature_init\",\"feature\":\"${FEATURE}\",\"schema_version\":\"3.0\",\"repo_profile\":\"${MODE}\",\"repo_size\":\"${REPO_SIZE}\",\"wiki_action\":\"${WIKI_ACTION}\"}" >>"$EVIDENCE_LOG"
fi

if [[ "$WIKI_ACTION" != "skip" ]]; then
  run "${ROOT}/scripts/wiki/ensure-wiki.sh" --workspace "$WORKSPACE" ${DRY_RUN:+--dry-run} || {
    echo "WARN: wiki ensure failed — continue without wiki bootstrap" >&2
  }
fi

POLICIES="${FEATURE_DIR}/policies.yaml"
if [[ ! -f "$POLICIES" && "$DRY_RUN" -eq 0 ]]; then
  if [[ -f "${ROOT}/templates/policies.yaml.example" ]]; then
    cp "${ROOT}/templates/policies.yaml.example" "$POLICIES"
  fi
fi

echo "{\"status\":\"ok\",\"feature\":\"${FEATURE}\",\"state_path\":\".adlc5/${FEATURE}/state.json\",\"schema_version\":\"3.0\"}"
