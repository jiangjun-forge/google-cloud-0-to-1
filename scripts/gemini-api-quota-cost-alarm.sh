#!/bin/bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
# gemini-api-quota-cost-alarm.sh
# 주의: 본 코드는 상용 배포용이 아닌 학습 및 데모용 가이드 스크립트다.
# 용도: 제미나이(Gemini ) API 사용에 대한 실시간 비용 및 할당량 한도 임계치 도달 시의 Pub/Sub 기반 경보 설정 및 복구 자동화 시나리오를 시뮬레이션하고 테스트한다.

# 전역 변수 선언 영역이다.
ALARM_THRESHOLD_PERCENT="0.9" # 경보를 유발할 임계 비율이다.
ALARM_THRESHOLD_USD="100" # 비용 경보 임계치다.
BILLING_ACCOUNT_ID="" # 타겟 클라우드 빌링 계정 ID다.
BUDGET_ALERT_NAME="gemini-budget-alert" # 비용 예산 경보 규칙 이름이다.
CLOUDFUNCTIONS_NAME="quota-auto-disable" # 자동 차단용 클라우드 펑션 이름이다.
PROJECT_ID=$(gcloud config get-value project 2>/dev/null) # 활성 GCP 프로젝트 ID다.
PUBSUB_TOPIC_NAME="gemini-cost-alerts" # Pub/Sub 주제 이름이다.



# GCP 프로젝트 ID 감지 여부를 점검한다.
if [ -z "${PROJECT_ID}" ]; then
  echo "[오류] 활성화된 GCP 프로젝트 ID를 감지하지 못했다. gcloud config set project 명령어로 설정하거나 PROJECT_ID 변수를 직접 지정하기 바란다."
  echo "     (참고: gcloud 로그인 필요 시 GCP 콘솔(https://console.cloud.google.com/ )에서 직접 확인 가능하다.)"
  exit 1
fi

echo "[설정 점검] 프로젝트 '${PROJECT_ID}'의 클라우드 빌링 정보를 동적으로 감지한다..."
BILLING_ACCOUNT_ID=$(gcloud beta billing projects describe "${PROJECT_ID}" --format="value(billingAccountName)" 2>/dev/null)

if [ -n "${BILLING_ACCOUNT_ID}" ]; then
  BILLING_ACCOUNT_ID="${BILLING_ACCOUNT_ID#billingAccounts/}"
  echo "[확인] 감지된 클라우드 빌링 계정 ID: ${BILLING_ACCOUNT_ID}"
else
  echo "[경고] 해당 프로젝트에 연동된 클라우드 빌링 계정을 감지하지 못했다."
  echo "     (참고: 실제 환경에서는 빌링 계정 ID를 수동으로 지정하거나 권한을 확인해야 한다.)"
  BILLING_ACCOUNT_ID="012345-6789AB-CDEF01" # 가상 시뮬레이션용 빌링 계정 ID다.
  echo "     (시뮬레이션 가상 ID 매핑 완료: ${BILLING_ACCOUNT_ID} )"
fi

echo "========================================================================"
echo "[1단계: Pub/Sub 경보 주제 생성 및 확인]"
# (Pub/Sub 주제 콘솔 주소: https://console.cloud.google.com/cloudpubsub/topic/list )
if ! gcloud pubsub topics describe "${PUBSUB_TOPIC_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "[안내] Pub/Sub 주제 '${PUBSUB_TOPIC_NAME}'가 존재하지 않아 새로 생성한다..."
  gcloud pubsub topics create "${PUBSUB_TOPIC_NAME}" --project="${PROJECT_ID}"
else
  echo "[통과] Pub/Sub 주제 '${PUBSUB_TOPIC_NAME}'가 이미 존재한다."
fi

echo "========================================================================"
echo "[2단계: 실시간 비용 예산 알림 생성 및 Pub/Sub 연동]"
# (결제 예산 관리 콘솔 주소: https://console.cloud.google.com/billing )
echo "[안내] 결제 예산 경보 규칙 '${BUDGET_ALERT_NAME}'을 생성하고 Pub/Sub 주제와 바인딩을 매핑한다..."

# 실제 budget 생성 명령 실행 시도
BUDGET_ERR_LOG=$(gcloud beta billing budgets create \
  --billing-account="${BILLING_ACCOUNT_ID}" \
  --display-name="${BUDGET_ALERT_NAME}" \
  --budget-filter-projects="projects/${PROJECT_ID}" \
  --specified-amount="currencyCode=USD,units=${ALARM_THRESHOLD_USD}" \
  --threshold-rule="percent=${ALARM_THRESHOLD_PERCENT}" \
  --pubsub-topic="projects/${PROJECT_ID}/topics/${PUBSUB_TOPIC_NAME}" 2>&1)

if [ $? -eq 0 ]; then
  echo "[성공] 빌링 계정 ${BILLING_ACCOUNT_ID}에 예산 경보 규칙이 정상적으로 생성 및 연동되었다."
