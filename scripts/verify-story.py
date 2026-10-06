#!/usr/bin/env python3
"""Deterministic per-story verification (lever 3 — cheaper implement-2-verify).

Runs the mechanical half of story verification from the code spec's YAML
frontmatter (see scripts/tasks/spec-lint.py / templates/feature-docs/code-spec.md)
so @assure-verifier only has to reason about what's actually left: does the
implementation match the design's intent, is the abstraction right, are the
tests meaningful rather than just present. This script does not replace
@assure-verifier — it narrows what it has to re-derive by hand.

Checks:
  file_boundary        — git-changed files (committed-since-branch-baseline,
                          best-effort, union working tree) stay within the
                          UNION of every story's declared files_to_create ∪
                          files_to_modify ∪ tests[].file for this feature —
                          not just this story's, so a parallel implement-1-build
                          batch doesn't flag sibling stories' legitimate files
                          as scope creep. Every declared files_to_create path
                          must exist on disk. Skipped (warn) when the
                          workspace isn't a git repo.
  tests_declared_exist — each tests[].file exists; each tests[].name is
                          found in that file (warn if not — naming/decorator
                          conventions vary, this is a heuristic).
  tests_pass            — ./scripts/run-tests.sh (whole-suite; there is no
                          scoped per-file runner yet — known limitation).
  signatures_match      — cross-checks signatures[] against
                          .agent-cache/symbols.json when the repo index has
                          been built; warn-only (repo-index is optional and
                          generated, and methods aren't indexed separately).
  no_debug_noise        — greps files_to_create/files_to_modify for common
                          debug leftovers (console.log, debugger;,
                          pdb.set_trace(), …). Always warn, never a blocker
                          — too language- and context-dependent to fail on.
  lint_clean             — ./scripts/run-lint.sh.

Usage:
  ./scripts/verify-story.py --feature NAME --story-id ID [--workspace DIR]

Stdout: JSON {status, feature, story_id, checks: [...]}
Exit: 0 pass (no fail-status checks), 1 fail, 2 usage/IO error
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR
sys.path.insert(0, str(ROOT))

from lib.simple_yaml import load_frontmatter  # noqa: E402

DEBUG_PATTERNS = [
    (re.compile(r"console\.log\("), "console.log("),
    (re.compile(r"\bdebugger;"), "debugger;"),
    (re.compile(r"pdb\.set_trace\(\)"), "pdb.set_trace()"),
    (re.compile(r"binding\.pry"), "binding.pry"),
    (re.compile(r"TODO:\s*remove", re.IGNORECASE), "TODO: remove"),
]


def find_code_spec(feature_dir: Path, story_id: str) -> Path | None:
    for base in ("tasks/code-spec", "delivery/code-spec"):
        for name in (f"{story_id}.md", f"US-{story_id}.md"):
            p = feature_dir / base / name
            if p.is_file():
                return p
    return None


def _git(workspace: Path, args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(["git", "-C", str(workspace), *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout


def branch_baseline(workspace: Path) -> str | None:
    """Best-effort merge-base with the feature branch's likely upstream.

    Working-tree status alone misses commits the story already made — those
    files drop out of `git status` the moment they're committed. Diffing
    against the branch point (when discoverable) catches those too. None
    when no candidate upstream ref resolves (no remote, detached, etc.) —
    callers fall back to working-tree-only, same as before.
    """
    for candidate in ("origin/HEAD", "origin/main", "origin/master"):
        ec, _ = _git(workspace, ["rev-parse", "--verify", "--quiet", candidate])
        if ec != 0:
            continue
        ec, out = _git(workspace, ["merge-base", "HEAD", candidate])
        if ec == 0 and out.strip():
            return out.strip()
    return None


def changed_files(workspace: Path) -> list[str] | None:
    """Repo-relative paths changed on this branch: committed-since-baseline
    (best-effort, see branch_baseline) union working tree (staged + unstaged
    + untracked). None if not a git repo."""
    ec, _ = _git(workspace, ["rev-parse", "--is-inside-work-tree"])
    if ec != 0:
        return None

    out: set[str] = set()

    baseline = branch_baseline(workspace)
    if baseline:
        ec, diff_out = _git(workspace, ["diff", "--name-only", f"{baseline}...HEAD"])
        if ec == 0:
            out.update(line.strip() for line in diff_out.splitlines() if line.strip())

    ec, status_out = _git(workspace, ["status", "--porcelain=v1", "--untracked-files=all"])
    if ec == 0:
        for line in status_out.splitlines():
            if not line.strip() or len(line) < 4:
                continue
            path_part = line[3:].strip()
            if " -> " in path_part:
                path_part = path_part.split(" -> ", 1)[1]
            out.add(path_part.strip('"'))

    return sorted(out)


def all_declared_files(feature_dir: Path) -> set[str]:
    """Union of files_to_create/files_to_modify/tests[].file across every
    code spec in the feature — not just the story being verified.

    A parallel implement-1-build batch has several stories' files coexisting
    in the same working tree. Comparing one story's changes against only its
    own declared boundary would falsely flag every sibling story's
    legitimate files as scope creep. Unioning across all stories' specs
    keeps the check about genuinely undeclared work, not who owns what.
    """
    declared: set[str] = set()
    for base in ("tasks/code-spec", "delivery/code-spec"):
        d = feature_dir / base
        if not d.is_dir():
            continue
        for path in d.glob("*.md"):
            fm, _ = load_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
            if not fm:
                continue
            declared.update(fm.get("files_to_create") or [])
            declared.update(fm.get("files_to_modify") or [])
            declared.update(t.get("file") for t in (fm.get("tests") or []) if isinstance(t, dict) and t.get("file"))
    return declared


def check_file_boundary(workspace: Path, fm: dict, feature_dir: Path) -> dict:
    files_create = fm.get("files_to_create") or []
    missing_created = [p for p in files_create if not (workspace / p).is_file()]

    changed = changed_files(workspace)
    if changed is None:
        return {
            "id": "file_boundary",
            "status": "warn",
            "message": "not a git repository (or git unavailable) — boundary check skipped",
        }

    # ADLC5's own bookkeeping (code specs, telemetry, this script's own
    # report) always shows as "changed" under .adlc5/ — that's not the
    # story's production-code boundary, so exclude it rather than false-flag
    # every run as scope creep.
    changed = [c for c in changed if not c.startswith(".adlc5/")]

    feature_boundary = all_declared_files(feature_dir)
    out_of_boundary = sorted(set(changed) - feature_boundary)
    if missing_created:
        return {
            "id": "file_boundary",
            "status": "fail",
            "message": f"declared files_to_create missing on disk: {', '.join(missing_created[:5])}",
        }
    if out_of_boundary:
        return {
            "id": "file_boundary",
            "status": "fail",
            "message": f"changed files not declared by any story's code spec: {', '.join(out_of_boundary[:5])}",
        }
    return {
        "id": "file_boundary",
        "status": "pass",
        "message": f"{len(changed)} changed file(s) within the feature's declared boundary "
        f"({len(feature_boundary)} file(s) across all stories)",
    }


def check_tests_declared_exist(workspace: Path, fm: dict) -> dict:
    tests = fm.get("tests") or []
    if not tests:
        return {"id": "tests_declared_exist", "status": "fail", "message": "no tests[] declared in frontmatter"}

    missing_files: list[str] = []
    missing_names: list[str] = []
    for t in tests:
        if not isinstance(t, dict):
            continue
        f, name = t.get("file"), t.get("name")
        if not f:
            continue
        path = workspace / f
        if not path.is_file():
            missing_files.append(f)
            continue
        if name:
            text = path.read_text(encoding="utf-8", errors="replace")
            if name not in text:
                missing_names.append(f"{f}::{name}")

    if missing_files:
        return {
            "id": "tests_declared_exist",
            "status": "fail",
            "message": f"declared test files missing: {', '.join(missing_files[:5])}",
        }
    if missing_names:
        return {
            "id": "tests_declared_exist",
            "status": "warn",
            "message": f"test name string not found in file (naming/decorator convention?): {', '.join(missing_names[:5])}",
        }
    return {"id": "tests_declared_exist", "status": "pass", "message": f"{len(tests)} declared test(s) present"}


def _run_json_script(script: Path, args: list[str]) -> tuple[int, dict | None, str]:
    if not script.is_file():
        return 2, None, f"missing: {script}"
    proc = subprocess.run(["bash", str(script), *args], capture_output=True, text=True)
    try:
        return proc.returncode, json.loads(proc.stdout), proc.stderr.strip()
    except json.JSONDecodeError:
        return proc.returncode, None, proc.stderr.strip() or proc.stdout.strip()


def check_tests_pass(workspace: Path, feature: str) -> dict:
    script = ROOT / "run-tests.sh"
    ec, data, err = _run_json_script(script, ["--feature", feature, "--workspace", str(workspace)])
    if data is None:
        return {"id": "tests_pass", "status": "fail", "message": err or "run-tests.sh produced no parseable output"}
    status = data.get("status", "fail")
    if status == "pass":
        return {"id": "tests_pass", "status": "pass", "message": f"{data.get('runner')}: {data.get('passed', '?')} passed"}
    if status == "skipped":
        return {"id": "tests_pass", "status": "warn", "message": "no test runner detected — could not confirm"}
    return {"id": "tests_pass", "status": "fail", "message": f"{data.get('runner')}: tests failed"}


def check_lint_clean(workspace: Path, feature: str) -> dict:
    script = ROOT / "run-lint.sh"
    ec, data, err = _run_json_script(script, ["--feature", feature, "--workspace", str(workspace)])
    if data is None:
        return {"id": "lint_clean", "status": "fail", "message": err or "run-lint.sh produced no parseable output"}
    status = data.get("status", "fail")
    if status == "pass":
        return {"id": "lint_clean", "status": "pass", "message": f"{data.get('runner')}: clean"}
    if status == "skipped":
        return {"id": "lint_clean", "status": "warn", "message": "no linter detected — could not confirm"}
    return {"id": "lint_clean", "status": "fail", "message": f"{data.get('runner')}: {data.get('errors', '?')} error(s)"}


def check_signatures_match(workspace: Path, fm: dict) -> dict:
    signatures = fm.get("signatures") or []
    if not signatures:
        return {"id": "signatures_match", "status": "pass", "message": "no signatures[] declared — nothing to check"}

    symbols_path = workspace / ".agent-cache" / "symbols.json"
    if not symbols_path.is_file():
        return {
            "id": "signatures_match",
            "status": "warn",
            "message": "no .agent-cache/symbols.json — run `adlc5 repo-index build` to enable this check",
        }
    try:
        symbols = json.loads(symbols_path.read_text(encoding="utf-8")).get("symbols") or []
    except json.JSONDecodeError:
        return {"id": "signatures_match", "status": "warn", "message": ".agent-cache/symbols.json unparseable"}

    known = {(s.get("file"), s.get("name")) for s in symbols if isinstance(s, dict)}
    missing = [
        f"{s.get('name')} in {s.get('file')}"
        for s in signatures
        if isinstance(s, dict) and (s.get("file"), s.get("symbol")) not in known
    ]
    if missing:
        return {
            "id": "signatures_match",
            "status": "warn",
            "message": f"not found in repo index (may be a method, or index is stale): {', '.join(missing[:5])}",
        }
    return {"id": "signatures_match", "status": "pass", "message": f"{len(signatures)} signature(s) found in repo index"}


def check_no_debug_noise(workspace: Path, fm: dict) -> dict:
    paths = [*(fm.get("files_to_create") or []), *(fm.get("files_to_modify") or [])]
    hits: list[str] = []
    for rel in paths:
        p = workspace / rel
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern, label in DEBUG_PATTERNS:
            if pattern.search(text):
                hits.append(f"{rel}: {label}")
    if hits:
        return {"id": "no_debug_noise", "status": "warn", "message": f"possible debug leftovers: {', '.join(hits[:5])}"}
    return {"id": "no_debug_noise", "status": "pass", "message": "no known debug patterns found"}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--feature", required=True)
    p.add_argument("--story-id", required=True)
    p.add_argument("--workspace", default=".")
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    workspace = Path(args.workspace).resolve()
    feature_dir = workspace / ".adlc5" / args.feature
    spec_path = find_code_spec(feature_dir, args.story_id)
    if spec_path is None:
        print(
            json.dumps({"status": "error", "message": f"no code spec found for story-id {args.story_id}"}),
            file=sys.stderr,
        )
        return 2

    fm, _body = load_frontmatter(spec_path.read_text(encoding="utf-8", errors="replace"))
    if not fm:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": f"{spec_path} has no parseable frontmatter — run spec-lint.py first",
                }
            ),
            file=sys.stderr,
        )
        return 2

    checks = [
        check_file_boundary(workspace, fm, feature_dir),
        check_tests_declared_exist(workspace, fm),
        check_tests_pass(workspace, args.feature),
        check_signatures_match(workspace, fm),
        check_no_debug_noise(workspace, fm),
        check_lint_clean(workspace, args.feature),
    ]
    overall = "fail" if any(c["status"] == "fail" for c in checks) else "pass"

    out = {
        "status": overall,
        "feature": args.feature,
        "story_id": args.story_id,
        "code_spec_path": str(spec_path),
        "checks": checks,
    }
    print(json.dumps(out, indent=2))

    report_path = feature_dir / "verify" / f"deterministic-report-{args.story_id}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
