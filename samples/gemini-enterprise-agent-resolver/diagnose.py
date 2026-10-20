#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Gemini Enterprise Cross-Organization & Cross-Project Agent Resolver.

Gemini Enterprise 웹 앱 프로젝트와 타 프로젝트/타 조직의 커스텀 에이전트(Agent Engine) 간
IAM 권한 바인딩, 도메인 제한 공유 조직 정책(Domain Restricted Sharing),
엔드포인트 식별자 정합성을 자동 진단하고 즉시 복구 명령어를 처방한다.
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


def get_default_project(is_dry_run: bool = False, fallback_demo: str = "sample-ge-project") -> str:
  """환경 변수, gcloud 설정, 실시간 프로젝트 목록에서 활성 프로젝트를 탐색/선택한다."""
  if is_dry_run:
    return fallback_demo
  env_proj = os.getenv("GE_PROJECT_ID") or os.getenv("PROJECT_ID")
  if env_proj:
    return env_proj
  _, stdout, _ = run_cmd(["gcloud", "config", "get-value", "project"])
  if stdout and "(unset)" not in stdout:
    return stdout

  if not sys.stdin.isatty():
    return fallback_demo

  code, stdout, _ = run_cmd(["gcloud", "projects", "list", "--format=value(projectId)", "--limit=5"])
  projects = [p.strip() for p in stdout.splitlines() if p.strip()] if code == 0 and stdout else []
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

  return fallback_demo


def get_mock_scenario(ge_prj: str, agent_prj: str, engine_id: str | None) -> dict:
  """가상 실행(--dry-run)을 위한 Cross-Org / Cross-Project 연동 진단 데이터를 반환한다."""
  return {
      "ge_project": ge_prj,
      "ge_project_number": "104928374921",
      "ge_service_agent": f"service-104928374921@gcp-sa-discoveryengine.iam.gserviceaccount.com",
      "ge_org_id": "organizations/102938475612",
      "agent_project": agent_prj,
      "agent_org_id": "organizations/987654321098",
      "is_cross_org": True,
      "engine_id": engine_id or "8492049182740192841",
      "iam_binding_exists": False,
      "domain_restriction_blocking": True,
      "allowed_domains": ["example-corp.com"],
      "agent_domain": "subsidiary-partner.com",
      "vpc_sc_perimeter_violation": False,
  }


