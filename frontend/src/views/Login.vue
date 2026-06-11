<template>
  <div class="login-container">
    <!-- 背景网格 -->
    <div class="bg-grid"></div>
    <!-- 背景光晕 -->
    <div class="bg-glow glow-1"></div>
    <div class="bg-glow glow-2"></div>

    <div class="login-card">
      <div class="card-corner tl"></div>
      <div class="card-corner tr"></div>
      <div class="card-corner bl"></div>
      <div class="card-corner br"></div>

      <div class="login-header">
        <img v-if="brandLogo" :src="brandLogo" class="login-logo-img" />
        <div v-else class="login-logo">{{ brandTitle.charAt(0) }}</div>
        <h1 class="login-title">{{ brandTitle }}</h1>
        <p v-if="brandSub" class="login-subtitle">{{ brandSub }}</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="login-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            size="large"
          >
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            show-password
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button
            size="large"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            <span class="btn-text">登 录</span>
          </el-button>
        </el-form-item>
      </el-form>

      <p v-if="errorMsg" class="login-error">{{ errorMsg }}</p>
    </div>

    <!-- 默认密码修改弹窗 -->
    <ChangePasswordDialog v-model="showPwdDialog" @done="onPwdDone" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import type { FormInstance, FormRules } from "element-plus";
import { User, Lock } from "@element-plus/icons-vue";
import ChangePasswordDialog from "@/components/ChangePasswordDialog.vue";
import axios from "axios";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const formRef = ref<FormInstance>();
const loading = ref(false);
const errorMsg = ref("");
const showPwdDialog = ref(false);

const brandTitle = ref("ZBXScreen");
const brandSub = ref("监控大屏展示系统");
const brandLogo = ref("");

onMounted(async () => {
  try {
    const res = await axios.get("/api/v1/settings/public");
    if (res.data.code === 0) {
      const d = res.data.data;
      if (d.title) brandTitle.value = d.title;
      if (d.subtitle) brandSub.value = d.subtitle;
      if (d.logo) brandLogo.value = d.logo;
    }
  } catch (e) { /* use defaults */ }
});

const form = reactive({
  username: "",
  password: "",
});

const rules: FormRules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  errorMsg.value = "";

  try {
    const isDefault = await authStore.login(form.username, form.password);
    if (isDefault) {
      showPwdDialog.value = true;
    } else {
      doRedirect();
    }
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail?.message || "登录失败，请检查用户名和密码";
  } finally {
    loading.value = false;
  }
}

function onPwdDone() {
  doRedirect();
}

function doRedirect() {
  const redirect = (route.query.redirect as string) || "/dashboard";
  router.push(redirect);
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100vw;
  height: 100vh;
  background: #05080f;
  position: relative;
  overflow: hidden;
}

/* 背景网格 */
.bg-grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(0, 229, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 229, 255, 0.04) 1px, transparent 1px);
  background-size: 60px 60px;
  pointer-events: none;
}

/* 背景光晕 */
.bg-glow {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  filter: blur(120px);
  opacity: 0.15;
}
.glow-1 {
  width: 600px; height: 600px;
  background: radial-gradient(circle, #00e5ff, transparent 70%);
  top: -200px; left: -150px;
  animation: float1 12s ease-in-out infinite;
}
.glow-2 {
  width: 500px; height: 500px;
  background: radial-gradient(circle, #7b61ff, transparent 70%);
  bottom: -200px; right: -100px;
  animation: float2 15s ease-in-out infinite;
}
@keyframes float1 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(60px, 40px); }
}
@keyframes float2 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-50px, -30px); }
}

/* 登录卡片 */
.login-card {
  width: 420px;
  padding: 52px 44px 40px;
  background: linear-gradient(135deg, rgba(13, 27, 46, 0.92), rgba(8, 22, 40, 0.95));
  border: 1px solid rgba(0, 229, 255, 0.18);
  border-radius: 6px;
  backdrop-filter: blur(20px);
  position: relative;
  box-shadow:
    0 0 80px rgba(0, 229, 255, 0.06),
    0 30px 60px rgba(0, 0, 0, 0.5);
  z-index: 1;
}

