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

# 제미나이 엔터프라이즈(Gemini Enterprise) 크로스 조직 커스텀 에이전트 연동 및 조직 정책 진단기 (`gemini-enterprise-agent-resolver`)

Gemini Enterprise 웹 앱 프로젝트와 타 프로젝트 또는 타 조직의 커스텀 에이전트(Agent Engine) 연동 시 발생하는 도메인 제한 공유 조직 정책(Domain Restricted Sharing) 차단, 서비스 에이전트 IAM 권한 부재, VPC-SC 경계 위반을 1분 만에 자동 진단하고 복구 명령어를 처방하는 도구다. (As of 2026-10-17)

---

## 1. 발생 증상 및 진단 대상 체크리스트

사내 또는 고객사 환경에서 아래 증상이 발생한다면 즉시 진단 대상이다:
- [ ] 사내 엔터프라이즈 환경에서 Gemini Enterprise 웹 앱(프로젝트 A, 조직 A)과 계열사/사업부별 커스텀 에이전트(Agent Engine, 프로젝트 B, 조직 B)가 서로 다른 프로젝트에 분리되어 있어 연동 시 403 Forbidden 오류가 발생한다.
- [ ] 상대 조직의 서비스 에이전트에 권한을 부여하려 할 때, 상위 조직 정책 `constraints/iam.allowedPolicyMemberDomains`에 의해 외부 도메인 계정 바인딩이 차단된다.
- [ ] Gemini Enterprise Agent Registry에 커스텀 에이전트 등록 시 필수 서비스 에이전트(`service-[NUM]@gcp-sa-discoveryengine.iam.gserviceaccount.com`)에 `roles/aiplatform.user` 역할이 부여되지 않아 에이전트 호출이 실패한다.
- [ ] VPC Service Controls(VPC-SC) 서비스 경계가 설정된 환경에서 두 프로젝트 간 API 호출이 차단되어 에이전트 목록 검색 및 추론이 불가능하다.


### 1.1 도구의 본질 및 비즈니스 해결 과제 (What & Why)
- **대상 사용자 (Target)**: Gemini Enterprise 어드민, 클라우드 IAM 보안팀, 멀티 프로젝트 아키텍트 및 거버넌스 리드
- **해결하는 핵심 문제 (Core Pain Points)**:
  1. 타 프로젝트나 타 조직에 호스팅된 커스텀 에이전트(Agent Engine)를 Gemini Enterprise app에 연동할 때 원인 불명의 권한 오류가 발생하는 문제
  2. 조직 정책 `constraints/iam.allowedPolicyMemberDomains`(DRS)에 의해 교차 프로젝트 서비스 계정 권한 부여가 차단되는 보안 충돌
  3. VPC Service Controls(VPC-SC) 보안 경계로 인해 프로젝트 간 Agent Engine API 호출이 차단되어 에이전트가 응답하지 않는 장애
- **본 솔루션의 해결 방식 (Solution)**:
  - Gemini Enterprise 테넌트 프로젝트와 대상 에이전트 프로젝트 간의 교차 IAM 역할(`roles/aiplatform.user`), 도메인 제한 공유(DRS) 조직 정책 상태 및 VPC-SC 인그레스 규칙을 종합 진단하여 즉시 해결 가능한 복구 스크립트를 제공한다.

### 1.2 최종 산출물 3종 세트 미리보기 (Deliverables & Visual Preview)
본 도구를 실행(`python diagnose.py`)하면 다음 3가지 구체적인 엔터프라이즈 자산이 생성된다:

