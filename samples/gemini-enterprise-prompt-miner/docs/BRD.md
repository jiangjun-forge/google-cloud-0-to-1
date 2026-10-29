<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# Gemini Enterprise 프롬프트 마이너 비즈니스 요구 사항 명세서 (BRD)

본 문서는 사내 제미나이 엔터프라이즈 앱(Gemini Enterprise app) 환경에서 축적된 사용자 질의(Prompt) 로그를 인라인 PII 마스킹과 멀티 턴 세션 묶음 정제를 거쳐 빅쿼리(BigQuery) 내장 임베딩(`ML.GENERATE_EMBEDDING`)과 자율 적응형(Auto-K) 군집화로 분석하고, 사내 3R(반복성 Repetitive, 규칙성 Rule-based, 검색 집약성 Retrieval-heavy) 마이크로 업무를 발굴하여 스킬 및 에이전트 전환 파이프라인을 극대화하기 위한 비즈니스 요구 사항 명세서(Business Requirements Document)다.

---

## 1. 추진 배경 및 비즈니스 동기 (Business Context)

1. **상투적 5대 대분류 탈피 및 실질적 자산화 건수 극대화**:
   - 임직원 질의를 5개 내외의 대분류(CS, HR, IT, 마케팅, 정산)로 뭉뚱그리면 누구나 머릿속으로 상상 가능한 결과만 도출되어 비싼 벡터 분석의 실효성이 상실된다.
   - 본 도구의 핵심 목적은 수백, 수천 명의 임직원이 겪는 마이크로 업무를 고해상도로 쪼개어 발굴하고, 이를 사내 '도구화 수(API 도구 / Tool)'와 '에이전트화 수(지식 검색 RAG / 자율 에이전트)' 파이프라인으로 전환시키는 데 있다.

2. **임직원 프라이버시 보호 및 민감 PII 인라인 살균**:
   - 실제 임직원 질의에는 주민등록번호, 계좌번호, 전화번호, 이메일, IP 등 민감 정보가 포함될 수 있어 보안 및 컴플라이언스 심의의 가장 큰 걸림돌이 된다.
   - 분석 전 단계에서 모든 민감 PII를 인라인 자동 마스킹하고, 사용자 계정을 솔트 해시 가명(`emp-xxxx`)으로 비식별화하여 프라이버시 침해를 사전에 방어해야 한다.

3. **멀티 턴 대화 세션의 단일 워크플로우 묶음 정제**:
   - 사용자의 2~3턴 후속 질문이 개별 문장으로 파편화되면 문맥이 상실되어 오라우팅되거나 잡음 군집으로 왜곡된다.
   - `session_id` 기반으로 대화 세션을 단일 업무 워크플로우로 묶어 결합 임베딩을 수행해야 한다.

4. **빅쿼리(BigQuery) 단일 임베딩 표준 (고객 인지 부하 제로화)**:
   - 다양한 외부 SDK, 엔드포인트 옵션, 별도 벡터 DB 인덱스를 제시하면 고객사는 도입을 주저하고 검토가 지연된다.
   - 이미 로그가 적재된 빅쿼리 내장 `ML.GENERATE_EMBEDDING` 단일 경로만을 제공하여 의존성과 인지 부하를 제로화해야 한다.

---

## 2. 핵심 비즈니스 요구 사항 목록 (Business Requirements)

### BR-01: 사내 프롬프트 로그 수집 및 멀티 턴 세션 묶음 정제
* 시스템은 BigQuery 감사 데이터셋(`cloudaudit_googleapis_com_data_access`)에서 `session_id`를 기반으로 사용자 질의를 순서대로 취합하여 단일 대화 워크플로우 단위로 병합할 수 있어야 한다.

### BR-02: 인라인 PII 마스킹 및 임직원 식별 정보 비식별화
* 시스템은 주민등록번호, 계좌번호, 휴대전화번호, 이메일, IP 등 6대 핵심 PII를 인라인 정규식 엔진으로 즉시 마스킹하고, 사용자 계정을 가명 식별자(`emp-xxxx`)로 변환해야 한다.

### BR-03: BigQuery 단일 내장 임베딩 파이프라인
* 시스템은 외부 복합 SDK 없이, 데이터가 저장된 빅쿼리 내장 `ML.GENERATE_EMBEDDING` SQL 함수만을 단일 표준으로 활용하여 고차원 임베딩을 생성해야 한다.

### BR-04: 자율 적응형(Auto-K) 고해상도 마이크로 업무 군집화
* 시스템은 5개 대분류 강제 고정을 완전히 배제하고, 입력 질의 모수와 임베딩 분화도에 따라 최적 군집 수 K(10~30+)를 자율 결정하여 실질적 마이크로 업무를 도출해야 한다.

### BR-05: 3R 기반 에이전트/스킬 전환 파이프라인 대시보드 도출
* 시스템은 각 군집별 최적의 자산 유형(API 연동 도구 vs 지식 검색 에이전트 vs 자율 복구 에이전트)을 정밀 매핑하고, 전체 전환 건수 및 체계적인 자산화 파이프라인 대시보드를 제공해야 한다.

---

## 3. 제약 사항 및 선결 과제 (Constraints)

1. **단일 빅쿼리 의존성 준수**:
   * 클라이언트 측에 무거운 머신러닝 라이브러리나 다중 SDK 의존성을 부과하지 않으며, 오직 `google-cloud-bigquery` 단일 클라이언트로만 동작한다.
2. **가상 실행(Dry-Run) 지원**:
   * GCP 프로젝트 권한이 없거나 Cloud Logging이 아직 활성화되지 않은 환경에서도 내장된 49건(24개 세션)의 모의 데이터셋을 통해 동일한 분석 파이프라인을 검증할 수 있어야 한다.

---

## 4. 비즈니스 성공 지표 (KPIs)

* **실질 자산화 전환 건수 극대화**: 상투적 5대 대분류를 넘어 10개 이상의 즉시 구현 가능한 스킬 및 에이전트 전환 파이프라인 발굴.
* **프라이버시 침해 및 PII 누출 0건**: 보고서 및 콘솔 출력 내 개인 식별 정보 노출 0건 및 안전 마스킹 검증.
* **고객 의사 결정 지연 제로화**: BigQuery 단일 표준화로 다중 옵션으로 인한 고객의 도입 주저 및 검토 공수 제거.
