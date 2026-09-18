# 진단 및 분석 리포트: swg-tenant-access-guard

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
============================================================================
 [SWG 관문 헤더 및 Context-Aware Access 인가 정합성 진단 리포트]
============================================================================
진단 대상 조직 ID      : 123456789012
사내 승인 허용 도메인  : example-corp.com
인가 관리자 보안 그룹  : gcp-authorized-users@example-corp.com
종합 진단 상태         : ACTION_REQUIRED
----------------------------------------------------------------------------

[항목별 세부 진단 결과]
1. [PASS] SWG_HEADER_DOMAIN_RESTRICTION
   설명: 개인 Gmail 및 비인가 도메인 접근이 차단되고 example-corp.com 계정만 통과하도록 헤더가 주입되고 있다.
   대상 헤더: X-GoogApps-Allowed-Domains
2. [WARNING] SWG_HEADER_TENANT_RESTRICTION
   설명: 사내 관문 프록시에서 Google Cloud 테넌트 제한 공식 헤더(X-Goog-Allowed-Resources)가 누락되어 있다. 사내 승인 계정을 이용해 외부 타사 GCP 조직 및 프로젝트로 우회 접근할 수 있는 위험이 존재한다.
   대상 헤더: X-Goog-Allowed-Resources
   필요 권장값: eyJyZXNvdXJjZXMiOlsib3JnYW5pemF0aW9ucy8xMjM0NTY3ODkwMTIiXSwib3B0aW9ucyI6InN0cmljdCJ9
3. [PASS] CONTEXT_AWARE_ACCESS_ENDPOINT
   설명: Endpoint Verification 및 관리 장치 신뢰 정책이 적용되어 사내 보안 인가 단말기만 콘솔 및 앱에 접근할 수 있다.
4. [PASS] CONTEXT_AWARE_ACCESS_GROUP
   설명: 인가된 사내 보안 그룹(gcp-authorized-users@example-corp.com)에 대해서만 Google Cloud 콘솔 및 생성형 AI 애플리케이션 접근이 바인딩되어 있다.
5. [NEEDS_REMEDIATION] FINANCIAL_COMPLIANCE_3_2
   설명: 단말기 인가 및 사용자 그룹 제어는 적합하나, 외부 테넌트 리소스 격리 헤더 미적용으로 인해 비인가 외부 조직 접근 통제 보완이 필요하다.

[사내 관문 프록시(SWG) 설정 가이드]
1. 개인 계정 및 외부 비인가 도메인 로그인 차단:
   - HTTP 요청 헤더: X-GoogApps-Allowed-Domains: example-corp.com
2. 사내 승인 계정의 외부 타사 GCP 조직 우회 접근 방지 (Tenant Restriction):
   - HTTP 요청 헤더: X-Goog-Allowed-Resources: eyJyZXNvdXJjZXMiOlsib3JnYW5pemF0aW9ucy8xMjM0NTY3ODkwMTIiXSwib3B0aW9ucyI6InN0cmljdCJ9
   - 주의: 과거 비공식 표기인 X-Goog-Allowed-Organizations 대신 공식 X-Goog-Allowed-Resources를 사용해야 한다.
   - 페이로드 원문: {"resources":["organizations/123456789012"],"options":"strict"}

[Context-Aware Access(CAA) 인가 정책 조치]
1. Access Context Manager 레벨 생성:
   gcloud access-context-manager levels create CorpDeviceOnly \
     --title="사내 인가 단말기 전용" \
     --basic-level-spec=device_policy.yaml
2. Google Cloud 콘솔 및 생성형 AI 앱 접근 바인딩:
   - 대상 그룹: gcp-authorized-users@example-corp.com
   - 적용 레벨: CorpDeviceOnly
============================================================================
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
