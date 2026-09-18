# 진단 및 분석 리포트: iam-permission-resolver

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
[데모 실행] --dry-run 모드가 활성화되어 가상 권한 거부 리포트를 시뮬레이션한다.
========================================================================
[진단 결과] GCP IAM 권한 거부(403) 감사 추적 및 해결 처방 리포트
  - 대상 프로젝트: sample-project-id
  - 조회 기간: 최근 7일
========================================================================

발견된 권한 거부 실패 내역: 3건

[실패 건 #1]
  - 실패 주체 계정: backend-developer@company.com
  - 요청 대상 서비스: aiplatform.googleapis.com
  - 실행 실패 액션: google.cloud.aiplatform.v1beta1.PredictionService.GenerateContent
  - 실제 오류 내용: Permission 'aiplatform.endpoints.predict' denied on resource
  [정밀 처방 역할 추천]
    - 권장 역할: roles/aiplatform.user
    - 역할 상세: Gemini API 호출 및 Vertex AI 파운데이션 모델 추론 권한
  [즉시 조치 가능한 원클릭 gcloud 해결 명령어]
    gcloud projects add-iam-policy-binding "sample-project-id" \
      --member="user:backend-developer@company.com" \
      --role="roles/aiplatform.user"
------------------------------------------------------------------------
[실패 건 #2]
  - 실패 주체 계정: batch-pipeline-sa@my-prod.iam.gserviceaccount.com
  - 요청 대상 서비스: bigquery.googleapis.com
  - 실행 실패 액션: google.cloud.bigquery.v2.JobService.InsertJob
  - 실제 오류 내용: Access Denied: Table my-prod:gcp_logs.request_response_logging: Permission bigquery.tables.getData denied
  [정밀 처방 역할 추천]
    - 권장 역할: roles/bigquery.dataEditor
    - 역할 상세: BigQuery 데이터세트 수정 및 테이블 데이터 편집 권한
  [즉시 조치 가능한 원클릭 gcloud 해결 명령어]
    gcloud projects add-iam-policy-binding "sample-project-id" \
      --member="serviceAccount:batch-pipeline-sa@my-prod.iam.gserviceaccount.com" \
      --role="roles/bigquery.dataEditor"
------------------------------------------------------------------------
[실패 건 #3]
  - 실패 주체 계정: intern-analyst@company.com
  - 요청 대상 서비스: storage.googleapis.com
  - 실행 실패 액션: storage.objects.get
  - 실제 오류 내용: Access denied: storage.objects.get for bucket gs://my-ml-datasets
  [정밀 처방 역할 추천]
    - 권장 역할: roles/storage.objectViewer
    - 역할 상세: Cloud Storage 버킷 객체 조회 뷰어 권한
  [즉시 조치 가능한 원클릭 gcloud 해결 명령어]
    gcloud projects add-iam-policy-binding "sample-project-id" \
      --member="user:intern-analyst@company.com" \
      --role="roles/storage.objectViewer"
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
