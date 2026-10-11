# ADLC5 platform adapters

Cross-IDE parity for skills and scripts.

| Tier | Scope |
|------|-------|
| T1 | Unified state, v2 scripts, skill-registry.yaml |
| T2 | AskQuestion / numbered fallbacks |
| T3 | Host hooks (Cursor, Claude Code, and Codex) |

## Install

```bash
./scripts/install.sh --platform all
```

## Host invoke map

| Host | Invoke |
|------|--------|
| Cursor | `@adlc5` |
| Claude Code | `/adlc5` |
| Codex / OpenCode | `skill({name:"adlc5"})` |
| Gemini / Antigravity | load skill `adlc5` |
| Hermes Agent | `/skill adlc5` or `hermes -s adlc5` |

Skills install from `skills/` via `./scripts/install.sh`.

The supervised runner supports Codex (confined), Claude Code (allowlist), Cursor (confined), and Hermes (attended; unattended only inside a declared container). Start it with `./scripts/adlc5 run --feature NAME --host HOST --workspace PATH`. Claude and Cursor also support unattended workers; Cursor never receives `--force`. Gemini, OpenCode, and Antigravity keep using the in-agent lifecycle. Comparative benchmark qualification remains pending; see [runner modes](../docs/running.md).

See [docs/CROSS-PLATFORM.md](../shared/docs/CROSS-PLATFORM.md).
