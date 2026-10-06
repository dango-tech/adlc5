#!/usr/bin/env python3
"""Assemble and budget a concrete story handoff; never trim required content."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.personas_load import check_persona_context, persona_mode_enabled
from lib.policies_load import load_policies, profile_name
from lib.simple_yaml import load_frontmatter
from lib.state_v2 import load_feature_state


def assemble(workspace: Path, feature: str, story_id: str, persona: str) -> tuple[str, list[str]]:
    workspace = workspace.resolve()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", feature):
        raise ValueError("feature must be kebab-case")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", story_id):
        raise ValueError("invalid story id")
    directory = workspace / ".adlc5" / feature
    state = load_feature_state(workspace, feature)
    if not state:
        raise ValueError("state.json missing")
    story = next((s for s in (state.get("tasks") or {}).get("stories", []) if s.get("id") == story_id), None)
    if story is None:
        raise ValueError("story not present in state.tasks.stories")
    tiny = profile_name(load_policies(workspace, feature)) == "tiny"
    spec = next((directory / base / name for base in ("tasks/code-spec", "delivery/code-spec")
                 for name in (f"{story_id}.md", f"US-{story_id}.md")
                 if (directory / base / name).is_file()), None)
    if spec is None and tiny:
        spec = directory / "change.md"
    if spec is None or not spec.is_file():
        raise ValueError("required code spec missing (tiny: provide change.md)")
    handoff = directory / "spec-handoff.md"
    if not handoff.is_file():
        raise ValueError("required spec-handoff.md missing")

    parts = [f"# Context pack — {story_id}\n\nFeature: {feature}\nPersona: {persona}",
             "## Story and acceptance\n\n```json\n" + json.dumps(story, indent=2) + "\n```"]
    sources: list[str] = []

    def include(path: Path, title: str) -> None:
        resolved = path.resolve()
        if not resolved.is_relative_to(workspace):
            raise ValueError(f"context source escapes workspace: {path}")
        rel = str(path.relative_to(workspace))
        sources.append(rel)
        parts.append(f"## {title}\n\nSource: `{rel}`\n\n" + path.read_text(encoding="utf-8"))

    include(spec, "Code spec" if spec.name != "change.md" else "Bounded change")
    include(handoff, "Locked requirements")
    for rel in ("AGENTS.md", ".agents/architecture.yaml", ".agents/boundaries.yaml", ".agents/commands.yaml"):
        path = workspace / rel
        if path.is_file():
            include(path, f"Repository rules: {rel}")
    fm, _ = load_frontmatter(spec.read_text(encoding="utf-8"))
    if spec.name != "change.md" and (not fm or fm.get("story_id") != story_id):
        raise ValueError("code spec needs valid frontmatter matching the story id")
    declared = (fm or {}).get("files_to_create", []) + (fm or {}).get("files_to_modify", []) + story.get("files", [])
    if not declared or any(not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts for path in declared):
        raise ValueError("declare a nonempty safe file boundary in the story or code spec")
    boundary = sorted(set(declared))
    parts.append("## File boundary\n\n" + json.dumps(boundary))
    parts.append("## Repository navigation\n\nInspect boundary files and their callers before editing. "
                 "Query `.agent-cache/repo-index.json` when available; code is authoritative.")
    if persona == "tester":
        for rel in ("design/plan.md", "design/1a-discovery.md", "design/1b-contracts.md", "design/1c-operations.md"):
            path = directory / rel
            if path.is_file():
                include(path, rel)
    else:
        parts.append("## Design pointers\n\nOmitted for coder persona — use the code spec.")
    if persona_mode_enabled(load_policies(workspace, feature)):
        result = check_persona_context(persona, sources, feature)
        if result["status"] != "pass":
            raise ValueError("persona context violation: " + json.dumps(result))
    return "\n\n".join(parts) + "\n", sources


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--feature", required=True)
    parser.add_argument("--story-id", required=True)
    parser.add_argument("--persona", choices=("coder", "tester"), default="coder")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    try:
        content, sources = assemble(workspace, args.feature, args.story_id, args.persona)
        directory = workspace / ".adlc5" / args.feature / "memory/context-packs"
        directory.mkdir(parents=True, exist_ok=True)
        prefix = "story" if args.persona == "coder" else "verify"
        pack = directory / f"{prefix}-{args.story_id}.md"
        pack.write_text(content, encoding="utf-8")
        budget = subprocess.run([sys.executable, str(ROOT / "scripts/memory/budget-check.py"),
                                 "--feature", args.feature, "--workspace", str(workspace),
                                 "--persona", args.persona, "--handoff", "--paths", str(pack)],
                                capture_output=True, text=True)
        report = json.loads(budget.stdout)
        result = {"status": "ok" if budget.returncode == 0 else "fail", "pack": str(pack.relative_to(workspace)),
                  "persona": args.persona, "sources": sources, "budget": report}
        print(json.dumps(result))
        return 0 if budget.returncode == 0 else 1
    except (ValueError, OSError, TypeError) as exc:
        print(json.dumps({"status": "fail", "message": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
