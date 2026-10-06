#!/usr/bin/env bash
# Prune stale ADLC5 skill/rule symlinks and aged install backups.
# install.sh / update-adlc5.sh / init-workspace.sh call this at the right time.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/adlc5-dirs.sh
source "${ROOT}/scripts/lib/adlc5-dirs.sh"
SKILLS_ROOT="$(adlc5_skills_dir "$ROOT")"
RULES_ROOT="${ROOT}/.cursor/rules"
cd "$ROOT"

PLATFORM="all"
DRY_RUN=0
PRUNE_SKILLS=0
PRUNE_RULES=0
PRUNE_BACKUPS=0
KEEP_BACKUP_DAYS=7
SKILL_TARGETS=()
RULE_TARGETS=()
BACKUP_ROOT_OVERRIDE=""

STALE_SKILL_NAMES=(
  adlc5-engineer
  adlc5-forge
  adlc5-forge-design
  adlc5-forge-stories
  adlc5-forge-code-spec
  adlc5-forge-implement
  adlc5-forge-verify
  adlc5-forge-integrate
  adlc5-forge-reworker
  forge-implementer
  forge-verifier
  pr-review
  adlc5-spec
  adlc5-engineering
  adlc5-plan-design
  adlc5-plan-stories
  adlc5-plan-code-spec
  adlc5-build
  adlc5-assure
  adlc5-assure-verify
  adlc5-assure-integrate
  adlc5-pilot
)

# Retired ADLC5-owned rule basenames (symlink names under rules targets).
STALE_RULE_NAMES=(
  adlc5-forge.mdc
  forge-discipline.mdc
)

ALLOWED_SKILL_NAMES=()
ALLOWED_RULE_NAMES=()

usage() {
  cat <<'EOF'
Usage: cleanup-stale-skills.sh [OPTIONS]

Prune stale or broken ADLC5 symlinks under skill/rule dirs, and aged install backups.

Options:
  --platform NAME        cursor | claude | codex | opencode | gemini | hermes | antigravity | all
  --skills-target DIR    Extra skills directory to prune (repeatable; project .agents/skills / tests)
  --rules-target DIR     Extra rules directory to prune (repeatable; tests/manual)
  --prune-stale-skills   Prune stale ADLC5 skill symlinks
  --prune-stale-rules    Prune retired ADLC5-owned rule symlinks only (never plain user files)
  --prune-backups        Remove install backup dirs older than KEEP_BACKUP_DAYS
  --backup-root DIR      Override install_backup_root (tests/manual)
  --keep-backup-days N   Default 7
  --dry-run              Print actions only
  -h, --help

When no prune flag is given, defaults to --prune-stale-skills only.

EOF
}

while [[ $# -gt 0 ]]; do
  [[ "$1" == \#* ]] && shift && continue
  case "$1" in
    --platform) PLATFORM="${2:?}"; shift 2 ;;
    --skills-target) SKILL_TARGETS+=("${2:?}"); shift 2 ;;
    --rules-target) RULE_TARGETS+=("${2:?}"); shift 2 ;;
    --prune-stale-skills) PRUNE_SKILLS=1; shift ;;
    --prune-stale-rules) PRUNE_RULES=1; shift ;;
    --prune-backups) PRUNE_BACKUPS=1; shift ;;
    --backup-root) BACKUP_ROOT_OVERRIDE="${2:?}"; shift 2 ;;
    --keep-backup-days) KEEP_BACKUP_DAYS="${2:?}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ "$PRUNE_SKILLS" -eq 0 && "$PRUNE_RULES" -eq 0 && "$PRUNE_BACKUPS" -eq 0 ]]; then
  PRUNE_SKILLS=1
fi

CONFIG="${ROOT}/config.yaml"
[[ -f "$CONFIG" ]] || CONFIG="${ROOT}/config.example.yaml"

