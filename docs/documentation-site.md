# Documentation website

The curated site lives in `website/docs/`. `mkdocs.yml` defines navigation,
Material styling, search, and the production canonical URL. The public Vercel
deployment serves only the generated `site/` directory. Edit original brand
assets under `assets/brand/`; the site shares them through a relative symlink.

## Preview and validate locally

From the repository root (Python 3.10+):

```bash
python3 -m venv .venv-docs
. .venv-docs/bin/activate
python -m pip install -r requirements-docs.txt
python -m mkdocs serve
```

Before submitting changes, run:

```bash
python -m mkdocs build --strict
python scripts/tests/test-docs-site.py
git diff --check
```

The documentation workflow runs strict build and site checks on PRs and pushes.
It does not publish the site. `.venv-docs/`, `.vercel/`, and `site/` are local
or generated files.

## Vercel project setup

Create one Vercel project connected to `dango-tech/adlc5`, with repository root
as its root directory. Keep the framework preset as **Other**. `vercel.json`
uses Vercel's `uv`-managed Python environment to install the pinned docs
dependencies, run a strict MkDocs build, and publish the `site` output
directory. `vercel.json` disables Git-triggered deployments, while
leaving Vercel CLI deployments from the manual GitHub Actions workflow enabled.

In GitHub repository settings, create `private-preview` and `production`
environments. Add these environment variables to each:

- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

Add `VERCEL_TOKEN` as an environment secret. Use a token scoped to the intended
Vercel team/project. Configure production environment reviewers and branch
restrictions where the repository plan supports them. Merges and direct pushes
to `main` refresh the private preview automatically; the workflow has no
production deployment step. The manual dispatch option is limited to `main`.

Enable Web Analytics from the project's **Analytics** page before the first
deployment with analytics enabled. The generated MkDocs pages load Vercel's
`/_vercel/insights/script.js` endpoint only when built for `adlc5.dev`; legacy
subpath builds omit the script.

Enable Vercel Authentication for preview deployments and grant access only to
the owner's Vercel account. Disable shareable links and automation bypasses.
Verify access in a signed-out browser; `noindex` is not access control. On the
Hobby plan, standard protection does not protect production domains, so this
workflow deliberately deploys previews only while the site must remain private.

## Refresh the private preview

After Vercel and GitHub settings are ready, every push to `main` rebuilds and
deploys the latest website to a new private Preview URL. A manual refresh is
also available:

1. Open **Actions → Deploy ADLC5 private preview → Run workflow** on `main`.
2. Open the deployment URL from the workflow summary and check the exact commit.
3. Verify owner access and denied anonymous access for private review.

Pull requests, including fork contributions, run validation only. Preview
deployments use only merged `main` code. A GitHub Actions button is visible to
repository users with sufficient Actions permission; Vercel Authentication
controls who can read the deployed site. Do not share bypass URLs or secrets.

## Connect `adlc5.dev` at public launch

Keep DNS unchanged during private review. When ready to publish publicly:

1. Add `adlc5.dev` in **Vercel → Project → Settings → Domains**.
2. Add `www.adlc5.dev` too and configure it to redirect to `adlc5.dev`.
3. Copy the exact DNS records Vercel displays into the domain registrar/DNS host.
   If Vercel is not the DNS provider, add the requested apex A/ALIAS and `www`
   CNAME records there. Do not guess values or replace unrelated records.
4. Wait for Vercel to show the domain as verified and HTTPS as ready.
5. Configure a deliberate production deployment path for the selected Vercel
   plan and protection policy.
6. Verify `https://adlc5.dev/`, the `www` redirect, page assets, sitemap, and
   canonical metadata. If the site is public, allow anonymous access on the
   production domain while keeping preview deployments protected.

The old GitHub Pages URL may remain available as a fallback during review. Before
retiring it, inventory existing routes and choose an explicit migration strategy;
canonical metadata alone does not redirect old links. No DNS records or live
Vercel settings are changed by repository updates.
