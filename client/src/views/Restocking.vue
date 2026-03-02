<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t("restocking.title") }}</h2>
      <p>{{ t("restocking.description") }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t("common.loading") }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <!-- Budget Card -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t("restocking.budgetCard.title") }}</h3>
        </div>

        <div class="budget-slider-section">
          <div class="slider-labels">
            <span>{{ formatCurrency(1000, currentCurrency) }}</span>
            <span>{{ formatCurrency(50000, currentCurrency) }}</span>
          </div>
          <input
            v-model.number="budget"
            type="range"
            min="1000"
            max="50000"
            step="500"
            class="budget-slider"
          />
        </div>

        <div class="budget-summary">
          <div class="budget-stat">
            <span class="budget-label">{{
              t("restocking.budgetCard.selected")
            }}</span>
            <span class="budget-value">{{
              formatCurrency(budget, currentCurrency)
            }}</span>
          </div>
          <div class="budget-stat">
            <span class="budget-label">{{
              t("restocking.budgetCard.allocated")
            }}</span>
            <span class="budget-value allocated">{{
              formatCurrency(allocatedTotal, currentCurrency)
            }}</span>
          </div>
          <div class="budget-stat">
            <span class="budget-label">{{
              t("restocking.budgetCard.remaining")
            }}</span>
            <span class="budget-value remaining">{{
              formatCurrency(remainingBudget, currentCurrency)
            }}</span>
          </div>
        </div>
      </div>

      <!-- Recommendations Table -->
      <div class="card">
        <div class="card-header">
          <div>
            <h3 class="card-title">
              {{ t("restocking.recommendations.title") }}
            </h3>
            <p class="drag-hint">
              {{ t("restocking.recommendations.dragHint") }}
            </p>
          </div>
          <button
            v-if="isCustomOrder"
            class="reset-priority-btn"
            @click="resetPriority"
          >
            {{ t("restocking.recommendations.resetPriority") }}
          </button>
        </div>

        <div v-if="recommendations.length === 0" class="empty-state">
          {{ t("restocking.recommendations.empty") }}
        </div>

        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th class="drag-handle-header"></th>
                <th>{{ t("restocking.recommendations.sku") }}</th>
                <th>{{ t("restocking.recommendations.item") }}</th>
                <th>{{ t("restocking.recommendations.trend") }}</th>
                <th>{{ t("restocking.recommendations.forecastGap") }}</th>
                <th>{{ t("restocking.recommendations.unitCost") }}</th>
                <th>{{ t("restocking.recommendations.recommendedQty") }}</th>
                <th>{{ t("restocking.recommendations.lineTotal") }}</th>
              </tr>
            </thead>
            <tbody>
              <!-- Use rec.sku as key — unique per inventory item, never index. Drag handlers reorder priorityOrder ref. -->
              <tr
                v-for="(rec, index) in recommendations"
                :key="rec.sku"
                draggable="true"
                @dragstart="onDragStart(index)"
                @dragover.prevent="onDragOver(index)"
                @drop="onDrop(index)"
                @dragend="onDragEnd"
                :class="{
                  'not-covered': rec.allocatedQty === 0,
                  dragging: draggedIndex === index,
                  'drag-over':
                    dragOverIndex === index && draggedIndex !== index,
                }"
              >
                <td class="drag-handle">⠿</td>
                <td>
                  <strong>{{ rec.sku }}</strong>
                </td>
                <td>{{ rec.name }}</td>
                <td>
                  <span :class="['badge', rec.trend]">{{
                    t(`trends.${rec.trend}`)
                  }}</span>
                </td>
                <td>{{ rec.gap }}</td>
                <td>{{ formatCurrency(rec.unit_cost, currentCurrency) }}</td>
                <td>
                  <span v-if="rec.allocatedQty > 0">{{
                    rec.allocatedQty
                  }}</span>
                  <!-- Show "not covered" note instead of a zero qty for budget-exceeded rows -->
                  <span v-else class="not-covered-note">{{
                    t("restocking.recommendations.notCovered")
                  }}</span>
                </td>
                <td>
                  <span v-if="rec.allocatedQty > 0">{{
                    formatCurrency(rec.lineTotal, currentCurrency)
                  }}</span>
                  <span v-else class="not-covered-note">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Place Order -->
      <div class="order-section">
        <div v-if="successMessage" class="success-message">
          {{ successMessage }}
        </div>
        <button
          class="place-order-btn"
          :disabled="submitting || orderItems.length === 0"
          @click="placeOrder"
        >
          {{
            submitting ? t("restocking.submitting") : t("restocking.placeOrder")
          }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from "vue";
import { api } from "../api";
import { useI18n } from "../composables/useI18n";
import { formatCurrency } from "../utils/currency";

export default {
  name: "Restocking",
  setup() {
    const { t, currentCurrency } = useI18n();

    // --- Reactive state ---
    const loading = ref(true);
    const error = ref(null);
    const forecasts = ref([]);
    const inventory = ref([]);
    const budget = ref(10000);
    const submitting = ref(false);
    const successMessage = ref(null);

    // --- O(1) lookup map: sku → inventory item ---
    const inventoryBySku = computed(() => {
      const map = new Map();
      for (const item of inventory.value) {
        map.set(item.sku, item);
      }
      return map;
    });

    // --- Layer 1: Base candidates (no sort, no allocation) ---
    // Pure derive: join forecasts ↔ inventory, compute gap, filter actionable items.
    const candidates = computed(() => {
      const result = [];
      for (const forecast of forecasts.value) {
        const invItem = inventoryBySku.value.get(forecast.item_sku);
        if (!invItem || typeof invItem.unit_cost !== "number") continue;

        const gap = forecast.forecasted_demand - forecast.current_demand;
        if (gap <= 0) continue;

        result.push({
          sku: forecast.item_sku,
          name: forecast.item_name,
          trend: forecast.trend,
          gap,
          unit_cost: invItem.unit_cost,
        });
      }
      return result;
    });

    // --- Layer 2: Priority order (stateful — user can reorder via drag) ---
    // Default auto-priority: highest gap first (same heuristic as before the refactor).
    const priorityOrder = ref([]);

    const defaultPriorityOrder = computed(() =>
      [...candidates.value].sort((a, b) => b.gap - a.gap).map((c) => c.sku),
    );

    // Initialize priority whenever the candidate set changes (data load).
    // Restocking.vue loads once on mount and has no filter watchers, so this runs once —
    // the user's manual reorder is preserved for the session.
    watch(
      candidates,
      () => {
        priorityOrder.value = [...defaultPriorityOrder.value];
      },
      { immediate: true },
    );

    const resetPriority = () => {
      priorityOrder.value = [...defaultPriorityOrder.value];
    };

    // True when the user has manually reordered — gates the Reset button visibility.
    const isCustomOrder = computed(() => {
      if (priorityOrder.value.length !== defaultPriorityOrder.value.length)
        return false;
      return priorityOrder.value.some(
        (sku, i) => sku !== defaultPriorityOrder.value[i],
      );
    });

    // --- Layer 3: Greedy budget allocation in user's priority order ---
    // O(1) lookup for building recommendations from priorityOrder.
    const candidatesBySku = computed(() => {
      const m = new Map();
      for (const c of candidates.value) m.set(c.sku, c);
      return m;
    });

    // Recomputes when budget OR priorityOrder changes → drag instantly re-flows allocation.
    // Rows that can't receive even 1 unit are kept (allocatedQty=0) so the user can
    // see what was excluded by budget constraints.
    const recommendations = computed(() => {
      let remaining = budget.value;
      const result = [];

      for (const sku of priorityOrder.value) {
        const candidate = candidatesBySku.value.get(sku);
        if (!candidate) continue; // defensive — stale SKU in priorityOrder

        const fullCost = candidate.gap * candidate.unit_cost;
        let allocatedQty;
        if (fullCost <= remaining) {
          // Entire gap fits in budget
          allocatedQty = candidate.gap;
          remaining -= fullCost;
        } else {
          // Partial allocation: as many units as remaining budget covers.
          // Once budget is exhausted, all subsequent items get 0 units.
          const partialQty = Math.floor(remaining / candidate.unit_cost);
          allocatedQty = partialQty > 0 ? partialQty : 0;
          remaining = 0;
        }

        result.push({
          ...candidate,
          allocatedQty,
          lineTotal: allocatedQty * candidate.unit_cost,
        });
      }

      return result;
    });

    // --- Derived budget figures ---
    const allocatedTotal = computed(() =>
      recommendations.value.reduce((sum, rec) => sum + rec.lineTotal, 0),
    );

    const remainingBudget = computed(() => budget.value - allocatedTotal.value);

    // --- Items to include in POST body (only those actually allocated) ---
    const orderItems = computed(() =>
      recommendations.value
        .filter((rec) => rec.allocatedQty > 0)
        .map((rec) => ({
          sku: rec.sku,
          name: rec.name,
          quantity: rec.allocatedQty,
          unit_cost: rec.unit_cost,
        })),
    );

    // --- Data loading ---
    const loadData = async () => {
      loading.value = true;
      error.value = null;
      try {
        // Fetch forecasts and full (unfiltered) inventory in parallel.
        // Inventory is fetched without filters because we need unit_cost for
        // every possible forecast SKU regardless of the active warehouse/category filter.
        const [forecastsData, inventoryData] = await Promise.all([
          api.getDemandForecasts(),
          api.getInventory(),
        ]);
        forecasts.value = forecastsData;
        inventory.value = inventoryData;
      } catch (err) {
        error.value = "Failed to load restocking data: " + err.message;
        console.error(err);
      } finally {
        loading.value = false;
      }
    };

    // --- Submit restocking order ---
    const placeOrder = async () => {
      if (orderItems.value.length === 0) return;
      submitting.value = true;
      try {
        const response = await api.createRestockingOrder(orderItems.value);
        successMessage.value = t("restocking.orderPlaced", {
          orderNumber: response.order_number,
        });
        // Auto-clear the success banner after 5 seconds
        setTimeout(() => {
          successMessage.value = null;
        }, 5000);
      } catch (err) {
        error.value = "Failed to submit restocking order: " + err.message;
        console.error(err);
      } finally {
        submitting.value = false;
      }
    };

    // --- Drag-and-drop state & handlers (native HTML5 DnD) ---
    const draggedIndex = ref(null);
    const dragOverIndex = ref(null);

    const onDragStart = (index) => {
      draggedIndex.value = index;
    };

    const onDragOver = (index) => {
      dragOverIndex.value = index;
    };

    const onDragEnd = () => {
      draggedIndex.value = null;
      dragOverIndex.value = null;
    };

    const onDrop = (dropIndex) => {
      if (draggedIndex.value === null || draggedIndex.value === dropIndex) {
        onDragEnd();
        return;
      }
      // Reorder priorityOrder: remove dragged SKU from its slot, insert at drop slot
      const order = [...priorityOrder.value];
      const [moved] = order.splice(draggedIndex.value, 1);
      order.splice(dropIndex, 0, moved);
      priorityOrder.value = order;
      onDragEnd();
    };

    onMounted(loadData);

    return {
      t,
      currentCurrency,
      formatCurrency,
      loading,
      error,
      budget,
      submitting,
      successMessage,
      recommendations,
      allocatedTotal,
      remainingBudget,
      orderItems,
      placeOrder,
      draggedIndex,
      dragOverIndex,
      onDragStart,
      onDragOver,
      onDragEnd,
      onDrop,
      resetPriority,
      isCustomOrder,
    };
  },
};
</script>

<style scoped>
/* ---- Budget slider section ---- */
.budget-slider-section {
  margin-bottom: 1.5rem;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-size: 0.813rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.budget-slider {
  width: 100%;
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  outline: none;
  cursor: pointer;
  accent-color: var(--accent);
}

/* Thumb: larger for easy grabbing */
.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
  border: 3px solid #ffffff;
  box-shadow:
    0 0 0 2px var(--accent),
    0 2px 6px rgba(200, 16, 46, 0.3);
  transition: box-shadow 0.15s ease;
}

.budget-slider::-webkit-slider-thumb:hover {
  box-shadow:
    0 0 0 3px rgba(200, 16, 46, 0.2),
    0 2px 8px rgba(200, 16, 46, 0.4);
}

.budget-slider::-moz-range-thumb {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
  border: 3px solid #ffffff;
  box-shadow: 0 0 0 2px var(--accent);
}

/* ---- Budget summary: 3-column grid ---- */
.budget-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--border);
}

