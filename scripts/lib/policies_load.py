"""Load .adlc5 policies.yaml without external deps (subset parser + optional PyYAML)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


CANONICAL_STEPS = (
    "specify-0-git",
    "specify-1-discover",
    "specify-2-requirements",
    "specify-3-nfr",
    "specify-4-handoff",
    "plan-1-engineering-architecture",
    "plan-2-engineering-patterns",
    "plan-3-engineering-algorithms",
    "plan-4-design-discovery",
    "plan-5-design-contracts",
    "plan-6-design-operations",
    "plan-7-design-critique",
    "tasks-1-stories",
    "tasks-2-code-spec",
    "implement-1-build",
    "implement-2-verify",
    "implement-3-integrate",
    "implement-4-qa",
    "implement-5-pr",
)

PROFILE_SKIPS = {
    "tiny": {
        "specify-1-discover",
        "specify-2-requirements",
        "specify-3-nfr",
        "plan-1-engineering-architecture",
        "plan-2-engineering-patterns",
        "plan-3-engineering-algorithms",
        "plan-4-design-discovery",
        "plan-5-design-contracts",
        "plan-6-design-operations",
        "plan-7-design-critique",
        "tasks-1-stories",
        "tasks-2-code-spec",
        "implement-3-integrate",
        "implement-4-qa",
    },
    "standard": {
        "plan-1-engineering-architecture",
        "plan-2-engineering-patterns",
        "plan-3-engineering-algorithms",
        "plan-5-design-contracts",
        "plan-6-design-operations",
        "plan-7-design-critique",
        "implement-4-qa",
    },
    "high_risk": set(),
}


def profile_name(policies: dict) -> str:
    return str((policies.get("autopilot") or {}).get("profile") or "full")


def step_enabled(policies: dict, step: str) -> bool:
    return step not in PROFILE_SKIPS.get(profile_name(policies), set())


def next_step_for_profile(policies: dict, current: str) -> str:
    try:
        index = CANONICAL_STEPS.index(current)
    except ValueError:
        return current
    for step in CANONICAL_STEPS[index + 1 :]:
        if step_enabled(policies, step):
            return step
    return "implement-5-pr"


def profile_risk_errors(workspace: Path, feature: str, policies: dict) -> list[str]:
    """Validate an explicit risk assessment; never infer safety from prose or clarity."""
    if profile_name(policies) not in ("tiny", "standard", "high_risk", "full"):
        return ["unknown profile; select tiny, standard, high_risk, or full before progression"]
    path = workspace / ".adlc5" / feature / "risk.json"
    try:
        risk = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ["record risk.json with categories, uncertain, and rationale before progression"]
    categories = {"auth", "money", "secrets", "migration", "concurrency", "destructive",
                  "public_compatibility", "disputed_requirements"}
    if (not isinstance(risk, dict) or not isinstance(risk.get("categories"), list)
            or any(not isinstance(c, str) or c not in categories for c in risk["categories"])
            or not isinstance(risk.get("uncertain"), bool)
            or not isinstance(risk.get("rationale"), str) or not risk["rationale"].strip()):
        return ["invalid risk.json: use known categories, boolean uncertain, and a nonempty rationale"]
    if (risk["categories"] or risk["uncertain"]) and profile_name(policies) != "high_risk":
        return ["risk or uncertainty requires high_risk profile before implementation"]
    if profile_name(policies) == "high_risk" and (policies.get("autopilot") or {}).get("require_human_pr_approval") is not True:
        return ["high_risk requires autopilot.require_human_pr_approval: true"]
    return []


def _merge_dict(base: dict, overlay: dict) -> dict:
    out = dict(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge_dict(out[k], v)
        else:
            out[k] = v
    return out


def _parse_scalar(value: str) -> Any:
    value = value.strip().strip('"').strip("'")
    if value in ("null", "~", ""):
        return None
    if value in ("true", "false"):
        return value == "true"
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def _parse_simple(text: str) -> dict:
    """Best-effort parse for ADLC5 policies shape."""
    data: dict[str, Any] = {
        "defaults": {},
        "autopilot": {},
        "persona_mode": {},
        "model_routing": {},
        "custom_gates": [],
        "required_gates": [],
    }
    section = "root"
    current_gate: dict[str, str] | None = None

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if re.match(r"^defaults:\s*$", line):
            section = "defaults"
            continue
        if re.match(r"^autopilot:\s*$", line):
            section = "autopilot"
            continue
        if re.match(r"^custom_gates:\s*$", line):
            if current_gate:
                data["custom_gates"].append(current_gate)
                current_gate = None
            section = "custom_gates"
            continue
        if re.match(r"^required_gates:\s*$", line):
            if current_gate:
                data["custom_gates"].append(current_gate)
                current_gate = None
            section = "required_gates"
            continue
        if re.match(r"^custom_gates:\s*\[\s*\]\s*$", line):
            section = "custom_gates"
            current_gate = None
            continue
        if re.match(r"^assure_skills_required:\s*$", line):
            section = "assure_skills_required"
            continue
        if re.match(r"^persona_mode:\s*$", line):
            section = "persona_mode"
            continue
        if re.match(r"^model_routing:\s*$", line):
            section = "model_routing"
            continue

        m_autopilot_subsection = re.match(r"^  ([A-Za-z0-9_]+):\s*$", line)
        if m_autopilot_subsection and section.startswith("autopilot"):
            name = m_autopilot_subsection.group(1)
            data["autopilot"][name] = [] if name in ("hard_escalation", "required_gates") else {}
            section = f"autopilot.{name}"
            continue

        m_autopilot_nested_list = re.match(r"^    ([A-Za-z0-9_]+):\s*$", line)
        if m_autopilot_nested_list and section.count(".") == 1:
            parent = data["autopilot"].get(section.split(".", 1)[1])
            if isinstance(parent, dict):
                name = m_autopilot_nested_list.group(1)
                parent[name] = []
                section = f"{section}.{name}"
                continue

        if section == "custom_gates":
            m_gate_dict = re.match(r"^\s+([A-Za-z0-9_-]+):\s*(.+)$", line)
            if m_gate_dict and m_gate_dict.group(1) != "name":
                cmd = m_gate_dict.group(2).strip().strip('"').strip("'")
                data["custom_gates"].append({"name": m_gate_dict.group(1), "command": cmd})
                continue

        m_item = re.match(r"^\s*-\s+name:\s*(.+)$", line)
        if m_item and section == "custom_gates":
            if current_gate:
                data["custom_gates"].append(current_gate)
            current_gate = {"name": m_item.group(1).strip().strip('"').strip("'")}
            continue
        m_cmd = re.match(r"^\s+command:\s*(.+)$", line)
        if m_cmd and current_gate is not None:
            current_gate["command"] = m_cmd.group(1).strip().strip('"').strip("'")
            continue
        m_cwd = re.match(r"^\s+cwd:\s*(.+)$", line)
        if m_cwd and current_gate is not None:
            current_gate["cwd"] = m_cwd.group(1).strip().strip('"').strip("'")
            continue
        m_list = re.match(r"^\s*-\s+(\S+)", line)
        if m_list and section.startswith("autopilot."):
            parts = section.split(".")
            target = data["autopilot"].get(parts[1])
            if len(parts) == 3 and isinstance(target, dict):
                target = target.get(parts[2])
            if isinstance(target, list):
                target.append(_parse_scalar(m_list.group(1)))
            continue
        if m_list and section == "required_gates":
            data["required_gates"].append(m_list.group(1))
            continue
        if m_list and section == "assure_skills_required":
            data.setdefault("assure_skills_required", []).append(m_list.group(1))
            continue

        m_kv = re.match(r"^(\s*)(\w+):\s*(.+)$", line)
        if m_kv:
            indent, key, val = m_kv.group(1), m_kv.group(2), m_kv.group(3).strip()
            parsed = _parse_scalar(val)
            if section == "defaults" and len(indent) <= 2:
                data["defaults"][key] = parsed
            elif section == "autopilot":
                data["autopilot"][key] = parsed
            elif section.startswith("autopilot."):
                target = data["autopilot"].get(section.split(".", 1)[1])
                if isinstance(target, dict):
                    target[key] = parsed
            elif section == "persona_mode":
                data["persona_mode"][key] = parsed
            elif section == "model_routing":
                data["model_routing"][key] = parsed

    if current_gate:
        data["custom_gates"].append(current_gate)
    return data


def load_policies_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return _parse_simple(text)


def find_policies_path(workspace: Path, feature: str) -> Path | None:
    for rel in (f".adlc5/{feature}/policies.yaml", ".adlc5/policies.yaml"):
        p = workspace / rel
        if p.is_file():
            return p
    return None


def load_policies(workspace: Path, feature: str) -> dict:
    path = find_policies_path(workspace, feature)
    if path is None:
        return {}
    raw = load_policies_file(path)
    defaults = raw.get("defaults") or {}
    autopilot = raw.get("autopilot") or {}
    merged = _merge_dict(defaults, {k: v for k, v in raw.items() if k not in ("defaults", "autopilot")})
    merged["autopilot"] = _merge_dict(merged.get("autopilot") or {}, autopilot)
    return merged


def normalize_custom_gates(policies: dict) -> list[dict]:
    gates = policies.get("custom_gates") or []
    out: list[dict] = []
    if isinstance(gates, dict):
        for name, cmd in gates.items():
            if isinstance(cmd, str):
                out.append({"name": name, "command": cmd})
            elif isinstance(cmd, dict):
                out.append({"name": name, **cmd})
        return out
    if isinstance(gates, list):
        for g in gates:
            if isinstance(g, dict) and g.get("name") and g.get("command"):
                out.append(g)
    return out


def required_gate_names(policies: dict) -> list[str]:
    names: list[str] = []
    for key in ("required_gates",):
        val = policies.get(key)
        if isinstance(val, list):
            names.extend(str(x) for x in val)
    ap = policies.get("autopilot") or {}
    if isinstance(ap.get("required_gates"), list):
        names.extend(str(x) for x in ap["required_gates"])
    qg = ap.get("quality_gates")
    if isinstance(qg, dict):
        for k in qg.get("required_custom_gates") or []:
            names.append(str(k))
    return list(dict.fromkeys(names))
