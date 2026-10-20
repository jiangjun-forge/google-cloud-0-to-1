<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 기술 상세 설계서 (TDD: Technical Design Document): 혁신 금융 서비스 규제 준수 보안 경계 진단 가이드 (korea-regulatory-perimeter-guard)

---

## 1. 시스템 아키텍처 개요 및 설계 원칙

### 1.1 설계 목표
본 도구는 대한민국 금융권의 엄격한 클라우드 보안 컴플라이언스(전자금융거래법, 전자금융감독규정, 신용정보법)를 Google Cloud 환경에서 자동 검증하기 위한 **경량 진단 엔진(Lightweight Diagnostic Engine)**이다.

### 1.2 핵심 설계 원칙
1. **순수 파이썬 단일 실행 모델**: CLI 기반 핵심 파이썬 스크립트(`diagnose.py`)를 통해 상위 폴더 의존성 없이 단일 명령 실행을 지원한다.
2. **비파괴적 읽기 전용 스캔(Non-Destructive Read-Only Scan)**: 모든 GCP 리소스에 대해 `describe`, `list`, `get` 조회 명령만 수행하여 운영 환경에 영향을 주지 않고 안전함.
3. **완전 독립형 모의 실행(`--dry-run`)**: 실제 GCP 인증이나 IAM 권한이 없는 환경에서도 결정론적(Deterministic) 모의 진단 데이터를 반환하여 빠른 데모 및 검증 보장.
4. **선언적 처방(Prescriptive Remediation)**: 결격 항목(FAIL/WARN) 식별 시 관리자가 즉시 복구할 수 있는 표준 `gcloud` CLI 명령어를 1:1 매핑하여 출력.

---

## 2. 시스템 아키텍처 및 런타임 상호작용 시퀀스

본 도구의 런타임 제어 및 데이터 상호작용 흐름은 아래 시퀀스 다이어그램과 같다. 금융보안팀 또는 CISO가 CLI를 실행하면 VPC-SC, Cloud Storage Bucket Lock, Cloud KMS CMEK, IAM 감사 로깅, SA 키 발급 차단, SSL/TLS 정책, Model Armor/SDP 가명화 설정을 교차 감사하여 9대 금융 기술 통제 준수 여부를 판정하고 정규 gcloud 복구 처방을 도출한다.

```mermaid
sequenceDiagram
    actor Auditor as 금융보안팀 / CISO / 감사관
    participant CLI as CLI 컨트롤러 (diagnose.py)
    participant VPCSC as Access Context Manager API
    participant Storage as Cloud Storage API
    participant KMS as Cloud KMS API
    participant IAM as Cloud Resource Manager API
    participant Compute as Compute Engine API
    participant Security as Model Armor & SDP API

    rect rgb(240, 245, 255)
    note right of CLI: 1단계: 9대 핵심 금융 규제 전수 비파괴 실사
    Auditor->>CLI: python diagnose.py --project $PROJECT_ID
    par 1. 논리적 망 분리 & RAG 격리
        CLI->>VPCSC: getServicePerimeter(perimeter_name)
        VPCSC-->>CLI: 서비스 경계 및 보호 리소스 상태
    and 2. 스토리지 5년 불변 보존
        CLI->>Storage: getBucket(audit_bucket)
        Storage-->>CLI: retentionPolicy (157,680,000s) 및 locked 여부
    and 3. CMEK 전면 적용
        CLI->>KMS: getCryptoKey(asia-northeast3)
        KMS-->>CLI: 키 알고리즘 및 자동 순환 상태
    and 4. Vertex AI 데이터 접근 감사
        CLI->>IAM: getIamPolicy(auditConfigs)
        IAM-->>CLI: DATA_READ, DATA_WRITE 전체 활성화 여부
    and 5. SA 키 발급 차단 & SSL 정책
        CLI->>Compute: getSslPolicy(ssl_policy_name)
        Compute-->>CLI: minTlsVersion: TLS_1_2 확인
    and 6. AI 가명화 및 프롬프트 살균
        CLI->>Security: getTemplate(model_armor_template)
        Security-->>CLI: PII 마스킹 및 인젝션 필터 활성화 여부
    end
    end

    rect rgb(245, 240, 255)
    note right of CLI: 2단계: 갭 분석 및 선언적 복구 처방 도출
    CLI->>CLI: 9대 기둥별 PASS/FAIL 판정 및 FSI 준수 종합 매트릭스 산출
    CLI->>CLI: 결격 항목별 표준 gcloud 복구 명령어 합성
    CLI-->>Auditor: FSI 소명 리포트 (report.md) 생성 및 화면 브리핑
    Auditor-->>Auditor: 금융감독원/금융보안원 보안성 심의 증적 확보
    end
```

