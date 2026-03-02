<template>
  <div class="app">
    <header class="top-nav">
      <div class="nav-container">
        <div class="logo">
          <h1>{{ t("nav.companyName") }}</h1>
          <span class="subtitle">{{ t("nav.subtitle") }}</span>
        </div>
        <nav class="nav-tabs">
          <router-link to="/" :class="{ active: $route.path === '/' }">
            {{ t("nav.overview") }}
          </router-link>
          <router-link
            to="/inventory"
            :class="{ active: $route.path === '/inventory' }"
          >
            {{ t("nav.inventory") }}
          </router-link>
          <router-link
            to="/orders"
            :class="{ active: $route.path === '/orders' }"
          >
            {{ t("nav.orders") }}
          </router-link>
          <router-link
            to="/spending"
            :class="{ active: $route.path === '/spending' }"
          >
            {{ t("nav.finance") }}
          </router-link>
          <router-link
            to="/demand"
            :class="{ active: $route.path === '/demand' }"
          >
            {{ t("nav.demandForecast") }}
          </router-link>
          <router-link
            to="/restocking"
            :class="{ active: $route.path === '/restocking' }"
          >
            {{ t("nav.restocking") }}
          </router-link>
          <router-link
            to="/reports"
            :class="{ active: $route.path === '/reports' }"
          >
            {{ t("nav.reports") }}
          </router-link>
        </nav>
        <LanguageSwitcher />
        <ProfileMenu
          @show-profile-details="showProfileDetails = true"
          @show-tasks="showTasks = true"
        />
      </div>
    </header>
    <FilterBar />
    <main class="main-content">
      <router-view />
    </main>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, computed } from "vue";
import { api } from "./api";
import { useAuth } from "./composables/useAuth";
import { useI18n } from "./composables/useI18n";
import FilterBar from "./components/FilterBar.vue";
import ProfileMenu from "./components/ProfileMenu.vue";
import ProfileDetailsModal from "./components/ProfileDetailsModal.vue";
import TasksModal from "./components/TasksModal.vue";
import LanguageSwitcher from "./components/LanguageSwitcher.vue";

export default {
  name: "App",
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher,
  },
  setup() {
    const { currentUser } = useAuth();
    const { t } = useI18n();
    const showProfileDetails = ref(false);
    const showTasks = ref(false);
    const apiTasks = ref([]);

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value];
    });

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks();
      } catch (err) {
        console.error("Failed to load tasks:", err);
      }
    };

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData);
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask);
      } catch (err) {
        console.error("Failed to add task:", err);
      }
    };

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some((t) => t.id === taskId);

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(
            (t) => t.id === taskId,
          );
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1);
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId);
          apiTasks.value = apiTasks.value.filter((t) => t.id !== taskId);
        }
      } catch (err) {
        console.error("Failed to delete task:", err);
      }
    };

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find((t) => t.id === taskId);

        if (mockTask) {
          // Toggle mock task status
          mockTask.status =
            mockTask.status === "pending" ? "completed" : "pending";
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId);
          const index = apiTasks.value.findIndex((t) => t.id === taskId);
          if (index !== -1) {
            apiTasks.value[index] = updatedTask;
          }
        }
      } catch (err) {
        console.error("Failed to toggle task:", err);
      }
    };

    onMounted(loadTasks);

    return {
      t,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask,
    };
  },
};
</script>

