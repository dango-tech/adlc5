
# Clean Architecture (R2)

**Architecture = boundaries + dependency direction.** Fight for the architecture alongside features.

## Dependency rule

Source code dependencies point **inward**. Inner circles know nothing about outer circles.

## Layers (inside → outside)

1. **Entities** — enterprise business rules
2. **Use cases** — application-specific business rules
3. **Interface adapters** — controllers, presenters, gateways, mappers
4. **Frameworks & drivers** — DB, UI, web, devices — **details**

## Agent rules

- **Frameworks are details** — Don't marry the framework; don't let ORM/SQL shapes leak into use cases.
- **Database is a detail** — Persistence belongs in adapters; domain logic stays framework-free.
- **Screaming architecture** — Project structure should scream **use cases**, not "Rails", "Spring", or folder-by-tech.
- **Policy vs detail** — Inner = high-level policy (stable); outer = pluggable mechanisms.
- **Humble Object** — Push hard-to-test edges (UI, DB) behind boundaries; keep core logic unit-testable.

## Review checks

- Import direction violates dependency rule?
- Business logic in controllers or framework hooks?
- Package/folder layout organized by framework instead of use case?

**Reference:** `shared/docs/playbook.md` Part III (Clean Architecture).
