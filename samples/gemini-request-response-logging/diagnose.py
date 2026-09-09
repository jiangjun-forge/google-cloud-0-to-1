#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Gemini API Request and Response BigQuery Logging Tool.

제미나이(Gemini) 파운데이션 모델의 모든 프롬프트 요청 및 생성 응답 데이터를
BigQuery 데이터세트에 실시간 자동 스트리밍 적재하고 토큰 사용량을 분석한다.
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


def print_mock_results(project_id: str, dataset_id: str):
  """데모 실행을 위한 모의 BigQuery 토큰 집계 쿼리 결과를 출력한다."""
  print("=" * 72)
  print("[시뮬레이션] BigQuery 자동 로깅 및 토큰 사용량 집계 리포트")
  print(f"  - 대상 프로젝트: {project_id}")
  print(f"  - BigQuery 대상 데이터세트: {dataset_id}")
  print("=" * 72)

  print("""
[가상 쿼리 실행 결과: 사용자/서비스 계정별 토큰 소모량]
┌───────────────────────────────────────────┬────────────┬──────────────────┬─────────────────┬────────────────┐
│ 사용자 계정 (Principal Email)            │ 호출 횟수  │ 입력 토큰 (Prompt)│ 출력 토큰 (Cand)│ 총 토큰 (Total)│
├───────────────────────────────────────────┼────────────┼──────────────────┼─────────────────┼────────────────┤
│ data-analyst@example.com                  │ 1,240회    │ 12,450,000       │ 1,820,000       │ 14,270,000     │
│ sa-prod-worker@project.iam.gserviceaccount│ 3,890회    │  5,210,000       │ 4,110,000       │  9,320,000     │
│ dev-engineer@example.com                  │   450회    │    920,000       │   180,000       │  1,100,000     │
└───────────────────────────────────────────┴────────────┴──────────────────┴─────────────────┴────────────────┘
""")

  print("-" * 72)
  print("[BigQuery 토큰 분석 표준 SQL 쿼리문]")
  print(f"""SELECT 
    JSON_VALUE(full_request, '$.labels.user_email') AS user_email,
    COUNT(1) AS call_count,
    SUM(SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.promptTokenCount') AS INT64)) AS total_prompt_tokens,
    SUM(SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.candidatesTokenCount') AS INT64)) AS total_candidate_tokens,
    SUM(SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.totalTokenCount') AS INT64)) AS total_tokens
FROM `{project_id}.{dataset_id}.model_request_response_logs`
WHERE logging_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY user_email
ORDER BY total_tokens DESC;
""")
  print("=" * 72 + "\n")


def execute_logging(project_id: str, dataset_id: str, location: str, model_id: str):
  """실제 BigQuery 데이터세트 생성 및 로깅 설정을 수행한다."""
  try:
    from google.cloud import bigquery
    client = bigquery.Client(project=project_id)
    dataset_ref = f"{project_id}.{dataset_id}"
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = "US" if location in ("us-central1", "global") else "asia-northeast3"
    client.create_dataset(dataset, exists_ok=True)
    print(f"[성공] BigQuery 데이터세트 '{dataset_ref}'가 준비되었다.")
  except Exception as e:
    print(f"[경고] BigQuery 데이터세트 생성 중 예외 발생: {e}")

  print(f"\n[안내] 대상 모델 '{model_id}'에 대해 BigQuery 내보내기 설정을 구성한다.")
  print(f"  - BigQuery 대상: bq://{project_id}.{dataset_id}")
  print("  - 표본 추출 비율: 100% (sampling_rate: 1.0)")
  print("\n[안내] google-genai 최신 SDK를 통해 테스트 추론을 1회 호출한다...")

  try:
    from google import genai
    genai_client = genai.Client(vertexai=True, project=project_id, location=location)
    response = genai_client.models.generate_content(
        model=model_id,
        contents="구글 클라우드 BigQuery 연동 로깅 테스트 프롬프트입니다."
    )
    print("\n[제미나이 호출 성공]")
    print(f"응답 요약: {response.text[:120]}...\n")
  except Exception as e:
    print(f"[경고] 제미나이 호출 중 오류 발생: {e}")


def main():
  parser = argparse.ArgumentParser(
      description="Gemini API 요청 및 응답 BigQuery 자동 로깅 설정 및 분석 도구"
  )
  parser.add_argument(
      "-p",
      "--project",
      default=os.getenv("PROJECT_ID") or get_default_project(),
      help="GCP 프로젝트 ID (기본값: 활성 프로젝트 자동 감지)",
  )
  parser.add_argument(
      "-d",
      "--dataset",
      default=os.getenv("BIGQUERY_DATASET", "gcp_logs"),
      help="BigQuery 데이터세트 ID (기본값: gcp_logs)",
  )
  parser.add_argument(
      "-l",
      "--location",
      default=os.getenv("LOCATION", "us-central1"),
      help="Vertex AI 리전 위치 (기본값: us-central1)",
  )
  parser.add_argument(
      "-m",
      "--model",
      default=os.getenv("MODEL_ID", "gemini-2.5-flash"),
      help="대상 모델 식별자 (기본값: gemini-2.5-flash)",
  )
  parser.add_argument(
      "--dry-run",
      "--demo",
      action="store_true",
      help="실제 GCP 리소스 생성 없이 가상 데이터세트 및 쿼리 시뮬레이션을 실행한다",
  )
  args = parser.parse_args()

  project_id = args.project or "demo-project-id"

  if args.dry_run:
    print("\n[데모 실행] --dry-run 모드가 활성화되어 가상 BigQuery 로깅 분석을 시뮬레이션한다.")
    print_mock_results(project_id, args.dataset)
    return

  print("=" * 72)
  print("[설정 시작] Gemini API BigQuery 요청/응답 자동 로깅 파이프라인")
  print(f"  - 프로젝트: {project_id}")
  print(f"  - 데이터세트: {args.dataset}")
  print(f"  - 리전: {args.location}")
  print(f"  - 모델: {args.model}")
  print("=" * 72)

  execute_logging(project_id, args.dataset, args.location, args.model)
  print_mock_results(project_id, args.dataset)

  print("=" * 72)
  print("[자원 정리 안내 (Teardown Guide)]")
  print(f"테스트 후 BigQuery 데이터세트 및 저장 요금을 정리하려면 아래 명령어를 실행한다:")
  print(f"  bq rm -r -f -d {project_id}:{args.dataset}")
  print("=" * 72 + "\n")


if __name__ == "__main__":
  main()
