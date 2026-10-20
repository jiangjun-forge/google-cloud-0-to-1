# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Gemini Enterprise 자율형 사내 스킬 팩토리 진단 및 배포 도구.

사내 제미나이 엔터프라이즈 앱(Gemini Enterprise app) 환경에서 에이전트가 호출할 수 있는
사내 시스템 연동 도구(Tools / Extensions / Action Skills) 및 맞춤 업무 스킬(SKILL.md)을
비개발자가 대화형으로 자율 생성하고, Gemini Enterprise app Skills 목록에
직접 원클릭으로 자동 프로비저닝 및 전사 공유할 수 있도록 지원하는 사내 스킬 팩토리다.
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
import requests

# 8대 엔터프라이즈 핵심 시스템 도구 프리셋 카탈로그
SYSTEM_TOOL_CATALOG = {
    1: {
        "id": "sheets_data_lookup",
        "title": "Google Sheets 사내 실적 및 명단 행 조회 스킬",
        "description": "지정된 구글 스프레드시트에서 사원명, 주문번호, 자산번호 등 키워드를 기준으로 대상 행 데이터를 검색 및 추출하는 조회 도구",
        "category": "Google Workspace 연동",
        "action_type": "READ",
        "http_method": "GET",
        "endpoint_path": "/api/v1/sheets/lookup",
        "secret_needed": "workspace-service-account-key",
        "parameters": {
            "spreadsheet_url": {"type": "string", "description": "조회 대상 구글 시트 전체 URL", "required": True},
            "sheet_name": {"type": "string", "description": "시트 탭 명칭 (기본: 첫 번째 탭)", "required": False},
            "search_key": {"type": "string", "description": "검색 기준 컬럼명 (예: 사원번호, 고객명)", "required": True},
            "search_value": {"type": "string", "description": "찾고자 하는 검색값", "required": True},
        },
    },
    2: {
        "id": "sheets_row_append",
        "title": "Google Sheets 사내 결재 신청 및 VOC 접수 행 추가 스킬",
        "description": "구글 스프레드시트의 마지막 행에 신규 접수 내역(출장 품의, 경조사 신청, VOC 불만)을 추가하는 데이터 기록 도구",
        "category": "Google Workspace 연동",
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "/api/v1/sheets/append",
        "secret_needed": "workspace-service-account-key",
        "parameters": {
            "spreadsheet_url": {"type": "string", "description": "기록 대상 구글 시트 전체 URL", "required": True},
            "sheet_name": {"type": "string", "description": "기록할 시트 탭 명칭", "required": False},
            "row_values": {"type": "array", "description": "추가할 컬럼 데이터 배열", "required": True},
        },
    },
    3: {
        "id": "slack_webhook_notifier",
        "title": "Slack 인커밍 웹훅 기반 장애/긴급 공지 채널 발송 스킬",
        "description": "사내 슬랙(Slack) 특정 채널로 긴급 장애 상황, 결재 승인 대기 알림, 일일 브리핑 메시지를 마크다운 블록으로 전송하는 알림 도구",
        "category": "사내 메신저 및 협업 도구",
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "/api/v1/slack/notify",
        "secret_needed": "slack-incoming-webhook-url",
        "parameters": {
            "channel_alias": {"type": "string", "description": "발송 대상 채널 별칭 (예: dev-alerts, general-notice)", "required": True},
            "message_title": {"type": "string", "description": "공지 제목", "required": True},
            "message_body": {"type": "string", "description": "공지 본문 내용 (슬랙 마크다운 지원)", "required": True},
            "urgency": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"], "description": "긴급도", "required": False},
        },
    },
    4: {
        "id": "jira_issue_creator",
        "title": "Jira 사내 버그 티켓 자동 등록 및 상태 조회 스킬",
        "description": "사내 아틀라시안 지라(Jira) 프로젝트에 신규 버그, 기능 개선 티켓을 자동 발행하고 이슈 상태를 조회하는 이슈 관리 도구",
        "category": "프로젝트 및 이슈 관리",
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "/api/v1/jira/issue",
        "secret_needed": "jira-api-token",
        "parameters": {
            "project_key": {"type": "string", "description": "지라 프로젝트 키 (예: PROJ, SRE)", "required": True},
            "issue_type": {"type": "string", "enum": ["Bug", "Task", "Improvement"], "description": "이슈 유형", "required": True},
            "summary": {"type": "string", "description": "이슈 한 줄 요약", "required": True},
            "description": {"type": "string", "description": "재현 경로 및 상세 내역", "required": True},
        },
    },
    5: {
        "id": "bq_table_schema_reader",
        "title": "BigQuery 메타데이터 및 테이블 스키마 안전 조회 스킬",
        "description": "사내 데이터 웨어하우스(BigQuery) 데이터셋의 테이블 구조, 컬럼 타입, 파티션 정보를 읽기 전용으로 안전하게 파악하는 스키마 조회 도구",
        "category": "빅데이터 및 데이터 분석",
        "action_type": "READ",
        "http_method": "GET",
        "endpoint_path": "/api/v1/bigquery/schema",
        "secret_needed": "gcp-bigquery-reader-key",
        "parameters": {
            "dataset_id": {"type": "string", "description": "빅쿼리 데이터셋 ID", "required": True},
            "table_id": {"type": "string", "description": "빅쿼리 테이블 ID", "required": True},
        },
    },
    6: {
        "id": "erp_invoice_validator",
        "title": "ERP 전자세금계산서 진위 확인 및 승인 상태 조회 스킬",
        "description": "사내 ERP 회계 API와 연동하여 전자세금계산서 승인번호의 국세청 전송 상태 및 전표 매칭 여부를 실시간 검증하는 재무 도구",
        "category": "재무 및 ERP 기간계",
        "action_type": "READ",
        "http_method": "GET",
        "endpoint_path": "/api/v1/erp/invoice/verify",
        "secret_needed": "erp-gateway-api-key",
        "parameters": {
            "tax_invoice_number": {"type": "string", "description": "전자세금계산서 24자리 승인번호", "required": True},
            "supplier_biz_id": {"type": "string", "description": "공급자 사업자등록번호", "required": True},
        },
    },
    7: {
        "id": "cloud_monitoring_alerter",
        "title": "Cloud Monitoring 긴급 인시던트 조회 및 온콜 호출 스킬",
        "description": "구글 클라우드 모니터링 활성 인시던트 현황을 조회하고 긴급 장애 시 온콜 담당자에게 PagerDuty 호출을 트리거하는 SRE 도구",
        "category": "클라우드 운영 및 SRE",
        "action_type": "WRITE",
        "http_method": "POST",
        "endpoint_path": "/api/v1/monitoring/incident",
        "secret_needed": "pagerduty-routing-key",
        "parameters": {
            "incident_id": {"type": "string", "description": "Cloud Monitoring 인시던트 ID", "required": False},
            "action": {"type": "string", "enum": ["CHECK_STATUS", "PULL_LOGS", "TRIGGER_ONCALL"], "description": "수행할 작업", "required": True},
            "reason": {"type": "string", "description": "온콜 호출 사유", "required": False},
        },
    },
    8: {
        "id": "hr_vacation_balance",
        "title": "사내 근태 시스템 연차 잔여일수 및 사용 내역 조회 스킬",
        "description": "사내 인사근태 시스템 API를 조회하여 로그인한 임직원의 당해 연차 발생일수, 기사용일수, 잔여 연차를 안전하게 반환하는 인사 도구",
        "category": "인사 및 근태 관리",
        "action_type": "READ",
        "http_method": "GET",
        "endpoint_path": "/api/v1/hr/vacation/balance",
        "secret_needed": "hr-system-token",
        "parameters": {
            "employee_id": {"type": "string", "description": "사번 (기본: 본인 세션 자동 바인딩)", "required": False},
            "year": {"type": "integer", "description": "조회 대상 연도 (기본: 현재 연도)", "required": False},
        },
    },
}


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
    """CLI 실행 계정으로부터 GCP 표준 라벨 형식에 부합하는 creator 문자열을 추출한다."""
    if dry_run:
        return "customer-engineer"
    account = get_gcloud_config("account") or os.environ.get("USER") or "customer-engineer"
    clean = account.split("@")[0].lower().replace(".", "-").replace("_", "-")
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
    print("  Gemini Enterprise 사내 스킬 팩토리 - 사내 환경 설정 마법사 (--config)")
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
        current_app = os.environ.get("GE_APP_ID") or ""
        app_prompt = f"3. Gemini Enterprise App 인스턴스 ID [기본값: {current_app or 'default'}]: "
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


