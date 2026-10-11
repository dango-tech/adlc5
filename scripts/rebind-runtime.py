#!/usr/bin/env python3
"""Repair a consumer's stale ADLC5 runtime binding without touching anything else.

`init-workspace.sh` records `adlc5_root` in `.adlc5/workspace.json`. When ADLC5 runs
from a host package cache (a plugin), that
path changes on update/relocation. This tool repoints ONLY those two values, and
only when the recorded root is stale: the path is gone or is no longer an ADLC5 root
(for example a package cache that moved after an update).

A recorded root that still exists is kept — a source clone or another host's package —
as is every other key/line. Hosts never depend on this binding: hooks, MCP and `bin/`
select their own current runtime, so two hosts with different caches coexist.

Usage: rebind-runtime.py --workspace DIR [--adlc5-root DIR] [--dry-run]
Stdout: one JSON object. Exit 0 on success/no-op, 2 on usage error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lib.package_guard import check_workspace  # noqa: E402
from lib.runtime_binding import is_adlc5_root, rebind_json, rebind_yaml  # noqa: E402

DEFAULT_ROOT = HERE.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--adlc5-root", default=str(DEFAULT_ROOT))
    parser.add_argument("--dry-run", action="store_true")
    ns = parser.parse_args()
    workspace, root = Path(ns.workspace).resolve(), Path(ns.adlc5_root).resolve()
    problem = check_workspace(root, workspace)
    if problem or not is_adlc5_root(str(root)):
        print(json.dumps({"status": "error", "message": problem or f"not an ADLC5 root: {root}"}))
        return 2
    adlc5 = workspace / ".adlc5"
    results = [rebind_json(adlc5 / "workspace.json", root, ns.dry_run), rebind_yaml(adlc5 / "config.yaml", root, ns.dry_run)]
    print(json.dumps({"status": "ok", "adlc5_root": str(root), "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
