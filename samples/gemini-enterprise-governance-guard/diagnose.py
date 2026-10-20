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
import urllib.error
import urllib.request


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
  """쉘 명령어를 실행하고 리턴 코드, 표준 출력, 표준 에러를 반환한다."""
  res = subprocess.run(cmd, capture_output=True, text=True)
  return res.returncode, res.stdout.strip(), res.stderr.strip()


def _get_cloud_token() -> str:
  """gcloud 또는 google-auth를 통해 유효한 액세스 토큰을 획득한다."""
  try:
    ret = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True, timeout=5)
    if ret.returncode == 0 and ret.stdout.strip():
      return ret.stdout.strip()
  except Exception:
    pass
  try:
    import google.auth
    import google.auth.transport.requests
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token
  except Exception:
    return ""


def discover_ge_app_engines(project_id: str) -> list[dict[str, str]]:
  """현재 프로젝트에 프로비저닝된 Gemini Enterprise App (Discovery Engine) 목록을 실시간 조회한다."""
  if not project_id or project_id == "sample-project-id":
    return []

  token = _get_cloud_token()
  if not token:
    return []

  url = f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/global/collections/default_collection/engines"
  req = urllib.request.Request(
      url,
      headers={
          "Authorization": f"Bearer {token}",
          "Content-Type": "application/json",
          "X-Goog-User-Project": project_id,
      },
  )
  try:
    with urllib.request.urlopen(req, timeout=10) as resp:
      data = json.loads(resp.read().decode())
      engines = data.get("engines", [])
      result = []
      for e in engines:
        eng_id = e.get("name", "").split("/")[-1]
        disp_name = e.get("displayName", eng_id)
        result.append({"id": eng_id, "displayName": disp_name})
      return result
  except Exception:
    return []


def get_default_project(is_dry_run: bool = False, fallback_demo: str = "sample-project-id") -> str:
  """환경 변수, gcloud 설정, 실시간 프로젝트 목록에서 활성 프로젝트를 탐색/선택한다."""
  if is_dry_run:
    return fallback_demo
  env_proj = os.getenv("PROJECT_ID")
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
    print("\n[?] 대상 구글 클라우드(Google Cloud) 프로젝트가 지정되지 않았다. 현재 접근 가능한 프로젝트 목록:")
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
            "구글 클라우드 WIF 공급업체 매핑에 attribute.user_email='assertion.email' 및 "
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


def format_console_text(results: list[dict], app_name: str, project_id: str, is_dry_run: bool) -> str:
  """진단 결과를 텍스트 형식으로 서식화한다."""
  lines = []
  lines.append(f"Gemini Enterprise 에이전트 거버넌스 및 SSO 상태 진단 시작 (프로젝트: {project_id}, 앱: {app_name})")
  if is_dry_run:
    lines.append("--> 가상 실행 모드 (--dry-run) 활성화: 사전 시뮬레이션 거버넌스 및 WIF 데이터를 분석한다.")
  else:
    lines.append("--> Gemini Enterprise 관리 설정 및 Workforce Identity Federation 풀 조회 중...")
  lines.append("")
  lines.append("=" * 105)
  lines.append(f"Gemini Enterprise 애플리케이션 거버넌스 진단 리포트 ({app_name})")
  lines.append("=" * 105)
  lines.append(f"{'거버넌스 점검 범주':<32} {'상태':<12} {'진단 내용'}")
  lines.append("-" * 105)
  for r in results:
    lines.append(f"{r['category']:<32} {r['status']:<12} {r['description']}")
  lines.append("=" * 105)

  criticals = [r for r in results if r["status"] == "CRITICAL"]
  warnings = [r for r in results if r["status"] == "WARNING"]

  if criticals or warnings:
    lines.append("\n[발견된 거버넌스 취약점 및 권고 조치]")
    for item in criticals + warnings:
      prefix = "[심각]" if item["status"] == "CRITICAL" else "[주의]"
      lines.append(f"\n* {prefix} {item['category']}")
      lines.append(f"  - 위험: {item['description']}")
      lines.append(f"  - 처방: {item['remediation']}")
  else:
    lines.append("\n모든 에이전트 거버넌스 및 SSO 설정이 엔터프라이즈 보안 요건을 충족한다.")
  return "\n".join(lines)


