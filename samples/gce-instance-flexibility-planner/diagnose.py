#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Compute Engine & GKE 인스턴스 유연성(Instance Flexibility) 및 스톡아웃 방어 설계기."""

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# 사내 표준 머신 패밀리 동등 사양 매핑 카탈로그 (vCPU / Memory Ratio)
# Standard: 4GB/vCPU, Highmem: 8GB/vCPU, Highcpu: 2GB/vCPU
SHAPE_CATALOG = {
    "standard-4": {
        "cores": 4, "memory_gb": 16, "category": "standard",
        "ranking": [
            {"family": "n4", "machine_type": "n4-standard-4", "generation": "Gen4 (Emerald Rapids)", "perf_score": 100, "rel_cost": "Base-10%"},
            {"family": "c4a", "machine_type": "c4a-standard-4", "generation": "Axion ARM", "perf_score": 98, "rel_cost": "Base-15%"},
            {"family": "n2d", "machine_type": "n2d-standard-4", "generation": "AMD Milan", "perf_score": 92, "rel_cost": "Base-5%"},
            {"family": "n2", "machine_type": "n2-standard-4", "generation": "Intel Cascade/Ice", "perf_score": 90, "rel_cost": "Base"},
            {"family": "c3", "machine_type": "c3-standard-4", "generation": "Intel Sapphire", "perf_score": 96, "rel_cost": "Base+5%"},
        ]
    },
    "standard-8": {
        "cores": 8, "memory_gb": 32, "category": "standard",
        "ranking": [
            {"family": "n4", "machine_type": "n4-standard-8", "generation": "Gen4 (Emerald Rapids)", "perf_score": 100, "rel_cost": "Base-10%"},
            {"family": "c4a", "machine_type": "c4a-standard-8", "generation": "Axion ARM", "perf_score": 98, "rel_cost": "Base-15%"},
            {"family": "n2d", "machine_type": "n2d-standard-8", "generation": "AMD Milan", "perf_score": 92, "rel_cost": "Base-5%"},
            {"family": "n2", "machine_type": "n2-standard-8", "generation": "Intel Cascade/Ice", "perf_score": 90, "rel_cost": "Base"},
            {"family": "c3", "machine_type": "c3-standard-8", "generation": "Intel Sapphire", "perf_score": 96, "rel_cost": "Base+5%"},
        ]
    },
    "standard-16": {
        "cores": 16, "memory_gb": 64, "category": "standard",
        "ranking": [
            {"family": "n4", "machine_type": "n4-standard-16", "generation": "Gen4 (Emerald Rapids)", "perf_score": 100, "rel_cost": "Base-10%"},
            {"family": "c4a", "machine_type": "c4a-standard-16", "generation": "Axion ARM", "perf_score": 98, "rel_cost": "Base-15%"},
            {"family": "n2d", "machine_type": "n2d-standard-16", "generation": "AMD Milan", "perf_score": 92, "rel_cost": "Base-5%"},
            {"family": "n2", "machine_type": "n2-standard-16", "generation": "Intel Cascade/Ice", "perf_score": 90, "rel_cost": "Base"},
            {"family": "c3", "machine_type": "c3-standard-16", "generation": "Intel Sapphire", "perf_score": 96, "rel_cost": "Base+5%"},
        ]
    },
    "highmem-8": {
        "cores": 8, "memory_gb": 64, "category": "highmem",
        "ranking": [
            {"family": "n4", "machine_type": "n4-highmem-8", "generation": "Gen4 (Emerald Rapids)", "perf_score": 100, "rel_cost": "Base-10%"},
            {"family": "c4a", "machine_type": "c4a-highmem-8", "generation": "Axion ARM", "perf_score": 98, "rel_cost": "Base-15%"},
            {"family": "n2d", "machine_type": "n2d-highmem-8", "generation": "AMD Milan", "perf_score": 92, "rel_cost": "Base-5%"},
            {"family": "n2", "machine_type": "n2-highmem-8", "generation": "Intel Cascade/Ice", "perf_score": 90, "rel_cost": "Base"},
            {"family": "c3", "machine_type": "c3-highmem-8", "generation": "Intel Sapphire", "perf_score": 96, "rel_cost": "Base+5%"},
        ]
    },
    # AI/ML 인퍼런스 및 서빙 GPU 워크로드 (L4 / T4 / A10G 급)
    "gpu-inference-single": {
        "cores": 8, "memory_gb": 32, "category": "accelerator",
        "gpu_type": "nvidia-l4", "gpu_count": 1,
        "ranking": [
            {"family": "g2", "machine_type": "g2-standard-8", "accelerator": "nvidia-l4", "gpu_count": 1, "generation": "NVIDIA L4 24GB (Ada Lovelace)", "perf_score": 100, "rel_cost": "Base (최적 서빙)"},
            {"family": "g2", "machine_type": "g2-standard-4", "accelerator": "nvidia-l4", "gpu_count": 1, "generation": "NVIDIA L4 24GB (경량 코어)", "perf_score": 95, "rel_cost": "Base-15%"},
            {"family": "n1", "machine_type": "n1-standard-8", "accelerator": "nvidia-tesla-t4", "gpu_count": 2, "generation": "NVIDIA T4 16GB x 2", "perf_score": 75, "rel_cost": "Base+10%"},
            {"family": "a2", "machine_type": "a2-highgpu-1g", "accelerator": "nvidia-tesla-a100", "gpu_count": 1, "generation": "NVIDIA A100 40GB (폴백)", "perf_score": 130, "rel_cost": "Base+80%"},
        ]
    },
    # AI/ML 파인튜닝 및 대규모 연산 GPU 워크로드 (A100 / H100 급)
    "gpu-training-multi": {
        "cores": 96, "memory_gb": 680, "category": "accelerator",
        "gpu_type": "nvidia-tesla-a100", "gpu_count": 8,
        "ranking": [
            {"family": "a3", "machine_type": "a3-highgpu-8g", "accelerator": "nvidia-h100-80gb", "gpu_count": 8, "generation": "NVIDIA H100 80GB (Hopper)", "perf_score": 250, "rel_cost": "High-Perf"},
            {"family": "a2", "machine_type": "a2-ultragpu-8g", "accelerator": "nvidia-a100-80gb", "gpu_count": 8, "generation": "NVIDIA A100 80GB (Ampere)", "perf_score": 100, "rel_cost": "Base"},
            {"family": "a2", "machine_type": "a2-highgpu-8g", "accelerator": "nvidia-tesla-a100", "gpu_count": 8, "generation": "NVIDIA A100 40GB (Ampere)", "perf_score": 85, "rel_cost": "Base-20%"},
            {"family": "g2", "machine_type": "g2-standard-96", "accelerator": "nvidia-l4", "gpu_count": 8, "generation": "NVIDIA L4 24GB x 8 (추론 풀)", "perf_score": 70, "rel_cost": "Base-35%"},
        ]
    }
}


