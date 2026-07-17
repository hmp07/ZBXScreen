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
  {fields}
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
    fields: str,
    redirect: str = "/integrations/zabbix/zabbix.php?action=dashboard.view",
) -> str:
    return LOGIN_PAGE_TEMPLATE.format(
        title=title,
        subtitle=subtitle,
        action=action,
        fields=fields,
        redirect=redirect,
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
        title="运维监控系统",
        subtitle="正在自动登录运维监控系统...",
        action=html.escape(action, quote=True),
        fields=f'''<input type="hidden" name="name" value="{html.escape(ds.username, quote=True)}">
  <input type="hidden" name="password" value="{html.escape(password, quote=True)}">
  <input type="hidden" name="enter" value="Sign in">''',
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
        return HTMLResponse(content="""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>iTop 未配置</title></head>
<body style="background:#0d1b2e;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
<div style="text-align:center;color:#e6f7ff;font-family:sans-serif">
  <div style="font-size:24px;margin-bottom:16px">运维管理系统 未配置</div>
  <div style="font-size:14px;color:#6b89a3">请在 系统设置→数据源→运维集成 中配置运维管理系统地址和凭据</div>
</div>
</body>
</html>""")

    # 读取 iTop 凭据
    result = await db.execute(
        select(Settings).where(Settings.key == "ITOP_USERNAME")
    )
    username_row = result.scalar_one_or_none()
    username = username_row.value if username_row else "admin"

    result = await db.execute(
        select(Settings).where(Settings.key == "ITOP_PASSWORD")
    )
    password_row = result.scalar_one_or_none()
    password = password_row.value if password_row else "admin"

    # 直接 POST 到 iTop 服务器（不经过代理，避免需要更新 nginx 配置）
    action = f"{itop_url.rstrip('/')}/pages/UI.php"

    return _build_login_html(
        title="运维管理系统",
        subtitle="正在自动登录运维管理系统...",
        action=html.escape(action, quote=True),
        fields=f'''<input type="hidden" name="auth_user" value="{html.escape(username, quote=True)}">
  <input type="hidden" name="auth_pwd" value="{html.escape(password, quote=True)}">
  <input type="hidden" name="login_mode" value="form">
  <input type="hidden" name="loginop" value="login">''',
        redirect=html.escape(f"{itop_url.rstrip('/')}{redirect}", quote=True),
    )
