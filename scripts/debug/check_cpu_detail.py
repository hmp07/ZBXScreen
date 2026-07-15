import sqlite3, json, os

db_path = os.environ.get("ZBX_DATA_DIR", "/app/data") + "/zabbixscreen.db"
conn = sqlite3.connect(db_path)

# Get our TOP CPU
r = conn.execute("SELECT data_json FROM monitor_cache WHERE cache_key='top_cpu_all'").fetchone()
our_cpu = json.loads(r[0])
print("Our CPU TOP 5:")
for x in our_cpu[:5]:
    print("  %s = %s%%" % (x["host"], x["value"]))

# Get memory TOP for comparison
r = conn.execute("SELECT data_json FROM monitor_cache WHERE cache_key='top_memory_all'").fetchone()
our_mem = json.loads(r[0])
print("\nOur Memory TOP 5:")
for x in our_mem[:5]:
    print("  %s = %s%%" % (x["host"], x["value"]))

# Get host_metrics for sample
r = conn.execute("SELECT data_json FROM monitor_cache WHERE cache_key='host_metrics_all'").fetchone()
hm = json.loads(r[0])

# Get hosts
r = conn.execute("SELECT data_json FROM monitor_cache WHERE cache_key='hosts_all'").fetchone()
hosts = json.loads(r[0])

# build name->hostid mapping
name_to_hid = {}
for h in hosts:
    name_to_hid[h.get("name") or h.get("host","")] = h.get("hostid","")

print("\nDetails for our CPU TOP 5:")
for item in our_cpu[:5]:
    hname = item["host"]
    hid = name_to_hid.get(hname, "")
    if hid:
        for k, v in list(hm.items()):
            if k.endswith(":" + hid):
                keys = [kk for kk in v.keys() if kk not in ("hostname","host","hostid","datasource_id")]
                print("  %s (hid=%s): cpu=%s, keys=%s" % (hname, hid, v.get("cpu","?"), keys))
                break

conn.close()
