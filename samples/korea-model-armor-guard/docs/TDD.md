<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 기술 상세 설계서 (TDD): 서울 리전 Model Armor 기능 제약 및 한국형 가드레일 하이브리드 보완 진단기 (korea-model-armor-guard)

## 1. 시스템 아키텍처 및 런타임 상호작용 시퀀스

본 도구의 런타임 제어 및 데이터 상호작용 흐름은 아래 시퀀스 다이어그램과 같다. 대한민국 서울 리전(asia-northeast3) 환경에서 Model Armor 템플릿의 리전 미지원 필터로 인한 보안 사각지대와 데이터 국외 이전 위험을 역추적하고, 한국형 6대 민감정보(InfoTypes) 및 로컬 하이브리드 가드레일 파이프라인을 처방한다.

```mermaid
sequenceDiagram
    actor User as 금융/엔터프라이즈 사용자
    actor SecOps as 보안 관리자 / CISO 팀
    participant Proxy as Cloud Run 로컬 가드레일 프록시
    participant MA as Model Armor (asia-northeast3 SDP)
    participant VertexAI as Vertex AI 엔드포인트 (asia-northeast3)
    participant CLI as 진단 CLI (diagnose.py)
    participant Report as 진단 리포트 생성기 (report.md)

    User->>Proxy: 프롬프트 입력 ("주민번호 900101-1234567 분석해 줘")
    Proxy->>MA: SDP 템플릿 검사 (KOREA_RRN 마스킹)
    MA-->>Proxy: 비식별화 텍스트 ("주민번호 [REDACTED] 분석해 줘")
    Proxy->>Proxy: 온소일 로컬 인젝션 살균 검증
    Proxy->>VertexAI: generate_content(asia-northeast3 온소일 추론)
    VertexAI-->>User: 안전한 답변 반환

    rect rgb(240, 245, 255)
    note right of CLI: 진단 단계: Model Armor 템플릿 및 리전 정합성 감사
    SecOps->>CLI: python diagnose.py --dry-run
    CLI->>MA: templates.get(location="asia-northeast3")
    MA-->>CLI: TemplateMetadata (필터 활성화 상태, 바인딩된 InfoTypes)
    CLI->>CLI: 데이터 국외 이전 위험 및 한국형 InfoType 누락 판정
    CLI->>Report: generate_markdown_report()
    Report-->>SecOps: 종합 진단 표, 하이브리드 처방전 및 report.md 생성
    end
```

---

## 2. 요구 사항 추적성 매핑 (Traceability Matrix)

| 비즈니스 요구 사항 (BRD) | 기능적 기술 요구 사항 (FR) | 비기능적 기술 요구 사항 (NFR) | 구현 파일 및 모듈 |
| :--- | :--- | :--- | :--- |
| **BR-01** (현장 장애 및 리스크 사전 탐지) | **FR-02** (핵심 운영 지표 및 설정 상태 정밀 진단) | **NFR-01** (최소 IAM 권한 준수) | `diagnose.py` (`audit_model_armor_template`, `check_korea_infotypes`) |
| **BR-02** (표준화된 자동 진단 체계 구축) | **FR-01** (계층형 환경 설정 및 리소스 자동 탐지) | **NFR-02** (비대화형 환경 호환성) | `diagnose.py` (`get_default_project`, `parse_args`) |
| **BR-03** (가상 실행 기반 무중단 사전 검증) | **FR-03** (가상 실행 스모크 테스트 모드) | **NFR-03** (민감 정보 비식별화) | `diagnose.py` (`get_mock_data`, `--dry-run`) |
| **BR-04** (실무자 조치 가이드 및 리포트 안내) | **FR-04** (직관적 콘솔 조치 가이드 및 리소스 정리 안내) | **NFR-04** (리포트 절대 경로 저장 보장) | `diagnose.py` (`generate_markdown_report`), `report.md` |
| **BR-05** (사내 거버넌스 4대 필수 라벨링 준수) | **FR-05** (사내 거버넌스 4대 필수 라벨링 적용) | **NFR-03** (보안 규약 준수) | `README.md`, `diagnose.py` |

---

## 3. 기능적 기술 요구 사항 (Functional Requirements)

| 요구 사항 ID | 연관 BR | 기술 요구 사항 명칭 | 구현 상세 및 검증 기준 |
| :--- | :--- | :--- | :--- |
| **FR-01** | **BR-01** | **계층형 환경 설정 및 리소스 자동 탐지** | CLI 인자(`--config, --dry-run, --json, --location, --project, --template`) > `.env` > `gcloud config` 활성 설정 > 대화형 번호 선택기 순으로 프로젝트 및 대상 리소스를 자동 확정한다. |
| **FR-02** | **BR-02** | **핵심 운영 지표 및 설정 상태 정밀 진단** | 대상 GCP 리소스의 메타데이터, 정책, 할당량 또는 로그 지표를 수집하여 정상(`PASS`), 주의(`WARN`), 위험(`FAIL`) 등급을 산출한다. |
| **FR-03** | **BR-03** | **가상 실행(`--dry-run`) 스모크 테스트 모드** | `--dry-run` 플래그 입력 시 외부 GCP API 호출을 우회하고 내장된 표준 시뮬레이션 데이터를 기반으로 전체 진단 리포트를 1초 내에 출력한다. |
| **FR-04** | **BR-04** | **직관적 콘솔 조치 가이드 및 리소스 정리 안내** | 진단 완료 시 복습 및 사내 공유용 리포트(report.md)를 자동 생성(덮어쓰기)하고, 진단 결과 하단에 Google Cloud 콘솔 조치 URL(Bare URL 표준)과 CLI 복구 명령어를 출력하여 즉각적인 후속 조치를 지원한다. |
| **FR-05** | **BR-05** | **사내 거버넌스 4대 필수 라벨링 적용** | Model Armor 및 DLP 리소스 구성 시 `managed-by=google-cloud-0-to-1`, `scenario=korea-model-armor-guard`, `env=sample`, `created-by=customer-engineer` 라벨을 필수로 주입한다. |

---

## 4. 비기능적 기술 요구 사항 (Non-Functional Requirements)

| 요구 사항 ID | 요구 사항 명칭 | 상세 기준 |
| :--- | :--- | :--- |
| **NFR-01** | **최소 IAM 권한 준수** | 진단에 필요한 최소 권한(`roles/dlp.reader, roles/modelarmor.viewer`)만을 요구하며, 불필요한 쓰기 권한을 강제하지 않는다. |
| **NFR-02** | **비대화형 환경 호환성 (CI/CD Ready)** | `sys.stdin.isatty()` 검증을 통해 백그라운드 태스크나 CI/CD 파이프라인 실행 시 입력 대기(Hang) 없이 안전하게 기본 후보를 채택한다. |
| **NFR-03** | **민감 정보 비식별화 및 보안 규약** | 소스 코드 및 문서 내에 실제 프로젝트 ID나 개인 식별 정보(PII)를 하드코딩하지 않으며, 모든 외부 참조 링크는 Bare URL 괄호 병기 원칙을 준수한다. |
| **NFR-04** | **리포트 절대 경로 저장 보장** | 로컬 진단 스크립트 실행 시 산출물 저장 경로는 스크립트 파일이 위치한 디렉터리의 절대 경로를 기준으로 저장하여 작업 디렉터리와 무관하게 안정적인 저장을 보장한다. |
