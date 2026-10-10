#!/usr/bin/env python3
"""Lint code-spec YAML frontmatter (lever 2 — machine-checkable code specs).

`tasks-2-code-spec-complete` used to accept any directory of `.md` files as
"code specs complete." This script replaces that weak check with a real one:
each `tasks/code-spec/{story-id}.md` must carry a `---`-delimited YAML
frontmatter block naming its files, its tests, and its acceptance criteria,
so `check-gates.py` and `./scripts/verify-story.py` have something concrete
to check instead of re-deriving it by reading prose.

Frontmatter schema (see templates/feature-docs/code-spec.md for a skeleton):

  story_id: US-001                       # required, non-empty
  files_to_create: [path, ...]           # required (may be empty list)
  files_to_modify: [path, ...]           # required (may be empty list)
  tests:                                 # required, non-empty
    - file: path/to/test_file.py
      name: test_function_name
      scenario: optional prose
  acceptance_criteria: [AC-1, AC-2]      # required, non-empty
  acceptance_checks:                    # required; each criterion maps to a named assertion
    AC-1: [test_file.py::test_named_case]
  signatures:                            # optional
    - symbol: create_item
      kind: function                     # function | method | class
      file: path/to/file.py

Usage:
  ./scripts/tasks/spec-lint.py --feature NAME [--workspace DIR] [--story-id ID]

Stdout: JSON {status, feature, specs_checked, results: [...]}
Exit: 0 pass (no blockers in any spec checked), 1 fail, 2 usage/IO error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.simple_yaml import load_frontmatter  # noqa: E402
from lib.state_v2 import load_feature_state  # noqa: E402

SIGNATURE_KINDS = {"function", "method", "class"}


def _is_nonempty_str(v: object) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _is_str_list(v: object) -> bool:
    return isinstance(v, list) and all(isinstance(x, str) for x in v)


def _suspicious_path(p: str) -> str | None:
    if p.startswith("/"):
        return "absolute path"
    if ".." in Path(p).parts:
        return "contains .."
    return None


def code_spec_paths(feature_dir: Path) -> list[Path]:
    for base in ("tasks/code-spec", "delivery/code-spec"):
        d = feature_dir / base
        if d.is_dir():
            paths = sorted(d.glob("*.md"))
            if paths:
                return paths
    return []


def lint_one(path: Path, *, known_story_ids: set[str] | None) -> dict:
    blockers: list[str] = []
    warnings: list[str] = []

    text = path.read_text(encoding="utf-8", errors="replace")
    fm, _body = load_frontmatter(text)

    if fm is None:
        return {
            "path": str(path),
            "story_id": None,
            "status": "fail",
            "blockers": ["frontmatter block present but is not valid YAML — fix the syntax, don't strip it"],
            "warnings": [],
        }
    if not fm:
        return {
            "path": str(path),
            "story_id": None,
            "status": "fail",
            "blockers": ["missing YAML frontmatter (--- ... --- block at top of file)"],
            "warnings": [],
        }

    story_id = fm.get("story_id")
    if not _is_nonempty_str(story_id):
        blockers.append("story_id missing or empty")
    elif known_story_ids is not None and story_id not in known_story_ids:
        warnings.append(f"story_id '{story_id}' not found in state.tasks.stories[]")

    files_create = fm.get("files_to_create")
    files_modify = fm.get("files_to_modify")
    if not _is_str_list(files_create):
        blockers.append("files_to_create must be a list of path strings (may be empty)")
        files_create = []
    if not _is_str_list(files_modify):
        blockers.append("files_to_modify must be a list of path strings (may be empty)")
        files_modify = []
    if _is_str_list(fm.get("files_to_create")) and _is_str_list(fm.get("files_to_modify")):
        all_files = [*files_create, *files_modify]
        if not all_files:
            warnings.append("files_to_create and files_to_modify are both empty — spec touches no files")
        for p in all_files:
            reason = _suspicious_path(p)
            if reason:
                blockers.append(f"suspicious path '{p}': {reason}")

    tests = fm.get("tests")
    if not isinstance(tests, list) or not tests:
        blockers.append("tests must be a non-empty list")
    else:
        for i, t in enumerate(tests):
            if not isinstance(t, dict):
                blockers.append(f"tests[{i}] must be a mapping with file/name")
                continue
            if not _is_nonempty_str(t.get("file")):
                blockers.append(f"tests[{i}].file missing or empty")
            if not _is_nonempty_str(t.get("name")):
                blockers.append(f"tests[{i}].name missing or empty")
            fname = t.get("file")
            if isinstance(fname, str) and "test" not in fname.lower():
                warnings.append(f"tests[{i}].file '{fname}' doesn't look like a test path (heuristic, non-blocking)")

    ac = fm.get("acceptance_criteria")
    if not isinstance(ac, list) or not ac:
        blockers.append("acceptance_criteria must be a non-empty list")
    checks = fm.get("acceptance_checks")
    if isinstance(ac, list) and ac:
        if not isinstance(checks, dict):
            blockers.append("acceptance_checks must map every acceptance criterion to named checks")
        else:
            missing = [item for item in ac if item not in checks]
            unknown = [item for item in checks if item not in ac]
            if missing:
                blockers.append("acceptance criteria lack named checks: " + ", ".join(map(str, missing)))
            if unknown:
                blockers.append("acceptance_checks contains unknown criteria: " + ", ".join(map(str, unknown)))
            for criterion, names in checks.items():
                if not isinstance(names, list) or not names or any(not _is_nonempty_str(name) or "::" not in name for name in names):
                    blockers.append(f"acceptance_checks[{criterion}] must be a non-empty list of file::test names")
                elif isinstance(tests, list):
                    test_names = {f"{test.get('file')}::{test.get('name')}" for test in tests if isinstance(test, dict)}
                    for name in names:
                        if name not in test_names:
                            blockers.append(f"acceptance check '{name}' must match a declared tests[] file and name")

    signatures = fm.get("signatures")
    if signatures is not None:
        if not isinstance(signatures, list):
            warnings.append("signatures should be a list when present")
        else:
            for i, s in enumerate(signatures):
                if not isinstance(s, dict):
                    warnings.append(f"signatures[{i}] should be a mapping")
                    continue
                if not _is_nonempty_str(s.get("symbol")):
                    warnings.append(f"signatures[{i}].symbol missing or empty")
                kind = s.get("kind")
                if kind not in SIGNATURE_KINDS:
                    warnings.append(f"signatures[{i}].kind '{kind}' not one of {sorted(SIGNATURE_KINDS)}")

    status = "fail" if blockers else "pass"
    return {
        "path": str(path),
        "story_id": story_id if _is_nonempty_str(story_id) else None,
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--feature", required=True)
    p.add_argument("--workspace", default=".")
    p.add_argument("--story-id", default=None, help="Lint only this story's code spec")
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    workspace = Path(args.workspace).resolve()
    feature_dir = workspace / ".adlc5" / args.feature
    if not feature_dir.is_dir():
        print(json.dumps({"status": "error", "message": f"feature dir not found: {feature_dir}"}), file=sys.stderr)
        return 2

    known_story_ids: set[str] | None = None
    component_story_ids: set[str] = set()
    state = load_feature_state(workspace, args.feature)
    if state:
        stories = (state.get("tasks") or {}).get("stories")
        if isinstance(stories, list):
            known_story_ids = {str(s.get("id")) for s in stories if isinstance(s, dict) and s.get("id")}
            # Integration stories represent cross-story wiring/E2E, not an
            # isolated file boundary of their own — excluded from the
            # one-spec-per-story coverage requirement below, matching
            # check-gates.py's existing type != "integration" convention.
            component_story_ids = {
                str(s.get("id"))
                for s in stories
                if isinstance(s, dict) and s.get("id") and s.get("type") != "integration"
            }

    paths = code_spec_paths(feature_dir)
    if args.story_id:
        paths = [p for p in paths if p.stem in (args.story_id, f"US-{args.story_id}")]
        if not paths:
            print(
                json.dumps({"status": "error", "message": f"no code spec found for story-id {args.story_id}"}),
                file=sys.stderr,
            )
            return 2

    if not paths and not component_story_ids:
        print(
            json.dumps(
                {
                    "status": "fail",
                    "feature": args.feature,
                    "specs_checked": 0,
                    "results": [],
                    "message": "no code specs found under tasks/code-spec/",
                }
            )
        )
        return 1

    results = [lint_one(path, known_story_ids=known_story_ids) for path in paths]

    # Every planned (non-integration) story needs its own matching spec —
    # a directory with N-1 well-formed specs for N planned stories must not
    # pass. Scoped to full-feature lint (--story-id already targets one).
    if not args.story_id and component_story_ids:
        linted_ids = {r["story_id"] for r in results if r.get("story_id")}
        missing = sorted(component_story_ids - linted_ids)
        if missing:
            results.append(
                {
                    "path": None,
                    "story_id": None,
                    "status": "fail",
                    "blockers": [f"no code spec found for planned story '{sid}'" for sid in missing],
                    "warnings": [],
                }
            )

    overall = "fail" if any(r["status"] == "fail" for r in results) else "pass"
    out = {
        "status": overall,
        "feature": args.feature,
        "specs_checked": len(paths),
        "results": results,
    }
    print(json.dumps(out, indent=2))
    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
