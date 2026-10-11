# Hermes Agent runner boundary

ADLC5's supervised Hermes mode defaults to attended execution:

```bash
./scripts/adlc5 setup models --host hermes
./scripts/adlc5 run --feature FEATURE --host hermes --mode attended --workspace .
```

The runner launches `hermes chat -q` in the current terminal, seeds the
worker brief, and waits for the attempt-specific result file. Attended Hermes
usage is currently recorded as unavailable because its interactive session
does not expose a verified usage file to this collector. Exit Hermes after it
reports the result file is ready so the runner can continue.

The Hermes CLI does not confine filesystem writes. Do not run it unattended
on the host. An unattended `hermes -z` worker is accepted only when the
workspace contains `.adlc5/external-sandbox.json` with
`{"type":"container","declared_by":"user"}` and the runner detects
`/.dockerenv` or `/run/.containerenv`. The marker file by itself is not a
sandbox. ADLC5 does not build or ship this container.

This support is experimental and does not carry comparative benchmark
qualification.
