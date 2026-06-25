#!/bin/bash
# Test chat API directly on the server

echo "=== Registering test user ==="
REG=$(curl -s -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"chattester","password":"chattester"}')
echo "Register: $REG"
TOKEN=$(echo "$REG" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "=== Login instead ==="
  LOGIN=$(curl -s -X POST http://localhost:8080/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"chattester","password":"chattester"}')
  echo "Login: $LOGIN"
  TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)
fi

echo "Token: ${TOKEN:0:30}..."

echo ""
echo "=== Creating conversation ==="
CONVO=$(curl -s -X POST http://localhost:8080/api/conversations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"test"}')
echo "Convo: $CONVO"
CONVO_ID=$(echo "$CONVO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
echo "ConvoID: $CONVO_ID"

echo ""
echo "=== Sending message (wait 30s) ==="
curl -s --max-time 30 -X POST "http://localhost:8080/api/conversations/$CONVO_ID/messages" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"Hello, what can you do?"}'

echo ""
echo "=== DONE ==="