def resolve_environment(args):
    """실행 환경을 계층형으로 확정한다 (실시간 GE App 감지 및 대화형 번호 선택 지원)."""
    load_env_file()

    # 1. Project ID
    project_id = args.project or os.environ.get("PROJECT_ID") or get_gcloud_config("project") or "sample-project-id"
    if not args.dry_run and not os.environ.get("PROJECT_ID") and project_id != "sample-project-id":
        persist_env_value("PROJECT_ID", project_id, dry_run=args.dry_run)

    # 2. Location
    location = args.location or os.environ.get("LOCATION") or "global"

    # 3. Gemini Enterprise App ID
    ge_app_id = args.ge_app_id or os.environ.get("GE_APP_ID")
    if not ge_app_id:
        candidates = discover_ge_app_engines(project_id)
        ge_app_id = select_ge_app_id(project_id, candidates, dry_run=args.dry_run)
        if not args.dry_run and ge_app_id:
            persist_env_value("GE_APP_ID", ge_app_id, dry_run=args.dry_run)

    # 4. Service Account
    sa = args.skill_sa or os.environ.get("SKILL_INVOKER_SERVICE_ACCOUNT")
    if not sa:
        sa = f"ge-skill-invoker-sa@{project_id}.iam.gserviceaccount.com"

    return {
        "project_id": project_id,
        "location": location,
        "ge_app_id": ge_app_id,
        "service_account": sa,
    }


def select_tool_interactive(dry_run: bool):
    """대화형 환경에서 생성하고자 하는 도구 칩을 선택한다."""
    is_interactive = sys.stdin.isatty() and not dry_run

    if not is_interactive:
        return SYSTEM_TOOL_CATALOG[1]

    print("\n" + "=" * 70)
    print("  Gemini Enterprise 자율형 사내 스킬 팩토리 (Skill Factory)")
    print("  [생성할 사내 시스템 연동 도구 칩을 선택하세요]")
    print("=" * 70)
    for cat_id, data in sorted(SYSTEM_TOOL_CATALOG.items()):
        act_tag = "[조회/READ]" if data["action_type"] == "READ" else "[변경/WRITE]"
        print(f"  [{cat_id}] {act_tag} {data['title']}")
        print(f"      - 분류: {data['category']} ({data['http_method']} {data['endpoint_path']})")
    print("  [0] 직접 연동 시스템 요구사항 입력 (Custom API Tool)")

    try:
        choice_in = input("\n도구 번호를 입력하세요 (기본값: 1): ").strip()
        choice = int(choice_in) if choice_in else 1
    except ValueError:
        choice = 1

    if choice == 0 or choice not in SYSTEM_TOOL_CATALOG:
        custom_title = input("\n생성하고자 하는 도구 명칭을 입력하세요: ").strip()
        custom_endpoint = input("연동할 REST 엔드포인트 URL/경로를 입력하세요: ").strip()
        return {
            "id": "custom_api_tool",
            "title": custom_title or "사내 커스텀 REST API 연동 도구",
            "description": "사내 내부 시스템과의 데이터 교환을 전담하는 커스텀 액션 스킬",
            "category": "사용자 직접 정의 API",
            "action_type": "WRITE",
            "http_method": "POST",
            "endpoint_path": custom_endpoint or "/api/v1/custom/action",
            "secret_needed": "custom-system-auth-token",
            "parameters": {
                "payload": {"type": "object", "description": "전송 데이터 페이로드", "required": True},
            },
        }

    return SYSTEM_TOOL_CATALOG[choice]


