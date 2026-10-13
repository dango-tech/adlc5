# ADLC5 Cursor Plugin (5.0)

Build the self-contained Cursor package with `python3 scripts/package-plugin.py --host cursor --out /tmp/adlc5-dist`. The generated directory at `/tmp/adlc5-dist/cursor/adlc5` contains this manifest, the shared skills, and the runtime.

## What this plugin declares

| Surface | Path |
|---------|------|
| Skills | `skills/` |
| Kernel CLI | `scripts/adlc5` (shim: `run-adlc5.sh`) |
| MCP (stdio) | `scripts/adlc5-mcp.py` (shim: `run-mcp.sh` → `mcp.json`) |

Shims set `ADLC5_ROOT` to the distribution root so hosts can invoke kernel/MCP without hard-coded absolute paths in the manifest.

## Load as Cursor plugin vs classic install

**Plugin load:** copy the generated package into `~/.cursor/plugins/local/adlc5`, reload Cursor, then enable it from **Customize**. Teams can distribute it through a team marketplace; the public Cursor Marketplace requires a repository submission and review.

**Classic install (seven-host matrix — unchanged):**

```bash
./scripts/install.sh --platform cursor   # or claude|codex|…|all
./scripts/verify-install.sh --platform cursor
```

Classic install symlinks skills/rules into host global dirs (`~/.cursor/skills`, etc.). It does **not** replace the need for the distribution clone: kernel + MCP always run from `ADLC5_ROOT` (this repo).

**Consumer app repos:** still use `./scripts/init-workspace.sh --project .` for project-local skills + `.adlc5/`.

## Quick checks

```bash
./.cursor-plugin/run-adlc5.sh version
./.cursor-plugin/run-mcp.sh --smoke
./scripts/adlc5 --help
```

See [ADLC5-kernel.md](../docs/ADLC5-kernel.md) and [INSTALL.md](../shared/docs/INSTALL.md).
