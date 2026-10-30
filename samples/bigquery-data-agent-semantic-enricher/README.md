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

# BigQuery Data Agent 시맨틱 메타데이터 준비도 진단 및 지능형 보강 가이드

빅쿼리(BigQuery) Data Agent(제미나이 인 빅쿼리(Gemini in BigQuery), 자연어 기반 SQL 생성 도구, NL2SQL) 도입 시 발생하는 심각한 환각(Hallucination)과 테이블 오라우팅 문제를 해결하기 위해, 대상 데이터셋의 테이블 및 컬럼 설명, 데이터플렉스(Dataplex) 데이터 프로파일링 통계, Knowledge Catalog 비즈니스 용어집(Glossary) 계산 공식 바인딩 상태를 종합 진단하고 지능적으로 보강(Enrichment)하는 실무 진단 도구다. (As of 2026-10-17)

---

## 1. 발생 증상 및 진단 대상 체크리스트

사내 또는 고객사 환경에서 아래 증상이 발생한다면 즉시 진단 대상이다:
다음과 같은 현상이 운영 또는 개발 환경에서 발생하고 있다면 즉시 본 진단 도구를 구동해야 한다:
- [ ] 자연어 질문 입력 시 Data Agent가 유사한 스키마를 가진 다른 테이블을 잘못 조인하거나 참조하는 경우
- [ ] 컬럼 설명(Description)이 비어 있어 LLM이 축약어(예: `amt`, `diff_qty`, `stat_cd`)의 의미를 임의로 날조하여 필터링하는 경우
- [ ] 순매출, 할인율, 결품 예상 시간 등 비즈니스 계산 공식(Formula)이 명시되지 않아 임의의 수식으로 계산 결과를 왜곡하는 경우
- [ ] Dataplex 데이터 프로파일링(Null 비율, 고유값 목록, 최솟값 및 최댓값)이 수행되지 않아 유효하지 않은 조건절을 생성하는 경우
- [ ] 수십 개 테이블의 메타데이터를 수작업으로 채우기 어려워 Data Agent 전사 확산이 지연되는 경우


### 1.1 도구의 본질 및 비즈니스 해결 과제 (What & Why)
- **대상 사용자 (Target)**: 데이터 엔지니어, 빅쿼리 분석가, 데이터 거버넌스 담당자 및 AI 솔루션 아키텍트
- **해결하는 핵심 문제 (Core Pain Points)**:
  1. BigQuery Data Agent(자연어 기반 SQL 생성) 도입 시 테이블 및 컬럼 설명 부재로 인한 심각한 쿼리 환각(Hallucination) 및 테이블 오라우팅
  2. Dataplex 데이터 프로파일링 통계(NULL 비율, 고유값 등)가 에이전트에 연동되지 않아 비효율적인 필터 조건과 엉뚱한 JOIN이 생성되는 문제
  3. 사내 핵심 비즈니스 KPI 및 용어집(Glossary) 계산 공식이 누락되어 매출, 활성 사용자 등의 질의에 잘못된 집계 로직이 도출되는 현상
- **본 솔루션의 해결 방식 (Solution)**:
  - 대상 데이터셋의 테이블/컬럼 설명 충실도, Dataplex 프로파일링 연동 여부, Knowledge Catalog 비즈니스 용어집 바인딩 상태를 3단계로 점수화(0~100점)하고, 결손 메타데이터를 지능적으로 보강하는 SQL DDL 및 콘솔 조치 명령을 도출한다.

### 1.2 최종 산출물 3종 세트 미리보기 (Deliverables & Visual Preview)
본 도구를 실행(`python diagnose.py`)하면 다음 3가지 구체적인 엔터프라이즈 자산이 생성된다:

| 산출물 구분 | 산출물 형태 및 명칭 | 주요 포함 내용 및 실무 활용 방안 |
| :--- | :--- | :--- |
| **① 터미널 콘솔 요약** | Visual CLI Table | 테이블/컬럼 설명 충실도, 프로파일링 연동, 용어집 바인딩 3대 영역 점수 및 최종 시맨틱 준비도 점수 |
| **② 정규 진단 보고서** | 마크다운 파일 (`report.md`) | 데이터셋 메타데이터 결손 전수 분석, 컬럼별 설명 보강 제안서, Dataplex 데이터 프로파일링 스캔 가이드 및 용어집 계산 공식 DDL |
| **③ 후속 조치 및 배포 자산** | Actionable Asset Specs | • **시맨틱 보강 DDL 스크립트**: 테이블/컬럼 주석을 즉시 반영하는 `ALTER TABLE ... SET OPTIONS` SQL<br/>• **Dataplex 데이터 프로파일링 가이드**: 메타데이터 카탈로그 자동 수집 작업 생성 명령어<br/>• **Knowledge Catalog 매핑 명세**: 비즈니스 용어집과 테이블 간 거버넌스 바인딩 가이드 |

---

## 2. 빠른 시작 (Quickstart)

> [!TIP]
> Cloud Shell 접속 환경 구성 및 저장소 클론(`git clone`) 방법은 루트의 [메인 README](../../README.md)를 참고한다.

### 1) 모의 데이터 가상 실행 (Dry-Run)
GCP API 호출 없이 내장된 가상 인프라 데이터로 정상 동작 여부를 즉시 검증한다:
```bash
python diagnose.py --dry-run
```

**터미널 진단 출력 미리보기:**
```text
BigQuery Data Agent 시맨틱 메타데이터 준비도 진단 결과 표
대상 데이터셋: cymbal_gold
==========================================================================================
테이블 ID                              테이블 설명       컬럼 설명율         데이터 프로파일       용어집 바인딩
------------------------------------------------------------------------------------------
pos_transactions_gold               X (누락/부실)    2/18 (11%)     X (미수행)        X (미연동)
gold_inventory_reconciliation_ledger X (누락/부실)    1/14 (7%)      X (미수행)        X (미연동)
pos_anomaly_alerts                  O (적합)       3/11 (27%)     O (수집됨)        X (미연동)
historical_transactional_data       X (누락/부실)    0/22 (0%)      X (미수행)        X (미연동)
------------------------------------------------------------------------------------------
```


### 2) 사내 환경 대화형 설정 (Config Wizard, 선택 사항)
사내 활성 프로젝트 및 환경 설정을 대화형으로 탐색하여 `.env`에 자동 저장한다:
```bash
python diagnose.py --config
```


### 3) 실제 사내 인프라 실시간 진단
```bash
python diagnose.py
```
> [!NOTE]
> 앞서 `python diagnose.py --config`로 환경 설정을 저장했거나 gcloud 활성 설정을 그대로 활용할 경우 별도의 `.env` 생성 없이 즉시 실행할 수 있다. (환경 변수를 텍스트 에디터로 직접 수동 편집하고자 할 때만 `cp -n .env.example .env` 실행 후 수정)

---

## 3. 솔루션 아키텍처 및 처리 흐름

```mermaid
flowchart TD
    subgraph Layer1 ["Layer 1: User & Interface Layer"]
        User["데이터 엔지니어 / AI 아키텍트"]
        CLI["진단 및 보강 컨트롤러<br/>(diagnose.py)"]
        User --> CLI
    end

    subgraph Layer2 ["Layer 2: Security & Governance Boundary"]
        IAMBoundary["IAM 최소 권한 경계<br/>(bigquery.metadataViewer, dataplex.viewer)"]
        NonDestructive["비파괴 읽기 전용 가드<br/>(기본 조회 모드, --apply 명시 시에만 패치)"]
        CLI --> IAMBoundary
        IAMBoundary --> NonDestructive
    end

    subgraph Layer3 ["Layer 3: Diagnostic & Semantic Engine"]
        ScoreEngine["NL2SQL 준비도 점수 산출기<br/>(설명율, 프로파일, 용어집 0~100점)"]
        EnrichEngine["Gemini 지능형 보강기<br/>(시맨틱 설명 추론 및 공식 도출)"]
        YamlGen["용어집 매니페스트 생성기<br/>(dataplex_glossary_terms.yaml)"]
        NonDestructive --> ScoreEngine
        ScoreEngine --> EnrichEngine
        EnrichEngine --> YamlGen
    end

    subgraph Layer4 ["Layer 4: Target Backend & Metadata Fabric"]
        BQMeta["BigQuery 스키마 메타데이터<br/>(테이블 및 컬럼 Description)"]
        DataplexProfile["Dataplex 데이터 프로파일<br/>(고유값, Null 비율, 통계치)"]
        KnowledgeCatalog["Knowledge Catalog<br/>(비즈니스 용어집 및 Formula)"]
        ScoreEngine --> BQMeta
        ScoreEngine --> DataplexProfile
        ScoreEngine --> KnowledgeCatalog
        EnrichEngine -.->|"선택적 패치 반영 (--apply)"| BQMeta
    end
```

