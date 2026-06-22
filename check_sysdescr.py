import sqlite3, json, os, urllib.request

# Connect to Zabbix API directly
db = os.environ.get("ZBX_DATA_DIR", "/app/data") + "/zabbixscreen.db"
conn = sqlite3.connect(db)

# Get Zabbix credentials from datasource
r = conn.execute("SELECT url, username, password_encrypted FROM datasources WHERE enabled=1").fetchone()
zabbix_url = r[0] + "/api_jsonrpc.php"
username = r[1]

# Get decrypted password - need the crypto module from the backend
import sys
sys.path.insert(0, "/app")
from utils.crypto import decrypt_password
password = decrypt_password(r[2])

# Simple Zabbix JSON-RPC client
def zabbix_call(method, params):
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req = urllib.request.Request(zabbix_url, data=body,
        headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())["result"]

# Login
token = zabbix_call("user.login", {"username": username, "password": password})
print("Logged in:", token[:20], "...")

# Get hosts with system.descr items
items = zabbix_call("item.get", {
    "search": {"key_": "system.descr"},
    "output": ["hostid", "key_", "lastvalue", "name"],
    "limit": 500
})
print("Total system.descr items:", len(items))

# Sample
seen_hids = set()
for item in items[:20]:
    hid = item["hostid"]
    if hid not in seen_hids:
        seen_hids.add(hid)
        print("  hostid=%s key=%s name=%s val=%s" % (
            hid, item["key_"], item["name"][:50],
            (item.get("lastvalue", "") or "")[:80]))

# Count unique hosts with system.descr
unique_hosts = set(i["hostid"] for i in items)
print("\nUnique hosts with system.descr:", len(unique_hosts))

# Check specific keys
key_counts = {}
for item in items:
    k = item["key_"]
    key_counts[k] = key_counts.get(k, 0) + 1
print("\nKey variants:")
for k, c in sorted(key_counts.items()):
    print("  %s: %d" % (k, c))

# Also check: what key is used for system.descr in this Zabbix?
# Try to find the SNMP system description
for item in items[:5]:
    print("\n  Full item:", json.dumps({k: item[k] for k in ["hostid","key_","lastvalue","name","units"]}, ensure_ascii=False))

conn.close()
