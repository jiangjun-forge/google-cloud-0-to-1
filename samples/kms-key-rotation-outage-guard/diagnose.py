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

"""Cloud KMS CMEK 키 순환 및 구버전 비활성화 장애 예방 도구."""

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional


def parse_args() -> argparse.Namespace:
    """명령줄 인자를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="Cloud KMS CMEK 키 순환 및 구버전 비활성화 장애 예방기"
    )
    parser.add_argument(
        "-p",
        "--project",
        default=os.getenv("PROJECT_ID", ""),
        help="GCP 프로젝트 ID (지정하지 않을 경우 gcloud 기본 프로젝트 사용)",
    )
    parser.add_argument(
        "-l",
        "--location",
        default=os.getenv("KMS_LOCATION") or "asia-northeast3",
        help="Cloud KMS 리전 위치 (기본값: asia-northeast3)",
    )
    parser.add_argument(
        "-k",
        "--keyring",
        default=os.getenv("KEY_RING") or "prod-keyring",
        help="Cloud KMS 키 링 이름 (기본값: prod-keyring)",
    )
    parser.add_argument(
        "-n",
        "--key-name",
        default=os.getenv("KEY_NAME") or "customer-data-key",
        help="Cloud KMS 암호화 키 이름 (기본값: customer-data-key)",
    )
    parser.add_argument(
        "-b",
        "--bucket",
        default=os.getenv("BUCKET_NAME") or "",
        help="점검 대상 Cloud Storage 버킷 이름 (지정하지 않을 경우 KMS 연동 버킷 자동 탐색)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 GCP API 호출 없이 모의 CMEK 키 및 버킷 데이터로 가상 실행",
    )
    return parser.parse_args()


def detect_project_id(cli_project: str, is_dry_run: bool = False) -> str:
    """프로젝트 ID를 탐지한다."""
    if cli_project:
        return cli_project
    if is_dry_run:
        return "demo-kms-project"
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
    return "demo-kms-project"


def get_mock_kms_data() -> Dict[str, Any]:
    """가상 실행용 모의 Cloud KMS 및 Cloud Storage 객체 버전 데이터를 반환한다."""
    return {
        "key_path": "projects/demo-kms-project/locations/asia-northeast3/keyRings/prod-keyring/cryptoKeys/customer-data-key",
        "primary_version": "3",
        "rotation_period": "90일 (7,776,000초)",
        "versions": [
            {
                "version": "3",
                "state": "ENABLED",
                "is_primary": True,
                "create_time": "2026-06-01T09:00:00Z",
                "status": "OK",
                "detail": "현재 활성 주 버전 (신규 암호화 수행)",
            },
            {
                "version": "2",
                "state": "ENABLED",
                "is_primary": False,
                "create_time": "2026-03-01T09:00:00Z",
                "status": "WARNING",
                "detail": "이전 버전 키 (활성 상태 유지 중, 480개 객체가 여전히 복호화에 참조)",
            },
            {
                "version": "1",
                "state": "DESTROY_SCHEDULED",
                "is_primary": False,
                "create_time": "2025-12-01T09:00:00Z",
                "status": "CRITICAL",
                "detail": "파기 예정(DESTROY_SCHEDULED) 상태이나 150개 객체가 여전히 이 키로 암호화되어 있어 파기 시 영구 복호화 불가",
            },
        ],
        "storage_bucket": "demo-kms-customer-archive",
        "total_objects": 1250,
        "object_distribution": [
            {"version": "3", "count": 620, "percentage": 49.6, "risk": "NONE"},
            {"version": "2", "count": 480, "percentage": 38.4, "risk": "MEDIUM"},
            {"version": "1", "count": 150, "percentage": 12.0, "risk": "CRITICAL"},
        ],
    }


def run_gcloud_json(cmd: List[str]) -> Optional[Any]:
    """gcloud 명령어를 실행하고 JSON 결과를 반환한다."""
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except Exception:
        return None


def inspect_kms(project_id: str, location: str, keyring: str, key_name: str, bucket_name: str) -> Dict[str, Any]:
    """실제 GCP 환경의 Cloud KMS 키 버전 및 Cloud Storage 객체 CMEK 분포를 점검한다."""
    key_cmd = [
        "gcloud", "kms", "keys", "describe", key_name,
        f"--keyring={keyring}", f"--location={location}", f"--project={project_id}", "--format=json"
    ]
    key_info = run_gcloud_json(key_cmd)
    if not key_info:
        return {}

    primary = key_info.get("primary", {})
    primary_version = primary.get("name", "").split("/")[-1]
    rot_period = key_info.get("rotationPeriod", "자동 순환 미설정")

    versions_cmd = [
        "gcloud", "kms", "keys", "versions", "list",
        f"--key={key_name}", f"--keyring={keyring}", f"--location={location}", f"--project={project_id}", "--format=json"
    ]
    raw_versions = run_gcloud_json(versions_cmd) or []

    version_list = []
    for v in raw_versions:
        v_num = v.get("name", "").split("/")[-1]
        state = v.get("state", "")
        is_pri = (v_num == primary_version)
        create_time = v.get("createTime", "")

        status = "OK"
        detail = "정상"
        if is_pri:
            detail = "현재 활성 주 버전 (신규 암호화 수행)"
        elif state in ("DISABLED", "DESTROY_SCHEDULED"):
            status = "CRITICAL"
            detail = f"구버전 키가 {state} 상태임. 기존 암호화 데이터 존재 시 복호화 실패"
        else:
            status = "WARNING"
            detail = "구버전 활성 키 (기존 데이터 복호화용으로 유지 필요)"

        version_list.append({
            "version": v_num,
            "state": state,
            "is_primary": is_pri,
            "create_time": create_time,
            "status": status,
            "detail": detail,
        })

    # 버킷 객체 점검
    total_objects = 0
    distribution = []
    if bucket_name:
        objs_cmd = [
            "gcloud", "storage", "objects", "list",
            f"gs://{bucket_name}", f"--project={project_id}", "--format=json"
        ]
        raw_objs = run_gcloud_json(objs_cmd) or []
        total_objects = len(raw_objs)
        v_counts: Dict[str, int] = {}
        for obj in raw_objs:
            kms_key = obj.get("kmsKeyName", "")
            if kms_key:
                v_used = kms_key.split("/")[-1]
                v_counts[v_used] = v_counts.get(v_used, 0) + 1
            else:
                v_counts["GOOGLE_MANAGED"] = v_counts.get("GOOGLE_MANAGED", 0) + 1

        for v_k, count in v_counts.items():
            pct = round((count / total_objects) * 100, 1) if total_objects > 0 else 0
            risk = "NONE" if v_k == primary_version else ("CRITICAL" if v_k in [v["version"] for v in version_list if v["state"] in ("DISABLED", "DESTROY_SCHEDULED")] else "MEDIUM")
            distribution.append({
                "version": v_k,
                "count": count,
                "percentage": pct,
                "risk": risk,
            })

    return {
        "key_path": key_info.get("name", ""),
        "primary_version": primary_version,
        "rotation_period": rot_period,
        "versions": version_list,
        "storage_bucket": bucket_name,
        "total_objects": total_objects,
        "object_distribution": distribution,
    }


def print_report(project_id: str, is_dry_run: bool, data: Dict[str, Any]) -> None:
    """진단 리포트를 출력한다."""
    print("=" * 80)
    print("Cloud KMS CMEK 키 순환 및 구버전 비활성화 장애 예방 리포트")
    print(f"진단 모드: {'가상 실행 (Dry-run)' if is_dry_run else '실제 환경 점검'}")
    print(f"대상 프로젝트: {project_id}")
    print(f"암호화 키 경로: {data.get('key_path', '')}")
    print(f"현재 주 버전(Primary): 버전 {data.get('primary_version', '')}")
    print(f"자동 순환 주기: {data.get('rotation_period', '')}")
    print("=" * 80)
    print()

    print("[1단계] Cloud KMS CryptoKey 버전별 라이프사이클 상태 점검")
    print("-" * 80)
    print(f"{'버전':<8} {'기본 키':<10} {'상태':<20} {'생성 일자':<22} {'위험 등급':<10}")
    print("-" * 80)
    for v in data.get("versions", []):
        pri_str = "YES (Primary)" if v["is_primary"] else "NO"
        print(f"v{v['version']:<7} {pri_str:<10} {v['state']:<20} {v['create_time']:<22} {v['status']:<10}")
    print("-" * 80)
    print()

    print("[2단계] Cloud Storage 버킷 내 구버전 키 종속성 및 객체 분포 분석")
    print("-" * 80)
    print(f"대상 버킷: gs://{data.get('storage_bucket', '미지정')}")
    print(f"점검 객체 총합: {data.get('total_objects', 0):,}개")
    print()
    print(f"{'암호화 버전':<16} {'객체 수':<12} {'비율':<10} {'위험도':<10}")
    print("-" * 80)
    for item in data.get("object_distribution", []):
        print(f"버전 {item['version']:<12} {item['count']:<12} {item['percentage']}%      {item['risk']:<10}")
    print("-" * 80)
    print()

    print("[3단계] 서비스 장애 방지 긴급 처방 및 데이터 재암호화 가이드")
    print("1. [긴급] 파기 예정 또는 비활성화된 구버전 키 즉각 복구 (장애 방어):")
    print("   gcloud kms keys versions restore 1 \\")
    print(f"     --key={os.getenv('KEY_NAME', 'customer-data-key')} \\")
    print(f"     --keyring={os.getenv('KEY_RING', 'prod-keyring')} \\")
    print(f"     --location={os.getenv('KMS_LOCATION', 'asia-northeast3')}")
    print()
    print("2. [필수] 구버전 키로 암호화된 객체를 최신 주 버전(Primary)으로 일괄 재암호화(Rewrite):")
    print(f"   # 최신 주 키(v{data.get('primary_version', '3')})로 객체 메타데이터 및 암호화 블록 갱신:")
    print(f"   gcloud storage objects rewrite gs://{data.get('storage_bucket', 'BUCKET_NAME')}/**")
    print()
    print("3. [검증] 모든 객체가 최신 주 버전 키로 마이그레이션 완료된 후에만 구버전 비활성화(Disable):")
    print("   gcloud kms keys versions disable 1 \\")
    print(f"     --key={os.getenv('KEY_NAME', 'customer-data-key')} \\")
    print(f"     --keyring={os.getenv('KEY_RING', 'prod-keyring')} \\")
    print(f"     --location={os.getenv('KMS_LOCATION', 'asia-northeast3')}")
    print("=" * 80)


def main() -> None:
    """메인 실행 함수."""
    args = parse_args()
    project_id = detect_project_id(args.project, args.dry_run)

    if args.dry_run:
        data = get_mock_kms_data()
    else:
        data = inspect_kms(project_id, args.location, args.keyring, args.key_name, args.bucket)
        if not data:
            print(f"프로젝트 [{project_id}]에서 지정된 Cloud KMS 키 [{args.key_name}]를 찾지 못했다.")
            sys.exit(0)

    print_report(project_id, args.dry_run, data)


if __name__ == "__main__":
    main()