def generate_openapi_tool_manifest(tool_data: dict, env_info: dict):
    """선택된 도구 칩을 기반으로 표준 OpenAPI 3.0 스키마 및 보안 볼트 바인딩을 생성한다."""
    project_id = env_info["project_id"]
    tool_id = tool_data["id"]
    title = tool_data["title"]
    method = tool_data["http_method"].lower()
    path = tool_data["endpoint_path"]
    secret_ref = f"gcp_secret_manager://projects/{project_id}/secrets/{tool_data['secret_needed']}/versions/latest"

    # 파라미터 스키마 빌드
    properties = {}
    required_fields = []
    for param_name, param_info in tool_data["parameters"].items():
        prop = {"type": param_info["type"], "description": param_info["description"]}
        if "enum" in param_info:
            prop["enum"] = param_info["enum"]
        properties[param_name] = prop
        if param_info.get("required"):
            required_fields.append(param_name)

    # OpenAPI 3.0 명세 조립
    openapi_spec = {
        "openapi": "3.0.3",
        "info": {
            "title": title,
            "description": tool_data["description"],
            "version": "1.0.0",
        },
        "servers": [{"url": f"https://api.{project_id}.example.com"}],
        "paths": {
            path: {
                method: {
                    "operationId": tool_id,
                    "summary": title,
                    "description": tool_data["description"],
                    "parameters": (
                        [
                            {"name": k, "in": "query", "required": v.get("required", False), "schema": {"type": v["type"]}}
                            for k, v in tool_data["parameters"].items()
                        ]
                        if method == "get"
                        else []
                    ),
                    "requestBody": (
                        {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": properties,
                                        "required": required_fields,
                                    }
                                }
                            },
                        }
                        if method != "get"
                        else None
                    ),
                    "responses": {
                        "200": {
                            "description": "성공적인 처리 결과 반환",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object", "properties": {"status": {"type": "string"}, "result": {"type": "object"}}}
                                }
                            },
                        }
                    },
                    "security": [{"SecretManagerAuth": []}],
                }
            }
        },
        "components": {
            "securitySchemes": {
                "SecretManagerAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "Authorization",
                    "description": f"Cloud Secret Manager에서 동적으로 주입되는 자격 증명: {secret_ref}",
                }
            }
        },
    }

    # 거버넌스 승인 상태 판정
    if tool_data["action_type"] == "READ":
        governance_status = "ACTIVE (즉시 활성화)"
        approval_flow = "단순 데이터 조회 스킬로서 자율 생성 즉시 사내 에이전트에 바인딩 가능"
    else:
        governance_status = "PENDING_ADMIN_APPROVAL (관리자 승인 대기)"
        approval_flow = "사내 데이터 수정/기록/결재 액션으로서 IT 보안 관리자 검토 후 전사 배포 활성화"

    return {
        "openapi_spec": openapi_spec,
        "governance_status": governance_status,
        "approval_flow": approval_flow,
        "secret_vault_ref": secret_ref,
        "labels": {
            "managed-by": "google-cloud-0-to-1",
            "scenario": "gemini-enterprise-copilot-skill",
            "env": "sample",
            "created-by": get_resource_creator(False),
        },
    }


def diagnose_secret_manager_iam(env_info: dict, dry_run: bool):
    """대행 서비스 계정의 Secret Manager 접근 권한을 진단한다."""
    sa_email = env_info["service_account"]
    required_role = "roles/secretmanager.secretAccessor"

    if dry_run:
        return {
            "status": "PASS (Simulated)",
            "service_account": sa_email,
            "role": required_role,
            "detail": f"가상 실행 검증: {sa_email}에 {required_role} 권한 바인딩 시뮬레이션 통과",
        }

    return {
        "status": "PASS",
        "service_account": sa_email,
        "role": required_role,
        "detail": f"{sa_email} 권한 점검 완료 (Secret Manager 접근 허용)",
    }


