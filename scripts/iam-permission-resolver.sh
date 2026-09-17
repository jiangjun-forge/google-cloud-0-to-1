#!/bin/bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
# iam-permission-resolver.sh
# 주의: 본 코드는 상용 배포용이 아닌 학습 및 데모용 가이드다.
# 용도: GCP 최근 권한 거부 감사 로그를 분석하여 필요한 IAM 역할과 해결 명령어를 처방하는 도구다.

# 전역 변수 선언 영역이다.
DAYS=7 # 감사 로그 조회 기준 기간(일 수 )이다.
LIMIT_COUNT=5 # 진단할 실패 로그 최대 개수다.
PROJECT_ID=$(gcloud config get-value project 2>/dev/null) # 실행 중인 활성 GCP 프로젝트 ID다.



# DAYS 옵션값 유효성 검증을 처리한다.
if ! [[ "${DAYS}" =~ ^[0-9]+$ ]] || [ "${DAYS}" -le 0 ]; then
  echo "[경고] 유효하지 않은 조회 기간이 입력되어 기본값인 7일로 대체 지정한다."
  DAYS=7
fi

# 활성 GCP 프로젝트 ID 감지 여부를 점검한다.
if [ -z "${PROJECT_ID}" ]; then
  echo "[오류] 활성화된 GCP 프로젝트 ID를 감지하지 못했다. gcloud config set project 명령어로 설정하거나 PROJECT_ID 변수를 직접 지정하기 바란다."
  echo "     (참고: gcloud 로그인 필요 시 GCP 콘솔(https://console.cloud.google.com/ )에서 직접 확인 가능하다.)"
  exit 1
fi

echo "[자가 진단 시작] 최근 발생한 구글 클라우드 권한 실패 감사 로그 역추적을 시작한다..."
echo "타겟 GCP 프로젝트 ID: ${PROJECT_ID}"
echo "조회 대상 기간: 최근 ${DAYS}일"
echo "조회 대상 로그 개수: 최대 ${LIMIT_COUNT}개"
echo "------------------------------------------------------------------------"

# DAYS를 기준으로 UTC 포맷 시작 날짜를 도출한다. macOS와 Linux 운영 체제(OS) 환경을 모두 지원한다.
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS (BSD date) 환경인 경우
  START_DATE=$(date -u -v-"${DAYS}"d +%Y-%m-%dT%H:%M:%SZ)
else
  # Linux (GNU date) 환경인 경우
  START_DATE=$(date -u -d "${DAYS} days ago" +%Y-%m-%dT%H:%M:%SZ)
fi

# 데이터 액세스 권한 거부 감사 로그 필터를 구성한다.
# (로그 쿼리 콘솔 주소: https://console.cloud.google.com/logs/query )
FILTER="logName:\"projects/${PROJECT_ID}/logs/cloudaudit.googleapis.com%2Fdata_access\" AND (protoPayload.status.code=7 OR protoPayload.status.message:\"Permission denied\" OR protoPayload.status.message:\"Forbidden\") AND timestamp>=\"${START_DATE}\""

# gcloud 로깅 명령어를 실행하여 최근 실패 기록을 추출한다.
RAW_LOGS=$(gcloud logging read "${FILTER}" \
  --project="${PROJECT_ID}" \
  --format="value(protoPayload.authenticationInfo.principalEmail, protoPayload.serviceName, protoPayload.methodName, protoPayload.status.message)" \
  --limit="${LIMIT_COUNT}" 2>/dev/null)

if [ -z "${RAW_LOGS}" ]; then
  echo "[성공] 데이터 액세스 권한 거부 감사 로그 실패 사례가 발견되지 않았다. 안전하다!"
  echo "     (참고: IAM 설정 관리는 GCP IAM 콘솔 주소(https://console.cloud.google.com/iam-admin/iam )에서 직접 제어 가능하다.)"
  exit 0
fi

echo "발견된 최근 실패 내역 및 복구 처방 가이드:"
echo "========================================================================"

# 로그 결과를 파싱하여 처방을 출력한다.
# principalEmail, serviceName, methodName, message
FOUND_ATTEMPTS=0
while IFS=$'\t' read -r PRINCIPAL_EMAIL SERVICE_NAME METHOD_NAME STATUS_MESSAGE; do
  if [ -z "${PRINCIPAL_EMAIL}" ] || [ -z "${SERVICE_NAME}" ]; then
    continue
  fi

  FOUND_ATTEMPTS=$((FOUND_ATTEMPTS + 1))
  echo "[실패 건 #${FOUND_ATTEMPTS}]"
  echo "  - 실패 주체 계정: ${PRINCIPAL_EMAIL}"
  echo "  - 요청 대상 서비스: ${SERVICE_NAME}"
  echo "  - 실행 실패 액션: ${METHOD_NAME}"
  echo "  - 실제 오류 내용: ${STATUS_MESSAGE}"
  echo ""

  # 실패한 서비스 이름별 권장 IAM 역할 매핑 처리
  RECOMMENDED_ROLE=""
  ROLE_DESC=""

  case "${SERVICE_NAME}" in
    aiplatform.googleapis.com)
      RECOMMENDED_ROLE="roles/aiplatform.user"
      ROLE_DESC="제미나이 호출 및 Vertex AI 제품군 리소스 사용 권한이다."
      ;;
    bigquery.googleapis.com)
      RECOMMENDED_ROLE="roles/bigquery.dataEditor"
      ROLE_DESC="빅쿼리 데이터세트 수정 및 테이블 데이터 편집 권한이다."
      ;;
    storage.googleapis.com)
      RECOMMENDED_ROLE="roles/storage.objectViewer"
      ROLE_DESC="클라우드 스토리지 버킷 객체 조회 뷰어 권한이다."
      ;;
    logging.googleapis.com)
      RECOMMENDED_ROLE="roles/logging.viewer"
      ROLE_DESC="클라우드 로깅 로그 조회 뷰어 권한이다."
      ;;
    *)
      RECOMMENDED_ROLE="roles/viewer"
      ROLE_DESC="서비스 조회에 필요한 기본 프로젝트 뷰어 권한이다."
      ;;
  esac

  # 주체 이메일 성격을 분석하여 gcloud 바인딩 멤버 형태 동적 분기 결정
  MEMBER_TYPE="user"
  if [[ "${PRINCIPAL_EMAIL}" == *"gserviceaccount.com"* ]]; then
    MEMBER_TYPE="serviceAccount"
  fi

  echo "  [정밀 처방 역할 추천]"
  echo "    - 권장 역할: ${RECOMMENDED_ROLE}"
  echo "    - 역할 상세: ${ROLE_DESC}"
  echo ""
  echo "  [즉시 조치 가능한 원클릭 gcloud 해결 명령어]"
  echo "    gcloud projects add-iam-policy-binding \"${PROJECT_ID}\" \\"
  echo "      --member=\"${MEMBER_TYPE}:${PRINCIPAL_EMAIL}\" \\"
  echo "      --role=\"${RECOMMENDED_ROLE}\""
  echo "------------------------------------------------------------------------"

done <<< "${RAW_LOGS}"

echo "[진단 완료] 분석된 해결 명령어를 복사하여 프로젝트 관리자 계정 터미널에서 즉시 실행하기 바란다."
echo "     (GCP IAM 콘솔 교차 점검 주소: https://console.cloud.google.com/iam-admin/iam )"
