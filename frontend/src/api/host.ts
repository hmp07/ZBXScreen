import request from "./request";

export function getHostList(params: {
  datasource_id?: number;
  hostgroup_id?: string;
  search?: string;
  page?: number;
  page_size?: number;
}) {
  return request.get("/hosts", { params });
}

export function getHostDetail(hostid: string, datasource_id: number) {
  return request.get(`/hosts/${hostid}`, { params: { datasource_id } });
}

export function getHostHistory(hostid: string, params: {
  datasource_id: number;
  item_key: string;
  start_time?: string;
  end_time?: string;
}) {
  return request.get(`/hosts/${hostid}/history`, { params });
}
