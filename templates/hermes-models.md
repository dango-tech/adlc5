# Hermes Agent — Model tier mapping for ADLC5

Map abstract tiers from [core/guides/model-matrix.md](../core/guides/model-matrix.md) via Hermes session model settings.

**Resolve:** `./scripts/resolve-model.sh --platform hermes --tier <tier>`

## Suggested mapping

| Tier | Typical Hermes use |
|------|--------------------|
| **reasoning** | Highest-capability provider model |
| **balanced** | Mid-cost default |
| **execution** | Inherit parent when `execution_policy: inherit` |
| **fast** | Not for implement/verify or `@qa` |

Prefer a fresh Hermes session when switching personas (`fresh_session_per_persona`).

## config.yaml example

```yaml
platform_profiles:
  hermes:
    reasoning: "anthropic/claude-opus-4"
    balanced: "google/gemini-2.5-flash"
    execution: "google/gemini-2.5-flash"
    spawn:
      fresh_session_per_persona: true
```

IDs change; keep them in gitignored `config.yaml`.
