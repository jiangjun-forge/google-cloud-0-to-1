#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""온프레미스 대용량 영상 STS 전송 및 KMS/VPC-SC 보안 검증 진단 도구."""

import argparse
import json
import os
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    """명령줄 인자를 파싱한다."""
    bw_val = os.getenv("BANDWIDTH_LIMIT_MB")
    parser = argparse.ArgumentParser(
        description="온프레미스 대용량 미디어 STS 보안 전송 파이프라인 진단기"
    )
    parser.add_argument(
        "-p",
        "--project",
        default=os.getenv("PROJECT_ID") or "",
        help="GCP 프로젝트 ID (지정하지 않을 경우 gcloud 기본 프로젝트 사용)",
    )
    parser.add_argument(
        "-b",
        "--bucket",
        default=os.getenv("TARGET_BUCKET") or "secure-media-archive",
        help="타깃 Cloud Storage 버킷명 (기본값: secure-media-archive)",
    )
    parser.add_argument(
        "-a",
        "--agent-pool",
        default=os.getenv("AGENT_POOL") or "on-prem-posix-pool",
        help="Storage Transfer Service 에이전트 풀 이름 (기본값: on-prem-posix-pool)",
    )
    parser.add_argument(
        "--bandwidth-limit",
        type=int,
        default=int(bw_val) if bw_val else 100,
        help="전송 대역폭 제한 (MB/s 단위, 기본값: 100)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 GCP API 호출 없이 모의 전송 시나리오 데이터로 가상 실행",
    )
    parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
    return parser.parse_args()


def detect_project_id(cli_project: str, is_dry_run: bool = False) -> str:
    """프로젝트 ID를 탐지하거나 대화형으로 선택한다."""
    if is_dry_run:
        return "sample-project-id"
    if cli_project:
        return cli_project
    env_proj = os.getenv("PROJECT_ID")
    if env_proj:
        return env_proj
    try:
        res = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            check=True,
        )
        detected = res.stdout.strip()
        if detected and "(unset)" not in detected:
            return detected
    except Exception:
        pass

    if not sys.stdin.isatty():
        return "sample-project-id"

    try:
        res = subprocess.run(
            ["gcloud", "projects", "list", "--format=value(projectId)", "--limit=5"],
            capture_output=True,
            text=True,
        )
        projects = [p.strip() for p in res.stdout.splitlines() if p.strip()]
        if projects:
            print("\n[?] 대상 GCP 프로젝트가 지정되지 않았다. 현재 접근 가능한 프로젝트 목록:")
            for idx, p in enumerate(projects, 1):
                print(f"  [{idx}] {p}")
            print(f"  [{len(projects) + 1}] 직접 입력 (Custom Input)")
            choice = input(f"선택할 번호 입력 [1-{len(projects) + 1}] (Enter 시 1번): ").strip()
            if not choice or choice == "1":
                return projects[0]
            if choice.isdigit() and 1 <= int(choice) <= len(projects):
                return projects[int(choice) - 1]
            if choice == str(len(projects) + 1):
                custom = input("프로젝트 ID 직접 입력: ").strip()
                if custom:
                    return custom
    except Exception:
        pass

    return "sample-project-id"


def get_mock_preflight_checks(bucket: str, pool: str) -> list[dict]:
    """가상 실행용 점검 결과를 반환한다."""
    return [
        {
            "step": "1. 온프렘 로컬 전처리",
            "item": "영상 비식별화 및 개인식별정보/번호판 마스킹",
            "status": "PASS",
            "detail": "142개 영상 파일(총 417GB) 전수 비식별화 메타데이터 태그 확인 완료",
        },
        {
            "step": "2. STS 에이전트 풀",
            "item": f"에이전트 풀 상태 ({pool})",
            "status": "PASS",
            "detail": "온프레미스 도커 에이전트 4대 정상 연결 (상태: CONNECTED, 버전: 최신)",
        },
        {
            "step": "3. 버킷 보안 통제",
            "item": f"타깃 버킷 공개 접근 차단 (PAP)",
            "status": "PASS",
            "detail": f"gs://{bucket} publicAccessPrevention=enforced 적용됨",
        },
        {
            "step": "4. 데이터 암호화",
            "item": "Cloud KMS CMEK 암호화 적용",
            "status": "PASS",
            "detail": f"서울 리전(asia-northeast3) KMS 키(projects/demo/locations/asia-northeast3/keyRings/nct/cryptoKeys/video-key) 바인딩됨",
        },
        {
            "step": "5. 무결성 검증 설정",
            "item": "CRC32c / MD5 체크섬 검증",
            "status": "PASS",
            "detail": "전송 중 손상 방지를 위한 청크 단위 CRC32c 해시 대조 자동 활성화",
        },
    ]


