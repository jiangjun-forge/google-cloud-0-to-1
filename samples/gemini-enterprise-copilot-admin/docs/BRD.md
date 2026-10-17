<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# Gemini Enterprise 어드민 코파일럿 비즈니스 요구 사항 명세서 (BRD)

본 문서는 사내 IT 어드민 및 클라우드 인프라 운영팀이 제미나이 엔터프라이즈 앱(Gemini Enterprise app) 운영 중 직면하는 5대 핵심 관리 과제(도메인 충돌, 외부 마켓플레이스 차단 거버넌스, 유휴 라이선스 회수, Overage 과금 방어, 사내망 FQDN 허용)를 대화형으로 신속 진단하고 자율 해결할 수 있도록 지원하는 어드민 전담 코파일럿 솔루션의 비즈니스 요구 사항 명세서(Business Requirements Document)다.

---

## 1. 추진 배경 및 비즈니스 동기

1. **엔터프라이즈 어드민의 반복적인 기술 문의 및 운영 부담**:
   - Gemini Enterprise 도입 직후 사내 IT 헬프데스크 및 인프라 어드민 팀에는 도메인 인증 오류, 외부 마켓플레이스 에이전트 차단 방법, 라이선스 배분 및 비용 알림 등 다양한 운영 문의가 집중된다.
   - 각 문제마다 서로 다른 관리 콘솔(Google Admin 콘솔, GCP 콘솔, Discovery Engine 콘솔, Billing 콘솔)을 찾아다니며 설정을 변경해야 하므로 운영 비효율이 극심하다.

2. **보안 및 규제 컴플라이언스 준수 의무**:
   - 금융권 및 대기업 보안 규정에 따라 사내 승인되지 않은 외부 공개 에이전트 사용을 차단하고, 임직원의 AI Studio API 키 발급 등 섀도우 과금을 원천 봉쇄해야 한다.
   - 와일드카드 도메인 허용이 불가한 폐쇄망 프록시 환경에서 필수 코어 FQDN의 방화벽 인가 목록을 정확히 도출해야 한다.

3. **Gemini Enterprise app 내장 어드민 헬프데스크 구현**:
   - 어드민 담당자가 터미널이나 콘솔을 직접 뒤지지 않고도, Gemini Enterprise 웹 채팅창에서 자연어 대화 또는 추천 칩 선택만으로 진단 스크립트와 조치 명령어를 즉시 받아볼 수 있어야 한다.

---

## 2. 핵심 비즈니스 요구 사항 목록 (Business Requirements)

| 요구 사항 ID | 구분 | 핵심 비즈니스 목표 및 요구 명세 |
| :--- | :--- | :--- |
| **BR-01** | 도메인 충돌 및 테넌트 온보딩 진단 | 사내 기본 도메인 선점 충돌 시 Cloud Identity Free 기반 테넌트 배포 및 TXT 레코드 소유권 확인 절차를 자동 안내해야 한다. |
| **BR-02** | 사내 거버넌스 및 마켓플레이스 차단 | 외부 공개 에이전트 마켓플레이스를 전면 차단하고 사내 승인 커스텀 에이전트만 노출하는 조직 정책 매니페스트를 합성해야 한다. |
| **BR-03** | 라이선스 채택률 및 유휴 라이선스 회수 | 부서별 활성 사용자 지표를 분석하고 30일 이상 미사용 임직원의 라이선스를 자동 회수할 수 있는 분석 쿼리를 제공해야 한다. |
| **BR-04** | Overage 과금 방어 및 결제 거버넌스 | 일일 쿼터 초과 쓰로틀링을 방어하고, Google AI Studio 유료 API 키 발급을 차단하는 Billing RBAC 가이드를 도출해야 한다. |
| **BR-05** | 사내망 Exact FQDN 및 방화벽 진단 | 와일드카드 도메인이 불허되는 사내 관문 프록시(SWG) 환경에서 필수 443 포트 아웃바운드 FQDN 목록을 산출해야 한다. |
| **BR-06** | 에이전트 스프롤 및 관리 헬 감사 | 수백 개 에이전트 난립 시 60일 미사용 좀비 에이전트, 토큰 과소비 톱 10, 장애 에이전트를 식별하는 BigQuery 쿼리 팩을 제공해야 한다. |
| **BR-07** | 원클릭 로그 싱크 및 콘솔 딥링크 | Cloud Logging의 감사 로그를 BigQuery로 라우팅하는 로그 싱크를 명령어 한 줄로 구축하고 GCP 콘솔 GE Admin 3단계 딥링크를 안내해야 한다. |
| **BR-08** | 대화형 추천 칩 및 원클릭 리포트 | Dolphin UI 네이티브 `suggested_questions` 추천 칩을 출력하고 `report.md` 표준 진단 보고서를 덮어써야 한다. |

---

## 3. 기대 효과 및 비즈니스 KPI

1. **어드민 운영 문의 대응 시간 80% 단축**: 5대 핵심 관리 이슈에 대한 원스톱 자율 진단으로 어드민의 티켓 처리 시간을 대폭 절감한다.
2. **사내 유휴 라이선스 비용 15% 이상 절감**: 미사용 라이선스를 신속하게 식별 및 회수하여 FinOps 비용 최적화를 달성한다.
3. **외부 미승인 에이전트 및 섀도우 과금 0건 달성**: 조직 정책 및 결제 거버넌스를 강화하여 엔터프라이즈 보안 무결성을 확보한다.
