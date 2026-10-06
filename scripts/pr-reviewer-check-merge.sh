#!/usr/bin/env bash
exec "$(cd "$(dirname "$0")" && pwd)/pr-reviewer/pr-reviewer-check-merge.sh" "$@"
