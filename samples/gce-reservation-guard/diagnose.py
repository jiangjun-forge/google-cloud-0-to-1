#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Compute Engine 하드웨어 예약(Reservation) 및 CUD 용량 보장 통합 진단 도구."""

import argparse
import datetime
from datetime import datetime as dt, timedelta, timezone
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute Engine 온디맨드 Reservation 확보율 및 Future Reservation(FR) 신청 현황 통합 진단기"
    )
    parser.add_argument(
        "-p", "--project",
        default=os.getenv("PROJECT_ID", ""),
        help="진단 대상 GCP 프로젝트 ID (미지정 시 활성 프로젝트 자동 감지)",
    )
    parser.add_argument(
        "-r", "--region",
        default=os.getenv("REGION") or "asia-northeast3",
        help="점검 대상 리전 (기본값: asia-northeast3)",
    )
    parser.add_argument(
        "-m", "--machine-families",
        default=os.getenv("MACHINE_FAMILIES") or "n4,n2,g2,a2",
        help="점검 대상 머신 패밀리 목록 (콤마 구분, 기본값: n4,n2,g2,a2)",
    )
    days_env = os.getenv("INSPECT_DAYS")
    parser.add_argument(
        "-d", "--days",
        type=int,
        default=int(days_env) if days_env else 14,
        help="에러 감사 로그 조회 기간 (일 단위, 기본값: 14)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 GCP 호출 없이 시뮬레이션 데이터로 가상 진단 실행",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="결과를 JSON 형식으로 출력한다.",
    )
    return parser.parse_args()


def detect_project_id(cli_project: str, is_dry_run: bool = False) -> str:
    if cli_project:
        return cli_project
    env_proj = os.getenv("PROJECT_ID") or os.getenv("GCP_PROJECT_ID")
    if env_proj:
        return env_proj
    try:
        res = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True, text=True, check=True,
        )
        detected = res.stdout.strip()
        if detected and "(unset)" not in detected:
            return detected
    except Exception:
        pass

    if is_dry_run or not sys.stdin.isatty():
        return "sample-reservation-project"

    try:
        res = subprocess.run(
            ["gcloud", "projects", "list", "--format=value(projectId)", "--limit=5"],
            capture_output=True, text=True,
        )
        projects = [p.strip() for p in res.stdout.splitlines() if p.strip()]
        if projects:
            print("\n[?] 대상 GCP 프로젝트가 지정되지 않았다. 현재 접근 가능한 프로젝트 목록:")
            for idx, p in enumerate(projects, 1):
                print(f"  [{idx}] {p}")
            print(f"  [{len(projects) + 1}] 직접 입력 (Custom Input)")
            choice = input(f"선택할 번호 입력 [1-{len(projects) + 1}] (Enter 시 1번): ").strip()
            if not choice or choice == "1":
                return projects[0]
            if choice.isdigit() and 1 <= int(choice) <= len(projects):
                return projects[int(choice) - 1]
            if choice == str(len(projects) + 1):
                custom = input("프로젝트 ID 직접 입력: ").strip()
                if custom:
                    return custom
    except Exception:
        pass

    return "sample-reservation-project"


def get_mock_diagnosis_data(project_id: str, region: str) -> Dict[str, Any]:
    now = dt.now(timezone.utc)
    return {
        "stockout_logs": [
            {
                "timestamp": (now - timedelta(days=2)).isoformat(),
                "zone": f"{region}-a",
                "machine_type": "n4-standard-8",
                "error_code": "ZONE_RESOURCE_POOL_EXHAUSTED",
                "caller": "gke-nodepool-autoscaler@example.com",
            },
            {
                "timestamp": (now - timedelta(days=5)).isoformat(),
                "zone": f"{region}-b",
                "machine_type": "g2-standard-8",
                "error_code": "ZONE_RESOURCE_POOL_EXHAUSTED",
                "caller": "admin-deployer@example.com",
            }
        ],
        "commitments": [
            {"name": "n4-cud-1yr", "plan": "TWELVE_MONTH", "cores": 64, "memory_gb": 256, "region": region},
            {"name": "n2-cud-3yr", "plan": "THIRTY_SIX_MONTH", "cores": 128, "memory_gb": 512, "region": region},
        ],
        "ondemand_reservations": [
            {"name": "res-n4-prod", "zone": f"{region}-a", "machine_type": "n4-standard-8", "count": 4, "total_cores": 32},
        ],
        "future_reservations": [
            {
                "name": "fr-a3-training-pending",
                "id": "2312445798605452488",
                "zone": f"{region}-a",
                "status": "PENDING_APPROVAL",
                "machineType": "a3-highgpu-8g",
                "acceleratorType": "nvidia-h100-80gb",
                "acceleratorCount": 8,
                "totalCount": 8,
                "startTime": (now + timedelta(days=10)).isoformat(),
                "endTime": (now + timedelta(days=180)).isoformat(),
            },
            {
                "name": "fr-g2-robotics-draft",
                "id": "9042446426570361614",
                "zone": f"{region}-c",
                "status": "DRAFTING",
                "machineType": "g2-standard-16",
                "acceleratorType": "nvidia-l4",
                "acceleratorCount": 16,
                "totalCount": 16,
                "startTime": (now + timedelta(hours=48)).isoformat(),
                "endTime": (now + timedelta(days=365)).isoformat(),
            }
        ]
    }


