import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import AppLayout from "@/components/layout/AppLayout.vue";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/Login.vue"),
    meta: { requiresAuth: false },
  },
  {
    path: "/",
    component: AppLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: "",
        redirect: "/dashboard",
      },
      {
        path: "dashboard",
        name: "Dashboard",
        component: () => import("@/views/Dashboard.vue"),
      },
      {
        path: "network",
        name: "NetworkDashboard",
        component: () => import("@/views/NetworkDashboard.vue"),
      },
      {
        path: "hosts",
        name: "HostList",
        component: () => import("@/views/HostList.vue"),
      },
      {
        path: "hosts/:hostid",
        name: "HostDetail",
        component: () => import("@/views/HostDetail.vue"),
      },
      {
        path: "datasources",
        name: "DatasourceList",
        component: () => import("@/views/DatasourceList.vue"),
      },
      {
        path: "alerts/rules",
        name: "AlertRules",
        component: () => import("@/views/AlertRules.vue"),
      },
      {
        path: "alerts/records",
        name: "AlertRecords",
        component: () => import("@/views/AlertRecords.vue"),
      },
      {
        path: "alerts/dashboard",
        name: "AlertDashboard",
        component: () => import("@/views/AlertDashboard.vue"),
      },
      {
        path: "alerts/:id",
        name: "AlertDetail",
        component: () => import("@/views/AlertDetail.vue"),
      },
      {
        path: "webhooks",
        name: "WebhookConfig",
        component: () => import("@/views/WebhookConfig.vue"),
      },
      {
        path: "settings",
        name: "Settings",
        component: () => import("@/views/Settings.vue"),
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore();

  if (to.meta.requiresAuth !== false && !authStore.isAuthenticated) {
    authStore.restoreSession();
    if (!authStore.isAuthenticated) {
      next({ name: "Login", query: { redirect: to.fullPath } });
      return;
    }
  }

  if (to.name === "Login" && authStore.isAuthenticated) {
    next({ name: "Dashboard" });
    return;
  }

  next();
});

export default router;
