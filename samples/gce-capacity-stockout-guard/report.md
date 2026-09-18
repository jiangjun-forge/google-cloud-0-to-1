# 진단 및 분석 리포트: gce-capacity-stockout-guard

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
================================================================================
Compute Engine 리전 용량 고갈(Stockout) 장애 방어 및 CUD/Reservation 정합성 진단 리포트
진단 모드: 가상 실행 (Dry-run)
대상 프로젝트: sample-project-id
대상 리전: us-central1
점검 머신 패밀리: n4, n2
감사 로그 조회 기간: 최근 14일
================================================================================

[1단계] 최근 14일간 리전 내 용량 고갈(ZONE_RESOURCE_POOL_EXHAUSTED) 발생 내역
--------------------------------------------------------------------------------
존(Zone)         머신 유형              실패 횟수      호출 주체                     상태
--------------------------------------------------------------------------------
us-central1-a   n4-highmem-4       144건       GKE Cluster Autoscaler    ZONE_RESOURCE_POOL_E
us-central1-b   n4-standard-4      121건       GKE Cluster Autoscaler    ZONE_RESOURCE_POOL_E
us-central1-c   n4-highmem-8       5건         Manual gcloud compute i   ZONE_RESOURCE_POOL_E
us-central1-f   n4-standard-4      42건        GKE Cluster Autoscaler    ZONE_RESOURCE_POOL_E
us-central1-a   n2-highmem-4       28건        GKE Cluster Autoscaler    ZONE_RESOURCE_POOL_E
--------------------------------------------------------------------------------
  총 고갈 에러 감지 건수: 340건
  영향 존: us-central1-a, us-central1-b, us-central1-c, us-central1-f

[2단계] CUD(지속 사용 약정) 대비 실제 Reservation(용량 예약) 구비율 분석
--------------------------------------------------------------------------------
약정명                            패밀리      약정 vCPU      약정 메모리         약정 기간
--------------------------------------------------------------------------------
n4-committed-use-discount-3y   N4       98 vCPU      685.0 GB       2026-06-30 ~ 2029-06-30
--------------------------------------------------------------------------------
  - 구매된 CUD 총 규모: vCPU 98 코어
  - 실제 확보된 온디맨드 Reservation: 0개 예약 (총 0대 인스턴스)

  [위험 경고: UNRESERVED CUD DETECTED]
  - 자사는 장기 CUD(요금 할인)를 보유하고 있으나 물리적 온디맨드 Reservation(용량 예약)이 0건이다.
  - CUD는 요금 감면 제도일 뿐 인프라 가용성(Capacity)을 보장하지 않는다.
  - 리전 재고 고갈 시 약정 할인 요금은 계속 청구되면서 신규 VM 생성이 불가능한 이중 손실 위험이 존재한다.

[3단계] GKE 노드풀 구성 및 고갈 취약점(SPOF) 평가
--------------------------------------------------------------------------------
  * 클러스터: prod-core-cluster (노드풀: n4-workload-pool)
    - 현재 머신 유형: n4-highmem-4 (26대 운영 중)
    - 자동 복구(Auto-repair): True | 자동 업그레이드(Auto-upgrade): True
    - 다중 패밀리 대체 노드풀(Multi-family Fallback): False
    - 진단 결과: [CRITICAL] 신규 N4 용량 고갈 상태에서 노드 auto-repair 발생 시 노드 영구 결손 및 롤링 업그레이드 무한 지연 위험
--------------------------------------------------------------------------------

[4단계] 장애 방어 및 CUD 보호를 위한 즉각 조치 처방 가이드
================================================================================
1. CUD 보호를 위한 온디맨드 Reservation 즉시 생성:
   - 재고가 존재하는 존 또는 공급 재개 즉시 온디맨드 예약을 생성하여 물리적 슬롯을 선점한다.
   gcloud compute reservations create res-us-central1-n4-guard \
     --project=sample-project-id \
     --zone=us-central1-a \
     --vm-count=10 \
     --machine-type=n4-highmem-4 \
     --require-specific-reservation=false

2. GKE 자동 복구/업그레이드로 인한 노드 삭제 및 결손 방지:
   - 신규 용량 수급이 불안정한 기간 동안 GKE 유지보수 제외(Maintenance Exclusion)를 선언하여
     Auto-upgrade/Auto-repair로 기존 노드가 제거된 후 재할당받지 못하는 참사를 방지한다.
   gcloud container clusters update prod-core-cluster \
     --project=sample-project-id \
     --location=us-central1 \
     --add-maintenance-exclusion-name=freeze-capacity-shortage \
     --add-maintenance-exclusion-start=2026-09-10T00:00:00Z \
     --add-maintenance-exclusion-end=2026-09-24T00:00:00Z \
     --add-maintenance-exclusion-scope=no_upgrades

3. GKE 다중 머신 패밀리 백업 노드풀(Fallback Node Pool) 구축:
   - N4 단일 패밀리 의존성을 제거하고 N2, C4, C3 기반의 보조 노드풀을 생성하여
     오토스케일러 실패 시 우선순위(PriorityClass)에 따라 보조 노드풀로 파드가 분산 배치되도록 구성한다.

4. Future Reservation(FR) 또는 Flexible CUD 전환 검토:
   - 장기적으로 고갈 위험이 높은 리전은 60~90일 전 Google 계정팀을 통해 Future Reservation을 제출한다.
   - 특정 머신 패밀리에 종속되지 않으려면 재계약 시 Flexible CUD로 전환을 검토한다.
================================================================================
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
