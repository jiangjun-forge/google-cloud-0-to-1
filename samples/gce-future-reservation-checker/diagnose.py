#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Compute Engine GPU 및 특수 인스턴스 Future Reservation 사전 예약 진단기.

Compute Engine Future Reservation(FR) 신청 상태를 점검하여 DRAFTING 잔류,
필수 파라미터 누락, 120시간 리드 타임 위반 및 프로젝트 불일치 문제를 신속하게 진단한다.
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
import subprocess
import sys


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
  """쉘 명령어를 실행하고 리턴 코드, 표준 출력, 표준 에러를 반환한다."""
  res = subprocess.run(cmd, capture_output=True, text=True)
  return res.returncode, res.stdout.strip(), res.stderr.strip()


def get_default_project(is_dry_run: bool = False, fallback_demo: str = "example-corp-dev") -> str:
  """환경 변수, gcloud 설정, 실시간 프로젝트 목록에서 활성 프로젝트를 탐색/선택한다."""
  env_proj = os.getenv("PROJECT_ID")
  if env_proj:
    return env_proj
  _, stdout, _ = run_cmd(["gcloud", "config", "get-value", "project"])
  if stdout and "(unset)" not in stdout:
    return stdout

  if is_dry_run or not sys.stdin.isatty():
    return fallback_demo

  code, stdout, _ = run_cmd(["gcloud", "projects", "list", "--format=value(projectId)", "--limit=5"])
  projects = [p.strip() for p in stdout.splitlines() if p.strip()] if code == 0 and stdout else []
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

  return fallback_demo


def get_mock_reservations() -> list[dict]:
  """가상 실행(--dry-run)을 위한 Future Reservation 샘플 목록을 반환한다."""
  now = datetime.now(timezone.utc)
  return [
      {
          "name": "fr-g4-robotics-draft",
          "id": "9042446426570361614",
          "zone": "us-south1-a",
          "project": "example-corp-dev",
          "status": "DRAFTING",
          "machineType": "g4-standard-48",
          "acceleratorType": "nvidia-rtx-pro-6000",
          "acceleratorCount": 24,
          "totalCount": 24,
          "autoDeleteAutoCreatedReservations": True,
          "creationTimestamp": (now - timedelta(hours=2)).isoformat(),
          "startTime": (now + timedelta(hours=48)).isoformat(),
          "endTime": (now + timedelta(days=365)).isoformat(),
      },
      {
          "name": "fr-a3-training-pending",
          "id": "2312445798605452488",
          "zone": "us-central1-a",
          "project": "example-corp-dev",
          "status": "PENDING_APPROVAL",
          "machineType": "a3-highgpu-8g",
          "acceleratorType": "nvidia-h100-80gb",
          "acceleratorCount": 8,
          "totalCount": 8,
          "autoDeleteAutoCreatedReservations": False,
          "creationTimestamp": (now - timedelta(days=2)).isoformat(),
          "startTime": (now + timedelta(days=10)).isoformat(),
          "endTime": (now + timedelta(days=180)).isoformat(),
      },
      {
          "name": "fr-g2-inference-approved",
          "id": "4152849182740192841",
          "zone": "asia-northeast3-a",
          "project": "example-corp-dev",
          "status": "APPROVED",
          "machineType": "g2-standard-16",
          "acceleratorType": "nvidia-l4",
          "acceleratorCount": 16,
          "totalCount": 16,
          "autoDeleteAutoCreatedReservations": False,
          "creationTimestamp": (now - timedelta(days=7)).isoformat(),
          "startTime": (now + timedelta(days=14)).isoformat(),
          "endTime": (now + timedelta(days=90)).isoformat(),
      },
  ]


def fetch_future_reservations(project_id: str, zone: str | None = None) -> list[dict]:
  """gcloud CLI를 통해 실제 프로젝트의 Future Reservation 목록을 조회한다."""
  cmd = [
      "gcloud",
      "beta",
      "compute",
      "future-reservations",
      "list",
      f"--project={project_id}",
      "--format=json",
  ]
  if zone:
    cmd.append(f"--filter=zone:({zone})")

  code, stdout, stderr = run_cmd(cmd)
  if code != 0:
    print(f"[경고] Future Reservation 조회 실패: {stderr}", file=sys.stderr)
    return []
  if not stdout:
    return []
  try:
    return json.loads(stdout)
  except json.JSONDecodeError:
    return []


