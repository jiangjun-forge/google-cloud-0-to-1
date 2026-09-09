#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""GCP IAM Permission Denial Resolver.

최근 발생한 GCP 데이터 액세스 권한 거부(Permission Denied / 403) 감사 로그를 역추적하여
호출 주체별로 필요한 최소 권한 IAM 역할과 복구 gcloud 명령어를 원클릭으로 처방한다.
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


def get_mock_failures():
  """데모 실행을 위한 가상 권한 거부 로그 목록을 반환한다."""
  return [
      {
          "principal": "backend-developer@company.com",
          "service": "aiplatform.googleapis.com",
          "method": "google.cloud.aiplatform.v1beta1.PredictionService.GenerateContent",
          "message": "Permission 'aiplatform.endpoints.predict' denied on resource",
      },
      {
          "principal": "batch-pipeline-sa@my-prod.iam.gserviceaccount.com",
          "service": "bigquery.googleapis.com",
          "method": "google.cloud.bigquery.v2.JobService.InsertJob",
          "message": "Access Denied: Table my-prod:gcp_logs.request_response_logging: Permission bigquery.tables.getData denied",
      },
      {
          "principal": "intern-analyst@company.com",
          "service": "storage.googleapis.com",
          "method": "storage.objects.get",
          "message": "Access denied: storage.objects.get for bucket gs://my-ml-datasets",
      },
  ]


def map_role(service_name: str) -> tuple[str, str]:
  """실패 서비스에 적합한 최소 권한 역할과 설명을 매핑한다."""
  if "aiplatform" in service_name:
    return "roles/aiplatform.user", "Gemini API 호출 및 Vertex AI 파운데이션 모델 추론 권한"
  elif "bigquery" in service_name:
    return "roles/bigquery.dataEditor", "BigQuery 데이터세트 수정 및 테이블 데이터 편집 권한"
  elif "storage" in service_name:
    return "roles/storage.objectViewer", "Cloud Storage 버킷 객체 조회 뷰어 권한"
  elif "logging" in service_name:
    return "roles/logging.viewer", "Cloud Logging 로그 조회 뷰어 권한"
  else:
    return "roles/viewer", "서비스 기본 리소스 조회 뷰어 권한"


def report_failures(failures: list[dict], project_id: str, days: int):
  """진단 리포트 및 해결 명령어를 출력한다."""
  print("=" * 72)
  print("[진단 결과] GCP IAM 권한 거부(403) 감사 추적 및 해결 처방 리포트")
  print(f"  - 대상 프로젝트: {project_id}")
  print(f"  - 조회 기간: 최근 {days}일")
  print("=" * 72)

  if not failures:
    print("\n[성공] 데이터 액세스 권한 거부(403) 실패 감사 로그가 발견되지 않았다. 안전하다!\n")
    return

  print(f"\n발견된 권한 거부 실패 내역: {len(failures)}건\n")

  for idx, f in enumerate(failures, start=1):
    role, role_desc = map_role(f["service"])
    member_type = "serviceAccount" if "gserviceaccount.com" in f["principal"] else "user"

    print(f"[실패 건 #{idx}]")
    print(f"  - 실패 주체 계정: {f['principal']}")
    print(f"  - 요청 대상 서비스: {f['service']}")
    print(f"  - 실행 실패 액션: {f['method']}")
    print(f"  - 실제 오류 내용: {f['message']}")
    print("  [정밀 처방 역할 추천]")
    print(f"    - 권장 역할: {role}")
    print(f"    - 역할 상세: {role_desc}")
    print("  [즉시 조치 가능한 원클릭 gcloud 해결 명령어]")
    print(f"    gcloud projects add-iam-policy-binding \"{project_id}\" \\")
    print(f"      --member=\"{member_type}:{f['principal']}\" \\")
    print(f"      --role=\"{role}\"")
    print("-" * 72)

  print("=" * 72 + "\n")


def fetch_failures(project_id: str, days: int, limit: int) -> list[dict]:
  """gcloud logging read 명령으로 403 권한 거부 감사 로그를 조회한다."""
  start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
  log_filter = (
      f'logName:"projects/{project_id}/logs/cloudaudit.googleapis.com%2Fdata_access" AND '
      f'(protoPayload.status.code=7 OR protoPayload.status.message:"Permission denied" OR protoPayload.status.message:"Forbidden") AND '
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

      results.append({
          "principal": auth.get("principalEmail", "미식별"),
          "service": proto.get("serviceName", "unknown"),
          "method": proto.get("methodName", "unknown"),
          "message": status.get("message", "Permission denied"),
      })
  except Exception as e:
    print(f"[경고] 로그 JSON 파싱 중 오류: {e}")
  return results


def main():
  parser = argparse.ArgumentParser(
      description="GCP IAM 권한 거부(403) 로그 역추적 및 원클릭 복구 처방 도구"
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
      help="실제 Cloud Logging 호출 없이 가상 권한 거부 시뮬레이션을 실행한다",
  )
  args = parser.parse_args()

  project_id = args.project or "demo-project-id"

  if args.dry_run:
    print("\n[데모 실행] --dry-run 모드가 활성화되어 가상 권한 거부 리포트를 시뮬레이션한다.")
    report_failures(get_mock_failures(), project_id, args.days)
    return

  print("=" * 72)
  print("[스캔 시작] GCP 최근 데이터 액세스 권한 거부 감사 로그 역추적")
  print(f"  - 프로젝트 ID: {project_id}")
  print(f"  - 조회 기간: 최근 {args.days}일")
  print(f"  - 최대 건수: {args.limit}건")
  print("=" * 72)

  failures = fetch_failures(project_id, args.days, args.limit)
  report_failures(failures, project_id, args.days)

  print("=" * 72)
  print("[자원 정리 안내 (Teardown Guide)]")
  print("본 도구는 순수 감사 로그 조회 도구이므로 별도의 자원 정리 작업이 필요하지 않다.")
  print("=" * 72 + "\n")


if __name__ == "__main__":
  main()
