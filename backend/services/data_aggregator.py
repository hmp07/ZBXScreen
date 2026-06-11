"""
数据聚合服务
- 并发拉取所有启用数据源
- 超时控制 + 慢数据源降级
- 跨数据源主机去重
- 采集 item-level 指标数据构建 TOP N 排行
- 写入 monitor_cache 表
"""
import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models.datasource import Datasource
from models.monitor_cache import MonitorCache
from utils.crypto import decrypt_password
from utils.cache import memory_cache
from services.zabbix_client import ZabbixClient, ZabbixAPIError
from config import settings

async def aggregate_all_datasources():
    """主聚合任务：每 30 秒由调度器调用"""
    print(f"[AGGREGATOR] Starting aggregation...")
    start = time.time()

    async with AsyncSessionLocal() as db:
        # 获取所有启用的数据源
        result = await db.execute(
            select(Datasource).where(Datasource.enabled == True)
        )
        datasources = result.scalars().all()

        if not datasources:
            print("[AGGREGATOR] No enabled datasources, skipping.")
            return

        # 并发拉取所有数据源（hosts + alerts + item metrics）
        tasks = [fetch_datasource_data(ds) for ds in datasources]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=settings.aggregation_total_timeout,
            )
        except asyncio.TimeoutError:
            print(f"[AGGREGATOR] Total timeout ({settings.aggregation_total_timeout}s) reached.")
            results = [None] * len(tasks)

        # 处理结果
        all_hosts = []
        total_alerts = 0
        all_host_metrics = {}  # hostname → metrics dict
        all_ping_status = {}   # hostid → bool (agent.ping 状态)
        all_interface_errors = {}  # hostid → {iface: {in_errors, out_errors, ...}}
        all_system_info = {}       # hostid → {descr, name, model, serial}

        for i, result in enumerate(results):
            ds = datasources[i]
            if isinstance(result, Exception):
                print(f"[AGGREGATOR] Datasource '{ds.name}' error: {result}")
                continue
            if result is None:
                continue

            hosts_data = result.get("hosts", [])
            for h in hosts_data:
                h["_datasource_id"] = ds.id
                h["_datasource_name"] = ds.name
            all_hosts.extend(hosts_data)
            total_alerts += result.get("alert_count", 0)

            # 合并 ping 状态
            ping_status = result.get("ping_status", {})
            all_ping_status.update(ping_status)

            # 合并 item metrics
            item_metrics = result.get("item_metrics", {})
            hostid_to_name = {}
            for h in hosts_data:
                hostid_to_name[h.get("hostid", "")] = h.get("host") or h.get("name", "unknown")

            for hostid, metrics in item_metrics.items():
                hostname = hostid_to_name.get(hostid, hostid)
                if hostname not in all_host_metrics:
                    all_host_metrics[hostname] = metrics

            # 合并网络接口错误数据
            iface_errors = result.get("interface_errors", {})
            for hostid, ifaces in iface_errors.items():
                if hostid not in all_interface_errors:
                    all_interface_errors[hostid] = {}
                for iface, err_data in ifaces.items():
                    if iface not in all_interface_errors[hostid]:
                        all_interface_errors[hostid][iface] = err_data
                    else:
                        # 合并（取最大值，因为错误计数是累积的）
                        existing = all_interface_errors[hostid][iface]
                        for k in ("in_errors", "out_errors", "in_discards", "out_discards"):
                            existing[k] = max(existing.get(k, 0), err_data.get(k, 0))

            # 合并系统信息
            sys_info = result.get("system_info", {})
            for hostid, info in sys_info.items():
                if hostid not in all_system_info:
                    all_system_info[hostid] = info
                else:
                    for k, v in info.items():
                        if v and not all_system_info[hostid].get(k):
                            all_system_info[hostid][k] = v

        # 跨数据源去重（按 hostname）
        seen = set()
        deduped_hosts = []
        for h in all_hosts:
            key = h.get("host", h.get("name", ""))
            if key not in seen:
                seen.add(key)
                deduped_hosts.append(h)

        # 通过 agent.ping 判断在线/离线状态
        offline_hostnames = set()
        online_count = 0
        offline_count = 0
        for h in deduped_hosts:
            hostid = h.get("hostid", "")
            hostname = h.get("host") or h.get("name", "")
            is_online = all_ping_status.get(hostid, True)
            if is_online:
                online_count += 1
            else:
                offline_count += 1
                offline_hostnames.add(hostname)

        summary = {
            "total_hosts": len(deduped_hosts),
            "online_hosts": online_count,
            "offline_hosts": offline_count,
            "alert_count": total_alerts,
        }

        # 构建 TOP N 排行（排除 agent.ping=0 的离线主机）
        top_cpu = _build_top_n(all_host_metrics, "cpu", 10, exclude_hosts=offline_hostnames)
        top_memory = _build_top_n(all_host_metrics, "memory", 10, exclude_hosts=offline_hostnames)
        top_disk = _build_top_n(all_host_metrics, "disk", 10, exclude_hosts=offline_hostnames)
        top_network_in = _build_top_n(all_host_metrics, "network_in", 10, exclude_hosts=offline_hostnames)
        top_network_out = _build_top_n(all_host_metrics, "network_out", 10, exclude_hosts=offline_hostnames)

        # ── 构建网络设备数据 ──
        network_devices = await _build_network_devices(
            datasources, all_interface_errors, all_system_info,
            deduped_hosts, all_ping_status, top_network_in, top_network_out, all_host_metrics
        )

        # 写入缓存表
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        expires = now + timedelta(seconds=settings.default_refresh_interval + 5)

        await upsert_cache(db, "summary", None, summary, expires)
        await upsert_cache(db, "hosts", None, deduped_hosts, expires)
        await upsert_cache(db, "top_cpu", None, top_cpu, expires)
        await upsert_cache(db, "top_memory", None, top_memory, expires)
        await upsert_cache(db, "top_disk", None, top_disk, expires)
        await upsert_cache(db, "top_network_in", None, top_network_in, expires)
        await upsert_cache(db, "top_network_out", None, top_network_out, expires)
        await upsert_cache(db, "network_devices", None, network_devices, expires)

        elapsed = time.time() - start
        net_summary = network_devices.get("network_summary", {})
        print(f"[AGGREGATOR] Done: {len(datasources)} sources, {len(deduped_hosts)} hosts "
              f"({online_count} online), {total_alerts} alerts, "
              f"TOP N: cpu={len(top_cpu)} mem={len(top_memory)} disk={len(top_disk)} "
              f"net_in={len(top_network_in)} net_out={len(top_network_out)}, "
              f"net_devices={net_summary.get('total_devices', 0)}, "
              f"{elapsed:.1f}s")

        # 更新内存缓存
        memory_cache.set("summary", summary, settings.default_refresh_interval)
        memory_cache.set("hosts", deduped_hosts, settings.default_refresh_interval)
        memory_cache.set("top_cpu", top_cpu, settings.default_refresh_interval)
        memory_cache.set("top_memory", top_memory, settings.default_refresh_interval)
        memory_cache.set("top_disk", top_disk, settings.default_refresh_interval)
        memory_cache.set("top_network_in", top_network_in, settings.default_refresh_interval)
        memory_cache.set("top_network_out", top_network_out, settings.default_refresh_interval)
        memory_cache.set("network_devices", network_devices, settings.default_refresh_interval)


