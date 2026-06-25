#!/bin/bash
set -e

echo "=== Loading images ==="
gunzip -c /tmp/matbrain-images.tar.gz | docker load

echo "=== Cleaning up ==="
rm -f /tmp/matbrain-images.tar.gz

echo "=== Starting services ==="
cd /opt/matbrain-agent
chmod -R 777 volumes/
docker compose up -d 2>&1

echo "=== Container Status ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== Backend Health ==="
sleep 5
curl -s http://localhost:8080/api/health 2>&1 || echo "Backend not ready yet"

echo ""
echo "=== BGE Health ==="
curl -s http://localhost:8000/health 2>&1 || echo "BGE not ready yet"

echo ""
echo "=== Frontend ==="
curl -sI http://localhost:3000 2>&1 | head -3

echo ""
echo "=== Disk ==="
df -h /

echo ""
echo "=== DONE ==="
