#!/usr/bin/env bash
# Update ADLC5 distribution (git pull) and re-install skills for one or all platforms.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLATFORM=""
SELF=0
GLOBAL=0
DRY_RUN=0
SKIP_PULL=0
WORKSPACE=""
PRUNE_FEATURES=0
PRUNE_FEATURES_OLDER_THAN=90
PRUNE_FEATURES_DELETE=0
KEEP_BACKUP=0

usage() {
  cat <<'EOF'
Usage: ./scripts/update-adlc5.sh [OPTIONS]

Agent prompt → command mapping (do not invent steps):
  "update adlc5 for yourself" / "update adlc5 for yourself to latest"
      → ./scripts/update-adlc5.sh --self
         (or --platform <host> when host is known)
  "update adlc5 globally"
      → ./scripts/update-adlc5.sh --global
         (same as --platform all)

Options:
  --self              Detect host platform and reinstall that platform only
  --global            Reinstall all platforms (alias: --platform all)
  --platform NAME     cursor | claude | codex | opencode | gemini | hermes | antigravity | all
  --workspace DIR     Consumer workspace; used to read .adlc5/config.yaml adlc5_root
                      Also used as target for optional --prune-features
  --skip-pull         Skip git fetch/pull (reinstall only)
  --keep-backup       Pass through to install.sh (skip aged backup prune)
  --prune-features    Opt-in: dry-run archive preview of aged complete/abandoned
                      .adlc5/{feature}/ (default action is archive, not delete)
  --prune-features-delete
                      With --prune-features: permanently delete matching feature trees
                      (explicit; never default — prefer cleanup-features.sh --archive)
  --prune-features-older-than N
                      Age filter in days for --prune-features (default: 90)
  --dry-run           Print planned actions without mutating git or install targets
  -h, --help          Show help

Root discovery order:
  1. ADLC5_ROOT env
  2. .adlc5/config.yaml adlc5_root (from --workspace or cwd)
  3. This script's parent (when run from an adlc5 clone)

Prints VERSION before and after. See shared/docs/INSTALL.md § Agent self-update.
EOF
}

get_yaml_value() {
  local key="$1" file="$2" raw
  [[ -f "$file" ]] || return 0
  raw="$(grep -E "^${key}:" "$file" | head -1 | sed -E "s/^${key}:[[:space:]]*//")"
  case "$raw" in
    \"*) raw="${raw#\"}"; printf '%s\n' "${raw%%\"*}" ;;            # double-quoted: keep any ` #` inside
    \'*) printf '%s\n' "$raw" | sed -E "s/^'(([^']|'')*)'.*$/\\1/; s/''/'/g" ;;  # single-quoted ('' is a literal ')
    *) printf '%s\n' "$raw" | sed -E 's/[[:space:]]+#.*$//' ;;      # plain: a ` #` starts a comment
  esac
}

expand_path() {
  local path="$1"
  if [[ "$path" == "~" ]]; then printf '%s\n' "$HOME"
  elif [[ "$path" == "~/"* ]]; then printf '%s/%s\n' "$HOME" "${path:2}"
  else printf '%s\n' "$path"; fi
}

resolve_root() {
  local candidate=""
  is_adlc5_root() {
    local r="$1"
    [[ -x "${r}/scripts/install.sh" ]] || return 1
    [[ -f "${r}/core/VERSION" || -f "${r}/v2/core/VERSION" ]]
  }

  if [[ -n "${ADLC5_ROOT:-}" ]]; then
    candidate="$(expand_path "$ADLC5_ROOT")"
    if is_adlc5_root "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  fi

  local search_dirs=()
  [[ -n "$WORKSPACE" ]] && search_dirs+=("$WORKSPACE")
  search_dirs+=("$PWD")
  local d cfg val
  for d in "${search_dirs[@]}"; do
    cfg="${d}/.adlc5/config.yaml"
    val="$(get_yaml_value adlc5_root "$cfg")"
    if [[ -n "$val" ]]; then
      candidate="$(expand_path "$val")"
      if is_adlc5_root "$candidate"; then
        printf '%s\n' "$candidate"
        return 0
      fi
    fi
  done

  if is_adlc5_root "$ROOT"; then
    printf '%s\n' "$ROOT"
    return 0
  fi

  echo "ERROR: could not locate adlc5 clone (set ADLC5_ROOT or adlc5_root in .adlc5/config.yaml)" >&2
  exit 1
}

detect_host_platform() {
  if [[ -n "${ADLC5_PLATFORM:-}" ]]; then
    printf '%s\n' "${ADLC5_PLATFORM}"
    return 0
  fi
  if [[ -n "${CURSOR_AGENT:-}" || -n "${CURSOR_TRACE_ID:-}" || "${TERM_PROGRAM:-}" == "vscode" ]]; then
    printf '%s\n' "cursor"
    return 0
  fi
  if [[ -n "${CLAUDECODE:-}" || -n "${CLAUDE_CODE:-}" ]]; then
    printf '%s\n' "claude"
    return 0
  fi
  if [[ -n "${CODEX_HOME:-}" || -n "${CODEX_CI:-}" ]]; then
    printf '%s\n' "codex"
    return 0
  fi
  if [[ -n "${OPENCODE:-}" || -n "${OPENCODE_CONFIG:-}" ]]; then
    printf '%s\n' "opencode"
    return 0
  fi
  if [[ -n "${HERMES_HOME:-}" || -n "${HERMES_AGENT:-}" ]]; then
    printf '%s\n' "hermes"
    return 0
  fi
  if [[ -n "${GEMINI_CLI:-}" || -n "${ANTIGRAVITY:-}" ]]; then
    printf '%s\n' "gemini"
    return 0
  fi
  # Default when running inside Cursor agent sessions without env markers
  printf '%s\n' "cursor"
}

print_version() {
  local label="$1" root="$2"
  local ver="unknown" vf
  if [[ -f "${root}/core/VERSION" ]]; then
    vf="${root}/core/VERSION"
  elif [[ -f "${root}/v2/core/VERSION" ]]; then
    vf="${root}/v2/core/VERSION"
  fi
  [[ -n "${vf:-}" ]] && ver="$(tr -d '[:space:]' <"$vf")"
  echo "ADLC5 version (${label}): ${ver}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --self) SELF=1; shift ;;
    --global) GLOBAL=1; shift ;;
    --platform) PLATFORM="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --skip-pull) SKIP_PULL=1; shift ;;
    --keep-backup) KEEP_BACKUP=1; shift ;;
    --prune-features) PRUNE_FEATURES=1; shift ;;
    --prune-features-delete) PRUNE_FEATURES_DELETE=1; shift ;;
    --prune-features-older-than) PRUNE_FEATURES_OLDER_THAN="${2:?}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 2 ;;
  esac
