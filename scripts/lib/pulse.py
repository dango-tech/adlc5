"""Bounded, read-only snapshots and offline views for ADLC5 Pulse."""
from __future__ import annotations

import hashlib
import html
import importlib.util
import json
import math
import os
import re
import subprocess
import stat
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 50_000
MAX_FEATURES = 200
FEATURE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
STAGES = ("specify", "plan", "tasks", "implement")

sys.path.insert(0, str(SCRIPTS))
from lib.model_prices import estimate_cost_usd, load_prices, lookup_price  # noqa: E402


class UnsafeInput(ValueError):
    pass


class Reader:
    """Read bounded regular files below one workspace; refuse symlinks and races."""

    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve(strict=True)
        self.observed: dict[str, tuple[int, int, int, int]] = {}
        self.warnings: list[str] = []
        self.count = 0
        self._started = time.monotonic()
        self._changed = False

    def prepare(self, paths: list[Path], *, max_bytes: int = 128 * 1024 * 1024, max_files: int = 10_000, timeout: float = 2.0) -> None:
        if len(paths) > max_files:
            raise UnsafeInput("fingerprint file-count limit exceeded")
        checked: dict[str, tuple[int, int, int, int] | None] = {}
        total = 0
        for path in paths:
            if time.monotonic() - self._started > timeout:
                raise UnsafeInput("fingerprint time limit exceeded")
            try:
                relative = path.relative_to(self.workspace)
            except ValueError as exc:
                raise UnsafeInput("fingerprint path outside workspace") from exc
            current = self.workspace
            info = None
            missing = False
            for part in relative.parts:
                current = current / part
                try:
                    info = current.lstat()
                except FileNotFoundError:
                    missing = True
                    break
                if stat.S_ISLNK(info.st_mode):
                    raise UnsafeInput("fingerprint symlink refused")
            if missing:
                checked[relative.as_posix()] = None
                continue
            if info is None or not stat.S_ISREG(info.st_mode):
                raise UnsafeInput("fingerprint non-regular file refused")
            if info.st_size > MAX_FILE_BYTES:
                raise UnsafeInput("fingerprint input exceeds 8 MiB limit")
            total += info.st_size
            if total > max_bytes:
                raise UnsafeInput("fingerprint aggregate byte limit exceeded")
            checked[relative.as_posix()] = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        self._prepared = checked

    def read(self, path: Path) -> bytes | None:
        try:
            relative = path.relative_to(self.workspace)
        except ValueError as exc:
            raise UnsafeInput("source outside selected workspace") from exc
        if hasattr(self, "_prepared") and relative.as_posix() not in self._prepared:
            raise UnsafeInput("fingerprint attempted an unprepared path")
        if hasattr(self, "_prepared") and time.monotonic() - self._started > 2:
            raise UnsafeInput("fingerprint time limit exceeded")
        current = self.workspace
        for part in relative.parts:
            current = current / part
            try:
                info = current.lstat()
            except FileNotFoundError:
                if hasattr(self, "_prepared") and self._prepared.get(relative.as_posix()) is not None:
                    raise UnsafeInput("source disappeared after validation")
                return None
            if stat.S_ISLNK(info.st_mode):
                raise UnsafeInput("symlink source refused")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(path, flags)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise UnsafeInput("source could not be opened safely") from exc
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                raise UnsafeInput("non-regular source refused")
            if before.st_size > MAX_FILE_BYTES:
                raise UnsafeInput("source exceeds 8 MiB limit")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                data = stream.read(MAX_FILE_BYTES + 1)
            after = os.fstat(fd)
        finally:
            os.close(fd)
        signature = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        if len(data) > MAX_FILE_BYTES or signature != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise UnsafeInput("source changed or exceeded bounded read")
        expected = getattr(self, "_prepared", {}).get(relative.as_posix())
        if hasattr(self, "_prepared") and expected != signature:
            raise UnsafeInput("source changed since validation")
        if relative.as_posix() in self.observed and self.observed[relative.as_posix()] != signature:
            self._changed = True
        self.observed[relative.as_posix()] = signature
        return data

    def stable(self) -> bool:
        if self._changed:
            return False
        for name, signature in self.observed.items():
            try:
                path = self.workspace / name
                info = path.lstat()
                if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                    return False
                if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) != signature:
                    return False
            except OSError:
                return False
        return True

    def release(self) -> None:
        self.__dict__.pop("_prepared", None)


