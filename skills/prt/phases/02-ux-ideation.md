---
name: ux-ideation
description: Phase 2 - UX Ideation + Prototype Spec. Maps PRT requirements to CORE UI components, defines testable user journeys, and produces a framework-specific prototype specification ready for rapid prototyping.
---

# Phase 2: UX Ideation + Prototype Spec

## Purpose

Transform the approved PRT into a **testable UX prototype specification** by:
1. Mapping every functional requirement to specific CORE UI components
2. Defining user journeys as step-by-step testable flows
3. Producing framework-specific component stubs wired to real design system selectors

This phase enables "fail fast" iteration — concept, test, and refine ideas **before** they enter the engineering backlog. The output should be actionable enough for a developer to build a working prototype in a single session using the design system.

## Output

A UX Ideation document saved to `.prt/{feature-name}/ux-ideation.md` containing:
- Component inventory (design system components mapped to requirements)
- Screen/view inventory with layout descriptions
- User journey flows (testable)
- Framework-specific prototype spec (based on `context.framework` in state.json)
- Optional Figma frame references
- Open questions for the design team

## Core Principles

### CORE UI First, Always

Every UI element in this spec must map to a CORE UI component. Load `guides/core-ui-reference.md` before starting. If a requirement cannot be met with existing CORE UI components, flag it explicitly:
```
[CUSTOM COMPONENT NEEDED]: {description of what's missing, flag for design team}
```

### Prototype Over Perfection

The goal is speed-to-feedback, not pixel-perfect design. A working prototype that uses real design system components and real data flows is worth more than a Figma mockup that hasn't been tested.

### Testable Journeys

Every user story from PRT Section 4 must produce at least one testable journey — a sequence of steps a user can walk through to validate the concept works as expected.

### Design-Engineering Continuity

This spec is the bridge between ideation and implementation. It must be specific enough that:
- A **designer** can validate component choices before pixel-perfect work begins
- A **developer** can scaffold the prototype without ambiguity
- A **PO/PM** can walk through the journey and confirm it solves the stated problem

## Phase 2 Process

### Step 0: Load Framework Preference

Read `context.framework` from state.json. This determines how Step 5 (Prototype Spec) is generated:

| `framework` | Step 5 Output |
|-------------|---------------|
| `angular` | Angular standalone component stubs with `CoreUIModule` imports, `.npmrc`, `angular.json` styles |
| `react` | React functional component stubs with hooks; design system class names and tokens |
| `vue` | Vue 3 Composition API SFC stubs; design system class names and tokens |
| `other` | Pseudo-code stubs showing component structure, data bindings, and event handlers |
| `framework-agnostic` | No code stubs; component inventory, screen inventory, user journeys, and TypeScript mock data interfaces only |

Steps 1-4 and Steps 6-7 are framework-agnostic and always produced.

### Step 1: Load PRT Context

Read `.prt/{feature-name}/prt.md`. Extract:
- All user stories from Section 4
- All functional requirements from Section 5
- All UI/UX requirements from Section 6
- Design System & Implementation notes from Section 8
- Non-functional requirements relevant to the prototype (performance, accessibility, browser support)

### Step 2: Build Component Inventory

For each functional requirement and UI/UX requirement in the PRT, identify the CORE UI component(s) needed.

Load `guides/core-ui-reference.md` for the component catalog.

Format as a table:

| Requirement | CORE UI Component | Selector | Variant/Config | Notes |
|-------------|-------------------|----------|----------------|-------|
| View invoice list | Data Table | `cui-data-table` | Sortable, filterable | Include status badge column |
| Approve/Reject action | Button | `cui-button` | Primary (Approve), Danger (Reject) | Triggers confirmation modal |
| Confirmation dialog | Modal | `cui-modal` | Standard | Include warning icon |
| Status display | Badge/Chip | `cui-badge` | Success/Warning/Danger variants | Map to invoice status values |
| Filter controls | Filter Bar | `cui-filter-bar` | Multi-select | Filter by status, date, vendor |
| Page navigation | Breadcrumb | `cui-breadcrumb` | Standard | Show current location |
| Loading state | Spinner | `cui-spinner` | Inline | Show during API calls |

