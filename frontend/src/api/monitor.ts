import request from "./request";

export function getSummary() {
  return request.get("/monitor/summary");
}

export function getHosts(params?: { datasource_id?: number; hostgroup_id?: string; limit?: number }) {
  return request.get("/monitor/hosts", { params });
}

export function getTopCpu(params?: { limit?: number }) {
  return request.get("/monitor/top-cpu", { params });
}

export function getTopMemory(params?: { limit?: number }) {
  return request.get("/monitor/top-memory", { params });
}

export function getTopDisk(params?: { limit?: number }) {
  return request.get("/monitor/top-disk", { params });
}

export function getTopNetworkIn(params?: { limit?: number }) {
  return request.get("/monitor/top-network-in", { params });
}

export function getTopNetworkOut(params?: { limit?: number }) {
  return request.get("/monitor/top-network-out", { params });
}

export function getAlerts(params?: { limit?: number }) {
  return request.get("/monitor/alerts", { params });
}
