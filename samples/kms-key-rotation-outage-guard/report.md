# 진단 및 분석 리포트: kms-key-rotation-outage-guard

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
================================================================================
Cloud KMS CMEK 키 순환 및 구버전 비활성화 장애 예방 리포트
진단 모드: 가상 실행 (Dry-run)
대상 프로젝트: sample-project-id
암호화 키 경로: projects/demo-kms-project/locations/asia-northeast3/keyRings/prod-keyring/cryptoKeys/customer-data-key
현재 주 버전(Primary): 버전 3
자동 순환 주기: 90일 (7,776,000초)
================================================================================

[1단계] Cloud KMS CryptoKey 버전별 라이프사이클 상태 점검
--------------------------------------------------------------------------------
버전       기본 키       상태                   생성 일자                  위험 등급     
--------------------------------------------------------------------------------
v3       YES (Primary) ENABLED              2026-06-01T09:00:00Z   OK        
v2       NO         ENABLED              2026-03-01T09:00:00Z   WARNING   
v1       NO         DESTROY_SCHEDULED    2025-12-01T09:00:00Z   CRITICAL  
--------------------------------------------------------------------------------

[2단계] Cloud Storage 버킷 내 구버전 키 종속성 및 객체 분포 분석
--------------------------------------------------------------------------------
대상 버킷: gs://demo-kms-customer-archive
점검 객체 총합: 1,250개

암호화 버전           객체 수         비율         위험도       
--------------------------------------------------------------------------------
버전 3            620          49.6%      NONE      
버전 2            480          38.4%      MEDIUM    
버전 1            150          12.0%      CRITICAL  
--------------------------------------------------------------------------------

[3단계] 서비스 장애 방지 긴급 처방 및 데이터 재암호화 가이드
1. [긴급] 파기 예정 또는 비활성화된 구버전 키 즉각 복구 (장애 방어):
   gcloud kms keys versions restore 1 \
     --key=customer-data-key \
     --keyring=prod-keyring \
     --location=asia-northeast3

2. [필수] 구버전 키로 암호화된 객체를 최신 주 버전(Primary)으로 일괄 재암호화(Rewrite):
   # 최신 주 키(v3)로 객체 메타데이터 및 암호화 블록 갱신:
   gcloud storage objects rewrite gs://demo-kms-customer-archive/**

3. [검증] 모든 객체가 최신 주 버전 키로 마이그레이션 완료된 후에만 구버전 비활성화(Disable):
   gcloud kms keys versions disable 1 \
     --key=customer-data-key \
     --keyring=prod-keyring \
     --location=asia-northeast3
================================================================================
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
