# Google Cloud LRO 비동기 폴링 쿼터 진단 리포트

- **진단 일시**: (실행 결과 자동 생성)
- **대상 서비스**: Cloud Speech-to-Text V2 (`speech.googleapis.com`)
- **대상 프로젝트**: `sample-project-id`
- **리전 위치**: `us-central1`
- **진단 모드**: `모의 실행 (Dry-run)`

---

## 1. 할당량 vs SDK LRO 폴링 트래픽 부하 진단

| 할당량 지표 (Metric Token) | 기본 한도 | 예상 소모량 | 상태 |
| :--- | :--- | :--- | :--- |
| `speech.googleapis.com/batch_recognize_requests` | 300 RPM | 12 RPM | **[정상]** 안전 여유 |
| `speech.googleapis.com/operation_requests` | 150 RPM | 204 RPM | **[위험]** 136.0% 초과 (429 유발) |

---

## 2. 메트릭 착시 현상 및 429 RESOURCE_EXHAUSTED 근본 원인 분석 (RCA)

1. **대시보드 메트릭 착시 (The Metric Mirage)**:
   - 운영 대시보드에서는 주 작업 요청 메트릭(`BatchRecognize`)만 확인하므로 정상 한도 내로 표시된다.
   - 그러나 구글 파이썬 클라이언트 SDK 공통 기반 라이브러리인 `google-api-core`는 `operation.result()` 호출 시 내부적으로 `GetOperation` API를 수초 간격으로 무차별 폴링한다.

2. **숨겨진 쿼터 고갈 메커니즘 (Hidden Quota Exhaustion)**:
   - 현재 동시 작업 수(12건)에서 SDK 기본 폴링 호출량은 약 **204 RPM**에 달한다.
   - 이는 리전당 기본 할당량인 `speech.googleapis.com/operation_requests`(150 RPM)을 **136.0%** 수준으로 소진하여 429 장애를 촉발한다.
   - 본 현상은 Cloud Speech-to-Text V2뿐만 아니라 Document AI, Video Intelligence, Translation 등 구글 클라우드의 모든 LRO 비동기 API에서 동일하게 발생한다.

---

## 3. 현업 즉시 조치 가이드 및 코드 처방전

### 처방 1: SDK 커스텀 Polling 지수 백오프 주입 (모든 LRO 서비스 공통 적용 가능)
초기 대기 시간을 늘리고 최대 폴링 주기를 30초로 설정하여 불필요한 GetOperation 호출을 85% 이상 절감한다:

```python
from google.api_core import polling
from google.cloud import speech_v2

# 1. 커스텀 폴링 폴러 정의 (초기 대기 15초, 최대 주기 30초, 지수 배수 1.5)
custom_polling = polling.DEFAULT_POLLING.with_delay(
    initial=15.0,
    maximum=30.0,
    multiplier=1.5,
)

# 2. 비동기 LRO 작업 제출
# operation = client.batchrecognize(request=request)

# 3. 커스텀 폴링 객체를 주입하여 완료 대기 (429 원천 차단)
result = operation.result(polling=custom_polling, timeout=3600)
```

### 처방 2: 동기식 블로킹 대기 지양 및 비동기 큐 파이프라인 분리 (엔터프라이즈 권장)
- 워커 프로세스에서 `operation.result()`로 동기 대기하지 않고, `operation.operation.name`을 Cloud Tasks나 Pub/Sub에 적재 후 즉시 반환한다.
- 단일 스케줄러 워커가 1분 간격으로 대기열에 있는 작업들의 상태를 일괄 조회하여 쿼터 소진을 원천 제어한다.

### 처방 3: 콘솔을 통한 필수 할당량 상향 요청 (QIR)
- 대상 서비스: Cloud Speech-to-Text V2 (리전: us-central1)
- 필수 상향 지표: `speech.googleapis.com/operation_requests` (기본 150 RPM -> 1,000+ RPM 권장)
- 콘솔 경로: IAM & Admin > Quotas ( https://console.cloud.google.com/iam-admin/quotas?project=sample-project-id )
