---
name: performance-accessibility
description: Phase 3 - Performance & Accessibility (Optional). Runs load tests against NFR targets, WCAG accessibility audits, and bundle analysis for frontend features. Produces performance-accessibility-report.md.
---

## Purpose

Validate that the application meets its performance SLAs and accessibility standards before deployment. This phase only runs when `context.is_ui_facing` is `true` OR `context.has_performance_targets` is `true`. If neither flag is set, the phase is skipped and `state.json` is updated to reflect that, allowing the pipeline to advance directly to Phase 4.

## Output

`performance-accessibility-report.md` — contains:
- Performance results vs. NFR targets (table with pass/fail per metric)
- WCAG 2.1 AA violations categorized by impact
- Bundle size analysis with optimization opportunities
- Generated load test scripts for staging/CI reuse

## Prerequisites

- Phase 2 (Quality Gate) complete — `quality-report.md` exists
- Application must be locally runnable for dynamic tests; if not, scripts are generated for later staging execution
- Performance targets from PRT NFRs or Plan operations design

## Phase 3 Process

---

### Step 1: Confirm Scope

Read `state.json` and check the context flags:

| Flag | Value | Action |
|---|---|---|
| `context.is_ui_facing` | false | Skip accessibility + bundle analysis |
| `context.has_performance_targets` | false | Skip load tests |
| Both false | — | Skip entire phase — set `performance_accessibility: "skipped"`, advance to Phase 4 |
| `context.is_ui_facing` | true | Run accessibility audit + bundle analysis |
| `context.has_performance_targets` | true | Run load tests |
| Both true | — | Run all three sub-phases |

When skipping, update `state.json`:
```json
{ "phase_status": { "performance_accessibility": "skipped" } }
```

Then notify the user:
> "Phase 3 skipped — not a UI-facing feature and no performance targets defined. Advancing to Phase 4: Compliance."

**Extract performance targets** from `.prt/{feature}/prt.md` NFRs section. Look for:
- p95 response time (e.g., `< 200ms`)
- Throughput (e.g., `1000 RPS`)
- Error rate (e.g., `< 0.1%`)
- Concurrent users (e.g., `500 simultaneous`)

If not found in PRT, check `.adlc5/{feature}/design/1c-operations.md` for a performance section. If targets are still not found, ask the user to confirm them before proceeding — do not assume defaults for performance targets, as they are highly system-specific.

---

### Step 2: Load Test Generation

*Applies when `has_performance_targets: true`.*

Extract user story scenarios from `.adlc5/{feature}/user_stories.md` and map them to load test scenarios. The goal is to simulate realistic traffic patterns, not just hammer a single endpoint.

**Four standard scenario types:**

| Scenario | Description | When to Run |
|---|---|---|
| Peak load | Sustained traffic at target concurrency for 5 minutes | Always |
| Spike | Sudden 10× increase over 30 seconds | When spike tolerance is an NFR |
| Soak | Sustained load for 10–30 minutes | When memory leak detection is an NFR |
| Ramp-up | Gradual increase from 0 to target over 2 minutes | Baseline profiling |

Generate a k6 load test script and write it to `.qa/{feature}/load-test.js`:

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

// Replace placeholders with resolved values from PRT NFRs
const TARGET_CONCURRENT_USERS = __ENV.CONCURRENT_USERS || 100;
const TARGET_P95_MS = __ENV.P95_MS || 200;
const TARGET_ERROR_RATE = __ENV.ERROR_RATE || 0.001;
const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000';

