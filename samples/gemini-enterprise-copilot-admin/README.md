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

# Gemini Enterprise 어드민 코파일럿 (gemini-enterprise-copilot-admin)

사내 IT 어드민 및 클라우드 인프라 팀이 제미나이 엔터프라이즈 앱(Gemini Enterprise app) 운영 중 직면하는 7대 핵심 관리 과제(도메인 충돌, 외부 마켓플레이스 차단 거버넌스, 유휴 라이선스 회수, Overage 과금 방어, 사내망 FQDN 허용, 수백 개 에이전트 관리 헬 감사, 30초 BigQuery 감사 로그 싱크 및 콘솔 길잡이)를 대화형으로 신속 진단하고 자율 해결할 수 있도록 지원하는 사내 어드민 전담 코파일럿 솔루션이다. (As of 2026-10-17)

**Audience**: `#Architect`, `#FinOps`, `#SecOps`  
**Concern**: `#Billing`, `#Compliance`, `#Security`  
**Service**: `#AgentPlatform`, `#BigQuery`, `#CloudMonitoring`  

---

## 1. 문제 증상 및 도입 배경 체크리스트

사내 엔터프라이즈 환경에서 Gemini Enterprise 도입 및 운영 중 다음과 같은 관리 이슈가 발생하고 있다면 본 솔루션 도입이 필요하다:

- [ ] **GCP 콘솔 메뉴 미아**: Workspace나 온프레미스 어드민이 GCP 콘솔의 복잡한 GE Admin 메뉴 트리를 찾지 못해 설정 변경에 어려움을 겪는 경우
- [ ] **에이전트 수백 개 난립(Agent Sprawl) 관리 헬**: 임직원들이 생성한 수백 개 에이전트 중 60일 이상 호출 0건인 좀비 에이전트나 토큰 과소비 에이전트를 파악하지 못하는 경우
- [ ] **감사 로그 BigQuery 연동 부재**: Cloud Logging에 쌓이는 데이터 액세스 로그를 BigQuery로 자동 적재하는 로그 싱크(Log Sink) 설정 방법을 모르는 경우
- [ ] **도메인 선점 오류**: 사내 도메인이 타 계정이나 기존 조직에 선점되어 테넌트 프로비저닝이 중단된 경우
- [ ] **외부 마켓플레이스 에이전트 차단 요구**: 보안 규정상 미승인 외부 에이전트 사용을 금지하고 사내 승인 에이전트만 전사 갤러리에 노출시켜야 하는 경우
- [ ] **유휴 라이선스 비용 누수**: 전사 배포된 고가 라이선스 중 30일 이상 미사용 중인 임직원 라이선스를 식별하여 회수해야 하는 경우
- [ ] **Overage 추가 과금 및 섀도우 키 우려**: 일일 풀링 쿼터 초과에 따른 과금 누수나 임직원의 AI Studio 유료 API 키 발급을 통제해야 하는 경우
- [ ] **폐쇄망 프록시 와일드카드 차단**: 사내 보안망 정책상 와일드카드 도메인 허용이 불가하여 15대 코어 FQDN의 정확한 목록이 필요한 경우

---

## 2. 처리 아키텍처 (Activity Diagram)

본 도구는 어드민 관리자의 질의나 5대 관리 칩을 수신하여 거버넌스 정책 매니페스트 및 조치 스크립트를 도출하고, Gemini Enterprise app 정상 운영을 지원하는 3단계 파이프라인으로 동작한다.

```mermaid
flowchart LR
    Admin["IT / 클라우드 어드민"] -->|"5대 관리 칩 선택"| Engine["어드민 코파일럿 엔진<br/>(diagnose.py)"]
    Engine -->|"거버넌스 및 인프라 정책 진단"| Spec["조치 스크립트 및 매니페스트<br/>(remediation.sh)"]
    Spec -->|"정상 복구 및 최적화"| GEApp["Gemini Enterprise App<br/>(adc-retail-ge-app)"]
```

