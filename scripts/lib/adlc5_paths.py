"""Canonical ADLC5 state paths with explicit legacy fallbacks."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .state_v2 import validate_against_schema


def _is_canonical(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return not validate_against_schema(data)
    except (json.JSONDecodeError, OSError, AttributeError, TypeError):
        return False


def state_path(workspace: Path, feature: str) -> Path:
    """Prefer schema-v3 state; fall back to legacy delivery/forge state."""
    root = workspace / ".adlc5" / feature
    canonical = root / "state.json"
    delivery = root / "delivery" / "state.json"
    legacy = root / "forge" / "state.json"
    if _is_canonical(canonical):
        return canonical
    if delivery.is_file():
        return delivery
    if legacy.is_file():
        return legacy
    return canonical


def load_state(workspace: Path, feature: str) -> dict[str, Any] | None:
    path = state_path(workspace, feature)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def delivery_state_path(workspace: Path, feature: str) -> Path:
    """Legacy delivery-state path for compatibility writers."""
    root = workspace / ".adlc5" / feature
    delivery = root / "delivery" / "state.json"
    forge = root / "forge" / "state.json"
    return delivery if delivery.is_file() or not forge.is_file() else forge


def load_delivery_state(workspace: Path, feature: str) -> dict[str, Any] | None:
    path = delivery_state_path(workspace, feature)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
