#!/usr/bin/env python3
"""Contract checks for the read-only ADLC5 Pulse projection."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.pulse import Reader, board_document, handoff, project_workspace  # noqa: E402
from lib.completion_evidence import fingerprint, gate_dependency_digest  # noqa: E402


class PulseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        (self.workspace / ".adlc5").mkdir()
        subprocess.run(["git", "init", "-q", str(self.workspace)], check=True)
        subprocess.run(["git", "-C", str(self.workspace), "config", "maintenance.auto", "false"], check=True)
        subprocess.run(["git", "-C", str(self.workspace), "config", "gc.auto", "0"], check=True)
        (self.workspace / "README.md").write_text("fixture\n")
        subprocess.run(["git", "-C", str(self.workspace), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(self.workspace), "-c", "user.name=Pulse Test", "-c", "user.email=pulse@example.test", "commit", "-qm", "fixture"], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def feature(self, name="sample-feature", state=None):
        base = self.workspace / ".adlc5" / name
        (base / "evidence").mkdir(parents=True)
        (base / "state.json").write_text(json.dumps(state or {
            "schema_version": "3.0", "feature": name,
            "current_stage": "implement", "current_step": "implement-2-verify",
            "stage_status": {"specify": "completed", "plan": "completed", "tasks": "completed", "implement": "in_progress"},
        }))
        return base

    def test_empty_workspace_is_valid_and_does_not_write(self):
        before = sorted(str(p.relative_to(self.workspace)) for p in self.workspace.rglob("*"))
        result = project_workspace(self.workspace)
        after = sorted(str(p.relative_to(self.workspace)) for p in self.workspace.rglob("*"))
        self.assertEqual(result["status"], "empty")
        self.assertEqual(result["features"], [])
        self.assertEqual(before, after)

    def test_partial_corrupt_and_unavailable_usage_are_never_zero_cost(self):
        base = self.feature()
        (base / "evidence" / "completion.jsonl").write_text('{bad json}\n{"kind":"checks","fingerprint":"old","results":[]}\n')
        (base / "memory").mkdir()
        (base / "memory" / "usage-ledger.jsonl").write_text(json.dumps({
            "model_id": "unknown-model", "input_tokens": 0, "output_tokens": 0,
            "extra": {"usage_unavailable": True},
        }) + "\n")
        result = project_workspace(self.workspace)
        feature = result["features"][0]
        self.assertEqual(feature["usage"]["status"], "unavailable")
        self.assertIsNone(feature["usage"]["complete_total_usd"])
        self.assertEqual(feature["evidence"]["checks"]["status"], "stale")
        self.assertTrue(result["warnings"])

    def test_archive_and_active_same_label_are_distinct(self):
        self.feature("same-name")
        archived = self.workspace / ".adlc5" / "_archive" / "same-name-20261017"
        (archived / "evidence").mkdir(parents=True)
        (archived / "state.json").write_text(json.dumps({"feature": "same-name", "current_stage": "implement", "current_step": "completed"}))
        result = project_workspace(self.workspace)
        self.assertEqual(len(result["features"]), 2)
        self.assertEqual(len({item["identity"] for item in result["features"]}), 2)
        self.assertEqual(sum(bool(item["archive_id"]) for item in result["features"]), 1)
        with self.assertRaises(ValueError):
            project_workspace(self.workspace, feature="same-name")
        archived_snapshot = project_workspace(self.workspace, feature="same-name-20261017")
        self.assertEqual(archived_snapshot["features"][0]["archive_id"], "same-name-20261017")

    def test_safe_fingerprint_matches_canonical_and_gate_inputs_invalidate(self):
        self.feature()
        state = json.loads((self.workspace / ".adlc5" / "sample-feature" / "state.json").read_text())
        safe_reader = Reader(self.workspace)
        regular = fingerprint(self.workspace, "sample-feature")
        bounded = fingerprint(self.workspace, "sample-feature", safe_reader=safe_reader, state_override=state)
        self.assertEqual(regular, bounded)
        before = gate_dependency_digest(self.workspace, "sample-feature")
        evidence = self.workspace / ".adlc5" / "sample-feature" / "evidence" / "completion.jsonl"
        evidence.write_text('{"kind":"approval","fingerprint":"x"}\n')
        self.assertNotEqual(before, gate_dependency_digest(self.workspace, "sample-feature"))

    def test_safe_fingerprint_refuses_symlink_before_read(self):
        base = self.feature()
        target = self.workspace / "private.txt"
        target.write_text("must-not-enter-snapshot\n")
        (base / "linked-secret.txt").symlink_to(target)
        state = json.loads((base / "state.json").read_text())
        with self.assertRaises(ValueError):
            fingerprint(self.workspace, "sample-feature", safe_reader=Reader(self.workspace), state_override=state)

    def test_reader_rejects_change_after_validation(self):
        reader = Reader(self.workspace)
        source = reader.workspace / "README.md"
        reader.prepare([source])
        source.write_text("changed after prepare\n")
        with self.assertRaises(ValueError):
            reader.read(source)

    def test_usage_preserves_only_observed_token_buckets(self):
        base = self.feature()
        (base / "memory").mkdir()
        (base / "memory" / "usage-ledger.jsonl").write_text(json.dumps({
            "model_id": "unknown-model", "tokens": {"input": 5, "thinking": 2},
            "extra": {"host_reported_cost_usd": 0.0},
        }) + "\n")
        usage = project_workspace(self.workspace)["features"][0]["usage"]
        self.assertEqual(usage["tokens"], {"input": 5, "thinking": 2})
        self.assertEqual(usage["token_records"], 1)
        self.assertEqual(usage["known_cost_usd"], 0.0)

    def test_usage_rejects_nonfinite_cost_and_malformed_token_counters(self):
        base = self.feature()
        (base / "memory").mkdir()
        rows = [
            {"model_id": "known", "extra": {"host_reported_cost_usd": float("nan")}},
            {"model_id": "known", "tokens": {"input": True, "output": 3, "cache_creation": 0, "cache_read": 0}},
        ]
        (base / "memory" / "usage-ledger.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
        usage = project_workspace(self.workspace)["features"][0]["usage"]
        self.assertEqual(usage["status"], "unavailable")
        self.assertIsNone(usage["known_cost_usd"])
        self.assertEqual(usage["invalid_records"], 2)

    def test_explicit_zero_cost_is_observed_but_total_stays_partial(self):
        base = self.feature()
        (base / "memory").mkdir()
        (base / "memory" / "usage-ledger.jsonl").write_text(json.dumps({
            "model_id": "unknown-model", "tokens": {"input": 0, "output": 0},
            "extra": {"host_reported_cost_usd": 0.0},
        }) + "\n")
        usage = project_workspace(self.workspace)["features"][0]["usage"]
        self.assertEqual(usage["known_cost_usd"], 0.0)
        self.assertIsNone(usage["complete_total_usd"])
        self.assertEqual(usage["accounted_records"], 1)

    def test_gate_emitter_records_fingerprinted_dependency_receipt(self):
        base = self.feature("gate-feature", {"schema_version": "3.0", "feature": "gate-feature", "current_stage": "implement", "current_step": "implement-1-build", "stage_status": {}})
        (base / "evidence").rmdir()
        (base / "policies.yaml").write_text("{}\n")
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "check-gates.py"), "--workspace", str(self.workspace), "--feature", "gate-feature", "--gate", "build-1-implementation"], capture_output=True, text=True)
        event_path = base / "evidence" / "events.jsonl"
        self.assertTrue(event_path.is_file(), f"exit={proc.returncode} stdout={proc.stdout} stderr={proc.stderr}")
        event = json.loads(event_path.read_text().splitlines()[-1])
        self.assertEqual(event["event"], "gate_check")
        self.assertEqual(event["gate"], "build-1-implementation")
        self.assertEqual(len(event["input_fingerprint_before"]), 64)
        self.assertEqual(len(event["dependency_digest_before"]), 64)
        self.assertTrue(event["evaluator_id"].startswith("adlc5-gate-v1:"))
        self.assertIn("time", event)

    def test_handoff_and_board_escape_untrusted_strings(self):
        name = "hostile"
        self.feature(name, {"feature": name, "current_stage": "implement", "current_step": "</script><script>alert(1)</script>"})
        (self.workspace / ".adlc5" / name / "evidence" / "completion.jsonl").write_text(json.dumps({
            "kind": "checks", "summary": "</script><script>alert(1)</script>", "fingerprint": "old", "results": []
        }) + "\n")
        result = project_workspace(self.workspace, feature=name)
        text = board_document(result)
        self.assertNotIn("</script><script>alert(1)", text)
        self.assertIn("sha256-", text)
        self.assertIn("connect-src 'none'", text)
        summary = handoff(result, name)
        self.assertNotIn("<script>alert(1)", summary)
        self.assertNotIn("<img", summary)

    def test_cli_snapshot_is_read_only_and_board_cache_is_explicit(self):
        self.feature()
        command = [sys.executable, str(ROOT / "scripts" / "adlc5")]
        before = sorted(str(p.relative_to(self.workspace)) for p in self.workspace.rglob("*"))
        snapshot = subprocess.run(command + ["pulse", "snapshot", "--workspace", str(self.workspace), "--feature", "sample-feature"], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(snapshot.stdout)["status"], "ok")
        after = sorted(str(p.relative_to(self.workspace)) for p in self.workspace.rglob("*"))
        self.assertEqual(before, after)
        board = subprocess.run(command + ["pulse", "board", "--workspace", str(self.workspace)], capture_output=True, text=True, check=True)
        result = json.loads(board.stdout)
        self.assertTrue((self.workspace / result["board"]).is_file())
        cached = subprocess.run(command + ["pulse", "band", "--cached", "--feature", "sample-feature", "--workspace", str(self.workspace)], capture_output=True, text=True)
        self.assertEqual(cached.returncode, 0, cached.stderr)
        self.assertIn("present freshness unverified", cached.stdout)
        env = {**os.environ, "ADLC5_FEATURE": "sample-feature", "ADLC5_WORKSPACE": str(self.workspace)}
        status = subprocess.run([sys.executable, str(ROOT / "scripts" / "pulse-statusline.py")], input="{}", capture_output=True, text=True, env=env)
        self.assertEqual(status.returncode, 0)
        self.assertIn("present freshness unverified", status.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
