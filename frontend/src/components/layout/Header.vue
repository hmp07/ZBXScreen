<template>
  <div class="header">
    <div class="header-spacer"></div>
    <div class="header-right">
      <span class="user-info">{{ authStore.username }}</span>
      <el-button text @click="handleLogout" style="color: var(--text-secondary)">
        退出
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const authStore = useAuthStore();

function handleLogout() {
  authStore.logout();
  router.push("/login");
}
</script>

<style scoped>
.header {
  height: 48px;
  min-height: 48px;
  background: rgba(13, 27, 46, 0.95);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-spacer {
  flex: 1;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-info {
  font-size: 13px;
  color: var(--color-accent);
}
</style>