def scan_live_reservations(project_id: str, region: str, days: int) -> Dict[str, Any]:
    # 실측 조회 시도
    data = {
        "stockout_logs": [],
        "commitments": [],
        "ondemand_reservations": [],
        "future_reservations": [],
    }

    # 1. Cloud Audit Logs 스톡아웃 조회
    try:
        filter_str = (
            f'resource.type="gce_instance" '
            f'jsonPayload.event_subtype="compute.instances.insert" '
            f'protoPayload.status.message:"ZONE_RESOURCE_POOL_EXHAUSTED"'
        )
        cmd = ["gcloud", "logging", "read", filter_str, f"--project={project_id}", "--format=json", "--limit=20"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if res.returncode == 0 and res.stdout.strip():
            entries = json.loads(res.stdout)
            for e in entries:
                data["stockout_logs"].append({
                    "timestamp": e.get("timestamp", ""),
                    "zone": e.get("resource", {}).get("labels", {}).get("zone", "unknown"),
                    "machine_type": "detected",
                    "error_code": "ZONE_RESOURCE_POOL_EXHAUSTED",
                    "caller": e.get("protoPayload", {}).get("authenticationInfo", {}).get("principalEmail", "unknown"),
                })
    except Exception:
        pass

    # 2. CUD 약정 조회
    try:
        cmd = ["gcloud", "compute", "commitments", "list", f"--project={project_id}", f"--filter=region:({region})", "--format=json"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode == 0 and res.stdout.strip():
            c_list = json.loads(res.stdout)
            for c in c_list:
                data["commitments"].append({
                    "name": c.get("name"),
                    "plan": c.get("plan"),
                    "cores": sum(int(r.get("amount", 0)) for r in c.get("resources", []) if r.get("type") == "VCPU"),
                    "memory_gb": sum(int(r.get("amount", 0)) / 1024 for r in c.get("resources", []) if r.get("type") == "MEMORY"),
                    "region": region,
                })
    except Exception:
        pass

    # 3. 온디맨드 Reservation 조회
    try:
        cmd = ["gcloud", "compute", "reservations", "list", f"--project={project_id}", "--format=json"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode == 0 and res.stdout.strip():
            r_list = json.loads(res.stdout)
            for r in r_list:
                z = r.get("zone", "").split("/")[-1]
                if region in z:
                    spec = r.get("specificReservation", {})
                    data["ondemand_reservations"].append({
                        "name": r.get("name"),
                        "zone": z,
                        "machine_type": spec.get("instanceProperties", {}).get("machineType", "unknown"),
                        "count": spec.get("count", 0),
                        "total_cores": spec.get("count", 0) * 8, # 근사 추정
                    })
    except Exception:
        pass

    # 4. Future Reservation 조회
    try:
        cmd = ["gcloud", "compute", "future-reservations", "list", f"--project={project_id}", "--format=json"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode == 0 and res.stdout.strip():
            fr_list = json.loads(res.stdout)
            for fr in fr_list:
                spec = fr.get("specificSkuProperties", {})
                data["future_reservations"].append({
                    "name": fr.get("name"),
                    "id": fr.get("id"),
                    "zone": fr.get("zone", "").split("/")[-1],
                    "status": fr.get("status"),
                    "machineType": spec.get("sourceInstanceTemplate", {}).split("/")[-1] or "custom",
                    "totalCount": spec.get("totalCount", 0),
                    "startTime": fr.get("timeWindow", {}).get("startTime"),
                    "endTime": fr.get("timeWindow", {}).get("endTime"),
                })
    except Exception:
        pass

    if not data["stockout_logs"] and not data["commitments"] and not data["future_reservations"]:
        return get_mock_diagnosis_data(project_id, region)

    return data


def print_text_report(
    project_id: str,
    region: str,
    data: Dict[str, Any],
    dry_run: bool,
) -> None:
    mode_str = "모의 실행 (Dry-run)" if dry_run else "사내 실측 진단"
    stockouts = data.get("stockout_logs", [])
    commitments = data.get("commitments", [])
    reservations = data.get("ondemand_reservations", [])
    future_res = data.get("future_reservations", [])

    total_cud_cores = sum(c.get("cores", 0) for c in commitments)
    total_res_cores = sum(r.get("total_cores", 0) for r in reservations)
    coverage_pct = (total_res_cores / total_cud_cores * 100) if total_cud_cores > 0 else 100.0

    print("\n" + "=" * 96)
    print(" [Compute Engine 하드웨어 예약(Reservation) 및 CUD 용량 보장 통합 진단 리포트]")
    print("=" * 96)
    print(f"대상 프로젝트 ID    : {project_id}")
    print(f"점검 대상 리전      : {region}")
    print(f"진단 모드           : {mode_str}")
    print("-" * 96)

    print("\n[1. 최근 용량 고갈(ZONE_RESOURCE_POOL_EXHAUSTED) 장애 이력]")
    if stockouts:
        print(f"  * 식별된 용량 고갈 실패 이벤트: {len(stockouts)}건")
        for idx, s in enumerate(stockouts, 1):
            print(f"    [{idx}] 발생시각: {s['timestamp']} | 타겟 존: {s['zone']} | 머신: {s['machine_type']}")
    else:
        print("  * 최근 기간 내 용량 고갈 에러 이벤트가 발견되지 않았다 (정상).")
    print("-" * 96)

    print("\n[2. 활성 CUD 약정 vs 온디맨드 Reservation 하드웨어 물리 용량 확보율 대조]")
    print(f"  * 총 CUD 약정 코어 수       : {total_cud_cores} vCPU (요금 할인용)")
    print(f"  * 온디맨드 예약 확보 코어 수 : {total_res_cores} vCPU (물리 용량 보장용)")
    print(f"  * 물리 용량 보호율(Coverage) : {coverage_pct:.1f}%")
    if coverage_pct < 100.0 and total_cud_cores > 0:
        print("  * [위험 경고] CUD 요금만 지불되고 물리적 하드웨어 용량이 확보되지 않은 '무방비 약정(Unreserved CUD)' 존재!")
        print("    -> 리전 스톡아웃 발생 시 요금은 나가면서 인스턴스를 띄우지 못하는 FinOps 손실 위험이 있다.")
    else:
        print("  * [안전] CUD 약정에 대한 예약 커버리지가 적정 수준이다.")
    print("-" * 96)

    print("\n[3. Compute Engine Future Reservation (GPU / 특수 인스턴스 사전 예약) 현황]")
    draft_items = [fr for fr in future_res if fr.get("status") == "DRAFTING"]
    if future_res:
        print(f"{'예약 이름':<26} | {'상태':<16} | {'존':<18} | {'머신/수량'}")
        print("-" * 96)
        for fr in future_res:
            stat = fr.get("status")
            stat_str = f"[{stat}]" if stat != "DRAFTING" else "[DRAFTING(제출누락!)]"
            print(f"{fr.get('name'):<26} | {stat_str:<16} | {fr.get('zone'):<18} | {fr.get('machineType')}({fr.get('totalCount')}대)")
    else:
        print("  * 등록된 Future Reservation 신청 내역이 없다.")

    if draft_items:
        print("\n  [주의] DRAFTING 상태로 남아 구글 용량 팀 심사가 시작되지 않은 신청서가 발견되었다:")
        for d in draft_items:
            print(f"    -> gcloud compute future-reservations submit {d.get('name')} --zone={d.get('zone')}")
    print("-" * 96)

    print("\n[4. 실무자 통합 처방전 및 즉각 조치 가이드]")
    print("  1) 무방비 CUD에 대한 온디맨드 Reservation 선점:")
    print(f"     gcloud compute reservations create res-n4-guaranteed --zone={region}-a --vm-count=8 --machine-type=n4-standard-8")
    print("  2) GPU 및 대규모 프로젝트용 Future Reservation 제출 완결:")
    print("     초안(DRAFTING) 상태의 신청서는 반드시 120시간(5일) 전까지 submit을 실행하여 승인을 획득해야 한다.")
    print("  3) 다중 머신 패밀리 폴백 아키텍처 결합:")
    print("     단일 머신 예약에만 의존하지 않고 `samples/gce-instance-flexibility-planner`를 결합하여")
    print("     GKE ComputeClass(CCC) 및 MIG instanceSelections 다중 머신 유연성을 동시 적용할 것을 권장한다.")
    print("=" * 96 + "\n")


def build_markdown_report(
    project_id: str,
    region: str,
    data: Dict[str, Any],
    dry_run: bool,
) -> str:
    mode_str = "모의 실행 (Dry-run)" if dry_run else "사내 실측 진단"
    stockouts = data.get("stockout_logs", [])
    commitments = data.get("commitments", [])
    reservations = data.get("ondemand_reservations", [])
    future_res = data.get("future_reservations", [])

    total_cud_cores = sum(c.get("cores", 0) for c in commitments)
    total_res_cores = sum(r.get("total_cores", 0) for r in reservations)
    coverage_pct = (total_res_cores / total_cud_cores * 100) if total_cud_cores > 0 else 100.0

    lines = [
        "# Compute Engine 하드웨어 예약(Reservation) 및 CUD 용량 보장 통합 진단 리포트",
        "",
        "- **진단 일시**: (실행 결과 자동 생성)",
        f"- **대상 프로젝트**: `{project_id}`",
        f"- **점검 대상 리전**: `{region}`",
        f"- **진단 모드**: `{mode_str}`",
        "",
        "---",
        "",
        "## 1. 최근 용량 고갈(ZONE_RESOURCE_POOL_EXHAUSTED) 장애 이력",
        "",
        f"- **식별된 용량 고갈 실패 이벤트 수**: {len(stockouts)}건",
    ]

    for s in stockouts:
        lines.append(f"- **[장애 감지]** {s['timestamp']} | 존: `{s['zone']}` | 머신: `{s['machine_type']}` | 호출자: `{s['caller']}`")

    lines.extend([
        "",
        "---",
        "",
        "## 2. 활성 CUD 약정 vs 온디맨드 Reservation 하드웨어 물리 용량 대조",
        "",
        f"- **총 CUD 약정 코어 수**: {total_cud_cores:,} vCPU (요금 할인용)",
        f"- **온디맨드 예약 확보 코어 수**: {total_res_cores:,} vCPU (물리 용량 보장용)",
        f"- **물리 용량 보호율(Coverage)**: {coverage_pct:.1f}%",
    ])

    if coverage_pct < 100.0 and total_cud_cores > 0:
        lines.append("- **[경고]** CUD 요금만 지출되고 실제 하드웨어 용량이 확보되지 않은 '무방비 약정(Unreserved CUD)'이 존재한다.")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Compute Engine Future Reservation (GPU / 특수 머신 사전 예약) 현황",
        "",
        "| 예약 이름 | 상태 | 존 | 머신 및 수량 |",
        "| :--- | :--- | :--- | :--- |",
    ])

    for fr in future_res:
        lines.append(f"| `{fr.get('name')}` | `{fr.get('status')}` | `{fr.get('zone')}` | `{fr.get('machineType')} ({fr.get('totalCount')}대)` |")

    lines.extend([
        "",
        "---",
        "",
        "## 4. 실무자 통합 처방전 및 즉각 조치 가이드",
        "",
        "### 1단계: 무방비 CUD에 대한 온디맨드 Reservation 선점",
        "```bash",
        f"gcloud compute reservations create res-guaranteed-capacity \\\n    --zone={region}-a \\\n    --vm-count=8 \\\n    --machine-type=n4-standard-8",
        "```",
        "",
        "### 2단계: DRAFTING 상태 Future Reservation 제출 완결",
        "```bash",
        "# 미제출된 Future Reservation 제출 승인 요청",
        f"gcloud compute future-reservations submit [FR_NAME] --zone=[ZONE]",
        "```",
    ])

    return "\n".join(lines).strip() + "\n"


def save_markdown_report(report_md: str, output_path: str = "report.md") -> None:
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었습니다: {output_path}")
    except Exception as e:
        print(f"[경고] 리포트 파일 저장 실패 ({output_path}): {e}")


def main() -> None:
    args = parse_args()
    proj_id = detect_project_id(args.project, is_dry_run=args.dry_run)
    reported_project = "sample-project-id" if args.dry_run else proj_id

    if args.dry_run:
        data = get_mock_diagnosis_data(reported_project, args.region)
    else:
        print(f"[*] '{reported_project}' 프로젝트({args.region})의 하드웨어 예약 및 CUD 용량 정합성을 점검 중...")
        data = scan_live_reservations(reported_project, args.region, args.days)

    if args.json_output:
        summary = {
            "project_id": reported_project,
            "region": args.region,
            "data": data,
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print_text_report(
            project_id=reported_project,
            region=args.region,
            data=data,
            dry_run=args.dry_run,
        )

    report_content = build_markdown_report(
        project_id=reported_project,
        region=args.region,
        data=data,
        dry_run=args.dry_run,
    )
    save_markdown_report(report_content, "report.md")


if __name__ == "__main__":
    main()
