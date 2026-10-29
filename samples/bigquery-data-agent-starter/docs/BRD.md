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
## 프로젝트명: BigQuery Data Agent 45-Minute Hands-on Starter Kit (Standalone & Optional Gemini Enterprise app) (As of 2026-10-19)

---

## 1. 비즈니스 개요 및 프로젝트 목적 (Executive Summary)

### 1.1 추진 배경
엔터프라이즈 유통 및 그룹사 대상 핸즈온 워크숍에서 참석자들은 BigQuery 데이터를 기반으로 자연어 분석을 수행하는 **BigQuery Data Agent**를 직접 만들고, 이를 BigQuery Studio 내에서 **단독(Standalone)**으로 활용하거나 필요에 따라 **Gemini Enterprise App** 사내 갤러리에 직결 게시하는 전 과정을 45분 내에 체험하고자 한다. 특히 구글 1P 완전 관리형 런타임(GDA `dataAgents` REST API)과 A2A(Agent-to-Agent) 표준 프로토콜을 결합하여, 컨테이너 빌드나 유휴 VM 비용 없이 CLI 원클릭으로 프로비저닝하는 골든 아키텍처를 실증하고자 한다.

### 1.2 비즈니스 난제 (Pain Points)
1. **초기 데이터 구성 및 에이전트 빌드 시간 과다**: 45분이라는 제한된 워크숍 시간 내에 참석자가 일일이 테이블을 설계하고 콘솔 UI에서 수동 클릭으로 에이전트를 생성하느라 정작 중요한 분석 질의 실습 시간이 부족해진다.
2. **사내 환경 다양성 (Standalone vs Gemini Enterprise app)**: BigQuery Studio 내에서 단독으로 에이전트를 사용하는 데이터 부서와 제미나이 엔터프라이즈 앱(Gemini Enterprise App)에 게시하여 전사 포털로 통합하려는 조직이 혼재되어 있어, 두 시나리오를 모두 지원하는 유연한 아키텍처가 요구된다.
3. **신속한 검증 환경 제공**: 순매출 및 결품 커버 시간 공식이 포함된 시맨틱 골드 뷰와 원천 테이블을 즉각 프로비저닝하여 검증 시간을 최소화해야 한다.

### 1.3 프로젝트 목표
본 프로젝트는 명령어 한 줄(`--setup-demo`)로 **`cymbal_gold` 4개 원천 테이블, 실데이터, 시맨틱 뷰를 10초 내에 자동 구축**하고, 구글 완전 관리형 런타임을 통해 **GDA `dataAgents` 원클릭 프로비저닝(`--deploy-agent`)**, **A2A Agent Card 표준 규격 생성**, **Discovery Engine API 기반 Gemini Enterprise App 직결 등록(`--register-ge-app`)**, **골든 프롬프트 3선 검증**을 원스톱으로 제공하는 데 목적이 있다.

---

## 2. 이해관계자 및 대상 페르소나 (Stakeholders & Personas)

| 페르소나 | 주요 관심사 및 목표 | 본 솔루션을 통한 비즈니스 혜택 |
| :--- | :--- | :--- |
| **사내 워크숍 참석자 (아키텍트 / 분석가)** | 45분 내에 BigQuery Data Agent 구축 및 질의응답 완주 | 원클릭 데이터 구성 및 CLI 원클릭 GDA 에이전트 배포로 실습 시간 단축 |
| **데이터 플랫폼 엔지니어** | 시맨틱 레이어 기반 NL2SQL 정확도 검증 | 시맨틱 뷰 및 골든 프롬프트를 통한 NL2SQL 응답 검증 환경 확보 |
| **워크숍 진행 엔지니어 (인프라 / 데이터 플랫폼 담당자)** | 참석자 실습 오류 최소화 및 시간 내 전원 완주 | 복잡한 수동 클릭 없이 원클릭(`--all`)으로 구동되는 독립 핸즈온 실습 키트 확보 |

---

## 3. 상세 비즈니스 요구 사항 명세 (Business Requirements)

