#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
NAMESPACE="insurance"

IMAGES=(
  "insurance-new-business:latest|services/new-business/Dockerfile"
  "insurance-underwriting:latest|services/underwriting/Dockerfile"
  "insurance-policy-admin:latest|services/policy-admin/Dockerfile"
  "insurance-claims:latest|services/claims/Dockerfile"
  "insurance-finance:latest|services/finance/Dockerfile"
  "insurance-gateway:latest|gateway/Dockerfile"
)

echo "Rebuilding and rolling out Insurance Platform..."

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
  img="${entry%%|*}"
  df="${entry##*|}"
  echo "  Building ${img}..."
  docker build -t "${img}" -f "${ROOT_DIR}/${df}" "${ROOT_DIR}"
  import_img "${img}"
done

echo "  Building insurance-web:latest..."
docker build -t insurance-web:latest "${ROOT_DIR}/frontend"
import_img "insurance-web:latest"

kubectl apply -f "${ROOT_DIR}/k8s/configmap.yaml"
kubectl apply -f "${ROOT_DIR}/k8s/kafka.yaml"
kubectl apply -f "${ROOT_DIR}/k8s/deployments.yaml"

kubectl rollout status deployment/insurance-kafka -n "${NAMESPACE}" --timeout=180s || true

for dep in new-business underwriting policy-admin claims finance gateway web; do
  kubectl rollout restart "deployment/${dep}" -n "${NAMESPACE}"
  kubectl rollout status "deployment/${dep}" -n "${NAMESPACE}" --timeout=180s
done

WEB_IP=$(kubectl get svc web -n "${NAMESPACE}" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)
echo ""
echo "Redeploy complete."
echo "Web URL: http://${WEB_IP:-<pending>}"