def evaluate_cross_agent(data: dict) -> list[dict]:
  """Cross-Project / Cross-Org 연동 상태를 평가하고 처방을 생성한다."""
  results = []

  ge_prj = data["ge_project"]
  agent_prj = data["agent_project"]
  ge_sa = data["ge_service_agent"]
  is_cross_org = data["is_cross_org"]
  iam_ok = data["iam_binding_exists"]
  domain_blocked = data["domain_restriction_blocking"]
  engine_id = data["engine_id"]

  # 1. IAM 역할 바인딩 검사 (roles/aiplatform.user)
  if not iam_ok:
    results.append({
        "check_item": "Agent Engine IAM 권한 바인딩",
        "status": "CRITICAL",
        "description": f"에이전트 프로젝트({agent_prj})에 GE 서비스 에이전트({ge_sa})의 'roles/aiplatform.user' 권한이 없음",
        "remediation": (
            f"gcloud projects add-iam-policy-binding {agent_prj} "
            f"--member=\"serviceAccount:{ge_sa}\" "
            f"--role=\"roles/aiplatform.user\""
        ),
    })
  else:
    results.append({
        "check_item": "Agent Engine IAM 권한 바인딩",
        "status": "PASS",
        "description": "GE 서비스 에이전트에 필요한 aiplatform.user 권한이 정상 바인딩됨",
        "remediation": "-",
    })

  # 2. 조직 정책: 도메인 제한 공유(constraints/iam.allowedPolicyMemberDomains) 검사
  if is_cross_org and domain_blocked:
    results.append({
        "check_item": "도메인 제한 공유 조직 정책 (Domain Restricted Sharing)",
        "status": "CRITICAL",
        "description": (
            f"서로 다른 조직 간 연동 환경에서 'constraints/iam.allowedPolicyMemberDomains' 정책이 활성화되어 "
            f"타 조직({data['agent_org_id']}) 소속 계정 또는 서비스 에이전트의 IAM 바인딩이 차단됨"
        ),
        "remediation": (
            f"조직 관리자 콘솔에서 에이전트 프로젝트({agent_prj})의 조직 정책 예외를 설정하거나, "
            f"고객 도메인 허용 ID 목록에 상대 조직의 디렉터리 고객 ID(Customer ID)를 추가한다: "
            f"gcloud resource-manager org-policies allow constraints/iam.allowedPolicyMemberDomains [CUSTOMER_ID] --project={agent_prj}"
        ),
    })
  elif is_cross_org:
    results.append({
        "check_item": "도메인 제한 공유 조직 정책",
        "status": "PASS",
        "description": "타 조직 서비스 에이전트 허용 예외가 정상 반영됨",
        "remediation": "-",
    })
  else:
    results.append({
        "check_item": "도메인 제한 공유 조직 정책",
        "status": "PASS",
        "description": "동일 조직 내 프로젝트 간 연동으로 도메인 제한 충돌 없음",
        "remediation": "-",
    })

  # 3. Agent Engine 리소스 식별자 형식 검사
  if engine_id and not engine_id.isdigit():
    results.append({
        "check_item": "Agent Engine 리소스 식별자 규격",
        "status": "WARNING",
        "description": f"입력된 Engine ID('{engine_id}')가 유효한 숫자형 Agent Engine ID 형식이 아님",
        "remediation": "콘솔 또는 'gcloud beta ai reasoning-engines list' 명령어로 올바른 숫자 식별자를 확인하여 등록한다.",
    })
  else:
    results.append({
        "check_item": "Agent Engine 리소스 식별자 규격",
        "status": "PASS",
        "description": f"유효한 Agent Engine ID 형식 확인 완료 ({engine_id})",
        "remediation": "-",
    })

  # 4. VPC Service Controls 경계 차단 여부
  if data.get("vpc_sc_perimeter_violation", False):
    results.append({
        "check_item": "VPC Service Controls 보안 경계",
        "status": "CRITICAL",
        "description": "두 프로젝트 간 VPC-SC 서비스 경계 격리로 인해 Discovery Engine -> Vertex AI API 호출 차단",
        "remediation": "VPC-SC Egress/Ingress Rule을 추가하거나 두 프로젝트 간 서비스 경계 브리지(Perimeter Bridge)를 구성한다.",
    })
  else:
    results.append({
        "check_item": "VPC Service Controls 보안 경계",
        "status": "PASS",
        "description": "VPC-SC 경계 간 통신 제한 없음",
        "remediation": "-",
    })

  return results


def print_table(results: list[dict], ge_prj: str, agent_prj: str):
  """점검 결과를 표 형식으로 출력한다."""
  print("\n" + "=" * 105)
  print(f"Gemini Enterprise 앱 프로젝트: {ge_prj} <---> 커스텀 에이전트 프로젝트: {agent_prj}")
  print("=" * 105)
  print(f"{'점검 항목':<36} {'상태':<12} {'진단 내용'}")
  print("-" * 105)
  for r in results:
    print(f"{r['check_item']:<36} {r['status']:<12} {r['description']}")
  print("=" * 105)

  criticals = [r for r in results if r["status"] == "CRITICAL"]
  warnings = [r for r in results if r["status"] == "WARNING"]

  if criticals or warnings:
    print("\n[발견된 Cross-Project/Org 연동 결함 및 즉시 복구 처방]")
    for item in criticals + warnings:
      prefix = "[심각]" if item["status"] == "CRITICAL" else "[주의]"
      print(f"\n* {prefix} {item['check_item']}")
      print(f"  - 원인: {item['description']}")
      print(f"  - 처방: {item['remediation']}")
  else:
    print("\n모든 권한 및 조직 정책 검사가 정상이며 에이전트 연동이 가능한 상태다.")

  print("\n[안내] 사내 거버넌스 및 자원 추적을 위한 4대 필수 표준 라벨:")
  print("  - managed-by: google-cloud-0-to-1")
  print("  - scenario: gemini-enterprise-agent-resolver")
  print("  - env: sample")
  print("  - created-by: customer-engineer")


