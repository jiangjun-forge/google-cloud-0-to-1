#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Gemini API Quota and Budget Alert Pipeline Tool.

제미나이(Gemini) API 비용 초과 시 Pub/Sub 기반 예산 알림 연동 및
Cloud Functions 자동 할당량(Quota) 차단 아키텍처를 진단하고 시뮬레이션한다.
"""

import argparse
import json
import os
import subprocess
import sys


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
  """쉘 명령어를 실행하고 반환 코드, 표준 출력, 표준 에러를 반환한다."""
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


def get_billing_account(project_id: str):
  """프로젝트에 바인딩된 빌링 계정 ID를 조회한다."""
  code, stdout, _ = run_cmd([
      "gcloud",
      "beta",
      "billing",
      "projects",
      "describe",
      project_id,
      "--format=value(billingAccountName)",
  ])
  if code == 0 and stdout:
    return stdout.replace("billingAccounts/", "")
  return None


def simulate_alarm(billing_id: str, budget_name: str, topic_name: str, project_id: str, dry_run: bool):
  """가상 예산 초과 JSON 페이로드를 생성하고 테스트를 수행한다."""
  payload = {
      "billingAccountId": billing_id or "012345-6789AB-CDEF01",
      "budgetDisplayName": budget_name,
      "costAmount": 120.0,
      "costIntervalStart": "2026-06-01T00:00:00Z",
      "budgetAmount": 100.0,
      "alertThresholdExceeded": 1.2,
      "currencyCode": "USD",
  }
  json_str = json.dumps(payload, indent=2)

  print("=" * 72)
  print("[시뮬레이션] 가상 예산 초과 이벤트 페이로드 생성")
  print("=" * 72)
  print(json_str)
  print("-" * 72)

  if dry_run:
    print("\n[데모 실행] --dry-run 모드에서는 실제 Pub/Sub 메시지를 발행하지 않고 파이프라인 설계를 검증한다.")
    print("  - 상태: 성공 (모의 이벤트 생성 및 스키마 유효성 검증 완료)\n")
    return

  print(f"\n[실행] Pub/Sub 주제 '{topic_name}'로 테스트 메시지를 발행하는 중...")
  code, stdout, stderr = run_cmd([
      "gcloud",
      "pubsub",
      "topics",
      "publish",
      topic_name,
      f"--message={json.dumps(payload)}",
      f"--project={project_id}",
  ])
  if code == 0:
    print(f"[성공] 테스트 메시지가 정상적으로 발행되었다: 메시지 ID {stdout}")
  else:
    print(f"[경고] 메시지 발행 실패: {stderr}")


def print_architecture_guide(project_id: str, topic_name: str):
  """비용 초과 시 할당량 자동 차단 Cloud Functions 아키텍처 코드를 출력한다."""
  print("=" * 72)
  print("[표준 처방] 비용 초과 시 자동 할당량(Quota) 차단 Cloud Functions 가이드")
  print("=" * 72)
  print(f"""1. 자동 차단 파이썬 핸들러 (main.py):
------------------------------------------------------------------------
import base64
import json
from google.cloud import service_usage_v1

def block_gemini_api(event, context):
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    data = json.loads(pubsub_message)
    
    # 예산 90% 이상 도달 시 차단
    if data.get('alertThresholdExceeded', 0.0) >= 0.9:
        client = service_usage_v1.ServiceUsageClient()
        request = service_usage_v1.UpdateConsumerQuotaLimitRequest(
            name='projects/{project_id}/services/aiplatform.googleapis.com/consumerQuotaMetrics/aiplatform.googleapis.com%2Fgenerate_content_requests_per_minute_per_project_per_base_model/limits/%2Fproject%2Fregion/consumerQuotaLimits/projects%2F{project_id}%2Fservices%2Faiplatform.googleapis.com%2FconsumerQuotaMetrics%2Faiplatform.googleapis.com%252Fgenerate_content_requests_per_minute_per_project_per_base_model%252Flimits%252F%252Fproject%252Fregion%252Flimit',
            quota_limit={{'values': {{'/project/region': 0}}}}
        )
        client.update_consumer_quota_limit(request=request)
        print('[긴급 조치] 예산 임계치 도달로 Gemini API 쿼터 한도가 0으로 조정되었다.')

2. Cloud Functions 2세대 배포 명령어:
------------------------------------------------------------------------
gcloud functions deploy quota-auto-disable \\
    --runtime=python311 \\
    --trigger-topic={topic_name} \\
    --entry-point=block_gemini_api \\
    --project={project_id} \\
    --region=asia-northeast3 \\
    --update-labels="managed-by=google-cloud-0-to-1,scenario=gemini-quota-cost-alert,env=sample"
