<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# Gemini Enterprise 자율형 사내 노코드 에이전트 팩토리 비즈니스 요구 사항 명세서 (BRD)

본 문서는 사내 비개발자 임직원이 제미나이 엔터프라이즈 앱(Gemini Enterprise app) 내에서 대화형 인터뷰와 추천 칩 선택만으로 사내 승인된 노코드(No-code) 에이전트를 자율 생성하고 즉시 등록할 수 있도록 지원하는 메타 에이전트 팩토리 솔루션의 비즈니스 요구 사항 명세서(Business Requirements Document)다.

---

## 1. 추진 배경 및 비즈니스 동기

1. **에이전트 도입 병목 현상 및 중앙 IT 부서의 운영 부하**:
   - 사내에 Gemini Enterprise app(구 Agentspace)이 도입된 후, 인사, 재무, 마케팅, 영업, 개발 등 현업 부서의 맞춤형 업무 보조 에이전트 제작 요청이 급증하고 있다.
   - 하지만 현재는 클라우드 콘솔 접근 권한을 가진 중앙 클라우드 인프라팀이 에이전트 기획, 지침(Instructions) 작성, 스타터 질문(Starter Prompts) 등록, 공개(Publish) 작업을 일일이 수작업으로 대행하고 있어 극심한 배포 병목이 발생한다.

2. **비개발자 임직원의 백지 증후군(Blank Canvas Syndrome)**:
   - 일반 임직원에게 빈 프롬프트 입력창을 제공할 경우, 어떤 지침과 가드레일을 작성해야 할지 몰라 시도를 포기하거나 비효율적인 단문 프롬프트만 입력하는 문제가 발생한다.
   - 검증된 부서별 업무 추천 칩(Seed Chips)과 실시간 구글 검색(Google Search Grounding)을 결합하여, 사용자가 최소한의 선택만으로도 업계 최신 표준 지침을 자동 완성할 수 있는 직관적인 경험이 필수적이다.

3. **섀도우 에이전트(Shadow Agent) 양산 방지 및 엔터프라이즈 거버넌스 강제**:
   - 임직원이 임의로 에이전트를 생성할 경우 개인 식별 정보(PII) 유출 위험, 모델 환각(Hallucination), 비인가 외부 데이터 반출 등 심각한 보안 사각지대가 발생한다.
   - 표준 메타 에이전트를 통해서만 에이전트가 생성되도록 단일 창구를 일원화하고, 사내 보안 수칙, 무학습(No-Training) 원칙, 최소 권한 원칙이 100% 강제 주입되는 설계 기반 거버넌스(Governance by Design) 체계가 요구된다.

---

## 2. 핵심 비즈니스 요구 사항 목록 (Business Requirements)

| 요구 사항 ID | 구분 | 핵심 비즈니스 목표 및 요구 명세 |
| :--- | :--- | :--- |
| **BR-01** | 자율형 메타 에이전트 배포 | 클라우드 인프라 담당자가 단 1회의 배포 명령으로 사내 Gemini Enterprise app 포털에 전사 공용 메타 에이전트(`@에이전트 팩토리`)를 등록할 수 있어야 한다. |
| **BR-02** | 추천 칩 기반 인터뷰 | 임직원이 Gemini Enterprise app 웹 채팅창에서 부서별 추천 칩을 확인하고, 1~2회의 선택만으로 복잡한 프롬프트 작성 없이 에이전트 제작 의도를 확정할 수 있어야 한다. |
| **BR-03** | 실시간 검색 요구사항 보강 | 정적 템플릿에 국한되지 않고, 사용자가 선택한 업무 주제에 대해 실시간 웹 검색을 수행하여 2026년 최신 규정, 법령, 실무 지침을 자동으로 보강 합성해야 한다. |
| **BR-04** | 무권한 임직원 대행 등록 | 일반 임직원은 구글 클라우드(Google Cloud) 콘솔 접근 및 IAM 권한이 전무(Zero Permission)하더라도, 전용 대행 서비스 계정을 통해 Gemini Enterprise app에 개인/팀 전용 에이전트로 자율 등록할 수 있어야 한다. |
| **BR-05** | 설계 기반 거버넌스 강제 | 생성되는 모든 노코드 에이전트의 지침서에 사내 보안 가드레일, 개인 식별 정보 보호, 환각 방지 폴백 원칙이 필수 골든 룰로 자동 삽입되어야 한다. |

---

## 3. 기대 효과 및 비즈니스 KPI

1. **에이전트 제작 및 배포 소요 시간 단축**:
   - 기존 중앙 IT 접수 및 수작업 배포 소요 시간(평균 3~5 영업일)을 현업 임직원 대화 1분 내외(즉시 배포)로 단축한다.
2. **사내 거버넌스 준수율 100% 달성**:
   - 수작업 등록 시 누락되던 보안 가드레일 및 무학습 서약을 팩토리 엔진이 강제 삽입하여 컴플라이언스 위험을 원천 차단한다.
3. **현업 업무 자동화 확산**:
   - 추천 칩 및 실시간 검색 보강을 통해 비개발자 임직원의 에이전트 제작 장벽을 제거하고, 전사 단위의 자율적 생성형 AI 활용을 촉진한다.
