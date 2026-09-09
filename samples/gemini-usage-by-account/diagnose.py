#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Gemini API Usage by Account Analyzer.

제미나이(Gemini) 파운데이션 모델의 BigQuery 자동 로깅 테이블을 조회하여
사용자(계정) 및 서비스 계정별 호출 횟수, 입력/출력/생각(Thinking) 토큰 소모량을 정밀 집계한다.
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


def get_sql_query(project_id: str, dataset: str, table: str, days: int) -> str:
  """BigQuery 분석용 표준 SQL 쿼리를 생성한다."""
  return f"""SELECT 
    COALESCE(JSON_VALUE(full_request, '$.labels.principal_email'), 'default_user') AS user_email,
    COUNT(1) AS request_count,
    SUM(SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.promptTokenCount') AS INT64)) AS total_input_tokens,
    SUM(SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.candidatesTokenCount') AS INT64)) AS total_output_tokens,
    SUM(SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.thoughtsTokenCount') AS INT64)) AS total_thinking_tokens
FROM `{project_id}.{dataset}.{table}`
WHERE logging_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
GROUP BY user_email
ORDER BY request_count DESC;"""


def print_mock_results(project_id: str, dataset: str, table: str, days: int):
  """데모 실행을 위한 가상 계정별 사용량 집계 결과를 출력한다."""
  print("=" * 72)
  print("[진단 결과] 제미나이(Gemini) API 계정별 사용량 및 토큰 통계 리포트")
  print(f"  - 대상 프로젝트: {project_id}")
  print(f"  - BigQuery 테이블: {dataset}.{table}")
  print(f"  - 집계 기간: 최근 {days}일")
  print("=" * 72)

  print("""
[계정별 API 호출 횟수 및 상세 토큰 소모량 순위]
┌───────────────────────────────────────────┬────────────┬──────────────────┬─────────────────┬──────────────────┐
│ 사용자 계정 (Principal Email)            │ 호출 횟수  │ 입력 토큰 (Prompt)│ 출력 토큰 (Cand)│ 생각 토큰 (Think)│
├───────────────────────────────────────────┼────────────┼──────────────────┼─────────────────┼──────────────────┤
│ dev-backend@company.iam.gserviceaccount   │ 8,420회    │ 25,260,000       │ 4,210,000       │ 1,530,000        │
│ kim.developer@company.com                 │ 1,350회    │  4,050,000       │   675,000       │   220,000        │
│ lee.analyst@company.com                   │   820회    │  1,640,000       │   410,000       │   110,000        │
│ park.intern@company.com                   │    95회    │    190,000       │    47,500       │    12,000        │
└───────────────────────────────────────────┴────────────┴──────────────────┴─────────────────┴──────────────────┘
""")

  print("-" * 72)
  print("[실행된 BigQuery 표준 SQL]")
  print(get_sql_query(project_id, dataset, table, days))
  print("=" * 72 + "\n")


def execute_query(project_id: str, dataset: str, table: str, days: int):
  """실제 BigQuery 라이브러리를 통해 쿼리를 실행한다."""
  try:
    from google.cloud import bigquery
    client = bigquery.Client(project=project_id)
    query = get_sql_query(project_id, dataset, table, days)
    print(f"\n[실행] BigQuery 쿼리를 수행하는 중 ({dataset}.{table})...")
    query_job = client.query(query)
    results = list(query_job.result())

    print("=" * 72)
    print("[진단 결과] 제미나이(Gemini) API 계정별 사용량 및 토큰 통계 리포트")
    print(f"  - 대상 프로젝트: {project_id}")
    print(f"  - BigQuery 테이블: {dataset}.{table}")
    print(f"  - 집계 기간: 최근 {days}일")
    print("=" * 72)

    if not results:
      print("\n[안내] 지정한 기간 내 집계된 호출 로그 데이터가 존재하지 않는다.\n")
      return

    print(f"\n집계된 사용자 계정 수: {len(results)}개\n")
    for row in results:
      print(f"계정: {row['user_email']}")
      print(f"  - 호출 횟수: {row['request_count']}회")
      print(f"  - 입력 토큰: {row['total_input_tokens'] or 0:,}")
      print(f"  - 출력 토큰: {row['total_output_tokens'] or 0:,}")
      print(f"  - 생각 토큰: {row['total_thinking_tokens'] or 0:,}")
      print("-" * 72)

  except Exception as e:
    print(f"[경고] BigQuery 쿼리 실행 중 오류 발생 (테이블 부재 또는 권한 확인 필요): {e}")
    print("[안내] 가상 모의 리포트로 폴백하여 출력 형식을 제시한다.")
    print_mock_results(project_id, dataset, table, days)


def main():
  parser = argparse.ArgumentParser(
      description="제미나이 API BigQuery 자동 로깅 기반 계정별 토큰 사용량 집계 도구"
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
      "--dataset",
      default=os.getenv("BIGQUERY_DATASET", "gcp_logs"),
      help="BigQuery 데이터세트 ID (기본값: gcp_logs)",
  )
  parser.add_argument(
      "--table",
      default=os.getenv("TABLE_NAME", "request_response_logging"),
      help="BigQuery 로깅 테이블 이름 (기본값: request_response_logging)",
  )
  parser.add_argument(
      "--dry-run",
      "--demo",
      action="store_true",
      help="실제 BigQuery 쿼리 호출 없이 모의 통계 리포트를 시뮬레이션한다",
  )
  args = parser.parse_args()

  project_id = args.project or "demo-project-id"

  if args.dry_run:
    print("\n[데모 실행] --dry-run 모드가 활성화되어 가상 계정별 통계를 시뮬레이션한다.")
    print_mock_results(project_id, args.dataset, args.table, args.days)
    return

  execute_query(project_id, args.dataset, args.table, args.days)

  print("=" * 72)
  print("[자원 정리 안내 (Teardown Guide)]")
  print("본 도구는 순수 BigQuery 조회(SELECT) 도구이므로 클라우드 리소스 생성 및 삭제 작업이 필요하지 않다.")
  print("=" * 72 + "\n")


if __name__ == "__main__":
  main()
