# Meridian Insurance Platform

Multi-product (AUTO / HOME / LIFE) insurance microservices on Python FastAPI, PostgreSQL, and MicroK8s — following the same deploy patterns as `shop-demo`.

## Architecture

```
insurance namespace
├── PostgreSQL (Bitnami Helm) — nb_db, uw_db, policy_db, claims_db, finance_db, identity_db, product_db
├── Kafka (apache/kafka KRaft) — topic insurance.domain.events
├── new-business ×2
├── underwriting ×2
├── policy-admin ×2
├── claims ×2
├── finance ×2
├── product-engine ×2   # plans + riders catalog
├── gateway ×2          # JWT auth + reverse proxy
├── web ×2              # React staff UI (LoadBalancer)
├── product-portal ×2   # Product Studio UI (LoadBalancer)
└── policyholder-portal ×2  # Customer self-serve UI (LoadBalancer)
```

Domain events use a **Postgres outbox → Kafka** pattern:

`ApplicationSubmitted` → UW → `UnderwritingDecided` → Policy Admin (bind) + New Business (status) → `PremiumDue` / `PolicyBound` → Finance / New Business. Claims emit `ClaimPaymentRequested` → Finance.

Topic: `insurance.domain.events` (one message per event; each service consumes with its own consumer group).

## Local development

```bash
cd /home/flyluk/development/insurance-platform
docker compose up --build
```

| Service | URL |
|---------|-----|
| Staff UI | http://localhost:8088 |
| Product Studio | http://localhost:8089 |
| Policyholder portal | http://localhost:8091 |
| Gateway API | http://localhost:8090 |
| Gateway docs | http://localhost:8090/docs |

### Demo logins

| Email | Password | Role |
|-------|----------|------|
| agent@insurance.local | agent123 | agent |
| uw@insurance.local | uw123456 | underwriter |
| claims@insurance.local | claims123 | claims |
| finance@insurance.local | finance123 | finance |
| product@insurance.local | product123 | product |
| admin@insurance.local | admin123 | admin |
| policyholder@insurance.local | holder123 | policyholder |

The policyholder account is linked to a seeded party, active AUTO policy (`AUTO-DEMO0001`), and an open premium invoice for self-serve pay and FNOL demos.

### Product engine (plans & riders)

- **Product Studio** (`product-portal`) is a separate login for `product` (and `admin`) to configure **basic plans** and **riders** per line (AUTO / HOME / LIFE).
- Each plan has a **risk field schema** (drives New Business quote forms), **UW rule thresholds** (decline/refer), and **effective-dated rate versions**.
- Seeded published plans match historical rating bases (AUTO 800, HOME 1200, LIFE 600) plus sample riders, schemas, and UW rules.
- Staff **New Business** quotes pick a published basic plan and optional riders; premium = `(effective plan + rider rates) × risk factors`.
- Underwriting loads thresholds from product-engine (`/api/products/evaluate-uw`) with a local fallback.
- Existing Postgres installs need a one-time `CREATE DATABASE product_db;` (and secret key `PRODUCT_DATABASE_URL`) before deploying `product-engine`.

## Cluster install (MicroK8s)

```bash
cd /home/flyluk/development/insurance-platform/scripts
./install-insurance.sh
```

Redeploy after code changes:

```bash
./redeploy-insurance.sh
```

## Happy-path workflow

1. Sign in as **agent** → create party → pick published plan (+ riders) → rate → submit  
2. Sign in as **underwriter** → decide referrals (auto-accept/decline may already bind)  
3. **Policies** appear when UW accepts → renew / cancel (policy change is **admin** only)  
4. **Claims** → open FNOL on an active policy → attach evidence documents → settle (triggers finance disbursement)  
5. **Finance** → pay premium invoices → view ledger  
6. Sign in to **Product Studio** as **product** → manage plans/riders → publish for quoting  
7. Sign in to **Policyholder portal** as **policyholder** → view policy → pay invoice (CARD/ACH) → file a claim  

### Policyholder payments

Self-serve collections use a **simulated processor** (no external PSP):

- **CARD** — requires number / expiry / CVV; cards ending in `0000` are declined (`402`)
- **ACH** — requires account name, account number, 9-digit routing; routing `000000000` is declined
- Full PAN/account numbers are never stored; only a processor reference and masked last-4 are kept
- Staff Finance can still record payments without instrument details

### Claim documents

Staff and policyholders can attach evidence to a claim (`PHOTO`, `POLICE_REPORT`, `MEDICAL`, `INVOICE`, `OTHER`):

- `POST /api/claims/{id}/documents` — multipart upload (`file` + `category`)
- `GET /api/claims/{id}/documents` — list metadata
- `GET /api/claims/{id}/documents/{doc_id}` — download bytes
- `DELETE /api/claims/{id}/documents/{doc_id}` — staff/admin only
- Stored in Postgres (`BYTEA`) so multi-replica claims pods share evidence without object storage
- Max **5 MB**; allowed types: JPEG, PNG, WebP, PDF, plain text

## Observability

- Each service exposes `/health` and `/metrics` (Prometheus)
- [`k8s/servicemonitor.yaml`](k8s/servicemonitor.yaml) scrapes metrics in-cluster
- Grafana dashboard ConfigMap: [`k8s/grafana-dashboard.yaml`](k8s/grafana-dashboard.yaml) (label `grafana_dashboard=1` for sidecar)

## Test automation

API, E2E (Kafka), and Playwright UI suite under [`tests/`](tests/). See [`tests/README.md`](tests/README.md).

```bash
pip install -r tests/requirements.txt
playwright install chromium
pytest tests/ -v
```

## Layout

```
insurance-platform/
├── services/          # five FastAPI domain services
├── gateway/           # auth + API proxy
├── frontend/          # React staff console
├── policyholder-portal/ # Customer self-serve portal
├── shared/            # JWT, outbox, metrics package
├── db/                # multi-database init SQL
├── k8s/               # manifests
├── scripts/           # install / redeploy
└── grafana/           # dashboard JSON
```
