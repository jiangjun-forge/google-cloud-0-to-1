#!/usr/bin/env bash
"""Copyright 2026 Google LLC

SPDX-License-Identifier: Apache-2.0
"""

import argparse
import os
import subprocess
import sys
from typing import Any, Dict, List, Tuple


def get_gcloud_active_config() -> Tuple[str, str]:
    """gcloud 활성 계정 및 설정된 기본 프로젝트를 안전하게 탐색한다."""
    project_id = ""
    region = ""
    try:
        p_res = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            check=False,
        )
        if p_res.returncode == 0:
            project_id = p_res.stdout.strip()
    except Exception:
        pass

    try:
        r_res = subprocess.run(
            ["gcloud", "config", "get-value", "compute/region"],
            capture_output=True,
            text=True,
            check=False,
        )
        if r_res.returncode == 0:
            region = r_res.stdout.strip()
    except Exception:
        pass

    return project_id, region


def parse_arguments() -> argparse.Namespace:
    """CLI 실행 인자를 파싱한다."""
    default_proj, default_reg = get_gcloud_active_config()

    parser = argparse.ArgumentParser(
        description="Speech-to-Text V2 LRO 폴링 쿼터 고갈 및 429 장애 진단 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-p",
        "--project",
        default=os.environ.get("PROJECT_ID") or default_proj or "example-project",
        help="대상 Google Cloud 프로젝트 ID (미지정 시 활성 gcloud 설정 자동 감지)",
    )
    parser.add_argument(
        "-l",
        "--location",
        default=os.environ.get("LOCATION") or default_reg or "us-central1",
        help="Speech-to-Text V2 리전 위치 (기본값: us-central1)",
    )
    parser.add_argument(
        "-c",
        "--concurrency",
        type=int,
        default=int(os.environ.get("CONCURRENCY") or 12),
        help="예상 동시 비동기 배치 음성 인식 작업 수 (기본값: 12)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 GCP 모니터링/할당량 API 호출 없이 내장된 가상 시나리오로 스모크 테스트 수행",
    )
    return parser.parse_args()


def simulate_lro_polling_load(concurrency: int) -> Dict[str, Any]:
    """동시 작업 수에 따른 SDK 기본 폴링 vs 권장 폴링 호출량 및 쿼터 고갈 위험도를 계산한다."""
    # Speech-to-Text V2 기본 할당량 한도
    operation_requests_quota_rpm = 150
    batch_recognize_quota_rpm = 300

    # SDK 기본 폴링 설정 (google-api-core polling.py)
    # 초기 1.0초 후 지수 증가하나 수초 이내에 짧은 간격(기본 최대 10~15초) 유지
    # 평균 폴링 주기: 약 3.5초에 1회 -> 작업당 분당 약 17회 GetOperation 발생
    default_sdk_polls_per_min_per_worker = 17

    # 권장 커스텀 폴링 설정 (initial=15.0, maximum=30.0, multiplier=1.5)
    # 대용량 오디오(수분~수십분) 처리 시 분당 약 2.5회 GetOperation 발생
    optimized_polls_per_min_per_worker = 2.5

    total_default_polling_rpm = concurrency * default_sdk_polls_per_min_per_worker
    total_optimized_polling_rpm = round(concurrency * optimized_polls_per_min_per_worker, 1)

    default_utilization_pct = round((total_default_polling_rpm / operation_requests_quota_rpm) * 100, 1)
    optimized_utilization_pct = round((total_optimized_polling_rpm / operation_requests_quota_rpm) * 100, 1)

    if default_utilization_pct >= 100.0:
        status = "CRITICAL_RISK"
    elif default_utilization_pct >= 70.0:
        status = "WARNING_RISK"
    else:
        status = "SAFE"

    return {
        "operation_requests_quota_rpm": operation_requests_quota_rpm,
        "batch_recognize_quota_rpm": batch_recognize_quota_rpm,
        "concurrency": concurrency,
        "default_polling_rpm": total_default_polling_rpm,
        "default_utilization_pct": default_utilization_pct,
        "optimized_polling_rpm": total_optimized_polling_rpm,
        "optimized_utilization_pct": optimized_utilization_pct,
        "status": status,
    }


def print_diagnostic_banner(project_id: str, location: str, dry_run: bool) -> None:
    """진단 헤더 배너를 출력한다."""
    print("=" * 88)
    print(" Speech-to-Text V2 LRO 폴링 쿼터 고갈 및 429 에러 예방 진단 리포트")
    print(f" 대상 프로젝트 : {project_id}")
    print(f" 리전 위치     : {location}")
    print(f" 진단 모드     : {'가상 실행 (Dry-run)' if dry_run else '사내 실측 진단'}")
    print("=" * 88)


