# ADLC5 benchmarks — proving efficacy

Benchmarks that support marketing claims. Each must produce a reproducible
artifact committed to `docs/benchmarks/` (results, not anecdotes).

## Suites

1. **Six-case consumer fixture** (existing): `dogfood/consumer/regression.py` +
   `scripts/evaluation/run-case.py`. Tracks: acceptance pass, escaped defects,
   rework count, token/cost, wall-clock. Runs per host × model tier.
2. **Brownfield change task**: apply a bounded feature to a real OSS repo with
   hidden acceptance tests; measure correctness, regression introduced,
   context tokens consumed, time.
3. **Greenfield scaffold**: from empty repo to working feature with tests;
   measure build success, test pass rate, lint clean, PR-ready gate pass.
4. **Resume/recovery**: kill mid-run, resume; measure state correctness and
   duplicate work avoided.
5. **Cost efficiency**: same task across tiers; report $/accepted-feature.

## Publication

- Raw: `docs/benchmarks/<date>-<suite>.json`
- Summary table in `website/docs/benchmarks.md` + README section.
- Claims only cite measured runs; "pending" stays until M2 (6 runs each).
" 