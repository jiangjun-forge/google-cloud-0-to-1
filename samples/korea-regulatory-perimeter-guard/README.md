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

# 혁신 금융 서비스 규제 준수 보안 경계 진단 가이드 (korea-regulatory-perimeter-guard)

대한민국 금융위원회의 「금융 분야 망 분리 개선 로드맵」(1단계 생성형 AI 활용 특례) 및 전자금융감독규정에 따라, 퍼블릭 클라우드 인프라가 책임져야 하는 **9대 핵심 기술적 통제(Technical Controls) 전수(Full-Set)**를 체계적으로 종합 점검하고 금융감독원 및 금융보안원(FSI) 보안성 심의 결격 사유를 사전에 예방하는 진단 도구다. (As of 2026-10-17)

---

## 1. 발생 증상 및 진단 대상 체크리스트

사내 또는 고객사 환경에서 아래 증상이 발생한다면 즉시 진단 대상이다:
- [ ] 관련 인프라 및 서비스 이상 징후 발생 시 즉시 진단 대상


### 1.1 도구의 본질 및 비즈니스 해결 과제 (What & Why)
- **대상 사용자 (Target)**: 금융기관 CISO, 핀테크 컴플라이언스 리드, 금융 클라우드 아키텍트 및 보안 운영팀
- **해결하는 핵심 문제 (Core Pain Points)**:
  1. 금융위 「금융 분야 망 분리 개선 로드맵」(1단계 생성형 AI 특례) 및 전자금융감독규정의 9대 핵심 인프라 통제 점검의 난해함
  2. 혁신 금융 서비스 지정 신청 시 금융보안원(FSI) 보안성 심의와 금융감독원 현장 실사 준비에 수개월이 지연되는 문제
  3. 스토리지 5년 불변 보존(Bucket Lock), 고강도 TLS 1.2+ 강제, WIF 전환 등 필수 요건 누락으로 인한 심사 반려 리스크
- **본 솔루션의 해결 방식 (Solution)**:
  - 금융 당국의 혁신 금융 서비스 1단계 특례 기준에 부합하는 9대 핵심 기술적 보안 통제(논리적 망 분리, 데이터 암호화, 감사 기록 5년 보존, 정적 키 차단 등)를 자동 진단하고 결격 항목에 대한 즉시 처방 명령어를 도출한다.

### 1.2 최종 산출물 3종 세트 미리보기 (Deliverables & Visual Preview)
본 도구를 실행(`python diagnose.py`)하면 다음 3가지 구체적인 엔터프라이즈 자산이 생성된다:

| 산출물 구분 | 산출물 형태 및 명칭 | 주요 포함 내용 및 실무 활용 방안 |
| :--- | :--- | :--- |
| **① 터미널 콘솔 요약** | Visual CLI Table | 9대 금융 규제 통제 항목별 상태(PASS/FAIL), 위반 인프라 리소스 및 필수 조치 우선순위 표 |
| **② 정규 진단 보고서** | 마크다운 파일 (`report.md`) | 금융 당국 제출용 혁신 금융 서비스 보안성 심의 진단서, 9대 규제 매핑 표, 위반 인프라 상세 분석 및 gcloud 조치 명령 |
| **③ 후속 조치 및 배포 자산** | Actionable Asset Specs | • **전자금융감독규정 준수 gcloud 명령어 세트**: TLS 정책, VPC-SC, Bucket Lock 원클릭 설정<br/>• **신용정보법 대응 SDP 템플릿**: 고유식별정보 비식별 조치를 위한 개인신용정보 마스킹 룰<br/>• **FSI 보안 심의 증적 패키지**: 금융보안원 제출용 표준 아키텍처 다이어그램 및 설정 소명서 |

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
- 조치 권고: 외부 검색 연동 워크로드를 VPC-SC 외부 DMZ 프로젝트로 이관하고 내부 인스턴스로의 비동기 적재 파이프라인 구성 권장
FR-03        | 데이터 보호         | [FAIL] | Cloud Storage 불변 보존(Retention Policy / Bucket Lock) 5년 충족 여부 (법 제22조)
  - 현재 상태: 지정 버킷에 보존 정책 미설정 (retention_period: 0s)
  - 규제 요건: 전자금융거래법 제22조 및 전자금융감독규정 제63조에 따라 감사 로그 및 AI 입출력 저장 버킷은 최소 5년(157,680,000초) 보존 및 잠금(Bucket Lock) 필수
  - 조치 권고: gcloud storage buckets update gs://sample-project-id-audit-logs --retention-period=157680000s && gcloud storage buckets lock gs://sample-project-id-audit-logs
FR-04        | 데이터 보호         | [PASS] | 고객 관리 암호화 키(CMEK) 전면 적용 여부 (감독규정 제14조)
  - 현재 상태: Cloud KMS 키(projects/sample-project-id/locations/asia-northeast3/keyRings/fsi-ring/cryptoKeys/cmek-key) 정상 바인딩 확인