def _json(reader: Reader, path: Path) -> dict[str, Any] | None:
    try:
        raw = reader.read(path)
    except UnsafeInput as exc:
        reader.warnings.append("unsafe_source:" + path.relative_to(reader.workspace).as_posix())
        return None
    if raw is None:
        return None
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        reader.warnings.append("malformed_json:" + path.relative_to(reader.workspace).as_posix())
        return None
    return value if isinstance(value, dict) else None


def _jsonl(reader: Reader, path: Path) -> tuple[list[dict[str, Any]], bool]:
    try:
        raw = reader.read(path)
    except UnsafeInput:
        reader.warnings.append("unsafe_or_oversized_source:" + path.relative_to(reader.workspace).as_posix())
        return [], True
    if raw is None:
        return [], False
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    partial = bool(text and not text.endswith(("\n", "\r")))
    if partial and lines:
        lines = lines[:-1]
        reader.warnings.append("partial_final_line:" + path.relative_to(reader.workspace).as_posix())
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        reader.count += 1
        if reader.count > MAX_RECORDS:
            reader.warnings.append("record_limit_exceeded")
            return rows, True
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            reader.warnings.append(f"malformed_record:{path.relative_to(reader.workspace).as_posix()}:{line_number}")
            continue
        if isinstance(item, dict):
            item["_pulse_source"] = path.relative_to(reader.workspace).as_posix()
            item["_pulse_line"] = line_number
            rows.append(item)
        else:
            reader.warnings.append(f"malformed_record:{path.relative_to(reader.workspace).as_posix()}:{line_number}")
    return rows, False


def _identity(directory: Path, workspace: Path) -> tuple[str, str | None]:
    relative = directory.relative_to(workspace / ".adlc5").as_posix()
    if relative.startswith("_archive/"):
        archive = relative.split("/", 1)[1]
        label = re.sub(r"-\d{8}$", "", archive)
        return label, archive
    return directory.name, None


def _feature_dirs(workspace: Path, active_only: bool, reader: Reader) -> list[Path]:
    root = workspace / ".adlc5"
    try:
        info = root.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise UnsafeInput(".adlc5 directory is unsafe")
    except FileNotFoundError:
        return []
    found: list[Path] = []
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if child.name == "_archive":
            if active_only:
                continue
            try:
                info = child.lstat()
                if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                    raise UnsafeInput("archive directory is unsafe")
            except FileNotFoundError:
                continue
            for archived in sorted(child.iterdir(), key=lambda p: p.name):
                if archived.name.startswith("."):
                    continue
                try:
                    info = archived.lstat()
                    if stat.S_ISREG(info.st_mode):
                        continue
                    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                        reader.warnings.append("unsafe_archive_directory:" + archived.name)
                        continue
                except FileNotFoundError:
                    continue
                if not FEATURE_NAME.fullmatch(archived.name):
                    reader.warnings.append("invalid_archive_id")
                    continue
                if any((archived / name).exists() for name in ('state.json', 'FEATURE.md', 'memory/usage-ledger.jsonl', 'delivery/state.json')):
                    found.append(archived)
            continue
        if child.name.startswith("."):
            continue
        try:
            info = child.lstat()
            if stat.S_ISREG(info.st_mode):
                continue
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                reader.warnings.append("unsafe_feature_directory:" + child.name)
                continue
        except FileNotFoundError:
            continue
        if not FEATURE_NAME.fullmatch(child.name):
            reader.warnings.append("invalid_feature_name")
            continue
        if any((child / name).exists() for name in ('state.json', 'FEATURE.md', 'memory/usage-ledger.jsonl', 'delivery/state.json')):
            found.append(child)
    if len(found) > MAX_FEATURES:
        reader.warnings.append("feature_limit_exceeded")
        found = found[:MAX_FEATURES]
    return found


