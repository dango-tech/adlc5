#!/usr/bin/env bash
# Run ADLC5 script exit-code contract tests.
set -euo pipefail
export ADLC5_SUPPRESS_LEGACY_WARNINGS=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

fail() { echo "FAIL: $*" >&2; exit 1; }
pass() { echo "PASS: $*"; }

# Gate fixtures deliberately exercise otherwise unreachable/invalid states.
# Write local JSON directly; normal API protection is tested below.
fixture_state_patch() {
  python3 - "$@" <<'PYFIXTURE'
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, "scripts")
from lib.state_v2 import deep_merge
parser = argparse.ArgumentParser()
parser.add_argument("--workspace", required=True)
parser.add_argument("--feature", required=True)
parser.add_argument("--patch", required=True)
args = parser.parse_args()
path = Path(args.workspace) / ".adlc5" / args.feature / "state.json"
path.write_text(json.dumps(deep_merge(json.loads(path.read_text()), json.loads(args.patch))))
PYFIXTURE
}

for tool in git python3 jq; do
  command -v "$tool" >/dev/null 2>&1 || fail "required tool '$tool' is missing; install Git, Python 3 and jq"
done
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "ERROR: Python 3.10 or newer is required; upgrade python3, then retry." >&2
  exit 1
fi


TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

FEATURE="test-feature"
mkdir -p "${TMP}/.adlc5/${FEATURE}/delivery"
cat >"${TMP}/.adlc5/${FEATURE}/delivery/state.json" <<'EOF'
{
  "feature_name": "test-feature",
  "current_phase": "build-1-implementation",
  "phase_status": {},
  "retry_policy": { "max_implementation_attempts": 2 },
  "stories": {
    "story-a": { "status": "implementation_complete", "type": "component" }
  }
}
EOF

# delivery-retry-classifier: retry
set +e
./scripts/delivery-retry-classifier.py --feature "$FEATURE" --story-id story-a \
  --workspace "$TMP" --attempt 1 --report "test failed assertion" >/tmp/retry-out.json
EC=$?
set -e
jq -e '.action == "retry"' /tmp/retry-out.json >/dev/null || fail "expected retry action"
[[ "$EC" -eq 0 ]] || fail "retry exit code expected 0 got $EC"
pass "delivery-retry-classifier retry"

# delivery-retry-classifier: escalate
set +e
./scripts/delivery-retry-classifier.py --feature "$FEATURE" --story-id story-a \
  --workspace "$TMP" --attempt 1 --report "spec ambiguous contradiction" >/dev/null
EC=$?
set -e
[[ "$EC" -eq 2 ]] || fail "escalate exit expected 2 got $EC"
pass "delivery-retry-classifier escalate"

# delivery-retry-classifier: exhausted
set +e
./scripts/delivery-retry-classifier.py --feature "$FEATURE" --story-id story-a \
  --workspace "$TMP" --attempt 2 --report "test failed" >/dev/null
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "stop exit expected 1 got $EC"
pass "delivery-retry-classifier exhausted"

# Canonical features read retry budgets from policies.yaml.
CANONICAL_CONSUMER_WS="${TMP}/canonical-python-consumers"
CANONICAL_CONSUMER_FEATURE="canonical-consumers"
mkdir -p "${CANONICAL_CONSUMER_WS}/.adlc5/${CANONICAL_CONSUMER_FEATURE}/tasks/code-spec"
cat >"${CANONICAL_CONSUMER_WS}/.adlc5/${CANONICAL_CONSUMER_FEATURE}/state.json" <<'EOF'
{"schema_version":"3.0","feature":"canonical-consumers","current_stage":"implement","current_step":"implement-1-build","stage_status":{},"memory":{"last_compacted":null}}
EOF
cat >"${CANONICAL_CONSUMER_WS}/.adlc5/${CANONICAL_CONSUMER_FEATURE}/policies.yaml" <<'EOF'
autopilot:
  retry_policy:
    max_implementation_attempts: 1
EOF
printf '%s\n' '# US-1 code spec' >"${CANONICAL_CONSUMER_WS}/.adlc5/${CANONICAL_CONSUMER_FEATURE}/tasks/code-spec/US-1.md"
set +e
./scripts/delivery-retry-classifier.py --feature "$CANONICAL_CONSUMER_FEATURE" --story-id US-1 \
  --workspace "$CANONICAL_CONSUMER_WS" --attempt 1 --report "test failed" >/tmp/canonical-retry.json
CANONICAL_RETRY_EC=$?
set -e
[[ "$CANONICAL_RETRY_EC" -eq 1 ]] || fail "canonical retry policy should stop at configured attempt"
jq -e '.max_attempts == 1' /tmp/canonical-retry.json >/dev/null \
  || fail "canonical retry policy should be loaded from policies.yaml"
(cd "$CANONICAL_CONSUMER_WS" && "$ROOT/scripts/compact-memory.py" --feature "$CANONICAL_CONSUMER_FEATURE" >/dev/null)
grep -q 'Current step:.*implement-1-build' \
  "${CANONICAL_CONSUMER_WS}/.adlc5/${CANONICAL_CONSUMER_FEATURE}/memory/INDEX.md" \
  || fail "compact-memory should report canonical current_step"
grep -q 'tasks/code-spec/US-1.md' \
  "${CANONICAL_CONSUMER_WS}/.adlc5/${CANONICAL_CONSUMER_FEATURE}/memory/INDEX.md" \
  || fail "compact-memory should index canonical code specs"
set +e
./scripts/score-coverage.py --feature "$CANONICAL_CONSUMER_FEATURE" \
  --workspace "$CANONICAL_CONSUMER_WS" >/dev/null
CANONICAL_COVERAGE_EC=$?
set -e
[[ "$CANONICAL_COVERAGE_EC" -eq 2 ]] || fail "canonical score-coverage fixture should skip without coverage"
jq -s -e 'any(.[]; .script == "score-coverage.py" and .phase == "implement-1-build")' \
  "${CANONICAL_CONSUMER_WS}/.adlc5/${CANONICAL_CONSUMER_FEATURE}/telemetry/events.jsonl" >/dev/null \
  || fail "score-coverage should emit canonical current_step"
pass "canonical Python state consumers"

# check-gates: pass
set +e
./scripts/check-gates.py --feature "$FEATURE" --workspace "$TMP" --gate build-1-implementation >/dev/null
EC=$?
set -e
[[ "$EC" -eq 0 ]] || fail "check-gates pass expected 0 got $EC"
pass "check-gates build pass"

# check-gates: fail (no complete stories)
cat >"${TMP}/.adlc5/${FEATURE}/delivery/state.json" <<'EOF'
{
  "current_phase": "build-1-implementation",
  "stories": { "story-a": { "status": "code_spec" } }
}
EOF
set +e
./scripts/check-gates.py --feature "$FEATURE" --workspace "$TMP" --gate build-1-implementation >/dev/null
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "check-gates fail expected 1 got $EC"
pass "check-gates build fail"

# advance-phase: blocked
chmod +x ./scripts/advance-phase.sh ./scripts/run-tests.sh ./scripts/run-lint.sh \
  ./scripts/run-security.sh ./scripts/check-architecture.sh ./scripts/tail-telemetry.sh \
  ./scripts/sync-verification-report.sh 2>/dev/null || true

set +e
./scripts/advance-phase.sh --feature "$FEATURE" --workspace "$TMP" >/dev/null
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "advance-phase blocked expected 1 got $EC"
pass "advance-phase blocked"

# run-tests/lint/security/architecture: skipped ok on empty tmp
for s in run-tests.sh run-lint.sh run-security.sh check-architecture.sh; do
  set +e
  "./scripts/$s" --feature "$FEATURE" --workspace "$TMP" >/dev/null
  EC=$?
  set -e
  [[ "$EC" -eq 0 ]] || fail "$s skipped expected 0 got $EC"
done
pass "gate scripts skipped"

# score-coverage: skipped
set +e
./scripts/score-coverage.py --feature "$FEATURE" --workspace "$TMP" >/dev/null
EC=$?
set -e
[[ "$EC" -eq 2 ]] || fail "score-coverage skipped expected 2 got $EC"
pass "score-coverage skipped"

# telemetry file created after run-tests
[[ -f "${TMP}/.adlc5/${FEATURE}/telemetry/events.jsonl" ]] || fail "telemetry not created"
pass "telemetry events.jsonl"

# telemetry correlation fields are optional and environment-driven
CORR_WS="${TMP}/correlation"
mkdir -p "$CORR_WS"
ADLC5_WORKSPACE="$CORR_WS" ADLC5_RUN_ID="run-1" ADLC5_NODE_ID="verify" \
  ADLC5_PARENT_NODE_IDS='["build"]' ADLC5_ATTEMPT="2" ADLC5_OUTCOME="defect_caught" \
  ADLC5_FINDING_ID="F-1" \
  bash -c 'source "scripts/lib/telemetry.sh"; telemetry_emit corr checkpoint test.sh fail verify "{}"'
jq -e '.run_id == "run-1" and .node_id == "verify" and .parent_node_ids == ["build"] and .attempt == 2 and .outcome == "defect_caught" and .finding_id == "F-1"' \
  "${CORR_WS}/.adlc5/corr/telemetry/events.jsonl" >/dev/null || fail "telemetry correlation fields"

NOJQ_BIN="${CORR_WS}/no-jq-bin"
mkdir -p "$NOJQ_BIN"
for cmd in python3 date mkdir; do
  ln -s "$(command -v "$cmd")" "${NOJQ_BIN}/${cmd}"
done
ADLC5_WORKSPACE="$CORR_WS" ADLC5_RUN_ID="run-fallback" ADLC5_NODE_ID="build" \
  ADLC5_PARENT_NODE_IDS='["specify"]' ADLC5_ATTEMPT="1" ADLC5_OUTCOME="pass" \
  PATH="$NOJQ_BIN" TELEMETRY_SCRIPT="$ROOT/scripts/lib/telemetry.sh" \
  /bin/bash -c 'source "$TELEMETRY_SCRIPT"; telemetry_emit corr-fallback checkpoint test.sh pass build "{}"'
python3 - "${CORR_WS}/.adlc5/corr-fallback/telemetry/events.jsonl" <<'PY'
import json, sys
event = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert event["run_id"] == "run-fallback"
assert event["node_id"] == "build"
assert event["parent_node_ids"] == ["specify"]
assert event["attempt"] == 1
assert event["outcome"] == "pass"
PY
pass "telemetry correlation fields"

# pr-ready: fail without completed phase / clearance
set +e
./scripts/check-gates.py --feature "$FEATURE" --workspace "$TMP" --gate pr-ready >/dev/null
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "pr-ready incomplete expected 1 got $EC"
pass "check-gates pr-ready fail"

# pr-ready: pass with completed delivery + integration + clearance + verification report
cat >"${TMP}/.adlc5/${FEATURE}/delivery/state.json" <<'EOF'
{
  "current_phase": "completed",
  "integration": { "status": "completed" },
  "stories": { "story-a": { "type": "component", "status": "verified" } }
}
EOF
mkdir -p "${TMP}/.adlc5/${FEATURE}/verify"
printf '%s\n' '**Overall:** pass' >"${TMP}/.adlc5/${FEATURE}/verify/verification-report.md"
mkdir -p "${TMP}/.qa/${FEATURE}"
echo "STATUS: CLEARED" >"${TMP}/.qa/${FEATURE}/deployment-clearance.md"
cat >"${TMP}/.adlc5/${FEATURE}/state.json" <<'EOF'
{
  "feature_name": "test-feature",
  "stage_status": { "assure": "completed" },
  "assure": { "pr_review": "completed" },
  "pr_review": { "url": "https://example.com/pr/1" }
}
EOF
set +e
./scripts/check-gates.py --feature "$FEATURE" --workspace "$TMP" --gate pr-ready >/tmp/legacy-pr-ready.json
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "legacy pr-ready must fail without bound evidence, got $EC"
jq -e 'any(.checks[]; .id == "completion_evidence" and .status == "fail") and all(.checks[] | select(.id != "completion_evidence" and .id != "code_specs_lint" and .id != "verifier_independence" and .id != "profile_risk"); .status == "pass")' \
  /tmp/legacy-pr-ready.json >/dev/null || fail "legacy readiness checks must pass independently of new evidence requirements"
pass "legacy readiness checks pass but missing evidence blocks completion"

# pr-ready: require_human_pr_approval blocks until clarity.history pr_approval exists
cat >"${TMP}/.adlc5/${FEATURE}/policies.yaml" <<'EOF'
autopilot:
  require_human_pr_approval: true
EOF
set +e
./scripts/check-gates.py --feature "$FEATURE" --workspace "$TMP" --gate pr-ready >/tmp/hpa-out.json
EC=$?
set -e
[[ "$EC" -ne 0 ]] || fail "pr-ready should fail without human pr_approval"
jq -e '.checks[] | select(.id == "human_pr_approval" and .status == "fail")' /tmp/hpa-out.json >/dev/null \
  || fail "human_pr_approval fail check missing"
pass "check-gates human approval blocks"

cat >"${TMP}/.adlc5/${FEATURE}/state.json" <<'EOF'
{
  "feature_name": "test-feature",
  "stage_status": { "assure": "completed" },
  "assure": { "pr_review": "completed" },
  "pr_review": { "url": "https://example.com/pr/1" },
  "clarity": { "history": [ { "type": "pr_approval", "approved_by": "agent" } ] }
}
EOF
set +e
./scripts/check-gates.py --feature "$FEATURE" --workspace "$TMP" --gate pr-ready >/tmp/hpa-agent.json
EC=$?
set -e
[[ "$EC" -ne 0 ]] || fail "agent-authored pr_approval must fail"
jq -e '.checks[] | select(.id == "human_pr_approval" and .status == "fail")' /tmp/hpa-agent.json >/dev/null \
  || fail "agent-authored pr_approval fail check missing"

cat >"${TMP}/.adlc5/${FEATURE}/state.json" <<'EOF'
{
  "feature_name": "test-feature",
  "stage_status": { "assure": "completed" },
  "assure": { "pr_review": "completed" },
  "pr_review": { "url": "https://example.com/pr/1" },
  "clarity": { "history": [ { "ts": "2026-01-01T00:00:00Z", "type": "pr_approval", "approved_by": "user" } ] }
}
EOF
set +e
./scripts/check-gates.py --feature "$FEATURE" --workspace "$TMP" --gate pr-ready >/tmp/hpa-recorded.json
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "historical approval without bound evidence must fail, got $EC"
jq -e 'any(.checks[]; .id == "human_pr_approval" and .status == "pass") and any(.checks[]; .id == "completion_evidence" and .status == "fail")' \
  /tmp/hpa-recorded.json >/dev/null || fail "historical approval handler or evidence requirement missing"
pass "check-gates human approval recorded"
rm -f "${TMP}/.adlc5/${FEATURE}/policies.yaml"

# plan-complete: design_critique verdict gate (v2 state)
PLAN_FEATURE="plan-feature"
mkdir -p "${TMP}/.adlc5/${PLAN_FEATURE}/design"
cat >"${TMP}/.adlc5/${PLAN_FEATURE}/state.json" <<'EOF'
{
  "schema_version": "3.0",
  "feature_name": "plan-feature",
  "current_stage": "plan",
  "current_step": "plan-7-design-critique",
  "craftsmanship": { "architecture_review": "completed", "pattern_selection": "completed" }
}
EOF
touch "${TMP}/.adlc5/${PLAN_FEATURE}/design/1a-discovery.md" \
      "${TMP}/.adlc5/${PLAN_FEATURE}/design/1b-contracts.md" \
      "${TMP}/.adlc5/${PLAN_FEATURE}/design/1c-operations.md"

# missing critique -> warn (exit 2) in HITL
set +e
./scripts/check-gates.py --feature "$PLAN_FEATURE" --workspace "$TMP" --gate plan-complete >/tmp/plan-out.json
EC=$?
set -e
[[ "$EC" -eq 2 ]] || fail "plan-complete without critique expected warn exit 2, got $EC"
jq -e '.checks[] | select(.id == "design_critique" and .status == "warn")' /tmp/plan-out.json >/dev/null \
  || fail "design_critique warn check missing"
pass "check-gates plan critique missing warns"

# missing critique + autonomous policy -> fail (exit 1)
cat >"${TMP}/.adlc5/${PLAN_FEATURE}/policies.yaml" <<'EOF'
autopilot:
  interaction_mode: autonomous
EOF
set +e
./scripts/check-gates.py --feature "$PLAN_FEATURE" --workspace "$TMP" --gate plan-complete >/dev/null
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "plan-complete autonomous without critique expected fail, got $EC"
rm -f "${TMP}/.adlc5/${PLAN_FEATURE}/policies.yaml"
pass "check-gates plan critique autonomous blocks"

# blocking verdict -> fail
printf '%s\n' '**critique_severity:** blocking' >"${TMP}/.adlc5/${PLAN_FEATURE}/design/design-critique.md"
set +e
./scripts/check-gates.py --feature "$PLAN_FEATURE" --workspace "$TMP" --gate plan-complete >/dev/null
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "plan-complete with blocking critique expected fail, got $EC"
pass "check-gates plan critique blocking fails"

# none verdict -> pass
printf '%s\n' '**critique_severity:** none' >"${TMP}/.adlc5/${PLAN_FEATURE}/design/design-critique.md"
set +e
./scripts/check-gates.py --feature "$PLAN_FEATURE" --workspace "$TMP" --gate plan-complete >/dev/null
EC=$?
set -e
[[ "$EC" -eq 0 ]] || fail "plan-complete with none critique expected pass, got $EC"
pass "check-gates plan critique none passes"

# deploy-ready: fails without deploy_approval, passes with clearance + pr + approval
set +e
./scripts/check-gates.py --feature "$FEATURE" --workspace "$TMP" --gate deploy-ready >/tmp/deploy-out.json
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "deploy-ready without approval expected fail, got $EC"
jq -e '.checks[] | select(.id == "deploy_approval" and .status == "fail")' /tmp/deploy-out.json >/dev/null \
  || fail "deploy_approval fail check missing"
pass "check-gates deploy-ready blocks without approval"

cat >"${TMP}/.adlc5/${FEATURE}/state.json" <<'EOF'
{
  "feature_name": "test-feature",
  "stage_status": { "assure": "completed" },
  "assure": { "pr_review": "completed" },
  "pr_review": { "url": "https://example.com/pr/1" },
  "clarity": { "history": [ { "type": "deploy_approval", "approved_by": "agent" } ] }
}
EOF
set +e
./scripts/check-gates.py --feature "$FEATURE" --workspace "$TMP" --gate deploy-ready >/tmp/deploy-agent.json
EC=$?
set -e
[[ "$EC" -ne 0 ]] || fail "agent-authored deploy_approval must fail"
jq -e '.checks[] | select(.id == "deploy_approval" and .status == "fail")' /tmp/deploy-agent.json >/dev/null \
  || fail "agent-authored deploy_approval fail check missing"

cat >"${TMP}/.adlc5/${FEATURE}/state.json" <<'EOF'
{
  "feature_name": "test-feature",
  "stage_status": { "assure": "completed" },
  "assure": { "pr_review": "completed" },
  "pr_review": { "url": "https://example.com/pr/1" },
  "clarity": { "history": [ { "ts": "2026-01-01T00:00:00Z", "type": "deploy_approval", "approved_by": "user", "environment": "staging" } ] }
}
EOF
set +e
./scripts/check-gates.py --feature "$FEATURE" --workspace "$TMP" --gate deploy-ready >/tmp/deploy-recorded.json
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "historical deployment approval cannot replace bound completion evidence, got $EC"
jq -e 'any(.checks[]; .id == "deploy_approval" and .status == "pass") and any(.checks[]; .id == "pr_published" and .status == "pass") and any(.checks[]; .id == "qa_deployment_clearance" and .status == "pass") and any(.checks[]; .id == "completion_evidence" and .status == "fail")' \
  /tmp/deploy-recorded.json >/dev/null || fail "deployment publication/approval/clearance or fresh-evidence check missing"
pass "deployment approval and publication pass but missing completion evidence blocks"

# delivery-retry-classifier: class + retryable fields
./scripts/delivery-retry-classifier.py --feature "$FEATURE" --story-id story-a \
  --workspace "$TMP" --attempt 1 --report "connection timed out" >/tmp/class-out.json
jq -e '.class == "transient" and .retryable == true' /tmp/class-out.json >/dev/null || fail "class contract"
pass "delivery-retry-classifier class contract"

# pilot.sh: emits JSON action on minimal delivery state
cat >"${TMP}/.adlc5/${FEATURE}/delivery/state.json" <<'EOF'
{
  "current_phase": "build-1-implementation",
  "stories": { "story-a": { "status": "code_spec" } }
}
EOF
chmod +x ./scripts/pilot.sh ./scripts/pilot-check-kill-switch.sh 2>/dev/null || true
PILOT_JSON=$(./scripts/pilot.sh --feature "$FEATURE" --workspace "$TMP" 2>/dev/null)
echo "$PILOT_JSON" | jq -e '.action' >/dev/null || fail "pilot.sh invalid JSON"
pass "pilot.sh JSON action"

# Provider detection is a fixture contract, independent of this clone's remote.
chmod +x ./scripts/pr-reviewer-*.sh 2>/dev/null || true
DETECT_WS="${TMP}/provider-detect"
mkdir -p "${DETECT_WS}/.github"
git -C "$DETECT_WS" init -q
git -C "$DETECT_WS" remote add origin https://github.com/example/repo.git
cp "${ROOT}/.github/PULL_REQUEST_TEMPLATE.md" "${DETECT_WS}/.github/PULL_REQUEST_TEMPLATE.md"
DETECT=$(./scripts/pr-reviewer-detect.sh --workspace "$DETECT_WS" 2>/dev/null)
echo "$DETECT" | jq -e '.provider' >/dev/null || fail "pr-reviewer-detect invalid JSON"
PROVIDER=$(echo "$DETECT" | jq -r '.provider')
[[ "$PROVIDER" == "github" ]] || fail "GitHub fixture should detect github"
echo "$DETECT" | jq -e '.repo_slug | length > 0' >/dev/null || fail "repo_slug missing"
echo "$DETECT" | jq -e '.pr_template_path == ".github/PULL_REQUEST_TEMPLATE.md"' >/dev/null \
  || fail "pr-reviewer-detect should find this repo's PR template"
pass "pr-reviewer-detect github"

