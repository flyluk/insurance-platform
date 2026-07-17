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

for entry in "${IMAGES[@]}"; do
  img="${entry%%|*}"
  df="${entry##*|}"
  docker build -t "${img}" -f "${ROOT_DIR}/${df}" "${ROOT_DIR}"
  if command -v microk8s &>/dev/null; then
    docker save "${img}" | microk8s ctr image import - 2>/dev/null || true
  fi
done
docker build -t insurance-web:latest "${ROOT_DIR}/frontend"
if command -v microk8s &>/dev/null; then
  docker save insurance-web:latest | microk8s ctr image import - 2>/dev/null || true
fi

kubectl apply -f "${ROOT_DIR}/k8s/configmap.yaml"
kubectl apply -f "${ROOT_DIR}/k8s/deployments.yaml"

for dep in new-business underwriting policy-admin claims finance gateway web; do
  kubectl rollout restart "deployment/${dep}" -n "${NAMESPACE}"
  kubectl rollout status "deployment/${dep}" -n "${NAMESPACE}" --timeout=180s
done

echo "Redeploy complete."
