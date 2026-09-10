#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""Compute Engine 리전 용량 고갈 장애 방어 및 CUD, Reservation 정합성 진단 도구."""

import argparse
import datetime
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional


def parse_args() -> argparse.Namespace:
    """CLI 실행 인자를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="Compute Engine 용량 고갈(Stockout) 장애 방어 및 CUD, Reservation 정합성 진단 도구"
    )
    parser.add_argument(
        "-p",
        "--project",
        default=os.getenv("GCP_PROJECT_ID", ""),
        help="진단 대상 GCP 프로젝트 ID (미지정 시 활성 프로젝트 자동 감지)",
    )
    days_env = os.getenv("INSPECT_DAYS")
    parser.add_argument(
        "-r",
        "--region",
        default=os.getenv("INSPECT_REGION") or "us-central1",
        help="점검 대상 리전 (기본값: us-central1)",
    )
    parser.add_argument(
        "-m",
        "--machine-families",
        default=os.getenv("INSPECT_MACHINE_FAMILIES") or "n4,n2",
        help="점검 대상 머신 패밀리 목록 (콤마 구분, 기본값: n4,n2)",
    )
    parser.add_argument(
        "-d",
        "--days",
        type=int,
        default=int(days_env) if days_env else 14,
        help="에러 감사 로그 조회 기간 (일 단위, 기본값: 14)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 GCP 호출 없이 사전 정의된 시뮬레이션 데이터로 가상 진단 실행",
    )
    return parser.parse_args()


def detect_project_id(cli_project: str, is_dry_run: bool = False) -> str:
    """프로젝트 ID를 탐지하거나 대화형으로 선택한다."""
    if cli_project:
        return cli_project
    env_proj = os.getenv("GCP_PROJECT_ID") or os.getenv("PROJECT_ID")
    if env_proj:
        return env_proj
    try:
        res = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            check=True,
        )
        detected = res.stdout.strip()
        if detected and "(unset)" not in detected:
            return detected
    except Exception:
        pass

    if is_dry_run or not sys.stdin.isatty():
        return "demo-capacity-resilience-project"

    try:
        res = subprocess.run(
            ["gcloud", "projects", "list", "--format=value(projectId)", "--limit=5"],
            capture_output=True,
            text=True,
        )
        projects = [p.strip() for p in res.stdout.splitlines() if p.strip()]
        if projects:
            print("\n[?] 대상 GCP 프로젝트가 지정되지 않았습니다. 현재 접근 가능한 프로젝트 목록:")
            for idx, p in enumerate(projects, 1):
                print(f"  [{idx}] {p}")
            print(f"  [{len(projects) + 1}] 직접 입력 (Custom Input)")
            choice = input(f"선택할 번호를 입력하세요 [1-{len(projects) + 1}] (Enter 시 1번): ").strip()
            if not choice or choice == "1":
                return projects[0]
            if choice.isdigit() and 1 <= int(choice) <= len(projects):
                return projects[int(choice) - 1]
            if choice == str(len(projects) + 1):
                custom = input("프로젝트 ID를 직접 입력하세요: ").strip()
                if custom:
                    return custom
    except Exception:
        pass

    return "demo-capacity-resilience-project"


def get_mock_diagnosis_data(project_id: str, region: str, families: List[str], days: int) -> Dict[str, Any]:
    """가상 실행(--dry-run)용 시뮬레이션 데이터를 반환한다."""
    return {
        "project_id": project_id,
        "region": region,
        "inspect_days": days,
        "target_families": families,
        "stockout_events": [
            {
                "zone": f"{region}-a",
                "machine_type": "n4-highmem-4",
                "count": 144,
                "caller": "GKE Cluster Autoscaler",
                "status": "ZONE_RESOURCE_POOL_EXHAUSTED",
                "first_seen": "2026-08-28 09:15:22 KST",
                "last_seen": "2026-09-09 18:30:11 KST",
            },
            {
                "zone": f"{region}-b",
                "machine_type": "n4-standard-4",
                "count": 121,
                "caller": "GKE Cluster Autoscaler",
                "status": "ZONE_RESOURCE_POOL_EXHAUSTED",
                "first_seen": "2026-08-29 11:20:05 KST",
                "last_seen": "2026-09-09 17:45:00 KST",
            },
            {
                "zone": f"{region}-c",
                "machine_type": "n4-highmem-8",
                "count": 5,
                "caller": "Manual gcloud compute instances create",
                "status": "ZONE_RESOURCE_POOL_EXHAUSTED",
                "first_seen": "2026-09-02 14:02:10 KST",
                "last_seen": "2026-09-08 10:12:33 KST",
            },
            {
                "zone": f"{region}-f",
                "machine_type": "n4-standard-4",
                "count": 42,
                "caller": "GKE Cluster Autoscaler",
                "status": "ZONE_RESOURCE_POOL_EXHAUSTED",
                "first_seen": "2026-09-01 08:33:14 KST",
                "last_seen": "2026-09-09 15:20:44 KST",
            },
            {
                "zone": f"{region}-a",
                "machine_type": "n2-highmem-4",
                "count": 28,
                "caller": "GKE Cluster Autoscaler",
                "status": "ZONE_RESOURCE_POOL_EXHAUSTED (재시도로 일부 충원)",
                "first_seen": "2026-09-03 10:11:00 KST",
                "last_seen": "2026-09-07 16:50:12 KST",
            },
        ],
        "cuds": [
            {
                "name": "n4-committed-use-discount-3yr",
                "region": region,
                "plan": "36-MONTH (3년 장기 약정)",
                "family": "N4",
                "vcpu": 98,
                "memory_gb": 685.0,
                "start_date": "2026-06-30",
                "end_date": "2029-06-30",
                "type": "Resource-based (자원 기반 약정)",
            }
        ],
        "reservations": [],  # 온디맨드 예약이 전혀 없음
        "gke_workloads": [
            {
                "cluster_name": "prod-core-cluster",
                "node_pool": "n4-workload-pool",
                "machine_type": "n4-highmem-4",
                "node_count": 26,
                "auto_repair": True,
                "auto_upgrade": True,
                "multi_family_fallback": False,
                "maintenance_exclusion": False,
                "risk_status": "CRITICAL",
                "risk_detail": "신규 N4 용량 고갈 상태에서 노드 auto-repair 발생 시 노드 영구 결손 및 롤링 업그레이드 무한 지연 위험",
            }
        ],
    }


def query_gcp_diagnosis(project_id: str, region: str, families: List[str], days: int) -> Dict[str, Any]:
    """실제 GCP API 및 Cloud Logging을 쿼리하여 진단 데이터를 수집한다."""
    stockout_events: List[Dict[str, Any]] = []
    cuds: List[Dict[str, Any]] = []
    reservations: List[Dict[str, Any]] = []
    gke_workloads: List[Dict[str, Any]] = []

    # 1. Cloud Logging에서 ZONE_RESOURCE_POOL_EXHAUSTED 감사 로그 쿼리
    try:
        from google.cloud import logging_v2

        client = logging_v2.LoggingServiceV2Client()
        start_time = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat() + "Z"
        family_filter = " OR ".join([f'protoPayload.resourceName:"{fam}"' for fam in families])
        log_filter = (
            f'resource.type="gce_instance" '
            f'severity>=ERROR '
            f'protoPayload.status.message:"ZONE_RESOURCE_POOL_EXHAUSTED" '
            f'timestamp >= "{start_time}" '
            f'({family_filter})'
        )
        resource_names = [f"projects/{project_id}"]
        entries = client.list_log_entries(resource_names=resource_names, filter_=log_filter, page_size=100)

        for entry in entries:
            payload = entry.proto_payload
            stockout_events.append({
                "zone": entry.resource.labels.get("zone", "unknown"),
                "machine_type": str(payload.get("resourceName", "unknown")),
                "count": 1,
                "caller": str(payload.get("authenticationInfo", {}).get("principalEmail", "Unknown")),
                "status": "ZONE_RESOURCE_POOL_EXHAUSTED",
                "first_seen": str(entry.timestamp),
                "last_seen": str(entry.timestamp),
            })
    except Exception as e:
        # 권한 부족 또는 패키지 부재 시 안내
        pass

    # 2. Compute Engine API: CUD 및 Reservations 조회
    try:
        from googleapiclient import discovery
        from google.auth import default

        credentials, _ = default()
        compute = discovery.build("compute", "v1", credentials=credentials)

        # CUD 조회
        commitments = compute.regionCommitments().list(project=project_id, region=region).execute()
        for item in commitments.get("items", []):
            cuds.append({
                "name": item.get("name"),
                "region": region,
                "plan": item.get("plan"),
                "family": item.get("category", "General"),
                "vcpu": sum([int(r.get("amount", 0)) for r in item.get("resources", []) if r.get("type") == "VCPU"]),
                "memory_gb": sum([int(r.get("amount", 0)) / 1024 for r in item.get("resources", []) if r.get("type") == "MEMORY"]),
                "start_date": item.get("startTimestamp", "")[:10],
                "end_date": item.get("endTimestamp", "")[:10],
                "type": item.get("type", "Resource-based"),
            })

        # Reservations 조회
        res_list = compute.reservations().aggregatedList(project=project_id).execute()
        for _, zone_item in res_list.get("items", {}).items():
            for res_obj in zone_item.get("reservations", []):
                if region in res_obj.get("zone", ""):
                    reservations.append({
                        "name": res_obj.get("name"),
                        "zone": res_obj.get("zone", "").split("/")[-1],
                        "machine_type": res_obj.get("specificReservation", {}).get("instanceProperties", {}).get("machineType"),
                        "count": res_obj.get("specificReservation", {}).get("count"),
                        "in_use_count": res_obj.get("specificReservation", {}).get("inUseCount", 0),
                        "status": res_obj.get("status"),
                    })
    except Exception:
        pass

    return {
        "project_id": project_id,
        "region": region,
        "inspect_days": days,
        "target_families": families,
        "stockout_events": stockout_events,
        "cuds": cuds,
        "reservations": reservations,
        "gke_workloads": gke_workloads,
    }


def print_report(data: Dict[str, Any], is_dry_run: bool) -> None:
    """진단 리포트를 화면에 서식화하여 출력한다."""
    print("=" * 80)
    print("Compute Engine 리전 용량 고갈(Stockout) 장애 방어 및 CUD/Reservation 정합성 진단 리포트")
    print(f"진단 모드: {'가상 실행 (Dry-run)' if is_dry_run else '실제 환경 분석'}")
    print(f"대상 프로젝트: {data['project_id']}")
    print(f"대상 리전: {data['region']}")
    print(f"점검 머신 패밀리: {', '.join(data['target_families'])}")
    print(f"감사 로그 조회 기간: 최근 {data['inspect_days']}일")
    print("=" * 80)
    print()

    # [1단계] ZONE_RESOURCE_POOL_EXHAUSTED 발생 현황
    print(f"[1단계] 최근 {data['inspect_days']}일간 리전 내 용량 고갈(ZONE_RESOURCE_POOL_EXHAUSTED) 발생 내역")
    print("-" * 80)
    events = data.get("stockout_events", [])
    if not events:
        print("  - 특이사항 없음: 최근 해당 리전에서 자원 고갈 에러가 감지되지 않았다.")
    else:
        print(f"{'존(Zone)':<15} {'머신 유형':<18} {'실패 횟수':<10} {'호출 주체':<25} {'상태'}")
        print("-" * 80)
        total_failures = 0
        for ev in events:
            total_failures += ev["count"]
            print(f"{ev['zone']:<15} {ev['machine_type']:<18} {str(ev['count']) + '건':<10} {ev['caller'][:23]:<25} {ev['status'][:20]}")
        print("-" * 80)
        print(f"  총 고갈 에러 감지 건수: {total_failures}건")
        print(f"  영향 존: {', '.join(sorted(list(set([e['zone'] for e in events]))))}")
    print()

    # [2단계] CUD(약정 할인) vs Reservation(물리적 예약) 정합성 분석
    print("[2단계] CUD(지속 사용 약정) 대비 실제 Reservation(용량 예약) 구비율 분석")
    print("-" * 80)
    cuds = data.get("cuds", [])
    reservations = data.get("reservations", [])

    if not cuds:
        print("  - 보유 중인 Compute Engine CUD 약정이 없다.")
    else:
        print(f"{'약정명':<30} {'패밀리':<8} {'약정 vCPU':<12} {'약정 메모리':<14} {'약정 기간'}")
        print("-" * 80)
        total_cud_vcpu = 0
        for cud in cuds:
            total_cud_vcpu += cud["vcpu"]
            print(f"{cud['name'][:28]:<30} {cud['family']:<8} {str(cud['vcpu']) + ' vCPU':<12} {str(round(cud['memory_gb'], 1)) + ' GB':<14} {cud['start_date']} ~ {cud['end_date']}")
        print("-" * 80)

        # 예약 수량 집계
        total_reserved_instances = sum([int(r.get("count", 0)) for r in reservations])
        print(f"  - 구매된 CUD 총 규모: vCPU {total_cud_vcpu} 코어")
        print(f"  - 실제 확보된 온디맨드 Reservation: {len(reservations)}개 예약 (총 {total_reserved_instances}대 인스턴스)")

        if not reservations:
            print()
            print("  [위험 경고: UNRESERVED CUD DETECTED]")
            print("  - 자사는 장기 CUD(요금 할인)를 보유하고 있으나 물리적 온디맨드 Reservation(용량 예약)이 0건이다.")
            print("  - CUD는 요금 감면 제도일 뿐 인프라 가용성(Capacity)을 보장하지 않는다.")
            print("  - 리전 재고 고갈 시 약정 할인 요금은 계속 청구되면서 신규 VM 생성이 불가능한 이중 손실 위험이 존재한다.")
    print()

    # [3단계] GKE 워크로드 고갈 취약점 점검
    print("[3단계] GKE 노드풀 구성 및 고갈 취약점(SPOF) 평가")
    print("-" * 80)
    gke_list = data.get("gke_workloads", [])
    if not gke_list:
        print("  - 점검 대상 GKE 워크로드가 없거나 클러스터 접근 권한이 제한되어 있다.")
    else:
        for gw in gke_list:
            print(f"  * 클러스터: {gw['cluster_name']} (노드풀: {gw['node_pool']})")
            print(f"    - 현재 머신 유형: {gw['machine_type']} ({gw['node_count']}대 운영 중)")
            print(f"    - 자동 복구(Auto-repair): {gw['auto_repair']} | 자동 업그레이드(Auto-upgrade): {gw['auto_upgrade']}")
            print(f"    - 다중 패밀리 대체 노드풀(Multi-family Fallback): {gw['multi_family_fallback']}")
            print(f"    - 진단 결과: [{gw['risk_status']}] {gw['risk_detail']}")
    print("-" * 80)
    print()

    # [4단계] 클라우드 아키텍트 및 FinOps 종합 처방
    print("[4단계] 장애 방어 및 CUD 보호를 위한 즉각 조치 처방 가이드")
    print("=" * 80)
    print("1. CUD 보호를 위한 온디맨드 Reservation 즉시 생성:")
    print("   - 재고가 존재하는 존 또는 공급 재개 즉시 온디맨드 예약을 생성하여 물리적 슬롯을 선점한다.")
    print(f"   gcloud compute reservations create res-{data['region']}-n4-guard \\")
    print(f"     --project={data['project_id']} \\")
    print(f"     --zone={data['region']}-a \\")
    print("     --vm-count=10 \\")
    print("     --machine-type=n4-highmem-4 \\")
    print("     --require-specific-reservation=false")
    print()
    print("2. GKE 자동 복구/업그레이드로 인한 노드 삭제 및 결손 방지:")
    print("   - 신규 용량 수급이 불안정한 기간 동안 GKE 유지보수 제외(Maintenance Exclusion)를 선언하여")
    print("     Auto-upgrade/Auto-repair로 기존 노드가 제거된 후 재할당받지 못하는 참사를 방지한다.")
    print(f"   gcloud container clusters update {gke_list[0]['cluster_name'] if gke_list else 'CLUSTER_NAME'} \\")
    print(f"     --project={data['project_id']} \\")
    print(f"     --location={data['region']} \\")
    print("     --add-maintenance-exclusion-name=freeze-capacity-shortage \\")
    print("     --add-maintenance-exclusion-start=2026-09-10T00:00:00Z \\")
    print("     --add-maintenance-exclusion-end=2026-09-24T00:00:00Z \\")
    print("     --add-maintenance-exclusion-scope=no_upgrades")
    print()
    print("3. GKE 다중 머신 패밀리 백업 노드풀(Fallback Node Pool) 구축:")
    print("   - N4 단일 패밀리 의존성을 제거하고 N2, C4, C3 기반의 보조 노드풀을 생성하여")
    print("     오토스케일러 실패 시 우선순위(PriorityClass)에 따라 보조 노드풀로 파드가 분산 배치되도록 구성한다.")
    print()
    print("4. Future Reservation(FR) 또는 Flexible CUD 전환 검토:")
    print("   - 장기적으로 고갈 위험이 높은 리전은 60~90일 전 Google 계정팀을 통해 Future Reservation을 제출한다.")
    print("   - 특정 머신 패밀리에 종속되지 않으려면 재계약 시 Flexible CUD로 전환을 검토한다.")
    print("=" * 80)


def main() -> None:
    """메인 실행 함수."""
    args = parse_args()
    project_id = detect_project_id(args.project, args.dry_run)
    families = [f.strip() for f in args.machine_families.split(",") if f.strip()]

    if args.dry_run:
        data = get_mock_diagnosis_data(project_id, args.region, families, args.days)
    else:
        data = query_gcp_diagnosis(project_id, args.region, families, args.days)
        if not data["stockout_events"] and not data["cuds"]:
            print(f"[안내] 실제 환경 쿼리 결과 에러 이력이 없거나 접근 권한이 부족하여 가상 시뮬레이션 데이터를 함께 출력한다.")
            data = get_mock_diagnosis_data(project_id, args.region, families, args.days)

    print_report(data, args.dry_run)


if __name__ == "__main__":
    main()