def _safe_text(value: Any, limit: int = 300) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(c if c >= " " and c != "\x7f" else " " for c in value).replace("\x1b", " ")[:limit]


def _receipt_sources(directory: Path, workspace: Path, reader: Reader) -> tuple[list[dict], list[dict], list[dict]]:
    evidence = directory / "evidence"
    checks, checks_limited = _jsonl(reader, evidence / "completion.jsonl")
    gates, gates_limited = _jsonl(reader, evidence / "events.jsonl")
    usage, usage_limited = _jsonl(reader, directory / "memory" / "usage-ledger.jsonl")
    if checks_limited or gates_limited or usage_limited:
        reader.warnings.append("source_record_limit_exceeded")
    return checks, gates, usage


def _usage(rows: list[dict], root: Path) -> dict[str, Any]:
    if not rows:
        return {"status": "unavailable", "currency": "USD", "known_cost_usd": None, "complete_total_usd": None, "observed_records": 0, "accounted_records": 0, "token_records": 0, "tokens": {}, "unpriced_models": []}
    prices = load_prices(ROOT)
    by_id: dict[str, dict] = {}
    conflicts: set[str] = set()
    unique: list[dict] = []
    for row in rows:
        extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
        native_id = next((extra.get(key) for key in ("usage_event_id", "cursor_usage_event_id", "attempt_id") if isinstance(extra.get(key), str) and extra.get(key)), None)
        if not native_id:
            unique.append(row)
            continue
        key = str(native_id)
        encoded = json.dumps(row, sort_keys=True, separators=(",", ":"))
        if key in conflicts:
            continue
        if key not in by_id:
            by_id[key] = row
            unique.append(row)
        elif json.dumps(by_id[key], sort_keys=True, separators=(",", ":")) != encoded:
            conflicts.add(key)
            unique = [entry for entry in unique if entry is not by_id[key]]
    known = 0.0
    accounted = 0
    token_totals: dict[str, int] = {}
    token_records = 0
    unpriced: set[str] = set()
    unavailable = 0
    invalid = 0
    for row in unique:
        extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
        if extra.get("usage_unavailable") is True:
            unavailable += 1
            continue
        host_cost = extra.get("host_reported_cost_usd", row.get("host_reported_cost_usd"))
        tokens = row.get("tokens") if isinstance(row.get("tokens"), dict) else {}
        token_map = {key: tokens[key] for key in ("input", "output", "thinking", "cache_creation", "cache_read", "cache_5m", "cache_1h") if key in tokens}
        valid = all(type(value) is int and value >= 0 for value in token_map.values())
        if valid and token_map:
            token_records += 1
            for key, value in token_map.items():
                token_totals[key] = token_totals.get(key, 0) + value
        if "host_reported_cost_usd" in extra or "host_reported_cost_usd" in row:
            try:
                amount = float(host_cost)
                if type(host_cost) in (int, float) and math.isfinite(amount) and amount >= 0 and math.isfinite(known + amount):
                    known += amount
                    accounted += 1
                    continue
            except (TypeError, ValueError, OverflowError):
                pass
            invalid += 1
            continue
        model = row.get("model_id") if isinstance(row.get("model_id"), str) else "unknown"
        required_cost_fields = {"input", "output", "cache_creation", "cache_read"}
        try:
            cost, priced = estimate_cost_usd(token_map, model, prices) if valid and required_cost_fields <= token_map.keys() else (None, False)
        except (TypeError, ValueError, OverflowError):
            cost, priced = None, False
            invalid += 1
        if priced and cost is not None and math.isfinite(cost) and cost >= 0 and math.isfinite(known + cost):
            known += cost
            accounted += 1
        elif not valid or token_map and not required_cost_fields <= token_map.keys():
            invalid += 1
        elif not lookup_price(prices, model):
            unpriced.add(model)
    status = "partial" if accounted else "unavailable"
    return {
        "status": status, "currency": "USD", "known_cost_usd": round(known, 8) if accounted else None,
        "complete_total_usd": None,
        "observed_records": len(rows), "accounted_records": accounted,
        "token_records": token_records, "tokens": token_totals if token_records else {},
        "unavailable_records": unavailable, "duplicate_units": max(0, len(rows) - len(unique)),
        "conflicting_units": len(conflicts), "invalid_records": invalid, "unpriced_models": sorted(unpriced),
    }


