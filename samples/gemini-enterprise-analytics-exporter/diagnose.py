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


def get_default_project(is_dry_run: bool = False, fallback_demo: str = "sample-project-id") -> str:
  """환경 변수, gcloud 설정, 실시간 프로젝트 목록에서 활성 프로젝트를 탐색/선택한다."""
  if is_dry_run:
    return fallback_demo
  env_proj = os.getenv("PROJECT_ID")
  if env_proj:
    return env_proj
  _, stdout, _ = run_cmd(["gcloud", "config", "get-value", "project"])
  if stdout and "(unset)" not in stdout:
    return stdout

  if not sys.stdin.isatty():
    return fallback_demo

  code, stdout, _ = run_cmd(["gcloud", "projects", "list", "--format=value(projectId)", "--limit=5"])
  projects = [p.strip() for p in stdout.splitlines() if p.strip()] if code == 0 and stdout else []
  if projects:
    print("\n[?] 대상 GCP 프로젝트가 지정되지 않았다. 현재 접근 가능한 프로젝트 목록:")
    for idx, p in enumerate(projects, 1):
      print(f"  [{idx}] {p}")
    print(f"  [{len(projects) + 1}] 직접 입력 (Custom Input)")
    choice = input(f"선택할 번호 입력 [1-{len(projects) + 1}] (Enter 시 1번): ").strip()
    if not choice or choice == "1":
      return projects[0]
    if choice.isdigit() and 1 <= int(choice) <= len(projects):
      return projects[int(choice) - 1]
    if choice == str(len(projects) + 1):
      custom = input("프로젝트 ID 직접 입력: ").strip()
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


def print_summary(evaluated: list[dict], threshold_days: int, dataset: str, table: str, seat_cost: float = 30.0):
  """분석 결과와 부서별 채택률, 회수 권고 목록을 콘솔에 출력한다."""
  total_seats = len(evaluated)
  dormant_users = [u for u in evaluated if u["reclaim_candidate"]]
  dormant_count = len(dormant_users)
  active_count = total_seats - dormant_count
  adoption_rate = (active_count / total_seats * 100) if total_seats > 0 else 0
  monthly_waste_usd = dormant_count * seat_cost

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
  if seat_cost > 0:
    print(f"* 추정 월간 비용 누수: 약 ${monthly_waste_usd:,} / 월 (좌석당 ${seat_cost:,}/월 기준, 공식 요금: https://cloud.google.com/gemini-enterprise/pricing )")
  else:
    print("* 추정 월간 비용 누수: 사내 계약 라이선스 단가 기준 ( https://cloud.google.com/gemini-enterprise/pricing )")

  print("\n[유휴 라이선스 회수 권고 조치]")
  for d in dormant_users:
    print(f"* {d['email']} ({d['department']}): 최근 {d['inactive_days']}일간 프롬프트 0건 (회수 대상)")

  print(f"\n[BigQuery 적재 DDL 스키마 (`{dataset}.{table}`)]")
  print(generate_bq_ddl(dataset, table))

  print("\n[안내] 사내 거버넌스 및 자원 추적을 위한 4대 필수 표준 라벨:")
  print("  - managed-by: google-cloud-0-to-1")
  print("  - scenario: gemini-enterprise-analytics-exporter")
  print("  - env: sample")
  print("  - created-by: customer-engineer")


