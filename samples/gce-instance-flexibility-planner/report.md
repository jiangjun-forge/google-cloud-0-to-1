# Compute Engine & GKE 인스턴스 유연성(Instance Flexibility) 및 스톡아웃 방어 설계 리포트

- **진단 일시**: (실행 결과 자동 생성)
- **대상 프로젝트**: `sample-project-id`
- **점검 대상 리전**: `asia-northeast3`
- **설계 대상 플랫폼**: `all`
- **기준 머신 타입**: `n2-standard-8` (8 vCPU, 32 GB RAM)
- **진단 모드**: `모의 실행 (Dry-run)`

---

## 1. 사내 클러스터 및 MIG 단일 머신 고착 취약점 분석

- **식별된 위험 항목 수**: 3건
- **[위험 발견]** GKE 노드 풀 'core-services-pool': 단일 머신 타입(n2-standard-8)에 의존하여 리전 스톡아웃 시 파드 Pending 발생 위험
- **[위험 발견]** GKE 노드 풀 'batch-worker-pool': Spot 인스턴스 단일 패밀리 구성으로 대규모 선점(Preemption) 시 복구 지연 위험
- **[위험 발견]** MIG 'api-gateway-mig': 단일 인스턴스 템플릿에 고착되어 특정 존 가용성 부족 시 오토스케일링 확장 실패 위험

---

## 2. 동등 사양 대체 머신 패밀리 랭킹 매핑 (Equi-Performance Ranking)

| 순위 | 머신 타입 | 아키텍처 및 세대 | 성능 지수 | 상대 비용 |
| :--- | :--- | :--- | :--- | :--- |
| 1위 | `n4-standard-8` | Gen4 (Emerald Rapids) | 100점 | Base-10% |
| 2위 | `c4a-standard-8` | Axion ARM | 98점 | Base-15% |
| 3위 | `n2d-standard-8` | AMD Milan | 92점 | Base-5% |
| 4위 | `n2-standard-8` | Intel Cascade/Ice | 90점 | Base |
| 5위 | `c3-standard-8` | Intel Sapphire | 96점 | Base+5% |

---

## 3. 플랫폼별 즉시 적용 매니페스트 및 명령어

### (1) GKE Custom ComputeClass(CCC) 매니페스트
용량 부족 시 하위 우선순위로 자동 폴백하며, 상위 머신 가용 시 `activeMigration`으로 자동 복귀한다:
```yaml
apiVersion: autoscaling.gke.io/v1
kind: ComputeClass
metadata:
  name: resilient-compute-class
spec:
  # 능동적 마이그레이션: 상위 우선순위 하드웨어 자원이 확보되면 자동으로 워크로드를 복귀시킴
  activeMigration:
    optimizeRulePriority: true
  nodePoolAutoCreation:
    enabled: true
  priorities:
    # 우선순위 1: Gen4 (Emerald Rapids) (성능 지수: 100)
    - machineFamily: n4
      minCores: 8
      spot: false
    # 우선순위 2: Axion ARM (성능 지수: 98)
    - machineFamily: c4a
      minCores: 8
      spot: false
    # 우선순위 3: AMD Milan (성능 지수: 92)
    - machineFamily: n2d
      minCores: 8
      spot: false
    # 우선순위 4: Intel Cascade/Ice (성능 지수: 90)
    - machineFamily: n2
      minCores: 8
      spot: false
    # 우선순위 5: Intel Sapphire (성능 지수: 96)
    - machineFamily: c3
      minCores: 8
      spot: false
  autoscalingPolicy:
    consolidationDelayMinutes: 5
```

### (2) Compute Engine Regional MIG instanceSelections 정책
Regional MIG 생성 시 머신 패밀리 가용성에 따라 스마트 스필오버를 수행한다:
```bash
gcloud compute instance-groups managed create resilient-worker-mig \
    --region=asia-northeast3 \
    --target-distribution-shape=BALANCED \
    --instance-template=resilient-worker-mig-template \
    --size=10 \
    --instance-flexibility-policy=instance-selections.json
```

### (3) 대규모 단기 배치/분석 작업용 bulkInsert API JSON
```json
{
  "count": 50,
  "minCount": 10,
  "locationPolicy": {
    "targetShape": "ANY"
  },
  "instanceFlexibilityPolicy": {
    "instanceSelections": {
      "selection-1": {
        "rank": 1,
        "machineTypes": [
          "n4-standard-8"
        ]
      },
      "selection-2": {
        "rank": 2,
        "machineTypes": [
          "c4a-standard-8"
        ]
      },
      "selection-3": {
        "rank": 3,
        "machineTypes": [
          "n2d-standard-8"
        ]
      },
      "selection-4": {
        "rank": 4,
        "machineTypes": [
          "n2-standard-8"
        ]
      },
      "selection-5": {
        "rank": 5,
        "machineTypes": [
          "c3-standard-8"
        ]
      }
    }
  }
}
```

---

## 4. 상업적 유연성(Flex CUD) 최적화 가이드

- **자원 기반 CUD(Resource-based CUD) 한계**: 특정 VM 패밀리(예: N2)와 특정 리전에 고착되어 차세대 N4/C4A 머신으로 전환 시 약정 할인이 단절된다.
- **Flex CUD 적용 권고**: 모든 범용/컴퓨팅 최적화 VM 패밀리 및 전 세계 모든 리전에 교차 적용되는 금액 기반 Flex CUD를 결합하여 인프라 유연성과 FinOps 비용 절감을 동시에 확보해야 한다.
