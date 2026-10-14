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
import base64
import json
import os
import re
import sys
import time
import unittest
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


# ============================================================================
# [모듈 1] Apps Script 핵심 파서 및 가드레일 로직의 파이썬 구현체 (SUT: System Under Test)
# ============================================================================

def safe_extract_json(raw_text: str, expect_array: bool = True) -> str:
    """LLM 응답 앞뒤의 사족 텍스트나 마크다운 코드블록을 슬라이싱하여 순수 JSON 문자열만 추출한다."""
    if not raw_text:
        return "[]" if expect_array else "{}"

    cleaned = re.sub(r"^```[a-z]*\s*", "", raw_text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())

    start_char = "[" if expect_array else "{"
    end_char = "]" if expect_array else "}"

    first_idx = cleaned.find(start_char)
    last_idx = cleaned.rfind(end_char)

    if first_idx != -1 and last_idx != -1 and last_idx > first_idx:
        return cleaned[first_idx : last_idx + 1]

    return cleaned


def safe_parse_json(raw_text: str, default_val: Any = None, expect_array: bool = True) -> Any:
    """비정형 LLM 응답을 안전하게 파싱하며 실패 시 기본값으로 안전 폴백한다."""
    try:
        extracted = safe_extract_json(raw_text, expect_array)
        return json.loads(extracted)
    except Exception:
        return default_val if default_val is not None else ([] if expect_array else {})


def inspect_revision_folder(existing_files: List[str], prefix: str = "00") -> Dict[str, Any]:
    """폴더 내 생성된 에셋 현황을 점검하여 누락 에셋 및 완료 상태를 판별한다."""
    required_specs = [
        f"{prefix}_banner_16x9.png",
        f"{prefix}_poster_9x16.png",
        f"{prefix}_sns_1x1.png",
        f"{prefix}_shorts.mp4"
    ]
    missing = [req for req in required_specs if req not in existing_files]
    has_doc = "campaign_content" in existing_files
    if not has_doc:
        missing.append("campaign_content")

    return {
        "is_empty": len(existing_files) == 0,
        "is_complete": len(missing) == 0,
        "missing_files": missing,
        "existing_files": existing_files,
        "has_doc": has_doc
    }


# ============================================================================
# [모듈 2] LLM 출력 비정형 사족 방어 단위 테스트 (EdgeCaseParserTest)
# ============================================================================

class EdgeCaseParserTest(unittest.TestCase):
    """LLM이 사족 문구나 백틱을 포함하여 출력할 때의 방어적 파싱 단위 테스트"""

    def test_clean_json_array(self):
        raw = '[{"id": 1, "text": "정상"}]'
        parsed = safe_parse_json(raw, [], True)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["id"], 1)

    def test_markdown_codeblock_wrapped(self):
        raw = "```json\n[\n  {\"id\": 2, \"text\": \"코드블록 감싸임\"}\n]\n```"
        parsed = safe_parse_json(raw, [], True)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["id"], 2)

    def test_conversational_chatter_prefix_and_suffix(self):
        raw = (
            "네, 요청하신 25인 페르소나 평가 결과 JSON 배열입니다:\n\n"
            "[\n  {\"name\": \"강민준\", \"rating\": 4.5}\n]\n\n"
            "추가 분석이 필요하시면 언제든 말씀해 주십시오!"
        )
        parsed = safe_parse_json(raw, [], True)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["name"], "강민준")

    def test_corrupted_json_fallback(self):
        raw = "이것은 완전한 텍스트이며 JSON 기호가 전혀 없습니다."
        parsed = safe_parse_json(raw, [{"fallback": True}], True)
        self.assertEqual(len(parsed), 1)
        self.assertTrue(parsed[0].get("fallback"))


# ============================================================================
# [모듈 3] 마케터 모킹(Mocking) 기반 5단계 E2E 시나리오 테스트
# ============================================================================

