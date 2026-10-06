# Repository structure

```
adlc5/
├── config.example.yaml   Copy to config.yaml — install targets, model_routing, platform_profiles
├── .cursor-plugin/       Cursor Agent Plugin (skills + kernel/MCP shims)
├── .cursor/              Cursor rules (.mdc), hooks, council agents
├── core/                 sdd-model, state-schema, gates.yaml, personas, governance/, guides/
├── skills/               @adlc5 + stage skills + aux (qa, discover, prt, reviewers, pbe-*, …)
├── scripts/              install / verify / cleanup, check-gates, adlc5 façade, MCP, pilot, memory/, wiki/
├── templates/            agent constitution, policies, personas, memory, wiki, github-workflows/, model tip sheets
├── platform/             codex-plugin metadata, headless runner stubs
├── docs/                 ADLC5.md lifecycle + ADLC5-kernel.md
├── dogfood/              Only place in this repo where lifecycles run
└── shared/
    ├── docs/             INSTALL, CROSS-PLATFORM, playbook, SKILL-MAP, knowledge-base
    └── rules/portable/   R0–R5 for non-Cursor hosts
```

| Task | Command |
|------|---------|
| Install | `./scripts/install.sh --platform all` |
| Verify | `./scripts/verify-install.sh` |
| Upgrade | `./scripts/update-adlc5.sh --self` \| `--global` |
| Init app | `./scripts/init-workspace.sh --project .` |
| Feature | `./scripts/init-feature.sh --feature NAME --interaction hitl` |
| Kernel | `./scripts/adlc5 version` / `gate` / `state` / … |
| Gates | `./scripts/check-gates.py --feature NAME --gate pr-ready` |
| Tests | `./scripts/tests/run-all.sh` |

Lifecycle: [docs/ADLC5.md](docs/ADLC5.md) · Kernel: [docs/ADLC5-kernel.md](docs/ADLC5-kernel.md) · Agent map: [AGENTS.md](AGENTS.md)

Do not put `.adlc5/{feature}/` in this repo unless dogfooding (`dogfood/`).
