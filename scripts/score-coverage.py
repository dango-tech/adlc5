#!/usr/bin/env python3
"""Parse coverage artifacts or emit skipped JSON when none present.

Usage:
  ./scripts/score-coverage.py --feature NAME [--workspace DIR] [--threshold 80]

Exit 0 pass, 1 fail, 2 skipped/warn, 3 error
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def emit_telemetry(feature: str, event: str, status: str, phase: str, details: dict) -> None:
    lib = SCRIPT_DIR / "lib" / "telemetry.sh"
    if not lib.is_file():
        return
    details_json = json.dumps(details)
    env = os.environ.copy()
    env["ADLC5_WORKSPACE"] = str(Path(os.environ.get("ADLC5_WORKSPACE", ".")).resolve())
    subprocess.run(
        [
            "bash",
            "-c",
            f'source "{lib}" && telemetry_emit "{feature}" "{event}" "score-coverage.py" "{status}" "{phase}" \'{details_json}\'',
        ],
        env=env,
        check=False,
        capture_output=True,
    )


def parse_coverage_json(path: Path) -> float | None:
    data = json.loads(path.read_text(encoding="utf-8"))
    # pytest-cov coverage.json totals
    if "totals" in data and "percent_covered" in data["totals"]:
        return float(data["totals"]["percent_covered"])
    # jest coverage-summary style
    if "total" in data and "lines" in data["total"]:
        pct = data["total"]["lines"].get("pct")
        if pct is not None:
            return float(pct)
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature", required=True)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--threshold", type=float, default=80.0)
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    os.environ["ADLC5_WORKSPACE"] = str(workspace)
    phase = ""
    sys.path.insert(0, str(SCRIPT_DIR))
    from lib.adlc5_paths import load_state  # noqa: E402

    state = load_state(workspace, args.feature)
    if state:
        phase = state.get("current_step") or state.get("current_phase", "")

    emit_telemetry(args.feature, "script.start", "ok", phase, {})

    candidates = [
        workspace / "coverage.json",
        workspace / "coverage" / "coverage-summary.json",
        workspace / "coverage" / "coverage-final.json",
    ]
    line_pct: float | None = None
    source = None
    for path in candidates:
        if path.is_file():
            try:
                line_pct = parse_coverage_json(path)
                source = str(path.relative_to(workspace))
                break
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

    if line_pct is None:
        out = {
            "status": "skipped",
            "line_coverage_percent": None,
            "threshold": args.threshold,
            "source": None,
            "message": "no coverage artifact found (run tests with coverage first)",
        }
        print(json.dumps(out, indent=2))
        emit_telemetry(args.feature, "script.end", "skipped", phase, out)
        return 2

    status = "pass" if line_pct >= args.threshold else "fail"
    out = {
        "status": status,
        "line_coverage_percent": round(line_pct, 2),
        "threshold": args.threshold,
        "source": source,
    }
    print(json.dumps(out, indent=2))
    emit_telemetry(args.feature, "script.end", status, phase, out)
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
