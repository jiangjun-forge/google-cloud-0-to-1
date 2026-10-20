#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""GCP IAM Permission Denial Resolver.

최근 발생한 GCP 데이터 액세스 권한 거부(Permission Denied / 403) 감사 로그를 역추적하여
호출 주체별로 필요한 최소 권한 IAM 역할과 복구 gcloud 명령어를 원클릭으로 처방한다.
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


def get_default_project(is_dry_run: bool = False, fallback_demo: str = "sample-project-id") -> str:
  """gcloud 설정 및 실시간 프로젝트 목록에서 활성 프로젝트를 탐색/선택한다."""
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


def get_mock_failures():
  """데모 실행을 위한 가상 권한 거부 로그 목록을 반환한다."""
  return [
      {
          "principal": "backend-developer@company.com",
          "service": "aiplatform.googleapis.com",
          "method": "google.cloud.aiplatform.v1beta1.PredictionService.GenerateContent",
          "message": "Permission 'aiplatform.endpoints.predict' denied on resource",
      },
      {
          "principal": "batch-pipeline-sa@my-prod.iam.gserviceaccount.com",
          "service": "bigquery.googleapis.com",
          "method": "google.cloud.bigquery.v2.JobService.InsertJob",
          "message": "Access Denied: Table my-prod:gcp_logs.request_response_logging: Permission bigquery.tables.getData denied",
      },
      {
          "principal": "intern-analyst@company.com",
          "service": "storage.googleapis.com",
          "method": "storage.objects.get",
          "message": "Access denied: storage.objects.get for bucket gs://my-ml-datasets",
      },
  ]


def map_role(service_name: str) -> tuple[str, str]:
  """실패 서비스에 적합한 최소 권한 역할과 설명을 매핑한다."""
  if "aiplatform" in service_name:
    return "roles/aiplatform.user", "Gemini API 호출 및 Vertex AI 파운데이션 모델 추론 권한"
  elif "bigquery" in service_name:
    return "roles/bigquery.dataEditor", "BigQuery 데이터세트 수정 및 테이블 데이터 편집 권한"
  elif "storage" in service_name:
    return "roles/storage.objectViewer", "Cloud Storage 버킷 객체 조회 뷰어 권한"
  elif "logging" in service_name:
    return "roles/logging.viewer", "Cloud Logging 로그 조회 뷰어 권한"
  else:
    return "roles/viewer", "서비스 기본 리소스 조회 뷰어 권한"


def report_failures(failures: list[dict], project_id: str, days: int):
  """진단 리포트 및 해결 명령어를 출력한다."""
  print("=" * 72)
  print("[진단 결과] GCP IAM 권한 거부(403) 감사 추적 및 해결 처방 리포트")
  print(f"  - 대상 프로젝트: {project_id}")
  print(f"  - 조회 기간: 최근 {days}일")
  print("=" * 72)

  if not failures:
    print("\n[성공] 데이터 액세스 권한 거부(403) 실패 감사 로그가 발견되지 않았다. 안전하다!\n")
    return

  print(f"\n발견된 권한 거부 실패 내역: {len(failures)}건\n")

  for idx, f in enumerate(failures, start=1):
    role, role_desc = map_role(f["service"])
    member_type = "serviceAccount" if "gserviceaccount.com" in f["principal"] else "user"

    print(f"[실패 건 #{idx}]")
    print(f"  - 실패 주체 계정: {f['principal']}")
    print(f"  - 요청 대상 서비스: {f['service']}")
    print(f"  - 실행 실패 액션: {f['method']}")
    print(f"  - 실제 오류 내용: {f['message']}")
    print("  [정밀 처방 역할 추천]")
    print(f"    - 권장 역할: {role}")
    print(f"    - 역할 상세: {role_desc}")
    print("  [즉시 조치 가능한 원클릭 gcloud 해결 명령어]")
    print(f"    gcloud projects add-iam-policy-binding \"{project_id}\" \\")
    print(f"      --member=\"{member_type}:{f['principal']}\" \\")
    print(f"      --role=\"{role}\"")
    print("-" * 72)

  print("=" * 72 + "\n")


