<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 비즈니스 요구 사항 명세서 (BRD: Business Requirements Document)
## 프로젝트명: BigQuery Data Agent 45-Minute Hands-on Starter Kit (Standalone & Optional GE App)

---

## 1. 비즈니스 개요 및 프로젝트 목적 (Executive Summary)

### 1.1 추진 배경
엔터프라이즈 유통 및 그룹사 대상 핸즈온 워크숍에서 참석자들은 BigQuery 데이터를 기반으로 자연어 분석을 수행하는 **BigQuery Data Agent**를 직접 만들고, 이를 BigQuery Studio 내에서 **단독(Standalone)**으로 활용하거나 필요에 따라 **Gemini Enterprise App** 대화창에 게시(Publish)하는 전 과정을 45분 내에 체험하고자 한다. 또한 워크숍 시간이 남을 경우 시맨틱 메타데이터 보강 전후(Before/After)의 NL2SQL 정확도 차이를 비교 시연할 수 있어야 한다.

### 1.2 비즈니스 난제 (Pain Points)
1. **초기 데이터 구성 시간 과다**: 45분이라는 제한된 워크숍 시간 내에 참석자가 일일이 테이블을 설계하고 샘플 데이터를 적재하느라 정작 중요한 에이전트 생성 및 질의 실습 시간이 부족해진다.
2. **고객 환경 다양성 (Standalone vs GE App)**: BigQuery Studio 내에서 단독으로 에이전트를 사용하는 고객과 Gemini Enterprise App에 게시하여 전사 포털로 통합하려는 고객이 혼재되어 있어, 두 시나리오를 모두 지원하는 유연한 구성이 요구된다.
3. **메타데이터 보강 효과 체감 필요**: 원천 테이블 설명이 비어 있을 때의 환각(Before)과 시맨틱 설명 보강 후(After)의 정확도 차이를 현장에서 즉각 시연할 수 있는 스키마 호환성이 필요하다.

### 1.3 프로젝트 목표
본 프로젝트는 명령어 한 줄(`--setup-demo`)로 **`bigquery-data-agent-semantic-enricher`와 100% 호환되는 `cymbal_gold` 4개 원천 테이블, 실데이터, 시맨틱 뷰를 10초 내에 자동 구축**하고, **BigQuery Studio 단독(Standalone) 에이전트 생성 지침(`--agent-config`)**, **선택적 Gemini Enterprise App 게시 가이드(`--register-ge-app`)**, **골든 프롬프트 3선 검증**을 원스톱으로 제공하는 데 목적이 있다.

---

## 2. 이해관계자 및 대상 페르소나 (Stakeholders & Personas)

| 페르소나 | 주요 관심사 및 목표 | 본 솔루션을 통한 비즈니스 혜택 |
| :--- | :--- | :--- |
| **워크숍 참석 고객 (아키텍트 / 분석가)** | 45분 내에 BigQuery Data Agent 구축 및 질의응답 완주 | 원클릭 데이터 구성 및 Standalone / GE App 선택형 실습 가이드 확보 |
| **데이터 플랫폼 엔지니어** | 시맨틱 레이어 기반 NL2SQL 정확도 및 Before/After 비교 | `bigquery-data-agent-semantic-enricher`와 연계하여 스키마 보강 전후 효과 즉시 검증 |
| **워크숍 진행 강사 (CE / SA)** | 참석자 실습 오류 최소화 및 시간 내 전원 완주 | 코드 의존성 없이 독립 실행되면서도 스키마가 호환되는 투트랙 데모 시나리오 확보 |

---

## 3. 상세 비즈니스 요구 사항 명세 (Business Requirements)

| 요구 사항 ID | 기능 영역 | 상세 요구 사항 및 비즈니스 목적 |
| :--- | :--- | :--- |
| **BR-01** | 호환 스몰셋 자동 구성 | `--setup-demo` 실행 시 `cymbal_gold` 데이터셋 내에 `pos_transactions_gold`, `gold_inventory_reconciliation_ledger`, `pos_anomaly_alerts`, `historical_transactional_data` 4개 테이블과 실데이터를 자동 생성하여야 한다. |
| **BR-02** | 시맨틱 골드 뷰 생성 | 순매출(`subtotal_amount - discount + tax_amount`)과 결품 커버 시간(`SAFE_DIVIDE((shelf_qty + backroom_qty), (total_units_sold_intraday / 12.0))`)이 내장된 시맨틱 뷰(`v_cymbal_retail_semantic`)를 자동 생성하여야 한다. |
| **BR-03** | 단독 에이전트 지침 도출 | `--agent-config` 실행 시 BigQuery Studio > Agent Hub에 바로 붙여넣을 수 있는 System Instructions와 Verified Queries를 출력하여야 한다. |
| **BR-04** | 선택적 GE App 연동 | `--register-ge-app` 실행 시 Agent Hub에서 Gemini Enterprise App으로 게시하는 콘솔 UI 절차를 선택 사항(Optional)으로 명확히 안내하여야 한다. |
| **BR-05** | Before/After 연계 시연 | 생성된 4개 원천 테이블은 의도적으로 설명이 누락된(Unenriched) 상태로 생성되어, `bigquery-data-agent-semantic-enricher` 실행 전후의 정확도 차이를 시연할 수 있어야 한다. |
| **BR-06** | 원클릭 리소스 정리 | `--teardown` 실행 시 실습에 사용된 `cymbal_gold` 데이터셋과 하위 테이블/뷰를 일괄 삭제하여 과금을 방지하여야 한다. |

---

## 4. 비기능 요구 사항 (Non-Functional Requirements)

| 요구 사항 ID | 분류 | 상세 요구 사항 |
| :--- | :--- | :--- |
| **NFR-01** | 완전 독립성 (Zero Dependency) | `bigquery-data-agent-starter`와 `bigquery-data-agent-semantic-enricher`는 서로의 파일이나 코드를 import하지 않고 100% 자체 완결적으로 동작한다. |
| **NFR-02** | 비파괴성 및 안전성 | `--dry-run` 모드는 실제 GCP 리소스 변경 없이 모든 DDL/DML과 지침을 사전 출력하여야 한다. |
| **NFR-03** | 식별 정보 비식별화 | 모든 코드와 샘플 데이터는 특정 기업명을 배제하고 표준 가명(`cymbal_gold`)만을 사용한다. |
