
# Design Principles (slim)

Detailed guidance lives in craftsmanship rules **R2–R5** and `shared/docs/playbook.md`. Use this file as a quick orientation only.

## Where to look

| Concern | Rule | Playbook |
|---------|------|----------|
| Layers, dependency direction, screaming architecture | R2 `clean-architecture.mdc` | Part III |
| Functions, tests, smells, Boy Scout | R3 `cc-functions-and-tests.mdc` | Part II |
| GoF patterns, composition, interfaces | R4 `oo-design-principles.mdc` | Part IV |
| O(·), hot paths, decision tables | R5 `algorithm-complexity.mdc` | Part V |
| Pattern assets, Rule of Three, catalog ROI | R0, R1 | Part I |

## SOLID (summary)

- **SRP** — One reason to change per module/class
- **OCP** — Extend via new types, not editing stable core
- **LSP** — Substitutable implementations across boundaries
- **ISP** — Many small interfaces; no fat ports
- **DIP** — Depend on abstractions; high-level policy independent of details

## Layer roles (summary)

- **Controllers/adapters** — HTTP, I/O, validation, response formatting
- **Use cases / services** — Business logic, orchestration
- **Repositories / gateways** — Data access and external calls
- **Models/DTOs** — Data structures and validation rules

Do not duplicate R2–R5 content here.
