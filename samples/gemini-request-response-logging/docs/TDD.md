<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 기술 상세 설계서 (TDD): 제미나이(Gemini) API 요청 및 응답 BigQuery 자동 로깅 (`gemini-request-response-logging`)

## 1. 시스템 아키텍처 및 런타임 상호작용 시퀀스

본 도구의 런타임 제어 및 데이터 상호작용 흐름은 아래 시퀀스 다이어그램과 같다. 별도의 무거운 리버스 프록시 서버 없이 Vertex AI의 내장 자동 로깅 파이프라인을 활성화하여 모든 Gemini 프롬프트 및 응답을 BigQuery 데이터셋에 실시간 스트리밍 적재하고 토큰 지출을 사용자별로 집계 분석한다.

```mermaid
sequenceDiagram
    actor Engineer as 인프라 / FinOps 엔지니어
    participant CLI as 진단 CLI (diagnose.py)
    participant VertexAI as Vertex AI (Gemini Foundation Model)
    participant BQ as BigQuery (요청 및 응답 로깅 데이터셋)
    participant Audit as 감사 및 리포트 엔진

    Engineer->>CLI: python diagnose.py --dry-run
    
    rect rgb(240, 245, 255)
    note right of CLI: 1단계: 사전 환경 진단 및 대상 데이터셋 검증
    CLI->>CLI: gcloud 설정 및 환경 변수 자동 탐색 (Cascade Fallback)
    CLI->>BQ: datasets.get(datasetId="gemini_request_response_logs")
    BQ-->>CLI: 200 OK (데이터셋 존재 및 4대 필수 라벨 검증)
    end

    rect rgb(245, 240, 255)
    note right of VertexAI: 2단계: Gemini API 호출 및 내장 자동 스트리밍 적재
    CLI->>VertexAI: generate_content(model="gemini-3.8-flash", prompt="...")
    VertexAI->>VertexAI: 프롬프트 추론 및 토큰 메타데이터 산출
    VertexAI-->>CLI: GenerationResponse(응답 텍스트 반환)
    VertexAI->>BQ: streaming_insert(prompt, response, user_identity, token_counts)
    BQ-->>VertexAI: 200 OK (파이프라인 비동기 적재 완료)
    end

    rect rgb(255, 245, 240)
    note right of Audit: 3단계: 사용자별 토큰 소비량 집계 및 진단 리포트 생성
    CLI->>BQ: jobs.query("SELECT user_id, SUM(total_tokens) ... GROUP BY user_id")
    BQ-->>CLI: QueryResults(사용자별/서비스 계정별 토큰 사용량)
    CLI->>Audit: 진단 결과 평가 및 report.md 자동 생성/갱신
    Audit-->>Engineer: 종합 진단 결과 및 콘솔 URL 출력
    end
```

---

## 2. 요구 사항 추적성 매핑 (Traceability Matrix)

| 비즈니스 요구 사항 (BRD) | 기능적 기술 요구 사항 (FR) | 비기능적 기술 요구 사항 (NFR) | 구현 파일 및 모듈 |
| :--- | :--- | :--- | :--- |
| **BR-01** (현장 장애 및 리스크 사전 탐지) | **FR-02** (핵심 운영 지표 및 설정 상태 정밀 진단) | **NFR-01** (최소 IAM 권한 준수) | `diagnose.py` (`check_bigquery_dataset`, `check_api_enabled`) |
| **BR-02** (표준화된 자동 진단 체계 구축) | **FR-01** (계층형 환경 설정 및 리소스 자동 탐지) | **NFR-02** (비대화형 환경 호환성) | `diagnose.py` (`get_default_project`, `parse_args`) |
| **BR-03** (가상 실행 기반 무중단 사전 검증) | **FR-03** (가상 실행 스모크 테스트 모드) | **NFR-03** (민감 정보 비식별화) | `diagnose.py` (`print_mock_results`, `--dry-run`) |
| **BR-04** (실무자 조치 가이드 및 리포트 안내) | **FR-04** (직관적 콘솔 조치 가이드 및 리포트 자동 생성) | **NFR-04** (리포트 절대 경로 저장 보장) | `diagnose.py` (`generate_markdown_report`), `report.md` |
| **BR-05** (사내 거버넌스 4대 필수 라벨링 준수) | **FR-05** (사내 거버넌스 4대 필수 라벨링 적용) | **NFR-03** (보안 규약 준수) | `diagnose.py` (`ensure_dataset_exists`), `README.md` |

