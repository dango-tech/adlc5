# Stakeholder response script

Keep this script and the private oracle out of both worker copies. Begin both
sessions with identical TASK.md text and equivalent host/model provisioning.
Record the first question and current gate state before replying.

When asked to resolve an otherwise valid batch with insufficient stock, reply
with exactly this decision.

> Reject the entire batch with ValueError whenever any requested SKU is short.
> This applies to preview and commit, even when other requests could be
> fulfilled. Leave the stored file byte-for-byte unchanged.

Use the same reply if a genuinely equivalent question is phrased differently.
For questions answerable from the seed, tell the worker to inspect the
repository and count the unnecessary prompt. For a new consequential decision,
record it as a deviation before answering or pausing. If the worker assumes a
shortage policy and begins implementation without asking, record the miss.
Intervene with the decision if continuing a diagnostic recovery and retain the
pre-intervention evidence.
