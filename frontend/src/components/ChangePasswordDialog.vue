<template>
  <el-dialog
    v-model="visible"
    title="修改默认密码"
    width="440px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    class="pwd-dialog"
  >
    <div class="pwd-warning">
      <span class="warn-icon">⚠</span>
      <span>检测到您正在使用默认密码，为了系统安全，请立即修改密码。</span>
    </div>
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      @keyup.enter="handleSubmit"
    >
      <el-form-item label="当前密码" prop="oldPassword">
        <el-input
          v-model="form.oldPassword"
          type="password"
          show-password
          placeholder="请输入当前密码"
          size="large"
        />
      </el-form-item>
      <el-form-item label="新密码" prop="newPassword">
        <el-input
          v-model="form.newPassword"
          type="password"
          show-password
          placeholder="请输入新密码（至少6位）"
          size="large"
        />
      </el-form-item>
      <el-form-item label="确认新密码" prop="confirmPassword">
        <el-input
          v-model="form.confirmPassword"
          type="password"
          show-password
          placeholder="请再次输入新密码"
          size="large"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button size="large" @click="handleSkip" class="skip-btn">稍后修改</el-button>
        <el-button type="primary" size="large" @click="handleSubmit" :loading="loading" class="submit-btn">
          确认修改
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from "vue";
import { useAuthStore } from "@/stores/auth";
import { ElMessage } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";

const props = defineProps<{ modelValue: boolean }>();
const emit = defineEmits<{ (e: "update:modelValue", v: boolean): void; (e: "done"): void }>();

const visible = ref(props.modelValue);
watch(() => props.modelValue, (v) => { visible.value = v; });
watch(visible, (v) => { emit("update:modelValue", v); });

const authStore = useAuthStore();
const formRef = ref<FormInstance>();
const loading = ref(false);

const form = reactive({
  oldPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const validateConfirm = (_rule: any, value: string, callback: any) => {
  if (value !== form.newPassword) callback(new Error("两次输入的密码不一致"));
  else callback();
};

const rules: FormRules = {
  oldPassword: [{ required: true, message: "请输入当前密码", trigger: "blur" }],
  newPassword: [
    { required: true, message: "请输入新密码", trigger: "blur" },
    { min: 6, message: "密码长度至少6位", trigger: "blur" },
  ],
  confirmPassword: [
    { required: true, message: "请确认新密码", trigger: "blur" },
    { validator: validateConfirm, trigger: "blur" },
  ],
};

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  if (form.newPassword === form.oldPassword) {
    ElMessage.warning("新密码不能与当前密码相同");
    return;
  }

  loading.value = true;
  try {
    await authStore.changePassword(form.oldPassword, form.newPassword);
    ElMessage.success("密码修改成功！");
    emit("done");
    visible.value = false;
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || "密码修改失败");
  } finally {
    loading.value = false;
  }
}

function handleSkip() {
  ElMessage.info("建议尽快修改默认密码以保证系统安全");
  emit("done");
  visible.value = false;
}
</script>

<style scoped>
:deep(.el-dialog) {
  background: linear-gradient(135deg, #0d1b2e 0%, #1a2a4a 100%);
  border: 1px solid rgba(0, 229, 255, 0.25);
  border-radius: 8px;
  box-shadow: 0 0 40px rgba(0, 229, 255, 0.15);
}
:deep(.el-dialog__title) {
  color: #00d4ff;
  font-weight: 700;
  letter-spacing: 2px;
}
:deep(.el-dialog__header) {
  border-bottom: 1px solid rgba(0, 229, 255, 0.15);
  margin-right: 0;
}
:deep(.el-form-item__label) {
  color: #a8c4d8;
}
:deep(.el-input__wrapper) {
  background: rgba(0, 229, 255, 0.04) !important;
  border-color: rgba(0, 229, 255, 0.2) !important;
  box-shadow: none !important;
}
:deep(.el-input__inner) {
  color: #e6f7ff;
}

.pwd-warning {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 14px;
  background: rgba(250, 173, 20, 0.1);
  border: 1px solid rgba(250, 173, 20, 0.3);
  border-radius: 4px;
  margin-bottom: 20px;
  color: #faad14;
  font-size: 13px;
  line-height: 1.6;
}
.warn-icon {
  font-size: 18px;
  flex-shrink: 0;
  margin-top: 1px;
}

.dialog-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
.submit-btn {
  background: linear-gradient(135deg, #00d4ff, #00b8d4) !important;
  border-color: #00d4ff !important;
  color: #001a2b !important;
  font-weight: 600;
  letter-spacing: 2px;
}
.skip-btn {
  background: transparent !important;
  border-color: rgba(0, 229, 255, 0.2) !important;
  color: #6b89a3 !important;
}
.skip-btn:hover {
  border-color: #6b89a3 !important;
  color: #a8c4d8 !important;
}
</style>
