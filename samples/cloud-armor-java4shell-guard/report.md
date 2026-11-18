<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
-->

> [!IMPORTANT]
> **구글 (Google LLC) 참조용 샘플 고지 사항**:
> 본 리포트는 Google LLC 참조용 샘플 진단기의 출력 결과이며, 프로덕션 환경 적용 전 반드시 Preview 모드 및 워크로드 테스트를 거쳐야 한다.

# Cloud Armor 기반 Java4Shell (CVE-2026-114938) 노출 및 WAF 진단 리포트

- **점검 일시**: 2026-11-18 07:07:45 UTC
- **점검 모드**: `DRY-RUN (모의 시뮬레이션)`
- **대상 프로젝트**: `sample-project-id`

---

## 1. AVX-512 VBMI 워크로드 노출 현황 (GCP-2026-082)

| 리소스 유형 | 워크로드 이름 | 머신 타입 | 노출 위험 | 상세 진단 내용 |
| :--- | :--- | :--- | :---: | :--- |
| GKE NodePool | `app-cluster-prod / java-pool-1` | `c3-standard-8` | `WARN` | AVX-512 VBMI 지원 시리즈(C3), JDK_JAVA_OPTIONS 미확인 |
| Compute Engine VM | `legacy-api-vm-01` | `n2-standard-4` | `WARN` | AVX-512 VBMI 지원 시리즈(N2), JVM 플래그 점검 필요 |
| Cloud Run (2nd Gen) | `payment-gateway-svc` | `managed-gen2` | `PASS` | 플랫폼 관리형 Java 런타임 AVX-512 마스킹 보호 대상 (커스텀 컨테이너 제외) |

---

## 2. Cloud Armor Security Policy 및 CEL 함정 감사 결과

### 정책: `prod-java-waf-policy` (연결된 Backend Service: `prod-external-alb-bs`)

| 점검 항목 | 대상 | 상태 | 진단 상세 |
| :--- | :--- | :---: | :--- |
| 본문 검사 상한 | `request-body-inspection-size (8KB)` | `WARN` | 본문 검사 상한이 64KB 미만이어서 8KB~64KB 구간 우회 위험이 있다. |
| CEL 우회 함정 | `Priority 940 (Enforce)` | `FAIL` | base64Decode() == '' 패턴은 앞 64B 부분 디코딩 시 우회되므로 contains('=') && matches(...)로 교체가 필요하다. |
| CEL 오탐 함정 | `Priority 1000 (Preview)` | `FAIL` | Cookie/표준 Base64에 .urlDecode() 사용 시 '+'가 공백으로 치환되어 오탐이 발생한다. |
| 헤더/쿼리 방어 (GA) | `Rule 1 (Authorization, Cookie, Query)` | `PASS` | Authorization, Cookie, Query 대상 비정상 Base64 패딩 차단 규칙이 활성화되어 있다. |
| 본문 방어 (Public Preview) | `Rule 2a/2b (Raw/JSON/XML vs Form 분리)` | `WARN` | request.body 기반 Rule 2a/2b 분리 적용 여부를 확인하고 정책 선연결 후 추가해야 한다. |

---

## 3. 단계별 권장 조치 및 가상 패치 CLI 처방

### 3.1 Cloud Armor 배포 순서 및 Custom CEL Virtual Patching
`request.body` / `request.params` (Public Preview) 규칙을 추가하기 전에 **반드시 Security Policy를 Backend Service에 먼저 연결**해야 `undeclared reference to 'request'` 오류를 피할 수 있다.