async def fetch_datasource_data(ds: Datasource) -> dict:
    """拉取单个数据源的主机数据、告警计数和 item-level 指标（含 ping 状态）"""
    try:
        password = decrypt_password(ds.password_encrypted)
        client = ZabbixClient(ds.url, ds.username, password)

        # 获取主机列表
        hosts = await client.get_hosts()

        # 获取活跃触发器数量
        triggers = await client.get_triggers(active_only=True)

        # 一次性获取所有 items，同时提取 metrics + ping 状态 + 网络接口错误 + 系统信息
        hostids = [h.get("hostid") for h in hosts if h.get("hostid")]
        item_metrics, ping_status, interface_errors, system_info = await _fetch_item_data(client, hostids)

        return {
            "hosts": hosts,
            "alert_count": len(triggers),
            "item_metrics": item_metrics,
            "ping_status": ping_status,
            "interface_errors": interface_errors,
            "system_info": system_info,
        }
    except ZabbixAPIError as e:
        print(f"[AGGREGATOR] Zabbix error for '{ds.name}': {e}")
        return {"hosts": [], "alert_count": 0, "item_metrics": {}, "ping_status": {},
                "interface_errors": {}, "system_info": {}}
    except Exception as e:
        print(f"[AGGREGATOR] Unexpected error for '{ds.name}': {e}")
        return {"hosts": [], "alert_count": 0, "item_metrics": {}, "ping_status": {},
                "interface_errors": {}, "system_info": {}}