For any requirement where no CORE UI component exists, add a row marked `[CUSTOM COMPONENT NEEDED]` with a description.

### Step 3: Define Screen/View Inventory

List every distinct screen or view the prototype needs. For each screen:

```markdown
### Screen: [Screen Name]

**Route:** `/[path]` (approximate)
**Entry point:** [how user arrives at this screen]
**Primary user story:** [Story N from PRT]

**Layout:**
- Header: [describe using CORE UI layout components]
- Main content area: [describe primary content block]
- Sidebar/panel (if applicable): [describe]
- Footer/action bar: [describe]

**CORE UI Components used:**
- [component selector]: [purpose]
- [component selector]: [purpose]

**Key interactions on this screen:**
- [user action] → [system response]
- [user action] → [system response]

**Data requirements:**
- [field/entity needed to render this screen]
```

### Step 4: Define Testable User Journeys

For each user story from PRT Section 4, define a testable journey — a numbered sequence of steps a person can walk through:

```markdown
### Journey: [Story Title]

**User story:** As a [role], I want [goal] so that [benefit].
**Entry point:** [URL or screen name]
**Happy path:**

1. User navigates to [screen]
2. [Component] displays [data] — *validation: list loads with correct columns*
3. User [action] on [component] — *validation: [expected state change]*
4. [Component] responds with [state] — *validation: [expected UI feedback]*
5. User [action] to complete — *validation: [success state]*

**Edge cases to test:**
- [edge case]: expected behavior
- [edge case]: expected behavior

**Fail fast criteria:** If [condition], this approach does not solve the problem because [reason].
```

The "fail fast criteria" is key — this defines what would invalidate the concept so the team knows when to pivot.

### Step 5: Prototype Spec

Generate the prototype specification based on the `framework` preference from state.json.

---

#### If `framework` is `"angular"`

Produce Angular standalone component stubs wired to CORE UI.

**Module Setup:**
```typescript
// app.component.ts (Standalone Angular 17+)
import { CoreUIModule } from '@epsilon/core-ui';
// If data visualization needed:
import { CoreUIDataVizModule } from '@epsilon/core-ui/data-viz';

@Component({
  standalone: true,
  imports: [CoreUIModule, /* CoreUIDataVizModule */]
})
```

**.npmrc (Required):**
```
@epsilon:registry=https://artifactory.cnvr.in/artifactory/api/npm/npm-internal/
```

**angular.json styles:**
```json
"styles": [
  "src/styles.css",
  "./node_modules/@epsilon/core-ui/assets/cui/styles/styles-all.scss"
]
```

**Component Stubs — one per screen from Step 3:**
```typescript
// [feature-name]-[screen-name].component.ts
import { Component, OnInit } from '@angular/core';
import { CoreUIModule } from '@epsilon/core-ui';

@Component({
  selector: 'app-[screen-name]',
  standalone: true,
  imports: [CoreUIModule],
  template: `
    <div class="cui-page-layout">
      <cui-breadcrumb [items]="breadcrumbs"></cui-breadcrumb>
      <h1 class="cui-heading-1">[Page Title]</h1>

      <cui-[component-selector]
        [items]="[dataBinding]"
        (onAction)="handle[Action]($event)">
      </cui-[component-selector]>
    </div>
  `
})
export class [ScreenName]Component implements OnInit {
  [dataBinding]: any[] = [];

  ngOnInit(): void {
    // Wire to [API endpoint from PRT Section 7]
  }

  handle[Action](event: any): void {
    // Implement [action description]
  }
}
```

---

#### If `framework` is `"react"`

Produce React functional component stubs with hooks.

**Project Setup:**
```bash
# Vite + React + TypeScript (recommended)
npm create vite@latest [feature-name]-prototype -- --template react-ts
```

**Design System Setup:**
```
# .npmrc
@epsilon:registry=https://artifactory.cnvr.in/artifactory/api/npm/npm-internal/

# Install CORE UI (if React bindings exist) or use CSS class names
npm install @epsilon/core-ui
```

**Global Styles (in main.tsx or index.css):**
```typescript
import '@epsilon/core-ui/assets/cui/styles/styles-all.scss';
```

