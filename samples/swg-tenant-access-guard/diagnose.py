#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""SWG 관문 HTTP 헤더 주입 및 Context-Aware Access 기반 접근 통제 진단 도구."""

import argparse
import base64
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
        description="사내 관문 SWG 헤더 주입 및 Context-Aware Access 단말기 인가 정합성을 진단한다."
    )
    parser.add_argument(
        "--org-id",
        dest="org_id",
        default=os.getenv("TARGET_ORG_ID", "123456789012"),
        help="Google Cloud 조직 ID (기본값: TARGET_ORG_ID 환경 변수 또는 123456789012)",
    )
    parser.add_argument(
        "--domain",
        dest="domain",
        default=os.getenv("ALLOWED_DOMAIN", "example-corp.com"),
        help="사내 승인 허용 도메인 (기본값: ALLOWED_DOMAIN 환경 변수 또는 example-corp.com)",
    )
    parser.add_argument(
        "--group-email",
        dest="group_email",
        default=os.getenv("AUTHORIZED_GROUP_EMAIL", "gcp-authorized-users@example-corp.com"),
        help="CAA 인가 관리자 보안 그룹 이메일",
    )
    parser.add_argument(
        "--proxy-url",
        dest="proxy_url",
        default=os.getenv("SWG_PROXY_URL", "https://swg-proxy.internal.example-corp.com:8080"),
        help="사내 관문 SWG 프록시 엔드포인트 URL",
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
    print("1. 개인 계정 및 외부 비인가 도메인 로그인 원천 차단:")
    print(f"   - HTTP 요청 헤더: X-GoogApps-Allowed-Domains: {report['allowed_domain']}")
    print("2. 사내 승인 계정의 외부 타사 GCP 조직 우회 접근 원천 차단 (Tenant Restriction):")
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


def main() -> None:
    args = parse_arguments()
    report = run_diagnostics(
        org_id=args.org_id,
        domain=args.domain,
        group_email=args.group_email,
        proxy_url=args.proxy_url,
        dry_run=args.dry_run,
    )

    if args.json_output:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_text_report(report)


if __name__ == "__main__":
    main()
