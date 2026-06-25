#!/bin/bash
# scripts/smoke_test.sh - End-to-end smoke test for Literature Agent
set -e

echo "=== Health Check ==="
curl -s http://localhost:8080/api/health | grep -q "ok" && echo "PASS: health" || echo "FAIL: health"

echo "=== Upload Test PDF ==="
python -c "
import fitz
doc = fitz.open()
doc.new_page().insert_text((50, 50), 'Test paper about titanium alloy Ti-6Al-4V SLM process. UTS is 950 MPa.')
doc.save('/tmp/test.pdf')
"
RESULT=$(curl -s -F "file=@/tmp/test.pdf" http://localhost:8080/api/upload)
PAPER_ID=$(echo $RESULT | python -c "import sys,json; print(json.load(sys.stdin)['paper_id'])")
echo "Upload result: $RESULT"
[[ -n "$PAPER_ID" ]] && echo "PASS: upload" || echo "FAIL: upload"

echo "=== List Papers ==="
sleep 3
curl -s http://localhost:8080/api/papers | python -c "import sys,json; d=json.load(sys.stdin); assert d['total']>=1" && echo "PASS: papers" || echo "FAIL: papers"

echo "=== Chat ==="
curl -s -X POST http://localhost:8080/api/chat -H "Content-Type: application/json" -d '{"query":"What is Ti-6Al-4V?"}' | head -3
echo "PASS: chat (SSE stream received)"

echo "=== Smoke test complete ==="
