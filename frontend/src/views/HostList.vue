<template>
  <div class="host-list-page">
    <div class="page-header">
      <h2>主机管理</h2>
      <div class="header-controls">
        <el-input v-model="searchText" placeholder="搜索主机名" clearable @input="onSearch" style="width:220px" />
      </div>
    </div>

    <el-table :data="hosts" v-loading="loading" stripe @row-click="goDetail" style="cursor:pointer" max-height="calc(100vh - 200px)">
      <el-table-column prop="host" label="主机名" min-width="140" />
      <el-table-column prop="name" label="可见名称" min-width="160" />
      <el-table-column label="IP" width="140">
        <template #default="{ row }">{{ row.interfaces?.[0]?.ip || '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.zbx_status === '1'" type="info" size="small">停用</el-tag>
          <el-tag v-else-if="row.online_status === 'online'" type="success" size="small">在线</el-tag>
          <el-tag v-else type="danger" size="small">离线</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="数据源" width="100">
        <template #default="{ row }">{{ row._datasource_name || '-' }}</template>
      </el-table-column>
      <el-table-column label="主机组" min-width="200">
        <template #default="{ row }">
          <el-tag v-for="g in (row.groups || []).slice(0,3)" :key="g.groupid" size="small" style="margin-right:4px">
            {{ g.name }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80" fixed="right">
        <template #default>
          <el-button link type="primary" size="small">大屏查看</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap" v-if="total > 0">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :page-sizes="[30, 40, 50, 60, 70, 80, 90, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="fetchHosts"
        @size-change="onPageSizeChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { getHostList } from "@/api/host";

const router = useRouter();
const searchText = ref("");
const hosts = ref<any[]>([]);
const loading = ref(false);
const page = ref(1);
const pageSize = ref(30);
const total = ref(0);
let searchTimeout: ReturnType<typeof setTimeout>;

onMounted(() => fetchHosts());

function onPageSizeChange(size: number) {
  pageSize.value = size;
  page.value = 1;
  fetchHosts();
}

async function fetchHosts() {
  loading.value = true;
  try {
    const res = await getHostList({
      search: searchText.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    });
    const d = res.data.data;
    hosts.value = d.items;
    total.value = d.total;
  } finally {
    loading.value = false;
  }
}

function onSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    page.value = 1;
    fetchHosts();
  }, 300);
}

function goDetail(row: any) {
  const dsId = row._datasource_id || 1;
  router.push(`/hosts/${row.hostid}?datasource_id=${dsId}`);
}
</script>

<style scoped>
.host-list-page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { font-size: 18px; color: var(--text-primary); margin: 0; }
.header-controls { display: flex; gap: 8px; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: center; }
</style>
