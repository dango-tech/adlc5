---
description: "Find ADLC5 releases, upgrade instructions, host support details, and the current public-preview qualification boundary."
---

# Releases and compatibility

## Current maturity

ADLC5 is in public preview. The repository tests workflow contracts, but those
checks do not establish comparative coding quality or live qualification on
every agent host. Read the current
[release notes](https://github.com/dango-tech/adlc5/releases) and
[cross-platform support guide](https://github.com/dango-tech/adlc5/blob/main/shared/docs/CROSS-PLATFORM.md)
for current version-specific details.

Download the [host packages and checksums](downloads.md). Candidate releases are
explicitly marked prerelease; package compatibility is distinct from live agent
qualification.

## Upgrade

Use the procedure for your installation type in the
[installation guide](installation.md). Plugin users should update the installed
package and run `adlc5-setup` again in the application repository. Review the
release notes for state, configuration, or migration changes before upgrading
active workspaces.

## Host support

ADLC5 provides installation adapters and native plugin packages for multiple
coding hosts. Availability of an adapter or package means it can be installed;
it does not by itself establish equivalent lifecycle validation or unattended
execution support. Check the
[cross-platform support guide](https://github.com/dango-tech/adlc5/blob/main/shared/docs/CROSS-PLATFORM.md)
for the latest host-specific evidence and limitations.

## Readiness claims

Story verification, `pr-ready`, deployment, and live host qualification are
distinct states. A passing local check or CI run does not prove production
deployment or live qualification. See
[completion limits](lifecycle.md#what-completion-establishes) before relying on
a readiness claim.
