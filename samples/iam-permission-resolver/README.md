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

# GCP IAM 권한 거부(403) 감사 역추적 및 원클릭 복구 (iam-permission-resolver)

구글 클라우드 IAM(Cloud IAM) 환경에서 발생하는 403 권한 거부(Permission Denied) 실패 이벤트를 감사 로그에서 정밀 역추적하고, **서비스별 최소 권한(Least Privilege) IAM 역할 및 즉시 복구 가능한 gcloud 명령어를 1분 만에 자동 처방**하는 도구다. (As of 2026-10-17)

---

## 1. 발생 증상 및 진단 대상 체크리스트

사내 또는 고객사 환경에서 아래 증상이 발생한다면 즉시 진단 대상이다:
- [ ] **원인 미상의 403 권한 거부**: 파이프라인이나 서비스에서 `Permission Denied` 오류가 발생했으나 정확히 어떤 IAM 역할(Role)이 누락되었는지 확인하기 어려울 때
- [ ] **과도한 권한 부여(오버 그랜트) 방지**: 문제를 해결하겠다고 `roles/editor`나 `roles/owner`를 남발하지 않고 최소 권한 역할만 선별하여 안전하게 부여하고자 할 때
- [ ] **감사 로그 기반의 즉각 처방**: Cloud Logging의 `cloudaudit.googleapis.com/data_access` 감사 로그를 분석하여 계정 형태(사용자 vs 서비스 계정)에 맞춘 gcloud 명령어를 원클릭으로 확보하고자 할 때

---

## 2. 빠른 시작 (Quickstart)

### 1) 모의 데이터 가상 실행 (Dry-Run)
GCP API 호출 없이 내장된 가상 인프라 데이터로 정상 동작 여부를 즉시 검증한다:
```bash
python diagnose.py --dry-run
```

**터미널 진단 출력 미리보기:**
```text
[진단 결과] GCP IAM 권한 거부(403) 감사 추적 및 해결 처방 리포트
  - 대상 프로젝트: sample-project-id
  - 조회 기간: 최근 7일
========================================================================
발견된 권한 거부 실패 내역: 3건
[실패 건 #1]
  - 실패 주체 계정: backend-developer@company.com
  - 요청 대상 서비스: aiplatform.googleapis.com
  - 실행 실패 액션: google.cloud.aiplatform.v1beta1.PredictionService.GenerateContent
  - 실제 오류 내용: Permission 'aiplatform.endpoints.predict' denied on resource
```

### 2) 실제 사내 인프라 실시간 진단
```bash
cp .env.example .env
python diagnose.py
```
> [!NOTE]
> `.env` 설정값을 비워두면 gcloud 활성 설정 및 사내 리소스를 자동으로 감지하여 진단한다.

---

## 3. 진단 및 해결 흐름

```mermaid
flowchart TD
    Start(["서비스 구동 중 403 Permission Denied 발생"]) --> RunTool["진단 도구 실행<br/><code>python diagnose.py -p my-project</code>"]
    
    RunTool --> QueryAudit["Cloud Logging 데이터 액세스 감사 로그 조회<br/>(cloudaudit.googleapis.com/data_access)"]
    QueryAudit --> ParseEvents["실패 이벤트 추출<br/>- 실패 계정<br/>- 서비스명<br/>- 메서드명<br/>- 에러 메시지"]
    
    ParseEvents --> MatchRole["서비스별 최소 권한 역할 매핑<br/>(aiplatform.user, bigquery.dataEditor 등)"]
    MatchRole --> GenerateCmd["원클릭 gcloud IAM 바인딩 명령어 자동 생성"]
    
    GenerateCmd --> ApplyCmd["프로젝트 관리자가 명령어 실행"]
    ApplyCmd --> Retest["서비스 재시도 검증"]
    Retest --> Done(["[복구 완료] 최소 권한 원칙 충족 및 정상 동작"])

    classDef alert fill:#ffdddd,stroke:#f44336,stroke-width:2px;
    classDef success fill:#ddffdd,stroke:#4caf50,stroke-width:2px;
    classDef action fill:#e3f2fd,stroke:#2196f3,stroke-width:2px;
    class Start,MatchRole alert;
    class Done success;
    class RunTool,QueryAudit,ParseEvents,GenerateCmd,ApplyCmd,Retest action;
```

---
## 4. 조치 가이드 및 권장 설정

- **Cloud IAM 관리 콘솔**: ( https://console.cloud.google.com/iam-admin/iam )
- **Cloud Logging 감사 로그 탐색기**: ( https://console.cloud.google.com/logs/query )

---
## 5. 사전 준비 사항 (필요 IAM 권한)

본 도구를 실행하려면 최소 아래의 IAM 권한이 필요하다:

감사 로그를 조회하고 IAM 역할을 바인딩하기 위해 필요한 역할 목록이다:

| 역할 (Role) | 권한 ID | 용도 |
| : | : | : |
| **클라우드 로깅 뷰어(roles/logging.viewer)** | `roles/logging.viewer` | Cloud Logging 데이터 액세스 감사 로그 읽기 |
| **프로젝트 IAM 관리자(roles/resourcemanager.projectIamAdmin)** | `roles/resourcemanager.projectIamAdmin` | 추천된 IAM 역할을 계정에 최종 부여 |

> [!NOTE]
> `--dry-run` 모드로 실행할 경우 별도의 권한 없이도 가상 권한 거부 시나리오와 처방 명령어 형식을 즉시 확인할 수 있다.

---

## 6. 기술적 배경 및 아키텍처 원리 (Deep Dive)

### 관련 상세 설계 및 요구 사항 명세
- [비즈니스 요구 사항 명세서 (BRD)](docs/BRD.md): 비즈니스 배경, 성공 지표 및 요구 사항(BR-01~) 명세
- [기술 상세 설계서 (TDD)](docs/TDD.md): 시스템 아키텍처, 기능(FR-01~) 및 비기능(NFR-01~) 설계 명세

스크립트가 완료되면 아래와 같이 **실패 내역과 즉시 복구할 수 있는 복사 가능한 gcloud 명령어**가 출력된다:

```text
========================================================================
[진단 결과] GCP IAM 권한 거부(403) 감사 추적 및 해결 처방 리포트
  - 대상 프로젝트: my-prod-project
  - 조회 기간: 최근 7일
========================================================================

발견된 권한 거부 실패 내역: 3건

[실패 건 #1]
  - 실패 주체 계정: backend-developer@company.com
  - 요청 대상 서비스: aiplatform.googleapis.com
  - 실행 실패 액션: google.cloud.aiplatform.v1beta1.PredictionService.GenerateContent
  - 실제 오류 내용: Permission 'aiplatform.endpoints.predict' denied on resource
  [정밀 처방 역할 추천]
    - 권장 역할: roles/aiplatform.user
    - 역할 상세: Gemini API 호출 및 버텍스 AI(Vertex AI) 파운데이션 모델 추론 권한
  [즉시 조치 가능한 원클릭 gcloud 해결 명령어]
    gcloud projects add-iam-policy-binding "my-prod-project" \
      --member="user:backend-developer@company.com" \
      --role="roles/aiplatform.user"
------------------------------------------------------------------------
```

---
## 7. 리소스 정리 (Teardown) 안내

본 도구는 순수 감사 로그 조회 도구이며 클라우드 상에 영구 자원을 생성하지 않으므로 별도의 자원 정리 작업이 필요하지 않다.
