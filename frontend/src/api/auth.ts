import request from "./request";

export function loginApi(username: string, password: string) {
  return request.post("/auth/login", { username, password });
}

export function refreshApi(refreshToken: string) {
  return request.post("/auth/refresh", { refresh_token: refreshToken });
}

export function changePasswordApi(oldPassword: string, newPassword: string) {
  return request.post("/auth/password", {
    old_password: oldPassword,
    new_password: newPassword,
  });
}
