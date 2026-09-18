# 진단 및 분석 리포트: storage-transfer-secure-uploader

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
=====================================================================================
온프레미스 대용량 미디어 STS 전송 및 보안 무결성 사전 진단 리포트
진단 모드: 가상 실행 (Dry-run)
대상 프로젝트: sample-project-id
타깃 버킷: gs://secure-media-archive
STS 에이전트 풀: on-prem-posix-pool
설정 대역폭 제한: 100 MB/s
=====================================================================================

[안전 전송 파이프라인 점검 현황]
-------------------------------------------------------------------------------------
단계                   점검 항목                          결과       상세 상태
-------------------------------------------------------------------------------------
1. 온프렘 로컬 전처리        영상 비식별화 및 개인식별정보/번호판 마스킹       PASS     142개 영상 파일(총 417GB) 전수 비식별화 메타데이터 태그 확인 완료
2. STS 에이전트 풀        에이전트 풀 상태 (on-prem-posix-pool) PASS     온프레미스 도커 에이전트 4대 정상 연결 (상태: CONNECTED, 버전: 최신)
3. 버킷 보안 통제          타깃 버킷 공개 접근 차단 (PAP)           PASS     gs://secure-media-archive publicAccessPrevention=enforced 적용됨
4. 데이터 암호화           Cloud KMS CMEK 암호화 적용          PASS     서울 리전(asia-northeast3) KMS 키(projects/demo/locations/asia-northeast3/keyRings/nct/cryptoKeys/video-key) 바인딩됨
5. 무결성 검증 설정         CRC32c / MD5 체크섬 검증            PASS     전송 중 손상 방지를 위한 청크 단위 CRC32c 해시 대조 자동 활성화
-------------------------------------------------------------------------------------

[전송 작업(Job) 생성 및 실행 가이드]
1. 온프레미스 에이전트 풀 생성 및 실행 토큰 발급:
   gcloud transfer agent-pools create on-prem-posix-pool --project=sample-project-id --display-name='Secure On-Prem Pool'
2. 타깃 버킷 공개 접근 차단 및 CMEK 강제:
   gcloud storage buckets update gs://secure-media-archive --public-access-prevention
   gcloud storage buckets update gs://secure-media-archive --default-kms-key=projects/sample-project-id/locations/asia-northeast3/keyRings/media-ring/cryptoKeys/video-key
3. 대역폭 제한(100 MB/s) 적용 온프렘-to-GCS 전송 작업 생성:
   gcloud transfer jobs create posix-to-gcs /mnt/on-prem/cctv gs://secure-media-archive/cctv-2026/ --source-agent-pool=on-prem-posix-pool --project=sample-project-id
=====================================================================================
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
