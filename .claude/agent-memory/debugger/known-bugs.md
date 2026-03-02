---
name: known-bugs
description: Confirmed bugs found in the inventory management app, with root causes and proposed fixes.
---

# Known Bugs

## BUG-001: PurchaseOrderModal missing from Dashboard

- **Symptom**: `[Vue warn]: Failed to resolve component: PurchaseOrderModal` on every Dashboard load
- **File**: `client/src/views/Dashboard.vue` line 289
- **Root cause**: `PurchaseOrderModal` is used in the template and its open/create/view logic is fully implemented in Dashboard.vue (lines 327–330, 653–673), but the component file `client/src/components/PurchaseOrderModal.vue` does not exist and is not imported in the script block (line 306–307 only imports ProductDetailModal and BacklogDetailModal).
- **Fix**: Create `client/src/components/PurchaseOrderModal.vue` and add it to Dashboard's `components: {}` and import (apply via vue-expert). The component needs props: `isOpen`, `backlogItem`, `mode`; event `@close` and `@po-created`.
- **Severity**: Warning (not crash) — the "Create PO" button in the shortages table is silently broken.

## BUG-002: /api/tasks endpoint missing from backend

- **Symptom**: `[ERROR] Failed to load tasks: AxiosError: Request failed with status code 404` on every page load
- **File**: `client/src/App.vue` line 94 → `client/src/api.js` line 78 → `GET http://localhost:8001/api/tasks`
- **Root cause**: `api.getTasks()` (api.js:78) calls `GET /api/tasks`, but this endpoint is not defined anywhere in `server/main.py`. The full route list contains no `/api/tasks`, `/api/tasks/{id}` or related PATCH/DELETE routes either. The frontend also calls `api.createTask`, `api.deleteTask`, and `api.toggleTask` — none of which have backend implementations.
- **Fix**: Add `/api/tasks` GET, POST, DELETE, PATCH endpoints to `server/main.py` with an in-memory store (consistent with the mock-data pattern). Alternatively, remove the task API calls from App.vue if tasks are meant to be client-only (the `currentUser.value.tasks` mock already works without API).
- **Severity**: Error on every page load — non-blocking but noisy.

## Reproduction commands

```bash
# Confirm tasks 404
curl http://localhost:8001/api/tasks
# => {"detail":"Not Found"}

# Confirm no tasks route in backend
grep -n "tasks" server/main.py
# => no route definitions found

# Confirm PurchaseOrderModal is missing
ls client/src/components/ | grep -i purchase
# => (no output)
```
