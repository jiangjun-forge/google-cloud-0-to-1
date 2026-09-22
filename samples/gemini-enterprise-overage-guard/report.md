# Gemini Enterprise 추가 과금 방어 및 비인가 API 호출 차단 진단 리포트

- **진단 일시**: (실행 결과 자동 생성)
- **대상 프로젝트**: `sample-project-id`
- **Cloud Billing 계정**: `012345-6789AB-CDEF01`
- **진단 모드**: `모의 실행 (Dry-run)`

---

## 1. 비의도적 유료 과금 방지 4대 기술적 가드레일 진단

| 통제 영역 | 상태 | 통제 항목 | 세부 상태 및 조치 가이드 |
| :--- | :--- | :--- | :--- |
| **Gemini Enterprise Overage** | `[PASS]` | 관리 콘솔 Overage 차단 (Toggle OFF) | Standard 에디션 Overage가 기본 OFF로 유지되어 일일 쿼터 초과 시 추가 과금 없이 당일 사용만 제한된다.<br>**처방**: `Gemini Enterprise 관리 콘솔 > 구독/라이선스 > Overage Settings에서 Toggle OFF 상태를 유지한다.` |
| **Google AI Studio 차단** | `[FAIL]` | API 키 생성 차단 조직 정책 (constraints/gcp.restrictServiceUsage) | apikeys.googleapis.com 제한 조직 정책이 미적용되어, 일반 사용자가 AI Studio에서 회사 결제 계정 프로젝트를 선택해 API 키를 발급할 수 있는 위험이 존재한다.<br>**처방**: `gcloud resource-manager org-policies enable-enforce constraints/gcp.restrictServiceUsage --project=sample-project-id (apikeys.googleapis.com 차단)` |
| **Google AI Studio 백엔드** | `[WARN]` | Generative Language API 비활성화 및 제한 | generativelanguage.googleapis.com 활성화 상태가 모니터링되지 않고 있어, AI Studio 유료 호출 경로가 열려 있을 수 있다.<br>**처방**: `gcloud services disable generativelanguage.googleapis.com --project=sample-project-id --force` |
| **계열사 위임 관리자 거버넌스** | `[WARN]` | 결제 계정 관리자/사용자(Billing Admin/User) 분리 | 계열사 IT 관리자 계정에 roles/billing.user 권한이 부여되어 있어 임의 프로젝트에 결제 계정을 연결할 위험이 있다.<br>**처방**: `계열사 관리자에게는 roles/billing.user 대신 OU 맞춤 관리자 역할 및 사전 프로비저닝된 프로젝트 내 roles/viewer 권한만 선별 부여한다.` |

---

## 2. 에디션별 오버리지 및 일일 쿼터 현황

| 에디션 | 오버리지 빌링 설정 | 일일 쿼터 소진율 | 진단 판정 | 분석 내용 |
| :--- | :--- | :--- | :--- | :--- |
| **Gemini Enterprise Plus** | ON (활성화) | 78.5% | `[OVERAGE_RUNAWAY_RISK]` | 오버리지 빌링이 활성화되어 있어 쿼터 소진 후에도 업무는 지속되나, Spend Cap 부재 시 통제되지 않은 초과 토큰 비용이 발생할 수 있다. |
| **Gemini Enterprise Standard** | OFF (비활성화) | 94.2% | `[THROTTLING_OUTAGE_RISK]` | 오버리지 빌링이 비활성화(OFF) 상태이며 현재 일일 쿼터의 94%가 소진되었다. 100% 도달 시 당일 자정까지 전사 프롬프트 요청이 차단된다. |

---

## 3. 실무자 즉각 조치 가이드 및 코드 처방전

### 1단계: Gemini Enterprise 관리 콘솔 내 Overage 차단 (필수)
- Gemini Enterprise Admin Console > 구독 및 라이선스 > Overage Settings > Toggle OFF 유지
- 결과: 일일 쿼터를 모두 소진한 경우 당일 추가 질의만 일시 제한되며, 추가 요금이 청구되지 않는다.

### 2단계: 조직 정책 기반 Google AI Studio API 키 발급 차단 (필수)
```bash
gcloud resource-manager org-policies enable-enforce constraints/gcp.restrictServiceUsage --project=sample-project-id
```

### 3단계: Generative Language API 비활성화 (권장)
```bash
gcloud services disable generativelanguage.googleapis.com --project=sample-project-id --force
```

### 4단계: 계열사 IT 관리자 결제 권한(Billing RBAC) 회수 및 최소 권한 적용
- 최고 관리자(Super Admin) 권한 부여를 금지하고, 계열사 조직 단위(OU)에 한정된 맞춤 역할을 생성하여 사용자/그룹 관리 권한만 위임한다.
- Google Cloud 콘솔에서 `roles/billing.admin` 및 `roles/billing.user` 권한을 계열사 관리자에게 부여하지 않는다.
