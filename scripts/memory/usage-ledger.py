#!/usr/bin/env python3
"""Model + token usage ledger for an ADLC5 feature (no LLM; best-effort self-reported).

Appends one JSON object per line to:
  .adlc5/{feature}/memory/usage-ledger.jsonl

Token fields are intentionally generic — different hosts/models expose different
counters (Anthropic: input/output/cache_creation/cache_read; OpenAI-style:
reasoning tokens under completion_tokens_details; …). Record whatever the
platform reports; unknown counters go in --extra-json rather than being dropped.
This is observability, not a billing reconciliation — "total" is a sum of the
tracked fields, not an authoritative token count.

Usage:
  ./scripts/memory/usage-ledger.py record --feature NAME [--workspace DIR] \\
    --model-id ID [--platform NAME] [--tier TIER] [--stage STAGE] [--step STEP] \\
    [--source self_reported|transcript|api] \\
    [--input-tokens N] [--output-tokens N] [--thinking-tokens N] \\
    [--cache-creation-tokens N] [--cache-read-tokens N] \\
    [--cache-5m-tokens N] [--cache-1h-tokens N] [--total-tokens N] \\
    [--run-id ID] [--node-id ID] [--parent-node-ids ID,ID] [--attempt N] [--outcome NAME] [--finding-id ID] \\
    [--extra-json JSON] [--note TEXT]

  ./scripts/memory/usage-ledger.py summary --feature-dir PATH [--format json|markdown]
  ./scripts/memory/usage-ledger.py summary --feature NAME --workspace DIR [--format json|markdown]

  ./scripts/memory/usage-ledger.py fleet --workspace DIR [--active-only] [--format json|markdown]

`fleet` rolls up every feature's usage-ledger.jsonl under a workspace's .adlc5/ —
active feature dirs plus archived snapshots under .adlc5/_archive/ (cleanup-features.sh
moves memory/ into the archive tree, so the ledger survives archival). Pass
--active-only to exclude _archive/. This is the cross-feature companion to
`summary` (which is scoped to one feature); same best-effort, non-billing caveat.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.model_prices import estimate_cost_usd, load_prices, normalize_model_id, pricing_meta  # noqa: E402
from lib.state_v2 import load_feature_state  # noqa: E402

LEDGER_REL = Path("memory") / "usage-ledger.jsonl"
RESERVED_TOP_LEVEL = {"governance", "memory", "wiki", "_archive"}

TOKEN_FIELDS = (
    "input",
    "output",
    "thinking",
    "cache_creation",
    "cache_read",
    "cache_5m",
    "cache_1h",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ledger_path(feature_dir: Path) -> Path:
    return feature_dir / LEDGER_REL


def _fmt(n: int) -> str:
    return f"{n:,}"


def record(
    feature_dir: Path,
    *,
    feature: str,
    model_id: str,
    platform: str | None,
    tier: str | None,
    stage: str | None,
    step: str | None,
    source: str,
    tokens: dict[str, int],
    total_tokens: int | None,
    run_id: str | None,
    node_id: str | None,
    parent_node_ids: list[str],
    attempt: int | None,
    outcome: str | None,
    finding_id: str | None,
    extra: dict | None,
    note: str | None,
) -> dict:
    total = total_tokens if total_tokens is not None else sum(tokens.values())
    entry = {
        "ts": utc_now(),
        "feature": feature,
        "stage": stage,
        "step": step,
        "platform": platform,
        "model_id": model_id,
        "tier": tier,
        "source": source,
        "tokens": {**{k: tokens.get(k, 0) for k in TOKEN_FIELDS}, "total": total},
    }
    if extra:
        entry["extra"] = extra
    if note:
        entry["note"] = note
    if run_id:
        entry["run_id"] = run_id
    if node_id:
        entry["node_id"] = node_id
    if parent_node_ids:
        entry["parent_node_ids"] = parent_node_ids
    if attempt is not None:
        entry["attempt"] = attempt
    if outcome:
        entry["outcome"] = outcome
    if finding_id:
        entry["finding_id"] = finding_id

    path = ledger_path(feature_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def load_entries(feature_dir: Path) -> list[dict]:
    path = ledger_path(feature_dir)
    if not path.is_file():
        return []
    entries: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            entries.append(obj)
    return entries


def _empty_bucket() -> dict:
    bucket = {k: 0 for k in TOKEN_FIELDS}
    bucket["total"] = 0
    bucket["calls"] = 0
    # None (JSON null) until at least one priced call lands — a bucket whose
    # every call is unpriced (e.g. by_model["some-unrecognized-id"]) must
    # report null, not a numeric $0.00 that reads as "this costs nothing."
    bucket["cost_usd"] = None
    bucket["priced_calls"] = 0
    bucket["unpriced_calls"] = 0
    bucket["unpriced_models"] = []
    return bucket


def _add(bucket: dict, tokens: dict, model_id: str, prices: dict) -> None:
    for k in TOKEN_FIELDS:
        bucket[k] += int(tokens.get(k, 0) or 0)
    bucket["total"] += int(tokens.get("total", 0) or 0)
    bucket["calls"] += 1

    cost, priced = estimate_cost_usd(tokens, model_id, prices)
    if priced:
        bucket["cost_usd"] = round((bucket["cost_usd"] or 0.0) + (cost or 0.0), 6)
        bucket["priced_calls"] += 1
    else:
        bucket["unpriced_calls"] += 1
        norm = normalize_model_id(model_id) or "unknown"
        if norm not in bucket["unpriced_models"]:
            bucket["unpriced_models"].append(norm)


def summarize(feature_dir: Path, prices: dict | None = None) -> dict:
    prices = prices if prices is not None else {}
    entries = load_entries(feature_dir)
    totals = _empty_bucket()
    by_model: dict[str, dict] = {}
    by_stage: dict[str, dict] = {}

    for e in entries:
        tokens = e.get("tokens") or {}
        model_id = e.get("model_id") or "unknown"
        stage = e.get("stage") or "unspecified"

        _add(totals, tokens, model_id, prices)

        by_model.setdefault(model_id, _empty_bucket())
        _add(by_model[model_id], tokens, model_id, prices)

        by_stage.setdefault(stage, _empty_bucket())
        _add(by_stage[stage], tokens, model_id, prices)

    ts_list = sorted(e.get("ts", "") for e in entries if e.get("ts"))
    return {
        "status": "ok",
        "entries": len(entries),
        "first_ts": ts_list[0] if ts_list else None,
        "last_ts": ts_list[-1] if ts_list else None,
        "totals": totals,
        "by_model": by_model,
        "by_stage": by_stage,
        "ledger_path": str(ledger_path(feature_dir)),
        "pricing": pricing_meta(prices),
    }


def render_markdown(summary: dict) -> list[str]:
    """Concise bullets suitable for embedding into an OKF FEATURE.md."""
    if not summary.get("entries"):
        return []
    totals = summary["totals"]
    lines = [
        f"Total tracked tokens: {_fmt(totals['total'])} across {totals['calls']} "
        f"recorded call(s), {summary['entries']} ledger entr{'y' if summary['entries'] == 1 else 'ies'}.",
        (
            "By type: input={input} output={output} thinking={thinking} "
            "cache_creation={cache_creation} cache_read={cache_read} "
            "cache_5m={cache_5m} cache_1h={cache_1h}"
        ).format(**{k: _fmt(totals[k]) for k in TOKEN_FIELDS}),
    ]
    if summary["by_model"]:
        parts = [
            f"{model}={_fmt(bucket['total'])} ({bucket['calls']} call(s))"
            for model, bucket in sorted(summary["by_model"].items())
        ]
        lines.append("By model: " + "; ".join(parts))
    if summary["by_stage"]:
        parts = [
            f"{stage}={_fmt(bucket['total'])}"
            for stage, bucket in sorted(summary["by_stage"].items())
        ]
        lines.append("By stage: " + "; ".join(parts))
    lines.append(_cost_line(summary["totals"], summary.get("pricing") or {}))
    return lines


def _cost_line(totals: dict, pricing: dict) -> str:
    """One-line self-reported cost estimate, honest about what it can't price."""
    if pricing.get("status") != "loaded":
        return "Estimated cost: unavailable — core/model-prices.yaml missing or unparseable."
    unpriced = totals.get("unpriced_models") or []
    unpriced_note = f"; unpriced models: {', '.join(sorted(unpriced))}" if unpriced else ""
    stale_note = " (pricing snapshot is over 180 days old — re-verify)" if pricing.get("stale_over_180d") else ""
    cost_usd = totals.get("cost_usd")
    cost_str = f"${cost_usd:.4f}" if cost_usd is not None else "unavailable (no priced calls)"
    return (
        f"Estimated cost: {cost_str} USD "
        f"({totals.get('priced_calls', 0)}/{totals.get('calls', 0)} call(s) priced{unpriced_note}). "
        f"Self-reported, list-price estimate — not a reconciled bill. "
        f"Pricing last verified {pricing.get('last_verified', 'unknown')}{stale_note}."
    )