---

## 3. 모듈 및 컴포넌트 설계

### 3.1 CLI 인자 파서 (`parse_args`)
- `-p`, `--project`: 대상 GCP 프로젝트 ID (미지정 시 활성 gcloud 프로젝트 자동 감지).
- `-l`, `--location`: 점검 대상 리전 (기본값: `asia-northeast3`).
- `-b`, `--audit-bucket`: 감사 로그 및 입출력 저장 대상 버킷명.
- `-k`, `--kms-key`: 검증 대상 CMEK 키 리소스 경로.
- `--dry-run`: 실제 API 호출 없이 모의 감사 데이터 실행.

### 3.2 서브프로세스 래퍼 (`run_gcloud_json`)
- 모든 gcloud 명령어를 `subprocess.run(..., capture_output=True, text=True, check=True)`로 안전하게 격리 실행.
- `--format=json` 인자를 강제하여 파이썬 딕셔너리로 역직렬화.
- 비정상 종료 시 예외를 포획하고 `None`을 반환하여 전체 진단 프로세스가 중단되지 않도록 안전장치(Fail-Safe) 마련.

### 3.3 리포트 포매터 (`print_report`)
- 9개 항목의 상태를 `[PASS]`, `[WARN]`, `[FAIL]`로 분류.
- 총 통제 항목 수 대비 충족, 주의, 미달 건수 요약 통계 집계.
- 결격 항목 발생 시 `규제 요건` 및 `조치 권고`를 2줄 들여쓰기로 명확히 시각화.
- 진단 완료 시 사내 공유 및 복습용 마크다운 리포트(`report.md`)를 자동 생성(덮어쓰기).
- 미달 항목(`FAIL`) 존재 시 프로세스 종료 코드 `1`을 반환하여 CI/CD 파이프라인 연동 지원.

---

## 4. 9대 기술 통제 세부 구현 명세 (Functional Requirements)

