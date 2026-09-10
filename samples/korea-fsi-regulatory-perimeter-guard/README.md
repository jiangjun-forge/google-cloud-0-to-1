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

# 혁신 금융 서비스 규제 준수 보안 경계 진단 가이드

대한민국 금융위원회의 「금융분야 망분리 개선 로드맵」(1단계 생성형 AI 활용 특례) 및 전자금융감독규정에 따라, 퍼블릭 클라우드 상에 물리적 망분리에 준하는 논리적 망분리 및 대체 정보보호통제(VPC Service Controls, Cloud Storage 5년 Bucket Lock, 고객 관리 암호화 키, 감사 로그, Model Armor 가드레일, Sensitive Data Protection)를 종합 점검하고 금융감독원 및 금융보안원(FSI) 보안성 심의 결격 사유를 사전에 예방하는 진단 도구다. (As of 2026-09-10)

**Audience**: `#Architect`, `#Compliance`, `#SecOps`
**Concern**: `#Compliance`, `#IAM`, `#Resilience`, `#Security`
**Service**: `#CloudKMS`, `#CloudStorage`, `#ModelArmor`, `#SensitiveDataProtection`, `#VertexAI`, `#VPCServiceControls`

---

## 1. 법적 근거 및 규제 프레임워크 사실 관계

본 도구는 현행 대한민국 금융 법령 및 감독 당국 규정에 정의된 조항에 근거하여 인프라를 진단한다:

1. **전자금융거래법 제21조(안전성의 확보의무) 및 제22조(전자금융거래기록의 생성 및 보존)**:
   - 금융회사는 컴퓨터 침해 사고 방지 및 안전성 확보를 위한 기술적, 물리적 조치를 다하여야 한다.
   - 금융 거래 및 시스템 접속 기록은 최소 **5년간 보존**하여야 한다.
2. **전자금융감독규정 제14조(전산자료 보호대책), 제15조(고유식별정보 등의 처리) 제1항 제3호 및 제5호**:
   - 내부 업무용 시스템은 인터넷 등 외부 통신망과 물리적으로 분리 및 차단(망분리 의무)되어야 한다.
   - 단, 금융위원회 규제 샌드박스(혁신 금융 서비스) 지정을 통해 예외 특례를 부여받는 경우, 이에 상응하는 엄격한 **논리적 망분리 및 대체 정보보호통제**를 구축하여야 한다.
3. **전자금융감독규정 제15조의2(클라우드컴퓨팅서비스 이용절차 등) 및 제63조(전자금융거래기록의 보기 및 보존 기간)**:
   - 중요 단말 및 시스템에서 클라우드 서비스를 이용할 경우 보안성 평가를 완료하여야 하며, 관련 감사 추적 로그는 5년간 불변 상태로 보관되어야 한다.
4. **신용정보의 이용 및 보호에 관한 법률 제20조의2(가명정보의 이용 및 제공)**:
   - 생성형 AI 모델에 원본 개인신용정보나 주민등록번호 등 고유식별정보를 직접 입력할 수 없으며, 반드시 비식별화 또는 **가명처리된 가명정보** 형태로만 처리되어야 한다.
5. **금융위원회 「금융분야 망분리 개선 로드맵」(1단계 규제 특례 부가조건)**:
   - 혁신 금융 서비스 지정을 통해 생성형 AI를 내부 업무망에서 활용할 경우 외부 인터넷 차단, 사내 고객 관리 암호화 키(CMEK) 적용, AI 악성 프롬프트 방어 가드레일, 비인가 데이터 유출 차단 조치가 의무 부과된다.

---

## 2. 진단 및 해결 흐름

```mermaid
flowchart TD
    A["진단 시작 (diagnose.py / run.sh)"] --> B["VPC-SC 논리적 망분리 검사 (전자금융감독규정 제15조)"]
    B --> C["스토리지 5년 불변 보존 및 CMEK 검사 (전자금융거래법 제22조)"]
    C --> D["Vertex AI 데이터 접근 감사 로그 검사 (전자금융감독규정 제14조/제63조)"]
    D --> E["Model Armor 및 SDP 가명처리 검사 (신용정보법 제20조의2)"]
    E --> F{"규제 결격 항목 발견 여부"}
    F -- "결격 발견 (FAIL/WARN)" --> G["항목별 조치 명령어 및 콘솔 가이드 출력"]
    F -- "전 항목 충족 (PASS)" --> H["FSI 보안성 심의 소명 준비 완료 리포트 확정"]
```

---

## 3. 사전 준비 사항

본 도구 구동을 위해 필요한 최소 IAM 권한은 다음과 같다.

