---
name: core-ui-reference
description: CORE UI v20.4.0 reference guide for PRT and UX Ideation phases. Contains package installation details, module variants, asset paths, and component catalog for use in PRT Section 7, Section 8, and Phase 2 (UX Ideation) component mapping.
---

# CORE UI Reference Guide

**Version:** 20.4.0  
**Documentation:** https://coreui.epsilon.com/0a9f9a0ed/p/196462-core-ui-v2040  
**Type:** Internal Epsilon design system (Angular component library)  
**Audience:** All Epsilon product teams building Angular applications

## Overview

CORE UI is Epsilon's internal open-source library of design principles and components that make up the interfaces of Epsilon apps. It is required for all UI-facing Epsilon product development. Teams must notify the UX team before adopting CORE UI.

**Important:** CORE UI should always be used in conjunction with a UX resource. Contact the UX team before starting any project using CORE UI.

## Installation

### Prerequisites

1. Notify the UX Team (required before adopting CORE UI)
2. Subscribe to the CORE UI support Slack channels and release notes
3. Attend or review developer training

### Step 1: Add `.npmrc` to project root

```
@epsilon:registry=https://artifactory.cnvr.in/artifactory/api/npm/npm-internal/
```

### Step 2: Install the package

```bash
npm install @epsilon/core-ui
```

### Step 3: Import the module

**Standalone / Angular 17+ (`app.component.ts`):**
```typescript
import { Component } from '@angular/core';
import { CoreUIModule } from '@epsilon/core-ui';
// Optional Mini variant:
import { CoreUIMiniModule } from '@epsilon/core-ui/mini';
// Optional Data Viz:
import { CoreUIDataVizModule } from '@epsilon/core-ui/data-viz';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CoreUIModule,            // Primary — use this for full CORE UI
    // CoreUIMiniModule,     // Mini — lightweight variant
    // CoreUIDataVizModule,  // Optional: add if feature uses charts/viz
  ]
})
export class AppComponent {}
```

**Module-Based / Pre-Angular 17 (`app.module.ts`):**
```typescript
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { CoreUIModule } from '@epsilon/core-ui';
// import { CoreUIMiniModule } from '@epsilon/core-ui/mini';
// import { CoreUIDataVizModule } from '@epsilon/core-ui/data-viz';

@NgModule({
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    CoreUIModule,
    // CoreUIDataVizModule,
    // CoreUIMiniModule,
  ],
  bootstrap: [AppComponent]
})
export class AppModule {}
```

### Step 4: Add styles to `angular.json`

```json
"styles": [
  "src/styles.css",
  "./node_modules/@epsilon/core-ui/assets/cui/styles/styles-all.scss"
]
```

For Mini variant:
```json
"./node_modules/@epsilon/core-ui/assets/cui/styles/styles-mini-all.scss"
```

For Data Viz (add alongside primary or mini):
```json
"./node_modules/@epsilon/core-ui/assets/cui/styles/data-viz.css"
```

### Step 5: Add favicon/bookmark icons

Image assets: `/node_modules/@epsilon/core-ui/assets/cui/images`

```html
<link rel="icon" type="image/png" sizes="256x256" href="favicon-256x256.png" />
<link rel="icon" type="image/png" sizes="32x32" href="favicon-32x32.png" />
<link rel="icon" type="image/x-icon" href="favicon.ico">
```

## Module Variants

| Module | Import Path | Use Case |
|--------|------------|----------|
| `CoreUIModule` | `@epsilon/core-ui` | Standard full-featured Epsilon apps (use this by default) |
| `CoreUIMiniModule` | `@epsilon/core-ui/mini` | Lightweight variant for apps with simpler UI needs |
| `CoreUIDataVizModule` | `@epsilon/core-ui/data-viz` | Add-on for charts, graphs, and data visualization |

**Choosing a variant:**
- Use **Primary** (`CoreUIModule`) for most enterprise apps with standard navigation, forms, tables, and modals
- Use **Mini** (`CoreUIMiniModule`) when building lightweight tools or dashboards with minimal component needs
- Add **Data Viz** (`CoreUIDataVizModule`) whenever the feature includes charts, performance graphs, or reporting views

## Asset Structure