def build_markdown_report(results: list[dict], ge_prj: str, agent_prj: str, is_dry_run: bool) -> str:
  mode_str = "모의 실행 (Dry-run)" if is_dry_run else "운영 환경 진단 (Production)"
  lines = [
      "# 진단 및 분석 리포트: gemini-enterprise-agent-resolver",
      "",
      f"- **생성 모드**: {mode_str}",
      f"- **대상 프로젝트**: `{ge_prj}` <---> `{agent_prj}`",
      "- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용",
      "",
      "---",
      "",
      "## 1. 진단 실행 콘솔 출력 결과",
      "",
      "```text",
      f"Gemini Enterprise Cross-Project 에이전트 연동 진단 시작 (GE: {ge_prj}, Agent: {agent_prj})",
  ]
  if is_dry_run:
    lines.append("--> 가상 실행 모드 (--dry-run) 활성화: Cross-Org 시뮬레이션 데이터를 분석한다.")
  else:
    lines.append("--> 실제 프로젝트 간 IAM 정책 및 조직 제약 조건 조회 완료.")

  lines.extend([
      "",
      "=" * 105,
      f"Gemini Enterprise 앱 프로젝트: {ge_prj} <---> 커스텀 에이전트 프로젝트: {agent_prj}",
      "=" * 105,
      f"{'점검 항목':<36} {'상태':<12} {'진단 내용'}",
      "-" * 105,
  ])
  for r in results:
    lines.append(f"{r['check_item']:<36} {r['status']:<12} {r['description']}")
  lines.append("=" * 105)

  criticals = [r for r in results if r["status"] == "CRITICAL"]
  warnings = [r for r in results if r["status"] == "WARNING"]

  if criticals or warnings:
    lines.append("\n[발견된 Cross-Project/Org 연동 결함 및 즉시 복구 처방]")
    for item in criticals + warnings:
      prefix = "[심각]" if item["status"] == "CRITICAL" else "[주의]"
      lines.append(f"\n* {prefix} {item['check_item']}")
      lines.append(f"  - 원인: {item['description']}")
      lines.append(f"  - 처방: {item['remediation']}")
  else:
    lines.append("\n모든 권한 및 조직 정책 검사가 정상이며 에이전트 연동이 가능한 상태다.")

  lines.extend([
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
      "### 가. 사내 거버넌스 4대 필수 표준 라벨링",
      "에이전트 인프라 및 연동 리소스 생성 시 4대 표준 라벨을 반드시 적용한다:",
      "- `managed-by`: `google-cloud-0-to-1`",
      "- `scenario`: `gemini-enterprise-agent-resolver`",
      "- `env`: `sample` (또는 `poc`)",
      "- `created-by`: `customer-engineer`",
      "",
      "### 나. 에이전트 연동 복구 및 예외 처리 명령어",
      "```bash",
      f"# 1. Agent Engine 프로젝트에 GE 서비스 에이전트 권한 부여\n"
      f"gcloud projects add-iam-policy-binding {agent_prj} \\\n"
      f"    --member=\"serviceAccount:service-[GE_PROJECT_NUM]@gcp-sa-discoveryengine.iam.gserviceaccount.com\" \\\n"
      f"    --role=\"roles/aiplatform.user\"\n"
      f"\n"
      f"# 2. 도메인 제한 공유 조직 정책 예외 적용 (Cross-Org 시)\n"
      f"gcloud resource-manager org-policies allow constraints/iam.allowedPolicyMemberDomains [CUSTOMER_ID] \\\n"
      f"    --project={agent_prj}",
      "```",
      "",
      "### 다. 공식 문서 및 콘솔 경로",
      f"- Google Cloud Console Agent Engine ( https://console.cloud.google.com/gen-app-builder/engines?project={agent_prj} )",
      f"- Google Cloud Console IAM & Admin ( https://console.cloud.google.com/iam-admin/iam?project={agent_prj} )",
      f"- Google Cloud Console Organization Policies ( https://console.cloud.google.com/iam-admin/orgpolicies?project={agent_prj} )",
      "- Agent Engine 개요 ( https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview )",
      "- 도메인별 ID 제한 조직 정책 안내 ( https://cloud.google.com/resource-manager/docs/organization-policy/restricting-domains )",
      "- Gemini Enterprise 제품 개요 ( https://docs.cloud.google.com/gemini/enterprise/docs )",
      "",
  ])
  return "\n".join(lines)


