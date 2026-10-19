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

# 국가 핵심 기술(NCT) 생성형 AI 보안 통제 및 데이터 주권 진단기 (korea-nct-compliance-checker)

대한민국 산업기술의 유출방지 및 보호에 관한 법률(산업기술보호법) 및 산업통상자원부 「국가 핵심 기술 클라우드 컴퓨팅 서비스 이용을 위한 보안 관리 안내서」에 따라, 국가 핵심 기술(NCT) 취급 기업이 생성형 AI 워크로드를 도입할 때 요구되는 **7대 핵심 기술적 통제(Technical Controls) 전수(Full-Set)**를 체계적으로 종합 점검하고 불법 기술 수출 및 데이터 유출 리스크를 효과적으로 예방하는 진단 도구다. (As of 2026-10-17)

---

## 1. 발생 증상 및 진단 대상 체크리스트

사내 또는 고객사 환경에서 아래 증상이 발생한다면 즉시 진단 대상이다:
- [ ] 관련 인프라 및 서비스 이상 징후 발생 시 즉시 진단 대상

---

## 2. 빠른 시작 (Quickstart)

### 1) 모의 데이터 가상 실행 (Dry-Run)
GCP API 호출 없이 내장된 가상 인프라 데이터로 정상 동작 여부를 즉시 검증한다:
```bash
python diagnose.py --dry-run
```

**터미널 진단 출력 미리보기:**
```text
=====================================================================================
국가 핵심 기술(NCT) 대상 생성형 AI 보안 통제 및 데이터 주권 진단 도구
진단 모드: 가상 실행 (Dry-run)
대상 프로젝트: sample-project-id
지정 리전: asia-northeast3 (대한민국 서울 리전)
=====================================================================================
[*] 가상 모의 감사 데이터를 로드하고 점검 항목을 시뮬레이션한다...
[항목별 기술적 보안 통제 준수 현황]
-------------------------------------------------------------------------------------
구분                 보안 통제 항목                         상태       현재 상태
```

### 2) 실제 사내 인프라 실시간 진단
```bash
cp .env.example .env
python diagnose.py
```
> [!NOTE]
> `.env` 설정값을 비워두면 gcloud 활성 설정 및 사내 리소스를 자동으로 감지하여 진단한다.

---

## 3. 진단 및 해결 흐름

```mermaid
flowchart TD
    A["진단 시작 (diagnose.py)"] --> B["1. 서울 리전 Data Boundary 조직 정책 점검 (법 제11조)"]
    B --> C["2. RAG 벡터 인덱스 사외 적재 차단 IAM Deny 검사 (법 제10조)"]
    C --> D["3. Cloud KMS CMEK 이중 암호화 상태 조회 (안내서 암호화 의무)"]
    D --> E["4. Vertex AI 서울 리전 엔드포인트 격리 검증 (안내서 국내 위치)"]
    E --> F["5. Cloud Audit Logs 데이터 접근 로깅 확인 (법 제10조)"]
    F --> G["6. 사외/외국 계정 공유 차단 조직 정책 점검 (안내서 외국 기업 배제)"]
    G --> H["7. 클라우드 사업자 임의 접근 차단 Access Approval 검사 (안내서 사전 승인 의무)"]
    H --> I{"컴플라이언스 미준수 항목 존재 여부"}
    I -- "결함 식별 (FAIL)" --> J["보안 정책 배포 및 CMEK 연동 처방 제시"]
    I -- "전체 적합 (PASS)" --> K["국가 핵심 기술 기술 통제 풀셋 인증 리포트 출력"]
```

---
## 4. 조치 가이드 및 권장 설정