async def _fetch_item_data(client: ZabbixClient, hostids: list[str]) -> tuple[dict, dict, dict, dict]:
    """
    一次性拉取所有 items，同时提取指标数据、agent.ping 状态、网络接口错误和系统信息。
    避免重复 API 调用。
    返回: (host_metrics, ping_status, interface_errors, system_info)
      host_metrics: {hostid: {cpu, memory, disk, network_in, network_out}}
      ping_status:  {hostid: bool}
      interface_errors: {hostid: [{iface, in_errors, out_errors, in_discards, out_discards}]}
      system_info: {hostid: {descr, name, model, serial}}
    """
    import re

    if not hostids:
        return {}, {}, {}, {}

    try:
        items = await client.get_items(hostids=hostids)
    except ZabbixAPIError:
        return {}, {}, {}, {}

    host_metrics = {}
    ping_status = {}
    # interface_errors: {hostid: {iface_name: {in_errors, out_errors, in_discards, out_discards}}}
    interface_errors = {}
    system_info = {}

    def _parse_iface(item_name: str, key: str) -> str:
        """从 item name 或 key 中提取接口名"""
        # name 格式: "Interface GE1/0/5(): Inbound packets with errors"
        m = re.search(r'Interface\s+(\S+?)\(\)', item_name)
        if m:
            return m.group(1)
        # key 格式: net.if.in.errors[ifInErrors.10]
        m = re.search(r'\[([^\]]+)\]', key)
        if m:
            return m.group(1)
        return "unknown"

    for item in items:
        hostid = item.get("hostid", "")
        key = item.get("key_", "")
        name = item.get("name", "")

        # --- agent.ping / icmpping 状态检测 ---
        if key == "agent.ping":
            try:
                ping_status[hostid] = (float(item.get("lastvalue", "0")) == 1.0)
            except (ValueError, TypeError):
                ping_status[hostid] = False
        elif key == "icmpping" and hostid not in ping_status:
            try:
                ping_status[hostid] = (float(item.get("lastvalue", "0")) > 0)
            except (ValueError, TypeError):
                pass

        # --- 指标值提取 ---
        try:
            val = float(item.get("lastvalue", "0"))
        except (ValueError, TypeError):
            val = 0.0

        if hostid not in host_metrics:
            host_metrics[hostid] = {}

        if "cpu" in key and "idle" in key:
            host_metrics[hostid]["cpu"] = round(100.0 - val, 1)
        elif "memory" in key and "utilization" in key:
            host_metrics[hostid]["memory"] = round(val, 1)
        elif "memory" in key and "pused" in key:
            host_metrics[hostid]["memory"] = round(val, 1)
        elif "memory" in key and "pavailable" in key:
            host_metrics[hostid]["memory"] = round(100.0 - val, 1)
        elif "vfs.fs.size" in key and "pused" in key:
            host_metrics[hostid]["disk"] = round(val, 1)
        elif "vfs.fs.size" in key and "pfree" in key:
            host_metrics[hostid]["disk"] = round(100.0 - val, 1)
        elif "net.if.in" in key and "lo" not in key and "error" not in key and "discard" not in key:
            host_metrics[hostid]["network_in"] = round(val * 8 / 1_000_000, 2)
        elif "net.if.out" in key and "lo" not in key and "error" not in key and "discard" not in key:
            host_metrics[hostid]["network_out"] = round(val * 8 / 1_000_000, 2)

        # --- 网络接口错误/丢弃计数 ---
        if hostid not in interface_errors:
            interface_errors[hostid] = {}

        if "net.if.in.errors" in key and "lo" not in key:
            iface = _parse_iface(name, key)
            if iface not in interface_errors[hostid]:
                interface_errors[hostid][iface] = {}
            interface_errors[hostid][iface]["in_errors"] = int(val)
        elif "net.if.out.errors" in key and "lo" not in key:
            iface = _parse_iface(name, key)
            if iface not in interface_errors[hostid]:
                interface_errors[hostid][iface] = {}
            interface_errors[hostid][iface]["out_errors"] = int(val)
        elif "net.if.in.discards" in key and "lo" not in key:
            iface = _parse_iface(name, key)
            if iface not in interface_errors[hostid]:
                interface_errors[hostid][iface] = {}
            interface_errors[hostid][iface]["in_discards"] = int(val)
        elif "net.if.out.discards" in key and "lo" not in key:
            iface = _parse_iface(name, key)
            if iface not in interface_errors[hostid]:
                interface_errors[hostid][iface] = {}
            interface_errors[hostid][iface]["out_discards"] = int(val)

        # --- 系统信息 ---
        item_value = item.get("lastvalue", "")
        if key.startswith("system.descr") and "lo" not in key:
            if hostid not in system_info:
                system_info[hostid] = {}
            system_info[hostid]["descr"] = str(item_value) if item_value else ""
        elif key == "system.name":
            if hostid not in system_info:
                system_info[hostid] = {}
            system_info[hostid]["name"] = str(item_value) if item_value else ""
        elif key.startswith("system.hw.model"):
            if hostid not in system_info:
                system_info[hostid] = {}
            system_info[hostid]["model"] = str(item_value) if item_value else ""
        elif key.startswith("system.hw.serialnumber"):
            if hostid not in system_info:
                system_info[hostid] = {}
            system_info[hostid]["serial"] = str(item_value) if item_value else ""

    return host_metrics, ping_status, interface_errors, system_info


