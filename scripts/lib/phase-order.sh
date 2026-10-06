#!/usr/bin/env bash
# Canonical ADLC5 phase order (delivery + lifecycle assure extensions).
# shellcheck disable=SC2034
ADLC5_PHASE_ORDER=(
  plan-1-discovery
  plan-2-contracts
  plan-3-operations
  plan-4-user-stories
  plan-5-code-spec
  build-1-implementation
  assure-1-verification
  assure-2-integration
  completed
  assure-3-qa
  assure-4-pr-reviewer
)

phase_index() {
  local id="$1" i
  for i in "${!ADLC5_PHASE_ORDER[@]}"; do
    [[ "${ADLC5_PHASE_ORDER[$i]}" == "$id" ]] || continue
    echo "$i"
    return 0
  done
  echo "-1"
}

phase_cmp() {
  local a="$1" b="$2"
  local ia ib
  ia=$(phase_index "$a")
  ib=$(phase_index "$b")
  if [[ "$ia" -lt 0 || "$ib" -lt 0 ]]; then
    echo 0
    return
  fi
  if [[ "$ia" -lt "$ib" ]]; then echo -1; elif [[ "$ia" -gt "$ib" ]]; then echo 1; else echo 0; fi
}
