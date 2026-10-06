#!/usr/bin/env python3
"""Checks for proportional planning and complete, bounded handoffs."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.policies_load import next_step_for_profile, profile_risk_errors
from lib.personas_load import check_persona_context

spec = importlib.util.spec_from_file_location("generate_pack", ROOT / "scripts/memory/generate-pack.py")
pack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)


class WorkflowTests(unittest.TestCase):
    def test_routes_keep_brief_plan(self):
        self.assertEqual(next_step_for_profile({"autopilot": {"profile": "standard"}}, "specify-4-handoff"), "plan-4-design-discovery")
        self.assertEqual(next_step_for_profile({"autopilot": {"profile": "tiny"}}, "specify-4-handoff"), "implement-1-build")

    def test_required_content_and_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            directory = workspace / ".adlc5/demo"
            (directory / "tasks/code-spec").mkdir(parents=True)
            (directory / "state.json").write_text(json.dumps({"schema_version": "3.0", "feature": "demo", "current_stage": "implement", "current_step": "implement-1-build", "stage_status": {}, "memory": {"context_budget_tokens": 100}, "tasks": {"stories": [{"id": "one", "acceptance": [{"id": "AC-1"}]}]}}))
            with self.assertRaisesRegex(ValueError, "code spec missing"):
                pack.assemble(workspace, "demo", "one", "coder")
            (directory / "tasks/code-spec/one.md").write_text("---\nstory_id: one\nfiles_to_create: [src/app.py]\nfiles_to_modify: []\n---\n# Spec\n" + "x" * 1000)
            with self.assertRaisesRegex(ValueError, "spec-handoff"):
                pack.assemble(workspace, "demo", "one", "coder")
            (directory / "spec-handoff.md").write_text("# Acceptance\nDo the independently checked thing.")
            content, sources = pack.assemble(workspace, "demo", "one", "coder")
            self.assertIn("Do the independently checked thing", content)
            self.assertIn("AC-1", content)
            self.assertIn("tasks/code-spec/one.md", sources[0])
            result = subprocess.run([sys.executable, str(ROOT / "scripts/memory/generate-pack.py"), "--workspace", tmp, "--feature", "demo", "--story-id", "one"], capture_output=True, text=True)
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertGreater(report["budget"]["estimated_tokens"], 100)
            self.assertIn("unknown", report["budget"]["host_overhead"])
            self.assertIn("Do the independently checked thing", (workspace / report["pack"]).read_text())

    def test_risk_is_explicit_and_conservative(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            directory = workspace / ".adlc5/demo"
            directory.mkdir(parents=True)
            policy = {"autopilot": {"profile": "tiny"}}
            self.assertTrue(profile_risk_errors(workspace, "demo", policy))
            risk = {"categories": [], "uncertain": False, "rationale": "bounded formatting change"}
            (directory / "risk.json").write_text(json.dumps(risk))
            self.assertEqual(profile_risk_errors(workspace, "demo", policy), [])
            risk["categories"] = ["money"]
            (directory / "risk.json").write_text(json.dumps(risk))
            self.assertTrue(profile_risk_errors(workspace, "demo", policy))
            self.assertEqual(profile_risk_errors(workspace, "demo", {"autopilot": {"profile": "high_risk", "require_human_pr_approval": True}}), [])
            risk["categories"] = []
            risk["uncertain"] = True
            (directory / "risk.json").write_text(json.dumps(risk))
            self.assertTrue(profile_risk_errors(workspace, "demo", policy))

    def test_memory_wall_normalizes_paths(self):
        registry = {"personas": {"coder": {"memory_allow": ["tasks/code-spec/"], "memory_deny": ["verify/"]}}}
        for path in (".adlc5/demo/verify/result.md", "/tmp/repo/.adlc5/demo/verify/result.md"):
            self.assertEqual(check_persona_context("coder", [path], "demo", registry)["status"], "fail")


if __name__ == "__main__":
    unittest.main()