def evaluate_reservation(fr: dict, active_project: str | None) -> dict:
  """Future Reservation의 위험 요소를 평가하고 처방을 생성한다."""
  name = fr.get("name", "unknown")
  zone = fr.get("zone", "").split("/")[-1]
  status = fr.get("status", "UNKNOWN")
  res_project = fr.get("project", active_project or "unknown")
  auto_delete = fr.get("autoDeleteAutoCreatedReservations", False)
  start_str = fr.get("startTime", "")

  issues = []
  remediations = []
  severity = "HEALTHY"

  # 1. DRAFTING 상태 검사
  if status == "DRAFTING":
    severity = "CRITICAL"
    issues.append("예약이 DRAFTING 상태에 머물러 있어 Capacity 심사 큐에 접수되지 않음")
    remediations.append(
        f"콘솔 상세 페이지에서 [제출/Submit] 버튼을 클릭하거나 다음 명령어를 실행한다: "
        f"gcloud beta compute future-reservations submit {name} --zone={zone} --project={res_project}"
    )

  # 2. CUD 연계 시 Auto-delete 옵션 검사
  if auto_delete:
    if severity != "CRITICAL":
      severity = "WARNING"
    issues.append("autoDeleteAutoCreatedReservations가 활성화되어 CUD 약정 연계 시 조기 소멸 위험 존재")
    remediations.append(
        "CUD 연결을 위해 생성 시 --no-auto-delete-auto-created-reservations 플래그를 필수로 지정해야 한다."
    )

  # 3. 120시간 사전 신청 리드 타임 정책 검사
  if start_str:
    try:
      start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
      now_dt = datetime.now(timezone.utc)
      lead_hours = (start_dt - now_dt).total_seconds() / 3600
      if lead_hours < 120 and status in ("DRAFTING", "PENDING_APPROVAL"):
        if severity != "CRITICAL":
          severity = "WARNING"
        issues.append(f"시작 시점까지 남은 리드 타임이 {lead_hours:.1f}시간으로 최소 권장 120시간(5일) 미만임")
        remediations.append(
            "Future Reservation 사전 신청 쿼터 정책 기준에 맞추어 시작 일시를 최소 120시간(5일) 이후로 수정하여 재신청한다."
        )
    except ValueError:
      pass

  # 4. 활성 프로젝트 불일치 검사
  if active_project and res_project != active_project:
    if severity != "CRITICAL":
      severity = "WARNING"
    issues.append(f"활성 프로젝트({active_project})와 예약 대상 프로젝트({res_project})가 일치하지 않음")
    remediations.append(
        f"조회 및 심사 요청 시 정확한 프로젝트 ID({res_project})를 일치시켜 전달한다."
    )

  return {
      "name": name,
      "id": fr.get("id", "-"),
      "zone": zone,
      "project": res_project,
      "status": status,
      "machineType": fr.get("machineType", "-"),
      "acceleratorType": fr.get("acceleratorType", "-"),
      "count": fr.get("totalCount", fr.get("acceleratorCount", 0)),
      "severity": severity,
      "issues": issues,
      "remediations": remediations,
  }


def print_table(diagnoses: list[dict]):
  """진단 결과를 표 형식으로 콘솔에 출력한다."""
  print("\n" + "=" * 95)
  print(f"{'예약 이름':<26} {'영역':<16} {'수량':<6} {'상태':<18} {'심각도':<10}")
  print("-" * 95)
  for d in diagnoses:
    print(f"{d['name']:<26} {d['zone']:<16} {d['count']:<6} {d['status']:<18} {d['severity']:<10}")
  print("=" * 95)

  criticals = [d for d in diagnoses if d["severity"] == "CRITICAL"]
  warnings = [d for d in diagnoses if d["severity"] == "WARNING"]

  if criticals or warnings:
    print("\n[발견된 주요 결함 및 처방 조치]")
    for item in criticals + warnings:
      prefix = "[심각]" if item["severity"] == "CRITICAL" else "[주의]"
      print(f"\n* {prefix} {item['name']} (영역: {item['zone']}, 상태: {item['status']})")
      for iss in item["issues"]:
        print(f"  - 원인: {iss}")
      for rem in item["remediations"]:
        print(f"  - 처방: {rem}")
  else:
    print("\n모든 Future Reservation이 정상 상태다.")


def main():
  parser = argparse.ArgumentParser(
      description="Compute Engine GPU 및 특수 인스턴스 Future Reservation 상태 및 쿼터 정책 정밀 진단기"
  )
  parser.add_argument("--project", help="대상 GCP 프로젝트 ID")
  parser.add_argument("--zone", help="특정 영역 필터 (예: us-south1-a, us-central1-a)")
  parser.add_argument("--dry-run", action="store_true", help="실제 API 호출 없이 가상 샘플 데이터로 진단")
  parser.add_argument("--json", action="store_true", help="결과를 JSON 포맷으로 출력")
  args = parser.parse_args()

  project_id = args.project or get_default_project(is_dry_run=args.dry_run)
  if not project_id and not args.dry_run:
    print("GCP 프로젝트 ID가 지정되지 않았다. --project 플래그를 주거나 gcloud config set project를 설정한다.", file=sys.stderr)
    sys.exit(1)

  target_zone = args.zone or os.getenv("ZONE") or os.getenv("LOCATION")
  print(f"Compute Engine GPU 및 특수 인스턴스 Future Reservation 상태 진단 시작 (프로젝트: {project_id or 'dry-run-mode'})")
  if args.dry_run:
    print("--> 가상 실행 모드 (--dry-run) 활성화: 사전 시뮬레이션 데이터를 분석한다.")
    raw_reservations = get_mock_reservations()
  else:
    raw_reservations = fetch_future_reservations(project_id, target_zone)

  if not raw_reservations:
    print("조회된 Future Reservation 예약 내역이 없다.")
    return

  diagnoses = [evaluate_reservation(fr, project_id) for fr in raw_reservations]

  if args.json:
    print(json.dumps(diagnoses, indent=2, ensure_ascii=False))
  else:
    print_table(diagnoses)


if __name__ == "__main__":
  main()
