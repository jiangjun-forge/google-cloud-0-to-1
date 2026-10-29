<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 기술 상세 설계서 (TDD): 제미나이(Gemini) API 비용 급증 원인 진단 (`gemini-billing-spike`)

## 1. 시스템 아키텍처 및 런타임 상호작용 시퀀스

본 도구의 런타임 제어 및 데이터 상호작용 흐름은 아래 시퀀스 다이어그램과 같다. 엔지니어가 비용 급증 진단을 실행하면 Cloud Monitoring API에서 무료 제공되는 `serviceruntime` 메트릭을 시계열로 수집하고, 자격 증명(API 키, SA, OAuth) 및 메서드별 점유율을 집계하여 누수 주체를 역추적하고 차단 명령을 도출한다.

```mermaid
sequenceDiagram
    actor FinOps as FinOps 엔지니어 / 인프라 관리자
    participant CLI as 진단 CLI (diagnose.py)
    participant Monitoring as Cloud Monitoring API
    participant Engine as 시계열 점유율 집계 엔진
    participant Console as Cloud IAM & API Keys 콘솔

    FinOps->>CLI: python diagnose.py --days 7
    
    rect rgb(240, 245, 255)
    note right of CLI: 1단계: Cloud Monitoring 플랫폼 시계열 지표 수집
    CLI->>Monitoring: timeSeries.list(metric.type="serviceruntime.googleapis.com/api/request_count")
    Monitoring-->>CLI: 서비스/메서드/자격증명 라벨 시계열 반환
    end

    rect rgb(245, 240, 255)
    note right of CLI: 2단계: 인증 수단별 호출 점유율 및 급증 역추적
    CLI->>Engine: aggregate_by_credential(time_series)
    Engine->>Engine: apikey vs serviceAccount vs oauth2 비율 산출
    Engine->>Engine: 80% 이상 트래픽 집중된 유출 의심 자격 증명 식별
    Engine-->>CLI: 이상 징후 분석 결과 반환
    end

    rect rgb(255, 245, 240)
    note right of CLI: 3단계: 즉각 차단 명령어 및 예산 가드 합성
    CLI->>Console: build_remediation_commands(credential_id)
    Console-->>CLI: API 키 삭제/제한 gcloud 명령어 도출
    end

    CLI-->>FinOps: 자격 증명별 점유율 표 및 report.md 생성
```

---

## 2. 요구 사항 추적성 매핑 (Traceability Matrix)

| 비즈니스 요구 사항 (BRD) | 기능적 기술 요구 사항 (FR) | 비기능적 기술 요구 사항 (NFR) | 구현 파일 및 모듈 |
| :--- | :--- | :--- | :--- |
| **BR-01** (계층형 환경 설정 및 리소스 자동 탐지) | **FR-01** (계층형 환경 설정 및 리소스 자동 탐지) | **NFR-02** (비대화형 환경 호환성) | `diagnose.py` |
| **BR-02** (감사 로그 부재 시 무료 지표 기반 역추적) | **FR-02** (핵심 운영 지표 및 설정 상태 정밀 진단) | **NFR-01** (최소 IAM 권한 준수) | `diagnose.py` |
| **BR-03** (가상 실행 스모크 테스트 지원) | **FR-03** (가상 실행 스모크 테스트 모드) | **NFR-03** (민감 정보 비식별화) | `diagnose.py` |
| **BR-04** (자격 증명 차단 및 예산 알림 조치 가이드) | **FR-04** (직관적 콘솔 조치 가이드 및 리소스 정리) | **NFR-04** (표준 리소스 라벨링) | `diagnose.py`, `report.md` |

---

## 3. 기능적 기술 요구 사항 (Functional Requirements)

| 요구 사항 ID | 연관 BR | 기술 요구 사항 명칭 | 구현 상세 및 검증 기준 |
| :--- | :--- | :--- | :--- |
| **FR-01** | **BR-01** | **계층형 환경 설정 및 리소스 자동 탐지** | CLI 인자(`--config, --days, --dry-run, --project`) > `.env` > `gcloud config` 활성 설정 > 대화형 번호 선택기 순으로 프로젝트 및 대상 리소스를 자동 확정한다. |
| **FR-02** | **BR-02** | **핵심 운영 지표 및 설정 상태 정밀 진단** | 대상 GCP 리소스의 메타데이터, 정책, 할당량 또는 로그 지표를 수집하여 정상(`PASS`), 주의(`WARN`), 위험(`FAIL`) 등급을 산출한다. |
| **FR-03** | **BR-03** | **가상 실행(`--dry-run`) 스모크 테스트 모드** | `--dry-run` 플래그 입력 시 외부 GCP API 호출을 우회하고 내장된 표준 시뮬레이션 데이터를 기반으로 전체 진단 리포트를 1초 내에 출력한다. |
| **FR-04** | **BR-04** | **직관적 콘솔 조치 가이드 및 리소스 정리 안내** | 진단 결과 하단에 Google Cloud 콘솔 조치 URL(Bare URL 표준)과 CLI 복구 명령어를 출력하여 즉각적인 후속 조치를 지원한다. |

---

## 4. 비기능적 기술 요구 사항 (Non-Functional Requirements)

| 요구 사항 ID | 요구 사항 명칭 | 상세 기준 |
| :--- | :--- | :--- |
| **NFR-01** | **최소 IAM 권한 준수** | 진단에 필요한 최소 권한(`roles/monitoring.viewer, roles/viewer`)만을 요구하며, 불필요한 쓰기 권한을 강제하지 않는다. |
| **NFR-02** | **비대화형 환경 호환성 (CI/CD Ready)** | `sys.stdin.isatty()` 검증을 통해 백그라운드 태스크나 CI/CD 파이프라인 실행 시 입력 대기(Hang) 없이 안전하게 기본 후보를 채택한다. |
| **NFR-03** | **민감 정보 비식별화 및 보안 규약** | 소스 코드 및 문서 내에 실제 프로젝트 ID나 개인 식별 정보(PII)를 하드코딩하지 않으며, 모든 외부 참조 링크는 Bare URL 괄호 병기 원칙을 준수한다. |
| **NFR-04** | **표준 리소스 라벨링 규약 준수** | 리소스 생성 가이드 및 CLI 명령어에 4대 필수 표준 라벨(`managed-by=google-cloud-0-to-1`, `scenario=gemini-billing-spike`, `env=sample`, `created-by=customer-engineer`)을 누락 없이 포함한다. |
