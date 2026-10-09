# Reference

The curated site covers getting started. Follow these repository documents for
the complete contracts and host-specific behavior.

[Intelligence](intelligence.md), the fifth pillar, explains how repository context
and current evidence connect all four stages.

## Canonical guides

| Guide | Contents |
| --- | --- |
| [Installation](https://github.com/dango-tech/adlc5/blob/main/shared/docs/INSTALL.md) | Hosts, configuration, worktrees, updates, cleanup |
| [ADLC5 lifecycle](https://github.com/dango-tech/adlc5/blob/main/docs/ADLC5.md) | Stages, gates, acceptance anchors |
| [Kernel](https://github.com/dango-tech/adlc5/blob/main/docs/ADLC5-kernel.md) | Command façade, state, MCP, usage |
| [Evidence-backed completion](https://github.com/dango-tech/adlc5/blob/main/docs/evidence-completion.md) | Checks, independent review, approvals, recovery |
| [Skill map](https://github.com/dango-tech/adlc5/blob/main/shared/docs/SKILL-MAP.md) | Lifecycle and auxiliary invokes |
| [Repository context](https://github.com/dango-tech/adlc5/blob/main/core/guides/repository-context.md) | Constitution and generated intelligence |
| [Model routing](https://github.com/dango-tech/adlc5/blob/main/core/guides/model-matrix.md) | Host tiers and execution policy |
| [Knowledge base](https://github.com/dango-tech/adlc5/blob/main/shared/docs/knowledge-base/README.md) | On-demand craftsmanship material |
| [Public project overview](https://github.com/dango-tech/adlc5/wiki/ADLC5-Overview) | Public preview, brownfield context, and current qualification limits |

## Commands from a consumer workspace

```bash
/path/to/adlc5/scripts/adlc5 --help
/path/to/adlc5/scripts/adlc5 state get --feature my-feature --workspace .
/path/to/adlc5/scripts/adlc5 pilot --feature my-feature --workspace .
/path/to/adlc5/scripts/adlc5 gate --feature my-feature --gate pr-ready --workspace .
/path/to/adlc5/scripts/adlc5 usage summary --feature my-feature --workspace .
```

Usage ledgers are best-effort, self-reported observations. Cost summaries use a
verified price snapshot rather than live billing; unknown models remain unpriced.
Framework version lives in `core/VERSION`; persisted state uses schema `3.0`.

## Supporting skills

| Intent | Invoke |
| --- | --- |
| Requirements discovery | `@discover`, `@prt` |
| Architecture and patterns | `@clean-architecture-review`, `@design-pattern-advisor` |
| Story implementation and verification | `@build-implementer`, `@assure-verifier` |
| Quality and PR review | `@qa`, `@pr-reviewer` |
| Team-shared repository memory | `@adlc5-project-wiki` |
| Infrastructure and authorized deployment | `@infra`, `@deploy` |

These support the lifecycle; they do not add stages. Host plugin namespaces may
prefix invoke names. Use the skill map for the full catalog.

## Maintain this site

The [site maintenance guide](https://github.com/dango-tech/adlc5/blob/main/docs/documentation-site.md)
contains local preview, validation, and GitHub Pages setup instructions.