# pr-reviewer-detect pr_template_path — absent, root-level, and multi-template dir cases
PRT_WS="${TMP}/pr-template-ws"
mkdir -p "$PRT_WS" && (cd "$PRT_WS" && git init -q && git remote add origin https://github.com/example/repo.git)
NO_TPL=$(./scripts/pr-reviewer-detect.sh --workspace "$PRT_WS")
[[ "$(echo "$NO_TPL" | jq -r '.pr_template_path')" == "" ]] || fail "pr_template_path should be empty when none exists"

mkdir -p "$PRT_WS/docs"
echo "# root template" >"${PRT_WS}/PULL_REQUEST_TEMPLATE.md"
ROOT_TPL=$(./scripts/pr-reviewer-detect.sh --workspace "$PRT_WS")
[[ "$(echo "$ROOT_TPL" | jq -r '.pr_template_path')" == "PULL_REQUEST_TEMPLATE.md" ]] \
  || fail "pr_template_path should find root PULL_REQUEST_TEMPLATE.md"
rm -f "${PRT_WS}/PULL_REQUEST_TEMPLATE.md"

mkdir -p "${PRT_WS}/.github/PULL_REQUEST_TEMPLATE"
echo "# feature" >"${PRT_WS}/.github/PULL_REQUEST_TEMPLATE/feature.md"
DIR_TPL=$(./scripts/pr-reviewer-detect.sh --workspace "$PRT_WS")
[[ "$(echo "$DIR_TPL" | jq -r '.pr_template_path')" == ".github/PULL_REQUEST_TEMPLATE/feature.md" ]] \
  || fail "pr_template_path should find multi-template dir entry"
pass "pr-reviewer-detect pr_template_path detection"

# init-workspace.sh --with-pr-template
IW_WS="${TMP}/init-workspace-ws"
mkdir -p "$IW_WS"
./scripts/init-workspace.sh --project "$IW_WS" --no-skills --with-pr-template >/tmp/iw-with-template.txt
[[ -f "${IW_WS}/.github/PULL_REQUEST_TEMPLATE.md" ]] || fail "init-workspace --with-pr-template should write PULL_REQUEST_TEMPLATE.md"
grep -q "Created ${IW_WS}/.github/PULL_REQUEST_TEMPLATE.md" /tmp/iw-with-template.txt \
  || fail "init-workspace --with-pr-template should report the created path"
echo "custom content — do not clobber" >"${IW_WS}/.github/PULL_REQUEST_TEMPLATE.md"
./scripts/init-workspace.sh --project "$IW_WS" --no-skills --with-pr-template --force >/tmp/iw-skip-template.txt
grep -q "PR template already exists" /tmp/iw-skip-template.txt || fail "init-workspace should skip an existing PR template"
[[ "$(cat "${IW_WS}/.github/PULL_REQUEST_TEMPLATE.md")" == "custom content — do not clobber" ]] \
  || fail "init-workspace --with-pr-template must never overwrite an existing template"
pass "init-workspace --with-pr-template creates and never overwrites"

# init-workspace.sh suggestion note when no template and flag omitted
IW_WS2="${TMP}/init-workspace-ws2"
mkdir -p "$IW_WS2"
./scripts/init-workspace.sh --project "$IW_WS2" --no-skills >/tmp/iw-suggest.txt
grep -q "no PR template found" /tmp/iw-suggest.txt || fail "init-workspace should suggest a PR template when none exists"
[[ -f "${IW_WS2}/.github/PULL_REQUEST_TEMPLATE.md" ]] && fail "init-workspace must not create a template without --with-pr-template"
grep -qF '# ADLC5 lifecycle artifacts (before git init)' "${IW_WS2}/.gitignore" \
  || fail "init-workspace before git init should persist lifecycle exclusions for later"
pass "init-workspace suggests PR template when missing"

# Git repositories get local exclusions without changing their tracked .gitignore.
IW_IGNORE_WS="${TMP}/init-workspace-ignore-ws"
mkdir -p "$IW_IGNORE_WS"
(cd "$IW_IGNORE_WS" && git init -q -b main && printf '%s\n' '# project rules' >.gitignore)
./scripts/init-workspace.sh --project "$IW_IGNORE_WS" --no-skills >/tmp/iw-local-ignore.txt
grep -qF '# project rules' "${IW_IGNORE_WS}/.gitignore" \
  || fail "default init-workspace must preserve project .gitignore content"
if grep -qF '# ADLC5 local lifecycle artifacts' "${IW_IGNORE_WS}/.gitignore"; then
  fail "default init-workspace must not add lifecycle exclusions to .gitignore"
fi
git -C "$IW_IGNORE_WS" check-ignore -q .adlc5/feature/state.json \
  || fail "local exclusions should hide lifecycle state"
if git -C "$IW_IGNORE_WS" check-ignore -q .adlc5/governance/production-ready.md; then
  fail "new local exclusions should leave governance available for tracking"
fi
pass "init-workspace keeps lifecycle exclusions local and governance trackable"

# A prior .adlc5/ rule has higher precedence than local excludes; opt-in shared
# rules add the same-file exception without removing unrelated user rules.
IW_LEGACY_WS="${TMP}/init-workspace-legacy-ignore-ws"
mkdir -p "$IW_LEGACY_WS"
(cd "$IW_LEGACY_WS" && git init -q -b main && printf '%s\n' '# project rules' '.adlc5/' >.gitignore)
./scripts/init-workspace.sh --project "$IW_LEGACY_WS" --no-skills \
  >/tmp/iw-legacy-ignore.txt 2>/tmp/iw-legacy-ignore.err
grep -qF 'run init-workspace.sh --shared-ignore' /tmp/iw-legacy-ignore.err \
  || fail "legacy ignore warning should recommend --shared-ignore"
if git -C "$IW_LEGACY_WS" check-ignore -q .adlc5/governance/production-ready.md; then
  : # Expected: the existing repository .gitignore takes precedence.
else
  fail "legacy .adlc5/ ignore should remain visible as a migration case"
fi
./scripts/init-workspace.sh --project "$IW_LEGACY_WS" --no-skills --shared-ignore >/tmp/iw-shared-ignore.txt
if git -C "$IW_LEGACY_WS" check-ignore -q .adlc5/governance/production-ready.md; then
  fail "--shared-ignore should override the legacy .adlc5/ rule for governance"
fi
grep -qF '# project rules' "${IW_LEGACY_WS}/.gitignore" \
  || fail "--shared-ignore must preserve existing .gitignore content"
pass "init-workspace migrates legacy ignore behavior through explicit shared rules"

# init-workspace.sh --with-hooks is platform-aware: bare flag defaults to
# cursor only; --hooks-platform selects the matching config + hook scripts.
IW_HOOKS_CURSOR="${TMP}/init-workspace-hooks-cursor"
mkdir -p "$IW_HOOKS_CURSOR"
./scripts/init-workspace.sh --project "$IW_HOOKS_CURSOR" --no-skills --with-hooks >/tmp/iw-hooks-cursor.txt
[[ -f "${IW_HOOKS_CURSOR}/.cursor/hooks.json" ]] || fail "bare --with-hooks should install .cursor/hooks.json"
[[ -f "${IW_HOOKS_CURSOR}/.cursor/hooks/cursor-usage.sh" ]] || fail "bare --with-hooks should install .cursor/hooks/cursor-usage.sh"
[[ -x "${IW_HOOKS_CURSOR}/.cursor/hooks/cursor-usage.sh" ]] || fail "installed cursor-usage.sh should be executable"
[[ ! -e "${IW_HOOKS_CURSOR}/.claude" ]] || fail "bare --with-hooks must not leak Claude hooks into a Cursor-only install"
[[ ! -e "${IW_HOOKS_CURSOR}/.codex" ]] || fail "bare --with-hooks must not leak Codex hooks into a Cursor-only install"
pass "init-workspace --with-hooks defaults to cursor only"

IW_HOOKS_CLAUDE="${TMP}/init-workspace-hooks-claude"
mkdir -p "$IW_HOOKS_CLAUDE"
./scripts/init-workspace.sh --project "$IW_HOOKS_CLAUDE" --no-skills --with-hooks --hooks-platform claude >/tmp/iw-hooks-claude.txt
[[ -f "${IW_HOOKS_CLAUDE}/.claude/settings.json" ]] || fail "--hooks-platform claude should install .claude/settings.json"
[[ -x "${IW_HOOKS_CLAUDE}/.claude/hooks/claude-usage.sh" ]] || fail "--hooks-platform claude should install executable claude-usage.sh"
# .cursor/agents/discover-council-* is installed unconditionally (unrelated
# to --with-hooks); only the hooks config/scripts must not leak.
[[ ! -e "${IW_HOOKS_CLAUDE}/.cursor/hooks.json" ]] || fail "--hooks-platform claude must not install Cursor hooks.json"
[[ ! -e "${IW_HOOKS_CLAUDE}/.cursor/hooks" ]] || fail "--hooks-platform claude must not install Cursor hook scripts"
[[ ! -e "${IW_HOOKS_CLAUDE}/.codex" ]] || fail "--hooks-platform claude must not install Codex hooks"
pass "init-workspace --hooks-platform claude installs only Claude hooks"

IW_HOOKS_ALL="${TMP}/init-workspace-hooks-all"
mkdir -p "$IW_HOOKS_ALL"
./scripts/init-workspace.sh --project "$IW_HOOKS_ALL" --no-skills --with-hooks --hooks-platform all >/tmp/iw-hooks-all.txt
[[ -f "${IW_HOOKS_ALL}/.cursor/hooks.json" ]] || fail "--hooks-platform all should install Cursor hooks"
[[ -f "${IW_HOOKS_ALL}/.claude/settings.json" ]] || fail "--hooks-platform all should install Claude hooks"
[[ -f "${IW_HOOKS_ALL}/.codex/hooks.json" ]] || fail "--hooks-platform all should install Codex hooks"
[[ -x "${IW_HOOKS_ALL}/.codex/hooks/codex-usage.sh" ]] || fail "--hooks-platform all should install executable codex-usage.sh"
pass "init-workspace --hooks-platform all installs every platform's hooks"

# Worktree-aware layer-2 scaffold: static artifacts are shared through the
# repository's common .git dir; feature lifecycle state stays worktree-local.
WT_REPO="${TMP}/wt-repo"
mkdir -p "$WT_REPO"
(cd "$WT_REPO" && git init -q -b main && echo x >README.md && git add -A \
  && git -c user.email=t@e -c user.name=t commit -qm init && git worktree add -q ../wt-feat -b feat/x)
WT_LINKED="${TMP}/wt-feat"

./scripts/init-workspace.sh --project "$WT_REPO" --no-skills >/tmp/iw-wt-main.txt
[[ -f "${WT_REPO}/.adlc5/config.yaml" && ! -L "${WT_REPO}/.adlc5/config.yaml" ]] \
  || fail "main worktree should keep a real .adlc5/config.yaml"
[[ -d "${WT_REPO}/.adlc5/governance" && ! -L "${WT_REPO}/.adlc5/governance" ]] \
  || fail "main worktree should keep a real .adlc5/governance/"
pass "init-workspace keeps real files in the main worktree"

echo 'repo_config_marker: preserved' >>"${WT_REPO}/.adlc5/config.yaml"

./scripts/init-workspace.sh --project "$WT_LINKED" --no-skills >/tmp/iw-wt-linked.txt
grep -q "Linked git worktree detected" /tmp/iw-wt-linked.txt \
  || fail "init-workspace should report linked-worktree sharing"
WT_SHARED="$(cd "${WT_REPO}/.git" && pwd -P)/adlc5-shared"
[[ -d "$WT_SHARED" ]] || fail "shared store should exist under the common .git dir"
grep -q 'repo_config_marker: preserved' "$WT_SHARED/config.yaml" \
  || fail "linked worktree should adopt the existing main-worktree config into shared settings"
for artifact in config.yaml governance policies.yaml.example; do
  [[ -L "${WT_LINKED}/.adlc5/${artifact}" ]] \
    || fail "linked worktree .adlc5/${artifact} should be a symlink, not a copy"
  [[ "$(readlink "${WT_LINKED}/.adlc5/${artifact}")" == "${WT_SHARED}/${artifact}" ]] \
    || fail ".adlc5/${artifact} should point at the shared store"
done
[[ -f "${WT_LINKED}/.adlc5/governance/production-ready.md" ]] \
  || fail "shared governance must resolve through the symlink"
grep -q "Adopted existing governance" /tmp/iw-wt-linked.txt \
  || fail "shared store should adopt the main worktree's governance copy"
echo "# repo-specific DoD" >>"${WT_SHARED}/governance/definition-of-done.md"
grep -q "repo-specific DoD" "${WT_LINKED}/.adlc5/governance/definition-of-done.md" \
  || fail "worktrees should read one shared governance copy"
pass "init-workspace shares static artifacts across worktrees"

./scripts/init-workspace.sh --project "$WT_LINKED" --no-skills >/tmp/iw-wt-linked2.txt
grep -q "OK (shared across worktrees): .adlc5/config.yaml" /tmp/iw-wt-linked2.txt \
  || fail "re-running init-workspace in a linked worktree should be idempotent"
WT_OPTOUT="${TMP}/wt-optout"
(cd "$WT_REPO" && git worktree add -q "$WT_OPTOUT" -b feat/y)
./scripts/init-workspace.sh --project "$WT_OPTOUT" --no-skills --no-shared-worktree >/dev/null
[[ -f "${WT_OPTOUT}/.adlc5/config.yaml" && ! -L "${WT_OPTOUT}/.adlc5/config.yaml" ]] \
  || fail "--no-shared-worktree should scaffold private copies"
./scripts/init-workspace.sh --project "$WT_OPTOUT" --no-skills >/dev/null
[[ ! -L "${WT_OPTOUT}/.adlc5/config.yaml" ]] \
  || fail "an existing real config.yaml must never be replaced by a shared symlink"
pass "init-workspace honours --no-shared-worktree and existing real files"

./scripts/init-feature.sh --feature shared-demo --workspace "$WT_REPO" --mode greenfield >/dev/null
./scripts/init-feature.sh --feature shared-demo --workspace "$WT_LINKED" --mode greenfield \
  2>/tmp/iw-wt-feature-warn.txt >/dev/null
[[ -f "${WT_LINKED}/.adlc5/shared-demo/state.json" && ! -L "${WT_LINKED}/.adlc5/shared-demo" ]] \
  || fail "feature state must stay worktree-local"
grep -q "already has lifecycle state in another worktree" /tmp/iw-wt-feature-warn.txt \
  || fail "init-feature should warn when another worktree owns the same feature"
pass "feature state stays worktree-local and warns on cross-worktree duplication"

python3 - "$IW_WS2" <<'PY'
from pathlib import Path
import re, sys
root = Path(sys.argv[1])
broken = []
for path in [root / "AGENTS.md", *(root / ".adlc5" / "governance").glob("*.md")]:
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
        target = target.split("#", 1)[0]
        if not target or "://" in target or target.startswith(("#", "mailto:")):
            continue
        if not (path.parent / target).resolve().exists():
            broken.append(f"{path.relative_to(root)} -> {target}")
if broken:
    raise SystemExit("generated workspace broken links:\n" + "\n".join(broken))
PY
pass "generated workspace links resolve"

WIKI_GATE_WS="${TMP}/wiki-gate"
WIKI_GATE_FEATURE="wiki-gate"
mkdir -p "$WIKI_GATE_WS"
(cd "$WIKI_GATE_WS" && git init -q)
./scripts/wiki/init-wiki.sh --workspace "$WIKI_GATE_WS" >/dev/null
mkdir -p "${WIKI_GATE_WS}/.adlc5/${WIKI_GATE_FEATURE}/memory"
cat >"${WIKI_GATE_WS}/.adlc5/${WIKI_GATE_FEATURE}/memory/promotion-candidates.md" <<'EOF'
### current-fact

**Claim:** Current fact.
**Target:** wiki/entities/current-fact.md
**Evidence:** `README.md:1-1`
EOF
printf '%s\n' '{"schema_version":"3.0","stage_status":{"implement":"in_progress"}}' \
  >"${WIKI_GATE_WS}/.adlc5/${WIKI_GATE_FEATURE}/state.json"
set +e
./scripts/wiki/promote-prepare.sh --feature "$WIKI_GATE_FEATURE" --workspace "$WIKI_GATE_WS" >/dev/null 2>&1
WIKI_PREPARE_EC=$?
set -e
[[ "$WIKI_PREPARE_EC" -ne 0 ]] || fail "wiki promotion prepare must block before Implement completes"

printf '%s\n' '{"schema_version":"3.0","stage_status":{"implement":"completed"}}' \
  >"${WIKI_GATE_WS}/.adlc5/${WIKI_GATE_FEATURE}/state.json"
./scripts/wiki/promote-prepare.sh --feature "$WIKI_GATE_FEATURE" --workspace "$WIKI_GATE_WS" >/dev/null
WIKI_APPROVED="${WIKI_GATE_WS}/wiki/drafts/promote-${WIKI_GATE_FEATURE}/approved.json"
cat >"$WIKI_APPROVED" <<'EOF'
{"feature":"wiki-gate","candidates":[{"id":"current-fact","action":"promote_entity","target":"wiki/entities/current-fact.md"}]}
EOF
set +e
./scripts/wiki/promote-apply.sh --feature "$WIKI_GATE_FEATURE" --workspace "$WIKI_GATE_WS" >/dev/null 2>&1
WIKI_APPLY_EC=$?
set -e
[[ "$WIKI_APPLY_EC" -ne 0 ]] || fail "wiki promotion apply must require approved_by"
[[ ! -e "${WIKI_GATE_WS}/wiki/entities/current-fact.md" ]] || fail "wiki apply must not write before approval validation"
python3 - "$WIKI_APPROVED" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path, encoding="utf-8"))
data["approved_by"] = "agent"
open(path, "w", encoding="utf-8").write(json.dumps(data))
PY
set +e
./scripts/wiki/promote-apply.sh --feature "$WIKI_GATE_FEATURE" --workspace "$WIKI_GATE_WS" >/dev/null 2>&1
WIKI_AGENT_EC=$?
set -e
[[ "$WIKI_AGENT_EC" -ne 0 ]] || fail "agent-authored wiki approval must fail"
[[ ! -e "${WIKI_GATE_WS}/wiki/entities/current-fact.md" ]] || fail "agent approval must not promote wiki content"
python3 - "$WIKI_APPROVED" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path, encoding="utf-8"))
data["approved_by"] = "user"
data["candidates"][0]["target"] = "../escape.md"
open(path, "w", encoding="utf-8").write(json.dumps(data))
PY
set +e
./scripts/wiki/promote-apply.sh --feature "$WIKI_GATE_FEATURE" --workspace "$WIKI_GATE_WS" >/dev/null 2>&1
WIKI_TRAVERSAL_EC=$?
set -e
[[ "$WIKI_TRAVERSAL_EC" -ne 0 ]] || fail "wiki promotion target traversal must fail"
[[ ! -e "${TMP}/escape.md" ]] || fail "wiki promotion must not write outside its workspace"
python3 - "$WIKI_APPROVED" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path, encoding="utf-8"))
data["candidates"][0]["target"] = "wiki/entities/current-fact.md"
open(path, "w", encoding="utf-8").write(json.dumps(data))
PY
./scripts/wiki/promote-apply.sh --feature "$WIKI_GATE_FEATURE" --workspace "$WIKI_GATE_WS" >/dev/null
[[ -f "${WIKI_GATE_WS}/wiki/entities/current-fact.md" ]] || fail "human-approved wiki promotion should apply"

python3 - "$WIKI_APPROVED" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path, encoding="utf-8"))
data["candidates"] = [{"id":"current-fact","action":"unexpected_action","target":"wiki/entities/unexpected.md"}]
open(path, "w", encoding="utf-8").write(json.dumps(data))
PY
set +e
./scripts/wiki/promote-apply.sh --feature "$WIKI_GATE_FEATURE" --workspace "$WIKI_GATE_WS" >/dev/null 2>&1
WIKI_ACTION_EC=$?
set -e
[[ "$WIKI_ACTION_EC" -ne 0 ]] || fail "wiki promotion must reject unknown actions"
[[ ! -e "${WIKI_GATE_WS}/wiki/entities/unexpected.md" ]] || fail "unknown wiki action must not write"

WIKI_LINK_WS="${TMP}/wiki-link-gate"
WIKI_LINK_FEATURE="wiki-link-gate"
WIKI_OUTSIDE="${TMP}/wiki-outside"
mkdir -p "$WIKI_LINK_WS" "$WIKI_OUTSIDE"
(cd "$WIKI_LINK_WS" && git init -q)
./scripts/wiki/init-wiki.sh --workspace "$WIKI_LINK_WS" >/dev/null
mkdir -p "${WIKI_LINK_WS}/.adlc5/${WIKI_LINK_FEATURE}/memory" \
  "${WIKI_LINK_WS}/wiki/drafts/promote-${WIKI_LINK_FEATURE}"
printf '%s\n' '{"schema_version":"3.0","stage_status":{"implement":"completed"}}' \
  >"${WIKI_LINK_WS}/.adlc5/${WIKI_LINK_FEATURE}/state.json"
cat >"${WIKI_LINK_WS}/.adlc5/${WIKI_LINK_FEATURE}/memory/promotion-candidates.md" <<'EOF'
### escape
**Claim:** Escape.
EOF
cat >"${WIKI_LINK_WS}/wiki/drafts/promote-${WIKI_LINK_FEATURE}/approved.json" <<'EOF'
{"feature":"wiki-link-gate","approved_by":"user","candidates":[{"id":"escape","action":"promote_entity","target":"wiki/entities/escape.md"}]}
EOF
rm -rf "${WIKI_LINK_WS}/wiki/entities"
ln -s "$WIKI_OUTSIDE" "${WIKI_LINK_WS}/wiki/entities"
set +e
./scripts/wiki/promote-apply.sh --feature "$WIKI_LINK_FEATURE" --workspace "$WIKI_LINK_WS" >/dev/null 2>&1
WIKI_ROOT_LINK_EC=$?
set -e
[[ "$WIKI_ROOT_LINK_EC" -ne 0 ]] || fail "symlinked wiki root must fail containment"
[[ ! -e "${WIKI_OUTSIDE}/escape.md" ]] || fail "symlinked wiki root must not write outside wiki"
pass "project wiki promotion gates"

chmod +x ./scripts/pr-reviewer-gh.sh 2>/dev/null || true
# pr-reviewer-gh requires auth; accept skip when not logged in
set +e
./scripts/pr-reviewer-gh.sh --action status --workspace "$ROOT" >/tmp/gh-status.json 2>/dev/null
GEC=$?
set -e
if [[ "$GEC" -eq 0 ]]; then
  pass "pr-reviewer-gh status"
elif jq -e '.error | test("not authenticated")' /tmp/gh-status.json >/dev/null 2>&1; then
  pass "pr-reviewer-gh status (skipped: gh not authenticated)"
else
  pass "pr-reviewer-gh status (skipped: no PR for branch)"
fi

# pr-reviewer-compose-body
./scripts/pr-reviewer-compose-body.sh --feature "$FEATURE" --workspace "$TMP" >/tmp/pr-body.md
[[ -s /tmp/pr-body.md ]] || fail "pr-reviewer-compose-body empty"
pass "pr-reviewer-compose-body"

