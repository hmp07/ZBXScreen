import sqlite3, json, os, urllib.request, struct

db = os.environ.get("ZBX_DATA_DIR", "/app/data") + "/zabbixscreen.db"
conn = sqlite3.connect(db)

r = conn.execute("SELECT url, username, password_encrypted FROM datasources WHERE enabled=1").fetchone()
zabbix_url = r[0] + "/api_jsonrpc.php"

import sys
sys.path.insert(0, "/app")
from utils.crypto import decrypt_password
password = decrypt_password(r[2])

def zabbix_call(method, params):
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req = urllib.request.Request(zabbix_url, data=body,
        headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req).read()
    data = json.loads(resp)
    if "error" in data:
        print("Zabbix error:", json.dumps(data["error"], ensure_ascii=False)[:300])
        return None
    return data.get("result", {})

# Login
token = zabbix_call("user.login", {"username": r[1], "password": password})
print("Token:", str(token)[:20] if token else "FAILED")

if not token:
    print("Login failed!")
    conn.close()
    exit()

# Get ALL items with system.descr - try different search approaches
# First, try wildcard search
items = zabbix_call("item.get", {
    "search": {"key_": "system.descr"},
    "searchWildcardsEnabled": True,
    "output": ["hostid", "key_", "lastvalue", "name"],
    "limit": 500
})

if items is None:
    # Try without searchWildcards
    items = zabbix_call("item.get", {
        "search": {"key_": "system.descr"},
        "output": ["hostid", "key_", "lastvalue", "name"],
        "limit": 500
    })

if items is None or len(items) == 0:
    print("No items found with key_ search. Trying different approach...")
    # Get all items and filter
    all_items = zabbix_call("item.get", {
        "output": ["hostid", "key_", "lastvalue", "name"],
        "limit": 10000
    })
    if all_items:
        items = [i for i in all_items if "system.descr" in i.get("key_", "")]
        print("Total items: %d, matched system.descr: %d" % (len(all_items), len(items)))

if items:
    print("Found %d system.descr items" % len(items))
    # Show unique key variants
    keys = {}
    for i in items:
        k = i["key_"]
        keys[k] = keys.get(k, 0) + 1
    for k, c in sorted(keys.items()):
        print("  key=%s count=%d" % (k, c))

    # Show samples
    for i in items[:5]:
        print("  hostid=%s key=%s val=%s" % (
            i["hostid"], i["key_"],
            str(i.get("lastvalue", ""))[:80]))
else:
    print("No system.descr items at all!")

conn.close()
