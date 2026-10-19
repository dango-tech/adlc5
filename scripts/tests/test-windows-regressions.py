#!/usr/bin/env python3
"""Regression checks for the Windows compatibility fixes (issue #20).

Runs on every platform; the Git Bash and WSL-launcher assertions apply only on
Windows, where those failures occurred.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
BASH = shutil.which("bash") or "bash"
WINDOWS = os.name == "nt"
# Python entry points that launch shell scripts and must not use a bare "bash".
ENTRY_POINTS = ("adlc5", "check-gates.py", "score-coverage.py", "verify-story.py", "evaluation/demo-consumer.py")


def load(relative: str):
    path = SCRIPTS / relative
    name = "entry_" + re.sub(r"\W", "_", relative)
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPTS))
    try:
        loader.exec_module(module)
    finally:
        sys.path.remove(str(SCRIPTS))
    return module


def run(argv: list[str], cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", timeout=300)


class CheckoutTest(unittest.TestCase):
    def test_auxiliary_directory_is_checked_out(self) -> None:
        self.assertTrue((ROOT / "skills/auxiliary/README.md").is_file())
        self.assertFalse((ROOT / "skills/aux").exists())
        tracked = run(["git", "-C", str(ROOT), "ls-files", "skills/auxiliary"]).stdout.split()
        self.assertIn("skills/auxiliary/README.md", tracked)

    def test_no_tracked_path_uses_a_reserved_device_name(self) -> None:
        reserved = re.compile(r"(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$", re.IGNORECASE)
        paths = run(["git", "-C", str(ROOT), "ls-files", "-z"]).stdout.split("\0")
        bad = [p for p in paths if any(reserved.match(part) for part in p.split("/"))]
        self.assertEqual(bad, [])


class CompactMemoryTest(unittest.TestCase):
    def test_index_and_state_use_forward_slashes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            feature = workspace / ".adlc5/demo"
            (feature / "design").mkdir(parents=True)
            (feature / "tasks/code-spec").mkdir(parents=True)
            (feature / "design/1a-discovery.md").write_text("# Discovery\n", encoding="utf-8")
            (feature / "tasks/code-spec/us-1-spec.md").write_text("# Spec\n", encoding="utf-8")
            (feature / "state.json").write_text(json.dumps({"current_stage": "plan"}), encoding="utf-8")
            result = run([sys.executable, str(SCRIPTS / "compact-memory.py"), "--feature", "demo"], cwd=workspace)
            self.assertEqual(result.returncode, 0, result.stderr)
            index = (feature / "memory/INDEX.md").read_text(encoding="utf-8")
            self.assertIn("| .adlc5/demo/design/1a-discovery.md |", index)
            self.assertIn("| .adlc5/demo/tasks/code-spec/us-1-spec.md |", index)
            self.assertNotIn("\\", index)
            state = json.loads((feature / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["memory"]["index_path"], ".adlc5/demo/memory/INDEX.md")


class GitBashTest(unittest.TestCase):
    def test_entry_points_select_bash_from_path(self) -> None:
        for relative in ENTRY_POINTS:
            with self.subTest(entry_point=relative):
                self.assertEqual(load(relative).BASH, BASH)

    @unittest.skipUnless(WINDOWS, "the System32 WSL launcher exists only on Windows")
    def test_selected_bash_is_git_bash_not_the_wsl_launcher(self) -> None:
        self.assertNotIn("system32", BASH.lower())
        result = run([BASH, "-c", "uname -s"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"^(MINGW|MSYS)")

    def test_score_coverage_writes_telemetry_through_bash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / ".adlc5/demo").mkdir(parents=True)
            env = dict(os.environ, ADLC5_WORKSPACE=str(workspace))
            result = run([sys.executable, str(SCRIPTS / "score-coverage.py"), "--feature", "demo",
                          "--workspace", str(workspace)], cwd=workspace, env=env)
            self.assertEqual(result.returncode, 2, result.stderr)  # skipped: no coverage report
            events = workspace / ".adlc5/demo/telemetry/events.jsonl"
            self.assertTrue(events.is_file(), "telemetry_emit did not run through Bash")
            records = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines() if line]
            self.assertTrue(any(r.get("script") == "score-coverage.py" for r in records), records)

    def test_facade_propagates_shell_exit_codes(self) -> None:
        facade = [sys.executable, str(SCRIPTS / "adlc5")]
        ok = run([*facade, "resolve-model", "--help"])
        self.assertEqual(ok.returncode, 0, ok.stderr)
        with tempfile.TemporaryDirectory() as temp:
            args = ["--feature", "demo", "--workspace", temp]
            direct = run([BASH, str(SCRIPTS / "advance-phase.sh"), *args])
            via_facade = run([*facade, "phase", *args])
            self.assertNotEqual(direct.returncode, 0, direct.stdout + direct.stderr)
            self.assertEqual(via_facade.returncode, direct.returncode, via_facade.stdout + via_facade.stderr)
            self.assertEqual(via_facade.stdout, direct.stdout)


if __name__ == "__main__":
    unittest.main()
