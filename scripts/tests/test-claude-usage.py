#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "claude-usage.py"


def load_module():
    spec = importlib.util.spec_from_file_location("claude_usage", MODULE_PATH)
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
    (memory_dir / "claude-usage-bindings.jsonl").write_text(
        json.dumps(binding) + "\n", encoding="utf-8"
    )


class ClaudeUsageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_iter_assistant_turns_reads_usage_and_skips_malformed_lines(self):
        with tempfile.TemporaryDirectory() as temp:
            transcript = Path(temp) / "session.jsonl"
            transcript.write_text(
                "\n".join(
                    [
                        json.dumps({"type": "user", "message": {"content": "hi"}}),
                        "not-json",
                        json.dumps(
                            {
                                "type": "assistant",
                                "uuid": "turn-1",
                                "timestamp": "2026-09-03T10:00:00.000Z",
                                "message": {
                                    "model": "claude-sonnet-4-6",
                                    "usage": {
                                        "input_tokens": 100,
                                        "output_tokens": 20,
                                        "cache_creation_input_tokens": 5,
                                        "cache_read_input_tokens": 10,
                                    },
                                },
                            }
                        ),
                        json.dumps({"type": "assistant", "message": {"content": "no usage"}}),
                    ]
                ),
                encoding="utf-8",
            )

            turns = self.module.iter_assistant_turns(transcript)

            self.assertEqual(len(turns), 1)
            self.assertEqual(turns[0]["message"]["model"], "claude-sonnet-4-6")

    def test_turn_fingerprint_distinguishes_turns_by_uuid(self):
        entry_a = {"uuid": "turn-1", "message": {"usage": {"input_tokens": 1}}}
        entry_b = {"uuid": "turn-2", "message": {"usage": {"input_tokens": 1}}}

        first = self.module.turn_fingerprint("sess-1", entry_a)
        second = self.module.turn_fingerprint("sess-1", dict(entry_a))
        third = self.module.turn_fingerprint("sess-1", entry_b)

        self.assertEqual(first, second)
        self.assertNotEqual(first, third)

    def test_parse_transcript_timestamp_handles_zulu_suffix(self):
        ms = self.module.parse_transcript_timestamp("2026-09-03T10:00:00.000Z")

        self.assertIsInstance(ms, int)
        self.assertIsNone(self.module.parse_transcript_timestamp("not-a-timestamp"))
        self.assertIsNone(self.module.parse_transcript_timestamp(None))

    def test_ingest_transcript_records_exact_tokens_and_dedupes(self):
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

            transcript = workspace / "session.jsonl"
            transcript.write_text(
                json.dumps(
                    {
                        "type": "assistant",
                        "uuid": "turn-1",
                        "timestamp": "2026-09-03T10:00:00.000Z",
                        "message": {
                            "model": "claude-sonnet-4-6",
                            "usage": {
                                "input_tokens": 100,
                                "output_tokens": 20,
                                "cache_creation_input_tokens": 5,
                                "cache_read_input_tokens": 10,
                            },
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            first = self.module.ingest_transcript(workspace, "sess-1", transcript)
            second = self.module.ingest_transcript(workspace, "sess-1", transcript)

            self.assertEqual(first["recorded"], 1)
            self.assertEqual(second["recorded"], 0)
            ledger = memory_dir / "usage-ledger.jsonl"
            entries = [json.loads(line) for line in ledger.read_text().splitlines()]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["model_id"], "claude-sonnet-4-6")
            self.assertEqual(entries[0]["platform"], "claude")
            self.assertEqual(entries[0]["source"], "transcript")
            self.assertEqual(entries[0]["tokens"]["input"], 100)
            self.assertEqual(entries[0]["tokens"]["cache_read"], 10)

    def test_ingest_transcript_skips_when_no_binding_for_session(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            transcript = workspace / "session.jsonl"
            transcript.write_text("", encoding="utf-8")

            result = self.module.ingest_transcript(workspace, "unbound-session", transcript)

            self.assertEqual(result, {"recorded": 0, "skipped": 0})


if __name__ == "__main__":
    unittest.main()
