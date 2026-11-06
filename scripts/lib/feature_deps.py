"""Minimal registry of dependencies between ADLC5 features.

Stored as JSON at ``<workspace>/.adlc5/_deps.json``. Stdlib only.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

DEPS_FILE = "_deps.json"


def workspace_root(start: Path | None = None) -> Path:
    p = (start or Path.cwd()).resolve()
    if (p / ".adlc5").is_dir():
        return p
    if (p.parent / ".adlc5").is_dir():
        return p.parent
    return p


def deps_path(workspace: Path | None = None) -> Path:
    return workspace_root(workspace) / ".adlc5" / DEPS_FILE


def _empty() -> dict[str, list[str]]:
    return {}


def load(workspace: Path | None = None) -> dict[str, list[str]]:
    path = deps_path(workspace)
    if not path.is_file():
        return _empty()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty()
    if not isinstance(data, dict):
        return _empty()
    out: dict[str, list[str]] = {}
    for k, v in data.items():
        if isinstance(v, list):
            out[str(k)] = [str(x) for x in v]
    return out


def save(data: dict[str, list[str]], workspace: Path | None = None) -> None:
    path = deps_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def add(depender: str, dependency: str, workspace: Path | None = None) -> None:
    data = load(workspace)
    deps = data.setdefault(depender, [])
    if dependency not in deps:
        deps.append(dependency)
    save(data, workspace)


def remove(depender: str, dependency: str | None = None, workspace: Path | None = None) -> None:
    data = load(workspace)
    if dependency is None:
        data.pop(depender, None)
    else:
        deps = data.get(depender, [])
        data[depender] = [d for d in deps if d != dependency]
        if not data[depender]:
            data.pop(depender, None)
    save(data, workspace)


def dependencies_of(feature: str, workspace: Path | None = None) -> list[str]:
    return list(load(workspace).get(feature, []))


def dependents_of(feature: str, workspace: Path | None = None) -> list[str]:
    data = load(workspace)
    return [k for k, v in data.items() if feature in v]


def validate(workspace: Path | None = None) -> list[list[str]]:
    """Return list of cycles (each a list of feature names); empty means valid."""
    data = load(workspace)
    cycles: list[list[str]] = []
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n: WHITE for n in data}
    for n in list(data):
        color.setdefault(n, WHITE)
    for n in list(data):
        for d in data.get(n, []):
            color.setdefault(d, WHITE)

    path: list[str] = []

    def dfs(node: str) -> None:
        color[node] = GRAY
        path.append(node)
        for dep in data.get(node, []):
            if dep not in color:
                color[dep] = WHITE
            if color.get(dep, WHITE) == WHITE:
                dfs(dep)
            elif color.get(dep, WHITE) == GRAY:
                # cycle found
                idx = path.index(dep) if dep in path else -1
                cyc = path[idx:] + [dep]
                if cyc not in cycles:
                    cycles.append(cyc)
        path.pop()
        color[node] = BLACK

    for node in list(color):
        if color.get(node, WHITE) == WHITE:
            dfs(node)
    return cycles


def _cli(argv: list[str]) -> int:
    cmd = argv[0] if argv else "list"
    if cmd == "add":
        if len(argv) < 3:
            print("usage: feature_deps add <depender> <dependency>", file=sys.stderr)
            return 2
        add(argv[1], argv[2])
        print(f"added {argv[1]} -> {argv[2]}")
        return 0
    if cmd == "remove":
        if len(argv) < 2:
            print("usage: feature_deps remove <depender> [dependency]", file=sys.stderr)
            return 2
        remove(argv[1], argv[2] if len(argv) > 2 else None)
        print("removed")
        return 0
    if cmd == "list":
        data = load()
        if not data:
            print("(no dependencies)")
            return 0
        for k in sorted(data):
            for d in data[k]:
                print(f"{k} -> {d}")
        return 0
    if cmd == "check":
        cycles = validate()
        if cycles:
            for c in cycles:
                print("CYCLE: " + " -> ".join(c))
            return 1
        print("OK: no cycles")
        return 0
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


def _self_check() -> None:
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        (ws / ".adlc5").mkdir()
        add("A", "B", workspace=ws)
        add("B", "C", workspace=ws)
        add("C", "A", workspace=ws)
        cycles = validate(workspace=ws)
        assert cycles, "expected cycle not detected"
        # non-cycle case
        ws2 = Path(tempfile.mkdtemp())
        (ws2 / ".adlc5").mkdir()
        add("X", "Y", workspace=ws2)
        assert not validate(workspace=ws2)
        import shutil
        shutil.rmtree(ws2, ignore_errors=True)


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