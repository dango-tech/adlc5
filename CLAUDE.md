# Claude Code — ADLC5

**Invoke:** `/adlc5` or stage skills `/adlc5-specify`, `/adlc5-plan`, `/adlc5-tasks`, `/adlc5-implement`.

```bash
./scripts/install.sh --platform claude
./scripts/verify-install.sh --platform claude
```

Skills install to `~/.claude/skills/`.

| Need | See |
|------|-----|
| Full invoke map + workspace facts | [AGENTS.md](AGENTS.md) |
| Lifecycle | [docs/ADLC5.md](docs/ADLC5.md) |
| Install / consumer setup | [shared/docs/INSTALL.md](shared/docs/INSTALL.md) |
| Cross-platform matrix | [shared/docs/CROSS-PLATFORM.md](shared/docs/CROSS-PLATFORM.md) |
| Craftsmanship rules | [shared/rules/portable/](shared/rules/portable/) |

**Claude-specific:** Use `AskUserQuestion` when available (same option ids as [askquestion-convention.md](core/guides/askquestion-convention.md)). During `implement-1-build`, spawn a subagent with [build-implementer](skills/build-implementer/SKILL.md).
