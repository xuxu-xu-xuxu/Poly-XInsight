#!/usr/bin/env python3
"""Deploy project to server via SSH/SFTP."""
import paramiko
import os
import sys

HOST = "172.20.252.20"
USER = "root"
PASS = "yunkun2025"
PROJECT_DIR = "/opt/literature-agent"
TARBALL = "d:/桌面/Project/literature-agent-deploy.tar.gz"

def run_ssh(client, cmd, timeout=60):
    """Run command via SSH and return output."""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(out)
    if err:
        print(f"[STDERR]: {err}")
    return out

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print("=== 连接服务器 ===")
    client.connect(HOST, username=USER, password=PASS, timeout=10, look_for_keys=False, allow_agent=False)
    print("SSH 连接成功")

    # Step 1: Create project directory
    print("\n=== 创建项目目录 ===")
    run_ssh(client, f"mkdir -p {PROJECT_DIR} && rm -rf {PROJECT_DIR}/*")

    # Step 2: Upload tarball via SFTP
    print(f"\n=== 上传文件到 {PROJECT_DIR} ===")
    sftp = client.open_sftp()
    remote_tarball = f"{PROJECT_DIR}/deploy.tar.gz"
    sftp.put(TARBALL, remote_tarball)
    sftp.close()
    file_size = os.path.getsize(TARBALL)
    print(f"上传完成: {file_size} bytes -> {remote_tarball}")

    # Step 3: Extract tarball
    print("\n=== 解压文件 ===")
    run_ssh(client, f"cd {PROJECT_DIR} && tar -xzf deploy.tar.gz && rm deploy.tar.gz && ls -la")

    # Step 4: Create .env file
    print("\n=== 创建 .env 配置文件 ===")
    env_content = """LLM_API_KEY=sk-0e3f9fb65291450684699febc7af150c
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com/v4
LLM_MODEL=deepseek-chat
JWT_SECRET=lit-agent-jwt-secret-change-me-2024
BGE_MODEL_PATH=BAAI/bge-m3
BGE_USE_FP16=false
HF_ENDPOINT=https://huggingface.co
FRONTEND_PORT=3000
INGESTION_CONCURRENCY=2
EMBEDDING_BATCH_SIZE=20
LLM_EXTRACT_CONCURRENCY=2
ENABLE_STRUCTURED_EXTRACTION=false
EXTRACTION_CONFIDENCE_THRESHOLD=0.7
"""
    run_ssh(client, f"cat > {PROJECT_DIR}/.env << 'ENVEOF'\n{env_content}\nENVEOF")
    run_ssh(client, f"cat {PROJECT_DIR}/.env")

    # Step 5: Create necessary directories
    print("\n=== 创建数据和挂载目录 ===")
    run_ssh(client, f"mkdir -p {PROJECT_DIR}/uploads {PROJECT_DIR}/downloads {PROJECT_DIR}/volumes")

    print("\n=== 部署文件准备完成 ===")
    print(f"项目目录: {PROJECT_DIR}")
    client.close()

if __name__ == "__main__":
    main()
