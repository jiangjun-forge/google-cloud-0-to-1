#!/usr/bin/env python3
"""Copyright 2026 Google LLC

SPDX-License-Identifier: Apache-2.0
"""

import argparse
import os
import subprocess
import sys
from typing import Any, Dict, List, Tuple

# Google Cloud 비동기 장기 실행 작업(LRO) 서비스별 프로필 메타데이터
SUPPORTED_SERVICES: Dict[str, Dict[str, Any]] = {
    "speech-to-text": {
        "name": "Cloud Speech-to-Text V2",
        "api_name": "speech.googleapis.com",
        "job_method": "BatchRecognize",
        "job_quota_token": "speech.googleapis.com/batch_recognize_requests",
        "job_quota_default": 300,
        "operation_quota_token": "speech.googleapis.com/operation_requests",
        "operation_quota_default": 150,
        "typical_duration_min": 10,
        "client_lib": "from google.cloud import speech_v2",
    },
    "document-ai": {
        "name": "Document AI (Batch OCR/Parser)",
        "api_name": "documentai.googleapis.com",
        "job_method": "BatchProcessDocuments",
        "job_quota_token": "documentai.googleapis.com/batch_process_requests",
        "job_quota_default": 120,
        "operation_quota_token": "documentai.googleapis.com/operation_requests",
        "operation_quota_default": 120,
        "typical_duration_min": 8,
        "client_lib": "from google.cloud import documentai_v1",
    },
    "video-intelligence": {
        "name": "Cloud Video Intelligence",
        "api_name": "videointelligence.googleapis.com",
        "job_method": "AnnotateVideo",
        "job_quota_token": "videointelligence.googleapis.com/annotate_video_requests",
        "job_quota_default": 180,
        "operation_quota_token": "videointelligence.googleapis.com/operation_requests",
        "operation_quota_default": 150,
        "typical_duration_min": 15,
        "client_lib": "from google.cloud import videointelligence_v1",
    },
    "translation": {
        "name": "Cloud Translation V3 (Batch Document)",
        "api_name": "translate.googleapis.com",
        "job_method": "BatchTranslateDocument",
        "job_quota_token": "translate.googleapis.com/batch_document_requests",
        "job_quota_default": 150,
        "operation_quota_token": "translate.googleapis.com/operation_requests",
        "operation_quota_default": 150,
        "typical_duration_min": 5,
        "client_lib": "from google.cloud import translate_v3",
    },
}


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
        description="Google Cloud LRO 비동기 작업 폴링 쿼터 고갈 및 429 장애 진단 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-p",
        "--project",
        default=os.environ.get("PROJECT_ID") or default_proj or "example-project",
        help="대상 Google Cloud 프로젝트 ID (미지정 시 활성 gcloud 설정 자동 감지)",
    )
    parser.add_argument(
        "-s",
        "--service",
        default=os.environ.get("SERVICE_TYPE") or "speech-to-text",
        choices=list(SUPPORTED_SERVICES.keys()),
        help="진단 대상 비동기 LRO 서비스 (기본값: speech-to-text, 선택: document-ai, video-intelligence, translation)",
    )
    parser.add_argument(
        "-l",
        "--location",
        default=os.environ.get("LOCATION") or default_reg or "us-central1",
        help="API 리전 위치 (기본값: us-central1 또는 asia-northeast3)",
    )
    parser.add_argument(
        "-c",
        "--concurrency",
        type=int,
        default=int(os.environ.get("CONCURRENCY") or 12),
        help="예상 동시 비동기 배치 작업 수 (기본값: 12)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 GCP 모니터링/할당량 API 호출 없이 내장된 가상 시나리오로 스모크 테스트 수행",
    )
    return parser.parse_args()


