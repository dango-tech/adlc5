# Shared machine home and configuration

`~/.adlc5/` owns machine configuration, content-addressed shared runtimes,
project configuration, the Pulse source registry, reports and derived caches.
Consumer requirements, decisions, approvals, usage ledgers and delivery evidence
remain owned by their project/workflow. They are not replaced by cached copies.

| Location | Authority |
|---|---|
| `~/.adlc5/config.yaml` | Machine defaults and optional enforced configuration |
| `~/.adlc5/install.yaml` | Machine-wide installation locations (legacy source config preserved) |
| `~/.adlc5/projects/<repository-id>/config.yaml` | Project defaults shared by Git worktrees |
| `<worktree>/.adlc5/overrides.yaml` | Explicit worktree overrides |
| `~/.adlc5/runtimes/<version>/<content-digest>/` | Shared runtime, skills, rules and references |
| `~/.adlc5/runtime.json` | Last staged runtime reference |
| `~/.adlc5/pulse/` | Shared report and source registry |
| `~/.adlc5/pulse/workspaces/<worktree-id>/` | Derived feature caches and host observations |

Stage the current distribution without installing or editing host configuration:

```bash
./scripts/adlc5 setup storage
```

Source installs stage the runtime and link their host skills/rules to that shared
copy. Identical content reuses the same directory across hosts; a changed build
gets a different digest even if the version number is unchanged. Existing runtime
content is checked before reuse; modifications are rejected rather than overwritten.
No user configuration or consumer evidence is copied into the runtime. Native
host-managed plugin packages retain their host-owned copies and update lifecycle;
ADLC5 does not rewrite installed plugin caches or force one version on active sessions.

Old runtimes and local caches are not automatically deleted. This preserves active
links and recoverability; disk reclamation needs a separately reviewed cleanup.
The first Pulse refresh reads the earlier global source registry. Legacy repository
configuration remains a compatibility layer; it is read without being moved or deleted.

## Resolution

Highest precedence: enforced machine fields, explicit command options, worktree
overrides, central project defaults, legacy repository configuration, machine defaults,
then built-in behavior. An explicit option conflicting with an enforced field is rejected.
Model routing and runner configuration share the same resolver used by Settings.
Existing feature governance and human permissions remain separate contracts;
changing a configuration file does not approve commands or invalidate their checks.

Example machine configuration:

```yaml
default_host: codex
defaults:
  summary: brief
enforced:
  platform_modes:
    hermes: confined
```

Example worktree override at `.adlc5/overrides.yaml`:

```yaml
defaults:
  summary: detailed
```

Only supplied keys override inherited values. Nested maps merge; scalar/list values
replace their inherited value. Malformed/non-mapping configuration fails resolution.
Only the machine layer may declare `enforced`. These are local configuration constraints,
not authentication against a user who can edit machine files. Unknown cache files,
transcripts and remembered answers never become configuration layers.

`adlc5 setup models --repo` now writes central project configuration; existing
`<git-common-dir>/adlc5-shared/config.yaml` and `.adlc5/config.yaml` are still read.
The worktree override is deliberately separate from generated cache content.

Settings is a read-only capture, with machine/project/worktree scope, effective
values, provenance and inheritance history. It also shows storage, scan roots,
workspace telemetry consent, credential availability and cached host-plugin versions.
It never exports credential values. Per-run command options remain with their run
records, not an invented global session state. Invalid settings are displayed as
unavailable. Cached plugin versions do not prove which version an active host loaded.
