"""
运维集成 API — Zabbix / iTop 自动登录桥接页
"""
import html
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.datasource import Datasource


from utils.crypto import decrypt_password

router = APIRouter(prefix="/integrations", tags=["运维集成"])

LOGIN_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>正在跳转...</title></head>
<body style="background:#0d1b2e;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
<div style="text-align:center;color:#e6f7ff;font-family:sans-serif">
  <div style="font-size:24px;margin-bottom:16px">{title}</div>
  <div style="font-size:14px;color:#6b89a3">{subtitle}</div>
</div>
<form id="f" action="{action}" method="POST">
  <input type="hidden" name="name" value="{username}">
  <input type="hidden" name="password" value="{password}">
  <input type="hidden" name="enter" value="Sign in">
  {extra_fields}
</form>
<script>
document.getElementById("f").submit();
setTimeout(function(){{ location.href = "{redirect}"; }}, 1200);
</script>
</body>
</html>"""


def _build_login_html(
    title: str,
    subtitle: str,
    action: str,
    username: str,
    password: str,
    redirect: str = "/integrations/zabbix/zabbix.php?action=dashboard.view",
    extra_fields: str = "",
) -> str:
    return LOGIN_PAGE_TEMPLATE.format(
        title=title,
        subtitle=subtitle,
        action=action,
        username=username,
        password=password,
        redirect=redirect,
        extra_fields=extra_fields,
    )


@router.get("/zabbix/login", response_class=HTMLResponse)
async def zabbix_auto_login(
    redirect: str = Query("/zabbix.php?action=dashboard.view", alias="redirect"),
    db: AsyncSession = Depends(get_db),
):
    """
    Zabbix 自动登录桥接页。
    用数据源凭据生成一个自动提交的登录表单，POST 到 Zabbix 代理路径。
    """
    result = await db.execute(
        select(Datasource).where(Datasource.enabled == True).limit(1)
    )
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail="未找到启用的 Zabbix 数据源")

    password = decrypt_password(ds.password_encrypted)
    # redirect 路径附加到反代根路径后
    action = f"/integrations/zabbix/index.php"

    return _build_login_html(
        title="Zabbix",
        subtitle="正在自动登录 Zabbix 监控系统...",
        action=html.escape(action, quote=True),
        username=html.escape(ds.username, quote=True),
        password=html.escape(password, quote=True),
        redirect=f"/integrations/zabbix{html.escape(redirect, quote=True)}",
    )


@router.get("/itop/login", response_class=HTMLResponse)
async def itop_auto_login(
    redirect: str = Query("/pages/exec.php/exec?exec_module=itop-incident-create"),
    db: AsyncSession = Depends(get_db),
):
    """
    iTop 自动登录桥接页。
    从 Settings 读取 iTop URL，生成自动提交的登录表单。
    """
    from models.settings import Settings

    result = await db.execute(
        select(Settings).where(Settings.key == "ITOP_URL")
    )
    row = result.scalar_one_or_none()
    itop_url = row.value if row else ""

    if not itop_url:
        raise HTTPException(status_code=404, detail="未配置 iTop 地址")

    # iTop 默认使用 admin/admin 或从 Settings 读取的凭据
    result = await db.execute(
        select(Settings).where(Settings.key == "ITOP_CREDENTIALS")
    )
    creds_row = result.scalar_one_or_none()
    username = "admin"
    password = "admin"
    if creds_row and creds_row.value:
        parts = creds_row.value.split(":", 1)
        username = parts[0]
        if len(parts) > 1:
            password = parts[1]

    action = f"/integrations/itop/pages/UI.php?redirect={html.escape(redirect, quote=True)}"

    return _build_login_html(
        title="iTop",
        subtitle="正在自动登录 iTop ITSM 系统...",
        action=html.escape(action, quote=True),
        username=html.escape(username, quote=True),
        password=html.escape(password, quote=True),
        extra_fields='<input type="hidden" name="login_mode" value="form">',
    )