get_yaml_value() {
  local key="$1" file="$2"
  grep -E "^${key}:" "$file" | head -1 | sed -E "s/^${key}:[[:space:]]*//" | sed -E 's/^["'\''](.*)["'\'']$/\1/' | sed -E 's/[[:space:]]+#.*$//'
}

expand_path() {
  local path="$1"
  if [[ "$path" == "~" ]]; then printf '%s\n' "$HOME"
  elif [[ "$path" == "~/"* ]]; then printf '%s/%s\n' "$HOME" "${path:2}"
  else printf '%s\n' "$path"; fi
}

get_path() {
  local key="$1" default="$2"
  local val
  val="$(get_yaml_value "$key" "$CONFIG")"
  [[ -z "$val" ]] && val="$default"
  expand_path "$val"
}

has_antigravity_plugin_target() {
  local val
  val="$(get_yaml_value antigravity_plugin_target "$CONFIG")"
  [[ -n "$val" ]] && return 0
  [[ -f "${ROOT}/config.example.yaml" ]] && val="$(get_yaml_value antigravity_plugin_target "${ROOT}/config.example.yaml")"
  [[ -n "$val" ]]
}

platform_enabled() { [[ "$PLATFORM" == "all" || "$PLATFORM" == "$1" ]]; }

run_rm() {
  if [[ "$DRY_RUN" -eq 1 ]]; then echo "[dry-run] rm -f $1"; else rm -f "$1"; fi
}

