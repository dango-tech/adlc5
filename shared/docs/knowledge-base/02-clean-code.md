## Part II — Clean Code

*Source: Robert C. Martin, Prentice Hall 2008 (462 pp.).*

### II.1 Core message

**Craftsmanship = knowledge + practice.** Clean code is readable, changeable, and tested. Bad code compounds cost (“total cost of owning a mess”). There is no reasonable excuse for doing less than your best.

**Boy Scout Rule:** Leave the code cleaner than you found it.

**Authors:** Code is written for human readers; you are an author.

### II.2 Part 1 — Principles (Ch 1–12)

| Chapter | Agent-relevant guidance |
|---------|-------------------------|
| **1 — Clean Code** | Professionalism; cost of mess; clean = readable + changeable |
| **2 — Meaningful names** | Intention-revealing; searchable; no encodings/Hungarian; one word per concept; no puns; minimal context |
| **3 — Functions** | Small; **do one thing**; one abstraction level; **stepdown rule** (read top-to-bottom); few arguments; no flag args; no side effects |
| **4 — Comments** | Explain *why*, not what; legal/docs OK; don't comment bad code—rewrite |
| **5 — Formatting** | Consistent layout; vertical density; team rules |
| **6 — Objects vs data** | Hide data; prefer polymorphism to `(structure, switch)` |
| **7 — Error handling** | Use exceptions; don't return/pass null; wrap third-party APIs |
| **8 — Boundaries** | Isolate foreign code; **learning tests** for APIs you don't control |
| **9 — Unit tests** | **FIRST:** Fast, Independent, Repeatable, Self-validating, Timely; one assert per concept; test code as clean as prod |
| **10 — Classes** | SRP; small classes; **DIP** for testability (depend on interfaces) |
| **11 — Systems** | Separate construction from use; DI at composition root |
| **12 — Emergence** | Clean design emerges when: all tests pass → no duplication → expresses intent → minimal elements |

### II.3 Part 2 — Case studies

Refactoring is **stepwise** with documented heuristics—not big-bang rewrites. Agents should change in small verifiable steps and cite which heuristic drove each change.

### II.4 Part 3 — Smells and heuristics (Ch 14)

High-value for PR review skills. Sample heuristics (see book Appendix C for full list):

| ID | Heuristic | Agent action |
|----|-----------|--------------|
| G5 | Duplication | Extract; DRY |
| G6 | Code at wrong abstraction level | Move up/down layer |
| G14 | Feature envy | Move method to right class |
| G23 | Prefer polymorphism to switch | Strategy/state |
| G30 | Functions do one thing | Split |
| F1 | Too many arguments | Parameter object |
| F4 | Dead function | Remove |
| N1 | Non-descriptive names | Rename |
| T1–T9 | Test insufficiency | Add boundary/fast tests |

### II.5 Clean Code ↔ Cursor

| Gap | Needed artifact |
|-----|----------------|
| `clean-code.mdc` is partial | Expand or add `cc-functions-and-tests.mdc` |
| Review without smell IDs | `craftsmanship-code-review` skill |
| AI slop vs intentional style | `ai-slop-cleanup` for noise; CC for structure |

---

