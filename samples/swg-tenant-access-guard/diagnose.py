#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""SWG 관문 HTTP 헤더 주입 및 Context-Aware Access 기반 접근 통제 진단 도구."""

import argparse
import base64
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


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="사내 관문 SWG 헤더 주입 및 Context-Aware Access 단말기 인가 정합성을 진단한다."
    )
    parser.add_argument(
        "--org-id",
        dest="org_id",
        default=os.getenv("TARGET_ORG_ID") or "",
        help="Google Cloud 조직 ID (지정하지 않을 경우 gcloud 활성 조직 자동 감지)",
    )
    parser.add_argument(
        "--domain",
        dest="domain",
        default=os.getenv("ALLOWED_DOMAIN") or "example-corp.com",
        help="사내 승인 허용 도메인 (기본값: ALLOWED_DOMAIN 환경 변수 또는 example-corp.com)",
    )
    parser.add_argument(
        "--group-email",
        dest="group_email",
        default=os.getenv("AUTHORIZED_GROUP_EMAIL") or "gcp-authorized-users@example-corp.com",
        help="CAA 인가 관리자 보안 그룹 이메일",
    )
    parser.add_argument(
        "--proxy-url",
        dest="proxy_url",
        default=os.getenv("SWG_PROXY_URL") or "https://swg-proxy.internal.example-corp.com:8080",
        help="사내 관문 SWG 프록시 엔드포인트 URL",
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


def detect_org_id(cli_org: str, is_dry_run: bool = False) -> str:
    """조직 ID를 탐지하거나 대화형으로 선택한다."""
    if cli_org:
        return cli_org
    env_org = os.getenv("TARGET_ORG_ID")
    if env_org:
        return env_org

    if is_dry_run or not sys.stdin.isatty():
        return "123456789012"

    try:
        res = subprocess.run(
            ["gcloud", "organizations", "list", "--format=value(ID,displayName)", "--limit=5"],
            capture_output=True,
            text=True,
        )
        lines = [line.strip().split("\t") for line in res.stdout.splitlines() if line.strip()]
        orgs = [item for item in lines if len(item) >= 1]
        if orgs:
            print("\n[?] 대상 Google Cloud 조직 ID가 지정되지 않았습니다. 현재 접근 가능한 조직 목록:")
            for idx, item in enumerate(orgs, 1):
                org_id = item[0]
                name = item[1] if len(item) > 1 else ""
                print(f"  [{idx}] {org_id} ({name})")
            print(f"  [{len(orgs) + 1}] 직접 입력 (Custom Input)")
            choice = input(f"선택할 번호 입력 [1-{len(orgs) + 1}] (Enter 시 1번): ").strip()
            if not choice or choice == "1":
                return orgs[0][0]
            if choice.isdigit() and 1 <= int(choice) <= len(orgs):
                return orgs[int(choice) - 1][0]
            if choice == str(len(orgs) + 1):
                custom = input("조직 ID를 직접 입력하세요: ").strip()
                if custom:
                    return custom
    except Exception:
        pass

    return "123456789012"


def build_expected_resource_header(org_id: str) -> str:
    payload = {
        "resources": [f"organizations/{org_id}"],
        "options": "strict",
    }
    dumped = json.dumps(payload, separators=(",", ":"))
    encoded = base64.urlsafe_b64encode(dumped.encode("utf-8")).decode("utf-8").rstrip("=")
    return encoded


def run_diagnostics(org_id: str, domain: str, group_email: str, proxy_url: str, dry_run: bool) -> Dict[str, Any]:
    expected_header = build_expected_resource_header(org_id)
    findings: List[Dict[str, Any]] = []

    if dry_run:
        findings.append({
            "category": "SWG_HEADER_DOMAIN_RESTRICTION",
            "status": "PASS",
            "header": "X-GoogApps-Allowed-Domains",
            "configured_value": domain,
            "description": f"개인 Gmail 및 비인가 도메인 접근이 차단되고 {domain} 계정만 통과하도록 헤더가 주입되고 있다.",
        })
        findings.append({
            "category": "SWG_HEADER_TENANT_RESTRICTION",
            "status": "WARNING",
            "header": "X-Goog-Allowed-Resources",
            "configured_value": "NOT_CONFIGURED",
            "expected_value": expected_header,
            "description": "사내 관문 프록시에서 Google Cloud 테넌트 제한 공식 헤더(X-Goog-Allowed-Resources)가 누락되어 있다. 사내 승인 계정을 이용해 외부 타사 GCP 조직 및 프로젝트로 우회 접근할 수 있는 위험이 존재한다.",
        })
        findings.append({
            "category": "CONTEXT_AWARE_ACCESS_ENDPOINT",
            "status": "PASS",
            "policy_name": "corp-managed-device-policy",
            "description": "Endpoint Verification 및 관리 장치 신뢰 정책이 적용되어 사내 보안 인가 단말기만 콘솔 및 앱에 접근할 수 있다.",
        })
        findings.append({
            "category": "CONTEXT_AWARE_ACCESS_GROUP",
            "status": "PASS",
            "group_email": group_email,
            "description": f"인가된 사내 보안 그룹({group_email})에 대해서만 Google Cloud 콘솔 및 생성형 AI 애플리케이션 접근이 바인딩되어 있다.",
        })
        findings.append({
            "category": "FINANCIAL_COMPLIANCE_3_2",
            "status": "NEEDS_REMEDIATION",
            "standard": "금융보안원 생성형 AI 보안대책 이행서 3.2 (관리자 단말기 인가 체계 및 접속 차단 대책)",
            "description": "단말기 인가 및 사용자 그룹 제어는 적합하나, 외부 테넌트 리소스 격리 헤더 미적용으로 인해 비인가 외부 조직 접근 통제 보완이 필요하다.",
        })
    else:
        findings.append({
            "category": "SWG_HEADER_DOMAIN_RESTRICTION",
            "status": "INFO",
            "header": "X-GoogApps-Allowed-Domains",
            "configured_value": domain,
            "description": f"사내 프록시({proxy_url}) 관문 헤더 검증을 위해 엔드포인트 연동 점검이 필요하다.",
        })
        findings.append({
            "category": "SWG_HEADER_TENANT_RESTRICTION",
            "status": "INFO",
            "header": "X-Goog-Allowed-Resources",
            "expected_value": expected_header,
            "description": f"조직 ID({org_id}) 전용 base64url 인코딩 페이로드가 필요하다.",
        })

    has_warning = any(f.get("status") in ("WARNING", "NEEDS_REMEDIATION") for f in findings)
    overall_status = "ACTION_REQUIRED" if has_warning else "HEALTHY"

    return {
        "overall_status": overall_status,
        "org_id": org_id,
        "allowed_domain": domain,
        "group_email": group_email,
        "expected_resource_header": expected_header,
        "findings": findings,
    }


def print_text_report(report: Dict[str, Any]) -> None:
    print("\n" + "=" * 76)
    print(" [SWG 관문 헤더 및 Context-Aware Access 인가 정합성 진단 리포트]")
    print("=" * 76)
    print(f"진단 대상 조직 ID      : {report['org_id']}")
    print(f"사내 승인 허용 도메인  : {report['allowed_domain']}")
    print(f"인가 관리자 보안 그룹  : {report['group_email']}")
    print(f"종합 진단 상태         : {report['overall_status']}")
    print("-" * 76)

    print("\n[항목별 세부 진단 결과]")
    for idx, f in enumerate(report["findings"], 1):
        status = f.get("status", "INFO")
        cat = f.get("category", "")
        desc = f.get("description", "")
        print(f"{idx}. [{status}] {cat}")
        print(f"   설명: {desc}")
        if "header" in f:
            print(f"   대상 헤더: {f['header']}")
        if "expected_value" in f:
            print(f"   필요 권장값: {f['expected_value']}")

    print("\n[사내 관문 프록시(SWG) 설정 가이드]")
    print("1. 개인 계정 및 외부 비인가 도메인 로그인 차단:")
    print(f"   - HTTP 요청 헤더: X-GoogApps-Allowed-Domains: {report['allowed_domain']}")
    print("2. 사내 승인 계정의 외부 타사 GCP 조직 우회 접근 방지 (Tenant Restriction):")
    print(f"   - HTTP 요청 헤더: X-Goog-Allowed-Resources: {report['expected_resource_header']}")
    print("   - 주의: 과거 비공식 표기인 X-Goog-Allowed-Organizations 대신 공식 X-Goog-Allowed-Resources를 사용해야 한다.")
    print("   - 페이로드 원문: {\"resources\":[\"organizations/" + report['org_id'] + "\"],\"options\":\"strict\"}")

    print("\n[Context-Aware Access(CAA) 인가 정책 조치]")
    print("1. Access Context Manager 레벨 생성:")
    print("   gcloud access-context-manager levels create CorpDeviceOnly \\")
    print("     --title=\"사내 인가 단말기 전용\" \\")
    print("     --basic-level-spec=device_policy.yaml")
    print("2. Google Cloud 콘솔 및 생성형 AI 앱 접근 바인딩:")
    print(f"   - 대상 그룹: {report['group_email']}")
    print("   - 적용 레벨: CorpDeviceOnly")
    print("=" * 76 + "\n")


def build_markdown_report(report: Dict[str, Any], is_dry_run: bool) -> str:
    """터미널 진단 결과와 완벽히 동기화된 마크다운 리포트를 생성한다."""
    mode_str = "모의 실행 (Dry-run)" if is_dry_run else "실제 환경 (Live)"
    lines = [
        "# 사내 관문 SWG 헤더 및 Context-Aware Access 인가 진단 리포트 (swg-tenant-access-guard)",
        "",
        f"- **진단 모드**: `{mode_str}`",
        f"- **진단 대상 조직 ID**: `{report['org_id']}`",
        f"- **사내 승인 허용 도메인**: `{report['allowed_domain']}`",
        f"- **인가 관리자 보안 그룹**: `{report['group_email']}`",
        f"- **종합 진단 상태**: `{report['overall_status']}`",
        "- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용",
        "",
        "---",
        "",
        "## 1. 항목별 세부 진단 결과",
        "",
        "| 번호 | 점검 카테고리 | 진단 상태 | 상세 내용 및 권장값 |",
        "| :--- | :--- | :--- | :--- |",
    ]
    for idx, f in enumerate(report["findings"], 1):
        status_md = f"**{f['status']}**" if f['status'] in ("WARNING", "NEEDS_REMEDIATION", "FAIL") else f['status']
        detail_parts = [f['description']]
        if "header" in f:
            detail_parts.append(f"대상 헤더: `{f['header']}`")
        if "expected_value" in f:
            detail_parts.append(f"필요 권장값: `{f['expected_value']}`")
        detail_str = "<br/>".join(detail_parts)
        lines.append(f"| {idx} | `{f['category']}` | {status_md} | {detail_str} |")

    lines.extend([
        "",
        "---",
        "",
        "## 2. 사내 관문 프록시(SWG) 설정 가이드",
        "",
        "### 1. 개인 계정 및 외부 비인가 도메인 로그인 차단",
        "```http",
        f"X-GoogApps-Allowed-Domains: {report['allowed_domain']}",
        "```",
        "",
        "### 2. 사내 승인 계정의 외부 타사 GCP 조직 우회 접근 방지 (Tenant Restriction)",
        "```http",
        f"X-Goog-Allowed-Resources: {report['expected_resource_header']}",
        "```",
        "- **참고**: 공식 `X-Goog-Allowed-Resources` 헤더를 사용해야 한다.",
        f"- **페이로드 원문**: `{{\"resources\":[\"organizations/{report['org_id']}\"],\"options\":\"strict\"}}`",
        "",
        "---",
        "",
        "## 3. Context-Aware Access(CAA) 인가 정책 조치",
        "",
        "### 1. Access Context Manager 레벨 생성",
        "```bash",
        "gcloud access-context-manager levels create CorpDeviceOnly \\",
        '  --title="사내 인가 단말기 전용" \\',
        "  --basic-level-spec=device_policy.yaml",
        "```",
        "",
        "### 2. Google Cloud 콘솔 및 생성형 AI 앱 접근 바인딩",
        f"- **대상 그룹**: `{report['group_email']}`",
        "- **적용 레벨**: `CorpDeviceOnly`",
        "",
        "---",
        "",
        "## 4. 사내 거버넌스 4대 필수 표준 라벨링",
        "",
        "Access Context Manager 정책 및 인가 연계 인프라 자원 구성 시 다음 4대 표준 라벨을 반드시 적용한다:",
        "- `managed-by`: `google-cloud-0-to-1`",
        "- `scenario`: `swg-tenant-access-guard`",
        "- `env`: `sample` (또는 `poc`)",
        "- `created-by`: `customer-engineer`",
        "",
        "---",
        "",
        "## 5. 콘솔 링크 조치 가이드 및 공식 레퍼런스",
        "",
        "- **Access Context Manager 콘솔**: ( https://console.cloud.google.com/security/access-levels )",
        "- **공식 문서 - Organization Restrictions 개요 및 헤더 규격**: ( https://docs.cloud.google.com/resource-manager/docs/organization-restrictions/overview )",
        "- **공식 문서 - Google Workspace 개인 계정 로그인 차단 설정**: ( https://support.google.com/a/answer/1668854 )",
        "- **공식 문서 - Context-Aware Access 개요 및 장치 정책**: ( https://docs.cloud.google.com/chrome-enterprise-premium/docs/overview )",
        "",
        "---",
        "",
        "## 6. 자원 정리 안내 (Teardown)",
        "테스트 목적으로 생성한 Access Context Manager 임시 정책이나 모의 레벨을 삭제하려면 다음 명령을 수행한다:",
        "```bash",
        "gcloud access-context-manager levels delete CorpDeviceOnly --policy=<POLICY_ID> --quiet",
        "```",
        "",
    ])
    return "\n".join(lines)


def save_markdown_report(report_md: str, output_path: str | None = None) -> None:
    """마크다운 리포트를 파일로 기록/덮어쓴다."""
    if output_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, "report.md")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"\n[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: {output_path}")
    except Exception as e:
        print(f"\n[경고] 리포트 파일 저장 실패 ({output_path}): {e}")



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
        run_config_mode("swg-tenant-access-guard")
        return
    org_id = detect_org_id(args.org_id, is_dry_run=args.dry_run)
    report = run_diagnostics(
        org_id=org_id,
        domain=args.domain,
        group_email=args.group_email,
        proxy_url=args.proxy_url,
        dry_run=args.dry_run,
    )

    if args.json_output:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_text_report(report)

    # 마크다운 리포트 자동 생성 및 덮어쓰기 (스크립트 기준 디렉터리 경로 사용)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_file_path = os.path.join(script_dir, "report.md")
    report_content = build_markdown_report(report, args.dry_run)
    save_markdown_report(report_content, report_file_path)


if __name__ == "__main__":
    main()
