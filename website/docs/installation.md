---
description: "Install ADLC5 for Codex, Claude Code, Cursor, and other supported AI coding hosts, then verify the framework setup."
---

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

Source installs stage a content-addressed runtime under `~/.adlc5/runtimes/`.
Machine configuration and project defaults also live under `~/.adlc5/`; explicit
worktree overrides take precedence except for enforced policy. See
[configuration and storage](configuration.md). Keep the distribution clone for updates.

## Native agent plugins: Codex, Claude Code, Cursor, and Hermes Agent

[Download a package](downloads.md) for your host, extract it, and run
`python3 install.py --dry-run` followed by `python3 install.py` (Windows:
`py -3 install.py`). The installer prints the remaining host-specific steps.

The repository provides buildable packages for all four plugin hosts. From an
ADLC5 checkout, run `python3 scripts/package-plugin.py --check` and then
`python3 scripts/package-plugin.py --out /tmp/adlc5-dist`. This creates the four
host-specific packages and local Codex and Claude Code marketplaces. See the
[all-host plugin guide](https://github.com/dango-tech/adlc5/blob/main/docs/agent-plugins.md)
for building one host, registering and installing each package, and submitting
to the Codex, Cursor, and Claude marketplaces/directories.

## Claude Code plugin (local package)

The self-contained local package includes skills, kernel, MCP server, hooks, and
templates. Build it from the distribution checkout; no separate clone is needed
at runtime:

```bash
python3 scripts/package-plugin.py --host claude --out /tmp/adlc5-dist
claude --plugin-dir /tmp/adlc5-dist/claude/adlc5
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

Package tests and bounded signed-in host qualification are separate evidence.
See the [recorded host qualification](https://github.com/dango-tech/adlc5/blob/main/docs/live-host-qualification.md)
for the exact cases, retries, and limits. The comparative campaign remains unexecuted.

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