def run_gcloud_json(cmd: list[str]) -> dict | list | None:
    """gcloud 명령어를 JSON 출력 모드로 실행한다."""
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL)
        return json.loads(res.stdout)
    except Exception:
        return None


def inspect_live_sts(project_id: str, bucket: str, pool: str) -> list[dict]:
    """실제 GCP 환경의 STS 에이전트 풀 및 타깃 버킷 구성을 점검한다."""
    checks = []

    # 1. 버킷 메타데이터 조회
    b_cmd = ["gcloud", "storage", "buckets", "describe", f"gs://{bucket}", "--format=json"]
    b_meta = run_gcloud_json(b_cmd)

    if b_meta:
        # 공개 접근 차단 확인
        pap = b_meta.get("public_access_prevention", "unspecified")
        if pap == "enforced":
            checks.append({
                "step": "버킷 보안 통제",
                "item": "공개 접근 차단(PAP)",
                "status": "PASS",
                "detail": "publicAccessPrevention=enforced 적용 완료",
            })
        else:
            checks.append({
                "step": "버킷 보안 통제",
                "item": "공개 접근 차단(PAP)",
                "status": "FAIL",
                "detail": f"현재 설정({pap}): 비인가 외부 공개 위험 존재, enforced 설정 필요",
            })

        # CMEK 키 확인
        cmek = b_meta.get("default_kms_key_name", "")
        if cmek:
            checks.append({
                "step": "데이터 암호화",
                "item": "Cloud KMS CMEK 적용",
                "status": "PASS",
                "detail": f"적용 키: {cmek.split('/')[-1]}",
            })
        else:
            checks.append({
                "step": "데이터 암호화",
                "item": "Cloud KMS CMEK 적용",
                "status": "FAIL",
                "detail": "기본 구글 관리 키 사용 중, 엔터프라이즈 CMEK 키 지정 필요",
            })
    else:
        checks.append({
            "step": "버킷 보안 통제",
            "item": "타깃 버킷 접근성",
            "status": "FAIL",
            "detail": f"gs://{bucket} 버킷이 존재하지 않거나 권한이 부족하다.",
        })

    # 2. STS 에이전트 풀 조회
    pool_cmd = ["gcloud", "transfer", "agent-pools", "describe", pool, f"--project={project_id}", "--format=json"]
    pool_meta = run_gcloud_json(pool_cmd)

    if pool_meta:
        checks.append({
            "step": "STS 에이전트 풀",
            "item": f"에이전트 풀 ({pool})",
            "status": "PASS",
            "detail": "온프레미스 에이전트 풀 정상 등록됨",
        })
    else:
        checks.append({
            "step": "STS 에이전트 풀",
            "item": f"에이전트 풀 ({pool})",
            "status": "FAIL",
            "detail": f"{pool} 에이전트 풀이 생성되지 않았음",
        })

    return checks


