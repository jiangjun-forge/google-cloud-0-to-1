#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Gemini API Resilience Pattern Checker.

제미나이(Gemini) API 호출 코드 내 429 에러 및 일시적 장애를 방어하기 위한
지수 백오프, 지터, 최대 재시도 제한, 폴백 모델 패턴 적용 여부를 정적 진단한다.
"""

import argparse
import os
from pathlib import Path
import re
import sys


def get_mock_findings():
  """데모 실행을 위한 가상 진단 결과를 반환한다."""
  return [
      {
          "file": "app/services/llm_client.py",
          "has_fallback": False,
          "has_jitter": False,
          "has_max_retries": False,
          "has_retry": False,
      },
      {
          "file": "batch_worker.py",
          "has_fallback": False,
          "has_jitter": False,
          "has_max_retries": True,
          "has_retry": True,
      },
  ]


def scan_file(file_path: Path) -> dict | None:
  """단일 소스 코드 파일을 검사하여 복원력 패턴 구비 여부를 분석한다."""
  try:
    content = file_path.read_text(encoding="utf-8", errors="ignore")
  except Exception:
    return None

  # 제미나이 호출 구문 감지
  gemini_call_pattern = re.compile(
      r"generate_content|generate_content_stream|generate_content_async|models\.generate_content"
  )
  if not gemini_call_pattern.search(content):
    return None

  has_fallback = bool(re.search(r"fallback|gemini-.*flash", content, re.IGNORECASE))
  has_jitter = bool(re.search(r"jitter|random|wait_random", content, re.IGNORECASE))
  has_max_retries = bool(re.search(r"stop_after|max_retries|stop=", content, re.IGNORECASE))
  has_retry = bool(re.search(r"retry|tenacity|backoff|sleep", content, re.IGNORECASE))

  return {
      "file": str(file_path),
      "has_fallback": has_fallback,
      "has_jitter": has_jitter,
      "has_max_retries": has_max_retries,
      "has_retry": has_retry,
  }


def scan_directory(scan_path: str) -> list[dict]:
  """지정한 디렉터리 내의 파이썬 및 쉘 스크립트 파일을 재귀 스캔한다."""
  results = []
  target_dir = Path(scan_path)
  if not target_dir.exists() or not target_dir.is_dir():
    print(f"[오류] 지정한 경로가 디렉터리가 아니거나 존재하지 않는다: {scan_path}", file=sys.stderr)
    sys.exit(1)

  for root, _, files in os.walk(target_dir):
    # 숨김 디렉터리 및 기타 라이브러리 경로 제외
    parts = Path(root).parts
    if any(part.startswith(".") or part in ("venv", "node_modules", "samples") for part in parts):
      continue
    for file in sorted(files):
      if file.endswith((".py", ".sh")):
        file_path = Path(root) / file
        finding = scan_file(file_path)
        if finding:
          results.append(finding)
  return results


def report_results(findings: list[dict]):
  """진단 결과를 정형화된 리포트로 출력하고 표준 처방 가이드를 제시한다."""
  print("=" * 72)
  print("[진단 결과] 제미나이(Gemini) API 호출 복원력(Resilience) 진단 리포트")
  print("=" * 72)

  if not findings:
    print("\n[안내] 대상 디렉터리에서 검사할 제미나이 API 호출 코드를 발견하지 못했다.")
    print("      (대상 파일 확장자: .py, .sh)\n")
    return

  total_files = len(findings)
  print(f"\n진단된 API 호출 소스 파일: {total_files}건\n")

  for f in findings:
    print(f"[파일: {f['file']}]")
    print(f"  - 지수 백오프 및 재시도: {'통과' if f['has_retry'] else '[경고] 누락'}")
    print(f"  - 지터 무작위 대기 제어: {'통과' if f['has_jitter'] else '[경고] 누락'}")
    print(f"  - 최대 재시도 횟수 제한: {'통과' if f['has_max_retries'] else '[경고] 누락'}")
    print(f"  - 폴백 모델 예외 체인  : {'통과' if f['has_fallback'] else '[권장] 미적용'}")
    print("-" * 72)

  total_issues = sum(
      1 for f in findings
      if not (f["has_retry"] and f["has_jitter"] and f["has_max_retries"] and f["has_fallback"])
  )

  if total_issues == 0:
    print("\n[성공] 모든 제미나이 호출 부위가 장애 방어 복원력 패턴을 충족하고 있다.\n")
    return

  print("\n" + "=" * 72)
  print("[추천 표준 처방 가이드 - 파이썬 tenacity 라이브러리 연동]")
  print("=" * 72)
  print("""from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_random_exponential

# 1. 지수 백오프, 지터, 최대 5회 재시도 제약 표준 결합 예시
@retry(
    wait=wait_random_exponential(min=1, max=60), # 지수 백오프 및 무작위성(지터) 추가
    stop=stop_after_attempt(5)                    # 최대 5회까지만 재시도 제한
)
def generate_with_retry(client, model_id, prompt):
  return client.models.generate_content(
      model=model_id,
      contents=prompt
  )

# 2. 주 모델(Gemini 3.8 Flash) 일시 장애 시 안정화 모델(Gemini 3.5 Flash)로 자동 우회
def generate_with_fallback(client, prompt):
  try:
    return generate_with_retry(client, 'gemini-3.8-flash', prompt)
  except Exception as e:
    print(f'[안내] 주 모델 호출 실패로 폴백 모델로 즉시 우회한다: {e}')
    return generate_with_retry(client, 'gemini-3.5-flash', prompt)
