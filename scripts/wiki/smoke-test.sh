#!/usr/bin/env bash
# Smoke test for project wiki scripts. Run from adlc5 repo or any path.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADLC5_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TEST_ROOT="$(mktemp -d)"
export ADLC5_ROOT TEST_ROOT

cleanup() { rm -rf "$TEST_ROOT"; }
trap cleanup EXIT

cd "$TEST_ROOT"
git init -q
git config user.email "wiki-smoke@test"
git config user.name "wiki-smoke"
git commit --allow-empty -m "init" -q

mkdir -p src/api .adlc5/demo-feature/memory src/auth
echo 'export const x = 1;' > src/api/index.ts
for i in $(seq 1 25); do echo "line $i"; done > src/auth/middleware.ts
echo '{"name":"demo"}' > package.json

echo "== init =="
"${SCRIPT_DIR}/init-wiki.sh" --workspace .

echo "== ingest =="
"${SCRIPT_DIR}/ingest-repo.sh" --workspace .
[[ -d wiki/drafts ]] || { echo "FAIL: no drafts"; exit 1; }

echo "== validate =="
"${SCRIPT_DIR}/validate-claim.sh" --workspace . --evidence "src/api/index.ts:1-1"

echo "== lint =="
"${SCRIPT_DIR}/lint.sh" --workspace .

cat > .adlc5/demo-feature/memory/promotion-candidates.md <<'EOF'
# Promotion candidates — demo-feature

### auth-jwt

**Claim:** JWT bearer tokens.
**Target:** wiki/entities/auth-service.md
**Evidence:** `src/auth/middleware.ts:10-20`
EOF
echo '{"schema_version":"3.0","stage_status":{"implement":"completed"}}' > .adlc5/demo-feature/state.json

echo "== promote-prepare =="
"${SCRIPT_DIR}/promote-prepare.sh" --feature demo-feature --workspace .
[[ -f wiki/drafts/promote-demo-feature/review-questions.json ]] || { echo "FAIL: no review-questions.json"; exit 1; }
python3 -c "import json; n=len(json.load(open('wiki/drafts/promote-demo-feature/review-questions.json'))['questions']); assert n>=1, f'expected questions, got {n}'"

echo "== promote-apply =="
cat > wiki/drafts/promote-demo-feature/approved.json <<'EOF'
{"feature":"demo-feature","approved_by":"user","candidates":[{"id":"auth-jwt","action":"promote_entity","target":"wiki/entities/auth-service.md"}]}
EOF
"${SCRIPT_DIR}/promote-apply.sh" --feature demo-feature --workspace .
grep -q auth-jwt wiki/entities/auth-service.md
grep -q auth-service wiki/index.md

echo "PASS: project wiki smoke test"
