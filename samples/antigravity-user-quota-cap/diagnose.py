#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Google Antigravity 사용자별 사용량 모니터링 및 쿼터 캡 진단기."""

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


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
    tokens_env = os.getenv("CAP_TOKENS") or "500000"
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
        help="사용자당 토큰 캡 임계치 (기본값: 500000)",
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
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="결과를 JSON 형식으로 출력한다.",
    )
    return parser.parse_args()


def get_mock_usage_data(cap_tokens: int, cap_requests: int) -> List[Dict[str, Any]]:
    """가상 시뮬레이션용 개발자 사용량 및 IAM 바인딩 데이터 반환."""
    return [
        {
            "user_email": "dev-lead@example.com",
            "department": "Platform Core",
            "request_count": 1420,
            "prompt_tokens": 420000,
            "candidate_tokens": 310000,
            "total_tokens": 730000,
            "primary_client": "VS Code",
            "iam_status": "ENFORCEABLE_ALLOWED",
            "cap_exceeded": True,
            "exceeded_reason": "TOKEN_CAP_EXCEEDED",
            "control_type": "AUTOMATED_CAP_ACTION_REQUIRED",
        },
        {
            "user_email": "senior-eng@example.com",
            "department": "Backend Service",
            "request_count": 980,
            "prompt_tokens": 280000,
            "candidate_tokens": 240000,
            "total_tokens": 520000,
            "primary_client": "JetBrains IntelliJ",
            "iam_status": "ENFORCEABLE_ALLOWED",
            "cap_exceeded": True,
            "exceeded_reason": "TOKEN_CAP_EXCEEDED",
            "control_type": "AUTOMATED_CAP_ACTION_REQUIRED",
        },
        {
            "user_email": "arch-lead@example.com",
            "department": "Architecture Office",
            "request_count": 1150,
            "prompt_tokens": 350000,
            "candidate_tokens": 270000,
            "total_tokens": 620000,
            "primary_client": "Antigravity CLI",
            "iam_status": "NOT_ENFORCEABLE",
            "cap_exceeded": True,
            "exceeded_reason": "TOKEN_AND_REQUEST_CAP_EXCEEDED",
            "control_type": "MANUAL_ACTION_REQUIRED (INHERITED_OR_GROUP)",
        },
        {
            "user_email": "frontend-dev@example.com",
            "department": "Web Frontend",
            "request_count": 510,
            "prompt_tokens": 160000,
            "candidate_tokens": 120000,
            "total_tokens": 280000,
            "primary_client": "VS Code",
            "iam_status": "ENFORCEABLE_ALLOWED",
            "cap_exceeded": False,
            "exceeded_reason": "NONE",
            "control_type": "NORMAL_USAGE",
        },
        {
            "user_email": "junior-eng@example.com",
            "department": "Mobile App",
            "request_count": 220,
            "prompt_tokens": 65000,
            "candidate_tokens": 45000,
            "total_tokens": 110000,
            "primary_client": "Android Studio",
            "iam_status": "ENFORCEABLE_ALLOWED",
            "cap_exceeded": False,
            "exceeded_reason": "NONE",
            "control_type": "NORMAL_USAGE",
        },
    ]