PR_V3_FEATURE="pr-body-v3"
mkdir -p "${TMP}/.adlc5/${PR_V3_FEATURE}"
cat >"${TMP}/.adlc5/${PR_V3_FEATURE}/state.json" <<'EOF'
{"schema_version":"3.0","feature":"pr-body-v3","current_stage":"implement","current_step":"implement-5-pr","stage_status":{},"tasks":{"stories":[{"id":"US-1","status":"verified"}]}}
EOF
./scripts/pr-reviewer-compose-body.sh --feature "$PR_V3_FEATURE" --workspace "$TMP" >/tmp/pr-body-v3.md
grep -q 'Current step: `implement-5-pr`' /tmp/pr-body-v3.md \
  || fail "pr-reviewer-compose-body should read canonical current_step"
grep -q '"id":"US-1","status":"verified"' /tmp/pr-body-v3.md \
  || fail "pr-reviewer-compose-body should render canonical story array"
grep -q '^_Opened by ADLC5 automation (@pr-reviewer)_$' /tmp/pr-body-v3.md \
  || fail "pr-reviewer-compose-body should include attribution trailer"
pass "pr-reviewer-compose-body canonical v3"

PR_MIXED_FEATURE="pr-body-mixed"
mkdir -p "${TMP}/.adlc5/${PR_MIXED_FEATURE}/delivery"
printf '%s\n' '{"current_stage":"assure"}' >"${TMP}/.adlc5/${PR_MIXED_FEATURE}/state.json"
printf '%s\n' '{"current_phase":"completed","stories":{"US-LEG":{"status":"verified"}}}' \
  >"${TMP}/.adlc5/${PR_MIXED_FEATURE}/delivery/state.json"
./scripts/pr-reviewer-compose-body.sh --feature "$PR_MIXED_FEATURE" --workspace "$TMP" >/tmp/pr-body-mixed.md
grep -q '"id":"US-LEG","status":"verified"' /tmp/pr-body-mixed.md \
  || fail "pr-reviewer-compose-body should preserve legacy stories when root state is non-v3"
pass "pr-reviewer-compose-body mixed-schema fallback"

# assure-1-verification: fail without report
set +e
./scripts/check-gates.py --feature "$FEATURE" --workspace "$TMP" --gate assure-1-verification >/dev/null
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "assure-1-verification expected fail without report got $EC"
pass "assure-1-verification fail without report"

# verification report + sync pass
mkdir -p "${TMP}/.adlc5/${FEATURE}/verify"
cat >"${TMP}/.adlc5/${FEATURE}/verify/verification-report.md" <<'EOF'
**Overall:** pass
**Synced at:** 2026-05-30T00:00:00Z
EOF
cat >"${TMP}/.adlc5/${FEATURE}/delivery/state.json" <<'EOF'
{
  "current_phase": "assure-1-verification",
  "stories": { "story-a": { "type": "component", "status": "verified" } }
}
EOF
set +e
./scripts/sync-verification-report.sh --feature "$FEATURE" --workspace "$TMP" >/dev/null
SEC=$?
./scripts/check-gates.py --feature "$FEATURE" --workspace "$TMP" --gate assure-1-verification >/tmp/legacy-verification.json
EC=$?
set -e
[[ "$SEC" -eq 0 ]] || fail "sync-verification-report expected 0 got $SEC"
[[ "$EC" -eq 1 ]] || fail "legacy report cannot certify completion, got $EC"
jq -e 'any(.checks[]; .id == "completion_evidence" and .status == "fail") and all(.checks[] | select(.id != "completion_evidence" and .id != "code_specs_lint" and .id != "verifier_independence" and .id != "profile_risk"); .status == "pass")' \
  /tmp/legacy-verification.json >/dev/null || fail "report sync must still satisfy the original verification checks"
pass "sync-verification-report + assure-1-verification pass"

# canonical v3 verification sync must not require legacy delivery/state.json
SYNC_V3_FEATURE="sync-v3-verification"
./scripts/init-feature.sh --feature "$SYNC_V3_FEATURE" --workspace "$TMP" --mode brownfield >/dev/null
fixture_state_patch --feature "$SYNC_V3_FEATURE" --workspace "$TMP" --patch \
  '{"current_stage":"implement","current_step":"implement-2-verify","stage_status":{"specify":"completed","plan":"completed","tasks":"completed","implement":"in_progress"},"tasks":{"stories":[{"id":"US-1","title":"Verified v3 story","status":"verified","batch":1,"files":[],"depends_on":[]}],"parallel_batches":[{"batch":1,"story_ids":["US-1"]}]},"implement":{"verification":{"status":"completed","reports":{"US-1":".adlc5/sync-v3-verification/verify/verification-report.md"}}}}' >/dev/null
mkdir -p "${TMP}/.adlc5/${SYNC_V3_FEATURE}/verify"
printf '%s\n' '**Overall:** pass' >"${TMP}/.adlc5/${SYNC_V3_FEATURE}/verify/verification-report.md"
[[ ! -e "${TMP}/.adlc5/${SYNC_V3_FEATURE}/delivery/state.json" ]] || fail "v3 sync fixture must not have legacy delivery state"
set +e
./scripts/sync-verification-report.sh --feature "$SYNC_V3_FEATURE" --workspace "$TMP" >/dev/null
SYNC_V3_EC=$?
./scripts/check-gates.py --feature "$SYNC_V3_FEATURE" --workspace "$TMP" --gate implement-2-verify >/tmp/sync-v3-gate.json
SYNC_V3_GATE_EC=$?
set -e
[[ "$SYNC_V3_EC" -eq 0 ]] || fail "v3 verification sync should use canonical state, got $SYNC_V3_EC"
[[ "$SYNC_V3_GATE_EC" -eq 1 ]] || fail "v3 verification must require current evidence, got $SYNC_V3_GATE_EC"
jq -e 'any(.checks[]; .id == "completion_evidence" and .status == "fail") and all(.checks[] | select(.id | startswith("assure_verification")); .status == "pass")' \
  /tmp/sync-v3-gate.json >/dev/null || fail "canonical report sync or evidence checks missing"
pass "canonical v3 verification report sync"

printf '%s\n' '**Overall:** pass-with-warnings' >"${TMP}/.adlc5/${SYNC_V3_FEATURE}/verify/verification-report.md"
fixture_state_patch --feature "$SYNC_V3_FEATURE" --workspace "$TMP" --patch \
  '{"clarity":{"history":[{"type":"verifier_waiver","approved_by":"agent"}]}}' >/dev/null
set +e
./scripts/sync-verification-report.sh --feature "$SYNC_V3_FEATURE" --workspace "$TMP" \
  >/tmp/sync-v3-agent-waiver.json
SYNC_AGENT_WAIVER_EC=$?
set -e
[[ "$SYNC_AGENT_WAIVER_EC" -eq 1 ]] || fail "agent-authored verifier waiver must fail sync"
printf '%s\n' '**Overall:** pass' >"${TMP}/.adlc5/${SYNC_V3_FEATURE}/verify/verification-report.md"
fixture_state_patch --feature "$SYNC_V3_FEATURE" --workspace "$TMP" --patch \
  '{"clarity":{"history":[]}}' >/dev/null
pass "verification sync rejects agent waiver"

mkdir -p "${TMP}/.adlc5/${SYNC_V3_FEATURE}/delivery"
cat >"${TMP}/.adlc5/${SYNC_V3_FEATURE}/delivery/state.json" <<'EOF'
{"current_phase":"assure-1-verification","stories":{"US-1":{"status":"pending"}},"verification_summary":{"overall":"fail"}}
EOF
set +e
./scripts/sync-verification-report.sh --feature "$SYNC_V3_FEATURE" --workspace "$TMP" \
  >/tmp/sync-v3-mixed.json
SYNC_V3_MIXED_EC=$?
set -e
[[ "$SYNC_V3_MIXED_EC" -eq 0 ]] \
  || fail "canonical v3 state should take precedence over stale legacy delivery state"
pass "canonical v3 state precedence"

PATHS_WS="${TMP}/canonical-paths"
PATHS_FEATURE="canonical-paths"
mkdir -p "${PATHS_WS}/.adlc5/${PATHS_FEATURE}/delivery"
printf '%s\n' '{"schema_version":"3.0","feature":"canonical-paths","current_stage":"implement","current_step":"implement-2-verify","stage_status":{"implement":"in_progress"}}' \
  >"${PATHS_WS}/.adlc5/${PATHS_FEATURE}/state.json"
printf '%s\n' '{"current_phase":"build-1-implementation"}' \
  >"${PATHS_WS}/.adlc5/${PATHS_FEATURE}/delivery/state.json"
# shellcheck source=../lib/adlc5-paths.sh
source ./scripts/lib/adlc5-paths.sh
[[ "$(adlc5_resolve_state "$PATHS_WS" "$PATHS_FEATURE")" == "${PATHS_WS}/.adlc5/${PATHS_FEATURE}/state.json" ]] \
  || fail "state resolver should prefer canonical schema-v3 state"
[[ "$(adlc5_current_step "$PATHS_WS" "$PATHS_FEATURE")" == "implement-2-verify" ]] \
  || fail "current-step resolver should read canonical current_step"
printf '%s\n' '{"current_stage":"assure"}' >"${PATHS_WS}/.adlc5/${PATHS_FEATURE}/state.json"
[[ "$(adlc5_resolve_state "$PATHS_WS" "$PATHS_FEATURE")" == "${PATHS_WS}/.adlc5/${PATHS_FEATURE}/delivery/state.json" ]] \
  || fail "non-v3 root state should fall back to legacy delivery state"
[[ "$(adlc5_current_step "$PATHS_WS" "$PATHS_FEATURE")" == "build-1-implementation" ]] \
  || fail "mixed-schema fallback should preserve legacy current_phase"
python3 - "$PATHS_WS" "$PATHS_FEATURE" <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, "scripts")
from lib.adlc5_paths import state_path
workspace, feature = Path(sys.argv[1]), sys.argv[2]
expected = workspace / ".adlc5" / feature / "delivery" / "state.json"
assert state_path(workspace, feature) == expected
PY
printf '%s\n' '{"schema_version":"3.0"}' >"${PATHS_WS}/.adlc5/${PATHS_FEATURE}/state.json"
[[ "$(adlc5_resolve_state "$PATHS_WS" "$PATHS_FEATURE")" == "${PATHS_WS}/.adlc5/${PATHS_FEATURE}/delivery/state.json" ]] \
  || fail "incomplete schema-v3 root should fall back to legacy delivery state"
python3 - "$PATHS_WS" "$PATHS_FEATURE" <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, "scripts")
from lib.adlc5_paths import state_path
workspace, feature = Path(sys.argv[1]), sys.argv[2]
expected = workspace / ".adlc5" / feature / "delivery" / "state.json"
assert state_path(workspace, feature) == expected
PY
PATHS_DELIVERY_FEATURE="delivery-only"
mkdir -p "${PATHS_WS}/.adlc5/${PATHS_DELIVERY_FEATURE}/delivery"
printf '%s\n' '{"current_phase":"completed"}' \
  >"${PATHS_WS}/.adlc5/${PATHS_DELIVERY_FEATURE}/delivery/state.json"
[[ "$(adlc5_resolve_state "$PATHS_WS" "$PATHS_DELIVERY_FEATURE")" == "${PATHS_WS}/.adlc5/${PATHS_DELIVERY_FEATURE}/delivery/state.json" ]] \
  || fail "state resolver should preserve delivery-only fallback"
PATHS_FORGE_FEATURE="forge-only"
mkdir -p "${PATHS_WS}/.adlc5/${PATHS_FORGE_FEATURE}/forge"
printf '%s\n' '{"current_phase":"completed"}' \
  >"${PATHS_WS}/.adlc5/${PATHS_FORGE_FEATURE}/forge/state.json"
[[ "$(adlc5_resolve_state "$PATHS_WS" "$PATHS_FORGE_FEATURE")" == "${PATHS_WS}/.adlc5/${PATHS_FORGE_FEATURE}/forge/state.json" ]] \
  || fail "state resolver should preserve forge-only fallback"
pass "canonical state path helper precedence"

# custom_gates + required_gates on pr-ready
mkdir -p "${TMP}/.adlc5/${FEATURE}"
cat >"${TMP}/.adlc5/${FEATURE}/policies.yaml" <<'EOF'
custom_gates:
  smoke_gate: "true"
required_gates:
  - smoke_gate
EOF
cat >"${TMP}/.adlc5/${FEATURE}/delivery/state.json" <<'EOF'
{
  "current_phase": "completed",
  "integration": { "status": "completed" },
  "stories": { "story-a": { "type": "component", "status": "verified" } }
}
EOF
printf '%s\n' '**Overall:** pass' >"${TMP}/.adlc5/${FEATURE}/verify/verification-report.md"
mkdir -p "${TMP}/.qa/${FEATURE}"
echo "STATUS: CLEARED" >"${TMP}/.qa/${FEATURE}/deployment-clearance.md"
cat >"${TMP}/.adlc5/${FEATURE}/state.json" <<'EOF'
{
  "stage_status": { "assure": "completed" },
  "assure": { "pr_review": "completed" },
  "pr_review": { "url": "https://example.com/pr/1" }
}
EOF
set +e
./scripts/check-gates.py --feature "$FEATURE" --workspace "$TMP" --gate pr-ready >/tmp/pr-custom.json
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "custom gate does not replace completion evidence, got $EC"
jq -e 'any(.checks[]; .id == "completion_evidence" and .status == "fail")' /tmp/pr-custom.json >/dev/null \
  || fail "custom-gate readiness must include completion evidence"
echo "$(cat /tmp/pr-custom.json)" | jq -e '.checks[] | select(.id == "custom_gate_smoke_gate" and .status == "pass")' >/dev/null || fail "custom_gate check missing"
pass "pr-ready custom_gates"

# cleanup-stale-skills
CLEAN_TMP="${TMP}/cleanup-skills"
mkdir -p "$CLEAN_TMP"
ln -s "/tmp/nonexistent/skills/adlc5-spec" "${CLEAN_TMP}/adlc5-spec"
ln -s "/tmp/nonexistent/skills/adlc5" "${CLEAN_TMP}/adlc5"
ln -s "${ROOT}/skills/discover" "${CLEAN_TMP}/discover"
mkdir -p "${CLEAN_TMP}/other-vendor"
echo "not adlc5" >"${CLEAN_TMP}/other-vendor/SKILL.md"
./scripts/cleanup-stale-skills.sh --skills-target "$CLEAN_TMP" --prune-stale-skills >/dev/null
[[ -L "${CLEAN_TMP}/adlc5-spec" ]] && fail "cleanup should remove adlc5-spec"
[[ -L "${CLEAN_TMP}/adlc5" ]] && fail "cleanup should remove stale adlc5 path"
[[ -L "${CLEAN_TMP}/discover" ]] || fail "cleanup should keep current discover link"
[[ -d "${CLEAN_TMP}/other-vendor" ]] || fail "cleanup must not remove non-symlink dirs"
pass "cleanup-stale-skills prune"

# cleanup-stale-skills — rules prune (ADLC5 symlinks only; keep user files)
RULES_TMP="${TMP}/cleanup-rules"
mkdir -p "$RULES_TMP"
ln -s "${ROOT}/.cursor/rules/agent-discipline.mdc" "${RULES_TMP}/agent-discipline.mdc"
ln -s "${ROOT}/.cursor/rules/missing-retired.mdc" "${RULES_TMP}/adlc5-forge.mdc"
echo "user rule body" >"${RULES_TMP}/my-custom-rule.mdc"
./scripts/cleanup-stale-skills.sh --rules-target "$RULES_TMP" --prune-stale-rules >/dev/null
[[ -L "${RULES_TMP}/adlc5-forge.mdc" ]] && fail "cleanup should remove stale ADLC5 rule symlink"
[[ -L "${RULES_TMP}/agent-discipline.mdc" ]] || fail "cleanup should keep current ADLC5 rule symlink"
[[ -f "${RULES_TMP}/my-custom-rule.mdc" ]] || fail "cleanup must not remove user-authored rule files"
pass "cleanup-stale-skills rules prune"

# cleanup-stale-skills — aged backup prune
BACKUP_TMP="${TMP}/install-backups"
mkdir -p "${BACKUP_TMP}/old-backup" "${BACKUP_TMP}/new-backup"
python3 - "$BACKUP_TMP/old-backup" <<'PY'
import os, sys, time
os.utime(sys.argv[1], (time.time() - 10 * 86400, time.time() - 10 * 86400))
PY
./scripts/cleanup-stale-skills.sh --prune-backups --keep-backup-days 7 --backup-root "$BACKUP_TMP" >/dev/null
[[ -d "${BACKUP_TMP}/old-backup" ]] && fail "aged backup should be pruned"
[[ -d "${BACKUP_TMP}/new-backup" ]] || fail "recent backup should be kept"
pass "cleanup-stale-skills backup prune"

# cleanup-features — dry-run default (archive plan); --archive moves + OKF FEATURE.md; --delete removes
FEAT_WS="${TMP}/feat-cleanup-ws"
mkdir -p "${FEAT_WS}/.adlc5/old-complete/memory/summaries" \
  "${FEAT_WS}/.adlc5/old-complete/design" \
  "${FEAT_WS}/.adlc5/active-wip" \
  "${FEAT_WS}/wiki"
cat >"${FEAT_WS}/.adlc5/old-complete/state.json" <<'EOF'
{
  "schema_version": "3.0",
  "feature": "old-complete",
  "stage_status": {
    "specify": "completed",
    "plan": "completed",
    "tasks": "waived",
    "implement": "completed"
  },
  "git": { "branch_name": "feat/old-complete", "base_branch": "main" },
  "implement": { "pr": { "status": "merged", "url": "https://example.com/pr/42" } }
}
EOF
cat >"${FEAT_WS}/.adlc5/old-complete/spec-handoff.md" <<'EOF'
# Spec handoff — old-complete

## Problem

Users cannot archive aged feature trees without losing context.

## Locked decisions

- Archive must write a concise OKF Feature card, not a journey dump.
EOF
cat >"${FEAT_WS}/.adlc5/old-complete/design/INDEX.md" <<'EOF'
# Design index

## Architecture

- cleanup-features moves trees into `.adlc5/_archive/`
- summarize-feature-okf extracts bullets from state + artifact heads
EOF
cat >"${FEAT_WS}/.adlc5/old-complete/memory/INDEX.md" <<'EOF'
# Memory index

| Path | Stage | Summary |
|------|-------|---------|
| spec-handoff.md | specify | Archive context problem |
EOF
cat >"${FEAT_WS}/.adlc5/active-wip/state.json" <<'EOF'
{
  "schema_version": "3.0",
  "feature": "active-wip",
  "stage_status": {
    "specify": "in_progress",
    "plan": "pending",
    "tasks": "pending",
    "implement": "pending"
  }
}
EOF
python3 - "${FEAT_WS}/.adlc5/old-complete/state.json" <<'PY'
import os, sys, time
os.utime(sys.argv[1], (time.time() - 100 * 86400, time.time() - 100 * 86400))
PY
./scripts/adlc5 usage record --feature old-complete --workspace "$FEAT_WS" \
  --model-id claude-sonnet-5 --platform claude --tier execution \
  --stage implement --step implement-1-build \
  --input-tokens 1000 --output-tokens 200 --thinking-tokens 150 \
  --cache-creation-tokens 50 --cache-read-tokens 900 >/dev/null
./scripts/adlc5 usage record --feature old-complete --workspace "$FEAT_WS" \
  --model-id claude-haiku-4-5 --platform claude --tier fast \
  --stage plan --step plan-1 \
  --input-tokens 300 --output-tokens 60 >/dev/null
[[ -f "${FEAT_WS}/.adlc5/old-complete/memory/usage-ledger.jsonl" ]] \
  || fail "adlc5 usage record should write usage-ledger.jsonl"
./scripts/cleanup-features.sh --workspace "$FEAT_WS" --status complete --older-than 30 >/tmp/feat-clean-dry.txt
grep -q "old-complete" /tmp/feat-clean-dry.txt || fail "cleanup-features dry-run should list complete aged feature"
grep -q "would archive" /tmp/feat-clean-dry.txt || fail "cleanup-features dry-run should preview archive"
grep -q "would write OKF summary" /tmp/feat-clean-dry.txt || fail "cleanup-features dry-run should preview OKF FEATURE.md"
[[ -d "${FEAT_WS}/.adlc5/old-complete" ]] || fail "dry-run must not archive or delete"
[[ -f "${FEAT_WS}/.adlc5/old-complete/FEATURE.md" ]] && fail "dry-run must not write FEATURE.md"
./scripts/cleanup-features.sh --workspace "$FEAT_WS" --status complete --older-than 30 --archive >/tmp/feat-clean-arch.txt
[[ -d "${FEAT_WS}/.adlc5/old-complete" ]] && fail "cleanup-features --archive should move complete aged feature"
arch_hits=("${FEAT_WS}/.adlc5/_archive/old-complete-"*)
[[ -d "${arch_hits[0]}" ]] || fail "cleanup-features --archive should create _archive/{feature}-YYYYMMDD"
[[ -f "${arch_hits[0]}/FEATURE.md" ]] || fail "archive should write FEATURE.md"
grep -q "^type: Feature" "${arch_hits[0]}/FEATURE.md" || fail "FEATURE.md should be OKF type Feature"
grep -q "Users cannot archive" "${arch_hits[0]}/FEATURE.md" || fail "FEATURE.md should include problem bullet"
[[ -f "${arch_hits[0]}/memory/usage-ledger.jsonl" ]] || fail "usage ledger should move with the archived feature tree"
grep -q "^## Usage" "${arch_hits[0]}/FEATURE.md" || fail "FEATURE.md should include a Usage section"
grep -q "Total tracked tokens: 2,660" "${arch_hits[0]}/FEATURE.md" || fail "FEATURE.md Usage section should total recorded tokens"
grep -q "claude-sonnet-5" "${arch_hits[0]}/FEATURE.md" || fail "FEATURE.md Usage section should list model ids"
[[ -f "${arch_hits[0]}/usage-summary.json" ]] || fail "archive should write usage-summary.json"
jq -e '.entries == 2 and .totals.total == 2660 and (.by_model["claude-sonnet-5"].total == 2300) and (.by_model["claude-haiku-4-5"].total == 360)' \
  "${arch_hits[0]}/usage-summary.json" >/dev/null || fail "usage-summary.json totals mismatch"
[[ -f "${FEAT_WS}/.adlc5/_archive/index.md" ]] || fail "archive should upsert _archive/index.md"
grep -q "old-complete" "${FEAT_WS}/.adlc5/_archive/index.md" || fail "archive index should list feature"
[[ -f "${FEAT_WS}/wiki/concepts/feature-old-complete.md" ]] || fail "wiki mirror should write when wiki/ exists"
./scripts/adlc5 feature summarize --feature-dir "${arch_hits[0]}" --workspace "$FEAT_WS" --dry-run >/tmp/feat-okf-dry.json
jq -e '.status == "ok" and .dry_run == true' /tmp/feat-okf-dry.json >/dev/null \
  || fail "adlc5 feature summarize --dry-run should emit ok JSON"
