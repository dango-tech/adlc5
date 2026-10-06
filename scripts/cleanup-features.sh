#!/usr/bin/env bash
# Safe cleanup of aged .adlc5/{feature}/ trees.
# Default action is archive (not delete). Default mode is dry-run.
# Never permanently deletes without --delete.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

WORKSPACE="."
OLDER_THAN_DAYS=90
DELETE=0
DRY_RUN=1

usage() {
  cat <<'EOF'
Usage: cleanup-features.sh [OPTIONS]

List, archive, or delete aged ADLC5 feature trees under .adlc5/{feature}/.

Safety:
  - Default is dry-run (print candidates; no filesystem changes).
  - Default action is archive → .adlc5/_archive/{feature}-YYYYMMDD
  - Pass --archive to actually move candidates into _archive/
  - On successful archive, writes an OKF Feature summary (FEATURE.md + _archive/index.md)
  - Pass --delete to permanently remove candidates (never the default)
  - Skips features already present under _archive/ (same name prefix)
  - Never runs automatically from install.sh

Options:
  --workspace DIR       Project root (default: .)
  --older-than N        Only features with state.json mtime older than N days (default: 90)
  --status NAME         complete | abandoned (repeatable). Omit = both when archiving/deleting/listing.
  --archive             Actually move matching feature dirs into .adlc5/_archive/
  --delete              Permanently remove matching feature directories (explicit; not default)
  --dry-run             Print actions only (default). Combine with --delete to preview deletes.
  -h, --help

Status rules:
  complete   — all of specify/plan/tasks/implement are completed or waived
  abandoned  — state.lifecycle_status == "abandoned" OR file ABANDONED exists

OKF archive summary (on --archive):
  .adlc5/_archive/{feature}-YYYYMMDD/FEATURE.md          # includes a Usage section
  .adlc5/_archive/{feature}-YYYYMMDD/usage-summary.json  # when usage was recorded
  .adlc5/_archive/index.md
  wiki/concepts/feature-{feature}.md   # only when consumer wiki/ exists

Model/token usage ledger (.adlc5/{feature}/memory/usage-ledger.jsonl, written via
`./scripts/adlc5 usage record`) moves with the feature tree on archive; FEATURE.md and
usage-summary.json are derived from it by the OKF summarizer.

Examples:
  ./scripts/cleanup-features.sh --workspace . --dry-run
  ./scripts/cleanup-features.sh --workspace . --status complete --older-than 30 --archive
  ./scripts/cleanup-features.sh --workspace . --status complete --older-than 30 --delete
  ./scripts/adlc5 cleanup-features --workspace . --status abandoned --older-than 14 --dry-run

Opt-in from update (dry-run archive preview unless --prune-features-delete):
  ./scripts/update-adlc5.sh --self --prune-features --prune-features-older-than 90
EOF
}

STATUSES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --older-than) OLDER_THAN_DAYS="${2:?}"; shift 2 ;;
    --status) STATUSES+=("${2:?}"); shift 2 ;;
    --archive) DELETE=0; DRY_RUN=0; shift ;;
    --delete) DELETE=1; DRY_RUN=0; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 1 ;;
  esac
done

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
ADLC5_DIR="${WORKSPACE}/.adlc5"
ARCHIVE_DIR="${ADLC5_DIR}/_archive"
STAMP="$(date +%Y%m%d)"

if [[ ! -d "$ADLC5_DIR" ]]; then
  echo "No .adlc5 directory at ${ADLC5_DIR}"
  exit 0
fi

