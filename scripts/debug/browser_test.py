import sqlite3, urllib.request, json

print("=== Simulating browser flow ===")

# Login
body = json.dumps({"username": "admin", "password": "Admin@123"}).encode()
req = urllib.request.Request("http://localhost:8088/api/v1/auth/login", data=body,
    headers={"Content-Type": "application/json"}, method="POST")
token = json.loads(urllib.request.urlopen(req).read())["data"]["access_token"]

# GET current settings
req2 = urllib.request.Request("http://localhost:8088/api/v1/settings",
    headers={"Authorization": "Bearer " + token})
current = json.loads(urllib.request.urlopen(req2).read())["data"]
print("Current title: " + str(current.get("SYSTEM_TITLE","?")))

# PUT new title (EXACT same format as browser sends)
new_data = json.dumps({
    "system_title": "BrowserSimTest",
    "system_subtitle": "",
    "system_logo": "",
    "default_refresh_interval": 30,
    "data_retention_days": 30,
    "theme": "dark",
    "tz": "Asia/Shanghai"
}).encode()
req3 = urllib.request.Request("http://localhost:8088/api/v1/settings", data=new_data,
    headers={"Content-Type": "application/json", "Authorization": "Bearer " + token}, method="PUT")
resp3 = json.loads(urllib.request.urlopen(req3).read())
print("PUT response: code=" + str(resp3.get("code")) + " " + str(resp3.get("message","")))

# GET again to verify
req4 = urllib.request.Request("http://localhost:8088/api/v1/settings",
    headers={"Authorization": "Bearer " + token})
after = json.loads(urllib.request.urlopen(req4).read())["data"]
print("After PUT title: " + str(after.get("SYSTEM_TITLE","?")))

# Public endpoint
pub = json.loads(urllib.request.urlopen("http://localhost:8088/api/v1/settings/public").read())
print("Public title: " + str(pub["data"]["title"]))

# Check DB
c = sqlite3.connect("/opt/zabbixscreen/data/zabbixscreen.db")
r = c.execute("SELECT value FROM settings WHERE key='SYSTEM_TITLE'").fetchone()
print("DB title: " + str(r[0] if r else "NOT FOUND"))
c.close()

if after.get("SYSTEM_TITLE") == "BrowserSimTest":
    print("\n*** ALL TESTS PASSED ***")
else:
    print("\n*** FAILED ***")
