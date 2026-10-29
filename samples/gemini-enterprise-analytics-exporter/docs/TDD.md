<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 기술 상세 설계서 (TDD): 제미나이 엔터프라이즈(Gemini Enterprise) 사용자 채택률 분석 및 유휴 라이선스 회수 진단기 (`gemini-enterprise-analytics-exporter`)

## 1. 시스템 아키텍처 및 런타임 상호작용 시퀀스

본 도구의 런타임 제어 및 데이터 상호작용 흐름은 아래 시퀀스 다이어그램과 같다. FinOps 담당자 또는 IT 어드민이 진단 명령을 실행하면 Cloud Logging 및 BigQuery 감사 로그를 스캔하여 사용자별 프롬프트/세션 활동성을 측정하고, 30일 이상 미사용자를 식별하여 유휴 라이선스 회수 처방과 DDL 스키마를 도출한다.

```mermaid
sequenceDiagram
    actor Admin as 사내 IT 어드민 / FinOps 담당자
    participant CLI as 진단 CLI (diagnose.py)
    participant Logs as Cloud Logging / Audit Logs
    participant Engine as 지표 분류 및 분석 엔진
    participant BQ as BigQuery (gemini_analytics)
    participant IDP as Cloud Identity / Workspace API

    Admin->>CLI: python diagnose.py --project PROJ_ID --threshold-days 30
    
    rect rgb(240, 245, 255)
    note right of CLI: 1단계: Gemini Enterprise 활동 로그 수집
    CLI->>Logs: searchLogEntries(protoPayload.serviceName="discoveryengine.googleapis.com")
    Logs-->>CLI: 사용자별 프롬프트 호출 및 타임스탬프 반환
    end

    rect rgb(245, 240, 255)
    note right of CLI: 2단계: 사용자별 활동성 분류 및 유휴 라이선스 탐지
    CLI->>Engine: analyze_user_activity(logs, threshold=30)
    Engine->>Engine: 활동 등급 분류 (High, Moderate, Low, Dormant)
    Engine->>Engine: 30일 이상 미사용(0 프롬프트) 계정 선별 및 비용 누수 산출
    Engine-->>CLI: 부서별 채택률 통계 및 회수 대상 명단 반환
    end

    rect rgb(255, 245, 240)
    note right of CLI: 3단계: BigQuery 파티션 테이블 DDL 합성 및 조치 가이드 생성
    CLI->>BQ: generate_ddl(partition_by=DATE, cluster_by=department)
    BQ-->>CLI: 표준 BigQuery DDL 및 bq mk 스크립트 도출
    CLI->>IDP: generate_license_reclaim_commands(dormant_users)
    IDP-->>CLI: gcloud/Admin SDK 라이선스 회수 명령어 도출
    end

    CLI-->>Admin: 전사 FinOps 종합 리포트 및 report.md 생성
```

---

## 2. 요구 사항 추적성 매핑 (Traceability Matrix)

| 비즈니스 요구 사항 (BRD) | 기능적 기술 요구 사항 (FR) | 비기능적 기술 요구 사항 (NFR) | 구현 파일 및 모듈 |
| :--- | :--- | :--- | :--- |
| **BR-01** (계층형 환경 설정 및 리소스 자동 탐지) | **FR-01** (계층형 환경 설정 및 리소스 자동 탐지) | **NFR-02** (비대화형 환경 호환성) | `diagnose.py` |
| **BR-02** (사용자별 활동 지표 및 유휴 라이선스 정밀 진단) | **FR-02** (핵심 운영 지표 및 설정 상태 정밀 진단) | **NFR-01** (최소 IAM 권한 준수) | `diagnose.py` |
| **BR-03** (가상 실행 스모크 테스트 지원) | **FR-03** (가상 실행 스모크 테스트 모드) | **NFR-03** (민감 정보 비식별화) | `diagnose.py` |
| **BR-04** (BigQuery DDL 및 라이선스 회수 조치 가이드) | **FR-04** (직관적 콘솔 조치 가이드 및 리소스 정리) | **NFR-04** (표준 리소스 라벨링) | `diagnose.py`, `report.md` |

---

## 3. 기능적 기술 요구 사항 (Functional Requirements)

| 요구 사항 ID | 연관 BR | 기술 요구 사항 명칭 | 구현 상세 및 검증 기준 |
| :--- | :--- | :--- | :--- |
| **FR-01** | **BR-01** | **계층형 환경 설정 및 리소스 자동 탐지** | CLI 인자(`--config, --dataset, --dry-run, --json, --project, --table, --threshold-days`) > `.env` > `gcloud config` 활성 설정 > 대화형 번호 선택기 순으로 프로젝트 및 대상 리소스를 자동 확정한다. |
| **FR-02** | **BR-02** | **핵심 운영 지표 및 설정 상태 정밀 진단** | 대상 GCP 리소스의 메타데이터, 정책, 할당량 또는 로그 지표를 수집하여 정상(`PASS`), 주의(`WARN`), 위험(`FAIL`) 등급을 산출한다. |
| **FR-03** | **BR-03** | **가상 실행(`--dry-run`) 스모크 테스트 모드** | `--dry-run` 플래그 입력 시 외부 GCP API 호출을 우회하고 내장된 표준 시뮬레이션 데이터를 기반으로 전체 진단 리포트를 1초 내에 출력한다. |
| **FR-04** | **BR-04** | **직관적 콘솔 조치 가이드 및 리소스 정리 안내** | 진단 결과 하단에 Google Cloud 콘솔 조치 URL(Bare URL 표준)과 CLI 복구 명령어를 출력하여 즉각적인 후속 조치를 지원한다. |

---

## 4. 비기능적 기술 요구 사항 (Non-Functional Requirements)

| 요구 사항 ID | 요구 사항 명칭 | 상세 기준 |
| :--- | :--- | :--- |
| **NFR-01** | **최소 IAM 권한 준수** | 진단에 필요한 최소 권한(`roles/bigquery.dataEditor, roles/bigquery.jobUser`)만을 요구하며, 불필요한 쓰기 권한을 강제하지 않는다. |
| **NFR-02** | **비대화형 환경 호환성 (CI/CD Ready)** | `sys.stdin.isatty()` 검증을 통해 백그라운드 태스크나 CI/CD 파이프라인 실행 시 입력 대기(Hang) 없이 안전하게 기본 후보를 채택한다. |
| **NFR-03** | **민감 정보 비식별화 및 보안 규약** | 소스 코드 및 문서 내에 실제 프로젝트 ID나 개인 식별 정보(PII)를 하드코딩하지 않으며, 모든 외부 참조 링크는 Bare URL 괄호 병기 원칙을 준수한다. |
| **NFR-04** | **표준 리소스 라벨링 규약 준수** | 리소스 생성 가이드 및 CLI 명령어에 4대 필수 표준 라벨(`managed-by=google-cloud-0-to-1`, `scenario=gemini-enterprise-analytics-exporter`, `env=sample`, `created-by=customer-engineer`)을 누락 없이 포함한다. |