| 산출물 구분 | 산출물 형태 및 명칭 | 주요 포함 내용 및 실무 활용 방안 |
| :--- | :--- | :--- |
| **① 터미널 콘솔 요약** | Visual CLI Table | 양방향 IAM 권한 충족 여부, DRS 정책 제한 상태, VPC-SC 격리 검증 및 연동 상태 판정 표 |
| **② 정규 진단 보고서** | 마크다운 파일 (`report.md`) | 크로스 프로젝트 연동 진단서, 교차 권한 복구 gcloud 명령어, DRS 예외 태그 정책 및 VPC-SC 인그레스 규칙 명세 |
| **③ 후속 조치 및 배포 자산** | Actionable Asset Specs | • **교차 프로젝트 IAM 바인딩 명령어**: GE 서비스 에이전트에 에이전트 호출 권한을 부여하는 명령<br/>• **DRS 조직 정책 예외 바인딩 스크립트**: 승인된 프로젝트 간 권한 부여를 허용하는 태그 정책<br/>• **VPC-SC 인그레스/이그레스 허용 룰 JSON**: 보안 경계를 통과하여 에이전트를 호출하는 인그레스 규칙 |

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
Gemini Enterprise Cross-Project 에이전트 연동 진단 시작 (GE: sample-ge-project, Agent: sample-agent-project)
--> 가상 실행 모드 (--dry-run) 활성화: Cross-Org 시뮬레이션 데이터를 분석한다.
=========================================================================================================
Gemini Enterprise 앱 프로젝트: sample-ge-project <---> 커스텀 에이전트 프로젝트: sample-agent-project
=========================================================================================================
점검 항목                                상태           진단 내용
---------------------------------------------------------------------------------------------------------
Agent Engine IAM 권한 바인딩              CRITICAL     에이전트 프로젝트(sample-agent-project)에 GE 서비스 에이전트(service-104928374921@gcp-sa-discoveryengine.iam.gserviceaccount.com)의 'roles/aiplatform.user' 권한이 없음
도메인 제한 공유 조직 정책 (Domain Restricted Sharing) CRITICAL     서로 다른 조직 간 연동 환경에서 'constraints/iam.allowedPolicyMemberDomains' 정책이 활성화되어 타 조직(organizations/987654321098) 소속 계정 또는 서비스 에이전트의 IAM 바인딩이 차단됨
Agent Engine 리소스 식별자 규격              PASS         유효한 Agent Engine ID 형식 확인 완료 (8492049182740192841)
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

본 도구는 Gemini Enterprise 웹 앱(Project A)과 타 프로젝트/조직의 커스텀 에이전트(Project B) 간 크로스 연동 토폴로지를 4계층으로 분석하고 차단 요소를 실시간 진단한다:

```mermaid
flowchart TD
    subgraph Layer1["1. 사용자 인터랙션 계층 (User Interaction)"]
        User["사내 임직원 / 인프라 관리자"] -->|"1. 커스텀 에이전트 호출 / CLI 진단"| GEApp["Gemini Enterprise app<br/>(웹 대화형 포털 /r/agents)"]
        CLI["진단 컨트롤러<br/>(diagnose.py)"]
    end

    subgraph Layer2["2. 보안 및 IAM 경계 (Security & IAM Boundary)"]
        OrgPol{"도메인 제한 공유 검사<br/>(iam.allowedPolicyMemberDomains)"}
        SA["GE 서비스 에이전트<br/>(service-PROJECT_NUM@gcp-sa-discoveryengine.iam)"]
        IAMCheck{"IAM 역할 바인딩<br/>(roles/aiplatform.user)"}
        VPCSC{"VPC-SC 서비스 경계 격리"}
    end

    subgraph Layer3["3. 호스팅 런타임 계층 (Hosting Runtime & Sandbox)"]
        RE["Agent Engine 런타임<br/>(Project B 관리형 gVisor 샌드박스)"]
    end

    subgraph Layer4["4. 대상 백엔드 서비스 계층 (Target Backend Services)"]
        DiscEng["Discovery Engine<br/>(사내 에이전트 카탈로그)"]
        CloudIAM["Cloud IAM & Resource Manager<br/>(조직 정책 및 접근 제어)"]
    end

    GEApp -->|"2. 에이전트 호출 트래픽 인입"| OrgPol
    OrgPol -->|"Cross-Org 허용 검증"| IAMCheck
    SA -.->|"신원 대행"| IAMCheck
    IAMCheck -->|"권한 검증 통과"| VPCSC
    VPCSC -->|"경계 인그레스 허용"| RE
    RE -->|"에이전트 응답 반환"| GEApp

    CLI -->|"정책/권한 비파괴 실시간 실사"| Layer2
    CLI -->|"런타임 식별자 규격 검증"| Layer3
    CLI -->|"메타데이터 상태 교차 분석"| Layer4

    classDef portal fill:#e8f0fe,stroke:#4285f4,stroke-width:2px;
    classDef security fill:#fef7e0,stroke:#f9ab00,stroke-width:2px;
    classDef runtime fill:#e6f4ea,stroke:#34a853,stroke-width:2px;
    classDef backend fill:#fce8e6,stroke:#ea4335,stroke-width:2px;

    class User,GEApp,CLI portal;
    class OrgPol,SA,IAMCheck,VPCSC security;
    class RE runtime;
    class DiscEng,CloudIAM backend;
```

