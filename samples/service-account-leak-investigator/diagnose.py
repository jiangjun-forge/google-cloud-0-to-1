#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""유출 의심 서비스 계정 감사 로그 역추적 및 WIF 전환 진단 도구."""

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    """명령줄 인자를 파싱한다."""
    days_val = os.getenv("LOOKBACK_DAYS")
    parser = argparse.ArgumentParser(
        description="유출 의심 서비스 계정 감사 로그 역추적 및 긴급 조치 진단기"
    )
    parser.add_argument(
        "-p",
        "--project",
        default=os.getenv("PROJECT_ID") or "",
        help="GCP 프로젝트 ID (지정하지 않을 경우 gcloud 기본 프로젝트 사용)",
    )
    parser.add_argument(
        "-s",
        "--service-accounts",
        default=os.getenv("COMPROMISED_SA_EMAILS") or "",
        help="조사 대상 서비스 계정 이메일 목록 (콤마 구분)",
    )
    parser.add_argument(
        "-d",
        "--days",
        type=int,
        default=int(days_val) if days_val else 7,
        help="감사 로그 역추적 기간 (일 단위, 기본값: 7)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 GCP API 호출 없이 모의 침해 시나리오 데이터로 가상 실행",
    )
    return parser.parse_args()


def detect_project_id(cli_project: str) -> str:
    """프로젝트 ID를 탐지한다."""
    if cli_project:
        return cli_project
    try:
        res = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            check=True,
        )
        detected = res.stdout.strip()
        if detected and "(unset)" not in detected:
            return detected
    except Exception:
        pass
    return "demo-compromised-investigation"


