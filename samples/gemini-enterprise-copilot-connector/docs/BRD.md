<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# Gemini Enterprise 데이터 커넥터 스캐폴더 비즈니스 요구 사항 명세서 (BRD)

본 문서는 사내 클라우드 아키텍트 및 데이터 엔지니어가 사내 다양한 기업 기간계 저장소(Jira, Confluence, Salesforce, ServiceNow, SharePoint, Google Drive, BigQuery 등)의 비정형/정형 데이터를 제미나이 엔터프라이즈 앱(Gemini Enterprise app)에 안전하게 연결할 수 있도록 지원하는 데이터 커넥터 스캐폴더 솔루션의 비즈니스 요구 사항 명세서(Business Requirements Document)다.

---

## 1. 추진 배경 및 비즈니스 동기

1. **기업 기간계 데이터 파편화와 연동 난관**:
   - 엔터프라이즈 생성형 AI 도입 후 임직원이 필요로 하는 핵심 지식은 슬랙(Slack), 지라(Jira), 컨플루언스(Confluence), 세일즈포스(Salesforce), 셰어포인트(SharePoint) 등 서로 다른 SaaS 및 기간계 시스템에 분산되어 있다.
   - 각 데이터 소스마다 인증 프로토콜(OAuth 2.0, API Token, Basic Auth), 페이징 규격, 증분 수집 방식이 상이하여 커넥터 구축에 수 주일의 엔지니어링 리소스가 소모된다.

2. **접근 제어 목록(ACL) 동기화 및 데이터 보안 사각지대**:
   - 원본 시스템의 사용자별 열람 권한(Document-level ACLs)이 무시된 채 검색 엔진에 색인될 경우, 급여 명세서나 기밀 프로젝트 문서가 권한 없는 일반 임직원에게 검색 및 답변으로 노출되는 심각한 컴플라이언스 위반이 발생한다.
   - 데이터 수집 시 사내 사용자 계정 매핑(Identity Mapping)과 문서별 ACL 정보를 온전히 동기화하는 보안 설계가 필수적이다.

3. **Gemini Enterprise app 대화형 커넥터 프로비저닝 (No-code / ChatOps)**:
   - 복잡한 GCP 콘솔이나 수십 장에 달하는 공식 문서를 뒤적이지 않고도, 전사 임직원 및 데이터 관리자가 Gemini Enterprise app 채팅창에서 대화하며 원하는 데이터 소스 칩을 선택하고 연동 매니페스트를 자율 도출할 수 있어야 한다.

---

## 2. 핵심 비즈니스 요구 사항 목록 (Business Requirements)

| 요구 사항 ID | 구분 | 핵심 비즈니스 목표 및 요구 명세 |
| :--- | :--- | :--- |
| **BR-01** | 엔터프라이즈 커넥터 카탈로그 및 자유 프롬프팅 | 사내 주요 기간계 시스템(그룹웨어, Confluence, Jira, Salesforce, ServiceNow, SharePoint, Google Drive, BigQuery, SAP ERP, Workday, Slack, PostgreSQL/MySQL, 인트라넷 웹, GitHub, Cloud Storage 등) 커넥터 프리셋을 제공하고, 사용자가 자유 프롬프트(`--prompt`)로 원하는 데이터 소스 연동 매니페스트를 자율 도출할 수 있어야 한다. |
| **BR-02** | 보안 볼트 기반 자격 증명 연동 | OAuth 2.0 클라이언트 시크릿, API 토큰 등 민감 자격 증명을 시크릿 매니저(Secret Manager)에 안전하게 암호화 보관하고 대행 서비스 계정에 최소 권한을 부여해야 한다. |
| **BR-03** | 문서 레벨 ACL 및 사용자 매핑 가이드 | 원본 기간계 시스템의 권한 체계가 손상되지 않도록 문서 레벨 접근 제어(Document-level ACL) 및 Cloud Identity 계정 매핑 정책을 자동 판정해야 한다. |
| **BR-04** | 동기화 주기 및 증분 색인 스케줄링 | 데이터 변경 빈도에 따라 1시간 단위 정기 동기화 또는 일일 배치 동기화 스케줄을 포함한 Discovery Engine Data Store 구성 매니페스트를 합성해야 한다. |
| **BR-05** | Gemini Enterprise app 사내 앱 직결 바인딩 | 생성된 데이터 저장소(Data Store)를 현재 사내 Gemini Enterprise app의 검색 엔진(Engine)에 원클릭 바인딩하는 자동화 명세를 제공해야 한다. |
| **BR-06** | 엔터프라이즈 보안 및 4대 필수 라벨 강제 | 모든 커넥터 리소스에 4대 표준 라벨(`managed-by`, `scenario`, `env`, `created-by`)을 주입하고 VPC-SC 보안 경계 차단 여부를 사전 진단해야 한다. |
| **BR-07** | 선언적 커넥터 레시피 아키텍처 및 케밥 케이스 표준 | 파이썬 코드 수정 없이 신규 데이터 소스를 확장할 수 있도록 선언적 카탈로그 파일(`catalog.yaml`) 분리 구조를 지원하고, 모든 커넥터 슬러그는 `[domain]-[system]-[action]` 형태의 3단계 소문자 케밥 케이스(kebab-case) 표준을 준수하여야 한다. |
| **BR-08** | 에어갭 및 오프라인 환경 회복 탄력성 보장 | 사내 보안 정책상 인터넷 연결이 차단된 에어갭(Air-gapped) 환경이나 외부 카탈로그 엔드포인트 장애 상황에서도 타임아웃(2.0초 이내)을 적용하고 내장된 시드 카탈로그로 원활히 폴백하여 무중단 동작을 보장하여야 한다. |
| **BR-09** | 다중 데이터 소스 인스턴스 스캐폴딩 지원 및 식별자 충돌 방어 | 사내 환경에서는 동일한 커넥터 종류(Jira, Confluence 등)라도 부서별/목적별로 서로 다른 데이터 소스(예: 개발팀 Jira vs 인사팀 Jira)를 연동해야 하므로, 스캐폴더에서 동일 커넥터 유형의 다중 인스턴스 중복 생성을 허용해야 한다. 단, 동일한 대상 데이터 저장소 ID(Data Store ID)에 대한 우발적 덮어쓰기 충돌은 고유 식별자 접미사를 통해 방어하여야 한다. |

---

## 3. 기대 효과 및 비즈니스 KPI

1. **기간계 데이터 연동 소요 시간 90% 단축**: 수 주일이 소요되던 SaaS 데이터 커넥터 연동 설계를 10분 이내 표준 매니페스트 생성으로 단축한다.
2. **사내 데이터 보안 사고 0건 달성**: 엄격한 문서 레벨 ACL 동기화 지침을 적용하여 권한 외 기밀 데이터 노출을 원천 방지한다.
3. **비개발 부서의 자율 데이터 확장**: 현업 부서가 직접 보유한 지식 저장소를 Gemini Enterprise app 대화창을 통해 간편하게 연결하여 전사 집단 지성을 가속화한다.