done

PRUNE_FEATURES_DELETE="${PRUNE_FEATURES_DELETE:-0}"

if [[ "$GLOBAL" -eq 1 ]]; then
  PLATFORM="all"
fi
if [[ "$SELF" -eq 1 && -z "$PLATFORM" ]]; then
  PLATFORM="$(detect_host_platform)"
fi
if [[ -z "$PLATFORM" ]]; then
  echo "ERROR: specify --self, --global, or --platform NAME" >&2
  usage >&2
  exit 2
fi

case "$PLATFORM" in
  cursor|claude|codex|opencode|gemini|hermes|antigravity|all) ;;
  *) echo "ERROR: unknown platform '${PLATFORM}'" >&2; exit 2 ;;
esac

ADLC5="$(resolve_root)"
cd "$ADLC5"

echo "ADLC5 root: ${ADLC5}"
if [[ -d "${ADLC5}/v2/skills" && ! -d "${ADLC5}/skills" ]]; then
  echo "WARNING: legacy v2/ layout detected (no root skills/). Pull latest 3.x (path lift) or re-clone, then re-run update." >&2
fi
print_version "before" "$ADLC5"
echo "Target platform: ${PLATFORM}"

if [[ "$SKIP_PULL" -eq 0 ]]; then
  if [[ ! -d "${ADLC5}/.git" ]]; then
    echo "WARNING: not a git checkout — skipping pull" >&2
  elif [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] git fetch --tags --prune && git pull --ff-only"
  else
    git fetch --tags --prune
    if ! git pull --ff-only; then
      echo "ERROR: git pull --ff-only failed (resolve local changes, then retry)" >&2
      exit 1
    fi
  fi
else
  echo "Skipping git pull (--skip-pull)"
fi

print_version "after-pull" "$ADLC5"

INSTALL_ARGS=(--platform "$PLATFORM")
if [[ "$KEEP_BACKUP" -eq 1 ]]; then
  INSTALL_ARGS+=(--keep-backup)
fi
if [[ "$DRY_RUN" -eq 1 ]]; then
  INSTALL_ARGS+=(--dry-run)
  echo "[dry-run] ./scripts/install.sh ${INSTALL_ARGS[*]}"
  ./scripts/install.sh "${INSTALL_ARGS[@]}"
else
  ./scripts/install.sh "${INSTALL_ARGS[@]}"
fi

# Opt-in feature tree cleanup (never silent; dry-run archive preview unless --prune-features-delete)
if [[ "$PRUNE_FEATURES" -eq 1 ]]; then
  feat_ws="${WORKSPACE:-$PWD}"
  feat_args=(--workspace "$feat_ws" --older-than "$PRUNE_FEATURES_OLDER_THAN")
  if [[ "${PRUNE_FEATURES_DELETE:-0}" -eq 1 && "$DRY_RUN" -eq 0 ]]; then
    feat_args+=(--delete)
  else
    feat_args+=(--dry-run)
  fi
  echo "Pruning features (opt-in): ./scripts/cleanup-features.sh ${feat_args[*]}"
  "${ADLC5}/scripts/cleanup-features.sh" "${feat_args[@]}"
fi

print_version "after-install" "$ADLC5"
echo "Update complete."
echo "Verify: ${ADLC5}/scripts/verify-install.sh --platform ${PLATFORM}"
