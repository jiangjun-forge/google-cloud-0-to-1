#!/bin/bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
# gemini-api-request-response-logging.sh
# 주의: 본 코드는 상용 배포용이 아닌 학습 및 데모용 가이드다.
# 용도: 엔드포인트 생성 없이 파운데이션 모델(Foundation Model) 자체에 요청/응답 빅쿼리 자동 로깅을 설정하고 호출한다.

# 전역 변수 선언 영역이다.
BIGQUERY_DATASET_ID="gcp_logs" # 로그 적재용 빅쿼리 데이터세트 ID
LOCATION_ID="global" # 모델 호출 리전 ID
MODEL_ID="gemini-3.5-flash" # 호출할 모델 식별자
PROJECT_ID=$(gcloud config get-value project 2>/dev/null) # 활성 GCP 프로젝트 ID


# 1. 필수 SDK 설치 확인
if ! python3 -c "import google.genai" >/dev/null 2>&1 || ! python3 -c "import vertexai" >/dev/null 2>&1; then
  pip3 install --quiet google-genai google-cloud-aiplatform
fi


# 2. 파운데이션 모델 로깅 활성화 및 테스트 호출을 수행한다.
python3 - <<EOF
from google import genai
from google.cloud import bigquery
from google.genai import types
from vertexai.preview.generative_models import GenerativeModel
import os
import vertexai

# 제어 영역 기능 설정을 위해 불가피하게 vertexai SDK를 병행 사용한다.
# Vertex AI 환경 초기화 단계다.
vertexai.init(project="${PROJECT_ID}", location="${LOCATION_ID}")

# 대상 빅쿼리 데이터세트를 사전에 생성한다.
try:
  bq_client = bigquery.Client(project="${PROJECT_ID}")
  dataset_id = "${BIGQUERY_DATASET_ID}"
  dataset_ref = bq_client.dataset(dataset_id)
  dataset = bigquery.Dataset(dataset_ref)
  dataset.location = "US"
  bq_client.create_dataset(dataset, exists_ok=True)
except Exception as e:
  print(f"[안내] 데이터세트 사전 생성 중 예외가 발생했으나 계속 진행한다: {e}")

# 파운데이션 모델 제어 인스턴스 초기화
control_model = GenerativeModel("${MODEL_ID}")

# 파운데이션 모델 자체에 빅쿼리 요청/응답 자동 로깅 설정을 활성화한다.
try:
  control_model.set_request_response_logging_config(
    enabled=True,
    sampling_rate=1.0,
    bigquery_destination="bq://${PROJECT_ID}.${BIGQUERY_DATASET_ID}"
  )
except Exception as e:
  print(f"[안내] 로깅 설정 활성화 중 예외가 발생했으나 계속 진행한다 (이미 설정되었을 수 있음): {e}")

# 신규 google-genai SDK 기반으로 예측 호출을 실행한다.
client = genai.Client(
  vertexai=True,
  project="${PROJECT_ID}",
  location="${LOCATION_ID}"
)

response = client.models.generate_content(
  model="${MODEL_ID}",
  contents="구글 클라우드의 주요 특징을 두 가지만 요약해라."
)

print("\n=== [제미나이 답변 결과] ===")
print(response.text)
print("============================\n")
EOF


# 3. 빅쿼리 자동 생성 테이블 및 사용자별 토큰 사용량 집계 단계다.
sleep 15
TABLE_NAME=$(bq ls --format=sparse "${PROJECT_ID}:${BIGQUERY_DATASET_ID}" | grep -E "(logging_[a-zA-Z0-9_]+|[a-zA-Z0-9_]+_logging)" | head -n 1 | awk '{print $1}')

if [ -n "${TABLE_NAME}" ]; then
  bq query --use_legacy_sql=false \
    "SELECT COUNT(1) as call_count, \
            SUM(LAX_INT64(full_response.usageMetadata.candidatesTokenCount)) as total_candidate_tokens, \
            SUM(LAX_INT64(full_response.usageMetadata.promptTokenCount)) as total_prompt_tokens, \
            SUM(LAX_INT64(full_response.usageMetadata.totalTokenCount)) as total_tokens, \
            COALESCE(JSON_EXTRACT_SCALAR(full_request, '\$.labels.principal_email'), 'default_user') as user_email \
       FROM \`${PROJECT_ID}.${BIGQUERY_DATASET_ID}.${TABLE_NAME}\` \
      WHERE logging_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY) \
      GROUP BY user_email \
      ORDER BY total_tokens DESC;"
else
  echo "[경고] 자동 생성된 로그 테이블을 감지하지 못했다. 적재 지연일 수 있으니 잠시 후 다시 조회를 권장한다."
fi
