# Claude Code — Model tier mapping for ADLC5

Map abstract tiers from [core/guides/model-matrix.md](../core/guides/model-matrix.md) via `/model` or Claude settings.

**Resolve:** `./scripts/resolve-model.sh --platform claude --tier <tier>`

## Suggested mapping

| Tier | Typical Claude use |
|------|---------------------|
| **reasoning** | Opus-class for design, code spec, verify, `@qa` |
| **balanced** | Sonnet-class for orchestration and stories |
| **execution** | Inherit parent when `execution_policy: inherit`; Haiku/Sonnet only if explicit |
| **fast** | Not for implement/verify or `@qa` |

## config.yaml example

```yaml
platform_profiles:
  claude:
    reasoning: "claude-opus-4-6"
    balanced: "claude-sonnet-4-6"
    execution: "claude-haiku-4-5"
    spawn:
      task_model_param: true
```

IDs change; keep them in gitignored `config.yaml`.
