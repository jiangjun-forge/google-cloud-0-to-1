<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# Gemini Enterprise 커스텀 에이전트 팩토리 및 Gemini Enterprise app 연동기 비즈니스 요구 사항 명세서 (BRD)

본 문서는 사내 클라우드 아키텍트 및 백엔드 개발자가 사내 데이터베이스, 레거시 시스템 및 외부 API를 결합한 고성능 커스텀(High-code) 에이전트를 신속하게 구축하고, 에이전트 런타임(Agent Runtime)에 배포한 후 제미나이 엔터프라이즈 앱(Gemini Enterprise app)에 외부 에이전트로 원클릭 연동할 수 있도록 지원하는 엔지니어링 도구의 비즈니스 요구 사항 명세서(Business Requirements Document)다.

---

## 1. 추진 배경 및 비즈니스 동기

1. **단순 프롬프트 에이전트의 기술적 한계**:
   - 노코드(No-code) 에이전트는 일반 질의응답이나 검색 그라운딩에 적합하지만, 사내 빅쿼리(BigQuery), 클라우드 SQL(Cloud SQL) 데이터베이스 질의, 사내 기간계 API 호출, MCP(Model Context Protocol) 기반 시스템 연동 등 복잡한 비즈니스 로직을 수행하기에는 기술적 한계가 존재한다.
   - 전문 개발팀이 파이썬(Python) SDK 기반으로 상태 머신, 다단계 추론(Reasoning), 커스텀 툴체인을 직접 코딩할 수 있는 하이코드(High-code) 개발 표준이 필수적이다.

2. **반복적인 인프라 보일러플레이트 작성 부담**:
   - 커스텀 에이전트를 프로덕션에 배포하기 위해서는 Google ADK 연동 코드, 도구 함수 명세, 에이전트 엔진(Agent Engine) 배포 스크립트 등 방대한 인프라 코드를 매번 수작업으로 작성해야 한다.
   - 단 한 줄의 자연어 아키텍처 요구사항으로부터 표준 파이썬 에이전트 코드와 배포 매니페스트를 자동 생성해 주는 개발자 생산성 도구가 요구된다.

3. **Gemini Enterprise app 사내 갤러리 연동의 복잡성 해결**:
   - 에이전트 엔진에 배포된 커스텀 에이전트를 전사 임직원이 사용하는 Gemini Enterprise app 웹 인터페이스에 노출시키려면, 프로젝트 간 IAM 권한 부여, 엔드포인트 바인딩, 조직 정책(Org Policy) 예외 처리가 수반되어 설정 오류가 빈번히 발생한다.
   - 런타임 배포부터 Gemini Enterprise app 사내 갤러리 등록(ADK Agent Binding)까지 전 과정을 자동화하고 연결 상태를 즉시 진단할 수 있어야 한다.

4. **GitHub 저장소 URL 기반 무인 자동 배포 (저장소 연동 자동 배포)**:
   - 개발팀이 CLI나 GCP 콘솔에 직접 접속하지 않고도, Gemini Enterprise app 대화창에서 개발 완료된 GitHub 저장소 주소(`https://github.com/...`)를 입력하는 것만으로 빌드, 배포, 갤러리 등록까지 완결되는 무인 배포 체계를 지원해야 한다.

5. **원클릭 온보딩 및 단일 에이전트 개별 배포**:
   - 최초 1회 개발자가 `diagnose.py`로 커스텀 팩토리 에이전트를 배포하면, 이후 사내 에이전트 확장은 GE App 웹 채팅창에서 4대 팩토리 카탈로그 또는 GitHub 저장소 URL 입력만으로 한 번에 하나씩 독립 배포할 수 있어야 한다.

---

## 2. 핵심 비즈니스 요구 사항 목록 (Business Requirements)