def _build_top_n(host_metrics: dict, metric_key: str, top_n: int = 10,
                  exclude_hosts: set = None) -> list[dict]:
    """从 host_metrics 构建指定指标的 TOP N 排行，排除不可用主机"""
    exclude = exclude_hosts or set()
    rankings = []
    for hostname, metrics in host_metrics.items():
        if hostname in exclude:
            continue
        if metric_key in metrics:
            val = metrics[metric_key]
            # 过滤明显来自 dead agent 的异常值
            # CPU=100 且其他指标全为 0 → agent 不响应
            rankings.append({
                "host": hostname,
                "value": val,
            })

    rankings.sort(key=lambda x: x["value"], reverse=True)
    return rankings[:top_n]


async def _get_network_host_ids(datasources: list) -> set:
    """
    从 Zabbix 主机组查询所有网络类主机的 hostid。
    网络组包括：交换机(27)、网络设备(28)、路由器(29)、防火墙(30)、网络安全设备(31)。
    """
    from utils.crypto import decrypt_password

    NETWORK_GROUP_IDS = ["27", "28", "29", "30", "31"]
    network_host_ids = set()

    if not datasources:
        return network_host_ids

    # 使用第一个启用的数据源
    for ds in datasources:
        try:
            password = decrypt_password(ds.password_encrypted)
            client = ZabbixClient(ds.url, ds.username, password)

            for gid in NETWORK_GROUP_IDS:
                try:
                    result = await client._call("hostgroup.get", {
                        "groupids": [gid],
                        "output": ["groupid", "name"],
                        "selectHosts": ["hostid", "host", "name"],
                    })
                    if result:
                        for h in result[0].get("hosts", []):
                            network_host_ids.add(h["hostid"])
                except Exception:
                    pass

            break  # 只需第一个数据源
        except Exception as e:
            print(f"[AGGREGATOR] Failed to query host groups for ds '{ds.name}': {e}")

    return network_host_ids