/* 卡片四角装饰 */
.card-corner {
  position: absolute; width: 18px; height: 18px;
  border: 2px solid #00e5ff;
  opacity: 0.7;
}
.tl { top: -1px; left: -1px; border-right: 0; border-bottom: 0; }
.tr { top: -1px; right: -1px; border-left: 0; border-bottom: 0; }
.bl { bottom: -1px; left: -1px; border-right: 0; border-top: 0; }
.br { bottom: -1px; right: -1px; border-left: 0; border-top: 0; }

/* 头部 */
.login-header {
  text-align: center;
  margin-bottom: 38px;
}
.login-logo {
  width: 56px; height: 56px;
  margin: 0 auto 16px;
  border-radius: 12px;
  background: linear-gradient(135deg, #00e5ff, #00b8d4);
  display: flex; align-items: center; justify-content: center;
  font-family: 'Orbitron', 'Consolas', monospace;
  font-weight: 900; color: #001a2b; font-size: 26px;
  box-shadow: 0 0 32px rgba(0, 229, 255, 0.3);
}
.login-logo-img {
  width: 64px; height: 64px;
  margin: 0 auto 16px;
  border-radius: 12px;
  object-fit: contain;
  display: block;
  filter: drop-shadow(0 0 16px rgba(0, 229, 255, 0.4));
}
.login-title {
  font-family: 'Orbitron', 'Consolas', monospace;
  font-size: 28px; font-weight: 700; letter-spacing: 4px;
  background: linear-gradient(180deg, #ffffff 30%, #00e5ff 100%);
  -webkit-background-clip: text; background-clip: text;
  color: transparent;
  margin-bottom: 8px;
}
.login-subtitle {
  font-size: 13px;
  color: #6b89a3;
  letter-spacing: 4px;
}

/* 表单 */
.login-form {
  width: 100%;
}
:deep(.el-input__wrapper) {
  background: rgba(0, 229, 255, 0.03) !important;
  border: 1px solid rgba(0, 229, 255, 0.15) !important;
  border-radius: 4px !important;
  box-shadow: none !important;
  transition: border-color 0.3s, background 0.3s;
}
:deep(.el-input__wrapper:hover) {
  border-color: rgba(0, 229, 255, 0.35) !important;
  background: rgba(0, 229, 255, 0.06) !important;
}
:deep(.el-input__wrapper.is-focus) {
  border-color: #00e5ff !important;
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.15) !important;
}
:deep(.el-input__inner) {
  color: #e6f7ff !important;
}
:deep(.el-input__prefix) {
  color: #455a72;
}
:deep(.el-input__suffix) {
  color: #455a72;
}

/* 登录按钮 */
.login-btn {
  width: 100% !important;
  height: 46px !important;
  margin-top: 8px;
  background: linear-gradient(135deg, #00b8d4, #00e5ff) !important;
  border: none !important;
  border-radius: 4px !important;
  position: relative;
  overflow: hidden;
  transition: all 0.3s !important;
  box-shadow:
    0 0 20px rgba(0, 229, 255, 0.25),
    0 4px 16px rgba(0, 0, 0, 0.3);
}
.login-btn:hover {
  transform: translateY(-1px);
  box-shadow:
    0 0 32px rgba(0, 229, 255, 0.4),
    0 6px 20px rgba(0, 0, 0, 0.4);
  background: linear-gradient(135deg, #00d4ff, #7be8ff) !important;
}
.login-btn:active {
  transform: translateY(0);
}
.login-btn.is-loading {
  background: linear-gradient(135deg, #0088a0, #00b8d4) !important;
}
.btn-text {
  font-size: 16px; font-weight: 700; letter-spacing: 8px;
  color: #001a2b;
}
:deep(.el-button.is-loading .btn-text) {
  visibility: hidden;
}

/* 错误提示 */
.login-error {
  text-align: center;
  color: #f5222d;
  font-size: 13px;
  margin-top: 16px;
  padding: 8px 0;
}
</style>
