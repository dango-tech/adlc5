# Cursor model tiers

Model choices are user-specific. Use `adlc5 setup models` when the Cursor adapter is available; until then, the in-agent lifecycle uses the current session model unless a host profile has been configured.

The tier contract is `reasoning`, `balanced`, and `execution`. Keep model name, effort, and context as separate fields; ADLC5 ships no model IDs.
