#!/usr/bin/env python3
"""Classify implementation failure reports for bounded retry policy.

Usage:
  ./scripts/delivery-retry-classifier.py --feature NAME \\
    --story-id story-1-foo \\
    [--report-file path.md] [--attempt N] [--stdin]

Stdout: JSON contract (see core/guides/working-memory.md retry_policy).
Exit codes:
  0 — action retry
  1 — action stop (exhausted or non-retryable)
  2 — action escalate
  3 — usage / IO error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))
from lib.adlc5_paths import load_state  # noqa: E402
from lib.policies_load import load_policies  # noqa: E402

TRANSIENT_PATTERNS = [
    r"timeout",
    r"timed out",
    r"connection refused",
    r"econnreset",
    r"rate limit",
    r"temporary",
    r"flaky",
    r"resource temporarily unavailable",
]
ENV_PATTERNS = [
    r"module not found",
    r"no module named",
    r"command not found",
    r"cannot find module",
    r"npm err",
    r"permission denied",
    r"missing dependency",
]
SPEC_PATTERNS = [
    r"ambiguous",
    r"contradiction",
    r"spec says",
    r"unclear requirement",
    r"untestable",
    r"design flaw",
    r"escalat",
]
BLOCKER_PATTERNS = [
    r"blocker",
    r"compilation error",
    r"syntax error",
    r"type error",
    r"signature mismatch",
    r"test failed",
    r"assertionerror",
    r"failed",
]


def load_retry_policy(state: dict, policies: dict) -> dict:
    default = {
        "max_implementation_attempts": 3,
        "max_rework_attempts": 3,
        "transient_retry": True,
        "escalate_on_spec_signal": True,
    }
    legacy = state.get("retry_policy") or {}
    current = (policies.get("autopilot") or {}).get("retry_policy") or {}
    return {
        **default,
        **(legacy if isinstance(legacy, dict) else {}),
        **(current if isinstance(current, dict) else {}),
    }


CATEGORY_TO_CLASS = {
    "transient": "transient",
    "environment": "transient",
    "implementation": "unknown",
    "spec_ambiguity": "spec_ambiguity",
    "exhausted": "unknown",
    "missing_report": "unknown",
    "unknown": "unknown",
}


def enrich_contract(result: dict) -> dict:
    """Add plan contract aliases: class, retryable, suggested_action."""
    category = result.get("category", "unknown")
    action = result.get("action", "stop")
    result["class"] = CATEGORY_TO_CLASS.get(category, "unknown")
    result["retryable"] = action == "retry"
    if action == "retry":
        result["suggested_action"] = "requeue_story_with_failure_context"
    elif action == "escalate":
        result["suggested_action"] = "halt_or_rework_spec"
    else:
        result["suggested_action"] = "present_to_user"
    return result


def classify_text(text: str, attempt: int, policy: dict) -> dict:
    lower = text.lower()
    max_attempts = int(policy.get("max_implementation_attempts", 3))

    if attempt >= max_attempts:
        return {
            "action": "stop",
            "category": "exhausted",
            "reason": f"implementation attempts ({attempt}) >= max ({max_attempts})",
            "attempt": attempt,
            "max_attempts": max_attempts,
            "retry_delay_seconds": 0,
        }

    if policy.get("escalate_on_spec_signal", True):
        for pat in SPEC_PATTERNS:
            if re.search(pat, lower):
                return {
                    "action": "escalate",
                    "category": "spec_ambiguity",
                    "reason": f"spec/design signal matched: {pat}",
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "retry_delay_seconds": 0,
                }

    if policy.get("transient_retry", True):
        for pat in TRANSIENT_PATTERNS:
            if re.search(pat, lower):
                return {
                    "action": "retry",
                    "category": "transient",
                    "reason": f"transient failure signal: {pat}",
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "retry_delay_seconds": 5,
                }

    for pat in ENV_PATTERNS:
        if re.search(pat, lower):
            return {
                "action": "retry",
                "category": "environment",
                "reason": f"environment/setup signal: {pat}",
                "attempt": attempt,
                "max_attempts": max_attempts,
                "retry_delay_seconds": 10,
            }

    for pat in BLOCKER_PATTERNS:
        if re.search(pat, lower):
            return {
                "action": "retry",
                "category": "implementation",
                "reason": f"implementation failure signal: {pat}",
                "attempt": attempt,
                "max_attempts": max_attempts,
                "retry_delay_seconds": 0,
            }

    return {
        "action": "retry",
        "category": "unknown",
        "reason": "no strong escalate/stop signal; default retry",
        "attempt": attempt,
        "max_attempts": max_attempts,
        "retry_delay_seconds": 0,
    }


def read_report(args: argparse.Namespace) -> str:
    if args.stdin:
        return sys.stdin.read()
    if args.report_file:
        return Path(args.report_file).read_text(encoding="utf-8", errors="replace")
    if args.report:
        return args.report
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify Implement build failures for retry policy")
    parser.add_argument("--feature", required=True)
    parser.add_argument("--story-id", required=True)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--report-file")
    parser.add_argument("--report", default="")
    parser.add_argument("--stdin", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    policy: dict = {}
    state = load_state(workspace, args.feature) or {}
    policy = load_retry_policy(state, load_policies(workspace, args.feature))

    report = read_report(args)
    if not report.strip():
        out = enrich_contract(
            {
                "story_id": args.story_id,
                "action": "stop",
                "category": "missing_report",
                "reason": "no failure report provided",
                "attempt": args.attempt,
                "max_attempts": int(policy.get("max_implementation_attempts", 3)),
                "retry_delay_seconds": 0,
            }
        )
        print(json.dumps(out, indent=2))
        return 1

    result = classify_text(report, args.attempt, policy)
    result["story_id"] = args.story_id
    result = enrich_contract(result)
    print(json.dumps(result, indent=2))

    action = result["action"]
    if action == "retry":
        return 0
    if action == "escalate":
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
