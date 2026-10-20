#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""GCP Organization Policy Violation Resolver.

최근 발생한 GCP 조직 정책(Organization Policy) 제약 조건 위반 실패 감사 로그를 역추적하여
위반된 제약 조건 식별자 및 원클릭 정책 해제/우회 gcloud 명령어를 처방한다.
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
import re
import subprocess
import sys


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
  """쉘 명령어를 실행하고 결과를 반환한다."""
  res = subprocess.run(cmd, capture_output=True, text=True)
  return res.returncode, res.stdout.strip(), res.stderr.strip()


def get_default_project(is_dry_run: bool = False, fallback_demo: str = "sample-project-id") -> str:
  """gcloud 설정 및 실시간 프로젝트 목록에서 활성 프로젝트를 탐색/선택한다."""
  if is_dry_run:
    return "sample-project-id"
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


def get_mock_violations():
  """데모 실행을 위한 가상 조직 정책 위반 로그 목록을 반환한다."""
  return [
      {
          "principal": "security-engineer@company.com",
          "service": "iam.googleapis.com",
          "method": "google.iam.admin.v1.CreateServiceAccountKey",
          "message": "Operation denied by organization policy: constraints/iam.disableServiceAccountKeyCreation violated",
          "constraint": "iam.disableServiceAccountKeyCreation",
      },
      {
          "principal": "cloud-infra-admin@company.com",
          "service": "compute.googleapis.com",
          "method": "compute.instances.insert",
          "message": "Operation denied by organization policy: constraints/compute.vmExternalIpAccess violated on instance vm-bastion-1",
          "constraint": "compute.vmExternalIpAccess",
      },
      {
          "principal": "web-deployer@company.com",
          "service": "storage.googleapis.com",
          "method": "storage.setIamPermissions",
          "message": "Constraint constraints/storage.publicAccessPrevention violated on bucket gs://web-static-assets",
          "constraint": "storage.publicAccessPrevention",
      },
  ]


def map_policy_info(constraint: str) -> tuple[str, str]:
  """제약 조건별 설명과 권장 처방을 도출한다."""
  if constraint == "iam.disableServiceAccountKeyCreation":
    return (
        "서비스 계정 키(JSON 키) 신규 생성을 전면 차단하는 조직 제약 조건이다.",
        "보안을 위해 워크로드 아이덴티티(Workload Identity) 연동을 권장하나, "
        "테스트 및 마이그레이션 단계에서 키 발급이 불가피한 경우 해당 프로젝트에 한해 제약을 해제할 수 있다."
    )
  elif constraint == "compute.vmExternalIpAccess":
    return (
        "Compute Engine VM 인스턴스에 외부 공용 IP 할당을 금지하는 조직 제약 조건이다.",
        "내부 IP 전용 VM 생성 및 Cloud NAT 게이트웨이 구성을 권장하나, "
        "단독 외부 접속이 필요한 경우 제약을 해제할 수 있다."
    )
  elif constraint == "storage.publicAccessPrevention":
    return (
        "Cloud Storage 버킷의 공용(allUsers) 공개 액세스를 차단하는 조직 제약 조건이다.",
        "데이터 유출 방지를 위해 비공개 액세스 유지를 권장하나, "
        "정적 웹사이트 호스팅이나 퍼블릭 다운로드 자산인 경우 제약을 해제할 수 있다."
    )
  else:
    return (
        "조직 리소스 생성 및 환경 설정을 제어하는 표준 보안 제약 조건이다.",
        "사내 보안 가이드라인을 검토하고 불가피한 경우에 한해 프로젝트 단위 정책 예외를 구성해야 한다."
    )