if [[ ${#STATUSES[@]} -eq 0 ]]; then
  STATUSES=(complete abandoned)
fi

is_complete() {
  local state_file="$1"
  python3 - "$state_file" <<'PY'
import json, sys
try:
    state = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    sys.exit(1)
ss = state.get("stage_status") or {}
needed = ("specify", "plan", "tasks", "implement")
ok = {"completed", "waived"}
for k in needed:
    if ss.get(k) not in ok:
        sys.exit(1)
sys.exit(0)
PY
}

is_abandoned() {
  local feature_dir="$1" state_file="$2"
  [[ -f "${feature_dir}/ABANDONED" ]] && return 0
  python3 - "$state_file" <<'PY'
import json, sys
try:
    state = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    sys.exit(1)
sys.exit(0 if state.get("lifecycle_status") == "abandoned" else 1)
PY
}

already_archived() {
  local name="$1"
  local hit
  shopt -s nullglob
  for hit in "${ARCHIVE_DIR}/${name}-"*; do
    [[ -e "$hit" ]] || continue
    shopt -u nullglob
    return 0
  done
  shopt -u nullglob
  return 1
}

SUMMARIZE_OKF="${ROOT}/scripts/memory/summarize-feature-okf.py"

write_okf_summary() {
  local feature_dir="$1"
  local dry="$2"
  local args=(--feature-dir "$feature_dir" --workspace "$WORKSPACE")
  [[ "$dry" -eq 1 ]] && args+=(--dry-run)
  if [[ ! -f "$SUMMARIZE_OKF" ]]; then
    echo "    warning: OKF summarizer missing: ${SUMMARIZE_OKF}" >&2
    return 0
  fi
  python3 "$SUMMARIZE_OKF" "${args[@]}"
}

# macOS find -mtime: +N means strictly older than N*24h
candidates=()
reasons=()
names=()

shopt -s nullglob
for feature_dir in "${ADLC5_DIR}"/*/; do
  name="$(basename "$feature_dir")"
  # Skip non-feature scaffolding and archive store
  case "$name" in
    governance|memory|wiki|_archive) continue ;;
  esac
  state_file="${feature_dir}state.json"
  [[ -f "$state_file" ]] || continue

  # Age filter via find on this single path
  if [[ -n "$(find "$state_file" -mtime +"${OLDER_THAN_DAYS}" 2>/dev/null)" ]]; then
    :
  else
    continue
  fi

  matched=""
  for st in "${STATUSES[@]}"; do
    case "$st" in
      complete)
        if is_complete "$state_file"; then matched="complete"; break; fi
        ;;
      abandoned)
        if is_abandoned "$feature_dir" "$state_file"; then matched="abandoned"; break; fi
        ;;
    esac
  done
  [[ -n "$matched" ]] || continue

  candidates+=("$feature_dir")
  reasons+=("$matched")
  names+=("$name")
done
shopt -u nullglob

action_label="archive"
[[ "$DELETE" -eq 1 ]] && action_label="delete"

echo "Feature cleanup scan: workspace=${WORKSPACE} older_than=${OLDER_THAN_DAYS}d statuses=${STATUSES[*]} action=${action_label} dry_run=${DRY_RUN}"
echo "Candidates: ${#candidates[@]}"

if [[ ${#candidates[@]} -eq 0 ]]; then
  exit 0
fi

i=0
for feature_dir in "${candidates[@]}"; do
  name="${names[$i]}"
  dest="${ARCHIVE_DIR}/${name}-${STAMP}"
  echo "  [${reasons[$i]}] ${feature_dir%/}"

  if [[ "$DELETE" -eq 1 ]]; then
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "    [dry-run] would delete ${feature_dir%/}"
    else
      rm -rf "$feature_dir"
      echo "    deleted"
    fi
  else
    if already_archived "$name"; then
      echo "    skipped (already archived under ${ARCHIVE_DIR}/${name}-*)"
    elif [[ "$DRY_RUN" -eq 1 ]]; then
      echo "    [dry-run] would archive → ${dest}"
      echo "    [dry-run] would write OKF summary → ${dest}/FEATURE.md"
      echo "    [dry-run] would update OKF index → ${ARCHIVE_DIR}/index.md"
      if [[ -d "${WORKSPACE}/wiki" ]]; then
        echo "    [dry-run] would mirror → ${WORKSPACE}/wiki/concepts/feature-${name}.md"
      fi
    else
      mkdir -p "$ARCHIVE_DIR"
      if [[ -e "$dest" ]]; then
        echo "    skipped (destination exists: ${dest})"
      else
        mv "$feature_dir" "$dest"
        echo "    archived → ${dest}"
        if write_okf_summary "$dest" 0 >/tmp/adlc5-okf-summary.json; then
          echo "    OKF summary → ${dest}/FEATURE.md"
        else
          echo "    warning: OKF summary failed (archive kept at ${dest})" >&2
        fi
      fi
    fi
  fi
  i=$((i + 1))
done

if [[ "$DRY_RUN" -eq 1 ]]; then
  if [[ "$DELETE" -eq 1 ]]; then
    echo "No deletions performed (dry-run). Re-run with --delete (without --dry-run) to remove candidates."
  else
    echo "No archives performed (dry-run). Re-run with --archive to move candidates into .adlc5/_archive/."
    echo "Permanent remove requires explicit --delete."
  fi
fi
