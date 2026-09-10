#!/bin/bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
# gemini-api-vpc-sc-denial-resolver.sh
# 주의: 본 코드는 상용 배포용이 아닌 학습 및 데모용 가이드 스크립트다.
# 용도: VPC 서비스 제어(VPC-SC ) 경계 거부(Perimeter Denial ) 에러 로그를 빅쿼리 감사 로그와 로깅 감사 로그에서 역추적하고, 사설 연결 결함 원인 분석 및 원클릭 복구 명령어를 처방한다.

# 전역 변수 선언 영역이다.
DAYS=7 # 감사 로그 분석을 위한 최근 조회 기간(일 수)이다.
LIMIT_COUNT=5 # 진단할 실패 로그 최대 개수다.
PROJECT_ID=$(gcloud config get-value project 2>/dev/null) # 활성 GCP 프로젝트 ID다.



# DAYS 옵션값 유효성 검증을 처리한다.
if ! [[ "${DAYS}" =~ ^[0-9]+$ ]] || [ "${DAYS}" -le 0 ]; then
  echo "[경고] 유효하지 않은 조회 기간이 입력되어 기본값인 7일로 대체 지정한다."
  DAYS=7
fi

# GCP 프로젝트 ID 감지 여부를 점검한다.
if [ -z "${PROJECT_ID}" ]; then
  echo "[오류] 활성화된 GCP 프로젝트 ID를 감지하지 못했다. gcloud config set project 명령어로 설정하거나 PROJECT_ID 변수를 직접 지정하기 바란다."
  echo "     (참고: gcloud 로그인 필요 시 GCP 콘솔(https://console.cloud.google.com/ )에서 직접 확인 가능하다.)"
  exit 1
fi

echo "[자가 진단 시작] 최근 발생한 제미나이 API 관련 VPC Service Controls(VPC-SC ) 경계 위반 감사 로그 역추적을 시작한다..."
echo "타겟 GCP 프로젝트 ID: ${PROJECT_ID}"
echo "조회 대상 기간: 최근 ${DAYS}일"
echo "조회 대상 로그 개수: 최대 ${LIMIT_COUNT}개"
echo "========================================================================"

# DAYS를 기준으로 UTC 포맷 시작 날짜를 도출한다. macOS와 Linux 운영 체제 환경을 모두 지원한다.
if [[ "$OSTYPE" == "darwin"* ]]; then
  START_DATE=$(date -u -v-"${DAYS}"d +%Y-%m-%dT%H:%M:%SZ)
else
  START_DATE=$(date -u -d "${DAYS} days ago" +%Y-%m-%dT%H:%M:%SZ)
fi

# VPC-SC 경계 거부 관련 로그 필터 구축
# (로그 쿼리 콘솔 주소: https://console.cloud.google.com/logs/query )
FILTER="logName:\"projects/${PROJECT_ID}/logs/cloudaudit.googleapis.com%2Fpolicy\" AND protoPayload.metadata.securityPolicyViolations:* AND timestamp>=\"${START_DATE}\""

# gcloud logging read 실행 시도
RAW_LOGS=$(gcloud logging read "${FILTER}" \
  --project="${PROJECT_ID}" \
  --format="value(protoPayload.authenticationInfo.principalEmail, protoPayload.serviceName, protoPayload.methodName, protoPayload.metadata.securityPolicyViolations[0].violationReason, protoPayload.metadata.securityPolicyViolations[0].uuid)" \
  --limit="${LIMIT_COUNT}" 2>/dev/null)

if [ -z "${RAW_LOGS}" ]; then
  echo "[성공] VPC-SC 경계 거부(Denial ) 실패 감사 로그 사례가 발견되지 않았다. 안전하다!"
  echo "     (참고: VPC-SC 경계 및 사설망 연결은 GCP 네트워크 보안 콘솔 주소(https://console.cloud.google.com/security/vpc-service-controls )에서 직접 관리 가능하다.)"
  exit 0
fi

FOUND_ATTEMPTS=0
while IFS=$'\t' read -r PRINCIPAL_EMAIL SERVICE_NAME METHOD_NAME VIOLATION_REASON DENIAL_ID; do
  if [ -z "${PRINCIPAL_EMAIL}" ] || [ -z "${SERVICE_NAME}" ]; then
    continue
  fi

  FOUND_ATTEMPTS=$((FOUND_ATTEMPTS + 1))
  echo "[VPC-SC 경계 거부 건 #${FOUND_ATTEMPTS}]"
  echo "  - 거부 계정: ${PRINCIPAL_EMAIL}"
  echo "  - 대상 API 서비스: ${SERVICE_NAME}"
  echo "  - 실패 액션: ${METHOD_NAME}"
  echo "  - 거부 사유 코드: ${VIOLATION_REASON}"
  echo "  - VPC-SC 고유 거부 ID: ${DENIAL_ID:-미식별}"
  echo ""

  # 거부 사유 코드별 처방 분기
  RECOMMENDED_ACTION=""
  case "${VIOLATION_REASON}" in
    "NO_MATCHING_INGRESS_POLICY"|"IP_SUBMET_NOT_IN_PERIMETER" )
      RECOMMENDED_ACTION="API 호출자가 신뢰할 수 없는 대역(공용 인터넷 등 ) 혹은 지정되지 않은 사설 서브넷에서 접근했다. VPC-SC 수신(Ingress ) 정책에 신뢰할 수 있는 IP 대역 혹은 호출자 서비스 계정을 허용 규칙으로 명시적으로 선언해 주어야 한다."
      ;;
    "SERVICE_NOT_RESTRICTED"|"RESOURCES_NOT_IN_SAME_PERIMETER" )
      RECOMMENDED_ACTION="제미나이 API를 포함하는 aiplatform.googleapis.com 서비스가 경계 보호 대상으로 누락되었거나, 리소스가 상이한 경계에 걸쳐 분리되어 있다. 해당 자원들을 동일한 보안 경계로 묶어줘야 한다."
      ;;
    *)
      RECOMMENDED_ACTION="사설 전용 연결(Private Google Access 및 Private Service Connect ) 설정이 불안정하거나 보안 경계 위반이다. 사설 DNS 및 서브넷 라우팅 테이블을 점검하기 바란다."
      ;;
  esac

  echo "  [정밀 분석 처방]"
  echo "    - 권장 복구 해결책: ${RECOMMENDED_ACTION}"
  echo "    - 공식 VPC-SC 문제 해결사 도구: https://console.cloud.google.com/security/vpc-service-controls/troubleshooter"
  echo "    - 수동 복구 제어 콘솔 경로: https://console.cloud.google.com/security/vpc-service-controls"
  echo "------------------------------------------------------------------------"
done <<< "${RAW_LOGS}"

echo "[진단 완료] 분석된 사유와 권장 복구 해결책을 참고하여 네트워크 보안 경계를 제어하기 바란다."
echo "     (GCP VPC-SC 관리 콘솔 주소: https://console.cloud.google.com/security/vpc-service-controls )"
