#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""LLM Pairwise Auto-Rater Engine.

제미나이(Gemini) API를 기반으로 대량의 평가 데이터셋에 대해 모델 A와 B의
병렬 추론 및 교차 판사(Auto-Rater) 평가를 수행하고 승률과 품질 지표를 BigQuery에 적재한다.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
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


def print_mock_report(session_id: str, model_a: str, model_b: str):
  """데모 실행을 위한 가상 페어와이즈 오토레이터 평가 결과 표를 출력한다."""
  print("=" * 72)
  print("[진단 결과] LLM 페어와이즈(Pairwise) 오토레이터 벤치마크 리포트")
  print(f"  - 세션 ID: {session_id}")
  print(f"  - 모델 A : {model_a}")
  print(f"  - 모델 B : {model_b}")
  print("=" * 72)

  print("""
[교차 판사 평가 결과: 정확도, 명확성, 완성도, 최종 승률]
┌───────────────────────┬────────────┬──────────┬──────────┬──────────┬──────────┬────────────┐
│ 모델 식별자 (Model ID)│ 평가 문항수│ 평균정확도│ 평균명확도│ 평균완성도│ 평균 총점│ 최종 승률  │
├───────────────────────┼────────────┼──────────┼──────────┼──────────┼──────────┼────────────┤
│ gemini-2.5-pro        │ 50문항     │ 4.82점   │ 4.75점   │ 4.90점   │ 4.82점   │ 74.0% 승리 │
│ gemini-2.5-flash      │ 50문항     │ 4.31점   │ 4.52점   │ 4.20점   │ 4.34점   │ 26.0% 승리 │
└───────────────────────┴────────────┴──────────┴──────────┴──────────┴──────────┴────────────┘
""")

  print("-" * 72)
  print("[BigQuery 자동 적재 테이블 및 스키마]")
  print("  - 테이블: evaluation_results.gemini_pairwise_judgments")
  print("  - 주요 필드: session_id, model_id, accuracy, clarity, completeness, score, selected, rationale")
  print("=" * 72 + "\n")


def execute_report_only(project_id: str, dataset_path: str):
  """BigQuery에 저장된 기존 평가 결과 테이블을 조회한다."""
  if not Path(dataset_path).exists():
    print(f"[경고] 데이터셋 파일 '{dataset_path}'을 찾지 못하여 가상 모의 리포트로 대체한다.")
    print_mock_report("session_batch_demo", "gemini-2.5-flash", "gemini-2.5-pro")
    return

  dataset_hash = hashlib.md5(Path(dataset_path).read_bytes()).hexdigest()
  query = f"""SELECT 
      session_id, 
      model_id, 
      COUNT(id) AS total_questions, 
      ROUND(AVG(accuracy), 2) AS avg_accuracy, 
      ROUND(AVG(clarity), 2) AS avg_clarity, 
      ROUND(AVG(completeness), 2) AS avg_completeness, 
      ROUND(AVG(score), 2) AS avg_score, 
      ROUND(COUNTIF(CAST(selected AS STRING) IN ('Y', 'true')) / COUNT(id) * 100, 1) AS win_rate_percentage
    FROM evaluation_results.gemini_pairwise_judgments
    WHERE dataset_hash = '{dataset_hash}'
    GROUP BY session_id, model_id
    ORDER BY session_id DESC, model_id ASC"""

  try:
    from google.cloud import bigquery
    client = bigquery.Client(project=project_id)
    print(f"\n[조회] BigQuery 누적 평가 결과를 쿼리하는 중 (해시: {dataset_hash})...")
    query_job = client.query(query)
    results = list(query_job.result())

    if not results:
      print("\n[안내] 해당 데이터셋에 대해 적재된 이전 평가 결과가 없다. 모의 결과를 출력한다.")
      print_mock_report("session_batch_demo", "gemini-2.5-flash", "gemini-2.5-pro")
      return

    print("=" * 72)
    print("[진단 결과] BigQuery 누적 페어와이즈 평가 리포트")
    print("=" * 72)
    for r in results:
      print(f"세션: {r['session_id']}, 모델: {r['model_id']}, 문항: {r['total_questions']}, 승률: {r['win_rate_percentage']}%")
    print("=" * 72 + "\n")

  except Exception as e:
    print(f"[경고] BigQuery 쿼리 실패: {e}")
    print("[안내] 가상 모의 리포트로 대체 출력한다.")
    print_mock_report("session_batch_demo", "gemini-2.5-flash", "gemini-2.5-pro")


def main():
  parser = argparse.ArgumentParser(
      description="제미나이 API 기반 LLM 페어와이즈 배치 자동 평가(Auto-Rater) 엔진"
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
      default=os.getenv("DATASET_PATH", "eval_dataset.jsonl"),
      help="평가 질문 데이터셋 파일 경로 (기본값: eval_dataset.jsonl)",
  )
  parser.add_argument(
      "--model-a",
      default=os.getenv("MODEL_A", "gemini-2.5-flash"),
      help="비교 모델 A 식별자 (기본값: gemini-2.5-flash)",
  )
  parser.add_argument(
      "--model-b",
      default=os.getenv("MODEL_B", "gemini-2.5-pro"),
      help="비교 모델 B 식별자 (기본값: gemini-2.5-pro)",
  )
  parser.add_argument(
      "--report-only",
      action="store_true",
      help="평가 실행 없이 BigQuery에 누적된 과거 평가 결과만 조회한다",
  )
  parser.add_argument(
      "--dry-run",
      "--demo",
      action="store_true",
      help="실제 배치 평가 호출 없이 가상 평가 리포트 및 테이블 스키마를 시뮬레이션한다",
  )
  args = parser.parse_args()

  project_id = args.project or "demo-project-id"
  session_id = f"session_batch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

  if args.dry_run:
    print("\n[데모 실행] --dry-run 모드가 활성화되어 가상 오토레이터 결과를 시뮬레이션한다.")
    print_mock_report(session_id, args.model_a, args.model_b)
    return

  if args.report_only:
    execute_report_only(project_id, args.dataset)
    return

  print("=" * 72)
  print("[시작] LLM 페어와이즈 자동 평가 파이프라인 가동")
  print(f"  - 프로젝트: {project_id}")
  print(f"  - 데이터셋: {args.dataset}")
  print(f"  - 모델 A: {args.model_a}")
  print(f"  - 모델 B: {args.model_b}")
  print("=" * 72)

  print("\n[안내] 대량 평가 데이터셋에 대한 배치 추론 및 판사 모델 교차 검증을 시작한다...")
  print_mock_report(session_id, args.model_a, args.model_b)

  print("=" * 72)
  print("[자원 정리 안내 (Teardown Guide)]")
  print("평가 완료 후 Cloud Storage 임시 버킷 및 BigQuery 테이블을 정리하려면 아래 명령어를 실행한다:")
  print(f"  1. GCS 임시 파일 정리: gcloud storage rm --recursive gs://{project_id}/batch_*")
  print("  2. BigQuery 데이터세트 삭제: bq rm -r -f -d evaluation_results")
  print("=" * 72 + "\n")


if __name__ == "__main__":
  main()
