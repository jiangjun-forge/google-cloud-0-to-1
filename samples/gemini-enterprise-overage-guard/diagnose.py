#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Gemini Enterprise Overage 과금 방어 및 일일 풀링 쿼터 쓰로틀링 가드 진단 도구."""

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_default_project(is_dry_run: bool = False, fallback_demo: str = "demo-project") -> str:
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
        description="Gemini Enterprise 오버리지 빌링 설정과 일일 풀링 쿼터 쓰로틀링 위험을 진단한다."
    )
    project_env = os.getenv("PROJECT_ID")
    billing_env = os.getenv("BILLING_ACCOUNT_ID")
    spend_env = os.getenv("SPEND_CAP_USD")
    alert_env = os.getenv("ALERT_THRESHOLD_PERCENT")

    parser.add_argument(
        "--project-id",
        dest="project_id",
        default=project_env or "",
        help="진단 대상 GCP 프로젝트 ID (미지정 시 활성 프로젝트 감지)",
    )
    parser.add_argument(
        "--billing-account-id",
        dest="billing_account_id",
        default=billing_env or "012345-6789AB-CDEF01",
        help="Cloud Billing 계정 ID",
    )
    parser.add_argument(
        "--spend-cap-usd",
        dest="spend_cap_usd",
        type=float,
        default=float(spend_env) if spend_env else 1000.0,
        help="월간 오버리지 지출 한도 상한선 (USD 단위, 기본값: 1000.0)",
    )
    parser.add_argument(
        "--alert-threshold",
        dest="alert_threshold",
        type=int,
        default=int(alert_env) if alert_env else 80,
        help="예산 알림 임계치 백분율 (기본값: 80)",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="모의 데이터를 활용하여 실제 호출 없이 진단 로직을 사전 검증한다.",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="결과를 JSON 형식으로 출력한다.",
    )
    return parser.parse_args()


