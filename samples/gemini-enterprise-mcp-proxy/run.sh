#!/usr/bin/env bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [[ -f ".env" ]]; then
  # shellcheck source=/dev/null
  source ".env"
fi

export PYTHONUNBUFFERED=1

# Cloud Run 배포 래퍼 모드
if [[ "${1:-}" == "--deploy" ]]; then
  PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo '')}"
  REGION="${REGION:-asia-northeast3}"
  SERVICE_NAME="${SERVICE_NAME:-gemini-enterprise-mcp-proxy}"

  if [[ -z "${PROJECT_ID}" ]]; then
    echo "[-] GCP 프로젝트 ID를 찾을 수 없다. .env 에 PROJECT_ID 를 설정하거나 gcloud config set project 를 실행 바란다."
    exit 1
  fi

  echo "[*] Cloud Run 에 사설 MCP 브리지 프록시 배포를 시작한다..."
  echo "    - 프로젝트: ${PROJECT_ID}"
  echo "    - 리전: ${REGION}"
  echo "    - 서비스명: ${SERVICE_NAME}"

  VPC_EGRESS_FLAG=()
  if [[ -n "${VPC_NETWORK:-}" && -n "${VPC_SUBNET:-}" ]]; then
    VPC_EGRESS_FLAG+=(
      "--network=${VPC_NETWORK}"
      "--subnet=${VPC_SUBNET}"
      "--vpc-egress=all-traffic"
    )
  fi

  gcloud run deploy "${SERVICE_NAME}" \
    --source . \
    --project "${PROJECT_ID}" \
    --region "${REGION}" \
    --allow-unauthenticated \
    --set-env-vars "UPSTREAM_MCP_URL=${UPSTREAM_MCP_URL:-http://10.10.0.5:8000/mcp},AUTH_MODE=${AUTH_MODE:-jwt},UPSTREAM_AUTH=${UPSTREAM_AUTH:-none},OAUTH_JWKS_URL=${OAUTH_JWKS_URL:-},OAUTH_AUDIENCE=${OAUTH_AUDIENCE:-}" \
    "${VPC_EGRESS_FLAG[@]}"

  echo "[+] 배포가 완료되었다. 위 서비스 URL 뒤에 /mcp 를 붙여 Gemini Enterprise 커스텀 MCP 서버 URL로 등록 바란다."
  exit 0
fi

exec python3 -u proxy.py "$@"