export const options = {
  scenarios: {
    peak_load: {
      executor: 'constant-vus',
      vus: TARGET_CONCURRENT_USERS,
      duration: '5m',
    },
    spike: {
      executor: 'ramping-vus',
      startTime: '6m',
      stages: [
        { duration: '30s', target: TARGET_CONCURRENT_USERS * 10 },
        { duration: '1m', target: TARGET_CONCURRENT_USERS * 10 },
        { duration: '30s', target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_duration: [`p(95)<${TARGET_P95_MS}`],
    http_req_failed: [`rate<${TARGET_ERROR_RATE}`],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}/api/endpoint`);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time OK': (r) => r.timings.duration < TARGET_P95_MS,
  });
  sleep(1);
}
```

For Python projects, also generate a Locust script at `.qa/{feature}/locustfile.py`:

```python
from locust import HttpUser, task, between

class FeatureUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def main_flow(self):
        self.client.get("/api/endpoint")

    @task(1)
    def secondary_flow(self):
        self.client.get("/api/other-endpoint")
```

Document the manual execution steps in the report for use in staging if the app is not locally runnable.

---

### Step 3: Run Load Tests

*Applies when `has_performance_targets: true` AND the application is locally runnable.*

First check if the app can be started:
```bash
# Check if a dev server port is already listening
lsof -i :PORT 2>/dev/null | grep LISTEN
```

If running, proceed. If not, attempt to start it using the detected stack (`npm run dev`, `uvicorn src.main:app`, etc.). If startup fails or requires external dependencies (databases, external APIs), generate the scripts for staging and note the limitation in the report — do not block on this.

Run the load test:
```bash
k6 run .qa/{feature}/load-test.js --out json=.qa/{feature}/k6-results.json
```

Parse `k6-results.json` and compare against targets:

| Metric | Target | Actual | Status |
|---|---|---|---|
| p95 response time | < 200ms | 187ms | PASS |
| p99 response time | < 500ms | 412ms | PASS |
| Throughput | 1000 RPS | 823 RPS | FAIL |
| Error rate | < 0.1% | 0.05% | PASS |
| Max concurrent users sustained | 500 | 500 | PASS |

For any missed targets, identify the likely bottleneck:
- **High p95/p99 latency:** Check for N+1 database queries, missing indexes, or synchronous blocking calls in hot paths
- **Low throughput:** Check for connection pool exhaustion, single-threaded event loop blocking, or insufficient horizontal scaling configuration
- **High error rate:** Check for timeouts, circuit breaker trips, or resource exhaustion (file handles, memory)

Include a bottleneck analysis section in the report with specific file/function references where possible.

---

### Step 4: Accessibility Audit

*Applies when `is_ui_facing: true`.*

**If the app has a running dev server:**

```bash
# axe-core CLI scan
npx axe http://localhost:PORT --reporter=json > .qa/{feature}/a11y-results.json

# Lighthouse full audit
npx lighthouse http://localhost:PORT \
  --output=json \
  --output-path=.qa/{feature}/lighthouse-report.json \
  --chrome-flags="--headless"
```

**If the app has component files but no running server, use jest-axe:**

```javascript
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);

test('component meets WCAG 2.1 AA', async () => {
  const { container } = render(<MyComponent />);
  const results = await axe(container, {
    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
  });
  expect(results).toHaveNoViolations();
});
```

Apply the full WCAG 2.1 AA checklist across all four principles:

**Perceivable:**
- All `<img>` elements have non-empty `alt` attributes
- Videos have captions or transcripts
- Color contrast ratio ≥ 4.5:1 for normal text, ≥ 3:1 for large text (18pt+ or 14pt+ bold)
- Information is not conveyed by color alone (icons, patterns, or text supplement color coding)

**Operable:**
- All interactive elements are reachable and activatable via keyboard only
- No keyboard traps (focus cannot be moved away from a component using only keyboard)
- Skip navigation links present for repetitive content
- All interactive elements have visible focus indicators
- No content flashes more than 3 times per second

**Understandable:**
- `<html lang>` attribute set correctly
- Navigation is consistent across pages
- Form errors are identified in text, not just color; error messages suggest how to fix
- Labels associated with all form inputs (`<label for>` or `aria-label`)

**Robust:**
- Valid HTML (no duplicate IDs, properly nested elements)
- ARIA roles and properties used correctly — no `role` values that conflict with the element's native semantics
- Status messages use `aria-live` regions so screen readers announce them

Categorize violations by impact:

| ID | Impact | Description | Element | WCAG Criterion |
|---|---|---|---|---|
| `color-contrast` | Critical | Text contrast ratio 2.1:1 (required 4.5:1) | `<p class="muted">` | 1.4.3 |
| `image-alt` | Serious | Image missing alt attribute | `<img src="logo.png">` | 1.1.1 |
| `label` | Serious | Form input has no associated label | `<input type="email">` | 1.3.1 |
| `focus-visible` | Moderate | Button has no visible focus indicator | `<button class="btn-ghost">` | 2.4.7 |

Critical and serious violations are soft-blocking (require user acceptance in Phase 4). Moderate and minor are non-blocking recommendations.

---

### Step 5: Bundle Analysis

*Applies when a frontend build system is detected (`package.json` with a build script AND presence of `webpack.config.js`, `vite.config.*`, or `next.config.*`).*

**Webpack:**
```bash
npx webpack --profile --json > stats.json
npx webpack-bundle-analyzer stats.json --mode=static \
  --report=.qa/{feature}/bundle-report.html
```

**Next.js:**
```bash
ANALYZE=true npm run build
```

**Vite:**
```bash
npx vite-bundle-visualizer --outDir=.qa/{feature}/bundle-report
```

Report the following metrics:

| Metric | Value | Target | Status |
|---|---|---|---|
| Total initial bundle (gzipped) | 312 KB | < 250 KB | FAIL |
| Largest single chunk | 180 KB | < 100 KB | FAIL |
| Number of chunks | 8 | — | Info |
| Duplicate packages | 2 | 0 | WARN |
| Unused exports ratio | 34% | < 10% | WARN |

**Common optimization opportunities to check:**
- Is `moment.js` or `lodash` imported in full? Suggest `date-fns` or `lodash-es` with tree-shaking
- Is the same package bundled in multiple chunks? Suggests a missing `SplitChunksPlugin` configuration
- Are large vendor libraries (charting, PDF rendering) loaded eagerly? Suggest dynamic `import()` for code splitting
- Are source maps included in the production bundle?

---

### Step 6: Produce performance-accessibility-report.md

Compile all findings into `.qa/{feature}/performance-accessibility-report.md`. The report structure:

1. **Executive Summary** — overall pass/fail verdict with counts
2. **Performance Results** — targets vs. actuals table, bottleneck analysis if targets missed
3. **Load Test Scripts** — links to generated k6/Locust scripts for reuse
4. **Accessibility Violations** — full table sorted by impact (critical first)
5. **Bundle Analysis** — size table, top 5 largest chunks, optimization recommendations
6. **Recommendations** — prioritized list of improvements

Update `state.json`:
```json
{
  "phase_status": { "performance_accessibility": "completed" },
  "results": {
    "performance": {
      "targets_met": false,
      "missed_targets": ["throughput"],
      "p95_ms": 187,
      "throughput_rps": 823
    },
    "accessibility": {
      "wcag_violations": {
        "critical": 1,
        "serious": 2,
        "moderate": 3,
        "minor": 1
      }
    },
    "bundle": {
      "initial_bundle_kb_gzipped": 312,
      "target_kb": 250,
      "meets_target": false
    }
  }
}
```

---

### Step 7: User Confirmation Gate

Present findings and ask how to proceed.

**All targets met AND no critical/serious accessibility violations:**
> "Phase 3 complete. Performance targets: all met. Accessibility: 0 critical, 0 serious violations. Bundle size: within target.
> Ready to proceed to Phase 4: Compliance?"

**Performance targets missed:**
> "Phase 3 complete with issues.
>
> Missed performance targets:
> - Throughput: 823 RPS vs. 1000 RPS target (bottleneck: connection pool — see load-test analysis)
>
> Options:
> 1. Fix the bottleneck and re-run Phase 3
> 2. Accept risk and proceed — findings will be logged in the clearance document
>
> How would you like to proceed?"

**Critical accessibility violations found:**
> "Phase 3 complete with blocking accessibility issues.
>
> Critical WCAG violations: 1 (color-contrast on primary text)
> Serious WCAG violations: 2 (missing labels on email input, image missing alt)
>
> These must be fixed before deployment to a public audience. Options:
> 1. Fix violations and re-run Phase 3
> 2. Accept risk with documented exceptions — requires explicit acknowledgment in Phase 4
>
> How would you like to proceed?"

Do not advance to Phase 4 until the user confirms. Record the decision in `state.json` as `phase_status.performance_accessibility_confirmed: true`.
