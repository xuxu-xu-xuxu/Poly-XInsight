#!/usr/bin/env python3
"""Setup SSH key on new server and check environment."""
import paramiko

HOST = "172.20.252.22"
USER = "root"
PASS = "yunkun2025"

PUBKEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIK8E8K2QV/EBc46wQPhPehoz+yHmW+JaH1QKUIxY8QhT 1346280527@qq.com"

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOST, username=USER, password=PASS, timeout=10, look_for_keys=False, allow_agent=False)
        print("SSH 连接成功")

        # Add SSH key
        cmd = f"grep -q '{PUBKEY}' ~/.ssh/authorized_keys 2>/dev/null && echo 'key_exists' || (mkdir -p ~/.ssh && echo '{PUBKEY}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo 'key_added')"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
        print(stdout.read().decode().strip())

        # Check environment
        commands = [
            "uname -a",
            "cat /etc/os-release | head -3",
            "free -h | head -2",
            "df -h /",
            "nproc",
            "docker --version 2>&1 || echo 'Docker NOT installed'",
            "docker compose version 2>&1 || echo 'Compose NOT installed'",
            "lspci | grep -i nvidia 2>/dev/null && echo 'GPU found' || echo 'No GPU'",
        ]
        for cmd in commands:
            print(f"\n--- {cmd} ---")
            stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            if out:
                print(out)
            if err:
                print(err)

        client.close()
        print("\nDone - key added, server info collected")
    except Exception as e:
        print(f"连接失败: {e}")

if __name__ == "__main__":
    main()
