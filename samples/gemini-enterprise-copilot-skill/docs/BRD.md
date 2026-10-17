<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# Gemini Enterprise 자율형 사내 스킬 팩토리 비즈니스 요구 사항 명세서 (BRD)

본 문서는 사내 제미나이 엔터프라이즈 앱(Gemini Enterprise app) 환경에서 에이전트가 손발처럼 호출하여 사내 시스템(구글 시트, 슬랙, 지라, ERP 등)을 직접 제어할 수 있는 도구 및 확장 기능(Tools / Extensions / Action Skills)을 비개발자 및 부서 관리자가 대화형으로 자율 생성하고 안전하게 등록할 수 있도록 지원하는 사내 스킬 팩토리 솔루션의 비즈니스 요구 사항 명세서(Business Requirements Document)다.

---

## 1. 추진 배경 및 비즈니스 동기

1. **에이전트의 단순 대화 한계 극복 및 시스템 제어 수요**:
   - 텍스트 질의응답 중심의 에이전트를 넘어, "사내 구글 시트(Google Sheets)에 승인 행 추가", "지라(Jira) 장애 티켓 발행", "슬랙(Slack) 긴급 알림 전송", "ERP 전표 조회" 등 실제 기업 시스템과 상호작용하는 액션 스킬(Action Skills)에 대한 현업의 수요가 폭발하고 있다.
   - 하지만 비개발자 임직원은 OpenAPI 3.0 스키마(YAML/JSON), 엔드포인트 파라미터 규격, HTTP 헤더 인증 처리를 직접 작성할 수 없어 도구 확장이 완전히 중단되는 문제가 발생한다.

2. **사내 API 자격 증명(Credentials) 유출 위험 차단**:
   - 현업 임직원이 시스템 연동을 시도할 때 API 토큰, 웹훅 URL, 데이터베이스 비밀번호를 프롬프트 지침이나 소스 코드에 평문(Plaintext)으로 하드코딩하는 보안 사고 위험이 상존한다.
   - 스킬 생성 시 시크릿 매니저(Secret Manager)와 연동하여 자격 증명을 안전하게 격리 보관하고, 에이전트 런타임에 주입되는 보안 볼트(Vault) 아키텍처가 필수적이다.

3. **조회(Read) vs 변경(Write) 작업의 거버넌스 분리**:
   - 시스템 데이터를 단순히 읽어오는 조회 스킬과, 데이터베이스를 수정하거나 결재를 승인하는 쓰기/변경 스킬을 동일한 권한으로 취급할 경우 치명적인 데이터 오염이나 비인가 결재 사고가 발생할 수 있다.
   - 스킬 유형에 따라 즉시 활성화(조회용)와 관리자 승인 플래그(변경용)를 구조적으로 분리하는 엔터프라이즈 거버넌스 체계가 요구된다.

---

## 2. 핵심 비즈니스 요구 사항 목록 (Business Requirements)

| 요구 사항 ID | 구분 | 핵심 비즈니스 목표 및 요구 명세 |
| :--- | :--- | :--- |
| **BR-01** | 대화형 노코드 스킬 생성 | 비개발자가 복잡한 OpenAPI 문법 없이도 대화형 칩 선택이나 자연어 설명만으로 Gemini Enterprise app용 도구 매니페스트(JSON/YAML)를 자동 도출해야 한다. |
| **BR-02** | 사내 8대 핵심 시스템 도구 프리셋 | 구글 시트, 슬랙, 지라, 빅쿼리, ERP, 클라우드 모니터링 등 사내에서 가장 빈번히 사용되는 8대 시스템 연동 템플릿을 기본 내장해야 한다. |
| **BR-03** | 자격 증명 보안 볼트 연동 | API 토큰이나 인증키의 평문 노출을 원천 차단하고, 시크릿 매니저(Secret Manager) 참조 및 대행 서비스 계정 기반 인증을 강제해야 한다. |
| **BR-04** | 조회(Read) vs 변경(Write) 승인 통제 | 데이터 조회 스킬은 자율 생성 즉시 활성화를 허용하고, 데이터 수정/삭제/결재 스킬은 사내 관리자 승인(Admin Approval)을 필수로 거치도록 격리해야 한다. |
| **BR-05** | Gemini Enterprise app 도구 레지스트리 원클릭 등록 | 완성된 도구 매니페스트를 사내 Gemini Enterprise app 도구 레지스트리에 배포하고, 기존 에이전트에 클릭 한 번으로 바인딩할 수 있어야 한다. |
| **BR-06** | 표준 리소스 라벨링 적용 의무화 | 사내 거버넌스, FinOps 비용 배분 및 자원 추적성을 위해 생성되는 도구 매니페스트, 보안 볼트 시크릿 및 관련 리소스에 4대 표준 라벨(`managed-by`, `scenario`, `env`, `created-by`)을 필수로 주입하여야 한다. |

---

## 3. 기대 효과 및 비즈니스 KPI

1. **사내 시스템 연동 스킬 제작 기간 90% 단축**:
   - 외부 시스템 연동용 OpenAPI 작성 및 배포(평균 1~2주)를 비개발자 인터뷰 5분 이내로 단축한다.
2. **사내 API 자격 증명 보안 사고 0건 유지**:
   - 시크릿 매니저 연동 강제를 통해 임직원의 API 키 하드코딩 및 프롬프트 노출 사고를 원천 방지한다.
3. **에이전트 실무 생산성 비약적 향상**:
   - 단순 챗봇을 전사 기간계 시스템과 유기적으로 연결된 '자율 실행형 워크플로우 봇'으로 격상시킨다.
