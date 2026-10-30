<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

> [!IMPORTANT]
> **구글 (Google LLC) 참조용 샘플 고지 사항**:
> 본 프로젝트의 모든 소스 코드와 문서는 Google LLC의 소유이며, Apache-2.0 라이선스에 따라 오직 **참조용 샘플 (Sample / Reference Only)** 목적으로만 제공된다. 프로덕션 환경에 그대로 사용할 수 없으며, 사전 통지 없이 언제든 내용이 수정, 변경 또는 삭제될 수 있다.

# 제미나이(Gemini) API 비용 급증 원인 진단 (`gemini-billing-spike`)

데이터 액세스 감사 로그(Audit Logs)가 꺼져 있어도, 클라우드 모니터링(Cloud Monitoring) 기본 지표를 통해 **어떤 인증 수단(API 키, 서비스 계정, OAuth 등)에서 Gemini 호출 비용이 급증했는지 1분 만에 규명**하는 진단 가이드다. (As of 2026-10-17)

---

## 1. 발생 증상 및 진단 대상 체크리스트

사내 또는 고객사 환경에서 아래 증상이 발생한다면 즉시 진단 대상이다:
- [ ] **비용 급증**: 이번 달 청구서나 예산 알림에서 Gemini(버텍스 AI(Vertex AI) 또는 AI Studio) 비용이 예상보다 갑자기 수 배 이상 급증했을 때
- [ ] **감사 로그 부재**: "누가 호출했는지" 확인하려 했으나, 빅쿼리(BigQuery) 감사 로그 내보내기나 데이터 액세스 감사 로그가 비활성화되어 있어 원인을 파악하기 어려울 때
- [ ] **보안 유출 의심**: 개발자가 GitHub나 클라이언트 앱에 API 키 또는 서비스 계정 키를 실수로 노출했는지 신속히 점검하고자 할 때


### 1.1 도구의 본질 및 비즈니스 해결 과제 (What & Why)
- **대상 사용자 (Target)**: 클라우드 FinOps 관리자, 보안 운영팀, 백엔드 개발 리드 및 클라우드 빌링 담당자
- **해결하는 핵심 문제 (Core Pain Points)**:
  1. Gemini API 호출 요금이 전일 대비 수배 이상 급증했으나 데이터 액세스 감사 로그가 꺼져 있어 원인 규명이 불가능한 문제
  2. 어떤 API 키가 유출되었는지, 특정 서비스 계정의 무한 루프인지, 사용자의 비정상 호출인지 분별하지 못해 API 전체를 차단해야 하는 위험
  3. 비용 급증 시 실시간으로 과금 주체를 추적하고 즉시 무효화할 수 있는 안전한 격리 플레이북의 부재
- **본 솔루션의 해결 방식 (Solution)**:
  - 데이터 액세스 감사 로그가 비활성화된 상태에서도 Cloud Monitoring의 기본 지표(`serviceruntime.googleapis.com`) 90일 시계열 데이터를 분석하여, 비용 급증을 유발한 특정 인증 수단(API 키, 서비스 계정, OAuth 자격 증명)을 규명하고 즉각적인 조치 가이드를 제공한다.

### 1.2 최종 산출물 3종 세트 미리보기 (Deliverables & Visual Preview)
본 도구를 실행(`python diagnose.py`)하면 다음 3가지 구체적인 엔터프라이즈 자산이 생성된다:

| 산출물 구분 | 산출물 형태 및 명칭 | 주요 포함 내용 및 실무 활용 방안 |
| :--- | :--- | :--- |
| **① 터미널 콘솔 요약** | Visual CLI Table | 90일간 API 호출 총량, 급증 시점, 인증 수단별 호출 비중(%) 및 과금 주체 식별 결과 표 |
| **② 정규 진단 보고서** | 마크다운 파일 (`report.md`) | 시계열 트래픽 분석 차트, 급증 유발 주체 상세 소명, 위험 API 키/서비스 계정 비활성화 가이드 및 방어 아키텍처 |
| **③ 후속 조치 및 배포 자산** | Actionable Asset Specs | • **위험 자격 증명 즉시 격리 명령어**: 문제의 API 키 삭제 및 서비스 계정 키 비활성화 gcloud 명령<br/>• **Cloud Billing 예산 알림 연동 가이드**: 지출 급증 시 Pub/Sub으로 실시간 경보를 전송하는 구성<br/>• **Gemini Request/Response 로깅 싱크**: 프롬프트 단위 추적을 위한 BigQuery 자동 로깅 설정 |

---

## 2. 빠른 시작 (Quickstart)

> [!TIP]
> Cloud Shell 접속 환경 구성 및 저장소 클론(`git clone`) 방법은 루트의 [메인 README](../../README.md)를 참고한다.

### 1) 모의 데이터 가상 실행 (Dry-Run)
GCP API 호출 없이 내장된 가상 인프라 데이터로 정상 동작 여부를 즉시 검증한다:
```bash
python diagnose.py --dry-run
```

