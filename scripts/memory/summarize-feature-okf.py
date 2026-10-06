#!/usr/bin/env python3
"""Write an OKF v0.2 Feature summary from an ADLC5 feature tree (no LLM).

Canonical output (on archive):
  .adlc5/_archive/{feature}-YYYYMMDD/FEATURE.md
  .adlc5/_archive/index.md          # progressive OKF index
  .adlc5/_archive/{feature}-YYYYMMDD/usage-summary.json   # when a usage ledger exists

Optional (when consumer wiki/ exists):
  wiki/concepts/feature-{feature}.md

Usage:
  ./scripts/memory/summarize-feature-okf.py --feature-dir PATH [--workspace DIR] [--dry-run]
  ./scripts/adlc5 feature summarize --feature-dir PATH [--workspace DIR] [--dry-run]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_BULLETS = 6
MAX_LINE = 160


def _load_usage_ledger():
    """Import the sibling usage-ledger.py module (hyphenated filename)."""
    spec = importlib.util.spec_from_file_location(
        "adlc5_usage_ledger", Path(__file__).resolve().parent / "usage-ledger.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


usage_ledger = _load_usage_ledger()
SECTION_HEADINGS = {
    "problem": (
        "problem",
        "problem statement",
        "overview",
        "summary",
        "what",
        "context",
    ),
    "architecture": (
        "architecture",
        "design",
        "design changes",
        "technical approach",
        "approach",
        "solution",
        "engineering",
    ),
    "results": (
        "results",
        "outcomes",
        "decisions",
        "locked decisions",
        "acceptance criteria",
        "status",
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def load_state(feature_dir: Path) -> dict:
    state_path = feature_dir / "state.json"
    if not state_path.is_file():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def truncate(line: str, limit: int = MAX_LINE) -> str:
    line = re.sub(r"\s+", " ", line).strip()
    if len(line) <= limit:
        return line
    return line[: limit - 1].rstrip() + "…"


def normalize_heading(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def extract_section(md: str, aliases: tuple[str, ...]) -> str:
    """Return body under the first matching AT1–H3 until next same-or-higher heading."""
    if not md:
        return ""
    lines = md.splitlines()
    start = None
    start_level = 0
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,3})\s+(.+?)\s*$", line)
        if not m:
            continue
        level = len(m.group(1))
        heading = normalize_heading(m.group(2))
        if any(heading == a or heading.startswith(a + " ") for a in aliases):
            start = i + 1
            start_level = level
            break
    if start is None:
        return ""

    body: list[str] = []
    for line in lines[start:]:
        m = re.match(r"^(#{1,3})\s+", line)
        if m and len(m.group(1)) <= start_level:
            break
        body.append(line)
    return "\n".join(body).strip()


def bullets_from_text(text: str, limit: int = MAX_BULLETS) -> list[str]:
    if not text:
        return []
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("```") or line.startswith("|"):
            continue
        if line.startswith(("#", "<!--")):
            continue
        if re.match(r"^[-*+]\s+", line) or re.match(r"^\d+[.)]\s+", line):
            line = re.sub(r"^([- *+]|\d+[.)])\s+", "", line)
        elif line.startswith(">"):
            line = line.lstrip("> ").strip()
        else:
            # Keep short prose lines as bullets; skip very long paragraphs
            if len(line) > 220:
                continue
        cleaned = truncate(line)
        if cleaned and cleaned not in out:
            out.append(cleaned)
        if len(out) >= limit:
            break
    return out


def first_existing(feature_dir: Path, rels: list[str]) -> Path | None:
    for rel in rels:
        path = feature_dir / rel
        if path.is_file():
            return path
    return None


def collect_refs(feature_dir: Path, workspace: Path) -> list[tuple[str, str]]:
    """Return (label, workspace-relative path) for main artifacts that exist."""
    candidates = [
        ("Spec", "spec-handoff.md"),
        ("Plan / design index", "design/INDEX.md"),
        ("Architecture notes", "design/architecture.md"),
        ("Feature docs", "docs/README.md"),
        ("Memory index", "memory/INDEX.md"),
        ("Specify summary", "memory/summaries/specify.md"),
        ("Plan summary", "memory/summaries/plan.md"),
        ("Implement summary", "memory/summaries/implement.md"),
        ("State", "state.json"),
    ]
    refs: list[tuple[str, str]] = []
    for label, rel in candidates:
        path = feature_dir / rel
        if path.is_file():
            try:
                display = str(path.relative_to(workspace))
            except ValueError:
                display = str(path)
            refs.append((label, display))
    return refs


def one_line_description(problem_bullets: list[str], feature: str) -> str:
    if problem_bullets:
        return truncate(problem_bullets[0], 120)
    return f"Archived ADLC5 feature summary for {feature}."


def feature_status(state: dict, feature_dir: Path) -> str:
    if (feature_dir / "ABANDONED").is_file() or state.get("lifecycle_status") == "abandoned":
        return "abandoned"
    ss = state.get("stage_status") or {}
    needed = ("specify", "plan", "tasks", "implement")
    ok = {"completed", "waived"}
    if all(ss.get(k) in ok for k in needed):
        return "archived"
    return "draft"


def outcome_bullets(state: dict, feature_dir: Path, status: str) -> list[str]:
    out: list[str] = []
    ss = state.get("stage_status") or {}
    if ss:
        parts = [f"{k}={v}" for k, v in ss.items() if v]
        if parts:
            out.append("Stages: " + ", ".join(parts[:8]))
    out.append(f"Lifecycle status: {status}")

    git = state.get("git") or {}
    branch = git.get("branch_name")
    if branch:
        out.append(f"Branch: `{branch}`")
    base = git.get("base_branch")
    if base:
        out.append(f"Base branch: `{base}`")

    impl = state.get("implement") or {}
    pr = impl.get("pr") or {}
    pr_url = pr.get("url") or state.get("pr_url")
    pr_status = pr.get("status")
    if pr_url:
        out.append(f"PR: {pr_url}" + (f" ({pr_status})" if pr_status else ""))
    elif pr_status:
        out.append(f"PR status: {pr_status}")

    craft = state.get("craftsmanship") or {}
    craft_bits = [f"{k}={v}" for k, v in craft.items() if v and v != "pending"]
    if craft_bits:
        out.append("Craftsmanship: " + ", ".join(craft_bits[:6]))

    if (feature_dir / "ABANDONED").is_file():
        note = read_text(feature_dir / "ABANDONED").strip().splitlines()
        if note:
            out.append("Abandoned note: " + truncate(note[0]))

    return out[:MAX_BULLETS]


def extract_from_sources(feature_dir: Path, kind: str) -> list[str]:
    aliases = SECTION_HEADINGS[kind]
    sources: list[Path] = []
    if kind == "problem":
        for rel in (
            "spec-handoff.md",
            "docs/README.md",
            "memory/summaries/specify.md",
            "memory/INDEX.md",
        ):
            p = feature_dir / rel
            if p.is_file():
                sources.append(p)
    elif kind == "architecture":
        for rel in (
            "design/INDEX.md",
            "design/architecture.md",
            "memory/summaries/plan.md",
            "docs/README.md",
            "spec-handoff.md",
        ):
            p = feature_dir / rel
            if p.is_file():
                sources.append(p)
        design = feature_dir / "design"
        if design.is_dir():
            for p in sorted(design.glob("*.md")):
                if p not in sources:
                    sources.append(p)
    else:  # results
        for rel in (
            "memory/summaries/implement.md",
            "spec-handoff.md",
            "docs/README.md",
            "memory/summaries/plan.md",
        ):
            p = feature_dir / rel
            if p.is_file():
                sources.append(p)

    for path in sources:
        section = extract_section(read_text(path), aliases)
        bullets = bullets_from_text(section)
        if bullets:
            return bullets
    # Problem only: fall back to first bullets in the primary artifact
    if kind == "problem" and sources:
        return bullets_from_text(read_text(sources[0]), limit=3)
    return []


def render_feature_md(
    *,
    feature: str,
    description: str,
    status: str,
    problem: list[str],
    architecture: list[str],
    results: list[str],
    usage: list[str],
    refs: list[tuple[str, str]],
    archive_rel: str | None,
    generated_at: str,
) -> str:
    tags = ["adlc5", "feature", "archive"]
    if status == "abandoned":
        tags.append("abandoned")

    fm_lines = [
        "---",
        "type: Feature",
        f"title: {feature}",
        f"description: {json.dumps(description)}",
        f"tags: [{', '.join(tags)}]",
        f"status: {status}",
        "scope: feature",
        f"feature_id: {feature}",
    ]
    if archive_rel:
        fm_lines.append(f"archive_path: {archive_rel}")
    fm_lines.append(
        f'generated: {{ by: "process:adlc5-summarize-feature-okf", at: "{generated_at}" }}'
    )
    fm_lines.append("---")
    fm_lines.append("")

    def section(title: str, items: list[str], empty: str) -> list[str]:
        lines = [f"## {title}", ""]
        if items:
            lines.extend(f"- {b}" for b in items)
        else:
            lines.append(f"- {empty}")
        lines.append("")
        return lines

    body: list[str] = []
    body.extend(section("Problem", problem, "No problem summary found in feature artifacts."))
    body.extend(
        section(
            "Architecture",
            architecture,
            "No architecture/design bullets found in feature artifacts.",
        )
    )
    body.extend(section("Results", results, "No outcome details recorded in state or summaries."))
    body.extend(
        section(
            "Usage",
            usage,
            "No model/token usage recorded (see `./scripts/adlc5 usage record`).",
        )
    )
    body.append("## References")
    body.append("")
    if refs:
        for label, path in refs:
            body.append(f"- {label}: `{path}`")
    else:
        body.append("- *(no local artifact paths found)*")
    body.append("")
    body.append(
        "Concise OKF feature card generated at archive time "
        "(template + extracted bullets — not a journey dump)."
    )
    body.append("")
    return "\n".join(fm_lines + body)


def upsert_archive_index(
    index_path: Path,
    *,
    feature: str,
    stamp_dir: str,
    description: str,
    dry_run: bool,
) -> str:
    link = f"{stamp_dir}/FEATURE.md"
    entry = f"* [{feature}]({link}) - {description}"
    header = (
        "---\n"
        'okf_version: "0.2"\n'
        "---\n\n"
        "# Archived ADLC5 features (OKF)\n\n"
        "Progressive index of feature summaries written when "
        "`cleanup-features --archive` succeeds.\n\n"
        "Read this file first; open at most 1–3 `FEATURE.md` cards.\n\n"
        "# Features\n\n"
    )

    existing = read_text(index_path) if index_path.is_file() else ""
    skip_re = re.compile(rf"^\*\s+\[{re.escape(feature)}\]\([^)]*FEATURE\.md\)\s*-")

    if not existing.strip():
        content = header + entry + "\n"
    else:
        kept = [ln for ln in existing.splitlines() if not skip_re.match(ln.strip())]
        text = "\n".join(kept).rstrip() + "\n"
        if not re.search(r"^#\s+Features\s*$", text, re.M):
            text = text.rstrip() + "\n\n# Features\n\n"
        if re.search(r"^#\s+Features\s*$", text, re.M):
            content = re.sub(
                r"(#\s+Features\s*\n(?:\n)?)",
                r"\1" + entry + "\n",
                text,
                count=1,
            )
        else:
            content = text.rstrip() + "\n\n# Features\n\n" + entry + "\n"
        content = content.rstrip() + "\n"

    if dry_run:
        return str(index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(content, encoding="utf-8")
    return str(index_path)


def write_wiki_mirror(
    workspace: Path,
    *,
    feature: str,
    body: str,
    archive_feature_rel: str | None,
    dry_run: bool,
) -> str | None:
    wiki = workspace / "wiki"
    if not wiki.is_dir():
        return None
    concepts = wiki / "concepts"
    out_path = concepts / f"feature-{feature}.md"
    # Prefer pointer-style body: reuse FEATURE content but note archive path
    content = body
    if archive_feature_rel and "Archive FEATURE.md" not in content:
        content = content.rstrip() + f"\n\n- Archive FEATURE.md: `{archive_feature_rel}`\n"
    if dry_run:
        return str(out_path)
    concepts.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return str(out_path)


def summarize(
    feature_dir: Path,
    workspace: Path,
    *,
    dry_run: bool = False,
) -> dict:
    feature_dir = feature_dir.resolve()
    workspace = workspace.resolve()
    state = load_state(feature_dir)
    if state.get("feature"):
        feature = str(state["feature"])
    elif state.get("feature_name"):
        feature = str(state["feature_name"])
    else:
        m = re.match(r"^(.*)-(\d{8})$", feature_dir.name)
        feature = m.group(1) if m else feature_dir.name

    status = feature_status(state, feature_dir)
    problem = extract_from_sources(feature_dir, "problem")
    architecture = extract_from_sources(feature_dir, "architecture")
    results = outcome_bullets(state, feature_dir, status)
    # Merge any results section bullets from docs (capped)
    doc_results = extract_from_sources(feature_dir, "results")
    for b in doc_results:
        if b not in results and len(results) < MAX_BULLETS:
            results.append(b)

    description = one_line_description(problem, feature)
    refs = collect_refs(feature_dir, workspace)

    usage_summary = usage_ledger.summarize(feature_dir)
    usage_bullets = usage_ledger.render_markdown(usage_summary)

    try:
        archive_rel = str(feature_dir.relative_to(workspace))
    except ValueError:
        archive_rel = str(feature_dir)

    generated_at = utc_now()
    body = render_feature_md(
        feature=feature,
        description=description,
        status=status,
        problem=problem,
        architecture=architecture,
        results=results,
        usage=usage_bullets,
        refs=refs,
        archive_rel=archive_rel,
        generated_at=generated_at,
    )

    feature_md = feature_dir / "FEATURE.md"
    usage_summary_path = feature_dir / "usage-summary.json"
    wrote: list[str] = []
    would: list[str] = []

    if dry_run:
        would.append(str(feature_md))
        if usage_summary.get("entries"):
            would.append(str(usage_summary_path))
    else:
        feature_dir.mkdir(parents=True, exist_ok=True)
        feature_md.write_text(body, encoding="utf-8")
        wrote.append(str(feature_md))
        if usage_summary.get("entries"):
            usage_summary_path.write_text(
                json.dumps(usage_summary, indent=2) + "\n", encoding="utf-8"
            )
            wrote.append(str(usage_summary_path))

    archive_root = workspace / ".adlc5" / "_archive"
    index_path = archive_root / "index.md"
    stamp_dir = feature_dir.name
    if feature_dir.parent == archive_root or archive_root in feature_dir.parents:
        idx = upsert_archive_index(
            index_path,
            feature=feature,
            stamp_dir=stamp_dir,
            description=description,
            dry_run=dry_run,
        )
        (would if dry_run else wrote).append(idx)

    wiki_path = write_wiki_mirror(
        workspace,
        feature=feature,
        body=body,
        archive_feature_rel=f"{archive_rel}/FEATURE.md"
        if not archive_rel.endswith("FEATURE.md")
        else archive_rel,
        dry_run=dry_run,
    )
    if wiki_path:
        (would if dry_run else wrote).append(wiki_path)

    return {
        "status": "ok",
        "feature": feature,
        "dry_run": dry_run,
        "feature_md": str(feature_md),
        "wrote": wrote,
        "would_write": would,
        "description": description,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--feature-dir",
        required=True,
        help="Path to .adlc5/{feature} or .adlc5/_archive/{feature}-YYYYMMDD",
    )
    p.add_argument("--workspace", default=".", help="Consumer repo root (default: .)")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print paths that would be written; no filesystem changes",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    feature_dir = Path(args.feature_dir)
    workspace = Path(args.workspace)
    if not feature_dir.is_dir():
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": f"feature dir not found: {feature_dir}",
                }
            ),
            file=sys.stderr,
        )
        return 2
    if not workspace.is_dir():
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": f"workspace not found: {workspace}",
                }
            ),
            file=sys.stderr,
        )
        return 2

    result = summarize(feature_dir, workspace, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
