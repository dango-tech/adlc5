"""Small deterministic checks for the runner journal and lock contracts."""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
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


def check_bootstrap() -> None:
    with tempfile.TemporaryDirectory() as temp:
        workspace = (Path(temp) / "repo").resolve()
        workspace.mkdir()

        def git(*args):
            return subprocess.run(["git", "-C", str(workspace), *args], check=True,
                                  capture_output=True, text=True).stdout.strip()

        git("init", "-q", "-b", "main")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "initial", "--allow-empty")
        subprocess.run([BASH, str(ROOT / "scripts/init-feature.sh"), "--feature", "demo",
                        "--workspace", str(workspace), "--mode", "brownfield",
                        "--interaction", "autonomous"], check=True, capture_output=True)
        feature = workspace / ".adlc5/demo"
        pilot = runner.call(workspace, "pilot", "--feature", "demo")
        diagnostic = json.loads(pilot.stdout)
        assert (diagnostic["action"], diagnostic["gate"]) == ("halt", "specify-0-git")
        assert diagnostic["bootstrap"]["condition"] == "git_isolation_unrecorded"
        blocked = runner.call(workspace, "transition", "specify-1-discover", "--feature", "demo", check=False)
        assert blocked.returncode
        assert json.loads(blocked.stdout)["bootstrap"] == diagnostic["bootstrap"]
        assert runner.load_feature_state(workspace, "demo")["current_step"] == "specify-0-git"
        args = SimpleNamespace(workspace=str(workspace), feature="demo", host="codex", mode="confined",
                               accept_defaults=True, summary="off", timeout=30)
        target = workspace.parent / "peer"
        git("add", ".agents", ".gitignore")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "workspace standards")
        git("worktree", "add", "-q", "-b", "feat/demo", str(target))
        assert not runner.checkout_dirty(workspace, "demo")
        actual_subprocess = subprocess.run

        def run_until_bootstrap(*command, **options):
            is_navigator = str(ROOT / "scripts/pilot-autopilot.sh") in command[0]
            if is_navigator and runner.load_feature_state(workspace, "demo")["current_step"] != "specify-0-git":
                return subprocess.CompletedProcess(command[0], 0, '{"action":"halt","stop_reason":"test boundary"}', "")
            return actual_subprocess(*command, **options)

        # Navigator failure needs neither a model nor an attempted worker. A repaired
        # branch advances from the existing state, even when no attempt journal exists.
        with patch.object(runner.subprocess, "run", side_effect=run_until_bootstrap), \
             patch.object(runner, "run_worker", side_effect=AssertionError("unexpected worker")) as executor, \
             patch.object(runner.hosts, "resolve_model") as models:
            for _ in range(2):
                output = io.StringIO()
                with redirect_stdout(output):
                    assert runner.run(args) == 1
                assert json.loads(output.getvalue())["condition"] == "branch_checked_out", output.getvalue()
                assert runner.load_feature_state(workspace, "demo")["current_step"] == "specify-0-git"
            blocker = json.loads((feature / "pilot/git-bootstrap.json").read_text())
            assert blocker["evidence"]["branch"] == "feat/demo"
            git("-C", str(target), "switch", "--detach")
            runner.call(workspace, "state", "set", "--feature", "demo", "--patch",
                        json.dumps({"git": {"worktree_path": str(target)}}))
            output = io.StringIO()
            with redirect_stdout(output):
                assert runner.run(args) == 1
            assert json.loads(output.getvalue())["condition"] == "worktree_binding_mismatch"
            runner.call(workspace, "state", "set", "--feature", "demo", "--patch",
                        '{"git":{"worktree_path":null}}')
            for _ in range(2):
                with redirect_stdout(io.StringIO()):
                    assert runner.run(args) == 1
                assert runner.load_feature_state(workspace, "demo")["current_step"] != "specify-0-git"
            executor.assert_not_called()
            models.assert_not_called()
        assert not (feature / "pilot/attempts.jsonl").exists()
        assert json.loads((feature / "pilot/git-bootstrap.json").read_text())["status"] == "pass"
        saved = runner.load_feature_state(workspace, "demo")
        assert saved["git"]["start_commit"] == git("rev-parse", "HEAD")
        transitions = [record for record in runner.evidence_records(workspace, "demo")
                       if record["kind"] == "transition"]
        assert len(transitions) == 1 and transitions[0]["from"] == "specify-0-git"

        if os.name != "nt":
            redirected = workspace.parent / "redirected"
            redirected.mkdir()
            (redirected / ".adlc5").symlink_to(workspace / ".adlc5", target_is_directory=True)
            output = io.StringIO()
            with redirect_stdout(output), patch.object(runner, "run_worker") as executor:
                assert runner.run(SimpleNamespace(**{**vars(args), "workspace": str(redirected)})) == 1
                executor.assert_not_called()
            assert json.loads(output.getvalue())["condition"] == "redirected_feature_path"

        non_git = workspace.parent / "non-git"
        non_git.mkdir()
        subprocess.run([BASH, str(ROOT / "scripts/init-feature.sh"), "--feature", "waiver",
                        "--workspace", str(non_git), "--mode", "brownfield",
                        "--interaction", "autonomous"], check=True, capture_output=True)
        assert runner.git_bootstrap.evaluate(non_git, "waiver")["condition"] == "git_isolation_unrecorded"
        runner.call(non_git, "state", "set", "--feature", "waiver", "--patch",
                    '{"git":{"isolation":"current","branch_name":"main"}}')
        assert runner.git_bootstrap.evaluate(non_git, "waiver")["condition"] == "git_metadata_unavailable"
        waiver = subprocess.run([BASH, str(ROOT / "scripts/git-orchestrate.sh"), "--feature", "waiver",
                                 "--workspace", str(non_git), "--action", "skip"], capture_output=True, text=True)
        assert waiver.returncode == 0, waiver.stderr
        assert runner.git_bootstrap.evaluate(non_git, "waiver")["evidence"] == {"isolation": "waived"}
        assert json.loads(runner.call(non_git, "pilot", "--feature", "waiver").stdout)["action"] == "advance"


