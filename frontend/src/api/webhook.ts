import request from "./request";

export function getWebhooks() {
  return request.get("/webhooks");
}

export function createWebhook(data: any) {
  return request.post("/webhooks", data);
}

export function updateWebhook(id: number, data: any) {
  return request.post(`/webhooks/${id}/update`, data);
}

export function deleteWebhook(id: number) {
  return request.post(`/webhooks/${id}/delete`);
}

export function toggleWebhook(id: number) {
  return request.post(`/webhooks/${id}/toggle`);
}

export function testWebhook(id: number) {
  return request.post(`/webhooks/${id}/test`);
}

export function getWebhookLogs(id: number, params: { page?: number; page_size?: number }) {
  return request.get(`/webhooks/${id}/logs`, { params });
}
