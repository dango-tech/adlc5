# Publication guardrails

Keep private development material outside this repository. Commit metadata must
use a GitHub noreply email. Do not import original repository ancestry or old PRs.

Enable the local gate in each clone:

```bash
git config core.hooksPath .githooks
git config user.email YOUR_GITHUB_NOREPLY_EMAIL
python3 scripts/check-publication.py --self-test
python3 scripts/check-publication.py
```

The pre-commit gate also checks the proposed author/committer identity. The pre-push gate scans the index, reachable history and commit emails/messages.
It rejects real home paths, non-public literal emails, recognizable credentials,
private artifact links, development plans, session state and caches. Only public
noreply identities and explicitly synthetic example email domains are accepted.
Reports identify files/commits without printing matched private content.

CI runs the same gate before release qualification. Protect main with required
privacy and OS test checks, PR review, no force pushes and no branch deletion.
Enable GitHub secret scanning and push protection when supported by the account.
Local hooks can be bypassed; CI notices pushed content after it reaches GitHub.
Native push protection covers supported secret types, not arbitrary personal
information. These layers reduce risk; they cannot guarantee that every private
value is detected. Review every imported file and commit before publishing.
