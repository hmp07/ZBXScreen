import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { loginApi, refreshApi, changePasswordApi } from "@/api/auth";

export const useAuthStore = defineStore("auth", () => {
  const accessToken = ref<string | null>(localStorage.getItem("access_token"));
  const refreshToken = ref<string | null>(localStorage.getItem("refresh_token"));
  const username = ref<string | null>(localStorage.getItem("username"));

  const isAuthenticated = computed(() => !!accessToken.value);

  function restoreSession() {
    accessToken.value = localStorage.getItem("access_token");
    refreshToken.value = localStorage.getItem("refresh_token");
    username.value = localStorage.getItem("username");
  }

  async function login(user: string, pwd: string) {
    const res = await loginApi(user, pwd);
    const data = res.data.data;
    accessToken.value = data.access_token;
    refreshToken.value = data.refresh_token;
    username.value = user;
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    localStorage.setItem("username", user);
    return data.is_default_password === true;
  }

  async function refreshAccessToken() {
    if (!refreshToken.value) throw new Error("No refresh token");
    const res = await refreshApi(refreshToken.value);
    const data = res.data.data;
    accessToken.value = data.access_token;
    refreshToken.value = data.refresh_token;
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
  }

  async function changePassword(oldPwd: string, newPwd: string) {
    await changePasswordApi(oldPwd, newPwd);
  }

  function logout() {
    accessToken.value = null;
    refreshToken.value = null;
    username.value = null;
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("username");
  }

  return {
    accessToken,
    refreshToken,
    username,
    isAuthenticated,
    restoreSession,
    login,
    refreshAccessToken,
    changePassword,
    logout,
  };
});
