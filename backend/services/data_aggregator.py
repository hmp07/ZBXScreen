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
        host_metrics_by_id = {}  # "{datasource_id}:{hostid}" → {hostname, host, metrics...}
        all_ping_status = {}   # hostid → bool (hostinterface.available 判断)
        all_interface_errors = {}  # hostid → {iface: {in_errors, out_errors, ...}}
        all_interface_traffic = {}  # hostid → {iface: {in_mbps, out_mbps}}
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
            hostid_to_host = {}
            for h in hosts_data:
                hid = h.get("hostid", "")
                hostid_to_name[hid] = h.get("name") or h.get("host", "unknown")
                hostid_to_host[hid] = h.get("host", hid)

            for hostid, metrics in item_metrics.items():
                hostname = hostid_to_name.get(hostid, hostid)
                host = hostid_to_host.get(hostid, hostid)
                if hostname not in all_host_metrics:
                    all_host_metrics[hostname] = metrics
                # 按 {datasource_id}:{hostid} 存储，供主机详情 API 缓存查询
                cache_key = f"{ds.id}:{hostid}"
                host_metrics_by_id[cache_key] = {
                    "hostname": hostname,
                    "host": host,
                    "hostid": hostid,
                    "datasource_id": ds.id,
                    **metrics,
                }

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

            # 合并接口流量（per-interface traffic）
            iface_traffic = result.get("interface_traffic", {})
            for hostid, ifaces in iface_traffic.items():
                if hostid not in all_interface_traffic:
                    all_interface_traffic[hostid] = {}
                for iface, traffic in ifaces.items():
                    if iface not in all_interface_traffic[hostid]:
                        all_interface_traffic[hostid][iface] = traffic
                    else:
                        # 同接口取最大值（不同数据源可能有不同精度）
                        existing = all_interface_traffic[hostid][iface]
                        existing["in_mbps"] = max(existing.get("in_mbps", 0), traffic.get("in_mbps", 0))
                        existing["out_mbps"] = max(existing.get("out_mbps", 0), traffic.get("out_mbps", 0))

        # 跨数据源去重（按 hostname）
        seen = set()
        deduped_hosts = []
        for h in all_hosts:
            key = h.get("host", h.get("name", ""))
            if key not in seen:
                seen.add(key)
                deduped_hosts.append(h)

        # ── 补全主机组信息（Zabbix 7.x selectGroups 受限，改用 hostgroup.get）──
        hostid_to_groups = await _fetch_host_groups_map(datasources)
        for h in deduped_hosts:
            hid = h.get("hostid", "")
            if hid in hostid_to_groups:
                h["groups"] = hostid_to_groups[hid]

        # 通过 hostinterface.available 判断在线/离线状态
        offline_hostnames = set()
        online_count = 0
        offline_count = 0
        for h in deduped_hosts:
            hostid = h.get("hostid", "")
            # 使用 name 字段（优先）作为主机标识，与 all_host_metrics 的 key 保持一致
            hostname = h.get("name") or h.get("host", "")
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
            deduped_hosts, all_ping_status, top_network_in, top_network_out,
            all_host_metrics, all_interface_traffic
        )

        # ── 从服务器 TOP N 排行中排除网络设备主机 ──
        net_hostnames = set(network_devices.get("network_hosts", []))
        top_cpu = [x for x in top_cpu if x["host"] not in net_hostnames]
        top_memory = [x for x in top_memory if x["host"] not in net_hostnames]
        top_disk = [x for x in top_disk if x["host"] not in net_hostnames]
        top_network_in = [x for x in top_network_in if x["host"] not in net_hostnames]
        top_network_out = [x for x in top_network_out if x["host"] not in net_hostnames]

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
        await upsert_cache(db, "host_metrics", None, host_metrics_by_id, expires)

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
        memory_cache.set("hosts_all", deduped_hosts, settings.default_refresh_interval)
        memory_cache.set("top_cpu", top_cpu, settings.default_refresh_interval)
        memory_cache.set("top_memory", top_memory, settings.default_refresh_interval)
        memory_cache.set("top_disk", top_disk, settings.default_refresh_interval)
        memory_cache.set("top_network_in", top_network_in, settings.default_refresh_interval)
        memory_cache.set("top_network_out", top_network_out, settings.default_refresh_interval)
        memory_cache.set("network_devices", network_devices, settings.default_refresh_interval)
        memory_cache.set("host_metrics_all", host_metrics_by_id, settings.default_refresh_interval)


