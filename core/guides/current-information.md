# ADLC5 — Current information policy

**last_verified:** 2026-08-28

Use this policy for facts that change independently of the repository: library and framework versions, APIs, protocol status, security guidance, provider capabilities, platform commands, and current best practices. Timeless craftsmanship may stay in the vendored knowledge base; volatile facts may not be trusted merely because they are already written here.

## Mandatory agent behavior

1. **Classify volatility.** Before using or editing a version, status, API, protocol, command, compatibility claim, or current recommendation, treat it as time-sensitive.
2. **Verify before relying.** Check an official primary source at task time—official specification, release notes, maintained repository, vendor documentation, or standards body. Use Context7 or another live documentation tool when available; fall back to official web sources.
3. **Record provenance.** A tracked snapshot must state `last_verified`, exact source URLs, and whether the referenced item is stable, candidate/preview, deprecated, or legacy.
4. **Separate fact from decision.** State what the source currently says, then state ADLC5's recommendation. Do not promote a candidate to stable or turn a roadmap item into a shipped capability.
5. **Fail closed on staleness.** If a load-bearing current claim cannot be revalidated, stale information is a blocker: mark it unverified or remove it rather than shipping it as fact.
6. **Recheck on release.** Refresh volatile claims whenever ADLC5 updates them, a consumer feature depends on them, or a major release is prepared. A date is evidence of the last check, not permission to skip a new check.

## Snapshot header

Use this compact header in any tracked volatile guide:

```yaml
last_verified: YYYY-MM-DD
status: stable | candidate | preview | deprecated | legacy
sources:
  - https://official.example/spec
```

## Example: A2UI

A2UI status must be checked against its [official specification](https://a2ui.org/specification/v1.0-a2ui/), evolution guide, roadmap, and maintained repository before recommending a wire version. As of this policy's `last_verified` date, production and candidate versions differ; see [agent-orchestration.md](agent-orchestration.md#current-a2ui-status).
