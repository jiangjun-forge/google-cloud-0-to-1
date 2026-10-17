# 진단 및 분석 리포트: gemini-enterprise-agent-resolver

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-ge-project` <---> `sample-agent-project`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

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
Reasoning Engine 리소스 식별자 규격          PASS         유효한 Reasoning Engine ID 형식 확인 완료 (8492049182740192841)
VPC Service Controls 보안 경계           PASS         VPC-SC 경계 간 통신 제한 없음
=========================================================================================================

[발견된 Cross-Project/Org 연동 결함 및 즉시 복구 처방]

* [심각] Agent Engine IAM 권한 바인딩
  - 원인: 에이전트 프로젝트(sample-agent-project)에 GE 서비스 에이전트(service-104928374921@gcp-sa-discoveryengine.iam.gserviceaccount.com)의 'roles/aiplatform.user' 권한이 없음
  - 처방: gcloud projects add-iam-policy-binding sample-agent-project --member="serviceAccount:service-104928374921@gcp-sa-discoveryengine.iam.gserviceaccount.com" --role="roles/aiplatform.user"

* [심각] 도메인 제한 공유 조직 정책 (Domain Restricted Sharing)
  - 원인: 서로 다른 조직 간 연동 환경에서 'constraints/iam.allowedPolicyMemberDomains' 정책이 활성화되어 타 조직(organizations/987654321098) 소속 계정 또는 서비스 에이전트의 IAM 바인딩이 차단됨
  - 처방: 조직 관리자 콘솔에서 에이전트 프로젝트(sample-agent-project)의 조직 정책 예외를 설정하거나, 고객 도메인 허용 ID 목록에 상대 조직의 디렉터리 고객 ID(Customer ID)를 추가한다: gcloud resource-manager org-policies allow constraints/iam.allowedPolicyMemberDomains [CUSTOMER_ID] --project=sample-agent-project
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```

---

## 3. 실무자 즉각 조치 가이드 및 처방전

### 가. 사내 거버넌스 4대 필수 표준 라벨링
에이전트 인프라 및 연동 리소스 생성 시 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-agent-resolver`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

### 나. 에이전트 연동 복구 및 예외 처리 명령어
```bash
# 1. Agent Engine 프로젝트에 GE 서비스 에이전트 권한 부여
gcloud projects add-iam-policy-binding sample-agent-project \
    --member="serviceAccount:service-[GE_PROJECT_NUM]@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# 2. 도메인 제한 공유 조직 정책 예외 적용 (Cross-Org 시)
gcloud resource-manager org-policies allow constraints/iam.allowedPolicyMemberDomains [CUSTOMER_ID] \
    --project=sample-agent-project
```

### 다. 공식 문서 및 콘솔 경로
- Google Cloud Console Vertex AI Reasoning Engines ( https://console.cloud.google.com/gen-app-builder/engines?project=sample-agent-project )
- Google Cloud Console IAM & Admin ( https://console.cloud.google.com/iam-admin/iam?project=sample-agent-project )
- Google Cloud Console Organization Policies ( https://console.cloud.google.com/iam-admin/orgpolicies?project=sample-agent-project )
- Agent Platform Agent Engine 개요 ( https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview )
- 도메인별 ID 제한 조직 정책 안내 ( https://cloud.google.com/resource-manager/docs/organization-policy/restricting-domains )
- Gemini Enterprise 제품 개요 ( https://docs.cloud.google.com/gemini/enterprise/docs )