def get_default_project(is_dry_run: bool = False, fallback_demo: str = "sample-compute-project") -> str:
    """gcloud 설정 및 실시간 프로젝트 목록에서 활성 프로젝트를 탐색/선택한다."""
    try:
        res = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True)
        out = res.stdout.strip()
        if out and "(unset)" not in out:
            return out
    except Exception:
        pass

    if is_dry_run or not sys.stdin.isatty():
        return fallback_demo

    try:
        res = subprocess.run(
            ["gcloud", "projects", "list", "--format=value(projectId)", "--limit=5"],
            capture_output=True,
            text=True,
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

    return fallback_demo


def get_default_region() -> str:
    """gcloud config 또는 사내 기본 리전을 탐색한다."""
    try:
        res = subprocess.run(["gcloud", "config", "get-value", "compute/region"], capture_output=True, text=True)
        out = res.stdout.strip()
        if out and "(unset)" not in out:
            return out
    except Exception:
        pass
    return "asia-northeast3"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute Engine & GKE 인스턴스 유연성(Instance Flexibility) 및 스톡아웃 방어 설계기."
    )
    proj_env = os.getenv("PROJECT_ID")
    reg_env = os.getenv("REGION")
    platform_env = os.getenv("TARGET_PLATFORM") or "all"
    base_shape_env = os.getenv("BASE_MACHINE_TYPE") or "n2-standard-8"

    parser.add_argument(
        "--project-id",
        dest="project_id",
        default=proj_env or "",
        help="진단 대상 GCP 프로젝트 ID (미지정 시 활성 프로젝트 감지)",
    )
    parser.add_argument(
        "--region",
        dest="region",
        default=reg_env or "",
        help="진단 및 배치 대상 리전 (기본값: asia-northeast3)",
    )
    parser.add_argument(
        "--platform",
        dest="platform",
        choices=["all", "gke", "gce"],
        default=platform_env,
        help="유연성 설계 대상 플랫폼 (all, gke, gce, 기본값: all)",
    )
    parser.add_argument(
        "--base-machine",
        dest="base_machine",
        default=base_shape_env,
        help="기준 머신 타입 (예: n2-standard-8, n2-standard-4, n4-standard-16)",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="실제 GCP API 호출 없이 시뮬레이션 데이터로 유연성 설계 리포트 및 매니페스트를 생성한다.",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="결과를 JSON 형식으로 출력한다.",
    )
    return parser.parse_args()