| 요구 사항 ID | 구분 | 핵심 비즈니스 목표 및 요구 명세 |
| :--- | :--- | :--- |
| **BR-01** | 하이코드 에이전트 자동 구축 및 코드 생성 | 개발자의 요구사항(도메인, 데이터 소스, 목적)을 입력받아 즉시 실행 및 커스터마이징 가능한 표준 파이썬 에이전트 코드(`agent.py`)를 자동 생성해야 한다. |
| **BR-02** | 엔터프라이즈 데이터 및 도구 템플릿 | 빅쿼리 SQL 쿼리, 사내 REST API 호출, MCP 도구 연동을 위한 함수(`tools.py`)를 표준 규격으로 자동 도출해야 한다. |
| **BR-03** | 에이전트 엔진 런타임 배포 자동화 | 생성된 에이전트를 에이전트 엔진(Agent Engine)에 배포하기 위한 `deploy.py`와 의존성 명세를 완비해야 한다. |
| **BR-04** | GitHub 저장소 직결 무인 배포 (Repo-driven) | 개발자가 대화창에 GitHub 저장소 URL을 제공하면 저장소 구조 검증, 런타임 빌드, 사내 갤러리 자동 등록을 원클릭으로 완결해야 한다. |
| **BR-05** | Gemini Enterprise app 사내 갤러리 원클릭 연동 | 배포된 커스텀 에이전트를 사내 Gemini Enterprise app 포털의 카탈로그에 등록하고 연결성을 사전 검증해야 한다. |
| **BR-06** | 실행 권한 및 환경 분리 | 서비스 계정 최소 권한 원칙(`roles/aiplatform.user`, `roles/discoveryengine.editor`)을 설계에 반영해야 한다. |
| **BR-07** | 표준 리소스 라벨링 적용 의무화 | 자원 추적성을 위해 생성되는 에이전트 서비스 및 관련 리소스에 4대 표준 라벨(`managed-by`, `scenario`, `env`, `created-by`)을 필수로 주입하여야 한다. |
| **BR-08** | 2단계 무인 고객 온보딩 여정 | 개발팀의 로컬 CLI 개입을 최초 1회(`python diagnose.py`)로 종결하고, 이후 에이전트 확장 및 배포는 전사 Gemini Enterprise app 웹 채팅창에서 완결되어야 한다. |
| **BR-09** | 4대 패밀리 팩토리 에이전트 카탈로그 및 0번 레포 직결 배포 | 4대 팩토리 에이전트 패밀리(1: 어드민 모듈, 2: 노코드 에이전트 팩토리, 3: 데이터 커넥터 스캐폴더, 4: 사내 스킬 팩토리)와 0번(임의 GitHub 저장소 URL 직결 배포) 프리셋을 제공하고, 대화형 카탈로그 조회 도구를 제공해야 한다. |
| **BR-10** | 선언적 커스텀 레시피 아키텍처 및 케밥 케이스 표준 | 파이썬 코드 수정 없이 커스텀 에이전트를 확장할 수 있도록 선언적 카탈로그 파일(`catalog.yaml`) 분리 구조를 지원하고, 모든 에이전트 슬러그는 소문자 케밥 케이스(kebab-case) 표준을 준수하여야 한다. |
| **BR-11** | 폐쇄망 및 오프라인 환경 회복 탄력성 확보 | 외부 인터넷 연결이 제한된 환경에서도 타임아웃(2.0초 이내)을 적용하고 내장된 시드 카탈로그로 폴백하여 안정적인 동작을 유지하여야 한다. |
| **BR-12** | 사전 중복 검증 인터셉터 및 멱등성 보장 | 신규 커스텀 에이전트 등록 요청 시 사내 포털에 이미 등록되어 활성화된 기존 에이전트와의 충돌을 사전 검증하여 중복 프로비저닝을 방지하고 기존 에이전트 안내를 반환하여야 한다. |

---

## 3. 기대 효과 및 비즈니스 KPI

1. **커스텀 에이전트 개발 및 배포 주기 80% 단축**:
   - 인프라 및 SDK 연동 보일러플레이트 작성 소요 시간(평균 2~3일)을 10분 이내 코드 생성으로 단축한다.
2. **사내 레거시 및 데이터베이스 AI 연결 가속**:
   - 표준화된 도구 템플릿을 통해 빅쿼리 및 사내 기간계 API 등 핵심 기업 자산을 에이전트 도구로 즉시 결합할 수 있다.
3. **개발팀과 현업 사용자의 단일 포털 통합**:
   - 전문 개발팀이 만든 고도화된 백엔드 에이전트를 비개발자 임직원이 매일 쓰는 Gemini Enterprise app 웹 화면에서 바로 호출하여 전사 업무 혁신을 달성한다.
