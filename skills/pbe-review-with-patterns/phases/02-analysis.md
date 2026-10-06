---
name: analysis
description: Phase 2 — Analysis for S6. Verify pattern roles and density in code.
---

# Phase 2: Analysis — PBE Review with Patterns

## Purpose

Compare observed structure to pattern roles and collaborations.

## Analysis steps

### 1. Claimed vs observed table

For each pattern:

| Pattern | Claimed role | Observed type/module | Match? |

### 2. Role verification

Map pattern roles to code symbols:

- Strategy: Context, Strategy interface, ConcreteStrategies
- Observer: Subject, Observer interface, notify loop
- Repository: Port interface, adapter implementation

### 3. Variability points

Does code allow variation where S5/S7 specified?

- Switch on type → likely misaligned Strategy
- Public concrete deps → DIP violation for pattern

### 4. Density check

Do combined patterns integrate as in S5 density notes?

### 5. Drift classification

| Severity | Example |
|----------|---------|
| major | Missing Strategy interface; concrete classes in use case |
| minor | Naming doesn't use pattern vocabulary but structure OK |

### 6. Target state sketch

If partial/misaligned, describe **incremental** steps using pattern names.

### 7: Escalations

- Layer issue → S2
- Smell → S1
- Complexity → S3c

Proceed to [03-output.md](03-output.md).