**Component Stubs — one per screen from Step 3:**
```tsx
// [ScreenName].tsx
import { useState, useEffect } from 'react';
import type { [EntityName] } from './types';

export function [ScreenName]() {
  const [data, setData] = useState<[EntityName][]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Wire to [API endpoint from PRT Section 7]
    setLoading(false);
  }, []);

  function handle[Action](item: [EntityName]) {
    // Implement [action description]
  }

  if (loading) return <div className="cui-spinner" />;

  return (
    <div className="cui-page-layout">
      <nav className="cui-breadcrumb">{/* Breadcrumb items */}</nav>
      <h1 className="cui-heading-1">[Page Title]</h1>

      {/* [Component purpose] — maps to cui-[selector] */}
      <div className="cui-data-table">
        {/* Table structure using CORE UI class names */}
      </div>

      {/* [Action buttons] */}
      <button className="cui-button cui-button--primary"
        onClick={() => handle[Action](selectedItem)}>
        [Action Label]
      </button>
    </div>
  );
}
```

> **Note:** If `@epsilon/core-ui` provides React component bindings, use those directly instead of CSS class names. If only Angular components are available, use CORE UI CSS classes and design tokens for consistent styling.

---

#### If `framework` is `"vue"`

Produce Vue 3 Composition API SFC stubs.

**Project Setup:**
```bash
# Vite + Vue 3 + TypeScript
npm create vite@latest [feature-name]-prototype -- --template vue-ts
```

**Design System Setup:**
```
# .npmrc
@epsilon:registry=https://artifactory.cnvr.in/artifactory/api/npm/npm-internal/

npm install @epsilon/core-ui
```

**Global Styles (in main.ts):**
```typescript
import '@epsilon/core-ui/assets/cui/styles/styles-all.scss';
```

**Component Stubs — one per screen from Step 3:**
```vue
<!-- [ScreenName].vue -->
<script setup lang="ts">
import { ref, onMounted } from 'vue';
import type { [EntityName] } from './types';

const data = ref<[EntityName][]>([]);
const loading = ref(true);

onMounted(async () => {
  // Wire to [API endpoint from PRT Section 7]
  loading.value = false;
});

function handle[Action](item: [EntityName]) {
  // Implement [action description]
}
</script>

<template>
  <div class="cui-page-layout">
    <nav class="cui-breadcrumb"><!-- Breadcrumb items --></nav>
    <h1 class="cui-heading-1">[Page Title]</h1>

    <div v-if="loading" class="cui-spinner" />

    <!-- [Component purpose] — maps to cui-[selector] -->
    <div v-else class="cui-data-table">
      <!-- Table structure using CORE UI class names -->
    </div>

    <!-- [Action buttons] -->
    <button class="cui-button cui-button--primary"
      @click="handle[Action](selectedItem)">
      [Action Label]
    </button>
  </div>
</template>
```

> **Note:** If `@epsilon/core-ui` provides Vue component bindings or web components, use those directly. Otherwise, use CORE UI CSS classes and design tokens.

---

#### If `framework` is `"other"`

Ask the user for a brief description of their framework/setup, then produce **pseudo-code stubs** that are framework-neutral:

```
Screen: [Screen Name]
Route: /[path]

Component Structure:
  - PageLayout
    - Breadcrumb(items: [...])
    - Heading("[Page Title]")
    - DataTable(
        columns: [col1, col2, col3],
        data: bind(dataSource),
        sortable: true,
        onRowClick: handleRowSelect
      )
    - ButtonGroup
      - Button(label: "[Action]", variant: "primary", onClick: handle[Action])
      - Button(label: "[Action]", variant: "danger", onClick: handle[Action])

Data Bindings:
  - dataSource: [EntityName][] ← fetch from [API endpoint]
  - selectedItem: [EntityName] | null

Event Handlers:
  - handle[Action](item): [description of what happens]
  - handleRowSelect(item): [description]

Design System Mapping:
  - PageLayout → cui-page-layout
  - DataTable → cui-data-table (sortable, filterable)
  - Button(primary) → cui-button--primary
  - Button(danger) → cui-button--danger
```

