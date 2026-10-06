# Shared adlc5 distribution paths (source from other scripts).
# shellcheck shell=bash

adlc5_root_dir() {
  local caller="${1:?}"
  local dir
  dir="$(cd "$(dirname "$caller")" && pwd)"
  if [[ "$(basename "$dir")" == "scripts" ]]; then
    printf '%s\n' "$(cd "${dir}/.." && pwd)"
    return 0
  fi
  # Nested under scripts/<subdir>/ (memory, wiki, …)
  if [[ "$(basename "$(dirname "$dir")")" == "scripts" ]]; then
    printf '%s\n' "$(cd "${dir}/../.." && pwd)"
    return 0
  fi
  printf '%s\n' "$(cd "${dir}/../.." && pwd)"
}

# Compatibility alias — framework content lives at repo root (3.x).
adlc5_v2_dir() {
  local root="${1:?}"
  printf '%s\n' "$(cd "$root" && pwd)"
}

adlc5_version_file() {
  local root="${1:?}"
  if [[ -f "${root}/core/VERSION" ]]; then
    printf '%s/core/VERSION\n' "$(cd "$root" && pwd)"
  elif [[ -f "${root}/v2/core/VERSION" ]]; then
    # Legacy clone layout before path lift
    printf '%s/v2/core/VERSION\n' "$(cd "$root" && pwd)"
  else
    printf '%s/core/VERSION\n' "$(cd "$root" && pwd)"
  fi
}

adlc5_skills_dir() {
  local root="${1:?}"
  if [[ -d "${root}/skills" ]]; then
    printf '%s/skills\n' "$(cd "$root" && pwd)"
  elif [[ -d "${root}/v2/skills" ]]; then
    printf '%s/v2/skills\n' "$(cd "$root" && pwd)"
  else
    printf '%s/skills\n' "$(cd "$root" && pwd)"
  fi
}

adlc5_templates_dir() {
  local root="${1:?}"
  if [[ -d "${root}/templates" ]]; then
    printf '%s/templates\n' "$(cd "$root" && pwd)"
  elif [[ -d "${root}/v2/templates" ]]; then
    printf '%s/v2/templates\n' "$(cd "$root" && pwd)"
  else
    printf '%s/templates\n' "$(cd "$root" && pwd)"
  fi
}

adlc5_guides_dir() {
  local root="${1:?}"
  if [[ -d "${root}/core/guides" ]]; then
    printf '%s/core/guides\n' "$(cd "$root" && pwd)"
  elif [[ -d "${root}/v2/core/guides" ]]; then
    printf '%s/v2/core/guides\n' "$(cd "$root" && pwd)"
  else
    printf '%s/core/guides\n' "$(cd "$root" && pwd)"
  fi
}

adlc5_dist_scripts_dir() {
  local root="${1:?}"
  printf '%s/scripts\n' "$(cd "$root" && pwd)"
}

adlc5_shared_docs_dir() {
  local root="${1:?}"
  printf '%s/shared/docs\n' "$(cd "$root" && pwd)"
}

adlc5_shared_rules_dir() {
  local root="${1:?}"
  printf '%s/shared/rules\n' "$(cd "$root" && pwd)"
}
