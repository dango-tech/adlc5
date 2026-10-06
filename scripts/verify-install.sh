#!/usr/bin/env bash
# Verify adlc5 install (M8 + M14 cross-platform).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/adlc5-dirs.sh
source "${ROOT}/scripts/lib/adlc5-dirs.sh"
SKILLS_ROOT="$(adlc5_skills_dir "$ROOT")"
cd "$ROOT"
PLATFORM="all"

adlc5_version() {
  local f="${ROOT}/core/VERSION"
  if [[ -f "$f" ]]; then tr -d '[:space:]' <"$f"
  else echo "0.0.0"; fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform) PLATFORM="${2:?}"; shift 2 ;;
    --version) shift 2 ;; # legacy ignored arg; use --print-version
    --print-version) echo "adlc5 $(adlc5_version)"; exit 0 ;;
    -h|--help) echo "Usage: verify-install.sh [--platform NAME] [--print-version]"; exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 1 ;;
  esac
done

CONFIG="${ROOT}/config.yaml"
[[ -f "$CONFIG" ]] || CONFIG="${ROOT}/config.example.yaml"
[[ -f "$CONFIG" ]] || { echo "ERROR: no config" >&2; exit 1; }

get_yaml_value() {
  local key="$1" file="$2"
  grep -E "^${key}:" "$file" | head -1 | sed -E "s/^${key}:[[:space:]]*//" | sed -E 's/^["'\''](.*)["'\'']$/\1/' | sed -E 's/[[:space:]]+#.*$//'
}


get_path() {
  local key="$1" default="$2"
  local val
  val="$(get_yaml_value "$key" "$CONFIG")"
  if [[ -z "$val" && -f "${ROOT}/config.example.yaml" ]]; then
    val="$(get_yaml_value "$key" "${ROOT}/config.example.yaml")"
  fi
  if [[ -z "$val" ]]; then val="$default"; fi
  expand_path "$val"
}

expand_path() {
  local path="$1"
  if [[ "$path" == "~" ]]; then printf '%s\n' "$HOME"
  elif [[ "$path" == "~/"* ]]; then printf '%s/%s\n' "$HOME" "${path:2}"
  else printf '%s\n' "$path"; fi
}

has_antigravity_plugin_target() {
  local val
  val="$(get_yaml_value antigravity_plugin_target "$CONFIG")"
  [[ -n "$val" ]] && return 0
  [[ -f "${ROOT}/config.example.yaml" ]] && val="$(get_yaml_value antigravity_plugin_target "${ROOT}/config.example.yaml")"
  [[ -n "$val" ]]
}

get_antigravity_plugin_root() {
  get_path antigravity_plugin_target "~/.gemini/config/plugins/adlc5-plugin"
}

errors=0
MIN_SKILLS=25
platform_enabled() { [[ "$PLATFORM" == "all" || "$PLATFORM" == "$1" ]]; }

