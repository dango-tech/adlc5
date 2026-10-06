#!/usr/bin/env bash
# H1 — Basic secret pattern scan on user prompts before submission.
set -euo pipefail

input="$(cat)"

prompt="$(printf '%s' "$input" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(0)
for key in ('prompt', 'text', 'content'):
    value = data.get(key)
    if isinstance(value, str) and value.strip():
        print(value, end='')
        break
" 2>/dev/null || true)"

if [[ -z "$prompt" ]]; then
  exit 0
fi

patterns=(
  'AKIA[0-9A-Z]{16}'
  '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'
  '(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token)[[:space:]]*[:=][[:space:]]*[^[:space:]]{8,}'
  'ghp_[A-Za-z0-9]{20,}'
  'gho_[A-Za-z0-9]{20,}'
  'xox[baprs]-[A-Za-z0-9-]{10,}'
  'password[[:space:]]*[:=][[:space:]]*[^[:space:]]{4,}'
)

for pattern in "${patterns[@]}"; do
  if printf '%s' "$prompt" | grep -Eiq -e "$pattern"; then
    cat <<'EOF'
{
  "continue": false,
  "user_message": "Possible secret detected in your prompt. Remove credentials or use environment variables / secret managers before submitting."
}
EOF
    exit 0
  fi
done

exit 0
