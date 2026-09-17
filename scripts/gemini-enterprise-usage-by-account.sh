#!/bin/bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
# gemini-enterprise-usage-by-account.sh
# 주의: 본 코드는 상용 배포용이 아닌 학습 및 데모용 가이드 스크립트다.
# 용도: Model Armor의 Sanitize Operation Logs를 활용하여 Gemini Enterprise의 모든 프롬프트 본문을 감사용으로 실시간 가로채고, 개인별 토큰 사용량을 집계/추정한다.

# 전역 변수 선언 영역이다.
BIGQUERY_DATASET_ID="gcp_logs" # 로그가 적재될 빅쿼리 데이터세트 식별자다.
BIGQUERY_LOCATION="asia-northeast3" # 빅쿼리 데이터세트 리전이다. (기본값 서울)
DAYS=7 # 쿼리 비용 최적화를 위한 최근 조회 기간(일 수)이다.
IAM_ROLE_BIGQUERY="roles/bigquery.dataEditor" # 로그 싱크용 빅쿼리 데이터 편집자 역할이다.
LOG_SINK_NAME="model-armor-logs-sink" # 감사 로그 전송용 로그 싱크 식별자다.
LOG_SINK_SERVICE_ACCOUNT="" # 동적 할당되는 로그 싱크의 서비스 계정이다.
PROJECT_ID=$(gcloud config get-value project 2>/dev/null) # 실행 중인 활성 GCP 프로젝트 ID다.



# DAYS 옵션값 유효성 검증을 처리한다.
if ! [[ "${DAYS}" =~ ^[0-9]+$ ]] || [ "${DAYS}" -le 0 ]; then
  echo "[경고] 유효하지 않은 조회 기간이 입력되어 기본값인 7일로 대체 지정한다."
  DAYS=7
fi

# GCP 프로젝트 ID 감지 여부를 점검한다.
if [ -z "${PROJECT_ID}" ]; then
  echo "[오류] 활성화된 GCP 프로젝트 ID를 감지하지 못했다. gcloud config set project 명령어로 설정하거나 PROJECT_ID 변수를 직접 지정하기 바란다."
  echo "     (참고: gcloud 로그인 필요 시 GCP 콘솔 (https://console.cloud.google.com/ ) 에서 직접 확인 가능하다.)"
  exit 1
fi


# 1. Model Armor API 및 로깅 활성화 점검 단계다.
# (수동 설정 콘솔 주소: https://console.cloud.google.com/security/modelarmor )
echo "[설정 점검] Model Armor API (modelarmor.googleapis.com ) 활성화 여부를 점검한다..."
if ! gcloud services list --enabled --filter="name:modelarmor.googleapis.com" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "[안내] Model Armor API가 비활성화되어 있어 활성화를 진행한다..."
  gcloud services enable modelarmor.googleapis.com --project="${PROJECT_ID}"
else
  echo "[통과] Model Armor API가 이미 활성화되어 있다."
fi


# 2. 빅쿼리 로그 싱크(Log Sink ) 및 로그 라우터 설정 단계다.
# (로그 라우터 설정 콘솔 주소: https://console.cloud.google.com/logs/router )

# 타겟 빅쿼리 데이터세트의 존재 여부를 미리 점검하고 없으면 자동 생성한다.
# (빅쿼리 분석 콘솔 주소: https://console.cloud.google.com/bigquery )
if ! bq show --dataset "${PROJECT_ID}:${BIGQUERY_DATASET_ID}" >/dev/null 2>&1; then
  echo "[안내] 빅쿼리 데이터세트 '${BIGQUERY_DATASET_ID}'가 존재하지 않아 새로 생성한다..."
  bq mk --location="${BIGQUERY_LOCATION}" --dataset "${PROJECT_ID}:${BIGQUERY_DATASET_ID}"
else
  echo "[통과] BigQuery 데이터세트 '${BIGQUERY_DATASET_ID}'가 이미 존재한다."
fi

# 기존 로그 싱크가 있으면 혼선을 줄이기 위해 사전 삭제 처리를 시도한다.
gcloud logging sinks delete "${LOG_SINK_NAME}" --project="${PROJECT_ID}" --quiet >/dev/null 2>&1

# Model Armor의 Sanitize Operation Logs만 필터링하여 빅쿼리로 전송하는 로그 싱크를 생성한다.
echo "[로그 싱크] Model Armor 전용 빅쿼리 로그 싱크 생성 중..."
gcloud logging sinks create "${LOG_SINK_NAME}" \
  "bigquery.googleapis.com/projects/${PROJECT_ID}/datasets/${BIGQUERY_DATASET_ID}" \
  --log-filter='jsonPayload.@type="type.googleapis.com/google.cloud.modelarmor.logging.v1.SanitizeOperationLogEntry"' \
  --project="${PROJECT_ID}"

