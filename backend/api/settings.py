"""系统设置 API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from database import get_db
from models.settings import Settings
from utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/settings", tags=["系统设置"])


def success(data=None, message="success"):
    return {"code": 0, "message": message, "data": data}


class SettingsUpdate(BaseModel):
    system_title: str | None = None
    system_subtitle: str | None = None
    system_logo: str | None = None  # base64 data URL or empty string to clear
    default_refresh_interval: int | None = None
    data_retention_days: int | None = None
    theme: str | None = None
    tz: str | None = None
    # 运维集成
    zabbix_frontend_url: str | None = None
    itop_url: str | None = None
    itop_incident_template: str | None = None


@router.get("")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Settings))
    all_settings = result.scalars().all()
    data = {s.key: s.value for s in all_settings}
    return success(data)


@router.get("/public")
async def get_public_settings(db: AsyncSession = Depends(get_db)):
    """公开接口：获取系统品牌信息（无需登录）"""
    result = await db.execute(
        select(Settings).where(Settings.key.in_(["SYSTEM_TITLE", "SYSTEM_SUBTITLE", "SYSTEM_LOGO"]))
    )
    data = {s.key: s.value for s in result.scalars().all()}
    return success({
        "title": data.get("SYSTEM_TITLE", "ZBXScreen"),
        "subtitle": data.get("SYSTEM_SUBTITLE", ""),
        "logo": data.get("SYSTEM_LOGO", ""),
    })


@router.post("")
async def update_settings(
    req: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    mapping = {
        "SYSTEM_TITLE": req.system_title,
        "SYSTEM_SUBTITLE": req.system_subtitle,
        "SYSTEM_LOGO": req.system_logo,
        "DEFAULT_REFRESH_INTERVAL": str(req.default_refresh_interval) if req.default_refresh_interval else None,
        "DATA_RETENTION_DAYS": str(req.data_retention_days) if req.data_retention_days else None,
        "THEME": req.theme,
        "TZ": req.tz,
        "ZABBIX_FRONTEND_URL": req.zabbix_frontend_url,
        "ITOP_URL": req.itop_url,
        "ITOP_INCIDENT_TEMPLATE": req.itop_incident_template,
    }

    for key, value in mapping.items():
        if value is not None:
            result = await db.execute(select(Settings).where(Settings.key == key))
            setting = result.scalar_one_or_none()
            if setting:
                setting.value = value
                setting.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            else:
                db.add(Settings(key=key, value=value))

    await db.commit()
    return success(message="设置已更新")
