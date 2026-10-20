<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

> [!IMPORTANT]
> **구글 (Google LLC) 참조용 샘플 고지 사항**:
> 본 프로젝트의 모든 소스 코드와 문서는 Google LLC의 소유이며, Apache-2.0 라이선스에 따라 오직 **참조용 샘플 (Sample / Reference Only)** 목적으로만 제공된다. 프로덕션 환경에 그대로 사용할 수 없으며, 사전 통지 없이 언제든 내용이 수정, 변경 또는 삭제될 수 있다.

# Agent Platform Search 데이터 저장소 색인 및 그라운딩 정합성 진단기 (vertex-search-grounding-validator)

Agent Platform 및 RAG 파이프라인에서 클라우드 스토리지(Cloud Storage) 원본 문서와 Agent Platform Search 데이터 저장소(Data Store) 간의 색인 누락, 청킹(Chunking) 실패, 서비스 에이전트 권한 누락 및 Gemini 그라운딩 검색 품질 저하를 1분 만에 일괄 진단하고 처방하는 도구다. (As of 2026-10-17)

---

## 1. 발생 증상 및 진단 대상 체크리스트

사내 또는 고객사 환경에서 아래 증상이 발생한다면 즉시 진단 대상이다:
- [ ] Cloud Storage 버킷에 신규 문서나 개정된 사내 규정을 업로드했으나, Agent Platform Search 및 제미나이(Gemini) 모델 답변에 최신 내용이 반영되지 않는 경우
- [ ] 원본 스토리지 객체 수 대비 데이터 저장소에 실제 색인(Indexed) 완료된 문서 수가 현저히 부족하여 색인 누락율을 전수 파악해야 하는 경우
- [ ] 복잡한 표(Table), 다단 레이아웃, 스캔 PDF 파일이 단순 Digital Parser로 처리되어 검색 결과가 깨지거나 누락되는 경우
- [ ] Discovery Engine 서비스 에이전트(`gcp-sa-discoveryengine`)에 스토리지 읽기 권한(`roles/storage.objectViewer`)이 누락되어 색인 동기화가 차단된 경우
- [ ] Gemini 그라운딩 프로브 질의를 통해 검색 청크(Chunk) 품질과 신뢰도 점수(Grounding Score)를 사전 정량 평가하고자 하는 경우

---

## 2. 빠른 시작 (Quickstart)

> [!TIP]
> Cloud Shell 접속 환경 구성 및 저장소 클론(`git clone`) 방법은 루트의 [메인 README](../../README.md)를 참고한다.

### 0) 사내 환경 대화형 설정 (Config Wizard, 선택 사항)
사내 활성 프로젝트 및 환경 설정을 대화형으로 탐색하여 `.env`에 자동 저장한다:
```bash
python diagnose.py --config
```

### 1) 모의 데이터 가상 실행 (Dry-Run)
GCP API 호출 없이 내장된 가상 인프라 데이터로 정상 동작 여부를 즉시 검증한다:
```bash
python diagnose.py --dry-run
```

**터미널 진단 출력 미리보기:**
```text
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
```

### 2) 실제 사내 인프라 실시간 진단
```bash
python diagnose.py
```
> [!NOTE]
> 앞서 `python diagnose.py --config`로 환경 설정을 저장했거나 gcloud 활성 설정을 그대로 활용할 경우 별도의 `.env` 생성 없이 즉시 실행할 수 있다. (환경 변수를 텍스트 에디터로 직접 수동 편집하고자 할 때만 `cp -n .env.example .env` 실행 후 수정)

---

## 3. 솔루션 아키텍처 및 처리 흐름

```mermaid
flowchart TD
    subgraph Layer1["Layer 1: User & Query Ingress (사용자 대화 및 그라운딩 질의)"]
        direction TB
        EndUser["사내 임직원 / AI 애플리케이션"]
        UserQuery["자연어 질문 / 프로브 질의<br/>(예: '2026 클라우드 보안 정책 가이드라인')"]
        EndUser --> UserQuery
    end

    subgraph Layer2["Layer 2: Identity & Access Boundary (서비스 에이전트 권한 경계)"]
        direction TB
        ServiceAgent["Discovery Engine 서비스 에이전트<br/>(service-PROJECT_NUMBER@gcp-sa-discoveryengine.iam.gserviceaccount.com)"]
        StorageViewerRole["스토리지 객체 뷰어 권한<br/>(roles/storage.objectViewer)"]
        ServiceAgent --- StorageViewerRole
    end

    subgraph Layer3["Layer 3: Serving & Diagnostic Runtime (검색 엔진 및 진단 런타임)"]
        direction TB
        SearchValidator["vertex-search-grounding-validator<br/>(diagnose.py)"]
        DataStoreEngine["Agent Platform Search (Discovery Engine)<br/>(Data Store: customer-faq-ds, Layout Parser)"]
        GroundingProbe["그라운딩 검색 품질 & 신뢰도 평가기"]
        SearchValidator --> GroundingProbe
        DataStoreEngine --> GroundingProbe
    end

    subgraph Layer4["Layer 4: Target Backend & Storage (원본 스토리지 및 제미나이 추론)"]
        direction TB
        SourceBucket["Cloud Storage 원본 문서 버킷<br/>(gs://demo-customer-faqs / PDF, HTML)"]
        GeminiModel["제미나이 3.8 Flash 모델<br/>(Search Grounding 연동 추론)"]
    end

    UserQuery ==>|"그라운딩 검색 요청"| DataStoreEngine
    ServiceAgent ==>|"문서 동기화 & 청킹"| SourceBucket
    SourceBucket -.->|"색인 누락률 / 파서 검증"| SearchValidator
    DataStoreEngine ==>|"관련 청크 인출 (Top-k)"| GeminiModel
    GeminiModel --> EndUser
```