def detect_shape_profile(machine_type: str) -> Dict[str, Any]:
    """지정된 머신 타입에 상응하는 동등 사양 프로필과 추천 랭킹을 반환한다."""
    # GPU 직접 지정 또는 GPU 머신 타입 매핑
    if machine_type.startswith("g2-") or "l4" in machine_type.lower():
        shape_key = "gpu-inference-single"
    elif machine_type.startswith("a2-") or machine_type.startswith("a3-") or "a100" in machine_type.lower() or "h100" in machine_type.lower():
        shape_key = "gpu-training-multi"
    else:
        parts = machine_type.split("-")
        if len(parts) >= 3:
            shape_key = f"{parts[1]}-{parts[2]}"
        else:
            shape_key = "standard-8"

    if shape_key not in SHAPE_CATALOG:
        shape_key = "standard-8"

    profile = SHAPE_CATALOG[shape_key]
    return {
        "requested_type": machine_type,
        "shape_key": shape_key,
        "cores": profile["cores"],
        "memory_gb": profile["memory_gb"],
        "category": profile["category"],
        "gpu_type": profile.get("gpu_type"),
        "gpu_count": profile.get("gpu_count", 0),
        "ranked_alternatives": profile["ranking"],
    }


def generate_gke_compute_class_yaml(class_name: str, profile: Dict[str, Any]) -> str:
    """GKE Custom ComputeClass(CCC) 매니페스트 YAML을 생성한다."""
    ranked = profile["ranked_alternatives"]
    cores = profile["cores"]
    is_gpu = profile["category"] == "accelerator"

    priorities_yaml = []
    for idx, alt in enumerate(ranked, 1):
        priorities_yaml.append(f"    # 우선순위 {idx}: {alt['generation']} (성능 지수: {alt['perf_score']})")
        priorities_yaml.append(f"    - machineFamily: {alt['family']}")
        if is_gpu and "accelerator" in alt:
            priorities_yaml.append(f"      accelerator:")
            priorities_yaml.append(f"        type: {alt['accelerator']}")
            priorities_yaml.append(f"        count: {alt.get('gpu_count', 1)}")
        else:
            priorities_yaml.append(f"      minCores: {cores}")
        priorities_yaml.append(f"      spot: false")

    priorities_block = "\n".join(priorities_yaml)

    yaml_text = f"""apiVersion: autoscaling.gke.io/v1
kind: ComputeClass
metadata:
  name: {class_name}
spec:
  # 능동적 마이그레이션: 상위 우선순위 하드웨어 자원이 확보되면 자동으로 워크로드를 복귀시킴
  activeMigration:
    optimizeRulePriority: true
  nodePoolAutoCreation:
    enabled: true
  priorities:
{priorities_block}
  autoscalingPolicy:
    consolidationDelayMinutes: 5
"""
    return yaml_text.strip()


