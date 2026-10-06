# Cursor — Model tier mapping for ADLC5

Map abstract tiers from [core/guides/model-matrix.md](../core/guides/model-matrix.md) to your Cursor model picker.

**Resolve:** `./scripts/resolve-model.sh --platform cursor --tier <tier>`

## Suggested mapping (update in `config.yaml`, not here)

| Tier | Typical Cursor use |
|------|---------------------|
| **reasoning** | Highest-capability / Max / `auto` for design, code spec, verify, `@qa` |
| **balanced** | Default strong model (e.g. Composer) for orchestration, stories, PR review |
| **execution** | Same as parent session when `execution_policy: inherit`; never Fast for `@build-implementer` |
| **fast** | Not used for ADLC5 delivery or QA |

## How to apply

1. Copy `model_routing` + `platform_profiles.cursor` (or flat `model_profiles`) from [config.example.yaml](../config.example.yaml) into gitignored `config.yaml`.
2. On first invoke, run resolve-model or read the skill **Model recommendation** notice and switch picker if needed.
3. For parallel Delivery implementation, keep the parent on a full-capability model so subagents inherit it.

## config.yaml example

```yaml
model_routing:
  execution_policy: inherit
platform_profiles:
  cursor:
    reasoning: "auto"
    balanced: "composer-2"
    execution: "composer-2"
    fast: "composer-2-fast"
    spawn:
      task_model_param: true
```

Model IDs change; adjust to what your Cursor account exposes.
