# Quickstart

After [installation](installation.md), open your application repository.
Replace `/path/to/adlc5` with the distribution clone or installed plugin root.

## Initialize the workspace

```bash
/path/to/adlc5/scripts/init-workspace.sh --project .
/path/to/adlc5/scripts/init-feature.sh --feature my-feature --interaction hitl
```

Initialization creates repository context and a local `.adlc5/my-feature/` tree.
Review the draft `.agents/` constitution so architecture, boundaries, and commands
describe your application. Generated `.agent-cache/` intelligence and `.adlc5/`
lifecycle state stay untracked.

Read [Intelligence](intelligence.md) to review the generated guidance, check map
freshness, and understand how story context reaches each agent.

## Start delivery

In your agent host, invoke:

```text
@adlc5 for my-feature
```

Describe the intended behavior, constraints, and acceptance evidence. ADLC5
captures requirements, chooses proportionate depth, plans the change, creates
bounded tasks, then builds and verifies it. Resolve unclear requirements before
implementation. See [the lifecycle](lifecycle.md) for outputs and gates.

For autonomous progression, initialize with `--interaction autonomous` instead
of `--interaction hitl`. Autonomous work still obeys required checks and approval
gates; it requires an agent host to execute judgment and coding actions.

## Inspect progress

Run these from the application repository:

```bash
/path/to/adlc5/scripts/adlc5 pilot --feature my-feature --workspace .
/path/to/adlc5/scripts/adlc5 gate --feature my-feature --gate pr-ready --workspace .
```

`pilot` reports the next enabled action. A readiness gate can fail while work is
in progress; read its missing evidence instead of editing state to claim completion.

## Try the framework's consumer example

From the distribution repository, run the baseline consumer regression:

```bash
python3 dogfood/consumer/regression.py
```

The [consumer guide](https://github.com/dango-tech/adlc5/blob/main/dogfood/consumer/README.md)
explains isolated evaluation tasks. Fixture checks do not establish comparative
coding quality or live host qualification.
