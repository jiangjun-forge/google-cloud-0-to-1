#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Gemini API VPC Service Controls Denial Resolver.

제미나이(Gemini) 및 Vertex AI 호출 시 발생하는 VPC Service Controls(VPC-SC)
보안 경계 차단(Perimeter Denial) 감사 로그를 역추적하고 원인별 해결책을 처방한다.
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
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


def get_mock_denials():
  """데모 실행을 위한 가상 VPC-SC 거부 로그 목록을 반환한다."""
  return [
      {
          "principal": "developer-workstation@company.com",
          "service": "aiplatform.googleapis.com",
          "method": "google.cloud.aiplatform.v1beta1.PredictionService.GenerateContent",
          "reason": "NO_MATCHING_INGRESS_POLICY",
          "denial_id": "vpc-sc-denial-8f2a1b9c-4d3e-41a2-98bc-abcdef012345",
      },
      {
          "principal": "data-pipeline-sa@my-prod.iam.gserviceaccount.com",
          "service": "aiplatform.googleapis.com",
          "method": "google.cloud.aiplatform.v1beta1.PredictionService.StreamGenerateContent",
          "reason": "RESOURCES_NOT_IN_SAME_PERIMETER",
          "denial_id": "vpc-sc-denial-3c7d9e1a-5b6f-42c8-89ae-123456789abc",
      },
  ]


def get_prescription(reason: str) -> str:
  """VPC-SC 거부 사유 코드에 따른 권장 처방을 도출한다."""
  if reason in ("NO_MATCHING_INGRESS_POLICY", "IP_SUBMET_NOT_IN_PERIMETER"):
    return (
        "API 호출자가 신뢰할 수 없는 공용 IP 대역 또는 미지정 사설 서브넷에서 접근했다. "
        "VPC-SC 수신(Ingress) 규칙에 호출자의 IP 서브넷 대역 또는 서비스 계정을 명시적으로 허용해야 한다."
    )
  elif reason in ("SERVICE_NOT_RESTRICTED", "RESOURCES_NOT_IN_SAME_PERIMETER"):
    return (
        "제미나이 API(aiplatform.googleapis.com)가 경계 보호 대상으로 누락되었거나, "
        "호출 리소스와 대상 모델이 서로 다른 보안 경계로 분리되어 있다. "
        "두 리소스를 동일한 서비스 경계로 병합하거나 경계 간 브리지(Bridge) 규칙을 구성해야 한다."
    )
  else:
    return (
        "비공개 Google 액세스(Private Google Access) 또는 Private Service Connect(PSC) 연결이 불안정하다. "
        "사설 DNS 해석 및 서브넷 라우팅 테이블 구성을 점검해야 한다."
    )


def report_denials(denials: list[dict], project_id: str, days: int):
  """진단 리포트 및 문제 해결 처방을 출력한다."""
  print("=" * 72)
  print("[진단 결과] 제미나이(Gemini) VPC Service Controls 경계 차단 진단 리포트")
  print(f"  - 대상 프로젝트: {project_id}")
  print(f"  - 조회 기간: 최근 {days}일")
  print("=" * 72)

  if not denials:
    print("\n[성공] 지정한 기간 내 VPC-SC 경계 차단(Perimeter Denial) 로그가 발견되지 않았다. 안전하다!\n")
    return

  print(f"\n발견된 VPC-SC 경계 거부 사례: {len(denials)}건\n")

  for idx, d in enumerate(denials, start=1):
    print(f"[거부 사례 #{idx}]")
    print(f"  - 호출 주체 계정: {d['principal']}")
    print(f"  - 대상 서비스   : {d['service']}")
    print(f"  - 호출 메서드   : {d['method']}")
    print(f"  - 거부 사유 코드: {d['reason']}")
    print(f"  - 고유 거부 ID  : {d['denial_id']}")
    print("  [권장 처방 및 복구 가이드]")
    print(f"    - 원인 분석 및 해결책: {get_prescription(d['reason'])}")
    print("    - VPC-SC 문제 해결사 콘솔 ( https://console.cloud.google.com/security/vpc-service-controls/troubleshooter )")
    print("    - 서비스 경계 관리 콘솔 ( https://console.cloud.google.com/security/vpc-service-controls )")
    print("-" * 72)

  print("=" * 72 + "\n")


def fetch_denials(project_id: str, days: int, limit: int) -> list[dict]:
  """gcloud logging read 명령으로 VPC-SC 감사 로그를 조회한다."""
  start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
  log_filter = (
      f'logName:"projects/{project_id}/logs/cloudaudit.googleapis.com%2Fpolicy" AND '
      f'protoPayload.metadata.securityPolicyViolations:* AND timestamp>="{start_date}"'
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
      metadata = proto.get("metadata", {})
      violations = metadata.get("securityPolicyViolations", [{}])
      v0 = violations[0] if violations else {}

      results.append({
          "principal": auth.get("principalEmail", "미식별"),
          "service": proto.get("serviceName", "aiplatform.googleapis.com"),
          "method": proto.get("methodName", "미식별"),
          "reason": v0.get("violationReason", "UNKNOWN"),
          "denial_id": v0.get("uuid", "미식별"),
      })
  except Exception as e:
    print(f"[경고] 로그 JSON 파싱 중 오류: {e}")
  return results


def main():
  parser = argparse.ArgumentParser(
      description="제미나이 API VPC-SC 경계 차단 감사 로그 분석 및 문제 해결 처방 도구"
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
      help="실제 Cloud Logging 호출 없이 가상 시뮬레이션 모드로 실행한다",
  )
  args = parser.parse_args()

  project_id = args.project or "demo-project-id"

  if args.dry_run:
    print("\n[데모 실행] --dry-run 모드가 활성화되어 가상 VPC-SC 차단 리포트를 시뮬레이션한다.")
    report_denials(get_mock_denials(), project_id, args.days)
    return

  print("=" * 72)
  print("[스캔 시작] 제미나이 API VPC-SC 경계 차단 감사 로그 역추적")
  print(f"  - 프로젝트 ID: {project_id}")
  print(f"  - 조회 기간: 최근 {args.days}일")
  print(f"  - 최대 건수: {args.limit}건")
  print("=" * 72)

  denials = fetch_denials(project_id, args.days, args.limit)
  report_denials(denials, project_id, args.days)

  print("=" * 72)
  print("[자원 정리 안내 (Teardown Guide)]")
  print("본 도구는 순수 감사 로그 조회 도구이므로 별도의 자원 정리 작업이 필요하지 않다.")
  print("=" * 72 + "\n")


if __name__ == "__main__":
  main()
