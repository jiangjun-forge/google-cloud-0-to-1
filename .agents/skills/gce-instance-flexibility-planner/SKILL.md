---
name: gce-instance-flexibility-planner
description: "Autopilot, hands-on diagnostics, and self-healing for gce-instance-flexibility-planner: Compute Engine 및 GKE 환경에서 하드웨어 용량 부족(ZONE_RESOURCE_POOL_EXHAUSTED)으로 인한 배포 중단 및 파드 적체 위험을 방어하기 위해, GKE Custom ComputeClass(CCC)의 능동적 마이그레이션 및 Compute Engine Regional MIG의 instanceSelections 다중 머신 랭킹 정책을 자동 설계하는 진단 도구다."
---

<!-- disableFinding(LINE_OVER_80) -->
<!-- disableFinding(WHITESPACE_TRAILING) -->

# GCE & GKE Instance Flexibility Planner Skill

본 스킬은 고객 및 파트너사 엔지니어가 Compute Engine 및 GKE 환경에서 단일 머신 타입/단일 존에 고착되어 발생하는 스톡아웃(ZONE_RESOURCE_POOL_EXHAUSTED) 장애를 사전에 방지하고, GKE Custom ComputeClass(CCC) 및 GCE Regional MIG 다중 머신 랭킹 정책을 원클릭으로 설계 및 검증할 수 있도록 돕는 실습/진단 가이드다.

```
                   [고객 실습 워크플로우 (3단계)]
 ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
 │ 1. 예습 (Mock)  │ ──> │ 2. 실습 (Live)  │ ──> │ 3. 복습 (Action)│
 │  --dry-run 실행  │     │   실환경 진단   │     │  report.md 검토 │
 └─────────────────┘     └─────────────────┘     └─────────────────┘
```

> [!IMPORTANT]
> **실습 환경 보존 및 자동 정리(Teardown) 금지 안내**:
> 실습으로 생성된 매니페스트와 설정은 사용자가 직접 검토하고 클러스터에 적용해 볼 수 있도록 절대로 에이전트가 임의로 삭제하거나 원상 복구하지 않는다.

---

## 1. 사전 점검 (Preflight Checks)

1. **작업 디렉터리 확인**:
   ```bash
   pwd
   # /.../google-cloud-0-to-1/samples/gce-instance-flexibility-planner 경로 확인
   ```

2. **필수 API 활성화 상태 점검**:
   - `compute.googleapis.com` (Compute Engine API)
   - `container.googleapis.com` (Kubernetes Engine API)

3. **필요 최소 IAM 권한**:
   - `roles/compute.viewer`
   - `roles/container.viewer`

---

## 2. 3단계 실습 실행 절차

### 1단계: 예습 (Dry-run 가상 모의 실행)
실제 클러스터나 인스턴스 조회 없이 8코어 32GB 표준 사양을 기준으로 동등 머신 패밀리 랭킹과 GKE CCC 매니페스트 생성을 1초 만에 검증한다:
```bash
python diagnose.py --dry-run
```

### 2단계: 실습 (사내 실환경 인프라 유연성 진단)
사내 활성 프로젝트의 GKE 노드 풀 및 MIG 설정을 점검하여 단일 고착 위험을 스캔하고 맞춤형 유연성 정책을 산출한다:
```bash
# 기본 활성 프로젝트 및 기본 머신 점검
python diagnose.py

# 특정 프로젝트 및 특정 머신(16코어) 대상 진단
python diagnose.py --project-id=<대상_프로젝트_ID> --base-machine=n2-standard-16

# GPU 인퍼런스/서빙(L4) 대상 대체 랭킹 및 GKE CCC/MIG 정책 진단
python diagnose.py --base-machine=g2-standard-8
```

### 3단계: 복습 (산출물 검토 및 즉각 조치)
자동 생성된 `report.md`를 열어 식별된 위험 항목과 플랫폼별 매니페스트를 검토한다:
- GKE 환경: `ComputeClass` 매니페스트(`resilient-compute-class`) 적용
- GCE 환경: Regional MIG 생성 시 `--instance-flexibility-policy` 파라미터 활용
- FinOps: 자원 기반 CUD 대신 전 리전/전 패밀리 교차 적용 Flex CUD 도입 검토
