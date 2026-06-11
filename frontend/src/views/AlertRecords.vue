<template>
  <div class="page">
    <div class="page-header"><h2>告警记录</h2></div>
    <div class="filters">
      <el-select v-model="filterLevel" placeholder="级别" clearable @change="fetchRecords" style="width:120px">
        <el-option v-for="l in ['INFO','WARNING','AVERAGE','HIGH','DISASTER']" :key="l" :value="l" :label="l" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="状态" clearable @change="fetchRecords" style="width:120px">
        <el-option value="active" label="活跃" /><el-option value="recovered" label="已恢复" />
      </el-select>
    </div>
    <el-table :data="records" v-loading="loading" stripe @row-click="goDetail" style="cursor:pointer">
      <el-table-column prop="host_name" label="主机" min-width="120" />
      <el-table-column prop="trigger_name" label="告警内容" min-width="200" show-overflow-tooltip />
      <el-table-column prop="level" label="级别" width="90">
        <template #default="{ row }"><el-tag :type="levelTag(row.level)" size="small">{{ row.level }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'danger' : 'success'" size="small">{{ row.status === 'active' ? '活跃' : '已恢复' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="value" label="值" width="80" />
      <el-table-column label="时间" min-width="160">
        <template #default="{ row }">{{ row.first_occurred ? new Date(row.first_occurred).toLocaleString() : '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small">大屏查看</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pagination" v-if="total > pageSize">
      <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev,pager,next" @current-change="fetchRecords" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { getAlertRecords } from "@/api/alert";
const router = useRouter();
const records = ref<any[]>([]); const loading = ref(false);
const page = ref(1); const pageSize = ref(20); const total = ref(0);
const filterLevel = ref(""); const filterStatus = ref("");
function levelTag(l: string) { return { INFO: "info", WARNING: "warning", AVERAGE: "", HIGH: "danger", DISASTER: "danger" }[l] || "info"; }
onMounted(fetchRecords);
async function fetchRecords() {
  loading.value = true;
  try { const r = await getAlertRecords({ page: page.value, page_size: pageSize.value, level: filterLevel.value || undefined, status: filterStatus.value || undefined }); const d = r.data.data; records.value = d.items; total.value = d.total; } finally { loading.value = false; }
}
function goDetail(row: any) {
  router.push(`/alerts/${row.id}?datasource_id=1`);
}
</script>
<style scoped>.page { padding: 0; } .page-header { margin-bottom: 16px; } .page-header h2 { font-size: 18px; color: var(--text-primary); margin: 0; } .filters { display: flex; gap: 8px; margin-bottom: 12px; } .pagination { margin-top: 16px; display: flex; justify-content: center; }</style>
