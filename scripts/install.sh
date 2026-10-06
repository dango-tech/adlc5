#!/usr/bin/env bash
# Install adlc5 skills and rules to user-global paths (M8 + M14 + M14g backup-replace).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/adlc5-dirs.sh
source "${ROOT}/scripts/lib/adlc5-dirs.sh"
SKILLS_ROOT="$(adlc5_skills_dir "$ROOT")"
cd "$ROOT"

PLATFORM="all"
DRY_RUN=0
KEEP_BACKUP=0
INSTALL_OK=0
RULES_ONLY=0
SKILLS_ONLY=0

BACKUP_ROOT=""
BACKUP_CREATED=0

usage() {
  cat <<'EOF'
Usage: ./scripts/install.sh [OPTIONS]

  --platform NAME   cursor | claude | codex | opencode | gemini | hermes | antigravity | all (default: all)
  --rules-only      Install Cursor rules globally only (~/.cursor/rules) — recommended once per machine
  --skills-only     Install skills globally only (skip rules)
  --dry-run         Print actions without creating symlinks or backups
  --keep-backup     Keep this run's backup AND skip aged backup prune (default: prune aged backups)
  --print-version   Print ADLC5 semver from core/VERSION and exit
  -h, --help        Show help

Version source of truth: core/VERSION
Update in place: ./scripts/update-adlc5.sh --self | --global

Project-local setup (recommended for app repos):
  ./scripts/init-workspace.sh --project /path/to/your-app
EOF
}

adlc5_version() {
  local f="${ROOT}/core/VERSION"
  if [[ -f "$f" ]]; then tr -d '[:space:]' <"$f"
  else echo "0.0.0"; fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform) PLATFORM="${2:?}"; shift 2 ;;
    --version) shift 2 ;; # legacy ignored arg; use --print-version
    --print-version) echo "adlc5 $(adlc5_version)"; exit 0 ;;
    --rules-only) RULES_ONLY=1; shift ;;
    --skills-only) SKILLS_ONLY=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --keep-backup) KEEP_BACKUP=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 1 ;;
  esac
done

echo "Installing adlc5 $(adlc5_version) (platform=${PLATFORM})"

if [[ -d "${ROOT}/v2/skills" && ! -d "${ROOT}/skills" ]]; then
  echo "ERROR: this clone still uses the legacy v2/ layout." >&2
  echo "  Upgrade the distribution to 4.x (root skills/, core/, …), then re-run install." >&2
  exit 1
fi
if [[ ! -f "${ROOT}/core/VERSION" ]]; then
  echo "ERROR: missing core/VERSION (semver source of truth)" >&2
  exit 1
fi

# Check kernel prerequisites before writing configuration or install targets.
for tool in git python3 jq; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "ERROR: required tool '$tool' is missing. Install Git, Python 3 and jq, then retry." >&2
    exit 1
  }
done
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "ERROR: Python 3.10 or newer is required; upgrade python3, then retry." >&2
  exit 1
fi


CONFIG="${ROOT}/config.yaml"
if [[ ! -f "$CONFIG" ]]; then
  if [[ -f "${ROOT}/config.example.yaml" ]]; then
    if [[ "$DRY_RUN" -eq 1 ]]; then
      CONFIG="${ROOT}/config.example.yaml"
    else
      cp "${ROOT}/config.example.yaml" "$CONFIG"
      echo "Created config.yaml from config.example.yaml"
    fi
  else
    echo "ERROR: config.yaml not found" >&2
    exit 1
  fi
fi

get_yaml_value() {
  local key="$1" file="$2"
  grep -E "^${key}:" "$file" | head -1 | sed -E "s/^${key}:[[:space:]]*//" | sed -E 's/^["'\''](.*)["'\'']$/\1/' | sed -E 's/[[:space:]]+#.*$//'
}