FR-05        | 감사 추적          | [FAIL] | 데이터 접근 감사 로그(DATA_READ, DATA_WRITE) 활성화 여부 (법 제22조)
  - 현재 상태: aiplatform.googleapis.com 데이터 접근 로그 미설정 (ADMIN_READ 만 활성화됨)
  - 규제 요건: 전자금융거래법 제22조 및 전자금융감독규정 제14조에 따라 금융 거래 및 AI 추론 데이터 조회를 위해 DATA_READ, DATA_WRITE 로그 감사 필수 수집
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

## 3. 솔루션 아키텍처 및 처리 흐름

```mermaid
flowchart TD
    subgraph Layer1 ["Layer 1: User & Interface Layer"]
        Auditor["금융보안팀 / CISO / 금융감독원 감사관"]
        CLI["FSI 규제 진단 컨트롤러<br/>(diagnose.py)"]
        Auditor --> CLI
    end

    subgraph Layer2 ["Layer 2: Security & Regulatory Boundary"]
        VPCSC["VPC Service Controls 경계<br/>(논리적 망 분리 및 RAG 격리)"]
        OrgPolicy["서비스 계정 키 발급 차단<br/>(constraints/iam.disableServiceAccountKeyCreation)"]
        SSLPolicy["전송 구간 암호화 정책<br/>(TLS 1.2+ Restricted 프로필)"]
        CLI --> VPCSC
        CLI --> OrgPolicy
        CLI --> SSLPolicy
    end

    subgraph Layer3 ["Layer 3: Diagnostic & Guardrail Engine"]
        FSIEngine["9대 금융 규제 평가기<br/>(전자금융감독규정 및 신용정보법 판정)"]
        ModelArmor["AI 안전 가드레일<br/>(Model Armor 및 SDP 가명 처리)"]
        Remediator["선언적 복구 스크립트 도출기<br/>(gcloud 정규 복구 명령어 합성)"]
        CLI --> FSIEngine
        FSIEngine --> ModelArmor
        FSIEngine --> Remediator
    end

    subgraph Layer4 ["Layer 4: Target Backend & FSI Storage Fabric"]
        GCSLock["Cloud Storage 불변 보존<br/>(5년 보존 정책 및 Bucket Lock)"]
        KMSCMEK["Cloud KMS 금융 CMEK<br/>(서울 리전 HSM 암호화 키)"]
        VertexAudit["Vertex AI 감사 추적<br/>(DATA_READ, DATA_WRITE 전체 수집)"]
        FSIEngine --> GCSLock
        FSIEngine --> KMSCMEK
        FSIEngine --> VertexAudit
    end
```

---
## 4. 조치 가이드 및 권장 설정

1. **서비스 계정 키 생성 차단 (전자금융감독규정 제13조)**:
   - 정적 서비스 계정 JSON 키 발급을 방지하고 WIF 연동을 강제한다.
   ```bash
   gcloud resource-manager org-policies enable-enforce constraints/iam.disableServiceAccountKeyCreation --project=$PROJECT_ID
   ```

2. **전송 구간 암호화 정책 수립 (전자금융감독규정 제14조)**:
   - 취약한 프로토콜(TLS 1.0, 1.1)을 차단하고 TLS 1.2 이상만 허용하는 커스텀 SSL 정책을 생성한다.
   ```bash
   gcloud compute ssl-policies create fsi-tls-policy --profile=RESTRICTED --min-tls-version=1.2 --project=$PROJECT_ID
   ```

3. **Cloud Storage 5년 보존 정책 및 Bucket Lock 적용 (전자금융거래법 제22조 및 전자금융감독규정 제63조)**:
   - 금융 감사 로그 및 AI 입출력 버킷에 5년(157,680,000초) 불변 보존을 강제한다.
   ```bash
   gcloud storage buckets update gs://<AUDIT_BUCKET_NAME> --retention-period=157680000s
   gcloud storage buckets lock gs://<AUDIT_BUCKET_NAME>
   ```

4. **Vertex AI 데이터 접근 감사 로그 강제 (전자금융감독규정 제14조 및 제63조)**:
   - 프로젝트 IAM 정책에 `aiplatform.googleapis.com` 및 `storage.googleapis.com` 데이터 접근 로그(`DATA_READ`, `DATA_WRITE`)를 추가한다.

5. **Model Armor 및 Sensitive Data Protection(SDP) 가드레일 연동 (신용정보법 제20조의2)**:
   - 악성 프롬프트 인젝션 방어 필터를 활성화하고 주민등록번호(`KOREA_RESIDENT_REGISTRATION_NUMBER`) 가명 처리 템플릿을 등록한다.

---
### GCP 리소스 생성 시 4대 필수 표준 라벨링 준수
- 사내 거버넌스 및 자원 식별, 비용 추적을 위해 관련 클라우드 리소스 생성 시 4대 표준 라벨을 필수로 주입한다:
  - `managed-by`: `google-cloud-0-to-1`
  - `scenario`: `korea-regulatory-perimeter-guard`
  - `env`: `sample`
  - `created-by`: `customer-engineer`
