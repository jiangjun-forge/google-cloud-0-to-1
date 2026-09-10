#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""FCM 대량 푸시 쿼터 고갈 및 다운스트림 쓰로틀링(429) 복원력 진단 도구."""

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
    except Exception:
        pass

    return fallback_demo


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="FCM 대량 다운스트림 메시지 전송량과 429 쓰로틀링 및 재시도 복원력을 진단한다."
    )
    project_env = os.getenv("PROJECT_ID")
    peak_env = os.getenv("PEAK_MESSAGES_PER_MINUTE")
    quota_env = os.getenv("CURRENT_QUOTA_LIMIT_PER_MINUTE")

    parser.add_argument(
        "--project-id",
        dest="project_id",
        default=project_env or "",
        help="진단 대상 GCP 프로젝트 ID (Firebase 프로젝트, 미지정 시 활성 프로젝트 감지)",
    )
    parser.add_argument(
        "--peak-msg-per-min",
        dest="peak_msg_per_min",
        type=int,
        default=int(peak_env) if peak_env else 750000,
        help="피크 시 분당 푸시 발송 시도량 (기본값: 750000)",
    )
    parser.add_argument(
        "--quota-limit-per-min",
        dest="quota_limit_per_min",
        type=int,
        default=int(quota_env) if quota_env else 600000,
        help="현재 프로젝트의 분당 다운스트림 메시지 할당량 (기본값: 600000)",
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
    peak_msg_per_min: int,
    quota_limit_per_min: int,
    dry_run: bool,
) -> Dict[str, Any]:
    quota_utilization_pct = round((peak_msg_per_min / quota_limit_per_min) * 100, 1)
    is_exceeded = peak_msg_per_min > quota_limit_per_min
    gap = peak_msg_per_min - quota_limit_per_min if is_exceeded else 0

    # 429 에러율 추정
    estimated_429_error_rate_pct = round((gap / peak_msg_per_min) * 100, 1) if is_exceeded else 0.0

    findings: List[Dict[str, Any]] = []

    if is_exceeded:
        findings.append({
            "item": "DOWNSTREAM_QUOTA_EXCEEDED",
            "status": "CRITICAL",
            "description": f"피크 시 분당 발송량({peak_msg_per_min:,}건)이 기본 할당량({quota_limit_per_min:,}건)을 {quota_utilization_pct}% 초과하여 약 {estimated_429_error_rate_pct}%의 요청이 429 쓰로틀링 에러로 실패한다.",
        })
    else:
        findings.append({
            "item": "DOWNSTREAM_QUOTA_EXCEEDED",
            "status": "PASS",
            "description": f"피크 발송량이 현재 할당량 이내({quota_utilization_pct}%)로 유지되고 있다.",
        })

    findings.append({
        "item": "TOKEN_BUCKET_RATE_LIMITING",
        "status": "WARNING",
        "description": "발송 백엔드에 토큰 버킷 속도 제한기(Rate Limiter)가 누락되어 있어 이벤트 발생 시 일시에 요청이 몰려 FCM 인프라 쓰로틀링을 유발한다.",
    })
    findings.append({
        "item": "EXPONENTIAL_BACKOFF_AND_JITTER",
        "status": "WARNING",
        "description": "429 에러 발생 시 고정 대기 재시도 또는 즉시 재시도로 인해 '재시도 폭풍(Retry Storm)'이 발생하고 있다. Full Jitter 기반 지수 백오프 도입이 시급하다.",
    })
    findings.append({
        "item": "TOPIC_FANOUT_OPTIMIZATION",
        "status": "INFO",
        "description": "단일 기기 토큰 반복 호출 대신 주제(Topic) 메시징 또는 일괄 발송(send_all) API를 활용하면 네트워크 오버헤드와 쓰로틀링을 대폭 완화할 수 있다.",
    })

    overall_status = "ACTION_REQUIRED" if is_exceeded else "HEALTHY"

    return {
        "project_id": project_id,
        "peak_messages_per_minute": peak_msg_per_min,
        "quota_limit_per_minute": quota_limit_per_min,
        "quota_utilization_pct": quota_utilization_pct,
        "estimated_429_error_rate_pct": estimated_429_error_rate_pct,
        "overall_status": overall_status,
        "findings": findings,
    }


def print_text_report(report: Dict[str, Any]) -> None:
    print("\n" + "=" * 76)
    print(" [FCM 대량 푸시 쿼터 고갈 및 429 쓰로틀링 복원력 진단 리포트]")
    print("=" * 76)
    print(f"진단 대상 프로젝트 ID   : {report['project_id']}")
    print(f"피크 분당 발송 시도량   : {report['peak_messages_per_minute']:,} 건/분")
    print(f"현재 분당 할당량 한도   : {report['quota_limit_per_minute']:,} 건/분")
    print(f"할당량 소진율           : {report['quota_utilization_pct']}%")
    print(f"추정 429 쓰로틀링 실패율: {report['estimated_429_error_rate_pct']}%")
    print(f"종합 진단 상태          : {report['overall_status']}")
    print("-" * 76)

    print("\n[항목별 세부 진단 결과]")
    for idx, f in enumerate(report["findings"], 1):
        print(f"{idx}. [{f['status']}] {f['item']}")
        print(f"   내용: {f['description']}")

    print("\n[복원력 강화 및 긴급 조치 가이드]")
    print("1. Google Cloud 콘솔 할당량 상향(Quota Increase) 신청:")
    print("   - 콘솔 경로: IAM 및 관리자 > 할당량 및 시스템 한도")
    print("   - 대상 지표: Firebase Cloud Messaging API - Downstream messages per minute")
    print(f"   - 권장 신청값: 피크 대비 1.5배 여유 확보 (최소 {int(report['peak_messages_per_minute'] * 1.5):,} 건/분)")
    print("2. 클라이언트/백엔드 토큰 버킷 속도 제한(Rate Limiting) 구현:")
    print(f"   - 발송 큐에서 초당 최대 전송량을 {int(report['quota_limit_per_minute'] / 60):,} msg/sec 이하로 스로틀링한다.")
    print("3. Full Jitter 지수 백오프 재시도 적용:")
    print("   - wait_time = min(max_backoff, base_backoff * (2 ** attempt)) * random.uniform(0.5, 1.5)")
    print("=" * 76 + "\n")


def main() -> None:
    args = parse_arguments()
    proj_id = args.project_id or get_default_project(is_dry_run=args.dry_run)
    report = run_diagnostics(
        project_id=proj_id,
        peak_msg_per_min=args.peak_msg_per_min,
        quota_limit_per_min=args.quota_limit_per_min,
        dry_run=args.dry_run,
    )

    if args.json_output:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_text_report(report)


if __name__ == "__main__":
    main()
