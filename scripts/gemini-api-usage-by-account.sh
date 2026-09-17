#!/bin/bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
# gemini-api-usage-by-account.sh
# 주의: 본 코드는 상용 배포용이 아닌 학습 및 데모용 가이드다.
# 용도: 요청/응답 자동 로깅 테이블로부터 사용자별 요청 횟수와 상세 토큰 소모량을 집계 및 모니터링한다.

# 전역 변수 선언 영역이다.
BIGQUERY_DATASET_ID="gcp_logs" # 로그가 적재될 빅쿼리 데이터세트 식별자다.
BIGQUERY_LOCATION="asia-northeast3" # 빅쿼리 데이터세트 리전이다. (기본값 서울)
DAYS=7 # 쿼리 비용 최적화를 위한 최근 조회 기간(일 수)이다.
PROJECT_ID=$(gcloud config get-value project 2>/dev/null) # 실행 중인 활성 GCP 프로젝트 ID다.
TABLE_NAME="request_response_logging" # 토큰 소모량이 적재되는 요청/응답 로깅 테이블 이름이다.



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


# 1. 빅쿼리 데이터세트 및 테이블 존재 여부 점검 단계다.
# (빅쿼리 분석 콘솔 주소: https://console.cloud.google.com/bigquery )

if ! bq show --dataset "${PROJECT_ID}:${BIGQUERY_DATASET_ID}" >/dev/null 2>&1; then
  echo "[안내] 빅쿼리 데이터세트 '${BIGQUERY_DATASET_ID}'가 존재하지 않아 새로 생성한다..."
  bq mk --location="${BIGQUERY_LOCATION}" --dataset "${PROJECT_ID}:${BIGQUERY_DATASET_ID}"
else
  echo "[통과] 빅쿼리 데이터세트 '${BIGQUERY_DATASET_ID}'가 이미 존재한다."
fi

# 요청/응답 로깅 테이블의 존재 여부를 점검한다.
if ! bq show "${PROJECT_ID}:${BIGQUERY_DATASET_ID}.${TABLE_NAME}" >/dev/null 2>&1; then
  echo "[오류] '${TABLE_NAME}' 테이블이 존재하지 않는다."
  echo "       이 오류를 해결하려면 먼저 'gemini-api-request-response-logging.sh' 스크립트를 구동하여"
  echo "       파운데이션 모델의 자동 로깅 설정을 활성화하고 API를 호출하기 바란다."
  exit 1
fi


# 2. 빅쿼리 SQL 조회 단계다.
# 비용 최적화를 위해 파티션 필터 조건을 설정하여 최근 DAYS일 데이터만 조회한다.
bq query --use_legacy_sql=false "
 SELECT COALESCE(JSON_EXTRACT_SCALAR(full_request, '\$.labels.principal_email'), 'default_user') AS user_email,
        COUNT(1) AS request_count,
        SUM(LAX_INT64(full_response.usageMetadata.promptTokenCount)) AS total_input_tokens,
        SUM(LAX_INT64(full_response.usageMetadata.candidatesTokenCount)) AS total_output_tokens,
        SUM(LAX_INT64(full_response.usageMetadata.thoughtsTokenCount)) AS total_thinking_tokens
   FROM \`${PROJECT_ID}.${BIGQUERY_DATASET_ID}.${TABLE_NAME}\`
  WHERE logging_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL ${DAYS} DAY)
  GROUP BY user_email
  ORDER BY request_count DESC;
"