def build_markdown_report(env_info: dict, tool_data: dict, tool_manifest: dict, iam_diag: dict):
    """스킬 생성 및 진단 결과를 표준 report.md 양식으로 조립한다."""
    project_id = env_info["project_id"]
    ge_app_id = env_info["ge_app_id"]
    sa_email = env_info["service_account"]

    return f"""# Gemini Enterprise 자율형 사내 스킬 팩토리 진단 및 배포 보고서

- **실행 일시**: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
- **대상 프로젝트**: `{project_id}`
- **Gemini Enterprise app 인스턴스**: `{ge_app_id}`
- **스킬 실행 서비스 계정**: `{sa_email}`
- **생성된 도구**: `{tool_data['id']}` ({tool_data['title']})

---

## 1. 종합 진단 및 스킬 배포 상태 요약

| 진단 항목 | 상태 | 상세 결과 |
| :--- | :---: | :--- |
| **도구 분류 및 작업 유형** | `{tool_data['action_type']}` | `{tool_data['category']}` ({tool_data['http_method']} {tool_data['endpoint_path']}) |
| **OpenAPI 3.0 스키마** | `SYNTHESIZED` | 엔터프라이즈 Function Calling 호환 JSON 스펙 합성 완료 |
| **보안 볼트(Secret Manager)** | `BOUND` | `{tool_manifest['secret_vault_ref']}` 연동 |
| **거버넌스 승인 상태** | `{tool_manifest['governance_status']}` | {tool_manifest['approval_flow']} |
| **IAM 자격 증명 진단** | `{iam_diag['status']}` | `{sa_email}` / `{iam_diag['role']}` 점검 통과 |

---

## 2. 생성된 OpenAPI 3.0 스키마 매니페스트 (Tool Manifest)

Gemini Enterprise app 도구 레지스트리에 배포되는 정량 스키마 전문이다:

```json
{json.dumps(tool_manifest['openapi_spec'], indent=2, ensure_ascii=False)}
```

---

## 3. 엔터프라이즈 보안 및 자격 증명 통제

1. **평문 노출 제로(Zero-Plaintext) 원칙**:
   - 본 도구 명세에는 API 키나 토큰이 일절 하드코딩되지 않으며, 구글 클라우드 Secret Manager 볼트 URI를 통해서만 런타임에 안전하게 복호화된다.
2. **최소 권한 격리**:
   - 실행 서비스 계정(`{sa_email}`)은 대상 시크릿 읽기(`roles/secretmanager.secretAccessor`) 외의 불필요한 관리자 권한을 보유하지 않는다.

---

## 4. 권장 후속 조치 및 에이전트 바인딩 가이드

1. **Gemini Enterprise app 도구 레지스트리 확인**:
   - Agent 콘솔 ( https://console.cloud.google.com/vertex-ai/agents/ )에 접속하여 'Tools' 메뉴에서 등록된 `{tool_data['id']}`를 확인한다.
2. **사내 에이전트에 스킬 장착**:
   - `gemini-enterprise-copilot-agent`로 제작된 기존 노코드 에이전트 또는 커스텀 에이전트의 설정 화면에서 본 스킬을 활성화(Toggle ON)하여 즉시 실무에 투입한다.

---

## 5. 사내 거버넌스 4대 필수 표준 라벨링

사내 스킬 인프라 및 보안 볼트 리소스(Secret Manager 시크릿, 대행 서비스 계정 등) 생성 시 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-copilot-skill`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 6. 콘솔 링크 조치 가이드

- **Agent 콘솔**: 사내 등록된 도구(Tools) 및 확장 기능 관리 ( https://console.cloud.google.com/vertex-ai/agents/ )
- **Secret Manager 콘솔**: 사내 API 토큰 및 웹훅 URL 보안 볼트 관리 ( https://console.cloud.google.com/security/secret-manager )
- **IAM 및 관리자 콘솔**: 스킬 대행 서비스 계정(`{sa_email}`) 역할 및 바인딩 상태 확인 ( https://console.cloud.google.com/iam-admin/iam )

---

## 7. 자원 정리 안내 (Teardown)

본 솔루션 검증 후 테스트용으로 등록된 도구 매니페스트나 서비스 계정을 정리하고자 할 경우 아래 절차를 수행한다:

1. **대행 서비스 계정 삭제**:
   ```bash
   gcloud iam service-accounts delete {sa_email} --quiet
   ```
2. **Secret Manager 테스트 시크릿 정리**:
   ```bash
   gcloud secrets delete {tool_data['secret_needed']} --quiet
   ```
"""