```
node_modules/
└── @epsilon/
    └── core-ui/
        └── assets/
            └── cui/
                ├── fonts/
                │   └── cui-icons.tff|woff|woff2    # CORE UI icon fonts
                ├── styles/
                │   ├── styles-all.scss              # Primary: all base styles
                │   ├── styles-mini-all.scss          # Mini: all base styles
                │   └── data-viz.css                 # Data viz styles
                ├── source-sans-pro/                  # Bundled font files
                └── images/                           # Favicon/bookmark icon assets
```

## Component Catalog

The full component catalog is documented at:  
https://coreui.epsilon.com/0a9f9a0ed/p/196462-core-ui-v2040

The site is organized into four sections:
- **Foundations** — Design tokens: colors, typography, spacing, elevation, iconography
- **Components** — Individual UI components (see known catalog below)
- **Patterns** — Composite patterns: page layouts, navigation, form patterns
- **System & Support** — Installation, developer responsibilities, support channels

### Known Component Categories

Based on CORE UI v20.4.0, the library covers the following component areas. When referencing components in a PRT or UX Ideation spec, use the CORE UI selector prefix `cui-` and verify the exact selector name in the Zeroheight documentation:

**Navigation**
- App header / top navigation
- Breadcrumbs (`cui-breadcrumb`)
- Side navigation / sidebar
- Tabs

**Layout**
- Page layout containers
- Grid system
- Dividers / separators
- Cards / panels

**Data Display**
- Data table (`cui-data-table`) — sortable, filterable, paginated
- List views
- Status badges / chips (`cui-badge`)
- Avatar / user display
- Empty state
- Loading states / skeleton screens (`cui-spinner`)

**Forms & Inputs**
- Text input (`cui-input`)
- Select / dropdown (`cui-select`)
- Multi-select
- Date picker (`cui-date-picker`)
- Checkbox (`cui-checkbox`)
- Radio button (`cui-radio`)
- Toggle / switch
- Search input
- Filter bar (`cui-filter-bar`)

**Actions**
- Button (`cui-button`) — Primary, Secondary, Danger, Ghost variants
- Icon button
- Button group
- Split button

**Overlays**
- Modal / dialog (`cui-modal`)
- Drawer / side panel
- Tooltip (`cui-tooltip`)
- Popover

**Feedback**
- Toast / notification (`cui-toast`)
- Alert / inline message (`cui-alert`)
- Progress bar
- Confirmation dialog

**Data Visualization** (requires `CoreUIDataVizModule`)
- Line chart
- Bar chart
- Donut / pie chart
- Sparkline
- Metric / KPI card

> **Note:** This is a representative catalog based on CORE UI v20.4.0. Always verify exact component names and available props/variants at https://coreui.epsilon.com/0a9f9a0ed/p/196462-core-ui-v2040 before finalizing PRT or prototype specs.

## Design Tokens

CORE UI provides a token system for consistent styling. When referencing tokens in PRTs and UX specs:

**Color tokens** (approximate — verify in Foundations section of docs):
- Primary brand colors: `--cui-color-primary-*`
- Semantic: `--cui-color-success`, `--cui-color-warning`, `--cui-color-danger`, `--cui-color-info`
- Neutral: `--cui-color-neutral-*`

**Typography tokens**:
- Font family: Source Sans Pro (bundled with CORE UI)
- Scale: `--cui-font-size-*`, `--cui-font-weight-*`

**Spacing tokens**:
- `--cui-spacing-*` (4px base grid)

> For complete token documentation, see the Foundations section at the CORE UI Zeroheight site.

## Governance & Support

- **Contact the UX Team** before adopting CORE UI in any new project
- **Subscribe to support channels** for live chat support, office hours, and release notes
- **Review Developer Responsibilities** training before using CORE UI
- **All dev progress** must be reviewed and signed off on by UX designers before going live
- **Custom components:** If a required component doesn't exist in CORE UI, flag it for the design team — do not build one-off components without design alignment

## Updating This Guide

When the Components section of the Zeroheight docs is explored and component selectors are confirmed, update the "Component Catalog" section above with:
- Verified `cui-*` selector names
- Available input properties / variants per component
- Links to specific component pages in Zeroheight
- Any deprecated or renamed components across versions
