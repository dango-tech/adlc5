# Build and install the ADLC5 agent plugins

ADLC5 supports developers using **Codex, Claude Code, or Cursor**. This repository is the source for all three packages: shared skills and runtime are packaged with each host's own manifest and integration files. `core/VERSION` is canonical; the build checks host manifest versions against it.

## Build the packages locally

Requirements: Python 3.10+, Git, and a cleanly cloned repository. Run from the ADLC5 checkout:

```bash
python3 scripts/package-plugin.py --check
python3 scripts/package-plugin.py --out /tmp/adlc5-dist
```

The build creates host-specific package directories and `.zip` / `.tar.gz` archives outside the source tree. Each package includes the portable root `plugin.json` where supported, plus host-specific manifests. It also creates local marketplaces for Codex and Claude Code:

| Host | Package | Local registration source |
|---|---|---|
| Codex | `/tmp/adlc5-dist/codex/adlc5/` and `adlc5-codex-plugin-<version>.zip` | `/tmp/adlc5-dist/codex-marketplace/` |
| Claude Code | `/tmp/adlc5-dist/claude/adlc5/` and `adlc5-claude-code-plugin-<version>.zip` | `/tmp/adlc5-dist/claude-marketplace/` |
| Cursor | `/tmp/adlc5-dist/cursor/adlc5/` and `adlc5-cursor-plugin-<version>.zip` | local plugin folder |

Use `--host codex`, `--host claude`, or `--host cursor` to build just one package. The archive builder includes only tracked or non-ignored source files selected for distribution; it rejects symlinks, likely secrets, and personal absolute home paths. Do not edit the generated files; change the source and rebuild.

When a GitHub Release is published, `.github/workflows/release-plugin-packages.yml` builds and attaches the six host-specific archives. Developers can also build the same artifacts from any checkout with the command above.

## Register and install

### Codex desktop

Register the repository marketplace. Codex accepts the repo's legacy-compatible `.claude-plugin/marketplace.json` and installs the root package with its portable `plugin.json`:

```bash
codex plugin marketplace add dango-tech/adlc5
codex plugin marketplace list
```

Restart or open the Codex desktop app, open **Plugins**, select **ADLC5**, then install **adlc5**. To test your generated package instead, register `/tmp/adlc5-dist/codex-marketplace` and select **ADLC5 local build**. Review the plugin's tools and local MCP server before enabling it. After install or update, invoke the packaged `adlc5-setup` skill for the consumer repository.

The repository provides `.claude-plugin/marketplace.json`, a Claude marketplace and a supported legacy-compatible Codex marketplace location. The source is the repository root. Codex reads the portable `plugin.json`, root `mcp.json`, and `skills/`; `.codex-plugin/plugin.json` remains as a compatibility fallback. Codex also supports a repo marketplace at `.agents/plugins/marketplace.json`; this repository keeps the shared marketplace file at the legacy-compatible path so Claude Code can use the same catalog. Claude Code's validator may report Codex's `policy` field as an ignored unknown field; the generated Claude-only marketplace omits it and validates without warnings.

### OpenAI public plugin directory (ChatGPT and Codex)

The public directory shared by ChatGPT and Codex is a separate submission route from local and Git-backed marketplaces. Follow OpenAI's [plugin submission and publishing guide](https://developers.openai.com/plugins/deploy/submission): prepare and validate the package, submit it through the plugin submission portal, and complete OpenAI's review. A local or repository marketplace entry does not create a public listing.

The current ADLC5 Codex package configures a local stdio MCP server (`python3 ./scripts/adlc5-mcp.py`). OpenAI's public submission guidance requires a remotely reachable HTTPS MCP endpoint for public submissions; the local stdio package is therefore for local/repo marketplace distribution. To pursue a public listing, deploy an HTTPS MCP service and create a public-submission package/configuration that points to it, then submit that package and endpoint through the portal. Keep the local package available for developers who want the self-contained local runtime.

### Hermes

ADLC5 ships as a Portable Agent Plugin v1 package (`plugin.json`, `skills/`,
`mcp.json`). Install and enable it directly from the repository:

```bash
hermes plugins install dango-tech/adlc5 --no-enable
hermes plugins enable adlc5
```

Skills are namespaced and discovered via `skills_list`/`skill_view`; MCP servers
from `mcp.json` load on the next session. Classic skills install via
`./scripts/install.sh --platform ...` remains available.

### Claude Code

Register the generated local marketplace and install from it:

```bash
claude plugin marketplace add /tmp/adlc5-dist/claude-marketplace
claude plugin install adlc5@adlc5-local
claude plugin list
```

For a one-session development load without registering a marketplace:

```bash
claude --plugin-dir /tmp/adlc5-dist/claude/adlc5
```

After installation or update, start a session in the consumer repository and invoke `adlc5-setup`. For the hosted GitHub marketplace, use `claude plugin marketplace add dango-tech/adlc5`, then install `adlc5@adlc5` from the `/plugin` Discover panel. The repo's marketplace manifest is kept in `.claude-plugin/marketplace.json`.

### Cursor

Install the generated Cursor package as a local plugin:

```bash
mkdir -p "$HOME/.cursor/plugins/local"
cp -R /tmp/adlc5-dist/cursor/adlc5 "$HOME/.cursor/plugins/local/adlc5"
```

Restart Cursor or run **Developer: Reload Window**. Open **Customize**, find ADLC5 under local plugins, and install/enable it. After install or update, invoke `adlc5-setup` in the consumer repository.

For team distribution, admins can import `https://github.com/dango-tech/adlc5` through **Dashboard → Plugins & MCPs → Add Marketplace** (Teams/Enterprise feature); `.cursor-plugin/marketplace.json` lists the plugin at the repository root.

For Cursor's public marketplace:

1. Build and locally load the package, then check the manifest, components, and README.
2. Push the plugin source to a public Git repository.
3. Sign in and submit the repository link at [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish).
4. Respond to review feedback. Cursor manually reviews plugins and updates.

Cursor's submission checklist requires an open-source plugin, a valid root `plugin.json` or `.cursor-plugin/plugin.json`, a unique lowercase kebab-case name, valid component files and paths, usage documentation, and local testing. This repository includes both manifest formats and a root README; `.cursor-plugin/marketplace.json` describes the repository's plugin catalog. Team marketplaces are private distribution and do not create a public listing.

### Claude directory publishing

Claude Code marketplace publishing and Anthropic's public directory are separate routes. The repo marketplace supports Claude Code CLI installation. Anthropic's directory is browsable on claude.ai and in Cowork; a directory installation can sync into Claude Code as `adlc5@synced`.

Build the Claude package and run strict validation before submitting:

```bash
python3 scripts/package-plugin.py --host claude --out /tmp/adlc5-dist
claude plugin validate --strict /tmp/adlc5-dist/claude/adlc5
```

Then sign in to the [Claude developer portal](https://claude.ai/directory/manage) and submit the plugin. Submission requires an eligible paid claude.ai plan or an authorized Team/Enterprise organization role. The portal applies additional checks beyond CLI validation. Review the component support matrix before claiming support on claude.ai, Cowork, and Claude Code. Bump the plugin version for each directory release.

The generated Claude package omits the repository marketplace catalog. The shared source repository includes Codex-specific marketplace policy fields and repo-level `CLAUDE.md`; neither belongs in the packaged plugin submitted for strict validation.

## Source checkout and classic skills install

Developers who prefer a live source checkout can use the host's local plugin development flow. The repository root contains each host's integration metadata, and the `scripts/package-plugin.py` output gives isolated copies for testing. Classic skills installation remains available:

```bash
./scripts/install.sh --platform codex   # or claude, cursor, all
./scripts/verify-install.sh --platform codex
```

Classic skills install and plugin install are separate integration paths. Both use the same ADLC5 source version. Plugin setup initializes the **consumer** repository; never run its feature lifecycle in this framework distribution repository.

## Publishing and qualification

Building an archive verifies packaging inputs, not successful installation or runtime behavior on every host. Before claiming a host is qualified, install it in that host, confirm the expected skills and MCP server load, run `adlc5-setup` in a disposable consumer repo, and verify the consumer-side kernel command. Cursor marketplace listing and Anthropic directory submission require their respective review processes; Codex repo/local marketplaces are distinct from OpenAI's public plugin directory.

## Official host instructions

- [Codex plugin packaging and marketplaces](https://developers.openai.com/plugins/build/plugins)
- [Submit and publish an OpenAI plugin](https://developers.openai.com/plugins/deploy/submission)
- [Claude Code plugins](https://code.claude.com/docs/en/plugins) and [marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- [Publish a Claude Code plugin and submit to Anthropic's directory](https://code.claude.com/docs/en/plugins/publish#submit-to-anthropics-directory)
- [Cursor plugins](https://docs.cursor.com/plugins)
- [Submit a plugin to the Cursor Marketplace](https://cursor.com/marketplace/publish)