async def _build_network_devices(
    datasources: list, interface_errors: dict, system_info: dict,
    hosts: list, ping_status: dict, top_network_in: list, top_network_out: list,
    host_metrics: dict
) -> dict:
    """
    构建网络设备监控数据（仅包含 Zabbix 主机组中的网络设备）：
    - device_categories: 按主机名/SNMP 识别类型
    - vendor_distribution: 按 SNMP sysDescr / hostname 识别厂商
    - crc_errors_top10: 接口错误 TOP 10
    - network_summary: 网络设备汇总统计
    """
    from utils.crypto import decrypt_password

    # ── 从 Zabbix 主机组查询网络设备 ID ──
    network_host_ids = await _get_network_host_ids(datasources)
    print(f"[AGGREGATOR] Network host IDs from groups: {network_host_ids}")

    # 建立 hostid → hostname 映射（仅网络设备）
    hostid_to_name = {}
    hostid_to_host = {}
    network_online = 0
    network_offline = 0
    for h in hosts:
        hostid = h.get("hostid", "")
        if hostid not in network_host_ids:
            continue
        name = h.get("name") or h.get("host", "unknown")
        hostid_to_name[hostid] = name
        hostid_to_host[hostid] = h.get("host", "unknown")
        # 在线状态
        if ping_status.get(hostid, True):
            network_online += 1
        else:
            network_offline += 1

    # 网络主机标识符集合：包含 host 字段（如 "192.168.1.81"）和 name 字段（如 "核心交换机"）
    # 因为不同数据源使用不同字段作为主机标识
    network_hostnames_all = set(hostid_to_host.values()) | set(hostid_to_name.values())

    # ── 1. 设备分类（仅网络设备）──
    device_categories = _build_device_categories(hostid_to_name, system_info, interface_errors)

    # ── 2. 厂商分布（仅网络设备）──
    vendor_distribution = _build_vendor_distribution(system_info, hostid_to_name)

    # ── 3. CRC 错误 TOP 10（仅网络设备）──
    crc_errors_top10 = _build_crc_errors_top10(interface_errors, hostid_to_name)

    # ── 4. 端口流量 TOP 10（仅网络设备）──
    port_traffic_top10 = _build_port_traffic_top10(
        top_network_in, top_network_out, interface_errors, network_hostnames_all
    )

    # 将 port traffic 中的 host 字段映射为显示名称
    # hostid_to_host: hostid → "192.168.1.81", hostid_to_name: hostid → "核心交换机"
    host_to_display = {hostid_to_host[hid]: hostid_to_name[hid] for hid in hostid_to_host if hid in hostid_to_name}
    for item in port_traffic_top10:
        item["device"] = host_to_display.get(item["device"], item["device"])

    # ── 5. 端口利用率 TOP 10 ──
    port_util_top10 = _build_port_util_top10(port_traffic_top10, host_metrics)
    # 同样映射 util 中的名称
    for item in port_util_top10:
        item["device"] = host_to_display.get(item["device"], item["device"])

    # ── 6. 网络设备汇总 ──
    total_traffic = sum(x.get("total_mbps", 0) for x in port_traffic_top10)
    network_summary = {
        "total_devices": len(hostid_to_name),
        "online_devices": network_online,
        "offline_devices": network_offline,
        "total_traffic_mbps": round(total_traffic, 2),
    }

    return {
        "device_categories": device_categories,
        "vendor_distribution": vendor_distribution,
        "crc_errors_top10": crc_errors_top10,
        "port_traffic_top10": port_traffic_top10,
        "port_util_top10": port_util_top10,
        "network_summary": network_summary,
        "network_hosts": list(network_hostnames_all),
    }


