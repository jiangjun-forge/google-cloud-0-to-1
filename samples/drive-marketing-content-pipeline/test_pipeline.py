#!/usr/bin/env python3
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Drive Marketing Content Pipeline - Comprehensive Test Suite & Local Runner

5대 파일 린(Lean) 표준을 준수하면서 파이프라인의 모든 비즈니스 로직과 엔터프라이즈 강건성을
로컬 터미널에서 100% 모의(Mock) 및 실시간 검증하는 자체 완결적 테스트 수이트다.

지원 모드:
  1. --scenario (또는 --dry-run): 마케터 5단계 전체 업무 흐름 및 에셋 보존 E2E 시나리오 검증 (2초 완료)
  2. --edge: LLM 비정형 사족 JSON 파싱 및 방어 단위 테스트
  3. --live: 실제 Google AI Studio API 키를 사용한 라이브 엔드포인트 직접 호출 검증
  4. --all: 시나리오, 에지 케이스, 라이브 API(키 있을 때) 전체 종합 검증
"""

import argparse
import os
import sys
import unittest
from typing import Dict

from tests.helpers import inspect_revision_folder, safe_extract_json, safe_parse_json
from tests.test_edge_cases import EdgeCaseParserTest
from tests.test_live_api import (
    LiveApiIntegrationTest,
    probe_live_gemini_text,
    probe_live_nano_banana_image,
)
from tests.test_scenario import MarketingWorkflowScenarioTest


# ============================================================================
# 통합 테스트 실행기 및 CLI 디스패처
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(description="Drive Marketing Content Pipeline Comprehensive Test Suite")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("GEMINI_API_KEY", ""),
        help="Google AI Studio Gemini API Key (or set GEMINI_API_KEY env var)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="API 호출 없이 가상 시나리오 및 에지케이스 전수 검증 (기본 권장)"
    )
    parser.add_argument(
        "--scenario",
        action="store_true",
        help="마케터 5단계 E2E 워크플로우 시나리오 모의 검증 실행"
    )
    parser.add_argument(
        "--edge",
        action="store_true",
        help="LLM 비정형 사족 JSON 파싱 단위 테스트 실행"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="실제 Google AI Studio REST API 엔드포인트 직접 호출 검증"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="시나리오, 에지케이스, 라이브 API(키 유효 시) 전체 검증"
    )
    return parser.parse_args()


def run_unit_suite(test_class) -> bool:
    """단위 테스트 클래스를 실행하고 성공 여부를 반환한다."""
    suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


def main():
    args = parse_args()
    api_key = args.api_key.strip()

    run_all = args.all or (not args.scenario and not args.edge and not args.live and not args.dry_run)
    run_scen = args.scenario or args.dry_run or run_all
    run_edge = args.edge or args.dry_run or run_all
    run_live = args.live or (run_all and bool(api_key))

    print("================================================================")
    print("Drive Marketing Content Pipeline - 종합 테스트 수이트")
    print(f"실행 모드: {'전체 종합 검증 (--all)' if run_all else '선택 모드'}")
    print("================================================================")

    results: Dict[str, str] = {}

    # 1. 마케터 모킹 E2E 시나리오 테스트
    if run_scen:
        print("\n[1] 마케터 모킹(Mocking) 기반 5단계 E2E 시나리오 테스트 실행...")
        success = run_unit_suite(MarketingWorkflowScenarioTest)
        results["마케터 E2E 시나리오 검증"] = "PASS" if success else "FAIL"

    # 2. LLM 비정형 사족 방어 단위 테스트
    if run_edge:
        print("\n[2] LLM 비정형 사족 JSON 파싱 및 런타임 가드레일 단위 테스트 실행...")
        success = run_unit_suite(EdgeCaseParserTest)
        results["LLM 사족 방어 단위 검증"] = "PASS" if success else "FAIL"

    # 3. 실제 Google AI Studio API 엔드포인트 검증
    if run_live:
        print("\n[3] Google AI Studio 실제 REST 엔드포인트 호출 검증...")
        if not api_key:
            print("  주의: API Key가 없어 실제 API 호출을 건너뜁니다 (--api-key 또는 GEMINI_API_KEY 환경 변수 필요).")
            results["라이브 API 검증"] = "SKIPPED (No Key)"
        else:
            t_res = probe_live_gemini_text(api_key)
            i_res = probe_live_nano_banana_image(api_key)
            results["라이브 API 검증"] = "PASS" if (t_res and i_res) else "FAIL"

    print("\n================================================================")
    print("테스트 수이트 종합 검증 결과 요약:")
    all_passed = True
    for name, status in results.items():
        print(f"  - {name:<30}: {status}")
        if status == "FAIL":
            all_passed = False
    print("================================================================")

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
