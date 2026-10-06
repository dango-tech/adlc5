## Part III — Clean Architecture

*Source: Robert C. Martin, Prentice Hall 2017 (429 pp.).*

### III.1 Core message

**Architecture = boundaries + dependency direction.** Two values: **behavior** (features) and **architecture** (structure). Both matter—**fight for the architecture** (important but not always urgent).

Design is what happens at every level; architecture is design at the scale where **boundaries** and **policy** dominate.

### III.2 SOLID at architecture scale (Ch 6–11)

Same principles as class-level SOLID, applied to **modules and components**:

| Principle | Architectural meaning |
|-----------|----------------------|
| **SRP** | One reason to change per module |
| **OCP** | Extend via new types, not editing stable core |
| **LSP** | Substitutable implementations across boundaries |
| **ISP** | Many small interfaces; no fat ports |
| **DIP** | High-level policy does not depend on low-level detail |

### III.3 Component principles (Ch 12–14)

| Principle | Rule for agents |
|-----------|---------------|
| **REP** | Reuse only from releasable components |
| **CCP** | Package what changes together |
| **CRP** | Don't force unrelated reuse |
| **ADP** | No cycles in component graph |
| **SDP** | Depend toward more stable components |
| **SAP** | Stable components should be abstract |

### III.4 Clean Architecture (Ch 22)

**Dependency Rule:** Source code dependencies point **inward**. Inner circles know nothing about outer circles.

**Concentric layers (inside → outside):**

1. **Entities** — enterprise business rules
2. **Use cases** — application-specific business rules
3. **Interface adapters** — controllers, presenters, gateways, mappers
4. **Frameworks & drivers** — DB, UI, web, devices — **details**

**Policy vs detail:** Inner = high-level policy (stable). Outer = mechanisms (pluggable).

**Screaming architecture:** Structure of a project should **scream** its use cases—not “Rails”, “Spring”, or “ASP”.

**Frameworks are tools, not architecture.** Don't marry the framework.

**Database is a detail.** No ORM entities or SQL shapes in use cases.

**Tests:** Outermost ring; depend inward; avoid tests that require GUI or DB when unit suffices.

**Services:** Microservices alone do not define architecture. Boundaries run **through** services; each service needs internal Clean Architecture.

**Humble Object:** Push hard-to-test edges (UI, DB) behind boundaries; keep core logic testable.

### III.5 Other architectural topics (select)

| Topic | Agent takeaway |
|-------|----------------|
| Independence (Ch 16) | Decouple use cases, layers, deployment modes |
| Boundaries (Ch 17–18) | Draw lines early; plugin architecture; boundary crossings are expensive |
| Policy and level (Ch 19) | Higher policy = higher in the diagram |
| Presenters (Ch 23) | Format data for views in adapter layer |

### III.6 Clean Architecture ↔ Cursor

| Gap | Needed artifact |
|-----|----------------|
| No dependency rule in rules | `clean-architecture.mdc` |
| Layer leaks in PRs | `clean-architecture-review` skill |
| Package by framework | Screaming architecture in reviews |

---

