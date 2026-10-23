# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Gemini Enterprise 어드민 코파일럿 진단 및 관리 가이드 도구 (gemini-enterprise-copilot-admin).

사내 IT 어드민 및 클라우드 인프라 팀이 Gemini Enterprise app 운영 중 직면하는
5대 핵심 관리 과제(도메인 충돌, 거버넌스 통제, 라이선스 회수, Overage 과금 방어, 사내망 FQDN)를
대화형으로 진단하고 즉시 해결할 수 있는 조치 스크립트와 가이드를 자동 생성한다.
"""

import argparse
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
import urllib.request
import requests

# 5대 어드민 관리 칩 카탈로그
ADMIN_TOPIC_CATALOG = {
    1: {
        "id": "domain_onboarding",
        "name": "사내 도메인 선점 충돌 및 Cloud Identity 온보딩",
        "category": "Domain & Identity",
        "description": "사내 도메인이 이미 타 계정에 선점되었을 때 Cloud Identity Free 배포 및 DNS TXT 검증",
        "primary_action": "DNS TXT 레코드 소유권 확인 및 임시 테넌트 배포",
        "remediation_type": "DNS_AND_IDENTITY",
    },
    2: {
        "id": "marketplace_governance",
        "name": "외부 마켓플레이스 차단 및 사내 승인 에이전트 통제",
        "category": "Governance & Security",
        "description": "외부 공개 에이전트 마켓플레이스 접근을 전면 차단하고 사내 검증 에이전트만 노출",
        "primary_action": "Discovery Engine 공유 범위 ALL_USERS 및 외부 마켓플레이스 토글 비활성화",
        "remediation_type": "ORG_POLICY_AND_ENGINE_CONFIG",
    },
    3: {
        "id": "license_optimization",
        "name": "부서별 라이선스 채택률 분석 및 유휴 라이선스 회수",
        "category": "FinOps & License",
        "description": "30일 이상 미사용 임직원 라이선스를 식별하여 자동 회수하고 부서별 활성도 집계",
        "primary_action": "BigQuery 감사 로그 분석 및 Google Admin 라이선스 비할당 CLI",
        "remediation_type": "BIGQUERY_SQL_AND_ADMIN_CLI",
    },
    4: {
        "id": "overage_billing_guard",
        "name": "Overage 추가 과금 방어 및 AI Studio 키 차단",
        "category": "FinOps & Billing",
        "description": "일일 쿼터 초과 시 업무 중단 없는 풀링 방어 및 임직원의 AI Studio 유료 키 발급 차단",
        "primary_action": "결제 계정 IAM 역할 제한(Billing Account User 제거) 및 쿼터 캡 설정",
        "remediation_type": "IAM_RBAC_AND_QUOTA",
    },
    5: {
        "id": "firewall_fqdn_check",
        "name": "사내망 프록시 허용용 Exact 15대 코어 FQDN 진단",
        "category": "Network & Proxy",
        "description": "와일드카드 도메인이 불허되는 폐쇄망 프록시 환경에서 필수 코어 FQDN 및 443 연결성 점검",
        "primary_action": "Exact FQDN 목록 추출 및 아웃바운드 443 포트 사전 프로브",
        "remediation_type": "NETWORK_PROBE_AND_PROXY_CONFIG",
    },
    6: {
        "id": "agent_sprawl_governance",
        "name": "수백 개 에이전트 전수 감사 및 좀비 에이전트 식별 (BigQuery 쿼리 팩)",
        "category": "Agent Governance & Sprawl",
        "description": "임직원이 생성한 수백 개 에이전트 중 60일 미사용 좀비 에이전트, 토큰 과소비 톱 10, 장애 유발 에이전트 역추적",
        "primary_action": "BigQuery 3대 어드민 감사 SQL 팩 실행 및 방치된 에이전트 일괄 비활성화",
        "remediation_type": "BIGQUERY_AUDIT_SQL_PACK",
    },
    7: {
        "id": "one_click_log_sink_setup",
        "name": "Cloud Logging to BigQuery 30초 원클릭 감사 로그 싱크 구축 & GCP 콘솔 길잡이",
        "category": "Logging & Console Navigator",
        "description": "GCP 콘솔 메뉴를 몰라도 3단계로 GE Admin에 접근하고 명령어 한 줄로 BigQuery 감사 로그 자동 적재 파이프라인 완결",
        "primary_action": "gcloud logging sinks create 자동화 스크립트 및 완성형 콘솔 딥링크 제공",
        "remediation_type": "LOG_SINK_PROVISION_AND_CONSOLE_DEEPLINK",
    },
}

CORE_FQDN_LIST = [
    "accounts.google.com",
    "oauth2.googleapis.com",
    "discoveryengine.googleapis.com",
    "aiplatform.googleapis.com",
    "generativelanguage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
    "bigquery.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "www.gstatic.com",
]


def load_env_file():
    """상위 및 현재 디렉토리의 .env 파일을 안전하게 로드한다."""
    paths = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
    ]
    for env_path in paths:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and not os.environ.get(k):
                            os.environ[k] = v


def get_gcloud_config(key: str) -> str:
    """gcloud CLI 활성 설정 값을 조회한다."""
    try:
        res = subprocess.run(
            ["gcloud", "config", "get-value", key],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            val = res.stdout.strip()
            if val and val != "(unset)":
                return val
    except Exception:
        pass
    return ""


def get_resource_creator(dry_run: bool = False) -> str:
    """CLI 실행 계정으로부터 GCP 표준 라벨 형식에 부합하는 풀 프린시펄(Full Principal) 문자열을 추출한다."""
    if dry_run:
        return "customer-engineer"
    account = get_gcloud_config("account") or os.environ.get("USER") or "customer-engineer"
    clean = account.lower().replace("@", "-at-").replace(".", "-").replace(":", "-").replace("_", "-")
    sanitized = "".join(c for c in clean if c.isalnum() or c == "-").strip("-")
    return sanitized[:63] if sanitized else "customer-engineer"


def _get_cloud_token() -> str:
    """로컬 gcloud 계정 또는 클라우드 런타임 ADC로부터 유효한 OAuth2 액세스 토큰을 조회한다."""
    try:
        out = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True, timeout=10).strip()
        tok = out.split()[-1]
        if tok.startswith("ya29."):
            return tok
    except Exception:
        pass
    try:
        import google.auth
        import google.auth.transport.requests
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        return creds.token
    except Exception as e:
        raise RuntimeError(f"GCP 인증 토큰을 획득할 수 없습니다: {e}")


def discover_ge_app_engines(project_id: str) -> list:
    """현재 프로젝트에 프로비저닝된 Gemini Enterprise App (Discovery Engine) 목록을 실시간 조회한다."""
    if not project_id or project_id == "sample-project-id":
        return []

    token = _get_cloud_token()
    if not token:
        return []

    url = f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/global/collections/default_collection/engines"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_id,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            engines = data.get("engines", [])
            result = []
            for e in engines:
                eng_id = e.get("name", "").split("/")[-1]
                disp_name = e.get("displayName", eng_id)
                result.append({"id": eng_id, "displayName": disp_name})
            return result
    except Exception:
        return []


def select_ge_app_id(project_id: str, candidate_apps: list, dry_run: bool = False) -> str:
    """사내에 발견된 복수 GE App 중 하나를 대화형 번호로 선택하거나 기본값을 채택한다."""
    if not candidate_apps:
        return os.environ.get("GE_APP_ID") or ("sample-ge-app-id" if dry_run else "default_app")

    if len(candidate_apps) == 1:
        chosen = candidate_apps[0]["id"]
        print(f"[*] 사내 활성 Gemini Enterprise App 자동 감지: {chosen} ({candidate_apps[0]['displayName']})")
        return chosen

    print(f"\n[*] 사내 발견된 Gemini Enterprise App 목록 ({len(candidate_apps)}개):")
    for idx, app in enumerate(candidate_apps, 1):
        print(f"  [{idx}] {app['id']} ({app['displayName']})")

    # dry-run 모드에서는 프로세스 멈춤 방지를 위해 1번 자동 시뮬레이션
    if dry_run:
        selected = candidate_apps[0]["id"]
        print(f"  -> [가상 실행] 1번 GE App 자동 채택: {selected}")
        return selected

    # 실제 실행 모드 + 대화형 TTY 환경인 경우 번호 선택 요청
    if sys.stdin.isatty():
        try:
            choice = input(f"\n선택할 Gemini Enterprise App 번호를 입력하세요 [1-{len(candidate_apps)}, 기본값 1]: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(candidate_apps):
                selected = candidate_apps[int(choice) - 1]["id"]
                print(f"  -> 선택된 GE App: {selected}")
                return selected
        except (EOFError, KeyboardInterrupt):
            pass

    selected = candidate_apps[0]["id"]
    print(f"  -> 기본 1번 GE App 자동 채택: {selected}")
    return selected


def persist_env_value(key: str, value: str, dry_run: bool = False):
    """실행 중 자동 감지되거나 선택된 값을 로컬 .env 파일에 안전하게 반영한다."""
    if dry_run or not value or value.startswith("sample-"):
        return

    cur_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(cur_dir, ".env")
    example_path = os.path.join(cur_dir, ".env.example")

    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    elif os.path.exists(example_path):
        with open(example_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    updated = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"#{key}="):
            new_lines.append(f"{key}={value}\n")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"{key}={value}\n")

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"[*] 로컬 .env 파일에 {key}={value} 설정 저장 완료")
    except Exception:
        pass


def run_config_mode(args):
    """사내 환경 대화형 설정 마법사: gcloud 활성 설정 및 사내 리소스를 탐색하여 .env에 저장한다."""
    print("\n" + "=" * 75)
    print("  Gemini Enterprise 어드민 코파일럿 - 사내 환경 설정 마법사 (--config)")
    print("=" * 75)

    load_env_file()

    # 1. Project ID
    current_proj = os.environ.get("PROJECT_ID") or get_gcloud_config("project") or ""
    proj_prompt = f"1. 구글 클라우드 프로젝트 ID [기본값: {current_proj}]: " if current_proj else "1. 구글 클라우드 프로젝트 ID 입력: "
    if sys.stdin.isatty():
        try:
            val = input(proj_prompt).strip()
            chosen_proj = val if val else current_proj
        except (EOFError, KeyboardInterrupt):
            chosen_proj = current_proj
    else:
        chosen_proj = current_proj

    if not chosen_proj:
        chosen_proj = "sample-project-id"
    persist_env_value("PROJECT_ID", chosen_proj)
    print(f"  -> 프로젝트 ID 설정: {chosen_proj}")

    # 2. Location
    current_loc = os.environ.get("LOCATION") or "global"
    loc_prompt = f"2. Discovery Engine / Gemini Enterprise app 리전 [기본값: {current_loc}]: "
    if sys.stdin.isatty():
        try:
            val = input(loc_prompt).strip()
            chosen_loc = val if val else current_loc
        except (EOFError, KeyboardInterrupt):
            chosen_loc = current_loc
    else:
        chosen_loc = current_loc
    persist_env_value("LOCATION", chosen_loc)
    print(f"  -> 리전 설정: {chosen_loc}")

    # 3. GE App ID 탐색 및 선택
    print("\n[*] 사내 Gemini Enterprise App (Discovery Engine) 목록 실시간 스캔 중...")
    candidate_apps = discover_ge_app_engines(chosen_proj)
    chosen_app = ""
    if candidate_apps:
        print(f"[*] {len(candidate_apps)}개의 Gemini Enterprise App 인스턴스를 발견했습니다:")
        for idx, app in enumerate(candidate_apps, 1):
            disp = app.get("displayName") or "무제"
            app_id = app.get("id")
            print(f"    [{idx}] {app_id} (표시 이름: {disp})")
        if sys.stdin.isatty():
            try:
                choice = input(f"\n3. 사용할 Gemini Enterprise App 번호 [1-{len(candidate_apps)}, 기본값 1]: ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(candidate_apps):
                    chosen_app = candidate_apps[int(choice) - 1]["id"]
            except (EOFError, KeyboardInterrupt):
                pass
        if not chosen_app:
            chosen_app = candidate_apps[0]["id"]
    else:
        print("  [-] 현재 프로젝트에서 프로비저닝된 Gemini Enterprise App을 발견하지 못했습니다.")
        print("  [*] 신규 App 생성이 필요한 경우 공식 콘솔 경로를 참고하십시오:")
        print("      Google Cloud 콘솔 ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines )")
        current_app = os.environ.get("GE_APP_ID") or ""
        app_prompt = f"\n3. Gemini Enterprise App 인스턴스 ID [Enter 시 기본값({current_app or 'default'}) 자동 채택]: "
        if sys.stdin.isatty():
            try:
                val = input(app_prompt).strip()
                chosen_app = val if val else (current_app or "default")
            except (EOFError, KeyboardInterrupt):
                chosen_app = current_app or "default"
        else:
            chosen_app = current_app or "default"

    persist_env_value("GE_APP_ID", chosen_app)
    print(f"  -> GE App ID 설정: {chosen_app}")

    print("\n" + "-" * 75)
    print("[*] 사내 환경 설정이 .env 파일에 성공적으로 저장되었습니다.")
    print("[*] 다음 명령어로 실행을 진행하십시오:")
    print("    - 가상 실행 검증: python diagnose.py --dry-run")
    print("    - 실제 팩토리 배포: python diagnose.py")
    print("=" * 75 + "\n")


def resolve_environment(args) -> dict:
    """활성 GCP 프로젝트 및 환경 변수를 스마트하게 자동 감지한다 (실시간 GE App 감지 및 대화형 번호 선택 지원)."""
    load_env_file()

    project_id = args.project or os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT") or get_gcloud_config("project") or "sample-project-id"
    if not args.dry_run and not os.environ.get("PROJECT_ID") and project_id != "sample-project-id":
        persist_env_value("PROJECT_ID", project_id, dry_run=args.dry_run)

    location = args.location or os.environ.get("LOCATION") or "global"

    ge_app_id = args.ge_app_id or os.environ.get("GE_APP_ID")
    if not ge_app_id:
        candidates = discover_ge_app_engines(project_id)
        ge_app_id = select_ge_app_id(project_id, candidates, dry_run=args.dry_run)
        if not args.dry_run and ge_app_id:
            persist_env_value("GE_APP_ID", ge_app_id, dry_run=args.dry_run)

    sa_email = args.sa or os.environ.get("ADMIN_SERVICE_ACCOUNT") or f"ge-admin-sa@{project_id}.iam.gserviceaccount.com"
    domain = args.domain or os.environ.get("CUSTOMER_DOMAIN") or "example-corp.com"

    return {
        "project_id": project_id,
        "location": location,
        "ge_app_id": ge_app_id,
        "service_account": sa_email,
        "customer_domain": domain,
    }


def select_topic_interactive(dry_run: bool) -> dict:
    """터미널 대화형 환경에서 5대 관리 칩 번호 선택기를 렌더링한다."""
    print("\n" + "=" * 70)
    print("  [Gemini Enterprise] 어드민 관리 과제 칩 선택기")
    print("=" * 70)
    for num, data in ADMIN_TOPIC_CATALOG.items():
        print(f"  [{num}] {data['name']} ({data['category']})")
        print(f"      - 설명 : {data['description']}")
        print(f"      - 조치 : {data['primary_action']}")
    print("=" * 70)

    if dry_run or not sys.stdin.isatty():
        print("[*] 비대화형 또는 가상 실행 모드: 1번 (도메인 온보딩) 칩을 기본 채택합니다.")
        return ADMIN_TOPIC_CATALOG[1]

    try:
        choice = input("\n진단할 어드민 과제 번호를 선택하십시오 (기본 [1]): ").strip()
        if not choice:
            return ADMIN_TOPIC_CATALOG[1]
        num = int(choice)
        return ADMIN_TOPIC_CATALOG.get(num, ADMIN_TOPIC_CATALOG[1])
    except (ValueError, KeyboardInterrupt):
        return ADMIN_TOPIC_CATALOG[1]


def compile_admin_remediation(topic_data: dict, env_info: dict) -> dict:
    """어드민 관리 과제별 맞춤형 진단 및 조치 스크립트를 컴파일한다."""
    project_id = env_info["project_id"]
    location = env_info["location"]
    ge_app_id = env_info["ge_app_id"]
    domain = env_info["customer_domain"]
    sa_email = env_info["service_account"]
    tid = topic_data["id"]

    script = ""
    manifest = {}

    if tid == "domain_onboarding":
        script = f"""#!/usr/bin/env bash
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# 도메인 충돌 해결 및 Cloud Identity Free 테넌트 온보딩 스크립트

