#!/usr/bin/env python3
"""Try pulling directly from Docker Hub (no mirrors)."""
import paramiko
import time

HOST = "172.20.252.20"
USER = "root"
PASS = "yunkun2025"
PROJECT_DIR = "/opt/literature-agent"

def run_ssh(client, cmd, timeout=120):
    print(f"\n>>> {cmd[:120]}...", flush=True)
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(out[-3000:])
    if err:
        for line in err.split('\n')[-5:]:
            if line.strip():
                print(f"[STDERR]: {line}")
    return out, err

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=10, look_for_keys=False, allow_agent=False)
    print("SSH 成功")

    # Step 1: REMOVE all mirrors - use Docker Hub directly
    print("\n=== 移除所有镜像源，直连 Docker Hub ===")
    daemon_config = '{"registry-mirrors": []}'
    run_ssh(client, f"cat > /etc/docker/daemon.json << 'EOF'\n{daemon_config}\nEOF")
    print("Config:", run_ssh(client, "cat /etc/docker/daemon.json")[0])
    run_ssh(client, "systemctl restart docker 2>&1 && sleep 2 && echo 'OK'")

    client.close()
    time.sleep(3)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=10, look_for_keys=False, allow_agent=False)
    print("重连成功")

    # Step 2: Test direct pull of hello-world
    print("\n=== 测试直连 Docker Hub ===")
    run_ssh(client, "docker pull hello-world 2>&1", timeout=120)

    # Step 3: Pull all services
    print("\n=== 拉取所有服务 ===")
    out, err = run_ssh(client, f"cd {PROJECT_DIR} && docker compose pull 2>&1", timeout=1800)

    # Step 4: Build custom images
    for svc in ["bge-m3", "backend", "frontend"]:
        print(f"\n=== 构建 {svc} ===")
        run_ssh(client, f"cd {PROJECT_DIR} && docker compose build {svc} 2>&1", timeout=900)

    # Step 5: Start
    print("\n=== 启动 ===")
    run_ssh(client, f"cd {PROJECT_DIR} && docker compose up -d 2>&1", timeout=300)

    # Step 6: Status
    print("\n=== 状态 ===")
    run_ssh(client, "docker compose -f /opt/literature-agent/docker-compose.yml ps 2>&1")
    run_ssh(client, "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | head -20")
    run_ssh(client, "df -h /")

    client.close()

if __name__ == "__main__":
    main()