def _evaluation(directory: Path, reader: Reader) -> dict[str, Any]:
    """Project local evaluator exports; compare only explicitly matched cohorts."""
    result = {
        "status": "not_measured", "runs": 0, "successful": 0,
        "success_rate_pct": None, "success_interval_pct": None,
        "escaped_defects": None, "rework": None,
        "savings_pct": None, "savings_range_pct": None, "matched_cases": 0,
        "reason": "No complete evaluation records; accuracy is not measured",
        "source": str((directory / "evaluation").relative_to(reader.workspace)),
    }
    warning_start = len(reader.warnings)
    records = []
    for name in ("telemetry", "usage", "outcomes"):
        rows, limited = _jsonl(reader, directory / "evaluation" / (name + ".jsonl"))
        records.append(rows)
        if limited:
            return {**result, "status": "partial", "reason": "Evaluation input exceeded limits"}
    telemetry, usage, outcomes = records
    if not any(records) and len(reader.warnings) == warning_start:
        return result
    spec = importlib.util.spec_from_file_location("pulse_evaluator", SCRIPTS / "evaluate-runs.py")
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    # The CLI scorer expects structured records; Pulse must fail closed on arbitrary local JSON.
    if (len(reader.warnings) != warning_start
        or any(not isinstance(row.get("run_id"), str) or not row["run_id"] for row in telemetry + usage + outcomes)
        or any(not isinstance(row.get("node_id"), str) or not row["node_id"] for row in telemetry + usage)
        or any(not isinstance(row.get("tokens", {}), dict) or not isinstance(row.get("extra", {}), dict) for row in usage)
        or any(not isinstance(row.get("profile"), str) for row in outcomes)
        or any("cost_usd" in row and type(row["cost_usd"]) not in (int, float) for row in usage)
        or any("estimated_cost_usd" in row.get("extra", {}) and type(row["extra"]["estimated_cost_usd"]) not in (int, float) for row in usage)):
        return {**result, "status": "partial", "reason": "Malformed evaluation records"}
    canonical_usage = [{k: v for k, v in row.items() if not k.startswith("_pulse_")} for row in usage]
    if len({json.dumps(row, sort_keys=True) for row in canonical_usage}) != len(usage):
        return {**result, "status": "partial", "reason": "Duplicate evaluation usage records"}
    try:
        report = scorer.evaluate(telemetry, usage, outcomes)
    except (TypeError, ValueError, OverflowError):
        return {**result, "status": "partial", "reason": "Invalid evaluation accounting"}
    result.update(runs=report["runs"]["total"], successful=report["runs"]["successful"])
    if report["status"] != "ok" or not outcomes:
        return {**result, "status": "partial", "reason": "Incomplete, duplicate, or uncorrelated evaluation records"}
    n = result["runs"]
    rate = result["successful"] / n
    z = 1.96
    center = (rate + z*z / (2*n)) / (1 + z*z/n)
    margin = z * math.sqrt(rate*(1-rate)/n + z*z/(4*n*n)) / (1 + z*z/n)
    result.update(status="measured", success_rate_pct=round(100*rate, 2),
                  success_interval_pct=[round(100*max(0, center-margin), 2), round(100*min(1, center+margin), 2)],
                  escaped_defects=sum(row["escaped_defects"] for row in outcomes),
                  rework=sum(row["rework"] for row in outcomes),
                  reason="Recorded outcome success, not a general accuracy score; no comparable cost baseline")
    groups = {}
    costs = {}
    for row in usage:
        explicit = row.get("cost_usd")
        if type(explicit) not in (int, float) or not math.isfinite(explicit) or explicit < 0:
            return result
        costs[row["run_id"]] = costs.get(row["run_id"], 0) + explicit
    for row in outcomes:
        arm, _, profile = row["profile"].partition(":")
        comparison = row.get("comparison_id")
        case = row.get("case_id")
        if (arm not in ("direct", "candidate") or not profile
            or not isinstance(comparison, str) or not comparison
            or not isinstance(case, str) or not case):
            return result
        groups.setdefault((comparison, case, profile), {}).setdefault(arm, []).append(row)
    savings = []
    baseline_total = candidate_total = 0
    for arms in groups.values():
        if set(arms) != {"direct", "candidate"}:
            return result
        # Compare equal repetitions only after every observed run meets the quality floor.
        if len(arms["direct"]) != len(arms["candidate"]) or any(not scorer.successful(row) for rows in arms.values() for row in rows):
            return {**result, "reason": "Savings withheld: unmatched repetitions or quality floor failed"}
        direct = sum(costs[row["run_id"]] for row in arms["direct"])
        candidate = sum(costs[row["run_id"]] for row in arms["candidate"])
        if direct <= 0 or not math.isfinite(direct + candidate):
            return result
        savings.append(100 * (direct-candidate) / direct)
        baseline_total += direct
        candidate_total += candidate
    if savings and math.isfinite(baseline_total + candidate_total):
        result.update(savings_pct=round(100*(baseline_total-candidate_total)/baseline_total, 2),
                      savings_range_pct=[round(min(savings), 2), round(max(savings), 2)], matched_cases=len(savings),
                      reason="Observed cost change vs direct agent; case range is not a confidence interval or future guarantee; general accuracy is not measured")
    return result


