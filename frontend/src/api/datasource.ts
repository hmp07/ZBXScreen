import request from "./request";

export interface Datasource {
  id: number;
  name: string;
  url: string;
  username: string;
  enabled: boolean;
  last_connected_at: string | null;
  zabbix_version: string | null;
  created_at: string;
}

export function getDatasources() {
  return request.get<{ code: number; data: Datasource[] }>("/datasources");
}

export function createDatasource(data: {
  name: string;
  url: string;
  username: string;
  password: string;
}) {
  return request.post("/datasources", data);
}

export function updateDatasource(
  id: number,
  data: { name?: string; url?: string; username?: string; password?: string }
) {
  return request.post(`/datasources/${id}/update`, data);
}

export function deleteDatasource(id: number) {
  return request.post(`/datasources/${id}/delete`);
}

export function testConnection(id: number) {
  return request.post(`/datasources/${id}/test`);
}

export function toggleDatasource(id: number) {
  return request.post(`/datasources/${id}/toggle`);
}

export function getHostgroups(id: number) {
  return request.get(`/datasources/${id}/hostgroups`);
}

export function getHosts(id: number, groupid?: string) {
  return request.get(`/datasources/${id}/hosts`, {
    params: groupid ? { groupid } : {},
  });
}
