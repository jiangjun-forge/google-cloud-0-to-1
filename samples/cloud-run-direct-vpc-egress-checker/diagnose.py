#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
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

"""Cloud Run Direct VPC Egress 구성 및 네트워크 연결성 진단 도구."""

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional


def parse_args() -> argparse.Namespace:
    """명령줄 인자를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="Cloud Run Direct VPC Egress 구성 및 네트워크 연결성 진단기"
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
        help="Cloud Run 배포 리전 (기본값: asia-northeast3)",
    )
    parser.add_argument(
        "-s",
        "--service",
        default=os.getenv("SERVICE_NAME", ""),
        help="점검 대상 Cloud Run 서비스 이름 (지정하지 않을 경우 리전 내 전수 점검)",
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
        return "demo-vpc-egress-project"

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

    return "demo-vpc-egress-project"


def get_mock_services() -> List[Dict[str, Any]]:
    """가상 실행용 모의 Cloud Run 서비스 구성 데이터를 반환한다."""
    return [
        {
            "name": "order-api-prod",
            "region": "asia-northeast3",
            "egress_type": "CONNECTOR",
            "connector": "projects/demo-vpc-egress-project/locations/asia-northeast3/connectors/legacy-vpc-conn",
            "network": "vpc-production",
            "subnetwork": "",
            "vpc_egress": "private-ranges-only",
            "max_scale": 80,
            "subnet_cidr": "",
            "subnet_pga": False,
            "has_nat": True,
            "status": "WARNING",
            "detail": "레거시 Serverless VPC Access 커넥터 사용 중, 대역폭 병목 및 커넥터 유휴 비용 발생 (Direct VPC Egress 전환 권장)",
        },
        {
            "name": "payment-gateway-prod",
            "region": "asia-northeast3",
            "egress_type": "DIRECT_VPC",
            "connector": "",
            "network": "vpc-production",
            "subnetwork": "sub-run-prod-01",
            "vpc_egress": "private-ranges-only",
            "max_scale": 120,
            "subnet_cidr": "10.10.1.0/28",
            "subnet_pga": False,
            "has_nat": True,
            "status": "CRITICAL",
            "detail": "서브넷 가용 IP 부족(/28 대역, 가용 IP 11개 < 최대 인스턴스 120개) 및 Private Google Access 미활성화",
        },
        {
            "name": "analytics-collector-prod",
            "region": "asia-northeast3",
            "egress_type": "DIRECT_VPC",
            "connector": "",
            "network": "vpc-production",
            "subnetwork": "sub-run-prod-02",
            "vpc_egress": "all-traffic",
            "max_scale": 40,
            "subnet_cidr": "10.10.2.0/24",
            "subnet_pga": True,
            "has_nat": False,
            "status": "CRITICAL",
            "detail": "모든 아웃바운드 트래픽(all-traffic)을 VPC로 라우팅 중이나 Cloud NAT 게이트웨이가 없어 외부 API 통신 전면 실패 위험",
        },
        {
            "name": "user-auth-service-prod",
            "region": "asia-northeast3",
            "egress_type": "DIRECT_VPC",
            "connector": "",
            "network": "vpc-production",
            "subnetwork": "sub-run-prod-03",
            "vpc_egress": "private-ranges-only",
            "max_scale": 50,
            "subnet_cidr": "10.10.3.0/24",
            "subnet_pga": True,
            "has_nat": True,
            "status": "OK",
            "detail": "Direct VPC Egress 정상 구성 (충분한 /24 대역 IP, Private Google Access 활성화, 온프레미스 연동 완료)",
        },
    ]


def run_gcloud_json(cmd: List[str]) -> Optional[Any]:
    """gcloud 명령어를 실행하고 JSON 결과를 반환한다."""
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except Exception:
        return None


def inspect_cloud_run(project_id: str, region: str, target_service: str) -> List[Dict[str, Any]]:
    """실제 GCP 환경의 Cloud Run 서비스 및 서브넷 구성을 점검한다."""
    cmd = [
        "gcloud",
        "run",
        "services",
        "list",
        f"--project={project_id}",
        f"--region={region}",
        "--format=json",
    ]
    raw_services = run_gcloud_json(cmd)
    if not raw_services:
        return []

    results = []
    for svc in raw_services:
        metadata = svc.get("metadata", {})
        svc_name = metadata.get("name", "")
        if target_service and svc_name != target_service:
            continue

        spec = svc.get("spec", {}).get("template", {})
        spec_metadata = spec.get("metadata", {})
        spec_annotations = spec_metadata.get("annotations", {})

        connector = spec_annotations.get("run.googleapis.com/vpc-access-connector", "")
        vpc_egress = spec_annotations.get("run.googleapis.com/vpc-access-egress", "private-ranges-only")
        max_scale_str = spec_annotations.get("autoscaling.knative.dev/maxScale", "100")
        try:
            max_scale = int(max_scale_str)
        except ValueError:
            max_scale = 100

        network = spec_annotations.get("run.googleapis.com/network-interfaces", "")
        network_dict = {}
        if network:
            try:
                network_dict = json.loads(network)
            except Exception:
                pass

        net_name = network_dict.get("network", "")
        subnet_name = network_dict.get("subnetwork", "")

        egress_type = "DIRECT_VPC" if (net_name or subnet_name) else ("CONNECTOR" if connector else "NONE")

        subnet_pga = False
        subnet_cidr = ""
        has_nat = False
        status = "OK"
        detail = "정상 구성"

        if egress_type == "DIRECT_VPC" and subnet_name:
            sub_info = run_gcloud_json([
                "gcloud", "compute", "networks", "subnets", "describe",
                subnet_name, f"--region={region}", f"--project={project_id}", "--format=json"
            ])
            if sub_info:
                subnet_cidr = sub_info.get("ipCidrRange", "")
                subnet_pga = sub_info.get("privateIpGoogleAccess", False)

            nat_info = run_gcloud_json([
                "gcloud", "compute", "routers", "nats", "list",
                f"--region={region}", f"--project={project_id}", "--format=json"
            ])
            if nat_info:
                has_nat = len(nat_info) > 0

            if not subnet_pga:
                status = "WARNING"
                detail = "서브넷 Private Google Access 비활성화 (구글 API 직접 통신 장애 위험)"
            if vpc_egress == "all-traffic" and not has_nat:
                status = "CRITICAL"
                detail = "all-traffic 설정 시 VPC Cloud NAT 부재로 외부 인터넷 통신 불가"
        elif egress_type == "CONNECTOR":
            status = "WARNING"
            detail = "Serverless VPC Access 커넥터 사용 중 (Direct VPC Egress 전환 권장)"
        elif egress_type == "NONE":
            status = "INFO"
            detail = "VPC 연동 없음 (공개 인터넷 기본 라우팅)"

        results.append({
            "name": svc_name,
            "region": region,
            "egress_type": egress_type,
            "connector": connector,
            "network": net_name,
            "subnetwork": subnet_name,
            "vpc_egress": vpc_egress,
            "max_scale": max_scale,
            "subnet_cidr": subnet_cidr,
            "subnet_pga": subnet_pga,
            "has_nat": has_nat,
            "status": status,
            "detail": detail,
        })
    return results


def print_report(project_id: str, region: str, is_dry_run: bool, services: List[Dict[str, Any]]) -> None:
    """진단 리포트를 출력한다."""
    print("=" * 80)
    print("Cloud Run Direct VPC Egress 구성 및 네트워크 연결성 진단 리포트")
    print(f"진단 모드: {'가상 실행 (Dry-run)' if is_dry_run else '실제 환경 점검'}")
    print(f"대상 프로젝트: {project_id}")
    print(f"대상 리전: {region}")
    print(f"점검 대상 서비스 수: {len(services)}개")
    print("=" * 80)
    print()

    print("[1단계] Cloud Run 서비스별 VPC 이그레스 아키텍처 현황")
    print("-" * 80)
    print(f"{'서비스 이름':<24} {'이그레스 방식':<14} {'트래픽 범위':<18} {'상태':<10}")
    print("-" * 80)
    for svc in services:
        print(f"{svc['name']:<24} {svc['egress_type']:<14} {svc['vpc_egress']:<18} {svc['status']:<10}")
    print("-" * 80)
    print()

    print("[2단계] 서브넷 IP 고갈 위험 및 네트워크 라우팅 세부 진단")
    print("-" * 80)
    for svc in services:
        print(f"- 서비스: {svc['name']}")
        print(f"  * 연동 방식: {svc['egress_type']}")
        if svc['connector']:
            print(f"  * VPC 커넥터: {svc['connector']}")
        if svc['subnetwork']:
            print(f"  * 대상 서브넷: {svc['subnetwork']} (대역: {svc['subnet_cidr'] or '확인 불가'})")
            print(f"  * Private Google Access: {'활성화 (OK)' if svc['subnet_pga'] else '비활성화 (경고)'}")
            print(f"  * Cloud NAT 구비 여부: {'구성됨 (OK)' if svc['has_nat'] else '미구성 (위험)'}")
            print(f"  * 최대 인스턴스(maxScale): {svc['max_scale']}개")
        print(f"  * 진단 결과: [{svc['status']}] {svc['detail']}")
        print()
    print("-" * 80)
    print()

    print("[3단계] 아키텍처 현대화 및 즉각 조치 처방")
    print("1. Serverless VPC Access 커넥터에서 Direct VPC Egress 로 전환:")
    print("   gcloud run services update <SERVICE_NAME> \\")
    print(f"     --region={region} \\")
    print("     --network=<VPC_NETWORK> \\")
    print("     --subnetwork=<SUBNET_NAME> \\")
    print("     --vpc-egress=private-ranges-only \\")
    print("     --clear-vpc-connector \\")
    print("     --labels=managed-by=google-cloud-0-to-1,scenario=cloud-run-direct-vpc-egress-checker,env=sample,created-by=customer-engineer")
    print()
    print("2. 서브넷 Private Google Access 활성화 (구글 API 직결 보장):")
    print("   gcloud compute networks subnets update <SUBNET_NAME> \\")
    print(f"     --region={region} \\")
    print("     --enable-private-ip-google-access")
    print()
    print("3. all-traffic 라우팅 시 외부 통신용 Cloud NAT 생성:")
    print(f"   gcloud compute routers create nat-router --network=<VPC_NETWORK> --region={region}")
    print(f"   gcloud compute routers nats create nat-gw --router=nat-router --auto-allocate-nat-external-ips --region={region}")
    print()
    print("4. 사내 거버넌스 4대 필수 표준 라벨링 준수:")
    print("   Cloud Run 서비스 및 네트워크 자원 생성 시 FinOps 추적을 위해 4대 표준 라벨을 필수 결합한다.")
    print("=" * 80)


def build_markdown_report(
    project_id: str, region: str, is_dry_run: bool, services: List[Dict[str, Any]]
) -> str:
    """진단 결과를 표준 마크다운 리포트로 구성한다."""
    mode_str = "모의 실행 (Dry-run)" if is_dry_run else "사내 실측 진단"

    lines = [
        "# 진단 및 분석 리포트: cloud-run-direct-vpc-egress-checker",
        "",
        f"- **생성 모드**: {mode_str}",
        f"- **대상 프로젝트**: `{project_id}`",
        "- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용",
        "",
        "---",
        "",
        "## 1. 진단 실행 콘솔 출력 결과",
        "",
        "```text",
        "=" * 80,
        "Cloud Run Direct VPC Egress 구성 및 네트워크 연결성 진단 리포트",
        f"진단 모드: {mode_str}",
        f"대상 프로젝트: {project_id}",
        f"대상 리전: {region}",
        f"점검 대상 서비스 수: {len(services)}개",
        "=" * 80,
        "",
        "[1단계] Cloud Run 서비스별 VPC 이그레스 아키텍처 현황",
        "-" * 80,
        f"{'서비스 이름':<25} {'이그레스 방식':<14} {'트래픽 범위':<19} {'상태'}",
        "-" * 80,
    ]

    for svc in services:
        lines.append(
            f"{svc['name']:<25} {svc['egress_type']:<14} {svc['vpc_egress']:<19} {svc['status']}"
        )

    lines.extend([
        "-" * 80,
        "",
        "[2단계] 서브넷 IP 고갈 위험 및 네트워크 라우팅 세부 진단",
        "-" * 80,
    ])

    for svc in services:
        lines.append(f"- 서비스: {svc['name']}")
        lines.append(f"  * 연동 방식: {svc['egress_type']}")
        if svc["connector"]:
            lines.append(f"  * VPC 커넥터: {svc['connector']}")
        if svc["subnetwork"]:
            lines.append(f"  * 대상 서브넷: {svc['subnetwork']} (대역: {svc['subnet_cidr'] or '확인 불가'})")
            lines.append(f"  * Private Google Access: {'활성화 (OK)' if svc['subnet_pga'] else '비활성화 (경고)'}")
            lines.append(f"  * Cloud NAT 구비 여부: {'구성됨 (OK)' if svc['has_nat'] else '미구성 (위험)'}")
            lines.append(f"  * 최대 인스턴스(maxScale): {svc['max_scale']}개")
        lines.append(f"  * 진단 결과: [{svc['status']}] {svc['detail']}")
        lines.append("")

    lines.extend([
        "-" * 80,
        "",
        "[3단계] 아키텍처 현대화 및 즉각 조치 처방",
        "1. Serverless VPC Access 커넥터에서 Direct VPC Egress 로 전환:",
        "   gcloud run services update <SERVICE_NAME> \\",
        f"     --region={region} \\",
        "     --network=<VPC_NETWORK> \\",
        "     --subnetwork=<SUBNET_NAME> \\",
        "     --vpc-egress=private-ranges-only \\",
        "     --clear-vpc-connector \\",
        "     --labels=managed-by=google-cloud-0-to-1,scenario=cloud-run-direct-vpc-egress-checker,env=sample,created-by=customer-engineer",
        "",
        "2. 서브넷 Private Google Access 활성화 (구글 API 직결 보장):",
        "   gcloud compute networks subnets update <SUBNET_NAME> \\",
        f"     --region={region} \\",
        "     --enable-private-ip-google-access",
        "",
        "3. all-traffic 라우팅 시 외부 통신용 Cloud NAT 생성:",
        f"   gcloud compute routers create nat-router --network=<VPC_NETWORK> --region={region}",
        f"   gcloud compute routers nats create nat-gw --router=nat-router --auto-allocate-nat-external-ips --region={region}",
        "",
        "4. 사내 거버넌스 4대 필수 표준 라벨링 준수:",
        "   Cloud Run 서비스 및 네트워크 자원 생성 시 FinOps 추적을 위해 4대 표준 라벨을 필수 결합한다.",
        "=" * 80,
        "```",
        "",
        "---",
        "",
        "## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)",
        "",
        "실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.",
        "실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:",
        "",
        "```bash",
        "python diagnose.py",
        "```",
        "",
        "---",
        "",
        "## 3. 실무자 즉각 조치 가이드 및 처방전",
        "",
        "### 1단계: Direct VPC Egress 마이그레이션 적용",
        "Serverless VPC Access 커넥터의 대역폭 한계와 유휴 인스턴스 비용을 제거하기 위해 Direct VPC Egress로 전환한다:",
        "- 구글 클라우드 콘솔 Cloud Run 서비스 목록 ( https://console.cloud.google.com/run )",
        "- Cloud Run Direct VPC Egress 설정 가이드 ( https://cloud.google.com/run/docs/configuring/vpc-direct-vpc )",
        "- VPC 네트워크 연결 옵션 비교 ( https://cloud.google.com/run/docs/configuring/connecting-vpc )",
        "",
        "### 2단계: 서브넷 Private Google Access 및 Cloud NAT 라우팅 정합성 확보",
        "1. 서브넷 Private Google Access 활성화: 비공개 구글 API 호출 실패를 방지한다.",
        "   - VPC 네트워크 목록 ( https://console.cloud.google.com/networking/networks/list )",
        "   - Private Google Access 개요 ( https://cloud.google.com/vpc/docs/private-google-access )",
        "2. 외부 통신(all-traffic) 경로용 Cloud NAT 게이트웨이 배치:",
        "   - Cloud NAT 콘솔 ( https://console.cloud.google.com/net-services/nat/list )",
        "",
        "### 3단계: 사내 거버넌스 4대 필수 표준 라벨링 준수",
        "Cloud Run 서비스 생성 및 수정 시 FinOps 비용 분석 및 추적을 위해 4대 표준 라벨(`--labels=managed-by=google-cloud-0-to-1,scenario=cloud-run-direct-vpc-egress-checker,env=sample,created-by=customer-engineer`)을 누락 없이 주입한다.",
        "",
    ])

    return "\n".join(lines)


def save_markdown_report(report_md: str, output_path: str = "report.md") -> None:
    """리포트 내용을 파일에 저장한다."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: {output_path}")
    except Exception as e:
        print(f"[경고] 리포트 파일 저장 실패 ({output_path}): {e}")


def main() -> None:
    """메인 실행 함수."""
    args = parse_args()
    project_id = detect_project_id(args.project, args.dry_run)
    reported_project = "sample-project-id" if args.dry_run else project_id

    if args.dry_run:
        services = get_mock_services()
        if args.service:
            services = [s for s in services if s["name"] == args.service]
    else:
        services = inspect_cloud_run(reported_project, args.region, args.service)
        if not services:
            print(f"프로젝트 [{reported_project}]의 리전 [{args.region}]에서 점검 대상 Cloud Run 서비스를 찾지 못했다.")
            sys.exit(0)

    print_report(reported_project, args.region, args.dry_run, services)
    report_md = build_markdown_report(reported_project, args.region, args.dry_run, services)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(script_dir, "report.md")
    save_markdown_report(report_md, report_path)


if __name__ == "__main__":
    main()