def _feature_projection(directory: Path, workspace: Path, reader: Reader, generated: str) -> dict[str, Any]:
    label, archive_id = _identity(directory, workspace)
    identity = hashlib.sha256((str(directory.relative_to(workspace)) + "\0" + label).encode()).hexdigest()[:20]
    reader._started = time.monotonic()
    state = _json(reader, directory / "state.json")
    if state is None:
        return {
            "id": label, "identity": identity, "archive_id": archive_id,
            "capture": {"stable": False, "input_fingerprint": None, "freshness": "unavailable", "captured_at": generated},
            "lifecycle": {"stage": None, "step": None},
            "evidence": {"checks": {"status": "unavailable"}, "review": {"status": "unavailable"}, "pr_ready": {"status": "unavailable", "reason": "state unavailable"}},
            "evaluation": _evaluation(directory, reader), "usage": _usage(_jsonl(reader, directory / 'memory/usage-ledger.jsonl')[0], ROOT), "next_action": {"reason_code": "state_unavailable", "label": "Inspect feature state"},
            "receipts": [], "events": [], "warnings": ["state_unavailable"],
        }
    stage = state.get("current_stage") if state.get("current_stage") in STAGES else None
    step = _safe_text(state.get("current_step"), 100) or None
    warning_start = len(reader.warnings)
    warnings: list[str] = []
    try:
        if archive_id:
            raise ValueError("archived evidence is historical")
        from lib.completion_evidence import fingerprint, gate_dependency_digest, gate_evaluator_id
        reader._started = time.monotonic()
        try:
            digest = fingerprint(workspace, label, safe_reader=reader, state_override=state)
            dependency_digest = gate_dependency_digest(workspace, label)
            evaluator_id = gate_evaluator_id(ROOT)
        finally:
            reader.release()
        freshness = "available"
    except Exception:
        digest = None
        dependency_digest = None
        evaluator_id = None
        freshness = "unavailable"
        warnings.append("input_fingerprint_unavailable")
    reader.count = 0
    checks, gates, usage_rows = _receipt_sources(directory, workspace, reader)
    warnings.extend(reader.warnings[warning_start:])
    latest_checks = next((row for row in reversed(checks) if row.get("kind") == "checks"), None)
    latest_review = next((row for row in reversed(checks) if row.get("kind") == "review"), None)
    def status_for(row: dict | None) -> str:
        if not row:
            return "unavailable"
        if row.get("stable") is False:
            return "unstable"
        if not digest or not row.get("fingerprint"):
            return "historical"
        if row.get("fingerprint") != digest:
            return "stale"
        if row.get("kind") == "checks":
            statuses = [item.get("status") for item in row.get("results", []) if isinstance(item, dict) and item.get("required", True)]
            return "pass" if statuses and all(x == "pass" for x in statuses) else "fail" if any(x == "fail" for x in statuses) else "partial"
        return "pass" if row.get("disposition") == "pass" and not row.get("blocking_findings") else "fail"
    check_status = status_for(latest_checks)
    review_status = status_for(latest_review)
    latest_gate = next((row for row in reversed(gates) if row.get("event") == "gate_check" and row.get("gate") == "pr-ready"), None)
    gate_status = "unavailable"
    if latest_gate:
        if latest_gate.get("inputs_verifiable") is not True or latest_gate.get("stable") is not True or not latest_gate.get("input_fingerprint_after"):
            gate_status = "historical"
        elif (latest_gate.get("input_fingerprint_after") == digest
              and latest_gate.get("dependency_digest_after") == dependency_digest
              and latest_gate.get("dependency_digest_after") == latest_gate.get("dependency_digest_before")
              and latest_gate.get("evaluator_id") == evaluator_id):
            gate_status = "pass" if latest_gate.get("status") == "pass" else "fail"
        else:
            gate_status = "stale"
    usage = _usage(usage_rows, ROOT)
    evaluation_warning_start = len(reader.warnings)
    evaluation = _evaluation(directory, reader)
    warnings.extend(reader.warnings[evaluation_warning_start:])
    pending = state.get("questions")
    if isinstance(pending, dict):
        pending = pending.get("pending")
    if pending:
        next_action = {"reason_code": "human_input_pending", "label": "Resolve the pending question"}
    elif check_status == "fail" or review_status == "fail" or gate_status == "fail":
        next_action = {"reason_code": "latest_evidence_failed", "label": "Review the latest failed evidence"}
    elif check_status == "stale" or review_status == "stale" or gate_status == "stale":
        next_action = {"reason_code": "evidence_stale", "label": "Rerun the required checks"}
    elif check_status == "unavailable":
        next_action = {"reason_code": "checks_unavailable", "label": "Inspect the current step and required checks"}
    else:
        next_action = {"reason_code": "inspect_current_step", "label": "Inspect the current canonical step"}
    receipts = []
    for row in (latest_checks, latest_review, latest_gate):
        if row:
            source = row.get("_pulse_source")
            receipts.append({"id": f"{source}:{row.get('_pulse_line')}" if source else None, "source": source, "line": row.get("_pulse_line"), "stage": _safe_text(row.get("stage"), 30), "step": _safe_text(row.get("step"), 80), "kind": _safe_text(row.get("kind") or row.get("event"), 40), "status": _safe_text(row.get("status"), 40) or _safe_text(row.get("disposition"), 40), "time": _safe_text(row.get("time"), 80) or None})
    source_events = []
    for row in (checks + gates)[-100:]:
        source = row.get("_pulse_source")
        source_events.append({"id": f"{source}:{row.get('_pulse_line')}" if source else None, "source": source, "line": row.get("_pulse_line"), "stage": _safe_text(row.get("stage"), 30), "step": _safe_text(row.get("step"), 80), "kind": _safe_text(row.get("kind") or row.get("event"), 40), "status": _safe_text(row.get("status") or row.get("disposition"), 40), "time": _safe_text(row.get("time"), 80) or None})
    capture_stable = reader.stable()
    if capture_stable and freshness == "available" and not archive_id:
        try:
            from lib.completion_evidence import fingerprint, gate_dependency_digest
            try:
                after_fingerprint = fingerprint(workspace, label, safe_reader=reader, state_override=state)
                after_dependencies = gate_dependency_digest(workspace, label)
            finally:
                reader.release()
            capture_stable = digest == after_fingerprint and dependency_digest == after_dependencies
        except Exception:
            capture_stable = False
            warnings.append("post_capture_fingerprint_unavailable")
    if not capture_stable:
        warnings.append("source_changed_during_capture")
        evaluation.update(status="partial", success_rate_pct=None, success_interval_pct=None, savings_pct=None, savings_range_pct=None, escaped_defects=None, rework=None, reason="Evaluation capture changed; repeat the snapshot")
        check_status = review_status = gate_status = "unstable"
        next_action = {"reason_code": "capture_unstable", "label": "Repeat the snapshot after inputs stop changing"}
    return {
        "id": label, "identity": identity, "archive_id": archive_id,
        "capture": {"stable": capture_stable, "input_fingerprint": digest, "freshness": freshness if capture_stable else "unstable", "captured_at": generated},
        "lifecycle": {"stage": stage, "step": step, "stage_status": {k: _safe_text(v, 30) for k, v in (state.get("stage_status") or {}).items() if k in STAGES}},
        "evidence": {
            "checks": {"status": check_status, "recorded_passed": sum(1 for x in (latest_checks or {}).get("results", []) if isinstance(x, dict) and x.get("required", True) and x.get("status") == "pass"), "required": sum(1 for x in (latest_checks or {}).get("results", []) if isinstance(x, dict) and x.get("required", True))},
            "review": {"status": review_status},
            "pr_ready": {"status": gate_status, "reason": None if gate_status != "unavailable" else "no sufficiently bound local gate receipt"},
        },
        "usage": usage, "evaluation": evaluation, "next_action": next_action,
        "receipts": receipts, "events": source_events,
        "warnings": warnings,
    }


