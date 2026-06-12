"""
SQLite 数据库初始化
- WAL 模式 PRAGMA 配置
- 异步引擎 + 连接池
- Session 依赖注入
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import event
from config import settings
import os

# 数据库文件路径
# 容器内后端代码在 /app/，本地开发在 backend/
# 优先使用环境变量 ZBX_DATA_DIR，回退到相对于本文件的路径
if os.environ.get("ZBX_DATA_DIR"):
    DB_DIR = os.environ["ZBX_DATA_DIR"]
else:
    DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DB_DIR, exist_ok=True)
DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(DB_DIR, settings.db_path)}"

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.debug,
    connect_args={"check_same_thread": False},  # SQLite 需要此参数
)

# 异步 Session 工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# 启用 WAL 模式和其他 PRAGMA（在每次连接时执行）
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA synchronous = NORMAL;")
    cursor.execute("PRAGMA cache_size = 10000;")
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("PRAGMA busy_timeout = 5000;")
    cursor.execute("PRAGMA wal_autocheckpoint = 1000;")
    cursor.close()


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库 session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