async def fetch_datasource_data(ds: Datasource) -> dict:
    """拉取单个数据源的主机数据、告警计数和 item-level 指标（含 ping 状态）"""
    try:
        password = decrypt_password(ds.password_encrypted)
        client = ZabbixClient(ds.url, ds.username, password)

        # 获取主机列表
        hosts = await client.get_hosts()

        # 获取活跃触发器数量
        triggers = await client.get_triggers(active_only=True)

        # 一次性获取所有 items，同时提取 metrics + 网络接口错误 + 系统信息 + 接口流量
        hostids = [h.get("hostid") for h in hosts if h.get("hostid")]
        item_metrics, _, interface_errors, system_info, interface_traffic = await _fetch_item_data(client, hostids)

        # 通过 hostinterface.available 判断在线状态（替代 agent.ping）
        ping_status = _build_online_status(hosts)

        return {
            "hosts": hosts,
            "alert_count": len(triggers),
            "item_metrics": item_metrics,
            "ping_status": ping_status,
            "interface_errors": interface_errors,
            "system_info": system_info,
            "interface_traffic": interface_traffic,
        }
    except ZabbixAPIError as e:
        print(f"[AGGREGATOR] Zabbix error for '{ds.name}': {e}")
        return {"hosts": [], "alert_count": 0, "item_metrics": {}, "ping_status": {},
                "interface_errors": {}, "system_info": {}, "interface_traffic": {}}
    except Exception as e:
        print(f"[AGGREGATOR] Unexpected error for '{ds.name}': {e}")
        return {"hosts": [], "alert_count": 0, "item_metrics": {}, "ping_status": {},
                "interface_errors": {}, "system_info": {}, "interface_traffic": {}}


def _build_online_status(hosts: list) -> dict:
    """
    通过 hostinterface 的 type + available 判断主机在线状态。
    Zabbix hostinterface.type: 1=agent, 2=SNMP, 3=IPMI, 4=JMX
    hostinterface.available: 0=unknown, 1=available, 2=unavailable

    规则：主接口 available=1 为在线，否则为离线。
    无接口信息的主机默认视为在线。
    """
    online_status = {}
    for h in hosts:
        hostid = h.get("hostid", "")
        if not hostid:
            continue
        interfaces = h.get("interfaces", [])
        if not interfaces:
            # 无接口信息，默认在线
            online_status[hostid] = True
            continue

        # 优先检查主接口 (main=1)
        main_iface = None
        for iface in interfaces:
            if iface.get("main") == "1" or iface.get("main") == 1:
                main_iface = iface
                break
        if main_iface is None:
            # 无主接口，取第一个
            main_iface = interfaces[0]

        avail = main_iface.get("available", "0")
        try:
            avail = int(avail) if isinstance(avail, str) else avail
        except (ValueError, TypeError):
            avail = 0

        # available=0(unknown): 初始状态，假设在线（仅排除 confirmed unavailable）
        # available=1(available): 确认在线
        # available=2(unavailable): 确认离线
        online_status[hostid] = (avail != 2)

    return online_status