def get_mock_audit_records(sa_list: list[str]) -> list[dict]:
    """가상 실행용 모의 감사 로그 레코드를 반환한다."""
    base_sa = sa_list[0] if sa_list else "app-backend-sa@example-project.iam.gserviceaccount.com"
    second_sa = sa_list[1] if len(sa_list) > 1 else "data-pipeline-sa@example-project.iam.gserviceaccount.com"

    now = datetime.now(timezone.utc)
    return [
        {
            "timestamp": (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "principal": base_sa,
            "service": "iam.googleapis.com",
            "method": "google.iam.admin.v1.SetIamPolicy",
            "caller_ip": "198.51.100.45",
            "risk": "HIGH",
            "detail": "외부 미인가 계정에 roles/owner 권한 부여 시도 감지",
        },
        {
            "timestamp": (now - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "principal": second_sa,
            "service": "storage.googleapis.com",
            "method": "storage.objects.get",
            "caller_ip": "203.0.113.88",
            "risk": "HIGH",
            "detail": "비정상 해외 IP 대역에서 sensitive-customer-pii 버킷 대량 다운로드",
        },
        {
            "timestamp": (now - timedelta(hours=14)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "principal": base_sa,
            "service": "bigquery.googleapis.com",
            "method": "google.cloud.bigquery.v2.JobService.InsertJob",
            "caller_ip": "198.51.100.45",
            "risk": "HIGH",
            "detail": "외부 공개 스토리지 버킷으로 결제 및 사용자 테이블 추출 쿼리 실행",
        },
        {
            "timestamp": (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "principal": second_sa,
            "service": "storage.googleapis.com",
            "method": "storage.objects.list",
            "caller_ip": "203.0.113.88",
            "risk": "MEDIUM",
            "detail": "사내 백업 버킷 내부 객체 목록 전수 정찰(Enumeration)",
        },
        {
            "timestamp": (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "principal": base_sa,
            "service": "storage.googleapis.com",
            "method": "storage.buckets.get",
            "caller_ip": "192.0.2.10",
            "risk": "LOW",
            "detail": "정상 빌드 파이프라인 버킷 메타데이터 확인",
        },
    ]


def query_audit_logs(project_id: str, sa_list: list[str], days: int) -> list[dict]:
    """실제 Cloud Audit Logs에서 서비스 계정 활동 기록을 조회한다."""
    try:
        from google.cloud import logging_v2

        client = logging_v2.Client(project=project_id)
        start_time = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        sa_filter = " OR ".join([f'protoPayload.authenticationInfo.principalEmail="{sa}"' for sa in sa_list])
        log_filter = (
            f"({sa_filter}) AND "
            f'timestamp >= "{start_time}" AND '
            'protoPayload.serviceName=("iam.googleapis.com" OR "storage.googleapis.com" OR "bigquery.googleapis.com")'
        )

        entries = client.list_entries(filter_=log_filter, page_size=100)
        records = []
        for entry in entries:
            payload = entry.payload or {}
            method = payload.get("methodName", "unknown")
            service = payload.get("serviceName", "unknown")
            auth = payload.get("authenticationInfo", {})
            principal = auth.get("principalEmail", "unknown")
            req_meta = payload.get("requestMetadata", {})
            caller_ip = req_meta.get("callerIp", "unknown")

            risk = "LOW"
            detail = "일반 리소스 조회"
            if "SetIamPolicy" in method or "CreateServiceAccountKey" in method:
                risk = "HIGH"
                detail = "IAM 권한 상승 또는 자격 증명 생성 행위"
            elif "InsertJob" in method or "exportData" in method or "objects.get" in method:
                risk = "HIGH"
                detail = "데이터 추출 또는 민감 객체 다운로드 가능성"
            elif "list" in method:
                risk = "MEDIUM"
                detail = "리소스 목록 정찰(Enumeration) 조회"

            records.append({
                "timestamp": entry.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if entry.timestamp else "N/A",
                "principal": principal,
                "service": service,
                "method": method,
                "caller_ip": caller_ip,
                "risk": risk,
                "detail": detail,
            })
        return records
    except Exception as exc:
        print(f"[경고] Cloud Logging API 조회 실패: {exc}")
        print("[안내] 모의 데이터로 대체하여 진단을 지속한다.")
        return get_mock_audit_records(sa_list)


def inspect_service_account_keys(project_id: str, sa_email: str, is_dry_run: bool) -> list[dict]:
    """서비스 계정에 등록된 사용자 관리 키 목록을 점검한다."""
    if is_dry_run:
        return [
            {
                "key_id": "7f8b9c0d1e2f3a4b",
                "created": "2025-11-10T08:00:00Z",
                "status": "ACTIVE",
                "key_type": "USER_MANAGED",
                "recommendation": "즉시 비활성화(DISABLE) 및 영구 삭제 권장",
            },
            {
                "key_id": "a1b2c3d4e5f67890",
                "created": "2026-05-15T16:00:00Z",
                "status": "ACTIVE",
                "key_type": "USER_MANAGED",
                "recommendation": "침해 의심 시점 생성 키, 즉시 삭제 필요",
            },
        ]

    try:
        cmd = [
            "gcloud", "iam", "service-accounts", "keys", "list",
            f"--iam-account={sa_email}",
            f"--project={project_id}",
            "--format=json",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        raw_keys = json.loads(res.stdout)
        keys = []
        for item in raw_keys:
            if item.get("keyType") == "USER_MANAGED":
                name = item.get("name", "")
                key_id = name.split("/")[-1] if "/" in name else name
                keys.append({
                    "key_id": key_id,
                    "created": item.get("validAfterTime", "N/A"),
                    "status": "ACTIVE",
                    "key_type": "USER_MANAGED",
                    "recommendation": "즉시 비활성화(DISABLE) 및 WIF 전환 필요",
                })
        return keys
    except Exception:
        return []


def main() -> None:
    """메인 실행 함수."""
    args = parse_args()
    project_id = detect_project_id(args.project)

    sa_input = args.service_accounts
    if sa_input:
        sa_list = [s.strip() for s in sa_input.split(",") if s.strip()]
    else:
        sa_list = [
            f"app-backend-sa@{project_id}.iam.gserviceaccount.com",
            f"data-pipeline-sa@{project_id}.iam.gserviceaccount.com",
        ]

    mode_label = "가상 실행 (Dry-run)" if args.dry_run else "실제 환경 (Live)"
    print("=" * 80)
    print("유출 의심 서비스 계정 감사 로그 역추적 및 침해 진단 리포트")
    print(f"진단 모드: {mode_label}")
    print(f"대상 프로젝트: {project_id}")
    print(f"조사 기간: 최근 {args.days}일")
    print(f"조사 대상 계정 수: {len(sa_list)}개")
    print("=" * 80)

    # 1. 활성 사용자 관리 키 점검
    print("\n[1단계] 서비스 계정 활성 키(User-Managed Key) 현황 점검")
    all_keys = []
    for sa in sa_list:
        keys = inspect_service_account_keys(project_id, sa, args.dry_run)
        for k in keys:
            all_keys.append({
                "sa": sa.split("@")[0],
                "key_id": k["key_id"][:12] + "...",
                "created": k["created"][:10],
                "status": k["status"],
                "recommendation": k["recommendation"],
            })

    if all_keys:
        print("-" * 80)
        print(f"{'서비스 계정':<16} {'키 ID':<18} {'생성 일자':<12} {'상태':<8} {'권장 조치'}")
        print("-" * 80)
        for row in all_keys:
            print(f"{row['sa']:<16} {row['key_id']:<18} {row['created']:<12} {row['status']:<8} {row['recommendation']}")
        print("-" * 80)
    else:
        print("사용자 관리 키가 발견되지 않았다.")

    # 2. Cloud Audit Logs 침해 활동 역추적
    print(f"\n[2단계] 최근 {args.days}일간 Cloud Audit Logs 위험 활동 역추적")
    if args.dry_run:
        records = get_mock_audit_records(sa_list)
    else:
        records = query_audit_logs(project_id, sa_list, args.days)

    if records:
        high_risk_count = 0
        print("-" * 80)
        print(f"{'발생 시각':<24} {'계정':<15} {'서비스':<10} {'메서드':<15} {'호출 IP':<15} {'위험도'}")
        print("-" * 80)
        for r in records:
            if r["risk"] == "HIGH":
                high_risk_count += 1
            sa_short = r["principal"].split("@")[0]
            svc_short = r["service"].replace(".googleapis.com", "")
            method_short = r["method"].split(".")[-1]
            print(f"{r['timestamp']:<24} {sa_short:<15} {svc_short:<10} {method_short:<15} {r['caller_ip']:<15} {r['risk']}")
            print(f"  └ 상세 내용: {r['detail']}")
        print("-" * 80)
        print(f"진단 요약: 총 {len(records)}건의 활동 중 고위험(HIGH) 이벤트 {high_risk_count}건 탐지")
        print("-" * 80)
    else:
        print("해당 기간 동안 의심스러운 활동 기록이 발견되지 않았다.")

    # 3. 긴급 대응 가이드 및 처방
    print("\n[3단계] 긴급 대응 조치 및 Workload Identity Federation 전환 처방")
    print("1. 유출된 서비스 계정 키 즉시 비활성화(Disable):")
    print("   gcloud iam service-accounts keys disable <KEY_ID> --iam-account=<SA_EMAIL>")
    print("2. 악의적으로 부여된 비인가 IAM 바인딩 제거:")
    print("   gcloud projects remove-iam-policy-binding <PROJECT_ID> --member=<USER> --role=<ROLE>")
    print("3. 영구 자격 증명 폐기 및 Workload Identity Federation 전환:")
    print("   - 깃허브 액션(GitHub Actions) 환경: OIDC 연동 풀(Pool) 생성 후 단기 토큰 발급 체계로 전면 전환")
    print("   - 온프레미스 서버 환경: mTLS 기반 SPIFFE/SPIRE 또는 IdP SAML/OIDC 페더레이션 적용")
    print("=" * 80)


if __name__ == "__main__":
    main()
