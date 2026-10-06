#!/usr/bin/env python3
"""Fail-fast ADLC5 engagement gate.

Catches the "scaffold exists, framework never actually ran" failure mode while
a session is still cheap -- not hours and hundreds of dollars later.

Two detection paths, one decision core:

1. Live (`session-edit` / `scan`): platform hooks feed each mutating tool call
   here. Once a session has touched enough distinct substantive files with no
   ADLC5 feature engaged for that conversation, the gate pushes a loud message
   back into the same agent turn through the platform's agent-message channel.
2. Backstop (`check-branch`): a git pre-push hook for sessions that never went
   through a hook at all (manual commits, non-agent editors).

"Engaged" deliberately means more than "a binding row exists": the bound
feature must also have a real `state.json`. A feature directory that was
scaffolded and abandoned -- bindings written with `stage: null, step: null`,
every subdirectory empty -- is exactly the bypass this gate exists to catch,
so it is reported as `scaffold-only`, not as engagement.

Default posture is warn, never block (`ADLC5_ENGAGEMENT_GATE=enforce` opts
into denying the tool call). Every failure path fails open.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import agent_usage_common as common  # noqa: E402
from lib import simple_yaml  # noqa: E402

# --- Thresholds -------------------------------------------------------------
#
# Counted unit is DISTINCT substantive files touched in a session, not raw edit
# events: iterating twenty times on one file is a tweak, while spreading edits
# across several files is the shape of feature work. That distinction is what
# keeps the gate quiet on legitimately small changes.
#
# 4 is the first-warn bar because 1-2 files is a typo/chore, 3 is the common
# benign triple (implementation + its test + an export/registration), and 4+
# distinct files is the size at which ADLC5 code specs would normally carry
# `files_to_create`/`files_to_modify` frontmatter -- i.e. story-sized work that
# should have had a design pin it. Four files is also still only a few dollars
# of tokens, which is the whole point: fail fast, not fail expensive.
FIRST_WARN_FILES = 4

# After the first warning, re-warn every N further distinct files so the signal
# escalates instead of being a single scrollable-past line.
ESCALATE_EVERY_FILES = 3

MUTATING_TOOLS = {
    "Write",
    "StrReplace",
    "Delete",
    "EditNotebook",
    "search_replace",
    "write",
    "delete_file",
    "edit_notebook",
    "Edit",
    "MultiEdit",
    "NotebookEdit",
    "apply_patch",
}

# Directories whose contents are never feature work: VCS/tooling metadata,
# ADLC5's own lifecycle artifacts, and dependency/build output.
EXCLUDED_DIR_PARTS = {
    ".git",
    ".adlc5",
    ".cursor",
    ".claude",
    ".codex",
    ".agent-cache",
    ".agents",
    ".discover",
    ".prt",
    ".qa",
    ".worktrees",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    "target",
    "vendor",
}

# Prose and generated artifacts are excluded from the substantive count.
# Markdown is the deliberate judgment call: ADLC5's own gate artifacts (design
# docs, code specs, spec-handoff) are markdown, so counting it would make the
# gate fire on the framework doing its job. Documentation-only sessions are
# therefore not caught live -- the git backstop still sees them at push time.
EXCLUDED_SUFFIXES = {
    ".md",
    ".markdown",
    ".rst",
    ".txt",
    ".log",
    ".lock",
    ".snap",
    ".map",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".pdf",
}

EXCLUDED_BASENAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Cargo.lock",
    "go.sum",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    "LICENSE",
}

DEFAULT_BRANCH_PREFIX = "feat"
MODE_OFF = "off"
MODE_WARN = "warn"
MODE_ENFORCE = "enforce"


# --- Workspace helpers ------------------------------------------------------


def adlc5_installed(workspace: Path) -> bool:
    return (workspace / ".adlc5").is_dir()


def load_workspace_config(workspace: Path) -> dict[str, Any]:
    path = workspace / ".adlc5" / "config.yaml"
    if not path.is_file():
        return {}
    try:
        value = simple_yaml.parse(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def resolve_mode(workspace: Path) -> str:
    """Env wins, then `.adlc5/config.yaml` -> `engagement_gate.mode`, else warn.

    Mirrors scope-guard's env-overrides-config precedence so both guards are
    toggled the same way.
    """
    env = (os.environ.get("ADLC5_ENGAGEMENT_GATE") or "").strip().lower()
    if env in (MODE_OFF, "0", "false", "disable", "disabled"):
        return MODE_OFF
    if env in (MODE_ENFORCE, "deny", "block", "hard"):
        return MODE_ENFORCE
    if env == MODE_WARN:
        return MODE_WARN

    section = load_workspace_config(workspace).get("engagement_gate")
    if isinstance(section, dict):
        configured = str(section.get("mode") or "").strip().lower()
        if configured in (MODE_OFF, "0", "false", "disable", "disabled"):
            return MODE_OFF
        if configured in (MODE_ENFORCE, "deny", "block", "hard"):
            return MODE_ENFORCE
    return MODE_WARN


def branch_prefix(workspace: Path) -> str:
    value = load_workspace_config(workspace).get("git_branch_prefix")
    if isinstance(value, str) and value.strip():
        return value.strip().strip("/")
    return DEFAULT_BRANCH_PREFIX


# --- Substantive-path filtering --------------------------------------------


def relative_path(workspace: Path, raw: str) -> str | None:
    candidate = Path(raw)
    absolute = candidate if candidate.is_absolute() else workspace / candidate
    try:
        return absolute.resolve().relative_to(workspace.resolve()).as_posix()
    except (ValueError, OSError):
        return None


def is_substantive(rel: str) -> bool:
    path = Path(rel)
    if any(part in EXCLUDED_DIR_PARTS for part in path.parts[:-1]):
        return False
    if path.name in EXCLUDED_BASENAMES:
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    # Root-level dotfiles are config chores, not feature work.
    if len(path.parts) == 1 and path.name.startswith("."):
        return False
    return True


def substantive_paths(workspace: Path, raws: list[str]) -> list[str]:
    results: list[str] = []
    for raw in raws:
        if not isinstance(raw, str) or not raw.strip():
            continue
        rel = relative_path(workspace, raw.strip())
        if rel and is_substantive(rel):
            results.append(rel)
    return results


def worktree_paths(workspace: Path) -> list[str]:
    """Distinct changed files in the git working tree (uncommitted work).

    Used by platforms without a per-tool-call hook: the same signal, derived at
    prompt-submit time instead of edit time.
    """
    try:
        completed = subprocess.run(
            ["git", "-C", str(workspace), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0:
        return []
    paths: list[str] = []
    for line in completed.stdout.splitlines():
        entry = line[3:].strip() if len(line) > 3 else ""
        if not entry:
            continue
        # Renames are reported as "old -> new"; the new path is what matters.
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        paths.append(entry.strip().strip('"'))
    return paths


# --- Session state ----------------------------------------------------------


def state_path(workspace: Path, platform: str, session_id: str) -> Path:
    digest = hashlib.sha256(f"{platform}:{session_id}".encode("utf-8")).hexdigest()[:16]
    return workspace / ".adlc5" / "engagement-gate" / f"{platform}-{digest}.json"


def load_session(workspace: Path, platform: str, session_id: str) -> dict[str, Any]:
    path = state_path(workspace, platform, session_id)
    if not path.is_file():
        return {
            "session_id": session_id,
            "platform": platform,
            "files": [],
            "last_warn_count": 0,
            "acknowledged": False,
            "acknowledged_reason": None,
        }
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        value = {}
    if not isinstance(value, dict):
        value = {}
    value.setdefault("session_id", session_id)
    value.setdefault("platform", platform)
    value.setdefault("files", [])
    value.setdefault("last_warn_count", 0)
    value.setdefault("acknowledged", False)
    value.setdefault("acknowledged_reason", None)
    return value


def save_session(workspace: Path, session: dict[str, Any]) -> None:
    session["updated_at_ms"] = common.now_ms()
    common.write_json(
        state_path(workspace, str(session["platform"]), str(session["session_id"])), session
    )


# --- Engagement detection ---------------------------------------------------


def has_real_state(feature_dir: Path) -> bool:
    """A truncated or empty `state.json` is scaffold, not lifecycle state."""
    path = feature_dir / "state.json"
    if not path.is_file():
        return False
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return isinstance(value, dict) and bool(value)


def feature_has_state(workspace: Path, feature: str) -> bool:
    """An archived feature is engagement, not a bypass -- check both trees."""
    if has_real_state(workspace / ".adlc5" / feature):
        return True
    archive = workspace / ".adlc5" / "_archive"
    if archive.is_dir():
        for candidate in archive.glob(f"{feature}-*"):
            if has_real_state(candidate):
                return True
        if has_real_state(archive / feature):
            return True
    return False


def engagement_status(workspace: Path, platform: str, session_id: str) -> tuple[str, str | None]:
    """Return (status, feature) where status is engaged|scaffold-only|unbound."""
    try:
        bindings = common.discover_bindings(platform, workspace)
    except OSError:
        bindings = []
    mine = [
        binding
        for binding in bindings
        if session_id and str(binding.get("conversation_id") or "") == session_id
    ]
    if not mine:
        return "unbound", None
    latest = max(mine, key=lambda item: common.parse_int(item.get("bound_at_ms", 0)) or 0)
    feature = str(latest.get("feature") or "").strip()
    if not feature:
        return "unbound", None
    if feature_has_state(workspace, feature):
        return "engaged", feature
    return "scaffold-only", feature


# --- Message composition ----------------------------------------------------


def compose_message(status: str, feature: str | None, count: int, escalated: bool) -> str:
    banner = "ADLC5 ENGAGEMENT GATE" + (" (still unresolved)" if escalated else "")
    if status == "scaffold-only":
        headline = (
            f"{count} distinct source files edited in this session, and the bound "
            f'ADLC5 feature "{feature}" has no state.json — its scaffold exists but '
            "Specify never completed, so nothing is gating this work."
        )
        remedy = (
            f"Either resume the lifecycle (`@adlc5 for {feature}`) so a design pins the "
            "contract before more code is written, or acknowledge that this is "
            "intentionally ad-hoc work."
        )
    else:
        headline = (
            f"{count} distinct source files edited in this session with no ADLC5 "
            "feature engaged for this conversation."
        )
        remedy = (
            "Either bind one (`@adlc5 for <feature-name>`) so the work gets a spec, "
            "design, and gates, or acknowledge that this is intentionally ad-hoc "
            "work (chore/hotfix/exploration)."
        )
    return (
        f"=== {banner} ===\n"
        f"{headline}\n"
        f"{remedy}\n"
        "Tell the user which one it is before continuing — do not silently keep editing. "
        "To silence this for the rest of the session after the user confirms it is "
        "intentional, run: "
        "`./scripts/engagement-gate.py ack --workspace . --session-id <id> "
        "--platform <platform> --reason '<why>'`"
    )


def emit(payload_format: str, mode: str, message: str | None) -> None:
    """Print the platform-appropriate hook response. Always exits 0."""
    if payload_format == "cursor":
        if message and mode == MODE_ENFORCE:
            print(
                json.dumps(
                    {
                        "permission": "deny",
                        "user_message": message,
                        "agent_message": message,
                    }
                )
            )
            return
        if message:
            print(json.dumps({"permission": "allow", "agent_message": message}))
            return
        print(json.dumps({"permission": "allow"}))
        return

    if payload_format == "claude":
        specific: dict[str, Any] = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny" if (message and mode == MODE_ENFORCE) else "allow",
        }
        if message:
            specific["permissionDecisionReason"] = message
            specific["additionalContext"] = message
        print(json.dumps({"hookSpecificOutput": specific}))
        return

    # plain: stdout is surfaced to the agent/user as-is (Codex, git hooks, CLI).
    if message:
        print(message)


# --- Commands ---------------------------------------------------------------


def evaluate_session(
    workspace: Path,
    platform: str,
    session_id: str,
    paths: list[str],
    *,
    replace: bool,
) -> tuple[str, str | None]:
    """Record paths against the session and decide whether to warn.

    Returns (mode, message). `replace` is for worktree scans, where the scanned
    set is authoritative rather than incremental.
    """
    mode = resolve_mode(workspace)
    if mode == MODE_OFF or not adlc5_installed(workspace) or not session_id:
        return mode, None

    status, feature = engagement_status(workspace, platform, session_id)
    session = load_session(workspace, platform, session_id)

    new_paths = substantive_paths(workspace, paths)
    known = set(session.get("files") or [])
    files = sorted(set(new_paths)) if replace else sorted(known | set(new_paths))
    session["files"] = files
    session["status"] = status
    session["feature"] = feature

    if status == "engaged":
        # Engagement clears the warning ledger: binding late is the desired
        # outcome, and the session should not keep nagging afterwards.
        session["last_warn_count"] = 0
        save_session(workspace, session)
        return mode, None

    count = len(files)
    last = common.parse_int(session.get("last_warn_count")) or 0
    if session.get("acknowledged") or count < FIRST_WARN_FILES:
        save_session(workspace, session)
        return mode, None
    if last and count < last + ESCALATE_EVERY_FILES:
        save_session(workspace, session)
        return mode, None

    session["last_warn_count"] = count
    save_session(workspace, session)
    return mode, compose_message(status, feature, count, escalated=bool(last))


def read_hook_payload() -> dict[str, Any]:
    if sys.stdin is None or sys.stdin.isatty():
        return {}
    try:
        raw = sys.stdin.read()
    except OSError:
        return {}
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def payload_paths(payload: dict[str, Any]) -> list[str]:
    tool_input = payload.get("tool_input") or payload.get("arguments") or {}
    if not isinstance(tool_input, dict):
        return []
    paths: list[str] = []
    for key in ("path", "file_path", "filePath", "target_notebook", "notebook_path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            paths.append(value.strip())
    value = tool_input.get("paths")
    if isinstance(value, list):
        paths.extend(item for item in value if isinstance(item, str) and item.strip())
    return paths


def payload_session_id(payload: dict[str, Any]) -> str:
    for key in ("conversation_id", "session_id", "sessionId", "conversationId", "thread_id"):
        value = payload.get(key)
        if value:
            return str(value)
    return ""


def payload_tool(payload: dict[str, Any]) -> str:
    return str(payload.get("tool_name") or payload.get("toolName") or "").strip()


def cmd_session_edit(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    payload = read_hook_payload()
    tool = args.tool or payload_tool(payload)
    session_id = args.session_id or payload_session_id(payload)
    paths = list(args.path or []) + payload_paths(payload)

    # Non-mutating tools never count; an unknown/empty tool name still counts if
    # explicit paths were supplied (CLI use and future hook shapes).
    if tool and tool not in MUTATING_TOOLS:
        emit(args.emit, MODE_WARN, None)
        return 0

    mode, message = evaluate_session(workspace, args.platform, session_id, paths, replace=False)
    emit(args.emit, mode, message)
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    payload = read_hook_payload()
    session_id = args.session_id or payload_session_id(payload)
    mode, message = evaluate_session(
        workspace, args.platform, session_id, worktree_paths(workspace), replace=True
    )
    emit(args.emit, mode, message)
    return 0


def cmd_ack(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    session = load_session(workspace, args.platform, args.session_id)
    session["acknowledged"] = True
    session["acknowledged_reason"] = args.reason or "unspecified"
    save_session(workspace, session)
    print(
        json.dumps(
            {
                "status": "ok",
                "acknowledged": True,
                "session_id": args.session_id,
                "platform": args.platform,
                "reason": session["acknowledged_reason"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    status, feature = engagement_status(workspace, args.platform, args.session_id)
    session = load_session(workspace, args.platform, args.session_id)
    print(
        json.dumps(
            {
                "mode": resolve_mode(workspace),
                "engagement": status,
                "feature": feature,
                "distinct_files": len(session.get("files") or []),
                "first_warn_files": FIRST_WARN_FILES,
                "acknowledged": bool(session.get("acknowledged")),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


# --- Git backstop -----------------------------------------------------------


def git_output(workspace: Path, arguments: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(workspace), *arguments],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def current_branch(workspace: Path) -> str:
    return git_output(workspace, ["rev-parse", "--abbrev-ref", "HEAD"]) or ""


def branch_commit_count(workspace: Path, branch: str) -> int:
    """Commits unique to this branch relative to the closest known base."""
    for base in ("origin/main", "origin/master", "main", "master", "origin/develop"):
        if git_output(workspace, ["rev-parse", "--verify", "--quiet", base]) is None:
            continue
        merge_base = git_output(workspace, ["merge-base", "HEAD", base])
        if not merge_base:
            continue
        count = git_output(workspace, ["rev-list", "--count", f"{merge_base}..HEAD"])
        if count is not None and count.isdigit():
            return int(count)
    count = git_output(workspace, ["rev-list", "--count", "HEAD"])
    return int(count) if count and count.isdigit() else 0


def cmd_check_branch(args: argparse.Namespace) -> int:
    """Warn-only backstop. Always exits 0 -- pushing is never blocked here."""
    workspace = Path(args.workspace).resolve()
    if resolve_mode(workspace) == MODE_OFF or not adlc5_installed(workspace):
        return 0

    branch = args.branch or current_branch(workspace)
    prefix = args.branch_prefix or branch_prefix(workspace)
    if not branch or not branch.startswith(f"{prefix}/"):
        return 0

    slug = branch[len(prefix) + 1 :].strip("/")
    if not slug or feature_has_state(workspace, slug):
        return 0

    commits = branch_commit_count(workspace, branch)
    if commits < 1:
        return 0

    scaffolded = (workspace / ".adlc5" / slug).is_dir()
    detail = (
        f'".adlc5/{slug}/" exists but has no state.json — the scaffold was created '
        "and then bypassed."
        if scaffolded
        else f'no ".adlc5/{slug}/" feature was ever created.'
    )
    print(
        "=== ADLC5 ENGAGEMENT GATE (pre-push backstop) ===\n"
        f"Branch \"{branch}\" has {commits} commit(s), and {detail}\n"
        "Nothing gated this work: no spec-handoff pinned the contract and no design "
        "critique or story verification ran against it.\n"
        "This is a warning, not a block — the push continues. If this branch is real "
        f"feature work, run `@adlc5 for {slug}` before the next round of changes.",
        file=sys.stderr,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(target: argparse.ArgumentParser) -> None:
        target.add_argument("--workspace", default=".")
        target.add_argument("--platform", default="cursor")
        target.add_argument("--session-id", default="")

    session_edit = subparsers.add_parser(
        "session-edit", help="Record one mutating tool call and decide whether to warn"
    )
    add_common(session_edit)
    session_edit.add_argument("--path", action="append", default=[])
    session_edit.add_argument("--tool", default="")
    session_edit.add_argument("--emit", choices=["cursor", "claude", "plain"], default="cursor")
    session_edit.set_defaults(func=cmd_session_edit)

    scan = subparsers.add_parser(
        "scan", help="Derive the session's touched-file set from the git working tree"
    )
    add_common(scan)
    scan.add_argument("--emit", choices=["cursor", "claude", "plain"], default="plain")
    scan.set_defaults(func=cmd_scan)

    ack = subparsers.add_parser("ack", help="Acknowledge intentionally ad-hoc work")
    add_common(ack)
    ack.add_argument("--reason", default="")
    ack.set_defaults(func=cmd_ack)

    status = subparsers.add_parser("status", help="Report the gate's view of a session")
    add_common(status)
    status.set_defaults(func=cmd_status)

    check_branch = subparsers.add_parser(
        "check-branch", help="Pre-push backstop: warn on ungated feature branches"
    )
    check_branch.add_argument("--workspace", default=".")
    check_branch.add_argument("--branch", default="")
    check_branch.add_argument("--branch-prefix", default="")
    check_branch.set_defaults(func=cmd_check_branch)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as error:  # fail open: a broken guard must never block work
        print(f"engagement-gate: {error}", file=sys.stderr)
        if getattr(args, "emit", None):
            emit(args.emit, MODE_WARN, None)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
