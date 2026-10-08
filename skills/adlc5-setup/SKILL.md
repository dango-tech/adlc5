---
name: adlc5-setup
description: Set up or verify ADLC5 in the current repository when ADLC5 runs as a host plugin — preflight tools, create missing workspace scaffolding, flag classic-install duplicates. Safe to repeat. Invoke via @adlc5-setup.
version: 5.0.0
---

# ADLC5 — Setup (plugin hosts)

Prepare the repository you are working in. Setup never installs global or project skills, never creates host-specific files for another host (for example Cursor agents), and never overwrites an existing `AGENTS.md`, constitution file, customized config, feature state, or evidence.

**Run the packaged script:** `adlc5-run plugin-setup.sh` (plugin hosts put `adlc5-run` on the shell PATH). If it is not on PATH, use `<adlc5_root>/scripts/plugin-setup.sh`, where `adlc5_root` is the runtime path the session context reports. Run from the consumer repository, or pass `--project DIR`.

1. **Report first** (writes nothing): `adlc5-run plugin-setup.sh --check`
2. Show the user the preflight result (Git, Bash 3.2+, Python 3.10+, jq), the repository root, the **tracked additions** to review and commit (`AGENTS.md`, `.agents/*.yaml`, `docs/adr/`), and any duplicate classic installs. Ask before continuing if anything is unexpected.
3. **Initialize what is missing:** `adlc5-run plugin-setup.sh`
4. Next: `adlc5 repo-spec reconcile --workspace .`, review `.agents/`, then start a feature with `@adlc5`.

Duplicates (classic hooks, classic skill links, a second MCP entry) are reported, not removed — delete them yourself when you want a single source. Repeat setup after a plugin update: it refreshes only a stale recorded runtime path (`adlc5_root`) and leaves every other setting alone.

Classic (clone-based) installs do not need this skill: use `./scripts/init-workspace.sh --project .` — see [INSTALL.md](../../shared/docs/INSTALL.md).
