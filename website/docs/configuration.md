---
description: "Understand ADLC5 machine storage, project defaults, worktree overrides, and the read-only Settings view."
---

# Configuration and shared storage

`~/.adlc5/` is the machine home for configuration, project defaults, shared source
runtimes, staged packages and derived Pulse reports. It is not a replacement for
consumer-owned requirements, acceptance and feature evidence.

| Location | Ownership |
| --- | --- |
| `~/.adlc5/config.yaml` | Machine defaults and enforced policy |
| `~/.adlc5/projects/<repository-id>/config.yaml` | Defaults shared by linked worktrees |
| `<worktree>/.adlc5/overrides.yaml` | Explicit local overrides |
| `<worktree>/.adlc5/<feature>/` | Local lifecycle state and evidence |
| `~/.adlc5/runtimes/` | Content-addressed source-install runtime |
| `~/.adlc5/packages/` | Staged downloaded host packages |
| `~/.adlc5/pulse/board.html` | Central offline board |

Local overrides supersede defaults, while enforced machine policy remains binding.
Legacy configuration is still read for compatibility. Conflicting explicit host
or execution-mode options are rejected. Native plugin managers retain ownership
of their own caches; ADLC5 does not rewrite those caches to force deduplication.
Old runtime versions, legacy caches and evidence are preserved rather than deleted.

Open [Pulse](pulse.md), then Settings, to inspect effective values and provenance
by machine, project or worktree. It shows overrides, paths, consent and credential
availability without secret values. Settings is a read-only capture; refresh the
board after editing configuration. Model routing and runner configuration use the
same resolver. See the [canonical precedence and migration guide](https://github.com/dango-tech/adlc5/blob/main/docs/shared-home.md)
for the complete ordering, legacy locations and policy rules.
