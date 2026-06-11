"""
调度器独立进程入口
由 supervisor 管理，与 FastAPI worker 完全隔离
避免多 worker 时 APScheduler 重复执行
"""
import asyncio
import sys
import os

# 确保 backend 目录在路径中
sys.path.insert(0, os.path.dirname(__file__))

from services.scheduler import start_scheduler


async def main():
    print("[scheduler] Starting APScheduler...")
    start_scheduler()
    # 保持进程运行
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