verify_skills_at() {
  local target="$1" label="$2"
  echo "Skills (${label}): ${target}"
  local ok=0 total=0
  for skill_dir in "${SKILLS_ROOT}"/*/; do
    [[ -d "$skill_dir" && -f "${skill_dir}/SKILL.md" ]] || continue
    name="$(basename "$skill_dir")"
    total=$((total + 1))
    if [[ -r "${target}/${name}/SKILL.md" ]]; then echo "  OK: ${name}"; ok=$((ok + 1))
    else echo "  FAIL: ${name}" >&2; errors=$((errors + 1)); fi
  done
  echo "  (${ok}/${total})"; echo
}

echo "Verifying adlc5 $(adlc5_version) (platform=${PLATFORM})"
for f in shared/README.md shared/docs/playbook.md shared/docs/CROSS-PLATFORM.md shared/docs/README.md STRUCTURE.md platform/codex-plugin/plugin.json \
  core/guides/working-memory.md core/guides/model-matrix.md \
  core/guides/repository-context.md \
  core/guides/scaffold-registry.md core/guides/current-information.md \
  .cursor/rules/current-information.mdc shared/rules/portable/current-information.md \
  templates/memory/INDEX.md templates/memory/context-pack-story.md \
  templates/memory/promotion-candidates.md \
  templates/agent/schemas/task-spec.schema.json \
  shared/docs/project-wiki.md \
  templates/wiki/SCHEMA.md templates/wiki/index.md \
  templates/cursor-models.md \
  templates/claude-models.md templates/codex-models.md \
  templates/opencode-models.md templates/hermes-models.md templates/gemini-models.md; do
  [[ -r "${ROOT}/${f}" ]] && echo "OK: ${f}" || { echo "FAIL: ${f}" >&2; errors=$((errors + 1)); }
done
echo

echo "ADLC5 structural check:"
for f in core/VERSION core/sdd-model.md core/state-schema.json core/gates.yaml core/skill-registry.yaml core/personas.yaml \
  templates/personas/analyst.md templates/personas/architect.md templates/personas/coder.md templates/personas/tester.md \
  skills/adlc5/SKILL.md skills/specify/SKILL.md skills/plan/SKILL.md skills/tasks/SKILL.md skills/implement/SKILL.md \
  scripts/init-feature.sh scripts/pilot-autopilot.sh scripts/resolve-model.sh scripts/git-orchestrate.sh \
  scripts/repository-context.py scripts/tests/test-repository-context.py \
  scripts/memory/compact-stage.sh scripts/memory/generate-pack.sh scripts/memory/persona-pack-filter.sh scripts/memory/budget-check.py \
  scripts/tasks/render-board.sh scripts/tasks/validate-graph.py scripts/tasks/check-anchors.py \
  scripts/evaluate-runs.py scripts/runner/dispatch.sh \
  scripts/lib/state_v2.py scripts/lib/personas_load.py scripts/lib/model_routing.py \
  scripts/update-adlc5.sh \
  docs/ADLC5.md docs/ADLC5-kernel.md docs/telemetry.md docs/evaluation.md FRAMEWORK.md \
  templates/policies-tiny.yaml.example templates/policies-small-feature.yaml.example templates/policies-high-risk.yaml.example \
  scripts/adlc5 scripts/adlc5-mcp.py .cursor-plugin/plugin.json .cursor-plugin/mcp.json \
  .cursor-plugin/README.md .cursor-plugin/run-adlc5.sh .cursor-plugin/run-mcp.sh \
  platform/codex-plugin/plugin.json platform/codex-plugin/README.md; do
  [[ -r "${ROOT}/${f}" ]] && echo "  OK: ${f}" || { echo "  FAIL: ${f}" >&2; errors=$((errors + 1)); }
done
# Plugin metadata must stay VERSION-aligned and path-safe (no .. traversal)
python3 - <<'PY' || { echo "  FAIL: plugin.json metadata" >&2; errors=$((errors + 1)); }
import json
from pathlib import Path
root = Path(".")
version = (root / "core/VERSION").read_text(encoding="utf-8").strip()
path_keys = ("skills", "rules", "agents", "commands", "hooks", "mcpServers")
runtime_keys = ("kernel", "mcp", "kernel_shim", "mcp_shim", "version_file", "docs")
for rel in (".cursor-plugin/plugin.json", "platform/codex-plugin/plugin.json"):
    data = json.loads((root / rel).read_text(encoding="utf-8"))
    assert data.get("name") == "adlc5", rel
    assert data.get("version") == version, f"{rel} version {data.get('version')} != {version}"
    require_exists = rel.startswith(".cursor-plugin/")
    for key in path_keys:
        val = data.get(key)
        if not val:
            continue
        assert not str(val).startswith("/") and ".." not in Path(str(val)).parts, f"{rel} unsafe path {key}={val}"
        if require_exists:
            assert (root / str(val)).exists(), f"{rel} missing path {key}={val}"
    meta = data.get("adlc5") or {}
    assert isinstance(meta, dict) and meta.get("kernel") and meta.get("mcp"), f"{rel} missing adlc5.kernel/mcp"
    for key in runtime_keys:
        val = meta.get(key)
        if not val:
            continue
        assert ".." not in Path(str(val)).parts, f"{rel} unsafe adlc5.{key}={val}"
        if " " in str(val):
            continue
        assert (root / str(val)).exists(), f"{rel} missing adlc5.{key}={val}"
mcp = json.loads((root / ".cursor-plugin/mcp.json").read_text(encoding="utf-8"))
assert "adlc5" in mcp.get("mcpServers", {}), "mcp.json missing adlc5 server"
args = mcp["mcpServers"]["adlc5"].get("args") or []
assert any("run-mcp.sh" in str(a) or str(a).endswith("adlc5-mcp.py") for a in args), (
    "mcp.json must point at run-mcp.sh or adlc5-mcp.py"
)
print("  OK: plugin.json metadata")
PY
for s in scripts/init-feature.sh scripts/pilot-autopilot.sh scripts/resolve-model.sh scripts/git-orchestrate.sh \
  scripts/memory/compact-stage.sh scripts/memory/generate-pack.sh scripts/memory/persona-pack-filter.sh \
  scripts/tasks/render-board.sh scripts/tasks/validate-graph.py scripts/tasks/check-anchors.py \
  scripts/evaluate-runs.py scripts/runner/dispatch.sh \
  scripts/update-adlc5.sh scripts/adlc5 scripts/adlc5-mcp.py \
  .cursor-plugin/run-adlc5.sh .cursor-plugin/run-mcp.sh; do
  if [[ -x "${ROOT}/${s}" ]]; then echo "  OK (exec): ${s}"
  else echo "  FAIL (not executable): ${s}" >&2; errors=$((errors + 1)); fi
done
# Kernel + MCP smoke (distribution root; does not mutate host skill dirs)
if ./scripts/adlc5 version | grep -Eq 'adlc5 [0-9]+\.[0-9]+\.[0-9]+'; then
  echo "  OK (kernel): scripts/adlc5 version"
else
  echo "  FAIL (kernel): scripts/adlc5 version" >&2
  errors=$((errors + 1))
fi
if ./.cursor-plugin/run-adlc5.sh version | grep -Eq 'adlc5 [0-9]+\.[0-9]+\.[0-9]+'; then
  echo "  OK (plugin shim): .cursor-plugin/run-adlc5.sh"
else
  echo "  FAIL (plugin shim): .cursor-plugin/run-adlc5.sh" >&2
  errors=$((errors + 1))
fi
if ./scripts/adlc5-mcp.py --smoke >/dev/null; then
  echo "  OK (mcp smoke): scripts/adlc5-mcp.py"
else
  echo "  FAIL (mcp smoke): scripts/adlc5-mcp.py" >&2
  errors=$((errors + 1))
fi
echo

echo "Autoresearch structural check:"
for f in skills/autoresearch/SKILL.md \
  skills/autoresearch/guides/campaign-mode.md \
  skills/autoresearch/phases/00-framing.md \
  skills/autoresearch/phases/00b-decompose.md \
  skills/autoresearch/phases/01-intake.md \
  skills/autoresearch/phases/02-baseline.md \
  skills/autoresearch/phases/03-experiment-loop.md \
  skills/autoresearch/phases/04-synthesis.md \
  skills/autoresearch/guides/knowledge-base.md \
  skills/autoresearch/guides/metric-discipline.md \
  skills/autoresearch/guides/mutation-strategies.md \
  skills/autoresearch/guides/safety-and-budget.md \
  skills/autoresearch/templates/program.md \
  skills/autoresearch/templates/state.json \
  skills/autoresearch/templates/leaderboard.md \
  skills/autoresearch/templates/experiment-log.md \
  skills/autoresearch/templates/report.md \
  skills/autoresearch/templates/INDEX.md \
  skills/autoresearch/templates/campaign-state.json \
  skills/autoresearch/templates/task-state.json \
  skills/autoresearch/templates/definition-of-done.md \
  skills/autoresearch-experimenter/SKILL.md; do
  [[ -r "${ROOT}/${f}" ]] && echo "  OK: ${f}" || { echo "  FAIL: ${f}" >&2; errors=$((errors + 1)); }
done
for s in skills/autoresearch/scripts/init-campaign.sh \
  skills/autoresearch/scripts/init-task.sh \
  skills/autoresearch/scripts/init-project.sh \
  skills/autoresearch/scripts/smoke-campaign.sh \
  skills/autoresearch/scripts/run-experiment.sh \
  skills/autoresearch/scripts/log-experiment.sh \
  skills/autoresearch/scripts/check-kill-switch.sh; do
  if [[ -x "${ROOT}/${s}" ]]; then echo "  OK (exec): ${s}"
  else echo "  FAIL (not executable): ${s}" >&2; errors=$((errors + 1)); fi
done
if [[ -x "${ROOT}/skills/autoresearch/scripts/smoke-campaign.sh" ]]; then
  if "${ROOT}/skills/autoresearch/scripts/smoke-campaign.sh" >/dev/null 2>&1; then
    echo "  OK (smoke): skills/autoresearch/scripts/smoke-campaign.sh"
  else
    echo "  FAIL (smoke): skills/autoresearch/scripts/smoke-campaign.sh" >&2
    errors=$((errors + 1))
  fi
fi
echo

echo "Autopilot framework (scripts + skills):"
for f in scripts/pilot-autopilot.sh \
  skills/adlc5-assure-reworker/SKILL.md \
  skills/adlc5-design-critic/SKILL.md \
  skills/pr-reviewer/SKILL.md \
  templates/policies.yaml.example \
  docs/telemetry.md; do
  [[ -r "${ROOT}/${f}" ]] && echo "  OK: ${f}" || { echo "  FAIL: ${f}" >&2; errors=$((errors + 1)); }
done
for s in scripts/advance-phase.sh scripts/check-gates.py scripts/delivery-retry-classifier.py \
  scripts/run-tests.sh scripts/run-lint.sh scripts/run-security.sh \
  scripts/score-coverage.py scripts/check-architecture.sh scripts/tail-telemetry.sh \
  scripts/pilot.sh scripts/pilot-check-kill-switch.sh scripts/lib/telemetry.sh \
  scripts/pr-reviewer/pr-reviewer-detect.sh scripts/pr-reviewer/pr-reviewer-compose-body.sh scripts/pr-reviewer/pr-reviewer-open.sh scripts/pr-reviewer/pr-reviewer-gh.sh scripts/pr-reviewer/pr-reviewer-check-merge.sh; do
  if [[ -r "${ROOT}/${s}" ]]; then
    if [[ "${s}" == *.sh ]] && [[ ! -x "${ROOT}/${s}" ]]; then
      echo "  WARN (not executable): ${s}" >&2
    else
      echo "  OK: ${s}"
    fi
  else
    echo "  FAIL: ${s}" >&2
    errors=$((errors + 1))
  fi
done
if [[ -x "${ROOT}/scripts/tests/run-all.sh" ]]; then
  if "${ROOT}/scripts/tests/run-all.sh" >/dev/null 2>&1; then
    echo "  OK (contract tests): scripts/tests/run-all.sh"
  else
    echo "  FAIL (contract tests): scripts/tests/run-all.sh" >&2
    errors=$((errors + 1))
  fi
fi
echo

echo "Project wiki scripts:"
for s in scripts/wiki/init-wiki.sh scripts/wiki/ingest-repo.sh \
  scripts/wiki/validate-claim.sh scripts/wiki/lint.sh \
  scripts/wiki/rebuild-index.sh scripts/wiki/promote-prepare.sh \
  scripts/wiki/promote-apply.sh; do
  if [[ -x "${ROOT}/${s}" ]]; then echo "  OK (exec): ${s}"
  else echo "  FAIL (not executable): ${s}" >&2; errors=$((errors + 1)); fi
done
[[ -r "${ROOT}/skills/project-wiki/SKILL.md" ]] && echo "  OK: skills/project-wiki/SKILL.md" \
  || { echo "  FAIL: skills/project-wiki/SKILL.md" >&2; errors=$((errors + 1)); }
if [[ -x "${ROOT}/scripts/wiki/smoke-test.sh" ]]; then
  if "${ROOT}/scripts/wiki/smoke-test.sh" >/dev/null 2>&1; then
    echo "  OK (smoke): scripts/wiki/smoke-test.sh"
  else
    echo "  FAIL (smoke): scripts/wiki/smoke-test.sh" >&2
    errors=$((errors + 1))
  fi
fi
echo

if python3 "${ROOT}/scripts/tests/test-repository-context.py" >/dev/null 2>&1; then
  echo "Repository context: OK"
else
  echo "Repository context: FAIL" >&2
  errors=$((errors + 1))
fi
echo

if platform_enabled cursor; then
  verify_skills_at "$(expand_path "$(get_yaml_value skills_install_target "$CONFIG")")" "cursor"
  rt="$(get_path rules_install_target "~/.cursor/rules")"
  echo "Rules (cursor): ${rt}"
  for rf in "${ROOT}/.cursor/rules"/*.mdc; do
    [[ -f "$rf" ]] || continue
    n="$(basename "$rf")"
    [[ -r "${rt}/${n}" ]] && echo "  OK: ${n}" || { echo "  FAIL: ${n}" >&2; errors=$((errors + 1)); }
  done
  echo
  if [[ -x "${ROOT}/scripts/smoke-test-council.sh" ]]; then
    if "${ROOT}/scripts/smoke-test-council.sh" >/dev/null 2>&1; then
      echo "Council agents (cursor): OK"
    else
      echo "Council agents (cursor): WARN (run ./scripts/install-council-agents.sh)" >&2
    fi
    echo
  fi
fi
if platform_enabled claude; then verify_skills_at "$(get_path claude_skills_target "~/.claude/skills")" "claude"; fi
if platform_enabled codex; then verify_skills_at "$(get_path codex_skills_target "~/.codex/skills")" "codex"; fi
if platform_enabled opencode; then verify_skills_at "$(get_path opencode_skills_target "~/.config/opencode/skills")" "opencode"; fi
if platform_enabled gemini; then verify_skills_at "$(get_path gemini_skills_target "~/.gemini/skills")" "gemini"; fi
if platform_enabled hermes; then verify_skills_at "$(get_path hermes_skills_target "~/.hermes/skills/adlc5")" "hermes"; fi
if platform_enabled antigravity; then
  if has_antigravity_plugin_target; then
    verify_skills_at "$(get_antigravity_plugin_root)/skills" "antigravity"
  else
    verify_skills_at "$(get_path antigravity_skills_target "~/.gemini/antigravity/skills")" "antigravity"
  fi
fi

[[ "$errors" -gt 0 ]] && { echo "FAILED (${errors})" >&2; exit 1; }
echo "Verification passed. See shared/docs/CROSS-PLATFORM.md"
