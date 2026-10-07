# Public preview distribution

ADLC5 ships the kernel, skills, templates, knowledge-base summaries, supported
host adapters, and portable examples/tests. Workflow enforcement and installation
have automated checks; comparative coding quality and newcomer usability remain
unqualified. See [evaluation](evaluation.md).

## Contents

`.cursor-plugin/` is the plugin package. `.cursor/rules`, `.cursor/agents`,
`.cursor/hooks`, `.claude/hooks` and `.codex/hooks` plus their hook configuration
files are product assets consumed by installers. They are intentionally retained.
Local lifecycle trees, caches, sessions, credentials, editor state and development
plans are excluded from distribution. Public documentation does not depend on
local development material.

Native `git archive` and GitHub source archives honor `.gitattributes`: development
plans, root developer instructions, GitHub maintenance configuration and local
state are excluded. Product adapters and runnable tests remain included. Create
a release archive from a reviewed commit with:

```bash
git archive --format=tar.gz --prefix=adlc5/ HEAD > /tmp/adlc5-source.tar.gz
python3 scripts/tests/test-distribution.py
```

Do not package a working directory with `tar` or ZIP: ignored local files may
contain credentials or session data. A source archive is not a standalone Git
checkout; baseline-comparison preparation needs the documented repository history.

## Publication checks

Review the complete Git history and release archive for private material and
redistribution rights before publishing. Ignoring or untracking a file does not
remove previous commits or hosted artifacts. Revoke any exposed credentials.
See [publication guardrails](publication-guardrails.md) for contributor checks
and their limitations.
