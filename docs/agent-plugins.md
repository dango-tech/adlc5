# Build and install the ADLC5 agent plugins

ADLC5 provides packages for **Codex, Claude Code, Cursor and Hermes Agent**. Shared skills and runtime are packaged with each host's own manifest and integration files. `core/VERSION` is canonical; the build checks host manifest versions against it.

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
| Hermes Agent | `/tmp/adlc5-dist/hermes/adlc5/` and `adlc5-hermes-plugin-<version>.zip` | native portable-plugin installer |

Use `--host codex|claude|cursor|hermes` to build one package. The archive builder includes only tracked or non-ignored source files selected for distribution; it rejects symlinks, likely secrets, and personal absolute home paths. Do not edit generated files. `INSTALL.json` records host, version, source commit and whether the source was dirty; candidate archives with the same version are distinguishable by provenance and checksum.

`.github/workflows/release-plugin-packages.yml` attaches all eight host archives and `SHA256SUMS` to a draft GitHub Release; publishing that release then pushes them to GitHub Packages. Its release tag must match `core/VERSION` (optionally prefixed with `v`). Publishing a release is separate from building candidate packages.

## Self-install from an archive

Download the package for the intended host and `SHA256SUMS`. Verify its checksum
before extracting (`shasum -a 256 FILE.zip`, or `Get-FileHash FILE.zip -Algorithm SHA256`
on PowerShell; compare with the matching checksum entry). Extract into a new directory,
then run:

```bash
python3 install.py --dry-run
python3 install.py
```

On Windows, use `python` if `python3` is unavailable. No archive is executed during
the build or download. The installer stages a content-addressed package source under
`~/.adlc5/packages/` and follows the host's local installation flow:

- **Codex:** registers a generated local marketplace. Finish installation/reinstallation
  through Codex's Plugins UI; the current CLI has no `plugin install` subcommand.
- **Claude Code:** registers the local marketplace and invokes native plugin installation.
  Existing installations may need marketplace refresh and `claude plugin update adlc5@adlc5-local`.
- **Cursor:** installs the local plugin folder. A managed prior package is retained
  in a timestamped backup; an unknown destination is refused. Reload and enable in Cursor.
- **Hermes:** creates a local Git source and invokes native `hermes plugins install`
  with a `file://` URL and `--no-enable`. Native scanning/consent stays in force.
  Review and explicitly enable it, then start a new session.

Native CLI availability, trust and enablement remain host responsibilities.
The installer does not edit native caches, bypass security scans, auto-enable Hermes,
or claim that an already-running host loaded the new package. Its dry run writes nothing.

## Build downloadable candidates or publish release assets

In GitHub Actions, choose **Release host plugin packages → Run workflow**, select
the desired branch/tag and run it. Download `adlc5-agent-packages-<commit>` from
the run's Artifacts section. Candidate artifacts expire after 30 days; release
assets persist with their release. This manual trigger becomes available after
the workflow update is merged into the default branch.

Equivalent CLI after that update:

```bash
gh workflow run release-plugin-packages.yml --ref YOUR_BRANCH_OR_TAG
```

This repository uses immutable releases, which refuse new assets once a release
is published. To publish durable assets, attach them while the release is still a
draft, then publish it:

```bash
gh release create vX.Y.Z --draft --prerelease --target "$(git rev-parse origin/main)"
gh workflow run release-plugin-packages.yml --ref main -f attach_draft=true -f release_tag=vX.Y.Z
# after the run attaches the four ZIPs, four tarballs and SHA256SUMS:
gh release edit vX.Y.Z --draft=false
```

The run refuses a published release, a tag that differs from `core/VERSION`, or a
draft whose target commit differs from the commit it built. Publishing the release
triggers the same workflow again to push the attached archives to GitHub Packages. This does not publish listings to each vendor's
public plugin directory. Those submission/review processes remain separate below.

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

The Cursor MCP config resolves its launcher and working directory through `${CURSOR_PLUGIN_ROOT}` so it remains anchored to the installed package when Cursor starts it from another directory. Cursor does not expand the standard `${PLUGIN_ROOT}` variable in `mcp.json`.

For team distribution, admins can import `https://github.com/dango-tech/adlc5` through **Dashboard → Plugins & MCPs → Add Marketplace** (Teams/Enterprise feature); `.cursor-plugin/marketplace.json` lists the plugin at the repository root.

For Cursor's public marketplace:

1. Build and locally load the package, then check the manifest, components, and README.
2. Push the plugin source to a public Git repository.
3. Sign in and submit the repository link at [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish).
4. Respond to review feedback. Cursor manually reviews plugins and updates.

