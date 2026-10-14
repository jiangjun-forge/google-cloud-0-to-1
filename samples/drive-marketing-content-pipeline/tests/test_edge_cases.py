#!/usr/bin/env python3
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Drive Marketing Content Pipeline - Edge Case Parser Tests.

LLM의 비정형 사족, 마크다운 코드블록 감싸임, 손상된 JSON 폴백 등
런타임 회복 탄력성을 검증하는 단위 테스트 모듈이다.
"""

import unittest

from tests.helpers import safe_extract_json, safe_parse_json


class EdgeCaseParserTest(unittest.TestCase):
    """LLM 비정형 사족 및 JSON 파서 회복 탄력성 단위 테스트."""

    def test_markdown_codeblock_wrapped(self):
        """마크다운 백틱(```json) 감싸임 안전 파싱 검증."""
        raw = "```json\n{\"id\": \"p01\", \"name\": \"강도윤\"}\n```"
        parsed = safe_parse_json(raw, {})
        self.assertEqual(parsed.get("id"), "p01")
        self.assertEqual(parsed.get("name"), "강도윤")

    def test_conversational_chatter_prefix_and_suffix(self):
        """앞뒤 대화형 사족 문구가 포함된 응답의 경계 슬라이싱 검증."""
        raw = (
            "네, 요청하신 25인 페르소나 JSON 객체입니다.\n\n"
            "[\n  {\"id\": \"p01\", \"points\": [\"의견1\"]},\n  {\"id\": \"p02\", \"points\": [\"의견2\"]}\n]\n\n"
            "추가 요청 사항이 있으시면 언제든 말씀해 주십시오."
        )
        parsed = safe_parse_json(raw, [], expect_array=True)
        self.assertTrue(isinstance(parsed, list))
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["id"], "p01")

    def test_corrupted_json_fallback(self):
        """완전히 깨진 비정형 텍스트 유입 시 기본값(fallback) 반환 검증."""
        raw = "이 텍스트는 유효한 JSON 구문이 전혀 없는 일반 설명글입니다."
        parsed = safe_parse_json(raw, fallback={"default": True})
        self.assertEqual(parsed, {"default": True})

    def test_clean_json_array(self):
        """순수 JSON 배열의 무결성 검증."""
        raw = "[{\"rating\": 4.5}, {\"rating\": 3.8}]"
        parsed = safe_parse_json(raw, [])
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["rating"], 4.5)


if __name__ == "__main__":
    unittest.main()
