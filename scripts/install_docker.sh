#!/bin/bash
# Install Docker on Ubuntu 22.04 using Chinese mirrors
set -e

echo "=== Adding Docker repo (TUNA mirror) ==="
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list

echo "=== Installing Docker ==="
apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin 2>&1 | tail -10

echo "=== Docker version ==="
docker --version
docker compose version

echo "=== Adding cnic to docker group ==="
usermod -aG docker cnic

echo "=== DONE ==="
