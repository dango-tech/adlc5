# Piecemeal Implementation — [pattern-id]

**Date:** [YYYY-MM-DD]  
**ADLC5 stage:** Catalog (Production)

---

## MVP delivered

| Artifact | Path | Covers variability |
|----------|------|-------------------|
| Skill | `skills/outbox-relay/SKILL.md` | transport=polling |

---

## Deferred (v1.1+)

- Webhook push transport variant
- Codegen for outbox table migration

---

## Invoke

@outbox-relay

---

## Verification

- [ ] Dry-run on exemplar `services/billing/outbox/`
- [ ] Linked from `docs/patterns/outbox-relay.md`
- [ ] Playbook skill map updated (if applicable)

---

## v1.0 limitations

Polling transport only; single-region assumption documented in skill.
