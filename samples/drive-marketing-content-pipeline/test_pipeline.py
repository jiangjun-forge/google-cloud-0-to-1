#!/usr/bin/env python3
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Drive Marketing Content Pipeline - Local Verification Test Runner

구글 시트나 Apps Script 콘솔에 일일이 수동 복사-붙여넣기하지 않고도,
로컬 Cloudtop 터미널 환경에서 Google AI Studio API 엔드포인트 및
콘텐츠/이미지/비디오 생성 파이프라인을 10초 만에 직접 검증하는 테스트 도구다.
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request


BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def parse_args():
    parser = argparse.ArgumentParser(description="Drive Marketing Content Pipeline Local Tester")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("GEMINI_API_KEY", ""),
        help="Google AI Studio Gemini API Key (or set GEMINI_API_KEY env var)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 API 호출 없이 가상 모의 데이터로 로컬 파이프라인 검증"
    )
    parser.add_argument(
        "--skip-video",
        action="store_true",
        help="비디오 생성(Veo) 생략하고 텍스트 및 이미지만 검증"
    )
    return parser.parse_args()


def test_text_generation(api_key: str, dry_run: bool = False):
    print("\n[1/3] 텍스트 마케팅 카피 생성 검증 (gemini-3.8-flash)...")
    if dry_run:
        print("  [가상 실행] gemini-3.8-flash 모의 카피 응답 성공 (Pass)")
        return "프리미엄 노이즈 캔슬링 헤드폰 - 도심의 소음을 지우고 온전한 나만의 쉼표를 만나다."

    url = f"{BASE_URL}/models/gemini-3.8-flash:generateContent?key={api_key}"
    prompt = (
        "프리미엄 노이즈 캔슬링 헤드폰 론칭 캠페인 카피라이팅 헤드카피 3종과 "
        "모바일 숏폼 영상 콘티(15초 9:16)를 200자 내외로 컴팩트하게 작성하라."
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}
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
            print("  성공! 생성된 카피 미리보기:\n  " + text[:150].replace("\n", "\n  ") + "...")
            return text
    except Exception as e:
        print(f"  실패: {e}")
        return None


def test_image_generation(api_key: str, dry_run: bool = False, output_dir: str = "test_output"):
    print("\n[2/3] 비주얼 광고 이미지 생성 검증 (gemini-nano-banana-2.1)...")
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, "00_banner_test.jpg")

    if dry_run:
        print(f"  [가상 실행] gemini-nano-banana-2.1 모의 이미지 생성 완료 -> {out_file} (Pass)")
        return out_file

    url = f"{BASE_URL}/models/gemini-nano-banana-2.1:generateContent?key={api_key}"
    prompt = "A modern Korean premium ANC headphone on wooden cafe table with warm golden autumn sunlight, photorealistic 8k studio lighting"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
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
                    print(f"  성공! 실제 생성된 이미지 저장 완료 ({len(img_bytes):,} bytes) -> {out_file}")
                    return out_file
            print("  실패: 응답에서 inlineData 이미지를 찾을 수 없습니다.")
    except Exception as e:
        print(f"  실패: {e}")
    return None