def discover_feature_dirs(workspace: Path, *, include_archived: bool = True) -> list[Path]:
    """Feature dirs under workspace/.adlc5 that have a usage-ledger.jsonl.

    Active features are direct children of .adlc5/ (excluding reserved
    scaffolding dirs). Archived features are one level deeper, under
    .adlc5/_archive/{feature}-{stamp}/ (cleanup-features.sh moves memory/
    into the archive tree, so the ledger travels with it).
    """
    adlc5_dir = workspace / ".adlc5"
    if not adlc5_dir.is_dir():
        return []

    dirs: list[Path] = []
    for child in sorted(adlc5_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name == "_archive":
            if include_archived:
                for arch_child in sorted(child.iterdir()):
                    if arch_child.is_dir() and ledger_path(arch_child).is_file():
                        dirs.append(arch_child)
            continue
        if child.name in RESERVED_TOP_LEVEL:
            continue
        if ledger_path(child).is_file():
            dirs.append(child)
    return dirs


def fleet_summarize(workspace: Path, *, include_archived: bool = True, prices: dict | None = None) -> dict:
    """Aggregate usage-ledger.jsonl across every feature in a workspace."""
    prices = prices if prices is not None else {}
    feature_dirs = discover_feature_dirs(workspace, include_archived=include_archived)

    totals = _empty_bucket()
    by_model: dict[str, dict] = {}
    by_stage: dict[str, dict] = {}
    by_feature: dict[str, dict] = {}
    all_ts: list[str] = []
    features_with_entries = 0

    for feature_dir in feature_dirs:
        entries = load_entries(feature_dir)
        if not entries:
            continue
        features_with_entries += 1
        status = "archived" if feature_dir.parent.name == "_archive" else "active"
        label = entries[0].get("feature") or feature_dir.name

        bucket = by_feature.get(label)
        if bucket is None:
            bucket = {**_empty_bucket(), "status": status, "feature_dir": str(feature_dir)}
            by_feature[label] = bucket
        elif status == "archived":
            # Same feature name seen active and archived (or archived twice) —
            # keep totals merged, but prefer the archived snapshot's path/status.
            bucket["status"] = "archived"
            bucket["feature_dir"] = str(feature_dir)

        for e in entries:
            tokens = e.get("tokens") or {}
            model_id = e.get("model_id") or "unknown"
            stage = e.get("stage") or "unspecified"

            _add(totals, tokens, model_id, prices)
            _add(bucket, tokens, model_id, prices)

            by_model.setdefault(model_id, _empty_bucket())
            _add(by_model[model_id], tokens, model_id, prices)

            by_stage.setdefault(stage, _empty_bucket())
            _add(by_stage[stage], tokens, model_id, prices)

            if e.get("ts"):
                all_ts.append(e["ts"])

    all_ts.sort()
    return {
        "status": "ok",
        "workspace": str(workspace),
        "features_scanned": len(feature_dirs),
        "features_with_entries": features_with_entries,
        "first_ts": all_ts[0] if all_ts else None,
        "last_ts": all_ts[-1] if all_ts else None,
        "totals": totals,
        "by_model": by_model,
        "by_stage": by_stage,
        "by_feature": by_feature,
        "pricing": pricing_meta(prices),
    }


def render_fleet_markdown(summary: dict) -> list[str]:
    """Concise bullets for a cross-feature usage rollup."""
    if not summary.get("features_with_entries"):
        return []
    totals = summary["totals"]
    lines = [
        f"Fleet total tracked tokens: {_fmt(totals['total'])} across {totals['calls']} "
        f"recorded call(s), {summary['features_with_entries']} feature(s) with usage "
        f"(of {summary['features_scanned']} scanned).",
        (
            "By type: input={input} output={output} thinking={thinking} "
            "cache_creation={cache_creation} cache_read={cache_read} "
            "cache_5m={cache_5m} cache_1h={cache_1h}"
        ).format(**{k: _fmt(totals[k]) for k in TOKEN_FIELDS}),
    ]
    if summary["by_model"]:
        parts = [
            f"{model}={_fmt(bucket['total'])} ({bucket['calls']} call(s))"
            for model, bucket in sorted(summary["by_model"].items())
        ]
        lines.append("By model: " + "; ".join(parts))
    if summary["by_stage"]:
        parts = [
            f"{stage}={_fmt(bucket['total'])}"
            for stage, bucket in sorted(summary["by_stage"].items())
        ]
        lines.append("By stage: " + "; ".join(parts))
    if summary["by_feature"]:
        parts = [
            f"{feature} [{bucket['status']}]={_fmt(bucket['total'])}"
            for feature, bucket in sorted(summary["by_feature"].items())
        ]
        lines.append("By feature: " + "; ".join(parts))
    lines.append(_cost_line(summary["totals"], summary.get("pricing") or {}))
    return lines


def resolve_feature_dir(args: argparse.Namespace) -> Path | None:
    if args.feature_dir:
        return Path(args.feature_dir)
    if args.feature:
        adlc5_dir = Path(args.workspace).resolve() / ".adlc5"
        active = adlc5_dir / args.feature
        if active.is_dir():
            return active
        # cleanup-features.sh --archive moves .adlc5/{feature} to
        # .adlc5/_archive/{feature}-YYYYMMDD once a feature completes.
        # Reconciliation that runs after archival (e.g. the Cursor Admin
        # API's 48h delayed-event overlap, or a late cloud-agent delta poll)
        # must still land in that archived ledger instead of erroring —
        # otherwise those events are silently lost, not merely delayed.
        archived = sorted((adlc5_dir / "_archive").glob(f"{args.feature}-*"))
        if archived:
            return archived[-1]
        return active
    return None


def cmd_record(args: argparse.Namespace) -> int:
    feature_dir = resolve_feature_dir(args)
    if feature_dir is None or not feature_dir.is_dir():
        print(
            json.dumps({"status": "error", "message": "feature dir not found (pass --feature or --feature-dir)"}),
            file=sys.stderr,
        )
        return 2

    stage, step = args.stage, args.step
    if stage is None or step is None:
        workspace = Path(args.workspace).resolve()
        feature = args.feature or feature_dir.name
        state = load_feature_state(workspace, feature) or {}
        stage = stage or state.get("current_stage")
        step = step or state.get("current_step")

    extra = None
    if args.extra_json:
        try:
            extra = json.loads(args.extra_json)
        except json.JSONDecodeError as exc:
            print(json.dumps({"status": "error", "message": f"invalid --extra-json: {exc}"}), file=sys.stderr)
            return 2

    tokens = {
        "input": args.input_tokens,
        "output": args.output_tokens,
        "thinking": args.thinking_tokens,
        "cache_creation": args.cache_creation_tokens,
        "cache_read": args.cache_read_tokens,
        "cache_5m": args.cache_5m_tokens,
        "cache_1h": args.cache_1h_tokens,
    }

    entry = record(
        feature_dir,
        feature=args.feature or feature_dir.name,
        model_id=args.model_id,
        platform=args.platform,
        tier=args.tier,
        stage=stage,
        step=step,
        source=args.source,
        tokens=tokens,
        total_tokens=args.total_tokens,
        run_id=args.run_id,
        node_id=args.node_id,
        parent_node_ids=[item for item in args.parent_node_ids.split(",") if item],
        attempt=args.attempt,
        outcome=args.outcome,
        finding_id=args.finding_id,
        extra=extra,
        note=args.note,
    )
    print(json.dumps({"status": "ok", "ledger_path": str(ledger_path(feature_dir)), "entry": entry}, indent=2))
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    feature_dir = resolve_feature_dir(args)
    if feature_dir is None or not feature_dir.is_dir():
        print(
            json.dumps({"status": "error", "message": "feature dir not found (pass --feature or --feature-dir)"}),
            file=sys.stderr,
        )
        return 2

    summary = summarize(feature_dir, prices=load_prices(ROOT))
    if args.format == "markdown":
        lines = render_markdown(summary)
        print("\n".join(lines) if lines else "No usage ledger entries recorded.")
    else:
        print(json.dumps(summary, indent=2))
    return 0


def cmd_fleet(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    summary = fleet_summarize(workspace, include_archived=not args.active_only, prices=load_prices(ROOT))
    if args.format == "markdown":
        lines = render_fleet_markdown(summary)
        print("\n".join(lines) if lines else "No usage ledger entries recorded across any feature.")
    else:
        print(json.dumps(summary, indent=2))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("record", help="Append a model/token usage entry")
    rec.add_argument("--feature", default=None)
    rec.add_argument("--feature-dir", dest="feature_dir", default=None)
    rec.add_argument("--workspace", default=".")
    rec.add_argument("--model-id", required=True)
    rec.add_argument("--platform", default=None)
    rec.add_argument("--tier", default=None)
    rec.add_argument("--stage", default=None, help="Default: state.json current_stage")
    rec.add_argument("--step", default=None, help="Default: state.json current_step")
    rec.add_argument("--source", default="self_reported", choices=["self_reported", "transcript", "api"])
    rec.add_argument("--input-tokens", type=int, default=0)
    rec.add_argument("--output-tokens", type=int, default=0)
    rec.add_argument("--thinking-tokens", type=int, default=0)
    rec.add_argument("--cache-creation-tokens", type=int, default=0)
    rec.add_argument("--cache-read-tokens", type=int, default=0)
    rec.add_argument("--cache-5m-tokens", type=int, default=0)
    rec.add_argument("--cache-1h-tokens", type=int, default=0)
    rec.add_argument("--total-tokens", type=int, default=None, help="Default: sum of tracked fields")
    rec.add_argument("--run-id", default=None)
    rec.add_argument("--node-id", default=None)
    rec.add_argument("--parent-node-ids", default="", help="Comma-separated parent node IDs")
    rec.add_argument("--attempt", type=int, default=None)
    rec.add_argument("--outcome", default=None)
    rec.add_argument("--finding-id", default=None)
    rec.add_argument("--extra-json", default=None, help="JSON object for platform-specific counters")
    rec.add_argument("--note", default=None)
    rec.set_defaults(func=cmd_record)

    summ = sub.add_parser("summary", help="Aggregate the ledger")
    summ.add_argument("--feature", default=None)
    summ.add_argument("--feature-dir", dest="feature_dir", default=None)
    summ.add_argument("--workspace", default=".")
    summ.add_argument("--format", default="json", choices=["json", "markdown"])
    summ.set_defaults(func=cmd_summary)

    fleet = sub.add_parser("fleet", help="Aggregate usage across every feature in a workspace")
    fleet.add_argument("--workspace", default=".")
    fleet.add_argument("--active-only", action="store_true", help="Exclude .adlc5/_archive/ snapshots")
    fleet.add_argument("--format", default="json", choices=["json", "markdown"])
    fleet.set_defaults(func=cmd_fleet)

    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