else
  echo "[경고] CLI를 통한 예산 경보 규칙 생성에 실패했다."
  echo "  - 실패 사유: ${BUDGET_ERR_LOG}"
  echo "  [수동 복구 및 해결 처방 가이드]"
  echo "    1. GCP 결제 관리 콘솔(https://console.cloud.google.com/billing )에 접속한다."
  echo "    2. 좌측 메뉴에서 '예산 및 알림'을 선택 후 '예산 생성' 버튼을 클릭한다."
  echo "    3. 예산 금액을 USD ${ALARM_THRESHOLD_USD}로 지정하고 '임계값 규칙'을 ${ALARM_THRESHOLD_PERCENT}로 지정한다."
  echo "    4. '알림 관리' 설정에서 '이 예산에 Pub/Sub 주제 연결'을 활성화한다."
  echo "    5. 방금 생성한 프로젝트 '${PROJECT_ID}'의 Pub/Sub 주제 'projects/${PROJECT_ID}/topics/${PUBSUB_TOPIC_NAME}'을 선택 및 저장한다."
fi

echo "========================================================================"
echo "[3단계: 비용 초과 시 제미나이 API 할당량(Quota ) 자동 차단 처방 구성 가이드]"
# (클라우드 펑션 콘솔 주소: https://console.cloud.google.com/functions/list )
echo "예산 경보가 발생했을 때, Pub/Sub 주제를 구독하여 자동으로 제미나이 API 할당량 한도를 0으로 긴급 조정해 버리는 클라우드 펑션(Cloud Functions )의 실무용 구동 코드를 제시한다."
echo ""
echo "  [자동 차단용 Node.js / Python 핵심 코드 템플릿]"
echo "    - 런타임: Python 3.10 이상 권장 (최신 제미나이 3.5 호환 기준 )"
echo "    - 소스 코드 요약:"
echo "      def block_gemini_api(event, context):"
echo "        import base64, json"
echo "        from google.cloud import service_usage_v1"
echo "        "
echo "        pubsub_message = base64.b64decode(event['data']).decode('utf-8')"
echo "        data = json.loads(pubsub_message)"
echo "        "
echo "        if data.get('alertThresholdExceeded', 0.0) >= ${ALARM_THRESHOLD_PERCENT}:"
echo "          client = service_usage_v1.ServiceUsageClient()"
echo "          request = service_usage_v1.UpdateConsumerQuotaLimitRequest("
echo "            name='projects/${PROJECT_ID}/services/aiplatform.googleapis.com/consumerQuotaMetrics/aiplatform.googleapis.com%2Fgenerate_content_requests_per_minute_per_project_per_base_model/limits/%2Fproject%2Fregion/consumerQuotaLimits/projects%2F${PROJECT_ID}%2Fservices%2Faiplatform.googleapis.com%2FconsumerQuotaMetrics%2Faiplatform.googleapis.com%252Fgenerate_content_requests_per_minute_per_project_per_base_model%252Flimits%252F%252Fproject%252Fregion%252Flimit',"
echo "            quota_limit={'values': {'/project/region': 0}}"
echo "          )"
echo "          client.update_consumer_quota_limit(request=request)"
echo "          print(f'[긴급 처방 실행] 비용 폭탄 예방을 위해 ${PROJECT_ID}의 Gemini API 쿼터 한도가 0으로 조정되어 자동 차단되었다.')"
echo ""
echo "  [클라우드 펑션 CLI 자동 배포 명령어]"
echo "    gcloud functions deploy ${CLOUDFUNCTIONS_NAME} \\"
echo "      --runtime=python310 \\"
echo "      --trigger-topic=${PUBSUB_TOPIC_NAME} \\"
echo "      --entry-point=block_gemini_api \\"
echo "      --project=${PROJECT_ID} \\"
echo "      --region=asia-northeast3"

echo "========================================================================"
echo "[4단계: 모의 비용 경보 이벤트(Simulated Alarm Event ) 발행 테스트]"
echo "실제 예산 소모량이 임계치를 넘어 $120에 도달한 상황의 가상 JSON 페이로드를 Pub/Sub 주제에 강제 퍼블리시하여 파이프라인의 실시간 연동을 검증한다."
echo "가상 퍼블리시 전송 중..."

SIMULATED_PAYLOAD=$(cat <<EOF
{
  "billingAccountId": "${BILLING_ACCOUNT_ID}",
  "budgetDisplayName": "${BUDGET_ALERT_NAME}",
  "costAmount": 120.0,
  "costIntervalStart": "2026-06-01T00:00:00Z",
  "budgetAmount": 100.0,
  "alertThresholdExceeded": 1.2,
  "currencyCode": "USD"
}
EOF
)

PUBLISH_RESULT=$(gcloud pubsub topics publish "${PUBSUB_TOPIC_NAME}" \
  --message="${SIMULATED_PAYLOAD}" \
  --project="${PROJECT_ID}" 2>&1)

if [ $? -eq 0 ]; then
  echo "[성공] 가상 예산 경보 이벤트가 Pub/Sub 주제에 완벽히 전달되었다."
  echo "  - 메시지 ID: ${PUBLISH_RESULT}"
  echo "  - 내용: ${SIMULATED_PAYLOAD}"
else
  echo "[실패] 가상 경보 이벤트 전송 실패"
  echo "  - 에러 내용: ${PUBLISH_RESULT}"
fi
echo "========================================================================"
echo "[처방 완료] 실시간 비용 및 쿼터 임계치 경보 설정 진단 가이드를 마친다."
