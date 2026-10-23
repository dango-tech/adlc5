# Auxiliary skills (`skills/`)

Auxiliary capabilities are **not** separate lifecycle stages. They install with `./scripts/install.sh` alongside core invokables (`adlc5`, `specify`, `plan`, `tasks`, `implement`).

| Aux invoke | Path | Stage |
|------------|------|-------|
| `@discover` | [discover](../discover/SKILL.md) | Specify |
| `@prt` | [prt](../prt/SKILL.md) | Specify |
| `@autoresearch` | [autoresearch](../autoresearch/SKILL.md) | Plan |
| `@build-implementer` | [build-implementer](../build-implementer/SKILL.md) | Implement (subagent) |
| `@assure-verifier` | [assure-verifier](../assure-verifier/SKILL.md) | Implement (subagent) |
| `@adlc5-assure-reworker` | [adlc5-assure-reworker](../adlc5-assure-reworker/SKILL.md) | Implement (subagent) |
| `@qa` | [qa](../qa/SKILL.md) | Implement |
| `@pr-reviewer` | [pr-reviewer](../pr-reviewer/SKILL.md) | Implement |
| `@adlc5-project-wiki` | [project-wiki](../project-wiki/SKILL.md) | Post `pr-ready` |
| `@clean-architecture-review` | [clean-architecture-review](../clean-architecture-review/SKILL.md) | Plan |
| `@design-pattern-advisor` | [design-pattern-advisor](../design-pattern-advisor/SKILL.md) | Plan |
| `@algorithm-advisor` | [algorithm-advisor](../algorithm-advisor/SKILL.md) | Plan |
| `@craftsmanship-code-review` | [craftsmanship-code-review](../craftsmanship-code-review/SKILL.md) | Implement |

Registry: [core/skill-registry.yaml](../../core/skill-registry.yaml)