| 요구 사항 ID | 점검 명칭 | 실행 명령어 | 판정 알고리즘 (Evaluation Logic) |
| :--- | :--- | :--- | :--- |
| **FR-01** | VPC-SC 보안 경계 | `gcloud access-context-manager perimeters list --format=json` | 프로젝트 번호/ID가 포함된 서비스 경계의 `restrictedServices` 목록에 `aiplatform.googleapis.com`이 포함되어 있으면 PASS, 아니면 FAIL. |
| **FR-02** | 웹 검색 Grounding 격리 | 아키텍처 정적 분석 | VPC-SC 내부에서 `web_search_tool` 호출 시 Egress 차단 위험을 경고하고 DMZ 프로젝트 분리 구조를 WARN으로 권고. |
| **FR-03** | Cloud Storage 5년 보존 | `gcloud storage buckets describe gs://<BUCKET> --format=json` | `retention_policy.retention_period >= 157680000` (5년) 이고 `retention_policy.is_locked == true` 이면 PASS, 잠금 미설정 시 WARN, 기간 미달/미설정 시 FAIL. |
| **FR-04** | 고객 관리 암호화 키 | `gcloud storage buckets describe gs://<BUCKET> --format=json` | `encryption.default_kms_key_name` 속성이 존재하고 활성화된 Cloud KMS 키와 일치하면 PASS, Google 기본 키면 FAIL. |
| **FR-05** | 데이터 접근 감사 로그 | `gcloud projects get-iam-policy <PROJECT> --format=json` | `auditConfigs` 내 `allServices` 또는 `aiplatform.googleapis.com`의 `auditLogConfigs`에 `DATA_READ`와 `DATA_WRITE`가 모두 포함되어 있으면 PASS, 아니면 FAIL. |
| **FR-06** | Model Armor 가드레일 | `gcloud beta model-armor templates list --location=<LOC> --format=json` | 대상 리전에 활성화된 Model Armor 템플릿이 1개 이상 존재하면 PASS, 없으면 FAIL. |
| **FR-07** | SDP 가명 처리 템플릿 | `gcloud dlp inspect-templates list --location=<LOC> --format=json` | 대상 리전에 DLP 검사 템플릿이 존재하면 PASS, 없으면 WARN. |
| **FR-08** | 서비스 계정 키 발급 차단 | `gcloud resource-manager org-policies describe constraints/iam.disableServiceAccountKeyCreation --project=<PROJECT> --format=json` | 정책 규칙의 `spec.rules`에 `enforce: true`가 설정되어 있으면 PASS, 아니면 FAIL. |
| **FR-09** | 전송 구간 TLS 1.2+ 암호화 | `gcloud compute ssl-policies list --project=<PROJECT> --format=json` | `minTlsVersion`이 `TLS_1_2` 또는 `TLS_1_3`으로 설정된 커스텀 SSL 정책이 식별되면 PASS, 없으면 WARN. |
| **FR-10** | 사내 거버넌스 4대 필수 라벨링 | 리소스 생성 및 점검 시 4대 표준 라벨 주입 검증 | 혁신 금융 서비스 통제 리소스 구성 시 `managed-by=google-cloud-0-to-1`, `scenario=korea-regulatory-perimeter-guard`, `env=sample`, `created-by=customer-engineer` 라벨을 필수로 주입한다. |

---

## 5. 보안 및 권한 설계 (Security & IAM Matrix)

본 도구를 실행하기 위해 진단 실행 주체(사용자 계정 또는 서비스 계정)에 요구되는 최소 IAM 권한은 다음과 같다:

```
roles/accesscontextmanager.reader  -> accesscontextmanager.perimeters.list
roles/compute.viewer               -> compute.sslPolicies.list
roles/dlp.inspectTemplatesReader   -> dlp.inspectTemplates.list
roles/logging.viewer               -> logging.views.access
roles/orgpolicy.policyViewer       -> orgpolicy.policies.get, orgpolicy.policies.list
roles/storage.admin                -> storage.buckets.get, storage.buckets.getIamPolicy
```

---

## 6. 비기능 설계 및 검증 전략 (Non-Functional Requirements)

| 요구 사항 ID | 분류 | 세부 설계 및 검증 방법 |
| :--- | :--- | :--- |
| **NFR-01** | 비파괴성 (안전성 확보) | 모든 GCP 호출을 읽기 전용(`describe`, `list`, `get`)으로 제한하여 기존 리소스 변경 없이 안전성 확보. |
| **NFR-02** | 모의 실행 (Dry-run) | 외부 네트워크 의존성 없이 `python3 diagnose.py --dry-run`으로 9개 항목 상태를 신속하게 시뮬레이션. |
| **NFR-03** | 실행 성능 | 전체 9개 항목의 실측 검사를 지연 없이 신속하게 완료할 수 있도록 경량 gcloud CLI 호출 최적화. |
| **NFR-04** | 민감 정보 비식별화 | 실제 고객 사명, 프로젝트 ID, 내부 도메인 등의 하드코딩 배제 및 가명 템플릿 변수 표준화. |
| **NFR-05** | 리포트 절대 경로 저장 보장 | 로컬 진단 스크립트 실행 시 산출물 저장 경로는 스크립트 파일이 위치한 디렉터리의 절대 경로를 기준으로 저장하여 작업 디렉터리와 무관하게 안정적인 저장을 보장한다. |
