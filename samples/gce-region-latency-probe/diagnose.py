#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Alternative Compute Engine GPU & Infrastructure Regions Latency Probe for Seoul Workloads.

서울 리전(asia-northeast3)의 GPU 및 고성능 인스턴스 재고 고갈 시 100ms 미만 지연 시간(RTT)을 보장하는
대체 리전(도쿄, 오사카, 대만, 싱가포르)의 실시간 네트워크 레이턴시와 지원 GPU 가용성을 진단한다.
"""

import argparse
import concurrent.futures
import json
import os
import socket
import statistics
import sys
import time

REGION_PROFILES = [
    {
        "region": "asia-northeast1",
        "location_name": "일본 도쿄 (Tokyo)",
        "endpoint": "asia-northeast1-docker.pkg.dev",
        "expected_rtt_ms": "30 - 40",
        "supported_gpus": ["A100", "H100", "L4", "G4"],
        "machine_families": ["a2-standard", "a2-ultragpu", "a3-highgpu", "a3-megagpu", "g2-standard", "g4-standard"],
        "recommendation": "1순위 추천 (최저 지연 & 최다 가용량)",
    },
    {
        "region": "asia-northeast2",
        "location_name": "일본 오사카 (Osaka)",
        "endpoint": "asia-northeast2-docker.pkg.dev",
        "expected_rtt_ms": "35 - 45",
        "supported_gpus": ["A100", "L4"],
        "machine_families": ["a2-standard", "g2-standard"],
        "recommendation": "보조 추천 (도쿄 유사 저지연, 자원 부족 시 백업)",
    },
    {
        "region": "asia-east1",
        "location_name": "대만 창화 (Changhua)",
        "endpoint": "asia-east1-docker.pkg.dev",
        "expected_rtt_ms": "40 - 55",
        "supported_gpus": ["A100", "H100", "L4", "G4"],
        "machine_families": ["a2-standard", "a2-ultragpu", "a3-highgpu", "g2-standard", "g4-standard"],
        "recommendation": "2순위 추천 (안정적 대안, 대규모 인프라 거점)",
    },
    {
        "region": "asia-southeast1",
        "location_name": "싱가포르 (Singapore)",
        "endpoint": "asia-southeast1-docker.pkg.dev",
        "expected_rtt_ms": "70 - 90",
        "supported_gpus": ["A100", "H100", "L4", "G4"],
        "machine_families": ["a2-standard", "a2-ultragpu", "a3-highgpu", "a3-megagpu", "g2-standard", "g4-standard"],
        "recommendation": "3순위 추천 (신규 가속기 및 AI 인프라 신속 배치 거점)",
    },
    {
        "region": "us-central1",
        "location_name": "미국 아이오와 (Iowa - 비교군)",
        "endpoint": "us-central1-docker.pkg.dev",
        "expected_rtt_ms": "140 - 160",
        "supported_gpus": ["A100", "H100", "L4", "G4"],
        "machine_families": ["a2-standard", "a3-highgpu", "g2-standard", "g4-standard"],
        "recommendation": "기준 초과 (100ms SLA 초과, 저지연 실시간 추론 부적합)",
    },
]


def measure_tcp_rtt(host: str, port: int = 443, count: int = 3, timeout: float = 3.0) -> float | None:
  """대상 엔드포인트와 TCP 3-Way Handshake를 수행하여 왕복 지연 시간(RTT ms)을 측정한다."""
  latencies = []
  for _ in range(count):
    t0 = time.perf_counter()
    try:
      with socket.create_connection((host, port), timeout=timeout):
        latencies.append((time.perf_counter() - t0) * 1000)
    except Exception:
      pass
  if latencies:
    return round(statistics.median(latencies), 2)
  return None


def probe_region(profile: dict, gpu_filter: str | None = None, threshold_ms: float = 100.0) -> dict:
  """개별 리전의 지연 시간 및 GPU 호환성을 진단한다."""
  rtt = measure_tcp_rtt(profile["endpoint"])
  
  # 필터 검사
  supported = profile["supported_gpus"]
  gpu_match = True
  if gpu_filter:
    gpu_match = any(gpu_filter.upper() in g.upper() for g in supported)

  # 적합성 판단
  if rtt is None:
    status = "UNREACHABLE"
    suitability = "측정 실패"
  elif rtt <= 60.0:
    status = "OPTIMAL"
    suitability = "최적 적합 (<60ms)"
  elif rtt <= threshold_ms:
    status = "ACCEPTABLE"
    suitability = f"허용 범위 (<={threshold_ms}ms)"
  else:
    status = "EXCEEDED"
    suitability = f"SLA 초과 (>{threshold_ms}ms)"

  return {
      "region": profile["region"],
      "location_name": profile["location_name"],
      "measured_rtt_ms": rtt if rtt is not None else -1,
      "expected_rtt_ms": profile["expected_rtt_ms"],
      "supported_gpus": supported,
      "gpu_match": gpu_match,
      "status": status,
      "suitability": suitability,
      "recommendation": profile["recommendation"],
  }


def get_mock_diagnoses(gpu_filter: str | None = None, threshold_ms: float = 100.0) -> list[dict]:
  """가상 실행(--dry-run)을 위한 서울 발 지연 시간 시뮬레이션 데이터를 반환한다."""
  mock_rtts = {
      "asia-northeast1": 34.2,
      "asia-northeast2": 38.6,
      "asia-east1": 46.8,
      "asia-southeast1": 76.4,
      "us-central1": 148.5,
  }

  results = []
  for p in REGION_PROFILES:
    rtt = mock_rtts.get(p["region"], 50.0)
    gpu_match = True
    if gpu_filter:
      gpu_match = any(gpu_filter.upper() in g.upper() for g in p["supported_gpus"])

    if rtt <= 60.0:
      status = "OPTIMAL"
      suitability = "최적 적합 (<60ms)"
    elif rtt <= threshold_ms:
      status = "ACCEPTABLE"
      suitability = f"허용 범위 (<={threshold_ms}ms)"
    else:
      status = "EXCEEDED"
      suitability = f"SLA 초과 (>{threshold_ms}ms)"

    results.append({
        "region": p["region"],
        "location_name": p["location_name"],
        "measured_rtt_ms": rtt,
        "expected_rtt_ms": p["expected_rtt_ms"],
        "supported_gpus": p["supported_gpus"],
        "gpu_match": gpu_match,
        "status": status,
        "suitability": suitability,
        "recommendation": p["recommendation"],
    })
  return results


def print_table(results: list[dict], threshold_ms: float, gpu_filter: str | None):
  """결과를 표 형식으로 정돈하여 콘솔에 출력한다."""
  print("\n" + "=" * 108)
  print(f"{'리전':<18} {'위치':<24} {'측정 지연(ms)':<14} {'기준 충족':<18} {'지원 GPU'}")
  print("-" * 108)

  for r in results:
    match_mark = " (타깃 매칭)" if gpu_filter and r["gpu_match"] else ""
    gpus_str = ", ".join(r["supported_gpus"]) + match_mark
    rtt_str = f"{r['measured_rtt_ms']} ms" if r['measured_rtt_ms'] > 0 else "N/A"
    print(f"{r['region']:<18} {r['location_name']:<24} {rtt_str:<14} {r['suitability']:<18} {gpus_str}")
  print("=" * 108)

  print(f"\n[서울 워크로드 대체 Compute Engine GPU 및 인프라 배포 전략 권고안 (기준: <= {threshold_ms} ms)]")
  filtered = [r for r in results if r["gpu_match"]]
  pass_candidates = [r for r in filtered if r["status"] in ("OPTIMAL", "ACCEPTABLE")]
  pass_candidates.sort(key=lambda x: x["measured_rtt_ms"])

  if not pass_candidates:
    print("지정된 조건 및 지연 시간 기준을 만족하는 대체 리전이 없다.")
    return

  for rank, c in enumerate(pass_candidates, 1):
    print(f"\n{rank}. {c['region']} ({c['location_name']}) - 지연 시간: {c['measured_rtt_ms']} ms")
    print(f"   - 권고 사유: {c['recommendation']}")
    print(f"   - 보유 GPU: {', '.join(c['supported_gpus'])}")

  exceeded = [r for r in results if r["status"] == "EXCEEDED"]
  if exceeded:
    print(f"\n* 부적합 리전: {', '.join(e['region'] for e in exceeded)} (왕복 지연 시간이 {threshold_ms}ms를 초과하여 제외됨)")

  print("\n[안내] 사내 거버넌스 및 자원 추적을 위한 4대 필수 표준 라벨:")
  print("  - managed-by: google-cloud-0-to-1")
  print("  - scenario: gce-region-latency-probe")
  print("  - env: sample")
  print("  - created-by: customer-engineer")


def build_markdown_report(results: list[dict], threshold_ms: float, gpu_filter: str | None, is_dry_run: bool) -> str:
  mode_str = "모의 실행 (Dry-run)" if is_dry_run else "운영 환경 진단 (Production)"
  lines = [
      "# 진단 및 분석 리포트: gce-region-latency-probe",
      "",
      f"- **생성 모드**: {mode_str}",
      "- **대상 프로젝트**: `sample-project-id`",
      "- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용",
      "",
      "---",
      "",
      "## 1. 진단 실행 콘솔 출력 결과",
      "",
      "```text",
      f"서울 워크로드 대체 Compute Engine GPU 및 인프라 리전 레이턴시 진단 시작 (지연 기준: {threshold_ms} ms, 타깃 GPU: {gpu_filter or '전체'})",
  ]
  if is_dry_run:
    lines.append("--> 가상 실행 모드 (--dry-run) 활성화: 사전 벤치마크 데이터를 분석한다.")
  else:
    lines.append("--> 각 Google Cloud 리전별 실시간 TCP 3-Way Handshake 왕복 시간(RTT) 측정 완료.")

  lines.extend([
      "",
      "=" * 108,
      f"{'리전':<18} {'위치':<24} {'측정 지연(ms)':<14} {'기준 충족':<18} {'지원 GPU'}",
      "-" * 108,
  ])

  for r in results:
    match_mark = " (타깃 매칭)" if gpu_filter and r["gpu_match"] else ""
    gpus_str = ", ".join(r["supported_gpus"]) + match_mark
    rtt_str = f"{r['measured_rtt_ms']} ms" if r['measured_rtt_ms'] > 0 else "N/A"
    lines.append(f"{r['region']:<18} {r['location_name']:<24} {rtt_str:<14} {r['suitability']:<18} {gpus_str}")
  lines.append("=" * 108)

  lines.append(f"\n[서울 워크로드 대체 Compute Engine GPU 및 인프라 배포 전략 권고안 (기준: <= {threshold_ms} ms)]")
  filtered = [r for r in results if r["gpu_match"]]
  pass_candidates = [r for r in filtered if r["status"] in ("OPTIMAL", "ACCEPTABLE")]
  pass_candidates.sort(key=lambda x: x["measured_rtt_ms"])

  if not pass_candidates:
    lines.append("지정된 조건 및 지연 시간 기준을 만족하는 대체 리전이 없다.")
  else:
    for rank, c in enumerate(pass_candidates, 1):
      lines.append(f"\n{rank}. {c['region']} ({c['location_name']}) - 지연 시간: {c['measured_rtt_ms']} ms")
      lines.append(f"   - 권고 사유: {c['recommendation']}")
      lines.append(f"   - 보유 GPU: {', '.join(c['supported_gpus'])}")

  exceeded = [r for r in results if r["status"] == "EXCEEDED"]
  if exceeded:
    lines.append(f"\n* 부적합 리전: {', '.join(e['region'] for e in exceeded)} (왕복 지연 시간이 {threshold_ms}ms를 초과하여 제외됨)")

  lines.extend([
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
      "### 가. 대체 리전 인스턴스 배포 시 4대 필수 표준 라벨링",
      "사내 거버넌스, FinOps 비용 배분 및 자원 추적성을 위해 리소스 생성 시 4대 표준 라벨을 반드시 적용한다:",
      "",
      "```bash",
      "gcloud compute instances create [INSTANCE_NAME] \\",
      "    --project=[PROJECT_ID] \\",
      "    --zone=[ZONE] \\",
      "    --machine-type=[MACHINE_TYPE] \\",
      "    --accelerator=type=[GPU_TYPE],count=1 \\",
      "    --maintenance-policy=TERMINATE \\",
      "    --labels=managed-by=google-cloud-0-to-1,scenario=gce-region-latency-probe,env=sample,created-by=customer-engineer",
      "```",
      "",
      "### 나. 공식 문서 및 콘솔 경로",
      "- Google Cloud Console Compute Engine VM 인스턴스 ( https://console.cloud.google.com/compute/instances )",
      "- Google Cloud Console Network Topology ( https://console.cloud.google.com/net-intelligence/network-topology )",
      "- Compute Engine 리전 및 영역 안내 ( https://cloud.google.com/compute/docs/regions-zones )",
      "- Compute Engine GPU 리전 가용성 가이드 ( https://cloud.google.com/compute/docs/regions-zones/gpu-regions-zones )",
      "",
  ])

  return "\n".join(lines)


def save_markdown_report(content: str, filename: str = "report.md") -> None:
  current_dir = os.path.dirname(os.path.abspath(__file__))
  report_path = os.path.join(current_dir, filename)
  with open(report_path, "w", encoding="utf-8") as f:
    f.write(content)


def main():
  parser = argparse.ArgumentParser(
      description="서울 워크로드 대체 Compute Engine GPU 및 인프라 리전 네트워크 레이턴시 프로브 및 추천기"
  )
  threshold_env = os.getenv("MAX_LATENCY_THRESHOLD_MS")
  parser.add_argument(
      "--threshold-ms",
      type=float,
      default=float(threshold_env) if threshold_env else 100.0,
      help="허용 최대 지연 시간 임계치 (기본값: 100.0 ms)",
  )
  parser.add_argument(
      "--gpu-type",
      default=os.getenv("TARGET_GPU_TYPE") or None,
      help="필터링할 GPU 모델명 (예: H100, A100, L4, G4)",
  )
  parser.add_argument("--dry-run", action="store_true", help="실제 네트워크 프로브 없이 시뮬레이션 데이터로 진단")
  parser.add_argument("--json", action="store_true", help="결과를 JSON 포맷으로 출력")
  args = parser.parse_args()

  print(f"서울 워크로드 대체 Compute Engine GPU 및 인프라 리전 레이턴시 진단 시작 (지연 기준: {args.threshold_ms} ms, 타깃 GPU: {args.gpu_type or '전체'})")

  if args.dry_run:
    print("--> 가상 실행 모드 (--dry-run) 활성화: 사전 벤치마크 데이터를 분석한다.")
    results = get_mock_diagnoses(args.gpu_type, args.threshold_ms)
  else:
    print("--> 각 Google Cloud 리전별 실시간 TCP 3-Way Handshake 왕복 시간(RTT) 측정 중...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
      future_map = {
          executor.submit(probe_region, p, args.gpu_type, args.threshold_ms): p
          for p in REGION_PROFILES
      }
      results = [f.result() for f in concurrent.futures.as_completed(future_map)]
      results.sort(key=lambda x: x["measured_rtt_ms"] if x["measured_rtt_ms"] > 0 else 9999)

  md_content = build_markdown_report(results, args.threshold_ms, args.gpu_type, is_dry_run=args.dry_run)
  save_markdown_report(md_content)

  if args.json:
    print(json.dumps(results, indent=2, ensure_ascii=False))
  else:
    print_table(results, args.threshold_ms, args.gpu_type)
    print("\n[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: report.md")


if __name__ == "__main__":
  main()