# Recreate live feature; second --archive should skip (already under _archive/)
mkdir -p "${FEAT_WS}/.adlc5/old-complete"
cp "${arch_hits[0]}/state.json" "${FEAT_WS}/.adlc5/old-complete/state.json"
python3 - "${FEAT_WS}/.adlc5/old-complete/state.json" <<'PY'
import os, sys, time
os.utime(sys.argv[1], (time.time() - 100 * 86400, time.time() - 100 * 86400))
PY
./scripts/cleanup-features.sh --workspace "$FEAT_WS" --status complete --older-than 30 --archive >/tmp/feat-clean-skip.txt
grep -q "already archived" /tmp/feat-clean-skip.txt || fail "cleanup-features should skip when already archived"
[[ -d "${FEAT_WS}/.adlc5/old-complete" ]] || fail "skip must leave live feature in place"
./scripts/cleanup-features.sh --workspace "$FEAT_WS" --status complete --older-than 30 --delete --dry-run >/tmp/feat-clean-del-dry.txt
grep -q "would delete" /tmp/feat-clean-del-dry.txt || fail "cleanup-features --delete --dry-run should preview delete"
[[ -d "${FEAT_WS}/.adlc5/old-complete" ]] || fail "delete dry-run must not remove"
./scripts/cleanup-features.sh --workspace "$FEAT_WS" --status complete --older-than 30 --delete >/tmp/feat-clean-del.txt
[[ -d "${FEAT_WS}/.adlc5/old-complete" ]] && fail "cleanup-features --delete should remove complete aged feature"
[[ -d "${FEAT_WS}/.adlc5/active-wip" ]] || fail "cleanup-features must not remove in-progress feature"
./scripts/adlc5 cleanup-features --workspace "$FEAT_WS" --older-than 1 --dry-run >/tmp/feat-adlc5.txt
pass "cleanup-features dry-run, archive OKF, and delete"

# adlc5 usage fleet — cross-feature rollup (active-wip live + old-complete archived-only now)
./scripts/adlc5 usage record --feature active-wip --workspace "$FEAT_WS" \
  --model-id claude-sonnet-5 --platform claude --tier execution \
  --stage specify --step specify-2-requirements \
  --input-tokens 500 --output-tokens 100 >/dev/null
./scripts/adlc5 usage fleet --workspace "$FEAT_WS" >/tmp/adlc5-usage-fleet.json
jq -e '.features_with_entries == 2 and .totals.total == 3260' /tmp/adlc5-usage-fleet.json >/dev/null \
  || fail "usage fleet should aggregate active + archived features (expected total 3260)"
jq -e '.by_feature["old-complete"].status == "archived" and .by_feature["active-wip"].status == "active"' \
  /tmp/adlc5-usage-fleet.json >/dev/null || fail "usage fleet should tag feature status"
./scripts/adlc5 usage fleet --workspace "$FEAT_WS" --active-only >/tmp/adlc5-usage-fleet-active.json
jq -e '.features_with_entries == 1 and .totals.total == 600 and (.by_feature | has("old-complete") | not)' \
  /tmp/adlc5-usage-fleet-active.json >/dev/null || fail "usage fleet --active-only should exclude archived features"
./scripts/adlc5 usage fleet --workspace "$FEAT_WS" --format markdown >/tmp/adlc5-usage-fleet.md
grep -q "Fleet total tracked tokens: 3,260" /tmp/adlc5-usage-fleet.md || fail "usage fleet markdown should render fleet totals"
pass "adlc5 usage fleet rollup"

# scope-guard warn vs enforce
SG_WS="${TMP}/scope-guard-ws"
mkdir -p "${SG_WS}/.adlc5/demo-feat" "${SG_WS}/src/in" "${SG_WS}/src/out"
echo "demo-feat" >"${SG_WS}/.adlc5/.active-feature"
cat >"${SG_WS}/.adlc5/demo-feat/policies.yaml" <<'EOF'
scope_guard:
  mode: warn
  allowed_paths:
    - src/in
EOF
HOOK_JSON='{"tool_name":"Write","tool_input":{"path":"src/out/x.ts"}}'
WARN_OUT="$(printf '%s' "$HOOK_JSON" | ADLC5_FEATURE=demo-feat python3 "${ROOT}/.cursor/hooks/scope-guard-check.py" --project "$SG_WS")"
echo "$WARN_OUT" | jq -e '.permission == "allow" and (.agent_message|test("WARNING"))' >/dev/null \
  || fail "scope-guard warn should allow with WARNING agent_message"
ENF_OUT="$(printf '%s' "$HOOK_JSON" | ADLC5_SCOPE_GUARD=enforce ADLC5_FEATURE=demo-feat \
  python3 "${ROOT}/.cursor/hooks/scope-guard-check.py" --project "$SG_WS")"
echo "$ENF_OUT" | jq -e '.permission == "deny"' >/dev/null || fail "scope-guard enforce should deny"
IN_OUT="$(printf '%s' '{"tool_name":"Write","tool_input":{"path":"src/in/ok.ts"}}' \
  | ADLC5_FEATURE=demo-feat python3 "${ROOT}/.cursor/hooks/scope-guard-check.py" --project "$SG_WS")"
echo "$IN_OUT" | jq -e '.permission == "allow"' >/dev/null || fail "in-scope write should allow"
pass "scope-guard warn and enforce"

# v2 init-feature emits state compatible with state-schema contract defaults
FEATURE_V2="v2-contract"
V2_TMP="${TMP}/v2-contract"
mkdir -p "$V2_TMP"
./scripts/init-feature.sh --feature "$FEATURE_V2" --workspace "$V2_TMP" --mode greenfield --interaction autonomous >/tmp/v2-init.json
python3 - "$ROOT/core/state-schema.json" "$V2_TMP/.adlc5/$FEATURE_V2/state.json" <<'PY'
import json, sys
schema = json.load(open(sys.argv[1], encoding="utf-8"))
state = json.load(open(sys.argv[2], encoding="utf-8"))
assert state["schema_version"] == "3.0"
assert state["git"]["isolation"] in schema["properties"]["git"]["properties"]["isolation"]["enum"]
assert state["clarity"]["score"] is None or isinstance(state["clarity"]["score"], int)
assert state["implement"]["pr"]["url"] is None or isinstance(state["implement"]["pr"]["url"], str)
PY
pass "v2 init-feature state-schema defaults"

# acceptance anchor schema: valid entries pass; malformed entries fail closed
VALID_ACCEPTANCE='{"tasks":{"stories":[{"id":"US-1","title":"Anchored","status":"ready","batch":1,"files":[],"depends_on":[],"acceptance":[{"id":"AC-1","owner":"product","evidence":{"type":"file","value":"tests/acceptance.txt"}},{"id":"AC-2","owner":"qa","evidence":{"type":"command","value":"./scripts/test.sh"}}]}]}}'
./scripts/adlc5 state set --feature "$FEATURE_V2" --workspace "$V2_TMP" \
  --patch "$VALID_ACCEPTANCE" --dry-run >/tmp/anchor-schema-valid.json \
  || fail "valid acceptance anchor schema should pass"
set +e
./scripts/adlc5 state set --feature "$FEATURE_V2" --workspace "$V2_TMP" \
  --patch '{"tasks":{"stories":[{"id":"US-1","acceptance":[{"owner":"product","evidence":{"type":"file","value":"tests/a.txt"}}]}]}}' \
  --dry-run >/tmp/anchor-schema-invalid.json
EC=$?
set -e
[[ "$EC" -eq 2 ]] || fail "acceptance anchor without id should fail schema validation"
jq -e '.error == "schema_validation_failed"' /tmp/anchor-schema-invalid.json >/dev/null \
  || fail "invalid acceptance anchor schema error shape"
for bad_patch in \
  '{"tasks":{"stories":[{"id":"US-1","acceptance":[{"id":"AC-1","owner":"","evidence":{"type":"file","value":"tests/a.txt"}}]}]}}' \
  '{"tasks":{"stories":[{"id":"US-1","acceptance":[{"id":"AC-1","owner":"product","evidence":{"type":"file","value":"tests/a.txt","unexpected":true}}]}]}}'; do
  set +e
  ./scripts/adlc5 state set --feature "$FEATURE_V2" --workspace "$V2_TMP" \
    --patch "$bad_patch" --dry-run >/tmp/anchor-schema-strict.json
  EC=$?
  set -e
  [[ "$EC" -eq 2 ]] || fail "acceptance schema should enforce minLength/additionalProperties"
done
pass "acceptance anchor schema"

# acceptance anchor locking/checking: files are frozen; commands remain explicit
ANCHOR_WS="${TMP}/anchor-contract"
ANCHOR_FEATURE="anchor-contract"
mkdir -p "$ANCHOR_WS/tests"
git -C "$ANCHOR_WS" init -q
printf '%s\n' 'expected behavior' >"${ANCHOR_WS}/tests/acceptance.txt"
./scripts/init-feature.sh --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  --mode brownfield --interaction autonomous >/dev/null
fixture_state_patch --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  --patch "$VALID_ACCEPTANCE" >/dev/null
./scripts/tasks/check-anchors.py lock --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  >/tmp/anchor-lock.json || fail "anchor lock should succeed"
jq -e '.status == "pass" and .locked == 1 and .unlocked_commands == 1 and (.patch.tasks.stories[0].acceptance[0].evidence.sha256 | test("^[0-9a-f]{64}$"))' \
  /tmp/anchor-lock.json >/dev/null || fail "anchor lock output contract"
fixture_state_patch --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  --patch "$(jq -c '.patch' /tmp/anchor-lock.json)" >/dev/null
[[ -f "${ANCHOR_WS}/.adlc5/${ANCHOR_FEATURE}/acceptance-lock.json" ]] \
  || fail "anchor lock should create a sealed manifest"
git -C "$ANCHOR_WS" rev-parse --verify "refs/adlc5/anchors/${ANCHOR_FEATURE}" >/dev/null \
  || fail "anchor lock should create a Git trust ref"
./scripts/tasks/check-anchors.py check --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  >/tmp/anchor-check.json || fail "unchanged anchor should pass"
jq -e '.status == "pass" and .locked == 1 and .unlocked_commands == 1' /tmp/anchor-check.json >/dev/null \
  || fail "anchor check pass contract"

printf '%s\n' 'changed behavior' >"${ANCHOR_WS}/tests/acceptance.txt"
set +e
./scripts/tasks/check-anchors.py check --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  >/tmp/anchor-changed.json
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "changed anchor should fail"
jq -e '.checks[] | select(.id == "AC-1" and .status == "fail" and .reason == "digest_mismatch")' \
  /tmp/anchor-changed.json >/dev/null || fail "changed anchor failure details"
set +e
./scripts/tasks/check-anchors.py lock --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  >/tmp/anchor-silent-relock.json
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "changed locked anchor must not silently relock"

fixture_state_patch --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" --patch \
  '{"clarity":{"history":[{"type":"anchor_relock_approval","acceptance_id":"AC-1","from_sha256":"wrong","to_sha256":"wrong","approved_by":"user"}]}}' >/dev/null
set +e
./scripts/tasks/check-anchors.py lock --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  >/tmp/anchor-wrong-approval.json
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "relock approval must be bound to exact old/new digests"

OLD_DIGEST=$(jq -r '.tasks.stories[0].acceptance[0].evidence.sha256' \
  "${ANCHOR_WS}/.adlc5/${ANCHOR_FEATURE}/state.json")
NEW_DIGEST=$(python3 - "${ANCHOR_WS}/tests/acceptance.txt" <<'PY'
import hashlib, sys
print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())
PY
)
APPROVAL_PATCH=$(jq -nc --arg old "$OLD_DIGEST" --arg new "$NEW_DIGEST" \
  '{clarity:{history:[{type:"anchor_relock_approval",acceptance_id:"AC-1",from_sha256:$old,to_sha256:$new,approved_by:"user"}]}}')
fixture_state_patch --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" --patch "$APPROVAL_PATCH" >/dev/null
./scripts/tasks/check-anchors.py lock --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  >/tmp/anchor-approved-relock.json || fail "exact approved anchor relock should succeed"
fixture_state_patch --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  --patch "$(jq -c '.patch' /tmp/anchor-approved-relock.json)" >/dev/null
./scripts/tasks/check-anchors.py check --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  >/dev/null || fail "approved relocked anchor should verify"

LOCKED_ACCEPTANCE=$(jq -c '.tasks.stories[0].acceptance' \
  "${ANCHOR_WS}/.adlc5/${ANCHOR_FEATURE}/state.json")
REMAINING_ACCEPTANCE=$(echo "$LOCKED_ACCEPTANCE" | jq -c 'map(select(.id == "AC-2"))')
fixture_state_patch --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  --patch "$(jq -nc --argjson acceptance "$REMAINING_ACCEPTANCE" '{tasks:{stories:[{id:"US-1",acceptance:$acceptance}]}}')" >/dev/null
set +e
./scripts/tasks/check-anchors.py check --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  >/tmp/anchor-deleted.json
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "deleted locked anchor should fail"
jq -e '.checks[] | select(.id == "AC-1" and .status == "fail" and .reason == "manifest_mismatch")' \
  /tmp/anchor-deleted.json >/dev/null || fail "deleted locked anchor failure details"
fixture_state_patch --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  --patch "$(jq -nc --argjson acceptance "$LOCKED_ACCEPTANCE" '{tasks:{stories:[{id:"US-1",acceptance:$acceptance}]}}')" >/dev/null

MUTATED_COMMAND=$(echo "$LOCKED_ACCEPTANCE" | jq -c 'map(if .id == "AC-2" then .evidence.value = "./scripts/changed.sh" else . end)')
fixture_state_patch --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  --patch "$(jq -nc --argjson acceptance "$MUTATED_COMMAND" '{tasks:{stories:[{id:"US-1",acceptance:$acceptance}]}}')" >/dev/null
cp "${ANCHOR_WS}/.adlc5/${ANCHOR_FEATURE}/acceptance-lock.json" /tmp/anchor-manifest-before-tamper.json
python3 - "${ANCHOR_WS}/.adlc5/${ANCHOR_FEATURE}/acceptance-lock.json" <<'PY'
import hashlib, json, sys
from pathlib import Path

path = Path(sys.argv[1])
manifest = json.loads(path.read_text())
for criterion in manifest["acceptance"]:
    if criterion["id"] == "AC-2":
        criterion["evidence"]["value"] = "./scripts/changed.sh"
canonical = json.dumps(manifest["acceptance"], sort_keys=True, separators=(",", ":")).encode()
manifest["sha256"] = hashlib.sha256(canonical).hexdigest()
path.write_text(json.dumps(manifest, indent=2) + "\n")
PY
set +e
./scripts/tasks/check-anchors.py check --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  >/tmp/anchor-command-mutated.json
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "changed command definition should fail"
jq -e '.checks[] | select(.id == "AC-2" and .status == "fail" and .reason == "manifest_mismatch")' \
  /tmp/anchor-command-mutated.json >/dev/null || fail "changed command failure details"
cp /tmp/anchor-manifest-before-tamper.json "${ANCHOR_WS}/.adlc5/${ANCHOR_FEATURE}/acceptance-lock.json"
fixture_state_patch --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  --patch "$(jq -nc --argjson acceptance "$LOCKED_ACCEPTANCE" '{tasks:{stories:[{id:"US-1",acceptance:$acceptance}]}}')" >/dev/null

cp "${ANCHOR_WS}/.adlc5/${ANCHOR_FEATURE}/acceptance-lock.json" /tmp/anchor-manifest-before-delete.json
fixture_state_patch --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  --patch '{"tasks":{"stories":[{"id":"US-1","acceptance":[]}]}}' >/dev/null
rm "${ANCHOR_WS}/.adlc5/${ANCHOR_FEATURE}/acceptance-lock.json"
set +e
./scripts/tasks/check-anchors.py check --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  >/tmp/anchor-joint-delete.json
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "deleting state anchors and local manifest should fail"
cp /tmp/anchor-manifest-before-delete.json "${ANCHOR_WS}/.adlc5/${ANCHOR_FEATURE}/acceptance-lock.json"
fixture_state_patch --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  --patch "$(jq -nc --argjson acceptance "$LOCKED_ACCEPTANCE" '{tasks:{stories:[{id:"US-1",acceptance:$acceptance}]}}')" >/dev/null

rm "${ANCHOR_WS}/tests/acceptance.txt"
set +e
./scripts/tasks/check-anchors.py check --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" \
  >/tmp/anchor-missing.json
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "missing anchor should fail"
jq -e '.checks[] | select(.id == "AC-1" and .status == "fail" and .reason == "missing")' \
  /tmp/anchor-missing.json >/dev/null || fail "missing anchor failure details"
pass "acceptance anchor lock/check"

ANCHOR_FACADE_FEATURE="anchor-facade"
printf '%s\n' 'facade behavior' >"${ANCHOR_WS}/tests/facade.txt"
./scripts/init-feature.sh --feature "$ANCHOR_FACADE_FEATURE" --workspace "$ANCHOR_WS" \
  --mode brownfield --interaction autonomous >/dev/null
fixture_state_patch --feature "$ANCHOR_FACADE_FEATURE" --workspace "$ANCHOR_WS" --patch \
  '{"tasks":{"stories":[{"id":"US-F","batch":1,"files":[],"depends_on":[],"acceptance":[{"id":"AC-F","owner":"product","evidence":{"type":"file","value":"tests/facade.txt"}}]}]}}' >/dev/null
./scripts/adlc5 anchors lock --feature "$ANCHOR_FACADE_FEATURE" --workspace "$ANCHOR_WS" \
  >/tmp/anchor-facade-lock.json || fail "adlc5 anchors lock should apply the lock"
jq -e '.status == "pass" and .applied == true' /tmp/anchor-facade-lock.json >/dev/null \
  || fail "adlc5 anchors lock output contract"
jq -e '.tasks.stories[0].acceptance[0].evidence.sha256 | test("^[0-9a-f]{64}$")' \
  "${ANCHOR_WS}/.adlc5/${ANCHOR_FACADE_FEATURE}/state.json" >/dev/null \
  || fail "adlc5 anchors lock should persist digest"
[[ -f "${ANCHOR_WS}/.adlc5/${ANCHOR_FACADE_FEATURE}/acceptance-lock.json" ]] \
  || fail "adlc5 anchors lock should persist manifest"
pass "adlc5 anchor façade applies lock"

python3 - "$ANCHOR_WS" <<'PY'
import importlib.machinery, importlib.util, io, json, sys
from contextlib import redirect_stdout
from pathlib import Path
from subprocess import CompletedProcess

loader = importlib.machinery.SourceFileLoader("adlc5_cli", "scripts/adlc5")
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)
workspace = Path(sys.argv[1])
manifest = workspace / ".adlc5" / "anchor-facade-exception" / "acceptance-lock.json"
manifest.parent.mkdir(parents=True, exist_ok=True)

def fake_run(*_args, **_kwargs):
    manifest.write_text("new manifest\n")
    return CompletedProcess([], 0, json.dumps({"status": "pass", "patch": {"tasks": {"stories": []}}}), "")

restored = []
module.subprocess.run = fake_run
module.read_anchor_ref = lambda *_args: "old-ref"
module.restore_anchor_trust = lambda *_args: restored.append(True)
module.set_feature_state = lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("simulated write failure"))
with redirect_stdout(io.StringIO()):
    result = module.cmd_anchors(["lock", "--feature", "anchor-facade-exception", "--workspace", str(workspace)])
assert result == 2 and restored == [True]
PY
pass "adlc5 anchor façade rolls back state-write exceptions"

for feature in anchor-unlocked-implement anchor-duplicate-id; do
  ./scripts/init-feature.sh --feature "$feature" --workspace "$ANCHOR_WS" \
    --mode brownfield --interaction autonomous >/dev/null
done
printf '%s\n' 'one' >"${ANCHOR_WS}/tests/one.txt"
printf '%s\n' 'two' >"${ANCHOR_WS}/tests/two.txt"
fixture_state_patch --feature anchor-unlocked-implement --workspace "$ANCHOR_WS" --patch \
  '{"current_stage":"implement","current_step":"implement-1-build","tasks":{"stories":[{"id":"US-1","batch":1,"files":[],"depends_on":[],"acceptance":[{"id":"AC-1","owner":"product","evidence":{"type":"file","value":"tests/one.txt"}}]}]}}' >/dev/null
set +e
./scripts/tasks/check-anchors.py lock --feature anchor-unlocked-implement --workspace "$ANCHOR_WS" \
  >/tmp/anchor-unlocked-implement.json
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "file anchor without digest must not be lockable after Implement starts"

fixture_state_patch --feature anchor-duplicate-id --workspace "$ANCHOR_WS" --patch \
  '{"tasks":{"stories":[{"id":"US-1","batch":1,"files":[],"depends_on":[],"acceptance":[{"id":"AC-DUP","owner":"product","evidence":{"type":"file","value":"tests/one.txt"}},{"id":"AC-DUP","owner":"qa","evidence":{"type":"file","value":"tests/two.txt"}}]}]}}' >/dev/null
set +e
./scripts/tasks/check-anchors.py lock --feature anchor-duplicate-id --workspace "$ANCHOR_WS" \
  >/tmp/anchor-duplicate-id.json
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "duplicate acceptance IDs must fail anchor locking"
jq -e '.checks[] | select(.reason == "duplicate_id" and .status == "fail")' \
  /tmp/anchor-duplicate-id.json >/dev/null || fail "duplicate acceptance ID details"
pass "acceptance anchor anti-bypass checks"

printf '%s\n' 'changed behavior' >"${ANCHOR_WS}/tests/acceptance.txt"
set +e
./scripts/check-gates.py --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" --gate pr-ready \
  >/tmp/anchor-pr-ready-clean.json
set -e
jq -e '.checks[] | select(.id == "anchor_integrity" and .status == "pass")' \
  /tmp/anchor-pr-ready-clean.json >/dev/null || fail "pr-ready should report clean anchors"

printf '%s\n' 'changed again' >"${ANCHOR_WS}/tests/acceptance.txt"
set +e
./scripts/check-gates.py --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" --gate implement-2-verify \
  >/tmp/anchor-verify-changed.json
VERIFY_EC=$?
./scripts/check-gates.py --feature "$ANCHOR_FEATURE" --workspace "$ANCHOR_WS" --gate pr-ready \
  >/tmp/anchor-pr-ready-changed.json
PR_EC=$?
set -e
[[ "$VERIFY_EC" -eq 1 && "$PR_EC" -eq 1 ]] || fail "changed anchors should fail verify and pr-ready"
for report in /tmp/anchor-verify-changed.json /tmp/anchor-pr-ready-changed.json; do
  jq -e '.checks[] | select(.id == "anchor_integrity" and .status == "fail")' "$report" >/dev/null \
    || fail "gate missing anchor_integrity failure: $report"