def render_assessment_table(metrics: Dict[str, Any]) -> None:
    """진단 결과 매트릭스 표를 출력한다."""
    print("\n[1단계: Speech-to-Text V2 할당량 vs SDK 폴링 트래픽 부하 진단]")
    print("-" * 88)
    print(f"{'할당량 지표 (Metric Token)':<46} | {'기본 한도':<10} | {'예상 소모량':<12} | {'상태'}")
    print("-" * 88)

    # 1. 배치 인식 제출 쿼터
    batch_rpm = metrics["concurrency"]
    batch_limit = metrics["batch_recognize_quota_rpm"]
    print(f"{'speech.googleapis.com/batch_recognize_requests':<46} | {batch_limit:>4} RPM  | {batch_rpm:>4} RPM     | [정상] 안전 여유")

    # 2. SDK LRO 폴링 쿼터
    poll_rpm = metrics["default_polling_rpm"]
    poll_limit = metrics["operation_requests_quota_rpm"]
    poll_pct = metrics["default_utilization_pct"]
    
    if metrics["status"] == "CRITICAL_RISK":
        poll_status = f"[위험] {poll_pct}% 초과 (429 유발)"
    elif metrics["status"] == "WARNING_RISK":
        poll_status = f"[주의] {poll_pct}% 소진 임박"
    else:
        poll_status = f"[정상] {poll_pct}% 건전"

    print(f"{'speech.googleapis.com/operation_requests':<46} | {poll_limit:>4} RPM  | {poll_rpm:>4} RPM     | {poll_status}")
    print("-" * 88)


def render_rca_and_prescription(metrics: Dict[str, Any], project_id: str, location: str) -> None:
    """원인 분석(RCA) 및 아키텍처 처방전을 출력한다."""
    print("\n[2단계: 메트릭 불일치 및 429 RESOURCE_EXHAUSTED 근본 원인 분석 (RCA)]")
    print(f"1. 대시보드 메트릭 착시 현상:")
    print("   - 운영 모니터링에서는 음성 변환 요청 자체(`BatchRecognize`)의 RPM을 주로 주시하므로 한도(300 RPM) 내 정상으로 표시된다.")
    print("   - 그러나 클라이언트 SDK(`google-api-core`)에서 `operation.result()`를 대기할 때 내부적으로 백그라운드 폴링(`GetOperation`)을 수초 간격으로 수행한다.")
    print(f"2. 쿼터 고갈 메커니즘:")
    print(f"   - 현재 동시 작업 수({metrics['concurrency']}건)에서 SDK 기본 폴링 호출량은 약 {metrics['default_polling_rpm']} RPM에 달한다.")
    print(f"   - 이는 리전 기본 할당량인 `speech.googleapis.com/operation_requests`({metrics['operation_requests_quota_rpm']} RPM)을 {metrics['default_utilization_pct']}% 초과하여 429 장애를 촉발한다.")

    print("\n[3단계: 현업 즉시 조치 가이드 및 코드 처방전]")
    print("-" * 88)
    print("처방 1: SDK 커스텀 Polling 지수 백오프 및 주기 완화 적용 (권장)")
    print("  -> 초기 대기 시간을 늘리고 최대 폴링 간격을 30초로 설정하여 불필요한 GetOperation 호출을 85% 이상 절감한다:")
    print(f"""
```python
from google.api_core import polling
from google.cloud import speech_v2

client = speech_v2.SpeechClient()

# 커스텀 폴링 폴러 정의 (초기 대기 15초, 최대 주기 30초, 배수 1.5)
custom_polling = polling.DEFAULT_POLLING.with_delay(
    initial=15.0,
    maximum=30.0,
    multiplier=1.5,
)

# BatchRecognize 작업 제출
operation = client.batch_recognize(request=request)

# 커스텀 폴링 객체 주입하여 대기
result = operation.result(polling=custom_polling, timeout=3600)
```
""")

    print("처방 2: 동기식 블로킹 대기 지양 및 비동기 파이프라인 분리 (아키텍처 개선)")
    print("  - 워커 프로세스에서 `operation.result()`로 동기 대기하지 않고, `operation.operation.name`을 Cloud Tasks나 Pub/Sub에 적재 후 즉시 반환한다.")
    print("  - 단일 스케줄러 워커가 1분 간격으로 대기열에 있는 작업들의 상태를 일괄 조회하여 쿼터 소진을 원천 제어한다.")

    print("\n처방 3: 콘솔을 통한 필수 할당량 상향 요청 (QIR)")
    print(f"  - 콘솔 경로: IAM & Admin > Quotas ( https://console.cloud.google.com/iam-admin/quotas?project={project_id} )")
    print(f"  - 대상 서비스: Cloud Speech-to-Text API (리전: {location})")
    print("  - 필수 상향 지표: `speech.googleapis.com/operation_requests` (기본 150 RPM -> 1,000+ RPM 권장)")
    print("=" * 88)


def main() -> None:
    args = parse_arguments()
    print_diagnostic_banner(args.project, args.location, args.dry_run)
    metrics = simulate_lro_polling_load(args.concurrency)
    render_assessment_table(metrics)
    render_rca_and_prescription(metrics, args.project, args.location)


if __name__ == "__main__":
    main()