.budget-stat {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.budget-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.budget-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.025em;
}

.budget-value.allocated {
  color: var(--accent);
}

.budget-value.remaining {
  color: var(--success);
}

/* ---- Recommendations table ---- */
/* Rows where the budget ran out are still shown so users understand coverage */
.not-covered {
  opacity: 0.45;
}

.not-covered td {
  font-style: italic;
}

.not-covered-note {
  font-size: 0.813rem;
  color: var(--text-secondary);
  font-style: italic;
}

/* ---- Empty state ---- */
.empty-state {
  padding: 2.5rem;
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.938rem;
}

/* ---- Place Order section ---- */
.order-section {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1rem;
  margin-top: 0.5rem;
  margin-bottom: 2rem;
}

.success-message {
  background: var(--success-bg);
  color: var(--success);
  padding: 0.75rem 1.25rem;
  border-radius: 6px;
  font-size: 0.938rem;
  font-weight: 500;
  border: 1px solid rgba(10, 125, 62, 0.3);
}

.place-order-btn {
  background: var(--accent);
  color: #ffffff;
  border: none;
  padding: 0.75rem 1.75rem;
  border-radius: 6px;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    background 0.15s ease,
    box-shadow 0.15s ease;
}

.place-order-btn:hover:not(:disabled) {
  background: var(--accent-dark);
  box-shadow: 0 2px 8px rgba(200, 16, 46, 0.3);
}

