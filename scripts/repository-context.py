#!/usr/bin/env python3
"""Initialize repository constitution files and build local repository intelligence."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TASK_SPEC_SCHEMA = ROOT / "templates" / "agent" / "schemas" / "task-spec.schema.json"
SCHEMA_VERSION = "1.0"
CONSTITUTION_DIR = ".agents"
LEGACY_CONSTITUTION_DIR = ".agent"
CONSTITUTION_FILES = ("architecture.yaml", "boundaries.yaml", "commands.yaml")
SCHEMA_REL = Path("schemas") / "task-spec.schema.json"

CODE_SUFFIXES = {
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".go": "go",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".kt": "kotlin",
    ".php": "php",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".scala": "scala",
    ".sh": "shell",
    ".swift": "swift",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".vue": "vue",
}
MANIFEST_NAMES = {
    "Cargo.toml",
    "go.mod",
    "package.json",
    "pnpm-workspace.yaml",
    "pom.xml",
    "pyproject.toml",
    "settings.gradle",
    "settings.gradle.kts",
}
EXCLUDED_PARTS = {
    ".adlc5",
    ".agent-cache",
    ".agents",
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
    "venv",
}
SECRET_NAMES = {
    ".env",
    ".npmrc",
    ".pypirc",
    "credentials",
    "credentials.json",
    "secrets.json",
}
SECRET_SUFFIXES = {".key", ".p12", ".pfx", ".pem"}
SECRET_STEMS = {"credential", "credentials", "secret", "secrets"}


def dump_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def command_output(*args: str, cwd: Path) -> str:
    proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def git_head(workspace: Path) -> str:
    return command_output("git", "rev-parse", "HEAD", cwd=workspace) or "none"


def relative_files(workspace: Path) -> list[Path]:
    output = command_output(
        "git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", cwd=workspace
    )
    candidates = [Path(item) for item in output.split("\0") if item] if output else []
    if not candidates:
        candidates = [path.relative_to(workspace) for path in workspace.rglob("*")]

    selected: list[Path] = []
    workspace_real = workspace.resolve()
    for rel in candidates:
        if any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        if (
            rel.name in SECRET_NAMES
            or rel.name.startswith(".env.")
            or rel.stem.lower() in SECRET_STEMS
            or rel.suffix.lower() in SECRET_SUFFIXES
        ):
            continue
        path = workspace / rel
        if path.is_symlink() or not path.is_file():
            continue
        try:
            path.resolve().relative_to(workspace_real)
        except ValueError:
            continue
        if path.suffix.lower() in CODE_SUFFIXES or path.name in MANIFEST_NAMES:
            selected.append(rel)
    return sorted(set(selected), key=lambda path: path.as_posix())


def snapshot_fingerprint(workspace: Path, files: list[Path]) -> str:
    digest = hashlib.sha256()
    for rel in files:
        digest.update(rel.as_posix().encode())
        digest.update(b"\0")
        digest.update((workspace / rel).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def add_cache_ignore(workspace: Path) -> None:
    gitignore = workspace / ".gitignore"
    current = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
    if any(line.strip() == ".agent-cache/" for line in current.splitlines()):
        return
    separator = "" if not current or current.endswith("\n") else "\n"
    gitignore.write_text(
        current + separator + "\n# ADLC5 generated repository intelligence\n.agent-cache/\n",
        encoding="utf-8",
    )


def yaml_scalar(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def detected_name(workspace: Path) -> str:
    package = workspace / "package.json"
    if package.is_file():
        try:
            return str(json.loads(package.read_text(encoding="utf-8")).get("name") or workspace.name)
        except (json.JSONDecodeError, OSError):
            pass
    return workspace.name


def source_roots(files: list[Path]) -> list[str]:
    roots = {
        rel.parts[0]
        for rel in files
        if rel.suffix.lower() in CODE_SUFFIXES
        and rel.parts
        and rel.parts[0] not in {"test", "tests", "spec", "specs"}
    }
    return sorted(roots)


def package_scripts(workspace: Path) -> dict[str, str]:
    package = workspace / "package.json"
    if not package.is_file():
        return {}
    try:
        scripts = json.loads(package.read_text(encoding="utf-8")).get("scripts", {})
    except (json.JSONDecodeError, OSError):
        return {}
    return {str(key): str(value) for key, value in scripts.items() if isinstance(value, str)}


def write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def constitution_relatives() -> list[Path]:
    return [Path(name) for name in CONSTITUTION_FILES] + [SCHEMA_REL]


def posix_under(root_name: str, rel: Path) -> str:
    return f"{root_name}/{rel.as_posix()}"


def list_top_level(path: Path) -> list[str]:
    if not path.is_dir():
        return []
    names: list[str] = []
    for child in sorted(path.iterdir(), key=lambda item: item.name):
        suffix = "/" if child.is_dir() else ""
        names.append(f"{path.name}/{child.name}{suffix}")
    return names


def constitution_report(workspace: Path) -> dict[str, object]:
    dest_root = workspace / CONSTITUTION_DIR
    legacy_root = workspace / LEGACY_CONSTITUTION_DIR
    constitution_names = {rel.parts[0] for rel in constitution_relatives()}
    kept_existing = [
        name
        for name in list_top_level(dest_root)
        if Path(name).name.rstrip("/") not in constitution_names
    ]
    leftover_legacy = [
        posix_under(LEGACY_CONSTITUTION_DIR, rel)
        for rel in constitution_relatives()
        if (legacy_root / rel).is_file()
    ]
    leftover_legacy_other = [
        name
        for name in list_top_level(legacy_root)
        if Path(name).name.rstrip("/") not in constitution_names
    ]
    return {
        "constitution_dir": CONSTITUTION_DIR,
        "kept_existing": kept_existing,
        "leftover_legacy": leftover_legacy,
        "leftover_legacy_other": leftover_legacy_other,
        "next_steps": [
            f"Review created or adopted files under {CONSTITUTION_DIR}/; fill unknown/draft values.",
            f"Keep existing {CONSTITUTION_DIR}/skills/ and any other non-constitution files in place.",
            "Do not copy Antigravity .agent/skills into .agents/skills; those hosts stay separate.",
            f"After validate succeeds, delete leftover constitution files under {LEGACY_CONSTITUTION_DIR}/ only.",
            f"Leave {LEGACY_CONSTITUTION_DIR}/skills/ alone if Antigravity uses it.",
            "Commit .agents/ constitution + docs/adr/; do not commit .agent-cache/.",
        ],
    }


def adopt_legacy_constitution(workspace: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    dest_root = workspace / CONSTITUTION_DIR
    legacy_root = workspace / LEGACY_CONSTITUTION_DIR
    adopted: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    if not legacy_root.is_dir():
        return adopted, skipped
    for rel in constitution_relatives():
        src = legacy_root / rel
        dest = dest_root / rel
        if not src.is_file():
            continue
        if dest.exists():
            skipped.append(
                {
                    "from": posix_under(LEGACY_CONSTITUTION_DIR, rel),
                    "to": posix_under(CONSTITUTION_DIR, rel),
                    "reason": "destination exists",
                }
            )
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        adopted.append(
            {
                "from": posix_under(LEGACY_CONSTITUTION_DIR, rel),
                "to": posix_under(CONSTITUTION_DIR, rel),
            }
        )
    return adopted, skipped


def repo_spec_init(workspace: Path) -> int:
    files = relative_files(workspace)
    name = detected_name(workspace)
    roots = source_roots(files)
    scripts = package_scripts(workspace)
    adopted, skipped_legacy = adopt_legacy_constitution(workspace)
    agent = workspace / CONSTITUTION_DIR
    created: list[str] = []

    architecture = [
        f'schema_version: "{SCHEMA_VERSION}"',
        "status: draft",
        "system:",
        f"  name: {yaml_scalar(name)}",
        '  description: ""',
        "architecture:",
        "  style: unknown",
        "source_roots:",
        *([f"  - {yaml_scalar(root)}" for root in roots] or ["  []"]),
        "components: []",
        "data_stores: []",
        "integrations: []",
        'adr_directory: "docs/adr"',
        "",
    ]
    boundaries = [
        f'schema_version: "{SCHEMA_VERSION}"',
        "status: draft",
        "dependency_rules: []",
        "trust_boundaries: []",
        "data_classifications: []",
        "protected_paths: []",
        "",
    ]
    commands = [
        f'schema_version: "{SCHEMA_VERSION}"',
        "status: draft",
        "commands:",
    ]
    if scripts:
        for key, value in sorted(scripts.items()):
            commands.extend(
                [
                    f"  {key}:",
                    f"    run: {yaml_scalar(value)}",
                    '    cwd: "."',
                ]
            )
    else:
        commands.append("  {}")
    commands.extend(["required_environment: []", "",])

    for path, content in (
        (agent / "architecture.yaml", "\n".join(architecture)),
        (agent / "boundaries.yaml", "\n".join(boundaries)),
        (agent / "commands.yaml", "\n".join(commands)),
    ):
        if write_if_missing(path, content):
            created.append(path.relative_to(workspace).as_posix())

    schema_dest = agent / "schemas" / "task-spec.schema.json"
    if not schema_dest.exists():
        schema_dest.parent.mkdir(parents=True, exist_ok=True)
        schema_dest.write_bytes(TASK_SPEC_SCHEMA.read_bytes())
        created.append(schema_dest.relative_to(workspace).as_posix())
    (workspace / "docs" / "adr").mkdir(parents=True, exist_ok=True)
    add_cache_ignore(workspace)
    payload = {
        "status": "ok",
        "created": created,
        "preserved": len(created) == 0 and not adopted,
        "adopted": adopted,
        "skipped_legacy": skipped_legacy,
        **constitution_report(workspace),
    }
    print(json.dumps(payload))
    return 0


def repo_spec_reconcile(workspace: Path) -> int:
    adopted, skipped_legacy = adopt_legacy_constitution(workspace)
    dest_root = workspace / CONSTITUTION_DIR
    missing = [
        posix_under(CONSTITUTION_DIR, rel)
        for rel in constitution_relatives()
        if not (dest_root / rel).is_file()
    ]
    payload = {
        "status": "ok" if not missing else "incomplete",
        "created": [],
        "adopted": adopted,
        "skipped_legacy": skipped_legacy,
        "missing": missing,
        **constitution_report(workspace),
    }
    print(json.dumps(payload))
    return 0 if not missing else 2


SPEC_KEYS = {
    "architecture.yaml": {"schema_version", "status", "system", "architecture", "source_roots", "components"},
    "boundaries.yaml": {"schema_version", "status", "dependency_rules", "trust_boundaries"},
    "commands.yaml": {"schema_version", "status", "commands"},
}


def top_level_yaml_keys(text: str) -> set[str]:
    return {
        match.group(1)
        for line in text.splitlines()
        if (match := re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s|$)", line))
    }


def repo_spec_validate(workspace: Path) -> int:
    errors: list[str] = []
    dest_root = workspace / CONSTITUTION_DIR
    legacy_root = workspace / LEGACY_CONSTITUTION_DIR
    for name, required in SPEC_KEYS.items():
        path = dest_root / name
        if not path.is_file():
            hint = ""
            if (legacy_root / name).is_file():
                hint = f" (legacy {LEGACY_CONSTITUTION_DIR}/{name} present — run repo-spec reconcile)"
            errors.append(f"missing {CONSTITUTION_DIR}/{name}{hint}")
            continue
        missing = sorted(required - top_level_yaml_keys(path.read_text(encoding="utf-8")))
        if missing:
            errors.append(f"{CONSTITUTION_DIR}/{name} missing keys: {', '.join(missing)}")
    schema = dest_root / SCHEMA_REL
    if not schema.is_file():
        hint = ""
        if (legacy_root / SCHEMA_REL).is_file():
            hint = f" (legacy {LEGACY_CONSTITUTION_DIR}/{SCHEMA_REL.as_posix()} present — run repo-spec reconcile)"
        errors.append(f"missing {CONSTITUTION_DIR}/{SCHEMA_REL.as_posix()}{hint}")
    else:
        try:
            json.loads(schema.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid task spec schema: {exc}")
    status = "ok" if not errors else "error"
    print(json.dumps({"status": status, "errors": errors}))
    return 0 if not errors else 2


def is_test(rel: Path) -> bool:
    stem = rel.stem.lower()
    return (
        any(part.lower() in {"test", "tests", "spec", "specs", "__tests__"} for part in rel.parts[:-1])
        or stem.startswith("test_")
        or stem.endswith(("_test", ".test", ".spec"))
    )


def module_id(rel: Path) -> str:
    return rel.parts[0] if len(rel.parts) > 1 else "."


def python_details(path: Path, rel: str) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    symbols: list[dict[str, object]] = []
    edges: list[dict[str, str]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return symbols, edges
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(
                {
                    "file": rel,
                    "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                    "line": node.lineno,
                    "name": node.name,
                    "public": not node.name.startswith("_"),
                }
            )
        elif isinstance(node, ast.Import):
            edges.extend({"source": rel, "target": alias.name, "type": "import"} for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            target = "." * node.level + (node.module or "")
            edges.append({"source": rel, "target": target, "type": "import"})
    return symbols, edges


JS_SYMBOL = re.compile(
    r"^\s*export\s+(?:default\s+)?(?:abstract\s+)?(class|function|const|let|var|interface|type|enum)\s+([A-Za-z_$][\w$]*)",
    re.MULTILINE,
)
JS_IMPORT = re.compile(r"(?:from\s+|require\s*\(\s*)['\"]([^'\"]+)['\"]")


def javascript_details(path: Path, rel: str) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    symbols = [
        {
            "file": rel,
            "kind": match.group(1),
            "line": text.count("\n", 0, match.start()) + 1,
            "name": match.group(2),
            "public": True,
        }
        for match in JS_SYMBOL.finditer(text)
    ]
    edges = [
        {"source": rel, "target": match.group(1), "type": "import"}
        for match in JS_IMPORT.finditer(text)
    ]
    return symbols, edges


def generic_symbols(path: Path, rel: str, language: str) -> list[dict[str, object]]:
    patterns = {
        "go": re.compile(r"^\s*(?:type\s+(\w+)\s+(?:struct|interface)|func\s+(?:\([^)]*\)\s*)?(\w+)\s*\()", re.MULTILINE),
        "java": re.compile(r"^\s*(?:public\s+)?(?:abstract\s+)?(?:class|interface|enum|record)\s+(\w+)", re.MULTILINE),
        "csharp": re.compile(r"^\s*(?:public\s+)?(?:abstract\s+)?(?:class|interface|enum|record)\s+(\w+)", re.MULTILINE),
    }
    pattern = patterns.get(language)
    if pattern is None:
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    out = []
    for match in pattern.finditer(text):
        name = next((group for group in match.groups() if group), None) or match.group(1)
        out.append(
            {
                "file": rel,
                "kind": "symbol",
                "line": text.count("\n", 0, match.start()) + 1,
                "name": name,
                "public": True,
            }
        )
    return out


def test_key(path: Path) -> str:
    stem = path.stem.lower()
    stem = re.sub(r"^(test_|spec_)", "", stem)
    stem = re.sub(r"(_test|_spec|\.test|\.spec)$", "", stem)
    return stem


def build_index(workspace: Path, *, write: bool) -> tuple[dict[str, object], dict[str, object]]:
    # ponytail: full deterministic scan; add per-file cache only when large-repo profiling justifies it.
    files = relative_files(workspace)
    fingerprint = snapshot_fingerprint(workspace, files)
    head = git_head(workspace)
    code_files = [rel for rel in files if rel.suffix.lower() in CODE_SUFFIXES]
    module_files: dict[str, list[dict[str, object]]] = defaultdict(list)
    symbols: list[dict[str, object]] = []
    edges: list[dict[str, str]] = []
    languages: dict[str, int] = defaultdict(int)
    test_files: list[Path] = []
    source_files: list[Path] = []

    for rel in code_files:
        language = CODE_SUFFIXES[rel.suffix.lower()]
        rel_text = rel.as_posix()
        test = is_test(rel)
        languages[language] += 1
        module_files[module_id(rel)].append(
            {"kind": "test" if test else "source", "language": language, "path": rel_text}
        )
        (test_files if test else source_files).append(rel)
        path = workspace / rel
        if language == "python":
            found_symbols, found_edges = python_details(path, rel_text)
        elif language in {"javascript", "typescript"}:
            found_symbols, found_edges = javascript_details(path, rel_text)
        else:
            found_symbols, found_edges = generic_symbols(path, rel_text, language), []
        symbols.extend(found_symbols)
        edges.extend(found_edges)

    modules = [
        {"file_count": len(module_files[key]), "id": key, "root": key}
        for key in sorted(module_files)
    ]
    module_map = {
        "schema_version": SCHEMA_VERSION,
        "modules": [
            {"files": sorted(module_files[key], key=lambda item: str(item["path"])), "id": key}
            for key in sorted(module_files)
        ],
    }
    by_source: dict[str, list[str]] = {}
    tests_by_key: dict[str, list[str]] = defaultdict(list)
    for rel in test_files:
        tests_by_key[test_key(rel)].append(rel.as_posix())
    for rel in source_files:
        matches = tests_by_key.get(test_key(rel), [])
        if matches:
            by_source[rel.as_posix()] = sorted(matches)

    snapshot = {"fingerprint": fingerprint, "head": head}
    repo_index = {
        "repository": {"name": detected_name(workspace)},
        "schema_version": SCHEMA_VERSION,
        "snapshot": snapshot,
        "summary": {
            "code_files": len(code_files),
            "languages": dict(sorted(languages.items())),
            "modules": len(modules),
            "symbols": len(symbols),
            "tests": len(test_files),
        },
        "modules": modules,
    }
    artifacts: dict[str, object] = {
        "repo-index.json": repo_index,
        "module-map.json": module_map,
        "symbols.json": {
            "schema_version": SCHEMA_VERSION,
            "symbols": sorted(symbols, key=lambda item: (str(item["file"]), int(item["line"]), str(item["name"]))),
        },
        "dependency-graph.json": {
            "representation": "adjacency-list",
            "schema_version": SCHEMA_VERSION,
            "edges": sorted(edges, key=lambda item: (item["source"], item["target"])),
        },
        "test-map.json": {
            "by_source": dict(sorted(by_source.items())),
            "schema_version": SCHEMA_VERSION,
            "tests": sorted(rel.as_posix() for rel in test_files),
        },
    }
    manifest = {
        "artifacts": sorted(artifacts),
        "generator_version": SCHEMA_VERSION,
        "schema_version": SCHEMA_VERSION,
        "snapshot": snapshot,
    }
    artifacts["manifest.json"] = manifest
    if write:
        add_cache_ignore(workspace)
        cache = workspace / ".agent-cache"
        cache.mkdir(parents=True, exist_ok=True)
        for name, value in artifacts.items():
            dump_json(cache / name, value)
    return manifest, artifacts


def repo_index_write(workspace: Path) -> int:
    manifest, _ = build_index(workspace, write=True)
    print(json.dumps({"status": "ok", "path": ".agent-cache/repo-index.json", "snapshot": manifest["snapshot"]}))
    return 0


def repo_index_check(workspace: Path) -> int:
    manifest_path = workspace / ".agent-cache" / "manifest.json"
    if not manifest_path.is_file():
        print(json.dumps({"status": "stale", "reason": "missing cache"}))
        return 3
    try:
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(json.dumps({"status": "stale", "reason": "invalid manifest"}))
        return 3
    cached_artifacts: dict[str, object] = {}
    for name in existing.get("artifacts", []):
        artifact = workspace / ".agent-cache" / str(name)
        if not artifact.is_file():
            print(json.dumps({"status": "stale", "reason": f"missing artifact: {name}"}))
            return 3
        try:
            data = json.loads(artifact.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(json.dumps({"status": "stale", "reason": f"invalid artifact: {name}"}))
            return 3
        if data.get("schema_version") != SCHEMA_VERSION:
            print(json.dumps({"status": "stale", "reason": f"schema mismatch: {name}"}))
            return 3
        cached_artifacts[str(name)] = data
    current, expected_artifacts = build_index(workspace, write=False)
    if existing.get("snapshot") != current.get("snapshot"):
        print(json.dumps({"status": "stale", "reason": "repository changed", "expected": existing.get("snapshot"), "current": current.get("snapshot")}))
        return 3
    for name, cached in cached_artifacts.items():
        if cached != expected_artifacts.get(name):
            print(json.dumps({"status": "stale", "reason": f"artifact mismatch: {name}"}))
            return 3
    print(json.dumps({"status": "ok", "snapshot": current["snapshot"]}))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("area", choices=("repo-spec", "repo-index"))
    parser.add_argument("action")
    parser.add_argument("--workspace", default=".")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        print(json.dumps({"status": "error", "error": "workspace not found"}))
        return 2
    if args.area == "repo-spec":
        if args.action == "init":
            return repo_spec_init(workspace)
        if args.action == "reconcile":
            return repo_spec_reconcile(workspace)
        if args.action == "validate":
            return repo_spec_validate(workspace)
    elif args.area == "repo-index":
        if args.action in {"build", "refresh"}:
            return repo_index_write(workspace)
        if args.action == "check":
            return repo_index_check(workspace)
    print(json.dumps({"status": "error", "error": f"unsupported action: {args.area} {args.action}"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
