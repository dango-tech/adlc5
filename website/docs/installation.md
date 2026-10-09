# Installation

## Prerequisites

Install Git, Bash 3.2 or newer, Python 3.10 or newer, and jq.
The baseline kernel requires no Python packages. An AI host is needed for coding
sessions, but not for contract tests or consumer checks.

## Classic installation

```bash
git clone https://github.com/dango-tech/adlc5.git
cd adlc5
cp config.example.yaml config.yaml
./scripts/install.sh --platform codex
./scripts/verify-install.sh --platform codex
```

Replace `codex` with your supported host. Install adapters exist for Cursor,
Claude, Codex, OpenCode, Gemini, Hermes Agent, and Antigravity.
Availability of an adapter does not establish equal end-to-end delivery validation.
See the [cross-platform reference](https://github.com/dango-tech/adlc5/blob/main/shared/docs/CROSS-PLATFORM.md)
for qualification and host-specific steps.

Keep the distribution clone available: installed skills and rules link to it.
Configure install targets and model routing in the clone's `config.yaml`;
do not point install targets at the clone's own `skills/` directory.

## Claude Code plugin (local package)

The self-contained local package includes skills, kernel, MCP server, hooks, and
templates. Build it from the distribution checkout; no separate clone is needed
at runtime:

```bash
python3 scripts/package-plugin.py --out /tmp/adlc5-dist
claude --plugin-dir /tmp/adlc5-dist/adlc5-plugin-5.0.0.zip
```

The session-local command changes no global configuration. Skills appear as
`adlc5:<name>`. Invoke `adlc5-setup` in your application repository after installation
or update. It checks prerequisites, shows tracked additions, and creates only
missing files. For scripted setup within the plugin session:

```bash
adlc5-run plugin-setup.sh --check
adlc5-run plugin-setup.sh
```

The plugin puts `adlc5` and `adlc5-run` on Bash PATH. Run consumer commands from your
application repository, with `--workspace .`. Feature state stays in that repository's
`.adlc5/`, never in the immutable plugin. Classic and plugin installations can coexist;
setup reports duplicates without deleting them. This is a local/private package,
not a public directory listing. See the
[plugin installation guide](https://github.com/dango-tech/adlc5/blob/main/shared/docs/INSTALL.md#claude-code-plugin-local-package).

The package has archive, MCP stdio, bootstrap, and hook tests plus a recorded live
local session for setup, gate checks, engagement warning, and resume. A full
human-approved lifecycle on it and live Codex qualification remain pending.

## Update and verify

```bash
# Update the current host's classic installation
/path/to/adlc5/scripts/update-adlc5.sh --self
# Or update all classic install targets
/path/to/adlc5/scripts/update-adlc5.sh --global
/path/to/adlc5/scripts/verify-install.sh --platform codex
```

Install/update prunes stale ADLC5 skill and rule symlinks and aged backups.
It does not delete feature trees. Shared repository configuration and per-feature
state have different lifetimes; see the
[installation guide](https://github.com/dango-tech/adlc5/blob/main/shared/docs/INSTALL.md)
for worktrees, cleanup, hooks, and troubleshooting.

Next: [initialize your first feature](quickstart.md).
