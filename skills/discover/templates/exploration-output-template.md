---
name: exploration-output-template
description: Structured format that all LLM Council members must follow when responding to exploration briefs. The orchestrator parses responses using this exact structure. For risk challenge output format, see the inline format in phases/02b-risk-challenge.md.
---

# Council Output Template

**IMPORTANT:** You MUST respond using exactly this structure. Do not add sections, remove sections, rename headings, or change the format. The orchestrator that reads your response depends on this exact structure to perform synthesis across multiple council members.

---

## Solution Directions

Propose 2-3 distinct solution directions. Each direction should make different fundamental trade-offs — do not propose variations of the same approach.

Use this structure for each direction:

---

### Direction [N]: [Short, Descriptive Name]

**Approach Summary**

In 3-5 sentences: what is this direction? What is the core mechanism? How does it address the problem framing? Be concrete — avoid abstractions like "a platform that enables X." Describe what someone would actually build.

**Key Trade-offs**

What are the major trade-offs this approach makes? Format as a table:

| Gain | Cost |
|------|------|
| {what this direction gets you} | {what you give up or take on} |
| {gain 2} | {cost 2} |

Include 2-4 rows. Be specific — vague trade-offs like "flexibility" are not useful.

**Risks**

List 2-3 risks specific to this direction (not general risks that apply to any approach):

- **[Risk name]:** {brief description of what could go wrong and why}
- **[Risk name]:** {brief description}

**Estimated Complexity**

`Low` | `Medium` | `High` | `Very High`

Brief justification (1-2 sentences): why this complexity estimate?

**Who Benefits Most**

Who specifically would benefit most from this direction? Be precise about the role and what changes for them.

---

*(Repeat for Direction 2, Direction 3)*

---

## Cross-Cutting Observations

Note anything that applies across all directions or to the problem space generally — patterns you noticed, constraints that seem important regardless of direction, or questions that need to be answered before any direction can succeed.

Format as bullet points:

- {observation 1}
- {observation 2}
- {observation 3}

---

## Your Strongest Recommendation

If you were advising someone with the constraints described in the framing, which of your directions would you prioritize and why? (2-3 sentences — be direct.)

---

**END OF RESPONSE. Do not add anything after this line.**
