# Gemini / Antigravity — ADLC5

**Invoke:** Load skill `adlc5` (or stage skills `@adlc5-specify`, `@adlc5-plan`, …).

```bash
./scripts/install.sh --platform gemini       # ~/.gemini/skills/
./scripts/install.sh --platform antigravity    # Antigravity plugin
```

| Need | See |
|------|-----|
| Full invoke map + workspace facts | [AGENTS.md](AGENTS.md) |
| Lifecycle | [docs/ADLC5.md](docs/ADLC5.md) |
| Install / consumer setup | [shared/docs/INSTALL.md](shared/docs/INSTALL.md) |
| Cross-platform matrix | [shared/docs/CROSS-PLATFORM.md](shared/docs/CROSS-PLATFORM.md) |
| Craftsmanship rules | [shared/rules/portable/](shared/rules/portable/) |

**Gemini-specific:** Copy [AGENTS.md](AGENTS.md) into consumer projects. Enable `experimental.skills` in Gemini CLI settings. Antigravity workspace skills: `.agent/skills/` (project) or `~/.gemini/config/plugins/adlc5-plugin/` (global).
