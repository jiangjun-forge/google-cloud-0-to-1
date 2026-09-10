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

"""Cloud NAT 포트 고갈 및 패킷 드롭 진단 도구."""

import argparse
import datetime
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


def parse_args() -> argparse.Namespace:
    """명령줄 인자를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="Cloud NAT 포트 고갈 및 패킷 드롭 진단기"
    )
    parser.add_argument(
        "-p",
        "--project",
        default=os.getenv("PROJECT_ID", ""),
        help="GCP 프로젝트 ID (지정하지 않을 경우 gcloud 기본 프로젝트 사용)",
    )
    parser.add_argument(
        "-r",
        "--region",
        default=os.getenv("REGION") or "asia-northeast3",
        help="점검 대상 리전 (기본값: asia-northeast3)",
    )
    parser.add_argument(
        "--router",
        default=os.getenv("ROUTER_NAME", ""),
        help="점검 대상 Cloud Router 이름 (지정하지 않을 경우 자동 감지)",
    )
    parser.add_argument(
        "--nat",
        default=os.getenv("NAT_NAME", ""),
        help="점검 대상 Cloud NAT 게이트웨이 이름 (지정하지 않을 경우 자동 감지)",
    )
    parser.add_argument(
        "-d",
        "--days",
        type=int,
        default=int(os.getenv("LOOKBACK_DAYS", "7")),
        help="모니터링 메트릭 조회 기간 (일 단위, 기본값: 7)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 GCP API 호출 없이 모의 인프라 데이터로 가상 실행",
    )
    return parser.parse_args()


def detect_project_id(cli_project: str, is_dry_run: bool = False) -> str:
    """프로젝트 ID를 탐지하거나 대화형으로 선택한다."""
    if cli_project:
        return cli_project
    env_proj = os.getenv("PROJECT_ID")
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
        return "example-prod-project"

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

    return "example-prod-project"


def get_mock_data() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """가상 실행용 모의 Cloud NAT 구성 및 모니터링 메트릭 데이터를 반환한다."""
    nat_config = {
        "router_name": "cr-prod-asia-northeast3",
        "nat_name": "nat-gw-prod-main",
        "region": "asia-northeast3",
        "natIpAllocateOption": "AUTO_ONLY",
        "autoAllocatedNatIps": [
            "34.64.120.10",
            "34.64.120.11",
        ],
        "sourceSubnetworkIpRangesToNat": "ALL_SUBNETWORKS_ALL_IP_RANGES",
        "minPortsPerVm": 64,
        "maxPortsPerVm": 1024,
        "enableDynamicPortAllocation": True,
        "enableEndpointIndependentMapping": False,
        "tcpEstablishedIdleTimeoutSec": 1200,
        "tcpTransitoryIdleTimeoutSec": 30,
        "tcpTimeWaitTimeoutSec": 120,
        "udpIdleTimeoutSec": 30,
    }

    metrics = {
        "dropped_packets_out_of_resources": 1420,
        "dropped_events_count": 8,
        "max_port_usage": 1012,
        "avg_port_usage": 240,
        "current_allocated_ports": 1024,
        "vms_exceeding_threshold": [
            {
                "instance_id": "gke-prod-core-pool-a1b2",
                "zone": "asia-northeast3-a",
                "peak_usage": 1012,
                "allocated": 1024,
                "usage_percent": 98.8,
                "dropped_count": 860,
            },
            {
                "instance_id": "gke-prod-core-pool-c3d4",
                "zone": "asia-northeast3-b",
                "peak_usage": 980,
                "allocated": 1024,
                "usage_percent": 95.7,
                "dropped_count": 560,
            },
        ],
    }
    return nat_config, metrics


def fetch_nat_configurations(
    project_id: str, region: str, router_filter: str, nat_filter: str
) -> List[Dict[str, Any]]:
    """gcloud CLI를 통해 Cloud Router 및 Cloud NAT 게이트웨이 구성을 조회한다."""
    cmd = [
        "gcloud",
        "compute",
        "routers",
        "list",
        f"--project={project_id}",
        f"--filter=region:({region})",
        "--format=json",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        routers = json.loads(res.stdout or "[]")
    except Exception as e:
        print(f"[-] Cloud Router 목록 조회 실패: {e}")
        return []

    results = []
    for router in routers:
        r_name = router.get("name", "")
        if router_filter and router_filter != r_name:
            continue
        nats = router.get("nats", [])
        for nat in nats:
            n_name = nat.get("name", "")
            if nat_filter and nat_filter != n_name:
                continue
            entry = {
                "router_name": r_name,
                "nat_name": n_name,
                "region": region,
                "natIpAllocateOption": nat.get("natIpAllocateOption", "AUTO_ONLY"),
                "natIps": nat.get("natIps", []),
                "autoAllocatedNatIps": nat.get("autoAllocatedNatIps", []),
                "sourceSubnetworkIpRangesToNat": nat.get("sourceSubnetworkIpRangesToNat", ""),
                "minPortsPerVm": nat.get("minPortsPerVm", 64),
                "maxPortsPerVm": nat.get("maxPortsPerVm", 1024 if nat.get("enableDynamicPortAllocation") else 64),
                "enableDynamicPortAllocation": nat.get("enableDynamicPortAllocation", False),
                "enableEndpointIndependentMapping": nat.get("enableEndpointIndependentMapping", False),
                "tcpEstablishedIdleTimeoutSec": nat.get("tcpEstablishedIdleTimeoutSec", 1200),
                "tcpTransitoryIdleTimeoutSec": nat.get("tcpTransitoryIdleTimeoutSec", 30),
                "tcpTimeWaitTimeoutSec": nat.get("tcpTimeWaitTimeoutSec", 120),
                "udpIdleTimeoutSec": nat.get("udpIdleTimeoutSec", 30),
            }
            results.append(entry)
    return results


def fetch_monitoring_metrics(
    project_id: str, router_name: str, nat_name: str, days: int
) -> Dict[str, Any]:
    """Cloud Monitoring API를 통해 Cloud NAT 드롭 패킷 및 포트 사용률 지표를 조회한다."""
    now = datetime.datetime.now(datetime.timezone.utc)
    start_time = (now - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    metrics_result: Dict[str, Any] = {
        "dropped_packets_out_of_resources": 0,
        "dropped_events_count": 0,
        "max_port_usage": 0,
        "avg_port_usage": 0,
        "current_allocated_ports": 0,
        "vms_exceeding_threshold": [],
    }

    # 1. 드롭 패킷 지표 조회
    filter_expr = (
        f'resource.type="nat_gateway" AND '
        f'resource.labels.router_id="{router_name}" AND '
        f'resource.labels.gateway_name="{nat_name}" AND '
        f'metric.type="router.googleapis.com/nat/dropped_sent_packets_count" AND '
        f'metric.labels.reason="OUT_OF_RESOURCES"'
    )
    cmd = [
        "gcloud",
        "monitoring",
        "time-series",
        "list",
        f"--project={project_id}",
        f"--filter={filter_expr}",
        f"--interval-start-time={start_time}",
        f"--interval-end-time={end_time}",
        "--format=json",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            series = json.loads(res.stdout)
            total_drops = 0
            for s in series:
                points = s.get("points", [])
                for pt in points:
                    val = pt.get("value", {})
                    total_drops += int(val.get("int64Value", 0))
            metrics_result["dropped_packets_out_of_resources"] = total_drops
            if total_drops > 0:
                metrics_result["dropped_events_count"] = len(series)
    except Exception:
        pass

    # 2. 포트 사용량 지표 조회
    port_usage_filter = (
        f'resource.type="gce_instance" AND '
        f'metric.type="compute.googleapis.com/nat/port_usage"'
    )
    cmd_usage = [
        "gcloud",
        "monitoring",
        "time-series",
        "list",
        f"--project={project_id}",
        f"--filter={port_usage_filter}",
        f"--interval-start-time={start_time}",
        f"--interval-end-time={end_time}",
        "--format=json",
    ]
    try:
        res_usage = subprocess.run(cmd_usage, capture_output=True, text=True)
        if res_usage.returncode == 0 and res_usage.stdout.strip():
            series_usage = json.loads(res_usage.stdout)
            peak_val = 0
            for su in series_usage:
                inst_id = su.get("resource", {}).get("labels", {}).get("instance_id", "unknown")
                zone = su.get("resource", {}).get("labels", {}).get("zone", "unknown")
                for pt in su.get("points", []):
                    v = int(pt.get("value", {}).get("int64Value", 0))
                    if v > peak_val:
                        peak_val = v
                    if v >= 512:
                        metrics_result["vms_exceeding_threshold"].append(
                            {
                                "instance_id": inst_id,
                                "zone": zone,
                                "peak_usage": v,
                                "allocated": 1024,
                                "usage_percent": round((v / 1024) * 100, 1),
                                "dropped_count": 0,
                            }
                        )
            metrics_result["max_port_usage"] = peak_val
    except Exception:
        pass

    return metrics_result


def analyze_and_report(
    nat_config: Dict[str, Any], metrics: Dict[str, Any], is_dry_run: bool
) -> None:
    """수집된 설정과 메트릭을 바탕으로 종합 평가 및 처방 리포트를 출력한다."""
    print("=" * 80)
    print(" Cloud NAT 포트 고갈 및 패킷 드롭 종합 진단 리포트")
    print("=" * 80)
    if is_dry_run:
        print("[!] 안내: 본 결과는 실제 GCP 호출이 아닌 내장 모의 인프라 데이터(Dry-Run) 기준이다.")

    r_name = nat_config.get("router_name", "")
    n_name = nat_config.get("nat_name", "")
    region = nat_config.get("region", "")
    dpa_enabled = nat_config.get("enableDynamicPortAllocation", False)
    min_ports = nat_config.get("minPortsPerVm", 64)
    max_ports = nat_config.get("maxPortsPerVm", 64)
    ip_mode = nat_config.get("natIpAllocateOption", "AUTO_ONLY")
    ips = nat_config.get("natIps") or nat_config.get("autoAllocatedNatIps") or []

    print(f"\n[1] 대상 게이트웨이 사양:")
    print(f"  - Cloud Router: {r_name} (리전: {region})")
    print(f"  - Cloud NAT: {n_name}")
    print(f"  - IP 할당 모드: {ip_mode} (보유 공인 IP 수: {len(ips)}개)")
    print(f"  - Dynamic Port Allocation (DPA): {'활성화 (Enabled)' if dpa_enabled else '비활성화 (Disabled, 정적 할당)'}")
    print(f"  - VM/노드당 최소 할당 포트 (minPortsPerVm): {min_ports}개")
    if dpa_enabled:
        print(f"  - VM/노드당 최대 확장 포트 (maxPortsPerVm): {max_ports}개")

    total_drops = metrics.get("dropped_packets_out_of_resources", 0)
    max_usage = metrics.get("max_port_usage", 0)
    high_usage_vms = metrics.get("vms_exceeding_threshold", [])

    print(f"\n[2] 모니터링 텔레메트리 실측 결과 (최근 분석 기간):")
    print(f"  - 자원 고갈 패킷 드롭 수 (OUT_OF_RESOURCES): {total_drops:,}건")
    print(f"  - VM/노드 피크 포트 사용량: {max_usage}개")
    print(f"  - 고위험 VM 및 파드 노드 수: {len(high_usage_vms)}대")

    # 위험 판정 로직
    # NET-AV-2: DPA가 켜져 있어도 버스트 시 확장 지연(최대 240초)으로 드롭 발생 가능
    status = "HEALTHY"
    reasons = []

    if total_drops > 0:
        status = "CRITICAL"
        reasons.append(f"Cloud NAT 게이트웨이에서 {total_drops:,}건의 아웃바운드 패킷 드롭(OUT_OF_RESOURCES)이 실제 발생함")
    elif not dpa_enabled and max_usage >= (min_ports * 0.8):
        status = "CRITICAL"
        reasons.append(f"DPA가 비활성화된 상태에서 포트 사용률이 한계치({min_ports}개)의 80%를 초과함")
    elif dpa_enabled and min_ports <= 64:
        status = "WARNING"
        reasons.append(f"DPA가 활성화되어 있으나 기본값(64개) 유지로 인해 트래픽 급증 시 확장 지연(최대 240초) 구간 패킷 드롭 위험(NET-AV-2) 내재")
    elif max_usage >= (max_ports * 0.85):
        status = "WARNING"
        reasons.append(f"피크 포트 사용량이 최대 확장 한도({max_ports}개)의 85%에 도달함")

    print(f"\n[3] 종합 진단 결과: [{status}]")
    for r in reasons:
        print(f"  * 원인 분석: {r}")
    if not reasons:
        print("  * 원인 분석: 현재 포트 할당 및 드롭 지표가 안정적인 상태를 유지하고 있음")

    if high_usage_vms:
        print(f"\n[4] 포트 임계치 초과 인스턴스 상세:")
        print(f"  {'인스턴스 식별자':<32} {'영역(Zone)':<18} {'피크 사용':<10} {'할당 포트':<10} {'사용률':<8} {'드롭 수'}")
        print("  " + "-" * 88)
        for vm in high_usage_vms:
            print(
                f"  {vm['instance_id']:<32} {vm['zone']:<18} "
                f"{vm['peak_usage']:<10} {vm['allocated']:<10} "
                f"{vm['usage_percent']}%{'':<3} {vm['dropped_count']:,}건"
            )

    print("\n[5] 긴급 조치 가이드 및 아키텍처 처방:")
    if status in ("CRITICAL", "WARNING"):
        recommended_min = 256 if min_ports < 256 else 512
        recommended_max = max(max_ports, 2048)

        print("  1. Cloud NAT 최소 할당 포트(min-ports-per-vm) 즉시 상향:")
        print("     - 트래픽 버스트 시 DPA가 추가 포트를 프로비저닝하는 지연 시간(최대 240초) 동안의 드롭을 원천 예방한다.")
        print(f"     # gcloud 수정 명령어:")
        print(
            f"     gcloud compute routers nats update {n_name} \\\n"
            f"       --router={r_name} \\\n"
            f"       --region={region} \\\n"
            f"       --enable-dynamic-port-allocation \\\n"
            f"       --min-ports-per-vm={recommended_min} \\\n"
            f"       --max-ports-per-vm={recommended_max}"
        )

        print("\n  2. 클라이언트 OS 커널 TCP SYN 재시도 횟수 조정 (GKE 노드 / GCE VM):")
        print("     - DPA가 새 포트 블록을 바인딩하는 동안 클라이언트의 일시적 SYN 드롭을 견딜 수 있도록 재시도 횟수를 상향한다.")
        print("     # Linux 호스트 또는 DaemonSet 실행 명령:")
        print("     sudo sysctl -w net.ipv4.tcp_syn_retries=6")
        print("     # 영구 적용 (/etc/sysctl.d/99-gcp-nat.conf):")
        print("     echo 'net.ipv4.tcp_syn_retries = 6' | sudo tee -a /etc/sysctl.d/99-gcp-nat.conf && sudo sysctl -p")

        print("\n  3. TCP 타임아웃 단축을 통한 포트 재사용성 개선:")
        print("     - 비정상 종료된 연결이 포트를 불필요하게 점유하지 않도록 Transitory Idle Timeout 단축을 검토한다.")
        print(f"     # tcp-transitory-idle-timeout-sec 권장값: 15초 (현재: {nat_config.get('tcpTransitoryIdleTimeoutSec')}초)")
    else:
        print("  - 현재 Cloud NAT 게이트웨이는 안정적으로 운영 중이다.")
        print("  - 향후 신규 마이크로서비스 배포나 대규모 트래픽 이벤트 전 피크 포트 사용량을 지속적으로 모니터링한다.")
    print("=" * 80)


def main() -> None:
    """메인 실행 진입점."""
    args = parse_args()
    print("\n[Cloud NAT Port Exhaustion Guard] 진단 프로세스를 시작한다.", flush=True)

    project_id = detect_project_id(args.project, args.dry_run)
    region = args.region

    print(f"[*] 대상 프로젝트: {project_id}", flush=True)
    print(f"[*] 대상 리전: {region}", flush=True)

    if args.dry_run:
        print("[1/3] 가상 실행 모드 활성화: 모의 인프라 데이터를 로드한다...", flush=True)
        nat_config, metrics = get_mock_data()
        print("[2/3] 모의 포트 할당 및 드롭 지표 분석을 완료했다.", flush=True)
        print("[3/3] 종합 평가 리포트를 생성한다...", flush=True)
        analyze_and_report(nat_config, metrics, is_dry_run=True)
        return

    print("[1/3] Cloud Router 및 Cloud NAT 게이트웨이 구성을 조회한다...", flush=True)
    nats = fetch_nat_configurations(project_id, region, args.router, args.nat)
    if not nats:
        print(f"[-] 리전({region}) 내에 활성화된 Cloud NAT 게이트웨이를 찾지 못했다.")
        print("    --router 및 --nat 인자를 지정하거나, gcloud compute routers list 명령어로 확인 바란다.")
        sys.exit(1)

    target_nat = nats[0]
    print(f"    선택된 게이트웨이: {target_nat['nat_name']} (Router: {target_nat['router_name']})", flush=True)

    print(f"[2/3] Cloud Monitoring 텔레메트리 지표(최근 {args.days}일)를 분석한다...", flush=True)
    metrics = fetch_monitoring_metrics(
        project_id, target_nat["router_name"], target_nat["nat_name"], args.days
    )

    print("[3/3] 종합 평가 및 맞춤형 처방 리포트를 생성한다...", flush=True)
    analyze_and_report(target_nat, metrics, is_dry_run=False)


if __name__ == "__main__":
    main()