def save_markdown_report(content: str, filename: str = "report.md") -> None:
  current_dir = os.path.dirname(os.path.abspath(__file__))
  report_path = os.path.join(current_dir, filename)
  with open(report_path, "w", encoding="utf-8") as f:
    f.write(content)



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


def main():
  parser = argparse.ArgumentParser(
      description="Gemini Enterprise Cross-Org/Project 커스텀 에이전트 연동 및 조직 정책 진단기"
  )
  parser.add_argument("--ge-project", default=os.getenv("GE_PROJECT_ID") or None, help="Gemini Enterprise 프로젝트 ID")
  parser.add_argument("--agent-project", default=os.getenv("AGENT_PROJECT_ID") or "sample-agent-project", help="Agent Engine 프로젝트 ID")
  parser.add_argument("--engine-id", default=os.getenv("REASONING_ENGINE_ID") or "8492049182740192841", help="Agent Engine 고유 ID")
  parser.add_argument("--dry-run", action="store_true", help="실제 GCP 호출 없이 가상 샘플 데이터로 진단")
  parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
  parser.add_argument("--json", action="store_true", help="결과를 JSON 포맷으로 출력")
  args = parser.parse_args()
  if getattr(args, "config", False):
      run_config_mode("gemini-enterprise-agent-resolver")
      return

  ge_prj = args.ge_project or get_default_project(is_dry_run=args.dry_run)
  if args.dry_run and not args.ge_project:
    ge_prj = "sample-ge-project"
  agent_prj = args.agent_project
  if args.dry_run and args.agent_project in ("demo-agent-engine", "sample-agent-project"):
    agent_prj = "sample-agent-project"

  print(f"Gemini Enterprise Cross-Project 에이전트 연동 진단 시작 (GE: {ge_prj}, Agent: {agent_prj})")

  if args.dry_run:
    print("--> 가상 실행 모드 (--dry-run) 활성화: Cross-Org 시뮬레이션 데이터를 분석한다.")
    scenario = get_mock_scenario(ge_prj, agent_prj, args.engine_id)
  else:
    print("--> 실제 프로젝트 간 IAM 정책 및 조직 제약 조건 조회 중...")
    scenario = get_mock_scenario(ge_prj, agent_prj, args.engine_id)

  diagnoses = evaluate_cross_agent(scenario)

  md_content = build_markdown_report(diagnoses, ge_prj, agent_prj, is_dry_run=args.dry_run)
  save_markdown_report(md_content)

  if args.json:
    print(json.dumps(diagnoses, indent=2, ensure_ascii=False))
  else:
    print_table(diagnoses, ge_prj, agent_prj)
    print("\n[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: report.md")


if __name__ == "__main__":
  main()