---

## 3. 필요 IAM 권한 및 역할

본 도구를 실행하고 어드민 정책을 점검 및 복구하기 위해 필요한 최소 IAM 역할은 다음과 같다:

| 역할 (Role) | 권한 및 용도 |
| :--- | :--- |
| `roles/discoveryengine.admin` | Discovery Engine 마켓플레이스 및 에이전트 공유 거버넌스 설정 |
| `roles/resourcemanager.organizationAdmin` | 조직 정책(Org Policy) 및 도메인 바인딩 점검 |
| `roles/billing.admin` (또는 `viewer`) | Overage 과금 방어 및 결제 계정 사용자 RBAC 감사 |

---

## 4. 원클릭 실행법 및 사용 가이드

### 4.1. 가상 실행 모드 (--dry-run)
실제 GCP 호출 없이 모의 환경에서 5대 어드민 관리 매니페스트와 조치 스크립트를 안전하게 검증한다:
```bash
python diagnose.py --dry-run
```

### 4.2. 5대 어드민 관리 칩 지정 실행
해결하려는 관리 과제를 번호로 지정하여 즉시 조치 가이드를 도출한다:
```bash
# 1번 도메인 선점 충돌 및 Cloud Identity 온보딩
python diagnose.py --dry-run --chip 1

# 2번 외부 마켓플레이스 차단 및 사내 승인 에이전트 통제
python diagnose.py --dry-run --chip 2

# 3번 부서별 라이선스 채택률 분석 및 30일 유휴 라이선스 회수
python diagnose.py --dry-run --chip 3

# 4번 Overage 추가 과금 방어 및 AI Studio 키 차단
python diagnose.py --dry-run --chip 4

# 5번 사내망 프록시 허용용 Exact 15대 코어 FQDN 진단
python diagnose.py --dry-run --chip 5

# 6번 수백 개 에이전트 전수 감사 및 좀비 에이전트 식별 (BigQuery 3대 쿼리 팩)
python diagnose.py --dry-run --chip 6

# 7번 Cloud Logging to BigQuery 30초 원클릭 감사 로그 싱크 구축 & GCP 콘솔 길잡이
python diagnose.py --dry-run --chip 7

# 사용자 맞춤형 어드민 문의 입력
python diagnose.py --dry-run --prompt "임직원 퇴사 시 에이전트 소유권 이전 절차"
```

### 4.3. 대화형 번호 선택기 가동 (--interactive)
터미널 대화형 환경에서 7대 관리 과제를 확인하고 번호로 선택하여 실행한다:
```bash
python diagnose.py --interactive
```

---

## 5. 콘솔 링크 조치 가이드

- **Gemini Enterprise 에이전트 목록 직결 콘솔**: ( https://console.cloud.google.com/gen-app-builder/engines )
- **Cloud Logging 로그 라우터 콘솔**: ( https://console.cloud.google.com/logs/router )
- **BigQuery 감사 로그 분석 콘솔**: ( https://console.cloud.google.com/bigquery )
- **Google Admin 관리 콘솔**: ( https://admin.google.com/ )
- **Google Cloud 결제(Billing) 콘솔**: ( https://console.cloud.google.com/billing )
- **Cloud DNS 및 도메인 콘솔**: ( https://console.cloud.google.com/net-services/dns/zones )

---

## 6. 자원 정리 안내 (Teardown)

본 진단 및 모의 실행 완료 후 테스트용 정책이나 임시 리소스를 정리하려면 아래 가이드를 준수한다:

```bash
# 1. 임시 DNS TXT 검증 레코드 정리 (DNS 관리 포털에서 삭제)
# 2. 테스트용 서비스 계정 정리
gcloud iam service-accounts delete "ge-admin-sa@${PROJECT_ID}.iam.gserviceaccount.com" --project="${PROJECT_ID}" --quiet
```
