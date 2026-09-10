#!/usr/bin/env python3
# Copyright 2026 Google LLC
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
    return parser.parse_args()


def detect_project_id(cli_project: str) -> str:
    """프로젝트 ID를 탐지한다."""
    if cli_project:
        return cli_project
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
    return "demo-secure-multimodal-transfer"


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
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
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


def main() -> None:
    """메인 실행 함수."""
    args = parse_args()
    project_id = detect_project_id(args.project)
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


if __name__ == "__main__":
    main()