def test_video_generation(api_key: str, dry_run: bool = False, output_dir: str = "test_output"):
    print("\n[3/3] 모바일 숏폼 비디오 생성 검증 (veo-3.1-fast-generate-preview)...")
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, "00_shorts_test.mp4")

    if dry_run:
        print(f"  [가상 실행] veo-3.1-fast-generate-preview 모의 비디오 생성 완료 -> {out_file} (Pass)")
        return out_file

    model = "veo-3.1-fast-generate-preview"
    url = f"{BASE_URL}/models/{model}:predictLongRunning?key={api_key}"
    prompt = "Vertical mobile commercial video (9:16 aspect ratio), modern lightweight ANC headphone in Seoul street at sunset, cinematic lighting"
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {"aspectRatio": "9:16"}
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            init_data = json.loads(resp.read().decode("utf-8"))
            op_name = init_data.get("name")
            if not op_name:
                print(f"  실패: 작업 ID를 취득하지 못했습니다. 응답: {init_data}")
                return None
            print(f"  LRO 렌더링 작업 큐 등록 성공: {op_name}")
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"  초기 요청 실패 (HTTP {e.code}): {err_msg}")
        return None

    # LRO 폴링
    poll_url = f"{BASE_URL}/{op_name}?key={api_key}"
    print("  렌더링 진행 대기 폴링 중 (5초 간격)...", end="", flush=True)
    for attempt in range(1, 25):
        time.sleep(5)
        print(".", end="", flush=True)
        poll_req = urllib.request.Request(poll_url, headers={"x-goog-api-key": api_key})
        try:
            with urllib.request.urlopen(poll_req, timeout=20) as p_resp:
                p_data = json.loads(p_resp.read().decode("utf-8"))
                if p_data.get("done") is True:
                    print(f" 완료! ({attempt * 5}초 소요)")
                    resp_obj = p_data.get("response", {})
                    gen_resp = resp_obj.get("generateVideoResponse", resp_obj)
                    samples = gen_resp.get("generatedSamples", [])
                    if samples and "video" in samples[0]:
                        v_obj = samples[0]["video"]
                        v_uri = v_obj.get("uri")
                        if v_uri:
                            dl_url = v_uri + ("&key=" + api_key if "?" in v_uri else "?key=" + api_key)
                            dl_req = urllib.request.Request(dl_url, headers={"x-goog-api-key": api_key})
                            with urllib.request.urlopen(dl_req, timeout=60) as dl_resp:
                                vid_bytes = dl_resp.read()
                                with open(out_file, "wb") as f:
                                    f.write(vid_bytes)
                                print(f"  성공! 실제 생성된 비디오 다운로드 완료 ({len(vid_bytes):,} bytes) -> {out_file}")
                                return out_file
                    print(f"  실패: 비디오 응답 구조 파싱 불가: {p_data}")
                    return None
        except Exception as p_err:
            print(f"\n  폴링 중 예외 발생: {p_err}")

    print("\n  시간 초과: 120초 내에 비디오 렌더링이 완료되지 않았습니다.")
    return None


def main():
    args = parse_args()
    api_key = args.api_key.strip()

    if not api_key and not args.dry_run:
        print("오류: API Key가 지정되지 않았습니다.")
        print("사용법: python test_pipeline.py --api-key YOUR_API_KEY (또는 --dry-run)")
        sys.exit(1)

    print("================================================================")
    print("Drive Marketing Content Pipeline - 로컬 파이프라인 검증 러너")
    print(f"인증 모드: {'가상 실행 (Dry-run)' if args.dry_run else 'Google AI Studio REST 직접 호출'}")
    print("================================================================")

    # 1. 텍스트 카피 테스트
    t_res = test_text_generation(api_key, args.dry_run)
    
    # 2. 이미지 생성 테스트
    i_res = test_image_generation(api_key, args.dry_run)

    # 3. 비디오 생성 테스트
    v_res = None
    if not args.skip_video:
        v_res = test_video_generation(api_key, args.dry_run)

    print("\n================================================================")
    print("로컬 종합 검증 결과 요약:")
    print(f"  - 텍스트 모델 (gemini-3.8-flash):         {'정상 (PASS)' if t_res else '실패 (FAIL)'}")
    print(f"  - 이미지 모델 (gemini-nano-banana-2.1):    {'정상 (PASS)' if i_res else '실패 (FAIL)'}")
    if not args.skip_video:
        print(f"  - 비디오 모델 (veo-3.1-fast-generate):    {'정상 (PASS)' if v_res else '실패 (FAIL)'}")
    print("================================================================")


if __name__ == "__main__":
    main()