- gcloud CLI 예시: `--labels=managed-by=google-cloud-0-to-1,scenario=korea-regulatory-perimeter-guard,env=sample,created-by=customer-engineer`

---

## 5. 사전 준비 사항 (필요 IAM 권한)

본 도구를 실행하려면 최소 아래의 IAM 권한이 필요하다:

본 도구 구동을 위해 필요한 최소 IAM 권한은 다음과 같다.

| 권한 역할 | 역할 명칭 | 필요 사유 |
| :--- | :--- | :--- |
| `roles/accesscontextmanager.reader` | `Access Context Manager 독자(roles/accesscontextmanager.reader)` | VPC-SC 서비스 보안 경계 설정 조회 (감독규정 제15조) |
| `roles/compute.viewer` | `Compute 뷰어(roles/compute.viewer)` | SSL 정책 TLS 최소 버전 조회 (감독규정 제14조) |
| `roles/dlp.inspectTemplatesReader` | `DLP 검사 템플릿 독자(roles/dlp.inspectTemplatesReader)` | Sensitive Data Protection 가명 처리 템플릿 조회 (신용정보법 제20조의2) |
| `roles/logging.viewer` | `클라우드 로깅 뷰어(roles/logging.viewer)` | 프로젝트 IAM 감사 로그(auditConfigs) 설정 조회 (법 제22조) |
| `roles/orgpolicy.policyViewer` | `조직 정책 뷰어(roles/orgpolicy.policyViewer)` | 서비스 계정 키 생성 차단 조직 정책 조회 (감독규정 제13조) |
| `roles/storage.admin` | `스토리지 관리자(roles/storage.admin)` | Cloud Storage 버킷 보존 정책 및 잠금 상태 조회 (5년 보존 규정) |

---

## 6. 기술적 배경 및 아키텍처 원리 (Deep Dive)

### 관련 상세 설계 및 요구 사항 명세
- [비즈니스 요구 사항 명세서 (BRD)](docs/BRD.md): 비즈니스 배경, 성공 지표 및 요구 사항(BR-01~) 명세
- [기술 상세 설계서 (TDD)](docs/TDD.md): 시스템 아키텍처, 기능(FR-01~) 및 비기능(NFR-01~) 설계 명세

```text
========================================================================================
 혁신 금융 서비스(FSI) 규제 준수 보안 경계 진단 리포트
 대상 프로젝트: example-fsi-corp | 점검 리전: asia-northeast3 | 실행 모드: 가상 진단 (Dry-Run)
========================================================================================

진단 요약: 총 9개 규제 항목 중 충족 4건, 주의 2건, 미달 3건
----------------------------------------------------------------------------------------
ID      | 분류             | 상태     | 진단 항목 및 조치 요약
----------------------------------------------------------------------------------------
FR-01   | 논리적 망 분리        | [PASS] | VPC-SC 보안 경계 내 Vertex AI 보호 확인
FR-02   | 논리적 망 분리        | [WARN] | 실시간 웹 검색 DMZ 분리 및 비동기 적재 구조 권고
FR-03   | 데이터 보호         | [FAIL] | Cloud Storage 5년 불변 보존(Bucket Lock) 미설정 (법 제22조)
FR-04   | 데이터 보호         | [PASS] | 고객 관리 암호화 키(CMEK) 전면 바인딩 확인 (감독규정 제14조)
FR-05   | 감사 추적          | [FAIL] | Vertex AI 데이터 접근 감사 로그(DATA_READ/WRITE) 미설정
FR-06   | AI 모델 거버넌스     | [PASS] | Model Armor 프롬프트 인젝션 방어 필터 적용 확인
FR-07   | AI 모델 거버넌스     | [WARN] | SDP 주민등록번호/계좌번호 특화 가명 처리 템플릿 등록 권고
FR-08   | 접근 통제          | [FAIL] | 서비스 계정 키 생성 차단 조직 정책 미적용 (감독규정 제13조)
FR-09   | 전송 보안          | [PASS] | 전송 구간 TLS 1.2+ 고강도 암호화 적용 확인 (감독규정 제14조)
----------------------------------------------------------------------------------------
종합 평가: 금융보안원 보안성 심의 전 미달(FAIL) 3건의 우선 조치가 요구된다.
========================================================================================
```

---
## 7. 리소스 정리 (Teardown) 안내

본 도구는 순수 진단 및 상태 점검을 수행하므로 자체적으로 영구 리소스를 생성하거나 과금을 유발하지 않는다.
진단 과정에서 테스트용으로 생성한 모의 버킷이나 키가 있는 경우 아래 명령어로 정리한다.

```bash
# 테스트용 버킷 삭제 (잠금되지 않은 버킷에 한함)
gcloud storage rm -r gs://<TEST_BUCKET_NAME>
```

---
