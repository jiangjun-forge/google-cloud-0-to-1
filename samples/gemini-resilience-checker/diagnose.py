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

# 2. 주 모델(Gemini 2.5 Pro) 실패 시 경량 모델(Gemini 2.5 Flash)로 자동 우회
def generate_with_fallback(client, prompt):
  try:
    return generate_with_retry(client, 'gemini-2.5-pro', prompt)
  except Exception as e:
    print(f'[안내] 주 모델 호출 실패로 폴백 모델로 즉시 우회한다: {e}')
    return generate_with_retry(client, 'gemini-2.5-flash', prompt)
""")
  print("=" * 72 + "\n")


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
      "--demo",
      action="store_true",
      help="실제 스캔 없이 가상 모의 취약 코드를 기반으로 리포트를 시뮬레이션한다",
  )
  args = parser.parse_args()

  if args.dry_run:
    print("\n[데모 실행] --dry-run 모드가 활성화되어 가상 분석 결과를 시뮬레이션한다.")
    report_results(get_mock_findings())
    return

  print(f"\n[스캔 시작] '{args.path}' 경로 내 제미나이 API 복원력 패턴을 진단하는 중...")
  findings = scan_directory(args.path)
  report_results(findings)


if __name__ == "__main__":
  main()