---
## 4. 조치 가이드 및 권장 설정

1. **테이블 및 컬럼 설명 패치 확인**:
   - Google Cloud 콘솔 BigQuery Studio에서 대상 테이블의 스키마 탭을 확인하여 각 필드에 구체적인 비즈니스 설명과 유효 범위가 반영되었는지 검증한다.
   - BigQuery Studio 콘솔 ( https://console.cloud.google.com/bigquery )
2. **Dataplex 데이터 프로파일링 실행**:
   - 통계 지표가 없는 테이블은 Dataplex Data Profile 스캔을 등록하고 실행하여 최솟값, 최댓값, 고유값 비율을 카탈로그에 게시한다.
   - Dataplex Data Profile 안내 ( https://cloud.google.com/dataplex/docs/data-profiling-overview )
3. **Knowledge Catalog 비즈니스 용어집 등록**:
   - 생성된 `dataplex_glossary_terms.yaml` 템플릿을 참조하여 Dataplex Knowledge Catalog에 비즈니스 용어와 계산 수식(`Formula`)을 등록하고 관련 테이블에 바인딩한다.
   - Dataplex Business Glossary 콘솔 ( https://console.cloud.google.com/dataplex/business-glossaries )
4. **Starter 키트 연계 및 완전 관리형 GDA `dataAgents` 자동 배포**:
   - 메타데이터 보강이 완료된 데이터셋은 `bigquery-data-agent-starter` 도구를 통해 구글 관리형 런타임 GDA REST API로 1초 만에 완전 관리형 데이터 에이전트로 자동 프로비저닝된다:
   ```bash
   cd ../bigquery-data-agent-starter
   python diagnose.py --deploy-agent
   ```
   - 보강된 컬럼 설명과 비즈니스 공식이 GDA 에이전트의 `systemInstruction` 및 `exampleQueries`로 자동 바인딩되어 환각을 0%에 가깝게 차단한다.
5. **(선택 사항) 타 클라우드 스토리지 연동 시 Cross-Cloud Caching 활성화**:
   - BigQuery Omni 및 보더리스 레이크하우스(Borderless Lakehouse) 환경에서 타 클라우드(AWS S3, Azure Blob)의 객체를 쿼리하는 경우, Cross-Cloud Caching을 활성화하여 전송(Egress) 비용을 줄이고 반복 NL2SQL 쿼리 지연 시간을 최대 50% 단축한다.
   - Cross-Cloud Caching 안내 ( https://cloud.google.com/blog/products/data-analytics/borderless-lakehouse-cross-cloud-caching-and-connections )
6. **GCP 리소스 생성 시 4대 필수 표준 라벨링 준수**:
   - 사내 거버넌스 및 FinOps 비용 추적을 위해 데이터셋, 테이블, Dataplex 데이터 스캔 생성 시 4대 표준 라벨을 필수로 주입한다:
     - `managed-by`: `google-cloud-0-to-1`
     - `scenario`: `bigquery-data-agent-semantic-enricher`
     - `env`: `sample`
     - `created-by`: `customer-engineer`
   - gcloud CLI 예시: `--labels=managed-by=google-cloud-0-to-1,scenario=bigquery-data-agent-semantic-enricher,env=sample`

---
## 5. 사전 준비 사항 (필요 IAM 권한)

본 도구를 실행하려면 최소 아래의 IAM 권한이 필요하다:

진단 및 메타데이터 보강을 실행하기 위해 사용자 계정 또는 서비스 계정에 요구되는 최소 IAM 권한은 다음과 같다:

| 역할 (Role) | 권한 (Permission) | 용도 |
| :--- | :--- | :--- |
| `roles/bigquery.metadataViewer` | `bigquery.tables.get`, `bigquery.tables.list` | 데이터셋 및 테이블 스키마, 기존 설명 조회 |
| `roles/bigquery.dataEditor` | `bigquery.tables.update` | 메타데이터 보강(`--apply`) 시 스키마 설명 반영 |
| `roles/dataplex.viewer` | `dataplex.dataScans.get`, `dataplex.dataScans.list` | 데이터 프로파일 스캔 결과 조회 |
| `roles/datacatalog.viewer` | `datacatalog.entries.get`, `datacatalog.glossaries.get` | 비즈니스 용어집 및 엔트리 바인딩 확인 |

---

## 6. 기술적 배경 및 아키텍처 원리 (Deep Dive)

### 관련 상세 설계 및 요구 사항 명세
- [비즈니스 요구 사항 명세서 (BRD)](docs/BRD.md): 비즈니스 배경, 성공 지표 및 요구 사항(BR-01~) 명세
- [기술 상세 설계서 (TDD)](docs/TDD.md): 시스템 아키텍처, 기능(FR-01~) 및 비기능(NFR-01~) 설계 명세

```text
==========================================================================================
BigQuery Data Agent 시맨틱 메타데이터 준비도 진단 결과 표
대상 데이터셋: cymbal_gold
==========================================================================================
테이블 ID                              테이블 설명       컬럼 설명율         데이터 프로파일       용어집 바인딩
------------------------------------------------------------------------------------------
pos_transactions_gold               X (누락/부실)    2/18 (11%)     X (미수행)        X (미연동)
gold_inventory_reconciliation_ledger X (누락/부실)    1/14 (7%)      X (미수행)        X (미연동)
pos_anomaly_alerts                  O (적합)       3/11 (27%)     O (수집됨)        X (미연동)
historical_transactional_data       X (누락/부실)    0/22 (0%)      X (미수행)        X (미연동)
------------------------------------------------------------------------------------------

[영역별 평가 세부 내역 및 준비도 점수]
1. 테이블 수준 설명 (Table Description)    : 1/4개 충족 -> 7.5 / 30.0점
2. 컬럼 수준 설명 (Column Description)      : 6/65개 충족 -> 2.8 / 30.0점
3. 데이터 프로파일 통계 (Data Profile Stats) : 1/4개 수집 -> 5.0 / 20.0점
4. 비즈니스 용어집 공식 (Glossary Formula)   : 0/4개 연동 -> 0.0 / 20.0점
------------------------------------------------------------------------------------------
종합 준비도 점수: 15.3 / 100.0점  [FAIL (미달: Data Agent 라우팅 실패 및 SQL 수식 왜곡 주의 요구)]
==========================================================================================

==========================================================================================
Gemini 및 Dataplex 기반 시맨틱 메타데이터 지능형 보강 계획 (Enrichment Plan)
==========================================================================================

[1. 테이블: pos_transactions_gold]
  * 추천 테이블 표준 설명 (AI 라우팅 최적화):
    "Real-time streaming intraday POS sales transactions with customer PII for daily store revenue and sales KPI monitoring."
  * 누락 컬럼 표준 설명 및 제약조건 자동 보강 내역:
    - subtotal_amount     : Pre-tax merchandise item subtotal before any discounts are deducted. Valid range: >= 0.00.
    - discount            : Promotional or coupon discount amount subtracted from subtotal. Range: >= 0.00.
    - tax_amount          : Local and state sales tax applied to transaction.
    - total               : Final net payment collected. Formula: subtotal_amount - discount + tax_amount. Must match tender total.
    - tender_type         : Primary payment method (Enum: CASH, CREDIT_CARD, MOBILE_PAY, GIFT_CARD).
  * Dataplex 비즈니스 용어집(Glossary) 계산 공식 매핑:
    - 공식: Net Revenue = subtotal_amount - discount + tax_amount (Filter: total > 0)
```

---
## 7. 리소스 정리 (Teardown) 안내

본 진단 도구는 BigQuery 스키마 메타데이터 및 카탈로그 설명만을 점검하고 보강하므로, 별도의 컴퓨팅 인스턴스나 영구 스토리지 과금을 유발하지 않는다.
가상 실행 과정에서 생성된 샘플 용어집 YAML 파일은 아래 명령어로 삭제한다:

```bash
rm -f dataplex_glossary_terms*.yaml
```

---