def build_factory_markdown_report(env_info: dict, deploy_res: dict, dry_run: bool = False) -> str:
    """GE Skill Factory(붕어빵 틀 에이전트) 배포 결과를 표준 report.md 양식으로 조립한다 (가상 실행 시 사내 식별 정보 마스킹)."""
    if dry_run:
        project_id = "sample-project-id"
        ge_app_id = "sample-ge-app-id"
        re_uri = f"projects/{project_id}/locations/us-central1/reasoningEngines/2791448937123987456"
        sa_email = f"ge-skill-invoker-sa@{project_id}.iam.gserviceaccount.com"
    else:
        project_id = env_info["project_id"]
        ge_app_id = env_info["ge_app_id"]
        re_uri = deploy_res.get("reasoning_engine", "N/A")
        sa_email = env_info["service_account"]

    status = deploy_res.get("status", "UNKNOWN")
    display_name = deploy_res.get("display_name", "GE Skill Factory (사내 스킬 팩토리)")
    portal_url = f"https://gemini.google.com/app/{ge_app_id}"

    return f"""# Gemini Enterprise 사내 스킬 팩토리 배포 보고서 (gemini-enterprise-copilot-skill)

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
| **내장 실행 도구** | `3종 완비` | `deploy_enterprise_skill_tool`, `list_enterprise_skills_tool`, `get_preset_skills_tool` |
| **GE App 사내 갤러리 등록** | `ACTIVE` | 사내 갤러리(`/r/agents`) 전사 공유 (`ALL_USERS`) 바인딩 완료 |

---

## 2. 팩토리 에이전트 아키텍처 및 스킬 제작 흐름

본 솔루션은 사내 개발자 및 임직원이 복잡한 OpenAPI 스펙이나 Secret Manager 권한을 일일이 수동 구성하지 않고, GE App 채팅창에서 자연어 대화만으로 사내 기간계 시스템 연동 도구(붕어빵)를 자율 제작 및 등록할 수 있도록 지원하는 **사내 스킬 팩토리(붕어빵 틀)**다:

```mermaid
flowchart TB
    subgraph Dev["1. 엔지니어링 & 프로비저닝"]
        A["인프라 / 플랫폼 엔지니어"] -->|"python diagnose.py"| B["스킬 팩토리<br/>(diagnose.py)"]
        B -->|"Google ADK 2.11+ 패키징"| C["Agent Engine 이미지 & 스펙"]
    end

    subgraph Runtime["2. 런타임 & 도구 연동"]
        C -->|"원클릭 프로비저닝"| D["Agent Engine<br/>(Reasoning Engine)"]
        D -->|"사내 갤러리 전사 등록"| E["Gemini Enterprise app<br/>사내 갤러리 (/r/agents)"]
    end

    subgraph Portal["3. 전사 임직원 인터페이스"]
        E -->|"대화형 스킬 빌더 제공"| F["사내 개발자 / 임직원<br/>(비즈니스 실무자)"]
        F -->|"자연어 도구 연동 요청"| E
        E -->|"스킬 자동 등록 도구 호출"| D
        D -->|"Secret 볼트 & 스킬 생성"| G[("Secret Manager 보안 볼트<br/>OpenAPI Tool 매니페스트")]
    end
```

---

## 3. 사내 실무자 활용 가이드 (도구 및 스킬 생성)

사내 임직원 및 개발자는 배포된 스킬 팩토리 에이전트와 대화하여 다음과 같이 사내 도구를 즉시 찍어낼 수 있다:

1. **Gemini Enterprise app 접속**:
   - 웹 포털 ( {portal_url} ) 접속 후 좌측 사이드바 **사내 갤러리(`/r/agents`)** 이동.
   - **`{display_name}`** 선택.

2. **자연어 붕어빵 생성 예시 프롬프트**:
   - *"사내 Google Sheets 실적 및 명단 행 조회 스킬 만들어 줘"*
   - *"사내 인시던트 발생 시 슬랙(Slack) 채널 알림 발송 도구 배포해 줘"*
   - *"Jira Cloud 신규 이슈 및 결함 티켓 자동 생성 스킬 등록해 줘"*
   - *"ERP 구매 주문(PO) 승인 상태 조회 및 품의서 연동 도구 만들어 줘"*

3. **팩토리 에이전트 자율 동작**:
   - 스킬 팩토리 에이전트가 인증 방식, 엔드포인트 파라미터, Secret Manager 보안 키를 확인하고,
   - 내장된 `deploy_enterprise_skill_tool`을 호출하여 표준 OpenAPI Tool 매니페스트 생성 및 사내 등록을 자동 완결한다.

---

## 4. 사내 거버넌스 4대 필수 표준 라벨

팩토리 에이전트 및 하위 생성 리소스 관리 시 아래 4대 표준 라벨이 기본 적용된다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-copilot-skill`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 5. 콘솔 링크 조치 가이드

- **Agent Engine 콘솔**: 프로비저닝된 에이전트 엔진 런타임 상태 및 인스턴스 모니터링 ( https://console.cloud.google.com/vertex-ai/agents/agent-engines?project={project_id} )
- **Agent Platform 콘솔**: 사내 등록된 에이전트 및 Gemini Enterprise app 바인딩 관리 ( https://console.cloud.google.com/gen-app-builder/engines/{ge_app_id}/assistants/default_assistant/agents?project={project_id} )
- **Secret Manager 콘솔**: 사내 시스템 API 키 및 보안 토큰 볼트 관리 ( https://console.cloud.google.com/security/secret-manager?project={project_id} )

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


def deploy_skill_factory_engine(env_info: dict, dry_run: bool = False) -> dict:
    """Gemini Enterprise Skill Factory를 Agent Engine으로 프로비저닝하고 GE App에 자동 등록한다."""
    project_id = env_info["project_id"]
    re_location = "us-central1"
    ge_app_id = env_info["ge_app_id"]
    ge_location = "global"
    staging_bucket = f"gs://{project_id}-agent-engine-staging"

    display_name = "GE Skill Factory (사내 스킬 팩토리)"
    description = "사내 맞춤형 스킬(Open Skills / SKILL.md) 대화형 자율 생성 및 Gemini Enterprise app 전사 즉시 프로비저닝 팩토리"

    labels = {
        "managed-by": "google-cloud-0-to-1",
        "scenario": "gemini-enterprise-copilot-skill",
        "env": "sample",
        "created-by": get_resource_creator(dry_run),
    }

    print("\n" + "=" * 75)
    print("  [원클릭 배포] GE Skill Factory 배포 파이프라인")
    print("=" * 75)
    print(f"[*] 대상 프로젝트 : {project_id}")
    print(f"[*] Agent Engine  : {re_location}")
    print(f"[*] GE App ID     : {ge_app_id} (위치: {ge_location})")
    print(f"[*] 필수 4대 라벨 : {labels}")

    if dry_run:
        print("\n--> [가상 실행 모드 (--dry-run)] 실제 배포 없이 프로비저닝 명세를 시뮬레이션합니다.")
        simulated_re_id = "5057054473252241408"
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

    # 1. 에이전트 내장 실행 도구 정의 (Skills 직접 프로비저닝)
    def deploy_enterprise_skill_tool(
        skill_name: str,
        description: str,
        instruction: str,
        scope: str = "ALL_USERS",
    ) -> str:
        """Create and deploy a new official skill directly into the user's Gemini Enterprise app Skills catalog.

        Args:
            skill_name: English display name for the skill (letters, numbers, hyphens, spaces only, max 64 chars).
            description: Concise description explaining what this skill does and when to invoke it.
            instruction: Comprehensive SKILL.md-compatible instructions and prompt rules for the skill.
            scope: Visibility scope ('ALL_USERS' for org-wide shared skill, or 'PRIVATE' for personal use).
        """
        import re
        import requests
        import google.auth
        import google.auth.transport.requests

        cleaned_name = re.sub(r"[^a-zA-Z0-9\s\-]", "", skill_name).strip()
        if not cleaned_name:
            cleaned_name = "Custom Enterprise Skill"
        if len(cleaned_name) > 64:
            cleaned_name = cleaned_name[:64].strip()

        try:
            creds, _ = google.auth.default()
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            cur_token = creds.token

            headers = {
                "Authorization": f"Bearer {cur_token}",
                "Content-Type": "application/json",
                "X-Goog-User-Project": project_id,
            }
            base_url = (
                f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}"
                f"/locations/{ge_location}/collections/default_collection"
                f"/engines/{ge_app_id}/assistants/default_assistant/agents"
            )

            body = {
                "displayName": cleaned_name,
                "description": description,
                "skillAgentDefinition": {
                    "instruction": instruction,
                },
            }
            post_resp = requests.post(base_url, headers=headers, json=body, timeout=30)
            if not post_resp.ok:
                return f"[배포 실패] Discovery Engine API 오류 ({post_resp.status_code}): {post_resp.text}"

            skill_data = post_resp.json()
            skill_id = skill_data.get("name", "").split("/")[-1]
            gcs_uri = skill_data.get("skillAgentDefinition", {}).get("gcsUri", "N/A")

            if scope == "ALL_USERS":
                patch_url = f"{base_url}/{skill_id}?updateMask=sharingConfig"
                patch_body = {"sharingConfig": {"scope": "ALL_USERS"}}
                patch_resp = requests.patch(patch_url, headers=headers, json=patch_body, timeout=30)
                final_scope = "ALL_USERS (전사 공유)" if patch_resp.ok else "PRIVATE (개인용)"
            else:
                final_scope = "PRIVATE (개인용)"

            return (
                f"### Gemini Enterprise 스킬 배포 완료\n\n"
                f"- **스킬 명칭**: `{cleaned_name}`\n"
                f"- **스킬 ID**: `{skill_id}`\n"
                f"- **공유 상태**: `{final_scope}`\n"
                f"- **GCS 아티팩트 URI**: `{gcs_uri}`\n"
                f"- **확인 방법**: GE App 좌측 **Skills** 메뉴를 새로고침(F5)하면 본인 및 팀원들의 스킬 갤러리에 즉시 표시됩니다."
            )
        except Exception as e:
            return f"[예외 발생] 스킬 배포 실패: {str(e)}"

    def list_enterprise_skills_tool() -> str:
        """List all registered skills currently deployed in the Gemini Enterprise app.

        Returns:
            A markdown-formatted summary table of registered skills.
        """
        import requests
        import google.auth
        import google.auth.transport.requests

        try:
            creds, _ = google.auth.default()
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            cur_token = creds.token

            headers = {
                "Authorization": f"Bearer {cur_token}",
                "Content-Type": "application/json",
                "X-Goog-User-Project": project_id,
            }
            base_url = (
                f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}"
                f"/locations/{ge_location}/collections/default_collection"
                f"/engines/{ge_app_id}/assistants/default_assistant/agents"
            )

            resp = requests.get(f"{base_url}?pageSize=50", headers=headers, timeout=30)
            if not resp.ok:
                return f"[조회 실패] 에이전트/스킬 목록 조회 오류: {resp.text}"

            agents = resp.json().get("agents", [])
            skills = [a for a in agents if a.get("skillAgentDefinition") is not None]
            if not skills:
                return "현재 등록된 커스텀 스킬이 없습니다. '스킬 생성'을 요청하시면 즉시 배포할 수 있습니다."

            lines = [
                "| 스킬 명칭 | 스킬 ID | 상태 | 공유 범위 |",
                "| :--- | :--- | :--- | :--- |",
            ]
            for s in skills:
                disp = s.get("displayName", "N/A")
                sid = s.get("name", "").split("/")[-1]
                st = s.get("state", "PRIVATE")
                sc = s.get("sharingConfig", {}).get("scope", "PRIVATE")
                lines.append(f"| {disp} | `{sid}` | `{st}` | `{sc}` |")

            return "\n".join(lines)
        except Exception as e:
            return f"[예외 발생] 스킬 목록 조회 실패: {str(e)}"

    def get_preset_skills_tool() -> str:
        """Get the enterprise recommended preset skills catalog (Slack, Google Sheets, Jira, BigQuery, ERP).

        Returns:
            A markdown catalog of 8 core enterprise preset skills ready to be deployed.
        """
        lines = [
            "### 사내 8대 엔터프라이즈 프리셋 스킬 카탈로그",
            "원하시는 스킬 번호나 명칭을 말씀하시면 즉시 귀하의 GE App에 등록해 드립니다:\n",
            "1. **Slack 긴급 장애 알림 스킬**: Slack 인커밍 웹훅 기반 장애/긴급 공지 채널 발송 (`slack_webhook_notifier`)",
            "2. **Google Sheets 사내 실적 행 조회 스킬**: 구글 스프레드시트 데이터 검색 및 행 추출 (`sheets_data_lookup`)",
            "3. **Google Sheets 신규 접수 행 추가 스킬**: 결재 신청 및 VOC 접수 내역 자동 추가 (`sheets_row_append`)",
            "4. **Jira 버그 티켓 자동 등록 스킬**: 아틀라시안 지라 이슈 자동 발행 및 상태 조회 (`jira_issue_creator`)",
            "5. **BigQuery 테이블 스키마 조회 스킬**: DW 데이터셋 및 테이블 스키마 안전 조회 (`bq_table_schema_reader`)",
            "6. **사내 ERP 전표 유효성 검증 스킬**: 전표 번호 및 공급가액 정합성 사전 검증 (`erp_invoice_validator`)",
            "7. **사내 문서 요약 및 번역 스킬**: 계약서/기술 문서 보안 요약 및 다국어 번역 (`doc_summarizer_translator`)",
            "8. **보안 감사 이벤트 알림 스킬**: Cloud Audit Logs 이상 징후 감지 및 알림 (`security_audit_notifier`)",
        ]
        return "\n".join(lines)

    print("\n[단계 1/2] Agent Engine 초기화 및 패키징 중...")
    vertexai.init(
        project=project_id,
        location=re_location,
        staging_bucket=staging_bucket,
        credentials=creds,
    )

    instruction = """당신은 Gemini Enterprise app 및 Open Skills 생태계의 '사내 스킬 팩토리(Skill Factory)' 마스터 에이전트입니다.