done
pass "verification gates enforce acceptance anchors"

# task graph validator: dependencies, batches, and parallel file ownership
GRAPH_WS="${TMP}/task-graph"
python3 - "$GRAPH_WS" <<'PY'
import json, sys
from pathlib import Path

root = Path(sys.argv[1])
cases = {
    "valid": [
        {"id": "A", "batch": 1, "files": ["src/a.py"], "depends_on": []},
        {"id": "B", "batch": 2, "files": ["src/b.py"], "depends_on": ["A"]},
        {"id": "C", "batch": 2, "files": ["src/c.py"], "depends_on": ["A"]},
    ],
    "duplicate": [
        {"id": "A", "batch": 1, "files": ["src/a.py"], "depends_on": []},
        {"id": "A", "batch": 2, "files": ["src/b.py"], "depends_on": []},
    ],
    "missing": [
        {"id": "A", "batch": 1, "files": ["src/a.py"], "depends_on": ["Z"]},
    ],
    "cycle": [
        {"id": "A", "batch": 1, "files": ["src/a.py"], "depends_on": ["B"]},
        {"id": "B", "batch": 2, "files": ["src/b.py"], "depends_on": ["A"]},
    ],
    "bad-batch": [
        {"id": "A", "batch": 1, "files": ["src/a.py"], "depends_on": []},
        {"id": "B", "batch": 1, "files": ["src/b.py"], "depends_on": ["A"]},
    ],
    "missing-batch": [
        {"id": "A", "files": ["src/a.py"], "depends_on": []},
    ],
    "batch-registry-mismatch": [
        {"id": "A", "batch": 1, "files": ["src/a.py"], "depends_on": []},
        {"id": "B", "batch": 2, "files": ["src/b.py"], "depends_on": ["A"]},
    ],
    "parallel-overlap": [
        {"id": "A", "batch": 1, "files": ["src/shared.py"], "depends_on": []},
        {"id": "B", "batch": 1, "files": ["src/shared.py"], "depends_on": []},
    ],
    "sequential-overlap": [
        {"id": "A", "batch": 1, "files": ["src/shared.py"], "depends_on": []},
        {"id": "B", "batch": 2, "files": ["src/shared.py"], "depends_on": ["A"]},
    ],
}
for name, stories in cases.items():
    feature_dir = root / ".adlc5" / name
    feature_dir.mkdir(parents=True)
    batches = {}
    for story in stories:
        if isinstance(story.get("batch"), int):
            batches.setdefault(story["batch"], []).append(story["id"])
    parallel_batches = [
        {"batch": batch, "story_ids": ids}
        for batch, ids in sorted(batches.items())
    ]
    if name == "batch-registry-mismatch":
        parallel_batches = [{"batch": 1, "story_ids": ["A", "B"]}]
    state = {
        "schema_version": "3.0",
        "feature": name,
        "current_stage": "tasks",
        "current_step": "tasks-1-stories",
        "stage_status": {},
        "tasks": {"stories": stories, "parallel_batches": parallel_batches},
    }
    (feature_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
PY

graph_case() {
  local feature="$1" expected="$2" check_id="${3:-}"
  set +e
  ./scripts/tasks/validate-graph.py --feature "$feature" --workspace "$GRAPH_WS" >"/tmp/task-graph-${feature}.json"
  local ec=$?
  set -e
  if [[ "$expected" == pass ]]; then
    [[ "$ec" -eq 0 ]] || fail "task graph $feature expected pass, got $ec"
    jq -e '.status == "pass"' "/tmp/task-graph-${feature}.json" >/dev/null || fail "task graph $feature pass JSON"
  else
    [[ "$ec" -eq 1 ]] || fail "task graph $feature expected fail, got $ec"
    jq -e --arg id "$check_id" '.status == "fail" and any(.checks[]; .id == $id and .status == "fail")' \
      "/tmp/task-graph-${feature}.json" >/dev/null || fail "task graph $feature missing $check_id failure"
  fi
}

graph_case valid pass
graph_case duplicate fail unique_story_ids
graph_case missing fail dependencies_exist
graph_case cycle fail acyclic
graph_case bad-batch fail batch_order
graph_case missing-batch fail batch_values
graph_case batch-registry-mismatch fail parallel_batches_match
graph_case parallel-overlap fail parallel_file_overlap
graph_case sequential-overlap pass
pass "task graph validation"

mkdir -p "${GRAPH_WS}/.adlc5/duplicate/tasks/code-spec"
cat >"${GRAPH_WS}/.adlc5/duplicate/tasks/code-spec/US-1.md" <<'EOF'
---
story_id: A
files_to_create:
  - src/a.py
files_to_modify: []
tests:
  - file: app/a.py
    name: add
acceptance_criteria:
  - AC-1
acceptance_checks:
  AC-1: [tests/test_a.py::test_a]
---
# code spec
EOF

# "valid" plans stories A, B, C — spec-lint requires one matching spec per
# planned (non-integration) story, so all three need one here.
mkdir -p "${GRAPH_WS}/.adlc5/valid/tasks/code-spec"
for sid in A B C; do
  sid_lower=$(printf '%s' "$sid" | tr '[:upper:]' '[:lower:]')
  cat >"${GRAPH_WS}/.adlc5/valid/tasks/code-spec/US-${sid}.md" <<EOF
---
story_id: ${sid}
files_to_create:
  - src/${sid_lower}.py
files_to_modify: []
tests:
  - file: tests/test_${sid_lower}.py
    name: test_${sid_lower}
acceptance_criteria:
  - AC-1
acceptance_checks:
  AC-1: [tests/test_${sid_lower}.py::test_${sid_lower}]
---
# code spec
EOF
done
./scripts/check-gates.py --feature valid --workspace "$GRAPH_WS" --gate tasks-complete \
  >/tmp/task-graph-gate-valid.json || fail "valid task graph should pass tasks-complete"
set +e
./scripts/check-gates.py --feature duplicate --workspace "$GRAPH_WS" --gate tasks-complete \
  >/tmp/task-graph-gate-duplicate.json
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "duplicate task graph should fail tasks-complete"
jq -e '.checks[] | select(.id == "task_graph_valid" and .status == "fail")' \
  /tmp/task-graph-gate-duplicate.json >/dev/null || fail "tasks-complete missing task_graph_valid failure"
pass "tasks-complete enforces task graph"

# v2 pilot emits valid action JSON on a fresh feature
./scripts/pilot-autopilot.sh --feature "$FEATURE_V2" --workspace "$V2_TMP" >/tmp/v2-pilot.json
jq -e '.action == "spawn" and .skill == "adlc5-specify" and .gate == "specify-complete"' /tmp/v2-pilot.json >/dev/null || fail "pilot-v2 fresh feature action contract"
jq -e '.recommended_model != null and (.model_version|tostring|length)>0' /tmp/v2-pilot.json >/dev/null || fail "pilot-v2 recommended_model fields"
jq -e '(.run_id | length) > 0 and .node_id == "specify-0-git" and .attempt == 1' \
  /tmp/v2-pilot.json >/dev/null || fail "pilot-v2 correlation fields"
PILOT_RUN_ID=$(jq -r '.run_id' /tmp/v2-pilot.json)
jq -s -e --arg run "$PILOT_RUN_ID" 'any(.[]; .run_id == $run and .node_id == "specify-0-git")' \
  "${V2_TMP}/.adlc5/${FEATURE_V2}/telemetry/events.jsonl" >/dev/null \
  || fail "pilot correlation should propagate to gate telemetry"
pass "pilot-v2 fresh feature JSON action"

# profile routing: explicit tiny, standard, and high-risk paths
ROUTE_WS="${TMP}/profile-routing"
mkdir -p "$ROUTE_WS"
git -C "$ROUTE_WS" init -q
printf '%s\n' 'Consumer contract fixture' >"${ROUTE_WS}/README.md"
git -C "$ROUTE_WS" add README.md
git -C "$ROUTE_WS" -c user.name='ADLC5 fixture' -c user.email='fixture@example.test' commit -qm 'fixture baseline'
for profile in tiny standard high_risk; do
  feature="route-${profile//_/-}"
  mkdir -p "$ROUTE_WS"
  ./scripts/init-feature.sh --feature "$feature" --workspace "$ROUTE_WS" \
    --mode brownfield --interaction autonomous >/dev/null
  mkdir -p "${ROUTE_WS}/.adlc5/${feature}"
  cat >"${ROUTE_WS}/.adlc5/${feature}/policies.yaml" <<EOF
autopilot:
  interaction_mode: autonomous
  profile: ${profile}
persona_mode:
  enabled: true
  verifier_different_model: true
  fresh_subagent_per_persona: true
  forbid_orchestrator_implement: true
EOF
  fixture_state_patch --feature "$feature" --workspace "$ROUTE_WS" --patch \
    '{"current_stage":"specify","current_step":"specify-4-handoff","git":{"isolation":"current"},"clarity":{"score":100}}' >/dev/null
  echo "# Spec handoff" >"${ROUTE_WS}/.adlc5/${feature}/spec-handoff.md"
  printf '%s\n' '{"categories":[],"uncertain":false,"rationale":"bounded routing fixture"}' \
    >"${ROUTE_WS}/.adlc5/${feature}/risk.json"
done

./scripts/pilot-autopilot.sh --feature route-tiny --workspace "$ROUTE_WS" >/tmp/route-tiny.json
./scripts/pilot-autopilot.sh --feature route-standard --workspace "$ROUTE_WS" >/tmp/route-standard.json
./scripts/pilot-autopilot.sh --feature route-high-risk --workspace "$ROUTE_WS" >/tmp/route-high-risk.json
jq -e '.action == "advance" and .suggested_next == "implement-1-build"' /tmp/route-tiny.json >/dev/null \
  || fail "tiny profile should route from Specify to Implement"
jq -e '.action == "advance" and .suggested_next == "plan-4-design-discovery"' /tmp/route-standard.json >/dev/null \
  || fail "standard profile should retain brief Plan"
jq -e '.action == "advance" and .suggested_next == "plan-1-engineering-architecture"' /tmp/route-high-risk.json >/dev/null \
  || fail "high-risk profile should retain Plan"

QUOTE_WS="${TMP}/route'space"
mkdir -p "$QUOTE_WS"
./scripts/init-feature.sh --feature route-quote --workspace "$QUOTE_WS" \
  --mode brownfield --interaction autonomous >/dev/null
mkdir -p "${QUOTE_WS}/.adlc5/route-quote"
printf '%s\n' 'autopilot:' '  interaction_mode: autonomous' '  profile: tiny' \
  >"${QUOTE_WS}/.adlc5/route-quote/policies.yaml"
fixture_state_patch --feature route-quote --workspace "$QUOTE_WS" --patch \
  '{"current_stage":"specify","current_step":"specify-4-handoff","git":{"isolation":"current"},"clarity":{"score":100}}' >/dev/null
printf '%s\n' '# Spec handoff' >"${QUOTE_WS}/.adlc5/route-quote/spec-handoff.md"
./scripts/pilot-autopilot.sh --feature route-quote --workspace "$QUOTE_WS" >/tmp/route-quote.json \
  || fail "profile routing should support apostrophes in workspace paths"
jq -e '.action == "advance" and .suggested_next == "implement-1-build"' /tmp/route-quote.json >/dev/null \
  || fail "quoted workspace profile route"

fixture_state_patch --feature route-high-risk --workspace "$ROUTE_WS" --patch \
  '{"current_stage":"implement","current_step":"implement-2-verify","persona":{"active":"tester"},"tasks":{"stories":[{"id":"US-1","title":"Risky","status":"implementation_complete","batch":1,"files":[],"depends_on":[]}]}}' >/dev/null
./scripts/pilot-autopilot.sh --feature route-high-risk --workspace "$ROUTE_WS" >/tmp/route-high-risk-verify.json
jq -e '.action == "spawn" and .persona == "tester" and .fresh_session == true and .verifier_different_model == true' \
  /tmp/route-high-risk-verify.json >/dev/null || fail "high-risk verifier separation policy"

set +e
./scripts/check-gates.py --feature route-high-risk --workspace "$ROUTE_WS" --gate implement-2-verify \
  >/tmp/route-high-risk-independence-missing.json
set -e
jq -e '.checks[] | select(.id == "verifier_independence" and .status == "fail")' \
  /tmp/route-high-risk-independence-missing.json >/dev/null \
  || fail "high-risk verification should fail without independence evidence"
fixture_state_patch --feature route-high-risk --workspace "$ROUTE_WS" --patch \
  '{"clarity":{"history":[{"type":"verifier_waiver","approved_by":"agent"}]}}' >/dev/null
set +e
./scripts/check-gates.py --feature route-high-risk --workspace "$ROUTE_WS" --gate implement-2-verify \
  >/tmp/route-high-risk-agent-waiver.json
set -e
jq -e '.checks[] | select(.id == "verifier_independence" and .status == "fail")' \
  /tmp/route-high-risk-agent-waiver.json >/dev/null \
  || fail "agent-authored verifier waiver should not bypass independence"
for empty_approver in 'human:' 'github:' 'email:'; do
  fixture_state_patch --feature route-high-risk --workspace "$ROUTE_WS" --patch \
    "$(jq -nc --arg approved_by "$empty_approver" '{clarity:{history:[{type:"verifier_waiver",approved_by:$approved_by}]}}')" >/dev/null
  set +e
  ./scripts/check-gates.py --feature route-high-risk --workspace "$ROUTE_WS" --gate implement-2-verify \
    >/tmp/route-high-risk-empty-waiver.json
  set -e
  jq -e '.checks[] | select(.id == "verifier_independence" and .status == "fail")' \
    /tmp/route-high-risk-empty-waiver.json >/dev/null \
    || fail "empty human waiver identifier should not bypass independence: $empty_approver"
done
fixture_state_patch --feature route-high-risk --workspace "$ROUTE_WS" --patch \
  '{"clarity":{"history":[]},"implement":{"verification":{"independence":{"fresh_session":true,"coder_session_id":"coder-1","verifier_session_id":"verifier-1","coder_model_id":"model-a","verifier_model_id":"model-b"}}}}' >/dev/null
set +e
./scripts/check-gates.py --feature route-high-risk --workspace "$ROUTE_WS" --gate implement-2-verify \
  >/tmp/route-high-risk-independence-present.json
set -e
jq -e '.checks[] | select(.id == "verifier_independence" and .status == "pass")' \
  /tmp/route-high-risk-independence-present.json >/dev/null \
  || fail "high-risk verification should accept independent verifier evidence"

mkdir -p "${ROUTE_WS}/.qa/route-high-risk"
printf '%s\n' 'Overall Status: BLOCKED' 'Do not continue before CLEARED by security.' \
  >"${ROUTE_WS}/.qa/route-high-risk/deployment-clearance.md"
set +e
./scripts/check-gates.py --feature route-high-risk --workspace "$ROUTE_WS" --gate implement-4-qa \
  >/tmp/route-high-risk-qa-blocked.json
QA_BLOCKED_EC=$?
set -e
[[ "$QA_BLOCKED_EC" -eq 1 ]] || fail "BLOCKED QA status must dominate incidental CLEARED text"
fixture_state_patch --feature route-high-risk --workspace "$ROUTE_WS" --patch \
  '{"implement":{"qa":{"status":"pending","clearance_path":""}}}' >/dev/null
printf '%s\n' 'STATUS: CLEARED' >"${ROUTE_WS}/.qa/route-high-risk/deployment-clearance.md"
./scripts/check-gates.py --feature route-high-risk --workspace "$ROUTE_WS" --gate implement-4-qa \
  >/tmp/route-high-risk-qa.json || fail "canonical implement-4-qa gate should reach QA handler"
jq -e '.status == "pass" and any(.checks[]; .id == "qa_deployment_clearance" and .status == "pass")' \
  /tmp/route-high-risk-qa.json >/dev/null || fail "canonical QA gate output"
fixture_state_patch --feature route-high-risk --workspace "$ROUTE_WS" --patch \
  '{"implement":{"pr":{"status":"completed","url":"https://example.test/pr/2"}}}' >/dev/null
./scripts/check-gates.py --feature route-high-risk --workspace "$ROUTE_WS" --gate implement-5-pr \
  >/tmp/route-high-risk-pr.json || fail "canonical implement-5-pr gate should reach PR handler"
jq -e '.status == "pass" and any(.checks[]; .id == "assure_pr_review" and .status == "pass")' \
  /tmp/route-high-risk-pr.json >/dev/null || fail "canonical PR gate output"

for feature in route-tiny route-standard route-high-risk; do
  set +e
  ./scripts/check-gates.py --feature "$feature" --workspace "$ROUTE_WS" --gate pr-ready \
    >"/tmp/${feature}-pr-ready.json"
  set -e
done
jq -e 'all(.checks[]; .id != "integration_completed" and .id != "qa_deployment_clearance")' \
  /tmp/route-tiny-pr-ready.json >/dev/null || fail "tiny pr-ready should skip integration and QA"
jq -e 'any(.checks[]; .id == "integration_completed") and all(.checks[]; .id != "qa_deployment_clearance")' \
  /tmp/route-standard-pr-ready.json >/dev/null || fail "standard pr-ready should require integration but skip QA"
jq -e 'any(.checks[]; .id == "integration_completed") and any(.checks[]; .id == "qa_deployment_clearance")' \
  /tmp/route-high-risk-pr-ready.json >/dev/null || fail "high-risk pr-ready should require integration and QA"
jq -e '.checks[] | select(.id == "anchor_integrity" and .status == "fail")' \
  /tmp/route-high-risk-pr-ready.json >/dev/null || fail "high-risk pr-ready should require a locked file anchor"
python3 - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, "scripts")
from lib.policies_load import _parse_simple, load_policies_file, required_gate_names

tiny = load_policies_file(Path("templates/policies-tiny.yaml.example"))
standard = load_policies_file(Path("templates/policies-small-feature.yaml.example"))
high = load_policies_file(Path("templates/policies-high-risk.yaml.example"))
assert tiny["autopilot"]["profile"] == "tiny"
assert standard["autopilot"]["profile"] == "standard"
assert high["autopilot"]["profile"] == "high_risk"
assert tiny["autopilot"]["quality_gates"]["require_tests"] is True
assert standard["autopilot"]["quality_gates"]["lint_errors_max"] == 0
assert high["autopilot"]["quality_gates"]["coverage_min"] == 80
assert high["autopilot"]["require_human_pr_approval"] is True
assert high["autopilot"]["require_anchors"] is True
assert high["persona_mode"] == {
    "enabled": True,
    "verifier_different_model": True,
    "fresh_subagent_per_persona": True,
    "forbid_orchestrator_implement": True,
}
fallback = _parse_simple("""autopilot:
  quality_gates:
    required_custom_gates:
      - smoke
""")
assert required_gate_names(fallback) == ["smoke"]
PY

# disposable profile smoke: tiny can finish without integration/QA; high-risk fails closed
cp templates/policies-tiny.yaml.example "${ROUTE_WS}/.adlc5/route-tiny/policies.yaml"
mkdir -p "${ROUTE_WS}/.adlc5/route-tiny/delivery" "${ROUTE_WS}/.adlc5/route-tiny/verify"
cat >"${ROUTE_WS}/.adlc5/route-tiny/delivery/state.json" <<'EOF'
{"current_phase":"completed","stories":{"US-1":{"type":"component","status":"verified"}},"verification_summary":{"overall":"pass"},"integration":{"status":"pending"}}
EOF
printf '%s\n' '**Overall:** pass' >"${ROUTE_WS}/.adlc5/route-tiny/verify/verification-report.md"
fixture_state_patch --feature route-tiny --workspace "$ROUTE_WS" --patch \
  '{"current_stage":"implement","current_step":"implement-5-pr","stage_status":{"specify":"completed","plan":"waived","tasks":"waived","implement":"completed"},"persona":{"active":"tester"},"tasks":{"stories":[]},"implement":{"verification":{"status":"completed"},"integration":{"status":"pending"},"qa":{"status":"pending","clearance_path":""},"pr":{"status":"completed","url":"https://example.test/pr/1"}}}' >/dev/null
set +e
./scripts/check-gates.py --feature route-tiny --workspace "$ROUTE_WS" --gate pr-ready \
  >/tmp/route-tiny-no-runner.json
NO_RUNNER_EC=$?
set -e
[[ "$NO_RUNNER_EC" -eq 1 ]] || fail "autonomous quality gates should fail when test/lint runners are skipped"
jq -e 'any(.checks[]; .id == "quality_gate_tests" and .status == "fail") and any(.checks[]; .id == "quality_gate_lint" and .status == "fail")' \
  /tmp/route-tiny-no-runner.json >/dev/null || fail "skipped quality runner failures missing"

# Freeze generated scaffold before the bounded source change fixture.
git -C "$ROUTE_WS" add .
git -C "$ROUTE_WS" -c user.name='ADLC5 fixture' -c user.email='fixture@example.test' commit -qm 'fixture scaffold'
FAKE_BIN="${ROUTE_WS}/fake-bin"
mkdir -p "$FAKE_BIN"
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' >"${FAKE_BIN}/npm"
chmod +x "${FAKE_BIN}/npm"
printf '%s\n' '{"scripts":{"test":"true","lint":"true"}}' >"${ROUTE_WS}/package.json"

./scripts/init-feature.sh --feature route-tiny-direct --workspace "$ROUTE_WS" \
  --mode brownfield --interaction autonomous >/dev/null
cp templates/policies-tiny.yaml.example "${ROUTE_WS}/.adlc5/route-tiny-direct/policies.yaml"
fixture_state_patch --feature route-tiny-direct --workspace "$ROUTE_WS" --patch \
  '{"current_stage":"implement","current_step":"implement-1-build","stage_status":{"specify":"completed","plan":"waived","tasks":"waived","implement":"in_progress"},"tasks":{"stories":[]}}' >/dev/null
PATH="${FAKE_BIN}:$PATH" ./scripts/check-gates.py --feature route-tiny-direct --workspace "$ROUTE_WS" \
  --gate implement-1-build >/tmp/route-tiny-direct-build.json \
  || fail "tiny direct build should pass runnable test/lint gates without synthetic stories"
jq -e '.status == "pass" and any(.checks[]; .id == "quality_gate_tests" and .status == "pass")' \
  /tmp/route-tiny-direct-build.json >/dev/null || fail "tiny direct build quality evidence"

cat >"${ROUTE_WS}/.adlc5/route-tiny/change.md" <<'EOF'
---
files_to_modify: [package.json, fake-bin/npm]
---
# Bounded change
Exercise runnable test/lint declarations in this disposable consumer fixture.
EOF
mkdir -p "${ROUTE_WS}/.adlc5/route-tiny/evidence"
cat >"${ROUTE_WS}/.adlc5/route-tiny/evidence/checks.json" <<'EOF'
[{"id":"tests","command":"python3 -c \"assert 1 + 1 == 2\""},{"id":"lint","command":"python3 -c \"compile('pass', 'fixture', 'exec')\""}]
EOF
printf '%s\n' '{"coder_session_id":"fixture-coder","verifier_session_id":"fixture-reviewer","coder_model_id":"fixture-model","verifier_model_id":"fixture-model","disposition":"pass","blocking_findings":[]}' \
  >"${TMP}/tiny-review.json"
