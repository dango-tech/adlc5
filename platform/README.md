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

The Codex headless runner is invoked from a terminal with `./scripts/adlc5 run --feature NAME --host codex --workspace PATH`; it supervises fresh workers and sends lifecycle changes through the kernel. Claude Code, Cursor, Gemini, OpenCode, Hermes, and Antigravity continue using the in-agent lifecycle until their unattended adapters are qualified.

See [docs/CROSS-PLATFORM.md](../shared/docs/CROSS-PLATFORM.md).