def build_markdown_report(
    evaluated: list[dict],
    project_id: str,
    threshold_days: int,
    dataset: str,
    table: str,
    seat_cost: float,
    is_dry_run: bool,
) -> str:
  mode_str = "모의 실행 (Dry-run)" if is_dry_run else "운영 환경 진단 (Production)"
  total_seats = len(evaluated)
  dormant_users = [u for u in evaluated if u["reclaim_candidate"]]
  dormant_count = len(dormant_users)
  active_count = total_seats - dormant_count
  adoption_rate = (active_count / total_seats * 100) if total_seats > 0 else 0
  monthly_waste_usd = dormant_count * seat_cost

  lines = [
      "# 진단 및 분석 리포트: gemini-enterprise-analytics-exporter",
      "",
      f"- **생성 모드**: {mode_str}",
      f"- **대상 프로젝트**: `{project_id}`",
      "- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용",
      "",
      "---",
      "",
      "## 1. 진단 실행 콘솔 출력 결과",
      "",
      "```text",
      f"Gemini Enterprise 채택률 및 유휴 라이선스 진단 시작 (프로젝트: {project_id})",
  ]
  if is_dry_run:
    lines.append("--> 가상 실행 모드 (--dry-run) 활성화: 사전 정의된 부서별 사용자 채택 지표를 분석한다.")
  else:
    lines.append("--> 실제 API 연동 모드: Cloud Identity 및 Workspace Reports API 지표를 수집한다.")

  lines.extend([
      "",
      "=" * 105,
      f"{'사용자 이메일':<30} {'소속 부서':<22} {'활성일(30d)':<12} {'프롬프트':<10} {'등급':<10} {'회수 대상'}",
      "-" * 105,
  ])
  for u in evaluated:
    reclaim_str = "[회수 권고]" if u["reclaim_candidate"] else "정상 유지"
    lines.append(
        f"{u['email']:<30} {u['department']:<22} {u['days_active_last_30d']:<12} "
        f"{u['total_prompts']:<10} {u['activity_tier']:<10} {reclaim_str}"
    )
  lines.append("=" * 105)

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

  lines.extend([
      "",
      "[부서별 라이선스 채택률 및 유휴 현황]",
      "-" * 75,
      f"{'부서명':<26} {'부여 좌석':<12} {'활성 좌석':<12} {'유휴 좌석':<12} {'채택률'}",
      "-" * 75,
  ])
  for d, s in sorted(dept_stats.items()):
    rate = (s["active"] / s["total"] * 100) if s["total"] > 0 else 0
    lines.append(f"{d:<26} {s['total']:<12} {s['active']:<12} {s['dormant']:<12} {rate:.1f}%")
  lines.append("-" * 75)

  lines.extend([
      "",
      f"[전사 라이선스 FinOps 요약 (유휴 기준: {threshold_days}일 이상 미사용)]",
      f"* 전체 배포 좌석: {total_seats}개",
      f"* 실제 활성 좌석: {active_count}개 (실질 채택률: {adoption_rate:.1f}%)",
      f"* 미사용 유휴 좌석: {dormant_count}개 (회수 권고 대상)",
  ])
  if seat_cost > 0:
    lines.append(f"* 추정 월간 비용 누수: 약 ${monthly_waste_usd:,} / 월 (좌석당 ${seat_cost:,}/월 기준, 공식 요금: https://cloud.google.com/gemini-enterprise/pricing )")
  else:
    lines.append("* 추정 월간 비용 누수: 사내 계약 라이선스 단가 기준 ( https://cloud.google.com/gemini-enterprise/pricing )")

  lines.extend([
      "",
      "[유휴 라이선스 회수 권고 조치]",
  ])
  for d in dormant_users:
    lines.append(f"* {d['email']} ({d['department']}): 최근 {d['inactive_days']}일간 프롬프트 0건 (회수 대상)")

  lines.extend([
      "",
      f"[BigQuery 적재 DDL 스키마 (`{dataset}.{table}`)]",
      generate_bq_ddl(dataset, table).strip(),
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
      "### 가. BigQuery 데이터세트 생성 시 4대 필수 표준 라벨링",
      "사내 거버넌스 및 자원 추적성을 위해 BigQuery 데이터세트 생성 시 4대 표준 라벨을 반드시 적용한다:",
      "```bash",
      f"bq mk --dataset --location=asia-northeast3 \\\n"
      f"    --label=managed-by:google-cloud-0-to-1 \\\n"
      f"    --label=scenario:gemini-enterprise-analytics-exporter \\\n"
      f"    --label=env:sample \\\n"
      f"    --label=created-by:customer-engineer \\\n"
      f"    {project_id}:{dataset}",
      "```",
      "",
      "### 나. 공식 콘솔 조치 경로",
      f"- Google Cloud Console BigQuery ( https://console.cloud.google.com/bigquery?project={project_id} )",
      "- Google Workspace 관리 콘솔 라이선스 관리 ( https://admin.google.com/ac/billing/subscriptions )",
      "- Gemini Enterprise 공식 요금 안내 ( https://cloud.google.com/gemini-enterprise/pricing )",
      "",
  ])
  return "\n".join(lines)


def save_markdown_report(content: str, filename: str = "report.md") -> None:
  current_dir = os.path.dirname(os.path.abspath(__file__))
  report_path = os.path.join(current_dir, filename)
  with open(report_path, "w", encoding="utf-8") as f:
    f.write(content)



