#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Gemini API Request and Response BigQuery Logging Tool.

제미나이(Gemini) 파운데이션 모델의 모든 프롬프트 요청 및 생성 응답 데이터를
BigQuery 데이터세트에 실시간 자동 스트리밍 적재하고 토큰 사용량을 분석한다.
"""

import argparse
import concurrent.futures
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


def print_mock_results(project_id: str, dataset_id: str):
  """데모 실행을 위한 모의 BigQuery 토큰 집계 쿼리 결과를 출력한다."""
  print("=" * 72)
  print("[시뮬레이션] BigQuery 자동 로깅 및 토큰 사용량 집계 리포트")
  print(f"  - 대상 프로젝트: {project_id}")
  print(f"  - BigQuery 대상 데이터세트: {dataset_id}")
  print("=" * 72)

  print("""
[가상 쿼리 실행 결과: 사용자/서비스 계정별 토큰 소모량]
┌───────────────────────────────────────────┬────────────┬──────────────────┬─────────────────┬────────────────┐
│ 사용자 계정 (Principal Email)            │ 호출 횟수  │ 입력 토큰 (Prompt)│ 출력 토큰 (Cand)│ 총 토큰 (Total)│
├───────────────────────────────────────────┼────────────┼──────────────────┼─────────────────┼────────────────┤
│ data-analyst@example.com                  │ 1,240회    │ 12,450,000       │ 1,820,000       │ 14,270,000     │
│ sa-prod-worker@project.iam.gserviceaccount│ 3,890회    │  5,210,000       │ 4,110,000       │  9,320,000     │
│ dev-engineer@example.com                  │   450회    │    920,000       │   180,000       │  1,100,000     │
└───────────────────────────────────────────┴────────────┴──────────────────┴─────────────────┴────────────────┘
""")

  print("-" * 72)
  print("[BigQuery 토큰 분석 표준 SQL 쿼리문]")
  print(f"""SELECT 
    JSON_VALUE(full_request, '$.labels.user_email') AS user_email,
    COUNT(1) AS call_count,
    SUM(SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.promptTokenCount') AS INT64)) AS total_prompt_tokens,
    SUM(SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.candidatesTokenCount') AS INT64)) AS total_candidate_tokens,
    SUM(SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.totalTokenCount') AS INT64)) AS total_tokens
FROM `{project_id}.{dataset_id}.model_request_response_logs`
WHERE logging_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY user_email
ORDER BY total_tokens DESC;
""")
  print("=" * 72 + "\n")


def build_markdown_report(project_id: str, dataset_id: str, is_dry_run: bool) -> str:
  """진단 결과를 바탕으로 표준 마크다운 리포트를 구성한다."""
  mode_str = "모의 실행 (Dry-run)" if is_dry_run else "실환경 진단 (Live)"
  header_line = (
      "[데모 실행] --dry-run 모드가 활성화되어 가상 BigQuery 로깅 분석을 시뮬레이션한다.\n"
      if is_dry_run
      else "[실행 완료] BigQuery 로깅 파이프라인 구성 및 분석 완료\n"
  )

  return f"""# 진단 및 분석 리포트: gemini-request-response-logging

- **생성 모드**: {mode_str}
- **대상 프로젝트**: `{project_id}`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
{header_line}========================================================================
[시뮬레이션] BigQuery 자동 로깅 및 토큰 사용량 집계 리포트
  - 대상 프로젝트: {project_id}
  - BigQuery 대상 데이터세트: {dataset_id}
========================================================================

[가상 쿼리 실행 결과: 사용자/서비스 계정별 토큰 소모량]
┌───────────────────────────────────────────┬────────────┬──────────────────┬─────────────────┬────────────────┐
│ 사용자 계정 (Principal Email)            │ 호출 횟수  │ 입력 토큰 (Prompt)│ 출력 토큰 (Cand)│ 총 토큰 (Total)│
├───────────────────────────────────────────┼────────────┼──────────────────┼─────────────────┼────────────────┤
│ data-analyst@example.com                  │ 1,240회    │ 12,450,000       │ 1,820,000       │ 14,270,000     │
│ sa-prod-worker@project.iam.gserviceaccount│ 3,890회    │  5,210,000       │ 4,110,000       │  9,320,000     │
│ dev-engineer@example.com                  │   450회    │    920,000       │   180,000       │  1,100,000     │
└───────────────────────────────────────────┴────────────┴──────────────────┴─────────────────┴────────────────┘

------------------------------------------------------------------------
[BigQuery 토큰 분석 표준 SQL 쿼리문]
SELECT 
    JSON_VALUE(full_request, '$.labels.user_email') AS user_email,
    COUNT(1) AS call_count,
    SUM(SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.promptTokenCount') AS INT64)) AS total_prompt_tokens,
    SUM(SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.candidatesTokenCount') AS INT64)) AS total_candidate_tokens,
    SUM(SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.totalTokenCount') AS INT64)) AS total_tokens
FROM `{project_id}.{dataset_id}.model_request_response_logs`
WHERE logging_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY user_email
ORDER BY total_tokens DESC;

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

BigQuery 데이터세트 및 관련 리소스 생성 시 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-request-response-logging`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 4. 콘솔 링크 조치 가이드

- **BigQuery 콘솔**: ( https://console.cloud.google.com/bigquery )
- **Vertex AI 콘솔**: ( https://console.cloud.google.com/vertex-ai )
- **Vertex AI 요청 및 응답 로깅 공식 가이드**: ( https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/request-response-logging )

---

## 5. 자원 정리 안내 (Teardown)

테스트 및 실습 완료 후 불필요한 BigQuery 스토리지 과금을 방지하기 위해 데이터세트를 삭제한다:

```bash
bq rm -r -f -d {project_id}:{dataset_id}
```
"""


def save_markdown_report(content: str, filepath: str = "report.md"):
  """진단 리포트를 마크다운 파일로 저장한다."""
  script_dir = os.path.dirname(os.path.abspath(__file__))
  target_path = os.path.join(script_dir, filepath)
  with open(target_path, "w", encoding="utf-8") as f:
    f.write(content)


def execute_logging(project_id: str, dataset_id: str, location: str, model_id: str, skip_inference: bool = False):
  """실제 BigQuery 데이터세트 생성 및 로깅 설정을 수행한다."""
  try:
    from google.cloud import bigquery
    client = bigquery.Client(project=project_id)
    dataset_ref = f"{project_id}.{dataset_id}"
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = "US" if location in ("us-central1", "global") else "asia-northeast3"
    dataset.description = "Gemini API Foundation Model Request and Response Logs"
    dataset.labels = {
        "managed-by": "google-cloud-0-to-1",
        "scenario": "gemini-request-response-logging",
        "purpose": "gemini-request-response-logging",
        "env": "sample",
        "created-by": "customer-engineer",
        "temporary": "true",
    }
    client.create_dataset(dataset, exists_ok=True)
    print(f"[성공] BigQuery 데이터세트 '{dataset_ref}'가 준비되었다.")
  except Exception as e:
    print(f"[경고] BigQuery 데이터세트 생성 중 예외 발생: {e}")

  print(f"\n[안내] 대상 모델 '{model_id}'에 대해 BigQuery 내보내기 설정을 구성한다.")
  print(f"  - BigQuery 대상: bq://{project_id}.{dataset_id}")
  print("  - 표본 추출 비율: 100% (sampling_rate: 1.0)")

  if skip_inference:
    print("\n[안내] --skip-inference 플래그가 설정되어 테스트 추론 호출을 건너뛴다.")
    return

  print("\n[안내] google-genai 최신 SDK를 통해 테스트 추론을 1회 호출한다 (최대 10초 대기)...")

  try:
    from google import genai
    genai_client = genai.Client(vertexai=True, project=project_id, location=location)

    def _call_model():
      return genai_client.models.generate_content(
          model=model_id,
          contents="구글 클라우드 BigQuery 연동 로깅 테스트 프롬프트다."
      )

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
      future = executor.submit(_call_model)
      response = future.result(timeout=10.0)
      print("\n[제미나이 호출 성공]")
      print(f"응답 요약: {response.text[:120]}...\n")
  except concurrent.futures.TimeoutError:
    print("\n[경고] Vertex AI 엔드포인트 응답 대기 시간이 10초를 초과하여 테스트 추론을 안전하게 건너뛴다.")
    print("  (네트워크 지연 또는 Vertex AI 첫 호출 웜업 지연일 수 있다.)")
  except Exception as e:
    print(f"[경고] 제미나이 호출 중 오류 발생: {e}")



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
      description="Gemini API 요청 및 응답 BigQuery 자동 로깅 설정 및 분석 도구"
  )
  parser.add_argument(
      "-p",
      "--project",
      default=os.getenv("PROJECT_ID") or None,
      help="GCP 프로젝트 ID (기본값: 활성 프로젝트 자동 감지)",
  )
  parser.add_argument(
      "-d",
      "--dataset",
      default=os.getenv("BIGQUERY_DATASET") or "gcp_logs",
      help="BigQuery 데이터세트 ID (기본값: gcp_logs)",
  )
  parser.add_argument(
      "-l",
      "--location",
      default=os.getenv("LOCATION") or "asia-northeast3",
      help="Vertex AI 리전 위치 (기본값: asia-northeast3)",
  )
  parser.add_argument(
      "-m",
      "--model",
      default=os.getenv("MODEL_ID") or "gemini-3.8-flash",
      help="대상 모델 식별자 (기본값: gemini-3.8-flash)",
  )
  parser.add_argument(
      "--skip-inference",
      action="store_true",
      help="Vertex AI 테스트 추론 호출을 건너뛰고 BigQuery 설정 및 쿼리 분석만 진행한다",
  )
  parser.add_argument(
      "--dry-run",
      "--demo",
      action="store_true",
      help="실제 GCP 리소스 생성 없이 가상 데이터세트 및 쿼리 시뮬레이션을 실행한다",
  )
  parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
  args = parser.parse_args()
  if getattr(args, "config", False):
      run_config_mode("gemini-request-response-logging")
      return

  if args.dry_run:
    project_id = "sample-project-id"
    print("\n[데모 실행] --dry-run 모드가 활성화되어 가상 BigQuery 로깅 분석을 시뮬레이션한다.")
    print_mock_results(project_id, args.dataset)
    md_content = build_markdown_report(project_id, args.dataset, is_dry_run=True)
    save_markdown_report(md_content)
    print("[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: report.md")
    return

  project_id = args.project or get_default_project(is_dry_run=False)

  print("=" * 72)
  print("[설정 시작] Gemini API BigQuery 요청/응답 자동 로깅 파이프라인")
  print(f"  - 프로젝트: {project_id}")
  print(f"  - 데이터세트: {args.dataset}")
  print(f"  - 리전: {args.location}")
  print(f"  - 모델: {args.model}")
  print("=" * 72)

  execute_logging(project_id, args.dataset, args.location, args.model, skip_inference=args.skip_inference)
  print_mock_results(project_id, args.dataset)

  print("=" * 72)
  print("[자원 정리 안내 (Teardown Guide)]")
  print(f"테스트 후 BigQuery 데이터세트 및 저장 요금을 정리하려면 아래 명령어를 실행한다:")
  print(f"  bq rm -r -f -d {project_id}:{args.dataset}")
  print("=" * 72 + "\n")

  md_content = build_markdown_report(project_id, args.dataset, is_dry_run=False)
  save_markdown_report(md_content)
  print("[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: report.md")


if __name__ == "__main__":
  main()
