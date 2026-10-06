# Gemini / Antigravity — Model tier mapping for ADLC5

Map abstract tiers from [core/guides/model-matrix.md](../core/guides/model-matrix.md) in Gemini CLI / IDE settings ([gemini-settings.json](gemini-settings.json)).

**Resolve:** `./scripts/resolve-model.sh --platform gemini --tier <tier>`

## Suggested mapping

| Tier | Typical Gemini use |
|------|--------------------|
| **reasoning** | Pro-class for design, code spec, verify, `@qa` |
| **balanced** | Flash/Pro mid tier for orchestration |
| **execution** | Inherit parent when `execution_policy: inherit` |
| **fast** | Not for implement/verify or `@qa` |

## config.yaml example

```yaml
platform_profiles:
  gemini:
    reasoning: "gemini-2.5-pro"
    balanced: "gemini-2.5-flash"
    execution: "gemini-2.5-flash"
```

IDs change; keep them in gitignored `config.yaml`. Antigravity installs use the same gemini profile unless you add an `antigravity` block.