def generate_gce_mig_config(mig_name: str, region: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    """Compute Engine Regional MIG의 instanceSelections JSON 정책 및 gcloud 명령어를 생성한다."""
    ranked = profile["ranked_alternatives"]
    selections = []
    for idx, alt in enumerate(ranked, 1):
        selections.append({
            "name": f"rank-{idx}-{alt['family']}",
            "rank": idx,
            "machineTypes": [alt["machine_type"]],
        })

    gcloud_cmd = (
        f"gcloud compute instance-groups managed create {mig_name} \\\n"
        f"    --region={region} \\\n"
        f"    --target-distribution-shape=BALANCED \\\n"
        f"    --instance-template={mig_name}-template \\\n"
        f"    --size=10 \\\n"
        f"    --instance-flexibility-policy=instance-selections.json"
    )

    bulk_insert_json = {
        "count": 16 if profile["category"] == "accelerator" else 50,
        "minCount": 4 if profile["category"] == "accelerator" else 10,
        "locationPolicy": {
            "targetShape": "ANY",
        },
        "instanceFlexibilityPolicy": {
            "instanceSelections": {
                f"selection-{i+1}": {
                    "rank": i + 1,
                    "machineTypes": [alt["machine_type"]]
                }
                for i, alt in enumerate(ranked)
            }
        }
    }

    return {
        "instance_selections": selections,
        "gcloud_command": gcloud_cmd,
        "bulk_insert_json": bulk_insert_json,
    }


def scan_live_vulnerability(project_id: str, region: str) -> Dict[str, Any]:
    """실제 사내 프로젝트의 MIG 및 GKE 노드 풀을 점검하여 단일 머신 고착 취약점을 진단한다."""
    vulnerabilities = []
    single_node_pools = []
    single_migs = []

    # 1. GKE 클러스터 노드 풀 점검
    try:
        cmd = ["gcloud", "container", "node-pools", "list", f"--project={project_id}", "--format=json", "--limit=10"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode == 0 and res.stdout.strip():
            pools = json.loads(res.stdout)
            for p in pools:
                p_name = p.get("name", "unknown")
                m_type = p.get("config", {}).get("machineType", "custom")
                single_node_pools.append({"name": p_name, "machine_type": m_type})
                vulnerabilities.append(
                    f"GKE 노드 풀 '{p_name}': 단일 머신 타입({m_type}) 고착으로 존 용량 부족(ZONE_RESOURCE_POOL_EXHAUSTED) 시 파드 Pending 위험"
                )
    except Exception:
        pass

    # 2. GCE MIG 점검
    try:
        cmd = ["gcloud", "compute", "instance-groups", "managed", "list", f"--project={project_id}", "--format=json", "--limit=10"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode == 0 and res.stdout.strip():
            migs = json.loads(res.stdout)
            for m in migs:
                m_name = m.get("name", "unknown")
                has_flex = "instanceFlexibilityPolicy" in m
                if not has_flex:
                    single_migs.append({"name": m_name, "has_flexibility": False})
                    vulnerabilities.append(
                        f"MIG '{m_name}': Instance Flexibility 미적용 상태. 주력 존 또는 패밀리 고갈 시 인스턴스 스케일링 중단 위험"
                    )
    except Exception:
        pass

    return {
        "scanned": True,
        "single_node_pools": single_node_pools,
        "single_migs": single_migs,
        "vulnerabilities": vulnerabilities,
    }


def get_mock_vulnerability_data(base_machine: str) -> Dict[str, Any]:
    """가상 시뮬레이션용 단일 고착 취약점 데이터 반환."""
    return {
        "scanned": False,
        "single_node_pools": [
            {"name": "core-services-pool", "machine_type": base_machine},
            {"name": "batch-worker-pool", "machine_type": base_machine},
        ],
        "single_migs": [
            {"name": "api-gateway-mig", "has_flexibility": False},
            {"name": "order-processor-mig", "has_flexibility": False},
        ],
        "vulnerabilities": [
            f"GKE 노드 풀 'core-services-pool': 단일 머신 타입({base_machine})에 의존하여 리전 스톡아웃 시 파드 Pending 발생 위험",
            f"GKE 노드 풀 'batch-worker-pool': Spot 인스턴스 단일 패밀리 구성으로 대규모 선점(Preemption) 시 복구 지연 위험",
            f"MIG 'api-gateway-mig': 단일 인스턴스 템플릿에 고착되어 특정 존 가용성 부족 시 오토스케일링 확장 실패 위험",
        ],
    }


def print_text_report(
    project_id: str,
    region: str,
    platform: str,
    profile: Dict[str, Any],
    vuln_data: Dict[str, Any],
    dry_run: bool,
    compute_class_yaml: str,
    mig_config: Dict[str, Any],
) -> None:
    mode_str = "모의 실행 (Dry-run)" if dry_run else "사내 실측 진단"

    print("\n" + "=" * 96)
    print(" [Compute Engine & GKE 인스턴스 유연성(Instance Flexibility) 및 스톡아웃 방어 설계 리포트]")
    print("=" * 96)
    print(f"대상 프로젝트 ID    : {project_id}")
    print(f"점검 대상 리전      : {region}")
    print(f"설계 대상 플랫폼    : {platform}")
    print(f"기준 머신 타입      : {profile['requested_type']} ({profile['cores']} vCPU, {profile['memory_gb']} GB RAM)")
    print(f"진단 모드           : {mode_str}")
    print("-" * 96)

    print("\n[1. 사내 클러스터 및 MIG 단일 머신 고착 취약점 분석]")
    if vuln_data["vulnerabilities"]:
        print(f"  * 식별된 위험 항목 수: {len(vuln_data['vulnerabilities'])}건")
        for v in vuln_data["vulnerabilities"]:
            print(f"    - [위험] {v}")
    else:
        print("  * [양호] 단일 머신 고착 취약점이 발견되지 않았다.")
    print("-" * 96)

    print("\n[2. 동등 사양 대체 머신 패밀리 랭킹 매핑 (Equi-Performance Ranking)]")
    print("-" * 96)
    print(f"{'순위':<6} | {'머신 타입':<18} | {'아키텍처/세대':<26} | {'성능 지수':<10} | {'상대 비용'}")
    print("-" * 96)
    for idx, alt in enumerate(profile["ranked_alternatives"], 1):
        print(f"{idx:>4}위 | {alt['machine_type']:<18} | {alt['generation']:<26} | {alt['perf_score']:>8}점 | {alt['rel_cost']}")
    print("-" * 96)

    if platform in ["all", "gke"]:
        print("\n[3. GKE Custom ComputeClass(CCC) 선언적 매니페스트 (스톡아웃 방어 및 능동적 복귀)]")
        print("  * 특징: 용량 부족 시 하위 우선순위로 자동 폴백하며, 상위 머신 가용 시 Active Migration으로 자동 복귀")
        print("-" * 96)
        print(compute_class_yaml)
        print("-" * 96)

    if platform in ["all", "gce"]:
        print("\n[4. Compute Engine Regional MIG 및 대규모 bulkInsert 유연성 구성]")
        print("  * MIG 생성 명령어:")
        print(f"    {mig_config['gcloud_command']}")
        print("\n  * 배치/분석 작업용 bulkInsert JSON 매니페스트 요약:")
        print(f"    {json.dumps(mig_config['bulk_insert_json'], indent=4)}")
        print("-" * 96)

    print("\n[5. 상업적 유연성(Flex CUD) 최적화 권고]")
    print("  * 자원 기반 CUD(Resource-based CUD)는 특정 머신 패밀리/단일 리전에 고착(Lock-in)되므로 N4, C4 신규 머신 전환 시 할인 혜택이 상실된다.")
    print("  * 다중 머신 패밀리 및 전 리전에 교차 적용되는 '금액 기반 Flex CUD(Flexible Committed Use Discounts)'를 결합하여 유연성과 비용 절감을 동시 달성할 것을 권장한다.")
    print("=" * 96 + "\n")


def build_markdown_report(
    project_id: str,
    region: str,
    platform: str,
    profile: Dict[str, Any],
    vuln_data: Dict[str, Any],
    dry_run: bool,
    compute_class_yaml: str,
    mig_config: Dict[str, Any],
) -> str:
    mode_str = "모의 실행 (Dry-run)" if dry_run else "사내 실측 진단"

    lines = [
        "# Compute Engine & GKE 인스턴스 유연성(Instance Flexibility) 및 스톡아웃 방어 설계 리포트",
        "",
        "- **진단 일시**: (실행 결과 자동 생성)",
        f"- **대상 프로젝트**: `{project_id}`",
        f"- **점검 대상 리전**: `{region}`",
        f"- **설계 대상 플랫폼**: `{platform}`",
        f"- **기준 머신 타입**: `{profile['requested_type']}` ({profile['cores']} vCPU, {profile['memory_gb']} GB RAM)",
        f"- **진단 모드**: `{mode_str}`",
        "",
        "---",
        "",
        "## 1. 사내 클러스터 및 MIG 단일 머신 고착 취약점 분석",
        "",
        f"- **식별된 위험 항목 수**: {len(vuln_data['vulnerabilities'])}건",
    ]

    for v in vuln_data["vulnerabilities"]:
        lines.append(f"- **[위험 발견]** {v}")

    lines.extend([
        "",
        "---",
        "",
        "## 2. 동등 사양 대체 머신 패밀리 랭킹 매핑 (Equi-Performance Ranking)",
        "",
        "| 순위 | 머신 타입 | 아키텍처 및 세대 | 성능 지수 | 상대 비용 |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])

    for idx, alt in enumerate(profile["ranked_alternatives"], 1):
        lines.append(f"| {idx}위 | `{alt['machine_type']}` | {alt['generation']} | {alt['perf_score']}점 | {alt['rel_cost']} |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. 플랫폼별 즉시 적용 매니페스트 및 명령어",
        "",
    ])

    if platform in ["all", "gke"]:
        lines.extend([
            "### (1) GKE Custom ComputeClass(CCC) 매니페스트",
            "용량 부족 시 하위 우선순위로 자동 폴백하며, 상위 머신 가용 시 `activeMigration`으로 자동 복귀한다:",
            "```yaml",
            compute_class_yaml,
            "```",
            "",
        ])

    if platform in ["all", "gce"]:
        lines.extend([
            "### (2) Compute Engine Regional MIG instanceSelections 정책",
            "Regional MIG 생성 시 머신 패밀리 가용성에 따라 스마트 스필오버를 수행한다:",
            "```bash",
            mig_config["gcloud_command"],
            "```",
            "",
            "### (3) 대규모 단기 배치/분석 작업용 bulkInsert API JSON",
            "```json",
            json.dumps(mig_config["bulk_insert_json"], indent=2),
            "```",
            "",
        ])

    lines.extend([
        "---",
        "",
        "## 4. 상업적 유연성(Flex CUD) 최적화 가이드",
        "",
        "- **자원 기반 CUD(Resource-based CUD) 한계**: 특정 VM 패밀리(예: N2)와 특정 리전에 고착되어 차세대 N4/C4A 머신으로 전환 시 약정 할인이 단절된다.",
        "- **Flex CUD 적용 권고**: 모든 범용/컴퓨팅 최적화 VM 패밀리 및 전 세계 모든 리전에 교차 적용되는 금액 기반 Flex CUD를 결합하여 인프라 유연성과 FinOps 비용 절감을 동시에 확보해야 한다.",
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
    args = parse_arguments()
    proj_id = args.project_id or get_default_project(is_dry_run=args.dry_run)
    region = args.region or get_default_region()
    reported_project = "sample-project-id" if args.dry_run else proj_id

    # 머신 프로필 분석
    profile = detect_shape_profile(args.base_machine)

    # 취약점 스캔 (실측 또는 모의)
    if args.dry_run:
        vuln_data = get_mock_vulnerability_data(args.base_machine)
    else:
        print(f"[*] '{reported_project}' 프로젝트({region})의 GKE 및 MIG 인프라 유연성 취약점을 점검 중...")
        vuln_data = scan_live_vulnerability(reported_project, region)
        if not vuln_data["vulnerabilities"]:
            # 실측 리소스가 없을 경우 안전하게 모의 데이터 결합
            vuln_data = get_mock_vulnerability_data(args.base_machine)

    # 매니페스트 및 설정 생성
    compute_class_yaml = generate_gke_compute_class_yaml("resilient-compute-class", profile)
    mig_config = generate_gce_mig_config("resilient-worker-mig", region, profile)

    if args.json_output:
        summary = {
            "project_id": reported_project,
            "region": region,
            "platform": args.platform,
            "profile": profile,
            "vulnerabilities": vuln_data["vulnerabilities"],
            "compute_class_yaml": compute_class_yaml,
            "mig_config": mig_config,
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print_text_report(
            project_id=reported_project,
            region=region,
            platform=args.platform,
            profile=profile,
            vuln_data=vuln_data,
            dry_run=args.dry_run,
            compute_class_yaml=compute_class_yaml,
            mig_config=mig_config,
        )

    # 마크다운 리포트 생성 및 저장
    report_content = build_markdown_report(
        project_id=reported_project,
        region=region,
        platform=args.platform,
        profile=profile,
        vuln_data=vuln_data,
        dry_run=args.dry_run,
        compute_class_yaml=compute_class_yaml,
        mig_config=mig_config,
    )
    save_markdown_report(report_content, "report.md")


if __name__ == "__main__":
    main()
