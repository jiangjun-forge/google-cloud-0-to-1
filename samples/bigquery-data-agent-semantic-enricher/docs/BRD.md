<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 비즈니스 요구사항 명세서 (BRD: Business Requirements Document)
## 프로젝트명: BigQuery Data Agent Semantic Metadata Enricher

**문서 버전**: 1.0.0  
**작성 일자**: 2026-09-10  
**상태**: 승인 완료 (Approved)  
**대상 서비스**: Google Cloud (`BigQuery`, `Dataplex`, `GeminiAPI`, `KnowledgeCatalog`)

---

## 1. 비즈니스 개요 및 프로젝트 목적 (Executive Summary)

### 1.1 배경 및 추진 배경
엔터프라이즈 기업들은 비즈니스 의사결정 속도를 높이고 데이터 민주화를 달성하기 위해 생성형 인공 지능(Gen AI) 기반의 **자연어 분석 에이전트(BigQuery Data Agent / NL2SQL)**를 적극 도입하고 있다. 그러나 실제 도입 과정에서 자연어 질문에 대해 잘못된 테이블을 조인하거나 엉터리 SQL을 생성하는 **심각한 환각(Hallucination)** 문제가 빈번히 발생하여 프로젝트가 중단되거나 신뢰를 상실하는 사례가 급증하고 있다.

### 1.2 비즈니스 난제 (Pain Points)
1. **메타데이터 부재로 인한 모델 환각**: 대다수 기업의 BigQuery 테이블과 컬럼에는 설명(Description)이 비어 있거나 축약어(예: `amt`, `cd`, `qty_diff`)만 존재하여, LLM이 컬럼의 실제 의미나 단위, 할인 전후 여부를 임의로 추정하여 잘못된 계산을 수행한다.
2. **비즈니스 계산 공식(Formula) 미표준화**: '순매출(Net Revenue)', '결품 위험(Cover Hours)', '할인 남용률' 등 업무 규칙이 코드 내 하드코딩되어 있고 카탈로그 용어집에 등록되어 있지 않아, 사용자 질문마다 서로 다른 수식으로 집계된다.
3. **수작업 메타데이터 큐레이션의 한계**: 수백, 수천 개의 테이블과 컬럼 설명을 일일이 사람이 작성하는 데 수개월이 소요되어 Data Agent의 전사 확산이 지연된다.

### 1.3 프로젝트 목표
본 프로젝트는 구글 클라우드 공식 베스트 프랙티스에 따라 대상 데이터셋의 메타데이터 충실도를 자동 진단하여 **"Data Agent NL2SQL 준비도 점수"**를 매기고, Gemini와 Dataplex 데이터 프로파일링 통계를 결합하여 **고품질 표준 설명과 비즈니스 용어집(Glossary) 수식 템플릿을 1클릭으로 자동 생성 및 주입**하는 데 목적이 있다.

---

## 2. 이해관계자 및 대상 페르소나 (Stakeholders & Personas)

| 페르소나 | 주요 관심사 및 목표 | 본 솔루션을 통한 비즈니스 혜택 |
| :--- | :--- | :--- |
| **데이터 플랫폼 리드 / 아키텍트** | Data Agent PoC 성공 및 엔터프라이즈 확산 | 메타데이터 준비도 점수를 통해 신뢰도 지표를 확보하고 전사 롤아웃 가속화 |
| **빅데이터 엔지니어** | 테이블/컬럼 설명 작성 자동화 | 수작업 메타데이터 등록 부담 90% 경감 및 BigQuery 스키마 원클릭 자동 패치 |
| **비즈니스 분석가 / 현업 사용자** | 자연어 질문에 대한 정확한 SQL 실행 결과 | 계산 공식 왜곡 없는 정밀한 비즈니스 메트릭 도출 및 분석 셀프서비스 달성 |
| **AI CoE 및 거버넌스 담당자** | 시맨틱 레이어 거버넌스 표준 수립 | Dataplex Knowledge Catalog 기반 비즈니스 용어집 및 데이터 품질 연동 체계 완성 |

---

## 3. 프로젝트 범위 및 경계 정의 (Scope & Boundary)

