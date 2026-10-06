#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${ROOT}/.cursor/rules"
DEST="${ROOT}/shared/rules/portable"
mkdir -p "$DEST"
count=0
for mdc in "${SRC}"/*.mdc; do
  [[ -f "$mdc" ]] || continue
  name="$(basename "$mdc" .mdc).md"
  awk 'BEGIN{fm=0} /^---$/{fm++; if(fm==1) next; if(fm==2) next} fm>=2 {print}' "$mdc" > "${DEST}/${name}"
  echo "  ${name}"
  count=$((count + 1))
done
echo "Wrote ${count} file(s) to ${DEST}/"
