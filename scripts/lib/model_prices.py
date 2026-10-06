"""ADLC5 model pricing lookup + self-reported cost estimation (lever 9).

Loads core/model-prices.yaml and turns a usage-ledger token bucket into an
estimated cost_usd. This is observability, not billing reconciliation — see
the "last_verified" field in the pricing file and the module docstring on
scripts/memory/usage-ledger.py.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .simple_yaml import parse as _parse_yaml
except ImportError:  # pragma: no cover - direct script execution without package context
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from simple_yaml import parse as _parse_yaml  # type: ignore

_BRACKET_SUFFIX = re.compile(r"\s*\[.*\]\s*$")

DEFAULT_CACHE_READ_MULTIPLIER = 0.1
DEFAULT_CACHE_WRITE_5M_MULTIPLIER = 1.25
DEFAULT_CACHE_WRITE_1H_MULTIPLIER = 2.0


def prices_path(root: Path) -> Path:
    return root / "core" / "model-prices.yaml"


def load_prices(root: Path) -> dict[str, Any]:
    """Load and parse core/model-prices.yaml; {} when absent or unparseable."""
    path = prices_path(root)
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        try:
            return _parse_yaml(text)
        except Exception:
            return {}


def normalize_model_id(model_id: str) -> str:
    """Strip a host-specific option suffix like '[reasoning=extra-high]' and whitespace."""
    return _BRACKET_SUFFIX.sub("", (model_id or "").strip()).strip()


def lookup_price(prices: dict, model_id: str) -> dict | None:
    models = prices.get("models") or {}
    if not isinstance(models, dict):
        return None
    entry = models.get(normalize_model_id(model_id))
    if isinstance(entry, dict) and "input" in entry and "output" in entry:
        return entry
    return None


def estimate_cost_usd(tokens: dict, model_id: str, prices: dict) -> tuple[float | None, bool]:
    """Estimate USD cost for one usage-ledger token bucket.

    Returns (cost_usd, priced) — priced is False (cost_usd None) when
    model_id has no entry in the pricing table, so callers can surface
    "unpriced" rather than silently reporting $0.

    "thinking" tokens are intentionally NOT added to output tokens here.
    usage-ledger.py's TOKEN_FIELDS is documented as generic across hosts,
    and different hosts report this counter with different, sometimes
    incompatible semantics: OpenAI-style completion_tokens_details.reasoning_tokens
    is a SUBSET already included in completion/output tokens, so adding it
    again would double-bill that portion. Record the full billable count in
    --output-tokens; --thinking-tokens is informational/breakdown-only for
    the cost estimate until per-platform semantics are threaded through here.

    cache_creation tokens not already broken out into cache_5m/cache_1h are
    treated as 5-minute TTL writes (the more common case and the
    conservative-but-typical default; record cache_5m/cache_1h explicitly
    for an exact figure).
    """
    entry = lookup_price(prices, model_id)
    if entry is None:
        return None, False

    price_in = float(entry.get("input", 0) or 0)
    price_out = float(entry.get("output", 0) or 0)
    cache_read_mult = float(
        entry.get("cache_read_multiplier", prices.get("cache_read_multiplier", DEFAULT_CACHE_READ_MULTIPLIER))
    )
    cache_write_5m_mult = float(
        entry.get(
            "cache_write_multiplier_5m",
            prices.get("cache_write_multiplier_5m", DEFAULT_CACHE_WRITE_5M_MULTIPLIER),
        )
    )
    cache_write_1h_mult = float(
        entry.get(
            "cache_write_multiplier_1h",
            prices.get("cache_write_multiplier_1h", DEFAULT_CACHE_WRITE_1H_MULTIPLIER),
        )
    )

    in_tok = float(tokens.get("input", 0) or 0)
    out_tok = float(tokens.get("output", 0) or 0)
    cache_read_tok = float(tokens.get("cache_read", 0) or 0)
    cache_5m_tok = float(tokens.get("cache_5m", 0) or 0)
    cache_1h_tok = float(tokens.get("cache_1h", 0) or 0)
    cache_generic_tok = float(tokens.get("cache_creation", 0) or 0) - cache_5m_tok - cache_1h_tok
    if cache_generic_tok < 0:
        cache_generic_tok = 0.0

    cost = (
        in_tok * price_in
        + out_tok * price_out
        + cache_read_tok * price_in * cache_read_mult
        + (cache_5m_tok + cache_generic_tok) * price_in * cache_write_5m_mult
        + cache_1h_tok * price_in * cache_write_1h_mult
    ) / 1_000_000.0
    return cost, True


def pricing_meta(prices: dict) -> dict:
    """Summary of the pricing snapshot for embedding in usage summaries."""
    if not prices:
        return {"status": "missing", "path": "core/model-prices.yaml"}
    last_verified = prices.get("last_verified")
    stale = None
    if isinstance(last_verified, str):
        try:
            lv = datetime.strptime(last_verified, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            stale = (datetime.now(timezone.utc) - lv).days > 180
        except ValueError:
            stale = None
    return {
        "status": "loaded",
        "last_verified": last_verified,
        "stale_over_180d": stale,
        "source": prices.get("source"),
    }
