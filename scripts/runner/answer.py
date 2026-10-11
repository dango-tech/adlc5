#!/usr/bin/env python3
"""Record the user's reply to one pending runner question."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


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
            if item.get("id") == args.question_id:
                found.append((path, item))
        except (OSError, json.JSONDecodeError):
            continue
    if len(found) != 1:
        print(json.dumps({"status": "error", "error": "question id is unknown or ambiguous"}), file=sys.stderr)
        return 2
    path, item = found[0]
    if item.get("answer"):
        print(json.dumps({"status": "error", "error": "question already answered"}), file=sys.stderr)
        return 2
    item["answer"] = text
    item["answered_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path.write_text(json.dumps(item, indent=2) + "\n", encoding="utf-8")
    journal = path.parent / "answers.jsonl"
    with journal.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"id": args.question_id, "step": item.get("step"), "answer": text,
                                "answered_at": item["answered_at"]}, sort_keys=True) + "\n")
    print(json.dumps({"status": "ok", "question_id": args.question_id, "feature": path.parents[1].name}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
