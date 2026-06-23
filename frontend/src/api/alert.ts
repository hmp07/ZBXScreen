import request from "./request";

export function getAlertRules() {
  return request.get("/alerts/rules");
}

export function createAlertRule(data: any) {
  return request.post("/alerts/rules", data);
}

export function updateAlertRule(id: number, data: any) {
  return request.post(`/alerts/rules/${id}/update`, data);
}

export function deleteAlertRule(id: number) {
  return request.post(`/alerts/rules/${id}/delete`);
}

export function toggleAlertRule(id: number) {
  return request.post(`/alerts/rules/${id}/toggle`);
}

export function getAlertRecords(params: {
  page?: number;
  page_size?: number;
  level?: string;
  status?: string;
}) {
  return request.get("/alerts/records", { params });
}

export function getAlertStats() {
  return request.get("/alerts/stats");
}

export function getAlertDashboard() {
  return request.get("/alerts/dashboard");
}
