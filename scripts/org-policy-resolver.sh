#!/bin/bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
# org-policy-resolver.sh
# 주의: 본 코드는 상용 배포용이 아닌 학습 및 데모용 가이드다.
# 용도: GCP 최근 조직 정책(Organization Policy ) 위반 감사 로그를 분석하여 해결 명령어를 처방하는 도구다.

# 전역 변수 선언 영역이다.
DAYS=7 # 감사 로그 조회 기준 기간(일 수)이다.
LIMIT_COUNT=5 # 진단할 실패 로그 최대 개수다.
PROJECT_ID=$(gcloud config get-value project 2>/dev/null) # 실행 중인 활성 GCP 프로젝트 ID다.



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

echo "[자가 진단 시작] 최근 발생한 GCP 조직 정책 위반 실패 감사 로그 역추적을 시작한다..."
echo "타겟 GCP 프로젝트 ID: ${PROJECT_ID}"
echo "조회 대상 기간: 최근 ${DAYS}일"
echo "조회 대상 로그 개수: 최대 ${LIMIT_COUNT}개"
echo "------------------------------------------------------------------------"

# DAYS를 기준으로 UTC 포맷 시작 날짜를 도출한다. macOS와 Linux 운영체제(OS) 환경을 모두 지원한다.
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS (BSD date) 환경인 경우
  START_DATE=$(date -u -v-"${DAYS}"d +%Y-%m-%dT%H:%M:%SZ)
else
  # Linux (GNU date) 환경인 경우
  START_DATE=$(date -u -d "${DAYS} days ago" +%Y-%m-%dT%H:%M:%SZ)
fi

# 에러 코드가 9 (Failed Precondition) 혹은 상태 메시지에 제약 조건 위반이 포함된 감사 로그를 필터링한다.
# 로그 쿼리 콘솔 주소: https://console.cloud.google.com/logs/query 
FILTER="logName:\"projects/${PROJECT_ID}/logs/cloudaudit.googleapis.com%2Factivity\" AND (protoPayload.status.code=9 OR protoPayload.status.message:\"Constraint\" OR protoPayload.status.message:\"violated\") AND timestamp>=\"${START_DATE}\""

# gcloud 로깅 명령어를 실행하여 최근 실패 기록을 추출한다.
RAW_LOGS=$(gcloud logging read "${FILTER}" \
  --project="${PROJECT_ID}" \
  --format="value(protoPayload.authenticationInfo.principalEmail, protoPayload.serviceName, protoPayload.methodName, protoPayload.status.message)" \
  --limit="${LIMIT_COUNT}" 2>/dev/null)

if [ -z "${RAW_LOGS}" ]; then
  echo "[성공] GCP 조직 정책 제약 조건(Constraints ) 위반 실패 감사 로그 사례가 발견되지 않았다. 안전하다!"
  echo "     (참고: 조직 정책 설정은 GCP 조직 정책 콘솔 주소(https://console.cloud.google.com/iam-admin/orgpolicies )에서 직접 제어 가능하다.)"
  exit 0
fi

echo "발견된 최근 조직 정책 위반 내역 및 복구 처방 가이드:"
echo "========================================================================"

# 로그 결과를 파싱하여 처방을 출력한다.
# principalEmail, serviceName, methodName, message
FOUND_ATTEMPTS=0
while IFS=$'\t' read -r PRINCIPAL_EMAIL SERVICE_NAME METHOD_NAME STATUS_MESSAGE; do
  if [ -z "${PRINCIPAL_EMAIL}" ] || [ -z "${SERVICE_NAME}" ]; then
    continue
  fi

  # 에러 메시지에서 제약 조건 ID를 동적으로 추출한다.
  CONSTRAINT_ID=$(echo "${STATUS_MESSAGE}" | grep -o -E "constraints/[a-zA-Z0-9.]+" | head -n 1)
  if [ -z "${CONSTRAINT_ID}" ]; then
    # 명시적 제약 조건 이름이 없다면 범용 제약 조건 식별자로 매핑한다.
    CONSTRAINT_ID="constraints/unknown"
  fi

  FOUND_ATTEMPTS=$((FOUND_ATTEMPTS + 1))
  echo "[위반 실패 건 #${FOUND_ATTEMPTS}]"
  echo "  - 실패 주체 계정: ${PRINCIPAL_EMAIL}"
  echo "  - 요청 대상 서비스: ${SERVICE_NAME}"
  echo "  - 실행 실패 액션: ${METHOD_NAME}"
  echo "  - 실제 오류 내용: ${STATUS_MESSAGE}"
  echo ""

  # 실패한 제약 조건별 처방 및 권장 해결책 매핑 처리
  SHORT_CONSTRAINT="${CONSTRAINT_ID#constraints/}"
  RECOMMENDED_ACTION=""
  POLICY_DESC=""

  case "${CONSTRAINT_ID}" in
    constraints/iam.disableServiceAccountKeyCreation)
      POLICY_DESC="서비스 계정 키 생성을 차단하는 제약 사항이다."
      RECOMMENDED_ACTION="안전한 인증을 위해 워크로드 아이덴티티(Workload Identity ) 연동 권장하나, 테스트 목적상 키 발급이 필요하면 제약을 해제할 수 있다."
      ;;
    constraints/compute.vmExternalIpAccess)
      POLICY_DESC="VM 인스턴스에 외부 IP 주소 할당을 차단하는 제약 사항이다."
      RECOMMENDED_ACTION="내부 IP 전용 VM 사용 및 Cloud NAT 구성을 권장하나, 외부 IP가 필요한 경우 제약을 해제할 수 있다."
      ;;
    constraints/storage.publicAccessPrevention)
      POLICY_DESC="스토리지 버킷의 공용 공개 액세스를 차단하는 제약 사항이다."
      RECOMMENDED_ACTION="비공개 액세스 유지를 권장하나, 정적 웹사이트 호스팅 등 공용 배포가 필요할 경우 제약을 해제할 수 있다."
      ;;
    *)
      POLICY_DESC="조직 정책에 의해 설정된 자원 생성 및 제어 규약 제약 사항이다."
      RECOMMENDED_ACTION="보안 정책상 위반 상태다. 우회가 필요한 경우 아래 제약 해제 명령을 검토하기 바란다."
      ;;
  esac

  echo "  [정밀 처방 제약 조건 분석]"
  echo "    - 검출 제약 사항: ${CONSTRAINT_ID}"
  echo "    - 제약 조건 설명: ${POLICY_DESC}"
  echo "    - 권장 임시 방안: ${RECOMMENDED_ACTION}"
  echo ""
  
  if [ "${SHORT_CONSTRAINT}" != "unknown" ]; then
    echo "  [즉시 조치 가능한 원클릭 gcloud 해결 명령어]"
    echo "    gcloud resource-manager org-policies disable-enforce \"${SHORT_CONSTRAINT}\" \\"
    echo "      --project=\"${PROJECT_ID}\""
  else
    echo "  [즉시 조치 가능한 가이드]"
    echo "    실제 거부 사유 구문에서 구체적인 제약 명칭을 파싱하지 못했다. 상단의 에러 로그를 점검하여 조직 정책에서 알맞은 예외 정책을 매핑하기 바란다."
  fi
  echo "------------------------------------------------------------------------"

done <<< "${RAW_LOGS}"

echo "[진단 완료] 분석된 정책 비활성화 명령어를 복사하여 프로젝트 관리자 계정 터미널에서 실행하기 바란다."
echo "     (GCP 조직 정책 설정 콘솔 주소: https://console.cloud.google.com/iam-admin/orgpolicies )"