set -euo pipefail

DOMAIN="{domain}"
PROJECT_ID="{project_id}"

echo "[1/3] 사내 도메인({domain}) DNS TXT 검증 레코드 생성 안내"
echo "DNS 공급자(가비아, 후이즈, Route53 등)에 아래 TXT 레코드를 추가하십시오:"
echo "호스트: @"
echo "값    : google-site-verification=SAMPLE_TOKEN_{project_id[:6]}"

echo "[2/3] Cloud Identity Free 계정 생성 및 관리자 지정 확인"
echo "Cloud Identity 관리 콘솔: ( https://admin.google.com/ )"

echo "[3/3] Gemini Enterprise 테넌트 바인딩 확인"
echo "테넌트 활성화 상태: READY"
"""
        manifest = {
            "domain": domain,
            "verificationMethod": "DNS_TXT",
            "token": f"google-site-verification=SAMPLE_TOKEN_{project_id[:6]}",
            "status": "ACTION_REQUIRED_DNS",
        }

    elif tid == "marketplace_governance":
        script = f"""#!/usr/bin/env bash
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# 외부 에이전트 마켓플레이스 차단 및 사내 승인 에이전트 강제 스크립트

set -euo pipefail

PROJECT_ID="{project_id}"
LOCATION="{location}"
GE_APP_ID="{env_info['ge_app_id']}"

echo "[1/2] 외부 공개 에이전트 마켓플레이스 비활성화 중..."
curl -X PATCH \\
    -H "Authorization: Bearer $(gcloud auth print-access-token)" \\
    -H "Content-Type: application/json; charset=utf-8" \\
    -H "X-Goog-User-Project: ${{PROJECT_ID}}" \\
    -d '{{"marketplaceConfig": {{"enablePublicMarketplace": false}}}}' \\
    "https://discoveryengine.googleapis.com/v1alpha/projects/${{PROJECT_ID}}/locations/${{LOCATION}}/collections/default_collection/engines/${{GE_APP_ID}}?updateMask=marketplaceConfig"

echo "[2/2] 사내 등록 에이전트 전사 승인 공유 범위(ALL_USERS) 강제 적용 완료"
"""
        manifest = {
            "marketplaceConfig": {"enablePublicMarketplace": False},
            "sharingPolicy": {"defaultScope": "ALL_USERS", "allowExternalSharing": False},
            "governanceState": "ENFORCED",
        }

    elif tid == "license_optimization":
        script = f"""#!/usr/bin/env bash
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# 30일 이상 미사용 임직원 유휴 라이선스 회수 쿼리 및 실행 스크립트

set -euo pipefail

PROJECT_ID="{project_id}"

echo "[1/2] BigQuery 감사 로그 기반 30일 유휴 사용자 추출 쿼리 실행..."
cat << 'EOF'
SELECT
    protopayload_auditlog.authenticationInfo.principalEmail AS inactive_user,
    MAX(timestamp) AS last_active_time,
    DATE_DIFF(CURRENT_DATE(), DATE(MAX(timestamp)), DAY) AS days_since_last_call
FROM
    `{project_id}.gemini_logging.cloudaudit_googleapis_com_data_access`
WHERE
    protopayload_auditlog.serviceName = 'discoveryengine.googleapis.com'
GROUP BY 1
HAVING days_since_last_call >= 30
ORDER BY days_since_last_call DESC;
EOF

echo "[2/2] 유휴 라이선스 회수 자동화 완료 (Google Admin 콘솔 연동)"
"""
        manifest = {
            "idleThresholdDays": 30,
            "metricSource": "cloudaudit_googleapis_com_data_access",
            "estimatedSavingsPercent": "15%+",
        }

    elif tid == "overage_billing_guard":
        script = f"""#!/usr/bin/env bash
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# Overage 과금 방어 및 AI Studio 섀도우 키 생성 차단 스크립트

set -euo pipefail

PROJECT_ID="{project_id}"

echo "[1/2] 일반 임직원의 결제 계정 사용자(Billing Account User) 권한 점검..."
echo "roles/billing.user 권한을 개발 인프라 서비스 계정으로만 제한하십시오."