async def _fetch_item_data(client: ZabbixClient, hostids: list[str]) -> tuple[dict, dict, dict, dict, dict]:
    """
    一次性拉取所有 items，提取指标数据、网络接口错误、系统信息和接口流量。
    （在线状态检测已移至 _build_online_status，基于 hostinterface.available 判断）
    避免重复 API 调用。
    返回: (host_metrics, _unused, interface_errors, system_info, interface_traffic)
      host_metrics: {hostid: {cpu, memory, disk, network_in, network_out}}
      interface_errors: {hostid: {iface_name: {in_errors, out_errors, in_discards, out_discards}}}
      system_info: {hostid: {descr, name, model, serial}}
      interface_traffic: {hostid: {iface_name: {in_mbps, out_mbps}}}
    """
    import re

    if not hostids:
        return {}, {}, {}, {}, {}

    try:
        items = await client.get_items(hostids=hostids)
    except ZabbixAPIError:
        return {}, {}, {}, {}, {}

    host_metrics = {}
    ping_status = {}
    # interface_errors: {hostid: {iface_name: {in_errors, out_errors, in_discards, out_discards}}}
    interface_errors = {}
    # interface_traffic: {hostid: {iface_name: {in_mbps, out_mbps}}}
    interface_traffic = {}
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

        # 跳过从未采集到数据的 item（lastclock=0 表示 host 离线/未响应）
        try:
            lc = int(item.get("lastclock", "0") or "0")
        except (ValueError, TypeError):
            lc = 0
        if lc == 0:
            continue

        # --- 指标值提取 ---
        try:
            val = float(item.get("lastvalue", "0"))
        except (ValueError, TypeError):
            val = 0.0

        if hostid not in host_metrics:
            host_metrics[hostid] = {}

        if "cpu" in key and "util" in key:
            # system.cpu.util[,idle] → val=idle% → usage = 100 - val
            # system.cpu.util (bare, no params) → val=usage% → usage = val
            # SNMP device keys: system.cpu.util[hwEntityCpuUsage.N] → don't match idle
            if "idle" in key:
                host_metrics[hostid]["cpu"] = round(100.0 - val, 1)
            elif "cpu" not in host_metrics[hostid]:
                # Fallback: bare system.cpu.util (no idle param) = direct utilization
                # Only set if no [,idle] variant was already processed
                host_metrics[hostid]["cpu"] = round(val, 1)
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
            # Zabbix net.if.in items use units=bps, value is already in bits/sec
            host_metrics[hostid]["network_in"] = round(val / 1_000_000, 2)
            # 同时记录 per-interface 流量（用于网络大屏端口流量图表）
            if hostid not in interface_traffic:
                interface_traffic[hostid] = {}
            iface = _parse_iface(name, key)
            if iface not in interface_traffic[hostid]:
                interface_traffic[hostid][iface] = {}
            interface_traffic[hostid][iface]["in_mbps"] = round(val / 1_000_000, 2)
        elif "net.if.out" in key and "lo" not in key and "error" not in key and "discard" not in key:
            host_metrics[hostid]["network_out"] = round(val / 1_000_000, 2)
            if hostid not in interface_traffic:
                interface_traffic[hostid] = {}
            iface = _parse_iface(name, key)
            if iface not in interface_traffic[hostid]:
                interface_traffic[hostid][iface] = {}
            interface_traffic[hostid][iface]["out_mbps"] = round(val / 1_000_000, 2)

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

    return host_metrics, ping_status, interface_errors, system_info, interface_traffic


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