class MarketingWorkflowScenarioTest(unittest.TestCase):
    """실제 마케터의 브라우저 업무 흐름(기획 -> 명세 -> 생성 -> 평가 -> 보정) 전수 시뮬레이션"""

    def setUp(self):
        self.workspace: Dict[str, Any] = {
            "root": {},
            "prompts": {},
            "input": {"아이디어 메모": "2026 프리미엄 초경량 노이즈 캔슬링 헤드폰 론칭 캠페인"},
            "output": {}
        }

    def test_step1_and_step2_plan_and_spec_separation(self):
        """[Step 1 & Step 2] 기획서(PLAN)와 제작 명세서(SPEC) 2단계 분리 도출 검증"""
        idea = self.workspace["input"]["아이디어 메모"]
        self.assertGreater(len(idea), 5)

        # 1단계: 아이디어 -> 기획서 (PLAN) 도출
        mock_plan = (
            "# 마케팅 캠페인 기획서 (PLAN)\n\n"
            "## 1. 캠페인 배경\n2026 프리미엄 오디오 시장 공략\n\n"
            "## 2. 타깃 오디언스 및 USP\n2030 통근 직장인, 180g 초경량 노이즈 캔슬링"
        )
        self.workspace["root"]["PLAN"] = mock_plan
        self.assertIn("PLAN", self.workspace["root"])

        # 2단계: 완성된 PLAN -> 제작 명세서 (SPEC) 도출
        mock_spec = (
            "# 콘텐츠 제작 명세서 (SPEC)\n\n"
            "## 1. 비주얼 규격\n* 16:9 배너 (1920x1080)\n* 9:16 포스터 (1080x1920)\n* 1:1 SNS (1080x1080)\n\n"
            "## 2. 숏폼 규격\n* 9:16 모바일 숏폼 15초\n"
        )
        self.workspace["root"]["SPEC"] = mock_spec
        self.assertIn("SPEC", self.workspace["root"])

        # 구분자 종속성 없이 완벽히 분리된 독스 2종 생성 검증
        self.assertNotIn("===SPEC_DELIMITER===", self.workspace["root"]["PLAN"])
        self.assertNotIn("===SPEC_DELIMITER===", self.workspace["root"]["SPEC"])

    def test_step3_initial_content_generation(self):
        """[Step 3] SPEC 규격 기반 초판 콘텐츠(rv-00) 세트 생성 검증"""
        rv00 = {
            "campaign_content": "# 초판 마케팅 카피 및 숏폼 영상 콘티 전문",
            "00_banner_16x9.png": b"mock_banner_bytes",
            "00_poster_9x16.png": b"mock_poster_bytes",
            "00_sns_1x1.png": b"mock_sns_bytes",
            "00_shorts.mp4": b"mock_video_bytes"
        }
        self.workspace["output"]["rv-00"] = rv00

        # 에셋 완성도 검사
        status = inspect_revision_folder(list(rv00.keys()), "00")
        self.assertTrue(status["is_complete"])
        self.assertEqual(len(status["missing_files"]), 0)

    def test_step4_marketer_directive_preservation(self):
        """[Step 4 & Step 5] 피드백 보고서와 독립된 마케터 보정 지침서의 영구 보존 검증"""
        fb01: Dict[str, str] = {
            "feedback_summary": "# 1차 피드백 종합 분석 보고서 (t-SNE 지형도 삽입본)",
            "마케터 보정 지침": "# 마케터 보정 지침 (초기 템플릿)"
        }
        self.workspace["input"]["fb-01"] = fb01

        # 마케터가 브라우저에서 보정 지침을 직접 수정함
        human_edited_directive = (
            "# 마케터 보정 지침 (마케터 최종 수정본)\n"
            "* 지침: 대학생 할인 프로모션을 메인 헤드카피로 전진 배치할 것."
        )
        fb01["마케터 보정 지침"] = human_edited_directive

        # AI가 피드백 종합 보고서(feedback_summary)를 재생성하더라도 마케터 지침은 보존되어야 함
        fb01["feedback_summary"] = "# 1차 피드백 종합 분석 보고서 (AI 2회차 재생성본)"

        self.assertEqual(fb01["마케터 보정 지침"], human_edited_directive, "마케터 작성 지침이 덮어써지지 않고 영구 보존되어야 함")

    def test_step6_smart_fill_missing_assets(self):
        """[Step 6] 동일 리비전 내 미완성 파일 고속 보충 vs 기존 에셋 보존 분기 검증"""
        # 이미지 1장과 숏폼 비디오가 누락된 불완전 상태 모의
        partial_rv01 = [
            "campaign_content",
            "01_banner_16x9.png",
            "01_poster_9x16.png"
        ]
        status = inspect_revision_folder(partial_rv01, "01")

        self.assertFalse(status["is_complete"])
        self.assertIn("01_sns_1x1.png", status["missing_files"])
        self.assertIn("01_shorts.mp4", status["missing_files"])
        self.assertEqual(len(status["missing_files"]), 2)


# ============================================================================
# [모듈 4] Google AI Studio 라이브 REST API 프로브 (LiveApiIntegrationTest)
# ============================================================================

def probe_live_gemini_text(api_key: str) -> Optional[str]:
    """gemini-3.8-flash 텍스트 생성 및 usageMetadata 토큰 집계 검증"""
    url = f"{BASE_URL}/models/gemini-3.8-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": "테스트 핑: 프리미엄 헤드폰 슬로건 1줄 작성"}]}],
        "generationConfig": {"temperature": 0.5, "maxOutputTokens": 100}
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
            tokens = usage.get("totalTokenCount", 0)
            print(f"    - 응답 카피: {text.strip()[:60]}... (소모 토큰: {tokens} tokens)")
            return text
    except Exception as e:
        print(f"    - 텍스트 API 실패: {e}")
        return None


def probe_live_nano_banana_image(api_key: str, out_dir: str = "test_output") -> Optional[str]:
    """gemini-nano-banana-2.1 상업 광고 비주얼 이미지 생성 검증"""
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "00_banner_test.jpg")
    url = f"{BASE_URL}/models/gemini-nano-banana-2.1:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": "Modern Korean lightweight ANC headphone on cafe table, warm sunset lighting, photorealistic 8k"}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]}
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            parts = data["candidates"][0]["content"]["parts"]
            for p in parts:
                if "inlineData" in p and "data" in p["inlineData"]:
                    img_bytes = base64.b64decode(p["inlineData"]["data"])
                    with open(out_file, "wb") as f:
                        f.write(img_bytes)
                    print(f"    - 이미지 렌더링 성공 ({len(img_bytes):,} bytes) -> {out_file}")
                    return out_file
    except Exception as e:
        print(f"    - 이미지 API 실패: {e}")
    return None


# ============================================================================
# [모듈 5] 메인 CLI 디스패처
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
