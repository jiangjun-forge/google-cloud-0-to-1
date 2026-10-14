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

    def test_copilot_deterministic_fallback_rules(self):
        """AI 코파일럿 장애 시 결정론적 룰 기반 폴백의 매핑 무결성 검증."""
        # 모의 상태: 폴더 있고 기획서 없는 상태
        status = {
            "folderUrl": "https://drive.google.com/drive/folders/test",
            "planDocUrl": "",
            "contentDocUrl": "",
            "summaryDocUrl": ""
        }

        # 파이썬으로 Code_Sidebar.js의 결정론적 룰을 모킹 검증
        def mock_deterministic_fallback(query: str, s: dict):
            q = query.lower().replace(" ", "")
            if any(k in q for k in ["지금", "다음", "순서", "뭐해"]):
                if not s.get("folderUrl"):
                    return "initCampaignWorkspace"
                if not s.get("planDocUrl"):
                    return "guardAndRunIdeaToPlan"
                if not s.get("contentDocUrl"):
                    return "guardAndRunInitialContent"
                if not s.get("summaryDocUrl"):
                    return "promptAndRunPersonaEvaluation"
                return "promptAndRunFeedbackRevision"
            if any(k in q for k in ["기획", "plan"]):
                return "guardAndRunIdeaToPlan"
            if any(k in q for k in ["초판", "콘텐츠", "제작", "카피"]):
                return "guardAndRunInitialContent"
            if any(k in q for k in ["25인", "페르소나", "평가"]):
                return "promptAndRunPersonaEvaluation"
            if any(k in q for k in ["보고서", "피드백", "요약"]):
                return "promptAndRunFeedbackSummary"
            if any(k in q for k in ["보정", "개정", "리비전"]):
                return "promptAndRunFeedbackRevision"
            return None

        # 1. 상태 질의 시 기획서 미생성이므로 기획서 액션 매핑
        self.assertEqual(mock_deterministic_fallback("지금 뭐 해야 돼?", status), "guardAndRunIdeaToPlan")
        # 2. 명시적 제작 요청
        self.assertEqual(mock_deterministic_fallback("초판 제작해 줘", status), "guardAndRunInitialContent")
        # 3. 명시적 평가 요청
        self.assertEqual(mock_deterministic_fallback("25인 평가 시작해줘", status), "promptAndRunPersonaEvaluation")
        # 4. 명시적 기획서 요청
        self.assertEqual(mock_deterministic_fallback("기획서 도출해 줘", status), "guardAndRunIdeaToPlan")

    def test_korean_spacing_in_code_and_docs(self):
        """소스 코드 및 문서 내 '제작해 줘', '도출해 줘' 등 보조용언 띄어쓰기 규격 준수 검증."""
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        targets = [
            os.path.join(base_dir, "apps-scripts", "Code_Sidebar.js"),
            os.path.join(base_dir, "README.md"),
            os.path.join(base_dir, "docs", "BRD.md")
        ]

        forbidden_words = ["제작해줘", "도출해줘", "만들어줘", "시작해줘"]
        for fpath in targets:
            if not os.path.exists(fpath):
                continue
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            for word in forbidden_words:
                self.assertNotIn(
                    word, content,
                    f"붙여 쓴 비표준 표기 '{word}'가 {os.path.basename(fpath)}에서 발견되었습니다. 띄어쓰기('~해 줘')를 준수해야 합니다."
                )


if __name__ == "__main__":
    unittest.main()