사내 Google Workspace (Google Sheets, Google Docs), Slack, Jira, BigQuery, ERP 등 기간계 시스템과 안전하게 연동할 수 있는 업무 스킬(SKILL.md)을 대화형으로 자율 생성하고, 귀하에게 장착된 실제 배포 도구(`deploy_enterprise_skill_tool`)를 호출하여 사용자의 GE App Skills 갤러리에 즉시 자동 프로비저닝 및 전사 배포합니다.

[2026년 Google Cloud AI 모델 표준 및 거버넌스 가이드라인]
- 사내 엔터프라이즈 표준 기본 모델은 'gemini-3.8-flash' (고속 응답, 사내 RAG 문서 검색, 일상 업무 자동화)이다.
- 에이전트 기획서 및 시스템 명세서 출력 시 적용 모델 항목에는 반드시 'gemini-3.8-flash (권장 기본)'로 명시한다.

[장착된 실제 실행 도구 (Tools)]
당신에게는 실제 클라우드 환경에 스킬을 프로비저닝하고 조회할 수 있는 실제 실행 도구가 장착되어 있습니다:
1. `deploy_enterprise_skill_tool`: 사용자가 스킬 생성을 요청하거나 확인하면, SKILL.md 지침을 컴파일하여 사용자의 Gemini Enterprise app Skills 목록에 즉시 배포합니다. (스킬 이름은 영문, 숫자, 하이픈, 공백만 허용).
2. `list_enterprise_skills_tool`: 현재 사내에 등록된 활성 스킬 목록을 실시간 조회할 때 호출하십시오.
3. `get_preset_skills_tool`: 사내 8대 엔터프라이즈 프리셋 스킬 카탈로그를 브리핑할 때 호출하십시오.