.place-order-btn:disabled {
  background: var(--text-muted);
  cursor: not-allowed;
  box-shadow: none;
}

/* ---- Drag-and-drop reorder ---- */
.drag-handle-header {
  width: 30px;
}

.drag-handle {
  cursor: grab;
  color: var(--text-muted);
  width: 30px;
  text-align: center;
  user-select: none;
  font-size: 1rem;
}

.drag-handle:active {
  cursor: grabbing;
}

/* Whole-row grab affordance (overrides default cursor on tbody rows) */
tbody tr[draggable="true"] {
  cursor: grab;
}

tbody tr[draggable="true"]:active {
  cursor: grabbing;
}

tr.dragging {
  opacity: 0.4;
}

/* Drop target indicator — blue top border shows where the row will land */
tr.drag-over td {
  border-top: 2px solid var(--accent);
}

/* ---- Recommendations card header additions ---- */
.drag-hint {
  margin: 0.25rem 0 0 0;
  font-size: 0.813rem;
  color: var(--text-muted);
}

.reset-priority-btn {
  background: transparent;
  color: var(--accent);
  border: 1px solid var(--accent);
  padding: 0.375rem 0.875rem;
  border-radius: 4px;
  font-size: 0.813rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s ease;
}

.reset-priority-btn:hover {
  background: var(--accent-bg);
}
</style>