def project_workspace(workspace: Path, feature: str | None = None, active_only: bool = False) -> dict[str, Any]:
    workspace = workspace.resolve(strict=True)
    reader = Reader(workspace)
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    directories = _feature_dirs(workspace, active_only, reader)
    if feature:
        if not FEATURE_NAME.fullmatch(feature):
            raise ValueError("invalid feature name")
        directories = [p for p in directories if feature in _identity(p, workspace)]
        if len(directories) > 1:
            raise ValueError("feature label is ambiguous; select its archive id")
    features = [_feature_projection(path, workspace, reader, generated) for path in directories]
    if not reader.stable():
        for item in features:
            item["capture"]["stable"] = False
            item["capture"]["freshness"] = "unstable"
            item["warnings"].append("source_changed_during_capture")
            item["evaluation"].update(status="partial", success_rate_pct=None, success_interval_pct=None, savings_pct=None, savings_range_pct=None, escaped_defects=None, rework=None, reason="Evaluation capture changed; repeat the snapshot")
            for evidence in item["evidence"].values():
                evidence["status"] = "unstable"
            item["next_action"] = {"reason_code": "capture_unstable", "label": "Repeat the snapshot after inputs stop changing"}
    result = {
        "schema_version": "1.0", "generated_at": generated,
        "status": "empty" if not features else "partial" if reader.warnings or any(f["warnings"] for f in features) else "ok",
        "capture": {"stable": reader.stable(), "scope": "feature" if feature else "workspace"},
        "workspace": {"label": workspace.name}, "features": features,
        "warnings": sorted(set(reader.warnings)),
    }
    return result


