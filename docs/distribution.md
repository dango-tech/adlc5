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
plans are ignored. Development plans are preserved locally but removed from tracking;
public documentation does not depend on them. The root agent guide contains
framework guidance only, without maintainer preferences.

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

## Before changing repository visibility

Check the complete Git history, not only the current tree, for secrets, personal
paths/emails, private consumer material and redistribution rights. Ignoring or
untracking a file does not remove previous commits, PRs or hosted artifacts.
If an actual secret is found, revoke it and remove exposed copies before publishing.
History rewriting and repository visibility changes require a separate explicit
action; this cleanup does neither. Choose a release version/tag and publish notes
that retain the preview qualification.

This repository uses independently authored snapshots: a sanitized evaluation
baseline and the current framework. No original commit ancestry, PRs or private
commit-email metadata were imported. The original repository remains private.

See [publication guardrails](publication-guardrails.md). These checks are bounded
heuristics; human review and native secret scanning remain necessary.
