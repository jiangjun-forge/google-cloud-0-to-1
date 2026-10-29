<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 기술 상세 설계서 (TDD): 제미나이 엔터프라이즈(Gemini Enterprise) 크로스 조직 커스텀 에이전트 연동 및 조직 정책 진단기 (`gemini-enterprise-agent-resolver`)

## 1. 시스템 아키텍처 및 런타임 상호작용 시퀀스

본 도구의 런타임 제어 및 데이터 상호작용 흐름은 아래 시퀀스 다이어그램과 같다. 인프라 관리자 또는 플랫폼 엔지니어가 진단 명령을 실행하면 양측 프로젝트의 조직 정책, IAM 역할, Agent Engine 식별자 및 VPC-SC 경계를 실시간 교차 검증하여 결함 원인을 규명하고 복구 처방을 도출한다.

```mermaid
sequenceDiagram
    actor Admin as 인프라 관리자 / 플랫폼 엔지니어
    participant CLI as 진단 CLI (diagnose.py)
    participant CRM as Cloud Resource Manager (조직 정책)
    participant IAM as Cloud IAM API (서비스 에이전트 권한)
    participant AgentEng as Agent Engine (런타임 슬롯)
    participant VPCSC as VPC Service Controls (보안 경계)

    Admin->>CLI: python diagnose.py --ge-project PROJ_A --agent-project PROJ_B
    
    rect rgb(240, 245, 255)
    note right of CLI: 1단계: 프로젝트 식별 및 크로스 조직 도메인 정책 감사
    CLI->>CRM: getAncestry(PROJ_A) & getAncestry(PROJ_B)
    CRM-->>CLI: 양측 부모 조직(Org ID) 반환
    opt 서로 다른 조직(Cross-Org)인 경우
        CLI->>CRM: getOrgPolicy(constraints/iam.allowedPolicyMemberDomains)
        CRM-->>CLI: 도메인 제한 공유 정책 상태 반환
    end
    end

    rect rgb(245, 240, 255)
    note right of CLI: 2단계: 서비스 에이전트 권한 및 런타임 식별자 감사
    CLI->>IAM: getIamPolicy(PROJ_B)
    IAM-->>CLI: GE 서비스 에이전트(roles/aiplatform.user) 바인딩 상태 반환
    CLI->>AgentEng: describeReasoningEngine(RESOURCE_NAME)
    AgentEng-->>CLI: Agent Engine 런타임 상태 및 식별자 정합성 반환
    end

    rect rgb(255, 245, 240)
    note right of CLI: 3단계: VPC-SC 서비스 경계 격리 상태 감사
    CLI->>VPCSC: getAccessPerimeter(PROJ_B)
    VPCSC-->>CLI: 서비스 경계 및 인그레스 규칙 반환
    end

    CLI->>CLI: 4대 핵심 기둥 진단 판정(PASS/WARN/CRITICAL) 및 원클릭 복구 명령 합성
    CLI-->>Admin: 종합 진단 매트릭스 표 및 report.md 생성
```

---

## 2. 요구 사항 추적성 매핑 (Traceability Matrix)

| 비즈니스 요구 사항 (BRD) | 기능적 기술 요구 사항 (FR) | 비기능적 기술 요구 사항 (NFR) | 구현 파일 및 모듈 |
| :--- | :--- | :--- | :--- |
| **BR-01** (계층형 환경 설정 및 리소스 자동 탐지) | **FR-01** (계층형 환경 설정 및 리소스 자동 탐지) | **NFR-02** (비대화형 환경 호환성) | `diagnose.py` |
| **BR-02** (크로스 프로젝트 4대 핵심 정책 정밀 진단) | **FR-02** (핵심 운영 지표 및 설정 상태 정밀 진단) | **NFR-01** (최소 IAM 권한 준수) | `diagnose.py` |
| **BR-03** (가상 실행 스모크 테스트 지원) | **FR-03** (가상 실행 스모크 테스트 모드) | **NFR-03** (민감 정보 비식별화) | `diagnose.py` |
| **BR-04** (원클릭 복구 처방 및 리소스 정리 가이드) | **FR-04** (직관적 콘솔 조치 가이드 및 리소스 정리) | **NFR-04** (표준 리소스 라벨링) | `diagnose.py`, `report.md` |

---

## 3. 기능적 기술 요구 사항 (Functional Requirements)

| 요구 사항 ID | 연관 BR | 기술 요구 사항 명칭 | 구현 상세 및 검증 기준 |
| :--- | :--- | :--- | :--- |
| **FR-01** | **BR-01** | **계층형 환경 설정 및 리소스 자동 탐지** | CLI 인자(`--agent-project, --config, --dry-run, --engine-id, --ge-project, --json`) > `.env` > `gcloud config` 활성 설정 > 대화형 번호 선택기 순으로 프로젝트 및 대상 리소스를 자동 확정한다. |
| **FR-02** | **BR-02** | **핵심 운영 지표 및 설정 상태 정밀 진단** | 대상 GCP 리소스의 메타데이터, 정책, 할당량 또는 로그 지표를 수집하여 정상(`PASS`), 주의(`WARN`), 위험(`FAIL`) 등급을 산출한다. |
| **FR-03** | **BR-03** | **가상 실행(`--dry-run`) 스모크 테스트 모드** | `--dry-run` 플래그 입력 시 외부 GCP API 호출을 우회하고 내장된 표준 시뮬레이션 데이터를 기반으로 전체 진단 리포트를 1초 내에 출력한다. |
| **FR-04** | **BR-04** | **직관적 콘솔 조치 가이드 및 리소스 정리 안내** | 진단 결과 하단에 Google Cloud 콘솔 조치 URL(Bare URL 표준)과 CLI 복구 명령어를 출력하여 즉각적인 후속 조치를 지원한다. |

---

## 4. 비기능적 기술 요구 사항 (Non-Functional Requirements)

| 요구 사항 ID | 요구 사항 명칭 | 상세 기준 |
| :--- | :--- | :--- |
| **NFR-01** | **최소 IAM 권한 준수** | 진단에 필요한 최소 권한(`roles/aiplatform.user, roles/aiplatform.viewer, roles/iam.securityReviewer, roles/orgpolicy.policyViewer`)만을 요구하며, 불필요한 쓰기 권한을 강제하지 않는다. |
| **NFR-02** | **비대화형 환경 호환성 (CI/CD Ready)** | `sys.stdin.isatty()` 검증을 통해 백그라운드 태스크나 CI/CD 파이프라인 실행 시 입력 대기(Hang) 없이 안전하게 기본 후보를 채택한다. |
| **NFR-03** | **민감 정보 비식별화 및 보안 규약** | 소스 코드 및 문서 내에 실제 프로젝트 ID나 개인 식별 정보(PII)를 하드코딩하지 않으며, 모든 외부 참조 링크는 Bare URL 괄호 병기 원칙을 준수한다. |
| **NFR-04** | **표준 리소스 라벨링 규약 준수** | 리소스 생성 가이드 및 CLI 명령어에 4대 필수 표준 라벨(`managed-by=google-cloud-0-to-1`, `scenario=gemini-enterprise-agent-resolver`, `env=sample`, `created-by=customer-engineer`)을 누락 없이 포함한다. |
