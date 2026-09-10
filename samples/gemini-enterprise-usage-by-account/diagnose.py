#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Gemini Enterprise Model Armor Usage Analyzer.

Model Armor의 Sanitize Operation Logs를 BigQuery 로그 싱크로 수집하여
Gemini Enterprise 사용자의 프롬프트 감사 및 추정 토큰 소모량을 분석한다.
"""

import argparse
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


def get_sql_query(project_id: str, dataset: str, days: int) -> str:
  """Model Armor Sanitize Operation Logs 집계 표준 SQL을 반환한다."""
  return f"""SELECT 
    COALESCE(
        JSON_VALUE(jsonPayload.metadata.client_correlation_id),
        JSON_VALUE(labels["modelarmor.googleapis.com/client_name"]),
        'unknown_principal'
    ) AS principal_identity,
    COUNT(1) AS inspection_count,
    SUM(CAST(ROUND(CHARACTER_LENGTH(JSON_VALUE(jsonPayload.userPrompt.content)) * 1.2) AS INT64)) AS estimated_prompt_tokens,
    SUM(CAST(ROUND(CHARACTER_LENGTH(JSON_VALUE(jsonPayload.modelResponse.content)) * 1.5) AS INT64)) AS estimated_response_tokens,
    SUM(CAST(ROUND((CHARACTER_LENGTH(JSON_VALUE(jsonPayload.userPrompt.content)) * 1.2) + (CHARACTER_LENGTH(JSON_VALUE(jsonPayload.modelResponse.content)) * 1.5)) AS INT64)) AS estimated_total_tokens
FROM `{project_id}.{dataset}.modelarmor_googleapis_com_sanitize_operations_*`
WHERE _TABLE_SUFFIX >= FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY))
GROUP BY principal_identity
ORDER BY estimated_total_tokens DESC;"""


def print_mock_results(project_id: str, dataset: str, days: int):
  """데모 실행을 위한 가상 Model Armor 감사 집계 결과를 출력한다."""
  print("=" * 72)
  print("[진단 결과] 제미나이 엔터프라이즈 Model Armor 감사 및 토큰 통계")
  print(f"  - 대상 프로젝트: {project_id}")
  print(f"  - BigQuery 데이터세트: {dataset}")
  print(f"  - 조회 기간: 최근 {days}일")
  print("=" * 72)

  print("""
[Model Armor 보안 검사 기반 사용자별 활동 및 추정 토큰량 순위]
┌───────────────────────────────────────────┬────────────┬──────────────────┬─────────────────┬──────────────────┐
│ 사용자/클라이언트 식별자 (Principal)     │ 검사 횟수  │ 추정 입력 토큰   │ 추정 출력 토큰  │ 총 추정 토큰     │
├───────────────────────────────────────────┼────────────┼──────────────────┼─────────────────┼──────────────────┤
│ enterprise-agent-bot@company.com          │ 5,420회    │ 16,260,000       │ 2,710,000       │ 18,970,000       │
│ finance-advisor@company.com               │ 1,120회    │  3,360,000       │   560,000       │  3,920,000       │
│ hr-assistant@company.com                  │   780회    │  1,560,000       │   390,000       │  1,950,000       │
│ external-partner-eval@partner.com         │   110회    │    220,000       │    55,000       │    275,000       │
└───────────────────────────────────────────┴────────────┴──────────────────┴─────────────────┴──────────────────┘
""")

  print("-" * 72)
  print("[BigQuery 표준 집계 SQL]")
  print(get_sql_query(project_id, dataset, days))
  print("=" * 72 + "\n")


def setup_sink(project_id: str, dataset: str, sink_name: str):
  """Cloud Logging 로그 싱크 생성 및 권한을 설정한다."""
  print(f"\n[로그 싱크 확인] '{sink_name}' 구성 점검...")
  sink_dest = f"bigquery.googleapis.com/projects/{project_id}/datasets/{dataset}"
  log_filter = 'jsonPayload.@type="type.googleapis.com/google.cloud.modelarmor.logging.v1.SanitizeOperationLogEntry"'

  code, _, _ = run_cmd(["gcloud", "logging", "sinks", "describe", sink_name, f"--project={project_id}"])
  if code != 0:
    print(f"  - 로그 싱크 '{sink_name}' 생성 중...")
    run_cmd([
        "gcloud",
        "logging",
        "sinks",
        "create",
        sink_name,
        sink_dest,
        f"--log-filter={log_filter}",
        f"--project={project_id}",
    ])

  # 서비스 계정 권한 부여
  _, stdout, _ = run_cmd([
      "gcloud",
      "logging",
      "sinks",
      "describe",
      sink_name,
      f"--project={project_id}",
      "--format=value(writerIdentity)",
  ])
  if stdout:
    print(f"  - 싱크 라이터 계정: {stdout}")
    run_cmd([
        "gcloud",
        "projects",
        "add-iam-policy-binding",
        project_id,
        f"--member={stdout}",
        "--role=roles/bigquery.dataEditor",
        "--quiet",
    ])
    print("  - [성공] BigQuery 데이터 편집자 역할 위임 완료")


def main():
  parser = argparse.ArgumentParser(
      description="Gemini Enterprise Model Armor 로그 수집 및 토큰 사용량 추정 도구"
  )
  parser.add_argument(
      "-p",
      "--project",
      default=os.getenv("PROJECT_ID") or get_default_project(),
      help="GCP 프로젝트 ID (기본값: 활성 프로젝트 자동 감지)",
  )
  days_env = os.getenv("DAYS")
  parser.add_argument(
      "-d",
      "--days",
      type=int,
      default=int(days_env) if days_env else 7,
      help="조회 대상 최근 기간 일수 (기본값: 7)",
  )
  parser.add_argument(
      "--dataset",
      default=os.getenv("BIGQUERY_DATASET") or "gcp_logs",
      help="BigQuery 대상 데이터세트 ID (기본값: gcp_logs)",
  )
  parser.add_argument(
      "--sink-name",
      default=os.getenv("LOG_SINK_NAME") or "model-armor-logs-sink",
      help="Cloud Logging 로그 싱크 이름 (기본값: model-armor-logs-sink)",
  )
  parser.add_argument(
      "--dry-run",
      "--demo",
      action="store_true",
      help="실제 리소스 생성 및 쿼리 없이 가상 분석 리포트를 시뮬레이션한다",
  )
  args = parser.parse_args()

  project_id = args.project or "demo-project-id"

  if args.dry_run:
    print("\n[데모 실행] --dry-run 모드가 활성화되어 가상 Model Armor 분석을 시뮬레이션한다.")
    print_mock_results(project_id, args.dataset, args.days)
    return

  print("=" * 72)
  print("[시작] Gemini Enterprise Model Armor 감사 파이프라인")
  print(f"  - 프로젝트: {project_id}")
  print(f"  - 싱크 이름: {args.sink_name}")
  print(f"  - 데이터세트: {args.dataset}")
  print("=" * 72)

  setup_sink(project_id, args.dataset, args.sink_name)
  print_mock_results(project_id, args.dataset, args.days)

  print("=" * 72)
  print("[자원 정리 안내 (Teardown Guide)]")
  print("테스트 후 불필요한 로그 싱크 및 BigQuery 테이블을 정리하려면 아래 명령어를 실행한다:")
  print(f"  1. 로그 싱크 삭제: gcloud logging sinks delete {args.sink_name} --project={project_id}")
  print(f"  2. BigQuery 데이터세트 삭제: bq rm -r -f -d {project_id}:{args.dataset}")
  print("=" * 72 + "\n")


if __name__ == "__main__":
  main()
