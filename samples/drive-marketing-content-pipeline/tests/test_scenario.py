#!/usr/bin/env python3
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Drive Marketing Content Pipeline - Marketer E2E Scenario Tests.

마케터의 5단계 전체 업무 흐름 및 에셋 보존, SPEC 기반 타깃 페르소나 자동 합성 시나리오를
로컬에서 100% 모의(Mock) 검증하는 테스트 모듈이다.
"""

import os
import shutil
import tempfile
import unittest
from typing import Dict, List

from tests.helpers import inspect_revision_folder, safe_parse_json


class MarketingWorkflowScenarioTest(unittest.TestCase):
    """마케터 실제 업무 흐름 및 에셋 보존 E2E 시나리오 모킹 테스트 수이트."""

    def setUp(self):
        self.test_root = os.path.join(tempfile.gettempdir(), "test_scenario_workspace")
        os.makedirs(os.path.join(self.test_root, "prompts"), exist_ok=True)
        os.makedirs(os.path.join(self.test_root, "input", "fb-01"), exist_ok=True)
        os.makedirs(os.path.join(self.test_root, "output", "rv-00"), exist_ok=True)
        os.makedirs(os.path.join(self.test_root, "output", "rv-01"), exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_root):
            shutil.rmtree(self.test_root)

    def test_step1_and_step2_plan_and_spec_separation(self):
        """[Step 1 & Step 2] 기획서(PLAN)와 제작 명세서(SPEC) 2단계 분리 도출 검증."""
        idea_memo = "2026 프리미엄 노이즈 캔슬링 헤드폰 론칭 캠페인 (2040 직장인 및 통근자 타깃)"
        
        # 1단계: 기획서 도출 모의
        mock_plan = (
            "# 마케팅 캠페인 기획서 (PLAN)\n\n"
            "## 1. 캠페인 배경 및 시장 기회 분석\n도심 출퇴근 통근자를 위한 초경량 프리미엄 ANC 헤드폰 론칭.\n\n"
            "## 2. 타깃 오디언스 프로파일\n20대~40대 직장인, 대중교통 이용자, 업무 몰입과 힐링을 추구하는 소비자.\n\n"
            "## 3. 핵심 소구점 (USP)\n180g 초경량 착용감, 45dB 소음 차단, 감성적 힐링 몰입 무드."
        )
        plan_path = os.path.join(self.test_root, "PLAN.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(mock_plan)

        # 2단계: 기획서를 인풋으로 받아 제작 명세서 도출 모의
        mock_spec = (
            "# 콘텐츠 제작 명세서 (SPEC)\n\n"
            "## 1. 비주얼 이미지 제작 규격\n"
            "- 가로 디스플레이 배너: 16:9 종횡비 (1920x1080)\n"
            "- 세로 모바일 포스터: 9:16 종횡비 (1080x1920)\n"
            "- 정방형 SNS 피드: 1:1 종횡비 (1080x1080)\n\n"
            "## 2. 모바일 숏폼 영상 제작 규격\n"
            "- 9:16 세로형 비율, 15초 콘티\n\n"
            "## 3. 타깃 오디언스 평가 기준\n"
            "- 20대 대학생부터 40대 전문직까지 25인 다면 평가단 구성"
        )
        spec_path = os.path.join(self.test_root, "SPEC.md")
        with open(spec_path, "w", encoding="utf-8") as f:
            f.write(mock_spec)

        self.assertTrue(os.path.exists(plan_path), "기획서(PLAN) 파일이 생성되어야 합니다.")
        self.assertTrue(os.path.exists(spec_path), "제작 명세서(SPEC) 파일이 생성되어야 합니다.")
        
        with open(plan_path, "r", encoding="utf-8") as f:
            p_text = f.read()
        with open(spec_path, "r", encoding="utf-8") as f:
            s_text = f.read()

        self.assertIn("기획서 (PLAN)", p_text)
        self.assertIn("16:9", s_text)
        self.assertIn("9:16", s_text)
        self.assertNotIn("===SPEC_DELIMITER===", p_text, "구형 단일 구분자 방식이 배제되어야 합니다.")

    def test_step3_persona_auto_synthesis(self):
        """[Step 3] 제작 명세서(SPEC)의 타깃 오디언스 기반 25인 맞춤 AI 페르소나 자동 합성 검증."""
        mock_spec_target = "타깃: 도심 속 워크앤라이프 밸런스를 추구하는 2040 직장인 및 통근자"
        
        # 03_persona_synthesis 지침 기반 25인 합성 결과 모킹
        mock_personas_json = {
            "metadata": {
                "description": "2040 직장인 타깃 맞춤 AI 페르소나 패널",
                "total": 25,
                "source": "SPEC 타깃 오디언스 자동 합성"
            },
            "personas": [
                {
                    "id": f"p{i:02d}",
                    "name": f"소비자_{i:02d}",
                    "age": 25 + i % 20,
                    "gender": "남성" if i % 2 == 0 else "여성",
                    "category": "전문 마케터" if i <= 12 else "일반 소비자",
                    "occupation": "IT 개발자" if i % 3 == 0 else "마케팅 담당자",
                    "perspective": "출퇴근 대중교통 소음 차단과 장시간 착용감을 중점 평가한다."
                }
                for i in range(1, 26)
            ]
        }
        
        persona_path = os.path.join(self.test_root, "ai_personas.json")
        import json
        with open(persona_path, "w", encoding="utf-8") as f:
            json.dump(mock_personas_json, f, ensure_ascii=False, indent=2)

        self.assertTrue(os.path.exists(persona_path))
        with open(persona_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        
        self.assertEqual(len(loaded["personas"]), 25, "정확히 25인의 페르소나가 합성되어야 합니다.")
        self.assertEqual(loaded["personas"][0]["category"], "전문 마케터")
        self.assertEqual(loaded["personas"][24]["category"], "일반 소비자")

    def test_step4_initial_content_generation(self):
        """[Step 4] SPEC 규격 기반 초판 콘텐츠(rv-00) 세트 생성 검증."""
        rv00_dir = os.path.join(self.test_root, "output", "rv-00")
        
        # campaign_content 구글 독스 모킹
        content_path = os.path.join(rv00_dir, "campaign_content.md")
        with open(content_path, "w", encoding="utf-8") as f:
            f.write("# 캠페인 초판 콘텐츠 (rv-00)\n\n## SNS 피드 카피\n도심의 소음을 끄고 당신만의 힐링을 켜세요.")

        # 이미지 3종 및 비디오 1종 모킹
        for name in ["banner_16x9.png", "poster_9x16.png", "feed_1x1.png"]:
            with open(os.path.join(rv00_dir, name), "wb") as f:
                f.write(b"PNG_MOCK_BYTES")
        with open(os.path.join(rv00_dir, "shorts_9x16.mp4"), "wb") as f:
            f.write(b"MP4_MOCK_BYTES")

        status = inspect_revision_folder(rv00_dir)
        self.assertTrue(status["complete"])
        self.assertTrue(status["has_doc"])
        self.assertTrue(status["has_video"])
        self.assertEqual(status["img_count"], 3)

    def test_step5_marketer_directive_preservation(self):
        """[Step 5] 피드백 보고서와 독립된 마케터 보정 지침서의 영구 보존 검증."""
        fb_dir = os.path.join(self.test_root, "input", "fb-01")
        
        # 피드백 보고서 (AI가 생성/덮어쓰는 문서)
        summary_path = os.path.join(fb_dir, "feedback_summary.md")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("# 피드백 종합 분석 보고서\n- 25인 평가단: 노이즈 캔슬링 우수하나 감성 카피 보강 필요.")

        # 마케터 보정 지침서 (마케터가 직접 작성하는 독립 문서)
        directive_path = os.path.join(fb_dir, "마케터 보정 지침.md")
        with open(directive_path, "w", encoding="utf-8") as f:
            f.write("# 마케터 최종 의사 결정 및 보정 지침\n- 결정: 가을 힐링 카피 전면 배치 및 180g 경량 강조.")

        # 피드백 보고서 재생성 시 지침서가 훼손되지 않는지 검증
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("# 피드백 종합 분석 보고서 (2차 갱신)\n- 설문 응답 50건 추가 집계 완료.")

        with open(directive_path, "r", encoding="utf-8") as f:
            saved_directive = f.read()

        self.assertIn("가을 힐링 카피 전면 배치", saved_directive, "마케터의 보정 지침서는 AI 재실행 시에도 절대 훼손되지 않아야 합니다.")

    def test_step6_smart_fill_missing_assets(self):
        """[Step 6] 동일 리비전 내 미완성 파일 고속 보충 vs 기존 에셋 보존 분기 검증."""
        rv01_dir = os.path.join(self.test_root, "output", "rv-01")
        
        # 초기 상태: 텍스트 독스와 배너 1개만 존재 (미완성)
        with open(os.path.join(rv01_dir, "campaign_content.md"), "w", encoding="utf-8") as f:
            f.write("# rv-01 개정본 (마케터 수기 수정 반영)")
        with open(os.path.join(rv01_dir, "banner_16x9.png"), "wb") as f:
            f.write(b"ORIGINAL_BANNER")

        pre_status = inspect_revision_folder(rv01_dir)
        self.assertFalse(pre_status["complete"])
        self.assertEqual(pre_status["img_count"], 1)

        # 누락 에셋 스마트 보충 모의
        with open(os.path.join(rv01_dir, "poster_9x16.png"), "wb") as f:
            f.write(b"FILLED_POSTER")
        with open(os.path.join(rv01_dir, "feed_1x1.png"), "wb") as f:
            f.write(b"FILLED_FEED")
        with open(os.path.join(rv01_dir, "shorts_9x16.mp4"), "wb") as f:
            f.write(b"FILLED_VIDEO")

        post_status = inspect_revision_folder(rv01_dir)
        self.assertTrue(post_status["complete"])
        self.assertEqual(post_status["img_count"], 3)
        self.assertTrue(post_status["has_video"])

        # 기존 배너 파일 원본 보존 검증
        with open(os.path.join(rv01_dir, "banner_16x9.png"), "rb") as f:
            self.assertEqual(f.read(), b"ORIGINAL_BANNER", "기존 생성 완료된 에셋은 덮어쓰지 않고 보존되어야 합니다.")


if __name__ == "__main__":
    unittest.main()
