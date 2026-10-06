---
okf_version: "0.2"
---

# ADLC5 craftsmanship catalog (OKF)

OKF v0.2 knowledge bundle for tool-efficient pattern and algorithm selection during ADLC5 code generation.

**Hard load rules:**

1. Read **this file** (or one group `index.md`) — never dump the whole catalog into context.
2. Prefer `./scripts/adlc5 patterns lookup --tags …` for matching **ids/paths** before opening cards.
3. Open **at most 1–3** concept `.md` files that match current problem tags.
4. Open linked knowledge-base essays **only if** the card is insufficient.
5. Cite concept **ids** in design docs; do not paste card bodies into Build/implementer packs unless the story names a pattern.

**Concept ID** = path relative to this bundle without `.md` (example: `gof/strategy`, `algorithms/sorting`).

**Spec:** [Open Knowledge Format v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)

# Bundles

* [GoF / HFDP design patterns](gof/) - Structural design pattern cards for `@design-pattern-advisor`
* [CLRS algorithm decisions](algorithms/) - Decision tables for `@algorithm-advisor`
* [PBE meta-patterns](pbe/) - Pattern-as-asset practices for PBE skills
* [Clean Architecture](architecture/) - Boundary principles for `@clean-architecture-review`
* [Clean Code](clean-code/) - Tactical principles for review / TDD skills

# How to search

1. Match NFR / concern tags via `./scripts/adlc5 patterns lookup --tags …` (or frontmatter `requirements_tags` / `tags` on 1–3 cards).
2. Prefer `status: stable` concepts; treat `draft` as advisory.
3. Follow markdown links for related patterns; open KB paths only for deep rationale.
4. Org-specific ROI-approved assets may be added beside these community seeds (S4 → S8 → S7).
