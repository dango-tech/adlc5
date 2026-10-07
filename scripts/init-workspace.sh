#!/usr/bin/env bash
# Initialize ADLC5 in a consumer project workspace (project-local skills + .adlc5 scaffold).
# Rules (R0–R5) remain global — run install.sh --rules-only once per machine.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/adlc5-dirs.sh
source "${ROOT}/scripts/lib/adlc5-dirs.sh"
# shellcheck source=lib/pr-template.sh
source "${ROOT}/scripts/lib/pr-template.sh"
# shellcheck source=lib/worktree-context.sh
source "${ROOT}/scripts/lib/worktree-context.sh"
TEMPLATES_ROOT="$(adlc5_templates_dir "$ROOT")"
SKILLS_ROOT="$(adlc5_skills_dir "$ROOT")"

adlc5_version() {
  local f="${ROOT}/core/VERSION"
  if [[ -f "$f" ]]; then tr -d '[:space:]' <"$f"
  else echo "0.0.0"; fi
}

PROJECT=""
WITH_SKILLS=1
WITH_HOOKS=0
HOOKS_PLATFORMS="cursor"
WITH_PROJECT_WIKI=0
WITH_PR_TEMPLATE=0
SHARED_IGNORE=0
DRY_RUN=0
FORCE=0
SHARE_STATIC=1

usage() {
  cat <<'EOF'
Usage: ./scripts/init-workspace.sh [OPTIONS]

Initialize ADLC5 in a consumer project (not global).

ADLC5 installs in three layers — this script is layer 2:

  1. Machine-global (install.sh, once per machine)
     Skills and rules are symlinked from this adlc5 clone into the agent
     homes (~/.agents/skills, ~/.claude/skills, ~/.cursor/rules, ...).
     Nothing is copied; every project and worktree reads the same clone.

  2. Repository-local (this script, once per repository)
     The .adlc5/ scaffold: workspace.json, config.yaml, governance/ and
     policies.yaml.example. These are static per repository, so in a linked
     git worktree they are symlinked to one shared copy under the repo's
     common .git dir instead of being duplicated. Lifecycle state is excluded
     locally by default; git never shares untracked files between worktrees,
     which is why a new worktree used to look like a fresh, duplicated install.

  3. Per-feature (init-feature.sh / @adlc5, once per feature)
     .adlc5/{feature}/ — state.json, design docs, code specs, memory. This
     stays worktree-local on purpose: parallel worktrees run different
     features and must not share lifecycle state.

  --project DIR     Target project root (default: current directory)
  --adlc5-root DIR  Path to adlc5 clone (default: parent of this script's repo)
  --version VER     Ignored (backward-compatible CLI)
  --no-skills       Skip symlinking skills into project .agents/skills/
  --with-hooks      Copy hook config + scripts from adlc5 (optional; default platform: cursor)
  --hooks-platform LIST  Comma-separated platforms for --with-hooks: cursor,claude,codex or all
                    (default: cursor — only installs hooks for the platform(s) named)
  --with-project-wiki  Scaffold team-shared wiki/ and sources/ (tracked; not gitignored)
  --shared-ignore    Put ADLC5 lifecycle exclusions in the repository .gitignore
                     (default: target repo's local Git exclude; no tracked diff)
  --with-pr-template  Copy ADLC5's starter PR body template to .github/PULL_REQUEST_TEMPLATE.md
                      (skipped if the project already has one at any conventional path)
  --force           Overwrite .adlc5/workspace.json and refresh skill links
  --no-shared-worktree  Scaffold private copies even in a linked worktree
                    (opt out of layer-2 sharing; rarely needed)
  --dry-run         Print actions only
  -h, --help        Show help

Global rules (one-time per machine):
  cd /path/to/adlc5 && ./scripts/install.sh --rules-only

Then in your app repo:
  /path/to/adlc5/scripts/init-workspace.sh --project .

Creates:
  .adlc5/workspace.json, .adlc5/config.yaml
  .adlc5/governance/ (production-ready, DoD, autopilot picker, verifier rules)
  .adlc5/policies.yaml.example
    In the main worktree these are real files. In a linked worktree they are
    symlinks into <git-common-dir>/adlc5-shared/, so every worktree of the
    repository reads one copy. An existing real file is never replaced.
  AGENTS.md (if missing)
  .agents/ (tracked constitution draft + existing skills/ files; init never overwrites)
  docs/adr/ (tracked architecture-decision record area)
  .agent-cache/ (generated, gitignored repository intelligence)
  .agents/skills/ → symlinks to adlc5 skills (unless --no-skills)
  .cursor/agents/discover-council-* → council model routing for @discover
  Local Git exclusions for lifecycle artifacts (unless --shared-ignore)
  .github/PULL_REQUEST_TEMPLATE.md (only with --with-pr-template, and only if missing)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="${2:?}"; shift 2 ;;
    --adlc5-root) ROOT="${2:?}"; shift 2 ;;
    --version) shift 2 ;; # legacy ignored arg
    --no-skills) WITH_SKILLS=0; shift ;;
    --with-hooks) WITH_HOOKS=1; shift ;;
    --hooks-platform) HOOKS_PLATFORMS="${2:?}"; shift 2 ;;
    --with-project-wiki) WITH_PROJECT_WIKI=1; shift ;;
    --with-pr-template) WITH_PR_TEMPLATE=1; shift ;;
    --shared-ignore) SHARED_IGNORE=1; shift ;;
    --force) FORCE=1; shift ;;
    --no-shared-worktree) SHARE_STATIC=0; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 1 ;;
  esac
