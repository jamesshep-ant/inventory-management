---
name: vue-optimize
description: Analyze Vue 3 component structure and suggest performance and code reuse optimizations. Use when reviewing .vue files, when the user asks to optimize/refactor Vue components, or when a component feels slow or repetitive.
---

# Vue Component Optimization Guide

This skill provides a structured process for analyzing Vue 3 Composition API components and producing actionable optimization recommendations grounded in **performance** and **code reuse**.

## Analysis Workflow

When asked to optimize a Vue component:

1. **Read the target `.vue` file(s) fully** — template, script, and style blocks.
2. **Build a mental dependency graph** — which refs feed which computeds, which computeds feed the template.
3. **Run each checklist below** — note every hit with a file:line reference.
4. **Rank findings** — prioritize by impact (render frequency × work per render) over stylistic nits.
5. **Report** using the format at the bottom.

Do **not** make edits as part of the analysis unless explicitly asked. Produce findings first.

---

## Performance Checklist

### P1. Methods doing computed's job ⚠️ High impact

A method called in a template re-runs on **every** component re-render. A `computed()` is cached until its reactive dependencies change.

**Look for:**

- Functions called with no arguments inside `{{ }}` or `v-for`/`v-if`
- Functions that derive pure values from reactive state (no side effects)
- `.filter()`, `.map()`, `.reduce()`, `.sort()` called directly in the template

**Example (bad):**

```vue
<!-- runs getFilteredItems() on every re-render -->
<tr v-for="item in getFilteredItems()" :key="item.id">
```

**Fix:**

```js
const filteredItems = computed(() => items.value.filter((i) => i.active));
```

**Scan command:**

