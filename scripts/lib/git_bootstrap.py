"""Mechanical checks for the opening Specify step."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from lib.package_guard import check_workspace
from lib.state_v2 import atomic_write_json, load_feature_state

ROOT = Path(__file__).resolve().parents[2]
STEP = "specify-0-git"


class BootstrapBlocked(RuntimeError):
    def __init__(self, condition: str, path: Path, next_action: str, **evidence):
        super().__init__(next_action)
        self.diagnostic = {
            "status": "blocked", "step": STEP, "condition": condition,
            "path": str(path), "next_action": next_action, "evidence": evidence,
        }


def feature_path(workspace: Path, feature: str) -> Path:
    if check_workspace(ROOT, workspace):
        raise BootstrapBlocked("workspace_unavailable", workspace, "Select a writable consumer workspace.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", feature):
        raise BootstrapBlocked("invalid_feature", workspace, "Use a kebab-case feature name.")
    path = workspace / ".adlc5" / feature
    for candidate in (path.parent, path, path / "state.json", path / "pilot", path / "evidence"):
        if candidate.resolve() != candidate:
            raise BootstrapBlocked("redirected_feature_path", candidate,
                                   "Bind the feature to a local ADLC5 state directory.")
    return path


def git_binding(workspace: Path) -> dict:
    commands = (
        ("repository_root", "rev-parse", "--show-toplevel"),
        ("start_commit", "rev-parse", "--verify", "HEAD"),
        ("git_dir", "rev-parse", "--absolute-git-dir"),
        ("git_common_dir", "rev-parse", "--git-common-dir"),
        ("branch", "branch", "--show-current"),
    )
    evidence = {}
    for key, *command in commands:
        try:
            result = subprocess.run(["git", "-C", str(workspace), *command],
                                    text=True, capture_output=True, check=False)
        except FileNotFoundError as exc:
            raise BootstrapBlocked("missing_git", workspace, "Make Git available on PATH.", command="git") from exc
        if result.returncode:
            raise BootstrapBlocked("git_metadata_unavailable", workspace,
                                   "Open the Git worktree root and ensure HEAD and Git metadata are accessible.",
                                   command="git " + " ".join(command), exit_code=result.returncode)
        evidence[key] = result.stdout.strip()
    for key in ("repository_root", "git_dir", "git_common_dir"):
        evidence[key] = str((workspace / evidence[key]).resolve())
    if Path(evidence["repository_root"]) != workspace:
        raise BootstrapBlocked("workspace_not_git_root", workspace, "Open the Git worktree root and resume.", **evidence)
    return evidence


def check_binding(workspace: Path, state: dict, binding: dict) -> None:
    recorded = state.get("git") or {}
    if recorded.get("worktree_path") and Path(recorded["worktree_path"]).resolve() != workspace:
        raise BootstrapBlocked("worktree_binding_mismatch", workspace, "Resume in the recorded worktree.",
                               recorded_worktree=recorded["worktree_path"])
    expected = recorded.get("branch_name")
    if recorded.get("isolation") in {"branch", "worktree", "current"} and (not expected or expected != binding["branch"]):
        raise BootstrapBlocked("branch_binding_mismatch", workspace, "Resume on the recorded feature branch.",
                               recorded_branch=expected, current_branch=binding["branch"])
    if recorded.get("isolation") == "worktree" and binding["git_dir"] == binding["git_common_dir"]:
        raise BootstrapBlocked("linked_worktree_required", workspace, "Resume in the linked feature worktree.", **binding)


def evaluate(workspace: Path, feature: str) -> dict:
    try:
        feature_path(workspace, feature)
        state = load_feature_state(workspace, feature) or {}
        recorded = state.get("git") or {}
        isolation = recorded.get("isolation")
        if isolation in {"skip", "skipped", "waived"}:
            return {"status": "pass", "step": STEP, "evidence": {"isolation": "waived"}}
        if isolation not in {"branch", "worktree", "current"}:
            raise BootstrapBlocked("git_isolation_unrecorded", workspace,
                                   "Record a Git isolation choice, or explicitly waive Git isolation.")
        binding = git_binding(workspace)
        check_binding(workspace, state, binding)
        return {"status": "pass", "step": STEP, "evidence": binding}
    except BootstrapBlocked as exc:
        return exc.diagnostic


def record(workspace: Path, feature: str, result: dict) -> None:
    path = feature_path(workspace, feature) / "pilot" / "git-bootstrap.json"
    if path.is_symlink():
        raise BootstrapBlocked("redirected_bootstrap_record", path, "Use a local bootstrap record path.")
    try:
        atomic_write_json(path, result)
    except OSError as exc:
        raise BootstrapBlocked("state_unwritable", path.parent,
                               "Grant write access to the feature state directory and resume.") from exc
