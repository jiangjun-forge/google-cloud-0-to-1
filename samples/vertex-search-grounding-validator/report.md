# Agent Platform Search 데이터 저장소 색인 및 그라운딩 정합성 진단 리포트 (vertex-search-grounding-validator)

- **진단 모드**: `모의 실행 (Dry-run)`
- **대상 프로젝트**: `sample-project-id`
- **위치(Location)**: `global`
- **점검 데이터 저장소 수**: 2개
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 데이터 저장소별 원본 스토리지 동기화 및 색인율 점검

| 저장소 ID | 원본 문서 수 | 색인 문서 수 | 동기화율 | 상태 |
| :--- | :--- | :--- | :--- | :--- |
| `enterprise-knowledge-ds` | 2400 | 1850 | 77.1% | **WARNING** |
| `customer-faq-ds` | 500 | 500 | 100.0% | OK |

---

## 2. 파서 구성, 청킹 전략 및 그라운딩 프로브 정밀 진단

### 데이터 저장소: `enterprise-knowledge-ds` (전사 사내 규정 및 기술 문서)
- **콘텐츠 유형**: `CONTENT_REQUIRED (비정형 문서)`
- **원본 버킷**: `gs://demo-enterprise-docs`
- **누락 문서 수**: 550건
- **적용 파서**: `DIGITAL_PARSER (단순 텍스트)`
- **청킹 단위**: `500 토큰 (고정 크기)`
- **서비스 에이전트 IAM 권한**: 정상 (`roles/storage.objectViewer`)
- **프로브 질의**: "2026 클라우드 보안 정책 가이드라인"
- **검색 청크 수**: 3개
- **그라운딩 신뢰도 점수**: **0.62** / 1.00
- **진단 결과**: **[WARNING]** GCS 원본 대비 550건(22.9%) 색인 누락 및 스캔 PDF 표/도표 파싱 불가로 그라운딩 신뢰도 저하 (레이아웃 파서 전환 및 재색인 필요)

### 데이터 저장소: `customer-faq-ds` (대고객 서비스 FAQ 저장소)
- **콘텐츠 유형**: `CONTENT_REQUIRED (HTML/웹)`
- **원본 버킷**: `gs://demo-customer-faqs`
- **누락 문서 수**: 0건
- **적용 파서**: `HTML_PARSER`
- **청킹 단위**: `250 토큰`
- **서비스 에이전트 IAM 권한**: 정상 (`roles/storage.objectViewer`)
- **프로브 질의**: "서비스 환불 및 라이선스 이전 절차"
- **검색 청크 수**: 4개
- **그라운딩 신뢰도 점수**: **0.95** / 1.00
- **진단 결과**: **[OK]** 문서 색인율 100%, 고품질 청킹 및 우수한 그라운딩 정확도 확인

---

## 3. RAG 파이프라인 품질 개선 및 즉각 조치 처방

### 1. Cloud Storage 신규 및 누락 문서 수동 델타 재색인 트리거
```bash
gcloud discovery-engine documents import \
  --data-store=<DATASTORE_ID> \
  --location=global \
  --gcs-uri="gs://<BUCKET_NAME>/*" \
  --auto-generate-ids
```

### 2. 복합 표/다단 PDF 문서를 위한 Layout Parser(고급 레이아웃 파서) 활성화
- **Agent Platform 콘솔** > Data Stores > Configurations > Document Processing
- Parser 옵션을 'Digital Parser'에서 'Layout Parser(청킹 지원)'로 변경 후 재색인 수행

### 3. Discovery Engine 서비스 에이전트에 버킷 읽기 권한 보장
```bash
gcloud storage buckets add-iam-policy-binding gs://<BUCKET_NAME> \
  --member="serviceAccount:service-<PROJECT_NUMBER>@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
```

---

## 4. 사내 거버넌스 4대 필수 표준 라벨링

Agent Platform Search 데이터 저장소 연계 Cloud Storage 버킷 및 RAG 파이프라인 리소스 프로비저닝 시 다음 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `vertex-search-grounding-validator`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 5. 콘솔 링크 조치 가이드 및 공식 레퍼런스

- **Agent Platform Search 데이터 저장소 콘솔**: ( https://console.cloud.google.com/vertex-ai/data-stores?project=sample-project-id )
- **공식 문서 - 비정형 데이터 저장소 생성 및 관리**: ( https://cloud.google.com/generative-ai-app-builder/docs/create-data-store-es )
- **공식 문서 - 문서 파싱 및 청킹 가이드**: ( https://cloud.google.com/generative-ai-app-builder/docs/parse-chunk-documents )
- **공식 문서 - Agent Platform Search를 활용한 Gemini 그라운딩**: ( https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/ground-gemini )

---

## 6. 자원 정리 안내 (Teardown)
본 진단 도구는 읽기 전용으로 데이터 저장소 메타데이터와 스토리지 색인 상태를 조회하므로 별도의 클라우드 인프라 자원을 생성하지 않는다.
