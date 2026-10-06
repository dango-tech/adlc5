# Governance

Lightweight, on purpose — this describes who decides what, not a process to route around.

## Scope tiers

| Area | Bar for merging | Why |
|------|------------------|-----|
| `core/` (state schema, gates, personas, skill registry) | Maintainer review required; breaking changes need a `core/VERSION` bump + `CHANGELOG.md` entry | Every skill and consumer workspace depends on this being stable and singular — see [docs/ADLC5-kernel.md](docs/ADLC5-kernel.md) "One state, one schema" |
| `scripts/` (kernel façade, gate checks) | Maintainer review + `scripts/tests/run-all.sh` passing | Deterministic logic has no judgment layer to catch a bad merge; the test suite is the only backstop |
| `skills/` (new or modified skills) | Community PRs welcome; reviewed for scope fit and consistency with existing skill shape | This is where most contribution should land |
| `shared/rules/portable/` | Community PRs welcome; must ship with the `.cursor/rules/*.mdc` mirror kept in sync | Cross-platform consistency matters more than any single host's convenience |
| `templates/`, `docs/` | Community PRs welcome, lighter review | Low blast radius |

## Decision process

1. Small, scoped changes (bug fixes, doc corrections, a new craftsmanship skill that doesn't touch `core/`) — a maintainer approval on the PR is sufficient.
2. Anything touching `core/state-schema.json`, `core/gates.yaml`, or the kernel façade contract (`./scripts/adlc5`) — open an issue first describing the change and why existing primitives don't cover it. See [CONTRIBUTING.md](CONTRIBUTING.md).
3. Disagreements are resolved by maintainer judgment, weighted toward keeping the kernel/skill split intact (see the "why SDD-first" evidence in [docs/ADLC5.md](docs/ADLC5.md)) over adding flexibility that erodes it.

## Maintainers

Repo ownership and merge rights live in the standard GitHub sense (CODEOWNERS / repo admins). This section will grow as the maintainer group grows past the original author.

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
