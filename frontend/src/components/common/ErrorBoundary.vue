<template>
  <div class="error-boundary">
    <p>数据加载失败</p>
    <el-button size="small" @click="$emit('retry')">点击重试</el-button>
  </div>
</template>

<script setup lang="ts">
defineEmits<{ retry: [] }>();
</script>

<style scoped>
.error-boundary {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 40px 20px; color: var(--text-secondary);
}
.error-boundary p { margin-bottom: 12px; }
</style>
