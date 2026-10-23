# Telemetry and feedback

ADLC5 keeps lifecycle event JSONL local. It may contain feature names, run IDs,
script details and test output, so ADLC5 never uploads those records verbatim.

The optional exporter is disabled by default. It previews fixed event/status
counts locally, requires explicit workspace opt-in, and only sends after a
separate manual confirmation. It includes no prompts, code, command output,
repository or feature labels, timestamps, run IDs, usage records, or persistent
user identifier. These counts do not measure savings or accuracy; see the
[controlled evaluation contract](https://github.com/dango-tech/adlc5/blob/main/docs/evaluation.md).

Feedback is a separate explicit submission. Optional free text is previewed,
limited to 1,000 characters, and stored apart from aggregates. Free text is not
anonymous; do not send secrets or personal data.

The reference Cloudflare Worker + D1 intake applies a 4 KiB payload limit,
three requests per minute per transport IP, and 90-day retention. It does not
store IPs or log request bodies, but Cloudflare processes connection metadata.
This is minimized telemetry, not a promise of anonymity. Deployment and live
ingestion are operator-managed and have not been qualified by these docs.

See the [telemetry guide](https://github.com/dango-tech/adlc5/blob/main/docs/telemetry.md) for commands and the
[intake setup guide](https://github.com/dango-tech/adlc5/blob/main/telemetry-intake/README.md) for Cloudflare setup and
current plan limits.