# 싱크 생성 시 자동 발행된 고유 라이터 서비스 계정 식별자를 추출한다.
LOG_SINK_SERVICE_ACCOUNT=$(gcloud logging sinks describe "${LOG_SINK_NAME}" \
  --project="${PROJECT_ID}" \
  --format="value(writerIdentity)" 2>/dev/null)

# 로그 싱크 서비스 계정에 빅쿼리 데이터 편집자 역할을 위임한다.
# (IAM 설정 콘솔 주소: https://console.cloud.google.com/iam-admin/iam )
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="${LOG_SINK_SERVICE_ACCOUNT}" \
  --role="${IAM_ROLE_BIGQUERY}" \
  --quiet >/dev/null 2>&1


# 3. 빅쿼리 SQL 토큰 분석 및 추정 단계다.
# Model Armor 보안 검사 로그에 수집된 프롬프트 원문 글자 수 길이를 기반으로 토큰 소모량을 근사치로 역계산한다.
# (기본 추정 공식: 영문 4자당 1토큰, 한글 1자당 1.5토큰 수준을 적용하여 가중 계산을 수행한다.)
# (빅쿼리 분석 콘솔 주소: https://console.cloud.google.com/bigquery )
echo ""
echo "========================================================================"
echo "[실행 안내] 빅쿼리에 스트리밍 적재된 Model Armor 보안 검사 로그 분석 SQL을 구동한다."
echo "========================================================================"

# 빅쿼리에 타겟 감사 로그 테이블이 존재하고 데이터가 적재되었는지 점검한다.
TABLE_EXISTS=$(bq ls --project_id="${PROJECT_ID}" "${BIGQUERY_DATASET_ID}" 2>/dev/null | grep -c "modelarmor_googleapis_com_sanitize_operations")

if [ "${TABLE_EXISTS}" -eq 0 ]; then
  echo "[안내] 빅쿼리에 'modelarmor_googleapis_com_sanitize_operations_*' 테이블이 존재하지 않는다."
  echo "     Model Armor 보안 검사를 호출하지 않았거나, 로그가 아직 빅쿼리 데이터세트로 전송되지 않았을 수 있다."
  echo "     Model Armor 보안 검사를 1회 이상 진행한 후 로그 스트리밍 적재를 기다렸다가 다시 실행하기 바란다."
else
  bq query --use_legacy_sql=false "
    SELECT 
      -- 호출자 식별 정보 (감사 로그 조인 또는 클라이언트 레이블 참조)
      COALESCE(
        JSON_VALUE(jsonPayload.metadata.client_correlation_id),
        JSON_VALUE(labels[\"modelarmor.googleapis.com/client_name\"]),
        'unknown_principal'
      ) AS principal_identity,
     
     -- 검사 호출 횟수
     COUNT(1) AS inspection_count,
     
     -- 가로챈 유저 프롬프트 본문 기반의 근사치 토큰 사용량 계산 (영문/한글 가중치 추정 공식 적용)
     SUM(
       CAST(
         ROUND(
           CHARACTER_LENGTH(JSON_VALUE(jsonPayload.userPrompt.content)) * 1.2
         ) AS INT64
       )
     ) AS estimated_prompt_tokens,
     
     -- 가로챈 모델 응답 본문 기반의 근사치 토큰 사용량 계산
     SUM(
       CAST(
         ROUND(
           CHARACTER_LENGTH(JSON_VALUE(jsonPayload.modelResponse.content)) * 1.5
         ) AS INT64
       )
     ) AS estimated_response_tokens,
  
     -- 총 추정 토큰 사용량 합산
     SUM(
       CAST(
         ROUND(
           (CHARACTER_LENGTH(JSON_VALUE(jsonPayload.userPrompt.content)) * 1.2) +
           (CHARACTER_LENGTH(JSON_VALUE(jsonPayload.modelResponse.content)) * 1.5)
         ) AS INT64
       )
     ) AS estimated_total_tokens
  
   FROM \`${PROJECT_ID}.${BIGQUERY_DATASET_ID}.modelarmor_googleapis_com_sanitize_operations_*\`
   WHERE _TABLE_SUFFIX >= FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL ${DAYS} DAY))
   GROUP BY principal_identity
   ORDER BY estimated_total_tokens DESC;
  "
fi

echo "========================================================================"
echo "[가이드 완료] Model Armor 우회 프롬프트 가로채기 및 토큰 사용량 추정 테스트 가이드를 종료한다."
echo "========================================================================"
