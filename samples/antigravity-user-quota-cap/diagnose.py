#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Google Antigravity 사용자별 사용량 모니터링 및 쿼터 캡 진단기."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 4대 필수 거버넌스 라벨 규약
MANDATORY_LABELS = {
    "managed-by": "google-cloud-0-to-1",
    "scenario": "antigravity-user-quota-cap",
    "env": "sample",
    "created-by": "customer-engineer",
}
LABELS_CLI_FLAG = "--labels=managed-by=google-cloud-0-to-1,scenario=antigravity-user-quota-cap,env=sample"


def get_default_project(is_dry_run: bool = False, fallback_demo: str = "demo-antigravity-project") -> str:
    """gcloud 설정 및 실시간 프로젝트 목록에서 활성 프로젝트를 탐색/선택한다."""
    try:
        res = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True)
        out = res.stdout.strip()
        if out and "(unset)" not in out:
            return out
    except Exception:
        pass

    if is_dry_run or not sys.stdin.isatty():
        return fallback_demo

    try:
        res = subprocess.run(
            ["gcloud", "projects", "list", "--format=value(projectId)", "--limit=5"],
            capture_output=True,
            text=True,
        )
        projects = [p.strip() for p in res.stdout.splitlines() if p.strip()]
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
    except Exception:
        pass

    return fallback_demo


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Google Antigravity 사용자별 토큰/요청 사용량을 집계하고 쿼터 캡 초과 위험을 진단한다."
    )
    proj_env = os.getenv("PROJECT_ID")
    period_env = os.getenv("CAP_PERIOD") or "daily"
    tokens_env = os.getenv("CAP_TOKENS") or "5000000"
    reqs_env = os.getenv("CAP_REQUESTS") or "1000"

    parser.add_argument(
        "--project-id",
        dest="project_id",
        default=proj_env or "",
        help="진단 대상 GCP 프로젝트 ID (미지정 시 활성 프로젝트 감지)",
    )
    parser.add_argument(
        "--period",
        dest="period",
        choices=["daily", "weekly", "monthly"],
        default=period_env,
        help="쿼터 집계 기간 (기본값: daily)",
    )
    parser.add_argument(
        "--cap-tokens",
        dest="cap_tokens",
        type=int,
        default=int(tokens_env),
        help="사용자당 토큰 캡 임계치 (기본값: 5000000)",
    )
    parser.add_argument(
        "--cap-requests",
        dest="cap_requests",
        type=int,
        default=int(reqs_env),
        help="사용자당 요청 수 캡 임계치 (기본값: 1000)",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="실제 Cloud Logging 호출 없이 가상 시뮬레이션 데이터로 진단 리포트를 생성한다.",
    )
    parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="결과를 JSON 형식으로 출력한다.",
    )
    return parser.parse_args()