```bash
# 1) 신규 테스트 정책 생성 및 64KB 본문 검사 상한 설정 (4대 표준 라벨 적용 권장)
gcloud compute security-policies create java4shell-waf-policy --project=sample-project-id
gcloud beta compute security-policies update java4shell-waf-policy --project=sample-project-id --request-body-inspection-size=64KB

# 2) Backend Service에 정책 선연결 (request.body 규칙 추가 전 필수)
gcloud compute backend-services update <BACKEND_SERVICE_NAME> --project=sample-project-id --security-policy=java4shell-waf-policy --global

# 3) Rule 1 (GA): Authorization, Cookie, Query 일괄 검사 (--preview 선배포)
gcloud compute security-policies rules create 1000 --project=sample-project-id \
  --security-policy=java4shell-waf-policy \
  --description="Mitigate CVE-2026-114938 malformed Base64 in Auth, Cookie, Query" \
  --expression="(has(request.headers['authorization']) && request.headers['authorization'].matches('(?:^|[^A-Za-z0-9+/_-])(?:[A-Za-z0-9+/_-]{4}){8,}[A-Za-z0-9+/_=-]{0,2}=(?:$|[^A-Za-z0-9+/_=-])')) || (has(request.headers['cookie']) && request.headers['cookie'].matches('(?:^|[^A-Za-z0-9+/_-])(?:[A-Za-z0-9+/_-]{64})+[A-Za-z0-9+/_=-]{0,2}(?:=|%3[Dd])(?:$|[^A-Za-z0-9+/_=-])')) || request.query.urlDecode().matches('(?:^|[^A-Za-z0-9+/_-])(?:[A-Za-z0-9+/_-]{64})+[A-Za-z0-9+/_=-]{0,2}=(?:$|[^A-Za-z0-9+/_=-])')" \
  --action=deny-403 --preview

# 4) Rule 2a (Public Preview): Raw/JSON/XML 본문 검사 (Form 제외)
gcloud compute security-policies rules create 1010 --project=sample-project-id \
  --security-policy=java4shell-waf-policy \
  --description="Mitigate CVE-2026-114938 malformed Base64 in raw/JSON/XML body" \
  --expression="(!has(request.headers['content-type']) || !request.headers['content-type'].lower().startsWith('application/x-www-form-urlencoded')) && size(request.body) > 64 && request.body.matches('(?:^|[^A-Za-z0-9+/_-])(?:[A-Za-z0-9+/_-]{64})+[A-Za-z0-9+/_=-]{0,2}(?:=|%3[Dd])(?:$|[^A-Za-z0-9+/_=-])')" \
  --action=deny-403 --preview

# 5) Rule 2b (Public Preview): Form POST 본문 검사
gcloud compute security-policies rules create 1015 --project=sample-project-id \
  --security-policy=java4shell-waf-policy \
  --description="Mitigate CVE-2026-114938 malformed Base64 in form-urlencoded body" \
  --expression="has(request.headers['content-type']) && request.headers['content-type'].lower().startsWith('application/x-www-form-urlencoded') && size(request.body) > 64 && request.body.urlDecode().matches('(?:^|[^A-Za-z0-9+/_-])(?:[A-Za-z0-9+/_-]{64})+[A-Za-z0-9+/_=-]{0,2}=(?:$|[^A-Za-z0-9+/_=-])')" \
  --action=deny-403 --preview

# 6) 테스트용 리소스 생성 시 4대 표준 라벨 적용 예시: --labels=managed-by=google-cloud-0-to-1,scenario=cloud-armor-java4shell-guard,env=sample,created-by=customer-engineer
```

### 3.2 워크로드 근본 조치 (GCP-2026-082)
Cloud Armor WAF는 압축 본문, 이중 인코딩, 64KB 초과 영역에 한계가 있으므로 백엔드에 아래 JVM 플래그를 병행 적용한 뒤 패치된 OpenJDK로 업그레이드한다.

```bash
JDK_JAVA_OPTIONS="-XX:+IgnoreUnrecognizedVMOptions -XX:UseAVX=2"
```

---

## 4. 참고 콘솔 및 공식 문서
- Cloud Armor Security Policies 콘솔 ( https://console.cloud.google.com/net-security/securitypolicies/list )
- Google Cloud Security Bulletins GCP-2026-082 ( https://docs.cloud.google.com/support/bulletins#gcp-2026-082 )
- Google Cloud Armor Custom Rules Language Reference ( https://cloud.google.com/armor/docs/create-security-policy-rules )