---

#### If `framework` is `"framework-agnostic"`

**Skip code stubs entirely.** The prototype spec section contains only:

1. A note: "Prototype spec is framework-agnostic. No code stubs generated. Use the component inventory (Section 1) and screen inventory (Section 2) to scaffold in your framework of choice."
2. Mock data TypeScript interfaces (see Mock Data Structure below)

This mode is useful when the PRT is handed off to a team that will choose their own scaffolding approach.

---

#### Mock Data Structure (All Frameworks)

Regardless of framework, always define TypeScript interfaces for primary data entities:

```typescript
// [feature-name].types.ts
export interface [EntityName] {
  id: string;
  // [field]: [type]; // [description from PRT]
}

// Mock data for prototype
export const MOCK_[ENTITY_NAME]S: [EntityName][] = [
  {
    id: '001',
    // [field]: [example value]
  }
];
```

### Step 6: Optional Figma References

If Figma frames exist or are planned, add a reference section:

```markdown
## Figma References

| Screen | Figma Frame ID | Status | Notes |
|--------|---------------|--------|-------|
| [Screen Name] | [frame-id or URL] | Planned / In Progress / Complete | |
```

If no Figma work exists yet, note: "Figma frames to be created after prototype validation. Reference CORE UI Figma library for component specs."

### Step 7: Design Team Open Questions

Flag any decisions that need design team input before prototype development begins:

```markdown
## Open Questions for Design Team

| # | Question | Impact | Owner | Target Date |
|---|----------|--------|-------|-------------|
| 1 | [Question about a component choice or custom component need] | [High/Medium/Low] | [Name/Team] | [Date] |
| 2 | [Question about interaction pattern] | | | |
```

## Quality Checklist for Phase 2

Before marking Phase 2 complete, verify:

### Completeness
- [ ] Every functional requirement from PRT Section 5 maps to a CORE UI component (or a flagged custom need)
- [ ] Every user story from PRT Section 4 has a testable journey defined
- [ ] Every screen has a layout description and component list
- [ ] Prototype spec matches the `framework` preference from state.json
- [ ] Mock data types/interfaces defined for all primary entities

### Quality
- [ ] All component selectors are real CORE UI selectors (not made up)
- [ ] Component variants/configs match what CORE UI supports
- [ ] "Fail fast criteria" defined for each journey
- [ ] No generic HTML elements used where CORE UI has an equivalent

### Handoff Readiness
- [ ] Could a developer scaffold a working prototype from this spec without asking questions?
- [ ] Could a PO/PM walk through the journeys and validate the concept?
- [ ] Could a designer identify what needs Figma work vs. what CORE UI handles?

## Output Document Structure

```markdown
# UX Ideation: [Feature Name]

**Based on PRT:** .prt/{feature-name}/prt.md
**Date:** [YYYY-MM-DD]
**Author:** [Generated by @prt skill]
**Framework:** [angular | react | vue | other | framework-agnostic]
**Status:** Draft / In Review / Approved

## 1. Component Inventory
[Component mapping table]

## 2. Screen / View Inventory
[Screen descriptions]

## 3. Testable User Journeys
[Journey flows]

## 4. Prototype Spec
### Project Setup
### Component Stubs
### Mock Data Structures

## 5. Figma References
[Frame references or placeholder]

## 6. Open Questions for Design Team
[Questions table]

## 7. Next Steps
- Prototype validation: [who reviews, acceptance criteria]
- Design sign-off: [who, what they're reviewing]
- ADLC5 handoff: [link to .adlc5/ path if handoff accepted]
```

## Definition of Done

Phase 2 is complete when:
- [ ] Component inventory covers all PRT functional requirements
- [ ] All user stories have testable journeys with fail-fast criteria
- [ ] Prototype spec matches framework preference and provides stubs for every screen (unless framework-agnostic)
- [ ] Mock data types defined for primary entities
- [ ] Quality checklist passes
- [ ] UX ideation saved to `.prt/{feature-name}/ux-ideation.md`
- [ ] state.json updated with `ux_ideation: "completed"`
- [ ] User approves: "Yes, this is ready for prototyping / ADLC5 handoff"
