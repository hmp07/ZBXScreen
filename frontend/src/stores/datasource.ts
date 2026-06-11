import { defineStore } from "pinia";
import { ref } from "vue";
import {
  getDatasources,
  createDatasource,
  updateDatasource,
  deleteDatasource,
  testConnection,
  toggleDatasource,
  type Datasource,
} from "@/api/datasource";
import { ElMessage } from "element-plus";

export const useDatasourceStore = defineStore("datasource", () => {
  const list = ref<Datasource[]>([]);
  const loading = ref(false);

  async function fetchList() {
    loading.value = true;
    try {
      const res = await getDatasources();
      list.value = res.data.data;
    } finally {
      loading.value = false;
    }
  }

  async function create(data: { name: string; url: string; username: string; password: string }) {
    await createDatasource(data);
    ElMessage.success("数据源添加成功");
    await fetchList();
  }

  async function update(
    id: number,
    data: { name?: string; url?: string; username?: string; password?: string }
  ) {
    await updateDatasource(id, data);
    ElMessage.success("数据源修改成功");
    await fetchList();
  }

  async function remove(id: number) {
    await deleteDatasource(id);
    ElMessage.success("数据源已删除");
    await fetchList();
  }

  async function test(id: number): Promise<{ connected: boolean; version?: string; error?: string }> {
    const res = await testConnection(id);
    return res.data.data;
  }

  async function toggle(id: number) {
    const res = await toggleDatasource(id);
    ElMessage.success(res.data.message);
    await fetchList();
  }

  return {
    list,
    loading,
    fetchList,
    create,
    update,
    remove,
    test,
    toggle,
  };
});