---
## 4. 조치 가이드 및 권장 설정

1. **데이터 저장소 수동 재색인 및 상태 모니터링**:
   - Agent Platform Search 데이터 저장소 콘솔 ( https://console.cloud.google.com/vertex-ai/data-stores ) > 대상 데이터 저장소 > 활동(Activity) 탭
   - 비정형 데이터 저장소 생성 및 관리 ( https://cloud.google.com/generative-ai-app-builder/docs/create-data-store-es )
2. **문서 청킹 및 Layout Parser 설정**:
   - 고품질 RAG 검색을 위해 복잡한 PDF 구조를 이해하는 Layout Parser와 적절한 청크 크기(200~500 토큰)를 설정한다.
   - 문서 파싱 및 청킹 가이드 ( https://cloud.google.com/generative-ai-app-builder/docs/parse-chunk-documents )
3. **제미나이(Gemini) 그라운딩 연동 최적화**:
   - 검색된 문서를 파운데이션 모델에 공급할 때 검색 점수 임계치(Dynamic Retrieval Threshold)를 설정하여 무관한 문서 인입을 차단한다.
   - Agent Platform Search를 활용한 Gemini 그라운딩 ( https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/ground-gemini )

---
## 5. 사전 준비 사항 (필요 IAM 권한)

본 도구를 실행하려면 최소 아래의 IAM 권한이 필요하다:

본 도구를 실행하려면 최소 아래의 IAM 권한이 필요하다:

| 역할 (Role) | 최소 IAM 권한 |
| :--- | :--- |
| 디스커버리 엔진 뷰어(`roles/discoveryengine.viewer`) | `discoveryengine.dataStores.get`, `discoveryengine.documents.list` |
| 스토리지 객체 뷰어(`roles/storage.objectViewer`) | `storage.buckets.get`, `storage.objects.get`, `storage.objects.list` |

---

## 6. 기술적 배경 및 아키텍처 원리 (Deep Dive)

### 관련 상세 설계 및 요구 사항 명세
- [비즈니스 요구 사항 명세서 (BRD)](docs/BRD.md): 비즈니스 배경, 성공 지표 및 요구 사항(BR-01~) 명세
- [기술 상세 설계서 (TDD)](docs/TDD.md): 시스템 아키텍처, 기능(FR-01~) 및 비기능(NFR-01~) 설계 명세

```text
================================================================================
Agent Platform Search 데이터 저장소 색인 및 그라운딩 정합성 진단 리포트
진단 모드: 가상 실행 (Dry-run)
대상 프로젝트: demo-agent-platform-project
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
   - Agent Platform 콘솔 > Data Stores > Configurations > Document Processing
   - Parser 옵션을 'Digital Parser'에서 'Layout Parser(청킹 지원)'로 변경 후 재색인 수행

3. Discovery Engine 서비스 에이전트에 버킷 읽기 권한 보장:
   gcloud storage buckets add-iam-policy-binding gs://<BUCKET_NAME> \
     --member="serviceAccount:service-<PROJECT_NUMBER>@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
     --role="roles/storage.objectViewer"
================================================================================
```

---
## 7. 리소스 정리 (Teardown) 안내

본 진단 도구는 읽기 전용으로 데이터 저장소 메타데이터와 스토리지 색인 상태를 조회하므로 별도의 클라우드 인프라 자원을 생성하지 않는다. 실습용으로 생성한 테스트 데이터 저장소나 앱 엔진이 있다면 콘솔에서 삭제한다:

```bash
# 테스트 데이터 저장소 삭제 안내
# Agent Platform 콘솔 ( https://console.cloud.google.com/vertex-ai/data-stores ) 에서 해당 저장소 선택 후 삭제(Delete)
```
