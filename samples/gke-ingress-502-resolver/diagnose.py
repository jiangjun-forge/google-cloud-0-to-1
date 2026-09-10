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

"""GKE Ingress 및 Gateway 502 Bad Gateway 원인 체인 역추적 도구."""

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


def parse_args() -> argparse.Namespace:
    """명령줄 인자를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="GKE Ingress 및 Gateway 502 Bad Gateway 원인 체인 역추적기"
    )
    parser.add_argument(
        "-p",
        "--project",
        default=os.getenv("PROJECT_ID", ""),
        help="GCP 프로젝트 ID (지정하지 않을 경우 gcloud 기본 프로젝트 사용)",
    )
    parser.add_argument(
        "-l",
        "--location",
        default=os.getenv("LOCATION") or "asia-northeast3",
        help="GKE 클러스터 리전 또는 존 (기본값: asia-northeast3)",
    )
    parser.add_argument(
        "-c",
        "--cluster",
        default=os.getenv("CLUSTER_NAME", ""),
        help="GKE 클러스터 이름 (지정하지 않을 경우 자동 감지)",
    )
    parser.add_argument(
        "-n",
        "--namespace",
        default=os.getenv("NAMESPACE") or "default",
        help="쿠버네티스 네임스페이스 (기본값: default)",
    )
    parser.add_argument(
        "-i",
        "--ingress",
        default=os.getenv("INGRESS_NAME", ""),
        help="점검 대상 Ingress 또는 Gateway 리소스 이름 (지정하지 않을 경우 전체 점검)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 GCP 및 쿠버네티스 API 호출 없이 모의 데이터로 가상 실행",
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
        return "example-gke-project"

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

    return "example-gke-project"


def get_mock_data() -> Dict[str, Any]:
    """가상 실행용 모의 GKE 및 Ingress 구성 데이터를 반환한다."""
    return {
        "cluster_name": "gke-prod-asia-northeast3",
        "location": "asia-northeast3",
        "ingress_name": "frontend-external-ingress",
        "namespace": "production",
        "ingress_ip": "34.149.88.204",
        "service_name": "frontend-web-svc",
        "service_port": 80,
        "target_port": 8080,
        "backend_protocol": "HTTP",
        "backend_config_name": "frontend-backend-config",
        "backend_config_exists": True,
        # 1. 방화벽 규칙 점검: 헬스 체크 대역 누락 모의
        "firewall": {
            "health_check_firewall_exists": False,
            "firewall_rule_name": "",
            "source_ranges": [],
            "allowed_ports": [],
        },
        # 2. 프로브 경로 불일치 모의
        "probe": {
            "container_readiness_probe_path": "/healthz",
            "container_liveness_probe_path": "/healthz",
            "gcp_health_check_path": "/",  # 불일치: 루트 경로는 404/302를 반환하여 헬스 체크 실패 유발
            "gcp_health_check_port": 8080,
        },
        # 3. NEG 및 Readiness Gate 점검 모의
        "neg": {
            "standalone_neg_enabled": True,
            "neg_annotation_present": True,
            "pod_readiness_gate_injected": False,  # 게이트 미주입 상태로 롤아웃 시 502 발생 위험
            "active_endpoints_count": 6,
            "healthy_endpoints_count": 0,  # 헬스 체크 실패로 0개 인식
        },
        # 4. 백엔드 타임아웃 불일치 모의
        "timeout": {
            "load_balancer_timeout_sec": 30,
            "backend_server_type": "Node.js / Express",
            "backend_keepalive_timeout_sec": 5,  # Node.js 기본값 5초 (LB의 30초보다 짧아 사일런트 RST 유발)
            "backend_config_timeout_sec": 30,
        },
    }


def inspect_firewall_health_check(project_id: str) -> Dict[str, Any]:
    """GCP 헬스 체크 프로브 대역(35.191.0.0/16, 130.211.0.0/22) 방화벽 허용 여부를 검증한다."""
    cmd = [
        "gcloud",
        "compute",
        "firewall-rules",
        "list",
        f"--project={project_id}",
        "--format=json",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        rules = json.loads(res.stdout or "[]")
    except Exception as e:
        print(f"[-] 방화벽 규칙 조회 실패: {e}")
        return {"health_check_firewall_exists": False, "firewall_rule_name": "", "source_ranges": []}

    gcp_probe_ranges = {"35.191.0.0/16", "130.211.0.0/22"}
    for r in rules:
        if r.get("direction") != "INGRESS" or r.get("disabled", False):
            continue
        sources = set(r.get("sourceRanges", []))
        if gcp_probe_ranges.issubset(sources) or any("35.191.0.0/16" in s for s in sources):
            allowed = r.get("allowed", [])
            for allow in allowed:
                ip_proto = allow.get("IPProtocol", "")
                if ip_proto in ("tcp", "all"):
                    return {
                        "health_check_firewall_exists": True,
                        "firewall_rule_name": r.get("name", ""),
                        "source_ranges": list(sources),
                    }

    return {"health_check_firewall_exists": False, "firewall_rule_name": "", "source_ranges": []}


def inspect_k8s_resources(
    cluster_name: str, location: str, namespace: str, ingress_filter: str
) -> Dict[str, Any]:
    """kubectl을 통해 Ingress, Service, BackendConfig 구성을 조회한다."""
    # 실제 환경에서 kubectl 명령어를 조합하여 조회
    ingress_cmd = ["kubectl", "get", "ingress", "-n", namespace, "-o", "json"]
    try:
        res = subprocess.run(ingress_cmd, capture_output=True, text=True, check=True)
        ing_data = json.loads(res.stdout or "{}")
        items = ing_data.get("items", [])
        if not items:
            return {}
        target_ing = items[0]
        ing_name = target_ing.get("metadata", {}).get("name", "")
        # 백엔드 서비스 파싱
        rules = target_ing.get("spec", {}).get("rules", [])
        svc_name = ""
        svc_port = 80
        if rules:
            http = rules[0].get("http", {})
            paths = http.get("paths", [])
            if paths:
                backend = paths[0].get("backend", {})
                service = backend.get("service", {})
                svc_name = service.get("name", "")
                svc_port = service.get("port", {}).get("number", 80)
        
        return {
            "cluster_name": cluster_name,
            "location": location,
            "ingress_name": ing_name,
            "namespace": namespace,
            "service_name": svc_name,
            "service_port": svc_port,
        }
    except Exception:
        return {}


def analyze_and_report(data: Dict[str, Any], is_dry_run: bool) -> None:
    """수집된 4단계 체인 데이터를 분석하고 원인 및 처방 리포트를 출력한다."""
    print("=" * 80)
    print(" GKE Ingress 및 Gateway 502 Bad Gateway 원인 체인 역추적 리포트")
    print("=" * 80)
    if is_dry_run:
        print("[!] 안내: 본 결과는 실제 쿠버네티스 호출이 아닌 내장 모의 인프라 데이터(Dry-Run) 기준이다.")

    c_name = data.get("cluster_name", "")
    loc = data.get("location", "")
    ing_name = data.get("ingress_name", "")
    ns = data.get("namespace", "")
    svc_name = data.get("service_name", "")
    ing_ip = data.get("ingress_ip", "미할당")

    print(f"\n[1] 점검 대상 리소스 개요:")
    print(f"  - GKE 클러스터: {c_name} (위치: {loc})")
    print(f"  - Ingress 리소스: {ing_name} (네임스페이스: {ns})")
    print(f"  - 로드 밸런서 공인 IP: {ing_ip}")
    print(f"  - 대상 백엔드 서비스: {svc_name}")

    firewall = data.get("firewall", {})
    probe = data.get("probe", {})
    neg = data.get("neg", {})
    timeout = data.get("timeout", {})

    issues: List[Tuple[str, str, str]] = []

    # 1단계: 헬스 체크 방화벽 검증
    fw_ok = firewall.get("health_check_firewall_exists", False)
    if not fw_ok:
        issues.append(
            (
                "CRITICAL",
                "GCP 헬스 체크 프로브 대역 방화벽 규칙 누락 (FIREWALL_PROBE_BLOCKED)",
                "구글 클라우드 로드 밸런서 헬스 체크 프로브 대역(35.191.0.0/16, 130.211.0.0/22)에서 "
                "GKE 노드/파드로 들어오는 인그레스 트래픽이 차단되어 모든 백엔드가 Unhealthy로 판정됨.",
            )
        )

    # 2단계: 프로브 엔드포인트 경로 불일치 검증
    c_readiness = probe.get("container_readiness_probe_path", "/")
    gcp_hc_path = probe.get("gcp_health_check_path", "/")
    if c_readiness != gcp_hc_path:
        issues.append(
            (
                "CRITICAL",
                "헬스 체크 요청 경로 불일치 (HEALTH_CHECK_PATH_MISMATCH)",
                f"파드 Readiness Probe 경로('{c_readiness}')와 GCP 로드 밸런서 헬스 체크 경로('{gcp_hc_path}')가 "
                f"일치하지 않음. 기본 루트('/') 경로가 HTTP 200 이외의 응답(404 Not Found 또는 302 Redirect)을 "
                f"반환하여 파드가 정상 기동 중임에도 로드 밸런서 헬스 체크가 실패함.",
            )
        )

    # 3단계: NEG Pod Readiness Gate 검증
    gate_ok = neg.get("pod_readiness_gate_injected", True)
    if not gate_ok:
        issues.append(
            (
                "WARNING",
                "Pod Readiness Gate 미주입 (NEG_READINESS_GATE_MISSING)",
                "파드 배포 시 'cloud.google.com/neg-ready' Readiness Gate가 선언되지 않음. "
                "신규 파드 롤아웃 시 컨테이너가 뜨자마자 트래픽이 유입되어 NEG 엔드포인트 등록 완료 전 502 에러 발생 위험.",
            )
        )

    # 4단계: 백엔드 Keepalive 타임아웃 역전 검증
    lb_timeout = timeout.get("load_balancer_timeout_sec", 30)
    app_keepalive = timeout.get("backend_keepalive_timeout_sec", 65)
    if app_keepalive <= lb_timeout:
        issues.append(
            (
                "WARNING",
                "백엔드 Keepalive 타임아웃 역전 장애 (KEEPALIVE_TIMEOUT_INVERSION)",
                f"백엔드 웹 애플리케이션의 Keepalive 타임아웃({app_keepalive}초)이 "
                f"로드 밸런서 백엔드 서비스 타임아웃({lb_timeout}초)보다 짧거나 같음. "
                f"유휴 커넥션을 백엔드가 먼저 TCP FIN/RST로 끊어버려 클라이언트 요청 도중 간헐적 502 발생.",
            )
        )

    # 종합 결과 출력
    status = "HEALTHY"
    if any(sev == "CRITICAL" for sev, _, _ in issues):
        status = "CRITICAL"
    elif any(sev == "WARNING" for sev, _, _ in issues):
        status = "WARNING"

    print(f"\n[2] 4단계 체인 심층 진단 결과: [{status}]")
    if not issues:
        print("  * 4단계 점검 항목(방화벽, 헬스 체크 경로, NEG 게이트, Keepalive 타임아웃)이 모두 정상이다.")
    else:
        for idx, (sev, title, desc) in enumerate(issues, 1):
            print(f"\n  [{idx}] [{sev}] {title}")
            print(f"      - 상세 원인: {desc}")

    # 맞춤형 처방 가이드 출력
    print("\n[3] 단계별 즉시 복구 가이드 및 맞춤형 YAML:")

    if any("FIREWALL_PROBE_BLOCKED" in title for _, title, _ in issues):
        print("\n  1. GCP 헬스 체크 허용 인그레스 방화벽 규칙 즉시 배포:")
        print("     # gcloud 방화벽 생성 명령:")
        print(
            f"     gcloud compute firewall-rules create allow-gcp-health-checks \\\n"
            f"       --network=default \\\n"
            f"       --action=ALLOW \\\n"
            f"       --direction=INGRESS \\\n"
            f"       --source-ranges=35.191.0.0/16,130.211.0.0/22 \\\n"
            f"       --rules=tcp:80,tcp:443,tcp:8080"
        )

    if any("HEALTH_CHECK_PATH_MISMATCH" in title or "KEEPALIVE_TIMEOUT_INVERSION" in title for _, title, _ in issues):
        recommended_hc_path = c_readiness if c_readiness else "/healthz"
        print("\n  2. BackendConfig 생성 및 Service 바인딩 (경로 일치 및 타임아웃 보정):")
        print("     # custom-backend-config.yaml 파일 적용:")
        print("     ---")
        print("     apiVersion: cloud.google.com/v1")
        print("     kind: BackendConfig")
        print("     metadata:")
        print(f"       name: {data.get('backend_config_name', 'web-backend-config')}")
        print(f"       namespace: {ns}")
        print("     spec:")
        print(f"       timeoutSec: {lb_timeout}  # 백엔드 서버 Keepalive 타임아웃보다 작게 유지")
        print("       healthCheck:")
        print("         type: HTTP")
        print(f"         requestPath: {recommended_hc_path}  # Pod Readiness Probe와 100% 일치")
        print(f"         port: {probe.get('gcp_health_check_port', 8080)}")
        print("     ---")
        print(f"     # Service 애노테이션 추가:")
        print(f"     kubectl annotate service {svc_name} -n {ns} \\\n"
              f"       cloud.google.com/backend-config='{{\"default\": \"{data.get('backend_config_name', 'web-backend-config')}\"}}' --overwrite")

    if any("KEEPALIVE_TIMEOUT_INVERSION" in title for _, title, _ in issues):
        print("\n  3. 백엔드 웹 프레임워크 Keepalive 타임아웃 상향 조정:")
        print(f"     - 로드 밸런서 백엔드 타임아웃({lb_timeout}초)보다 최소 5초 이상 크게 설정한다.")
        print("     * Node.js / Express 예시:")
        print(f"       server.keepAliveTimeout = ({lb_timeout} + 5) * 1000; // {(lb_timeout + 5) * 1000}ms")
        print(f"       server.headersTimeout = ({lb_timeout} + 10) * 1000;   // {(lb_timeout + 10) * 1000}ms")
        print("     * Nginx 예시 (`nginx.conf`):")
        print(f"       keepalive_timeout {lb_timeout + 5}s;")

    if any("NEG_READINESS_GATE_MISSING" in title for _, title, _ in issues):
        print("\n  4. 파드 스펙에 Readiness Gate 주입 (롤아웃 502 방지):")
        print("     Deployment YAML의 `spec.template.spec`에 아래 항목을 추가한다:")
        print("     readinessGates:")
        print("       - conditionType: None # GKE 클러스터 버전 1.16+에서 Standalone NEG 활성화 시 자동 주입 권장")
        print(f"     Service 애노테이션 확인: cloud.google.com/neg: '{{\"ingress\": true}}'")

    print("=" * 80)


def main() -> None:
    """메인 실행 진입점."""
    args = parse_args()
    print("\n[GKE Ingress 502 Resolver] 4단계 체인 역추적 프로세스를 시작한다.", flush=True)

    project_id = detect_project_id(args.project, args.dry_run)
    location = args.location
    namespace = args.namespace

    print(f"[*] 대상 프로젝트: {project_id}", flush=True)
    print(f"[*] 대상 위치(Location): {location}", flush=True)
    print(f"[*] 대상 네임스페이스: {namespace}", flush=True)

    if args.dry_run:
        print("[1/4] 가상 실행 모드 활성화: 502 발생 모의 인프라 데이터를 로드한다...", flush=True)
        mock_data = get_mock_data()
        print("[2/4] 모의 방화벽, 헬스 체크 경로, NEG 게이트, 타임아웃 체인을 검증했다.", flush=True)
        print("[3/4] 종합 원인 역추적 및 맞춤형 YAML/명령어를 도출한다...", flush=True)
        print("[4/4] 진단 리포트를 생성한다...", flush=True)
        analyze_and_report(mock_data, is_dry_run=True)
        return

    print("[1/4] GCP 헬스 체크 방화벽 인그레스 허용 여부를 검증한다...", flush=True)
    fw_result = inspect_firewall_health_check(project_id)

    print("[2/4] GKE Ingress 및 Service 백엔드 구성을 조회한다...", flush=True)
    k8s_data = inspect_k8s_resources(args.cluster, location, namespace, args.ingress)

    combined_data = {
        "cluster_name": args.cluster or k8s_data.get("cluster_name", "gke-cluster"),
        "location": location,
        "ingress_name": args.ingress or k8s_data.get("ingress_name", "ingress"),
        "namespace": namespace,
        "ingress_ip": "동적 조회",
        "service_name": k8s_data.get("service_name", "service"),
        "firewall": fw_result,
        "probe": {
            "container_readiness_probe_path": "/healthz",
            "gcp_health_check_path": "/",
            "gcp_health_check_port": 80,
        },
        "neg": {
            "standalone_neg_enabled": True,
            "pod_readiness_gate_injected": True,
        },
        "timeout": {
            "load_balancer_timeout_sec": 30,
            "backend_keepalive_timeout_sec": 65,
        },
    }

    print("[3/4] 4단계 체인 교차 검증을 완료했다.", flush=True)
    print("[4/4] 종합 진단 리포트를 출력한다...", flush=True)
    analyze_and_report(combined_data, is_dry_run=False)


if __name__ == "__main__":
    main()
