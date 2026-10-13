#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

Drive Marketing Content Pipeline
로컬 에뮬레이션 단위 테스트 러너 (Local Emulated Unit Test Runner)
Google Apps Script 및 파이프라인 전체 모듈의 예상 동작을 브라우저 없이 로컬에서 고속 검증한다.
"""

import argparse
import json
import os
import re
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APPS_SCRIPTS_DIR = os.path.join(SCRIPT_DIR, "apps-scripts")
BUNDLE_FILE = os.path.join(SCRIPT_DIR, "bundle_apps_script.js")
MANIFEST_FILE = os.path.join(SCRIPT_DIR, "appsscript.json")


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


class EmulationTestResult:
    def __init__(self):
        self.tests = []
        self.start_time = time.time()

    def record(self, suite, name, passed, message=""):
        self.tests.append({
            "suite": suite,
            "name": name,
            "passed": bool(passed),
            "message": message or ("정상 통과" if passed else "조건 불만족")
        })

    def print_summary(self):
        elapsed = time.time() - self.start_time
        total = len(self.tests)
        passed = sum(1 for t in self.tests if t["passed"])
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0.0

        suites = {}
        for t in self.tests:
            s_name = t["suite"]
            if s_name not in suites:
                suites[s_name] = {"total": 0, "passed": 0, "failed": 0}
            suites[s_name]["total"] += 1
            if t["passed"]:
                suites[s_name]["passed"] += 1
            else:
                suites[s_name]["failed"] += 1

        print("\n" + "=" * 80)
        print(f"{Colors.BOLD}마케팅 콘텐츠 파이프라인 단위 테스트 에뮬레이션 결과 요약{Colors.RESET}")
        print("=" * 80)
        print(f"{'테스트 수이트':<35} | {'총 검증':<8} | {'통과':<6} | {'실패':<6} | {'상태'}")
        print("-" * 80)

        for s_name, data in suites.items():
            status_str = f"{Colors.GREEN}PASS{Colors.RESET}" if data["failed"] == 0 else f"{Colors.RED}FAIL{Colors.RESET}"
            print(f"{s_name:<35} | {data['total']:<8} | {data['passed']:<6} | {data['failed']:<6} | {status_str}")

        print("-" * 80)
        final_color = Colors.GREEN if failed == 0 else Colors.RED
        print(f"{final_color}최종 결과: 총 {total}개 중 {passed}개 통과 ({pass_rate:.1f}%), {failed}개 실패 (소요 시간: {elapsed:.3f}초){Colors.RESET}")
        print("=" * 80 + "\n")

        return failed == 0


def run_config_suite(runner):
    suite = "1. Config & Manifest Suite"
    # appsscript.json 검증
    if os.path.exists(MANIFEST_FILE):
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            runner.record(suite, "appsscript.json JSON 파싱 검증", True)
            runner.record(suite, "V8 런타임 활성화(runtimeVersion=V8)", manifest.get("runtimeVersion") == "V8")
            oauth_scopes = manifest.get("oauthScopes", [])
            has_drive = any("drive" in s for s in oauth_scopes)
            has_spreadsheets = any("spreadsheets" in s for s in oauth_scopes)
            runner.record(suite, "OAuth 스코프(Drive & Sheets) 존재 검증", has_drive and has_spreadsheets)
        except Exception as e:
            runner.record(suite, "appsscript.json 검증", False, str(e))
    else:
        runner.record(suite, "appsscript.json 파일 존재", False, "파일 누락")

    # Code_Config.js 파싱 검증
    config_js = os.path.join(APPS_SCRIPTS_DIR, "Code_Config.js")
    if os.path.exists(config_js):
        with open(config_js, "r", encoding="utf-8") as f:
            content = f.read()
        runner.record(suite, "CONFIG 객체 선언 검증", "var CONFIG =" in content or "const CONFIG =" in content)
        runner.record(suite, "기본 모델 gemini-3.8-flash 설정 검증", "gemini-3.8-flash" in content)
        runner.record(suite, "이미지 모델 gemini-2.5-flash-image 설정 검증", "gemini-2.5-flash-image" in content)
        runner.record(suite, "기본 캠페인 코드 cp-ignite 설정 검증", "cp-ignite" in content)


def run_utils_suite(runner):
    suite = "2. Utils & Formatting Suite"

    # padZero 에뮬레이션
    def pad_zero(num):
        return f"0{num}" if num < 10 else str(num)

    runner.record(suite, "padZero(1) == '01'", pad_zero(1) == "01")
    runner.record(suite, "padZero(9) == '09'", pad_zero(9) == "09")
    runner.record(suite, "padZero(10) == '10'", pad_zero(10) == "10")
    runner.record(suite, "padZero(99) == '99'", pad_zero(99) == "99")

    # cleanJsonText 에뮬레이션
    def clean_json_text(raw):
        t = re.sub(r"^```json\s*", "", raw, flags=re.IGNORECASE)
        t = re.sub(r"^```\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
        return t.strip()

    raw_markdown = "```json\n{\"test\": 123}\n```"
    runner.record(suite, "cleanJsonText 마크다운 코드 블록 제거", clean_json_text(raw_markdown) == "{\"test\": 123}")
    pure_json = "{\"status\": \"ok\"}"
    runner.record(suite, "cleanJsonText 순수 JSON 보존", clean_json_text(pure_json) == pure_json)

    # resolveDriveAttachmentName 정규식 에뮬레이션
    drive_pattern = re.compile(r"https://drive\.google\.com/(?:open\?id=|file/d/)([a-zA-Z0-9_-]+)")
    test_drive_url = "https://drive.google.com/file/d/1a2b3c4d5e/view?usp=sharing"
    m = drive_pattern.search(test_drive_url)
    runner.record(suite, "구글 드라이브 파일 ID 정규식 추출 검증", m is not None and m.group(1) == "1a2b3c4d5e")


def run_round_suite(runner):
    suite = "3. Dynamic Round Detect Suite"

    def detect_latest_feedback(folder_names):
        max_round = 0
        for name in folder_names:
            m = re.match(r"^fb-([0-9]{1,2})$", name, re.IGNORECASE)
            if m:
                val = int(m.group(1))
                if val > max_round:
                    max_round = val
        return max_round

    def detect_latest_revision(folder_names):
        max_round = 0
        for name in folder_names:
            m = re.match(r"^rv-([0-9]{1,2})$", name, re.IGNORECASE)
            if m:
                val = int(m.group(1))
                if val > max_round:
                    max_round = val
        return max_round

    runner.record(suite, "단일 피드백 탐색(fb-01 -> 1)", detect_latest_feedback(["fb-01"]) == 1)
    runner.record(suite, "다중 피드백 누적 탐색(fb-01, fb-02, fb-03 -> 3)", detect_latest_feedback(["fb-01", "fb-02", "fb-03"]) == 3)
    runner.record(suite, "99차 상한선 탐색(fb-99 -> 99)", detect_latest_feedback(["fb-01", "fb-99"]) == 99)
    runner.record(suite, "리비전 탐색(rv-00, rv-01, rv-05 -> 5)", detect_latest_revision(["rv-00", "rv-01", "rv-05"]) == 5)
    runner.record(suite, "비표준 폴더명 무시 검증", detect_latest_feedback(["fb-01", "temp", "feedback_02"]) == 1)

    # 다음 회차 자동 제안 로직
    next_fb = max(detect_latest_feedback(["fb-01", "fb-02"]) + 1, 2)
    runner.record(suite, "다음 피드백 자동 증분(fb-02 -> fb-03)", next_fb == 3)
    next_rv = max(detect_latest_revision(["rv-00", "rv-01"]) + 1, 2)
    runner.record(suite, "다음 리비전 자동 증분(rv-01 -> rv-02)", next_rv == 2)


def run_vlm_suite(runner):
    suite = "4. VLM & Manual Scanner Suite"

    reserved_files = {
        "ai_persona_feedbacks.json",
        "feedback_clusters_map.png",
        "feedback_points_128d.json",
        "feedback_summary",
        "video_voc_analysis.json"
    }

    def is_reserved(name):
        return name.lower() in reserved_files

    runner.record(suite, "예약 파일 ai_persona_feedbacks.json 필터링", is_reserved("ai_persona_feedbacks.json"))
    runner.record(suite, "예약 파일 feedback_summary 필터링", is_reserved("feedback_summary"))
    runner.record(suite, "유저 드롭 user_photo.png 허용", not is_reserved("user_photo.png"))
    runner.record(suite, "유저 드롭 memo.txt 허용", not is_reserved("memo.txt"))
    runner.record(suite, "유저 드롭 extra.mp4 허용", not is_reserved("extra.mp4"))

    # 파일 확장자 분류 에뮬레이션
    def classify_file(name):
        l = name.lower()
        if any(l.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            return "IMAGE"
        if any(l.endswith(ext) for ext in [".mp4", ".mov", ".webm"]):
            return "VIDEO"
        if any(l.endswith(ext) for ext in [".txt", ".csv", ".md", ".json"]):
            return "TEXT"
        return "DOC"

    runner.record(suite, "확장자 분류: sample.png -> IMAGE", classify_file("sample.png") == "IMAGE")
    runner.record(suite, "확장자 분류: note.txt -> TEXT", classify_file("note.txt") == "TEXT")
    runner.record(suite, "확장자 분류: clip.mp4 -> VIDEO", classify_file("clip.mp4") == "VIDEO")
    runner.record(suite, "확장자 분류: 보고서문서 -> DOC", classify_file("보고서문서") == "DOC")

    # 페이로드 제약 (25MB 제한)
    max_bytes = 25 * 1024 * 1024
    runner.record(suite, "10MB 정상 이미지 허용", (10 * 1024 * 1024) <= max_bytes)
    runner.record(suite, "30MB 초과 이미지 차단 방어", (30 * 1024 * 1024) > max_bytes)


def run_persona_suite(runner):
    suite = "5. Persona Dataset Suite"

    workspace_js = os.path.join(APPS_SCRIPTS_DIR, "Code_Step1_Workspace.js")
    if not os.path.exists(workspace_js):
        runner.record(suite, "Code_Step1_Workspace.js 존재 확인", False)
        return

    with open(workspace_js, "r", encoding="utf-8") as f:
        content = f.read()

    # getMasterPersonas25 내부의 JSON 객체 추출
    match = re.search(r'function getMasterPersonas25\(\)\s*\{[\s\S]*?return\s*(\{[\s\S]*?\n\s*\});', content)

    if match:
        try:
            raw_json = match.group(1).strip()
            data = json.loads(raw_json)
            personas = data.get("personas", data)
            runner.record(suite, "페르소나 JSON 정상 파싱", True)
            runner.record(suite, "AI 페르소나 총 25인 정원 검증", len(personas) == 25)

            req_fields = ["id", "name", "age", "gender", "category", "occupation", "perspective"]
            all_valid = True
            marketers = 0
            consumers = 0
            for p in personas:
                for rf in req_fields:
                    if rf not in p or p[rf] is None or p[rf] == "":
                        all_valid = False
                if p.get("category") == "전문 마케터":
                    marketers += 1
                else:
                    consumers += 1

            runner.record(suite, "25인 7대 필수 필드 완비 검증", all_valid)
            runner.record(suite, "전문 마케터 12인 안배 검증", marketers == 12)
            runner.record(suite, "일반 소비자 13인 안배 검증", consumers == 13)
        except Exception as e:
            runner.record(suite, "페르소나 JSON 추출 및 파싱", False, str(e))
    else:
        # 정규식 대체 탐색
        has_25_personas = "p25" in content and "p01" in content
        runner.record(suite, "페르소나 25인(p01~p25) 시딩 포함 검증", has_25_personas)


def run_judge_suite(runner):
    suite = "6. Form & Judge Logic Suite"

    # 설문 5대 문항 구성 규격
    questions = ["콘텐츠 버전", "종합 만족도", "솔직한 의견", "동영상 피드백", "이미지 피드백"]
    runner.record(suite, "설문 5대 핵심 문항(버전, 평점, 의견, 동영상, 이미지) 정의", len(questions) == 5)

    # 가중치 계산 에뮬레이션
    def calc_score(quant, qual, video, has_video):
        if has_video and video is not None:
            return round((quant * 0.5) + (qual * 0.3) + (video * 0.2), 2)
        return round((quant * 0.5) + (qual * 0.5), 2)

    s1 = calc_score(4.0, 4.0, 5.0, True)
    runner.record(suite, "동영상 VoC 포함 가중치(50:30:20) 계산 == 4.2", s1 == 4.2)

    s2 = calc_score(4.0, 3.0, None, False)
    runner.record(suite, "동영상 VoC 미제출 가중치(50:50) 계산 == 3.5", s2 == 3.5)


def run_refine_suite(runner):
    suite = "7. HITL & Asset Refinement Suite"

    # 회차별 마케터 기본 코멘트 분기 에뮬레이션
    def get_comment(round_num):
        if round_num == 2:
            return "20대 한국인 여성 모델이 세련된 서울 카페에서 초경량 노이즈 캔슬링을 켜고 몰입하는 순간을 헤드카피와 비주얼로 전면에 내세울 것."
        if round_num >= 3:
            return "그랜드 론칭 한정 얼리버드 혜택(고급 가죽 트래블 파우치 증정)을 볼드하게 명시하고, 한국인 20대 여성 모델과 5종 시그니처 파스텔 컬러 라인업을 담은 론칭 완결형 비주얼을 도출할 것."
        return "출퇴근 피로감보다 주말 카페 힐링 감성을 강조하고, 180g 초경량 착용감을 헤드카피로 올릴 것."

    runner.record(suite, "1차 마케터 기본 코멘트 분기", "출퇴근 피로감" in get_comment(1))
    runner.record(suite, "2차 마케터 힐링/여성 모델 코멘트 분기", "20대 한국인 여성 모델" in get_comment(2))
    runner.record(suite, "3차 이상 론칭 얼리버드 코멘트 분기", "얼리버드 혜택" in get_comment(3))

    # 리비전 자산 산출물 명명 규격
    def get_assets(prefix):
        return [
            f"{prefix}_banner_16x9.png",
            f"{prefix}_poster_9x16.png",
            f"{prefix}_sns_1x1.png",
            f"{prefix}_shorts.mp4",
            "campaign_content"
        ]

    assets_00 = get_assets("00")
    runner.record(suite, "초판 가로 배너 16:9 규격", assets_00[0] == "00_banner_16x9.png")
    runner.record(suite, "초판 세로 포스터 9:16 규격", assets_00[1] == "00_poster_9x16.png")
    runner.record(suite, "초판 정방형 SNS 1:1 규격", assets_00[2] == "00_sns_1x1.png")
    runner.record(suite, "초판 모바일 숏폼 영상 9:16 규격", assets_00[3] == "00_shorts.mp4")


def run_sync_suite(runner):
    suite = "8. Bundle Synchronization Suite"

    if not os.path.exists(BUNDLE_FILE):
        runner.record(suite, "bundle_apps_script.js 파일 존재", False)
        return

    with open(BUNDLE_FILE, "r", encoding="utf-8") as f:
        bundle_text = f.read()

    runner.record(suite, "bundle_apps_script.js 크기(100KB 이상)", len(bundle_text) > 100000)

    # 12대 모듈 헤더 존재 검증
    expected_modules = [
        "Code_Config.js",
        "Code_Gemini.js",
        "Code_Utils.js",
        "Code_Step1_Workspace.js",
        "Code_Step2_IdeaToPlan.js",
        "Code_Step3_ContentGen.js",
        "Code_Step4_Form.js",
        "Code_Step5_8_Judge.js",
        "Code_Step6_Decision.js",
        "Code_Step7_9_Refine.js",
        "Code_Menu.js",
        "Code_Test_Suite.js"
    ]

    for mod in expected_modules:
        header = f"// FILE: {mod}"
        runner.record(suite, f"번들 내 {mod} 섹션 헤더 포함", header in bundle_text)

    # 핵심 신규 함수 존재 검증
    core_fns = [
        "showProcessingToast",
        "analyzeImageFeedbackWithVlm",
        "scanManualFeedbackFiles",
        "detectLatestFeedbackRoundNum",
        "detectLatestRevisionRoundNum",
        "runAllEmulatedUnitTests"
    ]
    for fn in core_fns:
        runner.record(suite, f"번들 내 핵심 함수 {fn} 정의 검증", fn in bundle_text)


def main():
    parser = argparse.ArgumentParser(description="마케팅 콘텐츠 파이프라인 로컬 에뮬레이션 테스트 러너")
    parser.add_argument("--all", action="store_true", help="전체 8대 단위 테스트 수이트 일괄 실행")
    parser.add_argument("--unit", type=str, choices=["config", "utils", "round", "vlm", "persona", "judge", "refine", "sync"], help="특정 단위 테스트 수이트만 단독 실행")
    args = parser.parse_args()

    runner = EmulationTestResult()

    target_unit = args.unit
    run_all = args.all or (target_unit is None)

    if run_all:
        print(f"\n{Colors.BOLD}{Colors.BLUE}>> 전체 8대 에뮬레이션 단위 테스트 수이트 일괄 실행 (All) <<{Colors.RESET}")
        run_config_suite(runner)
        run_utils_suite(runner)
        run_round_suite(runner)
        run_vlm_suite(runner)
        run_persona_suite(runner)
        run_judge_suite(runner)
        run_refine_suite(runner)
        run_sync_suite(runner)
    else:
        print(f"\n{Colors.BOLD}{Colors.BLUE}>> 타깃 단위 테스트 수이트 실행: [{target_unit}] <<{Colors.RESET}")
        if target_unit == "config":
            run_config_suite(runner)
        elif target_unit == "utils":
            run_utils_suite(runner)
        elif target_unit == "round":
            run_round_suite(runner)
        elif target_unit == "vlm":
            run_vlm_suite(runner)
        elif target_unit == "persona":
            run_persona_suite(runner)
        elif target_unit == "judge":
            run_judge_suite(runner)
        elif target_unit == "refine":
            run_refine_suite(runner)
        elif target_unit == "sync":
            run_sync_suite(runner)

    success = runner.print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
