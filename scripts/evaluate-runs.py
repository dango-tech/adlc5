#!/usr/bin/env python3
"""Join ADLC5 telemetry, usage, and external outcomes without inventing a quality score."""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    invalid = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            invalid += 1
            continue
        if isinstance(value, dict):
            records.append(value)
        else:
            invalid += 1
    return records, invalid


REQUIRED_OUTCOME_FIELDS = {
    "anchors_passed",
    "regression_passed",
    "quality_gates_passed",
    "anchor_changed",
    "rework",
    "human_rejected",
    "escaped_defects",
}


def complete_outcome(outcome: dict[str, Any]) -> bool:
    boolean_fields = REQUIRED_OUTCOME_FIELDS - {"rework", "escaped_defects"}
    return bool(
        REQUIRED_OUTCOME_FIELDS <= outcome.keys()
        and all(type(outcome.get(field)) is bool for field in boolean_fields)
        and all(type(outcome.get(field)) is int and outcome[field] >= 0
                for field in ("rework", "escaped_defects"))
    )


def successful(outcome: dict[str, Any]) -> bool:
    escaped_defects = outcome.get("escaped_defects")
    return bool(
        complete_outcome(outcome)
        and outcome.get("anchors_passed") is True
        and outcome.get("regression_passed") is True
        and outcome.get("quality_gates_passed") is True
        and outcome.get("anchor_changed") is False
        and outcome.get("human_rejected") is False
        and isinstance(escaped_defects, int)
        and not isinstance(escaped_defects, bool)
        and escaped_defects == 0
    )


def cost(entry: dict[str, Any]) -> float:
    extra = entry.get("extra") or {}
    value = entry["cost_usd"] if "cost_usd" in entry else extra.get("estimated_cost_usd", 0)
    return float(value)


def valid_usage_numbers(entry: dict[str, Any]) -> bool:
    token_count = (entry.get("tokens") or {}).get("total", 0)
    attempt = entry.get("attempt", 1)
    try:
        entry_cost = cost(entry)
    except (TypeError, ValueError):
        return False
    return bool(
        isinstance(token_count, int)
        and not isinstance(token_count, bool)
        and token_count >= 0
        and isinstance(attempt, int)
        and not isinstance(attempt, bool)
        and attempt >= 1
        and math.isfinite(entry_cost)
        and entry_cost >= 0
    )


def has_usage_accounting(entry: dict[str, Any]) -> bool:
    tokens = entry.get("tokens") or {}
    extra = entry.get("extra") or {}
    return "total" in tokens or "cost_usd" in entry or "estimated_cost_usd" in extra


