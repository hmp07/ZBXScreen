import sqlite3, json

db = "/opt/zabbixscreen/data/zabbixscreen.db"
c = sqlite3.connect(db)

for key in ["top_network_in_all", "top_network_out_all"]:
    r = c.execute("SELECT data_json FROM monitor_cache WHERE cache_key='" + key + "'").fetchone()
    if r:
        data = json.loads(r[0])
        print(key + ": " + str(len(data)) + " items")
        for x in data:
            print("  " + x["host"] + " = " + str(x["value"]) + " Mbps")

r2 = c.execute("SELECT data_json FROM monitor_cache WHERE cache_key='network_devices_all'").fetchone()
if r2:
    nd = json.loads(r2[0])
    pt = nd.get("port_traffic_top10", [])
    print("\nport_traffic_top10: " + str(len(pt)) + " items")
    for x in pt[:5]:
        print("  device=" + str(x.get("device","?")) + " port=" + str(x.get("port","?")) + " in=" + str(x.get("in_mbps",0)) + " out=" + str(x.get("out_mbps",0)))

c.close()
