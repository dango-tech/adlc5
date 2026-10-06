# Fail-fast ADLC5 engagement gate

**Last verified:** 2026-09-18  
**Status:** Warn by default on every platform; `enforce` is opt-in. Every
failure path fails open — a broken guard never blocks work.

The gate catches the "scaffold exists, framework never actually ran" failure
mode while a session is still cheap, instead of hours and hundreds of dollars
later. All decision logic lives in `scripts/engagement-gate.py`; the per-platform
hook wrappers (`.cursor/hooks/engagement-gate.sh`,
`.claude/hooks/engagement-gate.sh`, `.codex/hooks/engagement-gate.sh`) are thin
and just feed it payloads.

## Two detection paths, one decision core

| Path | Command | Trigger |
|---|---|---|
| Live, per tool call | `session-edit` | Each mutating tool call (`Write`, `StrReplace`, `Edit`, `apply_patch`, …) via the platform hook |
| Live, per prompt | `scan` | Platforms without a per-tool-call hook: the git working tree is the touched-file set |
| Backstop | `check-branch` | A git `pre-push` hook, for sessions that never passed through an agent hook at all |

When the gate decides to warn, it pushes the message back into the same agent
turn through the platform's agent-message channel, so the agent has to resolve
it with the user before continuing.

## What triggers a warning

The counted unit is **distinct substantive files touched in a session**, not raw
edit events: iterating twenty times on one file is a tweak, while spreading
edits across several files is the shape of feature work. That distinction is
what keeps the gate quiet on legitimately small changes.

| Threshold | Value | Rationale |
|---|---|---|
| `FIRST_WARN_FILES` | 4 | 1–2 files is a typo/chore, 3 is the common benign triple (implementation + its test + an export/registration), and 4+ distinct files is the size at which ADLC5 code specs would normally carry `files_to_create`/`files_to_modify` frontmatter — i.e. story-sized work that should have had a design pin it. Four files is also still only a few dollars of tokens, which is the whole point: fail fast, not fail expensive. |
| `ESCALATE_EVERY_FILES` | 3 | After the first warning, re-warn every 3 further distinct files so the signal escalates instead of being a single scrollable-past line. |

Not every path counts. Excluded from the substantive set: VCS/tooling metadata
and ADLC5's own lifecycle directories (`.git/`, `.adlc5/`, `.cursor/`,
`.claude/`, `.codex/`, …), dependency and build output (`node_modules/`,
`dist/`, `target/`, …), lockfiles, images, and root-level dotfiles. Markdown is
a deliberate judgment call: ADLC5's own gate artifacts (design docs, code specs,
spec-handoff) are markdown, so counting it would make the gate fire on the
framework doing its job. Documentation-only sessions are therefore not caught
live — the git backstop still sees them at push time.

## "Engaged" means more than a binding row

The gate reports one of three states for a session (`status` subcommand):

| State | Meaning |
|---|---|
| `engaged` | A feature is bound to this conversation **and** that feature has a real `state.json` (active tree or `.adlc5/_archive/{feature}-*/`). No warning. |
| `scaffold-only` | A binding exists, but the bound feature has no usable `state.json` — the scaffold was created and then bypassed. Warns. |
| `unbound` | No ADLC5 feature is bound to this conversation. Warns. |

`scaffold-only` is exactly the bypass the gate exists to catch: a feature
directory scaffolded and abandoned, bindings written with `stage: null,
step: null`, every subdirectory empty. A missing, empty, or unparseable
`state.json` all count as scaffold, not engagement.

Binding a feature late clears the warning ledger — that is the desired outcome,
and the session should not keep nagging afterwards.

## Warn vs enforce

```bash
export ADLC5_ENGAGEMENT_GATE=enforce   # deny the tool call instead of warning
export ADLC5_ENGAGEMENT_GATE=off       # disable the gate entirely
```

Precedence mirrors the scope guard: the env var wins, then
`.adlc5/config.yaml` → `engagement_gate.mode`, else `warn`.

```yaml
# .adlc5/config.yaml
engagement_gate:
  mode: warn   # warn (default) | enforce | off
```

In `warn` mode the hook still returns "allow" and only attaches the message. In
`enforce` mode the same message is returned as a deny decision, so the mutating
tool call is refused until a feature is bound or the session is acknowledged.
`check-branch` is warn-only in every mode — it prints to stderr and always
exits 0, so a push is never blocked.

## Acknowledging intentional ad-hoc work

Chores, hotfixes, and exploration are legitimate. Once the user confirms the
work is intentionally ad-hoc, acknowledge the session and the gate goes quiet
for the rest of it:

```bash
./scripts/engagement-gate.py ack \
  --workspace . \
  --session-id <conversation-or-session-id> \
  --platform cursor \
  --reason 'hotfix for prod incident'
```

Acknowledgement is persisted in the session's state file under
`.adlc5/engagement-gate/{platform}-{digest}.json` (`acknowledged: true` plus the
reason), so it survives across tool calls in the same session without silencing
anything else.

Inspect what the gate currently thinks:

```bash
./scripts/engagement-gate.py status --workspace . --platform cursor --session-id <id>
```

## Pre-push backstop

Sessions that never go through an agent hook — manual commits, non-agent
editors — are caught at push time instead. `check-branch` warns when the current
branch uses the configured feature prefix (`git_branch_prefix` in
`.adlc5/config.yaml`, default `feat`), has at least one commit of its own, and
no `state.json` exists for the matching feature slug in either
`.adlc5/{slug}/` or `.adlc5/_archive/{slug}-*/`.

Install it as a real git hook in a consumer repo:

```bash
/path/to/adlc5/scripts/hooks/install-pre-push-engagement-gate.sh --workspace /path/to/app
```

The installer writes `<workspace>/.git/hooks/pre-push` and makes it executable.
A pre-existing `pre-push` hook is never clobbered: it is moved to
`.git/hooks/pre-push.pre-adlc5` and the installed dispatcher runs it first —
same arguments, same stdin — then the gate. Both are non-fatal and the
dispatcher always exits 0. Re-running the installer is idempotent: it detects
its own dispatcher and keeps chaining the previously preserved hook.

## Tests

```bash
python3 -m unittest scripts/tests/test-engagement-gate.py -v
```

Covers the threshold and escalation arithmetic, `scaffold-only` detection,
acknowledgement persistence, the `check-branch` active/archived state lookup,
and the fail-open guarantees.
