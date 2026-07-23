#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://localhost:8090}"

echo "Health: $(curl -sf "$BASE/health")"

TOKEN=$(curl -sf -X POST "$BASE/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"agent@insurance.local","password":"agent123"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
echo "Login OK"

auth() { curl -sf -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' "$@"; }

PARTY=$(auth -X POST "$BASE/api/nb/parties" \
  -d '{"full_name":"Ada Lovelace","email":"ada@example.com","phone":"+1 555 0100","date_of_birth":"1815-12-10","address":"1 Analytical Engine Way","id_number":"ADA-001","gender":"female"}')
PID=$(echo "$PARTY" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
echo "Party $PID"

QUOTE=$(auth -X POST "$BASE/api/nb/quotes" \
  -d "{\"party_id\":\"$PID\",\"product_code\":\"AUTO\",\"risk_attributes\":{\"vehicle_year\":2022,\"drivers\":1,\"prior_claims\":0,\"driver_age\":34}}")
QID=$(echo "$QUOTE" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')

auth -X POST "$BASE/api/nb/quotes/$QID/rate" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("Rated", d["annual_premium"], d["status"])'
auth -X POST "$BASE/api/nb/quotes/$QID/submit" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("Submitted", d["id"], d["status"])'

sleep 6
auth "$BASE/api/policies" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("Policies", len(d), (d[0]["policy_number"], d[0]["status"]) if d else None)'
auth "$BASE/api/finance/invoices" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("Invoices", len(d), (d[0]["invoice_number"], d[0]["status"]) if d else None)'
auth "$BASE/api/nb/applications" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("Apps", [(a["status"], a.get("uw_decision"), a.get("policy_id")) for a in d[:3]])'
echo "E2E OK"
