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

# Cloud Run Direct VPC Egress 구성 및 네트워크 연결성 진단기

클라우드 런(Cloud Run) 환경에서 Serverless VPC Access 커넥터의 병목과 인스턴스 비용을 제거하기 위한 Direct VPC Egress 구성 상태, 서브넷 가용 IP 고갈 위험, Private Google Access 및 클라우드 NAT(Cloud NAT) 라우팅 정합성을 1분 만에 일괄 진단하는 도구다. (As of 2026-10-17)

---

## 1. 발생 증상 및 진단 대상 체크리스트

사내 또는 고객사 환경에서 아래 증상이 발생한다면 즉시 진단 대상이다:
- [ ] 기존 Serverless VPC Access 커넥터(VPC Connector)의 최대 처리량 제약이나 인스턴스 기동 지연(Cold Start) 병목을 해소하고자 하는 경우
- [ ] 커넥터 유지에 수반되는 고정 가상 머신(e2-micro 등) 인스턴스 비용을 절감하고 Direct VPC Egress 로 전환하고자 하는 경우
- [ ] Cloud Run 컨테이너가 급격히 수평 확장(Auto-scaling)될 때 할당된 서브넷의 사설 IP가 고갈되어 파드가 기동 실패(Crash)하는 위험을 사전에 방지하려는 경우
- [ ] `all-traffic` 옵션 설정 후 Cloud NAT 미구성으로 인해 외부 공용 API(결제 게이트웨이, 서드파티 웹훅) 통신이 차단되는 장애를 진단해야 하는 경우
- [ ] 서브넷의 Private Google Access(PGA) 설정 누락으로 클라우드 스토리지(Cloud Storage), 빅쿼리(BigQuery) 등 구글 사설 API 호출이 실패하는 원인을 규명하려는 경우

---

## 2. 빠른 시작 (Quickstart)

> [!TIP]
> Cloud Shell 접속 환경 구성 및 저장소 클론(`git clone`) 방법은 루트의 [메인 README](../../README.md)를 참고한다.

### 0) 사내 환경 대화형 설정 (Config Wizard, 선택 사항)
사내 활성 프로젝트 및 환경 설정을 대화형으로 탐색하여 `.env`에 자동 저장한다:
```bash
python diagnose.py --config
```

### 1) 모의 데이터 가상 실행 (Dry-Run)
GCP API 호출 없이 내장된 가상 인프라 데이터로 정상 동작 여부를 즉시 검증한다:
```bash
python diagnose.py --dry-run
```

**터미널 진단 출력 미리보기:**
```text
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
```

### 2) 실제 사내 인프라 실시간 진단
```bash
python diagnose.py
```
> [!NOTE]
> 앞서 `python diagnose.py --config`로 환경 설정을 저장했거나 gcloud 활성 설정을 그대로 활용할 경우 별도의 `.env` 생성 없이 즉시 실행할 수 있다. (환경 변수를 텍스트 에디터로 직접 수동 편집하고자 할 때만 `cp -n .env.example .env` 실행 후 수정)

---

## 3. 솔루션 아키텍처 및 처리 흐름

```mermaid
flowchart TD
    subgraph Layer1["Layer 1: User & Traffic Ingress (트래픽 계층)"]
        ExternalTraffic["외부 HTTPS 클라이언트 트래픽"]
        NetworkAdmin["네트워크 관리자 / SRE 팀"]
    end

    subgraph Layer2["Layer 2: Network & Routing Boundary (네트워크 경계)"]
        DirectEgress["Direct VPC Egress 인터페이스"]
        VPCSubnet["VPC 서브넷 (CIDR 가용 IP 풀)"]
        PGA["Private Google Access (사설 구글 API 라우팅)"]
        CloudNAT["Cloud NAT 게이트웨이 (외부 아웃바운드 인터넷)"]
    end

    subgraph Layer3["Layer 3: Serving & Diagnostic Runtime (런타임 분석)"]
        CloudRunInstance["Cloud Run 컨테이너 인스턴스 (수평 확장)"]
        DiagnosticCLI["diagnose.py 네트워크 정합성 분석기"]
        ReportOutput["복습용 진단 리포트 (report.md)"]
    end

    subgraph Layer4["Layer 4: Target Backend & Destinations (대상 백엔드)"]
        OnPremDB["사설 온프레미스 데이터베이스 / Cloud SQL"]
        GoogleServices["Google 사설 API (Cloud Storage, BigQuery)"]
        ExternalAPI["외부 써드파티 결제/웹훅 API"]
    end

    ExternalTraffic --> CloudRunInstance
    CloudRunInstance --> DirectEgress
    DirectEgress --> VPCSubnet
    VPCSubnet --> PGA
    VPCSubnet --> CloudNAT
    PGA --> GoogleServices
    VPCSubnet --> OnPremDB
    CloudNAT --> ExternalAPI
    NetworkAdmin --> DiagnosticCLI
    DiagnosticCLI --> DirectEgress
    DiagnosticCLI --> VPCSubnet
    DiagnosticCLI --> ReportOutput
```