def band(snapshot: dict[str, Any], feature: str | None = None) -> str:
    rows = snapshot.get("features") or []
    if not feature and len(rows) > 1:
        return f"ADLC5 Pulse · {len(rows)} features · choose --feature"
    item = next((f for f in rows if feature in (f.get("id"), f.get("archive_id"))), None) if feature else (rows[0] if rows else None)
    if not item:
        detail = "feature not found" if feature else "no features"
        return f"ADLC5 Pulse · {snapshot.get('workspace', {}).get('label', 'workspace')} · {detail}"
    cost = item.get("usage", {}).get("known_cost_usd")
    evaluation = item.get("evaluation", {})
    savings = evaluation.get("savings_pct")
    rate = evaluation.get("success_rate_pct")
    metrics = (f"savings {savings:.1f}% observed" if savings is not None else "savings Not measured") + " · " + (f"outcome success {rate:.1f}% (n={evaluation.get('runs', 0)})" if rate is not None else "outcome success Not measured")
    money = f"${cost:.2f}" if isinstance(cost, (int, float)) else "cost unavailable"
    return f"ADLC5 Pulse · {item.get('id')} · {item.get('lifecycle', {}).get('stage') or 'stage unknown'} · {item.get('evidence', {}).get('checks', {}).get('status')} · {money} · {metrics} · snapshot {snapshot.get('generated_at')} · {item.get('next_action', {}).get('label')}"


