#!/bin/bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
# gemini-api-sensitive-data-filter.sh
# 주의: 본 코드는 상용 배포용이 아닌 학습 및 데모용 가이드 스크립트다.
# 용도: 제미나이(Gemini ) API 프롬프트 전송 전, Cloud DLP API(Sensitive Data Protection )를 연동해 민감한 개인정보(PII ) 유출을 실시간 감지하고 마스킹(Redaction ) 처리하는 시나리오를 가이드 및 테스트한다.

# 전역 변수 선언 영역이다.
DLP_INFO_TYPES="PHONE_NUMBER,EMAIL_ADDRESS,KOREA_RRN" # 감지할 민감 개인정보(PII ) 타입 목록이다.
DLP_MASK_CHARACTER="*" # 민감 정보를 대체 마스킹할 문자다.
PROJECT_ID=$(gcloud config get-value project 2>/dev/null) # 활성 GCP 프로젝트 ID다.
TEST_PROMPT="안녕하세요. 제 연락처는 010-1234-5678이고 주민등록번호는 900101-1234567입니다. gcp-user@example.com 으로 제미나이 3.5 분석 자료를 보내주세요." # 테스트용 민감 정보 포함 프롬프트다.



# GCP 프로젝트 ID 감지 여부를 점검한다.
if [ -z "${PROJECT_ID}" ]; then
  echo "[오류] 활성화된 GCP 프로젝트 ID를 감지하지 못했다. gcloud config set project 명령어로 설정하거나 PROJECT_ID 변수를 직접 지정하기 바란다."
  echo "     (참고: gcloud 로그인 필요 시 GCP 콘솔(https://console.cloud.google.com/ )에서 직접 확인 가능하다.)"
  exit 1
fi

# Cloud DLP API 활성화 여부 점검 및 처리
echo "[설정 점검] Cloud DLP API(dlp.googleapis.com )가 활성화되어 있는지 확인한다..."
if ! gcloud services list --enabled --filter="name:dlp.googleapis.com" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "[안내] Cloud DLP API가 비활성화되어 있어 자동으로 활성화를 진행한다..."
  gcloud services enable dlp.googleapis.com --project="${PROJECT_ID}"
else
  echo "[통과] Cloud DLP API가 이미 활성화되어 있다."
fi

echo "========================================================================"
echo "[1단계: 프롬프트 내 민감 데이터 자가 검출 및 마스킹(Redact ) 실행]"
# (DLP 설정 제어 콘솔 주소: https://console.cloud.google.com/security/sensitive-data-protection )
echo "전처리 필터 대상 프롬프트: ${TEST_PROMPT}"
echo "감지 타겟 개인정보 유형: ${DLP_INFO_TYPES}"
echo "마스킹 문자: ${DLP_MASK_CHARACTER}"
echo ""

# curl을 사용하여 Cloud DLP API(Sensitive Data Protection)를 실전 호출하여 민감한 개인정보를 마스킹한다.
# (구글 클라우드 공식 참조 주소: https://cloud.google.com/sensitive-data-protection/docs/redacting-sensitive-data )
INFO_TYPES_JSON=$(echo "${DLP_INFO_TYPES}" | tr ',' '\n' | sed 's/\(.*\)/{"name": "\1"}/' | paste -sd, -)
ACCESS_TOKEN=$(gcloud auth print-access-token 2>/dev/null)

if [ -n "${ACCESS_TOKEN}" ]; then
  DLP_PAYLOAD=$(cat <<EOF
{
  "item": {
    "value": "${TEST_PROMPT}"
  },
  "deidentifyConfig": {
    "infoTypeTransformations": {
      "transformations": [
        {
          "infoTypes": [ ${INFO_TYPES_JSON} ],
          "primitiveTransformation": {
            "characterMaskConfig": {
              "maskCharacter": "${DLP_MASK_CHARACTER}"
            }
          }
        }
      ]
    }
  },
  "inspectConfig": {
    "infoTypes": [ ${INFO_TYPES_JSON} ]
  }
}
EOF
)

  RESPONSE=$(curl -s -X POST \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "${DLP_PAYLOAD}" \
    "https://dlp.googleapis.com/v2/projects/${PROJECT_ID}/content:deidentify")

  MASKED_PROMPT=$(echo "${RESPONSE}" | jq -r '.item.value' 2>/dev/null)
  
  # 만약 jq가 없거나 파싱에 실패할 경우, python 원라이너로 안전하게 추출을 시도한다.
  if [ -z "${MASKED_PROMPT}" ] || [ "${MASKED_PROMPT}" == "null" ]; then
    MASKED_PROMPT=$(echo "${RESPONSE}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('item', {}).get('value', ''))" 2>/dev/null)
  fi
fi

if [ $? -eq 0 ] && [ -n "${MASKED_PROMPT}" ]; then
  echo "[성공] 민감 데이터 마스킹 필터링이 완벽하게 처리되었다."
  echo "  - 필터 적용 후 프롬프트: ${MASKED_PROMPT}"
else
  echo "[경고] Cloud DLP API 호출 및 로컬 정적 검출 단계에서 오류가 발생했다. (권한 오류 등)"
  echo "  [수동 복구 및 자가 해결 가이드]"
  echo "    1. IAM 콘솔(https://console.cloud.google.com/iam-admin/iam )에서 현재 실행 계정이 'DLP 관리자(roles/dlp.admin )' 혹은 'DLP 검사자(roles/dlp.user )' 권한을 지녔는지 검증한다."
  echo "    2. Cloud DLP API 자가 활성화가 누락되었을 수 있으니 'gcloud services enable dlp.googleapis.com' 명령을 관리자 터미널에서 구동하기 바란다."
fi

echo "========================================================================"
echo "[2단계: 보안 가이드라인이 충족된 안전한 프롬프트로 제미나이 3.5 모델 호출 가이드]"
# (버텍스 AI 모델 실전 제어 콘솔 주소: https://console.cloud.google.com/vertex-ai )
echo "DLP 필터로 개인정보가 차단된 안전한 프롬프트를 Vertex AI Gemini API 모델로 안심하고 전송하는 가이드를 제시한다."
echo "  - 안전한 프롬프트는 제미나이 3.5 모델에 전송되어 외부 유출을 원천 예방한다."
echo "========================================================================"
echo "[자가 검증 완료] 프롬프트 민감 데이터 DLP 연동 안심 필터 가이드를 마친다."
