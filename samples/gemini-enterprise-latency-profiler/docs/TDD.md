<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 기술 상세 설계서 (TDD): 제미나이 엔터프라이즈(Gemini Enterprise) 파이프라인 구간별 지연 시간 분석기 (`gemini-enterprise-latency-profiler`)

## 1. 시스템 아키텍처 및 런타임 상호작용 시퀀스

본 도구의 런타임 제어 및 데이터 상호작용 흐름은 아래 시퀀스 다이어그램과 같다. 엔지니어가 프로파일링 명령을 실행하면 네트워크 전송(DNS/TCP/TLS), 보안 가드레일(Model Armor), 컨텍스트 증강(Search), 파운데이션 모델 추론(TTFT 및 토큰 생성 속도)을 순차 계측하고 워터폴 차트와 병목 처방을 합성한다.

```mermaid
sequenceDiagram
    actor Engineer as 성능 / AI 엔지니어
    participant CLI as 진단 CLI (diagnose.py)
    participant Net as 전송 네트워크 (DNS / TCP / TLS)
    participant Armor as Model Armor (가드레일 검사)
    participant Search as Vertex AI Search (RAG 증강)
    participant Gemini as Vertex AI Gemini 3.8 Flash

    Engineer->>CLI: python diagnose.py --prompt "..." --template TEMPLATE_ID
    
    rect rgb(240, 245, 255)
    note right of CLI: 1구간: 네트워크 전송 레이턴시 계측
    CLI->>Net: socket DNS query & connect(443) & ssl.wrap_socket()
    Net-->>CLI: DNS RTT, TCP Handshake, TLS Negotiation 시간 반환
    end

    rect rgb(245, 240, 255)
    note right of CLI: 2구간: 보안 가드레일 인스펙션 계측
    CLI->>Armor: sanitizeUserPrompt(template, user_prompt)
    Armor-->>CLI: 검사 결과 반환 (살균 및 탈옥 검사 소요 시간 계측)
    end

    rect rgb(255, 250, 240)
    note right of CLI: 3구간: RAG 컨텍스트 검색 계측
    opt 검색 그라운딩 활성화 시
        CLI->>Search: searchDataStore(query)
        Search-->>CLI: 검색 청크 반환 (RAG 검색 소요 시간 계측)
    end
    end

    rect rgb(240, 255, 245)
    note right of CLI: 4구간: 파운데이션 모델 추론 및 스트리밍 계측
    CLI->>Gemini: generateContentStream(contents)
    Gemini-->>CLI: First Chunk 도착 (TTFT 계측)
    loop 스트리밍 수신
        Gemini-->>CLI: Subsequent Token Chunks
    end
    Gemini-->>CLI: Stream Complete (전체 생성 시간 및 TPS 계산)
    end

    CLI->>CLI: 워터폴(Waterfall) 차트 생성 및 최대 병목 최적화 가이드 도출
    CLI-->>Engineer: 종합 레이턴시 프로파일링 리포트 및 report.md 생성
```

---

## 2. 요구 사항 추적성 매핑 (Traceability Matrix)

| 비즈니스 요구 사항 (BRD) | 기능적 기술 요구 사항 (FR) | 비기능적 기술 요구 사항 (NFR) | 구현 파일 및 모듈 |
| :--- | :--- | :--- | :--- |
| **BR-01** (계층형 환경 설정 및 리소스 자동 탐지) | **FR-01** (계층형 환경 설정 및 리소스 자동 탐지) | **NFR-02** (비대화형 환경 호환성) | `diagnose.py` |
| **BR-02** (구간별 지연 시간 분해 및 정밀 계측) | **FR-02** (핵심 운영 지표 및 설정 상태 정밀 진단) | **NFR-01** (최소 IAM 권한 준수) | `diagnose.py` |
| **BR-03** (가상 실행 스모크 테스트 지원) | **FR-03** (가상 실행 스모크 테스트 모드) | **NFR-03** (민감 정보 비식별화) | `diagnose.py` |
| **BR-04** (워터폴 차트 및 병목 최적화 가이드) | **FR-04** (직관적 콘솔 조치 가이드 및 리소스 정리) | **NFR-04** (표준 리소스 라벨링) | `diagnose.py`, `report.md` |
| **BR-05** (사내 거버넌스 4대 필수 라벨링 준수) | **FR-05** (사내 거버넌스 4대 필수 표준 라벨링 주입) | **NFR-04** (표준 리소스 라벨링) | `diagnose.py` |

