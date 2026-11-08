"""Track owner profile per feature in .adlc5/_ownership.json. Stdlib only."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

OWNERSHIP_FILE = "_ownership.json"


def workspace_root(start: Path | None = None) -> Path:
    p = (start or Path.cwd()).resolve()
    if (p / ".adlc5").is_dir():
        return p
    if (p.parent / ".adlc5").is_dir():
        return p.parent
    return p


def ownership_path(workspace: Path | None = None) -> Path:
    return workspace_root(workspace) / ".adlc5" / OWNERSHIP_FILE


def _empty() -> dict[str, str]:
    return {}


def load(workspace: Path | None = None) -> dict[str, str]:
    path = ownership_path(workspace)
    if not path.is_file():
        return _empty()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty()
    if not isinstance(data, dict):
        return _empty()
    return {str(k): str(v) for k, v in data.items() if isinstance(v, str)}


def save(data: dict[str, str], workspace: Path | None = None) -> None:
    path = ownership_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def set_owner(feature: str, owner: str, workspace: Path | None = None) -> None:
    data = load(workspace)
    data[feature] = owner
    save(data, workspace)


def get_owner(feature: str, workspace: Path | None = None) -> str | None:
    return load(workspace).get(feature)


def list_owners(workspace: Path | None = None) -> dict[str, str]:
    return dict(load(workspace))


def check(feature: str, actor: str, workspace: Path | None = None) -> bool:
    owner = get_owner(feature, workspace=workspace)
    return owner is None or owner == actor


def _cli(argv: list[str]) -> int:
    if not argv:
        print("usage: feature_ownership set|get|list|check ...", file=sys.stderr)
        return 2
    cmd = argv[0]
    if cmd == "set":
        if len(argv) < 3:
            print("usage: feature_ownership set <feature> <owner>", file=sys.stderr)
            return 2
        set_owner(argv[1], argv[2])
        print(f"set {argv[1]} -> {argv[2]}")
        return 0
    if cmd == "get":
        if len(argv) < 2:
            print("usage: feature_ownership get <feature>", file=sys.stderr)
            return 2
        o = get_owner(argv[1])
        print(o if o is not None else "(none)")
        return 0
    if cmd == "list":
        data = list_owners()
        if not data:
            print("(no owners)")
            return 0
        for k in sorted(data):
            print(f"{k}: {data[k]}")
        return 0
    if cmd == "check":
        if len(argv) < 3:
            print("usage: feature_ownership check <feature> <actor>", file=sys.stderr)
            return 2
        ok = check(argv[1], argv[2])
        print("OK" if ok else "DENIED")
        return 0 if ok else 1
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


def _self_check() -> None:
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        (ws / ".adlc5").mkdir()
        assert get_owner("f", workspace=ws) is None
        set_owner("f", "alice", workspace=ws)
        assert get_owner("f", workspace=ws) == "alice"
        assert check("f", "alice", workspace=ws) is True
        assert check("f", "bob", workspace=ws) is False
        assert check("g", "anyone", workspace=ws) is True
        assert list_owners(workspace=ws) == {"f": "alice"}


if __name__ == "__main__":
    if not sys.argv[1:]:
        _self_check()
        print("self-check: OK")
        sys.exit(0)
    if sys.argv[1] == "--self-check":
        _self_check()
        print("self-check: OK")
        sys.exit(0)
    sys.exit(_cli(sys.argv[1:]))