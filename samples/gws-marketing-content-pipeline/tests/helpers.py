# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Drive Marketing Content Pipeline - Test Helpers & SUT Functions."""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple


def safe_extract_json(text: str) -> Optional[str]:
    """LLM 응답 텍스트에서 비정형 사족을 걷어내고 순수 JSON 문자열만 추출한다."""
    if not text:
        return None
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
    first_brace = cleaned.find("{")
    first_bracket = cleaned.find("[")
    if first_brace == -1 and first_bracket == -1:
        return None
    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        start_idx = first_brace
        end_idx = cleaned.rfind("}")
    else:
        start_idx = first_bracket
        end_idx = cleaned.rfind("]")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return cleaned[start_idx : end_idx + 1]
    return cleaned


def safe_parse_json(text: str, fallback: Any = None, expect_array: bool = False) -> Any:
    """안전한 JSON 파싱을 수행하며 실패 시 지정된 기본값(fallback)을 반환한다."""
    extracted = safe_extract_json(text)
    if not extracted:
        return fallback
    try:
        data = json.loads(extracted)
        if expect_array and not isinstance(data, list):
            return fallback
        return data
    except Exception:
        return fallback


def inspect_revision_folder(folder_path: str) -> Dict[str, bool]:
    """특정 리비전 폴더 내 필수 에셋(구글 독스, 이미지 3종, 숏폼 비디오)의 완성도를 실사한다."""
    if not os.path.exists(folder_path):
        return {"complete": False, "has_doc": False, "has_video": False, "img_count": 0}
    files = os.listdir(folder_path)
    has_doc = any(f.endswith(".md") or f.endswith(".txt") or f == "campaign_content" for f in files)
    has_video = any(f.endswith(".mp4") for f in files)
    img_count = sum(1 for f in files if f.endswith(".png") or f.endswith(".jpg"))
    is_complete = has_doc and has_video and (img_count >= 3)
    return {
        "complete": is_complete,
        "has_doc": has_doc,
        "has_video": has_video,
        "img_count": img_count,
    }
