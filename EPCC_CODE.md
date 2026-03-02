# Implementation: CSV Export on Inventory Page

**Mode**: default | **Date**: 2026-03-02 | **Status**: Complete

## 1. Changes (3 files, +~100 lines)

**Modified**:

- `client/src/views/Inventory.vue` — Added `.export-btn` in card header, `exportCsv()` function with RFC 4180 field escaping, Blob-based download, and button styles matching the outline pattern from `Restocking.vue:623`
- `client/src/locales/en.js:84` — Added `inventory.exportCsv: "Export CSV"`
- `client/src/locales/ja.js:84` — Added `inventory.exportCsv: "CSVエクスポート"`

## 2. Quality

**E2E verified via Playwright**:

- Button renders with download icon next to search box
- Click downloads `inventory-2026-03-02.csv`
- File contains 1 header row + 32 data rows (matches table's 32 SKUs)
- Rows preserve the filtered/sorted order (Low Stock → Adequate → In Stock)
- No console errors related to this feature

**Screenshot**: `.playwright-mcp/inventory-export-button.png`

## 3. Decisions

**Export `filteredItems`, not raw `items`**: CSV matches what the user sees — respects warehouse/category filters and search query.

**Raw data in CSV, not translated labels**: Name/category/location use raw API values (`item.name`, `item.category`, `item.location`) for data portability across locales. Status is the exception — it uses the translated label since there's no raw status field in the data (it's derived from quantity vs reorder point).

**RFC 4180 escaping**: Fields containing `,`, `"`, or `\n` are quoted with doubled embedded quotes — prevents column misalignment on names like "Dual Output ±15V Power Supply". Commented inline per project convention.

**Client-side via Blob + `<a download>`**: No backend endpoint needed; simpler for a filter-aware export that's already in memory.

**Button disabled when empty**: `:disabled="filteredItems.length === 0"` prevents exporting an empty CSV.

## 4. Handoff

**Run**: `/epcc-commit` when ready
**Blockers**: None
**TODOs**: None