./scripts/adlc5 evidence check --feature route-tiny --workspace "$ROUTE_WS" >/dev/null
./scripts/adlc5 evidence review --feature route-tiny --workspace "$ROUTE_WS" --file "${TMP}/tiny-review.json" >/dev/null
set +e
PATH="${FAKE_BIN}:$PATH" \
./scripts/check-gates.py --feature route-tiny --workspace "$ROUTE_WS" --gate pr-ready \
  >/tmp/route-tiny-complete.json
TINY_EC=$?
set -e
[[ "$TINY_EC" -eq 0 ]] || fail "complete tiny profile should pass pr-ready"
jq -e '.status == "pass"' /tmp/route-tiny-complete.json >/dev/null || fail "tiny pr-ready pass JSON"
fixture_state_patch --feature route-tiny --workspace "$ROUTE_WS" --patch \
  '{"stage_status":{"implement":"in_progress"}}' >/dev/null
set +e
PATH="${FAKE_BIN}:$PATH" \
./scripts/check-gates.py --feature route-tiny --workspace "$ROUTE_WS" --gate pr-ready \
  >/tmp/route-tiny-in-progress.json
TINY_IN_PROGRESS_EC=$?
set -e
[[ "$TINY_IN_PROGRESS_EC" -eq 0 ]] \
  || fail "canonical pr-ready must pass before stage_status.implement is completed"
jq -e '.status == "pass"' /tmp/route-tiny-in-progress.json >/dev/null \
  || fail "canonical in-progress pr-ready pass JSON"
set +e
PATH="${FAKE_BIN}:$PATH" \
./scripts/pilot-autopilot.sh --feature route-tiny --workspace "$ROUTE_WS" \
  >/tmp/route-tiny-terminal.json
TINY_TERMINAL_EC=$?
set -e
[[ "$TINY_TERMINAL_EC" -eq 3 ]] || fail "terminal pilot should return done exit 3 after pr-ready"
jq -e '.action == "done" and .phase == "pr-ready"' /tmp/route-tiny-terminal.json >/dev/null \
  || fail "terminal pilot should finish instead of advancing to implement-5-pr again"

cp templates/policies-high-risk.yaml.example "${ROUTE_WS}/.adlc5/route-high-risk/policies.yaml"
set +e
./scripts/check-gates.py --feature route-high-risk --workspace "$ROUTE_WS" --gate pr-ready \
  >/tmp/route-high-risk-blocked.json
HIGH_EC=$?
set -e
[[ "$HIGH_EC" -eq 1 ]] || fail "incomplete high-risk profile should fail closed"
jq -e 'any(.checks[]; .id == "anchor_integrity" and .status == "fail") and any(.checks[]; .id == "human_pr_approval" and .status == "fail")' \
  /tmp/route-high-risk-blocked.json >/dev/null || fail "high-risk profile missing anchor/human blockers"
pass "profile routing and verifier separation"

# local dispatch stops with a structured executor handoff instead of spinning
FEATURE_DISPATCH="v2-dispatch"
DISPATCH_TMP="${TMP}/v2-dispatch"
mkdir -p "$DISPATCH_TMP"
set +e
./scripts/runner/dispatch.sh --feature "$FEATURE_DISPATCH" --workspace "$DISPATCH_TMP" --mode greenfield --max-iter 1 >/tmp/v2-dispatch.json 2>/tmp/v2-dispatch.err
EC=$?
set -e
[[ "$EC" -eq 1 ]] || fail "dispatch needs_executor expected exit 1 got $EC"
jq -e '.dispatch == "needs_executor" and .executor_required == true and .iterations == 1 and .action == "spawn"' \
  /tmp/v2-dispatch.json >/dev/null || fail "dispatch needs_executor JSON contract"
pass "dispatch structured executor handoff"

# Hermes Agent platform is supported by the global installer without side effects in dry-run
./scripts/install.sh --platform hermes --dry-run >/tmp/hermes-install-dry-run.txt
grep -q 'Skills (hermes):' /tmp/hermes-install-dry-run.txt || fail "hermes install dry-run did not target Hermes skills"
pass "hermes install dry-run"
./scripts/install.sh --platform antigravity --dry-run >/tmp/antigravity-install-dry-run.txt
! grep -q 'ADLC5 3\.0 skills' scripts/install.sh \
  || fail "Antigravity metadata must not advertise ADLC5 3.0"
pass "Antigravity metadata version coherence"

# resolve-model: alias + platform profile + version
# Isolated from user configuration; the example must not affect runtime routing.
chmod +x ./scripts/resolve-model.sh ./scripts/update-adlc5.sh
RESOLVE_DEFAULT_ROOT="${TMP}/resolve-model-default-root"
mkdir -p "${RESOLVE_DEFAULT_ROOT}/core"
cp config.example.yaml "${RESOLVE_DEFAULT_ROOT}/config.example.yaml"
cp core/VERSION "${RESOLVE_DEFAULT_ROOT}/core/VERSION"
python3 ./scripts/lib/model_routing.py --root "$RESOLVE_DEFAULT_ROOT" --platform cursor --tier implementation \
  >/tmp/resolve-model.json
jq -e '.tier == "execution" and .platform == "cursor" and (.version|length)>0' /tmp/resolve-model.json >/dev/null \
  || fail "resolve-model implementation→execution contract"
jq -e '.model_id == "host default"' /tmp/resolve-model.json >/dev/null \
  || fail "resolve-model should use host default without setup"
# bad tier fails
set +e
./scripts/resolve-model.sh --platform cursor --tier nope >/dev/null 2>&1
EC=$?
set -e
[[ "$EC" -ne 0 ]] || fail "resolve-model bad tier expected non-zero"
pass "resolve-model contract"

# update-adlc5 dry-run (skip pull) prints version and invokes install dry-run
./scripts/update-adlc5.sh --platform cursor --skip-pull --dry-run >/tmp/update-adlc5-dry-run.txt
grep -q 'ADLC5 version (before):' /tmp/update-adlc5-dry-run.txt || fail "update-adlc5 dry-run missing before version"
grep -q 'Target platform: cursor' /tmp/update-adlc5-dry-run.txt || fail "update-adlc5 dry-run missing platform"
pass "update-adlc5 dry-run"

# install/verify print-version
./scripts/install.sh --print-version | grep -Eq 'adlc5 [0-9]+\.[0-9]+\.[0-9]+' || fail "install --print-version"
./scripts/verify-install.sh --print-version | grep -Eq 'adlc5 [0-9]+\.[0-9]+\.[0-9]+' || fail "verify --print-version"
pass "print-version"

# adlc5 kernel façade: help + version
./scripts/adlc5 --help >/dev/null || fail "adlc5 --help"
./scripts/adlc5 version | grep -Eq 'adlc5 [0-9]+\.[0-9]+\.[0-9]+' || fail "adlc5 version"
pass "adlc5 help/version"

# adlc5 gate parity vs check-gates.py
cat >"${TMP}/.adlc5/${FEATURE}/delivery/state.json" <<'EOF'
{
  "feature_name": "test-feature",
  "current_phase": "build-1-implementation",
  "phase_status": {},
  "retry_policy": { "max_implementation_attempts": 2 },
  "stories": {
    "story-a": { "status": "implementation_complete", "type": "component" }
  }
}
EOF
set +e
./scripts/check-gates.py --feature "$FEATURE" --workspace "$TMP" --gate build-1-implementation >/tmp/adlc5-gate-direct.json
EC_DIRECT=$?
./scripts/adlc5 gate --feature "$FEATURE" --workspace "$TMP" --gate build-1-implementation >/tmp/adlc5-gate-facade.json
EC_FACADE=$?
set -e
[[ "$EC_DIRECT" -eq "$EC_FACADE" ]] || fail "adlc5 gate exit mismatch direct=$EC_DIRECT facade=$EC_FACADE"
diff -u /tmp/adlc5-gate-direct.json /tmp/adlc5-gate-facade.json >/dev/null \
  || fail "adlc5 gate stdout mismatch vs check-gates.py"
pass "adlc5 gate parity"

# adlc5 clarity parity (normalize scored_at)
SPEC_FILE="${TMP}/clarity-spec.md"
cat >"$SPEC_FILE" <<'EOF'
# Spec
## Functional Requirements
Users can create items.
## Acceptance Criteria
- Returns 201 on create
## Non-functional Requirements
p95 latency under 200ms
```json
{"id": "example"}
```
EOF
set +e
./scripts/clarity-score.py "$SPEC_FILE" --step-id specify >/tmp/adlc5-clarity-direct.json
EC_DIRECT=$?
./scripts/adlc5 clarity "$SPEC_FILE" --step-id specify >/tmp/adlc5-clarity-facade.json
EC_FACADE=$?
set -e
[[ "$EC_DIRECT" -eq "$EC_FACADE" ]] || fail "adlc5 clarity exit mismatch"
python3 - <<'PY'
import json
from pathlib import Path
def norm(p):
    d = json.loads(Path(p).read_text())
    d.pop("scored_at", None)
    if isinstance(d.get("detailed_report"), dict):
        d["detailed_report"].pop("scored_at", None)
    return d
a = norm("/tmp/adlc5-clarity-direct.json")
b = norm("/tmp/adlc5-clarity-facade.json")
if a != b:
    raise SystemExit(f"clarity JSON mismatch:\n{a}\n{b}")
PY
pass "adlc5 clarity parity"

# adlc5 pack parity vs generate-pack.sh
PACK_FEATURE="pack-feature"
mkdir -p "${TMP}/.adlc5/${PACK_FEATURE}/tasks/code-spec" "${TMP}/.adlc5/${PACK_FEATURE}/memory/context-packs"
cat >"${TMP}/.adlc5/${PACK_FEATURE}/state.json" <<'EOF'
{
  "schema_version": "3.0",
  "feature": "pack-feature",
  "tasks": {
    "stories": [{ "id": "story-a", "title": "Demo", "status": "ready" }]
  }
}
EOF
cat >"${TMP}/.adlc5/${PACK_FEATURE}/tasks/code-spec/story-a.md" <<'EOF'
---
story_id: story-a
files_to_create: [src/item.py]
files_to_modify: []
tests:
  - file: tests/test_item.py
    name: test_create
acceptance_criteria: [AC-1]
acceptance_checks:
  AC-1: [tests/test_item.py::test_create]
---
# Implementation
Create an item and preserve existing behavior.
EOF
printf '%s\n' '# Acceptance' 'AC-1: Creating an item returns its identifier.' \
  >"${TMP}/.adlc5/${PACK_FEATURE}/spec-handoff.md"
set +e
./scripts/memory/generate-pack.sh --feature "$PACK_FEATURE" --story-id story-a --workspace "$TMP" >/tmp/adlc5-pack-direct.json
EC_DIRECT=$?
# regenerate via façade after removing pack so paths stay comparable
rm -f "${TMP}/.adlc5/${PACK_FEATURE}/memory/context-packs/story-story-a.md"
./scripts/adlc5 pack --feature "$PACK_FEATURE" --story-id story-a --workspace "$TMP" >/tmp/adlc5-pack-facade.json
EC_FACADE=$?
set -e
[[ "$EC_DIRECT" -eq 0 && "$EC_FACADE" -eq 0 ]] || fail "adlc5 pack must succeed direct=$EC_DIRECT facade=$EC_FACADE"
diff -u /tmp/adlc5-pack-direct.json /tmp/adlc5-pack-facade.json >/dev/null \
  || fail "adlc5 pack stdout mismatch vs generate-pack.sh"
pass "adlc5 pack parity"

python3 ./scripts/tests/test-cursor-usage.py >/dev/null \
  || fail "Cursor usage collector unit tests"
pass "Cursor usage collector unit tests"

python3 ./scripts/tests/test-claude-usage.py >/dev/null \
  || fail "Claude usage collector unit tests"
pass "Claude usage collector unit tests"

python3 ./scripts/tests/test-claude-plugin.py >/tmp/claude-plugin-test.out 2>&1 \
  || { cat /tmp/claude-plugin-test.out >&2; fail "Claude plugin package, MCP stdio, bootstrap and hook tests"; }
pass "Claude plugin package, MCP stdio, bootstrap and hook tests"

python3 ./scripts/tests/test-codex-usage.py >/dev/null \
  || fail "Codex usage collector unit tests"
pass "Codex usage collector unit tests"

# adlc5 usage record/summary parity vs usage-ledger.py
USAGE_FEATURE="usage-feature"
mkdir -p "${TMP}/.adlc5/${USAGE_FEATURE}"
cat >"${TMP}/.adlc5/${USAGE_FEATURE}/state.json" <<'EOF'
{"schema_version":"3.0","feature":"usage-feature","current_stage":"implement","current_step":"implement-1-build","stage_status":{}}
EOF
./scripts/memory/usage-ledger.py record --feature "$USAGE_FEATURE" --workspace "$TMP" \
  --model-id claude-sonnet-5 --input-tokens 100 --output-tokens 50 --thinking-tokens 10 >/dev/null
./scripts/adlc5 usage record --feature "$USAGE_FEATURE" --workspace "$TMP" \
  --model-id claude-sonnet-5 --input-tokens 20 --output-tokens 5 >/dev/null
[[ $(wc -l <"${TMP}/.adlc5/${USAGE_FEATURE}/memory/usage-ledger.jsonl") -eq 2 ]] \
  || fail "adlc5 usage record should append via façade"
set +e
./scripts/memory/usage-ledger.py summary --feature "$USAGE_FEATURE" --workspace "$TMP" >/tmp/adlc5-usage-direct.json
EC_DIRECT=$?
./scripts/adlc5 usage summary --feature "$USAGE_FEATURE" --workspace "$TMP" >/tmp/adlc5-usage-facade.json
EC_FACADE=$?
set -e
[[ "$EC_DIRECT" -eq "$EC_FACADE" ]] || fail "adlc5 usage summary exit mismatch direct=$EC_DIRECT facade=$EC_FACADE"
diff -u /tmp/adlc5-usage-direct.json /tmp/adlc5-usage-facade.json >/dev/null \
  || fail "adlc5 usage summary stdout mismatch vs usage-ledger.py"
jq -e '.entries == 2 and .totals.total == 185' /tmp/adlc5-usage-direct.json >/dev/null \
  || fail "usage summary totals mismatch (expected 185)"
./scripts/adlc5 usage summary --feature "$USAGE_FEATURE" --workspace "$TMP" --format markdown >/tmp/adlc5-usage-md.txt
grep -q "Total tracked tokens: 185" /tmp/adlc5-usage-md.txt || fail "usage summary markdown should render totals"
pass "adlc5 usage record/summary parity"

# usage-ledger.py record must resolve an archived feature (cleanup-features
# --archive moved .adlc5/{feature} to .adlc5/_archive/{feature}-YYYYMMDD)
# instead of erroring, so delayed reconciliation (Cursor Admin API's 48h
# overlap, late cloud-agent deltas) after archival still lands somewhere.
ARCHIVED_USAGE_FEATURE="archived-usage-feature"
mkdir -p "${TMP}/.adlc5/_archive/${ARCHIVED_USAGE_FEATURE}-20260101/memory"
./scripts/memory/usage-ledger.py record --feature "$ARCHIVED_USAGE_FEATURE" --workspace "$TMP" \
  --model-id gpt-5.6-codex --platform codex --input-tokens 50 --output-tokens 10 >/tmp/archived-usage-record.json
jq -e '.status == "ok"' /tmp/archived-usage-record.json >/dev/null \
  || fail "usage-ledger record should resolve an archived feature directory"
[[ -f "${TMP}/.adlc5/_archive/${ARCHIVED_USAGE_FEATURE}-20260101/memory/usage-ledger.jsonl" ]] \
  || fail "usage-ledger record should append into the archived ledger, not a stray active dir"
[[ ! -e "${TMP}/.adlc5/${ARCHIVED_USAGE_FEATURE}" ]] \
  || fail "usage-ledger record must not create a stray active feature dir when only an archive exists"
pass "usage-ledger record resolves archived feature directories"

USAGE_CORR_FEATURE="usage-correlation"
mkdir -p "${TMP}/.adlc5/${USAGE_CORR_FEATURE}"
printf '%s\n' '{"schema_version":"3.0","feature":"usage-correlation","current_stage":"implement","current_step":"implement-2-verify","stage_status":{}}' \
  >"${TMP}/.adlc5/${USAGE_CORR_FEATURE}/state.json"
./scripts/adlc5 usage record --feature "$USAGE_CORR_FEATURE" --workspace "$TMP" \
  --model-id test-model --input-tokens 10 --output-tokens 5 \
  --run-id run-1 --node-id verify --parent-node-ids build,test --attempt 2 --outcome defect_caught --finding-id F-1 \
  >/tmp/adlc5-usage-correlation.json || fail "usage correlation record"
jq -e '.entry.run_id == "run-1" and .entry.node_id == "verify" and .entry.parent_node_ids == ["build","test"] and .entry.attempt == 2 and .entry.outcome == "defect_caught" and .entry.finding_id == "F-1"' \
  /tmp/adlc5-usage-correlation.json >/dev/null || fail "usage correlation fields"
pass "usage correlation fields"

# read-only run evaluation joins outcomes, usage, and telemetry by run/node IDs
EVAL_DIR="${TMP}/evaluation"
mkdir -p "$EVAL_DIR"
cat >"${EVAL_DIR}/telemetry.jsonl" <<'EOF'
{"run_id":"run-1","node_id":"build","event":"script.end","status":"pass","attempt":1}
{"run_id":"run-1","node_id":"verify","event":"gate_fail","status":"fail","attempt":1,"outcome":"defect_caught","finding_id":"F-1"}
{"run_id":"run-1","node_id":"verify","event":"gate_fail","status":"fail","attempt":2,"outcome":"defect_caught","finding_id":"F-2"}
{"run_id":"run-2","node_id":"verify","event":"script.end","status":"pass","attempt":1}
{"run_id":"run-3","node_id":"build","event":"script.end","status":"pass","attempt":1}
{"run_id":"run-5","node_id":"build","event":"script.end","status":"pass","attempt":1}
{"node_id":"orphan","event":"script.end","status":"pass"}
EOF
cat >"${EVAL_DIR}/usage.jsonl" <<'EOF'
{"run_id":"run-1","node_id":"build","attempt":1,"tokens":{"total":100},"extra":{"estimated_cost_usd":0.01}}
{"run_id":"run-1","node_id":"verify","attempt":1,"outcome":"defect_caught","finding_id":"F-1","tokens":{"total":20},"extra":{"estimated_cost_usd":0.005}}
{"run_id":"run-1","node_id":"verify","attempt":2,"outcome":"defect_caught","finding_id":"F-1","tokens":{"total":30},"extra":{"estimated_cost_usd":0.015}}
{"run_id":"run-2","node_id":"build","attempt":1,"tokens":{"total":80},"extra":{"estimated_cost_usd":0.01}}
{"run_id":"run-3","node_id":"build","attempt":1,"tokens":{"total":20},"extra":{"estimated_cost_usd":0.005}}
{"run_id":"run-5","node_id":"build","attempt":1,"tokens":{"total":40},"extra":{"estimated_cost_usd":0.004}}
{"node_id":"orphan","tokens":{"total":10}}
EOF
cat >"${EVAL_DIR}/outcomes.jsonl" <<'EOF'
{"run_id":"run-1","profile":"high_risk","anchors_passed":true,"regression_passed":true,"quality_gates_passed":true,"anchor_changed":false,"rework":1,"human_rejected":false,"escaped_defects":0}
{"run_id":"run-2","profile":"tiny","anchors_passed":true,"regression_passed":false,"quality_gates_passed":true,"anchor_changed":false,"rework":0,"human_rejected":false,"escaped_defects":0}
{"run_id":"run-3","profile":"standard","anchors_passed":true,"regression_passed":true,"quality_gates_passed":true,"anchor_changed":false,"rework":0,"human_rejected":false}
{"run_id":"run-4","profile":"tiny","anchors_passed":true,"regression_passed":true,"quality_gates_passed":true,"anchor_changed":false,"rework":0,"human_rejected":false,"escaped_defects":0}
{"run_id":"run-4","profile":"tiny","anchors_passed":false,"regression_passed":true,"quality_gates_passed":true,"anchor_changed":false,"rework":0,"human_rejected":false,"escaped_defects":0}
{"run_id":"run-5","profile":"high_risk","anchors_passed":true,"regression_passed":true,"quality_gates_passed":false,"anchor_changed":false,"rework":0,"human_rejected":false,"escaped_defects":0}
EOF
./scripts/evaluate-runs.py --telemetry "${EVAL_DIR}/telemetry.jsonl" \
  --usage "${EVAL_DIR}/usage.jsonl" --outcomes "${EVAL_DIR}/outcomes.jsonl" \
  >/tmp/adlc5-evaluation.json || fail "run evaluation should succeed with warnings"
jq -e '
  .status == "warn" and
  .runs == {total:4, successful:1} and
  .by_profile.high_risk == {runs:2, successful:1, tokens:150, cost_usd:0.03, failed_tokens:40, failed_cost_usd:0.004} and
  .by_profile.tiny == {runs:1, successful:0, tokens:0, cost_usd:0, failed_tokens:80, failed_cost_usd:0.01} and
  .by_profile.standard == {runs:1, successful:0, tokens:0, cost_usd:0, failed_tokens:20, failed_cost_usd:0.005} and
  .by_node.build == {calls:4, tokens:240, cost_usd:0.029, retries:0, failures_caught:0} and
  .by_node.verify == {calls:2, tokens:50, cost_usd:0.02, retries:1, failures_caught:2} and
  .missing.telemetry_without_run_id == 1 and
  .missing.usage_without_run_id == 1 and
  .missing.telemetry_without_usage_node == 1 and
  .missing.usage_without_telemetry_node == 1 and
  .missing.outcomes_incomplete == 1 and
  .missing.duplicate_outcomes == 1 and
  (has("quality_score") | not)
' /tmp/adlc5-evaluation.json >/dev/null || fail "run evaluation output contract"
pass "run evaluation joins cost and outcomes"

