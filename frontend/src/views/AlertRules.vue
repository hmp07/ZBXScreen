<template>
  <div class="page">
    <div class="page-header">
      <h2>告警规则</h2>
      <el-button type="primary" @click="openDialog()">添加规则</el-button>
    </div>
    <el-table :data="rules" v-loading="loading">
      <el-table-column prop="name" label="规则名称" min-width="150" />
      <el-table-column prop="rule_type" label="类型" width="130" />
      <el-table-column prop="level" label="级别" width="90">
        <template #default="{ row }"><el-tag :type="levelTag(row.level)" size="small">{{ row.level }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="enabled" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
          <el-button link type="primary" size="small" @click="toggleRule(row)">{{ row.enabled ? '禁用' : '启用' }}</el-button>
          <el-popconfirm title="确定删除？" @confirm="deleteRule(row.id)"><template #reference><el-button link type="danger" size="small">删除</el-button></template></el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="dlg" :title="editId ? '编辑规则' : '添加规则'" width="480px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型"><el-select v-model="form.rule_type" style="width:100%"><el-option value="zabbix_trigger" label="Zabbix 触发器" /><el-option value="custom_threshold" label="自定义阈值" /></el-select></el-form-item>
        <el-form-item label="级别"><el-select v-model="form.level" style="width:100%"><el-option v-for="l in ['INFO','WARNING','AVERAGE','HIGH','DISASTER']" :key="l" :value="l" :label="l" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="dlg = false">取消</el-button><el-button type="primary" @click="saveRule">确定</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { getAlertRules, createAlertRule, updateAlertRule, deleteAlertRule, toggleAlertRule } from "@/api/alert";

const rules = ref<any[]>([]);
const loading = ref(false);
const dlg = ref(false);
const editId = ref<number | null>(null);
const form = reactive({ name: "", rule_type: "zabbix_trigger", level: "WARNING" });

function levelTag(l: string) { return { INFO: "info", WARNING: "warning", AVERAGE: "", HIGH: "danger", DISASTER: "danger" }[l] || "info"; }

onMounted(fetchRules);
async function fetchRules() { loading.value = true; try { rules.value = (await getAlertRules()).data.data; } finally { loading.value = false; } }
function openDialog(row?: any) {
  editId.value = row?.id || null;
  form.name = row?.name || ""; form.rule_type = row?.rule_type || "zabbix_trigger"; form.level = row?.level || "WARNING";
  dlg.value = true;
}
async function saveRule() {
  if (editId.value) await updateAlertRule(editId.value, form);
  else await createAlertRule(form);
  dlg.value = false; fetchRules();
}
async function toggleRule(r: any) { await toggleAlertRule(r.id); fetchRules(); }
async function deleteRule(id: number) { await deleteAlertRule(id); fetchRules(); }
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { font-size: 18px; color: var(--text-primary); margin: 0; }
</style>
