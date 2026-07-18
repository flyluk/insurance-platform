#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
NAMESPACE="insurance"
RELEASE="insurance-postgres"

IMAGES=(
  "insurance-new-business:latest|services/new-business/Dockerfile"
  "insurance-underwriting:latest|services/underwriting/Dockerfile"
  "insurance-policy-admin:latest|services/policy-admin/Dockerfile"
  "insurance-claims:latest|services/claims/Dockerfile"
  "insurance-finance:latest|services/finance/Dockerfile"
  "insurance-product-engine:latest|services/product-engine/Dockerfile"
  "insurance-gateway:latest|gateway/Dockerfile"
)

echo "=========================================="
echo "Installing Insurance Platform"
echo "=========================================="

POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)}"
JWT_SECRET="${JWT_SECRET:-$(openssl rand -base64 32)}"

echo ""
echo "Step 1/6: Creating namespace..."
kubectl apply -f "${ROOT_DIR}/k8s/namespace.yaml"

echo ""
echo "Step 2/6: Deploying PostgreSQL..."
helm repo add bitnami https://charts.bitnami.com/bitnami 2>/dev/null || true
helm repo update

INIT_VALUES="${SCRIPT_DIR}/.insurance-postgres-init.generated.yaml"
python3 - <<PY
from pathlib import Path

init_sql = Path("${ROOT_DIR}/db/init-databases.sql").read_text()
indented = "\n".join("        " + line for line in init_sql.splitlines())
content = f"""primary:
  initdb:
    scripts:
      init.sql: |
{indented}
"""
Path("${INIT_VALUES}").write_text(content)
PY

helm upgrade --install "${RELEASE}" bitnami/postgresql \
  -n "${NAMESPACE}" \
  -f "${SCRIPT_DIR}/insurance-postgres-values.yaml" \
  -f "${INIT_VALUES}" \
  --set auth.password="${POSTGRES_PASSWORD}"

echo "Waiting for PostgreSQL..."
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/instance="${RELEASE}" \
  -n "${NAMESPACE}" \
  --timeout=300s

echo ""
echo "Step 2b/6: Deploying Kafka (apache/kafka)..."
# Remove failed Bitnami Helm release if present (image no longer on Docker Hub)
helm uninstall insurance-kafka -n "${NAMESPACE}" 2>/dev/null || true
kubectl delete job insurance-kafka-topic-init -n "${NAMESPACE}" --ignore-not-found
kubectl apply -f "${ROOT_DIR}/k8s/kafka.yaml"

echo "Waiting for Kafka..."
kubectl rollout status deployment/insurance-kafka -n "${NAMESPACE}" --timeout=300s
kubectl wait --for=condition=complete job/insurance-kafka-topic-init \
  -n "${NAMESPACE}" --timeout=180s

POSTGRES_HOST="${RELEASE}-postgresql.${NAMESPACE}.svc.cluster.local"
mkurl() { echo "postgresql://insurance:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:5432/$1"; }

echo ""
echo "Step 3/6: Creating secrets and config..."
kubectl apply -f "${ROOT_DIR}/k8s/configmap.yaml"
kubectl create secret generic insurance-secrets \
  -n "${NAMESPACE}" \
  --from-literal=POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
  --from-literal=JWT_SECRET="${JWT_SECRET}" \
  --from-literal=NB_DATABASE_URL="$(mkurl nb_db)" \
  --from-literal=UW_DATABASE_URL="$(mkurl uw_db)" \
  --from-literal=POLICY_DATABASE_URL="$(mkurl policy_db)" \
  --from-literal=CLAIMS_DATABASE_URL="$(mkurl claims_db)" \
  --from-literal=FINANCE_DATABASE_URL="$(mkurl finance_db)" \
  --from-literal=PRODUCT_DATABASE_URL="$(mkurl product_db)" \
  --from-literal=IDENTITY_DATABASE_URL="$(mkurl identity_db)" \
  --dry-run=client -o yaml | kubectl apply -f -

echo ""
echo "Step 4/6: Building container images..."
for entry in "${IMAGES[@]}"; do
  img="${entry%%|*}"
  df="${entry##*|}"
  echo "  Building ${img}..."
  docker build -t "${img}" -f "${ROOT_DIR}/${df}" "${ROOT_DIR}"
done
echo "  Building insurance-web:latest..."
docker build -t insurance-web:latest "${ROOT_DIR}/frontend"
echo "  Building insurance-product-portal:latest..."
docker build -t insurance-product-portal:latest "${ROOT_DIR}/product-portal"

echo "Importing images into MicroK8s..."
import_img() {
  local img="$1"
  if command -v microk8s &>/dev/null; then
    docker save "${img}" | microk8s ctr image import - 2>/dev/null || true
  else
    for host in microk8s-vm{1..6}.test.local; do
      docker save "${img}" | ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "${host}" 'microk8s ctr image import -' 2>/dev/null || true
    done
  fi
}
for entry in "${IMAGES[@]}"; do
  import_img "${entry%%|*}"
done
import_img "insurance-web:latest"
import_img "insurance-product-portal:latest"

echo ""
echo "Step 5/6: Deploying services..."
kubectl apply -f "${ROOT_DIR}/k8s/kafka.yaml"
kubectl apply -f "${ROOT_DIR}/k8s/deployments.yaml"
kubectl apply -f "${ROOT_DIR}/k8s/grafana-dashboard.yaml" 2>/dev/null || true
kubectl apply -f "${ROOT_DIR}/k8s/servicemonitor.yaml" 2>/dev/null || true

for dep in new-business underwriting policy-admin claims finance product-engine gateway web product-portal; do
  kubectl rollout status "deployment/${dep}" -n "${NAMESPACE}" --timeout=180s
done

echo ""
echo "Step 6/6: Waiting for LoadBalancer..."
sleep 10
WEB_IP=$(kubectl get svc web -n "${NAMESPACE}" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)
PORTAL_IP=$(kubectl get svc product-portal -n "${NAMESPACE}" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)

echo ""
echo "=========================================="
echo "Insurance Platform installed!"
echo "=========================================="
echo ""
echo "Namespace: ${NAMESPACE}"
echo "Web URL:   http://${WEB_IP:-<pending>}"
echo "Product portal: http://${PORTAL_IP:-<pending>}"
echo "Gateway:   http://gateway.${NAMESPACE}.svc.cluster.local:8000"
echo ""
echo "Demo logins (role @insurance.local):"
echo "  agent@insurance.local / agent123"
echo "  uw@insurance.local / uw123456"
echo "  claims@insurance.local / claims123"
echo "  finance@insurance.local / finance123"
echo "  product@insurance.local / product123"
echo "  admin@insurance.local / admin123"
echo ""
echo "Secrets: insurance-secrets (${NAMESPACE})"