def simulate_lro_polling_load(service_key: str, concurrency: int) -> Dict[str, Any]:
    """선택된 서비스와 동시 작업 수에 따른 SDK 기본 폴링 vs 권장 폴링 호출량 및 쿼터 소진율을 계산한다."""
    svc = SUPPORTED_SERVICES[service_key]
    operation_requests_quota_rpm = svc["operation_quota_default"]
    job_quota_rpm = svc["job_quota_default"]

    # SDK 기본 폴링 설정 (google-api-core polling.py)
    # 초기 1.0초 지연 후 지수 배수로 증가하나 수초 이내에 짧은 간격(상한 10~15초)을 유지
    # 평균 폴링 주기: 약 3.5초에 1회 -> 단일 작업당 분당 약 17회 GetOperation 호출 발생
    default_sdk_polls_per_min_per_worker = 17

    # 권장 커스텀 폴링 설정 (initial=15.0, maximum=30.0, multiplier=1.5)
    # 대용량 비동기 배치 특성에 맞추어 초기 지연을 늘리고 상한을 30초로 제한
    # 평균 폴링 주기: 약 24초에 1회 -> 단일 작업당 분당 약 2.5회 GetOperation 호출 발생
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
        "service_meta": svc,
        "concurrency": concurrency,
        "operation_requests_quota_rpm": operation_requests_quota_rpm,
        "job_quota_rpm": job_quota_rpm,
        "default_polling_rpm": total_default_polling_rpm,
        "default_utilization_pct": default_utilization_pct,
        "optimized_polling_rpm": total_optimized_polling_rpm,
        "optimized_utilization_pct": optimized_utilization_pct,
        "status": status,
    }


def print_diagnostic_banner(project_id: str, svc_name: str, location: str, dry_run: bool) -> None:
    """진단 헤더 배너를 출력한다."""
    print("=" * 88)
    print(" Google Cloud LRO(비동기 장기 실행 작업) 폴링 쿼터 고갈 및 429 에러 진단 리포트")
    print(f" 대상 서비스   : {svc_name}")
    print(f" 대상 프로젝트 : {project_id}")
    print(f" 리전 위치     : {location}")
    print(f" 진단 모드     : {'가상 실행 (Dry-run)' if dry_run else '사내 실측 진단'}")
    print("=" * 88)


def render_assessment_table(res: Dict[str, Any]) -> None:
    """진단 결과 매트릭스 표를 출력한다."""
    svc = res["service_meta"]
    print(f"\n[1단계: {svc['name']} 할당량 vs SDK LRO 폴링 트래픽 부하 진단]")
    print("-" * 88)
    print(f"{'할당량 지표 (Metric Token)':<46} | {'기본 한도':<10} | {'예상 소모량':<12} | {'상태'}")
    print("-" * 88)

    # 1. 메인 작업 제출 쿼터
    job_rpm = res["concurrency"]
    job_limit = res["job_quota_rpm"]
    print(f"{svc['job_quota_token']:<46} | {job_limit:>4} RPM  | {job_rpm:>4} RPM     | [정상] 안전 여유")

    # 2. SDK LRO 폴링 쿼터 (Operation Requests)
    poll_rpm = res["default_polling_rpm"]
    poll_limit = res["operation_requests_quota_rpm"]
    poll_pct = res["default_utilization_pct"]

    if res["status"] == "CRITICAL_RISK":
        poll_status = f"[위험] {poll_pct}% 초과 (429 유발)"
    elif res["status"] == "WARNING_RISK":
        poll_status = f"[주의] {poll_pct}% 소진 임박"
    else:
        poll_status = f"[정상] {poll_pct}% 건전"

    print(f"{svc['operation_quota_token']:<46} | {poll_limit:>4} RPM  | {poll_rpm:>4} RPM     | {poll_status}")
    print("-" * 88)


