<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 기술 상세 설계서 (TDD): Agent Platform Search 데이터 저장소 색인 및 그라운딩 정합성 진단기 (vertex-search-grounding-validator)

## 1. 시스템 아키텍처 및 동작 원리
본 도구는 순수 파이썬 단일 실행 기반(`diagnose.py`)의 미니셋 아키텍처로 구성된다. 상위 폴더 의존성 없이 `.env.example` 및 `gcloud config` 활성 프로젝트 자동 탐지(Cascade Fallback)를 통해 자체 완결적으로 동작하며, 진단 완료 시 마크다운 리포트(`report.md`)를 자동 덮어쓴다.

---

## 2. 시스템 아키텍처 및 런타임 상호작용 시퀀스

본 도구의 런타임 제어 및 데이터 상호작용 흐름은 아래 시퀀스 다이어그램과 같다. 검색/AI 엔지니어가 CLI를 실행하면 Cloud Storage 원본 문서 수와 Agent Platform Search(Discovery Engine) 데이터 저장소의 색인 완료 문서 수를 비교하여 색인 누락율을 산출하고, 파서/청킹 구성 점검 및 프로브 질의를 통한 그라운딩 신뢰도를 실측하여 리포트를 생성한다.

```mermaid
sequenceDiagram
    actor Engineer as AI / RAG 엔지니어
    participant CLI as CLI 컨트롤러 (diagnose.py)
    participant StorageAPI as Cloud Storage API (원본 문서)
    participant EngineAPI as Discovery Engine API (데이터 저장소)
    participant IAMAPI as Cloud Resource Manager API (SA 권한)
    participant GeminiAPI as Vertex AI Search API (프로브 질의)
    participant FileSys as 로컬 파일 시스템 (report.md)

    rect rgb(240, 245, 255)
    note right of CLI: 1단계: 원본 스토리지 대비 데이터 저장소 색인 상태 실사
    Engineer->>CLI: python diagnose.py -p $PROJECT_ID -d $DATASTORE_ID -b $BUCKET
    CLI->>StorageAPI: gcloud storage objects list gs://$BUCKET
    StorageAPI-->>CLI: 원본 객체 수 및 파일 포맷(PDF, HTML) 반환
    CLI->>EngineAPI: discoveryengine dataStores get / documents list
    EngineAPI-->>CLI: 색인 완료 문서 수, 적용 파서, 청킹 단위 반환
    CLI->>IAMAPI: gcloud projects get-iam-policy $PROJECT_ID
    IAMAPI-->>CLI: Discovery Engine SA의 roles/storage.objectViewer 보유 여부 반환
    end

    rect rgb(245, 240, 255)
    note right of CLI: 2단계: 그라운딩 검색 품질 측정 및 처방 리포트 생성
    CLI->>GeminiAPI: search probe query ("2026 클라우드 보안 정책 가이드라인")
    GeminiAPI-->>CLI: 검색 청크 목록 및 그라운딩 신뢰도 점수 반환
    CLI->>CLI: 색인 누락율, 파서 적합성, 그라운딩 품질 종합 판정 (PASS/WARN/FAIL)
    CLI->>FileSys: save_markdown_report(report.md)
    FileSys-->>CLI: 덮어쓰기 완료
    CLI-->>Engineer: 터미널 종합 리포트 및 Layout Parser 전환/재색인 명령어 브리핑
    end
```

---

## 3. 요구 사항 추적성 매핑 (Traceability Matrix)

| 비즈니스 요구 사항 (BRD) | 기능적 기술 요구 사항 (FR) | 비기능적 기술 요구 사항 (NFR) | 구현 파일 및 모듈 |
| :--- | :--- | :--- | :--- |
| **BR-01** (현장 장애 및 리스크 사전 탐지) | **FR-01** (계층형 환경 설정 및 리소스 자동 탐지) | **NFR-01** (최소 IAM 권한 준수) | `diagnose.py` (`parse_args`, `detect_project_id`) |
| **BR-02** (표준화된 자동 진단 체계) | **FR-02** (핵심 지표 및 설정 상태 정밀 진단) | **NFR-02** (비대화형 호환성) | `diagnose.py` (`check_datastore_health`, `validate_grounding_query`) |
| **BR-03** (가상 실행 기반 무중단 사전 검증) | **FR-03** (가상 실행 스모크 테스트 모드) | **NFR-02** (비대화형 환경 호환성) | `diagnose.py` (`get_mock_data`) |
| **BR-04** (실무자 조치 가이드 및 리소스 정리) | **FR-04** (직관적 콘솔 조치 가이드) | **NFR-03** (민감 정보 비식별화) | `diagnose.py` (`print_report`, `build_markdown_report`) |
| **BR-02** (자동 진단 및 리포트 영구 보존) | **FR-05** (마크다운 리포트 자동 생성/덮어쓰기) | **NFR-04** (리포트 절대 경로 저장) | `diagnose.py` (`save_markdown_report`) |
| **BR-05** (사내 거버넌스 4대 필수 라벨링) | **FR-06** (사내 거버넌스 4대 필수 라벨링 적용) | **NFR-03** (보안 및 거버넌스 규약) | `README.md`, `diagnose.py` |

