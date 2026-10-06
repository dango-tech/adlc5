#!/usr/bin/env python3
"""Validate ADLC5 story dependencies and parallel file ownership."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from graphlib import CycleError, TopologicalSorter
from pathlib import Path


def result(check_id: str, ok: bool, message: str, **details: object) -> dict:
    item: dict[str, object] = {
        "id": check_id,
        "status": "pass" if ok else "fail",
        "message": message,
    }
    if details:
        item["details"] = details
    return item


def validate(stories: list[dict], parallel_batches: list[dict]) -> list[dict]:
    checks: list[dict] = []
    story_ids = [story.get("id") for story in stories]
    duplicates = sorted(str(sid) for sid, count in Counter(story_ids).items() if count > 1)
    checks.append(
        result(
            "unique_story_ids",
            not duplicates and all(isinstance(sid, str) and sid for sid in story_ids),
            "story IDs are unique" if not duplicates else "duplicate story IDs",
            duplicates=duplicates,
        )
    )

    known = {sid for sid in story_ids if isinstance(sid, str) and sid}
    missing: dict[str, list[str]] = {}
    for story in stories:
        sid = story.get("id")
        deps = story.get("depends_on") or []
        absent = sorted(str(dep) for dep in deps if dep not in known)
        if absent and isinstance(sid, str):
            missing[sid] = absent
    checks.append(
        result(
            "dependencies_exist",
            not missing,
            "all dependencies exist" if not missing else "missing story dependencies",
            missing=missing,
        )
    )

    cycle: list[str] = []
    if not duplicates and not missing:
        graph = {str(story["id"]): set(story.get("depends_on") or []) for story in stories}
        try:
            tuple(TopologicalSorter(graph).static_order())
        except CycleError as exc:
            if len(exc.args) > 1:
                cycle = [str(node) for node in exc.args[1]]
    checks.append(
        result(
            "acyclic",
            not cycle,
            "dependency graph is acyclic" if not cycle else "dependency cycle detected",
            cycle=cycle,
        )
    )

    invalid_batches = [
        {"story": story.get("id"), "batch": story.get("batch")}
        for story in stories
        if not isinstance(story.get("batch"), int)
        or isinstance(story.get("batch"), bool)
        or int(story["batch"]) < 1
    ]
    checks.append(
        result(
            "batch_values",
            not invalid_batches,
            "all stories have positive integer batches" if not invalid_batches else "invalid or missing story batches",
            violations=invalid_batches,
        )
    )

    expected_batches: dict[int, list[str]] = defaultdict(list)
    for story in stories:
        batch = story.get("batch")
        sid = story.get("id")
        if isinstance(batch, int) and not isinstance(batch, bool) and isinstance(sid, str):
            expected_batches[batch].append(sid)
    expected = [
        {"batch": batch, "story_ids": sorted(ids)}
        for batch, ids in sorted(expected_batches.items())
    ]
    actual = [
        {"batch": item.get("batch"), "story_ids": sorted(item.get("story_ids") or [])}
        for item in parallel_batches
    ]
    actual.sort(key=lambda item: (str(item["batch"]), item["story_ids"]))
    checks.append(
        result(
            "parallel_batches_match",
            actual == expected,
            "parallel batch registry matches story batches"
            if actual == expected
            else "parallel batch registry differs from story batches",
            expected=expected,
            actual=actual,
        )
    )

    by_id = {story.get("id"): story for story in stories if story.get("id") in known}
    bad_order: list[dict] = []
    for story in stories:
        sid = story.get("id")
        batch = story.get("batch")
        for dep in story.get("depends_on") or []:
            dep_story = by_id.get(dep)
            dep_batch = dep_story.get("batch") if dep_story else None
            if isinstance(batch, int) and isinstance(dep_batch, int) and dep_batch >= batch:
                bad_order.append({"story": sid, "batch": batch, "dependency": dep, "dependency_batch": dep_batch})
    checks.append(
        result(
            "batch_order",
            not bad_order,
            "dependency batches precede dependent stories" if not bad_order else "invalid dependency batch order",
            violations=bad_order,
        )
    )

    owners: dict[tuple[int, str], list[str]] = defaultdict(list)
    for story in stories:
        batch = story.get("batch")
        sid = story.get("id")
        if not isinstance(batch, int) or not isinstance(sid, str):
            continue
        for path in set(story.get("files") or []):
            if isinstance(path, str) and path:
                owners[(batch, path)].append(sid)
    overlaps = [
        {"batch": batch, "file": path, "stories": sorted(ids)}
        for (batch, path), ids in sorted(owners.items())
        if len(ids) > 1
    ]
    checks.append(
        result(
            "parallel_file_overlap",
            not overlaps,
            "parallel stories have disjoint files" if not overlaps else "parallel stories claim the same files",
            overlaps=overlaps,
        )
    )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature", required=True)
    parser.add_argument("--workspace", default=".")
    args = parser.parse_args()

    state_path = Path(args.workspace).resolve() / ".adlc5" / args.feature / "state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        tasks = state.get("tasks") or {}
        stories = tasks.get("stories") or []
        parallel_batches = tasks.get("parallel_batches") or []
        if not isinstance(stories, list) or not all(isinstance(story, dict) for story in stories):
            raise ValueError("state.tasks.stories must be an array of objects")
        if not isinstance(parallel_batches, list) or not all(isinstance(batch, dict) for batch in parallel_batches):
            raise ValueError("state.tasks.parallel_batches must be an array of objects")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc), "checks": []}, indent=2))
        return 2

    checks = validate(stories, parallel_batches)
    status = "fail" if any(check["status"] == "fail" for check in checks) else "pass"
    print(json.dumps({"status": status, "feature": args.feature, "checks": checks}, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