def report_violations(violations: list[dict], project_id: str, days: int):
  """진단 리포트 및 해결 명령어를 출력한다."""
  print("=" * 72)
  print("[진단 결과] GCP 조직 정책(Organization Policy) 위반 감사 추적 리포트")
  print(f"  - 대상 프로젝트: {project_id}")
  print(f"  - 조회 기간: 최근 {days}일")
  print("=" * 72)

  if not violations:
    print("\n[성공] 조직 정책 제약 조건(Constraints) 위반 실패 감사 로그가 발견되지 않았다. 안전하다!\n")
    return

  print(f"\n발견된 조직 정책 위반 실패 내역: {len(violations)}건\n")

  for idx, v in enumerate(violations, start=1):
    desc, action = map_policy_info(v["constraint"])

    print(f"[위반 건 #{idx}]")
    print(f"  - 실패 주체 계정  : {v['principal']}")
    print(f"  - 요청 대상 서비스: {v['service']}")
    print(f"  - 실행 실패 액션  : {v['method']}")
    print(f"  - 실제 오류 내용  : {v['message']}")
    print("  [정밀 처방 제약 조건 분석]")
    print(f"    - 검출 제약 사항: constraints/{v['constraint']}")
    print(f"    - 제약 조건 설명: {desc}")
    print(f"    - 권장 임시 방안: {action}")
    print("  [즉시 조치 가능한 원클릭 gcloud 해결 명령어]")
    print(f"    gcloud resource-manager org-policies disable-enforce \"{v['constraint']}\" \\")
    print(f"      --project=\"{project_id}\"")
    print("-" * 72)

  print("=" * 72 + "\n")