---

## 4. 기능적 기술 요구 사항 (Functional Requirements)

| 요구 사항 ID | 연관 BR | 기술 요구 사항 명칭 | 구현 상세 및 검증 기준 |
| :--- | :--- | :--- | :--- |
| **FR-01** | **BR-01** | **계층형 환경 설정 및 리소스 자동 탐지** | CLI 인자(`--bucket, --config, --datastore, --dry-run, --location, --project, --query`) > `.env` > `gcloud config` 활성 설정 > 대화형 번호 선택기 순으로 프로젝트 및 대상 리소스를 자동 확정한다. |
| **FR-02** | **BR-02** | **핵심 운영 지표 및 설정 상태 정밀 진단** | 대상 GCP 리소스의 메타데이터, 정책, 할당량 또는 로그 지표를 수집하여 정상(`PASS`), 주의(`WARN`), 위험(`FAIL`) 등급을 산출한다. |
| **FR-03** | **BR-03** | **가상 실행(`--dry-run`) 스모크 테스트 모드** | `--dry-run` 플래그 입력 시 외부 GCP API 호출을 우회하고 내장된 표준 시뮬레이션 데이터를 기반으로 전체 진단 리포트를 1초 내에 출력한다. |
| **FR-04** | **BR-04** | **직관적 콘솔 조치 가이드 및 리소스 정리 안내** | 진단 결과 하단에 Google Cloud 콘솔 조치 URL(Bare URL 표준)과 CLI 복구 명령어를 출력하여 즉각적인 후속 조치를 지원한다. |
| **FR-05** | **BR-02** | **마크다운 진단 리포트 (report.md) 자동 생성 및 덮어쓰기** | 진단 실행 시 터미널 화면 출력과 동일한 색인율, 파서 구성, 그라운딩 신뢰도 및 RAG 개선 처방을 담은 `report.md` 파일을 자동 기록/갱신하여 사내 문서 공유 및 복습을 지원한다. |
| **FR-06** | **BR-05** | **사내 거버넌스 4대 필수 라벨링 적용** | Agent Platform Search 데이터 저장소 연계 인프라 프로비저닝 시 `managed-by=google-cloud-0-to-1`, `scenario=vertex-search-grounding-validator`, `env=sample`, `created-by=customer-engineer` 라벨을 필수로 주입한다. |

---

## 5. 비기능적 기술 요구 사항 (Non-Functional Requirements)

| 요구 사항 ID | 요구 사항 명칭 | 상세 기준 |
| :--- | :--- | :--- |
| **NFR-01** | **최소 IAM 권한 준수** | 진단에 필요한 최소 권한(`roles/discoveryengine.viewer, roles/storage.objectViewer`)만을 요구하며, 불필요한 쓰기 권한을 강제하지 않는다. |
| **NFR-02** | **비대화형 환경 호환성 (CI/CD Ready)** | `sys.stdin.isatty()` 검증을 통해 백그라운드 태스크나 CI/CD 파이프라인 실행 시 입력 대기(Hang) 없이 안전하게 기본 후보를 채택한다. |
| **NFR-03** | **민감 정보 비식별화 및 보안 규약** | 소스 코드 및 문서 내에 실제 프로젝트 ID나 개인 식별 정보(PII)를 하드코딩하지 않으며, 모든 외부 참조 링크는 Bare URL 괄호 병기 원칙을 준수한다. |
| **NFR-04** | **리포트 절대 경로 저장 보장** | 로컬 진단 스크립트 실행 시 산출물 저장 경로는 스크립트 파일이 위치한 디렉터리의 절대 경로를 기준으로 저장하여 작업 디렉터리와 무관하게 안정적인 저장을 보장한다. |
