<template>
  <div
    class="sidebar"
    :class="{ collapsed: layoutStore.sidebarEffective }"
    @mouseenter="layoutStore.sidebarHovered = true"
    @mouseleave="layoutStore.sidebarHovered = false"
  >
    <div class="logo">
      <img v-if="layoutStore.brandLogo" :src="layoutStore.brandLogo" class="logo-img" />
      <span v-else-if="layoutStore.sidebarEffective" class="logo-icon">{{ layoutStore.brandTitle?.charAt(0) || 'Z' }}</span>
      <span v-if="!layoutStore.sidebarEffective" class="logo-text">{{ layoutStore.brandTitle || 'ZBXScreen' }}</span>
    </div>

    <el-menu
      :default-active="activeMenu"
      :collapse="layoutStore.sidebarEffective"
      router
      background-color="transparent"
      text-color="#90a4ae"
      active-text-color="#00d4ff"
      :collapse-transition="false"
    >
      <el-menu-item index="/dashboard">
        <el-icon><DataAnalysis /></el-icon>
        <template #title>数据中心大屏</template>
      </el-menu-item>
      <el-menu-item index="/network">
        <el-icon><Connection /></el-icon>
        <template #title>网络监控大屏</template>
      </el-menu-item>
      <el-menu-item index="/hosts">
        <el-icon><Monitor /></el-icon>
        <template #title>主机管理</template>
      </el-menu-item>
      <el-menu-item index="/datasources">
        <el-icon><Coin /></el-icon>
        <template #title>数据源</template>
      </el-menu-item>
      <el-sub-menu index="alerts">
        <template #title>
          <el-icon><Bell /></el-icon>
          <span>告警管理</span>
        </template>
        <el-menu-item index="/alerts/dashboard">告警大屏</el-menu-item>
        <el-menu-item index="/alerts/rules">告警规则</el-menu-item>
        <el-menu-item index="/alerts/records">告警记录</el-menu-item>
      </el-sub-menu>
      <el-menu-item index="/webhooks">
        <el-icon><Connection /></el-icon>
        <template #title>Webhook</template>
      </el-menu-item>
      <el-menu-item index="/settings">
        <el-icon><Setting /></el-icon>
        <template #title>系统设置</template>
      </el-menu-item>
    </el-menu>

    <!-- 用户信息区 -->
    <div class="sidebar-user">
      <div class="user-avatar">{{ (authStore.username || 'A')[0].toUpperCase() }}</div>
      <div class="user-detail" v-if="!layoutStore.sidebarEffective">
        <span class="user-name">{{ authStore.username }}</span>
        <span class="user-logout" @click="handleLogout">退出</span>
      </div>
    </div>

    <!-- 收起/展开按钮 -->
    <el-tooltip :content="layoutStore.sidebarEffective ? '展开侧边栏' : '隐藏侧边栏'" placement="right">
      <div class="sidebar-toggle" @click="layoutStore.toggleSidebar()">
        <span class="toggle-icon">{{ layoutStore.sidebarEffective ? '>>' : '<<' }}</span>
      </div>
    </el-tooltip>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useLayoutStore } from "@/stores/layout";
import { useAuthStore } from "@/stores/auth";
import axios from "axios";

const route = useRoute();
const router = useRouter();
const layoutStore = useLayoutStore();
const authStore = useAuthStore();

// 首次加载时从 API 获取品牌设置，后续由 Settings 页面通过 store 更新
onMounted(async () => {
  try {
    const res = await axios.get("/api/v1/settings/public");
    if (res.data?.code === 0) {
      const d = res.data.data;
      layoutStore.setBrand(d.title || "", d.logo || "");
    }
  } catch { /* use defaults */ }
});

const activeMenu = computed(() => {
  const path = route.path;
  if (path.startsWith("/network")) return "/network";
  if (path.startsWith("/alerts/dashboard")) return "/alerts/dashboard";
  if (path.startsWith("/alerts/rules")) return "/alerts/rules";
  if (path.startsWith("/alerts/records")) return "/alerts/records";
  if (path.startsWith("/alerts/")) return "/alerts/records";
  if (path.match(/^\/hosts\/\d+$/)) return "/hosts";
  return path;
});

function handleLogout() {
  authStore.logout();
  router.push("/login");
}
</script>

<style scoped>
.sidebar {
  width: 220px;
  min-width: 220px;
  background: rgba(13, 27, 46, 0.95);
  border-right: 1px solid rgba(0, 212, 255, 0.12);
  display: flex;
  flex-direction: column;
  transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1), min-width 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  position: relative;
  z-index: 100;
}
.sidebar.collapsed {
  width: 64px;
  min-width: 64px;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
  flex-shrink: 0;
}
.logo-text {
  font-size: 18px;
  font-weight: bold;
  color: var(--color-accent);
  letter-spacing: 2px;
  white-space: nowrap;
}
.logo-icon {
  font-size: 22px;
  font-weight: 900;
  color: var(--color-accent);
  font-family: var(--font-num);
}
.logo-img {
  max-height: 40px;
  max-width: 100%;
}

.el-menu {
  border-right: none !important;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

/* 用户信息 */
.sidebar-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-top: 1px solid rgba(0, 212, 255, 0.08);
  flex-shrink: 0;
}
.sidebar.collapsed .sidebar-user {
  justify-content: center;
  padding: 10px 0;
}
.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  color: #001a2b;
  flex-shrink: 0;
}
.user-detail {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.user-name {
  font-size: 13px;
  color: var(--text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.user-logout {
  font-size: 11px;
  color: var(--text-3);
  cursor: pointer;
  transition: color 0.2s;
}
.user-logout:hover {
  color: var(--danger);
}

/* 收起/展开按钮 */
.sidebar-toggle {
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-top: 1px solid rgba(0, 212, 255, 0.1);
  cursor: pointer;
  color: var(--text-3);
  flex-shrink: 0;
  transition: background 0.2s, color 0.2s;
}
.sidebar-toggle:hover {
  background: rgba(0, 212, 255, 0.08);
  color: var(--primary);
}
.toggle-icon {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -2px;
  font-family: var(--font-num);
  transition: transform 0.25s;
}
</style>
