#!/usr/bin/env python3
"""Record the user's reply to one pending runner question."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runner.questions import check_current
from runner.run import acquire_lock
from lib.state_v2 import atomic_write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question_id")
    parser.add_argument("--text", required=True)
    parser.add_argument("--workspace", default=".")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    text = args.text.strip()
    if not text:
        parser.error("--text cannot be empty")
    found = []
    for path in (workspace / ".adlc5").glob("*/pilot/pending-question.json"):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(item, dict) and item.get("id") == args.question_id:
                found.append((path, item))
        except (OSError, json.JSONDecodeError):
            continue
    if len(found) != 1:
        print(json.dumps({"status": "error", "error": "question id is unknown or ambiguous"}), file=sys.stderr)
        return 2
    path, _ = found[0]
    lock = path.parent / 'runner.lock'
    try:
        acquire_lock(lock)
    except RuntimeError as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}), file=sys.stderr)
        return 2
    try:
        return record_reply(workspace, path, text, args.question_id)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}), file=sys.stderr)
        return 2
    finally:
        lock.unlink(missing_ok=True)


def record_reply(workspace: Path, path: Path, text: str, question_id: str, *, quiet=False) -> int:
    item = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(item, dict) or item.get('id') != question_id:
        raise ValueError('pending question changed; inspect the current decision')
    try:
        check_current(workspace, path.parents[1].name, item)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}), file=sys.stderr)
        return 2
    if item.get("answer") and item['answer'] != text:
        print(json.dumps({"status": "error", "error": "question already answered"}), file=sys.stderr)
        return 2
    journal = path.parent / 'answers.jsonl'
    answers = [json.loads(line) for line in journal.read_text().splitlines() if line.strip()] if journal.exists() else []
    if any(not isinstance(entry, dict) for entry in answers):
        raise ValueError('answer journal entries must be objects')
    existing = [entry for entry in answers if entry.get('id') == question_id]
    if existing:
        if len(existing) != 1 or existing[0]['answer'] != text:
            raise ValueError('conflicting answer history')
        if not quiet:
            print(json.dumps({'status': 'ok', 'question_id': question_id, 'already_recorded': True}))
        return 0
    item["answer"] = text
    item.setdefault('answered_at', datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    added = []
    if item.get('category') != 'product' and item.get("denied_actions") and text.lower() in ("allow", "yes", "approve"):
        for denial in item["denied_actions"]:
            if not isinstance(denial, dict) or denial.get("tool_name") != "Bash":
                continue
            command = (denial.get("tool_input") or {}).get("command")
            if isinstance(command, str) and command.strip():
                added.append(command)
        if added:
            allowlist = path.parent / "approved-commands.json"
            try:
                current = json.loads(allowlist.read_text(encoding="utf-8")) if allowlist.is_file() else []
            except json.JSONDecodeError as exc:
                print(json.dumps({"status": "error", "error": f"invalid feature command allowlist: {exc}"}), file=sys.stderr)
                return 2
            if not isinstance(current, list) or any(not isinstance(command, str) for command in current):
                print(json.dumps({"status": "error", "error": "invalid feature command allowlist"}), file=sys.stderr)
                return 2
            atomic_write_json(allowlist, sorted(set(current + added)))
    atomic_write_json(path, item)
    answers.append({"id": question_id, "step": item.get("step"), "answer": text,
                                'category': item.get('category', 'permission' if item.get('denied_actions') else 'legacy'),
                                'decision_id': item.get('decision_id'), 'intent_sha256': item.get('intent_sha256'),
                                "answered_at": item["answered_at"]})
    from lib.state_v2 import atomic_write_text
    atomic_write_text(journal, ''.join(json.dumps(entry, sort_keys=True) + '\n' for entry in answers))
    if not quiet:
        print(json.dumps({"status": "ok", "question_id": question_id, "feature": path.parents[1].name,
                          "approved_commands_added": len(added)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
