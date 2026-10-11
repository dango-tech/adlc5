#!/usr/bin/env python3
"""Run ADLC5's navigator with supervised agent workers."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
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
sys.path.insert(0, str(SCRIPTS))
from runner import hosts  # noqa: E402
from lib.completion_evidence import fingerprint, records as evidence_records  # noqa: E402
from lib.model_routing import load_yaml_file, merge_model_config  # noqa: E402
from lib.policies_load import CANONICAL_STEPS, load_policies, next_step_for_profile, profile_name, step_enabled  # noqa: E402
from lib.state_v2 import load_feature_state  # noqa: E402


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def call(workspace: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run([str(SCRIPTS / "adlc5"), *args, "--workspace", str(workspace)],
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
    return [item for line in path.read_text(encoding="utf-8").splitlines() if (item := read_json_line(line))]


def read_json_line(line: str) -> dict[str, Any] | None:
    try:
        item = json.loads(line)
        return item if isinstance(item, dict) else None
    except json.JSONDecodeError:
        return None


def acquire_lock(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"pid": os.getpid(), "started_at": now()}
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(payload, stream)
                stream.write("\n")
            return
        except FileExistsError:
            owner = read_json(path)
            if not isinstance(owner, dict) or not isinstance(owner.get("pid"), int):
                raise RuntimeError(f"invalid run lock at {path}; inspect and remove it manually")
            try:
                os.kill(owner["pid"], 0)
            except ProcessLookupError:
                path.unlink(missing_ok=True)
                continue
            except PermissionError:
                pass
            raise RuntimeError(f"feature is locked by pid {owner['pid']}, started {owner.get('started_at', 'unknown')}")


def ensure_isolation(workspace: Path, feature: str, feature_dir: Path, args: argparse.Namespace) -> tuple[str, str] | int:
    branch_prefix = "feat"
    # git_branch_prefix is retained in repository config independently of model setup.
    from lib.config_layers import config_paths
    for _source, path in config_paths(workspace):
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("git_branch_prefix:"):
                    branch_prefix = line.split(":", 1)[1].strip().strip("\"'") or branch_prefix
    branch = f"{branch_prefix}/{feature}"
    dirty = bool(git(workspace, "status", "--porcelain", "--untracked-files=all"))
    if dirty:
        state = load_feature_state(workspace, feature) or {}
        recorded_path = ((state.get("git") or {}).get("worktree_path"))
        events_path = feature_dir / "pilot/attempts.jsonl"
        events = journal(events_path) if events_path.is_file() else []
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
                raise RuntimeError("runner requires a clean feature branch; preserve or commit existing changes before running")
            base = git(workspace, "rev-parse", "HEAD")
            shared = Path(git(workspace, "rev-parse", "--git-common-dir"))
            if not shared.is_absolute():
                shared = (workspace / shared).resolve()
            target = shared / "adlc5-worktrees" / feature
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise RuntimeError(f"ADLC5 worktree target already exists: {target}")
            if subprocess.run(["git", "-C", str(workspace), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"]).returncode == 0:
                raise RuntimeError(f"feature branch {branch} already exists; attach a worktree for that branch and resume there")
            subprocess.run(["git", "-C", str(workspace), "worktree", "add", "-b", branch, str(target), base], check=True)
            target_feature = target / ".adlc5" / feature
            target_feature.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(feature_dir, target_feature, dirs_exist_ok=True, ignore=shutil.ignore_patterns("runner.lock"))
            # State changes are validated through the canonical kernel command.
            patch_file = target_feature / "pilot/runner-isolation.json"
            patch_file.write_text(json.dumps({"git": {"isolation": "worktree", "branch_name": branch,
                "base_branch": base, "worktree_path": str(target)}}), encoding="utf-8")
            saved = call(target, "state", "set", "--feature", feature, "--file", str(patch_file), check=False)
            patch_file.unlink(missing_ok=True)
            if saved.returncode:
                subprocess.run(["git", "-C", str(workspace), "worktree", "remove", "--force", str(target)], check=False)
                raise RuntimeError(saved.stderr.strip() or saved.stdout.strip() or "could not transfer feature state to runner worktree")
            return run(argparse.Namespace(**{**vars(args), "workspace": str(target)}))
        closed = attempt_event(events, resumable_attempt["attempt_id"], "closed")
        has_ingested_result = bool(closed and closed.get("outcome") == "fail" and
                                   attempt_event(events, resumable_attempt["attempt_id"], "evidence_ingested"))
        if not has_ingested_result:
            subprocess.run(["git", "-C", str(workspace), "reset", "--hard", resumable_attempt["start_commit"]], check=True)
            subprocess.run(["git", "-C", str(workspace), "clean", "-fd"], check=True)
    common = Path(git(workspace, "rev-parse", "--git-common-dir"))
    if not common.is_absolute():
        common = (workspace / common).resolve()
    gitdir = Path(git(workspace, "rev-parse", "--absolute-git-dir"))
    linked = gitdir.resolve() != common.resolve()
    current = git(workspace, "branch", "--show-current")
    if current != branch:
        if linked and current:
            raise RuntimeError(f"linked worktree is already on {current}; refusing to switch host-owned worktree")
        if current and current not in ("main", "master"):
            raise RuntimeError(f"runner is on branch {current}; use a host-created worktree for {branch}")
        exists = subprocess.run(["git", "-C", str(workspace), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"]).returncode == 0
        subprocess.run(["git", "-C", str(workspace), "switch", branch] if exists else
                       ["git", "-C", str(workspace), "switch", "-c", branch], check=True)
    state = load_feature_state(workspace, feature) or {}
    saved = call(workspace, "state", "set", "--feature", feature, "--patch", json.dumps({"git": {
        "isolation": "worktree" if linked else "branch", "branch_name": branch,
        "base_branch": state.get("git", {}).get("base_branch") or git(workspace, "rev-parse", "HEAD"),
        "worktree_path": str(workspace),
    }}), check=False)
    if saved.returncode:
        raise RuntimeError(saved.stderr.strip() or saved.stdout.strip() or "failed to record git isolation")
    return branch, "worktree" if linked else "branch"


def stage_brief(workspace: Path, feature: str, step: str, gates: Any) -> tuple[str, str | None]:
    state = load_feature_state(workspace, feature) or {}
    stage = str(state.get("current_stage", "specify"))
    skill = {"specify": "specify", "plan": "plan", "tasks": "tasks", "implement": "implement"}.get(stage, stage)
    story = None
    if step in ("implement-1-build", "implement-2-verify"):
        stories = (state.get("tasks") or {}).get("stories", [])
        story = next((s.get("id") for s in stories if step.endswith("build") and s.get("type") != "integration" and s.get("status") not in ("implementation_complete", "verified")), None)
        targets = [story] if story else ([s.get("id") for s in stories if s.get("type") != "integration" and s.get("status") in ("implementation_complete", "verified")] if step.endswith("verify") else [])
        packs = []
        for story_id in targets:
            proc = subprocess.run([str(SCRIPTS / "memory/generate-pack.sh"), "--feature", feature,
                                   "--story-id", str(story_id), "--persona", "coder" if step.endswith("build") else "tester",
                                   "--workspace", str(workspace)], cwd=workspace, capture_output=True, text=True)
            if proc.returncode:
                raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"context pack failed for {story_id}")
            packs.append((workspace / json.loads(proc.stdout)["pack"]).read_text(encoding="utf-8"))
        if packs:
            return "\n\n---\n\n".join(packs) + "\n\nGate feedback:\n" + json.dumps(gates, indent=2), story
    paths = sorted((ROOT / "skills" / skill / "phases").glob("*.md")) or [ROOT / "skills" / skill / "SKILL.md"]
    chunks = [f"## {path.name}\n\n{path.read_text(encoding='utf-8')}" for path in paths if path.is_file()]
    answers = workspace / ".adlc5" / feature / "pilot/answers.jsonl"
    answer_lines = answers.read_text(encoding="utf-8") if answers.is_file() else ""
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


def run_worker(workspace: Path, feature: str, attempt: dict[str, Any], brief: str,
               model: dict[str, Any], timeout: int, host: str, mode: str,
               interaction_mode: str) -> tuple[int, dict[str, Any], str]:
    result_dir = workspace / ".adlc5" / feature / "pilot/results"
    result_dir.mkdir(parents=True, exist_ok=True)
    attempt_id = attempt["attempt_id"]
    schema, last, result = (result_dir / f"{attempt_id}.{suffix}" for suffix in ("schema.json", "last-message.json", "json"))
    schema.write_text(json.dumps({"type": "object", "required": ["attempt_id", "status", "summary"],
        "properties": {"attempt_id": {"const": attempt_id}, "status": {"enum": ["completed", "needs_human", "failed"]},
                       "summary": {"type": "string"}, "question": {"type": "string"},
                       "story_id": {"type": "string"}, "state_patch": {"type": "object"},
                       "review": {"type": "object"}}, "additionalProperties": True}, indent=2))
    result_prompt = ("You are an ADLC5 worker. Do only the current step. Do not run transitions, change lifecycle state, "
              "commit, push, create worktrees, or perform the next step. Write only in the workspace. Return JSON "
              f"matching the supplied schema with attempt_id {attempt_id}. For a human decision return needs_human and a question.\n\n"
              f"Feature: {feature}\nStep: {attempt['step']}\n\n{brief}")
    prompt = result_prompt
    if mode == "attended" or host == "hermes":
        prompt += (f"\n\nWhen finished, write the final JSON object to {last}. Include attempt_id {attempt_id}, "
                   "status, summary, and any required story_id, state_patch, or review fields. Do not exit until that file is written. "
                   "Then tell the user the result file is ready so they can exit the host CLI and return control to the runner.")
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
                switch = subprocess.run([str(SCRIPTS / "pilot-check-kill-switch.sh"), "--feature", feature,
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
    if mode == "attended" or host == "hermes":
        if not last.is_file():
            return proc.returncode or 1, {"error": "worker exited without writing the attempt result file"}, log_text
    if events.get("denied_actions") and interaction_mode == "hitl":
        denied = events["denied_actions"]
        question = "The worker was denied: " + json.dumps(denied, ensure_ascii=False) + ". Reply 'allow' to add its command to this feature allowlist, or 'deny'."
        return 0, {"status": "needs_human", "attempt_id": attempt_id, "summary": "permission approval required",
                   "question": question, "denied_actions": denied, "usage": events.get("usage", {}),
                   "model_id": events.get("model_id"), "host_reported_cost_usd": events.get("host_reported_cost_usd")}, log_text
    if events.get("is_error") or events.get("denied_actions"):
        return proc.returncode or 1, {"error": "host reported an error or denied action", **events}, log_text
    if mode != "attended" and host != "hermes":
        try:
            raw_result = events.get("text") or "{}"
            result_data = raw_result if isinstance(raw_result, dict) else json.loads(raw_result)
            if result_data.get("attempt_id") != attempt_id:
                raise ValueError("structured result did not match the active attempt; host must return the schema object")
            last.write_text(json.dumps(result_data), encoding="utf-8")
        except (json.JSONDecodeError, ValueError, AttributeError, TypeError) as exc:
            return proc.returncode or 1, {"error": f"invalid {host} worker result: {exc}"}, log_text
    if not last.is_file():
        return (124 if timed_out else 130 if stopped else proc.returncode or 1), {"error": "missing result file"}, log_text
    try:
        worker = json.loads(last.read_text(encoding="utf-8"))
        if not isinstance(worker, dict) or worker.get("attempt_id") != attempt_id or worker.get("status") not in ("completed", "needs_human", "failed"):
            raise ValueError("result identity or status mismatch")
    except (ValueError, json.JSONDecodeError) as exc:
        return (proc.returncode or 1), {"error": f"invalid result: {exc}"}, log_text
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
        if events.get("is_error"):
            return proc.returncode or 1, {"error": "Hermes usage report indicates an incomplete or failed run", **events}, log_text
    host_session_id = events.get("session_id")
    if host == "cursor" and session_file.is_file():
        session_record = read_json(session_file, {})
        if isinstance(session_record, dict) and session_record.get("attempt_id") == attempt_id:
            host_session_id = session_record.get("session_id")
    if mode == "attended" and host == "claude":
        host_session_id = attempt_id
        transcript_usage, transcript_model = claude_session_usage(host_session_id)
        events["usage"] = transcript_usage
        events["model_id"] = transcript_model or model.get("model_id")
    # The attempt id is the runner-owned identity when a host exposes no session id.
    worker.update(session_id=host_session_id or attempt_id, host_session_id=host_session_id,
                  model_id=events.get("model_id") or model.get("model_id") or "unknown",
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
    extra = {"attempt_id": attempt["attempt_id"], "requested_model_id": model.get("model_id") or "host-default",
             "observed_model_id": result.get("model_id"), "config_sha256": attempt["config_sha256"],
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
            raise RuntimeError(check.stdout or check.stderr or "verification checks failed")
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
    proc = subprocess.run([str(SCRIPTS / "check-gates.py"), "--feature", feature, "--gate", gate, "--workspace", str(workspace)],
                          cwd=workspace, text=True, capture_output=True, check=False)
    try:
        return proc.returncode == 0 and json.loads(proc.stdout).get("status") == "pass"
    except json.JSONDecodeError:
        return False


def record_checkpoint(path: Path, attempt: dict[str, Any], name: str, **fields: Any) -> None:
    append(path, {"attempt_id": attempt["attempt_id"], "checkpoint": name, "at": now(), **fields})


def close_attempt(path: Path, attempt: dict[str, Any], number: int, outcome: str, **fields: Any) -> None:
    record_checkpoint(path, attempt, "closed", number=number, outcome=outcome, **fields)


def recover(workspace: Path, feature: str, path: Path, events: list[dict[str, Any]], run_id: str) -> None:
    attempts = {item["attempt_id"]: item for item in events if "step" in item and "start_commit" in item}
    for attempt_id, attempt in attempts.items():
        if attempt_event(events, attempt_id, "closed"):
            continue
        result_path = workspace / ".adlc5" / feature / "pilot/results" / f"{attempt_id}.json"
        validated = attempt_event(events, attempt_id, "result_validated")
        ingested = attempt_event(events, attempt_id, "evidence_ingested")
        used = attempt_event(events, attempt_id, "usage_recorded")
        result = read_json(result_path)
        if validated and result and not ingested:
            coder = [row for row in events if row.get("step") == "implement-1-build" and row.get("outcome") == "pass" and row.get("session_id")]
            ingest(workspace, feature, attempt, result, coder)
            record_checkpoint(path, attempt, "evidence_ingested")
            ingested = {"checkpoint": "evidence_ingested"}
        if ingested and result and not used:
            record_usage(workspace, feature, attempt, result, {"model_id": result.get("model_id"), "tier": attempt.get("tier")})
            record_checkpoint(path, attempt, "usage_recorded")
            used = {"checkpoint": "usage_recorded"}
        if used:
            passed = check_gate(workspace, feature, attempt.get("gate", ""))
            if attempt.get("step") == "implement-1-build" and result:
                passed = result.get("story_id", attempt.get("story")) == attempt.get("story")
            if passed:
                git(workspace, "add", "-A")
                if subprocess.run(["git", "-C", str(workspace), "diff", "--cached", "--quiet"]).returncode == 1:
                    subprocess.run(["git", "-C", str(workspace), "commit", "-m", f"feat({feature}): recover {attempt['step']}"] , check=True)
                close_attempt(path, attempt, attempt.get("number", 1), "pass", session_id=result.get("session_id"), model_id=result.get("model_id"))
                call(workspace, "pilot", "--feature", feature, "--record-result", "pass")
            else:
                close_attempt(path, attempt, attempt.get("number", 1), "fail", reason="recovered gate failure")
                call(workspace, "pilot", "--feature", feature, "--record-result", "fail")
        else:
            if git(workspace, "rev-parse", "HEAD") != attempt.get("start_commit"):
                raise RuntimeError(f"cannot safely recover attempt {attempt_id}: branch moved from its starting commit")
            subprocess.run(["git", "-C", str(workspace), "reset", "--hard", attempt["start_commit"]], check=True)
            subprocess.run(["git", "-C", str(workspace), "clean", "-fd"], check=True)
            close_attempt(path, attempt, attempt.get("number", 1), "fail", reason="interrupted before evidence ingestion")
            call(workspace, "pilot", "--feature", feature, "--record-result", "fail")


def finish_summary(workspace: Path, feature: str, status: str, branch: str, mode: str) -> None:
    state = load_feature_state(workspace, feature) or {}
    stories = (state.get("tasks") or {}).get("stories", [])
    checks = next((item for item in reversed(evidence_records(workspace, feature)) if item.get("kind") == "checks"), {})
    closed = journal(workspace / ".adlc5" / feature / "pilot/attempts.jsonl")
    repairs = sum(1 for item in closed if item.get("checkpoint") == "closed" and item.get("outcome") == "fail")
    summary = {"status": status, "branch": branch, "stories_delivered": sum(1 for item in stories if item.get("status") == "verified"),
               "checks_passed": sum(1 for item in checks.get("results", []) if item.get("status") == "pass"), "repairs": repairs,
               "pr": (((state.get("implement") or {}).get("pr") or {}).get("url"))}
    if mode == "detailed":
        proc = subprocess.run([sys.executable, str(SCRIPTS / "memory/usage-ledger.py"), "summary", "--feature", feature,
                               "--workspace", str(workspace), "--format", "json"], capture_output=True, text=True)
        try:
            summary["usage"] = json.loads(proc.stdout) if proc.returncode == 0 else {"status": "unavailable"}
        except json.JSONDecodeError:
            summary["usage"] = {"status": "unavailable"}
    print((f"{status}: {feature}" + (f" — {summary['pr']}" if summary.get("pr") else "")) if mode == "off" else json.dumps(summary, indent=2))


def run(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    feature_dir = workspace / ".adlc5" / args.feature
    if not (feature_dir / "state.json").is_file():
        raise RuntimeError("state.json missing; initialize the ADLC5 feature first")
    policies = load_policies(workspace, args.feature)
    lock = feature_dir / "pilot/runner.lock"
    acquire_lock(lock)
    try:
        journal_path = feature_dir / "pilot/attempts.jsonl"
        events = journal(journal_path) if journal_path.exists() else []
        config = merge_model_config(ROOT, workspace)
        profiles = config.get("platform_profiles") if isinstance(config.get("platform_profiles"), dict) else {}
        host = str(args.host or config.get("default_host") or "codex")
        if host not in hosts.HOSTS:
            raise RuntimeError(f"unsupported host: {host}")
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
        isolated = ensure_isolation(workspace, args.feature, feature_dir, args)
        if isinstance(isolated, int):
            return isolated
        branch, isolation = isolated
        state = load_feature_state(workspace, args.feature) or {}
        if state.get("stage_status", {}).get("implement") == "completed":
            finish_summary(workspace, args.feature, "completed", branch, args.summary or "brief")
            return 0
        call(workspace, "pilot", "--feature", args.feature)
        pending = read_json(feature_dir / "pilot/pending-question.json")
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
        recover(workspace, args.feature, journal_path, events, run_id)
        while True:
            nav = subprocess.run([str(SCRIPTS / "pilot-autopilot.sh"), "--feature", args.feature, "--workspace", str(workspace)],
                                 cwd=workspace, capture_output=True, text=True)
            try:
                action = json.loads(nav.stdout)
            except json.JSONDecodeError as exc:
                raise RuntimeError(nav.stderr.strip() or f"navigator returned invalid JSON: {exc}")
            if action.get("action") == "done":
                state = load_feature_state(workspace, args.feature) or {}
                if state.get("stage_status", {}).get("implement") != "completed":
                    call(workspace, "transition", "completed", "--feature", args.feature)
                finish_summary(workspace, args.feature, "completed", branch, summary_mode)
                return 0
            if action.get("action") == "halt":
                print(json.dumps({"status": "halted", "reason": action.get("stop_reason")}, indent=2))
                return 1
            if action.get("action") == "advance":
                if str(action.get("phase", "")).startswith("specify-") and str(action.get("transition_target", "")).startswith("plan-"):
                    enforce_scope_block(workspace, args.feature)
                call(workspace, "transition", str(action.get("transition_target") or action.get("suggested_next")), "--feature", args.feature)
                continue
            if action.get("action") != "spawn":
                raise RuntimeError(f"unsupported navigator action: {action.get('action')}")
            step = str(action.get("phase") or "")
            if step == "implement-5-pr":
                raise RuntimeError("PR review and scoped approval remain chat-owned; use the in-agent PR workflow for this step")
            tier = str(action.get("model_tier_resolved") or "balanced")
            model = hosts.resolve_model(ROOT, workspace, args.feature, tier, host)
            model["tier"] = tier
            prior = [item for item in journal(journal_path) if item.get("step") == step and item.get("checkpoint") == "closed"]
            consecutive = 0
            for item in reversed(prior):
                if item.get("outcome") != "fail":
                    break
                consecutive += 1
            attempt_no = consecutive + 1
            if attempt_no == 2:
                model["effort"] = {"minimal": "low", "low": "medium", "medium": "high", "high": "xhigh"}.get(model.get("effort") or "medium", "xhigh")
            elif attempt_no >= 3:
                tier = "reasoning" if tier != "reasoning" else "balanced"
                model = hosts.resolve_model(ROOT, workspace, args.feature, tier, host)
                model["tier"] = tier
            if step == "implement-2-verify" and model.get("verifier_different_model"):
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
            brief, story = stage_brief(workspace, args.feature, step, action.get("gates"))
            start_commit = git(workspace, "rev-parse", "HEAD")
            entry = {"attempt_id": str(uuid.uuid4()), "run_id": run_id, "step": step, "story": story,
                     "number": attempt_no, "pack_sha256": hashlib.sha256(brief.encode()).hexdigest(), "config_sha256": config_hash,
                     "start_commit": start_commit, "kernel_fingerprint": fingerprint(workspace, args.feature),
                     "requested_model_id": model.get("model_id"), "tier": tier, "gate": action.get("gate"), "at": now(),
                     "host": host, "mode": mode}
            append(journal_path, entry)
            record_checkpoint(journal_path, entry, "launched")
            try:
                timeout = min(args.timeout, max(1, worker_deadline(workspace, args.feature)))
                rc, result, _log = run_worker(workspace, args.feature, entry, brief, model, timeout, host, mode,
                                              current_interaction_mode)
                if rc or result.get("status") == "failed":
                    raise RuntimeError(result.get("error") or f"worker exited {rc}")
                record_checkpoint(journal_path, entry, "result_validated", session_id=result.get("session_id"), model_id=result.get("model_id"))
                if result.get("status") == "needs_human":
                    question = {"id": entry["attempt_id"], "question": result.get("question", "Human input required"), "step": step,
                                "denied_actions": result.get("denied_actions", []), "host": host}
                    (feature_dir / "pilot/pending-question.json").write_text(json.dumps(question, indent=2) + "\n")
                    record_usage(workspace, args.feature, entry, result, model)
                    record_checkpoint(journal_path, entry, "usage_recorded")
                    close_attempt(journal_path, entry, attempt_no, "needs_human")
                    print(json.dumps({"status": "needs_human", **question}, indent=2))
                    return 10
                coders = [item for item in journal(journal_path) if item.get("step") == "implement-1-build" and item.get("outcome") == "pass" and item.get("story") and item.get("session_id")]
                coder = coders if step == "implement-2-verify" else next((item for item in reversed(coders) if item.get("story") == entry.get("story")), None)
                ingest(workspace, args.feature, entry, result, coder)
                record_checkpoint(journal_path, entry, "evidence_ingested")
                record_usage(workspace, args.feature, entry, result, model)
                record_checkpoint(journal_path, entry, "usage_recorded")
                passed = check_gate(workspace, args.feature, str(action.get("gate") or ""))
                if step == "implement-1-build":
                    passed = result.get("story_id", entry.get("story")) == entry.get("story")
                if passed:
                    git(workspace, "add", "-A")
                    staged = subprocess.run(["git", "-C", str(workspace), "diff", "--cached", "--quiet"]).returncode
                    if staged == 1:
                        subprocess.run(["git", "-C", str(workspace), "commit", "-m", f"feat({args.feature}): complete {step}"], check=True)
                outcome = "pass" if passed else "fail"
                close_attempt(journal_path, entry, attempt_no, outcome, session_id=result.get("session_id"), model_id=result.get("model_id"),
                              **({} if passed else {"reason": "gate failed"}))
                call(workspace, "pilot", "--feature", args.feature, "--record-result", outcome)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                if git(workspace, "rev-parse", "HEAD") == start_commit:
                    subprocess.run(["git", "-C", str(workspace), "reset", "--hard", start_commit], check=False)
                    subprocess.run(["git", "-C", str(workspace), "clean", "-fd"], check=False)
                record_usage(workspace, args.feature, entry, {"usage": {}, "model_id": model.get("model_id") or "unknown"}, model)
                close_attempt(journal_path, entry, attempt_no, "fail", reason=str(exc))
                call(workspace, "pilot", "--feature", args.feature, "--record-result", "fail", check=False)
                print(f"attempt {entry['attempt_id']} failed: {exc}", file=sys.stderr)
                if attempt_no >= 3:
                    raise
    finally:
        lock.unlink(missing_ok=True)


def worker_deadline(workspace: Path, feature: str) -> int:
    meta = read_json(workspace / ".adlc5" / feature / "pilot/meta.json", {}) or {}
    try:
        started = datetime.fromisoformat(str(meta["started_at"]).replace("Z", "+00:00")).timestamp()
    except (KeyError, ValueError, TypeError):
        return 3600
    return int(started + 360 * 60 - time.time())


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
