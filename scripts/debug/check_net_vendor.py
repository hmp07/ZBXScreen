import sqlite3, json, os

db = os.environ.get("ZBX_DATA_DIR", "/app/data") + "/zabbixscreen.db"
conn = sqlite3.connect(db)

# Current network data
r = conn.execute("SELECT data_json FROM monitor_cache WHERE cache_key='network_devices_all'").fetchone()
nd = json.loads(r[0])
print("=== Current Vendors ===")
for v in nd.get("vendor_distribution", []):
    print("  %s: %s devices" % (v["name"], v["value"]))
print("\n=== Device Categories ===")
for c in nd.get("device_categories", []):
    print("  %s: %s total" % (c["name"], c["total"]))

# Network hostnames
net_hosts = set(nd.get("network_hosts", []))
print("\nNetwork hostnames: %d" % len(net_hosts))

# Check system_info in network_devices data
# The system_info from aggregation might not be in the cache
# Let's check host_metrics for the network device keys
r2 = conn.execute("SELECT data_json FROM monitor_cache WHERE cache_key='host_metrics_all'").fetchone()
hm = json.loads(r2[0])

# Check hosts with system.descr data by looking at network device IDs
# The network_host_ids in the aggregator code determines which hosts are network devices
r3 = conn.execute("SELECT data_json FROM monitor_cache WHERE cache_key='hosts_all'").fetchone()
hosts = json.loads(r3[0])

# Find all hosts that are network devices and check their info
print("\n=== Network device hosts ===")
for h in hosts:
    hname = h.get("name") or h.get("host", "")
    if hname in net_hosts:
        hid = h.get("hostid", "")
        # Check if this host has system info in network_devices data
        print("  %s (hostid=%s host=%s)" % (hname, hid, h.get("host","?")))
        ifaces = h.get("interfaces", [])
        for i in ifaces:
            print("    iface: type=%s main=%s avail=%s" % (i.get("type","?"), i.get("main","?"), i.get("available","?")))

# Check: are there hosts with SNMP interfaces (type=2) that are NOT in net_hosts?
print("\n=== SNMP hosts NOT in network_hosts? ===")
snmp_not_net = 0
for h in hosts:
    ifaces = h.get("interfaces", [])
    has_snmp = any(str(i.get("type","")) == "2" for i in ifaces)
    hname = h.get("name") or h.get("host", "")
    if has_snmp and hname not in net_hosts:
        snmp_not_net += 1
        if snmp_not_net <= 5:
            print("  %s (hostid=%s)" % (hname, h.get("hostid","")))
print("Total SNMP hosts not in network_hosts: %d" % snmp_not_net)

conn.close()
