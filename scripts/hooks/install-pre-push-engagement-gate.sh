#!/usr/bin/env bash
# Install the ADLC5 engagement-gate pre-push backstop into a repo's git hooks.
#
# Usage: install-pre-push-engagement-gate.sh --workspace DIR
#
# Any pre-existing pre-push hook is preserved: it is moved aside to
# pre-push.pre-adlc5 and still runs first (with the same arguments and the same
# stdin), then the gate runs. Both are non-fatal -- the push is never blocked.
set -euo pipefail

MARKER="adlc5-engagement-gate-dispatcher"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
gate_hook="${script_dir}/pre-push-engagement-gate.sh"

workspace=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace)
      workspace="${2:-}"
      shift 2
      ;;
    -h|--help)
      sed -n '2,8p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *)
      echo "install-pre-push-engagement-gate: unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$workspace" ]]; then
  echo "install-pre-push-engagement-gate: --workspace DIR is required" >&2
  exit 2
fi
if [[ ! -d "$workspace" ]]; then
  echo "install-pre-push-engagement-gate: not a directory: $workspace" >&2
  exit 1
fi
if [[ ! -f "$gate_hook" ]]; then
  echo "install-pre-push-engagement-gate: missing $gate_hook" >&2
  exit 1
fi

workspace="$(cd "$workspace" && pwd)"
hooks_dir="$(git -C "$workspace" rev-parse --git-path hooks 2>/dev/null || true)"
if [[ -z "$hooks_dir" ]]; then
  echo "install-pre-push-engagement-gate: $workspace is not a git repository" >&2
  exit 1
fi
case "$hooks_dir" in
  /*) ;;
  *) hooks_dir="${workspace}/${hooks_dir}" ;;
esac

chmod +x "$gate_hook"
mkdir -p "$hooks_dir"
hook="${hooks_dir}/pre-push"
preserved="${hooks_dir}/pre-push.pre-adlc5"

chain=""
if [[ -e "$hook" ]] && ! grep -q "$MARKER" "$hook" 2>/dev/null; then
  if [[ -e "$preserved" ]]; then
    preserved="${preserved}.$(date +%Y%m%d%H%M%S)"
  fi
  mv "$hook" "$preserved"
  chmod +x "$preserved" 2>/dev/null || true
  chain="$preserved"
  echo "install-pre-push-engagement-gate: existing hook preserved at $preserved"
elif [[ -x "$preserved" ]]; then
  # Re-install over our own dispatcher: keep chaining what we preserved before.
  chain="$preserved"
fi

{
  echo '#!/usr/bin/env bash'
  echo "# ${MARKER} — installed by scripts/hooks/install-pre-push-engagement-gate.sh"
  echo '# Chains any pre-existing hook, then the ADLC5 engagement-gate backstop.'
  echo '# Both are non-fatal: this hook always exits 0 and never blocks a push.'
  echo 'set -uo pipefail'
  echo ''
  echo 'refs="$(cat)"'
  if [[ -n "$chain" ]]; then
    echo "previous=\"$chain\""
    echo 'if [[ -x "$previous" ]]; then'
    echo '  printf '"'"'%s'"'"' "$refs" | "$previous" "$@" || true'
    echo 'fi'
    echo ''
  fi
  echo "gate=\"$gate_hook\""
  echo 'if [[ -f "$gate" ]]; then'
  echo '  printf '"'"'%s'"'"' "$refs" | bash "$gate" "$@" || true'
  echo 'fi'
  echo ''
  echo 'exit 0'
} >"$hook"

chmod +x "$hook"
echo "install-pre-push-engagement-gate: installed $hook"