def _build_device_categories(hostid_to_name: dict, system_info: dict, interface_errors: dict) -> list[dict]:
    """
    根据主机名/SNMP信息识别设备类型。
    仅处理网络设备（有 SNMP system.descr 数据或接口错误监控的主机）。
    """
    categories = {
        "核心交换机": {"icon": "🛰️", "total": 0, "up": 0, "down": 0, "alerts": 0},
        "汇聚交换机": {"icon": "🔀", "total": 0, "up": 0, "down": 0, "alerts": 0},
        "接入交换机": {"icon": "🔌", "total": 0, "up": 0, "down": 0, "alerts": 0},
        "防火墙":     {"icon": "🛡️", "total": 0, "up": 0, "down": 0, "alerts": 0},
        "路由器":     {"icon": "🌐", "total": 0, "up": 0, "down": 0, "alerts": 0},
        "其他设备":   {"icon": "📡", "total": 0, "up": 0, "down": 0, "alerts": 0},
    }

    for hostid, name in hostid_to_name.items():
        # 仅处理网络设备：有 SNMP system info 条目（即使值为空也说明配置了 SNMP 监控）
        sys_info = system_info.get(hostid, {})
        has_snmp = bool(sys_info.get("descr") or sys_info.get("name") or sys_info.get("model"))
        has_snmp_config = hostid in system_info  # 配置了 SNMP 监控但可能暂时无响应
        has_if_errors = bool(interface_errors.get(hostid))

        if not has_snmp and not has_if_errors and not has_snmp_config:
            continue

        # 按 SNMP sysDescr 和主机名关键字分类
        descr = (sys_info.get("descr", "") or "").lower()
        name_lower = name.lower()

        if "ce128" in descr or "核心" in name or "core" in name_lower:
            cat = "核心交换机"
        elif "汇聚" in name or "agg" in name_lower:
            cat = "汇聚交换机"
        elif "接入" in name or "access" in name_lower or "acc" in name_lower:
            cat = "接入交换机"
        elif "防火墙" in name or "firewall" in name_lower or "fw" in name_lower:
            cat = "防火墙"
        elif "路由" in name or "router" in name_lower:
            cat = "路由器"
        elif "交换" in name or "switch" in name_lower:
            cat = "接入交换机"
        else:
            # 即使无法细分，也归类为"其他设备"（网络类）
            cat = "其他设备"

        categories[cat]["total"] += 1
        categories[cat]["up"] += 1

    # 只返回有设备的分类
    return [
        {"name": k, "icon": v["icon"], "total": v["total"],
         "up": v["up"], "down": v["down"], "alerts": v["alerts"]}
        for k, v in categories.items() if v["total"] > 0
    ]


def _build_vendor_distribution(system_info: dict, hostid_to_name: dict) -> list[dict]:
    """
    从 SNMP sysDescr / system.name 识别厂商。
    仅处理有 SNMP 系统信息的主机（网络设备）。
    """
    VENDOR_KEYWORDS = [
        ("华为", ["huawei", "hw"], "#f5222d"),
        ("H3C", ["h3c", "comware"], "#fa8c16"),
        ("思科", ["cisco", "ios", "nx-os"], "#1890ff"),
        ("锐捷", ["ruijie", "锐捷"], "#52c41a"),
        ("Juniper", ["juniper", "junos"], "#7b61ff"),
        ("F5", ["f5", "big-ip"], "#00e5ff"),
        ("其他", [], "#6b89a3"),
    ]

    vendor_counts = {}
    classified = set()

    for hostid, name in hostid_to_name.items():
        info = system_info.get(hostid, {})
        descr = (info.get("descr", "") or "").lower()
        sys_name = (info.get("name", "") or "").lower()
        hostname_lower = name.lower()

        matched = False
        for vendor_name, keywords, color in VENDOR_KEYWORDS:
            if not keywords:
                continue
            for kw in keywords:
                if kw in descr or kw in sys_name or kw in hostname_lower:
                    vendor_counts[vendor_name] = vendor_counts.get(vendor_name, 0) + 1
                    classified.add(hostid)
                    matched = True
                    break
            if matched:
                break

        if not matched:
            vendor_counts["其他"] = vendor_counts.get("其他", 0) + 1
            classified.add(hostid)

    # 构建输出（含颜色）
    color_map = {v[0]: v[2] for v in VENDOR_KEYWORDS}
    result = []
    for vendor_name, count in sorted(vendor_counts.items(), key=lambda x: -x[1]):
        result.append({
            "name": vendor_name,
            "value": count,
            "color": color_map.get(vendor_name, "#6b89a3"),
        })

    return result


