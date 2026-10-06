# Scaffold manifest — {feature_name}

**Generated:** {ISO8601}  
**Repo profile:** {greenfield|brownfield|ambiguous}  
**Stack ID:** {stack_id or "none"}

---

## Stack detection

| Field | Value |
|-------|--------|
| Language | {language} |
| Framework | {framework} |
| Framework version | {framework_version or "unknown"} |
| Scaffold tool | {scaffold_tool or "n/a"} |
| Registry entry | {registry_entry or "none"} |

**Detection signals:** {files/deps used}

---

## Official scaffold

| Field | Value |
|-------|--------|
| Invoke | {e.g. @google-agents-cli-scaffold} |
| Command | `{exact CLI command — user-approved}` |
| Applied | {yes|no|pending} |
| Applied at | {ISO8601 or "—"} |

**Rule:** Greenfield Story 0 runs the command above — **do not** hand-create equivalent directories.

---

## Approved directory tree

```
{paste expected tree from scaffold-registry or post-scaffold listing}
```

Paths in code specs (`files_to_create`) must fall under this tree unless listed in Deviation log.

---

## Brownfield conventions (if applicable)

{From 1a-discovery Codebase Conventions subsection — module paths, test layout, naming}

---

## Layout compliance

| Check | Status |
|-------|--------|
| Matches registry expected layout | {pass|fail|n/a} |
| Forbidden patterns absent | {pass|fail|n/a} |
| `layout_compliance` (state) | {pending|pass|waived} |

---

## Deviation log

| Path / pattern | Reason | Waiver |
|----------------|--------|--------|
| {none} | — | — |

---

## Story 0

| Field | Value |
|-------|--------|
| Required | {yes — greenfield / optional — brownfield drift / no} |
| Story ID | {0 or "—"} |
| Type | {scaffold-foundation | layout-standardization | —} |
| Verification | {pending|pass} |