async def _fetch_host_groups_map(datasources: list) -> dict:
    """
    通过 hostgroup.get(selectHosts) 构建 hostid → [{"groupid":..., "name":...}] 映射。
    Zabbix 7.x 中 host.get 的 selectGroups 可能因权限受限返回空，
    但 hostgroup.get 配合 selectHosts 可正常获取组成员关系。
    """
    from utils.crypto import decrypt_password

    hostid_to_groups = {}

    for ds in datasources:
        try:
            password = decrypt_password(ds.password_encrypted)
            client = ZabbixClient(ds.url, ds.username, password)
            # 一次性获取所有主机组及其成员主机
            result = await client._call("hostgroup.get", {
                "selectHosts": ["hostid"],
            })
            for g in result:
                gid = g.get("groupid", "")
                gname = g.get("name", "")
                for h in g.get("hosts", []):
                    hid = h["hostid"]
                    if hid not in hostid_to_groups:
                        hostid_to_groups[hid] = []
                    hostid_to_groups[hid].append({"groupid": gid, "name": gname})
        except Exception as e:
            print(f"[AGGREGATOR] Failed to fetch host groups for ds '{ds.name}': {e}")

    return hostid_to_groups


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
    host_metrics: dict, interface_traffic: dict = None
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

    # ── 4. 端口流量 TOP 10（per-interface，仅网络设备）──
    if interface_traffic is None:
        interface_traffic = {}
    port_traffic_top10 = _build_network_port_traffic(
        interface_traffic, hostid_to_name, hostid_to_host, network_hostnames_all
    )

    # ── 5. 端口利用率 TOP 10 ──
    port_util_top10 = _build_port_util_top10(port_traffic_top10)

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
    SNMP 设备以 system.descr 为主要判断依据，将英文厂商名映射为中文显示名。
    非 SNMP 设备以主机名关键字作为辅助判断。
    """
    # 厂商识别规则：(中文显示名, system.descr 匹配关键词, hostname 匹配关键词, 颜色)
    VENDOR_RULES = [
        ("华为技术有限公司",     ["huawei", "vrp", "ce12800", "s5700", "s6700", "s12700",
                                 "ne40e", "ne20e", "ar2200", "ar3200"],
                                ["华为", "huawei", "hw-"],           "#f5222d"),
        ("新华三技术有限公司",   ["h3c", "comware", "s12500", "s10500", "s7500", "s5500",
                                 "msr", "sr6600", "secpath"],
                                ["h3c", "h3c-"],                    "#fa8c16"),
        ("思科系统公司",         ["cisco", "ios", "nx-os", "ios-xe", "ios-xr",
                                 "nexus", "catalyst", "asa", "isr"],
                                ["cisco", "思科"],                  "#1890ff"),
        ("锐捷网络股份有限公司", ["ruijie", "rgos", "rg-s", "rg-n"],
                                ["ruijie", "ruiji", "锐捷", "rg-"], "#52c41a"),
        ("瞻博网络",             ["juniper", "junos", "ex-series", "mx-series", "qfx"],
                                ["juniper", "junos", "瞻博"],       "#7b61ff"),
        ("F5 Networks",          ["f5 networks", "big-ip", "bigip"],
                                ["f5", "bigip"],                    "#00e5ff"),
        ("戴尔科技集团",         ["dell", "force10", "powerconnect"],
                                ["dell"],                           "#13c2c2"),
        ("Arista Networks",      ["arista", "eos"],
                                ["arista"],                         "#eb2f96"),
        ("飞塔信息",             ["fortinet", "fortigate", "fortiwifi"],
                                ["fortinet", "forti"],              "#ee3f4d"),
        ("Palo Alto Networks",   ["palo alto", "pan-os"],
                                ["paloalto", "pa-"],                "#fa541c"),
        ("深信服科技",           ["sangfor"],
                                ["深信服", "sangfor"],              "#2f54eb"),
    ]

    # 构建关键词→(厂商名, 颜色) 的快速查找表
    descr_kw_map = {}   # system.descr 关键词
    host_kw_map = {}    # hostname 关键词
    vendor_colors = {}
    for vendor_name, descr_keywords, host_keywords, color in VENDOR_RULES:
        vendor_colors[vendor_name] = color
        for kw in descr_keywords:
            descr_kw_map[kw] = (vendor_name, color)
        for kw in host_keywords:
            host_kw_map[kw] = (vendor_name, color)

    vendor_counts = {}

    for hostid, name in hostid_to_name.items():
        info = system_info.get(hostid, {})
        descr = (info.get("descr", "") or "").lower()
        sys_name = (info.get("name", "") or "").lower()
        hostname_lower = name.lower()

        matched_vendor = None

        # 1. 优先从 system.descr 识别（SNMP 设备的准确来源）
        if descr:
            for kw, (vendor_name, _) in descr_kw_map.items():
                if kw in descr:
                    matched_vendor = vendor_name
                    break

        # 2. system.descr 未命中时，检查 system.name
        if not matched_vendor and sys_name:
            for kw, (vendor_name, _) in descr_kw_map.items():
                if kw in sys_name:
                    matched_vendor = vendor_name
                    break

        # 3. 仍未命中时，通过主机名辅助识别
        if not matched_vendor:
            for kw, (vendor_name, _) in host_kw_map.items():
                if kw in hostname_lower:
                    matched_vendor = vendor_name
                    break

        # 4. 无法识别
        if not matched_vendor:
            matched_vendor = "其他"

        vendor_counts[matched_vendor] = vendor_counts.get(matched_vendor, 0) + 1

    # 构建输出
    result = []
    for vendor_name, count in sorted(vendor_counts.items(), key=lambda x: -x[1]):
        result.append({
            "name": vendor_name,
            "value": count,
            "color": vendor_colors.get(vendor_name, "#6b89a3"),
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


def _build_network_port_traffic(
    interface_traffic: dict, hostid_to_name: dict, hostid_to_host: dict,
    network_hostnames: set
) -> list[dict]:
    """从 per-interface 流量数据筛选网络设备接口，按总流量排序取 TOP 10"""
    # 构建 hostid → display_name 映射
    host_to_display = {}
    for hid in hostid_to_name:
        host_to_display[hid] = hostid_to_name[hid]

    entries = []
    for hostid, ifaces in interface_traffic.items():
        # 跳过非网络设备
        if hostid not in hostid_to_name:
            continue
        device_name = hostid_to_name[hostid]
        for iface, traffic in ifaces.items():
            in_mbps = traffic.get("in_mbps", 0)
            out_mbps = traffic.get("out_mbps", 0)
            total = round(in_mbps + out_mbps, 2)
            entries.append({
                "device": device_name,
                "port": iface,
                "in_mbps": in_mbps,
                "out_mbps": out_mbps,
                "total_mbps": total,
            })

    entries.sort(key=lambda x: x["total_mbps"], reverse=True)
    return entries[:10]


def _build_port_util_top10(port_traffic: list) -> list[dict]:
    """从端口流量数据构建端口利用率 TOP 10（基准带宽 1000Mbps）"""
    result = []
    for item in port_traffic[:10]:
        # 利用率 = 总流量(Mbps) / 1000(Mbps) * 100
        util = min(100, round(item["total_mbps"] / 1000 * 100, 1))
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