get_path() {
  local key="$1" default="$2"
  local val
  val="$(get_yaml_value "$key" "$CONFIG")"
  if [[ -z "$val" && -f "${ROOT}/config.example.yaml" ]]; then
    val="$(get_yaml_value "$key" "${ROOT}/config.example.yaml")"
  fi
  if [[ -z "$val" ]]; then val="$default"; fi
  expand_path "$val"
}

expand_path() {
  local path="$1"
  if [[ "$path" == "~" ]]; then printf '%s\n' "$HOME"
  elif [[ "$path" == "~/"* ]]; then printf '%s/%s\n' "$HOME" "${path:2}"
  else printf '%s\n' "$path"; fi
}

# Refuse installs into the adlc5 clone (prevents self-referential symlinks under skills/).
assert_safe_install_target() {
  local target="$1" label="$2"
  local abs_target abs_skills
  abs_target="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$target")"
  abs_skills="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$SKILLS_ROOT")"
  if [[ "$abs_target" == "$abs_skills" || "$abs_target" == "${abs_skills}/"* ]]; then
    echo "ERROR: ${label} resolves inside the adlc5 clone (${abs_target})." >&2
    echo "  Use a user-global path in config.yaml, or init a consumer project:" >&2
    echo "  ./scripts/init-workspace.sh --project /path/to/your-app" >&2
    exit 1
  fi
}

has_antigravity_plugin_target() {
  local val
  val="$(get_yaml_value antigravity_plugin_target "$CONFIG")"
  [[ -n "$val" ]] && return 0
  [[ -f "${ROOT}/config.example.yaml" ]] && val="$(get_yaml_value antigravity_plugin_target "${ROOT}/config.example.yaml")"
  [[ -n "$val" ]]
}

get_antigravity_plugin_root() {
  get_path antigravity_plugin_target "~/.gemini/config/plugins/adlc5-plugin"
}

init_backup_root() {
  local base
  base="$(get_path install_backup_root "~/.adlc5-install-backup")"
  local ts
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  BACKUP_ROOT="${base}/${ts}"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "Backup root (dry-run): ${BACKUP_ROOT}"
  else
    mkdir -p "$BACKUP_ROOT"
    BACKUP_CREATED=1
    echo "Backup root: ${BACKUP_ROOT}"
  fi
  echo
}

backup_entry() {
  local dest="$1" platform_slug="$2" entry_name="$3"
  local backup_dest="${BACKUP_ROOT}/${platform_slug}/${entry_name}"

  # Broken symlinks: -e is false but -L/-h is true — must still replace.
  if [[ ! -e "$dest" && ! -L "$dest" && ! -h "$dest" ]]; then
    return 0
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  [dry-run] backup: ${dest} -> ${backup_dest}"
    return 0
  fi

  mkdir -p "$(dirname "$backup_dest")"
  mv "$dest" "$backup_dest"
  echo "  Backed up: ${entry_name} (was at ${dest})"
}

cleanup_backup_on_success() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] would remove backup: ${BACKUP_ROOT}"
    return 0
  fi
  if [[ "$KEEP_BACKUP" -eq 1 ]]; then
    echo "Backup kept (--keep-backup): ${BACKUP_ROOT}"
    return 0
  fi
  if [[ "$BACKUP_CREATED" -eq 1 && -d "$BACKUP_ROOT" ]]; then
    rm -rf "$BACKUP_ROOT"
    echo "Removed install backup (success): ${BACKUP_ROOT}"
  fi
}

on_install_failure() {
  local exit_code=$?
  if [[ "$INSTALL_OK" -eq 1 ]]; then
    exit "$exit_code"
  fi
  echo >&2
  if [[ "$BACKUP_CREATED" -eq 1 && -d "$BACKUP_ROOT" ]]; then
    echo "Install failed — backup kept at: ${BACKUP_ROOT}" >&2
    echo "Restore manually: mv entries from backup paths back to install targets." >&2
  fi
  exit "$exit_code"
}