def build_markdown_report(
    checks: list[dict],
    project_id: str,
    bucket: str,
    pool: str,
    limit_mb: int,
    is_dry_run: bool,
) -> str:
    """터미널 진단 결과를 반영한 마크다운 리포트를 생성한다."""
    mode_str = "모의 실행 (Dry-run)" if is_dry_run else "실제 환경 (Live)"
    lines = [
        "# 온프레미스 대용량 미디어 STS 전송 및 보안 무결성 사전 진단 리포트 (storage-transfer-secure-uploader)",
        "",
        f"- **진단 모드**: `{mode_str}`",
        f"- **대상 프로젝트**: `{project_id}`",
        f"- **타깃 버킷**: `gs://{bucket}`",
        f"- **STS 에이전트 풀**: `{pool}`",
        f"- **설정 대역폭 제한**: {limit_mb} MB/s",
        "- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용",
        "",
        "---",
        "",
        "## 1. 안전 전송 파이프라인 점검 현황",
        "",
        "| 단계 | 점검 항목 | 결과 | 상세 상태 |",
        "| :--- | :--- | :--- | :--- |",
    ]
    for c in checks:
        status_md = f"**{c['status']}**" if c['status'] in ("FAIL", "WARN") else c['status']
        lines.append(f"| {c['step']} | {c['item']} | {status_md} | {c['detail']} |")

    lines.extend([
        "",
        "---",
        "",
        "## 2. 전송 작업(Job) 생성 및 실행 가이드",
        "",
        "### 1. 온프레미스 에이전트 풀 생성 및 실행 토큰 발급",
        "```bash",
        f"gcloud transfer agent-pools create {pool} --project={project_id} --display-name='Secure On-Prem Pool'",
        "```",
        "",
        "### 2. 타깃 버킷 공개 접근 차단 및 CMEK 강제",
        "```bash",
        f"gcloud storage buckets update gs://{bucket} --public-access-prevention",
        f"gcloud storage buckets update gs://{bucket} --default-kms-key=projects/{project_id}/locations/asia-northeast3/keyRings/media-ring/cryptoKeys/video-key",
        "```",
        "",
        f"### 3. 대역폭 제한({limit_mb} MB/s) 적용 온프렘-to-GCS 전송 작업 생성",
        "```bash",
        f"gcloud transfer jobs create posix-to-gcs /mnt/on-prem/cctv gs://{bucket}/cctv-2026/ --source-agent-pool={pool} --project={project_id}",
        "```",
        "",
        "---",
        "",
        "## 3. 사내 거버넌스 4대 필수 표준 라벨링",
        "",
        "STS 연계 타깃 Cloud Storage 버킷, 전송 작업 및 Cloud KMS 키링 프로비저닝 시 다음 4대 표준 라벨을 반드시 적용한다:",
        "- `managed-by`: `google-cloud-0-to-1`",
        "- `scenario`: `storage-transfer-secure-uploader`",
        "- `env`: `sample` (또는 `poc`)",
        "- `created-by`: `customer-engineer`",
        "",
        "---",
        "",
        "## 4. 콘솔 링크 조치 가이드 및 공식 레퍼런스",
        "",
        f"- **Storage Transfer Service 온프레미스 콘솔**: ( https://console.cloud.google.com/transfer/on-premises?project={project_id} )",
        f"- **Cloud Storage 버킷 브라우저**: ( https://console.cloud.google.com/storage/browser/{bucket}?project={project_id} )",
        "- **공식 문서 - 온프레미스 데이터 전송 개요**: ( https://cloud.google.com/storage-transfer/docs/on-prem-overview )",
        "- **공식 문서 - 온프레미스 에이전트 풀 관리**: ( https://cloud.google.com/storage-transfer/docs/on-prem-agent-pools )",
        "- **공식 문서 - Cloud Storage 공개 접근 차단(PAP)**: ( https://cloud.google.com/storage/docs/public-access-prevention )",
        "",
        "---",
        "",
        "## 5. 자원 정리 안내 (Teardown)",
        "본 진단 도구는 전송 준비 상태를 검사하는 도구이며, 테스트용으로 생성한 전송 작업(Job)이나 에이전트 풀이 있다면 아래 명령어로 정리한다:",
        "```bash",
        f"gcloud transfer jobs delete JOB_NAME --project={project_id}",
        f"gcloud transfer agent-pools delete {pool} --project={project_id}",
        "```",
        "",
    ])
    return "\n".join(lines)


def save_markdown_report(report_md: str, output_path: str | None = None) -> None:
    """마크다운 리포트를 파일로 기록/덮어쓴다."""
    if output_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, "report.md")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"\n[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: {output_path}")
    except Exception as e:
        print(f"\n[경고] 리포트 파일 저장 실패 ({output_path}): {e}")