| 권한 역할 | 역할 명칭 | 필요 사유 |
| :--- | :--- | :--- |
| `roles/accesscontextmanager.reader` | Access Context Manager 독자 | VPC-SC 서비스 보안 경계 설정 조회 (전자금융감독규정 제15조 대체 통제) |
| `roles/dlp.inspectTemplatesReader` | DLP 검사 템플릿 독자 | Sensitive Data Protection 가명처리 템플릿 조회 (신용정보법 제20조의2) |
| `roles/logging.viewer` | 로그 뷰어 | 프로젝트 IAM 감사 로그(auditConfigs) 설정 조회 (전자금융거래법 제22조) |
| `roles/resourcemanager.organizationViewer` | 조직 뷰어 | 조직 차원의 리소스 보안 바인딩 조회 |
| `roles/storage.admin` | 스토리지 관리자 | Cloud Storage 버킷 보존 정책(Retention Policy) 및 잠금 상태 조회 (5년 보존 규정) |

---

## 4. 1분 퀵스타트

### 옵션 A: Google Cloud Shell에서 바로 실행

```bash
# 저장소 클론 및 폴더 이동
git clone https://github.com/jiangjun-forge/google-cloud-0-to-1.git
cd google-cloud-0-to-1/samples/korea-fsi-regulatory-perimeter-guard

# 모의 가상 데이터 기반 스모크 테스트 (--dry-run)
./run.sh --dry-run

# 실제 사내 프로젝트 대상 보안 경계 전수 진단
./run.sh --project=example-fsi-corp --location=asia-northeast3
```

### 옵션 B: 로컬 파이썬 가상 환경에서 실행

```bash
# 가상 환경 생성 및 의존성 설치
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 진단 실행
python3 diagnose.py --dry-run
```

---

## 5. 결과 출력 예시

```text
========================================================================================
 혁신 금융 서비스(FSI) 규제 준수 보안 경계 진단 리포트
 대상 프로젝트: example-fsi-corp | 점검 리전: asia-northeast3 | 실행 모드: 가상 진단 (Dry-Run)
========================================================================================

진단 요약: 총 7개 규제 항목 중 충족 3건, 주의 2건, 미달 2건
----------------------------------------------------------------------------------------
ID           | 분류             | 상태     | 진단 항목 및 현황
----------------------------------------------------------------------------------------
FSI-SEC-01   | 논리적 망분리        | [PASS] | VPC-SC 보안 경계 내 Vertex AI 보호 여부 (감독규정 제15조)
  - 현재 상태: aiplatform.googleapis.com 이 서비스 경계(accessPolicies/123456/servicePerimeters/fsi_perimeter)에 등록됨

FSI-SEC-02   | 논리적 망분리        | [WARN] | 실시간 웹 검색(Web Search Grounding) 격리 여부 (외부망 차단)
  - 현재 상태: VPC-SC 내부에서 web_search_tool 호출 시 egress 차단 위험 존재
  - 규제 요건: 외부 인터넷 직접 통신 금지 원칙에 따라, 웹 검색 워크로드는 DMZ 전용 프로젝트로 분리 후 비동기 벡터 DB 적재 아키텍처 적용 필요
  - 조치 권고: 외부 검색 연동 워크로드를 VPC-SC 외부 DMZ 프로젝트로 이관하고 내부 인스턴스로의 비동기 적재 파이프라인 구성 권장

FSI-SEC-03   | 데이터 보호         | [FAIL] | Cloud Storage 불변 보존(Retention Policy / Bucket Lock) 5년 충족 여부 (법 제22조)
  - 현재 상태: 지정 버킷에 보존 정책 미설정 (retention_period: 0s)
  - 규제 요건: 전자금융거래법 제22조 및 전자금융감독규정 제63조에 따라 감사 로그 및 AI 입출력 저장 버킷은 최소 5년(157,680,000초) 보존 및 잠금(Bucket Lock) 필수
  - 조치 권고: gcloud storage buckets update gs://example-fsi-corp-audit-logs --retention-period=157680000s && gcloud storage buckets lock gs://example-fsi-corp-audit-logs

FSI-SEC-04   | 데이터 보호         | [PASS] | 고객 관리 암호화 키(CMEK) 전면 적용 여부 (감독규정 제14조)
  - 현재 상태: Cloud KMS 키(projects/example-fsi-corp/locations/asia-northeast3/keyRings/fsi-ring/cryptoKeys/cmek-key) 정상 바인딩 확인

FSI-SEC-05   | 감사 추적          | [FAIL] | 데이터 접근 감사 로그(DATA_READ, DATA_WRITE) 활성화 여부 (법 제22조)
  - 현재 상태: aiplatform.googleapis.com 데이터 접근 로그 미설정 (ADMIN_READ 만 활성화됨)
  - 규제 요건: 전자금융거래법 제22조에 따라 금융 거래 및 AI 추론 데이터 조회를 위한 DATA_READ, DATA_WRITE 로그 필수 수집
  - 조치 권고: gcloud projects get-iam-policy $PROJECT_ID 후 auditConfigs 에 aiplatform.googleapis.com 및 storage.googleapis.com 추가

FSI-SEC-06   | AI 모델 거버넌스     | [PASS] | Model Armor 실시간 프롬프트 인젝션 및 탈옥 방어 가드레일 (샌드박스 부가조건)
  - 현재 상태: Model Armor 템플릿(fsi-prompt-guard) 활성화 및 프롬프트 인젝션 탐지 필터 적용됨

FSI-SEC-07   | AI 모델 거버넌스     | [WARN] | Sensitive Data Protection (SDP) 개인신용정보 가명처리 템플릿 (신용정보법 제20조의2)
  - 현재 상태: 기본 민감 정보 템플릿 존재하나 주민등록번호(RRN) 및 계좌번호 특화 커스텀 InfoType 미등록
  - 규제 요건: 신용정보법 제20조의2 및 금융보안원 가명처리 기술 가이드라인에 따른 주민등록번호, 계좌번호, 카드번호 특화 검사 및 마스킹 규칙 등록 필수
  - 조치 권고: gcloud dlp inspect-templates create --display-name='fsi-rrn-filter' --info-types=KOREA_RESIDENT_REGISTRATION_NUMBER

========================================================================================
종합 평가 및 감사 준비 가이드:
본 진단 결과 규제 필수 요건에 미달하는 항목이 존재한다.
금융감독원 현장 실사 및 금융보안원 보안성 심의 전 미달(FAIL) 항목을 우선 조치해야 한다.
특히 스토리지 5년 불변 보존(Bucket Lock) 및 Vertex AI 감사 로깅은 전자금융거래법상 필수 소명 대상이다.
========================================================================================
```

