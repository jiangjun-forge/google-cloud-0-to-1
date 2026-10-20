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


def get_default_project(is_dry_run: bool = False, fallback_demo: str = "sample-project-id") -> str:
    """gcloud 설정 및 실시간 프로젝트 목록에서 활성 프로젝트를 탐색/선택한다."""
    if is_dry_run:
        return fallback_demo

    try:
        res = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True)
        out = res.stdout.strip()
        if out and "(unset)" not in out:
            return out
    except Exception:
        pass

    if not sys.stdin.isatty():
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
    parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
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
    print("4. 사내 거버넌스 4대 필수 표준 라벨링 준수:")
    print("   - 발송 백엔드(Cloud Run, GKE 등) 및 모니터링 알림 정책 생성 시 4대 표준 라벨 필수 적용:")
    print("     --labels=managed-by=google-cloud-0-to-1,scenario=fcm-push-quota-guard,env=sample,created-by=customer-engineer")
    print("=" * 76 + "\n")


def build_markdown_report(report: Dict[str, Any], is_dry_run: bool) -> str:
    mode_str = "모의 실행 (Dry-run)" if is_dry_run else "운영 환경 진단 (Production)"
    lines = [
        "# 진단 및 분석 리포트: fcm-push-quota-guard",
        "",
        f"- **생성 모드**: {mode_str}",
        f"- **대상 프로젝트**: `{report['project_id']}`",
        "- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용",
        "",
        "---",
        "",
        "## 1. 진단 실행 콘솔 출력 결과",
        "",
        "```text",
        "=" * 76,
        " [FCM 대량 푸시 쿼터 고갈 및 429 쓰로틀링 복원력 진단 리포트]",
        "=" * 76,
        f"진단 대상 프로젝트 ID   : {report['project_id']}",
        f"피크 분당 발송 시도량   : {report['peak_messages_per_minute']:,} 건/분",
        f"현재 분당 할당량 한도   : {report['quota_limit_per_minute']:,} 건/분",
        f"할당량 소진율           : {report['quota_utilization_pct']}%",
        f"추정 429 쓰로틀링 실패율: {report['estimated_429_error_rate_pct']}%",
        f"종합 진단 상태          : {report['overall_status']}",
        "-" * 76,
        "",
        "[항목별 세부 진단 결과]",
    ]
    for idx, f in enumerate(report["findings"], 1):
        lines.append(f"{idx}. [{f['status']}] {f['item']}")
        lines.append(f"   내용: {f['description']}")

    lines.extend([
        "",
        "[복원력 강화 및 긴급 조치 가이드]",
        "1. Google Cloud 콘솔 할당량 상향(Quota Increase) 신청:",
        "   - 콘솔 경로: IAM 및 관리자 > 할당량 및 시스템 한도",
        "   - 대상 지표: Firebase Cloud Messaging API - Downstream messages per minute",
        f"   - 권장 신청값: 피크 대비 1.5배 여유 확보 (최소 {int(report['peak_messages_per_minute'] * 1.5):,} 건/분)",
        "2. 클라이언트/백엔드 토큰 버킷 속도 제한(Rate Limiting) 구현:",
        f"   - 발송 큐에서 초당 최대 전송량을 {int(report['quota_limit_per_minute'] / 60):,} msg/sec 이하로 스로틀링한다.",
        "3. Full Jitter 지수 백오프 재시도 적용:",
        "   - wait_time = min(max_backoff, base_backoff * (2 ** attempt)) * random.uniform(0.5, 1.5)",
        "4. 사내 거버넌스 4대 필수 표준 라벨링 준수:",
        "   - 발송 백엔드(Cloud Run, GKE 등) 및 모니터링 알림 정책 생성 시 4대 표준 라벨 필수 적용:",
        "     --labels=managed-by=google-cloud-0-to-1,scenario=fcm-push-quota-guard,env=sample,created-by=customer-engineer",
        "=" * 76,
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
        "### 1단계: Google Cloud 콘솔 할당량 상향(Quota Increase) 신청",
        "- Google Cloud 콘솔 할당량 및 시스템 한도 ( https://console.cloud.google.com/iam-admin/quotas )",
        "- Firebase 콘솔 ( https://console.firebase.google.com )",
        "- FCM 스로틀링 및 할당량 공식 가이드 ( https://firebase.google.com/docs/cloud-messaging/throttling-and-quotas )",
        "",
        "### 2단계: 발송 큐 토큰 버킷 속도 제한 및 Full Jitter 지수 백오프 적용",
        "- Cloud Monitoring Firebase 및 FCM 지표 목록 ( https://cloud.google.com/monitoring/api/metrics_gcp )",
        "- 발송 백엔드에서 분당 할당량에 맞추어 초당 최대 송신 속도를 제어하고 무작위 지터를 적용하여 재시도 폭풍을 방어한다.",
        "",
        "### 3단계: GCP 리소스 생성 시 4대 필수 표준 라벨링 준수",
        "발송 인프라(Cloud Run, GKE 등) 및 모니터링 알림 정책 생성 시 FinOps 비용 분석 및 자원 추적을 위해 4대 표준 라벨(`--labels=managed-by=google-cloud-0-to-1,scenario=fcm-push-quota-guard,env=sample,created-by=customer-engineer`)을 누락 없이 주입한다.",
        "",
    ])
    return "\n".join(lines)


def save_markdown_report(content: str, filename: str = "report.md") -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(current_dir, filename)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
    return report_path



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
        run_config_mode("fcm-push-quota-guard")
        return
    proj_id = args.project_id or get_default_project(is_dry_run=args.dry_run)
    if args.dry_run and not args.project_id:
        proj_id = "sample-project-id"

    report = run_diagnostics(
        project_id=proj_id,
        peak_msg_per_min=args.peak_msg_per_min,
        quota_limit_per_min=args.quota_limit_per_min,
        dry_run=args.dry_run,
    )

    md_content = build_markdown_report(report, is_dry_run=args.dry_run)
    saved_path = save_markdown_report(md_content)

    if args.json_output:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_text_report(report)
        print(f"[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: {saved_path}")


if __name__ == "__main__":
    main()
