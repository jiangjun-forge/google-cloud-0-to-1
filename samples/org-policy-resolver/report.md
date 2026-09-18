# 진단 및 분석 리포트: org-policy-resolver

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
[데모 실행] --dry-run 모드가 활성화되어 가상 조직 정책 위반 리포트를 시뮬레이션한다.
========================================================================
[진단 결과] GCP 조직 정책(Organization Policy) 위반 감사 추적 리포트
  - 대상 프로젝트: sample-project-id
  - 조회 기간: 최근 7일
========================================================================

발견된 조직 정책 위반 실패 내역: 3건

[위반 건 #1]
  - 실패 주체 계정  : security-engineer@company.com
  - 요청 대상 서비스: iam.googleapis.com
  - 실행 실패 액션  : google.iam.admin.v1.CreateServiceAccountKey
  - 실제 오류 내용  : Operation denied by organization policy: constraints/iam.disableServiceAccountKeyCreation violated
  [정밀 처방 제약 조건 분석]
    - 검출 제약 사항: constraints/iam.disableServiceAccountKeyCreation
    - 제약 조건 설명: 서비스 계정 키(JSON 키) 신규 생성을 전면 차단하는 조직 제약 조건이다.
    - 권장 임시 방안: 보안을 위해 워크로드 아이덴티티(Workload Identity) 연동을 권장하나, 테스트 및 마이그레이션 단계에서 키 발급이 불가피한 경우 해당 프로젝트에 한해 제약을 해제할 수 있다.
  [즉시 조치 가능한 원클릭 gcloud 해결 명령어]
    gcloud resource-manager org-policies disable-enforce "iam.disableServiceAccountKeyCreation" \
      --project="sample-project-id"
------------------------------------------------------------------------
[위반 건 #2]
  - 실패 주체 계정  : cloud-infra-admin@company.com
  - 요청 대상 서비스: compute.googleapis.com
  - 실행 실패 액션  : compute.instances.insert
  - 실제 오류 내용  : Operation denied by organization policy: constraints/compute.vmExternalIpAccess violated on instance vm-bastion-1
  [정밀 처방 제약 조건 분석]
    - 검출 제약 사항: constraints/compute.vmExternalIpAccess
    - 제약 조건 설명: Compute Engine VM 인스턴스에 외부 공용 IP 할당을 금지하는 조직 제약 조건이다.
    - 권장 임시 방안: 내부 IP 전용 VM 생성 및 Cloud NAT 게이트웨이 구성을 권장하나, 단독 외부 접속이 필요한 경우 제약을 해제할 수 있다.
  [즉시 조치 가능한 원클릭 gcloud 해결 명령어]
    gcloud resource-manager org-policies disable-enforce "compute.vmExternalIpAccess" \
      --project="sample-project-id"
------------------------------------------------------------------------
[위반 건 #3]
  - 실패 주체 계정  : web-deployer@company.com
  - 요청 대상 서비스: storage.googleapis.com
  - 실행 실패 액션  : storage.setIamPermissions
  - 실제 오류 내용  : Constraint constraints/storage.publicAccessPrevention violated on bucket gs://web-static-assets
  [정밀 처방 제약 조건 분석]
    - 검출 제약 사항: constraints/storage.publicAccessPrevention
    - 제약 조건 설명: Cloud Storage 버킷의 공용(allUsers) 공개 액세스를 차단하는 조직 제약 조건이다.
    - 권장 임시 방안: 데이터 유출 방지를 위해 비공개 액세스 유지를 권장하나, 정적 웹사이트 호스팅이나 퍼블릭 다운로드 자산인 경우 제약을 해제할 수 있다.
  [즉시 조치 가능한 원클릭 gcloud 해결 명령어]
    gcloud resource-manager org-policies disable-enforce "storage.publicAccessPrevention" \
      --project="sample-project-id"
------------------------------------------------------------------------
========================================================================
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