def _build_crc_errors_top10(interface_errors: dict, hostid_to_name: dict) -> list[dict]:
    """从接口错误数据构建 CRC 错误 TOP 10（仅网络设备）"""
    all_ifaces = []

    for hostid, ifaces in interface_errors.items():
        # 跳过非网络设备
        if hostid not in hostid_to_name:
            continue
        hostname = hostid_to_name[hostid]
        for iface, err_data in ifaces.items():
            # 跳过 loopback / mgmt 接口
            if any(skip in iface.lower() for skip in ("loop", "meth", "vlan", "null")):
                continue
            in_err = err_data.get("in_errors", 0)
            out_err = err_data.get("out_errors", 0)
            total = in_err + out_err
            all_ifaces.append({
                "device": hostname,
                "port": iface,
                "errors": int(total),
                "in_errors": int(in_err),
                "out_errors": int(out_err),
                "rate": 0.0,
            })

    # 按总错误数降序
    all_ifaces.sort(key=lambda x: -x["errors"])
    top = all_ifaces[:10]

    return top


def _build_port_traffic_top10(
    top_network_in: list, top_network_out: list,
    interface_errors: dict, network_hostnames: set
) -> list[dict]:
    """从 TOP N 数据构建端口流量 TOP 10（仅网络设备）"""
    out_map = {x["host"]: x["value"] for x in top_network_out}

    result = []
    for item in top_network_in:
        host = item["host"]
        # 跳过非网络设备
        if host not in network_hostnames:
            continue
        in_val = item["value"]
        out_val = out_map.get(host, 0.0)

        port = "auto"
        result.append({
            "device": host,
            "port": port,
            "in_mbps": round(in_val, 2),
            "out_mbps": round(out_val, 2),
            "total_mbps": round(in_val + out_val, 2),
        })

        if len(result) >= 10:
            break

    return result


def _build_port_util_top10(port_traffic: list, host_metrics: dict) -> list[dict]:
    """从端口流量数据构建端口利用率 TOP 10（标准带宽 1000Mbps）"""
    result = []
    for item in port_traffic[:10]:
        # 利用率 = 总流量 / 1000 Mbps * 100（基于千兆端口假设）
        util = min(100, round(item["total_mbps"] / 10 * 100, 1))
        result.append({
            "device": item["device"],
            "port": item["port"],
            "util_pct": util,
            "total_mbps": item["total_mbps"],
        })
    return result


async def upsert_cache(db: AsyncSession, cache_type: str, datasource_id: int | None,
                       data: any, expires: datetime):
    """写入或更新缓存"""
    cache_key = f"{cache_type}_{datasource_id or 'all'}"
    data_json = json.dumps(data, default=str)

    # 查现有记录
    result = await db.execute(
        select(MonitorCache).where(MonitorCache.cache_key == cache_key)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.data_json = data_json
        existing.expires_at = expires
        existing.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        db.add(MonitorCache(
            cache_key=cache_key,
            cache_type=cache_type,
            datasource_id=datasource_id,
            data_json=data_json,
            expires_at=expires,
        ))

    await db.commit()
