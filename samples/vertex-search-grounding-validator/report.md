# 진단 및 분석 리포트: vertex-search-grounding-validator

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
================================================================================
Vertex AI Search 데이터 저장소 색인 및 그라운딩 정합성 진단 리포트
진단 모드: 가상 실행 (Dry-run)
대상 프로젝트: sample-project-id
위치(Location): global
점검 데이터 저장소 수: 2개
================================================================================

[1단계] 데이터 저장소별 원본 스토리지 동기화 및 색인율 점검
--------------------------------------------------------------------------------
저장소 ID                     원본 문서 수      색인 문서 수      동기화율       상태        
--------------------------------------------------------------------------------
enterprise-knowledge-ds    2400         1850         77.1%      WARNING   
customer-faq-ds            500          500          100.0%     OK        
--------------------------------------------------------------------------------

[2단계] 파서 구성, 청킹 전략 및 그라운딩 프로브 정밀 진단
--------------------------------------------------------------------------------
- 데이터 저장소: enterprise-knowledge-ds (전사 사내 규정 및 기술 문서)
  * 콘텐츠 유형: CONTENT_REQUIRED (비정형 문서)
  * 원본 버킷: gs://demo-enterprise-docs
  * 누락 문서 수: 550건
  * 적용 파서: DIGITAL_PARSER (단순 텍스트)
  * 청킹 단위: 500 토큰 (고정 크기)
  * 서비스 에이전트 IAM 권한: 정상 (roles/storage.objectViewer)
  * 프로브 질의: "2026 클라우드 보안 정책 가이드라인"
  * 검색 청크 수: 3개
  * 그라운딩 신뢰도 점수: 0.62 / 1.00
  * 진단 결과: [WARNING] GCS 원본 대비 550건(22.9%) 색인 누락 및 스캔 PDF 표/도표 파싱 불가로 그라운딩 신뢰도 저하 (레이아웃 파서 전환 및 재색인 필요)

- 데이터 저장소: customer-faq-ds (대고객 서비스 FAQ 저장소)
  * 콘텐츠 유형: CONTENT_REQUIRED (HTML/웹)
  * 원본 버킷: gs://demo-customer-faqs
  * 누락 문서 수: 0건
  * 적용 파서: HTML_PARSER
  * 청킹 단위: 250 토큰
  * 서비스 에이전트 IAM 권한: 정상 (roles/storage.objectViewer)
  * 프로브 질의: "서비스 환불 및 라이선스 이전 절차"
  * 검색 청크 수: 4개
  * 그라운딩 신뢰도 점수: 0.95 / 1.00
  * 진단 결과: [OK] 문서 색인율 100%, 고품질 청킹 및 우수한 그라운딩 정확도 확인

--------------------------------------------------------------------------------

[3단계] RAG 파이프라인 품질 개선 및 즉각 조치 처방
1. Cloud Storage 신규 및 누락 문서 수동 델타 재색인 트리거:
   gcloud discovery-engine documents import \
     --data-store=<DATASTORE_ID> \
     --location=global \
     --gcs-uri="gs://<BUCKET_NAME>/*" \
     --auto-generate-ids

2. 복합 표/다단 PDF 문서를 위한 Layout Parser(고급 레이아웃 파서) 활성화:
   - Agent Builder 콘솔 > Data Stores > Configurations > Document Processing
   - Parser 옵션을 'Digital Parser'에서 'Layout Parser(청킹 지원)'로 변경 후 재색인 수행

3. Discovery Engine 서비스 에이전트에 버킷 읽기 권한 보장:
   gcloud storage buckets add-iam-policy-binding gs://<BUCKET_NAME> \
     --member="serviceAccount:service-<PROJECT_NUMBER>@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
     --role="roles/storage.objectViewer"
================================================================================
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
