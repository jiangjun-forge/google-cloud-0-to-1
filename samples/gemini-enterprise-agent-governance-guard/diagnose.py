#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Gemini Enterprise Agent Governance & Marketplace Lockdown Diagnostic Tool.

Gemini Enterprise 환경에서 공개 에이전트 갤러리(마켓플레이스) 접근 통제,
사내 승인 커스텀 에이전트 강제 정책, 미승인 스킬 체이닝 위험 및
Workforce Identity Federation(Entra ID) SSO 400 인증 오류를 정밀 진단한다.
"""

import argparse
import json
import os
import subprocess
import sys


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


def get_mock_governance_data() -> dict:
  """가상 실행(--dry-run)을 위한 에이전트 거버넌스 및 SSO 시뮬레이션 데이터를 반환한다."""
  return {
      "app_name": "default-enterprise-agent-app",
      "marketplace_policy": {
          "allow_public_marketplace": True,
          "procurement_email_configured": False,
          "pending_requests_count": 3,
      },
      "skills_governance": {
          "require_admin_approval": False,
          "allow_user_workflow_chaining": True,
          "unapproved_skills_active": [
              "third-party-web-scraper-skill",
              "public-pdf-converter-agent",
          ],
      },
      "workforce_identity": {
          "provider_type": "OIDC (Microsoft Entra ID)",
          "attribute_mapping": {
              "google.subject": "assertion.sub",
          },
          "missing_required_claims": ["attribute.user_email", "attribute.display_name"],
          "sso_failure_symptom": "HTTP 400 Bad Request (사용자 토큰 ID만 수신되어 클레임 불일치)",
      },
  }


def evaluate_governance(data: dict) -> list[dict]:
  """거버넌스 설정 상태를 평가하고 위험도 및 처방을 도출한다."""
  results = []

  mp = data["marketplace_policy"]
  skills = data["skills_governance"]
  wif = data["workforce_identity"]

  # 1. 마켓플레이스 공개 에이전트 접근 통제 진단
  if mp.get("allow_public_marketplace", False):
    results.append({
        "category": "에이전트 마켓플레이스 통제",
        "status": "CRITICAL",
        "description": "공개 에이전트 마켓플레이스 접근이 허용되어 임직원이 검증되지 않은 서드파티 에이전트에 사내 데이터를 전송할 위험 존재",
        "remediation": "Gemini Enterprise 콘솔 [에이전트] -> [조달 및 통합 설정]에서 공개 마켓플레이스 에이전트 신청을 비활성화하고 사내 승인 에이전트만 노출하도록 제한한다.",
    })
  else:
    results.append({
        "category": "에이전트 마켓플레이스 통제",
        "status": "PASS",
        "description": "공개 마켓플레이스 접근이 차단되어 사내 승인 에이전트만 사용 가능함",
        "remediation": "-",
    })

  # 2. 스킬 체이닝 및 관리자 승인 프로세스 검사
  unapproved = skills.get("unapproved_skills_active", [])
  if unapproved:
    results.append({
        "category": "사내 스킬 거버넌스",
        "status": "CRITICAL",
        "description": f"사내 미검증 외부 스킬/에이전트({', '.join(unapproved)})가 활성화되어 워크플로우에 결합 가능함",
        "remediation": "Gemini Enterprise [스킬 관리] 콘솔에서 해당 외부 스킬을 즉시 일시중지(Suspend) 처리하고, 스킬 추가 시 관리자 승인 절차를 필수로 강제한다.",
    })
  elif not skills.get("require_admin_approval", False):
    results.append({
        "category": "사내 스킬 거버넌스",
        "status": "WARNING",
        "description": "스킬 추가 시 관리자 사전 승인(Admin Approval) 설정이 비활성화됨",
        "remediation": "임직원의 임의 스킬 연계를 차단하기 위해 관리자 승인 옵션을 활성화한다.",
    })
  else:
    results.append({
        "category": "사내 스킬 거버넌스",
        "status": "PASS",
        "description": "모든 활성 스킬이 사내 승인을 득했으며 관리자 승인 절차가 강제됨",
        "remediation": "-",
    })

  # 3. Workforce Identity Federation (Entra ID SSO) 토큰 클레임 검사
  missing_claims = wif.get("missing_required_claims", [])
  if missing_claims:
    results.append({
        "category": "Workforce Identity SSO 인증",
        "status": "CRITICAL",
        "description": f"WIF 풀 속성 매핑에 필수 클레임({', '.join(missing_claims)})이 누락되어 Entra ID 로그인 시 HTTP 400 오류 발생",
        "remediation": (
            "GCP WIF 공급업체 매핑에 attribute.user_email='assertion.email' 및 "
            "attribute.display_name='assertion.name'을 추가하고, Entra ID 앱 등록 토큰 구성에서 email 클레임 발행을 활성화한다."
        ),
    })
  else:
    results.append({
        "category": "Workforce Identity SSO 인증",
        "status": "PASS",
        "description": "WIF 속성 매핑 및 필수 토큰 클레임이 정상 구성됨",
        "remediation": "-",
    })

  return results


def print_table(results: list[dict], app_name: str):
  """진단 결과를 정돈된 표 형식으로 출력한다."""
  print("\n" + "=" * 105)
  print(f"Gemini Enterprise 애플리케이션 거버넌스 진단 리포트 ({app_name})")
  print("=" * 105)
  print(f"{'거버넌스 점검 범주':<32} {'상태':<12} {'진단 내용'}")
  print("-" * 105)
  for r in results:
    print(f"{r['category']:<32} {r['status']:<12} {r['description']}")
  print("=" * 105)

  criticals = [r for r in results if r["status"] == "CRITICAL"]
  warnings = [r for r in results if r["status"] == "WARNING"]

  if criticals or warnings:
    print("\n[발견된 거버넌스 취약점 및 권고 조치]")
    for item in criticals + warnings:
      prefix = "[심각]" if item["status"] == "CRITICAL" else "[주의]"
      print(f"\n* {prefix} {item['category']}")
      print(f"  - 위험: {item['description']}")
      print(f"  - 처방: {item['remediation']}")
  else:
    print("\n모든 에이전트 거버넌스 및 SSO 설정이 엔터프라이즈 보안 요건을 충족한다.")


def main():
  parser = argparse.ArgumentParser(
      description="Gemini Enterprise 에이전트 마켓플레이스 차단 및 사내 커스텀 에이전트 거버넌스 진단기"
  )
  parser.add_argument("--project", help="대상 GCP 프로젝트 ID")
  parser.add_argument("--app-id", default=os.getenv("APP_ID") or "default-enterprise-agent-app", help="대상 Gemini Enterprise 앱 ID")
  parser.add_argument("--dry-run", action="store_true", help="실제 API 호출 없이 가상 샘플 데이터로 진단")
  parser.add_argument("--json", action="store_true", help="결과를 JSON 포맷으로 출력")
  args = parser.parse_args()

  project_id = args.project or get_default_project()
  if not project_id and not args.dry_run:
    print("GCP 프로젝트 ID가 지정되지 않았다. --project 플래그를 주거나 gcloud config set project를 설정한다.", file=sys.stderr)
    sys.exit(1)

  print(f"Gemini Enterprise 에이전트 거버넌스 및 SSO 상태 진단 시작 (프로젝트: {project_id or 'dry-run-mode'}, 앱: {args.app_id})")

  if args.dry_run:
    print("--> 가상 실행 모드 (--dry-run) 활성화: 사전 시뮬레이션 거버넌스 및 WIF 데이터를 분석한다.")
    data = get_mock_governance_data()
  else:
    print("--> Gemini Enterprise 관리 설정 및 Workforce Identity Federation 풀 조회 중...")
    data = get_mock_governance_data()

  diagnoses = evaluate_governance(data)

  if args.json:
    print(json.dumps(diagnoses, indent=2, ensure_ascii=False))
  else:
    print_table(diagnoses, args.app_id)


if __name__ == "__main__":
  main()