def check_concurrent_stale_lock_recovery() -> None:
    with tempfile.TemporaryDirectory() as temp:
        lock = Path(temp) / "runner.lock"
        code = """
import runpy
import sys
from pathlib import Path

acquire = runpy.run_path(sys.argv[1])["acquire_lock"]
path = Path(sys.argv[2])
sys.stdin.readline()
try:
    acquire(path)
except RuntimeError as exc:
    print(str(exc), flush=True)
else:
    print("acquired", flush=True)
    sys.stdin.readline()
"""
        argv = [sys.executable, "-c", code, str(ROOT / "scripts/runner/run.py"), str(lock)]
        # Leave a real legacy-format lock owned by a process that has exited.
        subprocess.run(argv, input="start\n", check=True, capture_output=True, text=True, timeout=10)
        assert lock.is_file()
        contenders = [subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
                      for _ in range(2)]
        try:
            for proc in contenders:
                proc.stdin.write("start\n")
                proc.stdin.flush()
            results = [proc.stdout.readline().strip() for proc in contenders]
            assert results.count("acquired") == 1, results
            assert sum("locked by pid" in result for result in results) == 1, results
            winner = contenders[results.index("acquired")]
            assert json.loads(lock.read_text())["pid"] == winner.pid
        finally:
            for proc in contenders:
                if proc.poll() is None:
                    proc.terminate()
                proc.communicate(timeout=10)


