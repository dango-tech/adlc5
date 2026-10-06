# Contributing to ADLC5

Thanks for considering a contribution. ADLC5 is a skills + kernel framework — most contributions fall into one of three shapes: a new/improved **skill**, a **rule**, or a **kernel/script** change. Pick the closest section below.

## Before you start

- **This repo is the framework distribution, not a place to run lifecycles.** Feature work (`.adlc5/{feature}/`) belongs in `dogfood/` if you're validating a framework change, or in a consumer app repo otherwise. See [STRUCTURE.md](STRUCTURE.md).
- **Search first.** Check [core/skill-registry.yaml](core/skill-registry.yaml) and [shared/docs/SKILL-MAP.md](shared/docs/SKILL-MAP.md) for something that already covers your use case before proposing a new skill.
- **Open an issue before a large PR.** Small fixes (typos, doc links, bug fixes in scripts) can go straight to a PR. Anything that adds a new skill, changes a gate, or touches `core/state-schema.json` should start as an issue so the shape can be discussed first — see [GOVERNANCE.md](GOVERNANCE.md) for what's gatekept.

## Contributing a skill

1. Model it on an existing skill of similar scope (`skills/<name>/SKILL.md` + `phases/` if multi-step).
2. Register it in [core/skill-registry.yaml](core/skill-registry.yaml) under the right section (`core`, `auxiliary`, `craftsmanship`, or `soul`).
3. Add its invoke to [shared/docs/SKILL-MAP.md](shared/docs/SKILL-MAP.md).
4. If it's cross-cutting rather than a lifecycle stage (like `@adlc5-soul`), it doesn't need a gate — say so explicitly in the skill's `## Boundaries` section.
5. Run `./scripts/verify-install.sh` locally before opening the PR — it checks doc links resolve and skills are wired correctly.

## Contributing a rule

Rules live in [shared/rules/portable/](shared/rules/portable/) (the platform-neutral source) and are mirrored to `.cursor/rules/*.mdc` with Cursor frontmatter. Edit both, or ask for help if you're unsure how a given host consumes rules — see [shared/docs/CROSS-PLATFORM.md](shared/docs/CROSS-PLATFORM.md).

## Contributing to the kernel

Deterministic logic (gates, state, phase transitions) lives behind `./scripts/adlc5` — see [docs/ADLC5-kernel.md](docs/ADLC5-kernel.md). Kernel changes need a matching update to `scripts/tests/run-all.sh` — the kernel has no judgment layer to catch a mistake, so its own test suite is the safety net.

## Craftsmanship rules apply to your PR too

ADLC5 reviews itself with its own tools. Reasonable expectations for a PR here:
- Clean, minimal diffs — no drive-by refactors bundled with a feature (see [shared/rules/portable/agent-discipline.md](shared/rules/portable/agent-discipline.md))
- Comments only where the *why* isn't obvious from the code
- No speculative abstractions for hypothetical future needs

## Testing

Install Git, Bash 3.2+, Python 3.10+, and jq first; no AI subscription or global
host installation is required for these checks. CI uses Linux and macOS,
including macOS's system Bash.

```bash
/bin/bash ./scripts/tests/run-all.sh     # gates, state, docs and packaging
python3 scripts/tests/test-portable-install.py  # disposable Claude install
```

The install smoke test copies the distribution and uses a temporary home, so it
cannot replace your existing skills or configuration. Both commands should pass
before you open a PR. Use `./scripts/verify-install.sh --platform <host>` only
when checking an intentional installation in your own host directories.

## Focused validation

| Change | Focused check | Consumer scenario |
|---|---|---|
| Gates, transitions, evidence | `python3 scripts/tests/test_completion_evidence.py` | Demonstrate rejected stale/failed evidence and a valid transition |
| Skills, profiles, context | `python3 scripts/tests/test-lightweight-workflow.py` | Deliver or resume one bounded consumer task with the changed route |
| Evaluation | `python3 scripts/tests/test-evaluation-pilot.py` | Frozen acceptance fails before delivery; unknown outcomes stay unknown |
| Host adapter or install | `python3 scripts/tests/test-portable-install.py` | Disposable install plus actual delivery/resume for the claimed host |

Use [the consumer fixture](dogfood/consumer/README.md) for a reproducible task.
Attach actual command results and limitations to the PR. Fixture tests do not
replace live host validation; never claim observations that were not performed.

## Pull requests

- Fill out `.github/PULL_REQUEST_TEMPLATE.md` — Summary / Changes / Test plan.
- Reference the issue you opened (if any) for larger changes.
- One concern per PR. A skill addition and a bug fix elsewhere should be two PRs.

## Questions

Open a [discussion or issue](https://github.com/dango-tech/adlc5/issues) — see the issue templates under `.github/ISSUE_TEMPLATE/` for the right one to use (bug report, skill proposal, or framework RFC).

Before packaging, run `python3 scripts/tests/test-distribution.py`. Follow
[distribution guidance](docs/distribution.md) and use native Git archives.
Keep development plans and host-local state outside tracked publication inputs.

Set up [publication guardrails](docs/publication-guardrails.md) before pushing.
