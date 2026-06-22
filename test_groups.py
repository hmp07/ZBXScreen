import sys, json
sys.path.insert(0, "/opt/zabbixscreen/backend")
import asyncio
from database import AsyncSessionLocal
from sqlalchemy import select
from models.datasource import Datasource
from utils.crypto import decrypt_password
from services.zabbix_client import ZabbixClient

async def main():
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(Datasource).where(Datasource.enabled == True))
        ds = r.scalars().all()[0]
        pw = decrypt_password(ds.password_encrypted)
        client = ZabbixClient(ds.url, ds.username, pw)

        result = await client._call("hostgroup.get", {
            "selectHosts": ["hostid"],
        })
        print("Groups returned:", len(result))
        hostid_to_groups = {}
        for g in result:
            gname = g.get("name", "")
            hosts = g.get("hosts", [])
            if hosts:
                print(" ", gname + ":", len(hosts), "hosts")
                for h in hosts[:2]:
                    hid = h["hostid"]
                    if hid not in hostid_to_groups:
                        hostid_to_groups[hid] = []
                    hostid_to_groups[hid].append(gname)
        print("hostid_to_groups:", len(hostid_to_groups), "hosts")
        for hid, gnames in list(hostid_to_groups.items())[:5]:
            print(" ", hid + ":", gnames)
asyncio.run(main())
