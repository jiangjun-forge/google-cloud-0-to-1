# 진단 및 분석 리포트: gemini-vpc-sc-denial-resolver

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
[데모 실행] --dry-run 모드가 활성화되어 가상 VPC-SC 차단 리포트를 시뮬레이션한다.
========================================================================
[진단 결과] 제미나이(Gemini) VPC Service Controls 경계 차단 진단 리포트
  - 대상 프로젝트: sample-project-id
  - 조회 기간: 최근 7일
========================================================================

발견된 VPC-SC 경계 거부 사례: 2건

[거부 사례 #1]
  - 호출 주체 계정: developer-workstation@company.com
  - 대상 서비스   : aiplatform.googleapis.com
  - 호출 메서드   : google.cloud.aiplatform.v1beta1.PredictionService.GenerateContent
  - 거부 사유 코드: NO_MATCHING_INGRESS_POLICY
  - 고유 거부 ID  : vpc-sc-denial-8f2a1b9c-4d3e-41a2-98bc-abcdef012345
  [권장 처방 및 복구 가이드]
    - 원인 분석 및 해결책: API 호출자가 신뢰할 수 없는 공용 IP 대역 또는 미지정 사설 서브넷에서 접근했다. VPC-SC 수신(Ingress) 규칙에 호출자의 IP 서브넷 대역 또는 서비스 계정을 명시적으로 허용해야 한다.
    - VPC-SC 문제 해결사 콘솔 ( https://console.cloud.google.com/security/vpc-service-controls/troubleshooter )
    - 서비스 경계 관리 콘솔 ( https://console.cloud.google.com/security/vpc-service-controls )
------------------------------------------------------------------------
[거부 사례 #2]
  - 호출 주체 계정: data-pipeline-sa@my-prod.iam.gserviceaccount.com
  - 대상 서비스   : aiplatform.googleapis.com
  - 호출 메서드   : google.cloud.aiplatform.v1beta1.PredictionService.StreamGenerateContent
  - 거부 사유 코드: RESOURCES_NOT_IN_SAME_PERIMETER
  - 고유 거부 ID  : vpc-sc-denial-3c7d9e1a-5b6f-42c8-89ae-123456789abc
  [권장 처방 및 복구 가이드]
    - 원인 분석 및 해결책: 제미나이 API(aiplatform.googleapis.com)가 경계 보호 대상으로 누락되었거나, 호출 리소스와 대상 모델이 서로 다른 보안 경계로 분리되어 있다. 두 리소스를 동일한 서비스 경계로 병합하거나 경계 간 브리지(Bridge) 규칙을 구성해야 한다.
    - VPC-SC 문제 해결사 콘솔 ( https://console.cloud.google.com/security/vpc-service-controls/troubleshooter )
    - 서비스 경계 관리 콘솔 ( https://console.cloud.google.com/security/vpc-service-controls )
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