def fetch_failures(project_id: str, days: int, limit: int) -> list[dict]:
  """gcloud logging read 명령으로 403 권한 거부 감사 로그를 조회한다."""
  start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
  log_filter = (
      f'logName:"projects/{project_id}/logs/cloudaudit.googleapis.com%2Fdata_access" AND '
      f'(protoPayload.status.code=7 OR protoPayload.status.message:"Permission denied" OR protoPayload.status.message:"Forbidden") AND '
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

      results.append({
          "principal": auth.get("principalEmail", "미식별"),
          "service": proto.get("serviceName", "unknown"),
          "method": proto.get("methodName", "unknown"),
          "message": status.get("message", "Permission denied"),
      })
  except Exception as e:
    print(f"[경고] 로그 JSON 파싱 중 오류: {e}")
  return results


def build_markdown_report(failures: list[dict], project_id: str, days: int, is_dry_run: bool) -> str:
  """진단 결과를 표준 마크다운 리포트(report.md) 형식으로 생성한다."""
  mode_str = "모의 실행 (Dry-run)" if is_dry_run else "실제 환경 진단 (Live)"

  lines = []
  if is_dry_run:
    lines.append("[데모 실행] --dry-run 모드가 활성화되어 가상 권한 거부 리포트를 시뮬레이션한다.")
  lines.append("=" * 72)
  lines.append("[진단 결과] GCP IAM 권한 거부(403) 감사 추적 및 해결 처방 리포트")
  lines.append(f"  - 대상 프로젝트: {project_id}")
  lines.append(f"  - 조회 기간: 최근 {days}일")
  lines.append("=" * 72)

  if not failures:
    lines.append("\n[성공] 데이터 액세스 권한 거부(403) 실패 감사 로그가 발견되지 않았다. 안전하다!\n")
  else:
    lines.append(f"\n발견된 권한 거부 실패 내역: {len(failures)}건\n")
    for idx, f in enumerate(failures, start=1):
      role, role_desc = map_role(f["service"])
      member_type = "serviceAccount" if "gserviceaccount.com" in f["principal"] else "user"
      lines.append(f"[실패 건 #{idx}]")
      lines.append(f"  - 실패 주체 계정: {f['principal']}")
      lines.append(f"  - 요청 대상 서비스: {f['service']}")
      lines.append(f"  - 실행 실패 액션: {f['method']}")
      lines.append(f"  - 실제 오류 내용: {f['message']}")
      lines.append("  [정밀 처방 역할 추천]")
      lines.append(f"    - 권장 역할: {role}")
      lines.append(f"    - 역할 상세: {role_desc}")
      lines.append("  [즉시 조치 가능한 원클릭 gcloud 해결 명령어]")
      lines.append(f"    gcloud projects add-iam-policy-binding \"{project_id}\" \\")
      lines.append(f"      --member=\"{member_type}:{f['principal']}\" \\")
      lines.append(f"      --role=\"{role}\"")
      lines.append("-" * 72)
  lines.append("=" * 72)

  console_output = "\n".join(lines)

  report = f"""# 진단 및 분석 리포트: iam-permission-resolver

- **생성 모드**: {mode_str}
- **대상 프로젝트**: `{project_id}`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
{console_output}
```

---

## 2. 사내 거버넌스 4대 필수 표준 라벨링

신규 서비스 계정 생성 및 연계 리소스 배포 시 다음 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `iam-permission-resolver`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 3. 콘솔 링크 조치 가이드

- **Cloud IAM 관리 콘솔**: ( https://console.cloud.google.com/iam-admin/iam )
- **Cloud Logging 감사 로그 탐색기**: ( https://console.cloud.google.com/logs/query )

---

## 4. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
"""
  return report


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
      description="GCP IAM 권한 거부(403) 로그 역추적 및 원클릭 복구 처방 도구"
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
      help="실제 Cloud Logging 호출 없이 가상 권한 거부 시뮬레이션을 실행한다",
  )
  parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
  args = parser.parse_args()
  if getattr(args, "config", False):
      run_config_mode("iam-permission-resolver")
      return

  project_id = "sample-project-id" if args.dry_run else (args.project or get_default_project(is_dry_run=args.dry_run))

  if args.dry_run:
    print("\n[데모 실행] --dry-run 모드가 활성화되어 가상 권한 거부 리포트를 시뮬레이션한다.")
    failures = get_mock_failures()
    report_failures(failures, project_id, args.days)
    report_md = build_markdown_report(failures, project_id, args.days, is_dry_run=True)
    save_markdown_report(report_md)
    print("\n[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: report.md")
    return

  print(f"\n[진행] 프로젝트 '{project_id}' 최근 {args.days}일 데이터 액세스 권한 거부 감사 로그 조회 중 (최대 {args.limit}건)...")

  failures = fetch_failures(project_id, args.days, args.limit)
  report_failures(failures, project_id, args.days)

  report_md = build_markdown_report(failures, project_id, args.days, is_dry_run=False)
  save_markdown_report(report_md)
  print("\n[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: report.md")

  print("=" * 72)
  print("[자원 정리 안내 (Teardown Guide)]")
  print("본 도구는 순수 감사 로그 조회 도구이므로 별도의 자원 정리 작업이 필요하지 않다.")
  print("=" * 72 + "\n")


if __name__ == "__main__":
  main()
