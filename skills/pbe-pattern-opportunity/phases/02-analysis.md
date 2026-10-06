---
name: analysis
description: Phase 2 — Analysis for S4. Find recurrences and apply Rule of Three.
---

# Phase 2: Analysis — Pattern Opportunity

## Purpose

Identify candidate patterns with evidence and unique-context count.

## Analysis steps

### 1. Scan for repeated shapes

Look for:

- Similar class structures across modules
- Copy-pasted integration code
- Repeated review comments ("we always do X this way")
- Parallel switch/if chains on same force

### 2. Abstract problem statements

For each recurrence, write context-free problem:

- Bad: "Campaign export retry"
- Good: "Reliable async handoff with idempotent retry when downstream is unavailable"

### 3. Count unique contexts

For each candidate:

| # | Context | Evidence (link/path/ticket) |
|---|---------|----------------------------|

Mark contexts **unique** only if genuinely distinct situations.

### 4. Rule of Three evaluation

| Candidate | Count | Meets Rule of Three? |

### 5. Classify scope

Architectural | design | idiom — large-scope first.

### 6. Exemplar pointers

Best 1–3 code references per candidate for S10.

### 7. Antipattern guard

Drop candidates that are:

- One-off hacks
- Thin wrappers over library
- Pattern name without structural recurrence

Proceed to [03-output.md](03-output.md).
