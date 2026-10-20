#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Gemini API VPC Service Controls Denial Resolver.

제미나이(Gemini) 및 Vertex AI 호출 시 발생하는 VPC Service Controls(VPC-SC)
보안 경계 차단(Perimeter Denial) 감사 로그를 역추적하고 원인별 해결책을 처방한다.
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
import subprocess
import sys


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
  """쉘 명령어를 실행하고 결과를 반환한다."""
  res = subprocess.run(cmd, capture_output=True, text=True)
  return res.returncode, res.stdout.strip(), res.stderr.strip()


def get_default_project(is_dry_run: bool = False, fallback_demo: str = "demo-project-id") -> str:
  """gcloud 설정 및 실시간 프로젝트 목록에서 활성 프로젝트를 탐색/선택한다."""
  env_proj = os.getenv("PROJECT_ID")
  if env_proj:
    return env_proj
  _, stdout, _ = run_cmd(["gcloud", "config", "get-value", "project"])
  if stdout and "(unset)" not in stdout:
    return stdout

  if is_dry_run or not sys.stdin.isatty():
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


def get_mock_denials():
  """데모 실행을 위한 가상 VPC-SC 거부 로그 목록을 반환한다."""
  return [
      {
          "principal": "developer-workstation@company.com",
          "service": "aiplatform.googleapis.com",
          "method": "google.cloud.aiplatform.v1beta1.PredictionService.GenerateContent",
          "reason": "NO_MATCHING_INGRESS_POLICY",
          "denial_id": "vpc-sc-denial-8f2a1b9c-4d3e-41a2-98bc-abcdef012345",
      },
      {
          "principal": "data-pipeline-sa@my-prod.iam.gserviceaccount.com",
          "service": "aiplatform.googleapis.com",
          "method": "google.cloud.aiplatform.v1beta1.PredictionService.StreamGenerateContent",
          "reason": "RESOURCES_NOT_IN_SAME_PERIMETER",
          "denial_id": "vpc-sc-denial-3c7d9e1a-5b6f-42c8-89ae-123456789abc",
      },
  ]


def get_prescription(reason: str) -> str:
  """VPC-SC 거부 사유 코드에 따른 권장 처방을 도출한다."""
  if reason in ("NO_MATCHING_INGRESS_POLICY", "IP_SUBMET_NOT_IN_PERIMETER"):
    return (
        "API 호출자가 신뢰할 수 없는 공용 IP 대역 또는 미지정 사설 서브넷에서 접근했다. "
        "VPC-SC 수신(Ingress) 규칙에 호출자의 IP 서브넷 대역 또는 서비스 계정을 명시적으로 허용해야 한다."
    )
  elif reason in ("SERVICE_NOT_RESTRICTED", "RESOURCES_NOT_IN_SAME_PERIMETER"):
    return (
        "제미나이 API(aiplatform.googleapis.com)가 경계 보호 대상으로 누락되었거나, "
        "호출 리소스와 대상 모델이 서로 다른 보안 경계로 분리되어 있다. "
        "두 리소스를 동일한 서비스 경계로 병합하거나 경계 간 브리지(Bridge) 규칙을 구성해야 한다."
    )
  else:
    return (
        "비공개 Google 액세스(Private Google Access) 또는 Private Service Connect(PSC) 연결이 불안정하다. "
        "사설 DNS 해석 및 서브넷 라우팅 테이블 구성을 점검해야 한다."
    )


def report_denials(denials: list[dict], project_id: str, days: int):
  """진단 리포트 및 문제 해결 처방을 출력한다."""
  print("=" * 72)
  print("[진단 결과] 제미나이(Gemini) VPC Service Controls 경계 차단 진단 리포트")
  print(f"  - 대상 프로젝트: {project_id}")
  print(f"  - 조회 기간: 최근 {days}일")
  print("=" * 72)

  if not denials:
    print("\n[성공] 지정한 기간 내 VPC-SC 경계 차단(Perimeter Denial) 로그가 발견되지 않았다. 안전하다!\n")
    return

  print(f"\n발견된 VPC-SC 경계 거부 사례: {len(denials)}건\n")

  for idx, d in enumerate(denials, start=1):
    print(f"[거부 사례 #{idx}]")
    print(f"  - 호출 주체 계정: {d['principal']}")
    print(f"  - 대상 서비스   : {d['service']}")
    print(f"  - 호출 메서드   : {d['method']}")
    print(f"  - 거부 사유 코드: {d['reason']}")
    print(f"  - 고유 거부 ID  : {d['denial_id']}")
    print("  [권장 처방 및 복구 가이드]")
    print(f"    - 원인 분석 및 해결책: {get_prescription(d['reason'])}")
    print("    - VPC-SC 문제 해결사 콘솔 ( https://console.cloud.google.com/security/vpc-service-controls/troubleshooter )")
    print("    - 서비스 경계 관리 콘솔 ( https://console.cloud.google.com/security/vpc-service-controls )")
    print("-" * 72)

  print("=" * 72 + "\n")


