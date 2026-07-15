import sqlite3, json, os
db = os.environ.get("ZBX_DATA_DIR", "/app/data") + "/zabbixscreen.db"
conn = sqlite3.connect(db)

# Check host metrics - what keys do hosts have?
r = conn.execute("SELECT data_json FROM monitor_cache WHERE cache_key='host_metrics_all'").fetchone()
hm = json.loads(r[0])
print("HOST_METRICS: %d entries" % len(hm))

# Count hosts with CPU data
with_cpu = 0
without_cpu = 0
cpu_samples = []
no_cpu_samples = []
for k, v in hm.items():
    if "cpu" in v:
        with_cpu += 1
        if len(cpu_samples) < 5:
            cpu_samples.append((k, v))
    else:
        without_cpu += 1
        if len(no_cpu_samples) < 10:
            no_cpu_samples.append((k, v))

print("With CPU: %d, Without CPU: %d" % (with_cpu, without_cpu))
print("\n=== WITH CPU ===")
for k, v in cpu_samples:
    print("  %s: cpu=%s, keys=%s" % (k, v.get("cpu","?"), [kk for kk in v.keys() if kk not in ("hostname","host","hostid","datasource_id")][:5]))
print("\n=== WITHOUT CPU ===")
for k, v in no_cpu_samples:
    print("  %s: keys=%s" % (k, [kk for kk in v.keys() if kk not in ("hostname","host","hostid","datasource_id")][:5]))

# Check hosts_all for online hosts
r2 = conn.execute("SELECT data_json FROM monitor_cache WHERE cache_key='hosts_all'").fetchone()
hosts = json.loads(r2[0])
print("\n=== ONLINE HOSTS (sample) ===")
count = 0
for h in hosts:
    ifaces = h.get("interfaces", [])
    for i in ifaces:
        if str(i.get("available","")) == "1":
            count += 1
            if count <= 5:
                print("  %s (%s): type=%s avail=%s" % (
                    h.get("name") or h.get("host","?"),
                    h.get("host","?"),
                    i.get("type","?"),
                    i.get("available","?")))
            break
print("Total online: %d" % count)

conn.close()