---

## 6. 결과 확인 후 즉각 조치 가이드

1. **Cloud Storage 5년 보존 정책 및 Bucket Lock 적용 (전자금융거래법 제22조 및 전자금융감독규정 제63조)**:
   - 금융 관련 감사 로그 및 AI 입출력 데이터가 저장되는 버킷에 최소 5년(157,680,000초) 불변 보존을 설정하고 잠근다.
   - [Cloud Storage 콘솔](https://console.cloud.google.com/storage/browser)
   ```bash
   # 보존 기간 5년 설정 (157,680,000초)
   gcloud storage buckets update gs://<AUDIT_BUCKET_NAME> --retention-period=157680000s

   # 버킷 잠금 (주의: 잠금 후에는 보존 기간 단축 또는 해제가 불가능하다)
   gcloud storage buckets lock gs://<AUDIT_BUCKET_NAME>
   ```

2. **Vertex AI 데이터 접근 감사 로그 강제 (전자금융감독규정 제14조 및 제63조)**:
   - 프로젝트 IAM 정책에 `aiplatform.googleapis.com` 및 `storage.googleapis.com` 데이터 접근 로그(`DATA_READ`, `DATA_WRITE`)를 추가하여 모든 추론 및 모델 호출 이력을 보존한다.
   - [IAM 감사 로그 콘솔](https://console.cloud.google.com/iam-admin/audit)

3. **VPC-SC 내부 실시간 웹 검색(Web Search Grounding) 격리 아키텍처 수립 (전자금융감독규정 제15조)**:
   - VPC-SC 보안 경계 내부에서 `web_search_tool`을 직접 호출할 경우 Egress 차단이 발생하므로, 외부 인터넷 검색 전용 DMZ 프로젝트를 별도로 분리하고 수집된 정보를 내부 벡터 데이터베이스로 비동기 동기화하는 배치 파이프라인 구조로 전환한다.
   - [VPC Service Controls 콘솔](https://console.cloud.google.com/security/service-perimeter)

4. **Model Armor 및 Sensitive Data Protection(SDP) 가드레일 연동 (신용정보법 제20조의2)**:
   - 프롬프트 인젝션 및 탈옥 시도를 엔드포인트 도달 전 선제 차단하기 위해 Model Armor 템플릿을 생성하고, 주민등록번호(`KOREA_RESIDENT_REGISTRATION_NUMBER`) 특화 마스킹 규칙을 등록한다.
   - [Sensitive Data Protection 콘솔](https://console.cloud.google.com/security/dlp)

---

## 7. 자원 정리 가이드

본 도구는 순수 진단 및 상태 점검을 수행하므로 자체적으로 영구 리소스를 생성하거나 과금을 유발하지 않는다.
진단 과정에서 테스트용으로 생성한 모의 버킷이나 키가 있는 경우 아래 명령어로 정리한다.

```bash
# 테스트용 버킷 삭제 (잠금되지 않은 버킷에 한함)
gcloud storage rm -r gs://<TEST_BUCKET_NAME>
```
