# 진단 및 분석 리포트: korea-fsi-regulatory-perimeter-guard

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
========================================================================================
 혁신 금융 서비스(FSI) 규제 준수 보안 경계 진단 도구
 대상 프로젝트: example-fsi-corp | 점검 리전: asia-northeast3 | 실행 모드: 가상 진단 (Dry-Run)
========================================================================================

[*] 가상 모의 감사 데이터를 로드하고 점검 항목을 시뮬레이션한다...

========================================================================================
 혁신 금융 서비스(FSI) 규제 준수 보안 경계 진단 리포트
 대상 프로젝트: example-fsi-corp | 점검 리전: asia-northeast3 | 실행 모드: 가상 진단 (Dry-Run)
========================================================================================

진단 요약: 총 9개 규제 항목 중 충족 4건, 주의 2건, 미달 3건
----------------------------------------------------------------------------------------
ID           | 분류             | 상태     | 진단 항목 및 현황
----------------------------------------------------------------------------------------
FR-01        | 논리적 망 분리       | [PASS] | VPC-SC 보안 경계 내 Vertex AI 보호 여부 (감독규정 제15조)
  - 현재 상태: aiplatform.googleapis.com 이 서비스 경계(accessPolicies/123456/servicePerimeters/fsi_perimeter)에 등록됨

FR-02        | 논리적 망 분리       | [WARN] | VPC-SC 내부 실시간 웹 검색(Web Search Grounding) 격리 여부
  - 현재 상태: VPC-SC 내부에서 web_search_tool 호출 시 egress 차단 위험 존재
  - 규제 요건: 외부 인터넷 직접 통신 차단 원칙에 따라 웹 검색이 필요한 워크로드는 DMZ 전용 프로젝트로 분리 후 비동기 벡터 DB 적재 아키텍처 적용 필요
  - 조치 권고: 외부 검색 연동 워크로드를 VPC-SC 외부 DMZ 프로젝트로 이관하고 내부 인스턴스로의 비동기 적재 파이프라인 구성 권장

FR-03        | 데이터 보호         | [FAIL] | Cloud Storage 불변 보존(Retention Policy / Bucket Lock) 5년 충족 여부 (법 제22조)
  - 현재 상태: 지정 버킷에 보존 정책 미설정 (retention_period: 0s)
  - 규제 요건: 전자금융거래법 제22조 및 전자금융감독규정 제63조에 따라 감사 로그 및 AI 입출력 저장 버킷은 최소 5년(157,680,000초) 보존 및 잠금(Bucket Lock) 필수
  - 조치 권고: gcloud storage buckets update gs://example-fsi-corp-audit-logs --retention-period=157680000s && gcloud storage buckets lock gs://example-fsi-corp-audit-logs

FR-04        | 데이터 보호         | [PASS] | 고객 관리 암호화 키(CMEK) 전면 적용 여부 (감독규정 제14조)
  - 현재 상태: Cloud KMS 키(projects/example-fsi-corp/locations/asia-northeast3/keyRings/fsi-ring/cryptoKeys/cmek-key) 정상 바인딩 확인

FR-05        | 감사 추적          | [FAIL] | 데이터 접근 감사 로그(DATA_READ, DATA_WRITE) 활성화 여부 (법 제22조)
  - 현재 상태: aiplatform.googleapis.com 데이터 접근 로그 미설정 (ADMIN_READ 만 활성화됨)
  - 규제 요건: 전자금융거래법 제22조 및 전자금융감독규정 제14조에 따라 금융 거래 및 AI 추론 데이터 조회를 위해 DATA_READ, DATA_WRITE 로그 감사 필수 수집
  - 조치 권고: gcloud projects get-iam-policy $PROJECT_ID 후 auditConfigs 에 aiplatform.googleapis.com 및 storage.googleapis.com 추가

FR-06        | AI 모델 거버넌스     | [PASS] | Model Armor 실시간 프롬프트 인젝션 및 탈옥 방어 가드레일 (특례 부가 조건)
  - 현재 상태: Model Armor 템플릿(fsi-prompt-guard) 활성화 및 프롬프트 인젝션 탐지 필터 적용됨

FR-07        | AI 모델 거버넌스     | [WARN] | Sensitive Data Protection (SDP) 개인 신용 정보 가명 처리 템플릿 (신용정보법 제20조의2)
  - 현재 상태: 기본 민감 정보 템플릿 존재하나 주민등록번호(RRN) 및 계좌번호 특화 커스텀 InfoType 미등록
  - 규제 요건: 신용정보법 제20조의2 및 금융보안원 가이드라인에 따라 원본 개인 신용 정보 직접 입력 금지 및 주민등록번호, 계좌번호 특화 가명 처리 템플릿 등록 필수
  - 조치 권고: gcloud dlp inspect-templates create --display-name='fsi-rrn-filter' --info-types=KOREA_RESIDENT_REGISTRATION_NUMBER

FR-08        | 접근 통제          | [FAIL] | 서비스 계정 키(SA Key) 발급 차단 및 WIF 강제 (감독규정 제13조)
  - 현재 상태: 조직 정책 iam.disableServiceAccountKeyCreation 미적용 (로컬 JSON 키 발급 가능 위험)
  - 규제 요건: 전자금융감독규정 제13조에 따라 단말기 및 전산 시스템 접근 자격 증명의 유출을 방지하기 위해 정적 서비스 계정 키 생성을 차단하고 Workload Identity Federation(WIF) 필수 적용
  - 조치 권고: gcloud resource-manager org-policies enable-enforce constraints/iam.disableServiceAccountKeyCreation --project=example-fsi-corp

FR-09        | 전송 보안          | [PASS] | 전송 구간 고강도 암호화(TLS 1.2+ 강제) 통제 (감독규정 제14조)
  - 현재 상태: SSL 정책(fsi-tls-policy)을 통해 TLS 1.0, 1.1 차단 및 TLS 1.2+ 고강도 암호화 스위트 적용 확인

========================================================================================
종합 평가 및 감사 준비 가이드:
본 진단 결과 규제 필수 요건에 미달하는 항목이 존재한다.
금융감독원 현장 실사 및 금융보안원 보안성 심의 전 미달(FAIL) 항목을 우선 조치해야 한다.
특히 스토리지 5년 불변 보존(Bucket Lock) 및 Vertex AI 감사 로깅은 필수 소명 대상이다.
========================================================================================
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