---

## 3. 기능적 기술 요구 사항 (Functional Requirements)

| 요구 사항 ID | 연관 BR | 기술 요구 사항 명칭 | 구현 상세 및 검증 기준 |
| :--- | :--- | :--- | :--- |
| **FR-01** | **BR-01** | **계층형 환경 설정 및 리소스 자동 탐지** | CLI 인자(`--config, --dry-run, --location, --model, --project, --prompt, --template`) > `.env` > `gcloud config` 활성 설정 > 대화형 번호 선택기 순으로 프로젝트 및 대상 리소스를 자동 확정한다. |
| **FR-02** | **BR-02** | **핵심 운영 지표 및 설정 상태 정밀 진단** | 대상 구글 클라우드(Google Cloud) 리소스의 메타데이터, 정책, 할당량 또는 로그 지표를 수집하여 정상(`PASS`), 주의(`WARN`), 위험(`FAIL`) 등급을 산출한다. |
| **FR-03** | **BR-03** | **가상 실행(`--dry-run`) 스모크 테스트 모드** | `--dry-run` 플래그 입력 시 외부 구글 클라우드 API 호출을 우회하고 내장된 표준 시뮬레이션 데이터를 기반으로 전체 진단 리포트를 1초 내에 출력한다. |
| **FR-04** | **BR-04** | **직관적 콘솔 조치 가이드 및 리소스 정리 안내** | 진단 결과 하단에 구글 클라우드 콘솔 조치 URL(Bare URL 표준)과 CLI 복구 명령어를 출력하여 즉각적인 후속 조치를 지원한다. |
| **FR-05** | **BR-05** | **사내 거버넌스 4대 필수 표준 라벨링 주입** | 지연 시간 프로파일링 및 엔드포인트 테스트 리소스 생성 시 4대 표준 라벨(`managed-by`, `scenario`, `env`, `created-by`)을 필수로 주입한다. |

---

## 4. 비기능적 기술 요구 사항 (Non-Functional Requirements)

| 요구 사항 ID | 요구 사항 명칭 | 상세 기준 |
| :--- | :--- | :--- |
| **NFR-01** | **최소 IAM 권한 준수** | 진단에 필요한 최소 권한(`roles/aiplatform.user, roles/modelarmor.admin, roles/monitoring.viewer`)만을 요구하며, 불필요한 쓰기 권한을 강제하지 않는다. |
| **NFR-02** | **비대화형 환경 호환성 (CI/CD Ready)** | `sys.stdin.isatty()` 검증을 통해 백그라운드 태스크나 CI/CD 파이프라인 실행 시 입력 대기(Hang) 없이 안전하게 기본 후보를 채택한다. |
| **NFR-03** | **민감 정보 비식별화 및 보안 규약** | 소스 코드 및 문서 내에 실제 프로젝트 ID나 개인 식별 정보(PII)를 하드코딩하지 않으며, 모든 외부 참조 링크는 Bare URL 괄호 병기 원칙을 준수한다. |
| **NFR-04** | **사내 거버넌스 4대 필수 표준 라벨링 준수** | 사내 거버넌스, FinOps 비용 배분 및 자원 추적성을 위해 모든 생성 매니페스트 및 리소스에 4대 표준 라벨을 필수로 주입한다. |
