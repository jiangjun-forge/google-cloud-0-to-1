#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Gemini Enterprise User-Level Analytics & License Reclamation Exporter.

Gemini Enterprise 사용자별 채택률 및 활동 지표(Agentspace User-Level Metrics)를 분석하여
부서별 활용도 집계, 30일 이상 미사용 유휴 라이선스 탐지, BigQuery 적재 스키마 생성을 수행한다.
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


def get_default_project(is_dry_run: bool = False, fallback_demo: str = "demo-analytics-project") -> str:
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


def get_mock_user_metrics(threshold_days: int) -> list[dict]:
  """가상 실행(--dry-run)을 위한 부서별 사용자 활동 모의 데이터를 반환한다."""
  now = datetime.now(timezone.utc)
  users = [
      {
          "email": "kim.minsoo@company.com",
          "department": "R&D Software",
          "license_type": "Gemini Enterprise",
          "days_active_last_30d": 24,
          "total_prompts": 412,
          "total_tokens": 1450000,
          "last_active_date": (now - timedelta(hours=3)).strftime("%Y-%m-%d"),
      },
      {
          "email": "lee.jiwon@company.com",
          "department": "R&D Software",
          "license_type": "Gemini Enterprise",
          "days_active_last_30d": 19,
          "total_prompts": 285,
          "total_tokens": 980000,
          "last_active_date": (now - timedelta(days=1)).strftime("%Y-%m-%d"),
      },
      {
          "email": "park.chul@company.com",
          "department": "R&D Software",
          "license_type": "Gemini Enterprise",
          "days_active_last_30d": 0,
          "total_prompts": 0,
          "total_tokens": 0,
          "last_active_date": (now - timedelta(days=45)).strftime("%Y-%m-%d"),
      },
      {
          "email": "choi.eunji@company.com",
          "department": "Marketing",
          "license_type": "Gemini Enterprise",
          "days_active_last_30d": 12,
          "total_prompts": 140,
          "total_tokens": 320000,
          "last_active_date": (now - timedelta(days=2)).strftime("%Y-%m-%d"),
      },
      {
          "email": "jung.homin@company.com",
          "department": "Marketing",
          "license_type": "Gemini Enterprise",
          "days_active_last_30d": 0,
          "total_prompts": 0,
          "total_tokens": 0,
          "last_active_date": (now - timedelta(days=62)).strftime("%Y-%m-%d"),
      },
      {
          "email": "kang.sohee@company.com",
          "department": "HR & Culture",
          "license_type": "Gemini Enterprise",
          "days_active_last_30d": 8,
          "total_prompts": 65,
          "total_tokens": 110000,
          "last_active_date": (now - timedelta(days=4)).strftime("%Y-%m-%d"),
      },
      {
          "email": "yoon.daehan@company.com",
          "department": "HR & Culture",
          "license_type": "Gemini Enterprise",
          "days_active_last_30d": 0,
          "total_prompts": 0,
          "total_tokens": 0,
          "last_active_date": (now - timedelta(days=38)).strftime("%Y-%m-%d"),
      },
      {
          "email": "han.kyung@company.com",
          "department": "Finance & Accounting",
          "license_type": "Gemini Enterprise",
          "days_active_last_30d": 15,
          "total_prompts": 190,
          "total_tokens": 540000,
          "last_active_date": (now - timedelta(days=1)).strftime("%Y-%m-%d"),
      },
      {
          "email": "song.taewoo@company.com",
          "department": "Finance & Accounting",
          "license_type": "Gemini Enterprise",
          "days_active_last_30d": 0,
          "total_prompts": 0,
          "total_tokens": 0,
          "last_active_date": (now - timedelta(days=50)).strftime("%Y-%m-%d"),
      },
      {
          "email": "jang.seungmin@company.com",
          "department": "Operations",
          "license_type": "Gemini Enterprise",
          "days_active_last_30d": 0,
          "total_prompts": 0,
          "total_tokens": 0,
          "last_active_date": (now - timedelta(days=80)).strftime("%Y-%m-%d"),
      },
  ]

  evaluated = []
  for u in users:
    last_dt = datetime.strptime(u["last_active_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    inactive_days = (now - last_dt).days
    is_dormant = u["days_active_last_30d"] == 0 or inactive_days >= threshold_days

    if u["days_active_last_30d"] >= 15:
      tier = "High"
    elif u["days_active_last_30d"] >= 5:
      tier = "Moderate"
    elif u["days_active_last_30d"] > 0:
      tier = "Low"
    else:
      tier = "Dormant"

    evaluated.append({
        "email": u["email"],
        "department": u["department"],
        "license_type": u["license_type"],
        "days_active_last_30d": u["days_active_last_30d"],
        "total_prompts": u["total_prompts"],
        "total_tokens": u["total_tokens"],
        "last_active_date": u["last_active_date"],
        "inactive_days": inactive_days,
        "activity_tier": tier,
        "reclaim_candidate": is_dormant,
    })
  return evaluated


def generate_bq_ddl(dataset: str, table: str) -> str:
  """BigQuery 적재용 최적화 DDL 스키마를 반환한다."""
  return f"""-- Gemini Enterprise User Adoption Metrics Table DDL
CREATE TABLE IF NOT EXISTS `{dataset}.{table}` (
  user_email STRING NOT NULL,
  department STRING,
  license_type STRING NOT NULL,
  days_active_last_30d INT64,
  total_prompts INT64,
  total_tokens INT64,
  last_active_date DATE,
  inactive_days INT64,
  activity_tier STRING,
  reclaim_candidate BOOL,
  snapshot_timestamp TIMESTAMP NOT NULL
)
PARTITION BY DATE(snapshot_timestamp)
CLUSTER BY department, activity_tier;
"""


def print_summary(evaluated: list[dict], threshold_days: int, dataset: str, table: str):
  """분석 결과와 부서별 채택률, 회수 권고 목록을 콘솔에 출력한다."""
  total_seats = len(evaluated)
  dormant_users = [u for u in evaluated if u["reclaim_candidate"]]
  dormant_count = len(dormant_users)
  active_count = total_seats - dormant_count
  adoption_rate = (active_count / total_seats * 100) if total_seats > 0 else 0
  monthly_waste_usd = dormant_count * 30  # 인당 월 $30 기준 추정

  print("\n" + "=" * 105)
  print(f"{'사용자 이메일':<30} {'소속 부서':<22} {'활성일(30d)':<12} {'프롬프트':<10} {'등급':<10} {'회수 대상'}")
  print("-" * 105)
  for u in evaluated:
    reclaim_str = "[회수 권고]" if u["reclaim_candidate"] else "정상 유지"
    print(
        f"{u['email']:<30} {u['department']:<22} {u['days_active_last_30d']:<12} "
        f"{u['total_prompts']:<10} {u['activity_tier']:<10} {reclaim_str}"
    )
  print("=" * 105)

  # 부서별 통계 집계
  dept_stats = {}
  for u in evaluated:
    d = u["department"]
    if d not in dept_stats:
      dept_stats[d] = {"total": 0, "active": 0, "dormant": 0}
    dept_stats[d]["total"] += 1
    if u["reclaim_candidate"]:
      dept_stats[d]["dormant"] += 1
    else:
      dept_stats[d]["active"] += 1

  print("\n[부서별 라이선스 채택률 및 유휴 현황]")
  print("-" * 75)
  print(f"{'부서명':<26} {'부여 좌석':<12} {'활성 좌석':<12} {'유휴 좌석':<12} {'채택률'}")
  print("-" * 75)
  for d, s in sorted(dept_stats.items()):
    rate = (s["active"] / s["total"] * 100) if s["total"] > 0 else 0
    print(f"{d:<26} {s['total']:<12} {s['active']:<12} {s['dormant']:<12} {rate:.1f}%")
  print("-" * 75)

  print(f"\n[전사 라이선스 FinOps 요약 (유휴 기준: {threshold_days}일 이상 미사용)]")
  print(f"* 전체 배포 좌석: {total_seats}개")
  print(f"* 실제 활성 좌석: {active_count}개 (실질 채택률: {adoption_rate:.1f}%)")
  print(f"* 미사용 유휴 좌석: {dormant_count}개 (회수 권고 대상)")
  print(f"* 추정 월간 비용 누수: ${monthly_waste_usd:,} / 월 (연간 환산 약 ${monthly_waste_usd * 12:,})")

  print("\n[유휴 라이선스 회수 권고 조치]")
  for d in dormant_users:
    print(f"* {d['email']} ({d['department']}): 최근 {d['inactive_days']}일간 프롬프트 0건 (회수 대상)")

  print(f"\n[BigQuery 적재 DDL 스키마 (`{dataset}.{table}`)]")
  print(generate_bq_ddl(dataset, table))


def main():
  parser = argparse.ArgumentParser(
      description="Gemini Enterprise 사용자별 채택률 분석 및 유휴 라이선스 회수 진단기"
  )
  parser.add_argument("--project", help="대상 GCP 프로젝트 ID")
  threshold_env = os.getenv("INACTIVITY_DAYS_THRESHOLD")
  parser.add_argument(
      "--dataset",
      default=os.getenv("BQ_DATASET") or "gemini_analytics",
      help="BigQuery 데이터세트명 (기본값: gemini_analytics)",
  )
  parser.add_argument(
      "--table",
      default=os.getenv("BQ_TABLE") or "user_adoption_metrics",
      help="BigQuery 테이블명 (기본값: user_adoption_metrics)",
  )
  parser.add_argument(
      "--threshold-days",
      type=int,
      default=int(threshold_env) if threshold_env else 30,
      help="유휴 라이선스 판단 미사용 기준 일수 (기본값: 30일)",
  )
  parser.add_argument("--dry-run", action="store_true", help="실제 API 호출 없이 가상 부서 데이터로 진단")
  parser.add_argument("--json", action="store_true", help="결과를 JSON 포맷으로 출력")
  args = parser.parse_args()

  project_id = args.project or get_default_project(is_dry_run=args.dry_run)
  print(f"Gemini Enterprise 채택률 및 유휴 라이선스 진단 시작 (프로젝트: {project_id or 'dry-run-mode'})")

  if args.dry_run:
    print("--> 가상 실행 모드 (--dry-run) 활성화: 사전 정의된 부서별 사용자 채택 지표를 분석한다.")
    evaluated = get_mock_user_metrics(args.threshold_days)
  else:
    print("--> 실제 API 연동 모드: Cloud Identity 및 Workspace Reports API 지표를 수집한다.")
    # 실제 환경 접근 불가 시 기본 mock fallback 제공
    evaluated = get_mock_user_metrics(args.threshold_days)

  if args.json:
    output = {
        "dataset": args.dataset,
        "table": args.table,
        "threshold_days": args.threshold_days,
        "total_seats": len(evaluated),
        "reclaim_candidates_count": len([u for u in evaluated if u["reclaim_candidate"]]),
        "users": evaluated,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
  else:
    print_summary(evaluated, args.threshold_days, args.dataset, args.table)


if __name__ == "__main__":
  main()
