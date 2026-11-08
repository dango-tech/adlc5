#!/usr/bin/env python3
"""Minimal SAST/dependency gate: bandit on Python, pip-audit on requirements."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd, label):
    if not shutil.which(cmd[0]):
        print(f"{label}: tool not installed, skipping")
        return None
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    except Exception as e:
        print(f"{label}: error running {cmd[0]}: {e}")
        return False
    print(f"--- {label} ---")
    if r.stdout:
        print(r.stdout)
    if r.stderr:
        print(r.stderr)
    ok = r.returncode == 0
    print(f"{label}: {'PASS' if ok else 'FAIL'} (exit {r.returncode})")
    return ok


def main():
    results = []
    # bandit
    py_files = [str(p) for p in ROOT.rglob("*.py") if ".venv" not in p.parts and "node_modules" not in p.parts]
    if py_files:
        res = run(["bandit", "-q", "-r", ".", "-x", ".venv,node_modules,.git"], "bandit")
        if res is not None:
            results.append(res)
    else:
        print("bandit: no Python files found, skipping")

    # pip-audit on requirements
    reqs = list(ROOT.rglob("requirements*.txt"))
    reqs = [p for p in reqs if ".venv" not in p.parts]
    if reqs:
        for r in reqs:
            res = run(["pip-audit", "-r", str(r)], "pip-audit")
            if res is not None:
                results.append(res)
    else:
        print("pip-audit: no requirements files found, skipping")

    if not results:
        print("No tools available / nothing to scan: PASS (no-op)")
        return 0
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
