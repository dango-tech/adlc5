"""Mechanical checks for the opening Specify step."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
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


def untracked_feature_runtime(workspace: Path, feature: str, relative_path: str) -> bool:
    parts = Path(relative_path).parts
    if len(parts) < 3 or parts[0] != ".adlc5" or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", parts[1]):
        return False
    state = workspace / ".adlc5" / parts[1] / "state.json"
    return state.resolve() == state and (parts[1] == feature or state.is_file())


def place_worktree_state(workspace: Path, feature: str, metadata: dict) -> dict:
    """Resume a bound worktree or copy opening state into an unused destination."""
    source = feature_path(workspace, feature)
    target_workspace = Path(metadata["worktree_path"]).resolve()
    target = feature_path(target_workspace, feature)
    binding = git_binding(target_workspace)
    if (binding["git_common_dir"] != git_binding(workspace)["git_common_dir"]
            or binding["git_dir"] == binding["git_common_dir"]
            or binding["branch"] != metadata["branch_name"]):
        raise BootstrapBlocked("worktree_binding_mismatch", target_workspace, "Open the intended linked worktree.")
    metadata = dict(metadata, worktree_path=str(target_workspace), repository_root=str(target_workspace))
    patch = {"git": metadata}
    if target == source:
        return metadata
    if target.exists():
        existing = load_feature_state(target_workspace, feature) or {}
        if (existing.get("git") or {}).get("isolation") != "worktree" or (
                existing.get("git") or {}).get("worktree_path") != str(target_workspace):
            raise BootstrapBlocked("worktree_state_exists", target, "Inspect the existing destination feature state.")
        check_binding(target_workspace, existing, binding)
        return {key: existing["git"].get(key, value) for key, value in metadata.items()}
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.mkdir()
        shutil.copytree(source, target, dirs_exist_ok=True, symlinks=True,
                        ignore=shutil.ignore_patterns("runner.lock", "runner.lock.guard"))
        subprocess.run([sys.executable, str(ROOT / "scripts/adlc5"), "state", "set",
                        "--feature", feature, "--workspace", str(target_workspace), "--patch", json.dumps(patch)],
                       check=True, stdout=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BootstrapBlocked("worktree_state_transfer_failed", target,
                               "Inspect and preserve destination feature files. Use the retained source state "
                               "to complete the transfer, then resume in the linked worktree.",
                               source=str(source)) from exc
    return metadata
