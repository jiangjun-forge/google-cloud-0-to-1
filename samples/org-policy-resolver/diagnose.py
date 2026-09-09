#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""GCP Organization Policy Violation Resolver.

최근 발생한 GCP 조직 정책(Organization Policy) 제약 조건 위반 실패 감사 로그를 역추적하여
위반된 제약 조건 식별자 및 원클릭 정책 해제/우회 gcloud 명령어를 처방한다.
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
import re
import subprocess
import sys


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
  """쉘 명령어를 실행하고 결과를 반환한다."""
  res = subprocess.run(cmd, capture_output=True, text=True)
  return res.returncode, res.stdout.strip(), res.stderr.strip()


def get_default_project():
  """gcloud 설정에서 활성 프로젝트 ID를 조회한다."""
  _, stdout, _ = run_cmd(["gcloud", "config", "get-value", "project"])
  return stdout if stdout and "(unset)" not in stdout else None


def get_mock_violations():
  """데모 실행을 위한 가상 조직 정책 위반 로그 목록을 반환한다."""
  return [
      {
          "principal": "security-engineer@company.com",
          "service": "iam.googleapis.com",
          "method": "google.iam.admin.v1.CreateServiceAccountKey",
          "message": "Operation denied by organization policy: constraints/iam.disableServiceAccountKeyCreation violated",
          "constraint": "iam.disableServiceAccountKeyCreation",
      },
      {
          "principal": "cloud-infra-admin@company.com",
          "service": "compute.googleapis.com",
          "method": "compute.instances.insert",
          "message": "Operation denied by organization policy: constraints/compute.vmExternalIpAccess violated on instance vm-bastion-1",
          "constraint": "compute.vmExternalIpAccess",
      },
      {
          "principal": "web-deployer@company.com",
          "service": "storage.googleapis.com",
          "method": "storage.setIamPermissions",
          "message": "Constraint constraints/storage.publicAccessPrevention violated on bucket gs://web-static-assets",
          "constraint": "storage.publicAccessPrevention",
      },
  ]


def map_policy_info(constraint: str) -> tuple[str, str]:
  """제약 조건별 설명과 권장 처방을 도출한다."""
  if constraint == "iam.disableServiceAccountKeyCreation":
    return (
        "서비스 계정 키(JSON 키) 신규 생성을 전면 차단하는 조직 제약 조건이다.",
        "보안을 위해 워크로드 아이덴티티(Workload Identity) 연동을 권장하나, "
        "테스트 및 마이그레이션 단계에서 키 발급이 불가피한 경우 해당 프로젝트에 한해 제약을 해제할 수 있다."
    )
  elif constraint == "compute.vmExternalIpAccess":
    return (
        "Compute Engine VM 인스턴스에 외부 공용 IP 할당을 금지하는 조직 제약 조건이다.",
        "내부 IP 전용 VM 생성 및 Cloud NAT 게이트웨이 구성을 권장하나, "
        "단독 외부 접속이 필요한 경우 제약을 해제할 수 있다."
    )
  elif constraint == "storage.publicAccessPrevention":
    return (
        "Cloud Storage 버킷의 공용(allUsers) 공개 액세스를 차단하는 조직 제약 조건이다.",
        "데이터 유출 방지를 위해 비공개 액세스 유지를 권장하나, "
        "정적 웹사이트 호스팅이나 퍼블릭 다운로드 자산인 경우 제약을 해제할 수 있다."
    )
  else:
    return (
        "조직 리소스 생성 및 환경 설정을 제어하는 표준 보안 제약 조건이다.",
        "사내 보안 가이드라인을 검토하고 불가피한 경우에 한해 프로젝트 단위 정책 예외를 구성해야 한다."
    )


