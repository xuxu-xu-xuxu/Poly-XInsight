#!/bin/bash
cd /opt/matbrain-agent
sed -i 's|LLM_BASE_URL=.*|LLM_BASE_URL=https://api.deepseek.com/v1|' .env
echo "=== Fixed .env LLM config ==="
grep LLM .env
echo "=== Restarting backend ==="
docker compose restart backend
echo "=== DONE ==="
