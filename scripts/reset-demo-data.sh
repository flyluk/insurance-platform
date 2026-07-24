#!/usr/bin/env bash
# Wipe local Postgres (and Kafka ephemeral state) then recreate the stack with
# startup seeds (users, parties, policies, claims, UW cases, invoices, catalog).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "Stopping stack and removing volumes..."
docker compose down -v

echo "Starting stack (rebuild images)..."
docker compose up -d --build

echo "Waiting for gateway health..."
for i in $(seq 1 60); do
  if curl -sf http://localhost:8090/health >/dev/null; then
    echo "Gateway is up."
    break
  fi
  if [[ "$i" -eq 60 ]]; then
    echo "Timed out waiting for gateway." >&2
    exit 1
  fi
  sleep 2
done

echo
echo "Demo data reloaded. Logins:"
echo "  agent@insurance.local / agent123"
echo "  claims@insurance.local / claims123"
echo "  uw@insurance.local / uw123456"
echo "  policyholder@insurance.local / holder123"
echo
echo "Sample seeded records:"
echo "  Policies: AUTO-DEMO0001, AUTO-DEMO0002, HOME-DEMO0001, LIFE-DEMO0001, AUTO-DEMO-CX01"
echo "  Claims:   CLM-DEMO0001 (OPEN), CLM-DEMO0002 (RESERVED), CLM-DEMO-HI01 (PENDING_APPROVAL >\$10k)"
echo "  Clients:  Alex Rivera, Jordan Lee, Sam Chen, Riley Quinn, Morgan Blake, Avery Kim, Casey Rivera"
