# Locate a repo's PR description template (source from other scripts).
# shellcheck shell=bash

# adlc5_find_pr_template ROOT
# Prints the first matching path, relative to ROOT, or nothing if none exist.
# Checked in the same order GitHub/GitLab/Bitbucket UIs look for one.
adlc5_find_pr_template() {
  local root="${1:?}"
  local candidates=(
    ".github/pull_request_template.md"
    ".github/PULL_REQUEST_TEMPLATE.md"
    "PULL_REQUEST_TEMPLATE.md"
    "docs/PULL_REQUEST_TEMPLATE.md"
  )
  local rel
  for rel in "${candidates[@]}"; do
    if [[ -f "${root}/${rel}" ]]; then
      # Case-insensitive filesystems may match a differently-cased candidate.
      # Report the directory entry's real spelling so callers get a valid path.
      if [[ "$rel" == */* ]]; then
        local dir="${rel%/*}"
        local expected="${rel##*/}"
        local entry actual
        for entry in "${root}/${dir}"/*; do
          [[ -f "$entry" ]] || continue
          actual="$(basename "$entry")"
          if [[ "$(printf '%s' "$actual" | tr '[:upper:]' '[:lower:]')" == "$(printf '%s' "$expected" | tr '[:upper:]' '[:lower:]')" ]]; then
            printf '%s/%s\n' "$dir" "$actual"
            return 0
          fi
        done
      fi
      printf '%s\n' "$rel"
      return 0
    fi
  done
  # Multi-template directory: first *.md file, alphabetically.
  local dir="${root}/.github/PULL_REQUEST_TEMPLATE"
  if [[ -d "$dir" ]]; then
    local f
    for f in "$dir"/*.md; do
      [[ -f "$f" ]] || continue
      printf '.github/PULL_REQUEST_TEMPLATE/%s\n' "$(basename "$f")"
      return 0
    done
  fi
  return 0
}
