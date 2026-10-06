# ADLC5 — Scaffold registry

**Single source of truth** for official project scaffolding per stack. When an entry exists, **greenfield Story 0 must use `official_scaffold`** — manual directory trees are blocked unless the user waives via AskQuestion (`proceed_with_custom_layout`).

**Manifest artifact:** `.adlc5/{feature}/design/scaffold-manifest.md`  
**Repo profile:** canonical `scope.repo_profile` in `state.json` — see [interaction-modes.md](interaction-modes.md)

---

## Enforcement rules

| `repo_profile` | Behavior |
|----------------|----------|
| `greenfield` | Insert **Story 0: Scaffold Foundation**; run registry `official_scaffold` before feature stories |
| `brownfield` | Follow existing layout; compare to registry; if drift → suggest refactor via AskQuestion |
| `ambiguous` | AskQuestion: greenfield scaffold vs extend existing |

**Hard gates:**

- Component stories cannot enter **Implement** until Story 0 verification passes (greenfield)
- Code spec `files_to_create` must be under **Approved directory tree** in manifest
- [build-implementer](../../skills/build-implementer/SKILL.md) must not hand-scaffold when registry entry exists (Story 0)
- [assure-verifier](../../skills/assure-verifier/SKILL.md) fails greenfield hand-built layouts without waiver

---

## Registry entries

### `google-adk`

| Field | Value |
|-------|--------|
| **stack_id** | `google-adk` |
| **Detection** | `pyproject.toml` / `requirements.txt`: `google-adk`, `google-genai`; imports `google.adk`; `adk.yaml` present |
| **detected_stack** | `language: "python"`, `framework: "google-adk"`, `scaffold_tool: "agents-cli"` |
| **Official scaffold** | **`@google-agents-cli-scaffold`** — `agents-cli scaffold create <project-name> [flags]` |
| **Prerequisite skill** | `@google-agents-cli-workflow` Phase 0 (requirements) before `scaffold create` |
| **CLI install** | `uv tool install google-agents-cli` |
| **Layout doc** | Google ADK project layout from scaffold output; see [ADK docs](https://google.github.io/adk-docs/) |
| **Expected layout (post-scaffold)** | Project root created by CLI — typical: `app/` or agent module, `pyproject.toml`, deployment/CI stubs per flags; **do not** `mkdir` project before `scaffold create` |
| **Forbidden patterns** | Flat `agents/` tree without ADK app entry; hand-rolled `main.py` + random folders mimicking ADK; skipping `agents-cli` on empty repo |
| **Story 0 type** | `scaffold-foundation` |

**Example invoke (greenfield):**

```text
@google-agents-cli-scaffold
agents-cli scaffold create <name> --agent <template> --prototype  # or full deployment flags per PRD
```

Record exact command and flags in `scaffold-manifest.md`.

---

### `spring-boot`

| Field | Value |
|-------|--------|
| **stack_id** | `spring-boot` |
| **Detection** | `pom.xml` / `build.gradle`: `spring-boot-starter-*` |
| **Official scaffold** | [Spring Initializr](https://start.spring.io/) — `curl` API or IDE wizard; document URL in manifest |
| **Supplement** | [JAVA-SPRING-BOOT-SUPPLEMENT.md](platform-supplements/JAVA-SPRING-BOOT-SUPPLEMENT.md) |
| **Forbidden patterns** | Manual `src/main/java` tree without Initializr/baseline module |
| **Story 0 type** | `scaffold-foundation` (greenfield only) |

---

### `fastapi`

| Field | Value |
|-------|--------|
| **stack_id** | `fastapi` |
| **Detection** | `pyproject.toml` / `requirements.txt`: `fastapi` |
| **Official scaffold** | [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) or team cookiecutter — confirm via AskQuestion |
| **Supplement** | [PYTHON-FASTAPI-SUPPLEMENT.md](platform-supplements/PYTHON-FASTAPI-SUPPLEMENT.md) |
| **Forbidden patterns** | Single `main.py` monolith with no project package on greenfield |
| **Story 0 type** | `scaffold-foundation` (greenfield only) |

---

### `django`

| Field | Value |
|-------|--------|
| **stack_id** | `django` |
| **Detection** | `django` in deps; `manage.py` present |
| **Official scaffold** | `django-admin startproject` + `startapp` |
| **Supplement** | [PYTHON-DJANGO-SUPPLEMENT.md](platform-supplements/PYTHON-DJANGO-SUPPLEMENT.md) |
| **Story 0 type** | `scaffold-foundation` (greenfield only) |

---

### `react` / `nextjs` / `angular`

| Field | Value |
|-------|--------|
| **stack_id** | `react`, `nextjs`, `angular` |
| **Official scaffold** | `npm create vite@latest`, `npx create-next-app`, `ng new` respectively |
| **Supplement** | [REACT-CODING-GUIDELINES.MD](platform-supplements/REACT-CODING-GUIDELINES.MD), [ANGULAR-CODING-GUIDELINES.md](platform-supplements/ANGULAR-CODING-GUIDELINES.md) |
| **Story 0 type** | `scaffold-foundation` (greenfield only) |

---

## Lookup procedure

To perform automated project stack detection and greenfield/brownfield repo profiling, call the compliance script:

```bash
./scripts/check-scaffold.py /path/to/project-root
```

This script detects dependencies, validates matching stack entries, profiles whether the workspace is a greenfield or brownfield repo, and outputs JSON mapping to the state schema.

1. After running the script, verify `detected_stack.framework`
2. Find matching `stack_id` in this registry
3. If match: record `stack_id`, registry entry, and command in `scaffold-manifest.md`
4. If no match: record no registry match in the manifest — brownfield conventions only; no Story 0 unless user requests
5. Write or update `scaffold-manifest.md` during Plan Step 1

---

## Brownfield drift workflow

1. Compare Step 0b **Codebase Conventions** tree vs registry `expected_layout`
2. If structural drift (missing standard dirs, forbidden pattern present): score drift 1–5
3. **AskQuestion** when drift ≥ 3:
   - `refactor_standard` — insert Story 0: Layout Standardization
   - `document_deviations` — log in manifest Deviation log
   - `waive` — set `layout_compliance: waived`
4. Feature code specs use **existing paths** only unless refactor story approved

---

## Waive option (AskQuestion)

```json
{
  "id": "scaffold_layout",
  "prompt": "Layout does not match official scaffold for [stack]. How proceed?",
  "options": [
    { "id": "refactor_standard", "label": "Refactor to standard layout (Story 0)" },
    { "id": "document_deviations", "label": "Document deviations and continue" },
    { "id": "proceed_with_custom_layout", "label": "Waive — proceed with custom layout" }
  ]
}
```

---

## Skills referencing this guide

- [adlc5-plan](../../skills/plan/SKILL.md)
- [adlc5-plan-design](../../skills/plan/SKILL.md)
- [adlc5-plan-stories](../../skills/tasks/SKILL.md)
- [adlc5-build](../../skills/implement/SKILL.md)
- [build-implementer](../../skills/build-implementer/SKILL.md)
- [assure-verifier](../../skills/assure-verifier/SKILL.md)
