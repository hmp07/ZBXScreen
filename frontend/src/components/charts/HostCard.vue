<template>
  <div class="host-card">
    <div class="card-header">
      <span class="host-name">{{ host.host || host.name }}</span>
      <span class="status-dot" :class="host.status === '0' ? 'online' : 'offline'"></span>
    </div>
    <div class="card-body">
      <div class="info-row">
        <span class="label">主机名</span>
        <span class="value">{{ host.name }}</span>
      </div>
      <div class="info-row" v-if="host.interfaces?.[0]">
        <span class="label">IP</span>
        <span class="value">{{ host.interfaces[0].ip }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ host: any }>();
</script>

<style scoped>
.host-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 12px;
  transition: border-color 0.2s;
}
.host-card:hover { border-color: var(--color-accent); }
.card-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid var(--border-color);
}
.host-name { font-size: 14px; font-weight: 500; color: var(--text-primary); }
.status-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.status-dot.online { background: var(--color-success); box-shadow: 0 0 6px var(--color-success); }
.status-dot.offline { background: var(--color-danger); }
.card-body { display: flex; flex-direction: column; gap: 6px; }
.info-row { display: flex; justify-content: space-between; font-size: 12px; }
.label { color: var(--text-secondary); }
.value { color: var(--text-primary); }
</style>
