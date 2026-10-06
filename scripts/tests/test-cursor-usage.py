#!/usr/bin/env python3
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "cursor-usage.py"


def load_module():
    spec = importlib.util.spec_from_file_location("cursor_usage", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CursorUsageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_reads_protected_adlc5_config_without_shell_expansion(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "cursor-usage.env"
            config.write_text(
                "CURSOR_ADMIN_API_KEY=cursor_test\n"
                "CURSOR_USAGE_EMAIL=user@example.com\n"
                "UNRELATED=$(touch should-not-run)\n",
                encoding="utf-8",
            )
            config.chmod(0o600)

            values = self.module.read_config(config)

            self.assertEqual(values["CURSOR_ADMIN_API_KEY"], "cursor_test")
            self.assertEqual(values["CURSOR_USAGE_EMAIL"], "user@example.com")
            self.assertEqual(values["UNRELATED"], "$(touch should-not-run)")

    def test_rejects_config_readable_by_other_users(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "cursor-usage.env"
            config.write_text("CURSOR_ADMIN_API_KEY=cursor_test\n", encoding="utf-8")
            config.chmod(0o644)

            with self.assertRaisesRegex(ValueError, "0600"):
                self.module.read_config(config)

    def test_event_fingerprint_is_stable_and_sensitive_to_usage(self):
        event = {
            "timestamp": "1788444000000",
            "conversationId": "conv-1",
            "model": "composer",
            "tokenUsage": {
                "inputTokens": 10,
                "outputTokens": 2,
                "cacheWriteTokens": 3,
                "cacheReadTokens": 4,
            },
            "chargedCents": 0.5,
        }

        first = self.module.event_fingerprint(event)
        second = self.module.event_fingerprint(json.loads(json.dumps(event)))
        changed = json.loads(json.dumps(event))
        changed["tokenUsage"]["outputTokens"] = 3

        self.assertEqual(first, second)
        self.assertNotEqual(first, self.module.event_fingerprint(changed))

    def test_extracts_feature_from_lifecycle_prompt_and_cli_input(self):
        self.assertEqual(
            self.module.extract_feature({"prompt": "@adlc5 for cursor-token-usage"}),
            "cursor-token-usage",
        )
        self.assertEqual(
            self.module.extract_feature(
                {"tool_input": {"command": "./scripts/adlc5 gate --feature cursor-token-usage"}}
            ),
            "cursor-token-usage",
        )

    def test_selects_latest_binding_before_event(self):
        bindings = [
            {"bound_at_ms": 1000, "feature": "demo", "stage": "specify", "step": "specify-1"},
            {"bound_at_ms": 2000, "feature": "demo", "stage": "plan", "step": "plan-1"},
        ]

        selected = self.module.select_binding(bindings, 2500)

        self.assertEqual(selected["stage"], "plan")
        self.assertIsNone(self.module.select_binding(bindings, 500))

    def test_sync_deduplicates_usage_events(self):
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
            binding = {
                "conversation_id": "conv-1",
                "feature": "demo",
                "stage": "implement",
                "step": "implement-1-build",
                "bound_at_ms": 1000,
            }
            (memory_dir / "cursor-usage-bindings.jsonl").write_text(
                json.dumps(binding) + "\n", encoding="utf-8"
            )
            event = {
                "timestamp": "2000",
                "conversationId": "conv-1",
                "model": "composer",
                "isTokenBasedCall": True,
                "isChargeable": True,
                "tokenUsage": {
                    "inputTokens": 10,
                    "outputTokens": 2,
                    "cacheWriteTokens": 3,
                    "cacheReadTokens": 4,
                    "totalCents": 0.4,
                },
                "chargedCents": 0.5,
            }

            first = self.module.ingest_events(workspace, [event])
            second = self.module.ingest_events(workspace, [event])

            self.assertEqual(first["recorded"], 1)
            self.assertEqual(second["recorded"], 0)
            ledger = memory_dir / "usage-ledger.jsonl"
            entries = [json.loads(line) for line in ledger.read_text().splitlines()]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["tokens"]["total"], 19)
            self.assertEqual(entries[0]["extra"]["charged_cents"], 0.5)

    def test_dedupe_includes_archived_ledgers(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            memory_dir = workspace / ".adlc5" / "demo" / "memory"
            memory_dir.mkdir(parents=True)
            (memory_dir / "cursor-usage-bindings.jsonl").write_text(
                json.dumps(
                    {
                        "conversation_id": "conv-1",
                        "feature": "demo",
                        "bound_at_ms": 1000,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            event = {
                "timestamp": "2000",
                "conversationId": "conv-1",
                "model": "composer",
                "tokenUsage": {"inputTokens": 1},
            }
            archived_memory = workspace / ".adlc5" / "_archive" / "demo-20260903" / "memory"
            archived_memory.mkdir(parents=True)
            archived_memory.joinpath("usage-ledger.jsonl").write_text(
                json.dumps(
                    {
                        "extra": {
                            "cursor_usage_event_id": self.module.event_fingerprint(event)
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.module.ingest_events(workspace, [event])

            self.assertEqual(result["recorded"], 0)
            self.assertEqual(result["skipped"], 1)
            self.assertFalse((memory_dir / "usage-ledger.jsonl").exists())

    def test_ingest_skips_events_with_invalid_timestamps(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            result = self.module.ingest_events(
                workspace,
                [
                    {
                        "timestamp": "not-a-number",
                        "conversationId": "conv-1",
                        "tokenUsage": {"inputTokens": 1},
                    }
                ],
            )

            self.assertEqual(result["recorded"], 0)
            self.assertEqual(result["skipped"], 1)

    def test_usage_delta_clamps_negative_and_ignores_unchanged_fields(self):
        previous = {
            "inputTokens": 100,
            "outputTokens": 50,
            "cacheWriteTokens": 10,
            "cacheReadTokens": 200,
            "totalTokens": 360,
        }
        current = {
            "inputTokens": 130,
            "outputTokens": 50,
            "cacheWriteTokens": 5,
            "cacheReadTokens": 260,
            "totalTokens": 445,
        }

        delta = self.module.usage_delta(previous, current)

        self.assertEqual(delta["inputTokens"], 30)
        self.assertEqual(delta["outputTokens"], 0)
        self.assertEqual(delta["cacheWriteTokens"], 0)
        self.assertEqual(delta["cacheReadTokens"], 60)
        self.assertFalse(self.module.has_positive_usage({"inputTokens": 0, "outputTokens": 0}))
        self.assertTrue(self.module.has_positive_usage(delta))

    def test_usage_delta_treats_missing_previous_as_full_current(self):
        current = {"inputTokens": 12, "outputTokens": 3, "totalTokens": 15}

        delta = self.module.usage_delta(None, current)

        self.assertEqual(delta["inputTokens"], 12)
        self.assertEqual(delta["outputTokens"], 3)

    def test_discover_cloud_agents_follows_next_cursor_pagination(self):
        responses = [
            {"items": [{"id": "bc-1"}], "nextCursor": "bc-2"},
            {"items": [{"id": "bc-2"}]},
        ]
        calls: list[str] = []

        def fake_api_request(url, key, **kwargs):
            calls.append(url)
            return responses.pop(0)

        self.module.api_request = fake_api_request
        try:
            agents = self.module.discover_cloud_agents("test-key")
        finally:
            self.module.api_request = self.module.__dict__.get("api_request")

        self.assertEqual([agent["id"] for agent in agents], ["bc-1", "bc-2"])
        self.assertEqual(len(calls), 2)
        self.assertIn("cursor=bc-2", calls[1])

    def test_sync_cloud_workspace_records_only_new_delta_across_polls(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            memory_dir = workspace / ".adlc5" / "demo" / "memory"
            memory_dir.mkdir(parents=True)
            binding = {
                "conversation_id": "bc-agent-1",
                "feature": "demo",
                "stage": "implement",
                "step": "implement-1-build",
                "model_id": "composer-2",
                "bound_at_ms": 1000,
            }
            (memory_dir / "cursor-usage-bindings.jsonl").write_text(
                json.dumps(binding) + "\n", encoding="utf-8"
            )
            config = {"CURSOR_API_KEY": "test-key"}

            first_usage = {
                "inputTokens": 100,
                "outputTokens": 20,
                "cacheWriteTokens": 5,
                "cacheReadTokens": 50,
                "totalTokens": 175,
            }
            second_usage = {
                "inputTokens": 140,
                "outputTokens": 20,
                "cacheWriteTokens": 5,
                "cacheReadTokens": 90,
                "totalTokens": 255,
            }
            responses = [
                {"runs": [{"id": "run-1", "usage": first_usage}]},
                {"runs": [{"id": "run-1", "usage": second_usage}]},
            ]

            original_api_request = self.module.api_request
            self.module.api_request = lambda url, key, **kwargs: responses.pop(0)
            try:
                first = self.module.sync_cloud_workspace(workspace, config, force=True)
                second = self.module.sync_cloud_workspace(workspace, config, force=True)
            finally:
                self.module.api_request = original_api_request

            self.assertEqual(first["recorded"], 1)
            self.assertEqual(second["recorded"], 1)

            ledger = memory_dir / "usage-ledger.jsonl"
            entries = [json.loads(line) for line in ledger.read_text().splitlines()]
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["tokens"]["input"], 100)
            self.assertEqual(entries[0]["tokens"]["cache_read"], 50)
            self.assertEqual(entries[1]["tokens"]["input"], 40)
            self.assertEqual(entries[1]["tokens"]["cache_read"], 40)

    def test_sync_cloud_workspace_skips_when_no_cloud_bindings(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            result = self.module.sync_cloud_workspace(workspace, {"CURSOR_API_KEY": "k"}, force=True)

            self.assertEqual(result["status"], "skipped")
            self.assertEqual(result["reason"], "no-cloud-bindings")


if __name__ == "__main__":
    unittest.main()
