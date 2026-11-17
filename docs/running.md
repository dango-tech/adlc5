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
directory. Exit code `10` means a person must act. With status `needs_human`
an answer is pending; record it with
`./scripts/adlc5 answer QUESTION_ID --text 'allow' --workspace .` and resume.
With status `handoff` the run has reached PR review and approval, which stay
with the in-agent PR workflow; complete that, then run again.

`--host` or a configured `default_host` is required; the runner does not pick
a host for you. Each run prints one `starting` line to stderr with the host,
mode, tiers and the config layers in effect.

Inside an existing linked worktree, including one an agent host created on
its own branch, the runner creates or switches to the feature branch in place
and never adds another worktree. Workers report the repository paths they
changed. The runner checks that list against Git status and commits only the
matching paths from a clean starting checkout. Git status can identify
unreported paths. It cannot attribute concurrent edits to the same file, so
keep the feature worktree free of concurrent edits while a worker is active.

On interruption or unclassified edits, the runner leaves the index and
worktree intact. A structured stop appears under
`.adlc5/FEATURE/pilot/runner-stop.json`. Use its expected commit and worktree to
review the Git status and diff. Preserve edits separately, return to a clean
checkout at the expected commit, then rerun the same command. Keep the
attempt journal and result files for inspection. Recovery reuses validated
results from the expected checkout without staging any files. A result
whose inputs changed before ingestion requires review before recovery.

The runner records durable stops in `pilot/runner-stop.json` under the feature
directory. The operator owns resume. If a structured host error reports a quota
limit, the receipt identifies the host quota wait and records the earliest retry
time when the host supplies one. Invoking the runner on the same host before that time returns the
existing receipt without launching another worker. If the host gives no time,
check host availability before resuming. This path uses the normal lock,
permission checks, and retry budgets. Resume is an explicit invocation.


Started from a main checkout with uncommitted changes, the runner creates one
worktree at `.worktrees/FEATURE` (excluded through `.git/info/exclude`, so
`.gitignore` is not edited) and moves the feature's `.adlc5/FEATURE` state
into it. There is one copy of the state. A later `adlc5 run` from the main
checkout is redirected to that worktree.

When verification fails its checks or the reviewer rejects the change, the
next attempt is a rework: a coder on the execution tier receives the findings
and fixes the code, then a fresh review runs. The number of reworks is capped
by `autopilot.retry_budgets.verification_per_story` (default 3); after that
the run stops for human review.

The `brief` and `detailed` summaries list deviations from the configured
settings, and `off` reports their count. Deviations include rework, a tier
running on the host's default model, denied actions, and unavailable usage.

The complete worker prompt must fit the selected tier's budget before the
runner launches a worker. The defaults are 30,000 estimated tokens for
execution and 60,000 for the other tiers. Override them with
`pack_budget_tokens` in config. The estimate rounds up from four UTF-8 bytes
per token and is separate from provider-measured usage.

`autopilot.max_iterations` caps worker attempt reservations across the
feature. `autopilot.retry_budgets.worker_attempts_per_step` caps reservations
per step, story and attempt type. The default is five or one more than the
configured verification rework budget, whichever is larger. The runner
pauses after a worker failure and stops an unchanged gate failure before
another worker starts. Verification still supports bounded rework.
Set `autopilot.require_explicit_worker_model: true` to require an explicit
requested model for each worker launch. Observed model IDs come from host
reports and can be unavailable.

Set `autopilot.max_observed_worker_tokens` to a positive integer to pause
before a new launch once the feature's attributable, already reported
worker usage reaches that threshold. This strict policy supports Codex in
confined mode and Claude in allowlist mode. Codex uses the enclosing input
and output counters from one completed turn. Claude uses the terminal
result's input, output, cache-read, and cache-creation counters. A prior
attempt with missing, partial, conflicting, or legacy usage receipts pauses
the run even below the threshold. This policy also pauses on malformed
attempt journal or usage ledger records. Reported zero is valid when the counters
are present. Without this setting, the runner continues to record usage
without imposing an observed-token limit.

This policy uses host-reported measurements after exit. A call already in
progress can cross the threshold. Provider billing, costs, and activity
outside this supervised feature's worker attempts are separate.

Set `autopilot.max_worker_usd` to a positive finite number to pass
`--max-budget-usd` to each Claude worker in allowlist mode. This mode uses
Claude Code's noninteractive print command. Other hosts and attended modes
stop before dispatch when this policy is set. The native CLI stops based
on its estimated spend. An in-flight call can exceed the estimate, and
billed costs can differ. The configured amount applies to each worker
separately. [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference)

Cost uses the host's own figure when it reports one, otherwise
`core/model-prices.yaml`. Add or override entries in
`~/.adlc5/model-prices.yaml` using the same `models:` layout. A model with no
price is shown as unpriced, never as zero.

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
