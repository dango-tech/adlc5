# Git worktree context helpers for ADLC5 project scaffolding.
# shellcheck shell=bash
#
# Every linked worktree of a repository shares one real .git directory, which
# `git rev-parse --git-common-dir` resolves to identically from any worktree.
# ADLC5 uses that directory as the anchor for artifacts that are universal to
# the repository (governance templates, workspace config) so a second worktree
# reuses them instead of scaffolding a private duplicate.
#
# Untracked files are never shared by git between worktrees, and `.adlc5/` is
# gitignored — so without this, each new worktree starts empty and re-copies
# the same static files.

# Absolute path of the shared .git directory, or empty when not in a repo.
adlc5_git_common_dir() {
  local dir="${1:?}" common
  common="$(git -C "$dir" rev-parse --git-common-dir 2>/dev/null)" || return 0
  [[ -n "$common" ]] || return 0
  # Relative in the main worktree ('.git'), absolute in linked worktrees.
  if [[ "$common" != /* ]]; then
    local top
    top="$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null)" || return 0
    common="${top}/${common}"
  fi
  (cd "$common" 2>/dev/null && pwd) || true
}

# Exit 0 when DIR is a linked worktree (not the main working tree).
adlc5_is_linked_worktree() {
  local dir="${1:?}" git_dir common
  git_dir="$(git -C "$dir" rev-parse --absolute-git-dir 2>/dev/null)" || return 1
  common="$(adlc5_git_common_dir "$dir")"
  [[ -n "$common" && "$git_dir" != "$common" ]]
}

# Path of the repository's main worktree, or empty.
adlc5_main_worktree() {
  local dir="${1:?}"
  git -C "$dir" worktree list --porcelain 2>/dev/null \
    | awk '/^worktree /{print substr($0, 10); exit}'
}

# All worktree paths for the repository containing DIR, one per line.
adlc5_worktree_paths() {
  local dir="${1:?}"
  git -C "$dir" worktree list --porcelain 2>/dev/null \
    | awk '/^worktree /{print substr($0, 10)}'
}

# Directory holding repository-wide ADLC5 artifacts shared by every worktree.
# Lives under the common .git dir so it survives removal of any one worktree.
adlc5_shared_root() {
  local dir="${1:?}" common
  common="$(adlc5_git_common_dir "$dir")"
  [[ -n "$common" ]] || return 0
  printf '%s/adlc5-shared\n' "$common"
}

# Worktrees other than DIR that already hold .adlc5/<feature>/state.json.
adlc5_feature_peers() {
  local dir="${1:?}" feature="${2:?}" self wt
  self="$(cd "$dir" 2>/dev/null && pwd)" || self="$dir"
  while IFS= read -r wt; do
    [[ -n "$wt" ]] || continue
    [[ "$wt" == "$self" ]] && continue
    [[ -f "${wt}/.adlc5/${feature}/state.json" ]] || continue
    printf '%s\n' "$wt"
  done <<EOF
$(adlc5_worktree_paths "$dir")
EOF
}
