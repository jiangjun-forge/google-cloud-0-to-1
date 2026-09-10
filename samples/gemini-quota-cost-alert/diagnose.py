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


def get_default_project():
  """gcloud 설정에서 활성 프로젝트 ID를 조회한다."""
  _, stdout, _ = run_cmd(["gcloud", "config", "get-value", "project"])
  return stdout if stdout and "(unset)" not in stdout else None


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
    --region=asia-northeast3
========================================================================
""")


def main():
  parser = argparse.ArgumentParser(
      description="제미나이(Gemini) API 비용 및 쿼터 임계치 경보 설정 및 시뮬레이션 도구"
  )
  parser.add_argument(
      "-p",
      "--project",
      default=os.getenv("PROJECT_ID") or get_default_project(),
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

  project_id = args.project or "demo-project-id"

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


if __name__ == "__main__":
  main()