trap on_install_failure EXIT

link_path() {
  local src="$1" dest="$2" label="$3" platform_slug="$4"

  if [[ -L "$dest" ]]; then
    local current
    current="$(readlink "$dest" 2>/dev/null || true)"
    if [[ "$current" == "$src" ]]; then
      echo "  OK (already linked): ${label}"
      return 0
    fi
    backup_entry "$dest" "$platform_slug" "$label"
  elif [[ -e "$dest" ]]; then
    backup_entry "$dest" "$platform_slug" "$label"
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  [dry-run] link: ${label} -> ${dest}"
    return 0
  fi

  mkdir -p "$(dirname "$dest")"
  ln -s "$src" "$dest"
  echo "  Linked: ${label} -> ${dest}"
}

install_skills_to() {
  local target="$1" platform_slug="$2"
  assert_safe_install_target "$target" "skills target (${platform_slug})"
  echo "Skills (${platform_slug}): ${target}"
  local count=0

  for skill_dir in "${SKILLS_ROOT}"/*/; do
    [[ -d "$skill_dir" && -f "${skill_dir}/SKILL.md" ]] || continue
    local name
    name="$(basename "$skill_dir")"
    link_path "$skill_dir" "${target}/${name}" "$name" "$platform_slug"
    count=$((count + 1))
  done
  echo "  (${count} skills)"
  echo
}

install_cursor_rules() {
  local rules_target platform_slug="cursor-rules"
  rules_target="$(get_path rules_install_target "~/.cursor/rules")"
  echo "Rules (${platform_slug}): ${rules_target}"
  local rule_file name
  for rule_file in "${ROOT}/.cursor/rules"/*.mdc; do
    [[ -f "$rule_file" ]] || continue
    name="$(basename "$rule_file")"
    link_path "$rule_file" "${rules_target}/${name}" "$name" "$platform_slug"
  done
  echo
}

platform_enabled() { [[ "$PLATFORM" == "all" || "$PLATFORM" == "$1" ]]; }

echo "Installing adlc5 from ${ROOT} (platform=${PLATFORM})"
[[ "$DRY_RUN" -eq 1 ]] && echo "(dry-run)"
[[ "$KEEP_BACKUP" -eq 1 ]] && echo "(--keep-backup: will not delete backup after success)"
echo

init_backup_root

prune_stale_install_artifacts() {
  if [[ ! -x "${ROOT}/scripts/cleanup-stale-skills.sh" ]]; then
    return 0
  fi
  local args=(--platform "$PLATFORM")
  if [[ "$RULES_ONLY" -ne 1 ]]; then
    args+=(--prune-stale-skills)
  fi
  if [[ "$SKILLS_ONLY" -ne 1 ]] && platform_enabled cursor; then
    args+=(--prune-stale-rules)
  fi
  # Aged backup prune is default on success path; --keep-backup opts out.
  if [[ "$KEEP_BACKUP" -eq 0 ]]; then
    args+=(--prune-backups)
  fi
  # If only keep-backup + rules-only with no skills/rules flags, still run something useful
  if [[ ${#args[@]} -eq 1 ]]; then
    args+=(--prune-stale-skills)
  fi
  "${ROOT}/scripts/cleanup-stale-skills.sh" "${args[@]}"
}

if [[ "$DRY_RUN" -ne 1 ]]; then
  echo "Cleaning stale ADLC5 install artifacts before install..."
  prune_stale_install_artifacts
  echo
fi

if [[ "$RULES_ONLY" -eq 1 && "$SKILLS_ONLY" -eq 1 ]]; then
  echo "ERROR: use only one of --rules-only or --skills-only" >&2
  exit 1
fi

if platform_enabled cursor; then
  if [[ "$RULES_ONLY" -ne 1 ]]; then
    install_skills_to "$(get_path skills_install_target "~/.agents/skills")" "cursor-agents"
    if [[ -x "${ROOT}/scripts/install-council-agents.sh" ]]; then
      echo "Installing Cursor council agents (discover/ideate)..."
      "${ROOT}/scripts/install-council-agents.sh"
      echo
    fi
  fi
  if [[ "$SKILLS_ONLY" -ne 1 ]]; then
    install_cursor_rules
  fi
fi
if [[ "$RULES_ONLY" -ne 1 ]]; then
  if platform_enabled claude; then
    install_skills_to "$(get_path claude_skills_target "~/.claude/skills")" "claude"
  fi
  if platform_enabled codex; then
    install_skills_to "$(get_path codex_skills_target "~/.codex/skills")" "codex"
  fi
  if platform_enabled opencode; then
    install_skills_to "$(get_path opencode_skills_target "~/.config/opencode/skills")" "opencode"
  fi
  if platform_enabled gemini; then
    install_skills_to "$(get_path gemini_skills_target "~/.gemini/skills")" "gemini"
  fi
  if platform_enabled hermes; then
    install_skills_to "$(get_path hermes_skills_target "~/.hermes/skills/adlc5")" "hermes"
  fi
  if platform_enabled antigravity; then
    if has_antigravity_plugin_target; then
      antigravity_plugin="$(get_antigravity_plugin_root)"
      assert_safe_install_target "$antigravity_plugin" "antigravity_plugin_target"
      if [[ "$DRY_RUN" -eq 0 ]]; then
        mkdir -p "$antigravity_plugin"
        # Stub only — kernel/MCP stay at distribution ROOT (ADLC5_ROOT); no path traversal into clone.
        if [[ ! -f "${antigravity_plugin}/plugin.json" ]]; then
          cat <<EOF > "${antigravity_plugin}/plugin.json"
{
  "name": "adlc5-plugin",
  "version": "$(adlc5_version)",
  "description": "ADLC5 $(adlc5_version) skills (via install.sh). Kernel: \$ADLC5_ROOT/scripts/adlc5; MCP: \$ADLC5_ROOT/scripts/adlc5-mcp.py",
  "skills": "./skills/"
}
EOF
          printf '%s\n' "$ROOT" > "${antigravity_plugin}/ADLC5_ROOT"
        elif [[ ! -f "${antigravity_plugin}/ADLC5_ROOT" ]]; then
          printf '%s\n' "$ROOT" > "${antigravity_plugin}/ADLC5_ROOT"
        fi
      else
        echo "  [dry-run] would ensure plugin.json + ADLC5_ROOT at ${antigravity_plugin}/"
      fi
      install_skills_to "${antigravity_plugin}/skills" "antigravity"
    else
      install_skills_to "$(get_path antigravity_skills_target "~/.gemini/antigravity/skills")" "antigravity"
    fi
  fi
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "Dry-run complete (no changes made)."
  echo "ADLC5_ROOT=${ROOT} (kernel: scripts/adlc5, MCP: scripts/adlc5-mcp.py)"
  trap - EXIT
  exit 0
fi

echo "Verifying install..."
if ! "${ROOT}/scripts/verify-install.sh" --platform "$PLATFORM"; then
  echo "Verification failed — backup kept at: ${BACKUP_ROOT}" >&2
  exit 1
fi

INSTALL_OK=1
trap - EXIT

cleanup_backup_on_success

echo "Cleaning stale ADLC5 install artifacts after install..."
prune_stale_install_artifacts
echo

echo
echo "Install complete (adlc5 $(adlc5_version)). See shared/docs/CROSS-PLATFORM.md"
echo "ADLC5_ROOT=${ROOT}"
echo "Kernel: ${ROOT}/scripts/adlc5"
echo "MCP:    ${ROOT}/scripts/adlc5-mcp.py"
echo "Cursor plugin manifest: ${ROOT}/.cursor-plugin/plugin.json"
echo "Self-update later: ./scripts/update-adlc5.sh --self | --global"
