"""开发模式部署：传输后端+前端文件到测试服务器并重启服务"""
import paramiko
import os
import sys
import time

SERVER = "192.168.1.230"
USER = "root"
PASSWORD = "YNqt&2026"
REMOTE_BASE = "/opt/zabbixscreen"
REMOTE_BACKEND = f"{REMOTE_BASE}/backend"
REMOTE_SCRIPTS = f"{REMOTE_BASE}/scripts"
REMOTE_FRONTEND_DIST = f"{REMOTE_BASE}/frontend/dist"

LOCAL_BASE = os.path.dirname(os.path.abspath(__file__))

# ====== 后端文件部署列表 ======
backend_files = [
    ("backend/config.py", f"{REMOTE_BACKEND}/config.py"),
    ("backend/services/alert_engine.py", f"{REMOTE_BACKEND}/services/alert_engine.py"),
    ("scripts/init_db.py", f"{REMOTE_SCRIPTS}/init_db.py"),
]

# ====== 前端 dist 目录（整个目录上传） ======
LOCAL_DIST = os.path.join(LOCAL_BASE, "frontend", "dist")


def deploy():
    print(f"[*] Connecting to {SERVER}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USER, password=PASSWORD, timeout=15)

    sftp = ssh.open_sftp()

    # ── 1. 传输后端文件 ──
    print("\n─── Backend Files ───")
    for local_rel, remote_path in backend_files:
        local_path = os.path.join(LOCAL_BASE, local_rel.replace("/", os.sep))
        if not os.path.exists(local_path):
            print(f"  SKIP {local_rel} (not found)")
            continue
        print(f"  UPLOAD {local_rel} -> {remote_path}")
        sftp.put(local_path, remote_path)

    # ── 2. 传输前端 dist ──
    print("\n─── Frontend dist ───")
    if not os.path.exists(LOCAL_DIST):
        print(f"  SKIP frontend/dist (not found — run 'npm run build' first)")
    else:
        # 先清空旧的 dist 文件
        try:
            existing = sftp.listdir(REMOTE_FRONTEND_DIST)
            for f in existing:
                remote_f = f"{REMOTE_FRONTEND_DIST}/{f}"
                try:
                    # 递归删除目录
                    _rmtree_sftp(sftp, remote_f)
                except:
                    pass
            print(f"  Cleaned {len(existing)} items from {REMOTE_FRONTEND_DIST}")
        except FileNotFoundError:
            sftp.mkdir(REMOTE_FRONTEND_DIST)
            print(f"  Created {REMOTE_FRONTEND_DIST}")

        # 上传所有 dist 文件
        uploaded = 0
        for item in os.listdir(LOCAL_DIST):
            local_item = os.path.join(LOCAL_DIST, item)
            remote_item = f"{REMOTE_FRONTEND_DIST}/{item}"
            if os.path.isfile(local_item):
                sftp.put(local_item, remote_item)
                uploaded += 1
            elif os.path.isdir(local_item):
                # 递归上传目录(assets/)
                _upload_dir(sftp, local_item, remote_item)
                # 统计目录内文件数
                for _, _, files in os.walk(local_item):
                    uploaded += len(files)
        print(f"  Uploaded {uploaded} files to {REMOTE_FRONTEND_DIST}")

    sftp.close()

    # ── 3. 重启后端服务 ──
    print("\n─── Restarting Services ───")
    venv_python = f"{REMOTE_BACKEND}/venv/bin/python"

    # Kill uvicorn
    stdin, stdout, stderr = ssh.exec_command(
        "ps aux | grep 'uvicorn main:app' | grep -v grep | awk '{print $2}'"
    )
    uvicorn_pids = stdout.read().decode().strip().split()
    if uvicorn_pids:
        print(f"  Killing uvicorn PIDs: {uvicorn_pids}")
        ssh.exec_command(f"kill {' '.join(uvicorn_pids)} 2>/dev/null")
        time.sleep(2)

    # Kill scheduler
    stdin, stdout, stderr = ssh.exec_command(
        "ps aux | grep 'scheduler_main.py' | grep -v grep | awk '{print $2}'"
    )
    sched_pids = stdout.read().decode().strip().split()
    if sched_pids:
        print(f"  Killing scheduler PIDs: {sched_pids}")
        ssh.exec_command(f"kill {' '.join(sched_pids)} 2>/dev/null")
        time.sleep(1)

    # Start uvicorn
    print("  Starting uvicorn...")
    uvicorn_bin = f"{REMOTE_BACKEND}/venv/bin/uvicorn"
    ssh.exec_command(
        f"cd {REMOTE_BACKEND} && "
        f"nohup {uvicorn_bin} --host 127.0.0.1 --port 5001 --workers 1 "
        f"> /opt/zabbixscreen/logs/uvicorn.log 2>&1 &"
    )

    # Start scheduler
    print("  Starting scheduler...")
    ssh.exec_command(
        f"cd {REMOTE_BACKEND} && "
        f"nohup {venv_python} -u -B scheduler_main.py "
        f"> /opt/zabbixscreen/logs/scheduler.log 2>&1 &"
    )

    time.sleep(4)

    # ── 4. 验证 ──
    print("\n─── Verification ───")
    stdin, stdout, stderr = ssh.exec_command(
        "ps aux | grep -E 'uvicorn main:app|scheduler_main' | grep -v grep"
    )
    proc_out = stdout.read().decode().strip()
    if proc_out:
        print("  Processes running:")
        for line in proc_out.split("\n"):
            print(f"    {line[:120]}")
    else:
        print("  WARNING: No processes found!")

    # API health check
    stdin, stdout, stderr = ssh.exec_command(
        "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5001/api/v1/settings/public"
    )
    api_status = stdout.read().decode().strip()
    print(f"  API /settings/public → HTTP {api_status}")

    # Nginx frontend check
    stdin, stdout, stderr = ssh.exec_command(
        "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/"
    )
    frontend_status = stdout.read().decode().strip()
    print(f"  Frontend / → HTTP {frontend_status}")

    ssh.close()
    print("\n[DONE] Deployment complete.")


def _rmtree_sftp(sftp, path):
    """递归删除 SFTP 目录树"""
    try:
        for item in sftp.listdir(path):
            item_path = f"{path}/{item}"
            try:
                sftp.remove(item_path)
            except IOError:
                _rmtree_sftp(sftp, item_path)
        sftp.rmdir(path)
    except IOError:
        sftp.remove(path)


def _upload_dir(sftp, local_dir, remote_dir):
    """递归上传目录"""
    try:
        sftp.mkdir(remote_dir)
    except IOError:
        pass
    for item in os.listdir(local_dir):
        local_item = os.path.join(local_dir, item)
        remote_item = f"{remote_dir}/{item}"
        if os.path.isfile(local_item):
            sftp.put(local_item, remote_item)
        elif os.path.isdir(local_item):
            _upload_dir(sftp, local_item, remote_item)


if __name__ == "__main__":
    deploy()