<style>
:root {
  /* LFC Brand */
  --lfc-red: #c8102e;
  --lfc-red-dark: #97001e;
  --lfc-red-light: #e8304a;
  --lfc-gold: #f6eb61;
  --lfc-gold-dark: #d4c837;

  /* Neutrals — warm instead of cool slate */
  --bg-page: #faf7f2;
  --bg-surface: #ffffff;
  --bg-hover: #f5efe8;
  --bg-subtle: #f9f5f0;
  --border: #e8ddd4;
  --border-hover: #d9cbc0;

  /* Text */
  --text-primary: #1a1a1a;
  --text-secondary: #6b5b5b;
  --text-muted: #8a7a7a;

  /* Primary accent (replaces blue) */
  --accent: var(--lfc-red);
  --accent-bg: #fdf2f4;
  --accent-dark: var(--lfc-red-dark);

  /* Status — semantic, tuned to warm palette */
  --success: #0a7d3e;
  --success-bg: #d4edda;
  --warning: #8b6f00;
  --warning-bg: #fff8d6;
  --danger: #b00020;
  --danger-bg: #fde6ea;
  --info: var(--lfc-red-dark);
  --info-bg: #fde6ea;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family:
    "Inter",
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    Roboto,
    Oxygen,
    Ubuntu,
    Cantarell,
    sans-serif;
  background: var(--bg-page);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.top-nav {
  /* LFC red navbar — brand identity */
  background: var(--lfc-red);
  border-bottom: 1px solid var(--lfc-red-dark);
  box-shadow: 0 2px 8px rgba(200, 16, 46, 0.3);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-container {
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  padding: 0 2rem;
  height: 70px;
}

.nav-container > .nav-tabs {
  margin-left: auto;
  margin-right: 1rem;
}

.nav-container > .language-switcher {
  margin-right: 1rem;
}

.logo {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
}

.logo h1 {
  /* Oswald mimics LFC stadium/badge typography */
  font-family: "Oswald", sans-serif;
  font-size: 1.375rem;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.subtitle {
  font-size: 0.813rem;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 400;
  padding-left: 0.75rem;
  border-left: 1px solid rgba(255, 255, 255, 0.3);
}

.nav-tabs {
  display: flex;
  gap: 0.25rem;
}

.nav-tabs a {
  padding: 0.625rem 1.25rem;
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.938rem;
  border-radius: 6px;
  transition: all 0.2s ease;
  position: relative;
}

.nav-tabs a:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.15);
}

.nav-tabs a.active {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.2);
}

/* Gold underline on active nav tab — LFC accent color */
.nav-tabs a.active::after {
  content: "";
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--lfc-gold);
}

.main-content {
  flex: 1;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
  padding: 1.5rem 2rem;
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-header h2 {
  font-family: "Oswald", sans-serif;
  font-size: 1.875rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.375rem;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.page-header p {
  color: var(--text-secondary);
  font-size: 0.938rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: var(--bg-surface);
  padding: 1.25rem;
  border-radius: 10px;
  border: 1px solid var(--border);
  transition: all 0.2s ease;
}

.stat-card:hover {
  border-color: var(--border-hover);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.stat-label {
  font-family: "Oswald", sans-serif;
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.625rem;
}

.stat-value {
  font-family: "Oswald", sans-serif;
  font-size: 2.25rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.stat-card.warning .stat-value {
  color: var(--warning);
}

.stat-card.success .stat-value {
  color: var(--success);
}

.stat-card.danger .stat-value {
  color: var(--danger);
}

.stat-card.info .stat-value {
  color: var(--accent);
}

.card {
  background: var(--bg-surface);
  border-radius: 10px;
  padding: 1.25rem;
  border: 1px solid var(--border);
  margin-bottom: 1.25rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.875rem;
  border-bottom: 1px solid var(--border);
}

.card-title {
  font-family: "Oswald", sans-serif;
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--bg-subtle);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}

th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

td {
  padding: 0.5rem 0.75rem;
  border-top: 1px solid var(--bg-hover);
  color: var(--text-primary);
  font-size: 0.875rem;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: var(--bg-subtle);
}

.badge {
  display: inline-block;
  padding: 0.313rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
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

.badge.info {
  background: var(--info-bg);
  color: var(--info);
}

.badge.increasing {
  background: var(--success-bg);
  color: var(--success);
}

.badge.decreasing {
  background: var(--danger-bg);
  color: var(--danger);
}

.badge.stable {
  background: var(--info-bg);
  color: var(--info);
}

.badge.high {
  background: var(--danger-bg);
  color: var(--danger);
}

.badge.medium {
  background: var(--warning-bg);
  color: var(--warning);
}

.badge.low {
  background: var(--info-bg);
  color: var(--info);
}

.loading {
  text-align: center;
  padding: 3rem;
  color: var(--text-secondary);
  font-size: 0.938rem;
}

.error {
  background: var(--danger-bg);
  border: 1px solid var(--danger-bg);
  color: var(--danger);
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  font-size: 0.938rem;
}
</style>
