---
description: "Run ADLC5 supervised coding agents with per-host model profiles, attended or confined execution, and evidence-backed results."
---

# Running supervised agents

Set a per-host model profile and start a feature run:

```bash
./scripts/adlc5 setup models --host HOST
./scripts/adlc5 run --feature FEATURE --host HOST --workspace PATH
```

Setup stores the selected supervision mode for that host. `--mode` overrides
the saved mode for a single run.

| Host | Default mode | Unattended support |
|---|---|---|
| Codex | confined | Yes, with the CLI workspace-write sandbox |
| Claude Code | allowlist | Yes, with project commands from `.agents/commands.yaml` and host permission denials |
| Cursor | confined | Yes, with the CLI sandbox; ADLC5 never passes `--force` or selects a `-fast` model |
| Hermes Agent | attended | No on the host. Unattended runs require a user-declared, runtime-detected container. |

Use `--mode attended` to run a host CLI in the current terminal with its own
approval prompts. This mode needs a terminal and an attempt-specific result
file. After the host reports that the result is ready, exit its CLI to return
control to the runner. `hitl` denials pause for a human answer; `autonomous`
denials fail the attempt.

Comparative benchmark qualification is pending. Adapter support does not
establish a cost reduction or unchanged acceptance quality.
