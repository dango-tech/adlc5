#!/usr/bin/env python3
"""Estimate context token budget before orchestrator/subagent invocation (v2).

Usage:
  ./scripts/memory/budget-check.py --feature NAME [--workspace DIR] [--paths PATH ...]
  ./scripts/memory/budget-check.py --feature NAME --persona analyst [--paths PATH ...]

Exit 0 within budget, 1 over budget or persona violation, 2 warn (no paths), 3 error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.personas_load import (  # noqa: E402
    check_persona_context,
    get_persona_for_step,
    persona_mode_enabled,
)
from lib.policies_load import load_policies  # noqa: E402
from lib.state_v2 import is_v2_state, load_feature_state  # noqa: E402


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature", required=True)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--persona", default="")
    parser.add_argument("--paths", nargs="*", default=[])
    parser.add_argument("--handoff", action="store_true", help="measure an assembled handoff only")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    state = load_feature_state(workspace, args.feature)
    if not state:
        print(json.dumps({"status": "error", "message": "state.json missing"}))
        return 3

    policies = load_policies(workspace, args.feature)
    budget = int((state.get("memory") or {}).get("context_budget_tokens") or 8000)
    paths = list(args.paths)

    index = workspace / ".adlc5" / args.feature / "memory" / "INDEX.md"
    if not args.handoff and index.is_file() and str(index) not in paths:
        paths.insert(0, str(index))

    if not args.handoff and is_v2_state(state):
        stage = state.get("current_stage", "specify")
        summary = workspace / ".adlc5" / args.feature / "memory" / "summaries" / f"{stage}.md"
        if summary.is_file():
            paths.append(str(summary))

    persona_id = args.persona or (state.get("persona") or {}).get("active") or ""
    if not persona_id and is_v2_state(state):
        persona_id = get_persona_for_step(state.get("current_step", "")) or ""

    persona_check = None
    if persona_id and persona_mode_enabled(policies):
        persona_check = check_persona_context(persona_id, paths, args.feature)
        if persona_check["status"] != "pass":
            print(
                json.dumps(
                    {
                        "status": "fail",
                        "reason": "persona_context_violation",
                        "persona_check": persona_check,
                        "budget": budget,
                    },
                    indent=2,
                )
            )
            return 1

    if not paths:
        print(json.dumps({"status": "warn", "message": "no paths to measure", "budget": budget}))
        return 2

    total = 0
    details = []
    for p in dict.fromkeys(paths):
        path = Path(p)
        if not path.is_absolute():
            path = workspace / path
        if not path.is_file():
            details.append({"path": p, "tokens": 0, "status": "missing"})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        tokens = estimate_tokens(text)
        total += tokens
        details.append({"path": str(path), "tokens": tokens})
        try:
            details[-1]["path"] = str(path.relative_to(workspace))
        except ValueError:
            pass

    missing = [d["path"] for d in details if d.get("status") == "missing"]
    within = total <= budget and not missing
    out = {
        "status": "pass" if within else "fail",
        "estimated_tokens": total,
        "budget": budget,
        "within_budget": within,
        "paths": details,
        "missing": missing,
        "measurement": "characters/4 estimate of supplied content",
        "host_overhead": "unknown; subsequent reads and hidden host prompts are excluded",
    }
    if persona_check:
        out["persona_check"] = persona_check
    print(json.dumps(out, indent=2))
    return 0 if within else 1


if __name__ == "__main__":
    sys.exit(main())