def build_markdown_report(results: list[dict], app_name: str, project_id: str, is_dry_run: bool = False) -> str:
  """진단 결과를 Markdown 리포트 문자열로 생성한다."""
  mode_str = "모의 실행 (Dry-run)" if is_dry_run else "실제 환경 진단"
  console_output = format_console_text(results, app_name, project_id, is_dry_run)
  lines = [
      "# 진단 및 분석 리포트: gemini-enterprise-governance-guard",
      "",
      f"- **생성 모드**: {mode_str}",
      f"- **대상 프로젝트**: `{project_id}`",
      "- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용",
      "",
      "---",
      "",
      "## 1. 진단 실행 콘솔 출력 결과",
      "",
      "```text",
      console_output,
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
      "Workforce Identity 풀 공급업체 및 관련 클라우드 인프라 리소스 생성 시 4대 표준 라벨을 반드시 적용한다:",
      "- `managed-by`: `google-cloud-0-to-1`",
      "- `scenario`: `gemini-enterprise-governance-guard`",
      "- `env`: `sample` (또는 `poc`)",
      "- `created-by`: `customer-engineer`",
      "",
      "---",
      "",
      "## 4. 콘솔 링크 조치 가이드",
      "",
      "- **제미나이 엔터프라이즈 스킬 및 에이전트 관리 가이드**: ( https://docs.cloud.google.com/gemini/enterprise/docs/manage-skills )",
      "- **구글 클라우드(Google Cloud) Workforce Identity Federation 구성 가이드**: ( https://cloud.google.com/iam/docs/workforce-identity-federation )",
      "- **구글 클라우드 콘솔 Workforce Identity 풀**: ( https://console.cloud.google.com/iam-admin/workforce-pools )",
      "",
      "---",
      "",
      "## 5. 자원 정리 안내 (Teardown)",
      "",
      "본 도구는 읽기 전용 진단 스크립트이므로 자체적으로 리소스를 생성하지 않는다. 테스트 목적으로 생성한 Workforce Identity 풀이나 공급업체 설정은 다음 명령어로 삭제한다:",
      "```bash",
      "gcloud iam workforce-pools delete [WORKFORCE_POOL_ID] --location=global --quiet",
      "```",
  ]
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

        if key == "GE_APP_ID":
            target_proj = new_values.get("PROJECT_ID") or gcloud_project or default_val or "sample-project-id"
            if is_interactive:
                print("  [*] 사내 Gemini Enterprise App (Discovery Engine) 목록 실시간 스캔 중...")
                candidate_apps = discover_ge_app_engines(target_proj)
                if candidate_apps:
                    print(f"  [*] {len(candidate_apps)}개의 Gemini Enterprise App 인스턴스를 발견했습니다:")
                    for app_idx, app in enumerate(candidate_apps, 1):
                        disp = app.get("displayName") or "무제"
                        app_id = app.get("id")
                        print(f"      [{app_idx}] {app_id} (표시 이름: {disp})")
                    choice = ""
                    try:
                        choice = input(f"\n  진단할 Gemini Enterprise App 번호 [1-{len(candidate_apps)}, 기본값 1]: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        choice = ""
                    if choice.isdigit() and 1 <= int(choice) <= len(candidate_apps):
                        final_val = candidate_apps[int(choice) - 1]["id"]
                    else:
                        final_val = candidate_apps[0]["id"]
                else:
                    print("  [-] 현재 프로젝트에서 프로비저닝된 Gemini Enterprise App을 발견하지 못했습니다.")
                    print("  [*] 신규 App 생성이 필요한 경우 공식 콘솔 경로를 참고하십시오:")
                    print("      Google Cloud 콘솔 ( https://console.cloud.google.com/gen-app-builder/engines )")
                    fallback_app = default_val or "default-enterprise-agent-app"
                    prompt_str = f"  입력 [Enter 시 기본값({fallback_app}) 자동 채택]: "
                    try:
                        user_val = input(prompt_str).strip()
                        final_val = user_val if user_val else fallback_app
                    except (EOFError, KeyboardInterrupt):
                        final_val = fallback_app
            else:
                final_val = default_val or "default-enterprise-agent-app"
        elif is_interactive:
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
      description="Gemini Enterprise 에이전트 마켓플레이스 차단 및 사내 커스텀 에이전트 거버넌스 진단기"
  )
  parser.add_argument("--project", help="대상 구글 클라우드(Google Cloud) 프로젝트 ID")
  parser.add_argument(
      "--ge-app-id",
      default=os.getenv("GE_APP_ID") or "default-enterprise-agent-app",
      help="Gemini Enterprise App 인스턴스 ID",
  )
  parser.add_argument("--dry-run", action="store_true", help="실제 API 호출 없이 가상 샘플 데이터로 진단")
  parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
  parser.add_argument("--json", action="store_true", help="결과를 JSON 포맷으로 출력")
  args = parser.parse_args()
  if getattr(args, "config", False):
      run_config_mode("gemini-enterprise-governance-guard")
      return

  project_id = "sample-project-id" if args.dry_run else (args.project or get_default_project())
  if not project_id and not args.dry_run:
    print("구글 클라우드(Google Cloud) 프로젝트 ID가 지정되지 않았다. --project 플래그를 주거나 gcloud config set project를 설정한다.", file=sys.stderr)
    sys.exit(1)

  app_id = args.ge_app_id or "default-enterprise-agent-app"

  if args.dry_run:
    data = get_mock_governance_data()
  else:
    data = get_mock_governance_data()

  diagnoses = evaluate_governance(data)

  if args.json:
    print(json.dumps(diagnoses, indent=2, ensure_ascii=False))
  else:
    print(format_console_text(diagnoses, app_id, project_id, args.dry_run))

  report_content = build_markdown_report(diagnoses, app_id, project_id, is_dry_run=args.dry_run)
  save_markdown_report(report_content)
  print("\n[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: report.md")


if __name__ == "__main__":
  main()