def report_violations(violations: list[dict], project_id: str, days: int):
  """진단 리포트 및 해결 명령어를 출력한다."""
  print("=" * 72)
  print("[진단 결과] GCP 조직 정책(Organization Policy) 위반 감사 추적 리포트")
  print(f"  - 대상 프로젝트: {project_id}")
  print(f"  - 조회 기간: 최근 {days}일")
  print("=" * 72)

  if not violations:
    print("\n[성공] 조직 정책 제약 조건(Constraints) 위반 실패 감사 로그가 발견되지 않았다. 안전하다!\n")
    return

  print(f"\n발견된 조직 정책 위반 실패 내역: {len(violations)}건\n")

  for idx, v in enumerate(violations, start=1):
    desc, action = map_policy_info(v["constraint"])

    print(f"[위반 건 #{idx}]")
    print(f"  - 실패 주체 계정  : {v['principal']}")
    print(f"  - 요청 대상 서비스: {v['service']}")
    print(f"  - 실행 실패 액션  : {v['method']}")
    print(f"  - 실제 오류 내용  : {v['message']}")
    print("  [정밀 처방 제약 조건 분석]")
    print(f"    - 검출 제약 사항: constraints/{v['constraint']}")
    print(f"    - 제약 조건 설명: {desc}")
    print(f"    - 권장 임시 방안: {action}")
    print("  [즉시 조치 가능한 원클릭 gcloud 해결 명령어]")
    print(f"    gcloud resource-manager org-policies disable-enforce \"{v['constraint']}\" \\")
    print(f"      --project=\"{project_id}\"")
    print("-" * 72)

  print("=" * 72 + "\n")


def fetch_violations(project_id: str, days: int, limit: int) -> list[dict]:
  """gcloud logging read 명령으로 조직 정책 위반 감사 로그를 조회한다."""
  start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
  log_filter = (
      f'logName:"projects/{project_id}/logs/cloudaudit.googleapis.com%2Factivity" AND '
      f'(protoPayload.status.code=9 OR protoPayload.status.message:"Constraint" OR protoPayload.status.message:"violated") AND '
      f'timestamp>="{start_date}"'
  )

  cmd = [
      "gcloud",
      "logging",
      "read",
      log_filter,
      f"--project={project_id}",
      "--format=json",
      f"--limit={limit}",
  ]
  code, stdout, stderr = run_cmd(cmd)
  if code != 0:
    print(f"[경고] Cloud Logging 조회 실패: {stderr}")
    return []

  results = []
  try:
    entries = json.loads(stdout) if stdout else []
    for entry in entries:
      proto = entry.get("protoPayload", {})
      auth = proto.get("authenticationInfo", {})
      status = proto.get("status", {})
      msg = status.get("message", "")

      # 제약 조건 ID 추출
      match = re.search(r"constraints/([a-zA-Z0-9.]+)", msg)
      constraint = match.group(1) if match else "unknown"

      results.append({
          "principal": auth.get("principalEmail", "미식별"),
          "service": proto.get("serviceName", "unknown"),
          "method": proto.get("methodName", "unknown"),
          "message": msg,
          "constraint": constraint,
      })
  except Exception as e:
    print(f"[경고] 로그 JSON 파싱 중 오류: {e}")
  return results


def main():
  parser = argparse.ArgumentParser(
      description="GCP 조직 정책(Organization Policy) 위반 감사 추적 및 복구 처방 도구"
  )
  parser.add_argument(
      "-p",
      "--project",
      default=os.getenv("PROJECT_ID") or get_default_project(),
      help="GCP 프로젝트 ID (기본값: 활성 프로젝트 자동 감지)",
  )
  parser.add_argument(
      "-d",
      "--days",
      type=int,
      default=int(os.getenv("DAYS", "7")),
      help="조회 대상 최근 기간 일수 (기본값: 7)",
  )
  parser.add_argument(
      "-l",
      "--limit",
      type=int,
      default=int(os.getenv("LIMIT_COUNT", "5")),
      help="조회 대상 실패 로그 최대 건수 (기본값: 5)",
  )
  parser.add_argument(
      "--dry-run",
      "--demo",
      action="store_true",
      help="실제 Cloud Logging 호출 없이 가상 조직 정책 위반 시뮬레이션을 실행한다",
  )
  args = parser.parse_args()

  project_id = args.project or "demo-project-id"

  if args.dry_run:
    print("\n[데모 실행] --dry-run 모드가 활성화되어 가상 조직 정책 위반 리포트를 시뮬레이션한다.")
    report_violations(get_mock_violations(), project_id, args.days)
    return

  print("=" * 72)
  print("[스캔 시작] GCP 최근 조직 정책 제약 조건 위반 감사 로그 역추적")
  print(f"  - 프로젝트 ID: {project_id}")
  print(f"  - 조회 기간: 최근 {args.days}일")
  print(f"  - 최대 건수: {args.limit}건")
  print("=" * 72)

  violations = fetch_violations(project_id, args.days, args.limit)
  report_violations(violations, project_id, args.days)

  print("=" * 72)
  print("[자원 정리 안내 (Teardown Guide)]")
  print("본 도구는 순수 감사 로그 조회 도구이므로 별도의 자원 정리 작업이 필요하지 않다.")
  print("=" * 72 + "\n")


if __name__ == "__main__":
  main()