def check_bounded_execution() -> None:
    with tempfile.TemporaryDirectory() as temp:
        checkout = Path(temp).resolve()

        def git(*args):
            return subprocess.run(["git", "-C", str(checkout), *args], check=True,
                                  capture_output=True, text=True).stdout.strip()

        git("init", "-q", "-b", "feat/bounded")
        (checkout / "user.py").write_text("original\n")
        subprocess.run([BASH, str(ROOT / "scripts/init-feature.sh"), "--feature", "bounded",
                        "--workspace", str(checkout), "--mode", "brownfield",
                        "--interaction", "autonomous"], check=True, capture_output=True)
        (checkout / ".git/info/exclude").write_text(".adlc5/\n")
        git("add", ".")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "initial")
        pilot = checkout / ".adlc5/bounded/pilot"
        state_file = pilot.parent / "state.json"
        state = json.loads(state_file.read_text())
        state["current_step"] = "specify-2-requirements"
        state_file.write_text(json.dumps(state))
        args = SimpleNamespace(workspace=str(checkout), feature="bounded", host="codex", mode="confined",
                               accept_defaults=True, summary="off", timeout=30)

        config = {"defaults": {}, "pack_budget_tokens": {"balanced": 10}}
        with patch.object(runner, "merge_model_config", return_value=config), \
             patch.object(runner, "stage_brief", return_value=("tiny", None)), \
             patch.object(runner.hosts, "resolve_model", return_value={"model_id": "test-model"}), \
             patch.object(runner, "run_worker") as worker, redirect_stdout(io.StringIO()):
            assert runner.run(args) == 1
            receipt = json.loads((pilot / "runner-stop.json").read_text())
            assert receipt["condition"] == "pack_over_budget"
            assert receipt["resume_owner"] == "operator"
            assert receipt["earliest_retry_at"] is None
            assert receipt["estimated_tokens"] > 10
            worker.assert_not_called()

        state = json.loads(state_file.read_text())
        state.update(current_stage="implement", current_step="implement-1-build",
                     tasks={"stories": [{"id": "US-1", "status": "implementation_complete"}]})
        state_file.write_text(json.dumps(state))
        path = pilot / "attempts.jsonl"
        prior = {"attempt_id": "discarded", "start_commit": git("rev-parse", "HEAD"), "story": "US-1",
                 "step": "implement-1-build", "number": 1}
        result = {"attempt_id": "discarded", "status": "completed", "changed_paths": ["worker.py"]}
        runner.append(path, prior)
        runner.atomic_write_json(pilot / "results/discarded.json", result)
        runner.record_checkpoint(path, prior, "result_validated", result_sha256=runner.result_digest(result),
                                 result_fingerprint="dirty-fingerprint-before-discard")
        runner.record_checkpoint(path, prior, "evidence_ingested")
        config["pack_budget_tokens"]["balanced"] = 60000
        def next_worker(*_args):
            assert runner.load_feature_state(checkout, "bounded")["tasks"]["stories"][0]["status"] == "pending"
            return 1, {"error": "fixture stops after dispatch"}, ""
        with patch.object(runner, "merge_model_config", return_value=config), \
             patch.object(runner, "stage_brief", return_value=("tiny", "US-1")), \
             patch.object(runner.hosts, "resolve_model", return_value={"model_id": "test-model"}), \
             patch.object(runner, "record_usage"), \
             patch.object(runner, "run_worker", side_effect=next_worker) as worker, redirect_stdout(io.StringIO()):
            assert runner.run(args) == 1
            worker.assert_called_once()
            closed = runner.attempt_event(runner.journal(path), "discarded", "closed")
            assert closed["outcome"] == "fail" and closed["reason_code"] == "recovery_source_unverified"
        state = json.loads(state_file.read_text())
        state.update(current_stage="specify", current_step="specify-2-requirements")
        state_file.write_text(json.dumps(state))

        config["pack_budget_tokens"]["balanced"] = 60000
        with patch.object(runner, "merge_model_config", return_value=config), \
             patch.object(runner, "stage_brief", return_value=("tiny", None)), \
             patch.object(runner.hosts, "resolve_model", return_value={"model_id": "test-model"}), \
             patch.object(runner, "record_usage"), \
             patch.object(runner, "call", wraps=runner.call) as kernel, \
             patch.object(runner, "run_worker", return_value=(1, {
                 "error": "host quota limited", "failure_kind": "host_quota",
                 "earliest_retry_at": "2099-01-01T00:00:00+00:00",
             }, "")) as worker, redirect_stdout(io.StringIO()):
            assert runner.run(args) == 1
            receipt = json.loads((pilot / "runner-stop.json").read_text())
            assert receipt["condition"] == receipt["wait_kind"] == "host_quota"
            assert receipt["resume_owner"] == "operator"
            assert receipt["host"] == "codex"
            assert receipt["earliest_retry_at"] == "2099-01-01T00:00:00+00:00"
            assert not any("--record-result" in call.args for call in kernel.call_args_list)
            journal_before = (pilot / "attempts.jsonl").read_bytes()
            assert runner.run(args) == 1
            assert (pilot / "attempts.jsonl").read_bytes() == journal_before
            worker.assert_called_once()
            other_host = SimpleNamespace(**{**vars(args), "host": "claude", "mode": "allowlist"})
            assert runner.run(other_host) == 1
            assert worker.call_count == 2
            assert json.loads((pilot / "runner-stop.json").read_text())["host"] == "claude"
            assert not any("--record-result" in call.args for call in kernel.call_args_list)
        runner.clear_runner_stop(pilot / "runner-stop.json")
        state = json.loads(state_file.read_text())
        state["current_step"] = "specify-3-nfr"
        state_file.write_text(json.dumps(state))

        def interrupt_with_edits(*_args):
            (checkout / "user.py").write_text("concurrent user edit\n")
            (checkout / "new-user.py").write_text("another user edit\n")
            git("add", "user.py")
            return 1, {"error": "quota", "failure_kind": "host_quota",
                       "earliest_retry_at": "2099-01-01T00:00:00+00:00"}, ""

        with patch.object(runner, "merge_model_config", return_value=config), \
             patch.object(runner, "stage_brief", return_value=("tiny", None)), \
             patch.object(runner.hosts, "resolve_model", return_value={"model_id": "test-model"}) as models, \
             patch.object(runner, "record_usage") as usage, \
             patch.object(runner, "run_worker", side_effect=interrupt_with_edits) as worker, redirect_stdout(io.StringIO()):
            for _ in range(2):
                assert runner.run(args) == 1
                receipt = json.loads((pilot / "runner-stop.json").read_text())
                assert receipt["condition"] == "recovery_required"
                assert receipt["expected_commit"] == git("rev-parse", "HEAD")
                assert receipt["wait_kind"] == "host_quota"
                assert receipt["earliest_retry_at"] == "2099-01-01T00:00:00+00:00"
                assert (checkout / "user.py").read_text() == "concurrent user edit\n"
                assert (checkout / "new-user.py").read_text() == "another user edit\n"
                assert git("diff", "--cached", "--name-only") == "user.py"
            (checkout / "new-user.py").rename(pilot / "preserved-new-user.py")
            (checkout / "user.py").rename(pilot / "preserved-user.py")
            subprocess.run(["git", "-C", str(checkout), "restore", "--source=HEAD", "--staged", "--worktree",
                            "user.py"], check=True)
            assert runner.run(args) == 1
            receipt = json.loads((pilot / "runner-stop.json").read_text())
            assert receipt["condition"] == "host_quota"
            assert receipt["earliest_retry_at"] == "2099-01-01T00:00:00+00:00"
            worker.assert_called_once()
            models.assert_called_once()
            usage.assert_called_once()

    with tempfile.TemporaryDirectory() as temp:
        checkout = Path(temp).resolve()
        subprocess.run(["git", "-C", str(checkout), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(checkout), "-c", "user.name=Fixture", "-c",
                        "user.email=fixture@example.invalid", "commit", "-qm", "initial", "--allow-empty"], check=True)
        commit = runner.git(checkout, "rev-parse", "HEAD")
        pilot = checkout / ".adlc5/bounded/pilot"
        attempt = {"attempt_id": "a", "start_commit": commit, "step": "implement-1-build", "story": "US-1"}
        path = pilot / "attempts.jsonl"
        runner.append(path, attempt)
        result = {"attempt_id": "a", "status": "completed", "story_id": "US-1", "changed_paths": []}
        runner.atomic_write_json(pilot / "results/a.json", result)
        runner.record_checkpoint(path, attempt, "result_validated", result_sha256=runner.result_digest(result))
        with patch.object(runner, "ingest") as ingest, patch.object(runner, "record_usage") as usage, \
             patch.object(runner, "call") as kernel, patch.object(runner, "check_gate", return_value=True):
            for _ in range(2):
                runner.recover(checkout, "bounded", path, runner.journal(path))
            ingest.assert_called_once()
            usage.assert_called_once()
            kernel.assert_called_once()
        assert runner.attempt_event(runner.journal(path), "a", "closed")["outcome"] == "pass"
        for attempt_id, findings in (("rejected", "Missing assertion"), ("rework", "Check suite failed")):
            verify = {**attempt, "attempt_id": attempt_id, "step": "implement-2-verify"}
            outcome = {"attempt_id": attempt_id, "status": "completed", "changed_paths": [],
                       "review": {"disposition": "reject", "blocking_findings": [findings]}}
            runner.append(path, verify)
            runner.atomic_write_json(pilot / "results" / f"{attempt_id}.json", outcome)
            runner.record_checkpoint(path, verify, "result_validated", result_sha256=runner.result_digest(outcome))
            error = runner.ReworkNeeded(findings) if attempt_id == "rework" else None
            with patch.object(runner, "ingest", side_effect=error), patch.object(runner, "record_usage"), \
                 patch.object(runner, "call"), patch.object(runner, "check_gate", return_value=False):
                runner.recover(checkout, "bounded", path, runner.journal(path))
            rows = runner.journal(path)
            closed = runner.attempt_event(rows, attempt_id, "closed")
            assert closed["outcome"] == "fail" and "blocker_fingerprint" not in closed
            assert findings in runner.rework_findings(rows, 3)
        discarded = {**attempt, "attempt_id": "discarded"}
        output = {**result, "attempt_id": "discarded", "changed_paths": ["missing.py"]}
        runner.append(path, discarded)
        runner.atomic_write_json(pilot / "results/discarded.json", output)
        runner.record_checkpoint(path, discarded, "result_validated", result_sha256=runner.result_digest(output),
                                 result_fingerprint="fingerprint-with-discarded-source")
        with patch.object(runner, "ingest") as ingest, patch.object(runner, "record_usage") as usage, \
             patch.object(runner, "reopen_discarded_build") as reopen:
            for _ in range(2):
                runner.recover(checkout, "bounded", path, runner.journal(path))
            ingest.assert_not_called()
            usage.assert_called_once()
            reopen.assert_called_once()
        closed = runner.attempt_event(runner.journal(path), "discarded", "closed")
        assert closed["outcome"] == "fail" and closed["reason_code"] == "recovery_source_unverified"
        (checkout / "worker.py").write_text("worker result\n")
        (checkout / "unrelated.py").write_text("concurrent edit\n")
        declaration = {"changed_paths": ["worker.py"]}
        try:
            runner.commit_worker_changes(checkout, "bounded", path, attempt, declaration)
        except runner.RunnerStop as exc:
            assert exc.outcome["condition"] == "recovery_required"
        else:
            raise AssertionError("runner committed a result with unrelated edits")
        assert runner.git(checkout, "diff", "--cached", "--name-only") == ""
        assert (checkout / "unrelated.py").is_file()
        (checkout / "unrelated.py").rename(pilot / "preserved.py")
        runner.git(checkout, "config", "user.name", "Fixture")
        runner.git(checkout, "config", "user.email", "fixture@example.invalid")
        runner.commit_worker_changes(checkout, "bounded", path, attempt, declaration)
        assert runner.git(checkout, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD") == "worker.py"
        runner.require_recovered_source(checkout, attempt, declaration, runner.journal(path),
                                        {"result_sha256": runner.result_digest(declaration)})
        mismatch = {"changed_paths": ["different.py"]}
        try:
            runner.require_recovered_source(checkout, attempt, mismatch, runner.journal(path),
                                            {"result_sha256": runner.result_digest(mismatch)})
        except runner.RunnerStop as exc:
            assert exc.outcome["condition"] == "recovery_source_unverified"
        else:
            raise AssertionError("recovery accepted a commit with mismatched source")


def check_attended_worktree_bootstrap() -> None:
    with tempfile.TemporaryDirectory() as temp:
        workspace = Path(temp).resolve()
        subprocess.run(["git", "init", "-q", "-b", "main", str(workspace)], check=True)
        tracked = workspace / ".adlc5/standards.txt"
        tracked.parent.mkdir()
        tracked.write_text("committed\n")
        for feature in ("demo", "peer"):
            subprocess.run([BASH, str(ROOT / "scripts/init-feature.sh"), "--feature", feature,
                            "--workspace", str(workspace), "--mode", "brownfield",
                            "--interaction", "autonomous"], check=True, capture_output=True)
        (workspace / ".gitignore").write_text("*.pyc\n.agent-cache/\n")
        subprocess.run(["git", "-C", str(workspace), "add", ".agents", ".gitignore", ".adlc5/standards.txt"], check=True)
        subprocess.run(["git", "-C", str(workspace), "-c", "user.name=Fixture", "-c",
                        "user.email=fixture@example.invalid", "commit", "-qm", "initial"], check=True)
        status = subprocess.check_output(["git", "-C", str(workspace), "status", "--porcelain", "--untracked-files=all"], text=True)
        assert "?? .adlc5/peer/state.json" in status
        assert not runner.checkout_dirty(workspace, "demo"), status
        tracked.write_text("changed\n")
        assert runner.checkout_dirty(workspace, "demo")
        tracked.write_text("committed\n")
        source = workspace / "untracked source.py"
        source.write_text("pass\n")
        assert runner.checkout_dirty(workspace, "demo")
        source.unlink()

        orchestrate = [BASH, str(ROOT / "scripts/git-orchestrate.sh"), "--workspace", str(workspace),
                       "--feature", "demo", "--action", "worktree"]
        result = subprocess.run(orchestrate, check=True, capture_output=True, text=True)
        target = Path(json.loads(result.stdout)["worktree_path"])
        assert (workspace / ".gitignore").read_text() == "*.pyc\n.agent-cache/\n"
        assert (target / ".adlc5/demo/state.json").is_file()
        assert runner.load_feature_state(target, "demo")["git"]["repository_root"] == str(target)
        assert runner.git_bootstrap.evaluate(workspace, "demo")["condition"] == "worktree_binding_mismatch"
        assert json.loads(runner.call(target, "pilot", "--feature", "demo").stdout)["action"] == "advance"
        runner.call(target, "transition", "specify-1-discover", "--feature", "demo")
        target_state = target / ".adlc5/demo/state.json"
        advanced = target_state.read_bytes()
        subprocess.run(orchestrate, check=True, capture_output=True, text=True)
        assert target_state.read_bytes() == advanced
        assert runner.load_feature_state(target, "demo")["current_step"] == "specify-1-discover"
        transfer = runner.git_bootstrap.place_worktree_state
        source_state = workspace / ".adlc5/peer/state.json"
        original = source_state.read_bytes()
        partial = target / ".adlc5/peer"

        def fail_during_copy(source, destination, **options):
            assert source == source_state.parent and destination == partial
            (destination / "concurrent-evidence.txt").write_text("preserve\n")
            raise OSError("fixture copy interruption")

        with patch.object(runner.git_bootstrap.shutil, "copytree", side_effect=fail_during_copy):
            try:
                transfer(workspace, "peer", json.loads(result.stdout))
            except runner.git_bootstrap.BootstrapBlocked as failure:
                assert failure.diagnostic["condition"] == "worktree_state_transfer_failed"
            else:
                raise AssertionError("failed transfer must report a bootstrap blocker")
        assert (partial / "concurrent-evidence.txt").read_text() == "preserve\n"
        assert source_state.read_bytes() == original

        target_state.write_text("{}")
        refused = subprocess.run(orchestrate, capture_output=True, text=True)
        assert refused.returncode and "worktree_state_exists" in refused.stderr
        assert target_state.read_text() == "{}"


def check_verification_context() -> None:
    with tempfile.TemporaryDirectory() as temp:
        workspace = Path(temp)
        feature = workspace / ".adlc5/demo"
        specs = feature / "tasks/code-spec"
        specs.mkdir(parents=True)
        design = feature / "design"
        design.mkdir()
        (feature / "spec-handoff.md").write_text("Require tenant isolation for every story.\n")
        (workspace / "AGENTS.md").write_text("Run the deterministic suite before review.\n")
        (design / "1b-contracts.md").write_text("Preserve repository API compatibility.\n")
        stories = []
        for name, constraint in (("one", "Deny cross-tenant reads."), ("two", "Log successful exports.")):
            stories.append({"id": name, "status": "implementation_complete", "acceptance": [f"AC-{name}"]})
            (specs / f"{name}.md").write_text(
                f"---\nstory_id: {name}\nfiles_to_modify: [src/{name}.py]\n---\n"
                f"## Locked requirements\n\n{constraint}\n")
        (feature / "state.json").write_text(json.dumps({
            "schema_version": "3.0", "feature": "demo", "current_stage": "implement",
            "current_step": "implement-2-verify", "stage_status": {}, "tasks": {"stories": stories},
        }))
        from readiness_fixture import reviewed_fixture
        from lib.requirements_readiness import load_record, record, source
        reviewed_fixture(workspace)
        review = load_record(feature / "requirements-readiness.json")
        review["delivery"]["constraints"] = [{"requirement_ids": ["FIXTURE-1"],
            "text": "Reject unauthenticated requests before storage access.",
            "source": source(workspace, ".adlc5/demo/spec-handoff.md")}]
        record(workspace, "demo", review)
        for finding in (None, "The reviewer found an authorization gap."):
            brief, story = runner.stage_brief(workspace, "demo", "implement-2-verify", {"status": "fail"}, finding)
            assert story is None
            assert brief.count("Require tenant isolation for every story.") == 1
            assert brief.count("Source: `.adlc5/demo/spec-handoff.md`") == 1
            assert brief.count("Run the deterministic suite before review.") == 1
            assert brief.count("Reject unauthenticated requests before storage access.") == 1
            assert brief.count("Source: `.adlc5/demo/requirements-readiness.json`") == 1
            assert brief.count("Gate feedback:") == 1
            shared, first = brief.split("# Context pack — one", 1)
            first, second = first.split("# Context pack — two", 1)
            assert "# Shared context for all stories" in shared
            assert "AC-one" in first and "AC-two" in second
            assert "Deny cross-tenant reads." in first and "Log successful exports." in second
            assert "Log successful exports." not in first and "Deny cross-tenant reads." not in second
            assert "Source: `.adlc5/demo/tasks/code-spec/one.md`" in first
            assert "Source: `.adlc5/demo/tasks/code-spec/two.md`" in second
            assert "src/one.py" in first and "src/two.py" in second
            if finding:
                assert finding in brief and "Preserve repository API compatibility." not in brief
            else:
                assert brief.count("Preserve repository API compatibility.") == 1
                assert "Source: `.adlc5/demo/design/1b-contracts.md`" in shared
            prefix = "story" if finding else "verify"
            for name in ("one", "two"):
                pack_path = feature / "memory/context-packs" / f"{prefix}-{name}.md"
                assert "Require tenant isolation for every story." in pack_path.read_text()

    # Partial inclusion or differing content keeps the section under its own story.
    merge = runner.combine_story_packs([
        [{"text": "# One", "shareable": False}, {"text": "Rules version one", "shareable": True}],
        [{"text": "# Two", "shareable": False}, {"text": "Rules version two", "shareable": True}],
        [{"text": "# Three", "shareable": False}, {"text": "Rules omitted at cap", "shareable": False}],
    ])
    assert "# Shared context" not in merge
    assert merge.split("\n\n---\n\n") == ["# One\n\nRules version one", "# Two\n\nRules version two", "# Three\n\nRules omitted at cap"]


def main() -> None:
    check_bootstrap()
    check_bounded_execution()
    check_verification_context()
    check_concurrent_stale_lock_recovery()
    check_attended_worktree_bootstrap()
    assert runner.decode_worker_result({'attempt_id': 'a', 'status': 'needs_human', 'summary': 'decision',
        'payload_json': '{"question":{"text":"Who may export?"}}'})['question']['text'] == 'Who may export?'
    fenced = 'Inspected the requirement.\n```json\n{"attempt_id":"a","status":"needs_human","payload_json":"{}"}\n```'
    assert runner.parse_worker_result(fenced, 'cursor')['attempt_id'] == 'a'
    for malformed in (fenced + '\ntrailing output', fenced + '\n' + fenced):
        try:
            runner.parse_worker_result(malformed, 'cursor')
        except ValueError:
            pass
        else:
            raise AssertionError('ambiguous cursor result accepted')
    for invalid in ('[]', '{"status":"completed"}', 'not json'):
        try:
            runner.decode_worker_result({'payload_json': invalid})
        except ValueError:
            pass
        else:
            raise AssertionError('invalid or overriding transport payload accepted')
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
        except runner.RunnerStop as exc:
            assert exc.outcome["condition"] == "verification_rework_exhausted"
            assert exc.outcome["resume_owner"] == "operator"
            assert exc.outcome["findings"] == "still failing"
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
