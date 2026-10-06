# Codex — Model tier mapping for ADLC5

Map abstract tiers from [core/guides/model-matrix.md](../core/guides/model-matrix.md) via `~/.codex/config.toml` and `spawn_agent` model hints.

**Resolve:** `./scripts/resolve-model.sh --platform codex --tier <tier>`

## Suggested mapping

| Tier | Typical Codex use |
|------|---------------------|
| **reasoning** | High-reasoning Codex / GPT thinking for design and verify |
| **balanced** | Default Codex model for orchestration |
| **execution** | Inherit parent when `execution_policy: inherit` |
| **fast** | Not for implement/verify or `@qa` |

`platform_profiles.codex.spawn.spawn_agent_model: true` means council/spawn may pass an explicit model when policy allows.

## config.yaml example

```yaml
platform_profiles:
  codex:
    reasoning: "gpt-5.3-codex[reasoning=extra-high]"
    balanced: "gpt-5.3-codex"
    execution: "gpt-5.3-codex[fast=true]"
    spawn:
      spawn_agent_model: true
```

IDs change; keep them in gitignored `config.yaml`.
