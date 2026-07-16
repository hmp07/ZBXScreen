<template>
  <div class="page">
    <div class="page-header"><h2>系统设置</h2></div>
    <el-form :model="form" label-width="140px" style="max-width:600px" v-loading="loading">
      <el-form-item label="系统标题">
        <el-input v-model="form.system_title" placeholder="如：ZBXScreen" />
      </el-form-item>
      <el-form-item label="副标题">
        <el-input v-model="form.system_subtitle" placeholder="如：ZABBIX · VISUALIZATION（留空则不显示）" />
      </el-form-item>
      <el-form-item label="系统 Logo">
        <div style="display:flex;align-items:center;gap:12px">
          <div v-if="form.system_logo" class="logo-preview">
            <img :src="form.system_logo" />
            <el-button size="small" type="danger" @click="clearLogo" style="position:absolute;top:-6px;right:-6px" circle>✕</el-button>
          </div>
          <div v-else class="logo-preview logo-letter">{{ form.system_title?.charAt(0) || 'Z' }}</div>
          <el-button size="small" @click="triggerUpload">上传图标</el-button>
          <input ref="fileInput" type="file" accept="image/*" style="display:none" @change="onFileChange" />
          <span style="font-size:11px;color:var(--text-3)">推荐 128×128 PNG</span>
        </div>
      </el-form-item>
      <el-form-item label="默认刷新频率(秒)">
        <el-input-number v-model="form.default_refresh_interval" :min="5" :max="600" />
      </el-form-item>
      <el-form-item label="数据保留天数">
        <el-input-number v-model="form.data_retention_days" :min="1" :max="365" />
      </el-form-item>
      <el-form-item label="主题">
        <el-select v-model="form.theme"><el-option value="dark" label="深色" /><el-option value="light" label="浅色" /></el-select>
      </el-form-item>
      <el-form-item label="时区">
        <el-select v-model="form.tz"><el-option value="Asia/Shanghai" label="Asia/Shanghai" /><el-option value="UTC" label="UTC" /></el-select>
      </el-form-item>

      <el-divider content-position="left">运维集成</el-divider>
      <el-form-item label="Zabbix 前端地址">
        <el-input v-model="form.zabbix_frontend_url" placeholder="如：http://zabbix.example.com" />
      </el-form-item>
      <el-form-item label="iTop 地址">
        <el-input v-model="form.itop_url" placeholder="如：http://itop.example.com" />
      </el-form-item>
      <el-form-item label="iTop 工单模板">
        <el-input v-model="form.itop_incident_template" type="textarea" :rows="2"
          placeholder="{itop_url}/pages/exec.php/exec?exec_module=itop-incident-create&default_values[attr_title]={trigger_name}" />
        <div style="font-size:11px;color:var(--text-3);margin-top:4px">
          可用变量：<code>{itop_url}</code> <code>{host_name}</code> <code>{host_id}</code> <code>{trigger_name}</code>
        </div>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="saveSettings">保存设置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { getSettings, updateSettings } from "@/api/settings";
import { useLayoutStore } from "@/stores/layout";

const layoutStore = useLayoutStore();
const loading = ref(false);
const fileInput = ref<HTMLInputElement>();
const form = reactive({
  system_title: "ZBXScreen",
  system_subtitle: "",
  system_logo: "",
  default_refresh_interval: 30,
  data_retention_days: 30,
  theme: "dark",
  tz: "Asia/Shanghai",
  zabbix_frontend_url: "",
  itop_url: "",
  itop_incident_template: "",
});

onMounted(async () => {
  loading.value = true;
  try {
    const r = await getSettings();
    const d = r.data.data;
    if (d.SYSTEM_TITLE) form.system_title = d.SYSTEM_TITLE;
    if (d.SYSTEM_SUBTITLE) form.system_subtitle = d.SYSTEM_SUBTITLE;
    if (d.SYSTEM_LOGO) form.system_logo = d.SYSTEM_LOGO;
    if (d.DEFAULT_REFRESH_INTERVAL) form.default_refresh_interval = parseInt(d.DEFAULT_REFRESH_INTERVAL);
    if (d.DATA_RETENTION_DAYS) form.data_retention_days = parseInt(d.DATA_RETENTION_DAYS);
    if (d.THEME) form.theme = d.THEME;
    if (d.TZ) form.tz = d.TZ;
    if (d.ZABBIX_FRONTEND_URL) form.zabbix_frontend_url = d.ZABBIX_FRONTEND_URL;
    if (d.ITOP_URL) form.itop_url = d.ITOP_URL;
    if (d.ITOP_INCIDENT_TEMPLATE) form.itop_incident_template = d.ITOP_INCIDENT_TEMPLATE;
  } finally {
    loading.value = false;
  }
});

function triggerUpload() {
  fileInput.value?.click();
}

function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;
  if (file.size > 512 * 1024) {
    ElMessage.error("Logo 文件不能超过 512KB");
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    form.system_logo = reader.result as string;
  };
  reader.readAsDataURL(file);
}

function clearLogo() {
  form.system_logo = "";
}

async function saveSettings() {
  await updateSettings({ ...form });
  // 同步更新侧边栏品牌显示
  layoutStore.setBrand(form.system_title, form.system_logo);
  ElMessage.success("设置已保存");
}
</script>

<style scoped>
.page { padding: 0; }
.page-header { margin-bottom: 20px; }
.page-header h2 { font-size: 18px; color: var(--text-primary); margin: 0; }
.logo-preview {
  width: 56px; height: 56px; border-radius: 10px; position: relative;
  border: 1px solid var(--panel-border); background: rgba(0,229,255,0.06);
  display: flex; align-items: center; justify-content: center;
}
.logo-preview img {
  width: 100%; height: 100%; object-fit: contain; border-radius: 10px;
}
.logo-letter {
  font-family: var(--font-num); font-weight: 900; font-size: 24px;
  color: var(--primary); text-shadow: 0 0 10px var(--primary-glow);
}
</style>
