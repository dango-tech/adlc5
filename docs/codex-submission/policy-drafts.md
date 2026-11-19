# Publisher review of shared policy pages

Another submission agent is preparing `website/docs/privacy.md` and
`website/docs/terms.md`. Those shared pages are the candidates for all hosts;
Codex preparation does not replace or edit them.

Before populating the Codex listing's policy URLs, Dango Tech must confirm the
pages' operational/legal claims and publish the pages. Source files are not
proof that a public URL exists or that operational claims are true.

## Privacy checks

The repository supports a local stdio MCP server, local workflow records and
opt-in aggregate sharing with no built-in endpoint. A coding-agent host,
configured model provider, project tools and publication actions may transmit
data independently of ADLC5's optional exporter. Avoid implying that all agent
activity stays on the user's machine.

The shared draft describes a Dango Tech-operated Cloudflare Worker/D1 intake,
90-day retention, no stored IP addresses or request bodies, and no sale or
advertising use. Confirm these as actual operational practices, rather than
assuming that example intake code proves deployment or retention enforcement.
Confirm website analytics/logging, support-data retention and deletion handling,
and a usable privacy contact channel. Public issues should not request secrets
or personal data.

Local logs have no automatic rotation. Opt-out removes sharing consent, queued
batches and cursor; it does not delete existing local logs or data already
received by an endpoint. Feature archival preserves records. Do not prescribe
deleting all of `~/.adlc5/` without explaining that it also contains settings and
shared project state.

## Terms checks

Dango Tech confirmed that ADLC5 has no payments. The repository's MIT License
supplies software licensing, warranty and liability provisions. Confirm any
additional website/service terms with the publisher; do not infer acceptance of
new legal terms from consent to prepare a plugin package.

## Finalization

After approval and publication, fetch and inspect the actual public privacy and
terms pages without a login. Set their verified HTTPS URLs as
`privacyPolicyURL` and `termsOfServiceURL` under the root manifest's
`extensions.com.openai.interface`, mirror that interface in the compatibility
manifest, rebuild the Codex ZIP, and inspect the ZIP itself.
