# 사내 관문 SWG 헤더 및 Context-Aware Access 인가 진단 리포트 (swg-tenant-access-guard)

- **진단 모드**: `모의 실행 (Dry-run)`
- **진단 대상 조직 ID**: `123456789012`
- **사내 승인 허용 도메인**: `example-corp.com`
- **인가 관리자 보안 그룹**: `gcp-authorized-users@example-corp.com`
- **종합 진단 상태**: `ACTION_REQUIRED`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 항목별 세부 진단 결과

| 번호 | 점검 카테고리 | 진단 상태 | 상세 내용 및 권장값 |
| :--- | :--- | :--- | :--- |
| 1 | `SWG_HEADER_DOMAIN_RESTRICTION` | PASS | 개인 Gmail 및 비인가 도메인 접근이 차단되고 example-corp.com 계정만 통과하도록 헤더가 주입되고 있다.<br/>대상 헤더: `X-GoogApps-Allowed-Domains` |
| 2 | `SWG_HEADER_TENANT_RESTRICTION` | **WARNING** | 사내 관문 프록시에서 Google Cloud 테넌트 제한 공식 헤더(X-Goog-Allowed-Resources)가 누락되어 있다. 사내 승인 계정을 이용해 외부 타사 GCP 조직 및 프로젝트로 우회 접근할 수 있는 위험이 존재한다.<br/>대상 헤더: `X-Goog-Allowed-Resources`<br/>필요 권장값: `eyJyZXNvdXJjZXMiOlsib3JnYW5pemF0aW9ucy8xMjM0NTY3ODkwMTIiXSwib3B0aW9ucyI6InN0cmljdCJ9` |
| 3 | `CONTEXT_AWARE_ACCESS_ENDPOINT` | PASS | Endpoint Verification 및 관리 장치 신뢰 정책이 적용되어 사내 보안 인가 단말기만 콘솔 및 앱에 접근할 수 있다. |
| 4 | `CONTEXT_AWARE_ACCESS_GROUP` | PASS | 인가된 사내 보안 그룹(gcp-authorized-users@example-corp.com)에 대해서만 Google Cloud 콘솔 및 생성형 AI 애플리케이션 접근이 바인딩되어 있다. |
| 5 | `FINANCIAL_COMPLIANCE_3_2` | **NEEDS_REMEDIATION** | 단말기 인가 및 사용자 그룹 제어는 적합하나, 외부 테넌트 리소스 격리 헤더 미적용으로 인해 비인가 외부 조직 접근 통제 보완이 필요하다. |

---

## 2. 사내 관문 프록시(SWG) 설정 가이드

### 1. 개인 계정 및 외부 비인가 도메인 로그인 차단
```http
X-GoogApps-Allowed-Domains: example-corp.com
```

### 2. 사내 승인 계정의 외부 타사 GCP 조직 우회 접근 방지 (Tenant Restriction)
```http
X-Goog-Allowed-Resources: eyJyZXNvdXJjZXMiOlsib3JnYW5pemF0aW9ucy8xMjM0NTY3ODkwMTIiXSwib3B0aW9ucyI6InN0cmljdCJ9
```
- **참고**: 공식 `X-Goog-Allowed-Resources` 헤더를 사용해야 한다.
- **페이로드 원문**: `{"resources":["organizations/123456789012"],"options":"strict"}`

---

## 3. Context-Aware Access(CAA) 인가 정책 조치

### 1. Access Context Manager 레벨 생성
```bash
gcloud access-context-manager levels create CorpDeviceOnly \
  --title="사내 인가 단말기 전용" \
  --basic-level-spec=device_policy.yaml
```

### 2. Google Cloud 콘솔 및 생성형 AI 앱 접근 바인딩
- **대상 그룹**: `gcp-authorized-users@example-corp.com`
- **적용 레벨**: `CorpDeviceOnly`

---

## 4. 사내 거버넌스 4대 필수 표준 라벨링

Access Context Manager 정책 및 인가 연계 인프라 자원 구성 시 다음 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `swg-tenant-access-guard`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 5. 콘솔 링크 조치 가이드 및 공식 레퍼런스

- **Access Context Manager 콘솔**: ( https://console.cloud.google.com/security/access-levels )
- **공식 문서 - Organization Restrictions 개요 및 헤더 규격**: ( https://docs.cloud.google.com/resource-manager/docs/organization-restrictions/overview )
- **공식 문서 - Google Workspace 개인 계정 로그인 차단 설정**: ( https://support.google.com/a/answer/1668854 )
- **공식 문서 - Context-Aware Access 개요 및 장치 정책**: ( https://docs.cloud.google.com/chrome-enterprise-premium/docs/overview )

---

## 6. 자원 정리 안내 (Teardown)
테스트 목적으로 생성한 Access Context Manager 임시 정책이나 모의 레벨을 삭제하려면 다음 명령을 수행한다:
```bash
gcloud access-context-manager levels delete CorpDeviceOnly --policy=<POLICY_ID> --quiet
```
