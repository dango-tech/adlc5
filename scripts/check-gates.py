#!/usr/bin/env python3
"""Evaluate deterministic delivery/lifecycle gates from state files.

Usage:
  ./scripts/check-gates.py --feature NAME [--gate GATE_ID] [--workspace DIR]

Stdout: JSON { "gate", "status": pass|fail|warn, "checks": [...] }
Exit: 0 pass, 1 fail, 2 warn-only (no hard fail), 3 usage/IO error
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from lib.adlc5_paths import delivery_state_path, load_delivery_state  # noqa: E402
from lib.simple_yaml import load_frontmatter  # noqa: E402
from lib.policies_load import (  # noqa: E402
    load_policies,
    normalize_custom_gates,
    profile_name,
    required_gate_names,
    step_enabled,
)
from lib.state_v2 import (  # noqa: E402
    is_v2_state,
    load_feature_state,
    v2_to_delivery_compat,
)


def emit_telemetry(feature: str, event: str, status: str, phase: str, details: dict) -> None:
    lib = SCRIPT_DIR / "lib" / "telemetry.sh"
    if not lib.is_file():
        return
    details_json = json.dumps(details)
    env = os.environ.copy()
    env["ADLC5_WORKSPACE"] = str(Path(os.environ.get("ADLC5_WORKSPACE", ".")).resolve())
    subprocess.run(
        [
            "bash",
            "-c",
            f'source "{lib}" && telemetry_emit "{feature}" "{event}" "check-gates.py" "{status}" "{phase}" \'{details_json}\'',
        ],
        env=env,
        check=False,
        capture_output=True,
    )


def iter_stories(delivery: dict) -> list[tuple[str, dict]]:
    """Normalize delivery stories as dict or list to (id, story) pairs."""
    stories = delivery.get("stories") or {}
    if isinstance(stories, dict):
        return [(sid, s if isinstance(s, dict) else {}) for sid, s in stories.items()]
    if isinstance(stories, list):
        out: list[tuple[str, dict]] = []
        for item in stories:
            if not isinstance(item, dict):
                continue
            sid = item.get("id") or item.get("story_id") or item.get("name")
            if sid:
                out.append((str(sid), item))
        return out
    return []


def load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def run_custom_gate(name: str, command: str, workspace: Path, cwd: str | None) -> dict:
    run_dir = workspace / cwd if cwd else workspace
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(run_dir),
            capture_output=True,
            text=True,
            timeout=600,
        )
        ok = proc.returncode == 0
        return {
            "id": f"custom_gate_{name}",
            "status": "pass" if ok else "fail",
            "message": f"custom_gate {name} exit {proc.returncode}",
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {
            "id": f"custom_gate_{name}",
            "status": "fail",
            "message": f"custom_gate {name} timed out",
            "command": command,
        }
    except OSError as e:
        return {
            "id": f"custom_gate_{name}",
            "status": "fail",
            "message": str(e),
            "command": command,
        }


def check_custom_gates(workspace: Path, feature: str, policies: dict, *, strict: bool) -> list[dict]:
    checks: list[dict] = []
    gates = normalize_custom_gates(policies)
    required = set(required_gate_names(policies))
    ran: dict[str, dict] = {}

    for g in gates:
        name = g["name"]
        result = run_custom_gate(name, g["command"], workspace, g.get("cwd"))
        ran[name] = result
        checks.append(result)

    for name in required:
        if name not in ran:
            checks.append(
                {
                    "id": f"custom_gate_{name}",
                    "status": "fail" if strict else "warn",
                    "message": f"required custom_gate {name} not defined in custom_gates",
                }
            )
        elif ran[name]["status"] != "pass":
            checks[-1]["status"] = "fail" if strict else ran[name]["status"]

    return checks


def update_delivery_gate_summary(delivery_path: Path, checks: list[dict]) -> None:
    delivery = load_json(delivery_path)
    if delivery is None:
        return
    summary = delivery.get("verification_summary") or {}
    summary["gates"] = [
        {"id": c["id"], "status": c["status"], "message": c.get("message", "")}
        for c in checks
        if c["id"].startswith("custom_gate_")
    ]
    delivery["verification_summary"] = summary
    delivery_path.write_text(json.dumps(delivery, indent=2) + "\n", encoding="utf-8")


def check_build_implementation(delivery: dict) -> list[dict]:
    checks = []
    pairs = iter_stories(delivery)
    if not pairs:
        checks.append({"id": "stories_present", "status": "fail", "message": "no stories in delivery state"})
        return checks
    incomplete = [
        sid
        for sid, s in pairs
        if s.get("type") != "integration"
        and s.get("status") not in ("implementation_complete", "verified", "failed")
    ]
    checks.append(
        {
            "id": "stories_implementation_complete",
            "status": "pass" if not incomplete else "fail",
            "message": "all component stories implementation_complete or beyond"
            if not incomplete
            else f"incomplete: {', '.join(incomplete[:5])}",
        }
    )
    return checks


def check_assure_verification(delivery: dict, workspace: Path, feature: str) -> list[dict]:
    checks = list(check_assure_verification_stories(delivery))
    report = workspace / ".adlc5" / feature / "verify" / "verification-report.md"
    if not report.is_file():
        checks.append(
            {
                "id": "verification_report_present",
                "status": "fail",
                "message": "missing verify/verification-report.md",
            }
        )
    else:
        sync = SCRIPT_DIR / "sync-verification-report.sh"
        if sync.is_file():
            proc = subprocess.run(
                [str(sync), "--feature", feature, "--workspace", str(workspace)],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                checks.append(
                    {
                        "id": "verification_report_sync",
                        "status": "fail",
                        "message": "sync-verification-report.sh failed",
                    }
                )
            else:
                checks.append(
                    {
                        "id": "verification_report_sync",
                        "status": "pass",
                        "message": "verification report in sync with delivery",
                    }
                )
    return checks


def check_assure_verification_stories(delivery: dict) -> list[dict]:
    unverified = [
        sid
        for sid, s in iter_stories(delivery)
        if s.get("type") != "integration" and s.get("status") != "verified"
    ]
    return [
        {
            "id": "component_stories_verified",
            "status": "pass" if not unverified else "fail",
            "message": "all component stories verified"
            if not unverified
            else f"unverified: {', '.join(unverified[:5])}",
        }
    ]


def check_assure_integration(delivery: dict) -> list[dict]:
    integration = delivery.get("integration") or {}
    status = integration.get("status", "pending")
    return [
        {
            "id": "integration_completed",
            "status": "pass" if status == "completed" else "fail",
            "message": f"integration.status is {status}",
        }
    ]


def check_assure_qa(workspace: Path, feature: str) -> list[dict]:
    clearance = workspace / ".qa" / feature / "deployment-clearance.md"
    if not clearance.is_file():
        return [
            {
                "id": "qa_deployment_clearance",
                "status": "fail",
                "message": f"missing {clearance.relative_to(workspace)}",
            }
        ]
    text = clearance.read_text(encoding="utf-8", errors="replace")
    statuses = [
        match.upper()
        for match in re.findall(
            r"^\s*(?:\*{0,2}Overall Status:\*{0,2}|STATUS:)\s*"
            r"(CLEARED-WITH-EXCEPTIONS|CLEARED|BLOCKED)\s*$",
            text,
            re.I | re.M,
        )
    ]
    if "BLOCKED" in statuses:
        return [{"id": "qa_deployment_clearance", "status": "fail", "message": "deployment clearance BLOCKED"}]
    if "CLEARED" in statuses:
        return [{"id": "qa_deployment_clearance", "status": "pass", "message": "deployment clearance CLEARED"}]
    if "CLEARED-WITH-EXCEPTIONS" in statuses:
        return [
            {
                "id": "qa_deployment_clearance",
                "status": "warn",
                "message": "deployment clearance has exceptions requiring review",
            }
        ]
    return [
        {
            "id": "qa_deployment_clearance",
            "status": "fail",
            "message": "deployment-clearance.md missing an exact Overall Status/STATUS field",
        }
    ]


def check_assure_pr_review(lifecycle: dict | None) -> list[dict]:
    if not lifecycle:
        return [{"id": "lifecycle_assure", "status": "warn", "message": "lifecycle state.json missing"}]
    if is_v2_state(lifecycle):
        pr = (lifecycle.get("implement") or {}).get("pr") or {}
        if pr.get("status") == "completed" and pr.get("url"):
            return [{"id": "assure_pr_review", "status": "pass", "message": "implement.pr completed with URL"}]
        return [
            {
                "id": "assure_pr_review",
                "status": "warn",
                "message": f"implement.pr is {pr.get('status', 'pending')}",
            }
        ]
    assure = lifecycle.get("assure") or {}
    pr = assure.get("pr_review", "pending")
    if pr == "completed":
        return [{"id": "assure_pr_review", "status": "pass", "message": "assure.pr_review completed"}]
    pr_review = lifecycle.get("pr_review") or {}
    if pr_review.get("url"):
        return [{"id": "assure_pr_review", "status": "pass", "message": "pr_review url recorded"}]
    return [{"id": "assure_pr_review", "status": "warn", "message": f"assure.pr_review is {pr}"}]


PLAN_GATE_MAP: dict[str, tuple[str, str]] = {
    "plan-1-discovery": ("plan_discovery", "design/1a-discovery.md"),
    "plan-2-contracts": ("plan_contracts", "design/1b-contracts.md"),
    "plan-3-operations": ("plan_operations", "design/1c-operations.md"),
    "plan-4-user-stories": ("plan_user_stories", "design/user_stories.md"),
    "plan-5-code-spec": ("plan_code_spec", "code_specs"),
    "plan-phase": ("", ""),
}

# Alternate specify-* gate IDs (normalize on read via gates.yaml legacy_aliases)
for _legacy in (
    "specify-1-discovery",
    "specify-2-contracts",
    "specify-3-operations",
    "specify-4-user-stories",
    "specify-5-code-spec",
    "specify-phase",
):
    _plan = _legacy.replace("specify-", "plan-", 1)
    if _plan in PLAN_GATE_MAP:
        PLAN_GATE_MAP[_legacy] = PLAN_GATE_MAP[_plan]


def _normalize_plan_gate_id(gate_id: str) -> str:
    if gate_id.startswith("specify-"):
        return gate_id.replace("specify-", "plan-", 1)
    return gate_id


def _plan_phase_status(delivery: dict, phase_key: str) -> str:
    ps = delivery.get("phase_status") or {}
    if phase_key in ps:
        return ps[phase_key]
    legacy = phase_key.replace("plan_", "specify_", 1)
    return ps.get(legacy, "pending")


def check_plan_gate(
    delivery: dict, gate_id: str, workspace: Path, feature: str
) -> list[dict]:
    gate_id = _normalize_plan_gate_id(gate_id)
    current = _normalize_plan_gate_id(delivery.get("current_phase", ""))
    if gate_id == "plan-phase":
        gate_id = current if current in PLAN_GATE_MAP else "plan-1-discovery"

    mapping = PLAN_GATE_MAP.get(gate_id)
    if not mapping:
        return [{"id": "plan_gate", "status": "warn", "message": f"unknown plan gate {gate_id}"}]

    phase_key, artifact_rel = mapping
    phase_status = _plan_phase_status(delivery, phase_key)
    artifact_path = workspace / ".adlc5" / feature / artifact_rel
    if artifact_rel == "code_specs":
        artifact_ok = artifact_path.is_dir() and any(artifact_path.glob("*.md"))
    else:
        artifact_ok = artifact_path.is_file()

    status_ok = phase_status == "completed"
    if status_ok or artifact_ok:
        status = "pass"
        message = f"{phase_key} completed" if status_ok else f"artifact present: {artifact_rel}"
    else:
        status = "fail"
        message = f"{phase_key} is {phase_status}; missing {artifact_rel}"

    return [{"id": phase_key, "status": status, "message": message}]


def has_verifier_waiver_approval(lifecycle: dict | None) -> bool:
    if not lifecycle:
        return False
    history = (lifecycle.get("clarity") or {}).get("history") or []
    return any(
        h.get("type") == "verifier_waiver" and is_human_approver(h.get("approved_by"))
        for h in history
        if isinstance(h, dict)
    )


def is_human_approver(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    if normalized == "user":
        return True
    if normalized.startswith("human:"):
        return bool(normalized.removeprefix("human:").strip())
    if normalized.startswith("github:"):
        return bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,38})", normalized.removeprefix("github:")))
    if normalized.startswith("email:"):
        return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized.removeprefix("email:")))
    return False


def check_verifier_independence(lifecycle: dict | None, policies: dict) -> list[dict]:
    if profile_name(policies) != "high_risk":
        return []
    persona = policies.get("persona_mode") or {}
    require_fresh = bool(persona.get("fresh_subagent_per_persona"))
    require_different_model = bool(persona.get("verifier_different_model"))
    if not (require_fresh or require_different_model):
        return []
    if has_verifier_waiver_approval(lifecycle):
        return [{"id": "verifier_independence", "status": "pass", "message": "human verifier waiver recorded"}]

    evidence = ((((lifecycle or {}).get("implement") or {}).get("verification") or {}).get("independence") or {})
    failures = []
    if require_fresh and not (
        evidence.get("fresh_session") is True
        and evidence.get("coder_session_id")
        and evidence.get("verifier_session_id")
        and evidence.get("coder_session_id") != evidence.get("verifier_session_id")
    ):
        failures.append("fresh verifier session not evidenced")
    if require_different_model and not (
        evidence.get("coder_model_id")
        and evidence.get("verifier_model_id")
        and evidence.get("coder_model_id") != evidence.get("verifier_model_id")
    ):
        failures.append("different verifier model not evidenced")
    return [
        {
            "id": "verifier_independence",
            "status": "fail" if failures else "pass",
            "message": "; ".join(failures) if failures else "fresh-session and model separation evidenced",
        }
    ]


def check_human_pr_approval(lifecycle: dict | None, policies: dict) -> list[dict]:
    """Require a recorded human pr_approval when policies opt in."""
    autopilot = policies.get("autopilot") or {}
    required = bool(autopilot.get("require_human_pr_approval") or policies.get("require_human_pr_approval"))
    if not required:
        return []
    history = ((lifecycle or {}).get("clarity") or {}).get("history") or []
    approved = any(
        h.get("type") == "pr_approval" and is_human_approver(h.get("approved_by"))
        for h in history
        if isinstance(h, dict)
    )
    return [
        {
            "id": "human_pr_approval",
            "status": "pass" if approved else "fail",
            "message": "clarity.history pr_approval recorded"
            if approved
            else "require_human_pr_approval set but no clarity.history pr_approval entry",
        }
    ]


def check_deploy_ready(workspace: Path, feature: str, lifecycle: dict | None) -> list[dict]:
    """Gate for @deploy: QA clearance + PR recorded + explicit human deploy approval."""
    checks: list[dict] = []
    checks.extend(check_assure_qa(workspace, feature))
    checks.extend(check_assure_pr_review(lifecycle))
    history = ((lifecycle or {}).get("clarity") or {}).get("history") or []
    approved = any(
        h.get("type") == "deploy_approval" and is_human_approver(h.get("approved_by"))
        for h in history
        if isinstance(h, dict)
    )
    checks.append(
        {
            "id": "deploy_approval",
            "status": "pass" if approved else "fail",
            "message": "clarity.history deploy_approval recorded"
            if approved
            else "no clarity.history deploy_approval entry — deployment always requires human sign-off",
        }
    )
    return checks


def check_anchor_integrity(workspace: Path, feature: str, policies: dict) -> list[dict]:
    checker = SCRIPT_DIR / "tasks" / "check-anchors.py"
    proc = subprocess.run(
        [sys.executable, str(checker), "check", "--feature", feature, "--workspace", str(workspace)],
        capture_output=True,
        text=True,
    )
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        report = {"status": "error", "error": proc.stderr.strip() or "invalid anchor checker output"}
    anchors_required = profile_name(policies) == "high_risk" or bool(
        (policies.get("autopilot") or {}).get("require_anchors")
    )
    missing_required = anchors_required and int(report.get("locked", 0) or 0) == 0
    ok = proc.returncode == 0 and report.get("status") == "pass" and not missing_required
    return [
        {
            "id": "anchor_integrity",
            "status": "pass" if ok else "fail",
            "message": (
                "acceptance anchors are intact"
                if ok
                else "profile requires at least one locked file anchor"
                if missing_required
                else report.get("error", "acceptance anchors changed")
            ),
            "details": report.get("checks", []),
        }
    ]


def check_deterministic_verify(workspace: Path, feature: str, lifecycle: dict | None) -> list[dict]:
    """Lever 3 — mechanical pre-check (→ scripts/verify-story.py) before
    @assure-verifier reasons about what's actually left.

    Additive and backward-safe: only stories whose code spec carries lever-2
    frontmatter (scripts/tasks/spec-lint.py) get a deterministic check here.
    A feature with no frontmatter yet — pre-lever-2, or a consumer that
    hasn't adopted it — gets no checks from this function at all, so
    implement-2-verify behaves exactly as before for it.
    """
    if not lifecycle or not is_v2_state(lifecycle):
        return []
    stories = (lifecycle.get("tasks") or {}).get("stories") or []
    if not isinstance(stories, list):
        return []

    verifier = SCRIPT_DIR / "verify-story.py"
    checks: list[dict] = []
    for s in stories:
        if not isinstance(s, dict) or s.get("type") == "integration":
            continue
        sid = s.get("id")
        if not sid or s.get("status") not in ("implementation_complete", "verified", "failed"):
            continue

        spec_path = None
        for base in ("tasks/code-spec", "delivery/code-spec"):
            for name in (f"{sid}.md", f"US-{sid}.md"):
                cand = workspace / ".adlc5" / feature / base / name
                if cand.is_file():
                    spec_path = cand
                    break
            if spec_path is not None:
                break
        if spec_path is None:
            continue
        fm, _ = load_frontmatter(spec_path.read_text(encoding="utf-8", errors="replace"))
        if not fm:
            continue  # legacy code spec, no lever-2 frontmatter — not this check's concern

        proc = subprocess.run(
            [sys.executable, str(verifier), "--feature", feature, "--story-id", str(sid), "--workspace", str(workspace)],
            capture_output=True,
            text=True,
        )
        try:
            report = json.loads(proc.stdout)
        except json.JSONDecodeError:
            report = {"status": "error"}
        ok = proc.returncode == 0 and report.get("status") == "pass"
        checks.append(
            {
                "id": f"deterministic_verify_{sid}",
                "status": "pass" if ok else "fail",
                "message": f"story {sid}: "
                + ("deterministic checks pass" if ok else "deterministic checks failed — see verify-story.py output"),
                "details": report.get("checks", []),
            }
        )

    return checks


def check_pr_ready(
    workspace: Path, feature: str, delivery: dict, lifecycle: dict | None, policies: dict
) -> list[dict]:
    checks: list[dict] = []
    autopilot = policies.get("autopilot") or {}
    strict_quality = bool(autopilot.get("interaction_mode") == "autonomous" or autopilot.get("quality_gates"))
    checks.extend(check_quality_gates(workspace, feature, policies, strict=strict_quality))
    if lifecycle and is_v2_state(lifecycle):
        stage = lifecycle.get("current_stage")
        step = lifecycle.get("current_step")
        ready = stage == "implement" and step == "implement-5-pr"
        checks.append(
            {
                "id": "lifecycle_implement_pr_step",
                "status": "pass" if ready else "fail",
                "message": f"current stage/step is {stage}/{step}",
            }
        )
    else:
        phase = delivery.get("current_phase", "")
        checks.append(
            {
                "id": "delivery_phase_completed",
                "status": "pass" if phase == "completed" else "fail",
                "message": f"current_phase is {phase}",
            }
        )
    checks.extend(check_assure_verification(delivery, workspace, feature))
    checks.extend(check_verifier_independence(lifecycle, policies))
    if step_enabled(policies, "implement-3-integrate"):
        checks.extend(check_assure_integration(delivery))
    if step_enabled(policies, "implement-4-qa"):
        checks.extend(check_assure_qa(workspace, feature))
    if lifecycle and is_v2_state(lifecycle):
        checks.extend(check_anchor_integrity(workspace, feature, policies))
        checks.extend(check_deterministic_verify(workspace, feature, lifecycle))

    if lifecycle and not is_v2_state(lifecycle):
        stage_status = lifecycle.get("stage_status") or {}
        stage = stage_status.get("assure", "pending")
        stage_label = "assure"
        checks.append(
            {
                "id": "lifecycle_assure_completed",
                "status": "pass" if stage == "completed" else "warn",
                "message": f"stage_status.{stage_label} is {stage}",
            }
        )
        if not has_verifier_waiver_approval(lifecycle):
            report = workspace / ".adlc5" / feature / "verify" / "verification-report.md"
            if report.is_file():
                m = re.search(
                    r"^\*{0,2}Overall(?::\*{0,2}|\*{0,2}:)\s*(\S+)",
                    report.read_text(encoding="utf-8", errors="replace"),
                    re.I | re.M,
                )
                if m and m.group(1).lower() == "pass-with-warnings":
                    checks.append(
                        {
                            "id": "unapproved_verifier_waiver",
                            "status": "fail",
                            "message": "pass-with-warnings without clarity.history verifier_waiver",
                        }
                    )

    checks.extend(check_assure_pr_review(lifecycle))
    checks.extend(check_human_pr_approval(lifecycle, policies))
    strict = bool(policies.get("autopilot") or policies.get("required_gates") or normalize_custom_gates(policies))
    checks.extend(check_custom_gates(workspace, feature, policies, strict=strict or bool(required_gate_names(policies))))

    return checks


def check_quality_gates(
    workspace: Path, feature: str, policies: dict, *, strict: bool
) -> list[dict]:
    """Enforce policies.autopilot.quality_gates when strict (autonomous mode)."""
    checks: list[dict] = []
    autopilot = policies.get("autopilot") or {}
    qg = autopilot.get("quality_gates") or {}
    if not qg:
        return checks

    coverage_min = qg.get("coverage_min")
    if coverage_min is not None:
        cov_script = SCRIPT_DIR / "score-coverage.py"
        if cov_script.is_file():
            proc = subprocess.run(
                [
                    sys.executable,
                    str(cov_script),
                    "--feature",
                    feature,
                    "--workspace",
                    str(workspace),
                    "--threshold",
                    str(coverage_min),
                ],
                capture_output=True,
                text=True,
            )
            if proc.returncode == 2:
                checks.append(
                    {
                        "id": "quality_gate_coverage",
                        "status": "fail" if strict else "warn",
                        "message": f"coverage artifact missing (min {coverage_min}%)",
                    }
                )
            elif proc.returncode != 0:
                checks.append(
                    {
                        "id": "quality_gate_coverage",
                        "status": "fail",
                        "message": f"coverage below {coverage_min}%",
                    }
                )
            else:
                checks.append(
                    {
                        "id": "quality_gate_coverage",
                        "status": "pass",
                        "message": f"coverage >= {coverage_min}%",
                    }
                )

    lint_max = qg.get("lint_errors_max")
    if lint_max is not None:
        lint_script = SCRIPT_DIR / "run-lint.sh"
        if lint_script.is_file():
            proc = subprocess.run(
                ["bash", str(lint_script), "--feature", feature, "--workspace", str(workspace)],
                capture_output=True,
                text=True,
            )
            try:
                lint_out = json.loads(proc.stdout)
                runner = lint_out.get("runner", "unknown")
            except json.JSONDecodeError:
                runner = "unknown"
            if runner == "skipped":
                checks.append(
                    {
                        "id": "quality_gate_lint",
                        "status": "fail" if strict else "warn",
                        "message": "lint runner skipped under quality_gates policy",
                    }
                )
            elif proc.returncode != 0:
                checks.append(
                    {
                        "id": "quality_gate_lint",
                        "status": "fail",
                        "message": f"lint errors exceed max {lint_max}",
                    }
                )
            else:
                checks.append(
                    {
                        "id": "quality_gate_lint",
                        "status": "pass",
                        "message": f"lint errors <= {lint_max}",
                    }
                )

    tests_required = strict or qg.get("require_tests", True)
    if tests_required:
        test_script = SCRIPT_DIR / "run-tests.sh"
        if test_script.is_file():
            proc = subprocess.run(
                ["bash", str(test_script), "--feature", feature, "--workspace", str(workspace)],
                capture_output=True,
                text=True,
            )
            try:
                test_out = json.loads(proc.stdout)
                runner = test_out.get("runner", "unknown")
            except json.JSONDecodeError:
                runner = "unknown"
            if runner == "skipped":
                checks.append(
                    {
                        "id": "quality_gate_tests",
                        "status": "fail" if strict else "warn",
                        "message": "test runner skipped under quality_gates policy",
                    }
                )
            elif proc.returncode != 0:
                checks.append(
                    {
                        "id": "quality_gate_tests",
                        "status": "fail",
                        "message": "tests failed under quality_gates policy",
                    }
                )
            else:
                checks.append(
                    {
                        "id": "quality_gate_tests",
                        "status": "pass",
                        "message": "tests passed",
                    }
                )

    cyclomatic_max = qg.get("cyclomatic_max")
    if cyclomatic_max is not None:
        arch_script = SCRIPT_DIR / "check-architecture.sh"
        if arch_script.is_file():
            proc = subprocess.run(
                ["bash", str(arch_script), "--feature", feature, "--workspace", str(workspace)],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                checks.append(
                    {
                        "id": "quality_gate_cyclomatic",
                        "status": "fail" if strict else "warn",
                        "message": f"architecture/complexity check failed (max {cyclomatic_max})",
                    }
                )
            else:
                checks.append(
                    {
                        "id": "quality_gate_cyclomatic",
                        "status": "pass",
                        "message": f"cyclomatic complexity within {cyclomatic_max}",
                    }
                )
        else:
            checks.append(
                {
                    "id": "quality_gate_cyclomatic",
                    "status": "warn",
                    "message": f"cyclomatic_max={cyclomatic_max} configured; check-architecture.sh not run",
                }
            )

    return checks


def check_v2_specify_complete(workspace: Path, feature: str, state: dict) -> list[dict]:
    checks: list[dict] = []
    git = state.get("git") or {}
    isolation = git.get("isolation", "pending")
    if isolation in ("pending", ""):
        checks.append({"id": "git_isolation_recorded", "status": "fail", "message": "git.isolation not set"})
    elif isolation == "skip" and not any(
        h.get("type") == "git_waiver" for h in (state.get("clarity") or {}).get("history") or []
    ):
        checks.append(
            {
                "id": "git_isolation_recorded",
                "status": "warn",
                "message": "git isolation skipped without waiver in clarity.history",
            }
        )
    else:
        checks.append({"id": "git_isolation_recorded", "status": "pass", "message": f"git.isolation={isolation}"})

    handoff = workspace / ".adlc5" / feature / "spec-handoff.md"
    checks.append(
        {
            "id": "spec_handoff_exists",
            "status": "pass" if handoff.is_file() else "fail",
            "message": "spec-handoff.md present" if handoff.is_file() else "missing spec-handoff.md",
        }
    )
    checks.extend(check_clarity(state))
    return checks


def check_design_critique(workspace: Path, feature: str, policies: dict) -> list[dict]:
    """Design-critic verdict gate: design/design-critique.md with critique_severity.

    Missing artifact warns in HITL, fails in autonomous mode; blocking always fails.
    """
    strict = bool((policies.get("autopilot") or {}).get("interaction_mode") == "autonomous")
    path = workspace / ".adlc5" / feature / "design" / "design-critique.md"
    if not path.is_file():
        return [
            {
                "id": "design_critique",
                "status": "fail" if strict else "warn",
                "message": "missing design/design-critique.md — run @adlc5-design-critic",
            }
        ]
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"(?im)^\*{0,2}critique_severity:?\*{0,2}\s*:?\s*(none|minor|blocking)\b", text)
    if not m:
        return [
            {
                "id": "design_critique",
                "status": "fail",
                "message": "design-critique.md has no critique_severity verdict (none|minor|blocking)",
            }
        ]
    severity = m.group(1).lower()
    if severity == "blocking":
        status = "fail"
    elif severity == "minor":
        status = "warn"
    else:
        status = "pass"
    return [
        {
            "id": "design_critique",
            "status": status,
            "message": f"critique_severity is {severity}",
        }
    ]


def check_v2_plan_complete(
    workspace: Path, feature: str, state: dict, policies: dict | None = None
) -> list[dict]:
    checks: list[dict] = []
    craft = state.get("craftsmanship") or {}
    for key, cid in (
        ("architecture_review", "craftsmanship_architecture"),
        ("pattern_selection", "craftsmanship_patterns"),
    ):
        val = craft.get(key, "pending")
        checks.append(
            {
                "id": cid,
                "status": "pass" if val in ("completed", "waived") else "fail",
                "message": f"craftsmanship.{key} is {val}",
            }
        )
    algo = craft.get("algorithm_review", "not_applicable")
    if algo not in ("not_applicable", "waived"):
        checks.append(
            {
                "id": "craftsmanship_algorithms",
                "status": "pass" if algo == "completed" else "fail",
                "message": f"craftsmanship.algorithm_review is {algo}",
            }
        )
    for rel, cid in (
        ("design/1a-discovery.md", "design_discovery"),
        ("design/1b-contracts.md", "design_contracts"),
        ("design/1c-operations.md", "design_operations"),
    ):
        path = workspace / ".adlc5" / feature / rel
        checks.append(
            {
                "id": cid,
                "status": "pass" if path.is_file() else "fail",
                "message": f"{'present' if path.is_file() else 'missing'} {rel}",
            }
        )
    checks.extend(check_design_critique(workspace, feature, policies or {}))
    return checks


def check_v2_tasks_stories_complete(workspace: Path, feature: str, state: dict) -> list[dict]:
    checks: list[dict] = []
    pairs = iter_stories(v2_to_delivery_compat(state))
    if not pairs:
        checks.append({"id": "stories_defined", "status": "fail", "message": "no stories in state.tasks"})
    else:
        checks.append({"id": "stories_defined", "status": "pass", "message": f"{len(pairs)} stories defined"})
    return checks


def check_v2_tasks_code_spec_complete(workspace: Path, feature: str, state: dict) -> list[dict]:
    checks: list[dict] = []
    code_spec = workspace / ".adlc5" / feature / "tasks" / "code-spec"
    legacy = workspace / ".adlc5" / feature / "delivery" / "code-spec"
    ok = (code_spec.is_dir() and any(code_spec.glob("*.md"))) or (
        legacy.is_dir() and any(legacy.glob("*.md"))
    )
    checks.append(
        {
            "id": "code_specs_complete",
            "status": "pass" if ok else "fail",
            "message": "code specs directory has markdown files" if ok else "missing tasks/code-spec",
        }
    )
    if ok:
        checks.append(check_spec_lint(workspace, feature))
    return checks


def check_spec_lint(workspace: Path, feature: str) -> dict:
    """Machine-checkable code specs (lever 2) — → scripts/tasks/spec-lint.py.

    A code spec without frontmatter, or with malformed frontmatter, fails
    the tasks-2-code-spec-complete gate. This is what "code specs complete"
    now means beyond "the directory has markdown files in it."
    """
    linter = SCRIPT_DIR / "tasks" / "spec-lint.py"
    proc = subprocess.run(
        [sys.executable, str(linter), "--feature", feature, "--workspace", str(workspace)],
        capture_output=True,
        text=True,
    )
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "id": "code_specs_lint",
            "status": "fail",
            "message": (proc.stderr.strip() or "spec-lint.py produced no parseable output"),
        }
    if report.get("status") == "error":
        return {"id": "code_specs_lint", "status": "fail", "message": report.get("message", "spec-lint error")}
    failing = [r for r in report.get("results", []) if r.get("status") == "fail"]
    ok = proc.returncode == 0 and report.get("status") == "pass"
    return {
        "id": "code_specs_lint",
        "status": "pass" if ok else "fail",
        "message": (
            f"{report.get('specs_checked', 0)} code spec(s) linted, all pass"
            if ok
            else f"{len(failing)}/{report.get('specs_checked', 0)} code spec(s) fail lint: "
            + "; ".join(
                f"{r.get('story_id') or (Path(r['path']).stem if r.get('path') else 'coverage')}: {r['blockers'][0]}"
                for r in failing[:5]
            )
        ),
        "details": report.get("results", []),
    }


def check_v2_task_graph(workspace: Path, feature: str) -> list[dict]:
    validator = SCRIPT_DIR / "tasks" / "validate-graph.py"
    proc = subprocess.run(
        [sys.executable, str(validator), "--feature", feature, "--workspace", str(workspace)],
        capture_output=True,
        text=True,
    )
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        report = {"status": "error", "error": proc.stderr.strip() or "invalid validator output"}
    ok = proc.returncode == 0 and report.get("status") == "pass"
    return [
        {
            "id": "task_graph_valid",
            "status": "pass" if ok else "fail",
            "message": "task graph is valid" if ok else report.get("error", "task graph is invalid"),
            "details": report.get("checks", []),
        }
    ]


def check_v2_tasks_complete(workspace: Path, feature: str, state: dict) -> list[dict]:
    checks: list[dict] = []
    checks.extend(check_v2_tasks_stories_complete(workspace, feature, state))
    checks.extend(check_v2_tasks_code_spec_complete(workspace, feature, state))
    checks.extend(check_v2_task_graph(workspace, feature))
    return checks


def check_persona_context_gate(
    workspace: Path, feature: str, lifecycle: dict, policies: dict, paths: list[str] | None = None
) -> list[dict]:
    from lib.personas_load import check_persona_context, get_persona_for_step, persona_mode_enabled

    if not persona_mode_enabled(policies):
        return [
            {
                "id": "persona_context_violation",
                "status": "pass",
                "message": "persona_mode disabled — memory wall check skipped",
            }
        ]

    step = lifecycle.get("current_step", "")
    persona_block = lifecycle.get("persona") or {}
    persona_id = persona_block.get("active") or get_persona_for_step(step) or "analyst"

    if paths is None:
        paths = []
        index = workspace / ".adlc5" / feature / "memory" / "INDEX.md"
        if index.is_file():
            paths.append(str(index))
        stage = lifecycle.get("current_stage", "specify")
        summary = workspace / ".adlc5" / feature / "memory" / "summaries" / f"{stage}.md"
        if summary.is_file():
            paths.append(str(summary))

    if not paths:
        return [
            {
                "id": "persona_context_violation",
                "status": "warn",
                "message": "no paths to validate for persona memory wall",
            }
        ]

    result = check_persona_context(str(persona_id), paths, feature)
    if result["status"] == "pass":
        return [
            {
                "id": "persona_context_violation",
                "status": "pass",
                "message": f"persona {persona_id} context within memory walls",
            }
        ]
    detail = result.get("violations") or result.get("denied") or []
    return [
        {
            "id": "persona_context_violation",
            "status": "fail",
            "message": f"persona {persona_id} memory wall violation: {detail}",
        }
    ]


def normalize_gate_id(gate_id: str) -> str:
    v2_aliases = {
        "specify-complete": "specify-complete",
        "plan-complete": "plan-complete",
        "tasks-complete": "tasks-complete",
        "implement-1-build": "build-1-implementation",
        "implement-2-verify": "assure-1-verification",
        "implement-3-integrate": "assure-2-integration",
        "implement-4-qa": "assure-3-qa",
        "implement-5-pr": "assure-4-pr-reviewer",
    }
    return v2_aliases.get(gate_id, gate_id)


def check_clarity(lifecycle: dict | None) -> list[dict]:
    if not lifecycle:
        return [{"id": "lifecycle_state", "status": "warn", "message": "lifecycle state.json missing"}]
    clarity = lifecycle.get("clarity") or {}
    score = clarity.get("overall") or clarity.get("score")
    threshold = clarity.get("threshold") or 70
    if score is None:
        return [{"id": "clarity_score", "status": "warn", "message": "clarity score not set"}]
    status = "pass" if int(score) >= int(threshold) else "warn"
    return [
        {
            "id": "clarity_threshold",
            "status": status,
            "message": f"clarity {score} vs threshold {threshold}",
        }
    ]


GATE_HANDLERS = {
    "build-1-implementation": check_build_implementation,
    "assure-2-integration": check_assure_integration,
    "assure-3-qa": None,
    "assure-4-pr-reviewer": None,
}


def aggregate_status(checks: list[dict]) -> str:
    if any(c.get("status") == "fail" for c in checks):
        return "fail"
    if any(c.get("status") == "warn" for c in checks):
        return "warn"
    return "pass"


def append_evidence(workspace: Path, feature: str, event: dict) -> None:
    log_path = workspace / ".adlc5" / feature / "evidence" / "events.jsonl"
    if not log_path.parent.is_dir():
        return
    line = json.dumps(event, separators=(",", ":"))
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature", required=True)
    parser.add_argument("--gate", default="build-1-implementation")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--write-gate-summary", action="store_true", help="Update delivery verification_summary.gates")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    os.environ["ADLC5_WORKSPACE"] = str(workspace)
    delivery_path = delivery_state_path(workspace, args.feature)
    lifecycle_path = workspace / ".adlc5" / args.feature / "state.json"

    lifecycle = load_json(lifecycle_path)
    policies = load_policies(workspace, args.feature)
    gate_id = normalize_gate_id(args.gate)

    if is_v2_state(lifecycle):
        delivery = v2_to_delivery_compat(lifecycle)
        phase = lifecycle.get("current_step", "")
    else:
        delivery = load_delivery_state(workspace, args.feature)
        if delivery is None:
            print(
                json.dumps(
                    {"gate": args.gate, "status": "fail", "error": "delivery state missing", "checks": []},
                    indent=2,
                )
            )
            return 3
        phase = delivery.get("current_phase", "")

    emit_telemetry(args.feature, "script.start", "ok", phase, {"gate": args.gate})

    checks: list[dict] = []
    if gate_id == "specify-complete" and lifecycle and is_v2_state(lifecycle):
        checks.extend(check_v2_specify_complete(workspace, args.feature, lifecycle))
    elif gate_id == "plan-complete" and lifecycle and is_v2_state(lifecycle):
        checks.extend(check_v2_plan_complete(workspace, args.feature, lifecycle, policies))
    elif gate_id == "tasks-1-stories-complete" and lifecycle and is_v2_state(lifecycle):
        checks.extend(check_v2_tasks_stories_complete(workspace, args.feature, lifecycle))
    elif gate_id == "tasks-2-code-spec-complete" and lifecycle and is_v2_state(lifecycle):
        checks.extend(check_v2_tasks_code_spec_complete(workspace, args.feature, lifecycle))
    elif gate_id == "tasks-complete" and lifecycle and is_v2_state(lifecycle):
        checks.extend(check_v2_tasks_complete(workspace, args.feature, lifecycle))
    elif args.gate == "pr-ready":
        checks.extend(check_pr_ready(workspace, args.feature, delivery, lifecycle, policies))
    elif args.gate == "deploy-ready":
        checks.extend(check_deploy_ready(workspace, args.feature, lifecycle))
    elif gate_id == "assure-1-verification":
        checks.extend(check_assure_verification(delivery, workspace, args.feature))
        checks.extend(check_verifier_independence(lifecycle, policies))
        if lifecycle and is_v2_state(lifecycle):
            checks.extend(check_anchor_integrity(workspace, args.feature, policies))
            checks.extend(check_deterministic_verify(workspace, args.feature, lifecycle))
    elif gate_id == "assure-3-qa":
        checks.extend(check_assure_qa(workspace, args.feature))
    elif gate_id in ("assure-4-pr-reviewer", "assure-4-pr-review"):
        checks.extend(check_assure_pr_review(lifecycle))
    elif gate_id == "build-1-implementation" and profile_name(policies) == "tiny":
        checks.extend(check_quality_gates(workspace, args.feature, policies, strict=True))
    elif gate_id in GATE_HANDLERS and GATE_HANDLERS[gate_id]:
        checks.extend(GATE_HANDLERS[gate_id](delivery))  # type: ignore[operator]
    elif gate_id.startswith("plan") or gate_id.startswith("specify"):
        checks.extend(check_plan_gate(delivery, gate_id, workspace, args.feature))
        checks.extend(check_clarity(lifecycle))
    else:
        handler = GATE_HANDLERS.get(gate_id)
        if handler:
            checks.extend(handler(delivery))
        else:
            checks.append({"id": "unknown_gate", "status": "warn", "message": f"no handler for gate {args.gate}"})

    if not (args.gate == "pr-ready" or args.gate.startswith("custom")):
        if normalize_custom_gates(policies) and args.gate in (
            "assure-1-verification",
            "build-1-implementation",
        ):
            checks.extend(check_custom_gates(workspace, args.feature, policies, strict=False))

    if lifecycle and is_v2_state(lifecycle):
        checks.extend(check_persona_context_gate(workspace, args.feature, lifecycle, policies))

    status = aggregate_status(checks)
    out = {
        "gate": args.gate,
        "status": status,
        "checks": checks,
        "feature": args.feature,
        "schema_version": lifecycle.get("schema_version") if lifecycle else "1.0",
    }
    print(json.dumps(out, indent=2))
    emit_telemetry(args.feature, "script.end", status, phase, out)
    if lifecycle and is_v2_state(lifecycle):
        append_evidence(
            workspace,
            args.feature,
            {
                "event": "gate_check",
                "gate": args.gate,
                "status": status,
                "step": lifecycle.get("current_step"),
                "stage": lifecycle.get("current_stage"),
            },
        )

    if args.write_gate_summary and any(c["id"].startswith("custom_gate_") for c in checks):
        update_delivery_gate_summary(delivery_path, checks)

    if status == "pass":
        return 0
    if status == "warn":
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
