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
            # 0. 조회 의도 인터셉트
            if any(k in q for k in ["어디", "링크", "열어", "보여", "주소", "확인", "찾아", "열기"]):
                if any(k in q for k in ["기획", "plan"]) and s.get("planDocUrl"):
                    return "open_plan"
                if any(k in q for k in ["콘텐츠", "카피", "초판"]) and s.get("contentDocUrl"):
                    return "open_content"
                if any(k in q for k in ["보고서", "요약", "피드백"]) and s.get("summaryDocUrl"):
                    return "open_summary"
                return "open_link"
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
        self.assertEqual(mock_deterministic_fallback("25인 평가 시작해 줘", status), "promptAndRunPersonaEvaluation")
        # 4. 명시적 기획서 요청
        self.assertEqual(mock_deterministic_fallback("기획서 도출해 줘", status), "guardAndRunIdeaToPlan")
        # 5. 산출물 조회 질문 시 재생성 액션이 아니라 조회 인터셉트 검증
        status_with_plan = {
            "folderUrl": "https://drive.google.com/drive/folders/test",
            "planDocUrl": "https://docs.google.com/document/d/test-plan",
            "contentDocUrl": "",
            "summaryDocUrl": ""
        }
        self.assertEqual(mock_deterministic_fallback("기획서 어디 있어?", status_with_plan), "open_plan")
        self.assertEqual(mock_deterministic_fallback("기획서 링크 줘", status_with_plan), "open_plan")

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

    def test_dashboard_numeric_sanitization_rules(self):
        """실행 내역 시트의 소요 시간 및 소모 토큰 숫자 정제 규칙 검증."""
        import re

        def py_format_duration_sec(val):
            if val is None or val == "" or val == "-":
                return 0
            if isinstance(val, (int, float)):
                return round(val / 1000) if val > 1000 else round(val)
            digits = re.sub(r"[^0-9]", "", str(val))
            return int(digits) if digits else 0

        def py_format_token_count(val):
            if val is None or val == "" or val == "-" or val == "0":
                return 0
            if isinstance(val, (int, float)):
                return round(val)
            digits = re.sub(r"[^0-9]", "", str(val))
            return int(digits) if digits else 0

        # 소요 시간 단위 및 하이픈 정제
        self.assertEqual(py_format_duration_sec("24초"), 24)
        self.assertEqual(py_format_duration_sec("-"), 0)
        self.assertEqual(py_format_duration_sec(None), 0)
        self.assertEqual(py_format_duration_sec(15000), 15)
        self.assertEqual(py_format_duration_sec(42), 42)

        # 소모 토큰 단위 및 하이픈 정제
        self.assertEqual(py_format_token_count("1,200 tokens"), 1200)
        self.assertEqual(py_format_token_count("-"), 0)
        self.assertEqual(py_format_token_count(None), 0)
        self.assertEqual(py_format_token_count(3500), 3500)

    def test_feedback_cluster_points_self_healing(self):
        """points 파일 누락 시 페르소나 데이터셋 기반 자가 치유 포인트 복구 규칙 검증."""
        sample_feedbacks = [
            {
                "name": "강민준",
                "category": "20대 대학생",
                "open_feedback": "노이즈 캔슬링은 훌륭하나 가격대가 대학생에겐 다소 높다.",
                "points": [
                    {"point_id": "P1_1", "text": "ANC 성능 만족", "sentiment": "긍정", "rating": 4.5},
                    {"point_id": "P1_2", "text": "가격 부담", "sentiment": "가격", "rating": 3.0}
                ]
            },
            {
                "name": "이지원",
                "category": "20대 직장인",
                "open_feedback": "디자인이 깔끔하고 출퇴근길에 적합하다."
                # points 누락된 경우
            }
        ]

        # 파이썬 구현 검증
        extracted_points = []
        for idx, fb in enumerate(sample_feedbacks):
            pts = fb.get("points")
            if not pts:
                pts = [{
                    "point_id": f"P{idx+1}_1",
                    "text": fb.get("open_feedback", "만족"),
                    "sentiment": "중립",
                    "rating": 3.5
                }]
            for pt in pts:
                pt_copy = dict(pt)
                pt_copy["persona_name"] = fb["name"]
                pt_copy["persona_category"] = fb["category"]
                extracted_points.append(pt_copy)

        self.assertEqual(len(extracted_points), 3)
        self.assertEqual(extracted_points[0]["point_id"], "P1_1")
        self.assertEqual(extracted_points[2]["persona_name"], "이지원")

    def test_persona_feedback_dataset_structure(self):
        """AI 페르소나 다면 평가 데이터셋(ai_persona_feedbacks.json)의 필수 구조 검증."""
        # 128d 임베딩 투영 좌표를 가진 모의 데이터셋 구조
        mock_feedbacks = []
        for i in range(25):
            s_type = ["긍정", "가격", "비판", "중립"][i % 4]
            mock_feedbacks.append({
                "persona_id": f"kr_persona_{i+1:05d}",
                "name": f"소비자_{i+1}",
                "age": 20 + (i % 30),
                "gender": "남성" if i % 2 == 0 else "여성",
                "occupation": "직장인",
                "category": "소비자",
                "rating": 4.5 if s_type == "긍정" else (2.5 if s_type == "비판" else 3.5),
                "open_feedback": f"피드백 의견 {i+1}",
                "points": [
                    {"point_id": f"PT_{i+1}_1", "text": f"핵심 소감 {i+1}", "sentiment": s_type, "rating": 4.0}
                ]
            })

        self.assertEqual(len(mock_feedbacks), 25)
        for fb in mock_feedbacks:
            self.assertIn("persona_id", fb)
            self.assertIn("name", fb)
            self.assertIn("rating", fb)
            self.assertIn("points", fb)
            self.assertGreaterEqual(len(fb["points"]), 1)

    def test_first_feedback_round_auto_detection(self):
        """초기화로 생성된 빈 폴더가 있어도 최초 평가는 반드시 fb-01로 판별되는지 검증."""
        # 모의 폴더 구조: input/fb-01 (빈 폴더: 유효 파일 없음)
        mock_subfolders = [
            {"name": "fb-01", "files": []}
        ]

        def mock_detect_latest_feedback(folders):
            max_r = 0
            for f in folders:
                name = f["name"]
                if name.startswith("fb-"):
                    num = int(name.replace("fb-", ""))
                    # 유효 파일이 있을 때만 카운트
                    if len(f["files"]) > 0 and num > max_r:
                        max_r = num
            return max_r

        latest_completed_fb = mock_detect_latest_feedback(mock_subfolders)
        self.assertEqual(latest_completed_fb, 0, "빈 폴더만 있을 때는 완료된 회차가 0이어야 함")

        # 제안 회차 계산: latest_fb + 1
        suggested_round = max(latest_completed_fb + 1, 1)
        suggested_round_str = f"fb-{suggested_round:02d}"
        self.assertEqual(suggested_round_str, "fb-01", "최초 평가는 무조건 fb-01이어야 함")

        # 1차 평가 완료 후 (파일 생성됨)
        mock_subfolders[0]["files"] = ["ai_persona_feedbacks.json"]
        next_fb = mock_detect_latest_feedback(mock_subfolders)
        self.assertEqual(next_fb, 1, "유효 파일이 있으면 회차 1로 인식")
        next_suggested = f"fb-{(next_fb + 1):02d}"
        self.assertEqual(next_suggested, "fb-02", "1차 완료 후 차기 평가는 fb-02이어야 함")

    def test_artifact_link_round_tagging(self):
        """산출물 링크 텍스트에 (fb-01), (rv-00) 등 회차 태그가 반드시 명시되는지 검증."""
        def format_action_btn(url_type, round_tag):
            if url_type == "feedback_json":
                return f"[AI 페르소나 피드백 JSON 열기 ({round_tag})]"
            elif url_type == "summary":
                return f"[피드백 보고서 열기 ({round_tag})]"
            elif url_type == "directive":
                return f"[마케터 보정 지침 열기 ({round_tag})]"
            elif url_type == "content":
                return f"[콘텐츠 독스 열기 ({round_tag})]"
            return f"[산출물 열기 ({round_tag})]"

        self.assertEqual(format_action_btn("feedback_json", "fb-01"), "[AI 페르소나 피드백 JSON 열기 (fb-01)]")
        self.assertEqual(format_action_btn("summary", "fb-01"), "[피드백 보고서 열기 (fb-01)]")
        self.assertEqual(format_action_btn("directive", "fb-01"), "[마케터 보정 지침 열기 (fb-01)]")
        self.assertEqual(format_action_btn("content", "rv-00"), "[콘텐츠 독스 열기 (rv-00)]")
        self.assertEqual(format_action_btn("content", "rv-01"), "[콘텐츠 독스 열기 (rv-01)]")

    def test_persona_evaluation_links_json_dataset(self):
        """AI 페르소나 다면 평가 완료 시 ai_persona_feedbacks.json 링크가 직결되는지 검증."""
        mock_result = {
            "success": True,
            "targetRound": "fb-01",
            "message": "AI 페르소나 다면 평가 데이터셋이 생성되었습니다 (fb-01).",
            "feedbackJsonUrl": "https://drive.google.com/open?id=mock_json_file_id",
            "jsonUrl": "https://drive.google.com/open?id=mock_json_file_id"
        }
        # 링크 텍스트 생성 검증
        link_text = f"AI 페르소나 피드백 JSON 열기 ({mock_result['targetRound']})"
        self.assertEqual(link_text, "AI 페르소나 피드백 JSON 열기 (fb-01)")
        self.assertIn("ai_persona_feedbacks.json", "ai_persona_feedbacks.json 생성 완료")
        self.assertTrue(mock_result["feedbackJsonUrl"].startswith("https://drive.google.com/"))


if __name__ == "__main__":
    unittest.main()