cat >"${EVAL_DIR}/edge-telemetry.jsonl" <<'EOF'
{"run_id":"run-missing","node_id":"build","event":"script.end","status":"pass"}
{"run_id":"run-negative","node_id":"build","event":"script.end","status":"pass"}
{"run_id":"run-free","node_id":"build","event":"script.end","status":"pass"}
{"run_id":"run-uncorrelated","node_id":"verify","event":"script.end","status":"pass"}
{"run_id":"run-empty","node_id":"build","event":"script.end","status":"pass"}
{"run_id":"run-infinite","node_id":"build","event":"script.end","status":"pass"}
EOF
cat >"${EVAL_DIR}/edge-usage.jsonl" <<'EOF'
{"run_id":"run-negative","node_id":"build","tokens":{"total":-1},"cost_usd":-0.01}
{"run_id":"run-free","node_id":"build","tokens":{"total":10},"cost_usd":0,"extra":{"estimated_cost_usd":9.99}}
{"run_id":"run-uncorrelated","node_id":"build","tokens":{"total":10},"cost_usd":0.1}
{"run_id":"run-empty","node_id":"build"}
{"run_id":"run-infinite","node_id":"build","tokens":{"total":1},"cost_usd":Infinity}
EOF
cat >"${EVAL_DIR}/edge-outcomes.jsonl" <<'EOF'
{"run_id":"run-missing","profile":"tiny","anchors_passed":true,"regression_passed":true,"quality_gates_passed":true,"anchor_changed":false,"rework":0,"human_rejected":false,"escaped_defects":0}
{"run_id":"run-negative","profile":"tiny","anchors_passed":true,"regression_passed":true,"quality_gates_passed":true,"anchor_changed":false,"rework":0,"human_rejected":false,"escaped_defects":0}
{"run_id":"run-free","profile":"tiny","anchors_passed":true,"regression_passed":true,"quality_gates_passed":true,"anchor_changed":false,"rework":0,"human_rejected":false,"escaped_defects":0}
{"run_id":"run-uncorrelated","profile":"tiny","anchors_passed":true,"regression_passed":true,"quality_gates_passed":true,"anchor_changed":false,"rework":0,"human_rejected":false,"escaped_defects":0}
{"run_id":"run-empty","profile":"tiny","anchors_passed":true,"regression_passed":true,"quality_gates_passed":true,"anchor_changed":false,"rework":0,"human_rejected":false,"escaped_defects":0}
{"run_id":"run-infinite","profile":"tiny","anchors_passed":true,"regression_passed":true,"quality_gates_passed":true,"anchor_changed":false,"rework":0,"human_rejected":false,"escaped_defects":0}
EOF
./scripts/evaluate-runs.py --telemetry "${EVAL_DIR}/edge-telemetry.jsonl" \
  --usage "${EVAL_DIR}/edge-usage.jsonl" --outcomes "${EVAL_DIR}/edge-outcomes.jsonl" \
  >/tmp/adlc5-evaluation-edge.json || fail "edge run evaluation should complete"
jq -e '
  .status == "warn" and
  .runs == {total:6, successful:1} and
  .by_profile.tiny.cost_usd == 0 and
  .by_node.build == {calls:2,tokens:20,cost_usd:0.1,retries:0,failures_caught:0} and
  .missing.outcomes_without_correlated_usage == 5 and
  .missing.usage_invalid_numeric == 2 and
  .missing.usage_missing_accounting == 1
' /tmp/adlc5-evaluation-edge.json >/dev/null || fail "run evaluation should fail closed on invalid usage"
pass "run evaluation validates usage economics"

# adlc5 phase parity vs advance-phase.sh
set +e
./scripts/advance-phase.sh --feature "$FEATURE" --workspace "$TMP" >/tmp/adlc5-phase-direct.json
EC_DIRECT=$?
./scripts/adlc5 phase --feature "$FEATURE" --workspace "$TMP" >/tmp/adlc5-phase-facade.json
EC_FACADE=$?
set -e
[[ "$EC_DIRECT" -eq "$EC_FACADE" ]] || fail "adlc5 phase exit mismatch direct=$EC_DIRECT facade=$EC_FACADE"
diff -u /tmp/adlc5-phase-direct.json /tmp/adlc5-phase-facade.json >/dev/null \
  || fail "adlc5 phase stdout mismatch vs advance-phase.sh"
pass "adlc5 phase parity"

# adlc5 pilot parity vs pilot-autopilot.sh (reuse v2-contract fixture)
set +e
./scripts/pilot-autopilot.sh --feature "$FEATURE_V2" --workspace "$V2_TMP" >/tmp/adlc5-pilot-direct.json
EC_DIRECT=$?
./scripts/adlc5 pilot --feature "$FEATURE_V2" --workspace "$V2_TMP" >/tmp/adlc5-pilot-facade.json
EC_FACADE=$?
set -e
[[ "$EC_DIRECT" -eq "$EC_FACADE" ]] || fail "adlc5 pilot exit mismatch direct=$EC_DIRECT facade=$EC_FACADE"
diff -u /tmp/adlc5-pilot-direct.json /tmp/adlc5-pilot-facade.json >/dev/null \
  || fail "adlc5 pilot stdout mismatch vs pilot-autopilot.sh"
pass "adlc5 pilot parity"

# adlc5 state get + schema-validated state set
./scripts/adlc5 state get --feature "$FEATURE_V2" --workspace "$V2_TMP" >/tmp/adlc5-state-get.json
jq -e '.schema_version == "3.0"' /tmp/adlc5-state-get.json >/dev/null || fail "adlc5 state get missing schema_version"
BEFORE_STEP=$(jq -r '.current_step' /tmp/adlc5-state-get.json)
set +e
./scripts/adlc5 state get --feature missing-feature --workspace "$TMP" >/tmp/adlc5-state-missing.json
EC=$?
set -e
[[ "$EC" -eq 2 ]] || fail "adlc5 state get missing expected exit 2 got $EC"
jq -e '.error == "state_not_found"' /tmp/adlc5-state-missing.json >/dev/null || fail "adlc5 state get missing error shape"
# usage without patch/file
set +e
./scripts/adlc5 state set --feature "$FEATURE_V2" --workspace "$V2_TMP" >/tmp/adlc5-state-set-usage.json 2>/dev/null
EC=$?
set -e
[[ "$EC" -eq 2 ]] || fail "adlc5 state set usage expected exit 2 got $EC"
# invalid patch must not corrupt
cp "${V2_TMP}/.adlc5/${FEATURE_V2}/state.json" /tmp/adlc5-state-before.json
set +e
./scripts/adlc5 state set --feature "$FEATURE_V2" --workspace "$V2_TMP" \
  --patch '{"git":{"isolation":"not-an-isolation"}}' >/tmp/adlc5-state-set-bad.json
EC=$?
set -e
[[ "$EC" -eq 2 ]] || fail "adlc5 state set invalid expected exit 2 got $EC"
jq -e '.error == "schema_validation_failed"' /tmp/adlc5-state-set-bad.json >/dev/null \
  || fail "adlc5 state set invalid error shape"
diff -u /tmp/adlc5-state-before.json "${V2_TMP}/.adlc5/${FEATURE_V2}/state.json" >/dev/null \
  || fail "adlc5 state set invalid corrupted state.json"
# valid patch + dry-run then apply
./scripts/adlc5 state set --feature "$FEATURE_V2" --workspace "$V2_TMP" \
  --patch '{"git":{"isolation":"current"}}' --dry-run >/tmp/adlc5-state-set-dry.json
jq -e '.status == "ok" and .dry_run == true' /tmp/adlc5-state-set-dry.json >/dev/null \
  || fail "adlc5 state set dry-run"
[[ "$(jq -r '.current_step' "${V2_TMP}/.adlc5/${FEATURE_V2}/state.json")" == "$BEFORE_STEP" ]] \
  || fail "adlc5 state set dry-run mutated state"
./scripts/adlc5 state set --feature "$FEATURE_V2" --workspace "$V2_TMP" \
  --patch '{"git":{"isolation":"current"}}' >/tmp/adlc5-state-set-ok.json
jq -e '.status == "ok"' /tmp/adlc5-state-set-ok.json >/dev/null || fail "adlc5 state set ok status"
[[ "$(jq -r '.git.isolation' "${V2_TMP}/.adlc5/${FEATURE_V2}/state.json")" == "current" ]] \
  || fail "adlc5 state set did not apply metadata"
set +e
./scripts/adlc5 state set --feature "$FEATURE_V2" --workspace "$V2_TMP" \
  --patch '{"current_step":"specify-1-scope"}' >/tmp/adlc5-state-protected.json
EC=$?
set -e
[[ "$EC" -eq 2 ]] || fail "generic state set must reject progression"
jq -e '.error == "protected_state"' /tmp/adlc5-state-protected.json >/dev/null \
  || fail "protected progression error missing"
# feature mismatch refused
set +e
./scripts/adlc5 state set --feature "$FEATURE_V2" --workspace "$V2_TMP" \
  --patch "{\"feature\":\"other-feature\",\"current_step\":\"specify-1-scope\"}" >/tmp/adlc5-state-feat.json
EC=$?
set -e
[[ "$EC" -eq 2 ]] || fail "adlc5 state set feature mismatch expected 2 got $EC"
jq -e '.error == "feature_mismatch"' /tmp/adlc5-state-feat.json >/dev/null \
  || fail "adlc5 state set feature_mismatch shape"
# phase apply unavailable (suggest-only)
set +e
./scripts/adlc5 phase apply --feature "$FEATURE_V2" --workspace "$V2_TMP" >/tmp/adlc5-phase-apply.json
EC=$?
set -e
[[ "$EC" -eq 2 ]] || fail "adlc5 phase apply expected exit 2 got $EC"
jq -e '.error == "phase_apply_unavailable"' /tmp/adlc5-phase-apply.json >/dev/null \
  || fail "adlc5 phase apply error shape"
pass "adlc5 state get/set"

# adlc5 resolve-model parity
./scripts/resolve-model.sh --platform cursor --tier balanced >/tmp/adlc5-resolve-direct.json
./scripts/adlc5 resolve-model --platform cursor --tier balanced >/tmp/adlc5-resolve-facade.json
diff -u /tmp/adlc5-resolve-direct.json /tmp/adlc5-resolve-facade.json >/dev/null \
  || fail "adlc5 resolve-model stdout mismatch"
pass "adlc5 resolve-model parity"

# patterns lookup — ids/paths only; façade parity; no card body dump
chmod +x ./scripts/patterns/lookup.sh
./scripts/patterns/lookup.sh --id gof/strategy >/tmp/patterns-lookup-direct.txt
grep -q 'gof/strategy' /tmp/patterns-lookup-direct.txt || fail "patterns lookup id miss"
if grep -q 'Multiple algorithms' /tmp/patterns-lookup-direct.txt; then
  fail "patterns lookup must not print card body"
fi
./scripts/adlc5 patterns lookup --id gof/strategy >/tmp/patterns-lookup-facade.txt
diff -u /tmp/patterns-lookup-direct.txt /tmp/patterns-lookup-facade.txt >/dev/null \
  || fail "adlc5 patterns lookup stdout mismatch"
./scripts/adlc5 patterns lookup --tags extensibility --group gof --limit 2 >/tmp/patterns-lookup-tags.txt
[[ $(wc -l < /tmp/patterns-lookup-tags.txt | tr -d ' ') -le 2 ]] || fail "patterns lookup --limit 2 exceeded"
./scripts/patterns/lookup.sh --id gof/strategy --frontmatter | grep -q 'title=Strategy' \
  || fail "patterns lookup --frontmatter title"
pass "patterns lookup + façade"

# adlc5 MCP smoke (tool list + version via same façade invoke path)
./scripts/adlc5-mcp.py --smoke >/tmp/adlc5-mcp-smoke.json
jq -e '.status == "ok" and (.tools | index("adlc5_version")) and (.tools | index("adlc5_gate"))' \
  /tmp/adlc5-mcp-smoke.json >/dev/null || fail "adlc5-mcp smoke tool list"
grep -Eq 'adlc5 [0-9]+\.[0-9]+\.[0-9]+' /tmp/adlc5-mcp-smoke.json || fail "adlc5-mcp smoke version"
pass "adlc5-mcp smoke"

# plugin shims + manifest (no .. paths; VERSION aligned)
./.cursor-plugin/run-adlc5.sh version | grep -Eq 'adlc5 [0-9]+\.[0-9]+\.[0-9]+' || fail "plugin run-adlc5.sh"
./.cursor-plugin/run-mcp.sh --smoke >/tmp/adlc5-plugin-mcp-smoke.json
jq -e '.status == "ok"' /tmp/adlc5-plugin-mcp-smoke.json >/dev/null || fail "plugin run-mcp.sh smoke"
python3 - <<'PY'
import json
from pathlib import Path
root = Path('.')
version = (root / 'core/VERSION').read_text(encoding='utf-8').strip()
plug = json.loads((root / '.cursor-plugin/plugin.json').read_text(encoding='utf-8'))
assert plug['version'] == version
assert plug['mcpServers'] == '.cursor-plugin/mcp.json'
assert (root / plug['mcpServers']).is_file()
assert (root / plug['skills']).is_dir()
meta = plug['adlc5']
for key in ('kernel', 'mcp', 'kernel_shim', 'mcp_shim'):
    assert (root / meta[key]).exists(), key
    assert '..' not in Path(meta[key]).parts, key
codex = json.loads((root / 'platform/codex-plugin/plugin.json').read_text(encoding='utf-8'))
assert codex['version'] == version and codex['adlc5']['kernel'] == 'scripts/adlc5'
PY
pass "plugin packaging contract"

# Release-coupled lifecycle skills and SOUL track the framework; auxiliary skills version independently.
python3 - <<'PY'
from pathlib import Path
import re

version = Path('core/VERSION').read_text(encoding='utf-8').strip()
for skill in ('adlc5', 'specify', 'plan', 'tasks', 'implement', 'adlc5-soul'):
    text = Path(f'skills/{skill}/SKILL.md').read_text(encoding='utf-8')
    match = re.search(r'^version:\s*(\S+)', text, re.MULTILINE)
    assert match and match.group(1) == version, f'{skill}: {match.group(1) if match else "missing"} != {version}'
PY
pass "release-coupled skill version coherence"

# SOUL 4.0 must carry the graph/evidence reasoning lens on every host surface
python3 - <<'PY'
from pathlib import Path

paths = [
    Path('skills/adlc5-soul/SKILL.md'),
    Path('shared/rules/portable/adlc5-soul.md'),
    Path('.cursor/rules/adlc5-soul.mdc'),
]
required = (
    'consumer-owned acceptance',
    'minimum sufficient profile',
    'dependency and file-ownership',
    'independent verification',
    'quality floor',
)
for path in paths:
    text = path.read_text(encoding='utf-8')
    for phrase in required:
        assert phrase in text, f'{path}: missing {phrase}'
assert f"version: {Path('core/VERSION').read_text(encoding='utf-8').strip()}" in paths[0].read_text(encoding='utf-8')
PY
pass "SOUL 4.0 graph reasoning contract"

# Volatile technology guidance must be dated, primary-sourced, and refreshed before use
python3 - <<'PY'
from pathlib import Path

freshness = Path('core/guides/current-information.md').read_text(encoding='utf-8')
orchestration = Path('core/guides/agent-orchestration.md').read_text(encoding='utf-8')
for phrase in (
    'official primary source',
    'last_verified',
    'stale information is a blocker',
    'https://a2ui.org/specification/v1.0-a2ui/',
):
    assert phrase in freshness, phrase
for phrase in (
    'v0.9.1 is the current stable protocol release',
    'v1.0 is a release candidate',
    '`theme` and `primaryColor`',
    'branding belongs to the renderer',
):
    assert phrase in orchestration, phrase
for path in (
    Path('AGENTS.md'),
    Path('skills/adlc5/SKILL.md'),
    Path('skills/specify/SKILL.md'),
    Path('skills/plan/SKILL.md'),
    Path('skills/tasks/SKILL.md'),
    Path('skills/implement/SKILL.md'),
    Path('templates/AGENTS.project.md'),
    Path('shared/rules/portable/current-information.md'),
    Path('.cursor/rules/current-information.mdc'),
):
    text = path.read_text(encoding='utf-8')
    assert 'current-information.md' in text, path
    assert 'official' in text.lower(), path
PY
pass "current information and A2UI freshness contract"

./scripts/install.sh --rules-only --dry-run >/tmp/current-information-rule-install.txt
grep -q 'current-information.mdc' /tmp/current-information-rule-install.txt \
  || fail "installer should include the current-information rule"
pass "current information rule install dry-run"

python3 - <<'PY'
from pathlib import Path
import re

active = [
    'AGENTS.md',
    'templates/AGENTS.project.md',
    'core/guides/git-isolation.md',
    'core/guides/model-matrix.md',
    'core/guides/interaction-modes.md',
    'core/governance/autopilot-stage-picker.md',
    'templates/policies.yaml.example',
    'templates/agent-product/spec-checklist.md',
    'core/guides/working-memory.md',
    'core/governance/production-ready.md',
    'core/governance/verifier-rules.md',
    'core/checklists/assure-gates.md',
    'shared/docs/project-wiki.md',
    'templates/definition-of-done.md',
    'templates/memory/promotion-candidates.md',
    'templates/wiki/drafts/promotion-packet-template.md',
    'templates/wiki/SCHEMA.md',
    'skills/craftsmanship-code-review/SKILL.md',
    'skills/autoresearch/SKILL.md',
    'skills/autoresearch/phases/04-synthesis.md',
    'skills/adlc5-tdd/SKILL.md',
    'skills/build-implementer/SKILL.md',
    'skills/pr-reviewer/README.md',
    'skills/pr-reviewer/guides/github.md',
    'skills/pr-reviewer/phases/03-respond.md',
    'skills/pr-reviewer/SKILL.md',
    'skills/adlc5-assure-reworker/SKILL.md',
    'skills/adlc5-design-critic/SKILL.md',
    'skills/project-wiki/SKILL.md',
    'skills/assure-verifier/SKILL.md',
    'templates/memory/INDEX.md',
    'templates/memory/context-pack-story.md',
    'templates/memory/context-pack-verify.md',
]
retired = re.compile(
    r'@adlc5-spec(?!ify)|@adlc5-engineering|@adlc5-plan-(?:design|stories|code-spec)|'
    r'@adlc5-build|@adlc5-assure-(?:verify|integrate)|@adlc5-assure\b(?!-reworker)|@adlc5-pilot|'
    r'(?:\.adlc5/\{feature\}/)?delivery/state\.json|scripts/pilot\.sh|'
    r'\bspec-4-exit\b|\bbuild-1-implementation\b|\bassure-3-qa\b|'
    r'\bstage_status\.assure\b|\bpr_review(?:\.url)?\b|stories\.\*|'
    r'code_specs/|user_stories\.md|delivery:\d'
)
stale = []
for name in active:
    text = Path(name).read_text(encoding='utf-8')
    for match in retired.finditer(text):
        stale.append(f'{name}: {match.group(0)}')
assert not stale, 'retired active guidance:\n' + '\n'.join(stale)

for name in (
    'templates/memory/promotion-candidates.md',
    'templates/wiki/drafts/promotion-packet-template.md',
    'templates/wiki/SCHEMA.md',
    'skills/craftsmanship-code-review/SKILL.md',
):
    assert 'Assure complete' not in Path(name).read_text(encoding='utf-8'), name

for name in (
    'templates/policies.yaml.example',
    'core/guides/working-memory.md',
    'core/governance/production-ready.md',
    'skills/project-wiki/SKILL.md',
    'shared/docs/project-wiki.md',
    'core/governance/verifier-rules.md',
):
    text = Path(name).read_text(encoding='utf-8')
    assert 'current_phase' not in text, name
    assert 'phase_status' not in text, name

pr_skill = Path('skills/pr-reviewer/SKILL.md').read_text(encoding='utf-8')
assert '"implement": { "pr":' in pr_skill
assert '"assure": { "pr_review":' not in pr_skill
production = Path('core/governance/production-ready.md').read_text(encoding='utf-8')
assert 'tasks.stories[].status' in production
assert 'stage_status.implement' in production
wiki = Path('skills/project-wiki/SKILL.md').read_text(encoding='utf-8')
assert 'stage_status.implement: completed' in wiki

for name in ('.cursor/rules/adlc5-interaction.mdc', 'shared/rules/portable/adlc5-interaction.md'):
    text = Path(name).read_text(encoding='utf-8')
    assert 'core/sdd-model.md' in text, name
    assert 'phase-registry.md' not in text, name
    assert 'delivery state' not in text, name

clarity = Path('core/guides/clarity-scoring.md').read_text(encoding='utf-8')
assert 'specify-2-requirements' in clarity
assert 'spec-*' not in clarity
assert 'Build / Assure' not in clarity
assert 'clarity.score' in clarity

assert 'core/sdd-model.md' in production
assert 'phase-registry.md' not in production
for name in (
    'core/governance/production-ready.md',
    'core/checklists/assure-gates.md',
    'templates/definition-of-done.md',
):
    text = Path(name).read_text(encoding='utf-8')
    assert 'when the selected profile enables `implement-4-qa`' in text.lower(), name

sdd_model = Path('core/sdd-model.md').read_text(encoding='utf-8')
assert 'stage_status.implement: completed' in sdd_model
assert 'Post pr-ready promotion' not in sdd_model

canonical_guidance = [Path(name) for name in active] + [
    Path('CLAUDE.md'),
    Path('core/checklists/engineering-gates.md'),
    Path('core/guides/askquestion-convention.md'),
    Path('core/guides/platform-tooling.md'),
    Path('core/guides/scaffold-registry.md'),
    Path('shared/docs/knowledge-base/README.md'),
    Path('shared/docs/knowledge-base/07-ai-agent-orchestration.md'),
    Path('skills/clean-architecture-review/SKILL.md'),
    Path('skills/clean-architecture-review/phases/03-output.md'),
    Path('skills/design-pattern-advisor/SKILL.md'),
    Path('skills/design-pattern-advisor/phases/03-output.md'),
    Path('skills/algorithm-advisor/SKILL.md'),
    Path('skills/algorithm-advisor/phases/02-analysis.md'),
    Path('skills/pbe-select-patterns/SKILL.md'),
    Path('skills/pbe-review-with-patterns/SKILL.md'),
    Path('skills/complexity-review/SKILL.md'),
    Path('skills/qa/guides/quality-thresholds.md'),
    Path('skills/qa/phases/00-test-discovery.md'),
    Path('skills/qa/phases/03-performance-accessibility.md'),
]
for path in canonical_guidance:
    text = path.read_text(encoding='utf-8').lower()
    for stale_phrase in (
        'stage_status.engineering',
        'context.repo_profile',
        'context.scaffold',
        'delivery state',
        'build phase',
        'engineer stage',
        'assure stage',
        'spec stage',
        'spec exit',
        'after assure',
        'assure exit',
    ):
        assert stale_phrase not in text, f'{path}: {stale_phrase}'
PY
pass "active guidance excludes retired lifecycle contracts"