---

## 3. 기능적 기술 요구 사항 (Functional Requirements)

| 요구 사항 ID | 연관 BR | 기술 요구 사항 명칭 | 구현 상세 및 검증 기준 |
| :--- | :--- | :--- | :--- |
| **FR-01** | **BR-02** | **계층형 환경 설정 및 리소스 자동 탐지** | CLI 인자(`--config, --dataset, --dry-run, --location, --model, --project, --skip-inference`) > `.env` > `gcloud config` 활성 설정 > 대화형 번호 선택기 순으로 프로젝트 및 대상 리소스를 자동 확정한다. |
| **FR-02** | **BR-01** | **핵심 운영 지표 및 설정 상태 정밀 진단** | 대상 GCP 리소스의 메타데이터, 정책, 할당량 또는 로그 지표를 수집하여 정상(`PASS`), 주의(`WARN`), 위험(`FAIL`) 등급을 산출한다. |
| **FR-03** | **BR-03** | **가상 실행(`--dry-run`) 스모크 테스트 모드** | `--dry-run` 플래그 입력 시 외부 GCP API 호출을 우회하고 내장된 표준 시뮬레이션 데이터를 기반으로 전체 진단 리포트를 1초 내에 출력한다. |
| **FR-04** | **BR-04** | **직관적 콘솔 조치 가이드 및 리포트 자동 생성** | 진단 결과 하단에 Google Cloud 콘솔 조치 URL(Bare URL 표준)과 CLI 복구 명령어를 출력하고 복습용 리포트(`report.md`)를 자동으로 생성 및 갱신한다. |
| **FR-05** | **BR-05** | **사내 거버넌스 4대 필수 라벨링 적용** | BigQuery 데이터세트 생성 시 `managed-by=google-cloud-0-to-1`, `scenario=gemini-request-response-logging`, `env=sample`, `created-by=customer-engineer` 라벨을 필수로 주입한다. |

---

## 4. 비기능적 기술 요구 사항 (Non-Functional Requirements)

| 요구 사항 ID | 요구 사항 명칭 | 상세 기준 |
| :--- | :--- | :--- |
| **NFR-01** | **최소 IAM 권한 준수** | 진단에 필요한 최소 권한(`roles/aiplatform.user, roles/bigquery.dataEditor`)만을 요구하며, 불필요한 쓰기 권한을 강제하지 않는다. |
| **NFR-02** | **비대화형 환경 호환성 (CI/CD Ready)** | `sys.stdin.isatty()` 검증을 통해 백그라운드 태스크나 CI/CD 파이프라인 실행 시 입력 대기(Hang) 없이 안전하게 기본 후보를 채택한다. |
| **NFR-03** | **민감 정보 비식별화 및 보안 규약** | 소스 코드 및 문서 내에 실제 프로젝트 ID나 개인 식별 정보(PII)를 하드코딩하지 않으며, 모든 외부 참조 링크는 Bare URL 괄호 병기 원칙을 준수한다. |
| **NFR-04** | **리포트 절대 경로 저장 보장** | `report.md` 저장 시 스크립트 실행 작업 디렉터리(`cwd`)와 무관하게 스크립트 파일이 위치한 디렉터리의 절대 경로를 기준으로 저장하여 파일 유실을 방지한다. |
