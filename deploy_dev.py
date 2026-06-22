"""开发模式部署：传输后端文件到测试服务器并重启服务"""
import paramiko
import os
import sys

SERVER = "192.168.1.230"
USER = "root"
PASSWORD = "YNqt&2026"
REMOTE_BACKEND = "/opt/zbxscreen/backend"
REMOTE_SERVICES = f"{REMOTE_BACKEND}/services"
REMOTE_API = f"{REMOTE_BACKEND}/api"

LOCAL_BASE = os.path.dirname(os.path.abspath(__file__))

files_to_deploy = [
    ("backend/api/host.py", f"{REMOTE_API}/host.py"),
    ("backend/services/data_aggregator.py", f"{REMOTE_SERVICES}/data_aggregator.py"),
    ("backend/services/history_cache.py", f"{REMOTE_SERVICES}/history_cache.py"),
]

def deploy():
    print(f"[*] Connecting to {SERVER}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USER, password=PASSWORD)

    sftp = ssh.open_sftp()

    # 传输文件
    for local_rel, remote_path in files_to_deploy:
        local_path = os.path.join(LOCAL_BASE, local_rel)
        if not os.path.exists(local_path):
            print(f"  SKIP {local_rel} (not found)")
            continue
        print(f"  UPLOAD {local_rel} -> {remote_path}")
        sftp.put(local_path, remote_path)

    sftp.close()

    # 重启后端服务
    print("\n[*] Restarting backend services...")

    # 找到并kill uvicorn进程
    stdin, stdout, stderr = ssh.exec_command(
        "ps aux | grep 'uvicorn main:app' | grep -v grep | awk '{print $2}'"
    )
    pids = stdout.read().decode().strip().split()

    if pids:
        print(f"  Killing uvicorn PIDs: {pids}")
        ssh.exec_command(f"kill {' '.join(pids)} 2>/dev/null")
        import time
        time.sleep(2)

    # 重启 scheduler
    stdin, stdout, stderr = ssh.exec_command(
        "ps aux | grep 'scheduler_main.py' | grep -v grep | awk '{print $2}'"
    )
    sched_pids = stdout.read().decode().strip().split()
    if sched_pids:
        print(f"  Killing scheduler PIDs: {sched_pids}")
        ssh.exec_command(f"kill {' '.join(sched_pids)} 2>/dev/null")
        import time
        time.sleep(1)

    # 重新启动
    venv_python = f"{REMOTE_BACKEND}/venv/bin/python"

    print("  Starting uvicorn...")
    ssh.exec_command(
        f"cd {REMOTE_BACKEND} && nohup {venv_python} -u main.py > /opt/zbxscreen/logs/uvicorn.log 2>&1 &"
    )

    print("  Starting scheduler...")
    ssh.exec_command(
        f"cd {REMOTE_BACKEND} && nohup {venv_python} -u scheduler_main.py > /opt/zbxscreen/logs/scheduler.log 2>&1 &"
    )

    import time
    time.sleep(3)

    # 检查进程
    print("\n[*] Checking processes...")
    stdin, stdout, stderr = ssh.exec_command(
        "ps aux | grep -E 'uvicorn|scheduler' | grep -v grep"
    )
    print(stdout.read().decode() or "  (no output - processes may need manual check)")

    ssh.close()
    print("\n[DONE] Files deployed and services restarted.")

if __name__ == "__main__":
    deploy()
