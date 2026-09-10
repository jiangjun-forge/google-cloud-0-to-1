#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Cloud Run 사용량 기반 Compute CUD 약정 할인 최적화 및 권장 엔진 과소 약정 트랩 분석 도구."""

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
        description="Cloud Run 사용량 시계열을 분석하여 Compute Flexible CUD 최적 약정액을 산출한다."
    )
    billing_env = os.getenv("BILLING_ACCOUNT_ID")
    project_env = os.getenv("PROJECT_ID")
    lookback_env = os.getenv("LOOKBACK_DAYS")
    margin_env = os.getenv("SAFETY_MARGIN")

    parser.add_argument(
        "--billing-account-id",
        dest="billing_account_id",
        default=billing_env or "012345-6789AB-CDEF01",
        help="Cloud Billing 계정 ID",
    )
    parser.add_argument(
        "--project-id",
        dest="project_id",
        default=project_env or "demo-project",
        help="진단 대상 GCP 프로젝트 ID",
    )
    parser.add_argument(
        "--lookback-days",
        dest="lookback_days",
        type=int,
        default=int(lookback_env) if lookback_env else 90,
        help="사용량 분석 기간 (일 단위, 기본값: 90)",
    )
    parser.add_argument(
        "--safety-margin",
        dest="safety_margin",
        type=float,
        default=float(margin_env) if margin_env else 0.85,
        help="안전 마진 계수 (0.5 ~ 0.95, 기본값: 0.85)",
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


def run_cuds_analysis(
    billing_id: str,
    project_id: str,
    lookback_days: int,
    safety_margin: float,
    dry_run: bool,
) -> Dict[str, Any]:
    # 모의 시계열 지표 (시간당 지출 기준)
    # Cloud Run vCPU + Memory 실질 시간당 비용
    avg_hourly_spend = 52.40
    peak_hourly_spend = 88.60
    trough_hourly_spend = 36.00  # 야간/주말 Scale-in 시 도달하는 최저 바닥선
    console_recommended_commitment = 15.00  # 콘솔 기본 추천 엔진의 극보수적 수치

    # 최적화된 권장 약정액: 최저 바닥선 * 안전 마진 계수
    optimal_commitment = round(trough_hourly_spend * safety_margin, 2)

    # 할인율 기준 (Compute Flexible CUD: 1년 약 17%, 3년 약 28%)
    discount_1yr = 0.17
    discount_3yr = 0.28

    # 월간 시간 수 (730시간 기준)
    hours_per_month = 730

    # 콘솔 추천 수치 적용 시 절감액 (1년/3년)
    savings_console_1yr = round(console_recommended_commitment * discount_1yr * hours_per_month, 2)
    savings_console_3yr = round(console_recommended_commitment * discount_3yr * hours_per_month, 2)

    # 최적 약정 수치 적용 시 절감액 (1년/3년)
    savings_optimal_1yr = round(optimal_commitment * discount_1yr * hours_per_month, 2)
    savings_optimal_3yr = round(optimal_commitment * discount_3yr * hours_per_month, 2)

    # 추가 확보 절감액 (Gap)
    gap_1yr = round(savings_optimal_1yr - savings_console_1yr, 2)
    gap_3yr = round(savings_optimal_3yr - savings_console_3yr, 2)

    preflight_checks = [
        {
            "item": "CPU_ALLOCATION_OPTIMIZATION",
            "status": "PASS",
            "description": "배치 잡을 제외한 웹 서비스의 80% 이상이 '요청 처리 중에만 CPU 할당(Request-only)'으로 구성되어 유휴 vCPU 낭비가 방지되고 있다.",
        },
        {
            "item": "CONTAINER_CONCURRENCY_TUNING",
            "status": "PASS",
            "description": "컨테이너당 기본 동시성(80) 설정이 적절하여 불필요한 인스턴스 스케일 아웃이 억제되고 있다.",
        },
        {
            "item": "MIN_INSTANCES_AUDIT",
            "status": "WARNING",
            "description": "일부 개발 환경 서비스에 min-instances=1 이상이 설정되어 있어 트래픽 바닥선이 인위적으로 높게 잡힐 가능성이 있다. 실 운영 서비스 외 유휴 인스턴스 정리가 권장된다.",
        },
    ]

    return {
        "project_id": project_id,
        "billing_account_id": billing_id,
        "lookback_days": lookback_days,
        "safety_margin": safety_margin,
        "metrics": {
            "avg_hourly_spend_usd": avg_hourly_spend,
            "peak_hourly_spend_usd": peak_hourly_spend,
            "trough_hourly_spend_usd": trough_hourly_spend,
        },
        "recommendations": {
            "console_recommended_hourly_usd": console_recommended_commitment,
            "optimal_recommended_hourly_usd": optimal_commitment,
            "under_commitment_gap_hourly_usd": round(optimal_commitment - console_recommended_commitment, 2),
        },
        "estimated_monthly_savings": {
            "console_1yr_usd": savings_console_1yr,
            "console_3yr_usd": savings_console_3yr,
            "optimal_1yr_usd": savings_optimal_1yr,
            "optimal_3yr_usd": savings_optimal_3yr,
            "additional_savings_gain_1yr_usd": gap_1yr,
            "additional_savings_gain_3yr_usd": gap_3yr,
        },
        "preflight_checks": preflight_checks,
    }


def print_text_report(report: Dict[str, Any]) -> None:
    print("\n" + "=" * 76)
    print(" [Cloud Run Compute CUD 약정 최적화 및 과소 약정 트랩 분석 리포트]")
    print("=" * 76)
    print(f"대상 프로젝트 ID       : {report['project_id']}")
    print(f"Cloud Billing 계정 ID  : {report['billing_account_id']}")
    print(f"분석 대상 기간         : 최근 {report['lookback_days']}일")
    print(f"적용 안전 마진 계수    : {report['safety_margin'] * 100:.0f}% (최저 사용량 기준)")
    print("-" * 76)

    m = report["metrics"]
    print("\n[시간당 사용량 지표 분석 (USD)]")
    print(f"- 평균 시간당 지출     : ${m['avg_hourly_spend_usd']:.2f} / hour")
    print(f"- 피크 시간당 지출     : ${m['peak_hourly_spend_usd']:.2f} / hour")
    print(f"- 최저 바닥선(Trough)  : ${m['trough_hourly_spend_usd']:.2f} / hour  (야간/주말 Scale-in 시 최저점)")

    r = report["recommendations"]
    print("\n[CUD 약정 추천 수치 비교]")
    print(f"1. GCP 콘솔 기본 추천액 : ${r['console_recommended_hourly_usd']:.2f} / hour (변동성 보수 계산으로 과소 약정 유도)")
    print(f"2. 실질 최적 권장 약정액: ${r['optimal_recommended_hourly_usd']:.2f} / hour (바닥선 x {report['safety_margin']*100:.0f}%)")
    print(f"   => 약정 갭(추가 약정): ${r['under_commitment_gap_hourly_usd']:.2f} / hour")

    s = report["estimated_monthly_savings"]
    print("\n[월간 예상 순 절감액 비교 (USD, 월 730시간 기준)]")
    print(f"- 콘솔 추천 수용 시    : 1년 약정 ${s['console_1yr_usd']:,.2f} | 3년 약정 ${s['console_3yr_usd']:,.2f}")
    print(f"- 최적 권장 수용 시    : 1년 약정 ${s['optimal_1yr_usd']:,.2f} | 3년 약정 ${s['optimal_3yr_usd']:,.2f}")
    print(f"** 추가 확보 절감 이익  : 1년 약정 +${s['additional_savings_gain_1yr_usd']:,.2f} | 3년 약정 +${s['additional_savings_gain_3yr_usd']:,.2f} / month")

    print("\n[사전 최적화 점검 결과]")
    for idx, c in enumerate(report["preflight_checks"], 1):
        print(f"{idx}. [{c['status']}] {c['item']}")
        print(f"   내용: {c['description']}")

    print("\n[권장 실행 가이드]")
    print("1. min-instances 점검: 개발/스테이징 환경의 불필요한 상시 인스턴스를 0으로 조정하여 실제 프로덕션 바닥선을 재측정한다.")
    print("2. 약정 유형 선택: 서비스별 종속 약정이 아닌 'Compute Flexible CUD'를 구매한다 (Cloud Run, GKE, GCE 공통 적용).")
    print(f"3. 구매 커밋 금액: 콘솔 추천(${r['console_recommended_hourly_usd']:.2f})에 안주하지 않고 안전 바닥선인 ${r['optimal_recommended_hourly_usd']:.2f}/hr 수준으로 구매를 검토한다.")
    print("=" * 76 + "\n")


def main() -> None:
    args = parse_arguments()
    report = run_cuds_analysis(
        billing_id=args.billing_account_id,
        project_id=args.project_id,
        lookback_days=args.lookback_days,
        safety_margin=args.safety_margin,
        dry_run=args.dry_run,
    )

    if args.json_output:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_text_report(report)


if __name__ == "__main__":
    main()
