<template>
  <div class="reports">
    <div class="page-header">
      <h2>{{ t("reports.title") }}</h2>
      <p>{{ t("reports.description") }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t("common.loading") }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <!-- Quarterly Performance -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t("reports.quarterly.title") }}</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t("reports.quarterly.quarter") }}</th>
                <th>{{ t("reports.quarterly.totalOrders") }}</th>
                <th>{{ t("reports.quarterly.totalRevenue") }}</th>
                <th>{{ t("reports.quarterly.avgOrderValue") }}</th>
                <th>{{ t("reports.quarterly.fulfillmentRate") }}</th>
              </tr>
            </thead>
            <tbody>
              <!-- Use q.quarter as key — unique per row, avoids index-as-key bug -->
              <tr v-for="q in quarterlyData" :key="q.quarter">
                <td>
                  <strong>{{ q.quarter }}</strong>
                </td>
                <td>{{ q.total_orders }}</td>
                <td>{{ formatCurrency(q.total_revenue, currentCurrency) }}</td>
                <td>
                  {{ formatCurrency(q.avg_order_value, currentCurrency) }}
                </td>
                <td>
                  <span :class="getFulfillmentClass(q.fulfillment_rate)">
                    {{ q.fulfillment_rate }}%
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Monthly Trends Chart -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t("reports.monthly.title") }}</h3>
        </div>
        <div class="chart-container">
          <div class="bar-chart">
            <!-- Use month.month (YYYY-MM string) as key — unique, stable -->
            <div
              v-for="month in monthlyData"
              :key="month.month"
              class="bar-wrapper"
            >
              <div class="bar-container">
                <div
                  class="bar"
                  :style="{ height: getBarHeight(month.revenue) + 'px' }"
                  :title="formatCurrency(month.revenue, currentCurrency)"
                ></div>
              </div>
              <div class="bar-label">{{ formatMonth(month.month) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Month-over-Month Comparison -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t("reports.mom.title") }}</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t("reports.mom.month") }}</th>
                <th>{{ t("reports.mom.orders") }}</th>
                <th>{{ t("reports.mom.revenue") }}</th>
                <th>{{ t("reports.mom.change") }}</th>
                <th>{{ t("reports.mom.growthRate") }}</th>
              </tr>
            </thead>
            <tbody>
              <!--
                Keep (month, index) destructure here — index is needed to access
                monthlyData[index - 1] for the previous-month comparison.
                Use month.month as key (not index) per project conventions.
              -->
              <tr v-for="(month, index) in monthlyData" :key="month.month">
                <td>
                  <strong>{{ formatMonth(month.month) }}</strong>
                </td>
                <td>{{ month.order_count }}</td>
                <td>{{ formatCurrency(month.revenue, currentCurrency) }}</td>
                <td>
                  <span
                    v-if="index > 0"
                    :class="
                      getChangeClass(
                        month.revenue,
                        monthlyData[index - 1].revenue,
                      )
                    "
                  >
                    {{
                      getChangeValue(
                        month.revenue,
                        monthlyData[index - 1].revenue,
                      )
                    }}
                  </span>
                  <span v-else>-</span>
                </td>
                <td>
                  <span
                    v-if="index > 0"
                    :class="
                      getChangeClass(
                        month.revenue,
                        monthlyData[index - 1].revenue,
                      )
                    "
                  >
                    {{
                      getGrowthRate(
                        month.revenue,
                        monthlyData[index - 1].revenue,
                      )
                    }}
                  </span>
                  <span v-else>-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Summary Stats -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">{{ t("reports.stats.totalRevenue") }}</div>
          <div class="stat-value">
            {{ formatCurrency(totalRevenue, currentCurrency) }}
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t("reports.stats.avgMonthly") }}</div>
          <div class="stat-value">
            {{ formatCurrency(avgMonthlyRevenue, currentCurrency) }}
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t("reports.stats.totalOrders") }}</div>
          <div class="stat-value">{{ totalOrders }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t("reports.stats.bestQuarter") }}</div>
          <div class="stat-value">{{ bestQuarter }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from "vue";
import { api } from "../api";
import { useFilters } from "../composables/useFilters";
import { useI18n } from "../composables/useI18n";
import { formatCurrency } from "../utils/currency";

// Maps two-digit month number string (01-12) to locale key (jan-dec)
const MONTH_KEY_MAP = {
  "01": "jan",
  "02": "feb",
  "03": "mar",
  "04": "apr",
  "05": "may",
  "06": "jun",
  "07": "jul",
  "08": "aug",
  "09": "sep",
  10: "oct",
  11: "nov",
  12: "dec",
};

export default {
  name: "Reports",
  setup() {
    const { t, currentCurrency } = useI18n();

    const {
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      getCurrentFilters,
    } = useFilters();

    const loading = ref(true);
    const error = ref(null);
    const quarterlyData = ref([]);
    const monthlyData = ref([]);

    // --- Computed summary stats ---
    // These auto-recompute when monthlyData/quarterlyData change; no manual
    // recalculation call is needed after loadData resolves.

    const totalRevenue = computed(() =>
      monthlyData.value.reduce((sum, m) => sum + m.revenue, 0),
    );

    // Guard divide-by-zero when no data is loaded yet
    const avgMonthlyRevenue = computed(() =>
      monthlyData.value.length > 0
        ? totalRevenue.value / monthlyData.value.length
        : 0,
    );

    const totalOrders = computed(() =>
      monthlyData.value.reduce((sum, m) => sum + m.order_count, 0),
    );

    const bestQuarter = computed(() => {
      if (quarterlyData.value.length === 0) return "-";
      return quarterlyData.value.reduce((best, q) =>
        q.total_revenue > best.total_revenue ? q : best,
      ).quarter;
    });

    // --- Bar chart optimisation ---
    // Compute maxRevenue once (O(n)) so getBarHeight is O(1) instead of O(n²)
    const maxRevenue = computed(() =>
      Math.max(0, ...monthlyData.value.map((m) => m.revenue)),
    );

    // --- Data loading ---

    const loadData = async () => {
      loading.value = true;
      error.value = null;
      try {
        const filters = getCurrentFilters();
        // Fetch both endpoints in parallel to reduce total wait time
        const [quarterly, monthly] = await Promise.all([
          api.getReportsQuarterly(filters),
          api.getReportsMonthlyTrends(filters),
        ]);
        quarterlyData.value = quarterly;
        monthlyData.value = monthly;
      } catch (err) {
        error.value = "Failed to load reports: " + err.message;
      } finally {
        loading.value = false;
      }
    };

    // Re-fetch whenever any filter changes — mirrors Orders.vue:217-222
    watch(
      [selectedPeriod, selectedLocation, selectedCategory, selectedStatus],
      () => {
        loadData();
      },
    );

    onMounted(loadData);

    // --- Helper functions ---

    // Returns height in px (max 200px) relative to the tallest bar
    const getBarHeight = (revenue) => {
      if (maxRevenue.value === 0) return 0;
      return (revenue / maxRevenue.value) * 200;
    };

    // Convert "YYYY-MM" → localised abbreviated month + year, e.g. "Jan 2024"
    const formatMonth = (monthStr) => {
      const parts = monthStr.split("-");
      const year = parts[0];
      const monthNum = parts[1];
      const key = MONTH_KEY_MAP[monthNum];
      // Fall back to raw string if somehow unrecognised
      const abbr = key ? t(`months.${key}`) : monthNum;
      return `${abbr} ${year}`;
    };

    const getFulfillmentClass = (rate) => {
      if (rate >= 90) return "badge success";
      if (rate >= 75) return "badge warning";
      return "badge danger";
    };

    const getChangeClass = (current, previous) => {
      const change = current - previous;
      if (change > 0) return "positive-change";
      if (change < 0) return "negative-change";
      return "";
    };

    // Returns a signed, currency-formatted change string, e.g. "+$1,234" / "-¥185,050"
    const getChangeValue = (current, previous) => {
      const change = current - previous;
      if (change > 0)
        return "+" + formatCurrency(change, currentCurrency.value);
      if (change < 0)
        return "-" + formatCurrency(Math.abs(change), currentCurrency.value);
      return formatCurrency(0, currentCurrency.value);
    };

    const getGrowthRate = (current, previous) => {
      if (previous === 0) return "N/A";
      const rate = ((current - previous) / previous) * 100;
      const sign = rate > 0 ? "+" : "";
      return sign + rate.toFixed(1) + "%";
    };

    return {
      t,
      currentCurrency,
      loading,
      error,
      quarterlyData,
      monthlyData,
      totalRevenue,
      avgMonthlyRevenue,
      totalOrders,
      bestQuarter,
      formatCurrency,
      getBarHeight,
      formatMonth,
      getFulfillmentClass,
      getChangeClass,
      getChangeValue,
      getGrowthRate,
    };
  },
};
</script>

<style scoped>
.reports {
  padding: 0;
}

.card {
  background: var(--bg-surface);
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.card-header {
  margin-bottom: 1.5rem;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.reports-table {
  width: 100%;
  border-collapse: collapse;
}

.reports-table th {
  background: var(--bg-subtle);
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 2px solid var(--border);
}

.reports-table td {
  padding: 0.75rem;
  border-bottom: 1px solid var(--border);
}

.reports-table tr:hover {
  background: var(--bg-subtle);
}

.chart-container {
  padding: 2rem 1rem;
  min-height: 300px;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 250px;
  gap: 0.5rem;
}

.bar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  max-width: 80px;
}

.bar-container {
  height: 200px;
  display: flex;
  align-items: flex-end;
  width: 100%;
}

.bar {
  width: 100%;
  background: linear-gradient(to top, var(--lfc-red), var(--lfc-red-light));
  border-radius: 4px 4px 0 0;
  transition: all 0.3s;
  cursor: pointer;
}

.bar:hover {
  background: linear-gradient(to top, var(--lfc-red-dark), var(--lfc-red));
}

.bar-label {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-align: center;
  transform: rotate(-45deg);
  white-space: nowrap;
  margin-top: 1.5rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-top: 1.5rem;
}

.stat-card {
  background: var(--bg-surface);
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border-left: 4px solid var(--accent);
}

.stat-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.875rem;
  font-weight: 700;
  color: var(--text-primary);
}

.badge {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
}

.badge.success {
  background: var(--success-bg);
  color: var(--success);
}

.badge.warning {
  background: var(--warning-bg);
  color: var(--warning);
}

.badge.danger {
  background: var(--danger-bg);
  color: var(--danger);
}

.positive-change {
  color: var(--success);
  font-weight: 600;
}

.negative-change {
  color: var(--danger);
  font-weight: 600;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: var(--text-secondary);
}

.error {
  background: var(--danger-bg);
  color: var(--danger);
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
}
</style>