def handoff(snapshot: dict[str, Any], feature: str) -> str:
    item = next((f for f in snapshot.get("features", []) if feature in (f.get("id"), f.get("archive_id"))), None)
    if not item:
        raise ValueError("feature not found in snapshot")
    lines = [f"# ADLC5 Pulse handoff: {html.escape(item['id'])}", "", f"Captured: {snapshot['generated_at']}", f"Stage/step: {html.escape(str(item['lifecycle'].get('stage') or 'unknown'))} / {html.escape(str(item['lifecycle'].get('step') or 'unknown'))}", f"Capture stable: {str(item['capture'].get('stable')).lower()}", f"Input fingerprint: {item['capture'].get('input_fingerprint') or 'unavailable'}", f"Checks: {item['evidence']['checks']['status']}", f"Review: {item['evidence']['review']['status']}", f"Local PR-ready gate: {item['evidence']['pr_ready']['status']}", f"Usage coverage: {item['usage']['status']} ({item['usage']['accounted_records']}/{item['usage']['observed_records']} records)", f"Known USD subtotal: {item['usage']['known_cost_usd'] if item['usage']['known_cost_usd'] is not None else 'unavailable'}", f"Next: {html.escape(item['next_action']['label'])}", "", "Snapshot observations are checked at capture time. Suggested action only; no command was run."]
    evaluation = item.get("evaluation", {})
    lines[-2:-2] = [f"Outcome success: {evaluation.get('successful', 0)}/{evaluation.get('runs', 0)} recorded runs ({evaluation.get('status', 'not_measured')})", f"Observed cost savings: {evaluation.get('savings_pct')} percent" if evaluation.get("savings_pct") is not None else "Projected savings: Not measured", html.escape(evaluation.get("reason", "Accuracy is not measured"))]
    return "\n".join(lines) + "\n"


def board_document(snapshot: dict[str, Any]) -> str:
    payload = json.dumps(snapshot, ensure_ascii=True, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    import base64
    script = (ROOT / "shared" / "pulse" / "board.js").read_text(encoding="utf-8")
    css = (ROOT / "shared" / "pulse" / "board.css").read_text(encoding="utf-8")
    icon = base64.b64encode((ROOT / "assets" / "brand" / "icon.svg").read_bytes()).decode("ascii")
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode("ascii")
    template = (ROOT / "shared" / "pulse" / "board.html").read_text(encoding="utf-8")
    values = {
        "{{TITLE}}": html.escape(snapshot.get("workspace", {}).get("label", "workspace")),
        "{{SCRIPT_HASH}}": digest,
        "{{CSS}}": css,
        "{{ICON}}": "data:image/svg+xml;base64," + icon,
        "{{SNAPSHOT}}": payload,
        "{{SCRIPT}}": script,
    }
    for key, value in values.items():
        template = template.replace(key, value)
    if "{{" in template:
        raise ValueError("unresolved Pulse board template placeholder")
    return template