done

ADLC5_ROOT="$(cd "$ROOT" && pwd)"
SKILLS_ROOT="$(adlc5_skills_dir "$ADLC5_ROOT")"
TEMPLATES_ROOT="$(adlc5_templates_dir "$ADLC5_ROOT")"
TEMPLATE_CONFIG="${TEMPLATES_ROOT}/workspace-config.yaml"
TEMPLATE_AGENTS="${TEMPLATES_ROOT}/AGENTS.project.md"

if [[ ! -d "$SKILLS_ROOT" ]]; then
  echo "ERROR: adlc5 skills not found at ${SKILLS_ROOT}" >&2
  exit 1
fi

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

if [[ -z "$PROJECT" ]]; then
  PROJECT="$(pwd)"
fi
if [[ "$DRY_RUN" -eq 1 ]]; then
  mkdir -p "$PROJECT" 2>/dev/null || true
  PROJECT="$(cd "$PROJECT" 2>/dev/null && pwd || echo "$PROJECT")"
else
  run mkdir -p "$PROJECT"
  PROJECT="$(cd "$PROJECT" && pwd)"
fi

# Layer-2 sharing: a linked worktree reuses the repository's static artifacts
# instead of scaffolding private duplicates. The shared store lives under the
# common .git dir, so it outlives any single worktree.
SHARED_ROOT=""
MAIN_WORKTREE=""
if [[ "$SHARE_STATIC" -eq 1 ]] && adlc5_is_linked_worktree "$PROJECT"; then
  SHARED_ROOT="$(adlc5_shared_root "$PROJECT")"
  MAIN_WORKTREE="$(adlc5_main_worktree "$PROJECT")"
fi
[[ -n "$SHARED_ROOT" ]] || SHARE_STATIC=0

# Where a static artifact physically lives. Shared store in a linked worktree,
# worktree-local otherwise — and always worktree-local when a real file is
# already there, so existing hand-edited scaffolds are never replaced.
artifact_store_path() {
  local name="$1" local_path="$2"
  if [[ "$SHARE_STATIC" -eq 1 && ( ! -e "$local_path" || -L "$local_path" ) ]]; then
    printf '%s/%s\n' "$SHARED_ROOT" "$name"
  else
    printf '%s\n' "$local_path"
  fi
}

# Seed the shared store from the main worktree's existing copy, so promoting a
# repo that was initialized before this feature does not lose local edits.
seed_shared_artifact() {
  local name="$1" store="$2"
  [[ "$store" == "${SHARED_ROOT}/"* ]] || return 1
  [[ -e "$store" ]] && return 0
  local donor="${MAIN_WORKTREE}/.adlc5/${name}"
  [[ -n "$MAIN_WORKTREE" && -e "$donor" && ! -L "$donor" ]] || return 1
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  [dry-run] adopt ${donor} -> ${store}"
    return 0
  fi
  mkdir -p "$(dirname "$store")"
  cp -R "$donor" "$store"
  echo "  Adopted existing ${name} from ${MAIN_WORKTREE}"
}

