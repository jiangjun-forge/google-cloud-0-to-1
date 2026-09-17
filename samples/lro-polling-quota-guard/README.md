# Google Cloud LRO 비동기 작업 폴링 쿼터 고갈 및 429 장애 진단 도구

Google Cloud 비동기 장기 실행 작업(LRO, Long-Running Operations) 파이프라인에서 대시보드상 요청 RPM이 정상임에도 발생하는 원인 불명의 `429 RESOURCE_EXHAUSTED` 장애를 진단하고, Python SDK(`google-api-core`) 비동기 폴링 지수 백오프 최적화 및 비동기 분리 아키텍처를 처방하는 범용 진단 도구다. (As of 2026-09-18)

**Audience**: `#Architect`, `#Developer`  
**Concern**: `#Performance`, `#Resilience`  
**Service**: `#CloudMonitoring`, `#DocumentAI`, `#SpeechToText`

---

## 1. 이 가이드가 필요한 상황 (증상 체크리스트)
- [ ] Speech-to-Text V2 (`BatchRecognize`), Document AI (`BatchProcessDocuments`), Video Intelligence (`AnnotateVideo`), Translation V3 (`BatchTranslateDocument`) 등 대용량 비동기 배치 파이프라인에서 원인 모를 `429 RESOURCE_EXHAUSTED` 에러가 발생한다.
- [ ] Google Cloud 콘솔 할당량 대시보드에서 주 작업 요청 지표(예: `BatchRecognize requests`, `BatchProcess requests`)는 한도 대비 여유가 충분한데 서비스가 중단된다.
- [ ] 파이썬 코드에서 `operation = client.some_batch_method(...)` 실행 후 `operation.result()`로 동기 블로킹 대기하고 있다.
- [ ] 다수의 워커 스레드나 프로세스가 동시에 작업을 대기하면서 구글 클라이언트 SDK의 내부 폴링 주기로 인해 리전당 `operation_requests` 쿼터(기본 120~150 RPM)를 순식간에 초과하고 있다.

---

## 2. 진단 및 해결 흐름

```mermaid
flowchart TD
    A["LRO 비동기 작업 제출 (Speech/DocAI/Video/Translate)"] --> B["Python SDK operation.result() 대기"]
    B --> C["기본 SDK(google-api-core)가 GetOperation 수초 간격 무차별 폴링"]
    C --> D{"operation_requests 쿼터 120~150 RPM 초과?"}
    D -->|Yes| E["429 RESOURCE_EXHAUSTED 장애 발생 (메트릭 착시)"]
    D -->|No| F["정상 완료 대기"]
    E --> G["lro-polling-quota-guard 진단 실행"]
    G --> H["1. SDK 커스텀 Polling 지수 백오프 (initial=15s, max=30s) 주입"]
    G --> I["2. Pub/Sub / Cloud Tasks 기반 작업 제출/완료 비동기 파이프라인 분리"]
    G --> J["3. 콘솔 operation_requests 할당량 상향 (QIR)"]
```

---

## 3. 대표 발생 사례 4대 서비스 매핑

구글 파이썬 클라이언트 SDK의 공통 기반 라이브러리인 `google-api-core`는 모든 비동기 LRO 서비스에서 동일한 폴링 전략(`polling.py`)을 공유하므로 아래 서비스 전체에서 동일한 429 증상이 발생한다:

| 서비스 명칭 | 주 작업 요청 메서드 | 모니터링 주 작업 쿼터 | 숨겨진 폴링 쿼터 (장애 유발) |
| :--- | :--- | :--- | :--- |
| **Speech-to-Text V2** | `BatchRecognize` | `batch_recognize_requests` (300 RPM) | `operation_requests` (150 RPM) |
| **Document AI** | `BatchProcessDocuments` | `batch_process_requests` (120 RPM) | `operation_requests` (120 RPM) |
| **Video Intelligence** | `AnnotateVideo` | `annotate_video_requests` (180 RPM) | `operation_requests` (150 RPM) |
| **Translation V3** | `BatchTranslateDocument` | `batch_document_requests` (150 RPM) | `operation_requests` (150 RPM) |

---

## 4. 사전 준비 사항 및 필요 권한

본 도구 실행에는 Google Cloud 리소스 읽기 및 할당량 확인을 위한 최소 권한이 요구된다:

| 역할 (Role) | 설명 |
| :--- | :--- |
| `roles/monitoring.viewer` | Cloud Monitoring 지표 및 사용량 조회 권한 |
| `roles/serviceusage.serviceUsageViewer` | 대상 API 활성화 상태 및 기본 할당량 확인 권한 |

---

## 5. 1분 퀵스타트

### 가상 모의 실행 (Dry-run)
실제 GCP API 호출 없이 동시 작업 수에 따른 서비스별 LRO 폴링 쿼터 고갈 위험도를 시뮬레이션한다:
```bash
# 기본 서비스(Speech-to-Text) 모의 진단
./run.sh --dry-run

# Document AI 서비스 모의 진단
./run.sh --service document-ai --dry-run
```

### 사내 실측 진단 실행
현재 활성화된 프로젝트와 예상 동시성(Concurrency)을 입력하여 진단한다:
```bash
# 기본 활성 프로젝트 및 동시성 15건 점검
./run.sh -c 15

# 특정 서비스, 프로젝트, 리전 지정
./run.sh -s document-ai -p <대상_프로젝트_ID> -l us-central1 -c 20
```

---

## 6. 결과 확인 후 즉각 조치 가이드

1. **Python SDK 커스텀 Polling 설정 적용 (모든 LRO 공통 즉시 조치)**:
   기본 짧은 간격 폴링 대신 대용량 배치 처리에 적합한 지수 백오프 폴러를 주입하여 `GetOperation` 호출량을 85% 이상 절감한다:
   ```python
   from google.api_core import polling

   # 초기 대기 15초, 최대 주기 30초, 배수 1.5 지수 백오프
   custom_polling = polling.DEFAULT_POLLING.with_delay(
       initial=15.0,
       maximum=30.0,
       multiplier=1.5,
   )
   result = operation.result(polling=custom_polling, timeout=3600)
   ```

2. **비동기 큐 분리 아키텍처 전환 (엔터프라이즈 권장)**:
   - 클라이언트에서 `operation.result()` 블로킹 대기를 제거하고, `operation.operation.name`을 Cloud Tasks 또는 Pub/Sub에 발행 후 즉시 응답을 종료한다.
   - 단일 백그라운드 워커가 정기적으로 작업 상태를 일괄 점검하여 쿼터 소진을 원천 차단한다.

3. **필수 할당량 상향 요청 (QIR)**:
   - 콘솔 경로: IAM & Admin > Quotas ( https://console.cloud.google.com/iam-admin/quotas )
   - 대상 서비스: Cloud Speech-to-Text API, Document AI API 등
   - 필수 상향 지표: `operation_requests` (기본 120~150 RPM을 운영 트래픽에 맞추어 1,000+ RPM으로 상향)

---

## 7. 자원 정리 가이드 (Teardown)
본 미니 프로젝트는 순수 진단 및 시뮬레이션 도구이므로 별도의 클라우드 인프라 자원을 생성하지 않으며, 추가 삭제 절차가 필요하지 않다.
