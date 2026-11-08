# Host qualification cycles

Track per-host qualification. Update after each cycle.

| Host | Mode | Scenario A (question→resume) | Scenario B (changed intent) | Full Specify→PR | Status |
|---|---|---|---|---|---|
| Codex | confined | passed | passed | pending | partial |
| Claude Code | confined | passed (after repair) | passed | pending | partial |
| Cursor | confined | passed | passed | pending | partial |
| Hermes | attended | passed | not executed | pending | partial |

**Cycle definition**: run both scenarios + one full Specify→PR delivery on a
disposable consumer, record model IDs, usage, failures. Repeat per OS for the
matrix. Hermes unattended stays gated on container detection.
" 