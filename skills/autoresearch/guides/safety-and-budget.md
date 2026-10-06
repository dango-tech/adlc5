# Safety and budget

Running the loop unattended is the whole point of `autonomous` mode. The cost of unsafe autonomy: burned compute, leaked secrets, broken host, corrupted leaderboards. This guide is mandatory before Phase 3 in `autonomous` mode.

## Budget layers (all three must be set)

| Layer | Field | Default | Purpose |
|-------|-------|---------|---------|
| **Per-trial** | `context.budget.per_trial` | `5m` / `1000 steps` / `200 items` | Bounds a single run; enforced by `run-experiment.sh` |
| **Total trials** | `context.budget.max_trials` | `50` | Hard cap on loop iterations |
| **Total wall clock** | `context.budget.max_total_wall_clock` | `8h` | Real-time ceiling regardless of trial count |

The loop exits when **any** layer is hit. Layered budgets prevent both "many fast cheap trials never end" and "one trial blocks for hours".

## Kill switch (mandatory)

A file path (`context.safety.kill_switch_path`, default `.autoresearch/{project}/STOP`).

- The orchestrator checks for the file **before every trial** via `scripts/check-kill-switch.sh`
- If present (even empty), the loop exits with `stop_reason: "kill-switch"` and routes to Phase 4
- The user creates the file with `touch .autoresearch/{project}/STOP` from any shell

**The kill switch is more important than the budget.** Budgets prevent runaway autonomy; the kill switch lets a human stop a wrong-direction run immediately without killing processes.

## Cost cap (when trials hit paid APIs)

`context.safety.cost_cap_usd` (default `null`).

- Set when the trial's `execute_cmd` calls paid APIs (LLM eval, cloud GPU minutes)
- `log-experiment.sh` accumulates `cost_per_trial_usd` from the trial output (the artifact must report it)
- `check-kill-switch.sh` exits non-zero if cumulative cost ≥ cap
- Cumulative cost lives in `state.json.context.safety.cost_accumulated_usd`

If your trial cannot report its own cost, set `cost_cap_usd: null` and rely on wall-clock + trial count caps instead.

## Tripwires (failure cascades)

Configured in `context.safety.tripwires`. Defaults:

| Tripwire | Default value | Action |
|----------|---------------|--------|
| `consecutive_failures` | `3` | Three trials in a row with exit_code != 0 or unparseable metric → stop loop |
| `metric_nan_or_inf` | `true` | Any non-finite metric → stop loop |
| `regression_streak` | `{count: 5, threshold_pct: 50}` | 5 trials in a row regressing ≥ 50% vs baseline → stop loop |
| `trial_budget_overrun` | `2x` | A trial exceeds per-trial budget by 2× → stop loop (something is wrong with execute_cmd) |

Tripwires are checked by `check-kill-switch.sh` after each trial. They protect against a confused agent silently burning the night on broken runs.

## Permissions and host hardening

Karpathy's repo says **"disable all permissions"** — appropriate for a personal research box with nothing important on it. For ADLC5 use, that is **not** the default. Instead:

- **File boundaries** — the experimenter is told it can modify **only** `context.target.artifact_path`. Any write outside that path is a blocker reported to the orchestrator.
- **Network** — recommend running in a sandbox without secrets-bearing env vars; document required network egress per trial in `program.md`.
- **Filesystem** — supporting files are listed in intake and treated read-only by the experimenter; the orchestrator does not modify them either.
- **Process** — `run-experiment.sh` uses OS-level timeout to enforce wall-clock budget; trial subprocesses inherit a restricted env (the script masks unused secrets).

Document the chosen posture in `program.md` Safety section before flipping `interaction_mode` to `autonomous`.

## Reproducibility safety

Every kept trial must be reproducible from its snapshot. Phase 4 verifies this. If you cannot reproduce the best trial, treat it as **discarded** in `report.md` and document the failure — never ship a non-reproducible win.

## What to do when something goes wrong

| Symptom | Response |
|---------|----------|
| Loop appears stuck (no progress in 10+ minutes) | `touch .autoresearch/{project}/STOP`; inspect last trial's `run.log` |
| Costs spiking | Lower `cost_cap_usd` mid-session by editing `state.json`; the next gate read catches it |
| Metric collapsed | Tripwire should fire; if not, stop and check `metric_extract_cmd` |
| Wrong file got modified | Restore from `experiments/{parent_trial_id}/artifact.<ext>`; investigate why the experimenter wrote outside boundaries; tighten `program.md` File Boundaries section |
| Orchestrator session crashed | Resume — `@autoresearch for {project}` reads `state.json` and continues from last logged trial |

## Pre-flight checklist (before autonomous Phase 3)

- [ ] Per-trial, max-trials, max-total-wall-clock all set
- [ ] Kill-switch path documented in `program.md`
- [ ] Tripwires configured (or defaults accepted)
- [ ] Cost cap set if any paid APIs are used
- [ ] `program.md` File Boundaries lists the one mutable artifact
- [ ] Baseline reproduced cleanly in Phase 2
- [ ] User has shell access to `touch STOP` (or remote equivalent)
- [ ] `report.md` will be the only consumed artifact downstream — confirmed with user