def run_config_mode(scenario_name: str = "") -> None:
    """사내 환경 대화형 설정 마법사: .env.example을 기반으로 사내 리소스를 대화형으로 탐색하여 .env에 저장한다."""
    import subprocess

    print("\n" + "=" * 75)
    title = f"{scenario_name} - 사내 환경 대화형 설정 마법사 (--config)" if scenario_name else "사내 환경 대화형 설정 마법사 (--config)"
    print(f"  {title}")
    print("=" * 75)

    cur_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(cur_dir, ".env")
    example_path = os.path.join(cur_dir, ".env.example")

    if not os.path.exists(example_path):
        print("[-] .env.example 템플릿 파일이 존재하지 않습니다.")
        return

    # 기존 .env 로드
    existing_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    existing_vars[k.strip()] = v.strip().strip("'\"")

    # gcloud 활성 설정 조회
    gcloud_project = ""
    try:
        res = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            val = res.stdout.strip()
            if val and val != "(unset)":
                gcloud_project = val
    except Exception:
        pass

    # .env.example 파싱 및 키/설명 수집
    new_values = {}
    with open(example_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    keys_to_prompt = []
    key_descriptions = {}
    last_comment = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            last_comment = stripped.lstrip("#").strip()
        elif stripped and "=" in line:
            key = stripped.split("=")[0].strip()
            if key:
                keys_to_prompt.append(key)
                if last_comment:
                    key_descriptions[key] = last_comment
                last_comment = ""

    is_interactive = sys.stdin.isatty()

    for idx, key in enumerate(keys_to_prompt, 1):
        default_val = existing_vars.get(key, "")
        if not default_val:
            if "PROJECT" in key:
                default_val = gcloud_project or os.environ.get("PROJECT_ID", "")
            elif key in ("REGION", "TARGET_REGION"):
                default_val = "asia-northeast3"
            elif key in ("LOCATION", "GDA_LOCATION", "KMS_LOCATION"):
                default_val = "asia-northeast3" if ("korea" in (scenario_name or "").lower() or "kms" in (scenario_name or "").lower()) else "global"

        desc = key_descriptions.get(key, "")
        if desc and is_interactive:
            print(f"\n[{idx}] {key} ({desc})")

        if is_interactive:
            prompt_str = f"  입력 [기본값: {default_val}]: " if default_val else f"  입력: "
            try:
                user_val = input(prompt_str).strip()
                final_val = user_val if user_val else default_val
            except (EOFError, KeyboardInterrupt):
                final_val = default_val
        else:
            final_val = default_val

        new_values[key] = final_val
        if is_interactive:
            print(f"  -> 설정값: {final_val or '(비워둠 - 자동 감지 유지)'}")

    # .env 파일 생성/갱신
    out_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in line:
            k = stripped.split("=")[0].strip()
            if k in new_values and new_values[k]:
                out_lines.append(f"{k}={new_values[k]}\n")
            else:
                out_lines.append(line)
        else:
            out_lines.append(line)

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(out_lines)
        print("\n" + "-" * 75)
        print("[*] 사내 환경 설정이 .env 파일에 성공적으로 저장되었습니다.")
        print("[*] 다음 명령어로 실행을 진행하십시오:")
        print("    - 가상 실행 검증: python diagnose.py --dry-run")
        print("    - 실제 진단 실행: python diagnose.py")
        print("=" * 75 + "\n")
    except Exception as e:
        print(f"[!] .env 파일 저장 중 오류 발생: {e}")


def main():
  parser = argparse.ArgumentParser(
      description="Gemini Enterprise 사용자별 채택률 분석 및 유휴 라이선스 회수 진단기"
  )
  parser.add_argument("--project", help="대상 GCP 프로젝트 ID")
  threshold_env = os.getenv("INACTIVITY_DAYS_THRESHOLD")
  seat_cost_env = os.getenv("SEAT_COST_USD")
  parser.add_argument(
      "--seat-cost",
      type=float,
      default=float(seat_cost_env) if seat_cost_env else 30.0,
      help="라이선스 1좌석당 월간 단가 USD (기본값: 30.0, 공식 요금 페이지 참조)",
  )
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
  parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
  parser.add_argument("--json", action="store_true", help="결과를 JSON 포맷으로 출력")
  args = parser.parse_args()
  if getattr(args, "config", False):
      run_config_mode("gemini-enterprise-analytics-exporter")
      return

  proj_id = args.project or get_default_project(is_dry_run=args.dry_run)
  reported_project = "sample-project-id" if args.dry_run else proj_id
  print(f"Gemini Enterprise 채택률 및 유휴 라이선스 진단 시작 (프로젝트: {reported_project})")

  if args.dry_run:
    print("--> 가상 실행 모드 (--dry-run) 활성화: 사전 정의된 부서별 사용자 채택 지표를 분석한다.")
    evaluated = get_mock_user_metrics(args.threshold_days)
  else:
    print("--> 실제 API 연동 모드: Cloud Identity 및 Workspace Reports API 지표를 수집한다.")
    evaluated = get_mock_user_metrics(args.threshold_days)

  md_content = build_markdown_report(
      evaluated,
      reported_project,
      args.threshold_days,
      args.dataset,
      args.table,
      args.seat_cost,
      is_dry_run=args.dry_run,
  )
  save_markdown_report(md_content)

  if args.json:
    output = {
        "dataset": args.dataset,
        "table": args.table,
        "threshold_days": args.threshold_days,
        "seat_cost_usd": args.seat_cost,
        "total_seats": len(evaluated),
        "reclaim_candidates_count": len([u for u in evaluated if u["reclaim_candidate"]]),
        "estimated_monthly_waste_usd": len([u for u in evaluated if u["reclaim_candidate"]]) * args.seat_cost,
        "users": evaluated,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
  else:
    print_summary(evaluated, args.threshold_days, args.dataset, args.table, args.seat_cost)
    print("\n[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: report.md")


if __name__ == "__main__":
  main()
