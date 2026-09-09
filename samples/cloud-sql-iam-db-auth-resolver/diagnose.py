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

"""Cloud SQL IAM 데이터베이스 인증 및 연결 장애 진단 도구."""

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional


def parse_args() -> argparse.Namespace:
    """명령줄 인자를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="Cloud SQL IAM 데이터베이스 인증 및 연결 장애 진단기"
    )
    parser.add_argument(
        "-p",
        "--project",
        default=os.getenv("PROJECT_ID", ""),
        help="GCP 프로젝트 ID (지정하지 않을 경우 gcloud 기본 프로젝트 사용)",
    )
    parser.add_argument(
        "-i",
        "--instance",
        default=os.getenv("INSTANCE_NAME", ""),
        help="점검 대상 Cloud SQL 인스턴스 이름 (지정하지 않을 경우 프로젝트 내 전수 점검)",
    )
    parser.add_argument(
        "-u",
        "--user-email",
        default=os.getenv("DB_USER_EMAIL", ""),
        help="점검 대상 IAM 사용자 또는 서비스 계정 이메일",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 GCP API 호출 없이 모의 장애 데이터로 가상 실행",
    )
    return parser.parse_args()


def detect_project_id(cli_project: str, is_dry_run: bool = False) -> str:
    """프로젝트 ID를 탐지한다."""
    if cli_project:
        return cli_project
    if is_dry_run:
        return "demo-cloudsql-iam-project"
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
    return "demo-cloudsql-iam-project"


def get_mock_instances() -> List[Dict[str, Any]]:
    """가상 실행용 모의 Cloud SQL 인스턴스 및 IAM 계정 데이터를 반환한다."""
    return [
        {
            "name": "prod-postgres-main",
            "database_version": "POSTGRES_15",
            "region": "asia-northeast3",
            "iam_flag_enabled": False,
            "ssl_mode": "ENCRYPTED_ONLY",
            "users": [
                {
                    "name": "app-backend-sa@demo-cloudsql-iam-project.iam",
                    "type": "CLOUD_IAM_SERVICE_ACCOUNT",
                    "has_iam_role": True,
                    "status": "CRITICAL",
                    "detail": "인스턴스에 cloudsql.iam_authentication 플래그가 off 상태여서 IAM 토큰 로그인 실패",
                }
            ],
        },
        {
            "name": "order-mysql-db",
            "database_version": "MYSQL_8_0",
            "region": "asia-northeast3",
            "iam_flag_enabled": True,
            "ssl_mode": "ENCRYPTED_ONLY",
            "users": [
                {
                    "name": "order-sa@demo-cloudsql-iam-project.iam.gserviceaccount.com",
                    "type": "BUILT_IN",
                    "has_iam_role": False,
                    "status": "CRITICAL",
                    "detail": "계정 유형이 CLOUD_IAM_SERVICE_ACCOUNT 가 아닌 BUILT_IN 으로 등록되었고 roles/cloudsql.instanceUser 권한 누락",
                }
            ],
        },
        {
            "name": "billing-postgres-db",
            "database_version": "POSTGRES_14",
            "region": "asia-northeast3",
            "iam_flag_enabled": True,
            "ssl_mode": "TRUSTED_CLIENT_CERTIFICATE_REQUIRED",
            "users": [
                {
                    "name": "billing-reader-sa@demo-cloudsql-iam-project.iam",
                    "type": "CLOUD_IAM_SERVICE_ACCOUNT",
                    "has_iam_role": True,
                    "status": "WARNING",
                    "detail": "IAM 구성은 정상이나 애플리케이션 연결 풀(Connection Pool)에서 토큰 갱신 커넥터 부재 시 1시간 후 연결 끊김 발생",
                }
            ],
        },
        {
            "name": "auth-mysql-replica",
            "database_version": "MYSQL_8_0",
            "region": "asia-northeast3",
            "iam_flag_enabled": True,
            "ssl_mode": "ENCRYPTED_ONLY",
            "users": [
                {
                    "name": "auth-worker-sa",
                    "type": "CLOUD_IAM_SERVICE_ACCOUNT",
                    "has_iam_role": True,
                    "status": "OK",
                    "detail": "IAM 인증 플래그 on, CLOUD_IAM_SERVICE_ACCOUNT 유형, Cloud SQL Auth Proxy(-enable-iam-login) 연동 정상",
                }
            ],
        },
    ]


def run_gcloud_json(cmd: List[str]) -> Optional[Any]:
    """gcloud 명령어를 실행하고 JSON 결과를 반환한다."""
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except Exception:
        return None


def inspect_cloud_sql(project_id: str, target_instance: str, target_user: str) -> List[Dict[str, Any]]:
    """실제 GCP 환경의 Cloud SQL 인스턴스 및 IAM 사용자 구성을 점검한다."""
    cmd = ["gcloud", "sql", "instances", "list", f"--project={project_id}", "--format=json"]
    raw_instances = run_gcloud_json(cmd)
    if not raw_instances:
        return []

    # 프로젝트 IAM 정책 조회 (roles/cloudsql.instanceUser 바인딩 확인)
    iam_policy = run_gcloud_json(["gcloud", "projects", "get-iam-policy", project_id, "--format=json"])
    instance_users_set = set()
    if iam_policy:
        for binding in iam_policy.get("bindings", []):
            if binding.get("role") in ("roles/cloudsql.instanceUser", "roles/cloudsql.admin", "roles/editor", "roles/owner"):
                for member in binding.get("members", []):
                    instance_users_set.add(member)

    results = []
    for inst in raw_instances:
        inst_name = inst.get("name", "")
        if target_instance and inst_name != target_instance:
            continue

        db_version = inst.get("databaseVersion", "")
        region = inst.get("region", "")
        settings = inst.get("settings", {})
        db_flags = settings.get("databaseFlags", [])
        ssl_mode = settings.get("ipConfiguration", {}).get("sslMode", "ENCRYPTED_ONLY")

        iam_flag_enabled = False
        for flag in db_flags:
            if flag.get("name") == "cloudsql.iam_authentication" and flag.get("value") == "on":
                iam_flag_enabled = True
                break

        # DB 사용자 목록 조회
        users_raw = run_gcloud_json([
            "gcloud", "sql", "users", "list", f"--instance={inst_name}", f"--project={project_id}", "--format=json"
        ])
        user_list = []
        if users_raw:
            for u in users_raw:
                u_name = u.get("name", "")
                u_type = u.get("type", "BUILT_IN")
                if target_user and target_user not in u_name:
                    continue

                member_sa = f"serviceAccount:{u_name}"
                member_user = f"user:{u_name}"
                has_iam_role = (member_sa in instance_users_set or member_user in instance_users_set)

                status = "OK"
                detail = "IAM 인증 구성 정상"

                if not iam_flag_enabled:
                    status = "CRITICAL"
                    detail = "인스턴스에 cloudsql.iam_authentication 플래그가 on으로 설정되지 않음"
                elif u_type not in ("CLOUD_IAM_SERVICE_ACCOUNT", "CLOUD_IAM_USER"):
                    status = "CRITICAL"
                    detail = f"계정 유형이 {u_type} 임. IAM 인증을 위해서는 CLOUD_IAM_SERVICE_ACCOUNT/USER 유형이어야 함"
                elif not has_iam_role:
                    status = "CRITICAL"
                    detail = "GCP IAM roles/cloudsql.instanceUser 권한 미부여로 DB 로그인 거부됨"

                user_list.append({
                    "name": u_name,
                    "type": u_type,
                    "has_iam_role": has_iam_role,
                    "status": status,
                    "detail": detail,
                })

        results.append({
            "name": inst_name,
            "database_version": db_version,
            "region": region,
            "iam_flag_enabled": iam_flag_enabled,
            "ssl_mode": ssl_mode,
            "users": user_list,
        })
    return results


def print_report(project_id: str, is_dry_run: bool, instances: List[Dict[str, Any]]) -> None:
    """진단 리포트를 출력한다."""
    print("=" * 80)
    print("Cloud SQL IAM 데이터베이스 인증 및 연결 장애 진단 리포트")
    print(f"진단 모드: {'가상 실행 (Dry-run)' if is_dry_run else '실제 환경 점검'}")
    print(f"대상 프로젝트: {project_id}")
    print(f"점검 대상 인스턴스 수: {len(instances)}개")
    print("=" * 80)
    print()

    print("[1단계] Cloud SQL 인스턴스별 IAM 인증 플래그 활성화 현황")
    print("-" * 80)
    print(f"{'인스턴스 이름':<24} {'엔진 버전':<16} {'리전':<18} {'IAM 인증 플래그':<14}")
    print("-" * 80)
    for inst in instances:
        flag_status = "ON (활성)" if inst["iam_flag_enabled"] else "OFF (비활성, 오류)"
        print(f"{inst['name']:<24} {inst['database_version']:<16} {inst['region']:<18} {flag_status:<14}")
    print("-" * 80)
    print()

    print("[2단계] 등록된 DB 계정 유형 및 GCP IAM 역할 바인딩 정밀 진단")
    print("-" * 80)
    for inst in instances:
        print(f"- 인스턴스: {inst['name']} ({inst['database_version']})")
        print(f"  * IAM 플래그 상태: {'ON' if inst['iam_flag_enabled'] else 'OFF (조치 필요)'}")
        print(f"  * SSL/TLS 모드: {inst['ssl_mode']}")
        if not inst["users"]:
            print("  * 등록된 IAM DB 사용자가 존재하지 않음 (고정 비밀번호 전용 계정만 존재)")
        for u in inst["users"]:
            print(f"  * 사용자: {u['name']}")
            print(f"    - 등록 유형: {u['type']}")
            print(f"    - IAM 역할(roles/cloudsql.instanceUser): {'부여됨 (OK)' if u['has_iam_role'] else '누락됨 (거부)'}")
            print(f"    - 진단 결과: [{u['status']}] {u['detail']}")
        print()
    print("-" * 80)
    print()

    print("[3단계] IAM 데이터베이스 인증 표준 처방 및 즉각 조치 가이드")
    print("1. Cloud SQL 인스턴스 IAM 인증 플래그 활성화:")
    print("   gcloud sql instances patch <INSTANCE_NAME> \\")
    print("     --database-flags=cloudsql.iam_authentication=on")
    print()
    print("2. IAM 서비스 계정 DB 사용자 추가:")
    print("   # PostgreSQL 환경 (도메인 제외한 SA 이메일 접두사 사용):")
    print("   gcloud sql users create <SA_NAME>@<PROJECT_ID>.iam \\")
    print("     --instance=<INSTANCE_NAME> \\")
    print("     --type=CLOUD_IAM_SERVICE_ACCOUNT")
    print()
    print("   # MySQL 환경 (앞 32자 제한, .gserviceaccount.com 제외):")
    print("   gcloud sql users create <TRUNCATED_SA_NAME> \\")
    print("     --instance=<INSTANCE_NAME> \\")
    print("     --type=CLOUD_IAM_SERVICE_ACCOUNT")
    print()
    print("3. 호출자(SA 또는 개발자)에게 필수 IAM 역할 부여:")
    print("   gcloud projects add-iam-policy-binding <PROJECT_ID> \\")
    print("     --member=\"serviceAccount:<SA_EMAIL>\" \\")
    print("     --role=\"roles/cloudsql.instanceUser\"")
    print()
    print("4. 토큰 만료(1시간) 방지를 위한 Cloud SQL Auth Proxy 실행:")
    print("   ./cloud-sql-proxy <PROJECT_ID>:<REGION>:<INSTANCE_NAME> --enable-iam-login --port=5432")
    print("=" * 80)


def main() -> None:
    """메인 실행 함수."""
    args = parse_args()
    project_id = detect_project_id(args.project, args.dry_run)

    if args.dry_run:
        instances = get_mock_instances()
        if args.instance:
            instances = [i for i in instances if i["name"] == args.instance]
    else:
        instances = inspect_cloud_sql(project_id, args.instance, args.user_email)
        if not instances:
            print(f"프로젝트 [{project_id}]에서 점검 대상 Cloud SQL 인스턴스를 찾지 못했다.")
            sys.exit(0)

    print_report(project_id, args.dry_run, instances)


if __name__ == "__main__":
    main()
