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

---

## 2. 빠른 시작 (Quickstart)

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

### 2) 실제 사내 인프라 실시간 진단
```bash
cp .env.example .env
python diagnose.py
```
> [!NOTE]
> `.env` 설정값을 비워두면 gcloud 활성 설정 및 사내 리소스를 자동으로 감지하여 진단한다.

---

## 3. 진단 및 해결 흐름

```mermaid
flowchart TD
    A["진단 시작 (python diagnose.py)"] --> B["1. BigQuery 스키마 및 테이블/컬럼 설명 조회"]
    B --> C["2. Dataplex 데이터 프로파일 통계 수집 여부 점검"]
    C --> D["3. Knowledge Catalog 비즈니스 용어집(Glossary) 연동 확인"]
    D --> E["4. Data Agent NL2SQL 준비도 점수 산출 (0~100점)"]
    E --> F{"준비도 점수 합격 여부 (80점 기준)"}
    F -- "미달 (FAIL/WARN)" --> G["--enrich 옵션 활성화: Gemini 기반 메타데이터 생성"]
    G --> H["실데이터 프로파일 통계 기반 표준 컬럼 설명 도출"]
    H --> I["비즈니스 계산 공식(Formula) 용어집 템플릿 YAML 생성"]
    I --> J["--apply 옵션 지정 시 BigQuery 스키마 패치 반영"]
    F -- "합격 (PASS)" --> K["Data Agent NL2SQL 고정확도 운영 보장 리포트 출력"]
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
| : | : | : |
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
