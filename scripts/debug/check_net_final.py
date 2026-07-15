import sqlite3, json, os

db = os.environ.get("ZBX_DATA_DIR", "/app/data") + "/zabbixscreen.db"
conn = sqlite3.connect(db)

r = conn.execute("SELECT data_json FROM monitor_cache WHERE cache_key='network_devices_all'").fetchone()
nd = json.loads(r[0])
ns = nd.get("network_summary", {})
print("Network Summary: total=%s online=%s offline=%s traffic=%s Mbps" % (
    ns.get("total_devices","?"), ns.get("online_devices","?"),
    ns.get("offline_devices","?"), ns.get("total_traffic_mbps","?")))

print("\nDevice Categories:")
for c in nd.get("device_categories", []):
    print("  %s: %s total" % (c["name"], c["total"]))

print("\nVendors:")
for v in nd.get("vendor_distribution", []):
    print("  %s: %s" % (v["name"], v["value"]))

print("\nPort Traffic: %d items" % len(nd.get("port_traffic_top10", [])))
print("CRC Errors: %d items" % len(nd.get("crc_errors_top10", [])))
print("Network Hosts: %d" % len(nd.get("network_hosts", [])))
conn.close()