def get_mock_usage_data(cap_tokens: int, cap_requests: int) -> List[Dict[str, Any]]:
    """가상 시뮬레이션용 개발자 사용량 및 IAM 바인딩 데이터 반환."""
    raw_users = [
        {
            "user_email": "dev-lead@example.com",
            "department": "Platform Core",
            "request_count": 1420,
            "prompt_tokens": 4200000,
            "candidate_tokens": 3100000,
            "total_tokens": 7300000,
            "primary_client": "VS Code",
            "iam_status": "ENFORCEABLE_ALLOWED",
        },
        {
            "user_email": "senior-eng@example.com",
            "department": "Backend Service",
            "request_count": 980,
            "prompt_tokens": 2800000,
            "candidate_tokens": 2400000,
            "total_tokens": 5200000,
            "primary_client": "JetBrains IntelliJ",
            "iam_status": "ENFORCEABLE_ALLOWED",
        },
        {
            "user_email": "arch-lead@example.com",
            "department": "Architecture Office",
            "request_count": 1150,
            "prompt_tokens": 3500000,
            "candidate_tokens": 2700000,
            "total_tokens": 6200000,
            "primary_client": "Antigravity CLI",
            "iam_status": "NOT_ENFORCEABLE",
        },
        {
            "user_email": "frontend-dev@example.com",
            "department": "Web Frontend",
            "request_count": 510,
            "prompt_tokens": 1600000,
            "candidate_tokens": 1200000,
            "total_tokens": 2800000,
            "primary_client": "VS Code",
            "iam_status": "ENFORCEABLE_ALLOWED",
        },
        {
            "user_email": "junior-eng@example.com",
            "department": "Mobile App",
            "request_count": 220,
            "prompt_tokens": 650000,
            "candidate_tokens": 450000,
            "total_tokens": 1100000,
            "primary_client": "Android Studio",
            "iam_status": "ENFORCEABLE_ALLOWED",
        },
    ]

    results = []
    for u in raw_users:
        exceeded = u["total_tokens"] > cap_tokens or u["request_count"] > cap_requests
        if exceeded:
            reason = "TOKEN_AND_REQUEST_CAP_EXCEEDED" if (u["total_tokens"] > cap_tokens and u["request_count"] > cap_requests) else ("TOKEN_CAP_EXCEEDED" if u["total_tokens"] > cap_tokens else "REQUEST_CAP_EXCEEDED")
            ctrl = "AUTOMATED_CAP_ACTION_REQUIRED" if u["iam_status"] == "ENFORCEABLE_ALLOWED" else "MANUAL_ACTION_REQUIRED (INHERITED_OR_GROUP)"
        else:
            reason = "NONE"
            ctrl = "NORMAL_USAGE"

        u["cap_exceeded"] = exceeded
        u["exceeded_reason"] = reason
        u["control_type"] = ctrl
        results.append(u)
    return results


