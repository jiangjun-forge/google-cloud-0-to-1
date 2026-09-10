#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Gemini Legacy SDK Usage Scanner.

구형 제미나이 SDK(google.generativeai 또는 vertexai.generative_models) 호출 부위를
정적 분석하여 탐지하고 최신 google-genai SDK로의 마이그레이션 가이드를 제공한다.
"""

import argparse
import json
import os
from pathlib import Path
import re
import sys

# 레거시 SDK 패턴 정의
LEGACY_PATTERNS = [
    (r"import\s+google\.generativeai", "구형 AI Studio SDK 임포트 (google.generativeai)"),
    (r"from\s+google\s+import\s+generativeai", "구형 AI Studio SDK 임포트 (google.generativeai)"),
    (r"from\s+vertexai\..*import\s+generative_models", "구형 Vertex AI SDK 임포트 (generative_models)"),
    (r"from\s+vertexai\.generative_models\s+import", "구형 Vertex AI SDK 임포트 (vertexai.generative_models)"),
    (r"genai\.configure\(", "구형 AI Studio 설정 함수 (genai.configure)"),
    (r"genai\.GenerativeModel\(", "구형 모델 객체 생성자 (genai.GenerativeModel)"),
    (r"GenerativeModel\(", "구형 모델 객체 생성자 (GenerativeModel)"),
    (r"vertexai\.init\(", "구형 Vertex AI 초기화 함수 (vertexai.init)"),
]


def get_mock_findings():
  """데모 실행을 위한 가상 진단 결과를 반환한다."""
  return [
      {
          "file": "app/services/chat_bot.py",
          "matches": [
              (1, "import google.generativeai as genai", "구형 AI Studio SDK 임포트 (google.generativeai)"),
              (5, "genai.configure(api_key=os.environ['GEMINI_API_KEY'])", "구형 AI Studio 설정 함수 (genai.configure)"),
              (12, "model = genai.GenerativeModel('gemini-1.5-flash')", "구형 모델 객체 생성자 (genai.GenerativeModel)"),
          ],
      },
      {
          "file": "pipelines/evaluate.py",
          "matches": [
              (3, "from vertexai.generative_models import GenerativeModel", "구형 Vertex AI SDK 임포트 (vertexai.generative_models)"),
              (8, "model = GenerativeModel('gemini-1.5-pro')", "구형 모델 객체 생성자 (GenerativeModel)"),
          ],
      },
  ]


def scan_file(file_path: Path) -> dict | None:
  """단일 소스 코드 파일을 검사하여 구형 제미나이 SDK 사용 여부를 분석한다."""
  try:
    content = file_path.read_text(encoding="utf-8", errors="ignore")
  except Exception:
    return None

  lines = []
  if file_path.suffix == ".ipynb":
    try:
      nb_data = json.loads(content)
      for cell_idx, cell in enumerate(nb_data.get("cells", [])):
        if cell.get("cell_type") == "code":
          for line_idx, raw_line in enumerate(cell.get("source", [])):
            lines.append((f"셀 {cell_idx + 1}, 라인 {line_idx + 1}", raw_line.rstrip("\n")))
    except Exception:
      return None
  else:
    for line_idx, raw_line in enumerate(content.splitlines(), start=1):
      lines.append((str(line_idx), raw_line))

  matches = []
  for line_num, line_text in lines:
    for pattern, desc in LEGACY_PATTERNS:
      if re.search(pattern, line_text):
        matches.append((line_num, line_text.strip(), desc))
        break

  if matches:
    return {"file": str(file_path), "matches": matches}
  return None


def scan_directory(scan_path: str) -> list[dict]:
  """지정한 디렉터리 내의 파이썬, 쉘 스크립트, 주피터 노트북 파일을 재귀 스캔한다."""
  results = []
  target_dir = Path(scan_path)
  if not target_dir.exists() or not target_dir.is_dir():
    print(f"[오류] 지정한 경로가 디렉터리가 아니거나 존재하지 않는다: {scan_path}", file=sys.stderr)
    sys.exit(1)

  for root, _, files in os.walk(target_dir):
    parts = Path(root).parts
    if any(part.startswith(".") or part in ("venv", "node_modules", "samples") for part in parts):
      continue
    for file in sorted(files):
      if file.endswith((".ipynb", ".py", ".sh")):
        file_path = Path(root) / file
        finding = scan_file(file_path)
        if finding:
          results.append(finding)
  return results


def report_results(findings: list[dict]):
  """진단 결과를 정형화된 리포트로 출력하고 신규 SDK 마이그레이션 가이드를 제시한다."""
  print("=" * 72)
  print("[진단 결과] 구형 제미나이(Gemini) SDK 코드 정적 진단 리포트")
  print("=" * 72)

  if not findings:
    print("\n[안내] 대상 디렉터리에서 구형 제미나이 SDK 사용 코드를 발견하지 못했다.")
    print("      (대상 파일 확장자: .ipynb, .py, .sh)\n")
    return

  total_occurrences = sum(len(f["matches"]) for f in findings)
  print(f"\n검출된 구형 SDK 사용 파일: {len(findings)}건 (총 {total_occurrences}개 라인)\n")

  for f in findings:
    print(f"[파일: {f['file']}]")
    for line_num, line_content, desc in f["matches"]:
      print(f"  - [{line_num}행] {desc}")
      print(f"    코드: {line_content}")
    print("-" * 72)

  print("\n" + "=" * 72)
  print("[최신 google-genai SDK 마이그레이션 가이드]")
  print("=" * 72)
  print("""[패키지 설치 및 변경]
기존: pip install google-generativeai
      pip install google-cloud-aiplatform
신규: pip install google-genai

[코드 변환 예시 - Gemini Developer API 및 Vertex AI 단일 통일]
------------------------------------------------------------------------
# 1. 신규 통일 SDK 임포트 및 클라이언트 초기화
from google import genai
from google.genai import types

# API 키 기반 (AI Studio)
client = genai.Client(api_key="YOUR_API_KEY")

# 또는 GCP 프로젝트 기반 (Vertex AI)
# client = genai.Client(vertexai=True, project="YOUR_PROJECT_ID", location="us-central1")

# 2. 콘텐츠 생성 호출
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="안녕하세요, 최신 SDK 적용 테스트입니다."
)
print(response.text)
""")
  print("=" * 72 + "\n")


def main():
  parser = argparse.ArgumentParser(
      description="구형 제미나이 SDK 사용처 탐지 및 신규 google-genai 마이그레이션 도구"
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

  print(f"\n[스캔 시작] '{args.path}' 경로 내 구형 제미나이 SDK 사용처를 진단하는 중...")
  findings = scan_directory(args.path)
  report_results(findings)


if __name__ == "__main__":
  main()
