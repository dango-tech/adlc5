#!/usr/bin/env bash
# Shared helpers for ADLC5 project wiki scripts.
set -euo pipefail

wiki_resolve_workspace() {
  local ws="${1:-.}"
  mkdir -p "$ws"
  cd "$ws" && pwd
}

wiki_git_head() {
  local sha="none"
  if git -C "$1" rev-parse --is-inside-work-tree &>/dev/null; then
    sha="$(git -C "$1" rev-parse --short=7 HEAD 2>/dev/null | tr -d '[:space:]' || true)"
  fi
  [[ -n "$sha" ]] || sha="none"
  printf '%s' "$sha"
}

wiki_git_short() {
  local sha="$1"
  sha="$(printf '%s' "$sha" | tr -d '[:space:]')"
  if [[ "$sha" == "none" || "$sha" == "unknown" || "$sha" == "HEAD" ]]; then
    printf '%s' "$sha"
  else
    printf '%s' "${sha:0:7}"
  fi
}

wiki_log_append() {
  local log_file="$1" event="$2" detail="$3"
  local iso
  iso="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  {
    echo ""
    echo "## [${iso}] ${event} | ${detail}"
  } >>"$log_file"
}

wiki_render_template() {
  local src="$1" dest="$2"
  local iso sha_short feature
  iso="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha_short="$(printf '%s' "${3:-none}" | tr -d '\n\r')"
  feature="$(printf '%s' "${4:-}" | tr -d '\n\r')"
  sed -e "s|{ISO-8601-timestamp}|${iso}|g" \
      -e "s|{commit-short\|none}|${sha_short}|g" \
      -e "s|{commit-short}|${sha_short}|g" \
      -e "s|{feature-name}|${feature}|g" \
      -e "s|{feature}|${feature}|g" \
      -e "s|{n}|0|g" \
      "$src" >"$dest"
}

wiki_detect_roots() {
  local root="$1"
  local -a roots=()
  [[ -f "${root}/pnpm-workspace.yaml" ]] && roots+=("${root} (pnpm-workspace)")
  [[ -f "${root}/package.json" ]] && roots+=("${root} (package.json)")
  [[ -f "${root}/go.work" ]] && roots+=("${root} (go.work)")
  [[ -f "${root}/Cargo.toml" ]] && roots+=("${root} (Cargo.toml)")
  [[ -f "${root}/pyproject.toml" ]] && roots+=("${root} (pyproject.toml)")
  if [[ ${#roots[@]} -eq 0 ]]; then
    roots+=("${root} (filesystem)")
  fi
  printf '%s\n' "${roots[@]}"
}

wiki_parse_evidence() {
  # Input: path:start-end or path:line — output via globals WIKI_EVIDENCE_PATH WIKI_EVIDENCE_START WIKI_EVIDENCE_END
  local ev="$1"
  ev="${ev#\`}"
  ev="${ev%\`}"
  WIKI_EVIDENCE_PATH="${ev%%:*}"
  local rest="${ev#*:}"
  if [[ "$rest" == *"-"* ]]; then
    WIKI_EVIDENCE_START="${rest%%-*}"
    WIKI_EVIDENCE_END="${rest#*-}"
  else
    WIKI_EVIDENCE_START="$rest"
    WIKI_EVIDENCE_END="$rest"
  fi
}