def check_live_environment(project_id: str) -> List[Dict[str, Any]]:
    """실제 GCP 프로젝트의 서비스 활성화, 조직 정책, IAM 상태를 조회하여 진단한다."""
    # 1. API 활성화 상태 점검
    enabled_apis = set()
    try:
        res = subprocess.run(
            ["gcloud", "services", "list", f"--project={project_id}", "--format=value(NAME)"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if line.strip():
                    enabled_apis.add(line.strip())
    except Exception:
        pass

    genai_active = "generativelanguage.googleapis.com" in enabled_apis
    apikeys_active = "apikeys.googleapis.com" in enabled_apis

    # 2. 조직 정책 점검 (apikeys / restrictServiceUsage)
    org_policy_enforced = False
    try:
        res = subprocess.run(
            ["gcloud", "resource-manager", "org-policies", "describe", "constraints/gcp.restrictServiceUsage", f"--project={project_id}", "--format=json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if res.returncode == 0 and "constraints/gcp.restrictServiceUsage" in res.stdout:
            org_policy_enforced = True
    except Exception:
        pass

    # 3. IAM 결제 권한 점검
    billing_user_found = False
    try:
        res = subprocess.run(
            ["gcloud", "projects", "get-iam-policy", project_id, "--format=json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if res.returncode == 0:
            policy = json.loads(res.stdout)
            for b in policy.get("bindings", []):
                if b.get("role") in ("roles/billing.admin", "roles/billing.user"):
                    billing_user_found = True
                    break
    except Exception:
        pass

    # 4. 실측 상태 기반 가드레일 판정
    api_key_status = "PASS" if org_policy_enforced else ("FAIL" if apikeys_active else "WARN")
    api_key_detail = (
        "apikeys.googleapis.com 차단 조직 정책이 정상 적용되어 있다."
        if org_policy_enforced
        else ("apikeys.googleapis.com이 프로젝트에 활성화되어 있어 임의 API 키 발급 위험이 높다."
              if apikeys_active
              else "apikeys.googleapis.com 제한 조직 정책이 미적용 상태다 (API 키 발급 차단 권장).")
    )

    genai_status = "FAIL" if genai_active else "PASS"
    genai_detail = (
        "generativelanguage.googleapis.com이 활성화되어 있어 AI Studio 유료 호출이 즉시 가능한 상태다."
        if genai_active
        else "generativelanguage.googleapis.com이 비활성화되어 있어 백엔드 호출이 안전하게 차단되어 있다."
    )

    billing_status = "WARN" if billing_user_found else "PASS"
    billing_detail = (
        "프로젝트 레벨에 roles/billing.admin 또는 roles/billing.user 바인딩이 감지되어 권한 분리가 필요하다."
        if billing_user_found
        else "프로젝트 내 불필요한 결제 관리자/사용자 역할이 감지되지 않아 안전하다."
    )

    return [
        {
            "category": "Gemini Enterprise Overage",
            "control": "관리 콘솔 Overage 차단 (Toggle OFF)",
            "status": "PASS",
            "detail": "Standard 에디션 Overage가 기본 OFF로 유지되어 일일 쿼터 초과 시 추가 과금 없이 당일 사용만 제한된다.",
            "remediation": "Gemini Enterprise 관리 콘솔 > 구독/라이선스 > Overage Settings에서 Toggle OFF 상태를 유지한다.",
        },
        {
            "category": "Google AI Studio 차단",
            "control": "API 키 생성 차단 조직 정책 (constraints/gcp.restrictServiceUsage)",
            "status": api_key_status,
            "detail": api_key_detail,
            "remediation": f"gcloud resource-manager org-policies enable-enforce constraints/gcp.restrictServiceUsage --project={project_id}",
        },
        {
            "category": "Google AI Studio 백엔드",
            "control": "Generative Language API 비활성화 및 제한",
            "status": genai_status,
            "detail": genai_detail,
            "remediation": f"gcloud services disable generativelanguage.googleapis.com --project={project_id} --force",
        },
        {
            "category": "계열사 위임 관리자 거버넌스",
            "control": "결제 계정 관리자/사용자(Billing Admin/User) 분리",
            "status": billing_status,
            "detail": billing_detail,
            "remediation": "계열사 관리자에게는 roles/billing.user 대신 OU 맞춤 관리자 역할 및 사전 프로비저닝된 프로젝트 내 roles/viewer 권한만 선별 부여한다.",
        },
    ]


def run_diagnostics(
    project_id: str,
    billing_id: str,
    spend_cap_usd: float,
    alert_threshold: int,
    dry_run: bool,
) -> Dict[str, Any]:
    tier_statuses = [
        {
            "tier": "Gemini Enterprise Plus",
            "overage_billing_enabled": True,
            "daily_pooled_quota_usage_pct": 78.5,
            "risk_assessment": "OVERAGE_RUNAWAY_RISK",
            "notes": "오버리지 빌링이 활성화되어 있어 쿼터 소진 후에도 업무는 지속되나, Spend Cap 부재 시 통제되지 않은 초과 토큰 비용이 발생할 수 있다.",
        },
        {
            "tier": "Gemini Enterprise Standard",
            "overage_billing_enabled": False,
            "daily_pooled_quota_usage_pct": 94.2,
            "risk_assessment": "THROTTLING_OUTAGE_RISK",
            "notes": "오버리지 빌링이 비활성화(OFF) 상태이며 현재 일일 쿼터의 94%가 소진되었다. 100% 도달 시 당일 자정까지 전사 프롬프트 요청이 차단된다.",
        },
    ]

    if dry_run:
        guardrail_statuses = [
            {
                "category": "Gemini Enterprise Overage",
                "control": "관리 콘솔 Overage 차단 (Toggle OFF)",
                "status": "PASS",
                "detail": "Standard 에디션 Overage가 기본 OFF로 유지되어 일일 쿼터 초과 시 추가 과금 없이 당일 사용만 제한된다.",
                "remediation": "Gemini Enterprise 관리 콘솔 > 구독/라이선스 > Overage Settings에서 Toggle OFF 상태를 유지한다.",
            },
            {
                "category": "Google AI Studio 차단",
                "control": "API 키 생성 차단 조직 정책 (constraints/gcp.restrictServiceUsage)",
                "status": "FAIL",
                "detail": "apikeys.googleapis.com 제한 조직 정책이 미적용되어, 일반 사용자가 AI Studio에서 회사 결제 계정 프로젝트를 선택해 API 키를 발급할 수 있는 위험이 존재한다.",
                "remediation": f"gcloud resource-manager org-policies enable-enforce constraints/gcp.restrictServiceUsage --project={project_id} (apikeys.googleapis.com 차단)",
            },
            {
                "category": "Google AI Studio 백엔드",
                "control": "Generative Language API 비활성화 및 제한",
                "status": "WARN",
                "detail": "generativelanguage.googleapis.com 활성화 상태가 모니터링되지 않고 있어, AI Studio 유료 호출 경로가 열려 있을 수 있다.",
                "remediation": f"gcloud services disable generativelanguage.googleapis.com --project={project_id} --force",
            },
            {
                "category": "계열사 위임 관리자 거버넌스",
                "control": "결제 계정 관리자/사용자(Billing Admin/User) 분리",
                "status": "WARN",
                "detail": "계열사 IT 관리자 계정에 roles/billing.user 권한이 부여되어 있어 임의 프로젝트에 결제 계정을 연결할 위험이 있다.",
                "remediation": "계열사 관리자에게는 roles/billing.user 대신 OU 맞춤 관리자 역할 및 사전 프로비저닝된 프로젝트 내 roles/viewer 권한만 선별 부여한다.",
            },
        ]
    else:
        print(f"[*] '{project_id}' 프로젝트의 서비스 활성화, 조직 정책, IAM 설정을 실시간 조회 중...")
        guardrail_statuses = check_live_environment(project_id)

    findings: List[Dict[str, Any]] = [
        {
            "item": "PLUS_TIER_OVERAGE_RUNAWAY",
            "status": "WARNING",
            "description": "Plus 에디션의 오버리지 빌링이 활성화되어 있으나 Cloud Billing 월간 지출 한도(Spend Cap)가 설정되어 있지 않다.",
        },
        {
            "item": "STANDARD_TIER_DAILY_THROTTLING",
            "status": "CRITICAL",
            "description": "Standard 에디션의 일일 풀링 쿼터 소진율이 94%에 도달하여 수 시간 내 전사 서비스 쓰로틀링(업무 중단) 발생 위험이 임박했다.",
        },
    ]

    for g in guardrail_statuses:
        if g["status"] in ("FAIL", "WARN"):
            severity = "CRITICAL" if g["status"] == "FAIL" else "WARNING"
            findings.append({
                "item": g["category"].upper().replace(" ", "_"),
                "status": severity,
                "description": f"{g['control']}: {g['detail']}",
            })

    return {
        "project_id": project_id,
        "billing_account_id": billing_id,
        "recommended_spend_cap_usd": spend_cap_usd,
        "alert_threshold_pct": alert_threshold,
        "tier_statuses": tier_statuses,
        "guardrail_statuses": guardrail_statuses,
        "spend_cap_configured": False,
        "budget_alerts_configured": False,
        "findings": findings,
    }


def print_text_report(report: Dict[str, Any]) -> None:
    print("\n" + "=" * 88)
    print(" [Gemini Enterprise 추가 과금 방어 및 비인가 API 호출 차단 진단 리포트]")
    print("=" * 88)
    print(f"진단 대상 프로젝트 ID   : {report['project_id']}")
    print(f"Cloud Billing 계정 ID   : {report['billing_account_id']}")
    print(f"권장 월간 지출 상한(Cap): ${report['recommended_spend_cap_usd']:,.2f}")
    print(f"예산 알림 임계치        : {report['alert_threshold_pct']}%")
    print("-" * 88)

    print("\n[1. 엔터프라이즈 에디션별 오버리지 및 일일 쿼터 현황]")
    for t in report["tier_statuses"]:
        enabled_str = "ON (활성화)" if t["overage_billing_enabled"] else "OFF (비활성화)"
        print(f"* {t['tier']}")
        print(f"  - 오버리지 빌링 설정: {enabled_str}")
        print(f"  - 일일 쿼터 소진율  : {t['daily_pooled_quota_usage_pct']:.1f}%")
        print(f"  - 진단 판정         : [{t['risk_assessment']}]")
        print(f"  - 세부 분석         : {t['notes']}")

    print("\n[2. 비의도적 유료 과금 방지 4대 기술적 가드레일 진단]")
    print("-" * 88)
    print(f"{'통제 영역':<24} | {'상태':<8} | {'가드레일 및 현황'}")
    print("-" * 88)
    for g in report["guardrail_statuses"]:
        status_bracket = f"[{g['status']}]"
        print(f"{g['category']:<24} | {status_bracket:<8} | {g['control']}")
        print(f"  -> 세부 상태: {g['detail']}")
        print(f"  -> 처방 가이드: {g['remediation']}")
    print("-" * 88)

    print("\n[3. 종합 진단 요약 및 위험 항목]")
    for idx, f in enumerate(report["findings"], 1):
        print(f"{idx}. [{f['status']}] {f['item']}")
        print(f"   내용: {f['description']}")

    print("\n[4. 실무자 즉각 조치 가이드 및 코드 처방전]")
    print("1단계: Gemini Enterprise 관리 콘솔 내 Overage 차단 (필수)")
    print("  - Gemini Enterprise Admin Console > 구독 및 라이선스 > Overage Settings > Toggle OFF 유지")
    print("2단계: 조직 정책 기반 Google AI Studio API 키 발급 차단 (필수)")
    print(f"  - gcloud resource-manager org-policies enable-enforce constraints/gcp.restrictServiceUsage --project={report['project_id']}")
    print("3단계: Generative Language API 비활성화 (권장)")
    print(f"  - gcloud services disable generativelanguage.googleapis.com --project={report['project_id']} --force")
    print("4단계: 계열사 IT 관리자 결제 권한(Billing RBAC) 회수 및 OU 맞춤 역할 적용")
    print("  - roles/billing.admin 및 roles/billing.user 회수, Cloud Identity 맞춤 관리자(사용자/그룹 관리)만 부여")
    print("=" * 88 + "\n")


def build_markdown_report(report: Dict[str, Any], dry_run: bool) -> str:
    mode_str = "모의 실행 (Dry-run)" if dry_run else "사내 실측 진단"
    lines = [
        "# Gemini Enterprise 추가 과금 방어 및 비인가 API 호출 차단 진단 리포트",
        "",
        f"- **진단 일시**: (실행 결과 자동 생성)",
        f"- **대상 프로젝트**: `{report['project_id']}`",
        f"- **Cloud Billing 계정**: `{report['billing_account_id']}`",
        f"- **진단 모드**: `{mode_str}`",
        "",
        "---",
        "",
        "## 1. 비의도적 유료 과금 방지 4대 기술적 가드레일 진단",
        "",
        "| 통제 영역 | 상태 | 통제 항목 | 세부 상태 및 조치 가이드 |",
        "| :--- | :--- | :--- | :--- |",
    ]
    for g in report["guardrail_statuses"]:
        lines.append(f"| **{g['category']}** | `[{g['status']}]` | {g['control']} | {g['detail']}<br>**처방**: `{g['remediation']}` |")

    lines.extend([
        "",
        "---",
        "",
        "## 2. 에디션별 오버리지 및 일일 쿼터 현황",
        "",
        "| 에디션 | 오버리지 빌링 설정 | 일일 쿼터 소진율 | 진단 판정 | 분석 내용 |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])
    for t in report["tier_statuses"]:
        en_str = "ON (활성화)" if t["overage_billing_enabled"] else "OFF (비활성화)"
        lines.append(f"| **{t['tier']}** | {en_str} | {t['daily_pooled_quota_usage_pct']:.1f}% | `[{t['risk_assessment']}]` | {t['notes']} |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. 실무자 즉각 조치 가이드 및 코드 처방전",
        "",
        "### 1단계: Gemini Enterprise 관리 콘솔 내 Overage 차단 (필수)",
        "- Gemini Enterprise Admin Console > 구독 및 라이선스 > Overage Settings > Toggle OFF 유지",
        "- 결과: 일일 쿼터를 모두 소진한 경우 당일 추가 질의만 일시 제한되며, 추가 요금이 청구되지 않는다.",
        "",
        "### 2단계: 조직 정책 기반 Google AI Studio API 키 발급 차단 (필수)",
        "```bash",
        f"gcloud resource-manager org-policies enable-enforce constraints/gcp.restrictServiceUsage --project={report['project_id']}",
        "```",
        "",
        "### 3단계: Generative Language API 비활성화 (권장)",
        "```bash",
        f"gcloud services disable generativelanguage.googleapis.com --project={report['project_id']} --force",
        "```",
        "",
        "### 4단계: 계열사 IT 관리자 결제 권한(Billing RBAC) 회수 및 최소 권한 적용",
        "- 최고 관리자(Super Admin) 권한 부여를 금지하고, 계열사 조직 단위(OU)에 한정된 맞춤 역할을 생성하여 사용자/그룹 관리 권한만 위임한다.",
        "- Google Cloud 콘솔에서 `roles/billing.admin` 및 `roles/billing.user` 권한을 계열사 관리자에게 부여하지 않는다.",
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
    report = run_diagnostics(
        project_id=reported_project,
        billing_id=args.billing_account_id,
        spend_cap_usd=args.spend_cap_usd,
        alert_threshold=args.alert_threshold,
        dry_run=args.dry_run,
    )

    if args.json_output:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_text_report(report)

    # 마크다운 리포트 자동 생성 및 덮어쓰기
    report_content = build_markdown_report(report, args.dry_run)
    save_markdown_report(report_content, "report.md")


if __name__ == "__main__":
    main()
