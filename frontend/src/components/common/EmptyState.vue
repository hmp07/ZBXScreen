<template>
  <div class="empty-state">
    <el-icon class="empty-icon"><Warning /></el-icon>
    <p>{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{ message?: string }>();
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}
.empty-icon { font-size: 36px; margin-bottom: 12px; opacity: 0.5; }
.empty-state p { font-size: 14px; }
</style>
