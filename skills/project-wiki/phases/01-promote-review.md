---
name: project-wiki-promote-review
description: Human promotion review — packet + AskQuestion (Option C).
---

# Promote review

## Gate

- `stage_status.implement: completed`
- human `approved_by` recorded in `approved.json`

## Steps

1. `promote-prepare.sh --feature {feature} --workspace .`
2. Open `wiki/drafts/promote-{feature}/packet.md` — ensure evidence blocks are visible.
3. **AskQuestion** batches from `review-questions.json` (max 2 questions per call).
4. Build `approved.json` from answers; save beside packet.
5. User confirms → `promote-apply.sh --feature {feature}`

## Prompt quality

Each AskQuestion `prompt` must include:

- Candidate id and one-line claim
- Bullet list of evidence paths (from JSON)
- Doc conflict note if present in packet

Do not ask user to type yes/no in chat when options are known.
