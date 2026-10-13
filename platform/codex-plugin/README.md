# Codex plugin source metadata (ADLC5 5.0)

The distribution root `plugin.json` is the portable Agent Plugins manifest; `.codex-plugin/plugin.json` is retained as Codex's compatibility fallback. The build script creates a self-contained Codex package and local marketplace; developers do not need to assemble a plugin by copying metadata by hand.

## Surfaces

| Surface | Where |
|---------|--------|
| Skills (classic) | `./scripts/install.sh --platform codex` → `~/.codex/skills` |
| Skills + runtime package | `python3 scripts/package-plugin.py --host codex --out /tmp/adlc5-dist` |
| Local marketplace | `/tmp/adlc5-dist/codex-marketplace/` |
| Package metadata | generated root `plugin.json`, `.codex-plugin/plugin.json` fallback, and `mcp.json` |

Set `ADLC5_ROOT` to your adlc5 clone when invoking kernel/MCP from a host that did not start in the repo.

## Plugin load vs classic install

**Native Codex plugin:** follow [the cross-host build and install guide](../../docs/agent-plugins.md#codex-desktop).

**Classic skills install:**

```bash
./scripts/install.sh --platform codex
./scripts/verify-install.sh --platform codex
```

**Cursor Agent Plugin:** use [`.cursor-plugin/`](../../.cursor-plugin/README.md) at the distribution root.

```bash
export ADLC5_ROOT=/path/to/adlc5
"$ADLC5_ROOT/scripts/adlc5" version
python3 "$ADLC5_ROOT/scripts/adlc5-mcp.py" --smoke
```

See [ADLC5-kernel.md](../../docs/ADLC5-kernel.md) and [CROSS-PLATFORM.md](../../shared/docs/CROSS-PLATFORM.md).
