#!/usr/bin/env python3
"""OKF pattern catalog lookup — ids/paths (+ optional short frontmatter), never card bodies.

Usage:
  ./scripts/patterns/lookup.sh --tags latency,extensibility [--group gof] [--limit 3] [--frontmatter]
  ./scripts/adlc5 patterns lookup --tags latency [--group algorithms]

Exit 0 on success (including zero matches). Exit 2 on usage/IO error.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "shared" / "docs" / "patterns"
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
GROUPS = frozenset({"gof", "algorithms", "pbe", "architecture", "clean-code"})


def parse_frontmatter(text: str) -> dict[str, str]:
    """Top-level keys only (skip indented / list-item lines); first wins."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line or line[0] in (" ", "\t") or line.lstrip().startswith("-"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if not key or key.startswith("#") or key in fields:
            continue
        fields[key] = value.strip().strip("'\"")
    return fields


def tag_tokens(raw: str) -> set[str]:
    if not raw:
        return set()
    cleaned = raw.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    return {t.strip().strip("'\"").lower() for t in cleaned.split(",") if t.strip().strip("'\"")}


def concept_id(path: Path) -> str:
    return str(path.relative_to(CATALOG).with_suffix("")).replace("\\", "/")


def iter_concepts(group: str | None) -> list[Path]:
    base = CATALOG / group if group else CATALOG
    if not base.is_dir():
        return []
    paths: list[Path] = []
    for path in sorted(base.rglob("*.md")):
        if path.name.lower() in ("index.md", "readme.md", "log.md"):
            continue
        if path.parent == CATALOG:
            continue
        paths.append(path)
    return paths


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="adlc5 patterns lookup",
        description="Print matching OKF concept ids/paths only (token-efficient).",
    )
    parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated tags matched against tags + requirements_tags",
    )
    parser.add_argument(
        "--group",
        default=None,
        help="Limit to group: gof|algorithms|pbe|architecture|clean-code",
    )
    parser.add_argument("--query", default=None, help="Substring on id/title/description/tags")
    parser.add_argument("--id", default=None, help="Exact or substring concept id (e.g. gof/strategy)")
    parser.add_argument("--limit", type=int, default=3, help="Max results (default 3; 0 = all)")
    parser.add_argument(
        "--frontmatter",
        action="store_true",
        help="Include short frontmatter fields — still no card body",
    )
    args = parser.parse_args(argv)

    if not CATALOG.is_dir():
        print(f"ERROR: catalog missing: {CATALOG}", file=sys.stderr)
        return 2

    wanted = tag_tokens(args.tags)
    if not wanted and not args.query and not args.id:
        print("ERROR: provide --tags and/or --query and/or --id", file=sys.stderr)
        return 2

    if args.group and args.group not in GROUPS:
        print(f"ERROR: unknown group: {args.group}", file=sys.stderr)
        return 2

    hits: list[tuple[str, Path, dict[str, str]]] = []
    for path in iter_concepts(args.group):
        cid = concept_id(path)
        if args.id:
            needle = args.id.lower().removesuffix(".md")
            if needle not in cid.lower():
                continue

        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"ERROR: read failed: {path}: {exc}", file=sys.stderr)
            return 2
        fields = parse_frontmatter(text)

        if wanted:
            have = tag_tokens(fields.get("tags", "")) | tag_tokens(
                fields.get("requirements_tags", "")
            )
            if not (wanted & have):
                continue

        if args.query:
            q = args.query.lower()
            searchable = " ".join(
                [
                    cid,
                    fields.get("title", ""),
                    fields.get("description", ""),
                    fields.get("tags", ""),
                    fields.get("requirements_tags", ""),
                ]
            ).lower()
            if q not in searchable:
                continue

        hits.append((cid, path, fields))

    if args.limit != 0:
        hits = hits[: max(0, args.limit)]

    for cid, path, fields in hits:
        rel = path.relative_to(ROOT)
        if args.frontmatter:
            print(
                f"{cid}\t{rel}"
                f"\ttitle={fields.get('title', '')}"
                f"\tdescription={fields.get('description', '')}"
                f"\ttags={fields.get('tags', '')}"
                f"\trequirements_tags={fields.get('requirements_tags', '')}"
            )
        else:
            print(f"{cid}\t{rel}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
