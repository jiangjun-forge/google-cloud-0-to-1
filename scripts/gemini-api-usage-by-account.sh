#!/bin/bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
# gemini-api-usage-by-account.sh
# 주의: 본 코드는 상용 배포용이 아닌 학습 및 데모용 가이드 스크립트다.
# 용도: 제미나이(Gemini) API 호출 로그를 빅쿼리(BigQuery)로 자동 적재하고, SQL 쿼리를 통해 사용자별 사용 횟수를 산출해 모니터링하기 위함이다.

# 설정에 사용되는 쉘 전역 변수 모음이다. 본인의 구글 클라우드(Google Cloud) 프로젝트 및 환경에 맞춰 각 변수 값을 적절히 변경하여 사용한다.
BIGQUERY_DATASET_ID="gcp_logs"
BIGQUERY_LOCATION="asia-northeast3"  # 빅쿼리 데이터세트 리전 (서울 기본값)
IAM_ROLE_BIGQUERY="roles/bigquery.dataEditor"
LOG_SINK_NAME="gcp-logs-sink"
LOG_SINK_SERVICE_ACCOUNT=""          # 로그 싱크 생성 후 동적 할당될 서비스 계정
PROJECT_ID="your-project-id"         # 실제 구글 클라우드 프로젝트 ID


# 1. 로깅 활성화 (데이터 액세스 감사 로그, Data Access Audit Logs)
# 제미나이 및 Vertex AI API 로그 수집을 위해 Vertex AI 데이터 액세스 감사 로그를 활성화한다.
# 수동 설정 콘솔 주소: https://console.cloud.google.com/iam-admin/audit 
#
# gcloud 커맨드 라인 도구(gcloud CLI)를 사용해 현재 프로젝트의 IAM(Identity and Access Management) 감사 정책을 확인하고 보정한다.
# gcloud projects get-iam-policy ${PROJECT_ID} --format=json


# 2. Cloud Logging 필터 쿼리로 로그 확인
# 실시간으로 들어오는 제미나이 및 Vertex AI API 로그만 필터링하는 로깅 쿼리 언어(Logging Query Language, LQL) 쿼리다.
# 로그 쿼리 콘솔 주소: https://console.cloud.google.com/logs/query 
#
# 로깅 쿼리 원문: resource.type="audited_resource" AND protoPayload.serviceName="aiplatform.googleapis.com"


# 3. 빅쿼리로 로그 싱크(Log Sink) 설정 (로그 라우터, Log Router)
# 수집되는 데이터 감사 로그를 BigQuery 데이터세트로 우회시키는 싱크를 만든다.
# 로그 라우터 설정 콘솔 주소: https://console.cloud.google.com/logs/router 
#
# gcloud 명령을 실행해 대화형(interactive) 모드로 싱크 생성을 최종 확인한다.
gcloud logging sinks create "${LOG_SINK_NAME}" \
  "bigquery.googleapis.com/projects/${PROJECT_ID}/datasets/${BIGQUERY_DATASET_ID}" \
  --log-filter='resource.type="audited_resource" AND protoPayload.serviceName="aiplatform.googleapis.com"' \
  --project="${PROJECT_ID}"

# 싱크 생성 시 자동 발행된 고유 라이터 서비스 계정 식별자를 추출한다.
LOG_SINK_SERVICE_ACCOUNT=$(gcloud logging sinks describe "${LOG_SINK_NAME}" \
  --project="${PROJECT_ID}" \
  --format="value(writerIdentity)" 2>/dev/null)

# 추출한 로그 싱크 서비스 계정에 빅쿼리 데이터 편집자(roles/bigquery.dataEditor) 역할을 자동 위임한다.
# IAM 설정 콘솔 주소: https://console.cloud.google.com/iam-admin/iam 
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="${LOG_SINK_SERVICE_ACCOUNT}" \
  --role="${IAM_ROLE_BIGQUERY}"


# 4. 빅쿼리에서 SQL로 조회
# 수집 완료된 감사 로그 테이블에서 계정별 실시간 호출 점유 비율을 쿼리한다. 비용 최적화 및 쿼리 스캔량 최소화를 위해 파티션 필터(_PARTITIONDATE) 조건을 추가하여 최근 7일 데이터만 조회한다.
# 빅쿼리 분석 콘솔 주소: https://console.cloud.google.com/bigquery 
#
# 빅쿼리 커맨드 라인 도구(bq query CLI)를 사용해 터미널 상에서 직접 조회를 즉시 구동한다.
bq query --use_legacy_sql=false "
 SELECT protopayload_auditlog.authenticationInfo.principalEmail AS user_email,
        COUNT(1) AS request_count
   FROM \`${PROJECT_ID}.${BIGQUERY_DATASET_ID}.cloudaudit_googleapis_com_data_access_*\`
  WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
    AND resource.type = 'audited_resource'
    AND protopayload_auditlog.serviceName = 'aiplatform.googleapis.com'
  GROUP BY user_email
  ORDER BY request_count DESC;
"