### 3.1 In-Scope (자동화 및 보강 영역)
1. BigQuery 테이블 수준 설명(Table Description) 누락 여부 검사
2. BigQuery 컬럼 수준 설명(Column Description) 커버리지 산출
3. Dataplex 데이터 프로파일링 통계(최솟값, 최댓값, 고유값, 널 비율) 수집 상태 점검
4. Knowledge Catalog 비즈니스 용어집(Glossary) 및 수식(Formula) 연동 여부 감사
5. 4대 핵심 지표 기반 종합 "Data Agent NL2SQL 준비도 점수(0~100점)" 산출
6. Gemini 기반 표준 Table/Column Description 자동 생성
7. Dataplex Knowledge Catalog 배포용 용어집 YAML 템플릿 자동 도출
8. BigQuery 스키마 안전 패치(`--apply`) 및 가상 모의 실행(`--dry-run`)

### 3.2 Out-of-Scope (수동 승인 및 비즈니스 정책 영역)
- 비즈니스 용어의 최종 확정을 위한 현업 데이터 오너 서명 절차
- 원천 데이터베이스(RDBMS, ERP)의 DDL 원본 파일 수정

---

## 4. 상세 비즈니스 요구사항 명세 (Functional Requirements)

| 요구사항 ID | 기능 영역 | 상세 요구사항 및 비즈니스 목적 |
| :--- | :--- | :--- |
| **BR-01** | 테이블 설명 감사 | 대상 데이터셋의 모든 테이블에 대해 AI 에이전트 라우팅에 충분한 길이와 의미를 가진 Table Description이 존재하는지 검사하여야 한다. |
| **BR-02** | 컬럼 설명 감사 | 전체 컬럼 대비 명확한 설명이 기재된 컬럼의 비율(커버리지 %)을 산출하여 모호한 컬럼 존재 위험을 수치화하여야 한다. |
| **BR-03** | 프로파일링 검증 | Dataplex Data Profile 스캔 수행 여부를 확인하여, 유효값 범위 및 고유값 목록이 LLM 그라운딩에 제공 가능한 상태인지 평가하여야 한다. |
| **BR-04** | 용어집 공식 감사 | 주요 비즈니스 계산 메트릭에 대해 Dataplex Knowledge Catalog 용어집 수식(`Formula`)이 바인딩되어 있는지 감사하여야 한다. |
| **BR-05** | 준비도 점수화 | 테이블 설명(30%), 컬럼 설명(30%), 프로파일(20%), 용어집(20%) 가중치를 합산하여 100점 만점의 Data Agent 준비도 점수를 산출하여야 한다. |
| **BR-06** | 지능형 보강 계획 | 모호하거나 누락된 컬럼에 대해 Gemini 모델을 통해 실데이터 통계가 반영된 표준 설명 텍스트를 자동 생성하여야 한다. |
| **BR-07** | 용어집 템플릿화 | 핵심 계산 수식(예: `SAFE_DIVIDE`, `subtotal - discount + tax`)을 포함한 Knowledge Catalog 배포용 YAML 파일을 자동 생성하여야 한다. |
| **BR-08** | 스키마 패치 반영 | `--apply` 플래그 지정 시, 기존 데이터를 손상시키지 않고 BigQuery 테이블/컬럼 메타데이터만을 안전하게 패치(`client.update_table`)하여야 한다. |
| **BR-09** | 가상 모의 실행 | 실제 GCP 자격 증명이나 BigQuery 데이터셋이 없는 환경에서도 결정론적 샘플 데이터로 진단 및 보강 효과를 시연할 수 있어야 한다. |

---

## 5. 비기능 요구사항 (Non-Functional Requirements)

| 요구사항 ID | 분류 | 상세 요구사항 |
| :--- | :--- | :--- |
| **NFR-01** | 비파괴성 (Zero Risk) | 기본 진단 모드는 순수 읽기 전용으로 동작하며, 메타데이터 반영(`--apply`) 시에도 실제 데이터 레코드는 일절 변경하지 않는다. |
| **NFR-02** | 실행 성능 | 100개 미만의 테이블 스키마 진단을 10초 이내에 완료한다. |
| **NFR-03** | 확장성 | 단일 테이블부터 대규모 전사 데이터 웨어하우스 데이터셋까지 동일한 로직으로 진단 및 보강을 지원한다. |

---

## 6. 검증 및 인수 판정 기준 (Acceptance Criteria)

- [x] 준비도 점수 산출 공식이 4대 핵심 메타데이터 지표를 정확히 반영하는가?
- [x] 진단 결과표에서 FAIL 판정 시 원인 영역이 명확하게 식별되는가?
- [x] `--enrich` 옵션 실행 시 표준 설명과 용어집 YAML 파일이 정상 생성되는가?
- [x] `--dry-run` 모드가 100% 자체 완결적으로 동작하는가?
