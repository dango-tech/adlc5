# OpenAI / Codex public submission preparation

This package targets local Codex workflows. It is a public preview, not a claim
of comparative coding quality or production qualification. Claude and Cursor
submission work is separate.

## Source of truth and build

`plugin.json` owns the OpenAI listing, review cases and publication settings.
The Codex builder preserves those settings and copies the listing and review
metadata into `.codex-plugin/plugin.json` for compatibility. Edit the root
manifest first; keep the checked-in compatibility manifest synchronized.

```bash
python3 scripts/package-plugin.py --host codex --out /tmp/adlc5-codex-submission
python3 scripts/tests/test-codex-plugin.py
```

The ZIP has a root manifest, bundled skills, local stdio MCP server, hooks,
kernel and icon. It needs Git, Bash, Python 3.10+ and jq on the user's machine.
No ADLC5 account, payment, remote MCP service or plugin API key is required.
The agent host and optional external tools have their own access requirements.

Confirmed by the publisher on 2026-10-28: Dango Tech, all available countries,
no commerce. The manifest uses `countries: []` to remove country restrictions.
The portal must still verify the selected publisher identity.

## Current evidence

Local checks on 2026-10-28:

- Codex package tests: passed, including ZIP listing preservation, compatibility
  metadata, PNG dimensions/size, local-executor declaration, forbidden app
  bindings, relocated stdio protocol, safety annotations and invalid arguments.
- Existing four-host installation tests, distribution checks and CI-selection
  tests: passed. This does not qualify Claude or Cursor directory submissions.
- Shared Claude plugin regression suite: 35 tests passed after the common
  packager/MCP metadata changes.
- Codex CLI 0.162.1: generated marketplace registered and plugin installed in an
  isolated `CODEX_HOME`; normal user configuration was not changed.
- Extracted package: consumer setup and `submission-demo` initialization passed
  in a disposable Git repository with an isolated home.
- Five review tool fixtures: version returned the packaged version; Pulse
  returned an honest partial snapshot; state read returned Specify in progress;
  clarity reported a heuristic with no gate authority; index check reported
  `stale` / `missing cache` for a separate unindexed repository.
- Website and support URLs: fetched publicly, followed redirects and inspected
  product/support content. Both redirect to `www.adlc5.dev`.

These are direct tool/CLI checks. Model-selected tool use, the three negative
prompts, desktop UI installation, trusted hook dispatch, the recorded demo,
portal scans and remote CI for this patch remain unverified.

## Reproducible review setup and demo

Use a disposable Git repository, never a production customer repository.
From the installed package, run `scripts/plugin-setup.sh --host codex --project
<consumer>` and `scripts/init-feature.sh --feature submission-demo --workspace
<consumer>`. Review generated scaffolding. Create `spec.md` containing:

```markdown
# Export delivery status
As a developer I want a local JSON status report.
Acceptance: the command prints JSON and does not change workflow state.
```

Use a second disposable Git repository without setup/index generation for the
missing-index case. Run the five natural prompts in
`extensions.com.openai.review.test_cases.positive`; supply the appropriate
repository as the local thread workspace. Then run the three negative prompts
and confirm that no ADLC5 MCP tool is invoked and no success is fabricated.
The case descriptions contain expected tool names, setup and observable results.

For a 2–3 minute recording, show the installed release, consumer setup, then
version, Pulse and state responses; show the clarity limitation and the
missing-index recovery message, and one unsupported request. Use actual
responses, keep paths and private material off screen, and leave results
readable. Computer control does not itself record video: use a screen recorder,
play back the result, and host it where reviewers can view without requesting
access. Set the verified URL in `review.demo_recording_url` and rebuild.
A script or this walkthrough is not a completed recording.

## Remaining submission requirements

1. Review and publish privacy and terms pages. Shared policy page candidates and unresolved
   publisher decisions are tracked in [policy review](codex-submission/policy-drafts.md).
   Inspect the published pages, then set `interface.privacyPolicyURL` and
   `interface.termsOfServiceURL` in the root manifest and compatibility manifest.
   They are intentionally absent until real published URLs exist.
   The candidate `https://adlc5.dev/privacy/` and `https://adlc5.dev/terms/`
   both returned HTTP 404 during this preparation run.
2. Run the model-level review cases in the intended desktop host; record pass,
   fail or blocked evidence. Verify a real recording and include its URL.
3. Confirm local MCP submission eligibility. Find the submitting organization ID
   in OpenAI Platform organization settings; ask your OpenAI representative to
   confirm approval and allowlisting. Eligibility is currently unknown.
4. Rebuild and inspect the exact final ZIP. Complete developer/business identity
   verification, domain verification where required, portal scans and legal
   attestations. Do not infer those from local package checks.

After allowlisting and complete materials, follow the desktop-only guide: choose
Create plugin → Skills only → Upload ZIP (including the local MCP configuration).
Inspect imported listing, country availability and review metadata. Upload,
submission for review and publication are separate actions; none was performed
by this preparation work. Do not remove local MCP behavior merely to bypass the
allowlist requirement.

Official references (checked 2026-10-28):
[package format](https://developers.openai.com/plugins/build/plugins),
[submission fields and review](https://developers.openai.com/plugins/deploy/submission),
[desktop-only eligibility](https://developers.openai.com/plugins/deploy/desktop-only).
