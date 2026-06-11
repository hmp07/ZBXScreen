<template>
  <div class="page">
    <div class="page-header"><h2>Webhook 配置</h2><el-button type="primary" @click="openDialog()">添加端点</el-button></div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column prop="url" label="URL" min-width="250" show-overflow-tooltip />
      <el-table-column prop="method" label="方法" width="70" />
      <el-table-column prop="enabled" label="状态" width="80">
        <template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '启用' : '禁用' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="testWebhook(row.id)">测试</el-button>
          <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
          <el-button link size="small" @click="toggleWebhook(row)">{{ row.enabled ? '禁用' : '启用' }}</el-button>
          <el-popconfirm title="确定删除？" @confirm="delWebhook(row.id)"><template #reference><el-button link type="danger" size="small">删除</el-button></template></el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="dlg" :title="editId ? '编辑' : '添加'" width="520px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="URL"><el-input v-model="form.url" /></el-form-item>
        <el-form-item label="方法"><el-select v-model="form.method"><el-option value="POST" /><el-option value="PUT" /></el-select></el-form-item>
        <el-form-item label="Headers JSON"><el-input v-model="form.headers_json" type="textarea" :rows="3" placeholder='{"Authorization":"Bearer xxx"}' /></el-form-item>
        <el-form-item label="触发级别"><el-select v-model="form.trigger_levels" multiple placeholder="空=全部"><el-option v-for="l in ['INFO','WARNING','AVERAGE','HIGH','DISASTER']" :key="l" :value="l" /></el-select></el-form-item>
        <el-form-item label="重试次数"><el-input-number v-model="form.retry_count" :min="0" :max="10" /></el-form-item>
        <el-form-item label="超时(秒)"><el-input-number v-model="form.timeout" :min="1" :max="60" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dlg = false">取消</el-button><el-button type="primary" @click="save">确定</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { getWebhooks, createWebhook, updateWebhook, deleteWebhook, toggleWebhook as toggleWebhookApi, testWebhook as testWebhookApi } from "@/api/webhook";
const list = ref<any[]>([]); const loading = ref(false); const dlg = ref(false); const editId = ref<number | null>(null);
const form = reactive({ name: "", url: "", method: "POST", headers_json: "", trigger_levels: "" as any, retry_count: 3, timeout: 10 });
onMounted(fetch);
async function fetch() { loading.value = true; try { list.value = (await getWebhooks()).data.data; } finally { loading.value = false; } }
function openDialog(row?: any) { editId.value = row?.id || null; Object.assign(form, row ? { ...row, headers_json: row.headers_json || "", trigger_levels: row.trigger_levels?.split(",") || [] } : { name: "", url: "", method: "POST", headers_json: "", trigger_levels: [], retry_count: 3, timeout: 10 }); dlg.value = true; }
async function save() {
  const data = { ...form, trigger_levels: Array.isArray(form.trigger_levels) ? form.trigger_levels.join(",") : "" };
  if (editId.value) await updateWebhook(editId.value, data); else await createWebhook(data);
  dlg.value = false; fetch();
}
async function delWebhook(id: number) { await deleteWebhook(id); fetch(); }
async function toggleWebhook(r: any) { await toggleWebhookApi(r.id); fetch(); }
async function testWebhook(id: number) { const r: any = await testWebhookApi(id); ElMessage[r.data.data.success ? 'success' : 'error'](r.data.message); }
</script>
<style scoped>.page { padding: 0; } .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; } .page-header h2 { font-size: 18px; color: var(--text-primary); margin: 0; }</style>
