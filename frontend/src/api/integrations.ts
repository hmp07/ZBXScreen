/** 运维集成 API — Zabbix / iTop 跳转 URL 生成 */
import request from "./request";

export interface IntegrationSettings {
  zabbix_frontend_url: string;
  itop_url: string;
  itop_incident_template: string;
}

/** 获取集成配置 */
export function getIntegrationSettings(): Promise<{ data: { code: number; data: Record<string, string> } }> {
  return request.get("/settings");
}

/** 生成 Zabbix 主机页面 URL */
export function getZabbixHostUrl(zabbixBase: string, hostId: string): string {
  return `${zabbixBase}/integrations/zabbix/zabbix.php?action=host.edit&hostid=${hostId}`;
}

/** 根据模板生成 iTop 工单 URL */
export function getItopIncidentUrl(template: string, variables: Record<string, string>): string {
  let url = template;
  for (const [key, value] of Object.entries(variables)) {
    url = url.replace(`{${key}}`, encodeURIComponent(value));
  }
  return url;
}
