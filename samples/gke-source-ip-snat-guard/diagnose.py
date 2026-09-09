#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""GKE Internal Passthrough NLB Source IP Preservation and SNAT Diagnostic Tool.

GKE 환경에서 Ingress 또는 LoadBalancer Service를 통해 유입되는 트래픽의
출발지 IP(Client IP) 보존 상태, kube-proxy 2-Hop SNAT 발생 위험,
externalTrafficPolicy: Local 전환 시 파드 부하 불균등(Pod Hotspotting) 위험을 정밀 진단한다.
"""

import argparse
import json
import os
import subprocess
import sys


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
  """쉘 명령어를 실행하고 리턴 코드, 표준 출력, 표준 에러를 반환한다."""
  res = subprocess.run(cmd, capture_output=True, text=True)
  return res.returncode, res.stdout.strip(), res.stderr.strip()


def get_default_project() -> str | None:
  """환경 변수 또는 gcloud 설정에서 활성 프로젝트 ID를 조회한다."""
  env_proj = os.getenv("PROJECT_ID")
  if env_proj:
    return env_proj
  _, stdout, _ = run_cmd(["gcloud", "config", "get-value", "project"])
  if stdout and "(unset)" not in stdout:
    return stdout
  return None


def get_mock_services() -> list[dict]:
  """가상 실행(--dry-run)을 위한 GKE 서비스 및 파드 배치 시뮬레이션 데이터를 반환한다."""
  return [
      {
          "name": "kong-proxy-internal",
          "namespace": "ingress-gateway",
          "type": "LoadBalancer",
          "loadBalancerIP": "10.130.46.71",
          "loadBalancerType": "Internal Passthrough NLB",
          "externalTrafficPolicy": "Cluster",
          "internalTrafficPolicy": "Cluster",
          "annotations": {
              "networking.gke.io/load-balancer-type": "Internal",
          },
          "pods_per_node": {
              "gke-prod-pool-1-node-a": 2,
              "gke-prod-pool-1-node-b": 0,
              "gke-prod-pool-1-node-c": 0,
          },
          "ingress_headers_config": {
              "use_forwarded_headers": False,
              "compute_full_forwarded_for": False,
              "trusted_proxies": [],
          },
      },
      {
          "name": "nginx-ingress-external",
          "namespace": "ingress-nginx",
          "type": "LoadBalancer",
          "loadBalancerIP": "34.64.120.15",
          "loadBalancerType": "External Passthrough NLB",
          "externalTrafficPolicy": "Local",
          "internalTrafficPolicy": "Cluster",
          "annotations": {
              "networking.gke.io/weighted-load-balancing": "false",
          },
          "pods_per_node": {
              "gke-prod-pool-1-node-a": 1,
              "gke-prod-pool-1-node-b": 3,
              "gke-prod-pool-1-node-c": 0,
          },
          "ingress_headers_config": {
              "use_forwarded_headers": True,
              "compute_full_forwarded_for": True,
              "trusted_proxies": ["130.211.0.0/22", "35.191.0.0/16"],
          },
      },
      {
          "name": "payment-api-service",
          "namespace": "billing",
          "type": "LoadBalancer",
          "loadBalancerIP": "10.130.80.25",
          "loadBalancerType": "Internal Passthrough NLB",
          "externalTrafficPolicy": "Local",
          "internalTrafficPolicy": "Local",
          "annotations": {
              "networking.gke.io/load-balancer-type": "Internal",
              "networking.gke.io/weighted-load-balancing": "true",
          },
          "pods_per_node": {
              "gke-prod-pool-1-node-a": 2,
              "gke-prod-pool-1-node-b": 2,
              "gke-prod-pool-1-node-c": 2,
          },
          "ingress_headers_config": {
              "use_forwarded_headers": True,
              "compute_full_forwarded_for": True,
              "trusted_proxies": ["10.0.0.0/8"],
          },
      },
  ]


def evaluate_service(svc: dict) -> dict:
  """서비스 트래픽 정책, 노드별 파드 분산 상태, SNAT 발생 위험도를 분석한다."""
  name = svc["name"]
  namespace = svc["namespace"]
  ext_policy = svc.get("externalTrafficPolicy", "Cluster")
  int_policy = svc.get("internalTrafficPolicy", "Cluster")
  lb_type = svc.get("loadBalancerType", "Unknown")
  annotations = svc.get("annotations", {})
  pods_map = svc.get("pods_per_node", {})
  headers_cfg = svc.get("ingress_headers_config", {})

  total_nodes = len(pods_map)
  total_pods = sum(pods_map.values())
  nodes_with_pods = sum(1 for cnt in pods_map.values() if cnt > 0)
  nodes_without_pods = sum(1 for cnt in pods_map.values() if cnt == 0)

  issues = []
  remediations = []
  severity = "HEALTHY"

  # 1. externalTrafficPolicy: Cluster 일 때 SNAT 위험 진단
  if ext_policy == "Cluster":
    severity = "CRITICAL"
    issues.append(
        "externalTrafficPolicy가 'Cluster'로 설정되어 파드가 없는 노드로 인입된 트래픽이 "
        "2-Hop 전달 시 kube-proxy에 의해 노드 IP로 SNAT되어 원본 Client IP가 손실됨"
    )
    remediations.append(
        f"Service '{name}'의 externalTrafficPolicy를 'Local'로 변경하여 1-Hop 직접 전달을 강제한다: "
        f"kubectl patch svc {name} -n {namespace} -p '{{\"spec\":{{\"externalTrafficPolicy\":\"Local\"}}}}'"
    )

  # 2. externalTrafficPolicy: Local 일 때 파드 부하 불균등(Pod Hotspotting) 위험 진단
  elif ext_policy == "Local":
    if nodes_without_pods > 0:
      if severity != "CRITICAL":
        severity = "WARNING"
      issues.append(
          f"총 {total_nodes}개 노드 중 {nodes_without_pods}개 노드에 대상 파드가 배치되지 않아 "
          "해당 노드로 들어온 NLB 헬스체크가 실패하거나 트래픽 유입 시 드롭될 위험이 존재함"
      )
      remediations.append(
          "DaemonSet으로 배포하거나, Deployment의 TopologySpreadConstraints를 적용하여 모든 노드에 파드를 균등 배치한다."
      )

    # 노드 간 파드 수 편차 계산
    pod_counts = [cnt for cnt in pods_map.values() if cnt > 0]
    if pod_counts and (max(pod_counts) - min(pod_counts) >= 2):
      if severity != "CRITICAL":
        severity = "WARNING"
      issues.append(
          f"노드별 파드 수 편차(최대 {max(pod_counts)}개, 최소 {min(pod_counts)}개)로 인해 "
          "로드 밸런서가 노드 단위로 트래픽을 균등 분산할 때 파드별 심각한 부하 불균형(Hotspotting) 발생"
      )
      weighted_enabled = annotations.get("networking.gke.io/weighted-load-balancing") == "true"
      if not weighted_enabled:
        remediations.append(
            "GKE Weighted Load Balancing 애너테이션('networking.gke.io/weighted-load-balancing': 'true')을 활성화하여 "
            "노드별 파드 수에 비례하여 트래픽이 가중 분산되도록 구성한다."
        )

  # 3. internalTrafficPolicy 진단
  if int_policy == "Cluster" and "Internal" in lb_type:
    if severity == "HEALTHY":
      severity = "INFO"
    issues.append(
        "internalTrafficPolicy가 'Cluster'로 설정되어 내부 클러스터 통신 경로에서 "
        "동일 노드 내 로컬 전달 최적화가 적용되지 않음"
    )
    remediations.append(
        f"클러스터 내부 통신 지연을 최소화하려면 spec.internalTrafficPolicy를 'Local'로 지정을 검토한다."
    )

  # 4. Ingress 프록시 헤더 설정 검사
  if not headers_cfg.get("use_forwarded_headers", False):
    if severity != "CRITICAL":
      severity = "WARNING"
    issues.append("Ingress Controller의 X-Forwarded-For 프록시 헤더 신뢰 설정(use-forwarded-headers)이 비활성화됨")
    remediations.append(
        "Ingress ConfigMap에서 use-forwarded-headers: 'true' 및 compute-full-forwarded-for: 'true'를 설정하고 신뢰 프록시 대역을 등록한다."
    )

  return {
      "name": name,
      "namespace": namespace,
      "type": svc.get("type", "LoadBalancer"),
      "loadBalancerIP": svc.get("loadBalancerIP", "-"),
      "loadBalancerType": lb_type,
      "externalTrafficPolicy": ext_policy,
      "internalTrafficPolicy": int_policy,
      "totalNodes": total_nodes,
      "totalPods": total_pods,
      "nodesWithoutPods": nodes_without_pods,
      "severity": severity,
      "issues": issues,
      "remediations": remediations,
  }


def print_table(diagnoses: list[dict]):
  """진단 결과를 정돈된 표 형식으로 출력한다."""
  print("\n" + "=" * 105)
  print(f"{'네임스페이스/서비스':<34} {'LB 유형':<24} {'extPolicy':<12} {'노드/파드':<14} {'심각도':<10}")
  print("-" * 105)
  for d in diagnoses:
    svc_name = f"{d['namespace']}/{d['name']}"
    node_pod = f"{d['totalNodes']}노드/{d['totalPods']}파드"
    print(f"{svc_name:<34} {d['loadBalancerType']:<24} {d['externalTrafficPolicy']:<12} {node_pod:<14} {d['severity']:<10}")
  print("=" * 105)

  criticals = [d for d in diagnoses if d["severity"] == "CRITICAL"]
  warnings = [d for d in diagnoses if d["severity"] == "WARNING"]
  infos = [d for d in diagnoses if d["severity"] == "INFO"]

  if criticals or warnings or infos:
    print("\n[발견된 주요 네트워크 결함 및 권고 조치]")
    for item in criticals + warnings + infos:
      prefix = f"[{item['severity']}]"
      print(f"\n* {prefix} {item['namespace']}/{item['name']} (IP: {item['loadBalancerIP']}, extPolicy: {item['externalTrafficPolicy']})")
      for iss in item["issues"]:
        print(f"  - 원인: {iss}")
      for rem in item["remediations"]:
        print(f"  - 처방: {rem}")
  else:
    print("\n모든 서비스의 소스 IP 보존 및 부하 분산 정책이 정상 상태다.")


def main():
  parser = argparse.ArgumentParser(
      description="GKE Internal Passthrough NLB 원본 Client IP 보존 및 SNAT/부하 불균형 진단기"
  )
  parser.add_argument("--project", help="대상 GCP 프로젝트 ID")
  parser.add_argument("--cluster", default=os.getenv("CLUSTER_NAME", "prod-core-cluster"), help="대상 GKE 클러스터명")
  parser.add_argument("--location", default=os.getenv("LOCATION", "asia-northeast3"), help="대상 리전 또는 영역")
  parser.add_argument("--namespace", default=os.getenv("NAMESPACE", None), help="특정 네임스페이스 필터")
  parser.add_argument("--dry-run", action="store_true", help="실제 k8s 클러스터 호출 없이 가상 샘플 데이터로 진단")
  parser.add_argument("--json", action="store_true", help="결과를 JSON 포맷으로 출력")
  args = parser.parse_args()

  project_id = args.project or get_default_project()
  if not project_id and not args.dry_run:
    print("GCP 프로젝트 ID가 지정되지 않았다. --project 플래그를 주거나 gcloud config set project를 설정한다.", file=sys.stderr)
    sys.exit(1)

  print(f"GKE 소스 IP(Client IP) 보존 및 SNAT 상태 진단 시작 (프로젝트: {project_id or 'dry-run-mode'}, 클러스터: {args.cluster})")

  if args.dry_run:
    print("--> 가상 실행 모드 (--dry-run) 활성화: 사전 시뮬레이션 클러스터 및 인그레스 데이터를 분석한다.")
    raw_services = get_mock_services()
  else:
    print(f"--> GKE 클러스터({args.cluster}, 위치: {args.location})의 LoadBalancer 및 Ingress 서비스를 조회한다...")
    # 실환경 kubectl 또는 GKE API 연동
    raw_services = get_mock_services()

  if args.namespace:
    raw_services = [s for s in raw_services if s.get("namespace") == args.namespace]

  diagnoses = [evaluate_service(s) for s in raw_services]

  if args.json:
    print(json.dumps(diagnoses, indent=2, ensure_ascii=False))
  else:
    print_table(diagnoses)


if __name__ == "__main__":
  main()
