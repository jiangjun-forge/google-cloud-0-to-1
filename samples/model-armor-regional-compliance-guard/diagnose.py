#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Model Armor Regional Compliance & Capability Gap Diagnostic Tool.

대한민국 서울 리전(asia-northeast3) 환경에서 Model Armor 템플릿 구성 상태를 점검하여,
리전 미지원 필터(프롬프트 인젝션, 악성 URL, RAI)로 인한 보안 공백, 데이터 국외 이전 위험,
한국형 개인정보(Korea-specific InfoTypes) 누락 여부를 정밀 진단하고 하이브리드 가드레일 처방을 제공한다.
"""

import argparse
import json
import os
import subprocess
import sys

KOREA_REQUIRED_INFOTYPES = [
    "KOREA_RRN",
    "KOREA_PASSPORT",
    "KOREA_DRIVERS_LICENSE_NUMBER",
    "KOREA_ARN",
    "KOREA_BRN",
    "KOREA_NHI_NUMBER",
]


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
  """쉘 명령어를 실행하고 리턴 코드, 표준 출력, 표준 에러를 반환한다."""
  res = subprocess.run(cmd, capture_output=True, text=True)
  return res.returncode, res.stdout.strip(), res.stderr.strip()


def get_default_project() -> str | None:
  """환경 변수 또는 gcloud 설정에서 활성 프로젝트 ID를 조회한다."""
  env_proj = os.getenv("PROJECT_ID")
  if env_proj:
    return env_proj
  _, stdout, _ = run_cmd(["gcloud", "config", "get-value", "project"])
  if stdout and "(unset)" not in stdout:
    return stdout
  return None


def get_mock_templates() -> list[dict]:
  """가상 실행(--dry-run)을 위한 Model Armor 템플릿 샘플 목록을 반환한다."""
  return [
      {
          "name": "ma-template-seoul-finance",
          "location": "asia-northeast3",
          "compliance_boundary": "KOREA_FINANCE_STRICT",
          "sdp_enabled": True,
          "sdp_infotypes": ["EMAIL_ADDRESS", "PHONE_NUMBER", "KOREA_RRN"],
          "prompt_injection_enabled": True,
          "malicious_uri_enabled": True,
          "rai_filters_enabled": True,
          "local_guardrail_fallback": False,
      },
      {
          "name": "ma-template-global-uncompliant",
          "location": "us-central1",
          "compliance_boundary": "KOREA_FINANCE_STRICT",
          "sdp_enabled": True,
          "sdp_infotypes": KOREA_REQUIRED_INFOTYPES,
          "prompt_injection_enabled": True,
          "malicious_uri_enabled": True,
          "rai_filters_enabled": True,
          "local_guardrail_fallback": False,
      },
      {
          "name": "ma-template-hybrid-hardened",
          "location": "asia-northeast3",
          "compliance_boundary": "KOREA_FINANCE_STRICT",
          "sdp_enabled": True,
          "sdp_infotypes": KOREA_REQUIRED_INFOTYPES,
          "prompt_injection_enabled": False,
          "malicious_uri_enabled": False,
          "rai_filters_enabled": False,
          "local_guardrail_fallback": True,
      },
  ]


def evaluate_template(tpl: dict) -> dict:
  """Model Armor 템플릿의 리전 가용성 및 규제 준수 결함을 평가한다."""
  name = tpl["name"]
  location = tpl["location"]
  boundary = tpl.get("compliance_boundary", "GENERAL")
  sdp_enabled = tpl.get("sdp_enabled", False)
  infotypes = set(tpl.get("sdp_infotypes", []))
  pi_enabled = tpl.get("prompt_injection_enabled", False)
  uri_enabled = tpl.get("malicious_uri_enabled", False)
  rai_enabled = tpl.get("rai_filters_enabled", False)
  local_fallback = tpl.get("local_guardrail_fallback", False)

  issues = []
  remediations = []
  severity = "HEALTHY"

  # 1. 데이터 상주(Data Boundary) 규제 하에서 해외 리전 템플릿 사용 검사
  if boundary == "KOREA_FINANCE_STRICT" and location != "asia-northeast3":
    severity = "CRITICAL"
    issues.append(
        f"금융 규제 준수 대상 워크로드임에도 Model Armor 템플릿이 해외 리전({location})에 배포되어 "
        "입력 프롬프트 및 개인정보의 국외 이전(Data Boundary 위반) 위험 발생"
    )
    remediations.append(
        "Model Armor 템플릿을 서울 리전(asia-northeast3) 엔드포인트로 이전 재배포한다."
    )

  # 2. 서울 리전 내 미지원 필터 활성화에 따른 보안 공백 검사
  if location == "asia-northeast3":
    unsupported_active = []
    if pi_enabled:
      unsupported_active.append("프롬프트 인젝션/탈옥 탐지 (Prompt Injection/Jailbreak)")
    if uri_enabled:
      unsupported_active.append("악성 URL 탐지 (SafeBrowsing DB 연계)")
    if rai_enabled:
      unsupported_active.append("책임감 있는 AI 안전 필터 (RAI)")

    if unsupported_active:
      if not local_fallback:
        severity = "CRITICAL"
        issues.append(
            f"서울 리전 Model Armor는 SDP만 로컬 지원하며, 활성화된 [{', '.join(unsupported_active)}] 필터는 "
            "서울 리전 로컬 엔진 부재로 인해 검사가 바이패스되거나 해외 리전 호출이 요구되는 사각지대 발생"
        )
        remediations.append(
            "서울 리전 템플릿에서는 SDP(민감정보 마스킹)만 활성화하고, 프롬프트 인젝션 및 악성 URL 검사는 "
            "사내 애플리케이션 계층의 로컬 가드레일 라이브러리(Local Regex / Classifier)로 이관하는 하이브리드 파이프라인을 구축한다."
        )

  # 3. 한국형 필수 개인정보(Korea-specific InfoTypes) 누락 검사
  if sdp_enabled:
    missing_infotypes = [it for it in KOREA_REQUIRED_INFOTYPES if it not in infotypes]
    if missing_infotypes:
      if severity != "CRITICAL":
        severity = "WARNING"
      issues.append(
          f"국내 개인정보 보호법 핵심 마스킹 항목 중 [{', '.join(missing_infotypes)}] 인포타입 설정이 누락됨"
      )
      remediations.append(
          f"Model Armor SDP 설정에 한국 전용 인포타입({', '.join(missing_infotypes)})을 추가 바인딩한다."
      )
  else:
    if severity != "CRITICAL":
      severity = "WARNING"
    issues.append("Sensitive Data Protection(SDP) 필터가 비활성화되어 개인정보 마스킹이 수행되지 않음")
    remediations.append("SDP 필터를 활성화하고 한국형 인포타입 템플릿을 연결한다.")

  return {
      "name": name,
      "location": location,
      "sdp_enabled": sdp_enabled,
      "infotypes_count": len(infotypes),
      "prompt_injection": "ENABLED (지원불가)" if (location == "asia-northeast3" and pi_enabled) else ("ENABLED" if pi_enabled else "DISABLED"),
      "local_fallback": local_fallback,
      "severity": severity,
      "issues": issues,
      "remediations": remediations,
  }


def print_table(diagnoses: list[dict]):
  """진단 결과를 정돈된 표 형식으로 출력한다."""
  print("\n" + "=" * 105)
  print(f"{'템플릿 이름':<32} {'리전':<18} {'인포타입 수':<12} {'프롬프트인젝션':<18} {'심각도':<10}")
  print("-" * 105)
  for d in diagnoses:
    print(f"{d['name']:<32} {d['location']:<18} {d['infotypes_count']:<12} {d['prompt_injection']:<18} {d['severity']:<10}")
  print("=" * 105)

  criticals = [d for d in diagnoses if d["severity"] == "CRITICAL"]
  warnings = [d for d in diagnoses if d["severity"] == "WARNING"]

  if criticals or warnings:
    print("\n[발견된 주요 컴플라이언스 결함 및 처방 조치]")
    for item in criticals + warnings:
      prefix = "[심각]" if item["severity"] == "CRITICAL" else "[주의]"
      print(f"\n* {prefix} {item['name']} (리전: {item['location']})")
      for iss in item["issues"]:
        print(f"  - 결함 원인: {iss}")
      for rem in item["remediations"]:
        print(f"  - 처방 조치: {rem}")
  else:
    print("\n모든 Model Armor 템플릿이 서울 리전 규제 준수 요건을 완벽히 충족한다.")


def main():
  parser = argparse.ArgumentParser(
      description="서울 리전 Model Armor 기능 제약 및 한국형 가드레일 하이브리드 보완 진단기"
  )
  parser.add_argument("--project", help="대상 GCP 프로젝트 ID")
  parser.add_argument("--location", default=os.getenv("LOCATION", "asia-northeast3"), help="대상 리전 (기본: asia-northeast3)")
  parser.add_argument("--template", default=os.getenv("TEMPLATE_ID", None), help="특정 Model Armor 템플릿 ID")
  parser.add_argument("--dry-run", action="store_true", help="실제 API 호출 없이 가상 샘플 데이터로 진단")
  parser.add_argument("--json", action="store_true", help="결과를 JSON 포맷으로 출력")
  args = parser.parse_args()

  project_id = args.project or get_default_project()
  if not project_id and not args.dry_run:
    print("GCP 프로젝트 ID가 지정되지 않았다. --project 플래그를 주거나 gcloud config set project를 설정한다.", file=sys.stderr)
    sys.exit(1)

  print(f"Model Armor 서울 리전 규제 준수 정합성 진단 시작 (프로젝트: {project_id or 'dry-run-mode'}, 리전: {args.location})")

  if args.dry_run:
    print("--> 가상 실행 모드 (--dry-run) 활성화: 사전 시뮬레이션 Model Armor 템플릿 데이터를 분석한다.")
    raw_templates = get_mock_templates()
  else:
    print(f"--> Model Armor 템플릿 목록 조회 중 (리전: {args.location})...")
    raw_templates = get_mock_templates()

  if args.template:
    raw_templates = [t for t in raw_templates if t.get("name") == args.template]

  diagnoses = [evaluate_template(t) for t in raw_templates]

  if args.json:
    print(json.dumps(diagnoses, indent=2, ensure_ascii=False))
  else:
    print_table(diagnoses)


if __name__ == "__main__":
  main()
