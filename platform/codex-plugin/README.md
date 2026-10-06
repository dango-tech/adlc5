# Codex plugin metadata (ADLC5 4.0)

`plugin.json` is packaging metadata for Codex plugin discovery. The coherent Agent Plugin (skills + kernel + MCP) lives at the **distribution repo root**; this folder does not re-bundle the kernel.

## Surfaces

| Surface | Where |
|---------|--------|
| Skills (classic) | `./scripts/install.sh --platform codex` → `~/.codex/skills` |
| Skills (plugin dir) | `plugin.json` → `./skills/` after you link/copy skills beside this folder |
| Kernel CLI | `$ADLC5_ROOT/scripts/adlc5` (distribution root) |
| MCP | `$ADLC5_ROOT/scripts/adlc5-mcp.py` (see also `.cursor-plugin/mcp.json`) |

Set `ADLC5_ROOT` to your adlc5 clone when invoking kernel/MCP from a host that did not start in the repo.

## Plugin load vs classic install

**Classic (recommended for Codex):**

```bash
./scripts/install.sh --platform codex
./scripts/verify-install.sh --platform codex
```

**Plugin UI:** point Codex at this directory only if `./skills/` is populated (symlink to distribution `skills/` is fine). Kernel/MCP still require the distribution clone — do not invent a second runtime here.

**Cursor Agent Plugin:** use [`.cursor-plugin/`](../../.cursor-plugin/README.md) at the distribution root.

```bash
export ADLC5_ROOT=/path/to/adlc5
"$ADLC5_ROOT/scripts/adlc5" version
python3 "$ADLC5_ROOT/scripts/adlc5-mcp.py" --smoke
```

See [ADLC5-kernel.md](../../docs/ADLC5-kernel.md) and [CROSS-PLATFORM.md](../../shared/docs/CROSS-PLATFORM.md).