def evaluate(
    telemetry: list[dict[str, Any]], usage: list[dict[str, Any]], outcomes: list[dict[str, Any]]
) -> dict[str, Any]:
    run_telemetry = [item for item in telemetry if item.get("run_id")]
    run_usage = [item for item in usage if item.get("run_id")]
    valid_telemetry = [item for item in run_telemetry if item.get("node_id")]
    usage_with_node = [item for item in run_usage if item.get("node_id")]
    usage_missing_accounting = [item for item in usage_with_node if not has_usage_accounting(item)]
    accounted_usage = [item for item in usage_with_node if has_usage_accounting(item)]
    valid_usage = [item for item in accounted_usage if valid_usage_numbers(item)]
    invalid_usage = [item for item in accounted_usage if not valid_usage_numbers(item)]

    outcome_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in outcomes:
        if item.get("run_id"):
            outcome_groups[str(item["run_id"])].append(item)
    duplicate_outcomes = sum(len(items) - 1 for items in outcome_groups.values() if len(items) > 1)
    outcome_by_run = {run_id: items[0] for run_id, items in outcome_groups.items() if len(items) == 1}

    telemetry_runs = {str(item["run_id"]) for item in run_telemetry}
    usage_runs = {str(item["run_id"]) for item in valid_usage}
    telemetry_nodes = {(str(item["run_id"]), str(item["node_id"])) for item in valid_telemetry}
    usage_nodes = {(str(item["run_id"]), str(item["node_id"])) for item in valid_usage}
    correlated_usage_runs = {run_id for run_id, _ in telemetry_nodes & usage_nodes}

    usage_by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in valid_usage:
        usage_by_run[str(entry["run_id"])].append(entry)
    invalid_usage_runs = {
        str(entry["run_id"]) for entry in invalid_usage + usage_missing_accounting
    }
    run_success = {
        run_id: successful(outcome)
        and run_id in correlated_usage_runs
        and run_id not in invalid_usage_runs
        for run_id, outcome in outcome_by_run.items()
    }

    by_profile: dict[str, dict[str, int | float]] = {}
    for run_id, outcome in sorted(outcome_by_run.items()):
        profile = str(outcome.get("profile") or "unspecified")
        bucket = by_profile.setdefault(
            profile,
            {
                "runs": 0,
                "successful": 0,
                "tokens": 0,
                "cost_usd": 0.0,
                "failed_tokens": 0,
                "failed_cost_usd": 0.0,
            },
        )
        is_successful = run_success[run_id]
        bucket["runs"] += 1
        bucket["successful"] += int(is_successful)
        for entry in usage_by_run.get(run_id, []):
            token_count = int((entry.get("tokens") or {}).get("total", 0) or 0)
            if is_successful:
                bucket["tokens"] += token_count
                bucket["cost_usd"] += cost(entry)
            else:
                bucket["failed_tokens"] += token_count
                bucket["failed_cost_usd"] += cost(entry)

    caught = {
        (str(item["run_id"]), str(item["node_id"]), str(item["finding_id"]))
        for item in valid_telemetry + valid_usage
        if item.get("outcome") == "defect_caught"
        and item.get("finding_id")
        and (str(item["run_id"]), str(item["node_id"])) in telemetry_nodes & usage_nodes
    }
    by_node: dict[str, dict[str, int | float]] = {}
    max_attempt: dict[tuple[str, str], int] = {}
    for entry in valid_usage:
        run_id = str(entry["run_id"])
        node = str(entry["node_id"])
        bucket = by_node.setdefault(
            node,
            {"calls": 0, "tokens": 0, "cost_usd": 0.0, "retries": 0, "failures_caught": 0},
        )
        bucket["calls"] += 1
        bucket["tokens"] += int((entry.get("tokens") or {}).get("total", 0) or 0)
        bucket["cost_usd"] += cost(entry)
        key = (run_id, node)
        max_attempt[key] = max(max_attempt.get(key, 1), int(entry.get("attempt", 1) or 1))
    for (_, node), attempt in max_attempt.items():
        by_node[node]["retries"] += max(0, attempt - 1)
    for run_id, node, finding_id in caught:
        bucket = by_node.setdefault(
            node,
            {"calls": 0, "tokens": 0, "cost_usd": 0.0, "retries": 0, "failures_caught": 0},
        )
        bucket["failures_caught"] += 1

    for bucket in by_profile.values():
        bucket["cost_usd"] = round(float(bucket["cost_usd"]), 6)
        bucket["failed_cost_usd"] = round(float(bucket["failed_cost_usd"]), 6)
    for bucket in by_node.values():
        bucket["cost_usd"] = round(float(bucket["cost_usd"]), 6)

    missing = {
        "telemetry_without_run_id": len(telemetry) - len(run_telemetry),
        "usage_without_run_id": len(usage) - len(run_usage),
        "outcomes_without_run_id": len(outcomes) - sum(len(items) for items in outcome_groups.values()),
        "telemetry_without_node_id": len(run_telemetry) - len(valid_telemetry),
        "usage_without_node_id": len(run_usage) - len(usage_with_node),
        "usage_invalid_numeric": len(invalid_usage),
        "usage_missing_accounting": len(usage_missing_accounting),
        "telemetry_without_usage_node": len(telemetry_nodes - usage_nodes),
        "usage_without_telemetry_node": len(usage_nodes - telemetry_nodes),
        "outcomes_without_usage": len(set(outcome_by_run) - usage_runs),
        "outcomes_without_correlated_usage": len(set(outcome_by_run) - correlated_usage_runs),
        "outcomes_without_telemetry": len(set(outcome_by_run) - telemetry_runs),
        "usage_without_outcome": len(usage_runs - set(outcome_by_run)),
        "telemetry_without_outcome": len(telemetry_runs - set(outcome_by_run)),
        "outcomes_incomplete": sum(not complete_outcome(item) for item in outcome_by_run.values()),
        "duplicate_outcomes": duplicate_outcomes,
        "defects_without_finding_id": sum(
            item.get("outcome") == "defect_caught" and not item.get("finding_id")
            for item in valid_telemetry + valid_usage
        ),
    }
    status = "warn" if any(missing.values()) else "ok"
    return {
        "status": status,
        "runs": {
            "total": len(outcome_by_run),
            "successful": sum(run_success.values()),
        },
        "by_profile": by_profile,
        "by_node": by_node,
        "missing": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--telemetry", required=True)
    parser.add_argument("--usage", required=True)
    parser.add_argument("--outcomes", required=True)
    args = parser.parse_args()

    paths = [Path(args.telemetry), Path(args.usage), Path(args.outcomes)]
    try:
        telemetry, bad_telemetry = load_jsonl(paths[0])
        usage, bad_usage = load_jsonl(paths[1])
        outcomes, bad_outcomes = load_jsonl(paths[2])
    except OSError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        return 2

    report = evaluate(telemetry, usage, outcomes)
    invalid = {
        "telemetry_lines": bad_telemetry,
        "usage_lines": bad_usage,
        "outcome_lines": bad_outcomes,
    }
    if any(invalid.values()):
        report["status"] = "warn"
        report["invalid"] = invalid
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