**터미널 진단 출력 미리보기:**
```text
[진단 결과] 제미나이(Gemini) 사용량 및 비용 급증 원인 분석 리포트
   - 대상 프로젝트: sample-project-id
   - 조회 대상 기간: 최근 90일
========================================================================
총 집계된 API 호출 수: 148,250 건 (시계열 레코드: 2개)
┌──────────────────────────────────────────────────────────────────────┐
│ 1. 호출 주체(자격 증명)별 점유율 및 호출 횟수                             │
├──────────────────────────────────────────────────────────────────────┤
│  - apikey:AIzaSyB1234567890abcdefghijklmnopqr   :  135,200회 ( 91.2%) │
│  - serviceAccount:gemini-batch-sa@sample-proj.. :   13,050회 (  8.8%) │
```


### 2) 사내 환경 대화형 설정 (Config Wizard, 선택 사항)
사내 활성 프로젝트 및 환경 설정을 대화형으로 탐색하여 `.env`에 자동 저장한다:
```bash
python diagnose.py --config
```


### 3) 실제 사내 인프라 실시간 진단
```bash
python diagnose.py
```
> [!NOTE]
> 앞서 `python diagnose.py --config`로 환경 설정을 저장했거나 gcloud 활성 설정을 그대로 활용할 경우 별도의 `.env` 생성 없이 즉시 실행할 수 있다. (환경 변수를 텍스트 에디터로 직접 수동 편집하고자 할 때만 `cp -n .env.example .env` 실행 후 수정)

---

## 3. 솔루션 아키텍처 및 런타임 토폴로지

본 도구는 감사 로그 없이도 Cloud Monitoring 시스템 메트릭을 통해 비용 급증을 유발한 자격 증명(API 키, SA, OAuth)을 4계층으로 역추적한다:

```mermaid
flowchart TD
    subgraph Layer1["1. 클라이언트 및 인입 계층 (Traffic Ingress Layer)"]
        Caller["외부 호출자 / 배치 잡 / 클라이언트 앱"] -->|"API 요청 (헤더에 인증 정보 포함)"| Endpoint["Google Cloud API 엔드포인트<br/>(Vertex AI / Generative Language API)"]
        FinOps["FinOps 엔지니어 / 관리자"] -->|"1. 비용 급증 진단 실행"| CLI["진단 컨트롤러<br/>(diagnose.py)"]
    end

    subgraph Layer2["2. 인증 수단 및 자격 증명 경계 (Credential Boundary)"]
        APIKey{"API 키 (apikey:AIzaSy...)"}
        SAKey{"서비스 계정 (serviceAccount:...)"}
        OAuth{"OAuth 클라이언트 (oauth2:...)"}
    end

    subgraph Layer3["3. 모니터링 원격 측정 런타임 (Telemetry & Analysis Runtime)"]
        Engine["시계열 분석 및 주체별 집계 엔진<br/>(serviceruntime.googleapis.com 지표 분해)"]
        FixGen["원클릭 차단 처방 생성기<br/>(API 키 삭제 & IAM 회수 명령어)"]
        Engine --> FixGen
    end

    subgraph Layer4["4. 대상 클라우드 백엔드 인프라 (Target Backend Infrastructure)"]
        Metrics[("Cloud Monitoring<br/>(플랫폼 기본 무료 메트릭)")]
        IAMAdmin["Cloud IAM & API Keys 콘솔<br/>(자격 증명 비활성화/삭제)"]
        BillingAlert["Cloud Billing<br/>(예산 및 쿼터 한도 가드)"]
    end

    Endpoint --> Layer2
    Layer2 -->|"기본 플랫폼 텔레메트리 자동 기록"| Metrics

    CLI -->|"2. 권한 확인 및 메트릭 쿼리"| Metrics
    Metrics -->|"시계열 데이터 스트림"| Engine
    FixGen -->|"3. 키 삭제 및 쿼터 차단"| IAMAdmin
    FixGen -->|"4. 재발 방지 예산 설정"| BillingAlert

    classDef portal fill:#e8f0fe,stroke:#4285f4,stroke-width:2px;
    classDef security fill:#fef7e0,stroke:#f9ab00,stroke-width:2px;
    classDef runtime fill:#e6f4ea,stroke:#34a853,stroke-width:2px;
    classDef backend fill:#fce8e6,stroke:#ea4335,stroke-width:2px;

    class Caller,FinOps,CLI portal;
    class Endpoint,APIKey,SAKey,OAuth security;
    class Engine,FixGen runtime;
    class Metrics,IAMAdmin,BillingAlert backend;
```

---
## 4. 조치 가이드 및 권장 설정

출력된 자격 증명 유형에 따라 다음 단계로 이동하여 즉시 조치한다:

