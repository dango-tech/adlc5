#!/usr/bin/env python3
"""Lock and verify file-backed acceptance evidence."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

MANIFEST_NAME = "acceptance-lock.json"
TRUST_REF_PREFIX = "refs/adlc5/anchors"
FEATURE_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def evidence_path(workspace: Path, value: str) -> Path:
    path = (workspace / value).resolve()
    try:
        path.relative_to(workspace)
    except ValueError as exc:
        raise ValueError("evidence path escapes workspace") from exc
    return path


def relock_approved(state: dict, acceptance_id: str, old_digest: str, new_digest: str) -> bool:
    history = ((state.get("clarity") or {}).get("history") or [])
    return any(
        item.get("type") == "anchor_relock_approval"
        and item.get("acceptance_id") == acceptance_id
        and item.get("from_sha256") == old_digest
        and item.get("to_sha256") == new_digest
        and item.get("approved_by")
        for item in history
        if isinstance(item, dict)
    )


def manifest_entries(stories: list[dict]) -> list[dict]:
    entries = []
    for story in stories:
        for criterion in story.get("acceptance") or []:
            entries.append(
                {
                    "story_id": story.get("id"),
                    "id": criterion.get("id"),
                    "owner": criterion.get("owner"),
                    "evidence": criterion.get("evidence"),
                }
            )
    return sorted(entries, key=lambda item: str(item["id"]))


def manifest_seal(entries: list[dict]) -> str:
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def parse_manifest(raw: str) -> tuple[list[dict] | None, str | None]:
    try:
        manifest = json.loads(raw)
        entries = manifest["acceptance"]
        if not isinstance(entries, list) or manifest.get("sha256") != manifest_seal(entries):
            return None, "invalid_seal"
        return entries, None
    except (json.JSONDecodeError, KeyError, TypeError):
        return None, "invalid"


def load_manifest(path: Path) -> tuple[list[dict] | None, str | None]:
    if not path.is_file():
        return None, "missing"
    try:
        return parse_manifest(path.read_text(encoding="utf-8"))
    except OSError:
        return None, "invalid"


def trust_ref(feature: str) -> str:
    return f"{TRUST_REF_PREFIX}/{feature}"


def read_trusted_manifest(workspace: Path, feature: str) -> tuple[list[dict] | None, str | None, str | None]:
    ref = trust_ref(feature)
    resolved = subprocess.run(
        ["git", "-C", str(workspace), "rev-parse", "--verify", "--quiet", ref],
        capture_output=True,
        text=True,
    )
    if resolved.returncode != 0:
        probe = subprocess.run(
            ["git", "-C", str(workspace), "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
        )
        return None, "missing" if probe.returncode == 0 else "git_unavailable", None
    oid = resolved.stdout.strip()
    blob = subprocess.run(
        ["git", "-C", str(workspace), "cat-file", "blob", oid],
        capture_output=True,
        text=True,
    )
    if blob.returncode != 0:
        return None, "invalid_ref", oid
    entries, error = parse_manifest(blob.stdout)
    return entries, error, oid


def write_manifest(workspace: Path, feature: str, path: Path, entries: list[dict]) -> str:
    manifest = {"schema_version": "1.0", "acceptance": entries, "sha256": manifest_seal(entries)}
    raw = json.dumps(manifest, indent=2) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(raw, encoding="utf-8")
    ref = trust_ref(feature)
    previous = subprocess.run(
        ["git", "-C", str(workspace), "rev-parse", "--verify", "--quiet", ref],
        capture_output=True,
        text=True,
    )
    previous_oid = previous.stdout.strip() if previous.returncode == 0 else None
    hashed = subprocess.run(
        ["git", "-C", str(workspace), "hash-object", "-w", "--stdin"],
        input=raw,
        capture_output=True,
        text=True,
    )
    if hashed.returncode != 0:
        temporary.unlink(missing_ok=True)
        raise OSError(hashed.stderr.strip() or "unable to write anchor trust blob")
    oid = hashed.stdout.strip()
    expected = previous_oid or ("0" * 40)
    updated = subprocess.run(
        ["git", "-C", str(workspace), "update-ref", ref, oid, expected],
        capture_output=True,
        text=True,
    )
    if updated.returncode != 0:
        temporary.unlink(missing_ok=True)
        raise OSError(updated.stderr.strip() or "unable to update anchor trust ref")
    try:
        temporary.replace(path)
    except OSError:
        if previous_oid:
            subprocess.run(["git", "-C", str(workspace), "update-ref", ref, previous_oid, oid], check=False)
        else:
            subprocess.run(["git", "-C", str(workspace), "update-ref", "-d", ref, oid], check=False)
        temporary.unlink(missing_ok=True)
        raise
    return oid


def check_manifest(
    state: dict, current: list[dict], locked: list[dict], *, allow_relock: bool
) -> list[dict]:
    current_by_id = {item["id"]: item for item in current}
    locked_by_id = {item["id"]: item for item in locked}
    checks = []
    for criterion_id in sorted(set(current_by_id) | set(locked_by_id), key=str):
        actual = current_by_id.get(criterion_id)
        expected = locked_by_id.get(criterion_id)
        if actual == expected:
            continue
        approved_digest_change = False
        if allow_relock and actual and expected:
            actual_copy = copy.deepcopy(actual)
            expected_copy = copy.deepcopy(expected)
            actual_digest = (actual_copy.get("evidence") or {}).pop("sha256", None)
            expected_digest = (expected_copy.get("evidence") or {}).pop("sha256", None)
            approved_digest_change = (
                actual_copy == expected_copy
                and isinstance(actual_digest, str)
                and isinstance(expected_digest, str)
                and relock_approved(state, str(criterion_id), expected_digest, actual_digest)
            )
        if not approved_digest_change:
            checks.append(
                {
                    "id": criterion_id or "acceptance_manifest",
                    "status": "fail",
                    "reason": "manifest_mismatch",
                    "message": "acceptance criterion differs from the sealed manifest",
                }
            )
    return checks


def process(state: dict, workspace: Path, *, lock: bool) -> tuple[list[dict], list[dict], int, int]:
    stories = copy.deepcopy((state.get("tasks") or {}).get("stories") or [])
    checks: list[dict] = []
    locked = 0
    unlocked_commands = 0
    criterion_ids = [
        criterion.get("id")
        for story in stories
        for criterion in (story.get("acceptance") or [])
        if isinstance(criterion, dict)
    ]
    duplicates = sorted(str(item) for item, count in Counter(criterion_ids).items() if count > 1)
    if duplicates:
        checks.append(
            {
                "id": "acceptance_ids",
                "status": "fail",
                "reason": "duplicate_id",
                "message": "acceptance IDs must be unique across the feature",
                "duplicates": duplicates,
            }
        )
    implementation_started = state.get("current_stage") == "implement" or (
        (state.get("stage_status") or {}).get("implement") in ("in_progress", "completed")
    )

    for story in stories:
        for criterion in story.get("acceptance") or []:
            criterion_id = criterion["id"]
            evidence = criterion["evidence"]
            if evidence["type"] == "command":
                unlocked_commands += 1
                checks.append(
                    {
                        "id": criterion_id,
                        "status": "warn",
                        "reason": "command_manifest_locked",
                        "message": "command definition is manifest-locked; command output is not content-addressed",
                    }
                )
                continue

            try:
                path = evidence_path(workspace, evidence["value"])
            except ValueError as exc:
                checks.append(
                    {"id": criterion_id, "status": "fail", "reason": "outside_workspace", "message": str(exc)}
                )
                continue
            if not path.is_file():
                checks.append(
                    {
                        "id": criterion_id,
                        "status": "fail",
                        "reason": "missing",
                        "message": f"missing evidence file: {evidence['value']}",
                    }
                )
                continue

            actual = digest(path)
            expected = evidence.get("sha256")
            if lock:
                if not expected and implementation_started:
                    checks.append(
                        {
                            "id": criterion_id,
                            "status": "fail",
                            "reason": "unlocked_during_implementation",
                            "message": "file evidence must be locked before Implement starts",
                        }
                    )
                    continue
                if expected and expected != actual and not relock_approved(
                    state, criterion_id, expected, actual
                ):
                    checks.append(
                        {
                            "id": criterion_id,
                            "status": "fail",
                            "reason": "digest_mismatch",
                            "message": "locked evidence changed without anchor_relock_approval",
                        }
                    )
                    continue
                evidence["sha256"] = actual
                expected = actual
            elif not expected:
                checks.append(
                    {
                        "id": criterion_id,
                        "status": "fail",
                        "reason": "unlocked",
                        "message": "file evidence has no sha256 lock",
                    }
                )
                continue

            if expected != actual:
                checks.append(
                    {
                        "id": criterion_id,
                        "status": "fail",
                        "reason": "digest_mismatch",
                        "message": "evidence digest differs from the locked value",
                    }
                )
                continue

            locked += 1
            checks.append(
                {
                    "id": criterion_id,
                    "status": "pass",
                    "reason": "locked",
                    "message": "file evidence matches its sha256 lock",
                }
            )

    return stories, checks, locked, unlocked_commands


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("lock", "check"))
    parser.add_argument("--feature", required=True)
    parser.add_argument("--workspace", default=".")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    if not FEATURE_PATTERN.fullmatch(args.feature):
        print(json.dumps({"status": "error", "error": "invalid feature name", "checks": []}, indent=2))
        return 2
    state_path = workspace / ".adlc5" / args.feature / "state.json"
    manifest_path = state_path.parent / MANIFEST_NAME
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc), "checks": []}, indent=2))
        return 2

    stories, checks, locked, unlocked_commands = process(state, workspace, lock=args.action == "lock")
    entries = manifest_entries(stories)
    local_entries, local_error = load_manifest(manifest_path)
    sealed_entries, trust_error, _ = read_trusted_manifest(workspace, args.feature)
    if sealed_entries is not None:
        if local_entries != sealed_entries:
            checks.append(
                {
                    "id": "acceptance_manifest",
                    "status": "fail",
                    "reason": "manifest_worktree_mismatch",
                    "message": "local acceptance manifest differs from its Git trust ref",
                }
            )
        checks.extend(check_manifest(state, entries, sealed_entries, allow_relock=args.action == "lock"))
    elif (
        trust_error not in ("missing", "git_unavailable")
        or (trust_error == "git_unavailable" and bool(entries or local_entries is not None))
        or (args.action == "check" and bool(entries or local_entries is not None))
    ):
        checks.append(
            {
                "id": "acceptance_manifest",
                "status": "fail",
                "reason": f"trust_{trust_error}",
                "message": "acceptance lock Git trust ref is missing or invalid",
            }
        )
    if local_error not in (None, "missing"):
        checks.append(
            {
                "id": "acceptance_manifest",
                "status": "fail",
                "reason": f"manifest_{local_error}",
                "message": "local acceptance manifest is invalid",
            }
        )

    status = "fail" if any(item["status"] == "fail" for item in checks) else "pass"
    output = {
        "status": status,
        "feature": args.feature,
        "action": args.action,
        "locked": locked,
        "unlocked_commands": unlocked_commands,
        "checks": checks,
    }
    if args.action == "lock" and status == "pass":
        output["trust_oid"] = write_manifest(workspace, args.feature, manifest_path, entries)
        output["patch"] = {"tasks": {"stories": stories}}
    print(json.dumps(output, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
