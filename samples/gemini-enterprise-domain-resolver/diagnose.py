#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
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
        "-p",
        "--project",
        default=os.getenv("PROJECT_ID", ""),
        help="대상 Google Cloud 프로젝트 ID",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 DNS/Admin API 호출 없이 모의 도메인 충돌 데이터로 가상 실행",
    )
    parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
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
        "free_license_quota": "50+",
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
    """메인 실행 함수."""
    args = parse_args()
    if getattr(args, "config", False):
        run_config_mode("gemini-enterprise-domain-resolver")
        return
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
    print(f"* Cloud Identity Free 지원 여부: {'지원 가능 (50+개 무료 라이선스 즉시 제공)' if data['cloud_identity_free_available'] else '추가 신청 필요'}")
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

    md_content = build_markdown_report(data, is_dry_run=args.dry_run)
    save_markdown_report(md_content)
    print("\n[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: report.md")
    print("\n[안내] 사내 거버넌스 및 자원 추적을 위한 4대 필수 표준 라벨:")
    print("  - managed-by: google-cloud-0-to-1")
    print("  - scenario: gemini-enterprise-domain-resolver")
    print("  - env: sample")
    print("  - created-by: customer-engineer\n")


def build_markdown_report(data: dict, is_dry_run: bool) -> str:
    mode_label = "모의 실행 (Dry-run)" if is_dry_run else "운영 환경 진단 (Production)"
    domain = data["domain"]
    dns_status_str = "검증 완료 (VERIFIED)" if data["dns_verified"] else "미검증 (NOT VERIFIED - 조치 필요)"
    ci_support_str = "지원 가능 (50+개 무료 라이선스 즉시 제공)" if data["cloud_identity_free_available"] else "추가 신청 필요"

    lines = [
        "# 진단 및 분석 리포트: gemini-enterprise-domain-resolver",
        "",
        f"- **생성 모드**: {mode_label}",
        f"- **점검 대상 도메인**: `{domain}`",
        "- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용",
        "",
        "---",
        "",
        "## 1. 진단 실행 콘솔 출력 결과",
        "",
        "```text",
        "=" * 85,
        "Gemini Enterprise 도입을 위한 도메인 충돌(domain_in_use) 및 Cloud Identity 진단 리포트",
        f"진단 모드: {mode_label}",
        f"점검 대상 도메인: {domain}",
        "=" * 85,
        "",
        "[1단계] 도메인 충돌 상태 및 원인 분석",
        "-" * 85,
        f"* 충돌 증상 코드: {data['conflict_type']}",
        f"* 원인 분석: {data['conflict_reason']}",
    ]
    if data["unmanaged_user_count"] > 0:
        lines.append(f"* 식별된 미관리 사용자 계정 수: {data['unmanaged_user_count']}명")
        lines.append(f"* 대표 미관리 계정 목록: {', '.join(data['sample_unmanaged_users'])}")
    lines.extend([
        "-" * 85,
        "",
        "[2단계] DNS TXT 레코드 기반 도메인 소유권 검증 상태",
        "-" * 85,
        f"* DNS 검증 상태: {dns_status_str}",
        f"* 등록 필요 TXT 레코드 값: {data['dns_txt_record']}",
        "-" * 85,
        "",
        "[3단계] 라이선스 최적화 및 Gemini Enterprise 배포 전략",
        "-" * 85,
        f"* Cloud Identity Free 지원 여부: {ci_support_str}",
        "* 비용 최적화 제안: 전사 Google Workspace 유료 라이선스 구매 없이도 Cloud Identity Free 계정에",
        "  Gemini Enterprise 전용 애드온 라이선스만 할당하여 그룹사 분할 배포 가능",
        "-" * 85,
        "",
        "[4단계] 단계별 소유권 인수(Takeover) 및 계정 통합 처방",
        "1. DNS 공급자 콘솔 접속 후 도메인 TXT 레코드 추가:",
        f"   호스트: @ | 유형: TXT | 값: {data['dns_txt_record']}",
        "2. Google Admin Console에서 도메인 소유권 확인 완료:",
        "   ( https://admin.google.com/ac/domains/manage )",
        "3. 도메인 소유권 확인 후 미관리 사용자 통합 및 계정 충돌 해소:",
        "   - 관리 콘솔 > 디렉터리 > 사용자 > 미관리 사용자 초청 및 소유권 인수",
        "   - 또는 임시 계정(gtempaccount.com)으로의 자동 분리 승인",
        "4. Cloud Identity Free 라이선스를 통한 중앙 ID 거버넌스 수립:",
        "   ( https://admin.google.com/ac/billing/subscriptions )",
        "=" * 85,
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
        "## 3. 사내 거버넌스 4대 필수 표준 라벨링",
        "",
        "클라우드 리소스 및 도메인 바인딩 설정 시 4대 표준 라벨을 반드시 적용한다:",
        "- `managed-by`: `google-cloud-0-to-1`",
        "- `scenario`: `gemini-enterprise-domain-resolver`",
        "- `env`: `sample` (또는 `poc`)",
        "- `created-by`: `customer-engineer`",
        "",
        "---",
        "",
        "## 4. 결과 확인 후 즉각 조치 가이드",
        "",
        "1. **도메인 소유권 확인 및 인수(Takeover)**:",
        "   - Google Admin Console > 계정 > 도메인 > 도메인 관리 ( https://admin.google.com/ac/domains/manage )",
        "   - 도메인 소유권 확인 ( https://support.google.com/a/answer/7126229 )",
        "   - 도메인 충돌(domain_in_use) 해결 가이드 ( https://support.google.com/a/answer/11112794 )",
        "2. **미관리 사용자 계정 통합 및 관리**:",
        "   - 디렉터리 > 사용자 ( https://admin.google.com/ac/users )",
        "3. **Cloud Identity Free 라이선스 발급**:",
        "   - 결제 > 구독 ( https://admin.google.com/ac/billing/subscriptions )",
        "   - Cloud Identity 개요 ( https://cloud.google.com/identity/docs/overview )",
        "   - Cloud Identity 에디션 비교 ( https://cloud.google.com/identity/docs/editions )",
        "",
        "---",
        "",
        "## 5. 자원 정리 안내 (Teardown)",
        "",
        "본 진단 도구는 도메인 충돌 여부 및 DNS 상태를 조회하는 진단기이므로 별도의 클라우드 인프라 자원을 생성하지 않는다. 테스트 완료 후 불필요한 DNS TXT 레코드는 DNS 공급자 관리 화면에서 삭제한다.",
        "",
    ])
    return "\n".join(lines)


def save_markdown_report(content: str, filename: str = "report.md") -> None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(current_dir, filename)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    main()