### 1. `apikey:AIzaSy...`가 상위 점유율을 차지한 경우
- **원인**: 누군가 소스 코드, 프론트엔드 모바일 앱, 또는 퍼블릭 깃허브에 API 키를 노출했거나 외부 테스트용 키가 무제한 호출되고 있다.
- **조치 방법**:
  1. GCP 콘솔 > API 및 서비스 > 사용자 인증 정보 ( https://console.cloud.google.com/apis/credentials )로 이동한다.
  2. 화면에 찍힌 키 앞부분(`AIzaSy...`)과 일치하는 API 키를 찾는다.
  3. **키 수정(연필 아이콘)**을 눌러 조치한다:
     - **애플리케이션 제한**: 특정 웹사이트(HTTP 리퍼러)나 특정 IP에서만 호출되도록 제한한다.
     - **API 제한**: 반드시 필요한 API(예: Vertex AI API)만 체크하고 나머지는 잠근다.
  4. 알 수 없는 키이거나 유출이 확실한 경우 즉시 **삭제(휴지통 아이콘)**한다.

### 2. `serviceAccount:...`가 상위 점유율을 차지한 경우
- **원인**: 내부 배치 애플리케이션, 클라우드 런(Cloud Run) 서비스, 또는 CI/CD 파이프라인에서 무한 재시도나 대량 호출 루프가 돌고 있다.
- **조치 방법**:
  1. GCP 콘솔 > IAM 및 관리자 > 서비스 계정 ( https://console.cloud.google.com/iam-admin/serviceaccounts )으로 이동한다.
  2. 해당 서비스 계정이 연결된 VM, Cloud Run, GKE 워크로드를 확인한다.
  3. JSON 키 파일이 발급되어 있다면 해당 키의 최근 생성일을 확인하고 불필요한 키는 사용 중지(Disable) 또는 삭제한다.

---
### GCP 리소스 생성 시 4대 필수 표준 라벨링 준수
- 사내 거버넌스 및 자원 식별, 비용 추적을 위해 관련 클라우드 리소스 생성 시 4대 표준 라벨을 필수로 주입한다:
  - `managed-by`: `google-cloud-0-to-1`
  - `scenario`: `gemini-billing-spike`
  - `env`: `sample`
  - `created-by`: `customer-engineer`
- gcloud CLI 예시: `--labels=managed-by=google-cloud-0-to-1,scenario=gemini-billing-spike,env=sample,created-by=customer-engineer`

---

## 5. 사전 준비 사항 (필요 IAM 권한)

본 도구를 실행하려면 최소 아래의 IAM 권한이 필요하다:

이 도구는 **오직 읽기(조회) 작업만 수행**하며, 인프라를 변경하거나 삭제하지 않는다.  
스크립트를 실행하는 사용자 또는 서비스 계정에 아래 역할(Role) 중 하나가 필요하다:

| 역할 (Role) | 권한 ID | 용도 |
| :--- | :--- | :--- |
| **모니터링 뷰어 (권장)** | `roles/monitoring.viewer` | Cloud Monitoring 지표 데이터 조회 |
| **뷰어 (기본)** | `roles/viewer` | 프로젝트 리소스 및 지표 전반 조회 |

> [!NOTE]
> 사내 보안팀에 권한을 요청할 때는 **"Cloud Monitoring 지표 조회를 위한 `roles/monitoring.viewer` 권한 1개"**만 요청하면 된다.

---

## 6. 기술적 배경 및 아키텍처 원리 (Deep Dive)

### 관련 상세 설계 및 요구 사항 명세
- [비즈니스 요구 사항 명세서 (BRD)](docs/BRD.md): 비즈니스 배경, 성공 지표 및 요구 사항(BR-01~) 명세
- [기술 상세 설계서 (TDD)](docs/TDD.md): 시스템 아키텍처, 기능(FR-01~) 및 비기능(NFR-01~) 설계 명세

스크립트가 완료되면 아래와 같이 **어떤 자격 증명이 전체 호출의 몇 %를 차지했는지** 명확한 표로 출력된다:

```text
========================================================================
[진단 결과] 제미나이(Gemini) 사용량 및 비용 급증 원인 분석 리포트
   - 대상 프로젝트: sample-project-id
   - 조회 대상 기간: 최근 90일
========================================================================

총 집계된 API 호출 수: 148,250 건 (시계열 레코드: 4개)

┌──────────────────────────────────────────────────────────────────────┐
│ 1. 호출 주체(자격 증명)별 점유율 및 호출 횟수                        │
├──────────────────────────────────────────────────────────────────────┤
│  - apikey:AIzaSyB1234567890abcdefghijklmnopqr   :  135,200회 ( 91.2%) │
│  - serviceAccount:gemini-batch-sa@my-proj...    :   13,050회 (  8.8%) │
└──────────────────────────────────────────────────────────────────────┘

[2. 호출된 서비스 및 API 메서드]
  - aiplatform.googleapis.com (Vertex AI Gemini): 148,250회

[상위 호출 메서드]
  - GenerateContent: 142,100회
  - StreamGenerateContent: 6,150회
```

---
## 7. 리소스 정리 (Teardown) 안내

본 도구는 순수 Cloud Monitoring 플랫폼 지표 조회 도구이며 클라우드 상에 영구 자원을 생성하지 않으므로 별도의 자원 정리 작업이 필요하지 않다.
