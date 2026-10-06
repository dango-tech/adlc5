#!/usr/bin/env bash
# Vendor Cursor/agent skills into this repository (adlc5 M6).
#
# SOURCES (canonical paths on the developer machine):
#   adlc5-plan (source: fsd3) -> ~/.agents/skills/adlc5-plan
#   prt      -> ~/.agents/skills/prt
#   discover -> ~/.agents/skills/discover
#   qa       -> ~/.agents/skills/qa
#   pr3      -> ~/.cursor/skills/pr3  (legacy Bitbucket PR3; optional copy)
#   pr-reviewer -> skills/pr-reviewer/ (in-repo; see third-party/MANIFEST.md)
#
# Usage: from repo root, ./scripts/vendor-skills.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="${ROOT}/skills"
mkdir -p "${SKILLS_DIR}"

copy_skill() {
  local name="$1"
  local src="$2"
  if [[ ! -d "${src}" ]]; then
    echo "ERROR: missing source directory: ${src}" >&2
    return 1
  fi
  if [[ ! -f "${src}/SKILL.md" ]]; then
    echo "ERROR: ${src}/SKILL.md not found" >&2
    return 1
  fi
  rm -rf "${SKILLS_DIR}/${name}"
  cp -R "${src}" "${SKILLS_DIR}/${name}"
  echo "Copied ${name} from ${src}"
}

copy_skill adlc5-plan "${HOME}/.agents/skills/fsd3"
copy_skill prt "${HOME}/.agents/skills/prt"
copy_skill discover "${HOME}/.agents/skills/discover"
copy_skill qa "${HOME}/.agents/skills/qa"

if [[ -d "${HOME}/.cursor/skills/pr3" ]]; then
  copy_skill pr3 "${HOME}/.cursor/skills/pr3"
else
  echo "SKIP: pr3 — install legacy skill to ~/.cursor/skills/pr3 if needed"
fi

echo "Verifying SKILL.md for each vendored skill..."
for name in adlc5-plan prt discover qa; do
  if [[ ! -f "${SKILLS_DIR}/${name}/SKILL.md" ]]; then
    echo "ERROR: ${SKILLS_DIR}/${name}/SKILL.md missing after copy" >&2
    exit 1
  fi
done
if [[ ! -f "${SKILLS_DIR}/pr-reviewer/SKILL.md" ]]; then
  echo "ERROR: ${SKILLS_DIR}/pr-reviewer/SKILL.md missing (ADLC5 in-repo skill)" >&2
  exit 1
fi
echo "All vendored skills OK. ADLC5 @pr-reviewer remains at skills/pr-reviewer/."
