import urllib.request, json

def api(method, path, data=None):
    url = "http://localhost:5001" + path
    headers = {"Content-Type": "application/json"}
    if data:
        body = json.dumps(data).encode()
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)
    return json.loads(urllib.request.urlopen(req))

login = api("POST", "/api/v1/auth/login", {"username": "admin", "password": "Admin@123"})
token = login["data"]["access_token"]

def auth_get(path):
    req = urllib.request.Request("http://localhost:5001" + path, headers={"Authorization": "Bearer " + token})
    return json.loads(urllib.request.urlopen(req))

# Network dashboard
nd = auth_get("/api/v1/network/dashboard")["data"]
print("=== Port Traffic (per-interface) ===")
pt = nd.get("port_traffic_top10", [])
print("Items:", len(pt))
for x in pt[:8]:
    print("  %s | %s: in=%.2f out=%.2f total=%.2f" % (
        x.get("device","?"), x.get("port","?"),
        x.get("in_mbps",0), x.get("out_mbps",0), x.get("total_mbps",0)))

print("")
print("=== Port Util ===")
pu = nd.get("port_util_top10", [])
print("Items:", len(pu))
for x in pu[:5]:
    print("  %s | %s: util=%s%%" % (x.get("device","?"), x.get("port","?"), x.get("util_pct",0)))

print("")
print("=== CRC Errors ===")
crc = nd.get("crc_errors_top10", [])
print("Items:", len(crc))
for x in crc[:3]:
    print("  %s | %s: errors=%s" % (x.get("device","?"), x.get("port","?"), x.get("errors",0)))

# Host list
hl = auth_get("/api/v1/hosts?page=1&page_size=30")["data"]
print("")
print("=== Host List ===")
print("Total: %d, Page: %d, PageSize: %d" % (hl.get("total",0), hl.get("page",0), hl.get("page_size",0)))
items = hl.get("items", [])
if items:
    h = items[0]
    print("First host: %s name=%s" % (h.get("host","?"), h.get("name","?")))
    groups = h.get("groups", [])
    names = [g.get("name","?") for g in groups[:5]]
    print("Groups (%d): %s" % (len(groups), names))
