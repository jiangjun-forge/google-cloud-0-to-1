#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Gemini API Sensitive Data DLP Masking Tool.

제미나이(Gemini) API 프롬프트 전송 전, Cloud DLP(Sensitive Data Protection) API를 통해
전화번호, 주민등록번호, 이메일 등 개인 식별 정보(PII)를 실시간 마스킹(Redaction) 처리한다.
"""

import argparse
import os
import re
import subprocess
import sys

DEFAULT_TEST_PROMPT = (
    "안녕하세요. 제 연락처는 010-1234-5678이고 주민등록번호는 900101-1234567입니다. "
    "gcp-user@example.com 으로 제미나이 2.5 기술 자료를 보내주세요."
)


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
  """쉘 명령어를 실행하고 결과를 반환한다."""
  res = subprocess.run(cmd, capture_output=True, text=True)
  return res.returncode, res.stdout.strip(), res.stderr.strip()


def get_default_project():
  """gcloud 설정에서 활성 프로젝트 ID를 조회한다."""
  _, stdout, _ = run_cmd(["gcloud", "config", "get-value", "project"])
  return stdout if stdout and "(unset)" not in stdout else None


def simulate_masking(prompt: str, mask_char: str = "*") -> str:
  """로컬 정규식을 기반으로 모의 마스킹 처리를 수행한다."""
  # 전화번호 마스킹
  masked = re.sub(r"01[0-9]-[0-9]{3,4}-[0-9]{4}", mask_char * 13, prompt)
  # 주민등록번호 마스킹
  masked = re.sub(r"\d{6}-[1-4]\d{6}", mask_char * 14, masked)
  # 이메일 마스킹
  masked = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", mask_char * 20, masked)
  return masked


def print_report(original: str, masked: str, info_types: list[str]):
  """마스킹 전후 비교 리포트를 정형화하여 출력한다."""
  print("=" * 72)
  print("[진단 결과] 제미나이(Gemini) 프롬프트 민감 정보 마스킹 리포트")
  print("=" * 72)
  print(f"감지 타겟 개인정보 유형 (InfoTypes): {', '.join(info_types)}")
  print("-" * 72)
  print("[1. 원본 전송 프롬프트 (민감 정보 포함 위험)]")
  print(f"  {original}")
  print("-" * 72)
  print("[2. 마스킹 처리된 안전 프롬프트 (DLP Redacted)]")
  print(f"  {masked}")
  print("=" * 72)
  print("\n[안내] 마스킹 완료된 안전 프롬프트가 Gemini API로 안전하게 전송될 준비를 마쳤다.\n")


def mask_with_dlp(project_id: str, prompt: str, info_types: list[str], mask_char: str) -> str:
  """Cloud DLP API를 호출하여 민감 정보를 실제 마스킹한다."""
  try:
    from google.cloud import dlp_v2
    dlp = dlp_v2.DlpServiceClient()
    parent = f"projects/{project_id}/locations/global"

    inspect_config = {
        "info_types": [{"name": it} for it in info_types],
        "min_likelihood": dlp_v2.Likelihood.POSSIBLE,
    }
    deidentify_config = {
        "info_type_transformations": {
            "transformations": [
                {
                    "info_types": [{"name": it} for it in info_types],
                    "primitive_transformation": {
                        "character_mask_config": {
                            "masking_character": mask_char,
                        }
                    },
                }
            ]
        }
    }
    item = {"value": prompt}
    response = dlp.deidentify_content(
        request={
            "parent": parent,
            "deidentify_config": deidentify_config,
            "inspect_config": inspect_config,
            "item": item,
        }
    )
    return response.item.value
  except Exception as e:
    print(f"[경고] Cloud DLP API 호출 중 예외 발생 (권한 또는 API 활성화 필요): {e}")
    print("[안내] 로컬 정규식 모의 마스킹 결과로 폴백을 수행한다.")
    return simulate_masking(prompt, mask_char)


def main():
  parser = argparse.ArgumentParser(
      description="제미나이 API 프롬프트 전송 전 민감 정보 Cloud DLP 실시간 마스킹 도구"
  )
  parser.add_argument(
      "-p",
      "--project",
      default=os.getenv("PROJECT_ID") or get_default_project(),
      help="GCP 프로젝트 ID (기본값: 활성 프로젝트 자동 감지)",
  )
  parser.add_argument(
      "-t",
      "--text",
      default=DEFAULT_TEST_PROMPT,
      help="마스킹 테스트 대상 프롬프트 텍스트",
  )
  parser.add_argument(
      "--info-types",
      default=os.getenv("DLP_INFO_TYPES", "PHONE_NUMBER,EMAIL_ADDRESS,KOREA_RRN"),
      help="감지할 PII 유형 콤마 구분 목록",
  )
  parser.add_argument(
      "--mask-char",
      default=os.getenv("DLP_MASK_CHARACTER", "*"),
      help="마스킹 대체 문자 (기본값: *)",
  )
  parser.add_argument(
      "--dry-run",
      "--demo",
      action="store_true",
      help="실제 Cloud DLP API 호출 없이 가상 시뮬레이션 모드로 실행한다",
  )
  args = parser.parse_args()

  project_id = args.project or "demo-project-id"
  info_types = [it.strip() for it in args.info_types.split(",") if it.strip()]

  if args.dry_run:
    print("\n[데모 실행] --dry-run 모드가 활성화되어 가상 DLP 마스킹을 시뮬레이션한다.")
    masked_prompt = simulate_masking(args.text, args.mask_char)
    print_report(args.text, masked_prompt, info_types)
    return

  print("=" * 72)
  print("[처리 시작] Cloud DLP 실시간 민감 데이터 필터링 가동")
  print(f"  - 프로젝트: {project_id}")
  print(f"  - 대상 InfoTypes: {', '.join(info_types)}")
  print("=" * 72)

  masked_prompt = mask_with_dlp(project_id, args.text, info_types, args.mask_char)
  print_report(args.text, masked_prompt, info_types)

  print("=" * 72)
  print("[자원 정리 안내 (Teardown Guide)]")
  print("본 도구는 상태 비저장(Stateless) API 호출 도구이므로 별도의 영구 클라우드 자원 삭제가 불필요하다.")
  print("=" * 72 + "\n")


if __name__ == "__main__":
  main()
