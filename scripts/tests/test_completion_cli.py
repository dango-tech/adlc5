"""Supported CLI/MCP completion; local fixture approvals are not live approval evidence."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def mcp_call(name, arguments):
    request = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }).encode()
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/adlc5-mcp.py")],
        input=request + b"\n", capture_output=True, check=True,  # standard MCP stdio: one message per line
    )
    response = json.loads(proc.stdout.splitlines()[0])["result"]
    return json.loads(response["content"][0]["text"])


def exercise(profile, transport="cli", *, no_story=False):
    with tempfile.TemporaryDirectory() as temp:
        workspace = Path(temp)
        feature = workspace / ".adlc5/demo"
        (feature / "evidence").mkdir(parents=True)
        (feature / "tasks/code-spec").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", temp], check=True)
        (workspace / "app.py").write_text("def identity(value):\n    return value\n\ndef authorized(token):\n    return token == 'fixture-token'\n")
        (workspace / "test_app.py").write_text(
            "from app import identity\ndef test_identity():\n"
            "    assert identity(3) == 3\ntest_identity()\n"
        )
        (workspace / "test_security.py").write_text("from app import authorized\nassert not authorized(None)\nassert not authorized('wrong')\nassert authorized('fixture-token')\n")
        subprocess.run(["git", "-C", temp, "add", "."], check=True)
        subprocess.run([
            "git", "-C", temp, "-c", "user.name=Test",
            "-c", "user.email=test@example.invalid", "commit", "-qm", "baseline",
        ], check=True)

        def invoke(*args, success=True):
            if transport == "mcp" and args[0] in ("evidence", "transition"):
                arguments = {
                    "feature": "demo", "workspace": temp,
                    "action" if args[0] == "evidence" else "target": args[1],
                }
                if "--file" in args:
                    arguments["file"] = args[args.index("--file") + 1]
                result = mcp_call("adlc5_" + args[0], arguments)
                assert (result["exit_code"] == 0) == success, result
                return result
            proc = subprocess.run([
                sys.executable, str(ROOT / "scripts/adlc5"), *args,
                "--feature", "demo", "--workspace", temp,
            ], capture_output=True, text=True)
            assert (proc.returncode == 0) == success, proc.stdout + proc.stderr
            return proc

        state = {
            "schema_version": "3.0", "feature": "demo",
            "current_stage": "tasks", "current_step": "tasks-2-code-spec",
            "stage_status": {
                "specify": "completed", "plan": "completed",
                "tasks": "in_progress", "implement": "pending",
            },
            "tasks": {"stories": [{
                "id": "US-1", "status": "ready", "files": ["app.py", "test_app.py"],
                "acceptance": [{
                    "id": "AC-1", "owner": "test",
                    "evidence": {"type": "file", "value": "test_app.py"},
                }],
            }]},
        }
        (feature / "state.json").write_text(json.dumps(state))
        (feature / "policies.yaml").write_text(
            "autopilot:\n  profile: " + profile + "\n  require_human_pr_approval: true\n"
        )
        (feature / "risk.json").write_text(json.dumps({
            "categories": ["auth"] if profile == "high_risk" else [],
            "uncertain": False, "rationale": "fixture: identity helper",
        }))
        (feature / "tasks/code-spec/US-1.md").write_text(
            "---\nstory_id: US-1\nfiles_to_create: []\nfiles_to_modify:\n  - app.py\n"
            "tests:\n  - file: test_app.py\n    name: test_identity\n"
            "acceptance_criteria:\n  - AC-1\nacceptance_checks:\n  AC-1: [test_app.py::test_identity]\n---\nImplement identity.\n"
        )
        (feature / "evidence/checks.json").write_text(json.dumps([
            {"id": "acceptance", "command": "python3 -B test_app.py"},
            {"id": "integration", "command": "python3 -B test_app.py"},
            {"id": "optional", "command": None, "required": False},
        ]))
        if no_story:
            state["tasks"]["stories"] = []
            (feature / "state.json").write_text(json.dumps(state))
        else:
            invoke("anchors", "lock")
        # Raw state only prepares a fixture at Build; supported operations do all delivery.
        state = json.loads((feature / "state.json").read_text())
        if profile == "tiny":
            state.update(current_stage="specify", current_step="specify-4-handoff")
            state["stage_status"].update(specify="in_progress", plan="pending", tasks="pending")
            state["git"] = {"isolation": "current"}
            state["clarity"] = {"score": 90}
            (feature / "spec-handoff.md").write_text("Bounded identity behavior. Acceptance: test_app.py.\n")
            (feature / "change.md").write_text("---\nfiles_to_modify:\n  - app.py\n  - test_app.py\n---\nScope: identity. Reuse existing flow. Acceptance: identity test. Risk: low.\n")
            (feature / "tasks/code-spec/US-1.md").unlink()
        else:
            state.update(current_stage="implement", current_step="implement-1-build")
            state["stage_status"].update(implement="in_progress", tasks="completed")
        (feature / "state.json").write_text(json.dumps(state))
        if profile == "tiny":
            invoke("transition", "implement-1-build")
            statuses = json.loads((feature / "state.json").read_text())["stage_status"]
            assert statuses["plan"] == statuses["tasks"] == "waived"
            routed = json.loads((feature / "state.json").read_text())
            assert routed["persona"]["active"] == "coder"
            assert routed["implement"]["current_substep"] == "implement-1-build"
        (feature / "build.json").write_text(json.dumps({"story_ids": [] if no_story else ["US-1"]}))
        invoke("evidence", "build", "--file", str(feature / "build.json"))
        invoke("transition", "implement-2-verify")
        routed = json.loads((feature / "state.json").read_text())
        assert routed["persona"]["active"] == "tester"
        assert routed["implement"]["current_substep"] == "implement-2-verify"
        (feature / "review.json").write_text(json.dumps({
            "coder_session_id": "coder", "verifier_session_id": "reviewer",
            "coder_model_id": "model1", "verifier_model_id": "model2",
            "disposition": "pass", "blocking_findings": [],
        }))

        def verify():
            invoke("evidence", "check")
            invoke("evidence", "review", "--file", str(feature / "review.json"))

        verify()
        if profile == "high_risk":
            invoke("transition", "implement-3-integrate", success=False)
            checks_path = feature / "evidence/checks.json"
            checks = json.loads(checks_path.read_text())
            checks.append({"id": "security", "command": "python3 -B test_security.py"})
            checks_path.write_text(json.dumps(checks))
            verify()
        if profile != "tiny":
            invoke("transition", "implement-3-integrate")
            if profile == "standard":
                (feature / "evidence/integration.json").write_text(json.dumps({"status": "completed"}))
                invoke("evidence", "integrate", "--file", str(feature / "evidence/integration.json"))
                assert json.loads((feature / "state.json").read_text())["implement"]["integration"]["status"] == "completed"
        if profile == "high_risk":
            clearance = workspace / ".qa/demo/deployment-clearance.md"
            clearance.parent.mkdir(parents=True)
            clearance.write_text("Overall Status: CLEARED\n")
            verify()
            invoke("transition", "implement-4-qa")
        invoke("transition", "implement-5-pr")
        invoke("transition", "completed", success=False)
        (feature / "approval.json").write_text(json.dumps({
            "type": "pr_approval", "approved_by": "human:Test Fixture",
        }))
        # Adding an input after verification deliberately invalidates existing evidence.
        invoke("transition", "completed", success=False)
        verify()
        approval_request = feature / "evidence/approval-request.json"
        approval = {"type": "pr_approval", "approved_by": "human:Test Fixture"}
        approval_request.write_text(json.dumps(dict(approval, disposition="reject")))
        invoke("evidence", "approve", "--file", str(approval_request), success=False)
        approval_request.write_text(json.dumps(approval))
        invoke("evidence", "approve", "--file", str(approval_request))
        approval_request.write_text(json.dumps(dict(approval, decision="reject")))
        invoke("evidence", "approve", "--file", str(approval_request))
        invoke("transition", "completed", success=False)
        approval_request.write_text(json.dumps(approval))
        invoke("evidence", "approve", "--file", str(approval_request))
        invoke("transition", "completed")
        deploy = subprocess.run([sys.executable, str(ROOT / "scripts/adlc5"), "gate", "--gate", "deploy-ready", "--feature", "demo", "--workspace", temp], capture_output=True, text=True)
        report = json.loads(deploy.stdout)
        assert any(c["id"] == "pr_published" and c["status"] == "fail" for c in report["checks"])
        invoke("transition", "completed", success=False)
        assert json.loads((feature / "state.json").read_text())["stage_status"]["implement"] == "completed"


if __name__ == "__main__":
    exercise("tiny")
    exercise("tiny", no_story=True)
    exercise("standard")
    exercise("high_risk", "mcp")
    print("canonical CLI/MCP standard/high-risk checks passed")