def build_markdown_report(denials: list[dict], project_id: str, days: int, is_dry_run: bool) -> str:
  """진단 결과를 바탕으로 표준 마크다운 리포트를 구성한다."""
  mode_str = "모의 실행 (Dry-run)" if is_dry_run else "실환경 진단 (Live)"
  header_line = (
      "[데모 실행] --dry-run 모드가 활성화되어 가상 VPC-SC 차단 리포트를 시뮬레이션한다.\n"
      if is_dry_run
      else "[스캔 완료] 실제 Cloud Logging 감사 로그 역추적 완료\n"
  )

  case_lines = []
  if not denials:
    case_lines.append(
        "\n[성공] 지정한 기간 내 VPC-SC 경계 차단(Perimeter Denial) 로그가 발견되지 않았다. 안전하다!\n"
    )
  else:
    case_lines.append(f"\n발견된 VPC-SC 경계 거부 사례: {len(denials)}건\n")
    for idx, d in enumerate(denials, start=1):
      case_lines.append(f"[거부 사례 #{idx}]")
      case_lines.append(f"  - 호출 주체 계정: {d['principal']}")
      case_lines.append(f"  - 대상 서비스   : {d['service']}")
      case_lines.append(f"  - 호출 메서드   : {d['method']}")
      case_lines.append(f"  - 거부 사유 코드: {d['reason']}")
      case_lines.append(f"  - 고유 거부 ID  : {d['denial_id']}")
      case_lines.append("  [권장 처방 및 복구 가이드]")
      case_lines.append(f"    - 원인 분석 및 해결책: {get_prescription(d['reason'])}")
      case_lines.append(
          "    - VPC-SC 문제 해결사 콘솔 ( https://console.cloud.google.com/security/vpc-service-controls/troubleshooter )"
      )
      case_lines.append(
          "    - 서비스 경계 관리 콘솔 ( https://console.cloud.google.com/security/vpc-service-controls )"
      )
      case_lines.append("-" * 72)

  cases_text = "\n".join(case_lines)

  return f"""# 진단 및 분석 리포트: gemini-vpc-sc-denial-resolver

- **생성 모드**: {mode_str}
- **대상 프로젝트**: `{project_id}`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
{header_line}========================================================================
[진단 결과] 제미나이(Gemini) VPC Service Controls 경계 차단 진단 리포트
  - 대상 프로젝트: {project_id}
  - 조회 기간: 최근 {days}일
========================================================================
{cases_text}
========================================================================
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```

---

## 3. 사내 거버넌스 4대 필수 표준 라벨링

본 도구는 Cloud Logging 정책 감사 로그 조회 도구이나, 연관된 클라우드 인프라 자원 및 브리지 프로젝트 생성 시 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-vpc-sc-denial-resolver`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 4. 콘솔 링크 조치 가이드

- **VPC-SC 문제 해결사 콘솔**: ( https://console.cloud.google.com/security/vpc-service-controls/troubleshooter )
- **서비스 경계 관리 콘솔**: ( https://console.cloud.google.com/security/vpc-service-controls )
- **VPC Service Controls 문제 해결 공식 가이드**: ( https://cloud.google.com/vpc-service-controls/docs/troubleshooting )
- **VPC Service Controls 수신 및 송신 규칙 공식 가이드**: ( https://cloud.google.com/vpc-service-controls/docs/ingress-egress-rules )

---

## 5. 자원 정리 안내 (Teardown)

본 도구는 순수 감사 로그 조회 도구이며 클라우드 상에 영구 자원을 생성하지 않으므로 별도의 자원 정리 작업이 필요하지 않다.
"""