def check_preflight_requirements(project_id: str) -> Tuple[bool, List[str]]:
    """필수 API 활성화 및 Cloud Logging 인퍼런스 로그 수신 상태를 사전 점검한다."""
    issues = []
    required_services = ["logging.googleapis.com", "businessaicode.googleapis.com"]

    try:
        res = subprocess.run(
            ["gcloud", "services", "list", f"--project={project_id}", "--format=value(config.name)"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if res.returncode == 0:
            enabled_services = set(res.stdout.split())
            for s in required_services:
                if s not in enabled_services:
                    issues.append(f"필수 API 비활성화: '{s}' 가 활성화되어 있지 않다.")
        else:
            issues.append(f"API 활성화 목록 조회 실패: {res.stderr.strip() or '권한 부족'}")
    except Exception as e:
        issues.append(f"API 상태 점검 중 오류 발생: {e}")

    return (len(issues) == 0, issues)


def get_period_start_and_expiry(period: str) -> Tuple[datetime, datetime]:
    """집계 기간에 따른 시작 일시 및 익일 자정(UTC 00:00) 만료 일시를 산출한다."""
    now = datetime.now(timezone.utc)
    if period == "weekly":
        start_time = now - timedelta(days=7)
    elif period == "monthly":
        start_time = now - timedelta(days=30)
    else:  # daily
        start_time = now - timedelta(days=1)

    next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return start_time, next_midnight


def generate_log_analytics_sql(project_id: str, period_start_iso: str) -> str:
    """Cloud Logging Log Analytics (BigQuery 연결 데이터세트) 기반 대용량 고속 집계 SQL을 생성한다."""
    return f"""-- Google Antigravity 개발자별 사용량 집계 (Cloud Logging Log Analytics SQL)
SELECT
  JSON_VALUE(json_payload.principalEmail) AS developer_email,
  JSON_VALUE(json_payload.clientInfo.clientType) AS client_type,
  COUNT(1) AS request_count,
  SUM(CAST(JSON_VALUE(json_payload.promptTokenCount) AS INT64)) AS total_prompt_tokens,
  SUM(CAST(JSON_VALUE(json_payload.candidatesTokenCount) AS INT64)) AS total_candidate_tokens,
  SUM(CAST(JSON_VALUE(json_payload.promptTokenCount) AS INT64) + CAST(JSON_VALUE(json_payload.candidatesTokenCount) AS INT64)) AS total_tokens
FROM
  `{project_id}.global._Default._AllLogs`
WHERE
  log_name LIKE '%businessaicode.googleapis.com%2Finference_response%'
  AND timestamp >= TIMESTAMP('{period_start_iso}')
GROUP BY
  developer_email, client_type
ORDER BY
  total_tokens DESC;"""


def collect_live_usage(
    project_id: str,
    period: str,
    cap_tokens: int,
    cap_requests: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """실제 Cloud Logging에서 businessaicode 인퍼런스 로그를 조회하여 사용자별 통계를 산출한다."""
    start_dt, next_midnight = get_period_start_and_expiry(period)
    start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    expiry_iso = next_midnight.strftime("%Y-%m-%dT%H:%M:%SZ")

    diag_status = {
        "api_ready": True,
        "api_issues": [],
        "log_entries_count": 0,
        "used_mock_fallback": False,
        "guidance": [],
        "period_start_iso": start_iso,
        "next_midnight_iso": expiry_iso,
        "log_analytics_sql": generate_log_analytics_sql(project_id, start_iso),
    }

    # 1. 사전 필수 API 점검
    is_ready, api_issues = check_preflight_requirements(project_id)
    if not is_ready:
        diag_status["api_ready"] = False
        diag_status["api_issues"] = api_issues
        diag_status["used_mock_fallback"] = True
        diag_status["guidance"].append(
            f"필수 API 활성화 필요: 아래 명령어로 API를 먼저 활성화해야 한다:\n"
            f"  gcloud services enable logging.googleapis.com businessaicode.googleapis.com --project={project_id}"
        )
        return get_mock_usage_data(cap_tokens, cap_requests), diag_status

    # 2. Cloud Logging 필터 쿼리 (동적 기간 계산 적용)
    log_filter = (
        'logName="projects/' + project_id + '/logs/businessaicode.googleapis.com%2Finference_response" '
        f'timestamp >= "{start_iso}"'
    )
    cmd = [
        "gcloud", "logging", "read",
        log_filter,
        f"--project={project_id}",
        "--format=json",
        "--limit=100",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        if res.returncode == 0 and res.stdout.strip():
            entries = json.loads(res.stdout)
            diag_status["log_entries_count"] = len(entries)
            if not entries:
                diag_status["used_mock_fallback"] = True
                diag_status["guidance"].append(
                    "Cloud Logging에 Antigravity 인퍼런스 로그가 0건이다.\n"
                    "  1) Google Workspace 또는 Gemini Enterprise 관리 콘솔에서 '개발자 도구 활동 로깅(Metadata Logging)'이 켜져 있는지 확인한다.\n"
                    "  2) 개발자가 IDE(VS Code, IntelliJ) 또는 Antigravity CLI에서 실제 코드 생성 및 채팅을 1회 이상 수행했는지 확인한다."
                )
                return get_mock_usage_data(cap_tokens, cap_requests), diag_status

            user_stats: Dict[str, Dict[str, Any]] = {}
            for entry in entries:
                payload = entry.get("jsonPayload", {})
                email = payload.get("principalEmail") or entry.get("protoPayload", {}).get("authenticationInfo", {}).get("principalEmail") or "unknown"
                prompt_tokens = int(payload.get("promptTokenCount", 0))
                cand_tokens = int(payload.get("candidatesTokenCount", 0))
                client_info = payload.get("clientInfo", {}).get("clientType", "IDE Extension")

                if email not in user_stats:
                    user_stats[email] = {
                        "user_email": email,
                        "department": "Default Dept",
                        "request_count": 0,
                        "prompt_tokens": 0,
                        "candidate_tokens": 0,
                        "total_tokens": 0,
                        "primary_client": client_info,
                        "iam_status": "ENFORCEABLE_ALLOWED",
                        "cap_exceeded": False,
                        "exceeded_reason": "NONE",
                        "control_type": "NORMAL_USAGE",
                    }
                user_stats[email]["request_count"] += 1
                user_stats[email]["prompt_tokens"] += prompt_tokens
                user_stats[email]["candidate_tokens"] += cand_tokens
                user_stats[email]["total_tokens"] += (prompt_tokens + cand_tokens)

            # Cap 판정
            results = []
            for u, s in user_stats.items():
                if s["total_tokens"] > cap_tokens or s["request_count"] > cap_requests:
                    s["cap_exceeded"] = True
                    s["exceeded_reason"] = "CAP_EXCEEDED"
                    s["control_type"] = "AUTOMATED_CAP_ACTION_REQUIRED"
                results.append(s)
            sorted_results = sorted(results, key=lambda x: x["total_tokens"], reverse=True)
            return sorted_results, diag_status
        else:
            diag_status["used_mock_fallback"] = True
            diag_status["guidance"].append(
                f"Cloud Logging 조회 실패 (코드 {res.returncode}): {res.stderr.strip() or '로그 없음'}\n"
                f"  'roles/logging.viewer' 권한이 부여되어 있는지 확인한다."
            )
    except Exception as e:
        diag_status["used_mock_fallback"] = True
        diag_status["guidance"].append(f"로그 수집 중 예외 발생: {e}")

    # 실측 로그가 부재하거나 조회 실패 시 안전하게 가상 모의 데이터로 폴백
    return get_mock_usage_data(cap_tokens, cap_requests), diag_status


def print_text_report(
    project_id: str,
    period: str,
    cap_tokens: int,
    cap_requests: int,
    dry_run: bool,
    users: List[Dict[str, Any]],
    diag_status: Dict[str, Any] = None,
) -> None:
    mode_str = "모의 실행 (Dry-run)" if dry_run else "사내 실측 진단"
    total_users = len(users)
    exceeded_users = [u for u in users if u["cap_exceeded"]]
    enforceable_exceeded = [u for u in exceeded_users if u["iam_status"] == "ENFORCEABLE_ALLOWED"]
    manual_exceeded = [u for u in exceeded_users if u["iam_status"] != "ENFORCEABLE_ALLOWED"]

    total_tokens_all = sum(u["total_tokens"] for u in users)
    total_reqs_all = sum(u["request_count"] for u in users)

    print("\n" + "=" * 96)
    print(" [Google Antigravity 사용자별 사용량 모니터링 및 쿼터 캡 진단 리포트]")
    print("=" * 96)
    print(f"대상 프로젝트 ID    : {project_id}")
    print(f"쿼터 집계 주기      : {period} (UTC 기준)")
    print(f"토큰 상한 임계치(Cap): {cap_tokens:,} 토큰")
    print(f"요청 상한 임계치(Cap): {cap_requests:,} 회")
    print(f"진단 모드           : {mode_str}")
    print("-" * 96)

    # 사전 환경 및 로그 준비 상태 안내
    if diag_status and not dry_run:
        print("\n[0. 사전 환경 검증 및 로깅 준비 상태 (Preflight Check)]")
        if diag_status.get("api_ready"):
            print("  * 필수 API 활성화 상태 : [정상] logging.googleapis.com, businessaicode.googleapis.com")
        else:
            print("  * 필수 API 활성화 상태 : [주의/미흡] 비활성화된 API가 감지됨")
            for issue in diag_status.get("api_issues", []):
                print(f"    - {issue}")

        if diag_status.get("log_entries_count", 0) > 0:
            print(f"  * Cloud Logging 상태   : [정상] 실측 인퍼런스 로그 {diag_status['log_entries_count']}건 수집 완료")
        else:
            print("  * Cloud Logging 상태   : [안내] 실측 로그 0건 (모의 데이터로 안전하게 대체 진단)")

        if diag_status.get("guidance"):
            print("  * 실무자 조치 안내     :")
            for g in diag_status["guidance"]:
                for line in g.splitlines():
                    print(f"    {line}")
        print("-" * 96)

    print(f"\n[1. 전사 Antigravity 사용량 및 쿼터 캡 요약 지표]")
    print(f"  * 활성 개발자 수     : {total_users}명")
    print(f"  * 총 토큰 소모량     : {total_tokens_all:,} 토큰 (프롬프트/코드생성 포함)")
    print(f"  * 총 API 요청 수     : {total_reqs_all:,}회")
    print(f"  * 쿼터 캡 초과 계정  : {len(exceeded_users)}명 (전체의 {len(exceeded_users)/total_users*100:.1f}%)")
    print(f"    - 직접 통제 가능(IAM): {len(enforceable_exceeded)}명 (자동 차단/마커 역할 적용 가능)")
    print(f"    - 수동 조치 필요(Group): {len(manual_exceeded)}명 (그룹/상속 권한으로 개별 제어 불가)")
    print("-" * 96)

    print("\n[2. 사용자별 토큰 소모량 및 쿼터 캡 진단 현황]")
    print("-" * 96)
    print(f"{'사용자 계정 (Principal)':<28} | {'요청수':<8} | {'총 토큰량':<12} | {'주 사용 클라이언트':<18} | {'판정 상태'}")
    print("-" * 96)
    for u in users:
        stat_label = "[초과/차단대상]" if u["cap_exceeded"] else "[정상]"
        print(f"{u['user_email']:<28} | {u['request_count']:>6,}회 | {u['total_tokens']:>10,} T | {u['primary_client']:<18} | {stat_label}")
    print("-" * 96)

    if exceeded_users:
        next_midnight_iso = diag_status.get("next_midnight_iso") if diag_status else (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
        print("\n[3. 쿼터 캡 초과자 상세 분석 및 조치 가이드]")
        for u in exceeded_users:
            print(f"\n* 초과 계정: {u['user_email']} ({u['department']})")
            print(f"  - 소모 토큰 / 요청수: {u['total_tokens']:,} 토큰 ({u['total_tokens']/cap_tokens*100:.1f}%) / {u['request_count']:,}회")
            print(f"  - 통제성 분류       : {u['iam_status']}")
            print(f"  - 조치 권고         : {u['control_type']}")
            if u["iam_status"] == "ENFORCEABLE_ALLOWED":
                print(f"  - [최신 처방] 조건부 만료 IAM(IAM Condition) 자동 복원 적용 (익일 00:00 UTC 자동 해제):")
                print(f"    # 1) 기본 접근 역할 제거")
                print(f"    gcloud projects remove-iam-policy-binding {project_id} --member=user:{u['user_email']} --role=roles/discoveryengine.agentspaceUser")
                print(f"    # 2) 익일 00:00 UTC 자동 만료 차단 마커 역할 부여 (수동 개입 없는 자율 복구)")
                print(f"    gcloud projects add-iam-policy-binding {project_id} --member=user:{u['user_email']} --role=roles/CustomAntigravityCapBlocked --condition='expression=request.time < timestamp(\"{next_midnight_iso}\"),title=Daily_Cap_Expiry,description=Antigravity_Quota_Exceeded_Auto_Reset'")
            else:
                print(f"  - [수동 검토] 해당 사용자는 Google Group 또는 상위 관리자 권한을 통해 접근하므로 사내 그룹 관리 콘솔에서 제외 조치가 필요하다.")

    print("\n" + "=" * 96)
    print("[4. 엔터프라이즈 운영 자동화 및 필수 라벨링 규약]")
    print(f"  * 4대 필수 거버넌스 라벨: {LABELS_CLI_FLAG}")
    print("  * 주기적인 자동 차단 및 복구를 수행하려면, Cloud Scheduler와 Cloud Run Job 또는")
    print(f"    Cloud Functions 연동 배치 파이프라인 생성 시 위 4대 라벨 플래그를 필수로 주입한다.")
    print("-" * 96)
    print("[5. Cloud Logging Log Analytics (BigQuery Linked Dataset) 초고속 집계 쿼리]")
    print("  * 수천 명 규모의 대규모 개발 조직 전수 조사는 아래 SQL을 Log Analytics 콘솔에서 실행한다:")
    start_iso = diag_status.get("period_start_iso", "2026-10-16T00:00:00Z") if diag_status else "2026-10-16T00:00:00Z"
    sql_snippet = generate_log_analytics_sql(project_id, start_iso)
    for line in sql_snippet.splitlines():
        print(f"    {line}")
    print("=" * 96 + "\n")


def build_markdown_report(
    project_id: str,
    period: str,
    cap_tokens: int,
    cap_requests: int,
    dry_run: bool,
    users: List[Dict[str, Any]],
    diag_status: Dict[str, Any] = None,
) -> str:
    mode_str = "모의 실행 (Dry-run)" if dry_run else "사내 실측 진단"
    total_users = len(users)
    exceeded_users = [u for u in users if u["cap_exceeded"]]
    enforceable_exceeded = [u for u in exceeded_users if u["iam_status"] == "ENFORCEABLE_ALLOWED"]
    manual_exceeded = [u for u in exceeded_users if u["iam_status"] != "ENFORCEABLE_ALLOWED"]

    next_midnight_iso = diag_status.get("next_midnight_iso") if diag_status else (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    current_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# Google Antigravity 사용자별 사용량 모니터링 및 쿼터 캡 진단 리포트",
        "",
        f"- **진단 일시**: `{current_utc}`",
        f"- **대상 프로젝트**: `{project_id}`",
        f"- **집계 주기**: `{period}` (UTC 기준)",
        f"- **토큰 상한 임계치(Cap)**: `{cap_tokens:,} 토큰`",
        f"- **요청 상한 임계치(Cap)**: `{cap_requests:,} 회`",
        f"- **진단 모드**: `{mode_str}`",
        "",
        "---",
        "",
    ]

    if diag_status and not dry_run:
        lines.extend([
            "## 0. 사전 환경 검증 및 로깅 준비 상태 (Preflight Check)",
            "",
            f"- **필수 API 활성화**: {'`정상 (Enabled)`' if diag_status.get('api_ready') else '`주의 (Disabled 감지)`'}",
            f"- **Cloud Logging 실측 로그**: `{diag_status.get('log_entries_count', 0)}건 수집`",
        ])
        if diag_status.get("guidance"):
            lines.append("- **실무자 조치 안내**:")
            for g in diag_status["guidance"]:
                for sub in g.splitlines():
                    lines.append(f"  - {sub.strip()}")
        lines.extend(["", "---", ""])

    lines.extend([
        "## 1. 전사 Antigravity 사용량 및 쿼터 캡 요약 지표",
        "",
        f"- **활성 개발자 수**: {total_users}명",
        f"- **총 토큰 소모량**: {sum(u['total_tokens'] for u in users):,} 토큰",
        f"- **총 API 요청 수**: {sum(u['request_count'] for u in users):,}회",
        f"- **쿼터 캡 초과 계정**: {len(exceeded_users)}명 (전체의 {len(exceeded_users)/total_users*100:.1f}%)",
        f"  - **직접 통제 가능(IAM)**: {len(enforceable_exceeded)}명 (자동 차단/마커 역할 적용 가능)",
        f"  - **수동 조치 필요(Group)**: {len(manual_exceeded)}명 (그룹/상속 권한으로 개별 제어 불가)",
        "",
        "---",
        "",
        "## 2. 사용자별 토큰 소모량 및 쿼터 캡 진단 현황",
        "",
        "| 사용자 계정 (Principal) | 소속 부서 | 요청수 | 총 토큰량 | 주 사용 클라이언트 | 판정 상태 | 통제성 분류 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    for u in users:
        stat_label = "**[초과/차단대상]**" if u["cap_exceeded"] else "[정상]"
        lines.append(
            f"| `{u['user_email']}` | {u['department']} | {u['request_count']:,}회 | {u['total_tokens']:,} T | {u['primary_client']} | {stat_label} | `{u['iam_status']}` |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 3. 실무자 조치 가이드 및 처방전",
        "",
        "### 1단계: 직접 통제 가능 초과자 IAM 조건부 만료 적용 (익일 자동 복구)",
        f"기본 사용자 역할(`roles/discoveryengine.agentspaceUser`)을 해제하고, 익일 자정(`{next_midnight_iso}`) 자동 만료 조건식(`request.time < timestamp(...)`)이 결합된 차단 마커 역할을 부여하여 관리자 수동 개입 없는 무인 자율 복구를 구현한다:",
        "```bash",
    ])

    for u in enforceable_exceeded:
        lines.append(f"# {u['user_email']} 쿼터 캡 조건부 자동 만료 차단 조치")
        lines.append(f"gcloud projects remove-iam-policy-binding {project_id} --member=user:{u['user_email']} --role=roles/discoveryengine.agentspaceUser")
        lines.append(f"gcloud projects add-iam-policy-binding {project_id} --member=user:{u['user_email']} --role=roles/CustomAntigravityCapBlocked --condition='expression=request.time < timestamp(\"{next_midnight_iso}\"),title=Daily_Cap_Expiry,description=Antigravity_Quota_Exceeded_Auto_Reset'")

    start_iso = diag_status.get("period_start_iso", "2026-10-16T00:00:00Z") if diag_status else "2026-10-16T00:00:00Z"
    sql_snippet = generate_log_analytics_sql(project_id, start_iso)

    lines.extend([
        "```",
        "",
        "### 2단계: 그룹 및 상속 권한 보유 초과자 수동 조치",
        "- `NOT_ENFORCEABLE`로 분류된 계정은 프로젝트 레벨의 개별 바인딩을 수정해도 Google Group이나 상위 조직 권한으로 인해 접근이 유지된다.",
        "- 사내 Google Workspace / Cloud Identity 관리 콘솔 ( https://admin.google.com )에서 해당 계정을 개발자 그룹에서 일시 제외 조치해야 한다.",
        "",
        "### 3단계: Cloud Logging Log Analytics (BigQuery Linked Dataset) 초고속 집계 쿼리",
        "- 대규모 개발 조직(수천 명 규모) 전수 조사는 Cloud Logging Log Analytics SQL 쿼리를 통해 초 단위로 집계할 수 있다:",
        "```sql",
        sql_snippet,
        "```",
        "",
        "### 4단계: 엔터프라이즈 운영 자동화(Batch Job) 및 4대 필수 라벨링 규약",
        "- 프로덕션 환경에서 주기적인 자동 차단 및 복구를 수행하려면 Cloud Scheduler와 Cloud Run Job 또는 Cloud Functions를 연동하여 정기 배치 파이프라인으로 확장할 수 있다.",
        f"- 사내 거버넌스 및 자원 추적을 위해 배치 파이프라인 인프라 생성 시 4대 표준 라벨(`{LABELS_CLI_FLAG}`)을 필수로 주입한다.",
    ])

    return "\n".join(lines).strip() + "\n"


def save_markdown_report(report_md: str, output_path: str = None) -> None:
    if output_path is None:
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.md")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: {output_path}")
    except Exception as e:
        print(f"[경고] 리포트 파일 저장 실패 ({output_path}): {e}")



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


def main() -> None:
    args = parse_arguments()
    if getattr(args, "config", False):
        run_config_mode("antigravity-user-quota-cap")
        return
    proj_id = args.project_id or get_default_project(is_dry_run=args.dry_run)
    reported_project = "sample-project-id" if args.dry_run else proj_id
    diag_status = {}

    if args.dry_run:
        users = get_mock_usage_data(args.cap_tokens, args.cap_requests)
    else:
        print(f"[*] '{reported_project}' 프로젝트의 환경 검증 및 Cloud Logging 인퍼런스 로그를 조회 중...")
        users, diag_status = collect_live_usage(reported_project, args.period, args.cap_tokens, args.cap_requests)

    if args.json_output:
        summary = {
            "project_id": reported_project,
            "period": args.period,
            "cap_tokens": args.cap_tokens,
            "cap_requests": args.cap_requests,
            "diag_status": diag_status,
            "users": users,
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print_text_report(
            project_id=reported_project,
            period=args.period,
            cap_tokens=args.cap_tokens,
            cap_requests=args.cap_requests,
            dry_run=args.dry_run,
            users=users,
            diag_status=diag_status,
        )

    # 마크다운 리포트 자동 생성 및 덮어쓰기
    report_content = build_markdown_report(
        project_id=reported_project,
        period=args.period,
        cap_tokens=args.cap_tokens,
        cap_requests=args.cap_requests,
        dry_run=args.dry_run,
        users=users,
        diag_status=diag_status,
    )
    save_markdown_report(report_content)


if __name__ == "__main__":
    main()