Cursor's submission checklist requires an open-source plugin, a valid root `plugin.json` or `.cursor-plugin/plugin.json`, a unique lowercase kebab-case name, valid component files and paths, usage documentation, and local testing. This repository includes both manifest formats and a root README; `.cursor-plugin/marketplace.json` describes the repository's plugin catalog. Team marketplaces are private distribution and do not create a public listing.

### Claude Desktop upload

The Desktop upload/directory validator rejects top-level `bin/` executables. Build its package with:

```bash
python3 scripts/package-plugin.py --host claude --claude-hosted --out /tmp/adlc5-desktop-dist
```

Upload the generated ZIP through **Customize → Plugins → Add plugin → Upload plugin**. This variant uses the same skills, MCP server, and Pulse mod, but omits automatic shell PATH launchers. Its session hook reports the absolute Python kernel path; the Pulse card invokes that declared runtime directly. The standard local CLI marketplace build keeps the PATH launchers.

### Claude directory publishing

Claude Code marketplace publishing and Anthropic's public directory are separate routes. The repo marketplace supports Claude Code CLI installation. Anthropic's directory is browsable on claude.ai and in Cowork; a directory installation can sync into Claude Code as `adlc5@synced`.

Build the Claude package and run strict validation before submitting:

```bash
python3 scripts/package-plugin.py --host claude --claude-hosted --out /tmp/adlc5-dist
claude plugin validate --strict /tmp/adlc5-dist/claude/adlc5
```

Then sign in to the [Claude developer portal](https://claude.ai/directory/manage) and submit the plugin. Submission requires an eligible paid claude.ai plan or an authorized Team/Enterprise organization role. The portal applies additional checks beyond CLI validation. Review the component support matrix before claiming support on claude.ai, Cowork, and Claude Code. Bump the plugin version for each directory release.

The generated Claude package omits the repository marketplace catalog. The shared source repository includes Codex-specific marketplace policy fields and repo-level `CLAUDE.md`; neither belongs in the packaged plugin submitted for strict validation.

### Pulse plugin surfaces

All four packages expose the shared `@adlc5-pulse` skill and the read-only `adlc5_pulse` MCP snapshot tool. Generate the offline board with `./scripts/adlc5 pulse board --workspace .`. The Claude Code package additionally registers a native interactive band above the prompt, with Review, Audit, Board, and Details actions. Codex and Cursor keep the shared skill/MCP/CLI experience because their documented plugin surfaces do not expose a persistent custom prompt band.

Claude Code users may manually use the cached adapter after generating a board:

```json
{
  "statusLine": {
    "type": "command",
    "command": "ADLC5_FEATURE=my-feature python3 /path/to/adlc5/scripts/pulse-statusline.py"
  }
}
```

The adapter reads that consumer's derived cache under `~/.adlc5/pulse/workspaces/` only and prints “present freshness unverified.” Set `ADLC5_WORKSPACE` when Claude's session input does not identify the consumer directory. Add the snippet manually to the project's Claude settings; plugin installation never changes an existing status line. If Ponytail or another status line is configured, keep it and use the board/skill directly unless you intentionally choose a replacement.

See [ADLC5 Pulse](pulse.md) for commands, data semantics and refresh limits. Cursor package contents are tested; live Cursor IDE qualification remains pending until the package has been installed and exercised in Cursor.

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

## GitHub Packages registry

Release ZIPs do not populate the repository's Packages tab. The release workflow
also publishes the existing, checksum-verified release assets as four OCI archive
packages linked to this repository:

- `ghcr.io/dango-tech/adlc5-codex-plugin:5.3.1`
- `ghcr.io/dango-tech/adlc5-claude-code-plugin:5.3.1`
- `ghcr.io/dango-tech/adlc5-cursor-plugin:5.3.1`
- `ghcr.io/dango-tech/adlc5-hermes-plugin:5.3.1`

These are archive bundles, not runnable Docker images. With [ORAS](https://oras.land/docs/installation),
run `oras pull ghcr.io/dango-tech/adlc5-codex-plugin:5.3.1` in an empty directory,
verify SHA256SUMS, then extract and run `install.py` using the same OS prerequisites
as the [download guide](https://adlc5.dev/downloads/). No Docker daemon is needed.
Versioned registry artifacts retain the exact release bytes and source provenance;
registry storage adds no native agent certification. Preview status follows the
associated GitHub Release, not the numeric OCI tag.

To backfill a published release, run **Release host plugin packages** with
`publish_registry` enabled and `release_tag` set to that release. Normal manual
candidate builds leave registry publication off. Publication uses job-scoped
`packages: write`, checks all eight release archives and clean source provenance,
then pulls each host package back and compares it with the original bytes.
GitHub initially creates registry packages private; an organization maintainer
must make each package public in Package settings for anonymous downloads.