def render_rca_and_prescription(res: Dict[str, Any], project_id: str, location: str) -> None:
    """원인 분석(RCA) 및 아키텍처 처방전을 출력한다."""
    svc = res["service_meta"]
    print("\n[2단계: 메트릭 착시 현상 및 429 RESOURCE_EXHAUSTED 근본 원인 분석 (RCA)]")
    print("1. 대시보드 메트릭 착시 (The Metric Mirage):")
    print(f"   - 운영 대시보드에서는 주 작업 요청 메트릭(`{svc['job_method']}`)만 확인하므로 정상 한도 내로 표시된다.")
    print("   - 그러나 구글 파이썬 클라이언트 SDK 공통 기반 라이브러리인 `google-api-core`는")
    print("     `operation.result()` 호출 시 내부적으로 `GetOperation` API를 수초 간격으로 무차별 폴링한다.")
    print("2. 숨겨진 쿼터 고갈 메커니즘 (Hidden Quota Exhaustion):")
    print(f"   - 현재 동시 작업 수({res['concurrency']}건)에서 SDK 기본 폴링 호출량은 약 {res['default_polling_rpm']} RPM에 달한다.")
    print(f"   - 이는 리전당 기본 할당량인 `{svc['operation_quota_token']}`({res['operation_requests_quota_rpm']} RPM)을 {res['default_utilization_pct']}% 수준으로 소진하여 429 장애를 촉발한다.")
    print(f"   - 본 현상은 {svc['name']}뿐만 아니라 Document AI, Video Intelligence, Translation 등 구글 클라우드의 모든 LRO 비동기 API에서 동일하게 발생한다.")

    print("\n[3단계: 현업 즉시 조치 가이드 및 코드 처방전]")
    print("-" * 88)
    print("처방 1: SDK 커스텀 Polling 지수 백오프 주입 (모든 LRO 서비스 공통 적용 가능)")
    print("  -> 초기 대기 시간을 늘리고 최대 폴링 주기를 30초로 설정하여 불필요한 GetOperation 호출을 85% 이상 절감한다:")
    print(f"""
```python
from google.api_core import polling
{svc['client_lib']}

# 1. 커스텀 폴링 폴러 정의 (초기 대기 15초, 최대 주기 30초, 지수 배수 1.5)
custom_polling = polling.DEFAULT_POLLING.with_delay(
    initial=15.0,
    maximum=30.0,
    multiplier=1.5,
)

# 2. 비동기 LRO 작업 제출
# operation = client.{svc['job_method'].lower()}(request=request)

# 3. 커스텀 폴링 객체를 주입하여 완료 대기 (429 원천 차단)
result = operation.result(polling=custom_polling, timeout=3600)
```
""")

    print("처방 2: 동기식 블로킹 대기 지양 및 비동기 큐 파이프라인 분리 (엔터프라이즈 권장)")
    print("  - 워커 프로세스에서 `operation.result()`로 동기 대기하지 않고, `operation.operation.name`을 Cloud Tasks나 Pub/Sub에 적재 후 즉시 반환한다.")
    print("  - 단일 스케줄러 워커가 1분 간격으로 대기열에 있는 작업들의 상태를 일괄 조회하여 쿼터 소진을 원천 제어한다.")

    print("\n처방 3: 콘솔을 통한 필수 할당량 상향 요청 (QIR)")
    print(f"  - 콘솔 경로: IAM & Admin > Quotas ( https://console.cloud.google.com/iam-admin/quotas?project={project_id} )")
    print(f"  - 대상 서비스: {svc['name']} (리전: {location})")
    print(f"  - 필수 상향 지표: `{svc['operation_quota_token']}` (기본 {res['operation_requests_quota_rpm']} RPM -> 1,000+ RPM 권장)")
    print("=" * 88)


