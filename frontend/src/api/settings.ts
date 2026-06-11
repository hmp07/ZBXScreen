import request from "./request";

export function getSettings() {
  return request.get("/settings");
}

export function updateSettings(data: any) {
  return request.put("/settings", data);
}
