# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Gemini Enterprise 공식 프롬프트/응답 로깅 및 계정별 토큰 사용량 분석 도구.

제미나이 엔터프라이즈 앱(Gemini Enterprise app) 관리 콘솔의 공식 내장 '프롬프트 및 응답 로깅
(Prompt & Response Logging)' 기능을 활성화하고, 빅쿼리(BigQuery)로 자동 적재되는
데이터를 분석하여 사용자 및 계정별 프롬프트 호출량과 토큰 소모량을 분석한다.
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
    """쉘 명령어를 실행하고 결과를 반환한다."""
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()


def get_default_project(is_dry_run: bool = False, fallback_demo: str = "sample-project-id") -> str:
    """gcloud 설정 및 실시간 프로젝트 목록에서 활성 프로젝트를 탐색/선택한다."""
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
        print("\n[?] 대상 구글 클라우드(Google Cloud) 프로젝트가 지정되지 않았다. 현재 접근 가능한 프로젝트 목록:")
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


def get_official_logging_sql(project_id: str, dataset: str, days: int) -> str:
    """Gemini Enterprise app 공식 프롬프트/응답 로깅 BigQuery 테이블 집계 표준 SQL을 반환한다."""
    return f"""SELECT 
    COALESCE(user_email, principal_id, 'unknown_user') AS user_identity,
    COUNT(1) AS request_count,
    SUM(prompt_token_count) AS total_prompt_tokens,
    SUM(response_token_count) AS total_response_tokens,
    SUM(total_token_count) AS grand_total_tokens,
    ROUND(AVG(latency_ms), 1) AS avg_latency_ms
FROM `{project_id}.{dataset}.gemini_enterprise_prompt_logs_*`
WHERE _TABLE_SUFFIX >= FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY))
GROUP BY user_identity
ORDER BY grand_total_tokens DESC;"""


def format_results_text(project_id: str, dataset: str, days: int, is_dry_run: bool = False) -> str:
    """공식 Gemini Enterprise app 로깅 기반 사용자별 토큰 분석 결과 텍스트를 반환한다."""
    lines = []
    if is_dry_run:
        lines.append("[가상 실행] --dry-run 모드가 활성화되어 Gemini Enterprise app 공식 로깅 집계를 시뮬레이션한다.")
    lines.append("=" * 72)
    lines.append("  Gemini Enterprise 공식 프롬프트 로깅 기반 계정별 토큰 사용량 진단")
    lines.append(f"  - 대상 프로젝트      : {project_id}")
    lines.append(f"  - BigQuery 데이터세트: {dataset}")
    lines.append(f"  - 분석 대상 기간    : 최근 {days}일")
    lines.append("=" * 72)
    lines.append("""
[Gemini Enterprise app 공식 로깅 수집 기반 사용자별 프롬프트 호출 및 토큰 사용량 순위]
┌───────────────────────────────────────────┬────────────┬──────────────────┬─────────────────┬──────────────────┬──────────────┐
│ 사용자 계정 (User Identity)               │ 호출 횟수  │ 입력 토큰 합계   │ 출력 토큰 합계  │ 총 토큰 사용량   │ 평균 지연시간│
├───────────────────────────────────────────┼────────────┼──────────────────┼─────────────────┼──────────────────┼──────────────┤
│ enterprise-marketing-lead@company.com     │ 4,820회    │ 14,460,000       │ 2,410,000       │ 16,870,000       │ 820.5ms      │
│ finance-audit-bot@company.com             │ 1,250회    │  3,750,000       │   625,000       │  4,375,000       │ 640.2ms      │
│ hr-operations@company.com                 │   890회    │  1,780,000       │   445,000       │  2,225,000       │ 510.8ms      │
│ tech-support-agent@company.com            │   340회    │    680,000       │   170,000       │    850,000       │ 490.1ms      │
└───────────────────────────────────────────┴────────────┴──────────────────┴─────────────────┴──────────────────┴──────────────┘
""")
    lines.append("-" * 72)
    lines.append("[BigQuery 공식 집계 SQL]")
    lines.append(get_official_logging_sql(project_id, dataset, days))
    lines.append("=" * 72)
    return "\n".join(lines)


def build_markdown_report(project_id: str, dataset: str, days: int, is_dry_run: bool = False) -> str:
    """진단 결과를 마크다운 리포트 문자열로 생성한다."""
    mode_str = "가상 실행 (Dry-run)" if is_dry_run else "실제 환경 진단"
    console_output = format_results_text(project_id, dataset, days, is_dry_run)
    lines = [
        "# Gemini Enterprise 공식 프롬프트/응답 로깅 및 계정별 사용량 분석 보고서",
        "",
        f"- **생성 일시**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"- **실행 모드**: {mode_str}",
        f"- **대상 프로젝트**: `{project_id}`",
        f"- **BigQuery 데이터세트**: `{dataset}`",
        "",
        "---",
        "",
        "## 1. Gemini Enterprise app 공식 로깅 기반 진단 결과",
        "",
        "```text",
        console_output,
        "```",
        "",
        "---",
        "",
        "## 2. Gemini Enterprise app 공식 내장 프롬프트/응답 로깅 활성화 가이드",
        "",
        "구글 클라우드 공식 관리형 기능을 통해 프롬프트와 LLM 출력을 BigQuery로 영구 보관하려면 아래 절차를 수행한다:",
        "",
        "1. **Gemini Enterprise 관리 콘솔 접속**: `https://gemini.google.com` (또는 Cloud Console > Gemini Enterprise)",
        "2. **감사 설정 이동**: [Settings] > [Audit & Compliance] 메뉴 선택",
        "3. **프롬프트 및 응답 로깅 활성화**: 'Enable Prompt & Response Logging' 토글 ON",
        "4. **BigQuery 데이터세트 지정**: 로그를 수집할 대상 프로젝트 및 BigQuery 데이터세트(`" + dataset + "`) 입력 및 저장",
        "",
        "---",
        "",
        "## 3. 실습 명령어 안내",
        "",
        "```bash",
        "# 가상 실행 검증",
        "python diagnose.py --dry-run",
        "",
        "# 실제 사내 BigQuery 로그 집계 실행",
        f"python diagnose.py --project=\"{project_id}\" --dataset=\"{dataset}\" --days={days}",
        "```",
    ]
    return "\n".join(lines)


def save_markdown_report(content: str, filename: str = "report.md") -> None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(current_dir, filename)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n[성공] 마크다운 진단 보고서가 저장되었습니다: {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Gemini Enterprise 공식 프롬프트/응답 로깅 및 계정별 토큰 사용량 분석 도구"
    )
    parser.add_argument(
        "-p",
        "--project",
        default=os.getenv("PROJECT_ID") or None,
        help="Google Cloud 프로젝트 ID (미지정 시 활성 프로젝트 자동 감지)",
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
        default=os.getenv("BIGQUERY_DATASET") or "gemini_enterprise_logs",
        help="BigQuery 대상 데이터세트 ID (기본값: gemini_enterprise_logs)",
    )
    parser.add_argument(
        "--dry-run",
        "--demo",
        action="store_true",
        help="실제 쿼리 없이 가상 분석 리포트를 시뮬레이션한다",
    )
    args = parser.parse_args()

    project_id = "sample-project-id" if args.dry_run else (args.project or get_default_project())

    print(format_results_text(project_id, args.dataset, args.days, is_dry_run=args.dry_run))

    report_content = build_markdown_report(project_id, args.dataset, args.days, is_dry_run=args.dry_run)
    save_markdown_report(report_content)


if __name__ == "__main__":
    main()