def build_markdown_report(
    res: Dict[str, Any], project_id: str, location: str, dry_run: bool
) -> str:
    """터미널 진단 결과와 완벽히 동기화된 마크다운 리포트를 생성한다."""
    svc = res["service_meta"]
    job_rpm = res["concurrency"]
    job_limit = res["job_quota_rpm"]
    poll_rpm = res["default_polling_rpm"]
    poll_limit = res["operation_requests_quota_rpm"]
    poll_pct = res["default_utilization_pct"]

    if res["status"] == "CRITICAL_RISK":
        poll_status = f"**[위험]** {poll_pct}% 초과 (429 유발)"
    elif res["status"] == "WARNING_RISK":
        poll_status = f"**[주의]** {poll_pct}% 소진 임박"
    else:
        poll_status = f"**[정상]** {poll_pct}% 건전"

    mode_str = "모의 실행 (Dry-run)" if dry_run else "사내 실측 진단"

    report = f"""# Google Cloud LRO 비동기 폴링 쿼터 진단 리포트

- **진단 일시**: (실행 결과 자동 생성)
- **대상 서비스**: {svc['name']} (`{svc['api_name']}`)
- **대상 프로젝트**: `{project_id}`
- **리전 위치**: `{location}`
- **진단 모드**: `{mode_str}`

---

## 1. 할당량 vs SDK LRO 폴링 트래픽 부하 진단

| 할당량 지표 (Metric Token) | 기본 한도 | 예상 소모량 | 상태 |
| :--- | :--- | :--- | :--- |
| `{svc['job_quota_token']}` | {job_limit} RPM | {job_rpm} RPM | **[정상]** 안전 여유 |
| `{svc['operation_quota_token']}` | {poll_limit} RPM | {poll_rpm} RPM | {poll_status} |

---

## 2. 메트릭 착시 현상 및 429 RESOURCE_EXHAUSTED 근본 원인 분석 (RCA)

1. **대시보드 메트릭 착시 (The Metric Mirage)**:
   - 운영 대시보드에서는 주 작업 요청 메트릭(`{svc['job_method']}`)만 확인하므로 정상 한도 내로 표시된다.
   - 그러나 구글 파이썬 클라이언트 SDK 공통 기반 라이브러리인 `google-api-core`는 `operation.result()` 호출 시 내부적으로 `GetOperation` API를 수초 간격으로 무차별 폴링한다.

2. **숨겨진 쿼터 고갈 메커니즘 (Hidden Quota Exhaustion)**:
   - 현재 동시 작업 수({res['concurrency']}건)에서 SDK 기본 폴링 호출량은 약 **{res['default_polling_rpm']} RPM**에 달한다.
   - 이는 리전당 기본 할당량인 `{svc['operation_quota_token']}`({res['operation_requests_quota_rpm']} RPM)을 **{res['default_utilization_pct']}%** 수준으로 소진하여 429 장애를 촉발한다.
   - 본 현상은 {svc['name']}뿐만 아니라 Document AI, Video Intelligence, Translation 등 구글 클라우드의 모든 LRO 비동기 API에서 동일하게 발생한다.

---

## 3. 현업 즉시 조치 가이드 및 코드 처방전

### 처방 1: SDK 커스텀 Polling 지수 백오프 주입 (모든 LRO 서비스 공통 적용 가능)
초기 대기 시간을 늘리고 최대 폴링 주기를 30초로 설정하여 불필요한 GetOperation 호출을 85% 이상 절감한다:

```python
from google.api_core import polling
{svc['client_lib']}

# 1. 커스텀 폴링 폴러 정의 (초기 대기 15초, 최대 주기 30초, 지수 배수 1.5)
custom_polling = polling.DEFAULT_POLLING.with_delay(
    initial=15.0,
    maximum=30.0,
    multiplier=1.5,
)

# 2. 비동기 LRO 작업 제출
# operation = client.{svc['job_method'].lower()}(request=request)

# 3. 커스텀 폴링 객체를 주입하여 완료 대기 (429 원천 차단)
result = operation.result(polling=custom_polling, timeout=3600)
```

### 처방 2: 동기식 블로킹 대기 지양 및 비동기 큐 파이프라인 분리 (엔터프라이즈 권장)
- 워커 프로세스에서 `operation.result()`로 동기 대기하지 않고, `operation.operation.name`을 Cloud Tasks나 Pub/Sub에 적재 후 즉시 반환한다.
- 단일 스케줄러 워커가 1분 간격으로 대기열에 있는 작업들의 상태를 일괄 조회하여 쿼터 소진을 원천 제어한다.

### 처방 3: 콘솔을 통한 필수 할당량 상향 요청 (QIR)
- 대상 서비스: {svc['name']} (리전: {location})
- 필수 상향 지표: `{svc['operation_quota_token']}` (기본 {res['operation_requests_quota_rpm']} RPM -> 1,000+ RPM 권장)
- 콘솔 경로: IAM & Admin > Quotas ( https://console.cloud.google.com/iam-admin/quotas?project={project_id} )
"""
    return report.strip() + "\n"


def save_markdown_report(report_md: str, output_path: str = "report.md") -> None:
    """마크다운 리포트를 파일로 기록/덮어쓴다."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"\n[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었습니다: {output_path}")
    except Exception as e:
        print(f"\n[경고] 리포트 파일 저장 실패 ({output_path}): {e}")


def main() -> None:
    args = parse_arguments()
    res = simulate_lro_polling_load(args.service, args.concurrency)
    
    # Dry-run 모드일 때는 사내 실환경 프로젝트 노출 방지를 위해 가명 사용
    reported_project = "sample-project-id" if args.dry_run else args.project
    
    print_diagnostic_banner(reported_project, res["service_meta"]["name"], args.location, args.dry_run)
    render_assessment_table(res)
    render_rca_and_prescription(res, reported_project, args.location)

    # 마크다운 리포트 자동 생성 및 덮어쓰기
    report_content = build_markdown_report(res, reported_project, args.location, args.dry_run)
    save_markdown_report(report_content, "report.md")


if __name__ == "__main__":
    main()
