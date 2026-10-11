# Supervised headless runner

Configure the host tier profile and supervision mode, then start the run:

```bash
./scripts/adlc5 setup models --host claude
./scripts/adlc5 run --feature FEATURE --host claude --workspace .
```

Setup offers only modes supported by the selected host and stores the choice
in the machine or repository config. `--mode` overrides it for one run.

The runner calls the existing navigator, launches one worker at a time, and
submits lifecycle and evidence changes through the ADLC5 kernel. It records an
attempt journal, result, run log, and usage row under the feature's `.adlc5`
directory. Exit code `10` means a human answer is pending; record it with
`./scripts/adlc5 answer QUESTION_ID --text 'allow' --workspace .` and resume.

| Host | Default mode | Unattended | Chat launch | Boundary |
|---|---|---:|---:|---|
| Codex | confined | yes | no | `codex exec` uses `workspace-write` |
| Claude Code | allowlist | yes | yes, once logged in | `acceptEdits`; Bash permissions are built from `test`, `lint`, and `build` entries in `.agents/commands.yaml` plus commands explicitly approved for this feature |
| Cursor | confined | yes | yes | `cursor-agent -p --sandbox enabled`; `--force` and `-fast` model ids are rejected |
| Hermes Agent | attended | no outside a declared container | no | interactive `hermes chat -q`; unattended `hermes -z` requires a user declaration and a detected container runtime |

The runner does not silently switch to a weaker mode. Attended mode requires a terminal, starts the host CLI with
the worker brief as its first prompt, and requires a result file tied to the
attempt id. After reviewing the host's completion message, exit the host CLI to
return control to the runner. The process remains subject to the run timeout
and `STOP` file.

When Claude reports a denied Bash action, `hitl` mode creates a pending
question. Answer `allow` to add that exact command to the feature's local
allowlist and retry; any other answer stops the run. In `autonomous` mode a
denial fails the attempt. Review `.adlc5/FEATURE/pilot/approved-commands.json`
to see feature-specific approvals.

Hermes has no tested host-side confinement. A container run requires both a
container runtime marker (`/.dockerenv` or `/run/.containerenv`) and this
user-authored local declaration at `.adlc5/external-sandbox.json`:

```json
{"type":"container","declared_by":"user"}
```

The declaration alone does not enable unattended Hermes. The runner does not
build or ship a Hermes sandbox; the container recipe is an operator
responsibility.

The 2026-10-10 one-reply M0 spike measured first-call input at 45,238 tokens
for Claude Code 2.1.292 and 29,384 with trimming; Codex CLI 0.161.0 at 24,695
and 18,750; Cursor Agent 2026.10.01 at 20,760 with no trim flag found; and
Hermes 0.21.5 at 25,361 and 8,027 using the `terminal,file` toolsets. These
are setup measurements, not benchmark results or guarantees for later CLI
versions.

Headless Codex, Claude, Cursor, and Hermes workers capture provider usage when
the host exposes it. Claude attended usage is matched to the runner-assigned
session id and read from the Claude transcript. Cursor attended usage depends
on the existing session collector matching the session and time window;
otherwise the ledger records usage as unavailable. Attended Hermes usage is
unavailable. No unavailable counter is reported as zero.

These adapters are experimental. M2 comparative benchmarks are still
required before claiming lower cost or unchanged quality.
