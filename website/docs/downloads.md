---
description: "Download ADLC5 host plugin packages for Windows, macOS, and Ubuntu, with checksums and installation instructions."
---

# Download ADLC5 plugins

ADLC5 is public preview. These **5.1.0 candidate packages** are distributed through
[GitHub Releases](https://github.com/dango-tech/adlc5/releases/tag/v5.1.0).
The same Python/source archives serve Windows, macOS and Ubuntu; choose your
**agent host**, rather than a CPU architecture. They contain no bundled Python,
Bash or agent executable. Native agent availability depends on the host vendor.

| Agent | ZIP (all three operating systems) | tar.gz (macOS / Ubuntu) |
| --- | --- | --- |
| Codex | [Download ZIP](https://github.com/dango-tech/adlc5/releases/download/v5.1.0/adlc5-codex-plugin-5.1.0.zip) | [Download tar.gz](https://github.com/dango-tech/adlc5/releases/download/v5.1.0/adlc5-codex-plugin-5.1.0.tar.gz) |
| Claude Code | [Download ZIP](https://github.com/dango-tech/adlc5/releases/download/v5.1.0/adlc5-claude-code-plugin-5.1.0.zip) | [Download tar.gz](https://github.com/dango-tech/adlc5/releases/download/v5.1.0/adlc5-claude-code-plugin-5.1.0.tar.gz) |
| Cursor | [Download ZIP](https://github.com/dango-tech/adlc5/releases/download/v5.1.0/adlc5-cursor-plugin-5.1.0.zip) | [Download tar.gz](https://github.com/dango-tech/adlc5/releases/download/v5.1.0/adlc5-cursor-plugin-5.1.0.tar.gz) |
| Hermes Agent | [Download ZIP](https://github.com/dango-tech/adlc5/releases/download/v5.1.0/adlc5-hermes-plugin-5.1.0.zip) | [Download tar.gz](https://github.com/dango-tech/adlc5/releases/download/v5.1.0/adlc5-hermes-plugin-5.1.0.tar.gz) |

[Download SHA256SUMS](https://github.com/dango-tech/adlc5/releases/download/v5.1.0/SHA256SUMS).
Each archive contains `INSTALL.json` with host, version and exact source commit.
Use the release's validation link for OS test results. Checks cover archive
integrity, extraction, installer plans and preservation; they do not establish
live end-to-end qualification for every host/OS combination.

## Prerequisites and installation

Install Python 3.10+, Git, Bash 3.2+ and jq, plus your selected agent. On Windows,
use Git for Windows Bash (not the WSL launcher), put its `bin` directory and jq
on PATH, and ensure `python3` resolves to the installed Python for kernel commands.
WSL2 Ubuntu is a separate Linux environment: install the agent and dependencies
inside it rather than mixing Windows and WSL paths. Hermes documents both [native Windows](https://hermes-agent.nousresearch.com/docs/user-guide/windows-native)
and WSL2 installation; install its CLI in the same environment as ADLC5.

Extract the ZIP to an empty folder. From that folder:

```bash
# macOS / Ubuntu / WSL2
python3 install.py --dry-run
python3 install.py
```

```powershell
# Windows PowerShell: Python installer entry point
py -3 install.py --dry-run
py -3 install.py
```

The dry run writes nothing. Codex registers a local marketplace; finish installation
in its Plugins UI. Claude Code registers and installs through its CLI. Cursor
stages its local plugin; reload and review enablement. Hermes uses its native
scanner and installs with enablement off; review before enabling. Existing
unmanaged Cursor destinations are refused; managed replacements retain a backup.

For ZIP extraction on Windows, use `Expand-Archive`; macOS and Ubuntu can use
`unzip`. tar.gz archives contain a top-level directory; enter it before running
`install.py`. Restore executable bits with tar.gz if your ZIP extractor does not
preserve them on Unix. Compare `Get-FileHash -Algorithm SHA256`, `shasum -a 256`
(macOS), or `sha256sum` (Ubuntu) with SHA256SUMS before installing.

After host installation, run `adlc5-setup` in your application repository. Read
[the full plugin guide](https://github.com/dango-tech/adlc5/blob/main/docs/agent-plugins.md)
for build-from-source, host registration and updates, and
[bounded live qualification](https://github.com/dango-tech/adlc5/blob/main/docs/live-host-qualification.md)
for tested scenarios. The comparative 144-run campaign remains unexecuted.