link_shared_artifact() {
  local name="$1" store="$2" local_path="$3"
  [[ "$store" == "$local_path" ]] && return 0
  if [[ -L "$local_path" && "$(readlink "$local_path" 2>/dev/null)" == "$store" ]]; then
    echo "  OK (shared across worktrees): .adlc5/${name}"
    return 0
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  [dry-run] link .adlc5/${name} -> ${store}"
    return 0
  fi
  mkdir -p "$(dirname "$local_path")"
  rm -rf "$local_path"
  ln -s "$store" "$local_path"
  echo "  Shared: .adlc5/${name} -> ${store}"
}

link_skill() {
  local src="$1" dest="$2" name="$3"
  if [[ -L "$dest" ]]; then
    local current
    current="$(readlink "$dest" 2>/dev/null || true)"
    if [[ "$current" == "$src" ]]; then
      echo "  OK (linked): ${name}"
      return 0
    fi
  fi
  if [[ -e "$dest" && "$FORCE" -ne 1 ]]; then
    echo "  SKIP (exists): ${name} — use --force to replace"
    return 0
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  [dry-run] link ${name} -> ${dest}"
    return 0
  fi
  mkdir -p "$(dirname "$dest")"
  rm -rf "$dest" 2>/dev/null || true
  ln -s "$src" "$dest"
  echo "  Linked: ${name}"
}