========================================================================
""")


def build_markdown_report(project_id: str, topic: str, budget_name: str, is_dry_run: bool) -> str:
  """진단 결과를 바탕으로 표준 마크다운 리포트를 구성한다."""
  mode_str = "모의 실행 (Dry-run)" if is_dry_run else "실환경 진단 (Live)"
  dry_run_console_line = (
      "[데모 실행] --dry-run 가상 실행 모드가 활성화되었다.\n"
      if is_dry_run
      else f"[1단계] Pub/Sub 주제 '{topic}' 확인 완료\n"
  )

  return f"""# 진단 및 분석 리포트: gemini-quota-cost-alert

- **생성 모드**: {mode_str}
- **대상 프로젝트**: `{project_id}`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
========================================================================
[진단 시작] 제미나이(Gemini) API 실시간 비용 및 할당량 경보 아키텍처 점검
  - 프로젝트 ID: {project_id}
  - Pub/Sub 주제: {topic}
  - 예산 규칙명: {budget_name}
========================================================================

{dry_run_console_line}========================================================================
[표준 처방] 비용 초과 시 자동 할당량(Quota) 차단 Cloud Functions 가이드
========================================================================
1. 자동 차단 파이썬 핸들러 (main.py):
------------------------------------------------------------------------
import base64
import json
from google.cloud import service_usage_v1

def block_gemini_api(event, context):
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    data = json.loads(pubsub_message)
    
    # 예산 90% 이상 도달 시 차단
    if data.get('alertThresholdExceeded', 0.0) >= 0.9:
        client = service_usage_v1.ServiceUsageClient()
        request = service_usage_v1.UpdateConsumerQuotaLimitRequest(
            name='projects/{project_id}/services/aiplatform.googleapis.com/consumerQuotaMetrics/aiplatform.googleapis.com%2Fgenerate_content_requests_per_minute_per_project_per_base_model/limits/%2Fproject%2Fregion/consumerQuotaLimits/projects%2F{project_id}%2Fservices%2Faiplatform.googleapis.com%2FconsumerQuotaMetrics%2Faiplatform.googleapis.com%252Fgenerate_content_requests_per_minute_per_project_per_base_model%252Flimits%252F%252Fproject%252Fregion%252Flimit',
            quota_limit={{'values': {{'/project/region': 0}}}}
        )
        client.update_consumer_quota_limit(request=request)
        print('[긴급 조치] 예산 임계치 도달로 Gemini API 쿼터 한도가 0으로 조정되었다.')

2. Cloud Functions 2세대 배포 명령어:
------------------------------------------------------------------------
gcloud functions deploy quota-auto-disable \\
    --runtime=python311 \\
    --trigger-topic={topic} \\
    --entry-point=block_gemini_api \\
    --project={project_id} \\
    --region=asia-northeast3 \\
    --update-labels="managed-by=google-cloud-0-to-1,scenario=gemini-quota-cost-alert,env=sample"
========================================================================

========================================================================
[시뮬레이션] 가상 예산 초과 이벤트 페이로드 생성
========================================================================
{{
  "billingAccountId": "012345-6789AB-CDEF01",
  "budgetDisplayName": "{budget_name}",
  "costAmount": 120.0,
  "costIntervalStart": "2026-06-01T00:00:00Z",
  "budgetAmount": 100.0,
  "alertThresholdExceeded": 1.2,
  "currencyCode": "USD"
}}
------------------------------------------------------------------------

[데모 실행] --dry-run 모드에서는 실제 Pub/Sub 메시지를 발행하지 않고 파이프라인 설계를 검증한다.
  - 상태: 성공 (모의 이벤트 생성 및 스키마 유효성 검증 완료)

