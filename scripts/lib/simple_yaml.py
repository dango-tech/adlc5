"""Minimal indentation-based YAML-subset parser (no PyYAML dependency).

Handles the ADLC5 shapes used by pricing tables and code-spec frontmatter:
nested maps, flat lists of scalars, and lists of maps (`- key: value` blocks
followed by indented sibling keys). Not a general YAML parser — multi-line
strings, anchors, and flow collections beyond a bare `[a, b]` are not
supported. Prefer PyYAML when it is installed; callers should try `import
yaml` first and fall back to `parse()` here, matching the pattern already
used by scripts/lib/model_routing.py's `load_yaml_file`.
"""
from __future__ import annotations

import re
from typing import Any


def parse_scalar(raw: str) -> Any:
    s = raw.strip()
    if not s:
        return ""
    if s[0] in ("'", '"'):
        if not (len(s) >= 2 and s.endswith(s[0])):
            raise ValueError(f"unterminated quoted scalar: {raw!r}")
        return s[1:-1]
    low = s.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(item) for item in inner.split(",")]
    return s


def _clean_lines(text: str) -> list[tuple[int, str]]:
    """(indent, stripped_content) pairs, comments and blank lines dropped."""
    out: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        out.append((indent, line.strip()))
    return out


def parse(text: str) -> dict:
    """Indentation-stack parser for nested maps / lists of scalars / lists of maps."""
    lines = _clean_lines(text)
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    for i, (indent, content) in enumerate(lines):
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if content.startswith("- ") or content == "-":
            item_raw = content[2:].strip() if content.startswith("- ") else ""
            if not isinstance(parent, list):
                continue
            if item_raw and ":" in item_raw and not item_raw.startswith(("'", '"')):
                key, _, val = item_raw.partition(":")
                key = key.strip()
                val = val.strip()
                entry: dict[str, Any] = {}
                parent.append(entry)
                stack.append((indent, entry))
                if val == "":
                    child_container = _next_container(lines, i, indent)
                    entry[key] = child_container
                    stack.append((indent + 2, child_container))
                else:
                    entry[key] = parse_scalar(val)
            elif item_raw:
                parent.append(parse_scalar(item_raw))
            else:
                child: dict[str, Any] = {}
                parent.append(child)
                stack.append((indent, child))
            continue

        if ":" not in content:
            continue
        key, _, val = content.partition(":")
        key = key.strip()
        val = val.strip()
        if not isinstance(parent, dict):
            continue
        if val == "":
            child_container = _next_container(lines, i, indent)
            parent[key] = child_container
            stack.append((indent, child_container))
        else:
            parent[key] = parse_scalar(val)

    return root


def _next_container(lines: list[tuple[int, str]], i: int, indent: int) -> list | dict:
    """Peek the next deeper-indented line after (indent, content) at lines[i]

    to decide whether the value about to be parsed is a list (next line
    starts with "- ") or a nested map. Defaults to a map when the key has
    no children at all (an empty section).
    """
    for j in range(i + 1, len(lines)):
        next_indent, next_content = lines[j]
        if next_indent <= indent:
            break
        return [] if next_content.startswith("- ") or next_content == "-" else {}
    return {}


def load_frontmatter(text: str) -> tuple[dict | None, str]:
    """Split leading `---\\n...\\n---\\n` YAML frontmatter from the body.

    Returns (frontmatter, body_text) with three distinct outcomes for
    frontmatter, deliberately not collapsed into one:
      - {}   — no `---` block at all (caller decides whether that's an error)
      - None — a `---` block is present but failed to parse as valid YAML
               (distinct from "missing" so callers can report "malformed"
               rather than silently treating garbage as an empty spec)
      - dict — parsed successfully (possibly empty if the block itself was
               blank, which still counts as present-and-valid)

    PyYAML unavailable is not the same as PyYAML rejecting the text: only
    ImportError falls back to the bundled parser above; a real YAMLError (or
    a ValueError raised by the fallback parser itself, e.g. an unterminated
    quote) means the frontmatter is malformed and must not be silently
    reinterpreted into something that looks valid.
    """
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n?", text, re.DOTALL)
    if not match:
        return {}, text
    fm_text = match.group(1)
    body = text[match.end():]

    try:
        import yaml  # type: ignore
    except ImportError:
        try:
            return parse(fm_text), body
        except ValueError:
            return None, body

    try:
        loaded = yaml.safe_load(fm_text)
    except yaml.YAMLError:
        return None, body
    return (loaded if isinstance(loaded, dict) else {}), body
