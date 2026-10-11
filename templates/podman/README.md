# Podman local development (ADLC5 template)

Copy to consumer repo or reference from `.adlc5/{feature}/`.

## Quick start

```bash
./templates/podman/dev-up.sh
```

## Custom gate (policies.yaml)

```yaml
custom_gates:
  podman_smoke: podman compose -f templates/podman/compose.yaml run --rm smoke

required_gates:
  - podman_smoke
```

## Files

- `Containerfile` — app dev image
- `compose.yaml` — podman-compose services
- `dev-up.sh` — start dev stack

## Hermes supervised runner

For a separate container boundary, use the official Hermes image with a
standalone checkout (a `.git` directory, not a linked worktree). Initialize
the user's Hermes data directory and ADLC5 model config first. Create this
user-authored declaration in the checkout only after choosing to run inside
the container:

```json
{"type":"container","declared_by":"user"}
```

Then launch a shell in the Hermes image with only the checkout, framework, and
Hermes data mounted:

```bash
podman run --rm -it \
  -v "$PWD:/workspace:Z" \
  -v "$ADLC5_FRAMEWORK_ROOT:/adlc5:ro,Z" \
  -v "$HOME/.hermes:/opt/data:Z" \
  -v "$HOME/.adlc5:/opt/data/.adlc5:ro,Z" \
  -w /workspace \
  nousresearch/hermes-agent bash
```

Inside the container, start the runner with
`python3 /adlc5/scripts/adlc5 run --feature FEATURE --host hermes --mode confined --workspace /workspace`.
The runner checks the container runtime marker as well as the local
declaration. The mounted Hermes data includes credentials and session data;
the agent can read it, and container network access is not restricted by this
template. Do not run two Hermes containers against the same data directory
simultaneously. See the [official Hermes Docker guide](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/docker.md)
for the image's data-directory contract.
