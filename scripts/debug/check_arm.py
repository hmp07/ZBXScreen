import sqlite3, json, os
db = os.environ.get("ZBX_DATA_DIR", "/app/data") + "/zabbixscreen.db"
conn = sqlite3.connect(db)

r = conn.execute("SELECT data_json FROM monitor_cache WHERE cache_key='summary_all'").fetchone()
if r:
    s = json.loads(r[0])
    print("SUMMARY: total=%s online=%s offline=%s alerts=%s" % (
        s.get("total_hosts","?"), s.get("online_hosts","?"),
        s.get("offline_hosts","?"), s.get("alert_count","?")))

for key in ["top_cpu_all", "top_memory_all", "top_network_in_all", "top_network_out_all"]:
    r = conn.execute("SELECT data_json FROM monitor_cache WHERE cache_key='%s'" % key).fetchone()
    if r:
        data = json.loads(r[0])
        print("%s: %d items" % (key, len(data)))
        for x in data[:5]:
            print("  %s = %s" % (x.get("host","?"), x.get("value","?")))

r = conn.execute("SELECT data_json FROM monitor_cache WHERE cache_key='hosts_all'").fetchone()
if r:
    hosts = json.loads(r[0])
    print("HOSTS: %d total" % len(hosts))
    for h in hosts[:5]:
        ifaces = h.get("interfaces", [])
        avail_info = ""
        for i in ifaces:
            avail_info += " type=%s avail=%s" % (i.get("type","?"), i.get("available","?"))
        print("  %s (%s): status=%s%s" % (
            h.get("name") or h.get("host","?"), h.get("host","?"),
            h.get("status","?"), avail_info))

conn.close()
