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

"""Gemini Enterprise 도입을 위한 도메인 충돌(domain_in_use) 및 Cloud Identity 진단 도구."""

import argparse
import json
import os
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    """명령줄 인자를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="미관리 사용자 도메인 충돌(domain_in_use) 및 Cloud Identity 소유권 전환 진단기"
    )
    parser.add_argument(
        "-d",
        "--domain",
        default=os.getenv("TARGET_DOMAIN") or "example.com",
        help="점검 대상 기업 도메인명 (기본값: example.com)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 DNS/Admin API 호출 없이 모의 도메인 충돌 데이터로 가상 실행",
    )
    return parser.parse_args()


def get_mock_domain_status(domain: str) -> dict:
    """가상 실행용 모의 도메인 충돌 상태를 반환한다."""
    return {
        "domain": domain,
        "conflict_type": "domain_in_use",
        "conflict_reason": "임직원 개별 가입 구글 서비스(Essentials Starter 등)로 인한 비관리(Unmanaged) 테넌트 선점",
        "unmanaged_user_count": 8,
        "sample_unmanaged_users": [
            f"user1@{domain}",
            f"marketing-lead@{domain}",
            f"dev-ops@{domain}",
            f"finance-mgr@{domain}",
        ],
        "dns_txt_record": "google-site-verification=AbCdEf1234567890XyZ_mock_token",
        "dns_verified": False,
        "cloud_identity_free_available": True,
        "free_license_quota": 50,
    }


def inspect_live_dns(domain: str) -> tuple[bool, str]:
    """실제 DNS TXT 레코드 조회를 통해 구글 소유권 확인 토큰을 탐지한다."""
    try:
        res = subprocess.run(
            ["dig", "+short", "TXT", domain],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = res.stdout.strip().splitlines()
        for line in lines:
            cleaned = line.replace('"', '').strip()
            if "google-site-verification=" in cleaned:
                return True, cleaned
    except Exception:
        pass
    return False, "미확인"


def main() -> None:
    """메인 실행 함수."""
    args = parse_args()
    domain = args.domain

    mode_label = "가상 실행 (Dry-run)" if args.dry_run else "실제 환경 (Live)"
    print("=" * 85)
    print("Gemini Enterprise 도입을 위한 도메인 충돌(domain_in_use) 및 Cloud Identity 진단 리포트")
    print(f"진단 모드: {mode_label}")
    print(f"점검 대상 도메인: {domain}")
    print("=" * 85)

    if args.dry_run:
        data = get_mock_domain_status(domain)
    else:
        verified, token = inspect_live_dns(domain)
        data = {
            "domain": domain,
            "conflict_type": "미확인" if verified else "domain_in_use (추정)",
            "conflict_reason": "비관리 사용자 테넌트 점유 가능성",
            "unmanaged_user_count": 0,
            "sample_unmanaged_users": [],
            "dns_txt_record": token,
            "dns_verified": verified,
            "cloud_identity_free_available": True,
            "free_license_quota": 50,
        }

    # 1. 도메인 충돌 진단 결과
    print("\n[1단계] 도메인 충돌 상태 및 원인 분석")
    print("-" * 85)
    print(f"* 충돌 증상 코드: {data['conflict_type']}")
    print(f"* 원인 분석: {data['conflict_reason']}")
    if data["unmanaged_user_count"] > 0:
        print(f"* 식별된 미관리 사용자 계정 수: {data['unmanaged_user_count']}명")
        print(f"* 대표 미관리 계정 목록: {', '.join(data['sample_unmanaged_users'])}")
    print("-" * 85)

    # 2. 도메인 소유권 DNS 검증 현황
    print("\n[2단계] DNS TXT 레코드 기반 도메인 소유권 검증 상태")
    print("-" * 85)
    dns_status_str = "검증 완료 (VERIFIED)" if data["dns_verified"] else "미검증 (NOT VERIFIED - 조치 필요)"
    print(f"* DNS 검증 상태: {dns_status_str}")
    print(f"* 등록 필요 TXT 레코드 값: {data['dns_txt_record']}")
    print("-" * 85)

    # 3. 라이선스 최적화 방안 (Cloud Identity Free)
    print("\n[3단계] 라이선스 최적화 및 Gemini Enterprise 배포 전략")
    print("-" * 85)
    print(f"* Cloud Identity Free 지원 여부: {'지원 가능 (50개 무료 라이선스 즉시 제공)' if data['cloud_identity_free_available'] else '추가 신청 필요'}")
    print("* 비용 최적화 제안: 전사 Google Workspace 유료 라이선스 구매 없이도 Cloud Identity Free 계정에")
    print("  Gemini Enterprise 전용 애드온 라이선스만 할당하여 그룹사 분할 배포 가능")
    print("-" * 85)

    # 4. 단계별 해결 조치 가이드
    print("\n[4단계] 단계별 소유권 인수(Takeover) 및 계정 통합 처방")
    print(f"1. DNS 공급자 콘솔 접속 후 도메인 TXT 레코드 추가:")
    print(f"   호스트: @ | 유형: TXT | 값: {data['dns_txt_record']}")
    print(f"2. Google Admin Console에서 도메인 소유권 확인 완료:")
    print(f"   ( https://admin.google.com/ac/domains/manage )")
    print(f"3. 도메인 소유권 확인 후 미관리 사용자 통합 및 계정 충돌 해소:")
    print(f"   - 관리 콘솔 > 디렉터리 > 사용자 > 미관리 사용자 초청 및 소유권 인수")
    print(f"   - 또는 임시 계정(gtempaccount.com)으로의 자동 분리 승인")
    print(f"4. Cloud Identity Free 라이선스를 통한 중앙 ID 거버넌스 수립:")
    print(f"   ( https://admin.google.com/ac/billing/subscriptions )")
    print("=" * 85)


if __name__ == "__main__":
    main()
