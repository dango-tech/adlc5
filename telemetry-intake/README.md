# ADLC5 telemetry intake reference

This is an optional, operator-deployed Cloudflare Worker + D1 receiver for the
minimized aggregate and separate feedback commands documented in
[`docs/telemetry.md`](../docs/telemetry.md). ADLC5 does not deploy it, configure
an account, or send data to a default endpoint.

## Privacy and limits

- `POST /v1/aggregate` accepts only fixed event/status counts. Idempotency keys
  are random per submission, not stable per user.
- `POST /v1/feedback` accepts a rating/category and optional 1,000-character
  free-text field. Free text is deliberately separate from aggregates and is
  not anonymous.
- Both routes require JSON, cap request bodies at 4 KiB, and are limited to
  three requests per minute per Cloudflare transport IP. That IP is passed only
  to the edge rate-limit binding; the Worker does not store it. Shared IPs can
  cause unrelated users to share a limit.
- Application observability is disabled in `wrangler.toml`; the Worker does
  not log request headers, body, or errors. Review account/zone logging settings
  before launch because Cloudflare still processes connection metadata.
- A daily scheduled cleanup deletes both tables after 90 days.

This is data-minimized telemetry, not anonymous telemetry. The public intake
does not authenticate submissions; the small payload, allowlist, edge limit,
and retention cleanup reduce abuse and exposure but do not prove sender identity
or prevent all spam.

## Deploy your own instance

Check current Cloudflare plan limits and your privacy requirements first. At the
time this guide was written, Cloudflare's Workers Free plan included 100,000
requests/day, and D1 Free included 5 million rows read/day, 100,000 rows
written/day, and 5 GB storage; these are account-level quotas and can change.
Exceeding the D1 Free daily read/write quota causes queries to fail until reset.
See [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/)
and [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/).

1. Install Wrangler and authenticate to the Cloudflare account you control.
2. Create a D1 database named `adlc5-telemetry`; replace
   `database_id` in `wrangler.toml` with that database's ID.
3. Choose a rate-limit namespace ID unique in your account (the sample uses
   `1001`) and keep the `3`-per-minute setting unless a documented review says
   otherwise.
4. Apply the schema with `npx wrangler d1 migrations apply adlc5-telemetry --remote`.
5. Configure a route/domain you control, then deploy from this directory with
   `npx wrangler deploy`.
6. Review the live privacy notice and logging settings. Set the client endpoint
   only in the workspace where sharing is intended:

   ```bash
   ADLC5_TELEMETRY_ENDPOINT=https://your-host.example \
     ./scripts/adlc5 telemetry preview --workspace .
   ```

Do not deploy the sample with its placeholder database ID or rate namespace.
This repository's tests use local mocks and do not qualify a live Cloudflare
deployment or ingestion path.
