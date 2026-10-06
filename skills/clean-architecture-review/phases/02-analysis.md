---
name: analysis
description: Phase 2 — Analysis for S2. Trace dependencies, detect layer leaks, evaluate SOLID and component principles.
---

# Phase 2: Analysis — Clean Architecture Review

## Purpose

Validate the dependency rule and architectural quality for the scoped modules.

## Analysis steps

### 1. Build layer map

For each package/module, assign a layer:

- Entity / domain
- Use case / application
- Adapter (controller, gateway, presenter)
- Framework / driver

Document in a table with notes on ambiguity.

### 2. Trace imports / dependencies

For each inner-layer file, list imports:

- Do any point outward (framework, DB, HTTP)?
- Flag high-severity violations with file path.

Tools: IDE dependency graph, `grep` import statements, build dependency plugins.

### 3. Layer leak scan

Check use cases and entities for:

- ORM annotations or entity manager usage
- SQL strings or query builders
- HTTP request/response types
- Framework-specific base classes

### 4. Screaming architecture

Evaluate folder names:

- Good: `place_order/`, `cancel_subscription/`
- Bad: `controllers/`, `services/`, `models/` only

Note whether use case names appear in structure.

### 5. SOLID at module scale

| Principle | Question |
|-----------|----------|
| SRP | One reason to change per module? |
| OCP | Extension without modifying stable core? |
| LSP | Substitutable port implementations? |
| ISP | Interfaces narrow for clients? |
| DIP | Use cases depend on abstractions? |

### 6. Component principles

- **ADP:** Any dependency cycles between packages?
- **SDP:** Dependencies toward stable abstractions?
- **SAP:** Stable components abstract?

### 7. Humble Object & testability

- Can use cases be unit-tested without DB/UI?
- Are I/O edges thin adapters?

## Severity guide

| Severity | Example |
|----------|---------|
| high | Domain imports Spring/Web/ORM |
| medium | Use case returns framework DTO |
| low | Adapter slightly thick; logic extractable |

## Escalation

- Need pattern for ports/adapters → note for S3/S5
- Hot-path algorithm in domain → note for S3b

Proceed to [03-output.md](03-output.md).
