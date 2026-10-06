#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "codex-usage.py"


def load_module():
    spec = importlib.util.spec_from_file_location("codex_usage", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_binding(memory_dir: Path, **overrides) -> None:
    binding = {
        "conversation_id": "sess-1",
        "feature": "demo",
        "stage": "implement",
        "step": "implement-1-build",
        "bound_at_ms": 1000,
    }
    binding.update(overrides)
    (memory_dir / "codex-usage-bindings.jsonl").write_text(
        json.dumps(binding) + "\n", encoding="utf-8"
    )


def token_usage_line(turn_id: str, response_id: str, **usage_overrides) -> str:
    usage = {
        "input_tokens": 100,
        "output_tokens": 20,
        "cache_write_input_tokens": 5,
        "cached_input_tokens": 10,
        "total_tokens": 135,
    }
    usage.update(usage_overrides)
    return json.dumps(
        {
            "type": "token_usage_record",
            "payload": {"turn_id": turn_id, "response_id": response_id, "usage": usage},
        }
    )


def token_count_line(cumulative_total: int, **last_overrides) -> str:
    """The shape actually observed on real Codex CLI 0.144.0-alpha.4
    rollouts: an event_msg item wrapping a token_count event, with no
    turn_id/response_id at all. `cumulative_total` is the running
    info.total_token_usage.total_tokens; **last_overrides tweaks the
    per-turn info.last_token_usage fields (default total_tokens: 135)."""
    last = {
        "input_tokens": 100,
        "output_tokens": 20,
        "cache_write_input_tokens": 5,
        "cached_input_tokens": 10,
        "total_tokens": 135,
    }
    last.update(last_overrides)
    return json.dumps(
        {
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": last,
                    "total_token_usage": {"total_tokens": cumulative_total},
                },
            },
        }
    )


class CodexUsageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_find_turn_usage_matches_token_usage_record_by_turn_id_reverse_scan(self):
        with tempfile.TemporaryDirectory() as temp:
            rollout = Path(temp) / "rollout.jsonl"
            rollout.write_text(
                "\n".join(
                    [
                        json.dumps({"type": "response_item", "payload": {}}),
                        token_usage_line("turn-1", "resp-1", total_tokens=50),
                        "not-json",
                        token_usage_line("turn-2", "resp-2", total_tokens=135),
                    ]
                ),
                encoding="utf-8",
            )

            found = self.module.find_turn_usage(rollout, "turn-2")
            missing = self.module.find_turn_usage(rollout, "turn-nope")

            self.assertIsNotNone(found)
            usage, fingerprint_key = found
            self.assertEqual(usage["total_tokens"], 135)
            self.assertIn("resp-2", fingerprint_key)
            self.assertIsNone(missing)

    def test_find_turn_usage_falls_back_to_latest_token_count_event(self):
        """Real Codex CLI 0.144.0-alpha.4 rollouts carry no token_usage_record
        at all -- only event_msg/token_count items with no turn_id. Any
        turn_id argument must still resolve via the latest one in the file."""
        with tempfile.TemporaryDirectory() as temp:
            rollout = Path(temp) / "rollout.jsonl"
            rollout.write_text(
                "\n".join(
                    [
                        token_count_line(50),
                        "not-json",
                        token_count_line(185),
                    ]
                ),
                encoding="utf-8",
            )

            found = self.module.find_turn_usage(rollout, "turn-does-not-exist-in-this-shape")

            self.assertIsNotNone(found)
            usage, fingerprint_key = found
            self.assertEqual(usage["total_tokens"], 135)
            self.assertEqual(fingerprint_key, "token_count:185")

    def test_find_turn_usage_prefers_token_usage_record_over_token_count(self):
        with tempfile.TemporaryDirectory() as temp:
            rollout = Path(temp) / "rollout.jsonl"
            rollout.write_text(
                "\n".join(
                    [
                        token_usage_line("turn-1", "resp-1", total_tokens=135),
                        token_count_line(999),
                    ]
                ),
                encoding="utf-8",
            )

            found = self.module.find_turn_usage(rollout, "turn-1")

            self.assertIsNotNone(found)
            _, fingerprint_key = found
            self.assertTrue(fingerprint_key.startswith("turn:turn-1:"))

    def test_find_turn_usage_returns_none_for_missing_file(self):
        missing_path = Path(tempfile.mkdtemp()) / "does-not-exist.jsonl"

        self.assertIsNone(self.module.find_turn_usage(missing_path, "turn-1"))

    def test_record_fingerprint_distinguishes_by_key(self):
        first = self.module.record_fingerprint("sess-1", "turn:turn-1:resp-1")
        same = self.module.record_fingerprint("sess-1", "turn:turn-1:resp-1")
        different = self.module.record_fingerprint("sess-1", "turn:turn-1:resp-2")

        self.assertEqual(first, same)
        self.assertNotEqual(first, different)

    def test_ingest_turn_records_exact_tokens_and_dedupes(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            feature_dir = workspace / ".adlc5" / "demo"
            memory_dir = feature_dir / "memory"
            memory_dir.mkdir(parents=True)
            (feature_dir / "state.json").write_text(
                '{"schema_version":"3.0","feature":"demo","current_stage":"implement",'
                '"current_step":"implement-1-build","stage_status":{}}',
                encoding="utf-8",
            )
            write_binding(memory_dir)

            rollout = workspace / "rollout.jsonl"
            rollout.write_text(token_usage_line("turn-1", "resp-1") + "\n", encoding="utf-8")

            first = self.module.ingest_turn(workspace, "sess-1", "turn-1", "gpt-5.6-codex", rollout)
            second = self.module.ingest_turn(workspace, "sess-1", "turn-1", "gpt-5.6-codex", rollout)

            self.assertEqual(first, {"recorded": 1, "skipped": 0})
            self.assertEqual(second, {"recorded": 0, "skipped": 1})

            ledger = memory_dir / "usage-ledger.jsonl"
            entries = [json.loads(line) for line in ledger.read_text().splitlines()]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["model_id"], "gpt-5.6-codex")
            self.assertEqual(entries[0]["platform"], "codex")
            self.assertEqual(entries[0]["tokens"]["input"], 100)
            self.assertEqual(entries[0]["tokens"]["cache_read"], 10)
            self.assertEqual(entries[0]["tokens"]["total"], 135)

    def test_ingest_turn_records_via_token_count_fallback_and_dedupes(self):
        """End-to-end with the shape actually observed on real Codex CLI
        0.144.0-alpha.4 rollouts (no token_usage_record present at all)."""
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            feature_dir = workspace / ".adlc5" / "demo"
            memory_dir = feature_dir / "memory"
            memory_dir.mkdir(parents=True)
            (feature_dir / "state.json").write_text(
                '{"schema_version":"3.0","feature":"demo","current_stage":"implement",'
                '"current_step":"implement-1-build","stage_status":{}}',
                encoding="utf-8",
            )
            write_binding(memory_dir)

            rollout = workspace / "rollout.jsonl"
            rollout.write_text(token_count_line(135) + "\n", encoding="utf-8")

            first = self.module.ingest_turn(workspace, "sess-1", "turn-1", "gpt-5.6-codex", rollout)
            second = self.module.ingest_turn(workspace, "sess-1", "turn-1", "gpt-5.6-codex", rollout)

            self.assertEqual(first, {"recorded": 1, "skipped": 0})
            self.assertEqual(second, {"recorded": 0, "skipped": 1})

            ledger = memory_dir / "usage-ledger.jsonl"
            entries = [json.loads(line) for line in ledger.read_text().splitlines()]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["tokens"]["total"], 135)

            # A later Stop fire with an updated cumulative total is a new,
            # distinct turn's usage -- not a dedup hit.
            with rollout.open("a", encoding="utf-8") as handle:
                handle.write(token_count_line(250, total_tokens=115) + "\n")
            third = self.module.ingest_turn(workspace, "sess-1", "turn-2", "gpt-5.6-codex", rollout)
            self.assertEqual(third, {"recorded": 1, "skipped": 0})
            self.assertEqual(len(ledger.read_text().splitlines()), 2)

    def test_ingest_turn_skips_when_record_not_found(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            memory_dir = workspace / ".adlc5" / "demo" / "memory"
            memory_dir.mkdir(parents=True)
            write_binding(memory_dir)

            rollout = workspace / "rollout.jsonl"
            rollout.write_text(token_usage_line("turn-other", "resp-1") + "\n", encoding="utf-8")

            result = self.module.ingest_turn(workspace, "sess-1", "turn-1", "gpt-5.6-codex", rollout)

            self.assertEqual(result, {"recorded": 0, "skipped": 1})

    def test_ingest_turn_skips_when_no_binding_for_session(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            rollout = workspace / "rollout.jsonl"
            rollout.write_text(token_usage_line("turn-1", "resp-1") + "\n", encoding="utf-8")

            result = self.module.ingest_turn(
                workspace, "unbound-session", "turn-1", "gpt-5.6-codex", rollout
            )

            self.assertEqual(result, {"recorded": 0, "skipped": 0})


if __name__ == "__main__":
    unittest.main()
