# 진단 및 분석 리포트: gemini-quota-cost-alert

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
========================================================================
[진단 시작] 제미나이(Gemini) API 실시간 비용 및 할당량 경보 아키텍처 점검
  - 프로젝트 ID: sample-project-id
  - Pub/Sub 주제: gemini-cost-alerts
  - 예산 규칙명: gemini-budget-alert
========================================================================

[데모 실행] --dry-run 가상 실행 모드가 활성화되었다.
========================================================================
[표준 처방] 비용 초과 시 자동 할당량(Quota) 차단 Cloud Functions 가이드
========================================================================
1. 자동 차단 파이썬 핸들러 (main.py):
------------------------------------------------------------------------
import base64
import json
from google.cloud import service_usage_v1

def block_gemini_api(event, context):
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    data = json.loads(pubsub_message)
    
    # 예산 90% 이상 도달 시 차단
    if data.get('alertThresholdExceeded', 0.0) >= 0.9:
        client = service_usage_v1.ServiceUsageClient()
        request = service_usage_v1.UpdateConsumerQuotaLimitRequest(
            name='projects/sample-project-id/services/aiplatform.googleapis.com/consumerQuotaMetrics/aiplatform.googleapis.com%2Fgenerate_content_requests_per_minute_per_project_per_base_model/limits/%2Fproject%2Fregion/consumerQuotaLimits/projects%2Fsample-project-id%2Fservices%2Faiplatform.googleapis.com%2FconsumerQuotaMetrics%2Faiplatform.googleapis.com%252Fgenerate_content_requests_per_minute_per_project_per_base_model%252Flimits%252F%252Fproject%252Fregion%252Flimit',
            quota_limit={'values': {'/project/region': 0}}
        )
        client.update_consumer_quota_limit(request=request)
        print('[긴급 조치] 예산 임계치 도달로 Gemini API 쿼터 한도가 0으로 조정되었다.')

2. Cloud Functions 2세대 배포 명령어:
------------------------------------------------------------------------
gcloud functions deploy quota-auto-disable \
    --runtime=python311 \
    --trigger-topic=gemini-cost-alerts \
    --entry-point=block_gemini_api \
    --project=sample-project-id \
    --region=asia-northeast3
========================================================================

========================================================================
[시뮬레이션] 가상 예산 초과 이벤트 페이로드 생성
========================================================================
{
  "billingAccountId": "012345-6789AB-CDEF01",
  "budgetDisplayName": "gemini-budget-alert",
  "costAmount": 120.0,
  "costIntervalStart": "2026-06-01T00:00:00Z",
  "budgetAmount": 100.0,
  "alertThresholdExceeded": 1.2,
  "currencyCode": "USD"
}
------------------------------------------------------------------------

[데모 실행] --dry-run 모드에서는 실제 Pub/Sub 메시지를 발행하지 않고 파이프라인 설계를 검증한다.
  - 상태: 성공 (모의 이벤트 생성 및 스키마 유효성 검증 완료)

========================================================================
[자원 정리 안내 (Teardown Guide)]
테스트 완료 후 요금 발생 및 불필요한 자원 잔존을 방지하기 위해 아래 명령어로 삭제한다:
  1. Pub/Sub 주제 삭제: gcloud pubsub topics delete gemini-cost-alerts --project=sample-project-id
  2. Cloud Functions 삭제: gcloud functions delete quota-auto-disable --region=asia-northeast3
  3. 예산 규칙 삭제: GCP 결제 콘솔 ( https://console.cloud.google.com/billing ) '예산 및 알림' 메뉴에서 'gemini-budget-alert' 삭제
========================================================================
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
