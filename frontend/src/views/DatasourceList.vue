<template>
  <div class="datasource-page">
    <div class="page-header">
      <h2>数据源管理</h2>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>添加数据源
      </el-button>
    </div>

    <el-table :data="store.list" v-loading="store.loading" style="width: 100%">
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column prop="url" label="Zabbix URL" min-width="200" show-overflow-tooltip />
      <el-table-column prop="username" label="用户名" width="100" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
            {{ row.enabled ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Zabbix 版本" width="110">
        <template #default="{ row }">
          <span v-if="row.zabbix_version">{{ row.zabbix_version }}</span>
          <span v-else class="text-muted">未检测</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="testConnection(row)">
            测试
          </el-button>
          <el-button link type="primary" size="small" @click="openEditDialog(row)">
            编辑
          </el-button>
          <el-button link :type="row.enabled ? 'warning' : 'success'" size="small" @click="store.toggle(row.id)">
            {{ row.enabled ? '禁用' : '启用' }}
          </el-button>
          <el-popconfirm title="确定删除此数据源？" @confirm="store.remove(row.id)">
            <template #reference>
              <el-button link type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑数据源' : '添加数据源'"
      width="500px"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如：生产环境Zabbix" />
        </el-form-item>
        <el-form-item label="URL" prop="url">
          <el-input v-model="form.url" placeholder="http://zabbix.example.com" />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="Zabbix 登录用户名" />
        </el-form-item>
        <el-form-item label="密码" :prop="isEdit ? '' : 'password'">
          <el-input v-model="form.password" type="password" show-password
                    :placeholder="isEdit ? '留空则不修改' : 'Zabbix 登录密码'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { useDatasourceStore } from "@/stores/datasource";
import type { Datasource } from "@/api/datasource";

const store = useDatasourceStore();
const formRef = ref<FormInstance>();
const dialogVisible = ref(false);
const isEdit = ref(false);
const editId = ref<number | null>(null);
const submitting = ref(false);

const form = reactive({ name: "", url: "", username: "", password: "" });
const rules: FormRules = {
  name: [{ required: true, message: "请输入名称", trigger: "blur" }],
  url: [{ required: true, message: "请输入 Zabbix URL", trigger: "blur" }],
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

onMounted(() => store.fetchList());

function openCreateDialog() {
  isEdit.value = false;
  editId.value = null;
  form.name = ""; form.url = ""; form.username = ""; form.password = "";
  dialogVisible.value = true;
}

function openEditDialog(row: Datasource) {
  isEdit.value = true;
  editId.value = row.id;
  form.name = row.name; form.url = row.url; form.username = row.username;
  form.password = "";
  dialogVisible.value = true;
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  submitting.value = true;
  try {
    if (isEdit.value && editId.value) {
      const data: any = { name: form.name, url: form.url, username: form.username };
      if (form.password) data.password = form.password;
      await store.update(editId.value, data);
    } else {
      await store.create(form);
    }
    dialogVisible.value = false;
  } finally {
    submitting.value = false;
  }
}

async function testConnection(row: Datasource) {
  ElMessage.info("正在测试连接...");
  const result = await store.test(row.id);
  if (result.connected) {
    ElMessage.success(`连接成功！Zabbix 版本：${result.version}`);
  } else {
    ElMessage.error(`连接失败：${result.error}`);
  }
}
</script>

<style scoped>
.datasource-page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { font-size: 18px; color: var(--text-primary); margin: 0; }
.text-muted { color: var(--text-secondary); font-size: 12px; }
</style>