def save_markdown_report(content: str, filepath: str = "report.md"):
  """진단 리포트를 마크다운 파일로 저장한다."""
  script_dir = os.path.dirname(os.path.abspath(__file__))
  target_path = os.path.join(script_dir, filepath)
  with open(target_path, "w", encoding="utf-8") as f:
    f.write(content)


def fetch_denials(project_id: str, days: int, limit: int) -> list[dict]:
  """gcloud logging read 명령으로 VPC-SC 감사 로그를 조회한다."""
  start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
  log_filter = (
      f'logName:"projects/{project_id}/logs/cloudaudit.googleapis.com%2Fpolicy" AND '
      f'protoPayload.metadata.securityPolicyViolations:* AND timestamp>="{start_date}"'
  )

  cmd = [
      "gcloud",
      "logging",
      "read",
      log_filter,
      f"--project={project_id}",
      "--format=json",
      f"--limit={limit}",
  ]
  code, stdout, stderr = run_cmd(cmd)
  if code != 0:
    print(f"[경고] Cloud Logging 조회 실패: {stderr}")
    return []

  results = []
  try:
    entries = json.loads(stdout) if stdout else []
    for entry in entries:
      proto = entry.get("protoPayload", {})
      auth = proto.get("authenticationInfo", {})
      metadata = proto.get("metadata", {})
      violations = metadata.get("securityPolicyViolations", [{}])
      v0 = violations[0] if violations else {}

      results.append({
          "principal": auth.get("principalEmail", "미식별"),
          "service": proto.get("serviceName", "aiplatform.googleapis.com"),
          "method": proto.get("methodName", "미식별"),
          "reason": v0.get("violationReason", "UNKNOWN"),
          "denial_id": v0.get("uuid", "미식별"),
      })
  except Exception as e:
    print(f"[경고] 로그 JSON 파싱 중 오류: {e}")
  return results



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
      description="제미나이 API VPC-SC 경계 차단 감사 로그 분석 및 문제 해결 처방 도구"
  )
  parser.add_argument(
      "-p",
      "--project",
      default=os.getenv("PROJECT_ID") or None,
      help="GCP 프로젝트 ID (기본값: 활성 프로젝트 자동 감지)",
  )
  days_env = os.getenv("DAYS")
  limit_env = os.getenv("LIMIT_COUNT")
  parser.add_argument(
      "-d",
      "--days",
      type=int,
      default=int(days_env) if days_env else 7,
      help="조회 대상 최근 기간 일수 (기본값: 7)",
  )
  parser.add_argument(
      "-l",
      "--limit",
      type=int,
      default=int(limit_env) if limit_env else 5,
      help="조회 대상 실패 로그 최대 건수 (기본값: 5)",
  )
  parser.add_argument(
      "--dry-run",
      action="store_true",
      help="실제 Cloud Logging 호출 없이 가상 시뮬레이션 모드로 실행한다",
  )
  parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
  args = parser.parse_args()
  if getattr(args, "config", False):
      run_config_mode("gemini-vpc-sc-denial-resolver")
      return

  if args.dry_run:
    project_id = "sample-project-id"
    print("\n[데모 실행] --dry-run 모드가 활성화되어 가상 VPC-SC 차단 리포트를 시뮬레이션한다.")
    denials = get_mock_denials()
    report_denials(denials, project_id, args.days)
    md_content = build_markdown_report(denials, project_id, args.days, is_dry_run=True)
    save_markdown_report(md_content)
    print("[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: report.md")
    return

  project_id = args.project or get_default_project(is_dry_run=False)

  print("=" * 72)
  print("[스캔 시작] 제미나이 API VPC-SC 경계 차단 감사 로그 역추적")
  print(f"  - 프로젝트 ID: {project_id}")
  print(f"  - 조회 기간: 최근 {args.days}일")
  print(f"  - 최대 건수: {args.limit}건")
  print("=" * 72)

  denials = fetch_denials(project_id, args.days, args.limit)
  report_denials(denials, project_id, args.days)

  print("=" * 72)
  print("[자원 정리 안내 (Teardown Guide)]")
  print("본 도구는 순수 감사 로그 조회 도구이므로 별도의 자원 정리 작업이 필요하지 않다.")
  print("=" * 72 + "\n")

  md_content = build_markdown_report(denials, project_id, args.days, is_dry_run=False)
  save_markdown_report(md_content)
  print("[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: report.md")


if __name__ == "__main__":
  main()
