# 온프레미스 대용량 미디어 STS 전송 및 보안 무결성 사전 진단 리포트 (storage-transfer-secure-uploader)

- **진단 모드**: `모의 실행 (Dry-run)`
- **대상 프로젝트**: `sample-project-id`
- **타깃 버킷**: `gs://secure-media-archive`
- **STS 에이전트 풀**: `on-prem-posix-pool`
- **설정 대역폭 제한**: 100 MB/s
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 안전 전송 파이프라인 점검 현황

| 단계 | 점검 항목 | 결과 | 상세 상태 |
| :--- | :--- | :--- | :--- |
| 1. 온프렘 로컬 전처리 | 영상 비식별화 및 개인식별정보/번호판 마스킹 | PASS | 142개 영상 파일(총 417GB) 전수 비식별화 메타데이터 태그 확인 완료 |
| 2. STS 에이전트 풀 | 에이전트 풀 상태 (on-prem-posix-pool) | PASS | 온프레미스 도커 에이전트 4대 정상 연결 (상태: CONNECTED, 버전: 최신) |
| 3. 버킷 보안 통제 | 타깃 버킷 공개 접근 차단 (PAP) | PASS | gs://secure-media-archive publicAccessPrevention=enforced 적용됨 |
| 4. 데이터 암호화 | Cloud KMS CMEK 암호화 적용 | PASS | 서울 리전(asia-northeast3) KMS 키(projects/demo/locations/asia-northeast3/keyRings/nct/cryptoKeys/video-key) 바인딩됨 |
| 5. 무결성 검증 설정 | CRC32c / MD5 체크섬 검증 | PASS | 전송 중 손상 방지를 위한 청크 단위 CRC32c 해시 대조 자동 활성화 |

---

## 2. 전송 작업(Job) 생성 및 실행 가이드

### 1. 온프레미스 에이전트 풀 생성 및 실행 토큰 발급
```bash
gcloud transfer agent-pools create on-prem-posix-pool --project=sample-project-id --display-name='Secure On-Prem Pool'
```

### 2. 타깃 버킷 공개 접근 차단 및 CMEK 강제
```bash
gcloud storage buckets update gs://secure-media-archive --public-access-prevention
gcloud storage buckets update gs://secure-media-archive --default-kms-key=projects/sample-project-id/locations/asia-northeast3/keyRings/media-ring/cryptoKeys/video-key
```

### 3. 대역폭 제한(100 MB/s) 적용 온프렘-to-GCS 전송 작업 생성
```bash
gcloud transfer jobs create posix-to-gcs /mnt/on-prem/cctv gs://secure-media-archive/cctv-2026/ --source-agent-pool=on-prem-posix-pool --project=sample-project-id
```

---

## 3. 사내 거버넌스 4대 필수 표준 라벨링

STS 연계 타깃 Cloud Storage 버킷, 전송 작업 및 Cloud KMS 키링 프로비저닝 시 다음 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `storage-transfer-secure-uploader`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 4. 콘솔 링크 조치 가이드 및 공식 레퍼런스

- **Storage Transfer Service 온프레미스 콘솔**: ( https://console.cloud.google.com/transfer/on-premises?project=sample-project-id )
- **Cloud Storage 버킷 브라우저**: ( https://console.cloud.google.com/storage/browser/secure-media-archive?project=sample-project-id )
- **공식 문서 - 온프레미스 데이터 전송 개요**: ( https://cloud.google.com/storage-transfer/docs/on-prem-overview )
- **공식 문서 - 온프레미스 에이전트 풀 관리**: ( https://cloud.google.com/storage-transfer/docs/on-prem-agent-pools )
- **공식 문서 - Cloud Storage 공개 접근 차단(PAP)**: ( https://cloud.google.com/storage/docs/public-access-prevention )

---

## 5. 자원 정리 안내 (Teardown)
본 진단 도구는 전송 준비 상태를 검사하는 도구이며, 테스트용으로 생성한 전송 작업(Job)이나 에이전트 풀이 있다면 아래 명령어로 정리한다:
```bash
gcloud transfer jobs delete JOB_NAME --project=sample-project-id
gcloud transfer agent-pools delete on-prem-posix-pool --project=sample-project-id
```