build_allowed_skill_names() {
  ALLOWED_SKILL_NAMES=()
  local skill_dir name
  for skill_dir in "${SKILLS_ROOT}"/*/; do
    [[ -d "$skill_dir" && -f "${skill_dir}/SKILL.md" ]] || continue
    name="$(basename "$skill_dir")"
    ALLOWED_SKILL_NAMES+=("$name")
  done
}

build_allowed_rule_names() {
  ALLOWED_RULE_NAMES=()
  local rule_file name
  [[ -d "$RULES_ROOT" ]] || return 0
  for rule_file in "${RULES_ROOT}"/*.mdc; do
    [[ -f "$rule_file" ]] || continue
    name="$(basename "$rule_file")"
    ALLOWED_RULE_NAMES+=("$name")
  done
}

skill_name_allowed() {
  local name="$1" allowed
  for allowed in "${ALLOWED_SKILL_NAMES[@]}"; do
    [[ "$name" == "$allowed" ]] && return 0
  done
  return 1
}

rule_name_allowed() {
  local name="$1" allowed
  for allowed in "${ALLOWED_RULE_NAMES[@]}"; do
    [[ "$name" == "$allowed" ]] && return 0
  done
  return 1
}

skill_name_in_list() {
  local name="$1" entry
  for entry in "${STALE_SKILL_NAMES[@]}"; do
    [[ "$name" == "$entry" ]] && return 0
  done
  return 1
}

rule_name_in_stale_list() {
  local name="$1" entry
  for entry in "${STALE_RULE_NAMES[@]}"; do
    [[ "$name" == "$entry" ]] && return 0
  done
  return 1
}

is_adlc5_distribution_path() {
  local dest="$1"
  [[ -z "$dest" ]] && return 1
  [[ "$dest" == "${ROOT}"* ]] && return 0
  [[ "$dest" == *"/adlc5/"* ]] || [[ "$dest" == *"/adlc5" ]] && return 0
  return 1
}

is_adlc5_rules_path() {
  local dest="$1"
  [[ -z "$dest" ]] && return 1
  [[ "$dest" == "${RULES_ROOT}"* ]] && return 0
  [[ "$dest" == *"/adlc5/.cursor/rules/"* ]] && return 0
  [[ "$dest" == *"/adlc5/shared/rules/"* ]] && return 0
  [[ "$dest" == *"/v1/"*rules* ]] || [[ "$dest" == *"/v2/"*rules* ]] && return 0
  return 1
}

is_stale_adlc5_dest() {
  local dest="$1" name="$2"
  [[ -z "$dest" ]] && return 1

  local expected="${SKILLS_ROOT}/${name}"
  case "$dest" in
    "${expected}"|"${expected}/"|"${expected}"/*)
      return 1
      ;;
  esac

  # Legacy layouts: ADLC5 v1 tree or pre-lift v2/skills/ paths
  case "$dest" in
    */v1/skills/*|*/v2/skills/*) return 0 ;;
  esac

  if is_adlc5_distribution_path "$dest"; then
    return 0
  fi
  return 1
}

should_prune_symlink() {
  local link="$1" name="$2"
  local dest
  dest="$(readlink "$link" 2>/dev/null || true)"

  if skill_name_in_list "$name"; then
    return 0
  fi

  if [[ "$name" == adlc5-* ]] && ! skill_name_allowed "$name"; then
    return 0
  fi

  if is_stale_adlc5_dest "$dest" "$name"; then
    return 0
  fi

  if [[ -L "$link" && ! -e "$link" ]] && is_adlc5_distribution_path "$dest"; then
    return 0
  fi

  return 1
}

# Only ADLC5-owned rule symlinks — never delete user-authored plain files.
should_prune_rule_symlink() {
  local link="$1" name="$2"
  local dest
  [[ -L "$link" ]] || return 1
  dest="$(readlink "$link" 2>/dev/null || true)"

  if rule_name_in_stale_list "$name"; then
    return 0
  fi

  if ! is_adlc5_rules_path "$dest" && ! is_adlc5_distribution_path "$dest"; then
    return 1
  fi

  # Pointing at this clone's rules catalog but retired / missing
  if [[ "$dest" == "${RULES_ROOT}"* ]]; then
    if ! rule_name_allowed "$name"; then
      return 0
    fi
    local expected="${RULES_ROOT}/${name}"
    if [[ "$dest" != "$expected" && "$dest" != "${expected}/"* ]]; then
      return 0
    fi
  fi

  case "$dest" in
    */v1/*rules*|*/v2/*rules*|*/v1/rules/*|*/v2/rules/*) return 0 ;;
  esac

  if [[ -L "$link" && ! -e "$link" ]]; then
    return 0
  fi

  # Symlink into some other adlc5 rules tree for a name no longer in catalog
  if is_adlc5_rules_path "$dest" && ! rule_name_allowed "$name"; then
    return 0
  fi

  return 1
}

collect_skill_targets() {
  local t
  if [[ ${#SKILL_TARGETS[@]} -gt 0 ]]; then
    for t in "${SKILL_TARGETS[@]}"; do
      printf '%s\n' "$t"
    done
    return 0
  fi
  if platform_enabled cursor; then
    get_path skills_install_target "~/.agents/skills"
  fi
  if platform_enabled claude; then
    get_path claude_skills_target "~/.claude/skills"
  fi
  if platform_enabled codex; then
    get_path codex_skills_target "~/.codex/skills"
  fi
  if platform_enabled opencode; then
    get_path opencode_skills_target "~/.config/opencode/skills"
  fi
  if platform_enabled gemini; then
    get_path gemini_skills_target "~/.gemini/skills"
  fi
  if platform_enabled hermes; then
    get_path hermes_skills_target "~/.hermes/skills/adlc5"
  fi
  if platform_enabled antigravity; then
    if has_antigravity_plugin_target; then
      echo "$(get_path antigravity_plugin_target "~/.gemini/config/plugins/adlc5-plugin")/skills"
    else
      get_path antigravity_skills_target "~/.gemini/antigravity/skills"
    fi
  fi
}

collect_rule_targets() {
  local t
  if [[ ${#RULE_TARGETS[@]} -gt 0 ]]; then
    for t in "${RULE_TARGETS[@]}"; do
      printf '%s\n' "$t"
    done
    return 0
  fi
  # Cursor global rules; portable copies live in-repo (not a global install target).
  if platform_enabled cursor; then
    get_path rules_install_target "~/.cursor/rules"
  fi
}

prune_skill_target() {
  local target="$1"
  [[ -d "$target" ]] || return 0
  local link name dest reason
  for link in "${target}"/*; do
    [[ -L "$link" ]] || continue
    name="$(basename "$link")"
    should_prune_symlink "$link" "$name" || continue
    dest="$(readlink "$link" 2>/dev/null || true)"
    if [[ -L "$link" && ! -e "$link" ]]; then
      reason="broken"
    elif skill_name_in_list "$name"; then
      reason="stale name"
    elif [[ "$name" == adlc5-* ]] && ! skill_name_allowed "$name"; then
      reason="removed lifecycle skill"
    else
      reason="stale path"
    fi
    echo "  remove (${reason}): ${link} -> ${dest:-<empty>}"
    run_rm "$link"
    removed=$((removed + 1))
  done
}

prune_rule_target() {
  local target="$1"
  [[ -d "$target" ]] || return 0
  local link name dest reason
  for link in "${target}"/*; do
    [[ -e "$link" || -L "$link" ]] || continue
    name="$(basename "$link")"
    # Never touch non-symlinks (user-authored rules)
    [[ -L "$link" ]] || continue
    should_prune_rule_symlink "$link" "$name" || continue
    dest="$(readlink "$link" 2>/dev/null || true)"
    if [[ -L "$link" && ! -e "$link" ]]; then
      reason="broken"
    elif rule_name_in_stale_list "$name"; then
      reason="stale rule name"
    elif ! rule_name_allowed "$name"; then
      reason="retired ADLC5 rule"
    else
      reason="stale ADLC5 rule path"
    fi
    echo "  remove (${reason}): ${link} -> ${dest:-<empty>}"
    run_rm "$link"
    rules_removed=$((rules_removed + 1))
  done
}

removed=0
rules_removed=0

if [[ "$PRUNE_SKILLS" -eq 1 ]]; then
  build_allowed_skill_names
  echo "Pruning stale ADLC5 skill symlinks (${#ALLOWED_SKILL_NAMES[@]} current skills in catalog)..."
  while IFS= read -r target; do
    [[ -n "$target" ]] || continue
    echo "Target: ${target}"
    prune_skill_target "$target"
  done < <(collect_skill_targets)
  echo "Removed ${removed} stale ADLC5 skill symlink(s)."
  echo
fi

if [[ "$PRUNE_RULES" -eq 1 ]]; then
  build_allowed_rule_names
  echo "Pruning stale ADLC5 rule symlinks (${#ALLOWED_RULE_NAMES[@]} current rules in catalog)..."
  while IFS= read -r target; do
    [[ -n "$target" ]] || continue
    echo "Rules target: ${target}"
    prune_rule_target "$target"
  done < <(collect_rule_targets)
  echo "Removed ${rules_removed} stale ADLC5 rule symlink(s)."
  echo
fi

if [[ "$PRUNE_BACKUPS" -eq 1 ]]; then
  if [[ -n "$BACKUP_ROOT_OVERRIDE" ]]; then
    backup_root="$BACKUP_ROOT_OVERRIDE"
  else
    backup_root="$(get_path install_backup_root "~/.adlc5-install-backup")"
  fi
  echo "Pruning install backups under ${backup_root} (older than ${KEEP_BACKUP_DAYS} days)..."
  if [[ -d "$backup_root" ]]; then
    while IFS= read -r dir; do
      echo "  remove: ${dir}"
      if [[ "$DRY_RUN" -eq 1 ]]; then echo "[dry-run] rm -rf ${dir}"; else rm -rf "$dir"; fi
    done < <(find "$backup_root" -mindepth 1 -maxdepth 1 -type d -mtime +"${KEEP_BACKUP_DAYS}" 2>/dev/null || true)
  fi
  echo
fi

echo "Done. Re-run: ./scripts/install.sh && ./scripts/verify-install.sh"