| 요구 사항 ID | 기능 영역 | 상세 요구 사항 및 비즈니스 목적 |
| :--- | :--- | :--- |
| **BR-01** | 스몰셋 데이터셋 자동 구성 | `--setup-demo` 실행 시 `cymbal_gold` 데이터셋 내에 `pos_transactions_gold`, `gold_inventory_reconciliation_ledger`, `pos_anomaly_alerts`, `historical_transactional_data` 4개 테이블과 실데이터를 자동 생성하여야 한다. |
| **BR-02** | 시맨틱 골드 뷰 생성 | 순매출(`subtotal_amount - discount + tax_amount`)과 결품 커버 시간(`SAFE_DIVIDE((shelf_qty + backroom_qty), (total_units_sold_intraday / 12.0))`)이 내장된 시맨틱 뷰(`v_cymbal_retail_semantic`)를 자동 생성하여야 한다. |
| **BR-03** | GDA dataAgents 자동 프로비저닝 | `--deploy-agent` 실행 시 구글 완전 관리형 테넌트 GDA REST API(`geminidataanalytics.googleapis.com/v1beta`)를 호출하여 유휴 비용 없이 데이터 에이전트를 자동 생성하여야 한다. |
| **BR-04** | A2A Agent Card 표준 규격 도출 | GDA dataAgent 생성 후 A2UI, starter_prompts, full_history_when_stateless 확장이 포함된 A2A Agent Card JSON(`a2a_agent_card.json`)을 자동 생성 및 보존하여야 한다. |
| **BR-05** | Gemini Enterprise app 직결 연동 | `--register-ge-app` 실행 시 Discovery Engine REST API를 통해 Gemini Enterprise App 사내 갤러리에 `a2aAgentDefinition`으로 직결 등록하여야 한다. |
| **BR-06** | 콘솔 UI 수동 등록 보조 가이드 | `--agent-config` 실행 시 BigQuery Studio > Agents (Agent Catalog)에 붙여넣을 수 있는 System Instructions와 Verified Queries를 출력하여야 한다. |
| **BR-07** | 올인원 일괄 자동 배포 | `--all` 실행 시 Step 1(데이터셋) + Step 2(GDA 에이전트) + Step 3(GE App 연동)을 한 번에 순차 실행하여야 한다. |
| **BR-08** | 골든 프롬프트 3선 검증 | 지점별 순매출, 결품 위험 품목, 이상 거래 탐지 등 비즈니스 시나리오를 검증할 수 있는 대표 프롬프트를 제공하여야 한다. |
| **BR-09** | 원클릭 리소스 정리 | `--teardown` 실행 시 실습에 사용된 `cymbal_gold` 데이터셋과 GDA Data Agent를 일괄 삭제하여 과금을 방지하여야 한다. |
| **BR-10** | 자원 거버넌스 라벨링 | 생성되는 모든 데이터셋, 테이블, 뷰, GDA 리소스에 4대 필수 표준 라벨(`managed-by=google-cloud-0-to-1`, `scenario=bigquery-data-agent-starter`, `env=sample`, `created-by=customer-engineer`)을 누락 없이 주입하여야 한다. |

---

## 4. 비기능 요구 사항 (Non-Functional Requirements)

| 요구 사항 ID | 분류 | 상세 요구 사항 |
| :--- | :--- | :--- |
| **NFR-01** | 완전 독립성 (Zero Dependency) | 타 모듈이나 외부 라이브러리 의존 없이 자체 완결적으로 동작한다. |
| **NFR-02** | 비파괴성 및 안전성 | `--dry-run` 모드는 실제 GCP 리소스 변경 없이 모든 DDL/DML, GDA 페이로드, A2A Agent Card를 사전 출력하여야 한다. |
| **NFR-03** | 식별 정보 비식별화 | 모든 코드와 샘플 데이터는 특정 기업명을 배제하고 표준 가명(`cymbal_gold`)만을 사용한다. |
| **NFR-04** | FinOps 자원 추적성 | 워크숍 실습 인프라가 사내 비용 관리 시스템에서 자동 식별될 수 있도록 표준 메타데이터 태깅을 강제한다. |