---
## 4. 조치 가이드 및 권장 설정

### 1단계: Direct VPC Egress 마이그레이션 적용
- Cloud Run 콘솔 ( https://console.cloud.google.com/run ) > 대상 서비스 선택 > 수정 및 새 버전 배포 > 네트워킹 탭
- Cloud Run Direct VPC Egress 설정 가이드 ( https://cloud.google.com/run/docs/configuring/vpc-direct-vpc )
- VPC 네트워크 연결 옵션 비교 ( https://cloud.google.com/run/docs/configuring/connecting-vpc )

### 2단계: 서브넷 Private Google Access 및 Cloud NAT 라우팅 정합성 확보
- VPC 네트워크 ( https://console.cloud.google.com/networking/networks/list ) > 서브넷 선택 > 수정 > 비공개 Google 액세스 사용 설정
- Private Google Access 개요 ( https://cloud.google.com/vpc/docs/private-google-access )
- Cloud NAT 콘솔 ( https://console.cloud.google.com/net-services/nat/list )
- 외부 아웃바운드 트래픽(`all-traffic`)을 안전하게 처리하기 위한 Cloud NAT 게이트웨이를 배치한다.

### 3단계: GCP 리소스 생성 시 4대 필수 표준 라벨링 준수
- Cloud Run 서비스 및 관련 클라우드 인프라 생성/배포 시 FinOps 비용 분석 및 추적을 위해 4대 표준 라벨을 필수로 주입한다:
  - `managed-by`: `google-cloud-0-to-1`
  - `scenario`: `cloud-run-direct-vpc-egress-checker`
  - `env`: `sample`
  - `created-by`: `customer-engineer`
- gcloud CLI 예시: `--labels=managed-by=google-cloud-0-to-1,scenario=cloud-run-direct-vpc-egress-checker,env=sample,created-by=customer-engineer`

---
## 5. 사전 준비 사항 (필요 IAM 권한)

본 도구를 실행하려면 최소 아래의 IAM 권한이 필요하다:

본 도구를 실행하려면 최소 아래의 IAM 권한이 필요하다:

| 서비스 | 필요 역할(Role) | 최소 IAM 권한 |
| :--- | :--- | :--- |
| `Cloud Run` | `roles/run.viewer` | `run.services.get`, `run.services.list` |
| `Compute Engine` | `roles/compute.networkViewer` | `compute.networks.get`, `compute.routers.get`, `compute.subnetworks.get` |

---

## 6. 기술적 배경 및 아키텍처 원리 (Deep Dive)

### 관련 상세 설계 및 요구 사항 명세
- [비즈니스 요구 사항 명세서 (BRD)](docs/BRD.md): 비즈니스 배경, 성공 지표 및 요구 사항(BR-01~) 명세
- [기술 상세 설계서 (TDD)](docs/TDD.md): 시스템 아키텍처, 기능(FR-01~) 및 비기능(NFR-01~) 설계 명세

```text
================================================================================
Cloud Run Direct VPC Egress 구성 및 네트워크 연결성 진단 리포트
진단 모드: 가상 실행 (Dry-run)
대상 프로젝트: demo-vpc-egress-project
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
     --clear-vpc-connector \
     --labels=managed-by=google-cloud-0-to-1,scenario=cloud-run-direct-vpc-egress-checker,env=sample,created-by=customer-engineer

2. 서브넷 Private Google Access 활성화 (구글 API 직결 보장):
   gcloud compute networks subnets update <SUBNET_NAME> \
     --region=asia-northeast3 \
     --enable-private-ip-google-access

3. all-traffic 라우팅 시 외부 통신용 Cloud NAT 생성:
   gcloud compute routers create nat-router --network=<VPC_NETWORK> --region=asia-northeast3
   gcloud compute routers nats create nat-gw --router=nat-router --auto-allocate-nat-external-ips --region=asia-northeast3

4. 사내 거버넌스 4대 필수 표준 라벨링 준수:
   Cloud Run 서비스 및 네트워크 자원 생성 시 FinOps 추적을 위해 4대 표준 라벨을 필수 결합한다.
================================================================================
```

---
## 7. 리소스 정리 (Teardown) 안내

본 진단 도구는 읽기 전용으로 Cloud Run 및 VPC 네트워크 메타데이터를 조회하므로 별도의 클라우드 인프라 자원을 생성하지 않는다. 실습을 위해 생성한 테스트용 Cloud Run 서비스나 서브넷이 있다면 아래 명령어로 정리한다:

```bash
# 테스트 Cloud Run 서비스 삭제
gcloud run services delete SERVICE_NAME --region=REGION --quiet

# 테스트 서브넷 삭제
gcloud compute networks subnets delete SUBNET_NAME --region=REGION --quiet
```