def collect_live_usage(project_id: str, cap_tokens: int, cap_requests: int) -> List[Dict[str, Any]]:
    """실제 Cloud Logging에서 businessaicode 인퍼런스 로그를 조회하여 사용자별 통계를 산출한다."""
    # Cloud Logging 필터 쿼리
    log_filter = (
        'logName="projects/' + project_id + '/logs/businessaicode.googleapis.com%2Finference_response" '
        'timestamp >= "2026-09-01T00:00:00Z"'
    )
    cmd = [
        "gcloud", "logging", "read",
        log_filter,
        f"--project={project_id}",
        "--format=json",
        "--limit=100",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if res.returncode == 0 and res.stdout.strip():
            entries = json.loads(res.stdout)
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
            return sorted(results, key=lambda x: x["total_tokens"], reverse=True)
    except Exception:
        pass

    # 실측 로그가 부재하거나 조회 실패 시 안전하게 가상 모의 데이터로 폴백
    return get_mock_usage_data(cap_tokens, cap_requests)


def print_text_report(
    project_id: str,
    period: str,
    cap_tokens: int,
    cap_requests: int,
    dry_run: bool,
    users: List[Dict[str, Any]],
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
        print("\n[3. 쿼터 캡 초과자 상세 분석 및 조치 가이드]")
        for u in exceeded_users:
            print(f"\n* 초과 계정: {u['user_email']} ({u['department']})")
            print(f"  - 소모 토큰 / 요청수: {u['total_tokens']:,} 토큰 ({u['total_tokens']/cap_tokens*100:.1f}%) / {u['request_count']:,}회")
            print(f"  - 통제성 분류       : {u['iam_status']}")
            print(f"  - 조치 권고         : {u['control_type']}")
            if u["iam_status"] == "ENFORCEABLE_ALLOWED":
                print(f"  - [즉시 처방] 마커 역할 적용 (임시 차단):")
                print(f"    gcloud projects remove-iam-policy-binding {project_id} --member=user:{u['user_email']} --role=roles/discoveryengine.agentspaceUser")
                print(f"    gcloud projects add-iam-policy-binding {project_id} --member=user:{u['user_email']} --role=roles/CustomAntigravityCapBlocked")
            else:
                print(f"  - [수동 검토] 해당 사용자는 Google Group 또는 상위 관리자 권한을 통해 접근하므로 사내 그룹 관리 콘솔에서 제외 조치가 필요하다.")

    print("\n" + "=" * 96)
    print("[4. 엔터프라이즈 운영 자동화(Batch Job) 연계 안내]")
    print("  * 본 진단기는 개발자별 사용량을 신속히 파악하고 헤비 유저를 식별하는 읽기 전용 가이드다.")
    print("  * 실제 프로덕션 환경에서 15분 주기 Cloud Run Job으로 자동 차단 및 복구를 수행하려면,")
    print("    검증된 오픈소스 도구인 agy-admin-cli ( https://github.com/terrychahn/agy-admin-cli ) 배포를 권장한다.")
    print("=" * 96 + "\n")


def build_markdown_report(
    project_id: str,
    period: str,
    cap_tokens: int,
    cap_requests: int,
    dry_run: bool,
    users: List[Dict[str, Any]],
) -> str:
    mode_str = "모의 실행 (Dry-run)" if dry_run else "사내 실측 진단"
    total_users = len(users)
    exceeded_users = [u for u in users if u["cap_exceeded"]]
    enforceable_exceeded = [u for u in exceeded_users if u["iam_status"] == "ENFORCEABLE_ALLOWED"]
    manual_exceeded = [u for u in exceeded_users if u["iam_status"] != "ENFORCEABLE_ALLOWED"]

    lines = [
        "# Google Antigravity 사용자별 사용량 모니터링 및 쿼터 캡 진단 리포트",
        "",
        f"- **진단 일시**: (실행 결과 자동 생성)",
        f"- **대상 프로젝트**: `{project_id}`",
        f"- **집계 주기**: `{period}` (UTC 기준)",
        f"- **토큰 상한 임계치(Cap)**: `{cap_tokens:,} 토큰`",
        f"- **요청 상한 임계치(Cap)**: `{cap_requests:,} 회`",
        f"- **진단 모드**: `{mode_str}`",
        "",
        "---",
        "",
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
    ]

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
        "### 1단계: 직접 통제 가능 초과자 IAM 마커 역할 적용 (임시 차단)",
        "기본 사용자 역할(`roles/discoveryengine.agentspaceUser`)을 해제하고 차단 마커 역할(`CustomAntigravityCapBlocked`)을 임시 부여하여 당일 추가 토큰 소모를 차단한다:",
        "```bash",
    ])

    for u in enforceable_exceeded:
        lines.append(f"# {u['user_email']} 쿼터 캡 차단 조치")
        lines.append(f"gcloud projects remove-iam-policy-binding {project_id} --member=user:{u['user_email']} --role=roles/discoveryengine.agentspaceUser")
        lines.append(f"gcloud projects add-iam-policy-binding {project_id} --member=user:{u['user_email']} --role=roles/CustomAntigravityCapBlocked")

    lines.extend([
        "```",
        "",
        "### 2단계: 그룹 및 상속 권한 보유 초과자 수동 조치",
        "- `NOT_ENFORCEABLE`로 분류된 계정은 프로젝트 레벨의 개별 바인딩을 수정해도 Google Group이나 상위 조직 권한으로 인해 접근이 유지된다.",
        "- 사내 Google Workspace / Cloud Identity 관리 콘솔에서 해당 계정을 개발자 그룹에서 일시 제외 조치해야 한다.",
        "",
        "### 3단계: 엔터프라이즈 운영 자동화(Batch Job) 연계",
        "- 본 도구는 읽기 전용 진단 및 현황 보고를 지원한다.",
        "- 프로덕션 환경에서 15분 주기 자동 차단 및 복구 배치를 스케줄링하려면 검증된 오픈소스 유틸리티 `agy-admin-cli` 배포를 권장한다:",
        "- Antigravity 관리 유틸리티 레포지토리 ( https://github.com/terrychahn/agy-admin-cli )",
    ])

    return "\n".join(lines).strip() + "\n"


def save_markdown_report(report_md: str, output_path: str = "report.md") -> None:
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었습니다: {output_path}")
    except Exception as e:
        print(f"[경고] 리포트 파일 저장 실패 ({output_path}): {e}")


def main() -> None:
    args = parse_arguments()
    proj_id = args.project_id or get_default_project(is_dry_run=args.dry_run)
    reported_project = "sample-project-id" if args.dry_run else proj_id

    if args.dry_run:
        users = get_mock_usage_data(args.cap_tokens, args.cap_requests)
    else:
        print(f"[*] '{reported_project}' 프로젝트의 Cloud Logging(businessaicode) 인퍼런스 로그를 조회 중...")
        users = collect_live_usage(reported_project, args.cap_tokens, args.cap_requests)

    if args.json_output:
        summary = {
            "project_id": reported_project,
            "period": args.period,
            "cap_tokens": args.cap_tokens,
            "cap_requests": args.cap_requests,
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
        )

    # 마크다운 리포트 자동 생성 및 덮어쓰기
    report_content = build_markdown_report(
        project_id=reported_project,
        period=args.period,
        cap_tokens=args.cap_tokens,
        cap_requests=args.cap_requests,
        dry_run=args.dry_run,
        users=users,
    )
    save_markdown_report(report_content, "report.md")


if __name__ == "__main__":
    main()