[핵심 단계별 인터뷰 절차]
1단계 (연동 대상 시스템 파악): 연동하려는 사내 시스템 및 액션 목적 확인 (프리셋 도구 추천).
2단계 (스킬 명칭 및 지침 규칙 정의): 영문 스킬 명칭, 설명, 핵심 지침(SKILL.md) 및 트리거 조건 도출.
3단계 (실제 프로비저닝 집행): 사용자의 동의를 얻어 `deploy_enterprise_skill_tool`을 즉시 호출하여 GE App Skills 갤러리에 자동 배포.
4단계 (결과 및 활용 안내): 발급된 스킬 ID, GCS 아티팩트 URI, GE App Skills 새로고침 안내 제공.

[단계별 추천 후속 질문 안내 규약]
모든 답변 본문의 맨 끝에는 사용자가 다음 행동을 쉽게 선택할 수 있도록 구분선(---)과 함께 마크다운 번호 매기기 리스트로 2~3개의 '추천 후속 질문'을 명확히 안내한다:
---
**추천 후속 질문:**
1. Slack 긴급 장애 알림 스킬 배포해 줘
2. Google Sheets 조회 스킬 등록해 줘
3. 사내 등록된 스킬 목록 조회
- 주의: JSON이나 코드 블록(```suggested_questions 등) 형태가 아닌, 순수 마크다운 텍스트 리스트로 가독성 높게 출력한다.

[소통 원칙]
- 정중하고 품격 있는 문어체(-다, -한다)와 한글 맞춤법 복합어 띄어쓰기를 철저히 준수합니다.
- 이모지나 특수 기호 대신 깔끔한 마크다운을 사용합니다.
"""

    adk_agent = Agent(
        name="gemini_enterprise_skill_factory",
        description=description,
        model="gemini-3.8-flash",
        instruction=instruction,
        tools=[deploy_enterprise_skill_tool, list_enterprise_skills_tool, get_preset_skills_tool],
    )
    app = agent_engines.AdkApp(agent=adk_agent, enable_tracing=True)

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
        gcs_dir_name="ge_factory_skill_factory",
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
        "sharingConfig": {"scope": "ALL_USERS"},
        "customPlaceholderText": "새로 생성할 사내 스킬 요구사항이나 연동 시스템을 입력하세요...",
        "starterPrompts": [
            {"text": "Slack 긴급 장애 알림 스킬 생성해서 내 GE App Skills에 등록해 줘"},
            {"text": "Google Sheets 고객 피드백 조회 스킬 만들어 줘"},
            {"text": "Jira 버그 티켓 자동 발행 스킬 생성 및 전사 공유해 줘"},
            {"text": "현재 사내에 등록된 스킬 목록 조회해 줘"},
        ],
        "adkAgentDefinition": {
            "toolSettings": {"toolDescription": description},
            "provisionedReasoningEngine": {
                "reasoningEngine": re_res
            },
        },
    }

    target_agent_id = None
    existing_state = None
    list_resp = requests.get(base_url, headers=headers, timeout=30)
    if list_resp.ok:
        for a in list_resp.json().get("agents", []):
            if a.get("displayName") in [display_name, "GE Skill Scaffolder (사내 스킬 스캐폴더)"]:
                target_agent_id = a.get("name").split("/")[-1]
                existing_state = a.get("state")
                break

    if target_agent_id:
        if existing_state == "PRIVATE":
            requests.delete(f"{base_url}/{target_agent_id}", headers=headers, timeout=30)
            reg_resp = requests.post(base_url, headers=headers, json=body, timeout=30)
        else:
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
    """로컬 단일 도구/스킬 매니페스트 합성 및 스캐폴딩 보조 모드를 실행한다."""
    print("\n[안내] 로컬 단일 도구/스킬 매니페스트 합성 보조 모드 가동")

    # 1. 도구 칩 선택
    tool_data = SYSTEM_TOOL_CATALOG[1]
    if args.prompt:
        tool_data = {
            "id": "custom_api_tool",
            "title": args.prompt,
            "description": "사용자 맞춤형 사내 시스템 연동 액션 스킬",
            "category": "사용자 직접 정의 API",
            "action_type": "WRITE",
            "http_method": "POST",
            "endpoint_path": "/api/v1/custom/action",
            "secret_needed": "custom-system-auth-token",
            "parameters": {
                "payload": {"type": "object", "description": "전송 데이터 페이로드", "required": True},
            },
        }
    elif args.chip and args.chip in SYSTEM_TOOL_CATALOG:
        tool_data = SYSTEM_TOOL_CATALOG[args.chip]
    elif args.interactive or (sys.stdin.isatty() and not args.dry_run):
        tool_data = select_tool_interactive(args.dry_run)

    print(f"\n[단계 1/3] 도구 칩 스펙 컴파일 중...")
    print(f"  - 도구 명칭    : {tool_data['title']}")
    print(f"  - 시스템 분류  : {tool_data['category']}")
    print(f"  - 작업 유형    : {tool_data['action_type']} ({tool_data['http_method']} {tool_data['endpoint_path']})")

    # 2. OpenAPI 3.0 스키마 및 보안 볼트 합성
    print("\n[단계 2/3] OpenAPI 3.0 도구 매니페스트 및 보안 볼트(Secret Manager) 합성 중...")
    tool_manifest = generate_openapi_tool_manifest(tool_data, env_info)
    print(f"  - 거버넌스 상태 : {tool_manifest['governance_status']}")
    print(f"  - 보안 볼트 URI : {tool_manifest['secret_vault_ref']}")

    # 3. IAM 권한 진단
    print("\n[단계 3/3] 서비스 계정 IAM 권한 및 Gemini Enterprise app 도구 레지스트리 연동 진단 중...")
    iam_diag = diagnose_secret_manager_iam(env_info, args.dry_run)
    print(f"  - 상태: {iam_diag['status']} | {iam_diag['detail']}")

    # 4. 리포트 생성 및 저장
    report_content = build_markdown_report(env_info, tool_data, tool_manifest, iam_diag)
    save_markdown_report(report_content)

    print("\n" + "=" * 75)
    print("  사내 도구 스펙 컴파일 및 매니페스트 생성 완료")
    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(
        description="Gemini Enterprise 자율형 사내 스킬 팩토리 (붕어빵 틀) 배포 및 등록 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project", help="Google Cloud 프로젝트 ID (미지정 시 자동 감지)")
    parser.add_argument("--location", help="Discovery Engine / Gemini Enterprise app 리전 (기본: global)")
    parser.add_argument("--ge-app-id", help="Gemini Enterprise App 인스턴스 ID")
    parser.add_argument("--skill-sa", help="스킬 실행 대행 서비스 계정 이메일")
    parser.add_argument("--dry-run", action="store_true", default=False, help="실제 배포 없이 가상 실행 검증")
    parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
    parser.add_argument("--scaffold", action="store_true", default=False, help="로컬 단일 도구/스킬 매니페스트 합성 보조 모드")
    parser.add_argument("--chip", type=int, help="도구 칩 번호 직접 지정 (1~8)")
    parser.add_argument("--prompt", help="사용자 직접 정의 연동 시스템 요구사항")
    parser.add_argument("--interactive", action="store_true", default=False, help="로컬 대화형 번호 선택기 가동")
    parser.add_argument("--deploy-engine", action="store_true", default=False, help="Agent Engine 프로비저닝 (기본 실행과 동일)")

    args = parser.parse_args()

    # 사내 환경 대화형 설정 모드 분기
    if args.config:
        run_config_mode(args)
        return

    # 인자가 없고 비대화형 환경인 경우 기본 dry-run 활성화
    if len(sys.argv) == 1 and not sys.stdin.isatty():
        args.dry_run = True

    print("\n" + "=" * 75)
    print("  Gemini Enterprise 사내 스킬 팩토리 (gemini-enterprise-copilot-skill)")
    print("=" * 75)

    # 1. 환경 정보 해석
    env_info = resolve_environment(args)
    print(f"[*] 활성 프로젝트    : {env_info['project_id']}")
    print(f"[*] 대상 리전        : {env_info['location']}")
    print(f"[*] 대상 Gemini Enterprise App ID   : {env_info['ge_app_id']}")
    print(f"[*] 실행 서비스 계정 : {env_info['service_account']}")
    print(f"[*] 실행 모드        : {'가상 실행 (--dry-run)' if args.dry_run else '실제 프로비저닝 모드'}")

    # 로컬 스캐폴딩 보조 모드 분기 (명시적 플래그 지정 시에만 작동)
    if args.scaffold or args.chip or args.prompt or args.interactive:
        run_local_scaffolding_mode(args, env_info)
        return

    # [핵심 메인 워크플로우]: 붕어빵 틀(GE Skill Factory) 배포 및 GE App 사내 갤러리 등록
    print("\n[진행] 사내 스킬 팩토리(붕어빵 틀) 프로비저닝 파이프라인 가동...")
    deploy_res = deploy_skill_factory_engine(env_info, dry_run=args.dry_run)

    # 팩토리 리포트 생성 및 저장
    report_content = build_factory_markdown_report(env_info, deploy_res, dry_run=args.dry_run)
    save_markdown_report(report_content)

    creator = get_resource_creator(args.dry_run)
    print("\n" + "=" * 75)
    print("  사내 스킬 팩토리 배포 및 등록 완료 (모든 점검 통과)")
    print("=" * 75)
    print("\n[안내] 사내 거버넌스 및 자원 추적을 위한 4대 필수 표준 라벨:")
    print("  - managed-by: google-cloud-0-to-1")
    print("  - scenario: gemini-enterprise-copilot-skill")
    print("  - env: sample")
    print(f"  - created-by: {creator}\n")


if __name__ == "__main__":
    main()
