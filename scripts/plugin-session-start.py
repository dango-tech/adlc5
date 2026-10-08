#!/usr/bin/env python3
"""Claude Code SessionStart hook: tell the session which ADLC5 runtime is active.

The skills say `./scripts/adlc5 ...`. In plugin mode the runtime lives in the package
cache, so this hook states the mapping once per session (short, factual), exports
ADLC5_ROOT for the Bash tool through CLAUDE_ENV_FILE, and reports a stale workspace
binding or classic-install duplicates. Never fails the session: any error → no output.
"""
from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from lib.coexistence import find_duplicates  # noqa: E402
from lib.runtime_binding import binding_state  # noqa: E402


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        payload = {}
    cwd = payload.get("cwd") if isinstance(payload, dict) else None
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or cwd or os.getcwd()).resolve()
    version = (ROOT / "core" / "VERSION").read_text(encoding="utf-8").strip()

    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if env_file:
        with open(env_file, "a", encoding="utf-8") as handle:
            handle.write(f"export ADLC5_ROOT={shlex.quote(str(ROOT))}\n")

    lines = [
        f"ADLC5 plugin {version} runtime: {ROOT}",
        "In ADLC5 skills, `./scripts/X` and `{adlc5_root}/scripts/X` mean that runtime. "
        "Kernel: `adlc5 <command> --workspace <repo>` (on PATH). Other scripts: `adlc5-run <path under scripts/> ...`. "
        "Lifecycle state belongs in the consumer repository's .adlc5/, never in the plugin directory.",
    ]
    if not (project / ".adlc5").is_dir():
        lines.append(f"{project} has no .adlc5/ yet; the adlc5-setup skill initializes it.")
    else:
        state = binding_state(project, ROOT)
        if state:
            lines.append(state)
    for item in find_duplicates(project):
        lines.append(f"Coexistence notice ({item['kind']}): {item['path']} — {item['message']}")

    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n".join(lines)}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # fail open
        sys.exit(0)
