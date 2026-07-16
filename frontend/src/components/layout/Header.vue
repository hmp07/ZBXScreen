<template>
  <div class="header">
    <div class="header-left">
      <el-dropdown trigger="click" @command="handleToolCommand">
        <el-button text class="tools-btn">
          运维工具 <span style="font-size:10px;margin-left:2px">▼</span>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="zabbix">打开 Zabbix</el-dropdown-item>
            <el-dropdown-item command="itop">打开 iTop</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
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

function handleToolCommand(cmd: string) {
  if (cmd === "zabbix") {
    window.open("/integrations/zabbix/login", "_blank");
  } else if (cmd === "itop") {
    window.open("/integrations/itop/login", "_blank");
  }
}

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

.header-left {
  flex: 1;
}

.tools-btn {
  color: var(--primary);
  font-size: 13px;
  letter-spacing: 1px;
}
.tools-btn:hover { color: #7be8ff; }

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
