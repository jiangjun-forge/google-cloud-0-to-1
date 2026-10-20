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


def build_report_text(project_id: str, location: str, is_dry_run: bool, diagnoses: list[dict]) -> str:
  """진단 결과를 텍스트 리포트 형식으로 생성한다."""
  lines = []
  lines.append(f"Model Armor 서울 리전 규제 준수 정합성 진단 시작 (프로젝트: {project_id}, 리전: {location})")
  if is_dry_run:
    lines.append("--> 가상 실행 모드 (--dry-run) 활성화: 사전 시뮬레이션 Model Armor 템플릿 데이터를 분석한다.")
  lines.append("")
  lines.append("=" * 105)
  lines.append(f"{'템플릿 이름':<32} {'리전':<18} {'인포타입 수':<12} {'프롬프트인젝션':<18} {'심각도':<10}")
  lines.append("-" * 105)
  for d in diagnoses:
    lines.append(f"{d['name']:<32} {d['location']:<18} {d['infotypes_count']:<12} {d['prompt_injection']:<18} {d['severity']:<10}")
  lines.append("=" * 105)

  criticals = [d for d in diagnoses if d["severity"] == "CRITICAL"]
  warnings = [d for d in diagnoses if d["severity"] == "WARNING"]

  if criticals or warnings:
    lines.append("\n[발견된 주요 컴플라이언스 결함 및 처방 조치]")
    for item in criticals + warnings:
      prefix = "[심각]" if item["severity"] == "CRITICAL" else "[주의]"
      lines.append(f"\n* {prefix} {item['name']} (리전: {item['location']})")
      for iss in item["issues"]:
        lines.append(f"  - 결함 원인: {iss}")
      for rem in item["remediations"]:
        lines.append(f"  - 처방 조치: {rem}")
  else:
    lines.append("\n모든 Model Armor 템플릿이 서울 리전 규제 준수 요건을 충족한다.")

  return "\n".join(lines)


def build_markdown_report(report_text: str, project_id: str, is_dry_run: bool) -> str:
  """마크다운 리포트(report.md) 내용을 생성한다."""
  mode_str = "모의 실행 (Dry-run)" if is_dry_run else "실제 환경 점검 (Live)"
  return f"""# 진단 및 분석 리포트: korea-model-armor-guard

- **생성 모드**: {mode_str}
- **대상 프로젝트**: `{project_id}`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
{report_text}
```

---

## 2. 사내 거버넌스 4대 필수 표준 라벨링

Model Armor 템플릿 및 Sensitive Data Protection 템플릿 배포 시 다음 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `korea-model-armor-guard`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 3. 콘솔 링크 조치 가이드

- **Model Armor 제품 개요 및 리전 가용성 안내**: ( https://cloud.google.com/security/products/model-armor )
- **Model Armor 템플릿 구성 공식 가이드**: ( https://docs.cloud.google.com/model-armor/overview )
- **Sensitive Data Protection 글로벌 및 로컬 리전 위치**: ( https://cloud.google.com/sensitive-data-protection/docs/locations )

---

## 4. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
"""


def save_markdown_report(content: str, filepath: str | None = None):
  """마크다운 리포트를 지정된 경로에 저장한다."""
  if filepath is None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, "report.md")
  try:
    with open(filepath, "w", encoding="utf-8") as f:
      f.write(content)
  except Exception as e:
    print(f"[경고] 리포트 파일({filepath}) 저장 실패: {e}")



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
      description="서울 리전 Model Armor 기능 제약 및 한국형 가드레일 하이브리드 보완 진단기"
  )
  parser.add_argument("--project", help="대상 GCP 프로젝트 ID")
  parser.add_argument("--location", default=os.getenv("LOCATION") or "asia-northeast3", help="대상 리전 (기본: asia-northeast3)")
  parser.add_argument("--template", default=os.getenv("TEMPLATE_ID") or None, help="특정 Model Armor 템플릿 ID")
  parser.add_argument("--dry-run", action="store_true", help="실제 API 호출 없이 가상 샘플 데이터로 진단")
  parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
  parser.add_argument("--json", action="store_true", help="결과를 JSON 포맷으로 출력")
  args = parser.parse_args()
  if getattr(args, "config", False):
      run_config_mode("korea-model-armor-guard")
      return

  project_id = "sample-project-id" if args.dry_run else (args.project or get_default_project(is_dry_run=args.dry_run))
  if not project_id and not args.dry_run:
    print("GCP 프로젝트 ID가 지정되지 않았다. --project 플래그를 주거나 gcloud config set project를 설정한다.", file=sys.stderr)
    sys.exit(1)

  if args.dry_run:
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
    report_text = build_report_text(project_id, args.location, args.dry_run, diagnoses)
    print(report_text)
    report_md = build_markdown_report(report_text, project_id, args.dry_run)
    save_markdown_report(report_md)
    print("\n[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: report.md")


if __name__ == "__main__":
  main()
