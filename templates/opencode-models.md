# OpenCode — Model tier mapping for ADLC5

Map abstract tiers from [core/guides/model-matrix.md](../core/guides/model-matrix.md) in OpenCode model config.

**Resolve:** `./scripts/resolve-model.sh --platform opencode --tier <tier>`

## Suggested mapping

| Tier | Typical OpenCode use |
|------|----------------------|
| **reasoning** | Highest-capability provider model |
| **balanced** | Strong mid-cost model |
| **execution** | Cheap/fast provider model only when `execution_policy: explicit` |
| **fast** | Not for implement/verify or `@qa` |

`fresh_session_per_persona: true` — prefer a fresh session when switching delivery personas.

## config.yaml example

```yaml
platform_profiles:
  opencode:
    reasoning: "anthropic/claude-opus-4"
    balanced: "google/gemini-2.5-flash"
    execution: "google/gemini-2.5-flash"
    spawn:
      fresh_session_per_persona: true
```

Provider/model strings are placeholders; adjust to your OpenCode setup.
