# ADLC5 framework layout

Specify → Plan → Tasks → Implement — agent judgment, deterministic kernel, craftsmanship without textbook branding. Lifecycle: [docs/ADLC5.md](docs/ADLC5.md) · Kernel: [docs/ADLC5-kernel.md](docs/ADLC5-kernel.md).

```bash
./scripts/install.sh --platform cursor
./scripts/init-feature.sh --feature my-feature --interaction hitl
```

| Path | Role |
|------|------|
| `skills/` | Lifecycle + auxiliary skills |
| `core/` | gates, personas, guides, registry |
| `scripts/` | install, kernel façade, init-feature, pilot, memory/, runner/ |
| `templates/` | agent constitution, policies, wiki, memory |
| `platform/` | host plugin metadata + runner stubs |
| `docs/` | lifecycle + kernel reference |
| `dogfood/` | in-repo lifecycle experiments only |
