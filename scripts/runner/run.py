#!/usr/bin/env python3
"""Run ADLC5's navigator with supervised agent workers."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
# A bare "bash" on Windows resolves to the WSL launcher in System32 before PATH.
BASH = shutil.which("bash") or "bash"
sys.path.insert(0, str(SCRIPTS))
from lib import git_bootstrap  # noqa: E402
from runner import hosts  # noqa: E402
from runner.questions import pending as pending_question, check_current as check_question, current_answers, StaleQuestion  # noqa: E402
from lib.completion_evidence import fingerprint, records as evidence_records  # noqa: E402
from lib.config_layers import config_paths, effective_config  # noqa: E402
from lib.model_routing import load_yaml_file, merge_model_config  # noqa: E402
from lib.policies_load import CANONICAL_STEPS, load_policies, next_step_for_profile, profile_name, step_enabled  # noqa: E402
from lib.state_v2 import load_feature_state, atomic_write_json  # noqa: E402


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def retry_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return result.astimezone(timezone.utc) if result.tzinfo else None


def call(workspace: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run([sys.executable, str(SCRIPTS / "adlc5"), *args, "--workspace", str(workspace)],
                          cwd=workspace, text=True, capture_output=True, check=False)
    if check and proc.returncode:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"adlc5 {args[0]} failed")
    return proc


def git(workspace: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", "-C", str(workspace), *args], text=True, capture_output=True, check=False)
    if check and proc.returncode:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def attempt_event(events: list[dict[str, Any]], attempt_id: str, checkpoint: str) -> dict[str, Any] | None:
    return next((item for item in reversed(events) if item.get("attempt_id") == attempt_id and item.get("checkpoint") == checkpoint), None)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def resume_question(workspace: Path, feature: str) -> dict | None:
    feature_dir = workspace / '.adlc5' / feature
    path = feature_dir / 'pilot/pending-question.json'
    if not path.exists():
        return None
    pending = read_json(path)
    if not isinstance(pending, dict) or not isinstance(pending.get('id'), str) or not pending['id']:
        raise RuntimeError('invalid pending question; preserve and inspect it before resuming')
    if Path(pending['id']).name != pending['id'] or pending['id'] in ('.', '..'):
        raise RuntimeError('unsafe pending question id')
    try:
        check_question(workspace, feature, pending)
    except StaleQuestion:
        if pending.get('category') != 'product':
            raise
        atomic_write_json(feature_dir / 'pilot/superseded-questions' / (pending['id'] + '.json'), pending)
        path.unlink()
        deviation(feature_dir, 'superseded_product_question', question_id=pending['id'])
        return None
    if not pending.get('answer') or pending.get('denied_actions') and str(pending['answer']).lower() not in ('allow', 'yes', 'approve'):
        return pending
    from runner.answer import record_reply
    if record_reply(workspace, path, pending['answer'], pending['id'], quiet=True):
        raise RuntimeError('pending answer could not be recovered; inspect the answer journal')
    atomic_write_json(feature_dir / 'pilot/answered-questions' / (pending['id'] + '.json'), pending)
    path.unlink()
    return None


def interaction_mode(config: dict[str, Any], policies: dict[str, Any]) -> str:
    defaults = config.get("defaults") if isinstance(config.get("defaults"), dict) else {}
    mode = str(policies.get("interaction_mode") or defaults.get("interaction_mode") or "hitl")
    if mode not in ("hitl", "autonomous"):
        raise RuntimeError(f"unsupported interaction mode: {mode}")
    return mode


def append(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(item, sort_keys=True) + "\n")


def journal(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    return [item for line in lines if (item := read_json_line(line))]


def read_json_line(line: str) -> dict[str, Any] | None:
    try:
        item = json.loads(line)
        return item if isinstance(item, dict) else None
    except json.JSONDecodeError:
        return None


class ReworkNeeded(RuntimeError):
    """Verification found defects in the code; a coder must fix them before the next review."""


class RunnerStop(RuntimeError):
    """A durable stop whose next action can be taken in another process."""

    def __init__(self, condition: str, step: str, next_action: str, **detail: Any):
        super().__init__(condition)
        self.outcome = {"status": "stopped", "condition": condition, "step": step,
                        "next_action": next_action, "resume_owner": "operator",
                        "earliest_retry_at": None, **detail}


def stop_for_recovery(workspace: Path, attempt: dict[str, Any]) -> RunnerStop:
    return RunnerStop("recovery_required", attempt["step"],
        "Review the Git status and diff in this worktree. Preserve the changes separately, "
        "return to the expected commit with a clean checkout, then resume.",
        attempt_id=attempt["attempt_id"], workspace=str(workspace),
        expected_commit=attempt.get("expected_commit", attempt["start_commit"]))


def deviation(feature_dir: Path, kind: str, **detail: Any) -> None:
    """Record a departure from the configured settings; listed in the end summary."""
    append(feature_dir / "pilot/deviations.jsonl", {"kind": kind, "at": now(), **detail})


def rework_findings(events: list[dict[str, Any]], budget: int) -> str | None:
    """Findings to fix when the latest verify attempt was rejected; None when a review is due."""
    closed = [item for item in events if item.get("checkpoint") == "closed" and item.get("step") == "implement-2-verify"]
    if not closed or not closed[-1].get("rework"):
        return None
    if sum(1 for item in closed if item.get("kind") == "rework") >= budget:
        raise RuntimeError(f"verification still failing after {budget} rework attempts; human review required")
    return str(closed[-1].get("findings") or "verification failed")


def isolate_in_worktree(workspace: Path, feature: str, feature_dir: Path, branch: str) -> Path:
    """Create the feature's one worktree under .worktrees/ and move its state there."""
    base = git(workspace, "rev-parse", "HEAD")
    target = workspace / ".worktrees" / feature
    if target.resolve() != target or target.exists():
        raise git_bootstrap.BootstrapBlocked("worktree_target_unavailable", target,
            "Choose an unused local worktree path and resume.")
    if subprocess.run(["git", "-C", str(workspace), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"]).returncode == 0:
        raise git_bootstrap.BootstrapBlocked("feature_branch_exists", workspace,
            "Open a worktree for the existing feature branch and resume there.", branch=branch)
    # Excluded locally, so the tracked .gitignore is never edited.
    exclude = Path(git(workspace, "rev-parse", "--git-path", "info/exclude"))
    if not exclude.is_absolute():
        exclude = workspace / exclude
    if exclude.is_symlink():
        raise git_bootstrap.BootstrapBlocked("redirected_git_exclude", exclude,
            "Restore the Git exclude file within the repository metadata.")
    if ".worktrees/" not in (exclude.read_text(encoding="utf-8").splitlines() if exclude.is_file() else []):
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with exclude.open("a", encoding="utf-8") as stream:
            stream.write(".worktrees/\n")
    subprocess.run(["git", "-C", str(workspace), "worktree", "add", "-q", "-b", branch, str(target), base], check=True)
    target_feature = target / ".adlc5" / feature
    target_feature.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(feature_dir, target_feature, dirs_exist_ok=True, ignore=shutil.ignore_patterns("runner.lock", "runner.lock.guard"))
    # State changes are validated through the canonical kernel command.
    patch_file = target_feature / "pilot/runner-isolation.json"
    patch_file.parent.mkdir(parents=True, exist_ok=True)
    patch_file.write_text(json.dumps({"git": {"isolation": "worktree", "branch_name": branch,
        "base_branch": base, "worktree_path": str(target), "repository_root": str(target),
        "start_commit": base}}), encoding="utf-8")
    saved = call(target, "state", "set", "--feature", feature, "--file", str(patch_file), check=False)
    patch_file.unlink(missing_ok=True)
    if saved.returncode:
        subprocess.run(["git", "-C", str(workspace), "worktree", "remove", "--force", str(target)], check=False)
        subprocess.run(["git", "-C", str(workspace), "branch", "-D", branch], check=False, capture_output=True)
        raise RuntimeError(saved.stderr.strip() or saved.stdout.strip() or "could not transfer feature state to runner worktree")
    # Moved, not copied: one feature has one working directory and one copy of its state.
    shutil.rmtree(feature_dir)
    print(json.dumps({"status": "isolated", "worktree": str(target), "branch": branch,
                      "note": "feature state moved here; later runs from the main checkout are redirected"}), file=sys.stderr)
    return target


def feature_worktree(workspace: Path, feature: str) -> Path | None:
    """Another worktree of this repository that holds the feature's state."""
    listing = git(workspace, "worktree", "list", "--porcelain", check=False)
    for line in listing.splitlines():
        if line.startswith("worktree "):
            path = Path(line[9:])
            if path.resolve() != workspace and (path / ".adlc5" / feature / "state.json").is_file():
                return path.resolve()
    return None


def acquire_lock(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Serialize stale-owner reclamation. Keep the guard inode in place so
    # every contender locks the same file, including after a process exits.
    guard = path.with_name(path.name + ".guard")
    if path.is_symlink() or guard.is_symlink():
        raise RuntimeError(f"runner lock must be a regular file: {path}")
    with guard.open("ab") as stream:
        if os.name == "nt":
            import msvcrt
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        acquire_pid_lock(path)


def process_exists(pid: int) -> bool:
    if os.name == "nt":
        # A signal probe through os.kill is destructive on Windows.
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        process = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if not process:
            return ctypes.get_last_error() != 87  # ERROR_INVALID_PARAMETER
        try:
            return kernel.WaitForSingleObject(process, 0) != 0  # WAIT_OBJECT_0
        finally:
            kernel.CloseHandle(process)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    return True


def acquire_pid_lock(path: Path) -> None:
    payload = {"pid": os.getpid(), "started_at": now()}
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(payload, stream)
                stream.write("\n")
            return
        except FileExistsError:
            if not path.exists():
                continue
            owner = read_json(path)
            if not path.exists():
                continue
            if not isinstance(owner, dict) or type(owner.get("pid")) is not int or owner["pid"] <= 0:
                raise RuntimeError(f"invalid run lock at {path}; inspect and remove it manually")
            if not process_exists(owner["pid"]):
                path.unlink(missing_ok=True)
                continue
            raise RuntimeError(f"feature is locked by pid {owner['pid']}, started {owner.get('started_at', 'unknown')}")


def checkout_entries(workspace: Path, feature: str) -> dict[str, str]:
    result = subprocess.run(["git", "-C", str(workspace), "status", "--porcelain=v1", "-z", "--no-renames",
                             "--untracked-files=all"], check=True, capture_output=True)
    runtime_prefix = f"?? .adlc5/{feature}/"
    return {entry[3:]: entry[:2] for entry in os.fsdecode(result.stdout).split("\0")
            if entry and not entry.startswith(runtime_prefix)}


def checkout_dirty(workspace: Path, feature: str) -> bool:
    return bool(checkout_entries(workspace, feature))


def worker_change_paths(workspace: Path, feature: str, attempt: dict[str, Any], result: dict) -> list[str]:
    # Compare the full Git status so declarations cannot silently include unrelated index/worktree changes.
    changes = checkout_entries(workspace, feature)
    declared = result.get("changed_paths", [])
    if (git(workspace, "rev-parse", "HEAD") != attempt["start_commit"]
            or not isinstance(declared, list) or any(not isinstance(name, str) for name in declared)
            or set(changes) != set(declared) or any(status[0] not in (" ", "?") for status in changes.values())):
        raise stop_for_recovery(workspace, attempt)
    return list(changes)


def commit_worker_changes(workspace: Path, feature: str, path: Path, attempt: dict[str, Any], result: dict) -> None:
    paths = worker_change_paths(workspace, feature, attempt, result)
    if paths:
        subprocess.run(["git", "--literal-pathspecs", "-C", str(workspace), "add", "--", *paths], check=True)
        subprocess.run(["git", "--literal-pathspecs", "-C", str(workspace), "commit", "--only",
                        "-m", f"feat({feature}): complete {attempt['step']}", "--", *paths], check=True)
        record_checkpoint(path, attempt, "worker_committed", commit=git(workspace, "rev-parse", "HEAD"))


def ensure_isolation(workspace: Path, feature: str, feature_dir: Path, args: argparse.Namespace) -> tuple[str, str] | int:
    branch_prefix = "feat"
    # git_branch_prefix is retained in repository config independently of model setup.
    branch_prefix = effective_config(workspace)[0].get('git_branch_prefix') or branch_prefix
    state = load_feature_state(workspace, feature) or {}
    recorded_git = state.get("git") or {}
    recorded_isolation = recorded_git.get("isolation")
    branch = recorded_git.get("branch_name") if recorded_isolation in {"branch", "worktree", "current"} else None
    branch = branch or f"{branch_prefix}/{feature}"
    dirty = checkout_dirty(workspace, feature)
    if dirty:
        recorded_path = recorded_git.get("worktree_path")
        events_path = feature_dir / "pilot/attempts.jsonl"
        events = journal(events_path)
        resumable_attempt = None
        if recorded_path and Path(recorded_path).resolve() == workspace:
            for candidate in reversed(events):
                if "start_commit" not in candidate:
                    continue
                closed = attempt_event(events, candidate["attempt_id"], "closed")
                if not closed or closed.get("outcome") == "needs_human" or (
                    closed.get("outcome") == "fail" and attempt_event(events, candidate["attempt_id"], "evidence_ingested")
                ):
                    resumable_attempt = candidate
                    break
        runner_owned = bool(resumable_attempt and git(workspace, "rev-parse", "HEAD") == resumable_attempt.get("start_commit"))
        if not runner_owned:
            if git(workspace, "branch", "--show-current") not in ("main", "master"):
                raise git_bootstrap.BootstrapBlocked("dirty_checkout", workspace,
                    "Preserve or commit existing changes before running on this feature branch.")
            target = isolate_in_worktree(workspace, feature, feature_dir, branch)
            return run(argparse.Namespace(**{**vars(args), "workspace": str(target)}))
    common = Path(git(workspace, "rev-parse", "--git-common-dir"))
    if not common.is_absolute():
        common = (workspace / common).resolve()
    gitdir = Path(git(workspace, "rev-parse", "--absolute-git-dir"))
    linked = gitdir.resolve() != common.resolve()
    current = git(workspace, "branch", "--show-current")
    if current != branch:
        # A host-created worktree is reused as is: only the branch changes, in place.
        if not linked and current and current not in ("main", "master"):
            raise git_bootstrap.BootstrapBlocked("different_branch", workspace,
                "Open a worktree for the feature branch and resume.", current_branch=current, expected_branch=branch)
        exists = subprocess.run(["git", "-C", str(workspace), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"]).returncode == 0
        switch = subprocess.run(["git", "-C", str(workspace), "switch", "--", branch] if exists else
                                ["git", "-C", str(workspace), "switch", "-c", branch],
                                capture_output=True, text=True, check=False)
        if switch.returncode:
            content = switch.stderr
            if "already used by worktree" in content or "already checked out" in content:
                raise git_bootstrap.BootstrapBlocked("branch_checked_out", workspace,
                    "Open the worktree that already checks out the feature branch.", branch=branch)
            raise git_bootstrap.BootstrapBlocked("git_switch_failed", workspace,
                "Check Git metadata and checkout permissions, then resume.", branch=branch,
                command="git switch", exit_code=switch.returncode)
    isolation = "current" if recorded_isolation == "current" else "worktree" if linked else "branch"
    saved = call(workspace, "state", "set", "--feature", feature, "--patch", json.dumps({"git": {
        "isolation": isolation, "branch_name": branch,
        "base_branch": recorded_git.get("base_branch") or git(workspace, "rev-parse", "HEAD"),
        "worktree_path": str(workspace),
        "repository_root": str(workspace),
        "start_commit": recorded_git.get("start_commit") or git(workspace, "rev-parse", "HEAD"),
    }}), check=False)
    if saved.returncode:
        raise RuntimeError(saved.stderr.strip() or saved.stdout.strip() or "failed to record git isolation")
    return branch, isolation


def stage_brief(workspace: Path, feature: str, step: str, gates: Any, rework: str | None = None) -> tuple[str, str | None]:
    state = load_feature_state(workspace, feature) or {}
    stage = str(state.get("current_stage", "specify"))
    skill = "qa" if step == "implement-4-qa" else stage
    story = None
    if step in ("implement-1-build", "implement-2-verify"):
        stories = (state.get("tasks") or {}).get("stories", [])
        story = next((s.get("id") for s in stories if step.endswith("build") and s.get("type") != "integration" and s.get("status") not in ("implementation_complete", "verified")), None)
        targets = [story] if story else ([s.get("id") for s in stories if s.get("type") != "integration" and s.get("status") in ("implementation_complete", "verified")] if step.endswith("verify") else [])
        packs = []
        for story_id in targets:
            proc = subprocess.run([BASH, str(SCRIPTS / "memory/generate-pack.sh"), "--feature", feature,
                                   "--story-id", str(story_id), "--persona", "coder" if step.endswith("build") or rework else "tester",
                                   "--workspace", str(workspace)], cwd=workspace, capture_output=True, text=True)
            if proc.returncode:
                raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"context pack failed for {story_id}")
            packs.append((workspace / json.loads(proc.stdout)["pack"]).read_text(encoding="utf-8"))
        if packs:
            text = "\n\n---\n\n".join(packs) + "\n\nGate feedback:\n" + json.dumps(gates, indent=2)
            if rework:
                text = ((ROOT / "skills/adlc5-assure-reworker/SKILL.md").read_text(encoding="utf-8") + "\n\n---\n\n" + text +
                        "\n\nVerification findings to fix (do not review; fix the code):\n" + rework)
            return text, story
    skill_dir = ROOT / "skills" / skill
    if stage == "specify":
        phase = int(step.split("-")[1])
        paths = [skill_dir / "SKILL.md", *sorted((skill_dir / "phases").glob(f"{phase:02d}-*.md"))]
    else:
        paths = sorted((skill_dir / "phases").glob("*.md")) or [skill_dir / "SKILL.md"]
    chunks = [f"## {path.name}\n\n{path.read_text(encoding='utf-8')}" for path in paths if path.is_file()]
    answer_lines = '\n'.join(json.dumps(entry) for entry in current_answers(workspace, feature))
    return "\n\n".join(chunks) + "\n\nNavigator gate feedback:\n" + json.dumps(gates, indent=2) + \
        ("\n\nHuman answers:\n" + answer_lines if answer_lines else ""), story


def enforce_scope_block(workspace: Path, feature: str) -> None:
    path = workspace / ".adlc5" / feature / "spec-handoff.md"
    if not path.is_file():
        raise RuntimeError("scope confirmation is missing from spec-handoff.md")
    text = path.read_text(encoding="utf-8").lower()
    required = ("in scope", "out of scope", "source of truth", "assumptions")
    missing = [field for field in required if field not in text]
    if missing:
        raise RuntimeError("spec-handoff.md is missing scope confirmation fields: " + ", ".join(missing))


def command_allowlist(workspace: Path, feature: str) -> list[str]:
    """Translate repo-declared test/lint/build commands into Claude tool permissions."""
    path = workspace / ".agents" / "commands.yaml"
    if not path.is_file():
        return []
    try:
        data = load_yaml_file(path)
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"cannot read .agents/commands.yaml allowlist: {exc}") from exc
    commands = data.get("commands") if isinstance(data, dict) else None
    if not isinstance(commands, dict):
        raise RuntimeError(".agents/commands.yaml must contain a commands mapping")
    allowed = []
    for name in ("test", "lint", "build"):
        entry = commands.get(name)
        command = entry.get("run") if isinstance(entry, dict) else entry
        if isinstance(command, str) and command.strip():
            allowed.append("Bash(" + command.strip() + ")")
        elif isinstance(command, list):
            allowed.extend("Bash(" + item.strip() + ")" for item in command if isinstance(item, str) and item.strip())
    approved = read_json(workspace / ".adlc5" / feature / "pilot/approved-commands.json", [])
    if not isinstance(approved, list) or any(not isinstance(item, str) or not item.strip() for item in approved):
        raise RuntimeError("feature approved-commands.json is malformed")
    allowed.extend("Bash(" + item + ")" for item in approved)
    return allowed


def parse_worker_result(raw: Any, host: str) -> dict:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            # Cursor's JSON transport concatenates commentary and the final fenced result.
            blocks = list(re.finditer(r'```json\s*\n(.*?)\n```', raw, re.DOTALL)) if host == 'cursor' else []
            if len(blocks) != 1 or raw[blocks[0].end():].strip():
                raise ValueError('host did not return one final JSON result')
            raw = json.loads(blocks[0][1])
    return decode_worker_result(raw)


def decode_worker_result(value: Any) -> dict:
    if not isinstance(value, dict):
        raise ValueError('worker result must be an object')
    if 'payload_json' not in value:
        return value  # Older attended/result-file workers remain readable.
    payload = json.loads(value['payload_json'])
    if not isinstance(payload, dict) or set(payload) & {'attempt_id', 'status', 'summary', 'payload_json'}:
        raise ValueError('worker payload must be an object without envelope overrides')
    return {**{k: v for k, v in value.items() if k != 'payload_json'}, **payload}


def worker_prompt(workspace: Path, feature: str, attempt: dict[str, Any], brief: str,
                  host: str, mode: str) -> str:
    attempt_id = attempt["attempt_id"]
    last = workspace / ".adlc5" / feature / "pilot/results" / f"{attempt_id}.last-message.json"
    # Fixed rules first and the per-attempt id last, so separate workers share a cacheable prefix.
    result_prompt = ("You are an ADLC5 worker. Do only the current step. Do not run transitions, change lifecycle state, "
              "stage, commit, push, create worktrees, or perform the next step, even where the brief below says to. "
              "Write only in the workspace. Return one JSON object with attempt_id, status "
              "(completed, needs_human or failed), summary, and any story_id, state_patch or review the step requires. "
              "Report changed_paths as the list of workspace-relative repository files you edited, added or deleted. "
              "Use exact paths and omit ignored feature artifacts. "
              "Investigate consequential unknowns using repository inspection, official research, or a bounded experiment first. "
              "Ask the user for product tradeoffs and authorization they own. For a human product decision return needs_human "
              "and a question object with decision_id, category='product', text, rationale, recommendation, alternatives[], "
              "requirement_ids[] and intent_sha256 from readiness prepare. Ask one dependent decision at a time; "
              "reuse prior answers and explicit preferences. Never treat a product answer as command permission.\n\n"
              "Before completing Specify handoff, use adlc5 readiness prepare and record an actual "
              "requirements review (docs/requirements-readiness.md). Never infer readiness from a clarity score. "
              "After intent or policy changes, reassess before marking the step completed. "
              "High-risk intent needs an independent reviewer session; request human help if unavailable.\n\n"
              "Before leaving Plan (or Specify for tiny), extend the review with readiness delivery: "
              "assess operational applicability and validation methods, and preserve mandatory constraints for coders. "
              "Before Build map requirements and decisions to stories and matching acceptance IDs. "
              "During verification satisfy applicable obligations with current evidence and record delivery.conformance "
              "for missing, partial, contradictory, unrequested behavior and constraints. Use the actual diff reviewer's "
              "session ID. Return findings for bounded rework; never certify an unavailable check. "
              "Legacy_unbound answers are historical context, not current authorization; reassess consequential choices.\n\n"
              f"Feature: {feature}\nStep: {attempt['step']}\n\n{brief}\n\nattempt_id: {attempt_id}\n\n"
              "Transport format: return exactly attempt_id, status, summary, payload_json. "
              "payload_json is a JSON-encoded object containing the step-specific fields described above "
              "(question, story_id, state_patch, review, changed_paths); use '{}' when none apply. "
              "Do not put those fields at the outer level or repeat the envelope fields inside payload_json.")
    prompt = result_prompt
    try:
        from runner.questions import intent
        prompt += '\n\nKernel-computed current intent_sha256: ' + intent(workspace, feature) + \
            '. Use this digest for a product question; no shell command is needed to recompute it.'
    except (ValueError, TypeError, KeyError, OSError):
        pass  # Early discovery may not have its mandatory intent sources yet.
    if mode == "attended" or host == "hermes":
        prompt += (f"\n\nWhen finished, write the final JSON object to {last}. Include attempt_id {attempt_id}, "
                   "status, summary, and any required story_id, state_patch, or review fields. Do not exit until that file is written. "
                   "Then tell the user the result file is ready so they can exit the host CLI and return control to the runner.")
    return prompt


def run_worker(workspace: Path, feature: str, attempt: dict[str, Any], prompt: str,
               model: dict[str, Any], timeout: int, host: str, mode: str,
               interaction_mode: str) -> tuple[int, dict[str, Any], str]:
    result_dir = workspace / ".adlc5" / feature / "pilot/results"
    result_dir.mkdir(parents=True, exist_ok=True)
    attempt_id = attempt["attempt_id"]
    schema, last, result = (result_dir / f"{attempt_id}.{suffix}" for suffix in ("schema.json", "last-message.json", "json"))
    schema.write_text(json.dumps({"type": "object", "required": ["attempt_id", "status", "summary", "payload_json"],
        "properties": {"attempt_id": {"const": attempt_id}, "status": {"enum": ["completed", "needs_human", "failed"]},
                       "summary": {"type": "string"}, "payload_json": {"type": "string"}},
        "additionalProperties": False}, indent=2))
    allowlist = command_allowlist(workspace, feature) if host == "claude" else []
    usage_file = result_dir / f"{attempt_id}.usage.json"
    session_file = result_dir / f"{attempt_id}.session.json"
    argv = hosts.command(host=host, mode=mode, workspace=workspace, prompt=prompt,
                         model=model.get("model_id"), effort=model.get("effort"), allowlist=allowlist,
                         session_id=attempt_id, usage_file=usage_file if host == "hermes" and mode != "attended" else None)
    if mode != "attended" and host == "codex":
        argv[2:2] = ["--output-schema", str(schema), "-o", str(last)]
    elif mode != "attended" and host == "claude":
        argv.extend(("--json-schema", json.dumps(json.loads(schema.read_text(encoding="utf-8")))))
    log = result_dir / f"{attempt_id}.log"
    timed_out = stopped = False
    with log.open("w", encoding="utf-8") as stream:
        proc = subprocess.Popen(argv, cwd=workspace, env=hosts.environment(
                                    host, feature=feature, attempt_id=attempt_id,
                                    session_file=session_file if host == "cursor" else None),
                                stdout=None if mode == "attended" else stream,
                                stderr=None if mode == "attended" else subprocess.STDOUT,
                                start_new_session=True, text=True)
        started = time.monotonic()
        try:
            while proc.poll() is None:
                if time.monotonic() - started >= timeout:
                    timed_out = True
                    break
                if (workspace / ".adlc5" / feature / "STOP").exists():
                    stopped = True
                    break
                switch = subprocess.run([BASH, str(SCRIPTS / "pilot-check-kill-switch.sh"), "--feature", feature,
                                         "--workspace", str(workspace)], cwd=workspace, capture_output=True, text=True)
                if switch.returncode:
                    stopped = True
                    break
                time.sleep(2)
        except KeyboardInterrupt:
            stopped = True
        if timed_out or stopped:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
    log_text = log.read_text(encoding="utf-8", errors="replace")
    events = hosts.parse_events(host, log_text)
    if host == "hermes" and usage_file.is_file():
        usage_data = read_json(usage_file, {})
        if isinstance(usage_data, dict):
            events["usage"] = {name: usage_data[key] for name, key in {
                "input": "input_tokens", "output": "output_tokens", "thinking": "reasoning_tokens",
                "cache_read": "cache_read_tokens", "cache_creation": "cache_write_tokens"}.items()
                if type(usage_data.get(key)) is int and usage_data[key] >= 0}
            events["model_id"] = usage_data.get("model")
            events["host_reported_cost_usd"] = usage_data.get("estimated_cost_usd")
            events["calls"] = usage_data.get("api_calls", 1)
            events["is_error"] = any(usage_data.get(flag) is True for flag in ("failed", "interrupted", "partial"))
    # Failed attempts still spent tokens: every error result carries what the host reported.
    spent = {key: events[key] for key in ("usage", "model_id", "host_reported_cost_usd", "calls") if events.get(key)}
    spent["observed_model_id"] = events.get("model_id")
    if stopped:
        return 130, {"error": "worker interrupted", "failure_kind": "interrupted", **spent}, log_text
    if timed_out:
        return 124, {"error": "worker timed out", "failure_kind": "worker_timeout", **spent}, log_text
    if mode == "attended" or host == "hermes":
        if not last.is_file():
            return proc.returncode or 1, {"error": "worker exited without writing the attempt result file",
                                         "failure_kind": "invalid_worker_result", **spent}, log_text
    if events.get("denied_actions") and interaction_mode == "hitl":
        denied = events["denied_actions"]
        question = "The worker was denied: " + json.dumps(denied, ensure_ascii=False) + ". Reply 'allow' to add its command to this feature allowlist, or 'deny'."
        return 0, {"status": "needs_human", "attempt_id": attempt_id, "summary": "permission approval required",
                   "question": question, "denied_actions": denied, "usage": events.get("usage", {}),
                   "model_id": events.get("model_id"), "observed_model_id": events.get("model_id"),
                   "host_reported_cost_usd": events.get("host_reported_cost_usd")}, log_text
    if events.get("quota_limited") and not events.get("denied_actions"):
        earliest = retry_time(events.get("earliest_retry_at"))
        return proc.returncode or 1, {"error": "host quota limited", "failure_kind": "host_quota",
                                     "earliest_retry_at": earliest.isoformat() if earliest else None, **spent}, log_text
    if events.get("is_error") or events.get("denied_actions"):
        return proc.returncode or 1, {"error": "host reported an error or denied action",
                                       "failure_kind": "permission_required" if events.get("denied_actions") else "host_failed",
                                       **events, "observed_model_id": events.get("model_id")}, log_text
    if mode != "attended" and host != "hermes":
        try:
            raw_result = events.get("text") or "{}"
            result_data = parse_worker_result(raw_result, host)
            if result_data.get("attempt_id") != attempt_id:
                raise ValueError("structured result did not match the active attempt; host must return the schema object")
            last.write_text(json.dumps(result_data), encoding="utf-8")
        except (json.JSONDecodeError, ValueError, AttributeError, TypeError) as exc:
            return proc.returncode or 1, {"error": f"invalid {host} worker result: {exc}", "failure_kind": "invalid_worker_result", **spent}, log_text
    if not last.is_file():
        return (124 if timed_out else 130 if stopped else proc.returncode or 1), {"error": "missing result file", **spent}, log_text
    try:
        worker = decode_worker_result(json.loads(last.read_text(encoding="utf-8")))
        if not isinstance(worker, dict) or worker.get("attempt_id") != attempt_id or worker.get("status") not in ("completed", "needs_human", "failed"):
            raise ValueError("result identity or status mismatch")
    except (ValueError, json.JSONDecodeError) as exc:
        return (proc.returncode or 1), {"error": f"invalid result: {exc}", "failure_kind": "invalid_worker_result", **spent}, log_text
    host_session_id = events.get("session_id")
    if host == "cursor" and session_file.is_file():
        session_record = read_json(session_file, {})
        if isinstance(session_record, dict) and session_record.get("attempt_id") == attempt_id:
            host_session_id = session_record.get("session_id")
    if mode == "attended" and host == "claude":
        host_session_id = attempt_id
        transcript_usage, transcript_model = claude_session_usage(host_session_id)
        events["usage"] = transcript_usage
        events["model_id"] = transcript_model
    # The attempt id is the runner-owned identity when a host exposes no session id.
    worker.update(session_id=host_session_id or attempt_id, host_session_id=host_session_id,
                  model_id=events.get("model_id") or model.get("model_id") or "unknown",
                  observed_model_id=events.get("model_id"),
                  usage=events.get("usage") or {}, wall_seconds=round(time.monotonic() - started, 3),
                  calls=events.get("calls", 1), host_reported_cost_usd=events.get("host_reported_cost_usd"))
    temp = result.with_suffix(".tmp")
    temp.write_text(json.dumps(worker, indent=2) + "\n", encoding="utf-8")
    temp.replace(result)
    return proc.returncode, worker, log_text


def claude_session_usage(session_id: str, projects_dir: Path | None = None) -> tuple[dict[str, int], str | None]:
    usage: dict[str, int] = {}
    model = None
    project_dir = projects_dir or Path.home() / ".claude" / "projects"
    if not project_dir.is_dir():
        return usage, model
    for transcript in project_dir.glob(f"*/{session_id}.jsonl"):
        for line in transcript.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = entry.get("message") if isinstance(entry, dict) else None
            values = message.get("usage") if isinstance(message, dict) else None
            if not isinstance(values, dict):
                continue
            for target, key in (("input", "input_tokens"), ("output", "output_tokens"),
                                ("cache_read", "cache_read_input_tokens"),
                                ("cache_creation", "cache_creation_input_tokens")):
                if type(values.get(key)) is int:
                    usage[target] = usage.get(target, 0) + values[key]
            model = message.get("model") or model
    return usage, model


def record_usage(workspace: Path, feature: str, attempt: dict[str, Any], result: dict[str, Any], model: dict[str, Any]) -> None:
    ledger = workspace / ".adlc5" / feature / "memory/usage-ledger.jsonl"
    if ledger.is_file() and any((row := read_json_line(line)) and row.get("extra", {}).get("attempt_id") == attempt["attempt_id"]
                                for line in ledger.read_text(encoding="utf-8").splitlines()):
        return
    usage = result.get("usage") or {}
    if not usage:
        deviation(workspace / ".adlc5" / feature, "usage_unavailable", step=attempt["step"], attempt_id=attempt["attempt_id"])
    extra = {"attempt_id": attempt["attempt_id"], "requested_model_id": model.get("model_id") or "host-default",
             "observed_model_id": result.get("observed_model_id", result.get("model_id")), "config_sha256": attempt["config_sha256"],
             "host_session_id": result.get("host_session_id"),
             "usage_unavailable": not bool(usage), "wall_seconds": result.get("wall_seconds"),
             "host_reported_cost_usd": result.get("host_reported_cost_usd"), "calls": result.get("calls", 1)}
    args = [sys.executable, str(SCRIPTS / "memory/usage-ledger.py"), "record", "--feature", feature, "--workspace", str(workspace),
            "--source", "api" if usage else "self_reported", "--platform", str(attempt.get("host") or "codex"), "--model-id", str(result.get("model_id") or "unknown"),
            "--tier", str(model.get("tier") or "balanced"), "--step", attempt["step"], "--stage", attempt["step"].split("-", 1)[0],
            "--attempt", str(attempt["number"]), "--run-id", attempt["run_id"], "--node-id", attempt["step"], "--extra-json", json.dumps(extra)]
    for name, flag in (("input", "--input-tokens"), ("output", "--output-tokens"), ("thinking", "--thinking-tokens"),
                       ("cache_creation", "--cache-creation-tokens"), ("cache_read", "--cache-read-tokens")):
        if type(usage.get(name)) is int:
            args.extend((flag, str(usage[name])))
    subprocess.run(args, cwd=workspace, check=True)


def ingest(workspace: Path, feature: str, attempt: dict[str, Any], result: dict[str, Any], coder: dict[str, Any] | None) -> None:
    step = attempt["step"]
    if step == "tasks-1-stories":
        stories = (result.get("state_patch") or {}).get("stories")
        if not isinstance(stories, list):
            raise ValueError("tasks worker must return state_patch.stories")
        patch = workspace / ".adlc5" / feature / "pilot" / f"{attempt['attempt_id']}.patch.json"
        patch.write_text(json.dumps({"tasks": {"stories": stories}}), encoding="utf-8")
        call(workspace, "state", "set", "--feature", feature, "--file", str(patch))
        call(workspace, "anchors", "lock", "--feature", feature)
    elif step == "implement-1-build":
        story_id = result.get("story_id") or attempt.get("story")
        if not story_id:
            raise ValueError("build attempt has no story id")
        record = workspace / ".adlc5" / feature / "pilot" / f"{attempt['attempt_id']}.build.json"
        record.write_text(json.dumps({"story_ids": [story_id]}), encoding="utf-8")
        call(workspace, "evidence", "build", "--feature", feature, "--file", str(record))
    elif step == "implement-2-verify":
        check = call(workspace, "evidence", "check", "--feature", feature, check=False)
        if check.returncode:
            raise ReworkNeeded(check.stdout or check.stderr or "verification checks failed")
        review = result.get("review")
        if not isinstance(review, dict) or not coder or not result.get("session_id"):
            raise ValueError("verification requires a review plus recorded coder and verifier sessions")
        coders = coder if isinstance(coder, list) else [coder]
        sessions = [item.get("session_id") for item in coders if item.get("session_id")]
        models = [item.get("model_id") or "unknown" for item in coders if item.get("session_id")]
        if not sessions:
            raise ValueError("verification requires recorded coder sessions")
        review.update(coder_session_ids=sessions, verifier_session_id=result["session_id"],
                      coder_model_ids=models, verifier_model_id=result.get("model_id") or "unknown")
        if len(sessions) == 1:
            review.update(coder_session_id=sessions[0], coder_model_id=models[0])
        review.setdefault("disposition", "reject")
        review.setdefault("blocking_findings", ["review result did not declare blocking_findings"])
        review_file = workspace / ".adlc5" / feature / "pilot" / f"{attempt['attempt_id']}.review.json"
        review_file.write_text(json.dumps(review), encoding="utf-8")
        call(workspace, "evidence", "review", "--feature", feature, "--file", str(review_file))
    elif step == "implement-3-integrate":
        integration = (result.get("state_patch") or {}).get("integration")
        if integration != {"status": "completed"}:
            raise ValueError("integration worker must return state_patch.integration.status=completed")
        record = workspace / ".adlc5" / feature / "pilot" / f"{attempt['attempt_id']}.integration.json"
        record.write_text(json.dumps(integration), encoding="utf-8")
        call(workspace, "evidence", "integrate", "--feature", feature, "--file", str(record))


def check_gate(workspace: Path, feature: str, gate: str) -> bool:
    proc = subprocess.run([sys.executable, str(SCRIPTS / "check-gates.py"), "--feature", feature, "--gate", gate, "--workspace", str(workspace)],
                          cwd=workspace, text=True, capture_output=True, check=False)
    try:
        return proc.returncode == 0 and json.loads(proc.stdout).get("status") == "pass"
    except json.JSONDecodeError:
        return False


def record_checkpoint(path: Path, attempt: dict[str, Any], name: str, **fields: Any) -> None:
    append(path, {"attempt_id": attempt["attempt_id"], "checkpoint": name, "at": now(), **fields})


def close_attempt(path: Path, attempt: dict[str, Any], number: int, outcome: str, **fields: Any) -> None:
    record_checkpoint(path, attempt, "closed", number=number, outcome=outcome, step=attempt.get("step"),
                      story=attempt.get("story"), kind=attempt.get("kind", "work"), **fields)


def open_attempts(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in events if "step" in item and "start_commit" in item
            and not attempt_event(events, item["attempt_id"], "closed")]


def require_clean_recovery(workspace: Path, feature: str, attempt: dict[str, Any],
                           events: list[dict[str, Any]]) -> None:
    committed = attempt_event(events, attempt["attempt_id"], "worker_committed")
    expected = committed["commit"] if committed else attempt["start_commit"]
    if git(workspace, "rev-parse", "HEAD") != expected or checkout_dirty(workspace, feature):
        raise stop_for_recovery(workspace, {**attempt, "expected_commit": expected})


def quota_wait(events: list[dict[str, Any]], step: str, host: str) -> dict | None:
    for row in reversed(events):
        if row.get("checkpoint") != "quota_wait" or row.get("step") != step or row.get("host") != host:
            continue
        earliest = retry_time(row.get("earliest_retry_at"))
        if earliest and earliest > datetime.now(timezone.utc):
            return {"attempt_id": row["attempt_id"], "host": host, "wait_kind": "host_quota",
                    "earliest_retry_at": row["earliest_retry_at"]}
    return None


def result_digest(result: dict) -> str:
    return hashlib.sha256(json.dumps(result, sort_keys=True).encode("utf-8")).hexdigest()


def review_failure(step: str, passed: bool, result: dict) -> dict:
    review = result.get("review") if isinstance(result.get("review"), dict) else {}
    if step == "implement-2-verify" and not passed and (
        review.get("disposition") != "pass" or bool(review.get("blocking_findings"))
    ):
        return {"reason_code": "review_rejected", "rework": True,
                "findings": json.dumps(review.get("blocking_findings") or "review rejected")[:4000]}
    return {}


def require_recovered_source(workspace: Path, attempt: dict, result: dict,
                             events: list[dict[str, Any]], validated: dict) -> None:
    declared = result.get("changed_paths")
    committed = attempt_event(events, attempt["attempt_id"], "worker_committed")
    if declared == [] and not committed:
        return
    if (isinstance(declared, list) and declared and all(isinstance(name, str) for name in declared)
            and committed and validated.get("result_sha256")):
        commit = committed["commit"]
        parent = git(workspace, "rev-parse", f"{commit}^")
        changed = subprocess.run(["git", "-C", str(workspace), "diff-tree", "--no-commit-id", "--name-only",
                                  "-z", "--no-renames", "-r", commit], check=True, capture_output=True)
        files = set(os.fsdecode(changed.stdout).split("\0")) - {""}
        if parent == attempt["start_commit"] and files == set(declared):
            return
    raise RunnerStop("recovery_source_unverified", attempt["step"],
                     "Review the preserved result and committed source before accepting this attempt.",
                     attempt_id=attempt["attempt_id"])


def reopen_discarded_build(workspace: Path, feature: str, attempt: dict) -> None:
    if attempt["step"] != "implement-1-build" or not attempt.get("story"):
        return
    state = load_feature_state(workspace, feature) or {}
    if state.get("current_step") != attempt["step"]:
        return
    stories = (state.get("tasks") or {}).get("stories", [])
    story = next((entry for entry in stories if entry.get("id") == attempt["story"]), None)
    if not story or story.get("status") != "implementation_complete":
        return
    story["status"] = "pending"
    call(workspace, "state", "repair", "--feature", feature,
         "--patch", json.dumps({"tasks": {"stories": stories}}),
         "--reason", f"Discarded source from uncommitted worker attempt {attempt['attempt_id']}")


def recover(workspace: Path, feature: str, path: Path, events: list[dict[str, Any]]) -> None:
    for attempt in open_attempts(events):
        attempt_id = attempt["attempt_id"]
        require_clean_recovery(workspace, feature, attempt, events)
        result_path = workspace / ".adlc5" / feature / "pilot/results" / f"{attempt_id}.json"
        validated = attempt_event(events, attempt_id, "result_validated")
        ingested = attempt_event(events, attempt_id, "evidence_ingested")
        used = attempt_event(events, attempt_id, "usage_recorded")
        result = read_json(result_path)
        if not validated:
            close_attempt(path, attempt, attempt.get("number", 1), "fail", reason_code="interrupted_before_validation",
                          reason="interrupted before result validation")
            continue
        expected_result = validated.get("result_sha256")
        if (not isinstance(result, dict) or result.get("attempt_id") != attempt_id
                or expected_result and result_digest(result) != expected_result):
            raise RunnerStop("recovery_result_mismatch", attempt["step"],
                             "Review the attempt result and its validation receipt before resuming.",
                             attempt_id=attempt_id)
        declared = result.get("changed_paths")
        if (result.get("status") == "completed" and isinstance(declared, list) and declared
                and all(isinstance(name, str) for name in declared)
                and not attempt_event(events, attempt_id, "worker_committed")):
            if not used:
                record_usage(workspace, feature, attempt, result, {"model_id": attempt.get("requested_model_id"),
                                                                "tier": attempt.get("tier")})
                record_checkpoint(path, attempt, "usage_recorded")
            reopen_discarded_build(workspace, feature, attempt)
            close_attempt(path, attempt, attempt.get("number", 1), "fail",
                          reason_code="recovery_source_unverified",
                          reason="Declared worker source was discarded before commit")
            continue
        if not ingested and validated.get("result_fingerprint") and fingerprint(workspace, feature) != validated["result_fingerprint"]:
            raise RunnerStop("recovery_inputs_changed", attempt["step"],
                             "Review the changed inputs and validate the preserved attempt evidence.",
                             attempt_id=attempt_id)
        if result.get("status") == "needs_human":
            question = record_question(workspace, feature, attempt, result)
            if not used:
                record_usage(workspace, feature, attempt, result, {"model_id": attempt.get("requested_model_id"),
                                                                "tier": attempt.get("tier")})
                record_checkpoint(path, attempt, "usage_recorded")
            close_attempt(path, attempt, attempt.get("number", 1), "needs_human", reason_code=question["category"])
            continue
        require_recovered_source(workspace, attempt, result, events, validated)
        if not used:
            record_usage(workspace, feature, attempt, result, {"model_id": attempt.get("requested_model_id"),
                                                            "tier": attempt.get("tier")})
            record_checkpoint(path, attempt, "usage_recorded")
        if not ingested:
            try:
                if attempt.get("kind") != "rework":
                    coders = [row for row in events if row.get("outcome") == "pass" and row.get("session_id") and
                              (row.get("step") == "implement-1-build" or row.get("kind") == "rework")]
                    ingest(workspace, feature, attempt, result, coders)
            except ReworkNeeded as exc:
                close_attempt(path, attempt, attempt.get("number", 1), "fail", reason_code="rework_required",
                              rework=True, findings=str(exc)[:4000])
                call(workspace, "pilot", "--feature", feature, "--record-result", "fail", check=False)
                continue
            record_checkpoint(path, attempt, "evidence_ingested")
        passed = attempt.get("kind") == "rework" or check_gate(workspace, feature, attempt.get("gate", ""))
        if attempt.get("step") == "implement-1-build":
            passed = result.get("story_id", attempt.get("story")) == attempt.get("story")
        outcome = "pass" if passed else "fail"
        failure = review_failure(attempt["step"], passed, result)
        if not passed and not failure:
            failure = {"reason_code": "gate_failed", "blocker_fingerprint": fingerprint(workspace, feature)}
        close_attempt(path, attempt, attempt.get("number", 1), outcome,
                      session_id=result.get("session_id"), model_id=result.get("model_id"),
                      observed_model_id=result.get("observed_model_id"),
                      **failure)
        call(workspace, "pilot", "--feature", feature, "--record-result", outcome)


def record_question(workspace: Path, feature: str, attempt: dict[str, Any], result: dict[str, Any]) -> dict:
    feature_dir = workspace / ".adlc5" / feature
    current = read_json(feature_dir / "pilot/pending-question.json")
    if isinstance(current, dict):
        if current.get("id") != attempt["attempt_id"]:
            raise RuntimeError("a different question is already pending")
        return current
    question = pending_question(workspace, feature, result, attempt["attempt_id"], attempt["step"], attempt["host"])
    atomic_write_json(feature_dir / "pilot/pending-question.json", question)
    if question["denied_actions"]:
        deviation(feature_dir, "denied_action", step=attempt["step"], denied_actions=question["denied_actions"])
    return question


def finish_summary(workspace: Path, feature: str, status: str, branch: str, mode: str) -> None:
    state = load_feature_state(workspace, feature) or {}
    stories = (state.get("tasks") or {}).get("stories", [])
    checks = next((item for item in reversed(evidence_records(workspace, feature)) if item.get("kind") == "checks"), {})
    closed = journal(workspace / ".adlc5" / feature / "pilot/attempts.jsonl")
    repairs = sum(1 for item in closed if item.get("checkpoint") == "closed" and item.get("outcome") == "fail")
    summary = {"status": status, "branch": branch, "stories_delivered": sum(1 for item in stories if item.get("status") == "verified"),
               "checks_passed": sum(1 for item in checks.get("results", []) if item.get("status") == "pass"), "repairs": repairs,
               "pr": (((state.get("implement") or {}).get("pr") or {}).get("url"))}
    deviations_path = workspace / ".adlc5" / feature / "pilot/deviations.jsonl"
    deviations = journal(deviations_path) if deviations_path.is_file() else []
    summary["deviations"] = deviations
    if mode == "detailed":
        proc = subprocess.run([sys.executable, str(SCRIPTS / "memory/usage-ledger.py"), "summary", "--feature", feature,
                               "--workspace", str(workspace), "--format", "json"], capture_output=True, text=True)
        try:
            summary["usage"] = json.loads(proc.stdout) if proc.returncode == 0 else {"status": "unavailable"}
        except json.JSONDecodeError:
            summary["usage"] = {"status": "unavailable"}
    print((f"{status}: {feature}" + (f" — {summary['pr']}" if summary.get("pr") else "") +
           (f" ({len(deviations)} deviations)" if deviations else "")) if mode == "off" else json.dumps(summary, indent=2))


def report_bootstrap_block(workspace: Path, feature: str, result: dict[str, Any]) -> int:
    try:
        git_bootstrap.record(workspace, feature, result)
    except git_bootstrap.BootstrapBlocked as exc:
        result = exc.diagnostic
    print(json.dumps(result))
    return 1


def clear_runner_stop(path: Path) -> None:
    if not path.is_symlink():
        path.unlink(missing_ok=True)


def run(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    try:
        feature_dir = git_bootstrap.feature_path(workspace, args.feature)
    except git_bootstrap.BootstrapBlocked as exc:
        print(json.dumps(exc.diagnostic))
        return 1
    if not (feature_dir / "state.json").is_file():
        peer = feature_worktree(workspace, args.feature)
        if peer:
            print(json.dumps({"status": "redirected", "worktree": str(peer)}), file=sys.stderr)
            return run(argparse.Namespace(**{**vars(args), "workspace": str(peer)}))
        exc = git_bootstrap.BootstrapBlocked("feature_state_missing", feature_dir / "state.json",
                                             "Initialize this ADLC5 feature in the consumer workspace.")
        print(json.dumps(exc.diagnostic))
        return 1
    policies = load_policies(workspace, args.feature)
    lock = feature_dir / "pilot/runner.lock"
    try:
        acquire_lock(lock)
    except PermissionError:
        exc = git_bootstrap.BootstrapBlocked("state_unwritable", lock.parent,
                                             "Grant write access to the feature state directory and resume.")
        print(json.dumps(exc.diagnostic))
        return 1
    stop_path = feature_dir / "pilot/runner-stop.json"
    try:
        journal_path = feature_dir / "pilot/attempts.jsonl"
        events = journal(journal_path)
        for attempt in open_attempts(events):
            require_clean_recovery(workspace, args.feature, attempt, events)
        config = merge_model_config(ROOT, workspace)
        profiles = config.get("platform_profiles") if isinstance(config.get("platform_profiles"), dict) else {}
        host = str(args.host or config.get("default_host") or "")
        if not host:
            raise RuntimeError("no host selected; pass --host or set default_host with 'adlc5 setup models'")
        if host not in hosts.HOSTS:
            raise RuntimeError(f"unsupported host: {host}")
        options = {}
        if args.host:
            options['default_host'] = args.host
        if args.mode:
            options['platform_modes'] = {host: args.mode}
        effective_config(workspace, options)  # Reject explicit attempts to bypass machine constraints.
        profile = profiles.get(host) if isinstance(profiles.get(host), dict) else {}
        configured = any(isinstance(profile.get(tier), dict) and profile[tier].get("model")
                         for tier in ("reasoning", "balanced", "execution"))
        if not configured and not args.accept_defaults:
            raise RuntimeError("model setup is missing; run 'adlc5 setup models' or pass --accept-defaults")
        defaults = config.get("defaults") if isinstance(config.get("defaults"), dict) else {}
        current_interaction_mode = interaction_mode(config, policies)
        container_declared = hosts.in_declared_container(workspace)
        configured_modes = config.get("platform_modes") if isinstance(config.get("platform_modes"), dict) else {}
        mode = args.mode or configured_modes.get(host) or ("confined" if host == "hermes" and container_declared else hosts.MODES[host][0])
        if mode == "attended" and not sys.stdin.isatty():
            raise RuntimeError("attended mode requires a terminal; start adlc5 run from a terminal")
        if current_interaction_mode == "autonomous" and mode == "attended" and not container_declared:
            raise RuntimeError("autonomous interaction cannot use attended mode outside a declared container")
        if host == "hermes" and mode != "attended" and not container_declared:
            raise RuntimeError("Hermes unattended mode requires .adlc5/external-sandbox.json declared by the user as a container")
        if mode not in hosts.AVAILABLE_MODES[host]:
            raise RuntimeError(f"{host} does not support {mode} mode")
        state = load_feature_state(workspace, args.feature) or {}
        opening = state.get("current_step") == git_bootstrap.STEP
        recorded = state.get("git") or {}
        try:
            if opening and recorded.get("isolation") in {"branch", "worktree", "current", "skip", "skipped", "waived"}:
                result = git_bootstrap.evaluate(workspace, args.feature)
                if result["status"] == "blocked":
                    return report_bootstrap_block(workspace, args.feature, result)
                if result["evidence"].get("isolation") == "waived":
                    raise git_bootstrap.BootstrapBlocked("git_required_by_runner", workspace,
                        "Continue with in-agent Specify after opting out of Git isolation.")
                if checkout_dirty(workspace, args.feature):
                    raise git_bootstrap.BootstrapBlocked("dirty_checkout", workspace,
                        "Preserve or commit existing changes before running on this feature branch.")
                branch, isolation = recorded.get("branch_name"), recorded["isolation"]
            else:
                if opening:
                    binding = git_bootstrap.git_binding(workspace)
                    git_bootstrap.check_binding(workspace, state, binding)
                isolated = ensure_isolation(workspace, args.feature, feature_dir, args)
                if isinstance(isolated, int):
                    return isolated
                branch, isolation = isolated
        except git_bootstrap.BootstrapBlocked as exc:
            return report_bootstrap_block(workspace, args.feature, exc.diagnostic)
        state = load_feature_state(workspace, args.feature) or {}
        if state.get("stage_status", {}).get("implement") == "completed":
            finish_summary(workspace, args.feature, "completed", branch, args.summary or "brief")
            return 0
        wait = quota_wait(events, state.get("current_step"), host)
        if wait:
            raise RunnerStop("host_quota", state.get("current_step"),
                             "Check the host quota and resume when the host permits.", **wait)
        previous_stop = read_json(stop_path, {}) if not stop_path.is_symlink() else {}
        if (isinstance(previous_stop, dict) and previous_stop.get("condition") == "host_quota"
                and previous_stop.get("step") == state.get("current_step")
                and previous_stop.get("host") in (None, host)):
            earliest = retry_time(previous_stop.get("earliest_retry_at"))
            if earliest and earliest > datetime.now(timezone.utc):
                print(json.dumps(previous_stop, indent=2))
                return 1
        recover(workspace, args.feature, journal_path, events)
        pending = resume_question(workspace, args.feature)
        if pending and not pending.get("answer"):
            print(json.dumps({"status": "needs_human", **pending}, indent=2))
            return 10
        if pending and pending.get("denied_actions") and str(pending.get("answer", "")).lower() not in ("allow", "yes", "approve"):
            print(json.dumps({"status": "halted", "reason": "user denied the host permission request; no retry was started",
                              "question_id": pending.get("id")}, indent=2))
            return 1
        run_id = str(uuid.uuid4())
        summary_mode = args.summary or defaults.get("summary", "brief")
        config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        config_path = feature_dir / "pilot/run-config.json"
        config_path.write_text(json.dumps({"host": host, "mode": mode, "preset": (config.get("model_routing") or {}).get("strategy", "balanced"),
            "summary": summary_mode, "effective_config": config, "sha256": config_hash, "isolation": isolation}, indent=2) + "\n")
        print(json.dumps({"status": "starting", "host": host, "mode": mode, "summary": summary_mode, "isolation": isolation,
                          "tiers": {tier: profile.get(tier) or "host default" for tier in ("reasoning", "balanced", "execution")},
                          "config_layers": [source for source, path in config_paths(workspace) if path.is_file()]}), file=sys.stderr)
        while True:
            nav = subprocess.run([BASH, str(SCRIPTS / "pilot-autopilot.sh"), "--feature", args.feature, "--workspace", str(workspace)],
                                 cwd=workspace, capture_output=True, text=True)
            try:
                action = json.loads(nav.stdout)
            except json.JSONDecodeError as exc:
                raise RuntimeError(nav.stderr.strip() or f"navigator returned invalid JSON: {exc}")
            if action.get("action") == "done":
                clear_runner_stop(stop_path)
                state = load_feature_state(workspace, args.feature) or {}
                if state.get("stage_status", {}).get("implement") != "completed":
                    call(workspace, "transition", "completed", "--feature", args.feature)
                finish_summary(workspace, args.feature, "completed", branch, summary_mode)
                return 0
            if action.get("action") == "halt":
                print(json.dumps(action.get("bootstrap") or {"status": "halted", "reason": action.get("stop_reason")}, indent=2))
                return 1
            if action.get("action") == "advance":
                if str(action.get("phase", "")).startswith("specify-") and str(action.get("transition_target", "")).startswith("plan-"):
                    enforce_scope_block(workspace, args.feature)
                call(workspace, "transition", str(action.get("transition_target") or action.get("suggested_next")), "--feature", args.feature)
                clear_runner_stop(stop_path)
                continue
            if action.get("action") != "spawn":
                raise RuntimeError(f"unsupported navigator action: {action.get('action')}")
            step = str(action.get("phase") or "")
            if step == "implement-5-pr":
                clear_runner_stop(stop_path)
                # PR review and scoped approval are human-owned: hand off instead of failing the run.
                print(json.dumps({"status": "handoff", "step": step, "branch": branch,
                                  "next": "review and approve the PR with the in-agent PR workflow, then run again"}, indent=2))
                return 10
            history = journal(journal_path)
            last_closed = next((row for row in reversed(history)
                                if row.get("step") == step and row.get("checkpoint") == "closed"), {})
            if last_closed.get("blocker_fingerprint") and last_closed["blocker_fingerprint"] == fingerprint(workspace, args.feature):
                raise RunnerStop("gate_failed", step, "Repair the reported gate inputs before resuming.",
                                 attempt_id=last_closed["attempt_id"], gate=action.get("gate"))
            budget = int(((policies.get("autopilot") or {}).get("retry_budgets") or {}).get("verification_per_story") or 3)
            findings = rework_findings(history, budget) if step == "implement-2-verify" else None
            # A rejected review goes back to a coder on the execution tier, then to a fresh review.
            tier = "execution" if findings else str(action.get("model_tier_resolved") or "balanced")
            model = hosts.resolve_model(ROOT, workspace, args.feature, tier, host)
            model["tier"] = tier
            if findings:
                deviation(feature_dir, "rework", step=step, findings=findings[:500])
            if step == "implement-2-verify" and not findings and model.get("verifier_different_model"):
                coder_models = {item.get("model_id") for item in journal(journal_path)
                                if item.get("step") == "implement-1-build" and item.get("outcome") == "pass" and item.get("model_id")}
                candidates = [model] + [hosts.resolve_model(ROOT, workspace, args.feature, candidate, host)
                                        for candidate in ("reasoning", "balanced", "execution") if candidate != tier]
                model = next((candidate_model for candidate_model in candidates
                              if candidate_model.get("model_id") not in coder_models
                              and candidate_model.get("model_id", "host default").lower() not in ("host default", "inherit", "")), None)
                if not model:
                    raise RuntimeError("verification requires a configured model different from every implementer model")
                tier = model.get("tier") or tier
                model["tier"] = tier
            brief, story = stage_brief(workspace, args.feature, step, action.get("gates"), findings)
            attempt_id = str(uuid.uuid4())
            prompt = worker_prompt(workspace, args.feature, {"attempt_id": attempt_id, "step": step}, brief, host, mode)
            estimated_tokens = (len(prompt.encode("utf-8")) + 3) // 4
            pack_budgets = config.get("pack_budget_tokens") or {}
            pack_budget = pack_budgets.get(tier, 30000 if tier == "execution" else 60000) if isinstance(pack_budgets, dict) else None
            if type(pack_budget) is not int or pack_budget < 1:
                raise RunnerStop("invalid_pack_budget", step, "Set a positive worker prompt budget.",
                                 tier=tier, budget=pack_budget)
            if estimated_tokens > pack_budget:
                raise RunnerStop("pack_over_budget", step,
                    "Narrow the step context or review the configured prompt budget, then resume.",
                    story=story, tier=tier, estimated_tokens=estimated_tokens, budget=pack_budget)
            attempts = [row for row in history if row.get("checkpoint") is None and "start_commit" in row]
            kind = "rework" if findings else "work"
            same_step = [row for row in attempts if (row.get("step"), row.get("story"), row.get("kind", "work"))
                         == (step, story, kind)]
            attempt_no = len(same_step) + 1
            pilot_policy = policies.get("autopilot") or {}
            limits = pilot_policy.get("retry_budgets") or {}
            feature_limit = int(pilot_policy.get("max_iterations", 200))
            step_limit = int(limits.get("worker_attempts_per_step", max(5, budget + 1)))
            if attempt_no > step_limit or len(attempts) >= feature_limit:
                raise RunnerStop("worker_budget_exhausted", step,
                    "Review the attempt history and configured execution limits before resuming.",
                    story=story, step_attempts=len(same_step), step_limit=step_limit,
                    feature_attempts=len(attempts), feature_limit=feature_limit)
            if checkout_dirty(workspace, args.feature):
                raise RunnerStop("workspace_dirty", step,
                    "Review and preserve local edits, then resume from a clean feature checkout.",
                    workspace=str(workspace))
            remaining = worker_deadline(workspace, args.feature, policies)
            if remaining <= 0:
                raise RunnerStop("worker_time_budget_exhausted", step,
                    "Review the feature wall-clock budget before resuming.")
            if str(model.get("model_id") or "host default").lower() in ("host default", "host-default", "inherit", "unknown", ""):
                if pilot_policy.get("require_explicit_worker_model") is True:
                    raise RunnerStop("worker_model_unresolved", step,
                        "Configure an explicit model for this worker tier before resuming.", tier=tier, host=host)
                deviation(feature_dir, "host_default_model", step=step, tier=tier)
            start_commit = git(workspace, "rev-parse", "HEAD")
            entry = {"attempt_id": attempt_id, "run_id": run_id, "step": step, "story": story,
                     "number": attempt_no, "pack_sha256": hashlib.sha256(brief.encode()).hexdigest(), "config_sha256": config_hash,
                     "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "prompt_estimated_tokens": estimated_tokens,
                     "start_commit": start_commit, "kernel_fingerprint": fingerprint(workspace, args.feature),
                     "requested_model_id": model.get("model_id"), "tier": tier, "gate": action.get("gate"), "at": now(),
                     "host": host, "mode": mode, "kind": kind}
            append(journal_path, entry)
            record_checkpoint(journal_path, entry, "launched")
            clear_runner_stop(stop_path)
            try:
                result: dict[str, Any] = {}
                timeout = min(args.timeout, remaining)
                rc, result, _log = run_worker(workspace, args.feature, entry, prompt, model, timeout, host, mode,
                                              current_interaction_mode)
                if rc or result.get("status") == "failed":
                    raise RuntimeError(result.get("error") or f"worker exited {rc}")
                atomic_write_json(feature_dir / "pilot/results" / f"{attempt_id}.json", result)
                record_checkpoint(journal_path, entry, "result_validated", session_id=result.get("session_id"),
                                  model_id=result.get("model_id"), result_sha256=result_digest(result),
                                  result_fingerprint=fingerprint(workspace, args.feature))
                record_usage(workspace, args.feature, entry, result, model)
                record_checkpoint(journal_path, entry, "usage_recorded")
                if result.get("status") == "needs_human":
                    question = record_question(workspace, args.feature, entry, result)
                    close_attempt(journal_path, entry, attempt_no, "needs_human", reason_code=question["category"],
                                  observed_model_id=result.get("observed_model_id"))
                    print(json.dumps({"status": "needs_human", **question}, indent=2))
                    return 10
                worker_change_paths(workspace, args.feature, entry, result)
                # Everyone who wrote the code under review: build workers and rework workers.
                coders = [item for item in journal(journal_path) if item.get("outcome") == "pass" and item.get("session_id") and
                          (item.get("step") == "implement-1-build" and item.get("story") or item.get("kind") == "rework")]
                coder = coders if step == "implement-2-verify" else next((item for item in reversed(coders) if item.get("story") == entry.get("story")), None)
                if not findings:
                    ingest(workspace, args.feature, entry, result, coder)
                record_checkpoint(journal_path, entry, "evidence_ingested")
                passed = bool(findings) or check_gate(workspace, args.feature, str(action.get("gate") or ""))
                if step == "implement-1-build":
                    passed = result.get("story_id", entry.get("story")) == entry.get("story")
                if passed:
                    commit_worker_changes(workspace, args.feature, journal_path, entry, result)
                outcome = "pass" if passed else "fail"
                failure = review_failure(step, passed, result)
                rejected = bool(failure)
                if not passed and not rejected:
                    failure = {"reason_code": "gate_failed", "blocker_fingerprint": fingerprint(workspace, args.feature)}
                close_attempt(journal_path, entry, attempt_no, outcome, session_id=result.get("session_id"),
                              model_id=result.get("model_id"), observed_model_id=result.get("observed_model_id"),
                              **failure)
                call(workspace, "pilot", "--feature", args.feature, "--record-result", outcome)
            except KeyboardInterrupt:
                raise RunnerStop("interrupted", step, "Run the same feature again to recover this attempt.",
                                 attempt_id=attempt_id)
            except RunnerStop:
                raise
            except Exception as exc:
                recorded = journal(journal_path)
                if not attempt_event(recorded, attempt_id, "usage_recorded"):
                    record_usage(workspace, args.feature, entry, result, model)
                    record_checkpoint(journal_path, entry, "usage_recorded")
                condition = result.get("failure_kind") if isinstance(result.get("failure_kind"), str) else None
                if condition not in {"interrupted", "worker_timeout", "invalid_worker_result", "permission_required", "host_failed", "host_quota"}:
                    condition = "rework_required" if isinstance(exc, ReworkNeeded) else "worker_failed"
                if condition == "host_quota":
                    record_checkpoint(journal_path, entry, "quota_wait", step=step, host=host,
                                      earliest_retry_at=result.get("earliest_retry_at"))
                # A matching HEAD alone cannot establish ownership of index or worktree edits.
                require_clean_recovery(workspace, args.feature, entry, recorded)
                close_attempt(journal_path, entry, attempt_no, "fail", reason_code=condition, reason=str(exc)[:4000],
                              observed_model_id=result.get("observed_model_id"),
                              **({"rework": True, "findings": str(exc)[:4000]} if isinstance(exc, ReworkNeeded) else {}))
                if condition == "host_quota":
                    raise RunnerStop(condition, step, "Check the host quota and resume when the host permits.",
                                     attempt_id=attempt_id, host=host, wait_kind="host_quota",
                                     earliest_retry_at=result.get("earliest_retry_at"))
                call(workspace, "pilot", "--feature", args.feature, "--record-result", "fail", check=False)
                if isinstance(exc, ReworkNeeded):
                    continue
                raise RunnerStop(condition, step, "Review the worker result, then resume after addressing the failure.",
                                 attempt_id=attempt_id)
            if not passed and not rejected:
                raise RunnerStop("gate_failed", step, "Review the gate failures and repair the reported evidence before resuming.",
                                 attempt_id=attempt_id, gate=action.get("gate"))
    except RunnerStop as exc:
        if exc.outcome["condition"] == "recovery_required":
            quota = attempt_event(journal(journal_path), exc.outcome["attempt_id"], "quota_wait")
            if quota:
                exc.outcome.update(wait_kind="host_quota", host=quota["host"],
                                   earliest_retry_at=quota.get("earliest_retry_at"))
        if not stop_path.is_symlink():
            atomic_write_json(stop_path, exc.outcome)
        print(json.dumps(exc.outcome, indent=2))
        return 1
    finally:
        lock.unlink(missing_ok=True)


def worker_deadline(workspace: Path, feature: str, policies: dict[str, Any] | None = None) -> int:
    meta = read_json(workspace / ".adlc5" / feature / "pilot/meta.json", {}) or {}
    try:
        started = datetime.fromisoformat(str(meta["started_at"]).replace("Z", "+00:00")).timestamp()
    except (KeyError, ValueError, TypeError):
        return 3600
    # Same cap and default as pilot-check-kill-switch.sh.
    try:
        cap = int(((policies or {}).get("autopilot") or {}).get("wall_clock_cap_minutes") or 360)
    except (TypeError, ValueError):
        cap = 360
    return int(started + cap * 60 - time.time())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", required=True)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--host", choices=hosts.HOSTS, default=None)
    parser.add_argument("--mode", choices=("confined", "allowlist", "attended"), default=None)
    parser.add_argument("--summary", choices=("off", "brief", "detailed"), default=None)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--accept-defaults", action="store_true")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        return run(args)
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