```
Grep for `\{\{ \w+\(` in template block → methods-in-template candidates
Grep for `v-for="\w+ in \w+\(` → method called in v-for
```

---

### P2. Heavy work inside computed without memoizable inputs

`computed` caches the _result_, but if the computation reads a large ref that changes often, the cache is worthless.

**Look for:**

- `computed` that reads a frequently-mutated ref (e.g. a text input bound via `v-model`) and does expensive work
- Sorting/filtering large arrays on every keystroke

**Fix options:**

- Debounce the upstream ref (use `watchDebounced` from `@vueuse/core`)
- Split: cheap computed for the filter predicate, expensive computed that only depends on the cheap one + the data array

---

### P3. Over-broad reactive state

Putting unrelated state in one `ref({...})` or `reactive({...})` means changing any field invalidates every computed/template binding that reads _any_ field.

**Look for:**

- A single `const state = reactive({ a, b, c, d, ... })` where `a` and `d` are unrelated
- Computeds that destructure many fields but only use one

**Fix:** Separate refs per logical concern. This project already does this well — e.g. `Restocking.vue` has separate `budget`, `submitting`, `forecasts`, `inventory` refs.

---

### P4. `v-if` vs `v-show` mismatch

- `v-if`: tears down/recreates the DOM + component instance. Expensive toggle, cheap when hidden.
- `v-show`: toggles CSS `display`. Cheap toggle, always mounted.

**Look for:**

- `v-if` on elements toggled by high-frequency state (hover, drag, filter changes)
- `v-show` on heavy subtrees that are rarely shown (modals that open once)

**Scan:**

```
Grep for `v-if=` and `v-show=` → cross-reference with the reactivity of the condition
```

---

### P5. Unstable `v-for` keys

Using `index` or a non-unique value as `:key` causes Vue to reuse the wrong DOM nodes when the list reorders/filters.

**Look for:**

```vue
<div v-for="(item, i) in items" :key="i">     <!-- bad -->
<div v-for="item in items" :key="item.name">  <!-- bad if names can repeat -->
```

**Fix:** Use a stable unique field (`item.id`, `item.sku`). This project's convention: `sku` for inventory items, `id` for orders, `month` for time-series.

---

### P6. Unnecessary reactivity wrapping

Wrapping static config or never-mutated data in `ref()`/`reactive()` adds proxy overhead and tracking.

**Look for:**

- `const columns = ref([...])` where `columns` is never reassigned or mutated
- `ref()` around imported constants

**Fix:** Plain `const`. Use `shallowRef()` if you only need to track reassignment of large objects, not deep mutation.

---

### P7. Missed `Promise.all` parallelism

Sequential awaits on independent requests double the load time.

**Look for:**

```js
const a = await api.getA();
const b = await api.getB(); // doesn't depend on a
```

**Fix:**

```js
const [a, b] = await Promise.all([api.getA(), api.getB()]);
```

`Restocking.vue:284` and `Orders.vue:144` already do this correctly — use them as the reference pattern.

---

### P8. Lookup maps missing (O(n²) joins)

Joining two arrays with `.find()` inside a loop is O(n²).

**Look for:**

```js
forecasts.map(f => {
  const inv = inventory.find(i => i.sku === f.sku)  // O(n) per iteration
  ...
})
```

**Fix:** Build a `Map` once, lookup is O(1). See `Restocking.vue:159` (`inventoryBySku`) for the reference pattern.

---

## Code Reuse Checklist

### R1. Composable candidates

Extract to `client/src/composables/use*.js` when logic is:

- **Stateful** and **reused** across ≥2 components, OR
- **Self-contained** and >30 lines even if only used once (easier to test)

**Existing composables to extend rather than duplicate:**

- `useFilters.js` — warehouse/category/status/period filter state
- `useI18n.js` — translation + currency
- `useAuth.js` — auth state

**Common candidates in this codebase:**

- Data loading pattern (`loading`/`error`/`loadData` try-catch-finally) — appears in every view. A `useAsyncData(fetchFn)` composable would eliminate ~15 lines per view.
- Date formatting — if `formatDate` appears in ≥2 views, move to `client/src/utils/`.
- Status class mapping (`getOrderStatusClass`) — if it spreads, extract.

---

### R2. Component extraction

Extract a `<template>` fragment to a component when:

- The fragment is >30 lines AND repeated ≥2 times, OR
- The parent template is >150 lines total, OR
- The fragment has its own local state/handlers that don't interact with siblings

**Scan:**

- Count lines in `<template>` — if >150, look for natural seams (cards, table sections, modals)
- Grep for repeated class names across the template (e.g. multiple `class="kpi-card"` blocks → `<KpiCard>` candidate)

**Current candidates in this project:**

- `Dashboard.vue` KPI cards — 5 nearly-identical ~12-line blocks → `<KpiCard :label :value :goal :progress>`
- Repeated `<div class="card"><div class="card-header">...</div>` wrapper across all views → `<Card title="...">` slot component

---

### R3. Duplicate computed/method logic

Same derivation appearing in multiple components.

**Scan:**

```
Grep across client/src/views/*.vue for identical function bodies
Look for: formatCurrency, formatDate, calculatePercentage, status→class mappings
```

**Fix:** Move to `client/src/utils/` (pure functions) or `client/src/composables/` (stateful).

---

### R4. Inline magic values

Hardcoded numbers/strings that appear in both template and script, or across components.

**Look for:**

- Colors repeated in `<style scoped>` that should be CSS custom properties
- Status strings (`'Delivered'`, `'Processing'`) hardcoded in multiple places
- API paths duplicated outside `api.js`

**Fix:** Constants file, CSS variables in `App.vue`, or locale keys.

---

## Grep Recipes for Quick Scanning

Run these to build a findings list fast:

```
# Methods called in templates (P1 candidates)
Grep: pattern="\{\{ \w+\(" glob="*.vue" output_mode=content

# v-for with index keys (P5)
Grep: pattern=":key=\"(i|index|idx)\"" glob="*.vue" output_mode=content

# Sequential awaits (P7)
Grep: pattern="await .+\n\s+.+await" glob="*.vue" multiline=true output_mode=content

# .find inside .map/.filter (P8)
Grep: pattern="\.(map|filter|forEach)\([^)]*\.find\(" glob="*.vue" output_mode=content

# Repeated format functions (R3)
Grep: pattern="const format\w+ = " glob="*.vue" output_mode=content

# Large templates (R2)
wc -l client/src/views/*.vue | sort -rn
```

---

## Report Format

Present findings in this structure:

```markdown
## Summary

<1-2 sentence overview of the component's current health>

## Performance Findings

| #   | Rule | Location         | Issue                                                 | Suggested Fix                           | Est. Impact                           |
| --- | ---- | ---------------- | ----------------------------------------------------- | --------------------------------------- | ------------------------------------- |
| 1   | P1   | Dashboard.vue:98 | `getCircleSegment()` called 8× in template per render | Convert to computed map keyed by status | High — re-runs on every filter change |
| 2   | P5   | ...              | ...                                                   | ...                                     | ...                                   |

## Code Reuse Findings

| #   | Rule | Location(s)         | Issue                                         | Suggested Fix                         |
| --- | ---- | ------------------- | --------------------------------------------- | ------------------------------------- |
| 1   | R1   | All views           | loading/error/loadData pattern duplicated ~8× | Extract `useAsyncData(fn)` composable |
| 2   | R2   | Dashboard.vue:14-68 | 5 near-identical KPI card blocks              | Extract `<KpiCard>` component         |

## Recommended Priority

1. <highest-impact item, 1 sentence why>
2. ...
3. ...

## Not Worth Doing

- <low-ROI items the user might expect but you're deliberately skipping, with reason>
```

**Rules for the report:**

- Always cite `file:line` so the user can jump to it.
- "Est. Impact" is High/Medium/Low — High = affects every render or every keystroke; Low = one-time or rarely-triggered.
- Keep "Not Worth Doing" honest — don't pad with micro-optimizations.

---

## Project-Specific Notes

- This project uses **Composition API only** — don't suggest Options API patterns.
- Composables live in `client/src/composables/`, utils in `client/src/utils/`.
- Charts are **custom SVG** (no library) — don't suggest chart library migrations.
- The vue-expert subagent should be used for actually _implementing_ fixes to `.vue` files; this skill is for _analysis_.
