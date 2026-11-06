# Brownfield at scale — OpenViking state storage

For large brownfield repos, store derived repository state in OpenViking
instead of only local `.agent-cache/`, so state survives across sessions and
agents without bloating context.

## What to store
- Module/symbol/test maps (already in `.agent-cache/`) mirrored as OpenViking resources.
- Reviewed architecture/boundaries (`.agents/`) as OpenViking memories.
- Feature context packs as OpenViking session memory after each stage gate.

## Rules
- OpenViking is the durable store; `.agent-cache/` remains the fast local cache.
- Never store secrets or generated dependency trees.
- Re-index on `repo-index refresh`; mirror deltas only.
- Retrieval: agents query OpenViking first, fall back to local cache.
" 