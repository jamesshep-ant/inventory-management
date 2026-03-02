# Commit: CSV Export on Inventory Page

**SHA**: `0475fc7` | **Branch**: `new_features` | **Status**: Committed (local)

## 1. Summary (3 files, +812 -655)

Adds an Export CSV button to the Inventory page that downloads the currently filtered + sorted item list as a CSV file.

**Files**:

- `client/src/views/Inventory.vue` — export button, `exportCsv()` with RFC 4180 escaping, Blob download, button styles
- `client/src/locales/en.js` — `inventory.exportCsv: "Export CSV"`
- `client/src/locales/ja.js` — `inventory.exportCsv: "CSVエクスポート"`

**Commit**: `feat(inventory): add CSV export button`

> Line counts inflated by pre-existing Prettier formatting changes (single→double quotes) that were already uncommitted in these files. Actual feature delta is ~100 lines.

## 2. Validation

| Gate             | Result                                                                                              |
| ---------------- | --------------------------------------------------------------------------------------------------- |
| E2E (Playwright) | ✅ Button renders, click downloads `inventory-2026-03-02.csv`, 32 rows + header, correct sort order |
| Secrets scan     | ✅ Clean                                                                                            |
| Console errors   | ✅ None related to feature                                                                          |
| Branch safety    | ✅ `new_features` (not main)                                                                        |

No lint/test scripts found in `client/package.json`.

## 3. Behavioral Changes

- New: CSV export button in Inventory card header (outline style, download icon)
- Exports `filteredItems` — CSV respects warehouse/category filters + search + stock-status sort
- Button disabled when list is empty
- Filename: `inventory-YYYY-MM-DD.csv`
- **Breaking changes**: None

## 4. Completion

**PR**: Not created (local commit only)
**Next**: Push + PR when ready, or continue with next feature
