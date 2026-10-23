#!/usr/bin/env python3
"""Optional Claude Code status-line adapter; reads only a local Pulse cache."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "scripts"))
from lib.package_guard import check_workspace  # noqa: E402
from lib.pulse import band  # noqa: E402
from pulse import _load_cache  # noqa: E402


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("status-line input exceeds limit")
        session = json.loads(raw or b"{}")
        if not isinstance(session, dict):
            raise ValueError("invalid session input")
        workspace_text = (session.get("workspace", {}).get("current_dir") if isinstance(session.get("workspace"), dict) else None) or session.get("cwd") or os.environ.get("ADLC5_WORKSPACE") or os.environ.get("CLAUDE_PROJECT_DIR")
        feature = os.environ.get("ADLC5_FEATURE")
        if not isinstance(workspace_text, str):
            print("ADLC5 Pulse · snapshot unavailable")
            return 0
        workspace = Path(workspace_text).resolve(strict=True)
        problem = check_workspace(ROOT, workspace)
        if problem:
            print("ADLC5 Pulse · snapshot unavailable")
            return 0
        snapshot = _load_cache(workspace, feature)
        if not snapshot:
            print("ADLC5 Pulse · snapshot unavailable")
            return 0
        print(band(snapshot, feature) + " · present freshness unverified")
        return 0
    except Exception:
        print("ADLC5 Pulse · snapshot unavailable")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
