# Meridian Insurance Platform

Multi-product (AUTO / HOME / LIFE) insurance microservices on Python FastAPI, PostgreSQL, and MicroK8s — following the same deploy patterns as `shop-demo`.

## Architecture

```
insurance namespace
├── PostgreSQL (Bitnami Helm) — nb_db, uw_db, policy_db, claims_db, finance_db, identity_db
├── new-business ×2
├── underwriting ×2
├── policy-admin ×2
├── claims ×2
├── finance ×2
├── gateway ×2          # JWT auth + reverse proxy
└── web ×2              # React staff UI (LoadBalancer)

monitoring namespace
├── Prometheus ← ServiceMonitor /metrics
└── Grafana ← Insurance Platform dashboard
```

Domain events use a Postgres outbox + HTTP delivery (no Kafka):

`ApplicationSubmitted` → UW → `UnderwritingDecided` → Policy Admin (bind) + New Business (status) → `PremiumDue` / `PolicyBound` → Finance / New Business. Claims emit `ClaimPaymentRequested` → Finance.

## Local development

```bash
cd /home/flyluk/development/insurance-platform
docker compose up --build
```

| Service | URL |
|---------|-----|
| Staff UI | http://localhost:8088 |
| Gateway API | http://localhost:8090 |
| Gateway docs | http://localhost:8090/docs |

### Demo logins

| Email | Password | Role |
|-------|----------|------|
| agent@insurance.local | agent123 | agent |
| uw@insurance.local | uw123456 | underwriter |
| claims@insurance.local | claims123 | claims |
| finance@insurance.local | finance123 | finance |
| admin@insurance.local | admin123 | admin |

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

1. Sign in as **agent** → create party → create quote (AUTO/HOME/LIFE) → rate → submit  
2. Sign in as **underwriter** → decide referrals (auto-accept/decline may already bind)  
3. **Policies** appear when UW accepts → endorse / renew / cancel  
4. **Claims** → open FNOL on an active policy → settle (triggers finance disbursement)  
5. **Finance** → pay premium invoices → view ledger  

## Observability

- Each service exposes `/health` and `/metrics` (Prometheus)
- [`k8s/servicemonitor.yaml`](k8s/servicemonitor.yaml) scrapes metrics in-cluster
- Grafana dashboard ConfigMap: [`k8s/grafana-dashboard.yaml`](k8s/grafana-dashboard.yaml) (label `grafana_dashboard=1` for sidecar)

## Layout

```
insurance-platform/
├── services/          # five FastAPI domain services
├── gateway/           # auth + API proxy
├── frontend/          # React staff console
├── shared/            # JWT, outbox, metrics package
├── db/                # multi-database init SQL
├── k8s/               # manifests
├── scripts/           # install / redeploy
└── grafana/           # dashboard JSON
```
