# 진단 및 분석 리포트: cloud-run-direct-vpc-egress-checker

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
================================================================================
Cloud Run Direct VPC Egress 구성 및 네트워크 연결성 진단 리포트
진단 모드: 가상 실행 (Dry-run)
대상 프로젝트: sample-project-id
대상 리전: asia-northeast3
점검 대상 서비스 수: 4개
================================================================================

[1단계] Cloud Run 서비스별 VPC 이그레스 아키텍처 현황
--------------------------------------------------------------------------------
서비스 이름                   이그레스 방식        트래픽 범위             상태        
--------------------------------------------------------------------------------
order-api-prod           CONNECTOR      private-ranges-only WARNING   
payment-gateway-prod     DIRECT_VPC     private-ranges-only CRITICAL  
analytics-collector-prod DIRECT_VPC     all-traffic        CRITICAL  
user-auth-service-prod   DIRECT_VPC     private-ranges-only OK        
--------------------------------------------------------------------------------

[2단계] 서브넷 IP 고갈 위험 및 네트워크 라우팅 세부 진단
--------------------------------------------------------------------------------
- 서비스: order-api-prod
  * 연동 방식: CONNECTOR
  * VPC 커넥터: projects/demo-vpc-egress-project/locations/asia-northeast3/connectors/legacy-vpc-conn
  * 진단 결과: [WARNING] 레거시 Serverless VPC Access 커넥터 사용 중, 대역폭 병목 및 커넥터 유휴 비용 발생 (Direct VPC Egress 전환 권장)

- 서비스: payment-gateway-prod
  * 연동 방식: DIRECT_VPC
  * 대상 서브넷: sub-run-prod-01 (대역: 10.10.1.0/28)
  * Private Google Access: 비활성화 (경고)
  * Cloud NAT 구비 여부: 구성됨 (OK)
  * 최대 인스턴스(maxScale): 120개
  * 진단 결과: [CRITICAL] 서브넷 가용 IP 부족(/28 대역, 가용 IP 11개 < 최대 인스턴스 120개) 및 Private Google Access 미활성화

- 서비스: analytics-collector-prod
  * 연동 방식: DIRECT_VPC
  * 대상 서브넷: sub-run-prod-02 (대역: 10.10.2.0/24)
  * Private Google Access: 활성화 (OK)
  * Cloud NAT 구비 여부: 미구성 (위험)
  * 최대 인스턴스(maxScale): 40개
  * 진단 결과: [CRITICAL] 모든 아웃바운드 트래픽(all-traffic)을 VPC로 라우팅 중이나 Cloud NAT 게이트웨이가 없어 외부 API 통신 전면 실패 위험

- 서비스: user-auth-service-prod
  * 연동 방식: DIRECT_VPC
  * 대상 서브넷: sub-run-prod-03 (대역: 10.10.3.0/24)
  * Private Google Access: 활성화 (OK)
  * Cloud NAT 구비 여부: 구성됨 (OK)
  * 최대 인스턴스(maxScale): 50개
  * 진단 결과: [OK] Direct VPC Egress 정상 구성 (충분한 /24 대역 IP, Private Google Access 활성화, 온프레미스 연동 완료)

--------------------------------------------------------------------------------

[3단계] 아키텍처 현대화 및 즉각 조치 처방
1. Serverless VPC Access 커넥터에서 Direct VPC Egress 로 전환:
   gcloud run services update <SERVICE_NAME> \
     --region=asia-northeast3 \
     --network=<VPC_NETWORK> \
     --subnetwork=<SUBNET_NAME> \
     --vpc-egress=private-ranges-only \
     --clear-vpc-connector

2. 서브넷 Private Google Access 활성화 (구글 API 직결 보장):
   gcloud compute networks subnets update <SUBNET_NAME> \
     --region=asia-northeast3 \
     --enable-private-ip-google-access

3. all-traffic 라우팅 시 외부 통신용 Cloud NAT 생성:
   gcloud compute routers create nat-router --network=<VPC_NETWORK> --region=asia-northeast3
   gcloud compute routers nats create nat-gw --router=nat-router --auto-allocate-nat-external-ips --region=asia-northeast3
================================================================================
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