""")
  print("=" * 72 + "\n")


def build_markdown_report(findings: list[dict], is_dry_run: bool) -> str:
  """진단 결과를 바탕으로 표준 마크다운 리포트를 구성한다."""
  mode_str = "모의 실행 (Dry-run)" if is_dry_run else "실환경 진단 (Live)"
  header_line = (
      "[데모 실행] --dry-run 모드가 활성화되어 가상 분석 결과를 시뮬레이션한다.\n"
      if is_dry_run
      else "[스캔 완료] 실제 소스 코드 복원력 패턴 진단 완료\n"
  )

  finding_lines = []
  if not findings:
    finding_lines.append(
        "\n[안내] 대상 디렉터리에서 검사할 제미나이 API 호출 코드를 발견하지 못했다.\n      (대상 파일 확장자: .py, .sh)\n"
    )
  else:
    finding_lines.append(f"\n진단된 API 호출 소스 파일: {len(findings)}건\n")
    for f in findings:
      finding_lines.append(f"[파일: {f['file']}]")
      finding_lines.append(f"  - 지수 백오프 및 재시도: {'통과' if f['has_retry'] else '[경고] 누락'}")
      finding_lines.append(f"  - 지터 무작위 대기 제어: {'통과' if f['has_jitter'] else '[경고] 누락'}")
      finding_lines.append(f"  - 최대 재시도 횟수 제한: {'통과' if f['has_max_retries'] else '[경고] 누락'}")
      finding_lines.append(f"  - 폴백 모델 예외 체인  : {'통과' if f['has_fallback'] else '[권장] 미적용'}")
      finding_lines.append("-" * 72)

  findings_text = "\n".join(finding_lines)

  return f"""# 진단 및 분석 리포트: gemini-resilience-checker

- **생성 모드**: {mode_str}
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
{header_line}========================================================================
[진단 결과] 제미나이(Gemini) API 호출 복원력(Resilience) 진단 리포트
========================================================================
{findings_text}
========================================================================
[추천 표준 처방 가이드 - 파이썬 tenacity 라이브러리 연동]
========================================================================
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_random_exponential

# 1. 지수 백오프, 지터, 최대 5회 재시도 제약 표준 결합 예시
@retry(
    wait=wait_random_exponential(min=1, max=60), # 지수 백오프 및 무작위성(지터) 추가
    stop=stop_after_attempt(5)                    # 최대 5회까지만 재시도 제한
)
def generate_with_retry(client, model_id, prompt):
  return client.models.generate_content(
      model=model_id,
      contents=prompt
  )

# 2. 주 모델(Gemini 3.8 Flash) 일시 장애 시 안정화 모델(Gemini 3.5 Flash)로 자동 우회
def generate_with_fallback(client, prompt):
  try:
    return generate_with_retry(client, 'gemini-3.8-flash', prompt)
  except Exception as e:
    print(f'[안내] 주 모델 호출 실패로 폴백 모델로 즉시 우회한다: {{e}}')
    return generate_with_retry(client, 'gemini-3.5-flash', prompt)

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

본 도구는 소스 코드 정적 분석기이나, 연관된 클라우드 인프라 자원 및 워커 배포 시 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-resilience-checker`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 4. 콘솔 링크 조치 가이드

- **Service Health 콘솔**: ( https://console.cloud.google.com/servicehealth )
- **Vertex AI 콘솔**: ( https://console.cloud.google.com/vertex-ai )
- **클라우드 인시던트 핸들링 모범 사례 가이드**: ( https://cloud.google.com/blog/topics/developers-practitioners/cloud-reliability-incident-handling-best-practices )
- **구글 클라우드 Service Health 공식 개요**: ( https://cloud.google.com/service-health/docs/overview )

---

## 5. 자원 정리 안내 (Teardown)

이 도구는 소스 코드 정적 분석기이므로 클라우드 상에 생성된 리소스가 없으며, 별도의 자원 정리 작업이 필요하지 않다.
"""


def save_markdown_report(content: str, filepath: str = "report.md"):
  """진단 리포트를 마크다운 파일로 저장한다."""
  script_dir = os.path.dirname(os.path.abspath(__file__))
  target_path = os.path.join(script_dir, filepath)
  with open(target_path, "w", encoding="utf-8") as f:
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
      description="Gemini API 호출 429 장애 극복 복원력 패턴 자가 진단 도구"
  )
  parser.add_argument(
      "-p",
      "--path",
      default=os.getenv("SCAN_PATH") or ".",
      help="스캔 대상 소스 코드 디렉터리 경로 (기본값: 현재 디렉터리)",
  )
  parser.add_argument(
      "--dry-run",
      action="store_true",
      help="실제 스캔 없이 가상 모의 취약 코드를 기반으로 리포트를 시뮬레이션한다",
  )
  parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
  args = parser.parse_args()
  if getattr(args, "config", False):
      run_config_mode("gemini-resilience-checker")
      return

  if args.dry_run:
    print("\n[데모 실행] --dry-run 모드가 활성화되어 가상 분석 결과를 시뮬레이션한다.")
    findings = get_mock_findings()
    report_results(findings)
    md_content = build_markdown_report(findings, is_dry_run=True)
    save_markdown_report(md_content)
    print("[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: report.md")
    return

  print(f"\n[스캔 시작] '{args.path}' 경로 내 제미나이 API 복원력 패턴을 진단하는 중...")
  findings = scan_directory(args.path)
  report_results(findings)
  md_content = build_markdown_report(findings, is_dry_run=False)
  save_markdown_report(md_content)
  print("[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: report.md")


if __name__ == "__main__":
  main()
