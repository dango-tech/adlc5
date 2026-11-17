"""Small deterministic checks for the runner journal and lock contracts."""
import importlib.util
import io
import json
import os
import shutil
import subprocess
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
            assert receipt["estimated_tokens"] > 10
            worker.assert_not_called()

        prior_attempt = {"attempt_id": "observed", "run_id": "prior-run", "config_sha256": "config",
                         "start_commit": git("rev-parse", "HEAD"), "step": "specify-1-discover",
                         "host": "codex", "mode": "confined", "number": 1}
        attempts_file = pilot / "attempts.jsonl"
        runner.append(attempts_file, prior_attempt)
        runner.close_attempt(attempts_file, prior_attempt, 1, "pass")
        config["pack_budget_tokens"]["balanced"] = 60000
        policy = {"autopilot": {"max_observed_worker_tokens": 20}}
        with patch.object(runner, "merge_model_config", return_value=config), \
             patch.object(runner, "load_policies", return_value=policy), \
             patch.object(runner.hosts, "resolve_model") as models, \
             patch.object(runner, "run_worker") as worker, redirect_stdout(io.StringIO()):
            assert runner.run(args) == 1
            receipt = json.loads((pilot / "runner-stop.json").read_text())
            assert receipt["condition"] == "observed_token_usage_unavailable"
            assert receipt["unmeasured_attempts"] == 1
            runner.record_usage(checkout, "bounded", prior_attempt,
                                {"usage": {"input": 12, "output": 8}, "observed_token_total": 20},
                                {"model_id": "test-model"})
            assert runner.run(args) == 1
            receipt = json.loads((pilot / "runner-stop.json").read_text())
            assert receipt["condition"] == "observed_token_budget_exhausted"
            assert receipt["observed_tokens"] == 20
            assert receipt["unmeasured_attempts"] == 0
            models.assert_not_called()
            worker.assert_not_called()
        assert len(runner.journal(attempts_file)) == 2

        def interrupt_with_edits(*_args):
            (checkout / "user.py").write_text("concurrent user edit\n")
            (checkout / "new-user.py").write_text("another user edit\n")
            git("add", "user.py")
            return 124, {"error": "timeout", "failure_kind": "worker_timeout"}, ""

        config["pack_budget_tokens"]["balanced"] = 60000
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
                assert (checkout / "user.py").read_text() == "concurrent user edit\n"
                assert (checkout / "new-user.py").read_text() == "another user edit\n"
                assert git("diff", "--cached", "--name-only") == "user.py"
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
        result = {"attempt_id": "a", "status": "completed", "story_id": "US-1"}
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


def check_observed_usage_attribution() -> None:
    with tempfile.TemporaryDirectory() as temp:
        feature_dir = Path(temp) / "feature"
        ledger = feature_dir / "memory/usage-ledger.jsonl"
        policy = {"max_observed_worker_tokens": 21}
        attempt = {"attempt_id": "a", "run_id": "run", "host": "claude", "mode": "allowlist",
                   "step": "implement-1-build", "start_commit": "abc", "config_sha256": "config"}
        trusted = {"feature": "feature", "platform": "claude", "run_id": "run", "step": "implement-1-build",
                   "source": "api", "extra": {"attempt_id": "a", "observed_token_total": 20,
                                              "usage_unavailable": False, "config_sha256": "config"}}

        journal = feature_dir / "pilot/attempts.jsonl"

        def check(host="claude", mode="allowlist"):
            runner.enforce_observed_token_budget(feature_dir, "implement-1-build", policy, host, mode)

        check()
        try:
            check("cursor", "confined")
        except runner.RunnerStop as exc:
            assert exc.outcome["condition"] == "observed_token_budget_unsupported"
        else:
            raise AssertionError("unsupported host accepted observed-token budget")

        runner.append(ledger, trusted)
        runner.append(ledger, trusted)
        runner.append(ledger, {**trusted, "extra": {"attempt_id": "unrelated", "observed_token_total": 20}})
        try:
            check()
        except runner.RunnerStop as exc:
            assert exc.outcome["condition"] == "observed_token_usage_unavailable"
            assert exc.outcome["unmeasured_attempts"] == 1
        else:
            raise AssertionError("orphaned runner usage receipt was silently ignored")
        runner.append(journal, attempt)
        check()  # One attributable measurement totaling 20, below 21.
        runner.append(ledger, {**trusted, "run_id": "unexpected"})
        try:
            check()
        except runner.RunnerStop as exc:
            assert exc.outcome["condition"] == "observed_token_usage_unavailable"
            assert exc.outcome["unmeasured_attempts"] == 1
        else:
            raise AssertionError("conflicting receipt was counted as complete")
        with journal.open("a") as stream:
            stream.write('{"attempt_id": "incomplete"\n')
        assert runner.journal(journal) == [attempt]  # Legacy callers remain tolerant.
        try:
            check()
        except runner.RunnerStop as exc:
            assert exc.outcome["condition"] == "observed_token_usage_unavailable"
            assert "invalid attempt journal" in exc.outcome["next_action"]
        else:
            raise AssertionError("malformed reservation was silently ignored")


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
    check_observed_usage_attribution()
    check_verification_context()
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
