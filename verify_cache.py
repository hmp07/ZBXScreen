import sqlite3, json, os

db = os.environ.get("ZBX_DATA_DIR", "/app/data") + "/zabbixscreen.db"
conn = sqlite3.connect(db)

for key in ["top_cpu_all", "top_memory_all", "top_network_in_all", "top_network_out_all"]:
    r = conn.execute("SELECT data_json FROM monitor_cache WHERE cache_key='" + key + "'").fetchone()
    if r:
        data = json.loads(r[0])
        n = len(data)
        print(key + ": " + str(n) + " items")
        for x in data[:3]:
            print("  " + x.get("host", "?") + " = " + str(x.get("value", "?")))

# Summary
r = conn.execute("SELECT data_json FROM monitor_cache WHERE cache_key='summary_all'").fetchone()
if r:
    s = json.loads(r[0])
    print("Summary: total=" + str(s.get("total_hosts","?")) + " online=" + str(s.get("online_hosts","?")))

conn.close()
