import urllib.request, re

req = urllib.request.Request("http://127.0.0.1/integrations/zabbix/zabbix.php")
resp = urllib.request.urlopen(req)
body = resp.read().decode("utf-8", errors="replace")

# Find all input fields in the page
inputs = re.findall(r'<input[^>]+>', body)
print("Input fields on login page:")
for inp in inputs:
    n = re.search(r'name="([^"]+)"', inp)
    t = re.search(r'type="([^"]+)"', inp)
    v = re.search(r'value="([^"]*)"', inp)
    name = n.group(1) if n else '?'
    typ = t.group(1) if t else '?'
    val = v.group(1) if v else '?'
    print(f"  {typ} name={name} value={val[:50]}")

# Check for specific hidden fields
hidden = re.findall(r'<input type="hidden"[^>]+>', body)
print(f"\nHidden fields ({len(hidden)}):")
for h in hidden:
    n = re.search(r'name="([^"]+)"', h)
    print(f"  {n.group(1) if n else '?'}")

# Check for autologin support
if 'autologin' in body.lower():
    print("\nZabbix mentions autologin!")
