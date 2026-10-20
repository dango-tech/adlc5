#!/usr/bin/env python3
import contextlib
import io
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("telemetry_share", ROOT / "scripts/telemetry-share.py")
share = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(share)


class TelemetryShareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        self.events = self.workspace / ".adlc5/secret-feature/telemetry/events.jsonl"
        self.events.parent.mkdir(parents=True)
        self.events.write_text("\n".join([
            json.dumps({"event": "script.end", "status": "pass", "feature": "secret-feature", "details": {"stdout": "private source"}, "run_id": "private-id"}),
            json.dumps({"event": "gate_fail", "status": "fail", "details": {"command": "secret command"}}),
            "not-json",
        ]) + "\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_preview_is_allowlisted_aggregate_and_disabled_by_default(self):
        payload = share.aggregate(self.workspace)
        self.assertFalse(share.is_enabled(self.workspace))
        self.assertEqual(set(payload), {"schema_version", "kind", "events", "statuses"})
        encoded = json.dumps(payload)
        for forbidden in ("secret-feature", "private source", "private-id", "secret command"):
            self.assertNotIn(forbidden, encoded)
        self.assertEqual(payload["events"]["script_end"], 1)
        self.assertEqual(payload["statuses"]["pass"], 1)

    def test_opt_in_is_explicit_and_opt_out_removes_queue_and_consent(self):
        share.set_enabled(self.workspace, True)
        payload, cursor = share.prepare_aggregate(self.workspace)
        share.enqueue(self.workspace, payload, cursor)
        self.assertTrue(share.is_enabled(self.workspace))
        share.set_enabled(self.workspace, False)
        self.assertFalse(share.is_enabled(self.workspace))
        self.assertFalse(share.outbox_path(self.workspace).exists())

    def test_disabled_send_refuses_before_network(self):
        with patch.object(share, "post_payload", side_effect=AssertionError("network called")):
            self.assertNotEqual(share.send_aggregate(self.workspace, "https://example.invalid"), 0)

    def test_retry_is_bounded_and_failure_keeps_queue(self):
        share.set_enabled(self.workspace, True)
        payload, cursor = share.prepare_aggregate(self.workspace)
        share.enqueue(self.workspace, payload, cursor)
        with patch.object(share, "post_payload", side_effect=OSError("offline")) as post:
            self.assertNotEqual(share.send_aggregate(self.workspace, "https://example.invalid", retries=2), 0)
        self.assertEqual(post.call_count, 2)
        self.assertTrue(share.outbox_path(self.workspace).exists())

    def test_unknown_local_fields_do_not_enter_payload(self):
        payload = share.aggregate(self.workspace)
        self.assertEqual(set(payload["events"]), set(share.EVENT_BUCKETS))
        self.assertEqual(set(payload["statuses"]), set(share.STATUS_BUCKETS))

    def test_malformed_local_enum_values_are_bucketed_as_other(self):
        with self.events.open("a") as stream:
            stream.write(json.dumps({"event": [], "status": {"secret": True}}) + "\n")
        payload = share.aggregate(self.workspace)
        self.assertEqual(payload["events"]["other"], 1)
        self.assertEqual(payload["statuses"]["other"], 1)

    def test_repeat_previews_are_deltas_after_successful_snapshot_cursor(self):
        payload, cursor = share.prepare_aggregate(self.workspace)
        self.assertEqual(payload["events"]["script_end"], 1)
        share._write_cursor(self.workspace, cursor)
        self.assertEqual(share.aggregate(self.workspace)["events"]["script_end"], 0)
        with self.events.open("a") as stream:
            stream.write(json.dumps({"event": "script.end", "status": "pass"}) + "\n")
        self.assertEqual(share.aggregate(self.workspace)["events"]["script_end"], 1)

    def test_send_previews_the_queued_payload_not_newer_events(self):
        share.set_enabled(self.workspace, True)
        payload, cursor = share.prepare_aggregate(self.workspace)
        share.enqueue(self.workspace, payload, cursor)
        with self.events.open("a") as stream:
            stream.write(json.dumps({"event": "script.end", "status": "pass"}) + "\n")
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch("builtins.input", return_value="yes"), patch.object(share, "post_payload") as post:
            self.assertEqual(share.main(["send", "--workspace", str(self.workspace), "--endpoint", "https://example.invalid"]), 0)
        preview, _ = json.JSONDecoder().raw_decode(output.getvalue())
        self.assertEqual(preview, payload)
        self.assertEqual(post.call_args.args[2], preview)
        self.assertEqual(share.aggregate(self.workspace)["events"]["script_end"], 1)

    def test_send_freezes_preview_before_confirmation(self):
        share.set_enabled(self.workspace, True)
        def confirm(_prompt):
            with self.events.open("a") as stream:
                stream.write(json.dumps({"event": "script.end", "status": "pass"}) + "\n")
            return "yes"
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch("builtins.input", side_effect=confirm), patch.object(share, "post_payload") as post:
            self.assertEqual(share.main(["send", "--workspace", str(self.workspace), "--endpoint", "https://example.invalid"]), 0)
        preview, _ = json.JSONDecoder().raw_decode(output.getvalue())
        self.assertEqual(post.call_args.args[2], preview)
        self.assertEqual(share.aggregate(self.workspace)["events"]["script_end"], 1)

    def test_successful_send_advances_local_cursor_without_recounting_old_events(self):
        share.set_enabled(self.workspace, True)
        sent = []
        with patch.object(share, "post_payload", side_effect=lambda _url, _route, payload, _key=None: sent.append(payload)):
            self.assertEqual(share.send_aggregate(self.workspace, "https://example.invalid"), 0)
            self.assertEqual(share.send_aggregate(self.workspace, "https://example.invalid"), 0)
        self.assertEqual(sent[0]["events"]["script_end"], 1)
        self.assertEqual(sent[1]["events"]["script_end"], 0)


if __name__ == "__main__":
    unittest.main()
