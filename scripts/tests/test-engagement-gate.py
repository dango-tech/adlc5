#!/usr/bin/env python3
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "engagement-gate.py"

STATE_JSON = json.dumps(
    {
        "schema_version": "3.0",
        "feature": "demo",
        "current_stage": "implement",
        "current_step": "implement-1-build",
        "stage_status": {},
    }
)


def load_module():
    spec = importlib.util.spec_from_file_location("engagement_gate", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(workspace: Path, *arguments: str) -> None:
    subprocess.run(
        [
            "git",
            "-C",
            str(workspace),
            "-c",
            "user.name=ADLC5 Test",
            "-c",
            "user.email=adlc5-test@example.com",
            *arguments,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


class EngagementGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def setUp(self):
        # Hook payloads arrive on stdin; keep it deterministic and empty so the
        # CLI commands under test read no payload instead of blocking on a tty.
        original_stdin = sys.stdin
        sys.stdin = io.StringIO("")
        self.addCleanup(lambda: setattr(sys, "stdin", original_stdin))

        original_mode = os.environ.pop("ADLC5_ENGAGEMENT_GATE", None)
        if original_mode is not None:
            self.addCleanup(os.environ.__setitem__, "ADLC5_ENGAGEMENT_GATE", original_mode)

    def make_workspace(self, temp: str, *, feature: str | None = "demo") -> Path:
        """Workspace with ADLC5 installed and (optionally) a session binding."""
        workspace = Path(temp).resolve()
        (workspace / ".adlc5").mkdir(parents=True)
        if feature:
            (workspace / ".adlc5" / "cursor-usage-bindings.jsonl").write_text(
                json.dumps(
                    {
                        "conversation_id": "conv-1",
                        "feature": feature,
                        "bound_at_ms": 1000,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        return workspace

    def touch_files(self, workspace: Path, count: int, *, start: int = 1) -> list[str]:
        paths = []
        for index in range(start, start + count):
            rel = f"src/module_{index}.py"
            target = workspace / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"value = {index}\n", encoding="utf-8")
            paths.append(rel)
        return paths

    def edit(self, workspace: Path, paths: list[str]) -> str | None:
        _mode, message = self.module.evaluate_session(
            workspace, "cursor", "conv-1", paths, replace=False
        )
        return message

    # --- thresholds ---------------------------------------------------------

    def test_stays_quiet_below_first_warn_threshold(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_workspace(temp, feature=None)
            paths = self.touch_files(workspace, self.module.FIRST_WARN_FILES - 1)

            for path in paths:
                self.assertIsNone(self.edit(workspace, [path]))

    def test_warns_at_first_warn_threshold(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_workspace(temp, feature=None)
            paths = self.touch_files(workspace, self.module.FIRST_WARN_FILES)

            messages = [self.edit(workspace, [path]) for path in paths]

            self.assertEqual(messages[:-1], [None] * (self.module.FIRST_WARN_FILES - 1))
            self.assertIsNotNone(messages[-1])
            self.assertIn("ADLC5 ENGAGEMENT GATE", messages[-1])
            self.assertIn(f"{self.module.FIRST_WARN_FILES} distinct source files", messages[-1])

    def test_escalates_every_n_further_files(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_workspace(temp, feature=None)
            total = self.module.FIRST_WARN_FILES + self.module.ESCALATE_EVERY_FILES
            paths = self.touch_files(workspace, total)

            messages = [self.edit(workspace, [path]) for path in paths]

            warned_at = [index + 1 for index, message in enumerate(messages) if message]
            self.assertEqual(
                warned_at,
                [self.module.FIRST_WARN_FILES, total],
            )
            self.assertIn("still unresolved", messages[-1])

    def test_repeated_edits_to_one_file_never_warn(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_workspace(temp, feature=None)
            paths = self.touch_files(workspace, 1)

            for _ in range(self.module.FIRST_WARN_FILES * 3):
                self.assertIsNone(self.edit(workspace, paths))

    # --- engagement detection ----------------------------------------------

    def test_real_state_json_counts_as_engaged_and_suppresses_warning(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_workspace(temp)
            feature_dir = workspace / ".adlc5" / "demo"
            feature_dir.mkdir()
            (feature_dir / "state.json").write_text(STATE_JSON, encoding="utf-8")

            status, feature = self.module.engagement_status(workspace, "cursor", "conv-1")
            paths = self.touch_files(workspace, self.module.FIRST_WARN_FILES)

            self.assertEqual((status, feature), ("engaged", "demo"))
            self.assertIsNone(self.edit(workspace, paths))

    def test_scaffold_without_state_json_is_not_engagement(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_workspace(temp)
            for sub in ("memory", "tasks", "design"):
                (workspace / ".adlc5" / "demo" / sub).mkdir(parents=True)
            paths = self.touch_files(workspace, self.module.FIRST_WARN_FILES)

            status, feature = self.module.engagement_status(workspace, "cursor", "conv-1")
            message = self.edit(workspace, paths)

            self.assertEqual((status, feature), ("scaffold-only", "demo"))
            self.assertIsNotNone(message)
            self.assertIn("no state.json", message)
            self.assertIn("demo", message)

    def test_empty_state_json_is_not_engagement(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_workspace(temp)
            feature_dir = workspace / ".adlc5" / "demo"
            feature_dir.mkdir()
            (feature_dir / "state.json").write_text("", encoding="utf-8")
            paths = self.touch_files(workspace, self.module.FIRST_WARN_FILES)

            status, _feature = self.module.engagement_status(workspace, "cursor", "conv-1")

            self.assertEqual(status, "scaffold-only")
            self.assertIsNotNone(self.edit(workspace, paths))

    def test_archived_feature_state_counts_as_engaged(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_workspace(temp)
            archived = workspace / ".adlc5" / "_archive" / "demo-20260101"
            archived.mkdir(parents=True)
            (archived / "state.json").write_text(STATE_JSON, encoding="utf-8")

            self.assertTrue(self.module.feature_has_state(workspace, "demo"))

    def test_unbound_session_reports_unbound(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_workspace(temp, feature=None)

            status, feature = self.module.engagement_status(workspace, "cursor", "conv-1")

            self.assertEqual((status, feature), ("unbound", None))

    # --- ack ----------------------------------------------------------------

    def test_ack_persists_state_and_suppresses_further_warnings(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_workspace(temp, feature=None)
            paths = self.touch_files(workspace, self.module.FIRST_WARN_FILES)

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                exit_code = self.module.main(
                    [
                        "ack",
                        "--workspace",
                        str(workspace),
                        "--platform",
                        "cursor",
                        "--session-id",
                        "conv-1",
                        "--reason",
                        "hotfix",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(json.loads(buffer.getvalue())["acknowledged"])

            persisted = json.loads(
                self.module.state_path(workspace, "cursor", "conv-1").read_text(encoding="utf-8")
            )
            self.assertTrue(persisted["acknowledged"])
            self.assertEqual(persisted["acknowledged_reason"], "hotfix")

            self.assertIsNone(self.edit(workspace, paths))
            self.assertIsNone(self.edit(workspace, self.touch_files(workspace, 5, start=100)))

    # --- check-branch backstop ---------------------------------------------

    def make_repo(self, temp: str, *, prefix: str = "feat", slug: str = "demo") -> Path:
        workspace = Path(temp).resolve()
        (workspace / ".adlc5").mkdir(parents=True)
        git(workspace, "init", "--quiet")
        (workspace / "README.md").write_text("base\n", encoding="utf-8")
        git(workspace, "add", "README.md")
        git(workspace, "commit", "--quiet", "-m", "base")
        git(workspace, "checkout", "--quiet", "-b", f"{prefix}/{slug}")
        (workspace / "src").mkdir(exist_ok=True)
        (workspace / "src" / "feature.py").write_text("value = 1\n", encoding="utf-8")
        git(workspace, "add", "src/feature.py")
        git(workspace, "commit", "--quiet", "-m", "feature work")
        return workspace

    def run_check_branch(self, workspace: Path) -> str:
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            exit_code = self.module.main(["check-branch", "--workspace", str(workspace)])
        self.assertEqual(exit_code, 0)
        return buffer.getvalue()

    def test_check_branch_warns_on_ungated_feature_branch(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_repo(temp)

            output = self.run_check_branch(workspace)

            self.assertIn("pre-push backstop", output)
            self.assertIn("feat/demo", output)
            self.assertIn("was ever created", output)

    def test_check_branch_quiet_when_active_state_json_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_repo(temp)
            (workspace / ".adlc5" / "demo").mkdir()
            (workspace / ".adlc5" / "demo" / "state.json").write_text(
                STATE_JSON, encoding="utf-8"
            )

            self.assertEqual(self.run_check_branch(workspace), "")

    def test_check_branch_quiet_when_archived_state_json_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_repo(temp)
            archived = workspace / ".adlc5" / "_archive" / "demo-20260101"
            archived.mkdir(parents=True)
            (archived / "state.json").write_text(STATE_JSON, encoding="utf-8")

            self.assertEqual(self.run_check_branch(workspace), "")

    def test_check_branch_warns_on_scaffold_only_feature_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_repo(temp)
            (workspace / ".adlc5" / "demo" / "memory").mkdir(parents=True)

            output = self.run_check_branch(workspace)

            self.assertIn("scaffold was created", output)

    def test_check_branch_ignores_branches_without_the_configured_prefix(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_repo(temp, prefix="chore")

            self.assertEqual(self.run_check_branch(workspace), "")

    def test_check_branch_honors_configured_branch_prefix(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_repo(temp, prefix="feature")
            (workspace / ".adlc5" / "config.yaml").write_text(
                "git_branch_prefix: feature\n", encoding="utf-8"
            )

            self.assertEqual(self.module.branch_prefix(workspace), "feature")
            self.assertIn("feature/demo", self.run_check_branch(workspace))

    # --- fail-open ----------------------------------------------------------

    def test_session_edit_fails_open_on_missing_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "nope"

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                exit_code = self.module.main(
                    [
                        "session-edit",
                        "--workspace",
                        str(missing),
                        "--session-id",
                        "conv-1",
                        "--tool",
                        "Write",
                        "--path",
                        "src/a.py",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(buffer.getvalue()), {"permission": "allow"})

    def test_session_edit_fails_open_when_evaluation_raises(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_workspace(temp, feature=None)
            original = self.module.evaluate_session

            def boom(*_args, **_kwargs):
                raise RuntimeError("synthetic failure")

            self.module.evaluate_session = boom
            self.addCleanup(setattr, self.module, "evaluate_session", original)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = self.module.main(
                    [
                        "session-edit",
                        "--workspace",
                        str(workspace),
                        "--session-id",
                        "conv-1",
                        "--tool",
                        "Write",
                        "--path",
                        "src/a.py",
                        "--emit",
                        "claude",
                    ]
                )

            self.assertEqual(exit_code, 0)
            # Fail open: no decision, so the host's own permission flow is untouched.
            self.assertEqual(json.loads(stdout.getvalue()), {})
            self.assertIn("synthetic failure", stderr.getvalue())

    def test_claude_emit_warn_adds_context_without_granting_permission(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.module.emit("claude", self.module.MODE_WARN, "engage ADLC5")
        specific = json.loads(buffer.getvalue())["hookSpecificOutput"]
        self.assertEqual(specific["additionalContext"], "engage ADLC5")
        self.assertNotIn("permissionDecision", specific)

    def test_claude_emit_enforce_denies(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.module.emit("claude", self.module.MODE_ENFORCE, "engage ADLC5")
        specific = json.loads(buffer.getvalue())["hookSpecificOutput"]
        self.assertEqual(specific["permissionDecision"], "deny")

    def test_check_branch_fails_open_on_non_git_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_workspace(temp, feature=None)

            self.assertEqual(self.run_check_branch(workspace), "")

    # --- mode -------------------------------------------------------------

    def test_off_mode_disables_the_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_workspace(temp, feature=None)
            paths = self.touch_files(workspace, self.module.FIRST_WARN_FILES)
            os.environ["ADLC5_ENGAGEMENT_GATE"] = "off"
            self.addCleanup(os.environ.pop, "ADLC5_ENGAGEMENT_GATE", None)

            self.assertEqual(self.module.resolve_mode(workspace), self.module.MODE_OFF)
            self.assertIsNone(self.edit(workspace, paths))

    def test_enforce_mode_denies_the_tool_call_when_warning(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = self.make_workspace(temp, feature=None)
            paths = self.touch_files(workspace, self.module.FIRST_WARN_FILES)
            os.environ["ADLC5_ENGAGEMENT_GATE"] = "enforce"
            self.addCleanup(os.environ.pop, "ADLC5_ENGAGEMENT_GATE", None)

            mode, message = self.module.evaluate_session(
                workspace, "cursor", "conv-1", paths, replace=False
            )
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                self.module.emit("cursor", mode, message)

            self.assertEqual(mode, self.module.MODE_ENFORCE)
            self.assertEqual(json.loads(buffer.getvalue())["permission"], "deny")


if __name__ == "__main__":
    unittest.main()
