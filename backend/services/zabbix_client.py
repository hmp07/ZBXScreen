"""
Zabbix API 封装
- 版本自适应认证（5.x / 6.x / 7.x）
- Auth token 缓存（内存 TTL 3600s）
- 超时控制 + 自动重连
- 主机、监控项、历史数据、触发器、主机组查询
- 网卡自动发现
"""
import time
import asyncio
import httpx
from typing import Optional
from config import settings

# 优先匹配的网卡名称（适配 Predictable Network Interface Names）
PREFERRED_INTERFACES = ["eth0", "ens33", "enp0s3", "eno1", "ens192", "ens160"]


class ZabbixClient:
    """Zabbix JSON-RPC API 客户端"""

    def __init__(self, url: str, username: str, password: str):
        self.url = url.rstrip("/") + "/api_jsonrpc.php"
        self.username = username
        self.password = password
        self._auth_token: Optional[str] = None
        self._token_expires_at: float = 0  # Unix timestamp
        self._version: Optional[int] = None

    @property
    def auth_token(self) -> Optional[str]:
        """获取有效的 auth token（自动检查过期）"""
        if self._auth_token and time.time() < self._token_expires_at:
            return self._auth_token
        return None

    async def _call(self, method: str, params: dict = None, auth_required: bool = True) -> dict:
        """通用 JSON-RPC 调用。Zabbix 7.x 使用 HTTP Bearer 认证，旧版使用 auth 字段。"""
        if params is None:
            params = {}

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1,
        }

        if auth_required and method not in ("user.login", "apiinfo.version", "user.checkAuthentication"):
            if not self.auth_token:
                await self.authenticate()

        # 构建 headers
        headers = {"Content-Type": "application/json"}
        if auth_required and method not in ("user.login", "apiinfo.version", "user.checkAuthentication"):
            # Zabbix 7.x: 使用 HTTP Bearer 认证（不再使用 JSON body 的 auth 字段）
            if self._version and self._version >= 7:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            else:
                payload["auth"] = self.auth_token

        async with httpx.AsyncClient(timeout=settings.zabbix_request_timeout) as client:
            try:
                resp = await client.post(self.url, json=payload, headers=headers)
                resp.raise_for_status()
                result = resp.json()

                if "error" in result:
                    error_data = result["error"]
                    # Token 过期，重新登录后重试一次
                    if error_data.get("code") == -32602 and auth_required:
                        await self.authenticate()
                        if self._version and self._version >= 7:
                            headers["Authorization"] = f"Bearer {self.auth_token}"
                        else:
                            payload["auth"] = self.auth_token
                        resp2 = await client.post(self.url, json=payload, headers=headers)
                        resp2.raise_for_status()
                        return resp2.json()["result"]

                    raise ZabbixAPIError(
                        f"Zabbix API error: {error_data.get('message', 'Unknown')}",
                        code=error_data.get("code"),
                    )

                return result["result"]

            except httpx.TimeoutException:
                raise ZabbixAPIError(f"Zabbix API timeout ({settings.zabbix_request_timeout}s)")
            except httpx.HTTPError as e:
                raise ZabbixAPIError(f"Zabbix HTTP error: {str(e)}")

    async def _detect_version(self) -> int:
        """检测 Zabbix 主版本号（5/6/7）"""
        if self._version is not None:
            return self._version
        version_str = await self._call("apiinfo.version", {}, auth_required=False)
        self._version = int(version_str.split(".")[0])
        return self._version

    async def authenticate(self):
        """版本自适应认证"""
        token = await self._call("user.login", {
            "username": self.username,
            "password": self.password,
        }, auth_required=False)

        # Zabbix 7.x: 登录后建议验证 token
        version = await self._detect_version()
        if version >= 7:
            await self._call("user.checkAuthentication", {
                "sessionid": token
            }, auth_required=False)

        self._auth_token = token
        self._token_expires_at = time.time() + 3600  # TTL 1 小时
        return token

    async def test_connection(self) -> dict:
        """测试连接，返回 Zabbix 版本号"""
        version_str = await self._call("apiinfo.version", {}, auth_required=False)
        # 同时测试认证
        await self.authenticate()
        return {"version": version_str, "authenticated": True}

    # ── 数据查询方法 ──

    async def get_hosts(self, groupids: list = None, hostids: list = None,
                        filter_name: str = None) -> list:
        """获取主机列表"""
        params = {
            "output": ["hostid", "host", "name", "status", "description", "available"],
            "selectInterfaces": ["ip", "dns", "type", "main", "available"],
            "selectGroups": ["groupid", "name"],
            # selectInventory removed: may cause "Invalid request" on Zabbix 7.x
            # without super admin permissions
        }
        if groupids:
            params["groupids"] = groupids
        if hostids:
            params["hostids"] = hostids
        if filter_name:
            params["search"] = {"host": filter_name}

        return await self._call("host.get", params)

    async def get_items(self, hostids: list, search_keys: list = None) -> list:
        """
        获取监控项列表。
        search_keys: 可选的关键 key 模式列表（如 ["system.cpu.util", "vm.memory"]）。
        在 Python 侧做模糊匹配（Zabbix API search 不支持 OR 逻辑）。
        """
        params = {
            "hostids": hostids,
            "output": ["itemid", "hostid", "name", "key_", "lastvalue", "lastclock", "units", "value_type"],
            "limit": 50000,  # 提高上限（251 主机约 12500+ items）
        }
        items = await self._call("item.get", params)

        if search_keys:
            filtered = []
            for item in items:
                key = item.get("key_", "")
                for pattern in search_keys:
                    # 去掉参数部分做前缀匹配：system.cpu.util[,idle] → system.cpu.util
                    clean_pattern = pattern.split("[")[0]
                    if clean_pattern in key:
                        filtered.append(item)
                        break
            return filtered

        return items

    async def get_history(self, hostids: list, item_key: str, start_time: int,
                          end_time: int, limit: int = 500) -> list:
        """获取历史数据（≤1 天用此接口）"""
        # 先查 itemid
        items = await self._call("item.get", {
            "hostids": hostids,
            "search": {"key_": item_key},
            "output": ["itemid", "name"],
        })
        if not items:
            return []

        itemids = [i["itemid"] for i in items]
        history = await self._call("history.get", {
            "itemids": itemids,
            "time_from": start_time,
            "time_till": end_time,
            "sortfield": "clock",
            "sortorder": "ASC",
            "limit": limit,
            "output": "extend",
        })
        return history

    async def get_trends(self, hostids: list, item_key: str, start_time: int,
                         end_time: int, limit: int = 500) -> list:
        """获取趋势数据（>1 天用此接口）"""
        items = await self._call("item.get", {
            "hostids": hostids,
            "search": {"key_": item_key},
            "output": ["itemid", "name"],
        })
        if not items:
            return []

        itemids = [i["itemid"] for i in items]
        trends = await self._call("trend.get", {
            "itemids": itemids,
            "time_from": start_time,
            "time_till": end_time,
            "sortfield": "clock",
            "sortorder": "ASC",
            "limit": limit,
            "output": "extend",
        })
        return trends

    async def get_triggers(self, hostids: list = None, groupids: list = None,
                           active_only: bool = True, min_severity: int = 0) -> list:
        """获取触发器列表"""
        params = {
            "output": ["triggerid", "description", "priority", "value", "lastchange"],
            "selectHosts": ["hostid", "host", "name"],
            "selectGroups": ["groupid", "name"],
            "sortfield": "lastchange",
            "sortorder": "DESC",
        }
        if hostids:
            params["hostids"] = hostids
        if groupids:
            params["groupids"] = groupids
        if active_only:
            params["filter"] = {"value": 1}  # 1=Problem
        if min_severity > 0:
            params["min_severity"] = str(min_severity)

        return await self._call("trigger.get", params)

    async def get_hostgroups(self) -> list:
        """获取主机组列表"""
        return await self._call("hostgroup.get", {
            "output": ["groupid", "name"],
        })

    async def get_snmp_system_info(self, hostids: list) -> dict:
        """
        专用方法：获取 SNMP 系统信息（system.descr, system.name, system.hw.*）。
        使用 Zabbix API search 参数服务端过滤，避免全量拉取 item 超时。
        返回: {hostid: {descr, name, model, serial}}
        """
        system_info = {}

        # 搜索 system.descr / system.name / system.hw.model / system.hw.serialnumber
        search_patterns = ["system.descr", "system.name", "system.hw.model",
                          "system.hw.serialnumber", "system.hw.uptime"]

        for pattern in search_patterns:
            try:
                items = await self._call("item.get", {
                    "hostids": hostids,
                    "search": {"key_": pattern},
                    "output": ["itemid", "hostid", "name", "key_", "lastvalue"],
                    "limit": 5000,
                })
                for item in items:
                    hostid = item.get("hostid", "")
                    key = item.get("key_", "")
                    val = str(item.get("lastvalue", "")) if item.get("lastvalue") else ""

                    if hostid not in system_info:
                        system_info[hostid] = {}

                    if "system.descr" in key:
                        system_info[hostid]["descr"] = val
                    elif "system.name" in key:
                        system_info[hostid]["name"] = val
                    elif "hw.model" in key:
                        system_info[hostid]["model"] = val
                    elif "hw.serialnumber" in key:
                        system_info[hostid]["serial"] = val
            except Exception as e:
                print(f"[SNMP] Failed to fetch {pattern}: {e}")
                continue

        return system_info

    async def discover_network_interface(self, host_id: str) -> str:
        """网卡自动发现：按 PREFERRED_INTERFACES 顺序匹配，排除 lo"""
        items = await self._call("item.get", {
            "hostids": [host_id],
            "search": {"key_": "net.if.in["},
            "searchWildcardsEnabled": True,
            "output": ["key_"],
        })

        interfaces = set()
        for item in items:
            key = item["key_"]
            # 提取接口名：net.if.in[eth0] → eth0, net.if.in[ens33,bytes] → ens33
            part = key.split("[")[1].split("]")[0].split(",")[0]
            if part and part != "lo":
                interfaces.add(part)

        # 按优先顺序匹配
        for pref in PREFERRED_INTERFACES:
            if pref in interfaces:
                return pref

        # 取第一个非 lo 的接口
        if interfaces:
            return min(interfaces)

        return "eth0"  # fallback


class ZabbixAPIError(Exception):
    """Zabbix API 调用错误"""
    def __init__(self, message: str, code: int = -1):
        self.message = message
        self.code = code
        super().__init__(message)