append_ignore_rules() {
  local gi="${PROJECT}/.gitignore"
  local target marker tracked path
  if [[ "$SHARED_IGNORE" -eq 1 ]]; then
    target="$gi"
    marker="# ADLC5 shared lifecycle artifacts"
  else
    local exclude
    exclude="$(git -C "$PROJECT" rev-parse --git-path info/exclude 2>/dev/null || true)"
    if [[ -z "$exclude" ]]; then
      echo "  No Git repository; local ignore rules are not needed"
      return 0
    fi
    [[ "$exclude" == /* ]] || exclude="${PROJECT}/${exclude}"
    target="$exclude"
    marker="# ADLC5 local lifecycle artifacts"
  fi
  if [[ -f "$target" ]] && grep -qF "$marker" "$target" 2>/dev/null; then
    echo "  ADLC5 lifecycle exclusions already configured in ${target}"
  else
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "  [dry-run] append ADLC5 lifecycle exclusions to ${target}"
    else
      printf '\n%s\n!.adlc5/\n.adlc5/*\n!.adlc5/governance/\n.discover/\n.prt/\n.qa/\n.worktrees/\n' "$marker" >>"$target"
      if [[ "$SHARED_IGNORE" -eq 1 ]]; then
        echo "  Updated .gitignore — review and commit if the team should share these exclusions"
      else
        echo "  Updated local Git exclusions (not part of the repository diff)"
      fi
    fi
  fi

  tracked="$(git -C "$PROJECT" ls-files -- '.adlc5/*' '.discover/*' '.prt/*' '.qa/*' '.worktrees/*' 2>/dev/null || true)"
  if [[ -n "$tracked" ]]; then
    while IFS= read -r path; do
      [[ -n "$path" ]] || continue
      case "$path" in .adlc5/governance/*) continue ;; esac
      echo "  WARNING: ${path} is already tracked; ignore rules do not untrack it" >&2
    done <<<"$tracked"
  fi
}

echo "Initializing ADLC5 workspace: ${PROJECT}"
echo "ADLC5 root: ${ADLC5_ROOT}"
if [[ "$SHARE_STATIC" -eq 1 ]]; then
  echo "Linked git worktree detected — reusing this repository's shared ADLC5 artifacts:"
  echo "  ${SHARED_ROOT}"
  echo "  (config.yaml, governance/, policies.yaml.example are symlinked, not copied;"
  echo "   .adlc5/{feature}/ lifecycle state stays local to this worktree)"
fi
[[ "$DRY_RUN" -eq 1 ]] && echo "(dry-run)"
echo

# .adlc5 scaffold
ADLC5_DIR="${PROJECT}/.adlc5"
WORKSPACE_JSON="${ADLC5_DIR}/workspace.json"
CONFIG_YAML="${ADLC5_DIR}/config.yaml"

if [[ -f "$WORKSPACE_JSON" && "$FORCE" -ne 1 ]]; then
  echo "Workspace already initialized: ${WORKSPACE_JSON}"
  echo "Use --force to refresh workspace.json and skill links."
else
  run mkdir -p "$ADLC5_DIR"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] write ${WORKSPACE_JSON}"
  else
    cat >"$WORKSPACE_JSON" <<EOF
{
  "adlc5_version": "$(adlc5_version)",
  "adlc5_root": "${ADLC5_ROOT}",
  "project_root": "${PROJECT}",
  "initialized_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "skills_path": ".agents/skills"
}
EOF
    echo "Created ${WORKSPACE_JSON}"
  fi
fi

CONFIG_STORE="$(artifact_store_path config.yaml "$CONFIG_YAML")"
seed_shared_artifact config.yaml "$CONFIG_STORE" || true
if [[ ! -f "$CONFIG_STORE" ]]; then
  if [[ -f "$TEMPLATE_CONFIG" ]]; then
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "[dry-run] copy workspace config template"
    else
      mkdir -p "$(dirname "$CONFIG_STORE")"
      sed "s|adlc5_root: /path/to/adlc5|adlc5_root: ${ADLC5_ROOT}|" "$TEMPLATE_CONFIG" >"$CONFIG_STORE"
      echo "Created ${CONFIG_STORE} — edit model_profiles"
    fi
  fi
else
  echo "Config exists: ${CONFIG_STORE}"
fi
link_shared_artifact config.yaml "$CONFIG_STORE" "$CONFIG_YAML"

# AGENTS.md
AGENTS_MD="${PROJECT}/AGENTS.md"
if [[ ! -f "$AGENTS_MD" ]]; then
  if [[ -f "$TEMPLATE_AGENTS" ]]; then
    run cp "$TEMPLATE_AGENTS" "$AGENTS_MD"
    echo "Created ${AGENTS_MD}"
  fi
else
  echo "AGENTS.md already exists — not overwritten"
fi

append_ignore_rules

# Repository context: tracked constitution + generated, gitignored intelligence.
REPOSITORY_CONTEXT="${ADLC5_ROOT}/scripts/repository-context.py"
if [[ -f "$REPOSITORY_CONTEXT" ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] repo-spec init --workspace ${PROJECT}"
    echo "[dry-run] repo-index build --workspace ${PROJECT}"
  else
    python3 "$REPOSITORY_CONTEXT" repo-spec init --workspace "$PROJECT"
    python3 "$REPOSITORY_CONTEXT" repo-index build --workspace "$PROJECT"
  fi
else
  echo "WARN: repository context tool missing: ${REPOSITORY_CONTEXT}" >&2
fi

# Governance copies (tracked in consumer .adlc5/governance/)
GOV_DST="${ADLC5_DIR}/governance"
copy_governance() {
  local src="$1" dest="$2"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  [dry-run] cp ${src} -> ${dest}"
    return 0
  fi
  mkdir -p "$(dirname "$dest")"
  cp "$src" "$dest"
  echo "  Copied $(basename "$dest")"
}
GOV_STORE="$(artifact_store_path governance "$GOV_DST")"
seed_shared_artifact governance "$GOV_STORE" || true
echo "Installing governance templates to ${GOV_STORE}"
run mkdir -p "$GOV_STORE"
copy_governance "${TEMPLATES_ROOT}/definition-of-done.md" "${GOV_STORE}/definition-of-done.md"
copy_governance "${ADLC5_ROOT}/core/governance/production-ready.md" "${GOV_STORE}/production-ready.md"
copy_governance "${ADLC5_ROOT}/core/governance/autopilot-stage-picker.md" "${GOV_STORE}/autopilot-stage-picker.md"
copy_governance "${ADLC5_ROOT}/core/governance/verifier-rules.md" "${GOV_STORE}/verifier-rules.md"
link_shared_artifact governance "$GOV_STORE" "$GOV_DST"
POLICY_EX="${ADLC5_DIR}/policies.yaml.example"
POLICY_STORE="$(artifact_store_path policies.yaml.example "$POLICY_EX")"
seed_shared_artifact policies.yaml.example "$POLICY_STORE" || true
if [[ ! -f "$POLICY_STORE" || "$FORCE" -eq 1 ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  [dry-run] cp policies.yaml.example"
  else
    mkdir -p "$(dirname "$POLICY_STORE")"
    cp "${TEMPLATES_ROOT}/policies.yaml.example" "$POLICY_STORE"
    echo "  Created ${POLICY_STORE}"
  fi
else
  echo "  policies.yaml.example exists — not overwritten"
fi
link_shared_artifact policies.yaml.example "$POLICY_STORE" "$POLICY_EX"

# Optional team-shared project wiki (tracked in git)
if [[ "$WITH_PROJECT_WIKI" -eq 1 ]]; then
  WIKI_INIT="${ADLC5_ROOT}/scripts/wiki/init-wiki.sh"
  if [[ ! -x "$WIKI_INIT" ]]; then
    echo "WARN: --with-project-wiki but ${WIKI_INIT} not executable" >&2
  elif [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] ${WIKI_INIT} --workspace ${PROJECT}"
  else
    echo "Initializing project wiki (team-shared, tracked)"
    "$WIKI_INIT" --workspace "$PROJECT"
  fi
fi

# PR body template — capability suggestion for repos using adlc5 skills (@pr-reviewer
# mirrors an existing repo template automatically; ship a starter when none exists).
EXISTING_PR_TEMPLATE="$(adlc5_find_pr_template "$PROJECT")"
if [[ "$WITH_PR_TEMPLATE" -eq 1 ]]; then
  if [[ -n "$EXISTING_PR_TEMPLATE" ]]; then
    echo "PR template already exists: ${EXISTING_PR_TEMPLATE} — not overwritten"
  else
    PR_TEMPLATE_SRC="${TEMPLATES_ROOT}/github/PULL_REQUEST_TEMPLATE.md"
    PR_TEMPLATE_DST="${PROJECT}/.github/PULL_REQUEST_TEMPLATE.md"
    if [[ ! -f "$PR_TEMPLATE_SRC" ]]; then
      echo "WARN: --with-pr-template but ${PR_TEMPLATE_SRC} not found" >&2
    elif [[ "$DRY_RUN" -eq 1 ]]; then
      echo "[dry-run] cp ${PR_TEMPLATE_SRC} -> ${PR_TEMPLATE_DST}"
    else
      mkdir -p "$(dirname "$PR_TEMPLATE_DST")"
      cp "$PR_TEMPLATE_SRC" "$PR_TEMPLATE_DST"
      echo "Created ${PR_TEMPLATE_DST}"
    fi
  fi
fi

# Optional platform hooks (from adlc5 distribution). Each platform keeps its
# own config filename and hook-script directory so Cursor hooks never leak
# into a Claude Code or Codex CLI install, and vice versa.
install_platform_hooks() {
  local platform="$1" config_name="$2"
  local hooks_src="${ADLC5_ROOT}/.${platform}"
  local hooks_dst="${PROJECT}/.${platform}"
  if [[ ! -f "${hooks_src}/${config_name}" ]]; then
    echo "WARN: --with-hooks requested '${platform}' but ${hooks_src}/${config_name} not found" >&2
    return 0
  fi
  echo "Installing ${platform} hooks"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  [dry-run] copy ${config_name} and hooks/*.sh,*.py to ${hooks_dst}"
    return 0
  fi
  mkdir -p "${hooks_dst}/hooks"
  cp "${hooks_src}/${config_name}" "${hooks_dst}/${config_name}"
  if [[ -d "${hooks_src}/hooks" ]]; then
    for hook_script in "${hooks_src}/hooks"/*; do
      [[ -f "$hook_script" ]] || continue
      base="$(basename "$hook_script")"
      case "$base" in
        *.sh|*.py) ;;
        *) continue ;;
      esac
      cp "$hook_script" "${hooks_dst}/hooks/${base}"
      chmod +x "${hooks_dst}/hooks/${base}"
    done
  fi
  echo "  Installed ${hooks_dst}/${config_name}"
}

if [[ "$WITH_HOOKS" -eq 1 ]]; then
  if [[ "$HOOKS_PLATFORMS" == "all" ]]; then
    selected_hook_platforms=(cursor claude codex)
  else
    IFS=',' read -ra selected_hook_platforms <<< "$HOOKS_PLATFORMS"
  fi
  for platform in "${selected_hook_platforms[@]}"; do
    case "$platform" in
      cursor) install_platform_hooks cursor hooks.json ;;
      claude) install_platform_hooks claude settings.json ;;
      codex) install_platform_hooks codex hooks.json ;;
      *) echo "WARN: unknown --hooks-platform value: ${platform} (expected cursor, claude, codex, or all)" >&2 ;;
    esac
  done
fi

# Project-local skills
if [[ "$WITH_SKILLS" -eq 1 ]]; then
  SKILLS_TARGET="${PROJECT}/.agents/skills"
  echo
  echo "Linking skills to ${SKILLS_TARGET}"
  run mkdir -p "$SKILLS_TARGET"
  local_count=0
  for skill_dir in "${SKILLS_ROOT}"/*/; do
    [[ -d "$skill_dir" && -f "${skill_dir}/SKILL.md" ]] || continue
    name="$(basename "$skill_dir")"
    link_skill "$skill_dir" "${SKILLS_TARGET}/${name}" "$name"
    local_count=$((local_count + 1))
  done
  echo "  (${local_count} skills)"
  if [[ "$SHARE_STATIC" -eq 1 ]]; then
    echo "  These are symlinks into ${SKILLS_ROOT} — the same clone every worktree"
    echo "  and every agent host reads. No skill content is copied per worktree."
  fi
  # Prune retired/broken ADLC5 skill symlinks in the project-local skills dir
  if [[ -x "${ADLC5_ROOT}/scripts/cleanup-stale-skills.sh" ]]; then
    echo "Pruning stale project-local skill symlinks..."
    if [[ "$DRY_RUN" -eq 1 ]]; then
      "${ADLC5_ROOT}/scripts/cleanup-stale-skills.sh" \
        --skills-target "$SKILLS_TARGET" --prune-stale-skills --dry-run || true
    else
      "${ADLC5_ROOT}/scripts/cleanup-stale-skills.sh" \
        --skills-target "$SKILLS_TARGET" --prune-stale-skills || true
    fi
  fi
fi

# Project-local discover/ideate council agents (Cursor prefers .cursor/agents/ over ~/.cursor/agents/)
COUNCIL_INSTALL="${ADLC5_ROOT}/scripts/install-council-agents.sh"
if [[ -x "$COUNCIL_INSTALL" ]]; then
  COUNCIL_CONFIG="$CONFIG_YAML"
  [[ -f "$COUNCIL_CONFIG" ]] || COUNCIL_CONFIG="${ADLC5_ROOT}/config.example.yaml"
  echo
  echo "Installing discover council agents to ${PROJECT}/.cursor/agents"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  [dry-run] ${COUNCIL_INSTALL} --target ${PROJECT}/.cursor/agents --config ${COUNCIL_CONFIG}"
  else
    "$COUNCIL_INSTALL" --target "${PROJECT}/.cursor/agents" --config "$COUNCIL_CONFIG"
  fi
fi

echo
echo "Workspace init complete."
echo
echo "Next steps:"
echo "  1. (once per machine) cd ${ADLC5_ROOT} && ./scripts/install.sh --rules-only"
if [[ "$SHARE_STATIC" -eq 1 ]]; then
  echo "  2. Edit ${CONFIG_STORE} — set model_profiles"
  echo "     (shared by every worktree of this repo; .adlc5/config.yaml links to it)"
else
  echo "  2. Edit ${CONFIG_YAML} — set model_profiles"
fi
echo "  3. ${ADLC5_ROOT}/scripts/adlc5 repo-spec reconcile --workspace ${PROJECT}"
echo "     Review .agents/{architecture,boundaries,commands}.yaml; keep .agents/skills/;"
echo "     delete leftover .agent/ constitution files only after validate (not .agent/skills)."
echo "  4. ./scripts/init-feature.sh --feature [name] --interaction hitl"
echo "  5. Open project in Cursor and run: @adlc5 for [feature-name]"
[[ "$WITH_PROJECT_WIKI" -eq 1 ]] && echo "  6. Brownfield: @adlc5-project-wiki ingest — then review wiki/drafts/"
if [[ "$WITH_PR_TEMPLATE" -ne 1 && -z "$(adlc5_find_pr_template "$PROJECT")" ]]; then
  echo
  echo "Tip: no PR template found in this repo. @pr-reviewer mirrors one automatically when"
  echo "  opening PRs; re-run with --with-pr-template to add ADLC5's starter, or add your own"
  echo "  at .github/PULL_REQUEST_TEMPLATE.md."
fi
echo
echo "Note: visual-qa-tools (or any kebab-case name) is a FEATURE folder under .adlc5/, not part of the adlc5 framework."