def run_config_mode(scenario_name: str = "") -> None:
    """사내 환경 대화형 설정 마법사: .env.example을 기반으로 사내 리소스를 대화형으로 탐색하여 .env에 저장한다."""
    import subprocess

    print("\n" + "=" * 75)
    title = f"{scenario_name} - 사내 환경 대화형 설정 마법사 (--config)" if scenario_name else "사내 환경 대화형 설정 마법사 (--config)"
    print(f"  {title}")
    print("=" * 75)

    cur_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(cur_dir, ".env")
    example_path = os.path.join(cur_dir, ".env.example")

    if not os.path.exists(example_path):
        print("[-] .env.example 템플릿 파일이 존재하지 않습니다.")
        return

    # 기존 .env 로드
    existing_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    existing_vars[k.strip()] = v.strip().strip("'\"")

    # gcloud 활성 설정 조회
    gcloud_project = ""
    try:
        res = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            val = res.stdout.strip()
            if val and val != "(unset)":
                gcloud_project = val
    except Exception:
        pass

    # .env.example 파싱 및 키/설명 수집
    new_values = {}
    with open(example_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    keys_to_prompt = []
    key_descriptions = {}
    last_comment = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            last_comment = stripped.lstrip("#").strip()
        elif stripped and "=" in line:
            key = stripped.split("=")[0].strip()
            if key:
                keys_to_prompt.append(key)
                if last_comment:
                    key_descriptions[key] = last_comment
                last_comment = ""

    is_interactive = sys.stdin.isatty()

    for idx, key in enumerate(keys_to_prompt, 1):
        default_val = existing_vars.get(key, "")
        if not default_val:
            if "PROJECT" in key:
                default_val = gcloud_project or os.environ.get("PROJECT_ID", "")
            elif key in ("REGION", "TARGET_REGION"):
                default_val = "asia-northeast3"
            elif key in ("LOCATION", "GDA_LOCATION", "KMS_LOCATION"):
                default_val = "asia-northeast3" if ("korea" in (scenario_name or "").lower() or "kms" in (scenario_name or "").lower()) else "global"

        desc = key_descriptions.get(key, "")
        if desc and is_interactive:
            print(f"\n[{idx}] {key} ({desc})")

        if is_interactive:
            prompt_str = f"  입력 [기본값: {default_val}]: " if default_val else f"  입력: "
            try:
                user_val = input(prompt_str).strip()
                final_val = user_val if user_val else default_val
            except (EOFError, KeyboardInterrupt):
                final_val = default_val
        else:
            final_val = default_val

        new_values[key] = final_val
        if is_interactive:
            print(f"  -> 설정값: {final_val or '(비워둠 - 자동 감지 유지)'}")

    # .env 파일 생성/갱신
    out_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in line:
            k = stripped.split("=")[0].strip()
            if k in new_values and new_values[k]:
                out_lines.append(f"{k}={new_values[k]}\n")
            else:
                out_lines.append(line)
        else:
            out_lines.append(line)

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(out_lines)
        print("\n" + "-" * 75)
        print("[*] 사내 환경 설정이 .env 파일에 성공적으로 저장되었습니다.")
        print("[*] 다음 명령어로 실행을 진행하십시오:")
        print("    - 가상 실행 검증: python diagnose.py --dry-run")
        print("    - 실제 진단 실행: python diagnose.py")
        print("=" * 75 + "\n")
    except Exception as e:
        print(f"[!] .env 파일 저장 중 오류 발생: {e}")


def main() -> None:
    """메인 실행 함수."""
    args = parse_args()
    if getattr(args, "config", False):
        run_config_mode("storage-transfer-secure-uploader")
        return
    project_id = "sample-project-id" if args.dry_run else detect_project_id(args.project, is_dry_run=args.dry_run)
    bucket = args.bucket
    pool = args.agent_pool
    limit_mb = args.bandwidth_limit

    mode_label = "가상 실행 (Dry-run)" if args.dry_run else "실제 환경 (Live)"
    print("=" * 85)
    print("온프레미스 대용량 미디어 STS 전송 및 보안 무결성 사전 진단 리포트")
    print(f"진단 모드: {mode_label}")
    print(f"대상 프로젝트: {project_id}")
    print(f"타깃 버킷: gs://{bucket}")
    print(f"STS 에이전트 풀: {pool}")
    print(f"설정 대역폭 제한: {limit_mb} MB/s")
    print("=" * 85)

    if args.dry_run:
        checks = get_mock_preflight_checks(bucket, pool)
    else:
        checks = inspect_live_sts(project_id, bucket, pool)

    print("\n[안전 전송 파이프라인 점검 현황]")
    print("-" * 85)
    print(f"{'단계':<20} {'점검 항목':<30} {'결과':<8} {'상세 상태'}")
    print("-" * 85)
    for c in checks:
        print(f"{c['step']:<20} {c['item']:<30} {c['status']:<8} {c['detail']}")
    print("-" * 85)

    print("\n[전송 작업(Job) 생성 및 실행 가이드]")
    print(f"1. 온프레미스 에이전트 풀 생성 및 실행 토큰 발급:")
    print(f"   gcloud transfer agent-pools create {pool} --project={project_id} --display-name='Secure On-Prem Pool'")
    print(f"2. 타깃 버킷 공개 접근 차단 및 CMEK 강제:")
    print(f"   gcloud storage buckets update gs://{bucket} --public-access-prevention")
    print(f"   gcloud storage buckets update gs://{bucket} --default-kms-key=projects/{project_id}/locations/asia-northeast3/keyRings/media-ring/cryptoKeys/video-key")
    print(f"3. 대역폭 제한({limit_mb} MB/s) 적용 온프렘-to-GCS 전송 작업 생성:")
    print(f"   gcloud transfer jobs create posix-to-gcs /mnt/on-prem/cctv gs://{bucket}/cctv-2026/ --source-agent-pool={pool} --project={project_id}")
    print("=" * 85)

    # 마크다운 리포트 자동 생성 및 덮어쓰기 (스크립트 기준 디렉터리 경로 사용)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_file_path = os.path.join(script_dir, "report.md")
    report_content = build_markdown_report(checks, project_id, bucket, pool, limit_mb, args.dry_run)
    save_markdown_report(report_content, report_file_path)


if __name__ == "__main__":
    main()