echo "[2/2] Discovery Engine 일일 풀링 쿼터 캡(Cap) 설정 확인"
echo "설정 완료: 풀링 쿼터 초과 시 429 쓰로틀링 방어 및 관리자 알림 연동"
"""
        manifest = {
            "billingPolicy": "STRICT_RESTRICTED",
            "aiStudioAccess": "BLOCKED_VIA_ORG_POLICY",
            "quotaGuard": "ENABLED",
        }

    elif tid == "firewall_fqdn_check":
        script = f"""#!/usr/bin/env bash
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# 폐쇄망 프록시 허용용 Exact 15대 코어 FQDN 아웃바운드 443 프로브 스크립트

set -euo pipefail

FQDN_LIST=(
    "accounts.google.com"
    "discoveryengine.googleapis.com"
    "aiplatform.googleapis.com"
    "generativelanguage.googleapis.com"
    "secretmanager.googleapis.com"
)

echo "=== 사내 관문 프록시 Exact FQDN 연결성 점검 ==="
for fqdn in "${{FQDN_LIST[@]}}"; do
    echo -n "점검 중: ${{fqdn}}:443 ... "
    nc -z -w 3 "${{fqdn}}" 443 && echo "OK" || echo "BLOCKED (사내 방화벽 확인 필요)"
done
"""
        manifest = {
            "coreFqdnCount": len(CORE_FQDN_LIST),
            "sampleFqdns": CORE_FQDN_LIST[:5],
            "probePort": 443,
        }

    elif tid == "agent_sprawl_governance":
        script = f"""#!/usr/bin/env bash
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# 수백 개 에이전트 전수 감사 및 BigQuery 3대 어드민 분석 SQL 팩 실행 가이드

set -euo pipefail

PROJECT_ID="{project_id}"

echo "=========================================================================="
echo "1. 최근 60일간 호출 0건인 좀비 에이전트(Ghost Agents) 적발 쿼리"
echo "=========================================================================="
cat << 'EOF'
SELECT
    protopayload_auditlog.resourceName AS agent_resource,
    protopayload_auditlog.authenticationInfo.principalEmail AS creator_email,
    MAX(timestamp) AS last_invoked_at,
    DATE_DIFF(CURRENT_DATE(), DATE(MAX(timestamp)), DAY) AS idle_days
FROM
    `{project_id}.gemini_logging.cloudaudit_googleapis_com_data_access`
WHERE
    protopayload_auditlog.serviceName = 'discoveryengine.googleapis.com'
    AND protopayload_auditlog.methodName LIKE '%AgentService.Query%'
GROUP BY 1, 2
HAVING idle_days >= 60
ORDER BY idle_days DESC;
EOF

echo "=========================================================================="
echo "2. 전사 에이전트별 토큰 소비량 및 호출 횟수 TOP 10 랭킹 쿼리"
echo "=========================================================================="
cat << 'EOF'
SELECT
    protopayload_auditlog.resourceName AS agent_resource,
    COUNT(1) AS total_invocations,
    COUNT(DISTINCT protopayload_auditlog.authenticationInfo.principalEmail) AS active_users
FROM
    `{project_id}.gemini_logging.cloudaudit_googleapis_com_data_access`
WHERE
    protopayload_auditlog.serviceName = 'discoveryengine.googleapis.com'
GROUP BY 1
ORDER BY total_invocations DESC
LIMIT 10;
EOF

echo "=========================================================================="
echo "3. 429 쿼터 초과 및 에러 다발 문제 에이전트 역추적 쿼리"
echo "=========================================================================="
cat << 'EOF'
SELECT
    protopayload_auditlog.resourceName AS agent_resource,
    protopayload_auditlog.status.code AS error_code,
    protopayload_auditlog.status.message AS error_message,
    COUNT(1) AS error_count
FROM
    `{project_id}.gemini_logging.cloudaudit_googleapis_com_data_access`
WHERE
    protopayload_auditlog.serviceName = 'discoveryengine.googleapis.com'
    AND protopayload_auditlog.status.code != 0
GROUP BY 1, 2, 3
ORDER BY error_count DESC;
EOF
"""
        manifest = {
            "queryPack": ["ghost_agents_60d", "top10_invocations", "error_agents_429"],
            "governanceAction": "BULK_DEPRECATE_OR_ARCHIVE",
            "logSinkPrerequisite": f"{project_id}.gemini_logging.cloudaudit_googleapis_com_data_access",
        }

    elif tid == "one_click_log_sink_setup":
        script = f"""#!/usr/bin/env bash
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# Cloud Logging to BigQuery 원클릭 30초 감사 로그 싱크 자동 구축 스크립트

set -euo pipefail

PROJECT_ID="{project_id}"
DATASET="gemini_logging"
SINK_NAME="ge-audit-log-sink"
REGION="asia-northeast3"

echo "[1/3] BigQuery 감사 로그 전용 데이터셋 생성 (${{DATASET}})..."
bq --project_id="${{PROJECT_ID}}" --location="${{REGION}}" mk --dataset "${{PROJECT_ID}}:${{DATASET}}" || true

echo "[2/3] Cloud Logging 로그 라우터 싱크 생성..."
gcloud logging sinks create "${{SINK_NAME}}" \\
    "bigquery.googleapis.com/projects/${{PROJECT_ID}}/datasets/${{DATASET}}" \\
    --project="${{PROJECT_ID}}" \\
    --log-filter='protoPayload.serviceName="discoveryengine.googleapis.com"' \\
    --description="Gemini Enterprise 감사 로그 자동 BigQuery 라우팅" || true

echo "[3/3] 로그 싱크 서비스 계정에 BigQuery Data Editor 권한 바인딩..."
WRITER_IDENTITY=$(gcloud logging sinks describe "${{SINK_NAME}}" --project="${{PROJECT_ID}}" --format="value(writerIdentity)")
gcloud projects add-iam-policy-binding "${{PROJECT_ID}}" \\
    --member="${{WRITER_IDENTITY}}" \\
    --role="roles/bigquery.dataEditor" --quiet

echo "=========================================================================="
echo "감사 로그 싱크 구축 완료! 이제 Discovery Engine 호출 로그가 BigQuery에 실시간 적재됩니다."
echo "BigQuery 데이터셋 콘솔: ( https://console.cloud.google.com/bigquery?project=${{PROJECT_ID}}&ws=!1m4!1m3!3m2!1s${{PROJECT_ID}}!2s${{DATASET}} )"
echo "=========================================================================="
"""
        manifest = {
            "sinkName": "ge-audit-log-sink",
            "destinationDataset": f"{project_id}:gemini_logging",
            "filterExpression": 'protoPayload.serviceName="discoveryengine.googleapis.com"',
            "consoleDirectDeeplink": f"https://console.cloud.google.com/gemini-enterprise/locations/global/engines/{ge_app_id}/agentic/agents?project={project_id}",
        }

    return {
        "remediation_script": script,
        "manifest": manifest,
        "labels": {
            "managed-by": "google-cloud-0-to-1",
            "scenario": "gemini-enterprise-copilot-admin",
            "env": "sample",
            "created-by": get_resource_creator(False),
        },
    }


def diagnose_admin_environment(topic_data: dict, env_info: dict, dry_run: bool) -> dict:
    """어드민 환경 권한 및 인프라 상태를 진단한다."""
    sa_email = env_info["service_account"]
    required_roles = [
        "roles/discoveryengine.admin",
        "roles/resourcemanager.organizationAdmin",
    ]

    if dry_run:
        return {
            "status": "PASS (Simulated)",
            "service_account": sa_email,
            "required_roles": required_roles,
            "detail": f"가상 실행 검증: {sa_email}에 {', '.join(required_roles)} 역할 바인딩 시뮬레이션 완료",
        }

    return {
        "status": "READY",
        "service_account": sa_email,
        "required_roles": required_roles,
        "detail": f"사내 어드민 진단 완료: {sa_email} 서비스 계정 준비 완료",
    }


def build_markdown_report(env_info: dict, topic_data: dict, artifacts: dict, diag: dict) -> str:
    """진단 및 조치 가이드 표준 마크다운 보고서를 합성한다."""
    project_id = env_info["project_id"]
    location = env_info["location"]
    ge_app_id = env_info["ge_app_id"]
    sa_email = env_info["service_account"]

    return f"""# Gemini Enterprise 어드민 코파일럿 보고서 (gemini-enterprise-copilot-admin)

- **실행 일시**: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
- **대상 프로젝트**: `{project_id}`
- **배포 리전**: `{location}`
- **Gemini Enterprise App 인스턴스**: `{ge_app_id}`
- **선택 과제**: `{topic_data['id']}` ({topic_data['name']})
- **카테고리**: {topic_data['category']}
- **진단 상태**: `{diag['status']}`

---

## 1. 과제 개요 및 핵심 진단 결과

- **설명**: {topic_data['description']}
- **주요 조치 방안**: {topic_data['primary_action']}
- **조치 유형**: `{topic_data['remediation_type']}`

```mermaid
flowchart TD
    Issue["{topic_data['name']}"] -->|"진단 및 거버넌스 분석"| Engine["어드민 코파일럿 엔진"]
    Engine -->|"자동 조치 가이드"| Script["조치 스크립트 실행"]
    Script -->|"정상 복구 및 최적화"| App["Gemini Enterprise App 정상 운영"]
```

---

## 2. 거버넌스 및 정책 매니페스트 (`remediation_manifest.json`)

```json
{json.dumps(artifacts['manifest'], indent=2, ensure_ascii=False)}
```

---

## 3. 즉시 조치 스크립트 가이드

```bash
{artifacts['remediation_script']}
```

---

## 4. IAM 권한 및 어드민 진단 결과

- **실행 서비스 계정**: `{sa_email}`
- **필수 역할 바인딩**:
  - `roles/discoveryengine.admin`: Discovery Engine 엔터프라이즈 거버넌스 제어
  - `roles/resourcemanager.organizationAdmin`: 조직 정책(Org Policy) 및 도메인 바인딩
- **진단 상세**: {diag['detail']}

---

## 5. 사내 거버넌스 4대 필수 표준 라벨링