def fetch_violations(project_id: str, days: int, limit: int) -> list[dict]:
  """gcloud logging read 명령으로 조직 정책 위반 감사 로그를 조회한다."""
  start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
  log_filter = (
      f'logName:"projects/{project_id}/logs/cloudaudit.googleapis.com%2Factivity" AND '
      f'(protoPayload.status.code=9 OR protoPayload.status.message:"Constraint" OR protoPayload.status.message:"violated") AND '
      f'timestamp>="{start_date}"'
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
      status = proto.get("status", {})
      msg = status.get("message", "")

      # 제약 조건 ID 추출
      match = re.search(r"constraints/([a-zA-Z0-9.]+)", msg)
      constraint = match.group(1) if match else "unknown"

      results.append({
          "principal": auth.get("principalEmail", "미식별"),
          "service": proto.get("serviceName", "unknown"),
          "method": proto.get("methodName", "unknown"),
          "message": msg,
          "constraint": constraint,
      })
  except Exception as e:
    print(f"[경고] 로그 JSON 파싱 중 오류: {e}")
  return results


def build_markdown_report(violations: list[dict], project_id: str, days: int, is_dry_run: bool) -> str:
  """터미널 진단 결과와 완벽히 동기화된 마크다운 리포트를 생성한다."""
  mode_str = "모의 실행 (Dry-run)" if is_dry_run else "사내 실측 진단"
  lines = [
      "# GCP 조직 정책 위반 감사 역추적 및 복구 진단 리포트 (org-policy-resolver)",
      "",
      f"- **생성 모드**: {mode_str}",
      f"- **대상 프로젝트**: `{project_id}`",
      f"- **조회 기간**: 최근 {days}일",
      "- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용",
      "",
      "---",
      "",
      f"## 1. 발견된 조직 정책 위반 실패 내역: {len(violations)}건",
      "",
  ]
  if not violations:
    lines.append("조직 정책 제약 조건(Constraints) 위반 실패 감사 로그가 발견되지 않았다. 안전하다!\n")
  else:
    for idx, v in enumerate(violations, start=1):
      desc, action = map_policy_info(v["constraint"])
      c_name = v["constraint"]
      lines.extend([
          f"### [위반 건 #{idx}]",
          f"- **실패 주체 계정**: `{v['principal']}`",
          f"- **요청 대상 서비스**: `{v['service']}`",
          f"- **실행 실패 액션**: `{v['method']}`",
          f"- **실제 오류 내용**: `{v['message']}`",
          "",
          "#### 정밀 처방 제약 조건 분석",
          f"- **검출 제약 사항**: `constraints/{c_name}`",
          f"- **제약 조건 설명**: {desc}",
          f"- **권장 임시 방안**: {action}",
          "",
          "#### 즉시 조치 가능한 원클릭 gcloud 해결 명령어",
          "```bash",
          f'gcloud resource-manager org-policies disable-enforce "{c_name}" \\',
          f'  --project="{project_id}"',
          "```",
          "",
      ])

  lines.extend([
      "---",
      "",
      "## 2. 사내 거버넌스 4대 필수 표준 라벨링",
      "",
      "조직 정책 예외 적용 대상 인프라 자원(Compute Engine VM, Cloud Storage 버킷, 서비스 계정 등) 프로비저닝 시 다음 4대 표준 라벨을 반드시 적용한다:",
      "- `managed-by`: `google-cloud-0-to-1`",
      "- `scenario`: `org-policy-resolver`",
      "- `env`: `sample` (또는 `poc`)",
      "- `created-by`: `customer-engineer`",
      "",
      "---",
      "",
      "## 3. 콘솔 링크 조치 가이드 및 공식 레퍼런스",
      "",
      f"- **조직 정책 관리 콘솔**: ( https://console.cloud.google.com/iam-admin/orgpolicies?project={project_id} )",
      f"- **Cloud Logging 탐색기**: ( https://console.cloud.google.com/logs/viewer?project={project_id} )",
      "- **공식 문서 - 조직 정책 제약 조건 목록**: ( https://cloud.google.com/resource-manager/docs/organization-policy/org-policy-constraints )",
      "",
      "---",
      "",
      "## 4. 자원 정리 안내 (Teardown)",
      "본 도구는 순수 감사 로그 조회 도구이므로 별도의 자원 정리 작업이 필요하지 않다.",
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


def main():
  parser = argparse.ArgumentParser(
      description="GCP 조직 정책(Organization Policy) 위반 감사 추적 및 복구 처방 도구"
  )
  days_val = os.getenv("DAYS")
  limit_val = os.getenv("LIMIT_COUNT")
  parser.add_argument(
      "-p",
      "--project",
      default=os.getenv("PROJECT_ID") or None,
      help="GCP 프로젝트 ID (미입력 시 활성 프로젝트 자동 감지)",
  )
  parser.add_argument(
      "-d",
      "--days",
      type=int,
      default=int(days_val) if days_val else 7,
      help="조회 대상 최근 기간 일수 (기본값: 7)",
  )
  parser.add_argument(
      "-l",
      "--limit",
      type=int,
      default=int(limit_val) if limit_val else 5,
      help="조회 대상 실패 로그 최대 건수 (기본값: 5)",
  )
  parser.add_argument(
      "--dry-run",
      action="store_true",
      help="실제 Cloud Logging 호출 없이 가상 조직 정책 위반 시뮬레이션을 실행한다",
  )
  parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
  args = parser.parse_args()
  if getattr(args, "config", False):
      run_config_mode("org-policy-resolver")
      return

  reported_project = "sample-project-id" if args.dry_run else (args.project or get_default_project(is_dry_run=args.dry_run))

  if args.dry_run:
    print("\n[데모 실행] --dry-run 모드가 활성화되어 가상 조직 정책 위반 리포트를 시뮬레이션한다.")
    violations = get_mock_violations()
    report_violations(violations, reported_project, args.days)
  else:
    print(f"\n[진행] 프로젝트 '{reported_project}' 최근 {args.days}일 조직 정책 위반 감사 로그 조회 중 (최대 {args.limit}건)...")
    violations = fetch_violations(reported_project, args.days, args.limit)
    report_violations(violations, reported_project, args.days)
    print("=" * 72)
    print("[자원 정리 안내 (Teardown)]")
    print("본 도구는 순수 감사 로그 조회 도구이므로 별도의 자원 정리 작업이 필요하지 않다.")
    print("=" * 72 + "\n")

  script_dir = os.path.dirname(os.path.abspath(__file__))
  report_file_path = os.path.join(script_dir, "report.md")
  report_content = build_markdown_report(violations, reported_project, args.days, args.dry_run)
  save_markdown_report(report_content, report_file_path)


if __name__ == "__main__":
  main()
