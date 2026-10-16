#!/usr/bin/env python3
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Drive Marketing Content Pipeline - Apps Script Bundler.

apps-scripts/ 디렉터리의 9대 모듈을 단일 번들 파일(bundle_apps_script.js)로 병합하고,
구문 검증 및 엔진 버전을 판올림한다.
"""

import os
import re
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APPS_SCRIPTS_DIR = os.path.join(BASE_DIR, "apps-scripts")
BUNDLE_FILE = os.path.join(BASE_DIR, "bundle_apps_script.js")
BOOTSTRAP_FILE = os.path.join(BASE_DIR, "bootstrap.js")

MODULE_FILES = [
    "Code_Config.js",
    "Code_Gemini.js",
    "Code_Prompts.js",
    "Code_Utils.js",
    "Code_Workspace.js",
    "Code_Content.js",
    "Code_Feedback.js",
    "Code_Sidebar.js",
    "Code_Menu.js"
]

HEADER = """/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline - Consolidated Engine Bundle
 * Generated automatically from modular apps-scripts/
 */
"""


def build_bundle():
    """9대 모듈을 bundle_apps_script.js로 번들링한다."""
    parts = [HEADER]
    for filename in MODULE_FILES:
        filepath = os.path.join(APPS_SCRIPTS_DIR, filename)
        if not os.path.exists(filepath):
            print(f"[Error] 모듈 파일 누락: {filepath}", file=sys.stderr)
            sys.exit(1)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
        parts.append(f"\n// ==========================================\n// Module: {filename}\n// ==========================================\n" + content)

    bundle_content = "\n".join(parts) + "\n"

    with open(BUNDLE_FILE, "w", encoding="utf-8") as f:
        f.write(bundle_content)
    print(f"[Success] bundle_apps_script.js 생성 완료 ({len(bundle_content):,} bytes)")

    # 구문 검증
    try:
        res = subprocess.run(["node", "-c", BUNDLE_FILE], capture_output=True, text=True, check=True)
        print("[Success] bundle_apps_script.js 구문 검증(Syntax Check) 통과")
    except subprocess.CalledProcessError as e:
        print(f"[Error] bundle_apps_script.js 구문 오류:\n{e.stderr}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    build_bundle()