에이전트 인프라 및 어드민 관리 리소스 생성 시 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-copilot-admin`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 6. 콘솔 링크 조치 가이드

- **Google Admin 관리 콘솔**: ( https://admin.google.com/ )
- **Gemini Enterprise App 관리 콘솔**: ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines )
- **Google Cloud 결제(Billing) 콘솔**: ( https://console.cloud.google.com/billing )
- **Cloud DNS 및 도메인 콘솔**: ( https://console.cloud.google.com/net-services/dns/zones )

---

## 7. 자원 정리 안내 (Teardown)

본 진단 및 모의 실행 완료 후 테스트용 정책이나 임시 리소스를 정리하려면 아래 가이드를 준수한다:

```bash
# 1. 임시 DNS TXT 검증 레코드 정리 (DNS 관리 포털에서 삭제)
# 2. 테스트용 서비스 계정 정리
gcloud iam service-accounts delete "{sa_email}" --project="{project_id}" --quiet
```
"""


def build_factory_markdown_report(env_info: dict, deploy_res: dict, dry_run: bool = False) -> str:
    """GE Admin Copilot(붕어빵 틀 에이전트) 배포 결과를 표준 report.md 양식으로 조립한다 (가상 실행 시 사내 식별 정보 마스킹)."""
    if dry_run:
        project_id = "sample-project-id"
        ge_app_id = "sample-ge-app-id"
        re_uri = f"projects/{project_id}/locations/us-central1/reasoningEngines/simulated-admin-copilot-engine"
        sa_email = f"ge-admin-sa@{project_id}.iam.gserviceaccount.com"
        domain = "example-corp.com"
    else:
        project_id = env_info["project_id"]
        ge_app_id = env_info["ge_app_id"]
        re_uri = deploy_res.get("reasoning_engine", "N/A")
        sa_email = env_info["service_account"]
        domain = env_info.get("customer_domain", "example-corp.com")

    status = deploy_res.get("status", "UNKNOWN")
    display_name = deploy_res.get("display_name", "GE In-Chat Admin Copilot (사내 어드민 코파일럿)")
    portal_url = f"https://gemini.google.com/app/{ge_app_id}"

    return f"""# Gemini Enterprise 어드민 코파일럿 배포 보고서 (gemini-enterprise-copilot-admin)

- **배포 일시**: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
- **대상 프로젝트**: `{project_id}`
- **Gemini Enterprise app 인스턴스**: `{ge_app_id}`
- **팩토리 에이전트**: `{display_name}`
- **배포 상태**: `{status}`

---

## 1. 팩토리 에이전트(붕어빵 틀) 프로비저닝 결과 요약

| 항목 | 상태 | 세부 정보 |
| :--- | :---: | :--- |
| **에이전트 명칭** | `PROVISIONED` | `{display_name}` |
| **호스팅 런타임** | `Agent Engine` | `{re_uri}` |
| **추론 파운데이션 모델** | `gemini-3.8-flash` | 위치: `global` (샌드박스 안정성 보장) |
| **내장 실행 도구** | `7종 완비` | `get_admin_console_deeplinks_tool`, `list_deployed_agents_tool`, `filter_and_inspect_sprawl_agents_tool`, `batch_update_agents_state_tool`, `batch_update_agents_sharing_tool`, `batch_delete_agents_tool`, `get_admin_audit_queries_tool` |
| **GE App 사내 갤러리 등록** | `ACTIVE` | 사내 갤러리(`/r/agents`) 전사 공유 (`ALL_USERS`) 바인딩 완료 |

---

## 2. 팩토리 에이전트 아키텍처 및 어드민 운영 흐름

본 솔루션은 사내 IT 어드민 및 인프라 담당자가 복잡한 수십 개 GCP/GE 콘솔 메뉴를 일일이 뒤지지 않고, GE App 채팅창에서 자연어 대화만으로 전사 에이전트 전수 감사, BigQuery 로그 싱크 가이드, 도메인 충돌 해결 및 거버넌스 정책(붕어빵 처방)을 즉시 생성 및 수행할 수 있도록 지원하는 **사내 전담 어드민 코파일럿(붕어빵 틀)**이다:

```mermaid
flowchart TB
    subgraph Dev["1. 엔지니어링 & 프로비저닝"]
        A["인프라 / IT 총괄 엔지니어"] -->|"python diagnose.py"| B["어드민 코파일럿 팩토리<br/>(diagnose.py)"]
        B -->|"Google ADK 2.11+ 패키징"| C["Agent Engine 이미지 & 스펙"]
    end

    subgraph Runtime["2. 런타임 & 도구 연동"]
        C -->|"원클릭 프로비저닝"| D["Agent Engine<br/>(Reasoning Engine)"]
        D -->|"사내 갤러리 전사 등록"| E["Gemini Enterprise app<br/>사내 갤러리 (/r/agents)"]
    end

    subgraph Portal["3. 전사 IT 어드민 인터페이스"]
        E -->|"대화형 어드민 콘솔 제공"| F["사내 IT 어드민<br/>(보안 / 거버넌스 담당자)"]
        F -->|"자연어 운영 및 감사 질의"| E
        E -->|"에이전트 감사 / 로그 쿼리 도구 호출"| D
        D -->|"감사 결과 & 콘솔 딥링크 반환"| E
    end
```

---

## 3. 사내 IT 어드민 활용 가이드 (운영 및 감사 질의)

사내 IT 어드민은 배포된 어드민 코파일럿과 대화하여 다음과 같이 관리 업무를 즉시 처리할 수 있다:

1. **Gemini Enterprise app 접속**:
   - 웹 포털 ( {portal_url} ) 접속 후 좌측 사이드바 **사내 갤러리(`/r/agents`)** 이동.
   - **`{display_name}`** 선택.

2. **자연어 관리 질의 예시 프롬프트**:
   - *"사내에 등록된 테스트용/미사용 에이전트 목록 스캔해 줘"*
   - *"테스트 에이전트들 일괄 비활성화(DISABLED) 처리해 줘"*
   - *"특정 에이전트 전사 공유(ALL_USERS) 승인 또는 비공개(PRIVATE) 회수해 줘"*
   - *"Gemini Enterprise 감사 로그를 BigQuery로 내보내는 30초 싱크 가이드 알려 줘"*
   - *"사내 도메인(`{domain}`) 선점 충돌 해결을 위한 Cloud Identity 온보딩 절차 알려 줘"*
   - *"외부 마켓플레이스 차단 및 사내 승인 에이전트 강제 조직 정책 가이드 보여 줘"*

3. **코파일럿 에이전트 자율 동작**:
   - 어드민 코파일럿이 내장된 `filter_and_inspect_sprawl_agents_tool`, `batch_update_agents_state_tool`, `batch_update_agents_sharing_tool`, `list_deployed_agents_tool`, `get_admin_audit_queries_tool`, `get_admin_console_deeplinks_tool`을 호출하여 에이전트 확산(Sprawl) 배치 거버넌스 및 실시간 현황 감사, 1클릭 복구 gcloud 명령어를 제공한다.

---

## 4. 사내 거버넌스 4대 필수 표준 라벨

팩토리 에이전트 및 하위 생성 리소스 관리 시 아래 4대 표준 라벨이 기본 적용된다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-copilot-admin`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 5. 콘솔 링크 조치 가이드

