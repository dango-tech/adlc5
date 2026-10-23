---
description: "Troubleshoot common ADLC5 setup and delivery issues, then route questions and bug reports to the right place."
---

# Support and troubleshooting

## Installation or plugin does not appear

Confirm you installed the host package for the host you are using, then restart
or reload that host. After installation or update, run `adlc5-setup` from the
application repository. Follow the host-specific steps in the
[plugin installation guide](https://github.com/dango-tech/adlc5/blob/main/docs/agent-plugins.md).

## Commands use the wrong repository

Run lifecycle and kernel commands from the application repository and pass its
workspace explicitly when needed:

```bash
/path/to/adlc5/scripts/adlc5 state get --feature my-feature --workspace .
```

The ADLC5 distribution checkout contains framework code; feature state belongs
in the application repository's `.adlc5/` directory.

## A gate is failing

Treat the gate output as a list of missing or stale evidence. Review the named
artifacts and current test results, fix the underlying issue, then rerun the
gate. Do not edit lifecycle state to claim a check passed. See
[completion evidence](lifecycle.md#what-completion-establishes) for what each
readiness status establishes.

## An agent stopped or a run needs to resume

Check the current branch/worktree and feature state before continuing. Read the
feature's memory index and latest gate output, then resume from the recorded
stage. Do not assume a stopped run completed its last command.

## Ask a question or report a bug

- Use [GitHub Discussions](https://github.com/dango-tech/adlc5/discussions) for
  questions, ideas, or workflow feedback.
- Use [GitHub Issues](https://github.com/dango-tech/adlc5/issues) for a reproducible
  defect or actionable request.

Include the ADLC5 release, agent host and version, operating system, exact
reproduction steps, expected and actual behavior, and relevant redacted output.
Never post access tokens, secrets, private repository content, or personal data
in a public issue. For security concerns, use
[GitHub's private vulnerability reporting](https://github.com/dango-tech/adlc5/security/advisories/new)
when enabled for the repository.
