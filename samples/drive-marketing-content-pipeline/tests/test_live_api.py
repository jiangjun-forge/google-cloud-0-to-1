#!/usr/bin/env python3
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Drive Marketing Content Pipeline - Live API Integration Tests.

실제 Google AI Studio REST API 엔드포인트(Gemini Flash, Nano Banana)를
직접 호출하여 토큰 계측 및 모델 응답 무결성을 검증하는 통합 테스트 모듈이다.
"""

import base64
import json
import os
import unittest
import urllib.error
import urllib.request
from typing import Optional

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def probe_live_gemini_text(api_key: str) -> Optional[str]:
    """Gemini 텍스트 모델 직접 호출 프로브."""
    url = f"{BASE_URL}/models/gemini-3.8-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": "마케팅 캠페인 슬로건 1줄을 작성하라 (예: 도심 속 당신만의 힐링)"}
                ]
            }
        ],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 100},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            usage = data.get("usageMetadata", {})
            total_tokens = usage.get("totalTokenCount", 0)
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"  성공: gemini-3.8-flash 응답 수신 (소모 토큰: {total_tokens}) -> {text}")
            return text
    except Exception as e:
        print(f"  실패: Gemini 텍스트 호출 오류: {e}")
        return None


def probe_live_nano_banana_image(api_key: str, out_dir: str = "test_output") -> Optional[str]:
    """Gemini Nano Banana 2.1 이미지 모델 직접 호출 프로브."""
    url = f"{BASE_URL}/models/gemini-nano-banana-2.1:generateContent?key={api_key}"
    prompt = "A modern lightweight ANC headphone sitting on an aesthetic wooden cafe table in warm autumn afternoon light, 16:9 banner"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "image/png",
            "aspectRatio": "16:9",
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            part = data["candidates"][0]["content"]["parts"][0]
            if "inlineData" in part:
                b64 = part["inlineData"]["data"]
                img_bytes = base64.b64decode(b64)
                os.makedirs(out_dir, exist_ok=True)
                out_path = os.path.join(out_dir, "test_banner_16x9.png")
                with open(out_path, "wb") as f:
                    f.write(img_bytes)
                print(f"  성공: gemini-nano-banana-2.1 이미지 생성 완료 ({len(img_bytes):,} bytes) -> {out_path}")
                return out_path
    except Exception as e:
        print(f"  실패: Nano Banana 이미지 호출 오류: {e}")
        return None


class LiveApiIntegrationTest(unittest.TestCase):
    """Google AI Studio 라이브 API 통합 테스트 수이트."""

    def test_live_text_probe(self):
        """API 키가 주어졌을 때 실제 Gemini 호출 검증."""
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            self.skipTest("GEMINI_API_KEY 환경 변수가 설정되지 않아 라이브 API 테스트를 건너뜁니다.")
        res = probe_live_gemini_text(api_key)
        self.assertIsNotNone(res)
        self.assertGreater(len(res), 3)


if __name__ == "__main__":
    unittest.main()