---
## 4. 조치 가이드 및 권장 설정

### 가. 사내 거버넌스 4대 필수 표준 라벨링
에이전트 인프라 및 연동 리소스 생성 시 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-agent-resolver`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

### 나. 에이전트 연동 복구 및 예외 처리 명령어

#### 1. Agent Engine 프로젝트에 GE 서비스 에이전트 권한 부여
```bash
gcloud projects add-iam-policy-binding [AGENT_PROJECT_ID] \
    --member="serviceAccount:service-[GE_PROJECT_NUM]@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```

#### 2. 도메인 제한 공유 조직 정책 예외 적용 (Cross-Org 시)
```bash
gcloud resource-manager org-policies allow constraints/iam.allowedPolicyMemberDomains [CUSTOMER_ID] \
    --project=[AGENT_PROJECT_ID]
```

### 다. 공식 문서 및 콘솔 경로
- Google Cloud Console Agent Engine ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines )
- Google Cloud Console IAM & Admin ( https://console.cloud.google.com/iam-admin/iam )
- Google Cloud Console Organization Policies ( https://console.cloud.google.com/iam-admin/orgpolicies )
- Agent Engine 개요 ( https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview )
- 도메인별 ID 제한 조직 정책 안내 ( https://cloud.google.com/resource-manager/docs/organization-policy/restricting-domains )
- Gemini Enterprise 제품 개요 ( https://docs.cloud.google.com/gemini/enterprise/docs )

---
## 5. 사전 준비 사항 (필요 IAM 권한)

본 도구를 실행하려면 최소 아래의 IAM 권한이 필요하다:

- `roles/iam.securityReviewer` (IAM 정책 조회)
- `roles/orgpolicy.policyViewer` (조직 정책 제약 조건 조회)
- `roles/aiplatform.viewer` (Agent Engine 조회)

---

## 6. 기술적 배경 및 아키텍처 원리 (Deep Dive)

### 관련 상세 설계 및 요구 사항 명세
- [비즈니스 요구 사항 명세서 (BRD)](docs/BRD.md): 비즈니스 배경, 성공 지표 및 요구 사항(BR-01~) 명세
- [기술 상세 설계서 (TDD)](docs/TDD.md): 시스템 아키텍처, 기능(FR-01~) 및 비기능(NFR-01~) 설계 명세

---

## 7. 리소스 정리 (Teardown) 안내

본 도구는 읽기 전용 진단 스크립트이므로 자체적으로 리소스를 생성하지 않는다. 테스트 목적으로 부여한 크로스 프로젝트 IAM 권한은 다음 명령어로 회수할 수 있다:
```bash
gcloud projects remove-iam-policy-binding [AGENT_PROJECT_ID] \
    --member="serviceAccount:service-[GE_PROJECT_NUM]@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```