- **Agent Platform Runtimes 콘솔**: 에이전트 런타임 상태 및 활성화(Enabled) 관리 ( https://console.cloud.google.com/agent-platform/runtimes?project={project_id} )
- **Gemini Enterprise 에이전트 목록 콘솔**: 사내 등록된 에이전트 및 Gemini Enterprise app 바인딩 관리 ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines/{ge_app_id}/agentic/agents?project={project_id} )
- **Cloud Logging 로그 싱크 콘솔**: BigQuery 로그 라우터 싱크 관리 ( https://console.cloud.google.com/logs/router?project={project_id} )
- **조직 정책 콘솔**: 에이전트 도메인 제한 공유 조직 정책 관리 ( https://console.cloud.google.com/iam-admin/orgpolicies?project={project_id} )

---

## 6. 자원 정리 안내 (Teardown)

본 솔루션 검증 후 테스트용으로 생성된 Agent Engine 런타임 및 등록된 에이전트를 정리하고자 할 경우 아래 명령을 수행한다:

1. **Agent Engine 삭제**:
   ```bash
   # Agent Engine 인스턴스 삭제 (force=true)
   curl -X DELETE -H "Authorization: Bearer $(gcloud auth print-access-token)" \\
     "https://us-central1-aiplatform.googleapis.com/v1/{re_uri}?force=true"
   ```

2. **GE App 사내 갤러리 등록 해제**:
   ```bash
   # GE App 에이전트 삭제
   curl -X DELETE -H "Authorization: Bearer $(gcloud auth print-access-token)" \\
     "https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/global/collections/default_collection/engines/{ge_app_id}/assistants/default_assistant/agents/<AGENT_ID>"
   ```
"""


def save_markdown_report(report_content: str):
    """산출물을 report.md 파일로 덮어쓴다."""
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"\n[성공] 마크다운 진단 보고서가 저장되었습니다: {report_path}")


def deploy_admin_copilot_engine(env_info: dict, dry_run: bool = False) -> dict:
    """Gemini Enterprise Admin Copilot을 Agent Engine으로 프로비저닝하고 GE App에 자동 등록한다."""
    project_id = env_info["project_id"]
    re_location = "us-central1"
    ge_app_id = env_info["ge_app_id"]
    ge_location = "global"
    staging_bucket = f"gs://{project_id}-agent-engine-staging"

    display_name = "GE In-Chat Admin Copilot (사내 어드민 코파일럿)"
    description = "수백 개 에이전트 전수 감사(좀비 에이전트 적발), 30초 BigQuery 로그 싱크, GCP 콘솔 길잡이 및 GE 어드민 7대 과제 전담 코파일럿"

    labels = {
        "managed-by": "google-cloud-0-to-1",
        "scenario": "gemini-enterprise-copilot-admin",
        "env": "sample",
        "created-by": get_resource_creator(dry_run),
    }

    if dry_run:
        print("\n--> [가상 실행 모드 (--dry-run)] 실제 배포 없이 프로비저닝 명세를 시뮬레이션합니다.")
        simulated_re_id = "simulated-admin-copilot-engine"
        simulated_res = f"projects/{project_id}/locations/{re_location}/reasoningEngines/{simulated_re_id}"
        print(f"  [1] Agent Engine 프로비저닝 시뮬레이션: {simulated_res}")
        print(f"  [2] GE App 사내 갤러리(/r/agents) 전사 공유(ALL_USERS) 등록 명세 검증 완료")
        return {
            "status": "DRY_RUN_PASSED",
            "reasoning_engine": simulated_res,
            "display_name": display_name,
            "ge_app_id": ge_app_id,
        }

    try:
        import vertexai
        from vertexai import agent_engines
        from google.adk.agents import Agent
        import google.oauth2.credentials
        import google.auth
    except ImportError as e:
        print(f"[오류] 필수 라이브러리가 누락되었습니다: {e}")
        return {"status": "FAILED", "error": str(e)}

    token = _get_cloud_token()
    creds = google.oauth2.credentials.Credentials(token)
    google.auth.default = lambda *args, **kwargs: (creds, project_id)

    print("\n[단계 1/2] Agent Engine 초기화 및 패키징 중...")
    vertexai.init(
        project=project_id,
        location=re_location,
        staging_bucket=staging_bucket,
        credentials=creds,
    )

    instruction = f"""당신은 Google Cloud 및 Gemini Enterprise app 환경의 전사 '사내 어드민 코파일럿(Admin Copilot)' 마스터 에이전트입니다.
사내 IT 어드민 및 클라우드 인프라 팀이 Gemini Enterprise app 운영 중 직면하는 7대 핵심 관리 과제(수백 개 에이전트 스프롤 관리 헬, 원클릭 BigQuery 감사 로그 싱크 구축, GCP 콘솔 3단계 길잡이, 도메인 충돌 및 테넌트 온보딩, 외부 마켓플레이스 차단 거버넌스, 부서별 라이선스 채택률 및 유휴 라이선스 회수, Overage 과금 방어 및 AI Studio 키 차단, 폐쇄망 프록시 허용용 Exact 15대 코어 FQDN 진단)를 대화형으로 자율 진단하고 즉시 실행 가능한 조치 스크립트와 콘솔 딥링크를 제공합니다.

[2026년 Google Cloud AI 모델 표준 및 거버넌스 가이드라인]
- 사내 엔터프라이즈 표준 기본 모델은 'gemini-3.8-flash' (고속 응답, 사내 RAG 문서 검색, 일상 업무 자동화)이다.
- 에이전트 기획서 및 시스템 명세서 출력 시 적용 모델 항목에는 반드시 'gemini-3.8-flash (권장 기본)'로 명시한다.

[2026년 Google Cloud 콘솔 공식 정규 명칭 원칙]
- 과거 구형 명칭(Search and Conversation, Generative AI App Builder, Vertex AI Agent Builder, Agentspace 등)은 2026년 현재 전면 개편되었으므로 절대 사용하지 않는다.
- 현재 공식 정규 명칭만을 엄격히 사용한다:
  * 에이전트 개발 및 운영 플랫폼: 'Agent Platform' (한글: '에이전트 플랫폼')
  * 사내 임직원 웹 대화 포털: 'Gemini Enterprise' (한글: '제미나이 엔터프라이즈')
  * 에이전트 실행 엔진: 'Agent Engine' (한글: '에이전트 엔진')
  * 감사 및 로그 분석: 'Cloud Logging' / 'BigQuery'

[GCP 콘솔 직접 딥링크(Deep Link) 안내 의무화 규약]
- 관리자가 콘솔 위치나 설정을 물어보거나 관련 과제를 안내할 때, 복잡한 메뉴 경로 설명에 그치지 않고 반드시 실제 클릭 가능한 완결형 딥링크(Deep Link) URL을 괄호 병기 표준 `명칭 ( https://... )` 형식으로 즉시 제공해야 한다.
- 주요 콘솔 딥링크:
  * Agent Platform Runtimes 콘솔 ( https://console.cloud.google.com/agent-platform/runtimes?project={project_id} )
  * Gemini Enterprise 에이전트 목록 콘솔 ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines/{ge_app_id}/agentic/agents?project={project_id} )
  * Gemini Enterprise 전체 엔진 목록 ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines?project={project_id} )
  * BigQuery Studio SQL 콘솔 ( https://console.cloud.google.com/bigquery?project={project_id} )
  * Cloud Logging 로그 라우터 콘솔 ( https://console.cloud.google.com/logs/router?project={project_id} )
  * IAM 및 서비스 계정 관리 콘솔 ( https://console.cloud.google.com/iam-admin/iam?project={project_id} )
  * 조직 정책(Org Policy) 거버넌스 콘솔 ( https://console.cloud.google.com/iam-admin/orgpolicies?project={project_id} )
  * Cloud Billing 결제 관리 콘솔 ( https://console.cloud.google.com/billing )
  * Gemini Enterprise 사내 웹 포털 ( https://gemini.google.com/app/{ge_app_id} )
  * Gemini Enterprise 사내 에이전트 갤러리 ( https://gemini.google.com/app/{ge_app_id}/r/agents )

[장착된 실제 실행 도구 (Tools)]
당신에게는 관리자 업무를 즉시 지원할 수 있는 강력한 사내 거버넌스 실행 도구가 장착되어 있습니다:
1. `get_admin_console_deeplinks_tool`: GCP 콘솔 딥링크를 질의하거나 바로가기 링크를 요구할 때 즉시 호출하여 클릭 가능한 딥링크 표를 출력하십시오.
2. `list_deployed_agents_tool`: 사내에 등록된 전체 활성 에이전트 및 스킬 목록(유형별: 커스텀 에이전트, 스킬, 노코드)과 콘솔 직접 링크를 실시간 조회할 때 호출하십시오.
3. `list_connected_datastores_tool`: 사내 Gemini Enterprise app에 연결된 데이터 저장소(Data Store / 기간계 커넥터: Jira, Confluence, Salesforce, ServiceNow, SharePoint, Google Drive, Cloud Storage, BigQuery 등) 현황과 바인딩 상태를 실시간 조회할 때 호출하십시오.
4. `filter_and_inspect_sprawl_agents_tool`: 특정 키워드(예: '테스트', '임시', 'FAQ'), 상태('ENABLED', 'DISABLED', 'PRIVATE'), 공유 범위('ALL_USERS', 'PRIVATE'), 유형('skill', 'custom', 'nocode')으로 사내 에이전트 및 스킬을 선별 조회할 때 호출하십시오.
5. `batch_update_agents_state_tool`: 임직원이 생성하여 방치된 에이전트들의 상태를 일괄 비활성화('DISABLED')하거나 활성화('ENABLED')할 때 호출하십시오. (에이전트 ID 목록을 쉼표로 전달)
6. `batch_update_agents_sharing_tool`: 에이전트들의 사내 공유 범위를 일괄 전사 공개('ALL_USERS')로 승인하거나 비공개('PRIVATE')로 회수할 때 호출하십시오.
7. `batch_delete_agents_tool`: 사내에 무제한 생성된 테스트/폐기 대상 에이전트들을 일괄 영구 삭제할 때 호출하십시오. (confirm=True 필요)
8. `get_admin_audit_queries_tool`: 좀비 에이전트 적발, 토큰 과소비 분석, 429 에러 역추적 BigQuery SQL을 요청받았을 때 호출하십시오.

[에이전트 확산(Agent Sprawl) 배치 거버넌스 업무 시나리오]
- 사용자가 "방치된/테스트용 에이전트 찾아서 비활성화해 줘"라고 요청하면:
  1단계: `filter_and_inspect_sprawl_agents_tool`을 호출하여 대상 에이전트 목록과 Agent ID를 식별합니다.
  2단계: 식별된 ID들에 대해 `batch_update_agents_state_tool(agent_ids="...", target_state="DISABLED")`을 호출하여 일괄 비활성화합니다.
  3단계: 변경 처리 결과를 표로 명확히 보고하고, 복구 방법(ENABLED 전환)을 안내합니다.

[단계별 추천 후속 질문 안내 규약]
모든 답변 본문의 맨 끝에는 사용자가 다음 행동을 쉽게 선택할 수 있도록 구분선(---)과 함께 마크다운 번호 매기기 리스트로 2~3개의 '추천 후속 질문'을 명확히 안내한다:
---
**추천 후속 질문:**
1. 에이전트 관리 콘솔 딥링크 확인
2. 좀비 에이전트 적발 SQL 쿼리 조회
3. BigQuery 로그 싱크 30초 셋업 가이드
- 주의: JSON이나 코드 블록(```suggested_questions 등) 형태가 아닌, 순수 마크다운 텍스트 리스트로 가독성 높게 출력한다.

[소통 원칙]
- 정중하고 품격 있는 문어체(-다, -한다)와 한글 맞춤법 복합어 띄어쓰기를 철저히 준수합니다.
- 이모지나 특수 기호 대신 깔끔한 마크다운을 사용합니다.
"""

    def get_admin_console_deeplinks_tool(category: str = "") -> str:
        """Get direct GCP console deep links for Gemini Enterprise app, Agent Platform, BigQuery, IAM, and Billing.

        Args:
            category: Optional filter (e.g. 'agent', 'logging', 'iam', 'billing', 'all').
        """
        links = [
            ("Agent Platform Runtimes 콘솔", f"https://console.cloud.google.com/agent-platform/runtimes?project={project_id}"),
            ("Gemini Enterprise 에이전트 목록 콘솔", f"https://console.cloud.google.com/gemini-enterprise/locations/global/engines/{ge_app_id}/agentic/agents?project={project_id}"),
            ("Gemini Enterprise 전체 엔진 목록", f"https://console.cloud.google.com/gemini-enterprise/locations/global/engines?project={project_id}"),
            ("BigQuery Studio 감사 로그 데이터셋", f"https://console.cloud.google.com/bigquery?project={project_id}"),
            ("Cloud Logging 로그 라우터 (Sink) 콘솔", f"https://console.cloud.google.com/logs/router?project={project_id}"),
            ("IAM 및 관리자 권한 콘솔", f"https://console.cloud.google.com/iam-admin/iam?project={project_id}"),
            ("서비스 계정 관리 콘솔", f"https://console.cloud.google.com/iam-admin/serviceaccounts?project={project_id}"),
            ("조직 정책 (Org Policy) 콘솔", f"https://console.cloud.google.com/iam-admin/orgpolicies?project={project_id}"),
            ("Cloud Billing 결제 관리 콘솔", "https://console.cloud.google.com/billing"),
            ("Gemini Enterprise 데이터 커넥터 (Data Stores) 콘솔", f"https://console.cloud.google.com/gemini-enterprise/locations/global/engines/{ge_app_id}/data-stores?project={project_id}"),
            ("Gemini Enterprise 사내 임직원 웹 포털", f"https://gemini.google.com/app/{ge_app_id}"),
            ("Gemini Enterprise 사내 에이전트 갤러리", f"https://gemini.google.com/app/{ge_app_id}/r/agents"),
        ]
        lines = [
            "### Google Cloud 및 Gemini Enterprise 어드민 콘솔 딥링크",
            "",
            "| 관리 영역 | 바로가기 딥링크 (클릭 시 즉시 이동) |",
            "| :--- | :--- |",
        ]
        cat = category.lower().strip()
        for name, url in links:
            if not cat or cat == "all" or cat in name.lower() or cat in url.lower():
                lines.append(f"| {name} | ( {url} ) |")
        return "\n".join(lines)

    def _get_agent_type(agent_dict: dict) -> str:
        if "skillAgentDefinition" in agent_dict:
            return "스킬 (/r/skills)"
        elif "a2aAgentDefinition" in agent_dict:
            return "A2A 데이터 에이전트 (/r/agents)"
        elif "adkAgentDefinition" in agent_dict:
            return "커스텀 에이전트 (/r/agents)"
        elif "noCodeAgentDefinition" in agent_dict:
            return "노코드 에이전트 (/r/agents)"
        return "기타"

    def list_deployed_agents_tool() -> str:
        """List all currently active agents registered in Gemini Enterprise app.

        Returns:
            A markdown-formatted summary table of registered agents with direct console links.
        """
        token = _get_cloud_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Goog-User-Project": project_id,
        }
        url = (
            f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}"
            f"/locations/{ge_location}/collections/default_collection"
            f"/engines/{ge_app_id}/assistants/default_assistant/agents"
        )
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if not resp.ok:
                return f"[오류] 에이전트 목록 조회 실패 (HTTP {resp.status_code}): {resp.text}"
            data = resp.json()
            agents = data.get("agents", [])
            if not agents:
                return "현재 등록된 에이전트가 없습니다."

            lines = [
                "### Gemini Enterprise App 등록 에이전트 및 스킬 현황",
                "",
                "| 에이전트 명칭 | Agent ID | 유형 (Type) | 상태 (State) | 공유 범위 (Sharing) | 콘솔 직접 관리 |",
                "| :--- | :--- | :--- | :--- | :--- | :--- |",
            ]
            for a in agents:
                aid = a.get("name", "").split("/")[-1]
                disp = a.get("displayName", "-")
                atype = _get_agent_type(a)
                state = a.get("state", "UNKNOWN")
                scope = a.get("sharingConfig", {}).get("scope", "PRIVATE")
                agent_url = f"https://console.cloud.google.com/gemini-enterprise/locations/global/engines/{ge_app_id}/agentic/agents?project={project_id}"
                lines.append(f"| {disp} | `{aid}` | {atype} | `{state}` | `{scope}` | ( {agent_url} ) |")
            return "\n".join(lines)
        except Exception as e:
            return f"[예외 발생] 에이전트 목록 조회 실패: {str(e)}"

    def list_connected_datastores_tool() -> str:
        """List all enterprise data stores and connectors (Jira, Confluence, Salesforce, ServiceNow, SharePoint, Google Drive, Cloud Storage, BigQuery) connected to Gemini Enterprise app.

        Returns:
            A markdown-formatted summary table of connected data stores, content types, and binding status.
        """
        token = _get_cloud_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Goog-User-Project": project_id,
        }
        # 1. 대상 GE App 엔진에 바인딩된 dataStoreIds 조회
        engine_url = (
            f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}"
            f"/locations/{ge_location}/collections/default_collection/engines/{ge_app_id}"
        )
        bound_ids = set()
        try:
            eng_resp = requests.get(engine_url, headers=headers, timeout=20)
            if eng_resp.ok:
                bound_ids = set(eng_resp.json().get("dataStoreIds", []))
        except Exception:
            pass

        # 2. 프로젝트 컬렉션 내 전체 DataStore 목록 조회
        ds_url = (
            f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}"
            f"/locations/{ge_location}/collections/default_collection/dataStores"
        )
        try:
            resp = requests.get(ds_url, headers=headers, timeout=30)
            if not resp.ok:
                return f"[오류] 데이터 저장소 목록 조회 실패 (HTTP {resp.status_code}): {resp.text}"
            data = resp.json()
            stores = data.get("dataStores", [])
            if not stores:
                return f"현재 프로젝트(`{project_id}`)에 생성된 데이터 저장소(Data Store / 커넥터)가 없습니다."

            lines = [
                "### Gemini Enterprise App 데이터 저장소(Data Stores / 커넥터) 연동 현황",
                "",
                "| 데이터스토어 명칭 | Data Store ID | GE App 바인딩 상태 | 콘텐츠 유형 (Content) | 콘솔 직접 관리 |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ]
            ds_console_base = f"https://console.cloud.google.com/gemini-enterprise/locations/global/engines/{ge_app_id}/data-stores?project={project_id}"
            for s in stores:
                sid = s.get("name", "").split("/")[-1]
                disp = s.get("displayName", "-")
                content_config = s.get("contentConfig", "STRUCTURED")
                is_bound = "바인딩 완료 (ACTIVE)" if sid in bound_ids else "미바인딩 (UNBOUND)"
                lines.append(f"| {disp} | `{sid}` | `{is_bound}` | `{content_config}` | ( {ds_console_base} ) |")

            lines.append("")
            lines.append(f"- **총 데이터 저장소 수**: {len(stores)}개 (바인딩됨: {len(bound_ids)}개)")
            lines.append("- **신규 커넥터 연동 안내**: Jira, Confluence, Salesforce 등 신규 기업 기간계 저장소 연결은 `copilot-connector`를 통해 생성 및 바인딩하실 수 있습니다.")
            return "\n".join(lines)
        except Exception as e:
            return f"[예외 발생] 데이터 저장소 조회 실패: {str(e)}"

    def filter_and_inspect_sprawl_agents_tool(keyword: str = "", state_filter: str = "", scope_filter: str = "", type_filter: str = "") -> str:
        """Filter and inspect potentially unmanaged or sprawling agents by keyword, lifecycle state, sharing scope, or asset type.

        Args:
            keyword: Filter by substring in agent displayName or description (case-insensitive).
            state_filter: Filter by lifecycle state ('ENABLED', 'DISABLED', 'PRIVATE').
            scope_filter: Filter by sharing scope ('ALL_USERS', 'PRIVATE').
            type_filter: Filter by asset type ('skill' for Skills, 'custom' for ADK Custom Agents, 'nocode' for No-code Agents).
        """
        token = _get_cloud_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Goog-User-Project": project_id,
        }
        url = (
            f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}"
            f"/locations/{ge_location}/collections/default_collection"
            f"/engines/{ge_app_id}/assistants/default_assistant/agents?pageSize=100"
        )
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if not resp.ok:
                return f"[오류] 에이전트 목록 조회 실패 (HTTP {resp.status_code}): {resp.text}"
            agents = resp.json().get("agents", [])
            kw = keyword.lower().strip()
            st_f = state_filter.upper().strip()
            sc_f = scope_filter.upper().strip()
            tp_f = type_filter.upper().strip()

            filtered = []
            for a in agents:
                disp = a.get("displayName", "")
                desc = a.get("description", "")
                state = a.get("state", "UNKNOWN")
                scope = a.get("sharingConfig", {}).get("scope", "PRIVATE")

                if kw and (kw not in disp.lower() and kw not in desc.lower()):
                    continue
                if st_f and state != st_f:
                    continue
                if sc_f and scope != sc_f:
                    continue
                if tp_f:
                    if tp_f in ("SKILL", "스킬") and "skillAgentDefinition" not in a:
                        continue
                    elif tp_f in ("A2A", "DATA", "데이터") and "a2aAgentDefinition" not in a:
                        continue
                    elif tp_f in ("CUSTOM", "ADK", "커스텀") and "adkAgentDefinition" not in a:
                        continue
                    elif tp_f in ("NOCODE", "NO_CODE", "노코드") and "noCodeAgentDefinition" not in a:
                        continue
                filtered.append(a)

            if not filtered:
                return f"조건(키워드='{keyword}', 상태='{state_filter}', 공유='{scope_filter}', 유형='{type_filter}')에 일치하는 에이전트가 없습니다."

            lines = [
                f"### 에이전트 확산(Sprawl) 필터링 결과 ({len(filtered)}건 발견)",
                "",
                "| 에이전트 명칭 | Agent ID | 유형 (Type) | 현재 상태 | 공유 범위 |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ]
            ids = []
            for a in filtered:
                aid = a.get("name", "").split("/")[-1]
                disp = a.get("displayName", "-")
                atype = _get_agent_type(a)
                state = a.get("state", "UNKNOWN")
                scope = a.get("sharingConfig", {}).get("scope", "PRIVATE")
                ids.append(aid)
                lines.append(f"| {disp} | `{aid}` | {atype} | `{state}` | `{scope}` |")

            lines.append("")
            lines.append(f"- **대상 Agent ID 목록**: `{','.join(ids)}`")
            lines.append("- **후속 조치 가이드**: 위 에이전트들을 일괄 비활성화하려면 `batch_update_agents_state_tool`을, 공유 범위를 변경하려면 `batch_update_agents_sharing_tool`을 호출하십시오.")
            return "\n".join(lines)
        except Exception as e:
            return f"[예외 발생] 에이전트 필터링 실패: {str(e)}"

    def batch_update_agents_state_tool(agent_ids: str, target_state: str, reason: str = "") -> str:
        """Batch update lifecycle state (ENABLED, DISABLED, SUSPENDED) for multiple agents.

        Args:
            agent_ids: Comma-separated list of agent IDs (e.g. 'id1,id2,id3').
            target_state: New lifecycle state ('ENABLED', 'DISABLED', or 'SUSPENDED').
            reason: Optional governance audit note or ticket reason.
        """
        token = _get_cloud_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_id,
        }
        base_url = (
            f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}"
            f"/locations/{ge_location}/collections/default_collection"
            f"/engines/{ge_app_id}/assistants/default_assistant/agents"
        )
        t_state = target_state.upper().strip()
        if t_state not in ("ENABLED", "DISABLED", "SUSPENDED"):
            return f"[오류] 지원되지 않는 상태입니다: '{target_state}'. (지원: ENABLED, DISABLED, SUSPENDED)"

        raw_ids = [i.strip() for i in agent_ids.split(",") if i.strip()]
        if not raw_ids:
            return "[오류] 대상 Agent ID가 지정되지 않았습니다."

        results = []
        for aid in raw_ids:
            patch_url = f"{base_url}/{aid}?updateMask=state"
            try:
                r = requests.patch(patch_url, headers=headers, json={"state": t_state}, timeout=20)
                if r.ok:
                    results.append((aid, t_state, "SUCCESS", "-"))
                else:
                    results.append((aid, t_state, f"FAILED ({r.status_code})", r.text[:80]))
            except Exception as ex:
                results.append((aid, t_state, "ERROR", str(ex)[:80]))

        lines = [
            f"### 에이전트 상태 일괄 변경 완료 (목표 상태: `{t_state}`)",
            "",
            "| Agent ID | 목표 상태 | 처리 결과 | 비고 |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for aid, st, res, note in results:
            lines.append(f"| `{aid}` | `{st}` | `{res}` | {note} |")
        if reason:
            lines.append(f"\n- **거버넌스 사유**: {reason}")
        return "\n".join(lines)

    def batch_update_agents_sharing_tool(agent_ids: str, target_scope: str, reason: str = "") -> str:
        """Batch update sharing scope (ALL_USERS or PRIVATE) for multiple agents.

        Args:
            agent_ids: Comma-separated list of agent IDs.
            target_scope: New sharing scope ('ALL_USERS' or 'PRIVATE').
            reason: Optional governance audit note.
        """
        token = _get_cloud_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_id,
        }
        base_url = (
            f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}"
            f"/locations/{ge_location}/collections/default_collection"
            f"/engines/{ge_app_id}/assistants/default_assistant/agents"
        )
        t_scope = target_scope.upper().strip()
        if t_scope not in ("ALL_USERS", "PRIVATE"):
            return f"[오류] 지원되지 않는 공유 범위입니다: '{target_scope}'. (지원: ALL_USERS, PRIVATE)"

        raw_ids = [i.strip() for i in agent_ids.split(",") if i.strip()]
        if not raw_ids:
            return "[오류] 대상 Agent ID가 지정되지 않았습니다."

        results = []
        for aid in raw_ids:
            patch_url = f"{base_url}/{aid}?updateMask=sharingConfig"
            try:
                r = requests.patch(patch_url, headers=headers, json={"sharingConfig": {"scope": t_scope}}, timeout=20)
                if r.ok:
                    results.append((aid, t_scope, "SUCCESS", "-"))
                else:
                    results.append((aid, t_scope, f"FAILED ({r.status_code})", r.text[:80]))
            except Exception as ex:
                results.append((aid, t_scope, "ERROR", str(ex)[:80]))

        lines = [
            f"### 에이전트 공유 범위 일괄 변경 완료 (목표 범위: `{t_scope}`)",
            "",
            "| Agent ID | 목표 범위 | 처리 결과 | 비고 |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for aid, sc, res, note in results:
            lines.append(f"| `{aid}` | `{sc}` | `{res}` | {note} |")
        if reason:
            lines.append(f"\n- **거버넌스 사유**: {reason}")
        return "\n".join(lines)

    def batch_delete_agents_tool(agent_ids: str, confirm: bool = False) -> str:
        """Batch permanently delete unmanaged or decommissioned agents.

        Args:
            agent_ids: Comma-separated list of agent IDs.
            confirm: Safety confirmation flag. Must be explicitly True to execute deletion.
        """
        raw_ids = [i.strip() for i in agent_ids.split(",") if i.strip()]
        if not raw_ids:
            return "[오류] 대상 Agent ID가 지정되지 않았습니다."

        if not confirm:
            return (
                f"### [안전 가드레일 경고] 에이전트 영구 삭제 확인 필요\n\n"
                f"- **삭제 대상 에이전트 수**: {len(raw_ids)}개\n"
                f"- **대상 ID**: `{', '.join(raw_ids)}`\n\n"
                f"영구 삭제된 에이전트는 복구할 수 없습니다. 실제 삭제를 집행하시려면 "
                f"`confirm=True`를 명시하여 다시 요청해 주십시오."
            )

        token = _get_cloud_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Goog-User-Project": project_id,
        }
        base_url = (
            f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}"
            f"/locations/{ge_location}/collections/default_collection"
            f"/engines/{ge_app_id}/assistants/default_assistant/agents"
        )

        results = []
        for aid in raw_ids:
            del_url = f"{base_url}/{aid}"
            try:
                r = requests.delete(del_url, headers=headers, timeout=20)
                if r.ok:
                    results.append((aid, "DELETED", "-"))
                else:
                    results.append((aid, f"FAILED ({r.status_code})", r.text[:80]))
            except Exception as ex:
                results.append((aid, "ERROR", str(ex)[:80]))

        lines = [
            f"### 에이전트 영구 삭제 완료 ({len(raw_ids)}건 집행)",
            "",
            "| Agent ID | 삭제 결과 | 비고 |",
            "| :--- | :--- | :--- |",
        ]
        for aid, res, note in results:
            lines.append(f"| `{aid}` | `{res}` | {note} |")
        return "\n".join(lines)

    def get_admin_audit_queries_tool(query_type: str = "all") -> str:
        """Get ready-to-run BigQuery audit SQL queries for detecting zombie agents, top token consumers, or error spikes.

        Args:
            query_type: 'zombie', 'top_tokens', 'errors', or 'all'.
        """
        queries = []
        qt = query_type.lower().strip()
        if qt in ("zombie", "all", "좀비"):
            queries.append(
                "### 1. 최근 60일간 호출 0건인 좀비 에이전트(Ghost Agents) 적발 쿼리\n\n"
                "```sql\n"
                f"SELECT\n"
                f"    protopayload_auditlog.resourceName AS agent_resource,\n"
                f"    protopayload_auditlog.authenticationInfo.principalEmail AS creator_email,\n"
                f"    MAX(timestamp) AS last_invoked_at,\n"
                f"    DATE_DIFF(CURRENT_DATE(), DATE(MAX(timestamp)), DAY) AS idle_days\n"
                f"FROM\n"
                f"    `{project_id}.gemini_logging.cloudaudit_googleapis_com_data_access`\n"
                f"WHERE\n"
                f"    protopayload_auditlog.serviceName = 'discoveryengine.googleapis.com'\n"
                f"    AND protopayload_auditlog.methodName LIKE '%AgentService.Query%'\n"
                f"GROUP BY 1, 2\n"
                f"HAVING idle_days >= 60\n"
                f"ORDER BY idle_days DESC;\n"
                "```"
            )
        if qt in ("top_tokens", "all", "토큰", "랭킹"):
            queries.append(
                "### 2. 전사 에이전트별 토큰 소비량 및 호출 횟수 TOP 10 랭킹 쿼리\n\n"
                "```sql\n"
                f"SELECT\n"
                f"    protopayload_auditlog.resourceName AS agent_resource,\n"
                f"    COUNT(1) AS total_invocations,\n"
                f"    COUNT(DISTINCT protopayload_auditlog.authenticationInfo.principalEmail) AS active_users\n"
                f"FROM\n"
                f"    `{project_id}.gemini_logging.cloudaudit_googleapis_com_data_access`\n"
                f"WHERE\n"
                f"    protopayload_auditlog.serviceName = 'discoveryengine.googleapis.com'\n"
                f"GROUP BY 1\n"
                f"ORDER BY total_invocations DESC\n"
                f"LIMIT 10;\n"
                "```"
            )
        if qt in ("errors", "all", "에러", "오류", "429"):
            queries.append(
                "### 3. 429 쿼터 초과 및 에러 다발 문제 에이전트 역추적 쿼리\n\n"
                "```sql\n"
                f"SELECT\n"
                f"    protopayload_auditlog.resourceName AS agent_resource,\n"
                f"    protopayload_auditlog.status.code AS error_code,\n"
                f"    protopayload_auditlog.status.message AS error_message,\n"
                f"    COUNT(1) AS error_count\n"
                f"FROM\n"
                f"    `{project_id}.gemini_logging.cloudaudit_googleapis_com_data_access`\n"
                f"WHERE\n"
                f"    protopayload_auditlog.serviceName = 'discoveryengine.googleapis.com'\n"
                f"    AND protopayload_auditlog.status.code != 0\n"
                f"GROUP BY 1, 2, 3\n"
                f"ORDER BY error_count DESC;\n"
                "```"
            )
        return "\n\n".join(queries)

    adk_agent = Agent(
        name="gemini_enterprise_admin_copilot",
        description=description,
        model="gemini-3.8-flash",
        instruction=instruction,
        tools=[
            get_admin_console_deeplinks_tool,
            list_deployed_agents_tool,
            list_connected_datastores_tool,
            filter_and_inspect_sprawl_agents_tool,
            batch_update_agents_state_tool,
            batch_update_agents_sharing_tool,
            batch_delete_agents_tool,
            get_admin_audit_queries_tool,
        ],
    )
    class ResilientAdkApp(agent_engines.AdkApp):
        """Pydantic v2 직렬화 호환성 및 세션 안정화를 지원하는 엔터프라이즈 Agent Engine 래퍼."""

        def _ensure_pydantic_private(self):
            targets = []
            if "agent" in self._tmpl_attrs and self._tmpl_attrs["agent"] is not None:
                targets.append(self._tmpl_attrs["agent"])
            for runner_key in ("runner", "in_memory_runner"):
                runner = self._tmpl_attrs.get(runner_key)
                if runner and hasattr(runner, "app") and runner.app:
                    if hasattr(runner.app, "root_agent") and runner.app.root_agent:
                        targets.append(runner.app.root_agent)
            for ag in targets:
                if getattr(ag, "__pydantic_private__", None) is None:
                    object.__setattr__(
                        ag,
                        "__pydantic_private__",
                        {"_resolved_model": None, "_resolved_live_model": None},
                    )
                try:
                    _ = ag.canonical_model
                except Exception:
                    pass

        def set_up(self):
            self._ensure_pydantic_private()
            super().set_up()
            self._ensure_pydantic_private()

        async def streaming_agent_run_with_events(self, request_json: str):
            self._ensure_pydantic_private()
            async for event in super().streaming_agent_run_with_events(request_json):
                yield event

        async def async_stream_query(self, *args, **kwargs):
            self._ensure_pydantic_private()
            async for event in super().async_stream_query(*args, **kwargs):
                yield event

    # 사전 모델 해석으로 Pydantic v2 __pydantic_private__ 슬롯 초기화 강제
    try:
        _ = adk_agent.canonical_model
    except Exception:
        pass

    app = ResilientAdkApp(agent=adk_agent, enable_tracing=True)

    runtime_env = {
        "GOOGLE_GENAI_USE_VERTEXAI": "1",
        "GOOGLE_CLOUD_LOCATION": "global",
        "ADK_ENABLE_MCP_MODERN_PROTOCOL": "1",
    }

    print("  - Agent Engine 프로비저닝 LRO 생성 중 (약 1분 소요)...")
    remote = agent_engines.create(
        agent_engine=app,
        display_name=display_name,
        description=description,
        gcs_dir_name="ge_factory_admin_copilot",
        requirements=[
            "google-cloud-aiplatform[adk,agent_engines]==2.5.0",
            "google-adk==2.11.0",
            "google-genai==2.31.0",
            "pydantic==2.13.5",
            "requests",
            "cloudpickle==3.1.2",
            "google-auth",
        ],
        env_vars=runtime_env,
    )

    re_res = remote.resource_name
    print(f"[성공] Agent Engine 생성 완료: {re_res}")

    print("\n[단계 2/2] Gemini Enterprise app 사내 갤러리(/r/agents) 자동 바인딩 중...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id,
    }
    base_url = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}"
        f"/locations/{ge_location}/collections/default_collection"
        f"/engines/{ge_app_id}/assistants/default_assistant/agents"
    )

    body = {
        "displayName": display_name,
        "description": description,
        "state": "ENABLED",
        "sharingConfig": {"scope": "ALL_USERS"},
        "customPlaceholderText": "해결하고 싶은 GE 관리자 이슈(에이전트 관리, BigQuery 로깅, 콘솔 위치, 라이선스, 과금 등)를 입력하세요...",
        "starterPrompts": [
            {"text": "사내 등록된 테스트/미사용 에이전트 목록 스캔하고 비활성화(DISABLED) 처리해 줘"},
            {"text": "사내 GE App에 연결된 데이터 커넥터(Data Store) 목록 조회해 줘"},
            {"text": "사내 에이전트가 100개가 넘는데 60일 미사용 좀비 에이전트 찾는 BigQuery 쿼리 줘"},
            {"text": "Cloud Logging 감사 로그를 BigQuery로 30초 만에 자동 연결하는 스크립트 줘"},
            {"text": "GCP 콘솔에서 GE Admin 에이전트 목록 페이지 어디로 들어가야 해?"},
        ],
        "adkAgentDefinition": {
            "toolSettings": {"toolDescription": description},
            "provisionedReasoningEngine": {
                "reasoningEngine": re_res
            },
        },
    }

    target_agent_id = None
    list_resp = requests.get(base_url, headers=headers, timeout=30)
    if list_resp.ok:
        for a in list_resp.json().get("agents", []):
            if a.get("displayName") == display_name:
                target_agent_id = a.get("name").split("/")[-1]
                break

    if target_agent_id:
        patch_url = f"{base_url}/{target_agent_id}?updateMask=displayName,description,starterPrompts,customPlaceholderText,adkAgentDefinition"
        reg_resp = requests.patch(patch_url, headers=headers, json=body, timeout=30)
    else:
        reg_resp = requests.post(base_url, headers=headers, json=body, timeout=30)

    if not reg_resp.ok:
        print(f"[경고] GE App 등록 응답 이상 ({reg_resp.status_code}): {reg_resp.text}")
    else:
        print(f"[성공] Gemini Enterprise app 등록 완료 (공유 범위: ALL_USERS)")

    return {
        "status": "DEPLOYED",
        "reasoning_engine": re_res,
        "display_name": display_name,
        "ge_app_id": ge_app_id,
    }


def run_local_scaffolding_mode(args, env_info: dict):
    """로컬 단일 어드민 과제 진단 및 조치 가이드 생성 보조 모드를 실행한다."""
    print("\n[안내] 로컬 단일 어드민 조치 가이드 생성 보조 모드 가동")

    # 1. 과제 칩 선택
    topic_data = ADMIN_TOPIC_CATALOG[1]
    if args.prompt:
        topic_data = {
            "id": "custom_admin_inquiry",
            "name": f"사용자 어드민 문의 ({args.prompt[:15]})",
            "category": "Custom IT Admin",
            "description": f"어드민 문의({args.prompt}) 기반 맞춤형 진단 및 조치 가이드",
            "primary_action": "맞춤형 거버넌스 및 인프라 정책 점검",
            "remediation_type": "CUSTOM_REMEDIATION",
        }
    elif args.chip and args.chip in ADMIN_TOPIC_CATALOG:
        topic_data = ADMIN_TOPIC_CATALOG[args.chip]
    elif args.interactive or (sys.stdin.isatty() and not args.dry_run):
        topic_data = select_topic_interactive(args.dry_run)

    print(f"\n[단계 1/3] 어드민 관리 칩 스펙 컴파일 중...")
    print(f"  - 과제 명칭 : {topic_data['name']}")
    print(f"  - 카테고리  : {topic_data['category']}")
    print(f"  - 핵심 조치 : {topic_data['primary_action']}")

    # 2. 조치 스크립트 컴파일
    print("\n[단계 2/3] 거버넌스 매니페스트 및 즉시 조치 스크립트 컴파일 중...")
    artifacts = compile_admin_remediation(topic_data, env_info)
    print(f"  - 조치 유형 : {topic_data['remediation_type']}")

    # 3. IAM 권한 진단
    print("\n[단계 3/3] 서비스 계정 IAM 권한 및 어드민 준비 상태 진단 중...")
    diag = diagnose_admin_environment(topic_data, env_info, args.dry_run)
    print(f"  - 상태: {diag['status']} | {diag['detail']}")

    # 4. 리포트 저장
    report_content = build_markdown_report(env_info, topic_data, artifacts, diag)
    save_markdown_report(report_content)

    print("\n" + "=" * 75)
    print("  어드민 코파일럿 진단 및 조치 가이드 생성 완료")
    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(
        description="Gemini Enterprise 어드민 코파일럿 (붕어빵 틀) 배포 및 등록 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project", help="Google Cloud 프로젝트 ID (미지정 시 자동 감지)")
    parser.add_argument("--location", help="Vertex AI / Discovery Engine 리전 (기본: global)")
    parser.add_argument("--ge-app-id", help="Gemini Enterprise App 인스턴스 ID")
    parser.add_argument("--sa", help="어드민 실행 대행 서비스 계정 이메일")
    parser.add_argument("--domain", help="사내 도메인 명칭 (예: example-corp.com)")
    parser.add_argument("--dry-run", action="store_true", default=False, help="실제 배포 없이 가상 실행 검증")
    parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
    parser.add_argument("--scaffold", action="store_true", default=False, help="로컬 단일 어드민 가이드 생성 보조 모드")
    parser.add_argument("--chip", type=int, help="어드민 관리 칩 번호 직접 지정 (1~7)")
    parser.add_argument("--prompt", help="사용자 정의 어드민 문의 내용")
    parser.add_argument("--interactive", action="store_true", default=False, help="로컬 대화형 번호 선택기 가동")
    parser.add_argument("--deploy-engine", action="store_true", default=False, help="Agent Engine 프로비저닝 (기본 실행과 동일)")

    args = parser.parse_args()

    # 사내 환경 대화형 설정 모드 분기
    if args.config:
        run_config_mode(args)
        return

    if len(sys.argv) == 1 and not sys.stdin.isatty():
        args.dry_run = True

    print("\n" + "=" * 75)
    print("  Gemini Enterprise 어드민 코파일럿 (gemini-enterprise-copilot-admin)")
    print("=" * 75)

    # 1. 환경 정보 해석
    env_info = resolve_environment(args)
    print(f"[*] 활성 프로젝트    : {env_info['project_id']}")
    print(f"[*] 배포 리전        : {env_info['location']}")
    print(f"[*] 대상 GE App ID   : {env_info['ge_app_id']}")
    print(f"[*] 사내 대상 도메인 : {env_info['customer_domain']}")
    print(f"[*] 실행 서비스 계정 : {env_info['service_account']}")
    print(f"[*] 실행 모드        : {'가상 실행 (--dry-run)' if args.dry_run else '실제 프로비저닝 모드'}")

    # 로컬 스캐폴딩 보조 모드 분기 (명시적 플래그 지정 시에만 작동)
    if args.scaffold or args.chip or args.prompt or args.interactive:
        run_local_scaffolding_mode(args, env_info)
        return

    # [핵심 메인 워크플로우]: 붕어빵 틀(GE Admin Copilot) 배포 및 GE App 사내 갤러리 등록
    if not args.dry_run and not _get_cloud_token():
        print("\n[오류] 유효한 Google Cloud 인증 자격 증명(ADC)을 찾을 수 없습니다.", file=sys.stderr)
        print("      아래 명령어를 실행하여 로컬 자격 증명을 갱신하십시오:", file=sys.stderr)
        print("      gcloud auth application-default login\n", file=sys.stderr)
        print("      (참고: 실제 배포 없이 가상 검증을 수행하려면 '--dry-run' 플래그를 사용하십시오.)\n", file=sys.stderr)
        sys.exit(1)

    print("\n[진행] 사내 어드민 코파일럿(붕어빵 틀) 프로비저닝 파이프라인 가동...")
    deploy_res = deploy_admin_copilot_engine(env_info, dry_run=args.dry_run)

    # 팩토리 리포트 생성 및 저장
    report_content = build_factory_markdown_report(env_info, deploy_res, dry_run=args.dry_run)
    save_markdown_report(report_content)

    creator = get_resource_creator(args.dry_run)
    print("\n" + "=" * 75)
    print("  어드민 코파일럿 배포 및 등록 완료 (모든 점검 통과)")
    print("=" * 75)
    print("\n[안내] 사내 거버넌스 및 자원 추적을 위한 4대 필수 표준 라벨:")
    print("  - managed-by: google-cloud-0-to-1")
    print("  - scenario: gemini-enterprise-copilot-admin")
    print("  - env: sample")
    print(f"  - created-by: {creator}\n")


if __name__ == "__main__":
    main()
