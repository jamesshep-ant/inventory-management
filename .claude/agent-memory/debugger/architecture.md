---
name: architecture
description: Key file paths, API routes, and architecture notes for debugging the inventory management app.
---

# Architecture Notes

## Backend API Routes (server/main.py) — complete list as of investigation

- GET /
- GET /api/inventory
- GET /api/inventory/{item_id}
- GET /api/orders
- GET /api/orders/{order_id}
- GET /api/demand
- GET /api/backlog
- GET /api/dashboard/summary
- GET /api/spending/summary
- GET /api/spending/monthly
- GET /api/spending/categories
- GET /api/spending/transactions
- GET /api/reports/quarterly
- GET /api/reports/monthly-trends
- GET /api/restocking-orders
- POST /api/restocking-orders
- POST /api/purchase-orders (referenced in api.js:98, confirmed in main.py line 120)
- GET /api/purchase-orders/{backlog_item_id}
- **MISSING**: /api/tasks (all CRUD)

## Key Frontend Files

- `client/src/App.vue` — shell, loads tasks on mount via api.getTasks()
- `client/src/api.js` — all API calls centralized here
- `client/src/views/Dashboard.vue` — main dashboard, uses PurchaseOrderModal (not yet created)
- `client/src/components/` — modal components; PurchaseOrderModal.vue is MISSING

## Components present in client/src/components/

- BacklogDetailModal.vue
- CostDetailModal.vue
- FilterBar.vue
- InventoryDetailModal.vue
- LanguageSwitcher.vue
- ProductDetailModal.vue
- ProfileDetailsModal.vue
- ProfileMenu.vue
- TasksModal.vue
- **MISSING**: PurchaseOrderModal.vue (used in Dashboard.vue:289)

## Data flow reminder

Vue filters → api.js → FastAPI → mock_data.py JSON files → Pydantic validation → response