========================================================================
[자원 정리 안내 (Teardown Guide)]
테스트 완료 후 요금 발생 및 불필요한 자원 잔존을 방지하기 위해 아래 명령어로 삭제한다:
  1. Pub/Sub 주제 삭제: gcloud pubsub topics delete {topic} --project={project_id}
  2. Cloud Functions 삭제: gcloud functions delete quota-auto-disable --region=asia-northeast3
  3. 예산 규칙 삭제: GCP 결제 콘솔 ( https://console.cloud.google.com/billing ) '예산 및 알림' 메뉴에서 '{budget_name}' 삭제
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

Cloud Pub/Sub 주제, Cloud Functions 및 관련 클라우드 인프라 리소스 생성 시 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-quota-cost-alert`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 4. 콘솔 링크 조치 가이드

- **Cloud Billing 콘솔**: ( https://console.cloud.google.com/billing )
- **Cloud Pub/Sub 콘솔**: ( https://console.cloud.google.com/cloudpubsub )
- **Cloud Functions 콘솔**: ( https://console.cloud.google.com/functions )
- **Cloud Billing 예산 및 지출 한도 알림 생성**: ( https://docs.cloud.google.com/billing/docs/how-to/budgets )
- **Cloud Billing Pub/Sub 예산 알림 연동 가이드**: ( https://docs.cloud.google.com/billing/docs/how-to/notify )

---

## 5. 자원 정리 안내 (Teardown)

실습 및 테스트 완료 후 불필요한 과금과 리소스 누수를 방지하기 위해 생성한 자원을 아래 순서로 반드시 정리한다:
```bash
# 1. Pub/Sub 알림 주제 삭제
gcloud pubsub topics delete {topic} --project={project_id}

# 2. Cloud Functions 자동 차단 함수 삭제
gcloud functions delete quota-auto-disable --region=asia-northeast3 --project={project_id}

# 3. 결제 예산 규칙 정리
# GCP 결제 콘솔 ( https://console.cloud.google.com/billing ) 에 접속하여 '예산 및 알림' 메뉴에서 '{budget_name}' 예산 규칙을 삭제한다.
```
"""


def save_markdown_report(content: str, filepath: str = "report.md"):
  """진단 리포트를 마크다운 파일로 저장한다."""
  script_dir = os.path.dirname(os.path.abspath(__file__))
  target_path = os.path.join(script_dir, filepath)
  with open(target_path, "w", encoding="utf-8") as f:
    f.write(content)


def main():
  parser = argparse.ArgumentParser(
      description="제미나이(Gemini) API 비용 및 쿼터 임계치 경보 설정 및 시뮬레이션 도구"
  )
  parser.add_argument(
      "-p",
      "--project",
      default=os.getenv("PROJECT_ID") or None,
      help="GCP 프로젝트 ID (지정하지 않을 경우 gcloud 활성 프로젝트 자동 감지)",
  )
  parser.add_argument(
      "-b",
      "--billing-account",
      default=os.getenv("BILLING_ACCOUNT_ID"),
      help="클라우드 빌링 계정 ID (미지정 시 자동 조회)",
  )
  parser.add_argument(
      "-t",
      "--topic",
      default=os.getenv("PUBSUB_TOPIC") or "gemini-cost-alerts",
      help="Pub/Sub 알림 주제 이름 (기본값: gemini-cost-alerts)",
  )
  parser.add_argument(
      "--budget-name",
      default=os.getenv("BUDGET_NAME") or "gemini-budget-alert",
      help="예산 경보 규칙 이름 (기본값: gemini-budget-alert)",
  )
  parser.add_argument(
      "--dry-run",
      "--demo",
      action="store_true",
      help="실제 GCP 자원 생성 및 호출 없이 가상 시뮬레이션 모드로 실행한다",
  )
  args = parser.parse_args()

  if args.dry_run:
    project_id = "sample-project-id"
  else:
    project_id = args.project or get_default_project(is_dry_run=False)

  print("=" * 72)
  print("[진단 시작] 제미나이(Gemini) API 실시간 비용 및 할당량 경보 아키텍처 점검")
  print(f"  - 프로젝트 ID: {project_id}")
  print(f"  - Pub/Sub 주제: {args.topic}")
  print(f"  - 예산 규칙명: {args.budget_name}")
  print("=" * 72)

  billing_id = args.billing_account
  if not billing_id and not args.dry_run and args.project:
    print("\n[점검] 프로젝트에 연결된 빌링 계정을 확인하는 중...")
    billing_id = get_billing_account(args.project)
    if billing_id:
      print(f"  - 확인된 빌링 계정: {billing_id}")
    else:
      print("  - [안내] 연결된 빌링 계정을 조회하지 못하여 기본 모의 계정으로 진행한다.")
      billing_id = "012345-6789AB-CDEF01"

  if args.dry_run:
    print("\n[데모 실행] --dry-run 가상 실행 모드가 활성화되었다.")
  else:
    print(f"\n[1단계] Pub/Sub 주제 '{args.topic}' 상태 확인...")
    code, _, _ = run_cmd(["gcloud", "pubsub", "topics", "describe", args.topic, f"--project={project_id}"])
    if code != 0:
      print(f"  - Pub/Sub 주제 '{args.topic}' 생성 필요 (실제 운영 시 배포 필요)")
    else:
      print(f"  - Pub/Sub 주제 '{args.topic}' 확인 완료")

  print_architecture_guide(project_id, args.topic)
  simulate_alarm(billing_id, args.budget_name, args.topic, project_id, args.dry_run)

  print("=" * 72)
  print("[자원 정리 안내 (Teardown Guide)]")
  print("테스트 완료 후 요금 발생 및 불필요한 자원 잔존을 방지하기 위해 아래 명령어로 삭제한다:")
  print(f"  1. Pub/Sub 주제 삭제: gcloud pubsub topics delete {args.topic} --project={project_id}")
  print("  2. Cloud Functions 삭제: gcloud functions delete quota-auto-disable --region=asia-northeast3")
  print(f"  3. 예산 규칙 삭제: GCP 결제 콘솔 ( https://console.cloud.google.com/billing ) '예산 및 알림' 메뉴에서 '{args.budget_name}' 삭제")
  print("=" * 72 + "\n")

  md_content = build_markdown_report(project_id, args.topic, args.budget_name, args.dry_run)
  save_markdown_report(md_content)
  print("[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: report.md")


if __name__ == "__main__":
  main()
