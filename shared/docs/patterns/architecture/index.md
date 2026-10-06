# Clean Architecture principles

Load **≤3** concepts after lookup. Do not paste this whole list into chat. Deep essay (on demand): `../knowledge-base/03-clean-architecture.md`.

* [Dependency Rule](dependency-rule.md) - Source dependencies point inward; inner circles know nothing about outer.
* [Screaming Architecture](screaming-architecture.md) - Project structure should scream use cases, not framework names.
* [Humble Object](humble-object.md) - Push hard-to-test edges behind boundaries; keep core unit-testable.
* [Ports and Adapters](ports-and-adapters.md) - Depend on ports (interfaces); adapters implement details outward.
