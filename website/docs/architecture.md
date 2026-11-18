---
description: "See how the engineer, host, ADLC5 kernel, worker, and consumer repository fit together."
---

# How ADLC5 works inside your repo

The engineer works through an agent host. A runner and host adapter launch scoped agent work; the worker reasons, edits and reviews. The ADLC5 kernel validates gates and advances feature state. The consumer repository holds the project's inputs and evidence across sessions.

<div class="architecture" aria-label="ADLC5 architecture">
<div class="architecture-row"><strong>Engineer</strong><span>↓</span><strong>Agent host · Claude Code, Codex, Cursor or Hermes</strong></div>
<div class="architecture-row"><span>CLI or MCP ↓</span><strong>ADLC5 kernel · validates gates and advances state</strong></div>
<div class="architecture-row"><strong>Runner and host adapter</strong><span>→ launches scoped work →</span><strong>Agent worker · reasons, edits, reviews</strong></div>
<div class="repo-boundary"><strong>Consumer repository</strong><ul><li>Reviewed constitution and repository index provide focused context.</li><li>Feature intent, decisions and stories guide the worker.</li><li>Source code and declared tests produce check results.</li><li>Feature state, evidence and usage ledger preserve recorded progress.</li></ul></div>
<div class="architecture-row"><strong>Pulse · recorded progress, evidence and usage</strong><span>→ suggested next action →</span><strong>Engineer</strong></div>
</div>

The runner submits results to the kernel; test results are evidence for its checks. The kernel records feature state and evidence, which Pulse reads on demand. The host and worker do not replace the kernel's progression checks. Repository indexes are derived context, while reviewed guidance and feature artifacts carry the team's intent. See [Intelligence](intelligence.md), [Pulse](pulse.md), and the [kernel reference](https://github.com/dango-tech/adlc5/blob/main/docs/ADLC5-kernel.md).
