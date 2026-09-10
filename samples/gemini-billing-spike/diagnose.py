#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Gemini API Cost & Usage Spike Diagnostic Tool.

Cloud Monitoring API의 서비스 런타임 지표를 활용하여 데이터 액세스 감사 로그(Audit Logs)가
꺼져 있는 환경에서도 자격 증명(API Key, 서비스 계정, OAuth2)별 호출 추이를 규명합니다.
"""

import argparse
from collections import defaultdict
import datetime
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


def get_gcp_project_id(cli_project: str | None = None, is_dry_run: bool = False, fallback_demo: str = "demo-project") -> str | None:
  """우선순위에 따라 활성 GCP 프로젝트 ID를 결정합니다."""
  if cli_project:
    return cli_project
  for env_var in ("GOOGLE_CLOUD_PROJECT", "PROJECT_ID", "CLOUDSDK_CORE_PROJECT"):
    val = os.getenv(env_var)
    if val:
      return val
  # gcloud config CLI 대체 조회
  try:
    res = subprocess.run(
        ["gcloud", "config", "get-value", "project"],
        capture_output=True,
        text=True,
        check=False,
    )
    project = res.stdout.strip()
    if project and project != "(unset)":
      return project
  except Exception:
    pass

  if is_dry_run or not sys.stdin.isatty():
    return fallback_demo

  try:
    res = subprocess.run(
        ["gcloud", "projects", "list", "--format=value(projectId)", "--limit=5"],
        capture_output=True,
        text=True,
    )
    projects = [p.strip() for p in res.stdout.splitlines() if p.strip()]
    if projects:
      print("\n[?] 대상 GCP 프로젝트가 지정되지 않았습니다. 현재 접근 가능한 프로젝트 목록:")
      for idx, p in enumerate(projects, 1):
        print(f"  [{idx}] {p}")
      print(f"  [{len(projects) + 1}] 직접 입력 (Custom Input)")
      choice = input(f"선택할 번호를 입력하세요 [1-{len(projects) + 1}] (Enter 시 1번): ").strip()
      if not choice or choice == "1":
        return projects[0]
      if choice.isdigit() and 1 <= int(choice) <= len(projects):
        return projects[int(choice) - 1]
      if choice == str(len(projects) + 1):
        custom = input("프로젝트 ID를 직접 입력하세요: ").strip()
        if custom:
          return custom
  except Exception:
    pass

  return None


def get_access_token() -> str | None:
  """Google ADC(Application Default Credentials)를 통해 인증 토큰을 발급받습니다."""
  try:
    import google.auth
    import google.auth.transport.requests

    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token
  except Exception:
    # gcloud auth CLI 대체 시도
    try:
      res = subprocess.run(
          ["gcloud", "auth", "print-access-token"],
          capture_output=True,
          text=True,
          check=False,
      )
      token = res.stdout.strip()
      if token:
        return token
    except Exception:
      pass
  return None


def fetch_monitoring_metrics(project_id: str, days: int, access_token: str) -> dict:
  """Cloud Monitoring REST API를 호출하여 시계열 메트릭을 수집합니다."""
  now = datetime.datetime.now(datetime.timezone.utc)
  start_time = (now - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
  end_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")

  metric_filter = (
      'metric.type="serviceruntime.googleapis.com/api/request_count" AND '
      '(resource.labels.service="aiplatform.googleapis.com" OR '
      'resource.labels.service="generativelanguage.googleapis.com")'
  )

  url = f"https://monitoring.googleapis.com/v3/projects/{project_id}/timeSeries"
  params = {
      "filter": metric_filter,
      "interval.startTime": start_time,
      "interval.endTime": end_time,
  }
  full_url = f"{url}?{urllib.parse.urlencode(params)}"

  req = urllib.request.Request(
      full_url,
      headers={"Authorization": f"Bearer {access_token}"},
  )
  try:
    with urllib.request.urlopen(req) as resp:
      return json.loads(resp.read().decode("utf-8"))
  except urllib.error.HTTPError as e:
    err_body = e.read().decode("utf-8", errors="replace")
    print(f"[오류] Cloud Monitoring API 호출 실패 (HTTP {e.code}): {err_body}", file=sys.stderr)
    sys.exit(1)
  except Exception as e:
    print(f"[오류] 데이터 요청 중 네트워크 예외 발생: {e}", file=sys.stderr)
    sys.exit(1)


def parse_and_report(project_id: str, days: int, data: dict):
  """수집된 메트릭 데이터를 자격 증명, 서비스, 메서드별로 집계하고 가이드를 출력합니다."""
  time_series = data.get("timeSeries", [])
  print("=" * 72)
  print("[진단 결과] 제미나이(Gemini) 사용량 및 비용 급증 원인 분석 리포트")
  print(f"   - 대상 프로젝트: {project_id}")
  print(f"   - 조회 대상 기간: 최근 {days}일")
  print("=" * 72)

  if not time_series:
    print(f"\n[안내] 최근 {days}일 동안 대상 API 호출 메트릭이 기록되지 않았다.")
    print("      (해당 기간 동안 API 호출이 없었거나, 아직 지표가 전파되지 않았을 수 있다.)\n")
    return

  credential_counts = defaultdict(int)
  method_counts = defaultdict(int)
  service_counts = defaultdict(int)
  total_calls = 0

  for ts in time_series:
    metric = ts.get("metric", {})
    resource = ts.get("resource", {})
    labels = metric.get("labels", {})
    r_labels = resource.get("labels", {})

    cred_id = r_labels.get("credential_id") or labels.get("credential_id", "unknown-credential")
    service_name = r_labels.get("service") or labels.get("service", "unknown-service")
    method_name = r_labels.get("method") or labels.get("method", "unknown-method")

    ts_total = sum(int(pt.get("value", {}).get("int64Value", "0")) for pt in ts.get("points", []))
    credential_counts[cred_id] += ts_total
    method_counts[method_name] += ts_total
    service_counts[service_name] += ts_total
    total_calls += ts_total

  print(f"\n총 집계된 API 호출 수: {total_calls:,} 건 (시계열 레코드: {len(time_series)}개)\n")

  # 1. 자격 증명별 집계
  print("┌" + "─" * 70 + "┐")
  print(f"│ {'1. 호출 주체(자격 증명)별 점유율 및 호출 횟수':<56} │")
  print("├" + "─" * 70 + "┤")
  for cred, count in sorted(credential_counts.items(), key=lambda x: x[1], reverse=True):
    pct = (count / total_calls * 100) if total_calls > 0 else 0
    cred_display = (cred[:42] + "..") if len(cred) > 44 else cred
    print(f"│  - {cred_display:<44} : {count:>8,}회 ({pct:5.1f}%) │")
  print("└" + "─" * 70 + "┘")

  # 2. 서비스 및 메서드별 집계
  print("\n[2. 호출된 서비스 및 API 메서드]")
  for s_name, count in sorted(service_counts.items(), key=lambda x: x[1], reverse=True):
    svc_desc = "Vertex AI Gemini" if "aiplatform" in s_name else "Google AI Studio (Developer API)"
    print(f"  - {s_name} ({svc_desc}): {count:,}회")

  print("\n[상위 호출 메서드]")
  for m_name, count in sorted(method_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
    print(f"  - {m_name}: {count:,}회")

  # 3. 조치 가이드
  print("\n" + "=" * 72)
  print("[추천 즉시 조치 가이드]")
  print("=" * 72)

  has_api_key = any("apikey:" in cred for cred in credential_counts)
  has_sa = any("serviceAccount:" in cred for cred in credential_counts)
  has_oauth = any("oauth2:" in cred for cred in credential_counts)

  if has_api_key:
    print("\n[API 키 발견] 'apikey:AIzaSy...' 형태의 호출 감지:")
    print("  1. 소스 코드나 클라이언트 앱에 API 키가 노출되었을 가능성이 있다.")
    print("  2. GCP 콘솔 사용자 인증 정보 페이지로 이동:")
    print(f"     사용자 인증 정보 콘솔 ( https://console.cloud.google.com/apis/credentials?project={project_id} )")
    print("  3. 해당 키를 찾아 'API 제한사항'을 점검하거나, 즉시 삭제 또는 재발급 조치한다.")

  if has_sa:
    print("\n[서비스 계정 발견] 'serviceAccount:...' 형태의 호출 감지:")
    print("  1. 백엔드 배치 잡이나 유출된 서비스 계정 키 파일(JSON)을 통한 호출이다.")
    print("  2. GCP 콘솔 서비스 계정 페이지로 이동:")
    print(f"     서비스 계정 콘솔 ( https://console.cloud.google.com/iam-admin/serviceaccounts?project={project_id} )")
    print("  3. 해당 계정의 활성 키를 점검하고 미사용 키는 즉시 삭제 조치한다.")

  if has_oauth:
    print("\n[OAuth2 클라이언트 발견] 'oauth2:...' 형태의 호출 감지:")
    print("  1. 등록된 웹/모바일 앱 클라이언트를 통해 사용자 인증 후 호출된 내역이다.")
    print(f"     사용자 인증 정보 콘솔 ( https://console.cloud.google.com/apis/credentials?project={project_id} )")

  print("\n추가 비용 누수 방지 권장 사항:")
  print(f"   - Cloud Billing 예산 설정 ( https://console.cloud.google.com/billing/budgets )")
  print(f"   - IAM 및 관리자 할당량 설정 ( https://console.cloud.google.com/iam-admin/quotas?project={project_id} )")
  print("=" * 72 + "\n")


def get_mock_metrics() -> dict:
  """단위 테스트 및 데모 체험을 위한 가상 메트릭 데이터를 반환합니다."""
  return {
      "timeSeries": [
          {
              "metric": {
                  "labels": {
                      "credential_id": "apikey:AIzaSyB1234567890abcdefghijklmnopqr",
                      "method": "GenerateContent",
                  }
              },
              "resource": {
                  "labels": {
                      "service": "aiplatform.googleapis.com",
                  }
              },
              "points": [{"value": {"int64Value": "135200"}}],
          },
          {
              "metric": {
                  "labels": {
                      "credential_id": "serviceAccount:gemini-batch-sa@demo-ai-project.iam.gserviceaccount.com",
                      "method": "StreamGenerateContent",
                  }
              },
              "resource": {
                  "labels": {
                      "service": "aiplatform.googleapis.com",
                  }
              },
              "points": [{"value": {"int64Value": "13050"}}],
          },
      ]
  }


def main():
  parser = argparse.ArgumentParser(
      description="Gemini API 비용 및 호출 급증 원인 자가 진단 도구"
  )
  parser.add_argument(
      "-p",
      "--project",
      help="분석 대상 GCP 프로젝트 ID (기본값: 환경 변수 또는 gcloud 기본 프로젝트)",
  )
  lookback_env = os.getenv("LOOKBACK_DAYS")
  parser.add_argument(
      "-d",
      "--days",
      type=int,
      default=int(lookback_env) if lookback_env else 90,
      help="분석 조회 기간(일 수, 기본값: 90)",
  )
  parser.add_argument(
      "--dry-run",
      "--demo",
      action="store_true",
      help="실제 GCP 호출 없이 가상 샘플 데이터로 진단 리포트를 출력하는 데모 모드",
  )
  args = parser.parse_args()

  if args.dry_run:
    print("\n[데모 실행] --dry-run 모드가 활성화되어 가상 샘플 데이터를 기반으로 리포트를 시뮬레이션한다.")
    demo_project = args.project or "demo-gemini-project"
    parse_and_report(demo_project, args.days, get_mock_metrics())
    return

  project_id = get_gcp_project_id(args.project, is_dry_run=args.dry_run)
  if not project_id:
    print(
        "[오류] 분석할 GCP 프로젝트 ID를 확인할 수 없다.\n"
        "      --project 옵션을 지정하거나 'gcloud config set project <ID>' 명령어로 설정한다.\n"
        "      (참고: 사전 결과 확인은 '--dry-run' 옵션을 사용한다.)",
        file=sys.stderr,
    )
    sys.exit(1)

  token = get_access_token()
  if not token:
    print(
        "[오류] GCP 인증 토큰을 획득하지 못했다.\n"
        "      'gcloud auth application-default login' 또는 'gcloud auth login'을 실행한다.\n"
        "      (참고: 사전 결과 확인은 '--dry-run' 옵션을 사용한다.)",
        file=sys.stderr,
    )
    sys.exit(1)

  print(f"\n[1/2] Cloud Monitoring API에서 '{project_id}'의 최근 {args.days}일간 메트릭 수집 중...")
  data = fetch_monitoring_metrics(project_id, args.days, token)

  print("[2/2] 호출 데이터 분석 및 요약 완료.\n")
  parse_and_report(project_id, args.days, data)


if __name__ == "__main__":
  main()