1. **조직 정책 리소스 위치 제약 설정 (산업기술보호법 제11조 기술 수출 승인/신고 의무)**:
   - 해외 리전(us-central1 등) 생성을 차단하여 승인 없는 해외 기술 이전 리스크를 방어한다.
   - 리소스 위치 정의 ( https://cloud.google.com/resource-manager/docs/organization-policy/defining-locations )
   - 대한민국 Data Boundary 패키지 ( https://cloud.google.com/assured-workloads/docs/control-packages/south-korea-data-boundary )
2. **사외/외국 기업 계정 공유 차단 (보안 관리 안내서 외국 기업 접근 배제)**:
   - 승인된 사내 Google Workspace 도메인 외 계정으로의 IAM 바인딩을 차단한다.
   ```bash
   # constraints/iam.allowedPolicyMemberDomains 설정 적용
   gcloud resource-manager org-policies set-policy policy.yaml --project=$PROJECT_ID
   ```
3. **클라우드 제공자 임의 접근 통제 (보안 관리 안내서 사전 승인 의무)**:
   - 구글 엔지니어의 장애 지원 접근 시 고객 사전 승인을 강제한다.
   ```bash
   gcloud access-approval settings update --project=$PROJECT_ID --enrolled-services=all-services
   ```
4. **Cloud KMS CMEK 키 관리 (보안 관리 안내서 이중 암호화 의무)**:
   - 국내 키링에 고객 관리 암호화 키를 생성하고 모든 버킷 및 데이터셋에 연동하여 CSP의 데이터 접근 통제권을 확보한다.
   - Cloud KMS 콘솔 ( https://console.cloud.google.com/security/kms )

---
## 5. 사전 준비 사항 (필요 IAM 권한)

본 도구를 실행하려면 최소 아래의 IAM 권한이 필요하다:

본 도구를 실행하려면 최소 아래의 IAM 권한이 필요하다:

| 서비스 | 필요 역할(Role) | 최소 IAM 권한 | 필요 사유 |
| : | : | : | : |
| `Access Approval` | `Access Approval 뷰어(roles/accessapproval.viewer)` | `accessapproval.settings.get` | CSP 임의 접근 사전 승인 설정 조회 |
| `Cloud IAM` | `보안 검토자(roles/iam.securityReviewer)` | `iam.denyPolicies.get`, `iam.denyPolicies.list` | RAG 벡터 저장 차단 IAM Deny 확인 (법 제10조) |
| `Cloud KMS` | `클라우드 KMS 뷰어(roles/cloudkms.viewer)` | `cloudkms.keyRings.list`, `cloudkms.cryptoKeys.list` | 서울 리전 CMEK 이중 암호화 키링 상태 조회 (안내서 기준) |
| `Logging` | `클라우드 로깅 뷰어(roles/logging.viewer)` | `logging.views.access` | Cloud Audit Logs 데이터 접근 감사 로깅 조회 (법 제10조) |
| `Resource Manager` | `조직 정책 뷰어(roles/orgpolicy.policyViewer)` | `orgpolicy.policies.list`, `orgpolicy.constraints.list` | 리소스 위치 및 외부 도메인 차단 조직 정책 조회 (법 제11조) |

---

## 6. 기술적 배경 및 아키텍처 원리 (Deep Dive)

```text
=====================================================================================
국가 핵심 기술(NCT) 대상 생성형 AI 보안 통제 및 데이터 주권 진단 리포트
진단 모드: 가상 실행 (Dry-run)
대상 프로젝트: demo-nct-compliance-project | 점검 리전: asia-northeast3 (서울)
=====================================================================================

[항목별 기술적 보안 통제 준수 현황]
-------------------------------------------------------------------------------------
ID    | 보안 통제 항목              | 상태   | 현황 및 규제 요건
-------------------------------------------------------------------------------------
FR-01 | 물리적 국내 위치 (법 제11조)  | PASS | 서울 리전(asia-northeast3) 생성 제한 적용 완료
FR-02 | RAG 벡터 사외 저장 차단     | FAIL | aiplatform.indexes.* 차단 Deny Policy 미설정
FR-03 | Cloud KMS CMEK 이중 암호화  | FAIL | 기본 구글 관리 키 사용 중 (KMS CMEK 미연동)
FR-04 | 추론 리전 국소화 (Vertex AI) | PASS | Vertex AI 서울 엔드포인트 사용 강제 확인
FR-05 | 데이터 접근 감사 로그       | PASS | DATA_READ, DATA_WRITE 감사 로그 활성화 상태
FR-06 | 사외/외국 계정 공유 차단    | FAIL | iam.allowedPolicyMemberDomains 조직 정책 미적용
FR-07 | 제공자 임의 접근 사전 승인  | PASS | Access Approval 정상 활성화 확인
-------------------------------------------------------------------------------------
진단 결과: 총 7개 항목 중 PASS 4건, FAIL 3건 (미준수 항목 즉각 조치 필요)
=====================================================================================
```

---
## 7. 리소스 정리 (Teardown) 안내

본 진단 도구는 환경 설정을 조회하는 읽기 전용 스크립트이므로 별도의 클라우드 리소스를 생성하지 않는다. 테스트용으로 생성한 Cloud KMS 키링이나 IAM Deny 정책은 아래 명령어로 삭제하거나 폐기한다:

```bash
# 테스트용 IAM Deny 정책 삭제
gcloud iam deny-policies delete nct-rag-deny --attachment-point=cloudresourcemanager.googleapis.com/projects/PROJECT_ID

# Cloud KMS 키 버전 비활성화 및 파기 예약
gcloud kms keys versions destroy 1 --key=nct-cmek-key --keyring=nct-keyring --location=asia-northeast3
```

---
