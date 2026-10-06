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