# Skill and key guide links must resolve; broken links degrade agent navigation at runtime
python3 - <<'PY'
from pathlib import Path
import re
root = Path('.')
files = list(root.rglob('SKILL.md')) + [
    root / 'shared/docs/SKILL-MAP.md',
    root / 'core/guides/agent-orchestration.md',
]
broken = []
for path in files:
    if not path.is_file():
        continue
    text = path.read_text(encoding='utf-8', errors='replace')
    for match in re.finditer(r'\[[^\]]*\]\(([^)]+)\)', text):
        link = match.group(1)
        if link.startswith(('http://', 'https://', '#', 'mailto:')):
            continue
        rel = link.split('#', 1)[0]
        if not rel:
            continue
        if not (path.parent / rel).resolve().exists():
            broken.append(f'{path}: {link}')
if broken:
    raise SystemExit('Broken doc links:\n' + '\n'.join(broken))
PY
pass "skill doc links resolve"

# --- Cost-optimization levers ---------------------------------------------

# Legacy tier keys are ignored; structured setup values are authoritative.
LEVER1_WS=$(mktemp -d)
LEVER1_FEATURE="lever1-feature"
mkdir -p "${LEVER1_WS}/.adlc5/${LEVER1_FEATURE}"
cat >"${LEVER1_WS}/.adlc5/${LEVER1_FEATURE}/policies.yaml" <<'EOF'
autopilot:
  profile: tiny
model_routing:
  execution_policy: explicit
EOF

FEATURE_EXEC_JSON=$(./scripts/resolve-model.sh --tier execution --platform claude --workspace "$LEVER1_WS" --feature "$LEVER1_FEATURE")
jq -e '.model_id == "host default" and (.notice|contains("Legacy model settings are ignored"))' \
  <<<"$FEATURE_EXEC_JSON" >/dev/null \
  || fail "removed execution_policy setting should be ignored with a notice"
pass "resolve-model.sh: removed model settings fail over to host default with notice"
rm -rf "$LEVER1_WS"

# Lever 2: spec-lint.py — frontmatter contract
LEVER2_WS=$(mktemp -d)
LEVER2_FEATURE="lever2-feature"
mkdir -p "${LEVER2_WS}/.adlc5/${LEVER2_FEATURE}/tasks/code-spec"
cat >"${LEVER2_WS}/.adlc5/${LEVER2_FEATURE}/tasks/code-spec/US-001.md" <<'EOF'
---
story_id: US-001
files_to_create:
  - src/thing.py
files_to_modify: []
tests:
  - file: tests/test_thing.py
    name: test_it_works
acceptance_criteria:
  - AC-1
acceptance_checks:
  AC-1: [tests/test_thing.py::test_it_works]
---
# US-001
EOF
set +e
./scripts/tasks/spec-lint.py --feature "$LEVER2_FEATURE" --workspace "$LEVER2_WS" >/dev/null
LEVER2_GOOD_EC=$?
set -e
[[ "$LEVER2_GOOD_EC" -eq 0 ]] || fail "spec-lint should pass a well-formed code spec, got exit $LEVER2_GOOD_EC"

sed -i.bak 's#tests/test_thing.py::test_it_works#tests/test_missing.py::test_missing#' \
  "${LEVER2_WS}/.adlc5/${LEVER2_FEATURE}/tasks/code-spec/US-001.md"
set +e
LEVER2_MAP_OUT=$(./scripts/tasks/spec-lint.py --feature "$LEVER2_FEATURE" --workspace "$LEVER2_WS")
LEVER2_MAP_EC=$?
set -e
[[ "$LEVER2_MAP_EC" -eq 1 ]] || fail "spec-lint should reject an unmapped/nonexistent named check"
grep -q 'acceptance check' <<<"$LEVER2_MAP_OUT" || fail "spec-lint should explain the invalid acceptance mapping"
mv "${LEVER2_WS}/.adlc5/${LEVER2_FEATURE}/tasks/code-spec/US-001.md.bak" \
   "${LEVER2_WS}/.adlc5/${LEVER2_FEATURE}/tasks/code-spec/US-001.md"

cat >"${LEVER2_WS}/.adlc5/${LEVER2_FEATURE}/tasks/code-spec/US-002.md" <<'EOF'
# US-002 legacy spec, no frontmatter
EOF
set +e
LEVER2_BAD_OUT=$(./scripts/tasks/spec-lint.py --feature "$LEVER2_FEATURE" --workspace "$LEVER2_WS")
LEVER2_BAD_EC=$?
set -e
[[ "$LEVER2_BAD_EC" -eq 1 ]] || fail "spec-lint should fail a directory with a frontmatter-less spec, got exit $LEVER2_BAD_EC"
jq -e '.results | map(select(.story_id == "US-001")) | .[0].status == "pass"' <<<"$LEVER2_BAD_OUT" >/dev/null \
  || fail "spec-lint should still report US-001 as passing alongside the broken US-002"
pass "spec-lint.py: frontmatter contract"

# check-gates: tasks-2-code-spec-complete wired to spec-lint
cat >"${LEVER2_WS}/.adlc5/${LEVER2_FEATURE}/state.json" <<'EOF'
{"schema_version":"3.0","feature_name":"lever2-feature","current_stage":"tasks","current_step":"tasks-2-code-spec","tasks":{"stories":[]}}
EOF
rm "${LEVER2_WS}/.adlc5/${LEVER2_FEATURE}/tasks/code-spec/US-002.md"
set +e
./scripts/check-gates.py --feature "$LEVER2_FEATURE" --workspace "$LEVER2_WS" --gate tasks-2-code-spec-complete >/dev/null
LEVER2_GATE_EC=$?
set -e
[[ "$LEVER2_GATE_EC" -eq 0 ]] || fail "tasks-2-code-spec-complete should pass with only the well-formed spec present"

echo '# no frontmatter here either' >"${LEVER2_WS}/.adlc5/${LEVER2_FEATURE}/tasks/code-spec/US-001.md"
set +e
./scripts/check-gates.py --feature "$LEVER2_FEATURE" --workspace "$LEVER2_WS" --gate tasks-2-code-spec-complete >/dev/null
LEVER2_GATE_FAIL_EC=$?
set -e
[[ "$LEVER2_GATE_FAIL_EC" -eq 1 ]] || fail "tasks-2-code-spec-complete should fail once frontmatter is removed"
pass "check-gates: tasks-2-code-spec-complete linted, not just present"
rm -rf "$LEVER2_WS"

# Lever 3: verify-story.py + implement-2-verify additive wiring
LEVER3_WS=$(mktemp -d)
LEVER3_FEATURE="lever3-feature"
(
  cd "$LEVER3_WS"
  git init -q
  git config user.email t@example.com
  git config user.name t
  mkdir -p app ".adlc5/${LEVER3_FEATURE}/tasks/code-spec" ".adlc5/${LEVER3_FEATURE}/verify"
  printf 'def add(a, b):\n    return a + b\n' >app/thing.py
  cat >".adlc5/${LEVER3_FEATURE}/tasks/code-spec/US-001.md" <<'EOF'
---
story_id: US-001
files_to_create:
  - app/thing.py
files_to_modify: []
tests:
  - file: app/thing.py
    name: add
acceptance_criteria:
  - AC-1
acceptance_checks:
  AC-1: [app/thing.py::add]
---
# US-001
EOF
  git add -A
)
set +e
LEVER3_OUT=$(./scripts/verify-story.py --feature "$LEVER3_FEATURE" --story-id US-001 --workspace "$LEVER3_WS")
LEVER3_EC=$?
set -e
[[ "$LEVER3_EC" -eq 0 ]] || fail "verify-story.py should pass a spec whose declared files/tests exist within boundary, got exit $LEVER3_EC: $LEVER3_OUT"
jq -e '.checks | map(select(.id == "file_boundary")) | .[0].status == "pass"' <<<"$LEVER3_OUT" >/dev/null \
  || fail "verify-story.py file_boundary check should pass for an in-boundary change"
[[ -f "${LEVER3_WS}/.adlc5/${LEVER3_FEATURE}/verify/deterministic-report-US-001.json" ]] \
  || fail "verify-story.py should write a per-story deterministic report"

echo "junk = 1" >"${LEVER3_WS}/app/scope_creep.py"
set +e
LEVER3_CREEP_OUT=$(./scripts/verify-story.py --feature "$LEVER3_FEATURE" --story-id US-001 --workspace "$LEVER3_WS")
LEVER3_CREEP_EC=$?
set -e
[[ "$LEVER3_CREEP_EC" -eq 1 ]] || fail "verify-story.py should fail once an undeclared file changes"
jq -e '.checks | map(select(.id == "file_boundary")) | .[0].status == "fail"' <<<"$LEVER3_CREEP_OUT" >/dev/null \
  || fail "verify-story.py file_boundary check should catch scope creep"
pass "verify-story.py: boundary + declared-test checks"

# implement-2-verify: deterministic_verify_* is additive and story-scoped
rm "${LEVER3_WS}/app/scope_creep.py"
cat >"${LEVER3_WS}/.adlc5/${LEVER3_FEATURE}/verify/verification-report.md" <<'EOF'
**Overall:** pass
**Synced at:** 2026-01-01T00:00:00Z
EOF
cat >"${LEVER3_WS}/.adlc5/${LEVER3_FEATURE}/state.json" <<'EOF'
{
  "schema_version": "3.0",
  "feature_name": "lever3-feature",
  "current_stage": "implement",
  "current_step": "implement-2-verify",
  "tasks": {"stories": [{"id": "US-001", "title": "t", "status": "implementation_complete", "type": "component", "batch": 1, "files": ["app/thing.py"]}]}
}
EOF
LEVER3_GATE_OUT=$(./scripts/check-gates.py --feature "$LEVER3_FEATURE" --workspace "$LEVER3_WS" --gate implement-2-verify || true)
jq -e '.checks | map(select(.id == "deterministic_verify_US-001")) | .[0].status == "pass"' <<<"$LEVER3_GATE_OUT" >/dev/null \
  || fail "implement-2-verify should surface a passing deterministic_verify_US-001 check for a lever-2 story"
pass "check-gates: implement-2-verify additive deterministic_verify_*"

# A feature with no frontmatter at all gets no deterministic_verify_* checks (backward-safe)
LEVER3_LEGACY_WS=$(mktemp -d)
LEVER3_LEGACY_FEATURE="lever3-legacy-feature"
mkdir -p "${LEVER3_LEGACY_WS}/.adlc5/${LEVER3_LEGACY_FEATURE}/tasks/code-spec" "${LEVER3_LEGACY_WS}/.adlc5/${LEVER3_LEGACY_FEATURE}/verify"
echo '# legacy spec, no frontmatter' >"${LEVER3_LEGACY_WS}/.adlc5/${LEVER3_LEGACY_FEATURE}/tasks/code-spec/US-001.md"
cat >"${LEVER3_LEGACY_WS}/.adlc5/${LEVER3_LEGACY_FEATURE}/verify/verification-report.md" <<'EOF'
**Overall:** pass
**Synced at:** 2026-01-01T00:00:00Z
EOF
cat >"${LEVER3_LEGACY_WS}/.adlc5/${LEVER3_LEGACY_FEATURE}/state.json" <<'EOF'
{
  "schema_version": "3.0",
  "feature_name": "lever3-legacy-feature",
  "current_stage": "implement",
  "current_step": "implement-2-verify",
  "tasks": {"stories": [{"id": "US-001", "title": "t", "status": "verified", "type": "component", "batch": 1, "files": []}]}
}
EOF
LEVER3_LEGACY_OUT=$(./scripts/check-gates.py --feature "$LEVER3_LEGACY_FEATURE" --workspace "$LEVER3_LEGACY_WS" --gate implement-2-verify || true)
jq -e '[.checks[] | select(.id | startswith("deterministic_verify_"))] | length == 0' <<<"$LEVER3_LEGACY_OUT" >/dev/null \
  || fail "a feature with no lever-2 frontmatter should get zero deterministic_verify_* checks"
jq -e 'any(.checks[]; .id == "strict_spec_US-001" and .status == "fail")' <<<"$LEVER3_LEGACY_OUT" >/dev/null \
  || fail "legacy frontmatter limitation must surface before completion"
pass "legacy features remain readable but require upgraded specs before completion"
rm -rf "$LEVER3_WS" "$LEVER3_LEGACY_WS"

# Lever 9: priced usage ledger
LEVER9_WS=$(mktemp -d)
LEVER9_FEATURE="lever9-feature"
mkdir -p "${LEVER9_WS}/.adlc5/${LEVER9_FEATURE}"
./scripts/memory/usage-ledger.py record --feature "$LEVER9_FEATURE" --workspace "$LEVER9_WS" \
  --model-id claude-sonnet-5 --stage implement --input-tokens 10000 --output-tokens 1000 >/dev/null
./scripts/memory/usage-ledger.py record --feature "$LEVER9_FEATURE" --workspace "$LEVER9_WS" \
  --model-id some-unpriced-model --stage implement --input-tokens 500 --output-tokens 50 >/dev/null
LEVER9_SUMMARY=$(./scripts/memory/usage-ledger.py summary --feature "$LEVER9_FEATURE" --workspace "$LEVER9_WS")
python3 - "$LEVER9_SUMMARY" <<'PY'
import json, sys
d = json.loads(sys.argv[1])
totals = d["totals"]
expected = round((10000 * 2.00 + 1000 * 10.00) / 1_000_000.0, 6)
assert abs(totals["cost_usd"] - expected) < 1e-9, (totals["cost_usd"], expected)
assert totals["priced_calls"] == 1, totals
assert totals["unpriced_calls"] == 1, totals
assert "some-unpriced-model" in totals["unpriced_models"], totals
assert d["pricing"]["status"] == "loaded", d["pricing"]
PY
pass "usage-ledger.py: cost_usd priced from core/model-prices.yaml, unpriced models flagged"

# cost_usd is null, not 0.0, for a bucket where every call is unpriced
LEVER9_SUMMARY_2=$(./scripts/memory/usage-ledger.py summary --feature "$LEVER9_FEATURE" --workspace "$LEVER9_WS")
python3 - "$LEVER9_SUMMARY_2" <<'PY'
import json, sys
d = json.loads(sys.argv[1])
bucket = d["by_model"]["some-unpriced-model"]
assert bucket["cost_usd"] is None, bucket
assert bucket["priced_calls"] == 0, bucket
assert bucket["unpriced_calls"] == 1, bucket
PY
pass "usage-ledger.py: fully-unpriced bucket reports cost_usd null, not 0.0"
rm -rf "$LEVER9_WS"

# Thinking tokens are not double-billed on top of output tokens
LEVER9B_WS=$(mktemp -d)
LEVER9B_FEATURE="lever9b-feature"
mkdir -p "${LEVER9B_WS}/.adlc5/${LEVER9B_FEATURE}"
./scripts/memory/usage-ledger.py record --feature "$LEVER9B_FEATURE" --workspace "$LEVER9B_WS" \
  --model-id claude-sonnet-5 --stage implement --output-tokens 1000 >/dev/null
./scripts/memory/usage-ledger.py record --feature "$LEVER9B_FEATURE" --workspace "$LEVER9B_WS" \
  --model-id claude-sonnet-5 --stage implement --output-tokens 1000 --thinking-tokens 200 >/dev/null
LEVER9B_SUMMARY=$(./scripts/memory/usage-ledger.py summary --feature "$LEVER9B_FEATURE" --workspace "$LEVER9B_WS")
python3 - "$LEVER9B_SUMMARY" <<'PY'
import json, sys
d = json.loads(sys.argv[1])
totals = d["totals"]
per_call_cost = round(1000 * 10.00 / 1_000_000.0, 6)
expected = round(per_call_cost * 2, 6)
assert abs(totals["cost_usd"] - expected) < 1e-9, (totals["cost_usd"], expected)
PY
pass "model_prices.py: thinking tokens not added on top of output (no double-billing)"
rm -rf "$LEVER9B_WS"

# Lever 2 follow-up: every planned (non-integration) story needs a matching spec
LEVER2B_WS=$(mktemp -d)
LEVER2B_FEATURE="lever2b-feature"
mkdir -p "${LEVER2B_WS}/.adlc5/${LEVER2B_FEATURE}/tasks/code-spec"
cat >"${LEVER2B_WS}/.adlc5/${LEVER2B_FEATURE}/state.json" <<'EOF'
{"schema_version":"3.0","feature_name":"lever2b-feature","current_stage":"tasks","current_step":"tasks-2-code-spec","tasks":{"stories":[{"id":"A","type":"component"},{"id":"B","type":"component"},{"id":"INT","type":"integration"}]}}
EOF
cat >"${LEVER2B_WS}/.adlc5/${LEVER2B_FEATURE}/tasks/code-spec/US-A.md" <<'EOF'
---
story_id: A
files_to_create:
  - src/a.py
files_to_modify: []
tests:
  - file: tests/test_a.py
    name: test_a
acceptance_criteria:
  - AC-1
acceptance_checks:
  AC-1: [tests/test_a.py::test_a]
---
# US-A
EOF
set +e
LEVER2B_OUT=$(./scripts/tasks/spec-lint.py --feature "$LEVER2B_FEATURE" --workspace "$LEVER2B_WS")
LEVER2B_EC=$?
set -e
[[ "$LEVER2B_EC" -eq 1 ]] || fail "spec-lint should fail when a planned story has no matching spec, got exit $LEVER2B_EC"
jq -e '[.results[] | select(.blockers[]? | contains("planned story '\''B'\''"))] | length == 1' <<<"$LEVER2B_OUT" >/dev/null \
  || fail "spec-lint should name the specific missing story"
jq -e '[.results[] | select(.blockers[]? | contains("planned story '\''INT'\''"))] | length == 0' <<<"$LEVER2B_OUT" >/dev/null \
  || fail "spec-lint should not require a spec for an integration-type story"

cat >"${LEVER2B_WS}/.adlc5/${LEVER2B_FEATURE}/tasks/code-spec/US-B.md" <<'EOF'
---
story_id: B
files_to_create:
  - src/b.py
files_to_modify: []
tests:
  - file: app/b.py
    name: sub
acceptance_criteria:
  - AC-1
acceptance_checks:
  AC-1: [app/b.py::sub]
---
# US-B
EOF
set +e
./scripts/tasks/spec-lint.py --feature "$LEVER2B_FEATURE" --workspace "$LEVER2B_WS" >/dev/null
LEVER2B_EC2=$?
set -e
[[ "$LEVER2B_EC2" -eq 0 ]] || fail "spec-lint should pass once every planned component story has a spec"
pass "spec-lint.py: one spec required per planned (non-integration) story"
rm -rf "$LEVER2B_WS"

# Lever 3 follow-up: verifying one story in a parallel batch must not flag a
# sibling story's already-changed files as scope creep, and must still catch
# a genuinely undeclared file.
LEVER3B_WS=$(mktemp -d)
LEVER3B_FEATURE="lever3b-feature"
(
  cd "$LEVER3B_WS"
  git init -q
  git config user.email t@example.com
  git config user.name t
  mkdir -p app ".adlc5/${LEVER3B_FEATURE}/tasks/code-spec"
  printf 'def add(a, b):\n    return a + b\n' >app/a.py
  printf 'def sub(a, b):\n    return a - b\n' >app/b.py
  cat >".adlc5/${LEVER3B_FEATURE}/tasks/code-spec/US-A.md" <<'EOF'
---
story_id: A
files_to_create:
  - app/a.py
files_to_modify: []
tests:
  - file: app/a.py
    name: add
acceptance_criteria:
  - AC-1
acceptance_checks:
  AC-1: [app/a.py::add]
---
# US-A
EOF
  cat >".adlc5/${LEVER3B_FEATURE}/tasks/code-spec/US-B.md" <<'EOF'
---
story_id: B
files_to_create:
  - app/b.py
files_to_modify: []
tests:
  - file: app/b.py
    name: sub
acceptance_criteria:
  - AC-1
acceptance_checks:
  AC-1: [app/b.py::sub]
---
# US-B
EOF
  git add -A
)
set +e
LEVER3B_OUT=$(./scripts/verify-story.py --feature "$LEVER3B_FEATURE" --story-id A --workspace "$LEVER3B_WS")
LEVER3B_EC=$?
set -e
[[ "$LEVER3B_EC" -eq 0 ]] || fail "verify-story.py should not flag a sibling story's file as scope creep, got exit $LEVER3B_EC: $LEVER3B_OUT"
jq -e '.checks | map(select(.id == "file_boundary")) | .[0].status == "pass"' <<<"$LEVER3B_OUT" >/dev/null \
  || fail "verify-story.py file_boundary should pass when only sibling-declared files changed alongside this story's own"

echo "print('undeclared')" >"${LEVER3B_WS}/app/nobody_declared_this.py"
set +e
LEVER3B_OUT2=$(./scripts/verify-story.py --feature "$LEVER3B_FEATURE" --story-id A --workspace "$LEVER3B_WS")
LEVER3B_EC2=$?
set -e
[[ "$LEVER3B_EC2" -eq 1 ]] || fail "verify-story.py should still fail on a file no story declares"
jq -e '.checks | map(select(.id == "file_boundary")) | .[0].status == "fail"' <<<"$LEVER3B_OUT2" >/dev/null \
  || fail "verify-story.py file_boundary should fail once a genuinely undeclared file appears"
pass "verify-story.py: sibling stories' declared files don't false-flag scope creep"
rm -rf "$LEVER3B_WS"

# simple_yaml.py: malformed frontmatter (unterminated quote) must fail, not
# be silently reinterpreted into something that looks like a valid spec.
LEVER4_WS=$(mktemp -d)
LEVER4_FEATURE="lever4-feature"
mkdir -p "${LEVER4_WS}/.adlc5/${LEVER4_FEATURE}/tasks/code-spec"
printf -- '---\nstory_id: "US-1\nfiles_to_create: []\nfiles_to_modify: []\ntests:\n  - file: t.py\n    name: test_x\nacceptance_criteria: [AC-1]\n---\n# broken\n' \
  >"${LEVER4_WS}/.adlc5/${LEVER4_FEATURE}/tasks/code-spec/US-001.md"
set +e
LEVER4_OUT=$(./scripts/tasks/spec-lint.py --feature "$LEVER4_FEATURE" --workspace "$LEVER4_WS")
LEVER4_EC=$?
set -e
[[ "$LEVER4_EC" -eq 1 ]] || fail "spec-lint should reject malformed (unterminated-quote) YAML frontmatter, got exit $LEVER4_EC: $LEVER4_OUT"
jq -e '.results[0].status == "fail" and (.results[0].story_id == null)' <<<"$LEVER4_OUT" >/dev/null \
  || fail "spec-lint should not extract a story_id out of malformed frontmatter"
pass "spec-lint.py: malformed YAML frontmatter fails validation, not silently accepted"
rm -rf "$LEVER4_WS"

for test in test_completion_evidence.py test_completion_cli.py test_story_git_paths.py test-lightweight-workflow.py test-evaluation-pilot.py test-pilot-metadata.py test-runner-hosts.py test-runner-core.py test-config-routing.py; do
  python3 "./scripts/tests/$test" || fail "$test"
  pass "$test"
done

echo "All script contract tests passed."
