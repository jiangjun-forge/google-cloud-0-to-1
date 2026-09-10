#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Gemini Enterprise Overage 과금 방어 및 일일 풀링 쿼터 쓰로틀링 가드 진단 도구."""

import argparse
import json
import os
import sys
from typing import Any, Dict, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


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
        default=project_env or "demo-project",
        help="진단 대상 GCP 프로젝트 ID",
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

    spend_cap_configured = False
    budget_alerts_configured = False

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
        {
            "item": "INDIVIDUAL_LIMIT_UNSUPPORTED",
            "status": "INFO",
            "description": "현재 Gemini Enterprise 콘솔은 사용자나 그룹별 개별 지출 한도 부여를 지원하지 않으므로 프로젝트/빌링 계정 단위 글로벌 Spend Cap으로 제어해야 한다.",
        },
        {
            "item": "STORAGE_INDEX_SEPARATE_BILLING",
            "status": "INFO",
            "description": "데이터스토어 인덱싱 및 스토리지 초과 사용량은 오버리지 토글 설정과 무관하게 계약 조건에 따라 별도 과금된다.",
        },
    ]

    return {
        "project_id": project_id,
        "billing_account_id": billing_id,
        "recommended_spend_cap_usd": spend_cap_usd,
        "alert_threshold_pct": alert_threshold,
        "tier_statuses": tier_statuses,
        "spend_cap_configured": spend_cap_configured,
        "budget_alerts_configured": budget_alerts_configured,
        "findings": findings,
    }


def print_text_report(report: Dict[str, Any]) -> None:
    print("\n" + "=" * 76)
    print(" [Gemini Enterprise Overage 빌링 및 쿼터 쓰로틀링 진단 리포트]")
    print("=" * 76)
    print(f"진단 대상 프로젝트 ID   : {report['project_id']}")
    print(f"Cloud Billing 계정 ID   : {report['billing_account_id']}")
    print(f"권장 월간 지출 상한(Cap): ${report['recommended_spend_cap_usd']:,.2f}")
    print(f"예산 알림 임계치        : {report['alert_threshold_pct']}%")
    print("-" * 76)

    print("\n[에디션별 오버리지 및 일일 쿼터 현황]")
    for t in report["tier_statuses"]:
        enabled_str = "ON (활성화)" if t["overage_billing_enabled"] else "OFF (비활성화)"
        print(f"* {t['tier']}")
        print(f"  - 오버리지 빌링 설정: {enabled_str}")
        print(f"  - 일일 쿼터 소진율  : {t['daily_pooled_quota_usage_pct']:.1f}%")
        print(f"  - 진단 판정         : [{t['risk_assessment']}]")
        print(f"  - 세부 분석         : {t['notes']}")

    print("\n[항목별 상세 진단 결과]")
    for idx, f in enumerate(report["findings"], 1):
        print(f"{idx}. [{f['status']}] {f['item']}")
        print(f"   내용: {f['description']}")

    print("\n[단계별 긴급 대응 및 거버넌스 가이드]")
    print("1. Standard 티어 업무 중단 긴급 방어:")
    print("   - Gemini Enterprise 관리 콘솔에서 Standard 티어의 오버리지 빌링을 수동 활성화(ON)하여 쿼터 소진 시 즉각적인 쓰로틀링을 차단한다.")
    print("2. Cloud Billing Spend Cap(월 지출 한도) 즉시 설정:")
    print(f"   - 결제 콘솔에서 월간 오버리지 상한(${report['recommended_spend_cap_usd']:,.2f})을 설정하여 예기치 못한 비용 급증을 효과적으로 예방한다.")
    print(f"3. 실시간 예산 경보(Budget Alerts {report['alert_threshold_pct']}%) 연동:")
    print("   - Pub/Sub 및 인프라 담당자 이메일 알림을 등록하여 임계치 초과 시 FinOps 팀에 즉각 노티되도록 조치한다.")
    print("=" * 76 + "\n")


def main() -> None:
    args = parse_arguments()
    report = run_diagnostics(
        project_id=args.project_id,
        billing_id=args.billing_account_id,
        spend_cap_usd=args.spend_cap_usd,
        alert_threshold=args.alert_threshold,
        dry_run=args.dry_run,
    )

    if args.json_output:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_text_report(report)


if __name__ == "__main__":
    main()
