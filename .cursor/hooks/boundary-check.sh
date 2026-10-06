#!/usr/bin/env bash
# H4 — Clean Architecture boundary check (optional stub).
# Not wired in hooks.json by default — enable in afterFileEdit when layer rules are stable.
#
# Intended behavior: inspect edited file path and imports for dependency-rule violations
# (e.g. domain layer importing framework adapters). Low false-positive heuristics required.
set -euo pipefail

# No-op stub — extend when S2 clean-architecture-review rules are project-aware.
exit 0
