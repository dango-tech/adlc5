# Documentation website

The six curated user pages live in `website/docs/`. `mkdocs.yml` supplies the
navigation, Material theme, search, code copying, and light/dark palettes. Brand
assets are shared through `website/docs/assets/brand`, a relative symlink to
`assets/brand/`. Edit the original assets rather than creating copies.

## Preview and validate

From the repository root (Python 3.10+):

```bash
python3 -m venv .venv-docs
. .venv-docs/bin/activate
python -m pip install -r requirements-docs.txt
python -m mkdocs serve
```

Open the local URL printed by MkDocs. Check narrow-screen navigation, search,
code copying, and both palettes. Before submitting changes:

```bash
python -m mkdocs build --strict
python scripts/tests/test-docs-site.py
git diff --check
```

The tests build in a temporary directory and check generated local links,
fragments, assets, search entries, and the six-page navigation. To validate an
existing build, use `python scripts/tests/test-docs-site.py --site-dir site`.
The separate docs dependencies are not required by the framework's baseline
contract suite. `.venv-docs/`, `site/`, and local lifecycle evidence stay untracked.

## Host with GitHub Pages

After reviewing and merging the website changes:

1. In the repository's **Settings → Pages**, choose **GitHub Actions** as the source.
2. Check the `github-pages` environment's deployment branch policy permits your
   default branch. Add required reviewers if publication should need approval.
3. Run the **Documentation** workflow on the default branch, or push a change there.
4. Read the deployed URL from the workflow's deployment environment after it succeeds.

Pull requests build and validate without deploying. Deployment depends on a passing
build and runs only on the default branch, including manual runs. The deploy job
alone receives Pages and OIDC write permissions. The build job reads Pages metadata
on publishable runs so project subpaths and forks use the configured `base_url`.

For a local build targeting another URL:

```bash
DOCS_SITE_URL=https://example.github.io/my-repo/ python -m mkdocs build --strict
```

Keep the trailing slash and use relative links between site pages. On a fork,
also update `repo_url` and the canonical repository links if maintaining a separate
documentation authority. No custom domain or external font service is configured.

Creating this workflow does not establish live publication. GitHub Pages setup,
remote workflow checks, and an actual deployed URL require separate verification.
See [GitHub's publishing-source guide](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).
