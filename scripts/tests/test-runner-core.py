"""Small deterministic checks for the runner journal and lock contracts."""
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash") or "bash"
SPEC = importlib.util.spec_from_file_location("runner_run", ROOT / "scripts/runner/run.py")
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(runner)
CONFIG_SPEC = importlib.util.spec_from_file_location("configure_models", ROOT / "scripts/configure-models.py")
configure_models = importlib.util.module_from_spec(CONFIG_SPEC)
assert CONFIG_SPEC.loader
CONFIG_SPEC.loader.exec_module(configure_models)


def main() -> None:
    assert runner.interaction_mode({"defaults": {"interaction_mode": "hitl"}}, {"interaction_mode": "autonomous"}) == "autonomous"
    assert runner.interaction_mode({"defaults": {"interaction_mode": "autonomous"}}, {}) == "autonomous"
    try:
        runner.interaction_mode({}, {"interaction_mode": "unknown"})
    except RuntimeError:
        pass
    else:
        raise AssertionError("invalid interaction mode must fail closed")
    with tempfile.TemporaryDirectory() as temp:
        lock = Path(temp) / "runner.lock"
        runner.acquire_lock(lock)
        try:
            try:
                runner.acquire_lock(lock)
            except RuntimeError as exc:
                assert "locked by pid" in str(exc)
            else:
                raise AssertionError("second owner acquired an active lock")
        finally:
            lock.unlink()
        journal = Path(temp) / "attempts.jsonl"
        attempt = {"attempt_id": "a", "step": "implement-1-build", "start_commit": "abc", "number": 1}
        runner.append(journal, attempt)
        runner.record_checkpoint(journal, attempt, "launched")
        assert runner.attempt_event(runner.journal(journal), "a", "launched")
        result = Path(temp) / "result.json"
        result.write_text(json.dumps({"attempt_id": "other", "status": "completed"}))
        assert json.loads(result.read_text())["attempt_id"] != attempt["attempt_id"]
        workspace = Path(temp) / "repo"
        (workspace / ".agents").mkdir(parents=True)
        (workspace / ".agents/commands.yaml").write_text(
            "schema_version: '1.0'\nstatus: active\ncommands:\n  test:\n    run: pytest -q\n  build:\n    run: npm run build\n")
        assert runner.command_allowlist(workspace, "feature") == ["Bash(pytest -q)", "Bash(npm run build)"]
        feature_pilot = workspace / ".adlc5/feature/pilot"
        feature_pilot.mkdir(parents=True)
        (feature_pilot / "pending-question.json").write_text(json.dumps({
            "id": "question", "step": "implement-1-build", "denied_actions": [
                {"tool_name": "Bash", "tool_input": {"command": "npm run test:e2e"}}
            ]}))
        answer = ROOT / "scripts/runner/answer.py"
        import subprocess
        subprocess.run(["python3", str(answer), "question", "--text", "allow", "--workspace", str(workspace)], check=True,
                       capture_output=True, text=True)
        assert json.loads((feature_pilot / "approved-commands.json").read_text()) == ["npm run test:e2e"]
        assert "Bash(npm run test:e2e)" in runner.command_allowlist(workspace, "feature")
        projects = Path(temp) / "claude-projects"
        project = projects / "repo"
        project.mkdir(parents=True)
        (project / "session-1.jsonl").write_text("\n".join([
            json.dumps({"type": "assistant", "message": {"model": "claude-sonnet", "usage": {
                "input_tokens": 12, "output_tokens": 4, "cache_read_input_tokens": 5, "cache_creation_input_tokens": 2}}}),
            json.dumps({"type": "assistant", "message": {"model": "claude-sonnet", "usage": {
                "input_tokens": 8, "output_tokens": 3, "cache_read_input_tokens": 1, "cache_creation_input_tokens": 0}}}),
        ]))
        # The worker deadline follows the feature's policy cap, with the kill switch's 360-minute default.
        meta = workspace / ".adlc5/feature/pilot/meta.json"
        meta.write_text(json.dumps({"started_at": runner.now()}))
        assert 170 * 60 < runner.worker_deadline(workspace, "feature", {"autopilot": {"wall_clock_cap_minutes": 180}}) <= 180 * 60
        assert 350 * 60 < runner.worker_deadline(workspace, "feature", {}) <= 360 * 60
        # A host-created worktree on its own named branch is reused: the feature branch is made in place.
        repo, host_tree = Path(temp) / "origin", Path(temp) / "host-tree"
        repo.mkdir()
        git = lambda cwd, *a: subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@x", "-c", "user.name=t", *a],
                                             check=True, capture_output=True, text=True).stdout
        git(repo, "init", "-q", "-b", "main")
        (repo / "README.md").write_text("x\n")
        git(repo, "add", "."), git(repo, "commit", "-qm", "init")
        git(repo, "worktree", "add", "-q", "-b", "host/session", str(host_tree))
        subprocess.run([BASH, str(ROOT / "scripts/init-feature.sh"), "--feature", "wt-feature", "--workspace", str(host_tree),
                        "--mode", "brownfield", "--interaction", "autonomous"], check=True, capture_output=True)
        git(host_tree, "add", "-A"), git(host_tree, "commit", "-qm", "scaffold", "--allow-empty")
        before = git(repo, "worktree", "list").count("\n")
        branch, isolation = runner.ensure_isolation(host_tree.resolve(), "wt-feature", host_tree.resolve() / ".adlc5/wt-feature", SimpleNamespace())
        assert (branch, isolation) == ("feat/wt-feature", "worktree")
        assert git(host_tree, "branch", "--show-current").strip() == "feat/wt-feature"
        assert git(repo, "worktree", "list").count("\n") == before
        # Closed records carry step, story and kind: verification and the retry ladder look attempts up by them.
        work = {"attempt_id": "b1", "step": "implement-1-build", "story": "US-1", "start_commit": "x"}
        runner.append(journal, work)
        runner.close_attempt(journal, work, 1, "pass", session_id="s1", model_id="m1")
        closed = runner.journal(journal)[-1]
        assert (closed["step"], closed["story"], closed["kind"], closed["outcome"]) == ("implement-1-build", "US-1", "work", "pass")
        # A rejected review routes to a rework, then back to review, within a budget.
        verify = {"attempt_id": "v1", "step": "implement-2-verify", "start_commit": "x"}
        assert runner.rework_findings(runner.journal(journal), 3) is None
        runner.close_attempt(journal, verify, 1, "fail", rework=True, findings="missing null check")
        assert runner.rework_findings(runner.journal(journal), 3) == "missing null check"
        runner.close_attempt(journal, {**verify, "attempt_id": "r1", "kind": "rework"}, 1, "pass", session_id="s2")
        assert runner.rework_findings(runner.journal(journal), 3) is None
        runner.close_attempt(journal, {**verify, "attempt_id": "v2"}, 1, "fail", rework=True, findings="still failing")
        try:
            runner.rework_findings(runner.journal(journal), 1)
        except RuntimeError as exc:
            assert "human review required" in str(exc)
        else:
            raise AssertionError("an exhausted rework budget must stop the run")
        # A dirty main checkout gets one worktree under .worktrees/, and the feature state moves into it.
        main_repo = Path(temp) / "main-repo"
        main_repo.mkdir()
        git(main_repo, "init", "-q", "-b", "main")
        (main_repo / "README.md").write_text("x\n")
        git(main_repo, "add", "."), git(main_repo, "commit", "-qm", "init")
        subprocess.run([BASH, str(ROOT / "scripts/init-feature.sh"), "--feature", "moved", "--workspace", str(main_repo),
                        "--mode", "brownfield", "--interaction", "autonomous"], check=True, capture_output=True)
        main_repo = main_repo.resolve()
        target = runner.isolate_in_worktree(main_repo, "moved", main_repo / ".adlc5/moved", "feat/moved")
        assert target == main_repo / ".worktrees/moved" and (target / ".adlc5/moved/state.json").is_file()
        assert not (main_repo / ".adlc5/moved").exists()
        assert ".worktrees" not in git(main_repo, "status", "--porcelain")
        assert runner.feature_worktree(main_repo, "moved") == target
        assert json.loads((target / ".adlc5/moved/state.json").read_text())["git"]["worktree_path"] == str(target)
        # Deviations are recorded for the end summary.
        runner.deviation(target / ".adlc5/moved", "host_default_model", step="specify-0-git", tier="balanced")
        assert runner.journal(target / ".adlc5/moved/pilot/deviations.jsonl")[0]["kind"] == "host_default_model"
        # A user price file is layered over the shipped table.
        from lib.model_prices import estimate_cost_usd, load_prices
        user_prices = Path(temp) / "model-prices.yaml"
        user_prices.write_text("models:\n  local-model:\n    input: 1.0\n    output: 2.0\n")
        prices = load_prices(ROOT, user_prices)
        assert estimate_cost_usd({"input": 1_000_000}, "local-model", prices) == (1.0, True)
        assert estimate_cost_usd({"input": 1_000_000}, "gpt-6-luna", prices)[1] is True
        usage, model = runner.claude_session_usage("session-1", projects)
        assert usage == {"input": 20, "output": 7, "cache_read": 6, "cache_creation": 2}
        assert model == "claude-sonnet"
        with patch.object(configure_models.subprocess, "run", return_value=SimpleNamespace(
                returncode=0, stdout="Available models\ngpt-5-low - Low\ngpt-5-low-fast - Low Fast\n")):
            assert configure_models.cursor_models() == ["gpt-5-low"]
        master = Path(temp) / "master.json"
        master.write_text(json.dumps({"model_routing": {"strategy": "balanced"}, "defaults": {"summary": "brief"},
                                      "platform_profiles": {"claude": {tier: {"model": "host default", "effort": "medium"}
                                                                  for tier in ("reasoning", "balanced", "execution")}}}))
        repo = workspace / ".adlc5/config.yaml"
        with patch.object(configure_models, "target_path", side_effect=lambda _workspace, is_repo: repo if is_repo else master), \
             patch.object(configure_models, "read_effective", return_value=(json.loads(master.read_text()), {})), \
             patch.object(configure_models.shutil, "which", return_value="/usr/bin/claude"), \
             patch.object(configure_models, "answer", side_effect=["balanced", "attended", "host default", "medium",
                                                                     "host default", "medium", "host default", "medium",
                                                                     "brief", "no"]):
            configure_models.setup(workspace, True, False, "claude")
        assert json.loads(repo.read_text())["platform_modes"] == {"claude": "attended"}


if __name__ == "__main__":
    main()
    print("runner core checks passed")
