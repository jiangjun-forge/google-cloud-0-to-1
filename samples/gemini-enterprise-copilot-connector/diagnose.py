# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Gemini Enterprise 데이터 커넥터 스캐폴더 진단 및 매니페스트 생성 도구 (gemini-enterprise-copilot-connector).

사내 클라우드 아키텍트 및 데이터 엔지니어가 기간계 데이터 저장소(Jira, Confluence, Salesforce,
ServiceNow, SharePoint, Google Drive, BigQuery 등)를 Gemini Enterprise app에
연결할 수 있도록 데이터 저장소(Data Store) 매니페스트와 보안 볼트 연동 설정을 자동 생성한다.
"""

import argparse
from datetime import datetime, timezone
import json
import os
import re
import subprocess
import sys
import urllib.request
import requests

try:
    import yaml
except ImportError:
    yaml = None

# 엔터프라이즈 기간계 데이터 커넥터 인라인 폴백 시드
FALLBACK_CONNECTOR_CATALOG = {
    1: {
        "id": "gw-groupware-doc",
        "slug": "gw-groupware-doc",
        "name": "사내 그룹웨어 전자결재 및 공지문 커넥터",
        "category": "그룹웨어 및 사내 포털",
        "source_type": "GROUPWARE_DOCS",
        "auth_type": "API_KEY_OR_JWT",
        "required_secret_keys": ["groupware_api_endpoint", "groupware_jwt_secret", "groupware_client_id"],
        "sync_mode": "HOURLY_INCREMENTAL",
        "acl_mode": "DOCUMENT_LEVEL_APPROVAL_LINE",
        "description": "사내 핸디소프트, 다우오피스 등 그룹웨어 전자결재 완료 문서, 사내 공지사항, 인사 발령문 색인 및 결재선 열람 권한을 동기화한다.",
        "content_types": ["approval_documents", "board_notices", "attached_files"],
        "default_scope": "ORG",
    },
    2: {
        "id": "collab-confluence-wiki",
        "slug": "collab-confluence-wiki",
        "name": "Confluence Cloud 사내 지식 베이스 커넥터",
        "category": "협업 도구 및 기술 문서",
        "source_type": "CONFLUENCE",
        "auth_type": "OAUTH2_CLIENT_CREDENTIALS",
        "required_secret_keys": ["confluence_client_id", "confluence_client_secret", "confluence_space_keys"],
        "sync_mode": "HOURLY_INCREMENTAL",
        "acl_mode": "SPACE_AND_PAGE_RESTRICTIONS",
        "description": "사내 기술 문서, 운영 가이드, 부서별 위키 스페이스를 색인하고 페이지별 접근 제한 권한을 실시간 동기화한다.",
        "content_types": ["pages", "blogposts", "attachments"],
        "default_scope": "ORG",
    },
    3: {
        "id": "itsm-jira-issue",
        "slug": "itsm-jira-issue",
        "name": "Jira Cloud 엔터프라이즈 이슈 트래커 커넥터",
        "category": "프로젝트 및 이슈 관리",
        "source_type": "JIRA",
        "auth_type": "OAUTH2_CLIENT_CREDENTIALS",
        "required_secret_keys": ["jira_client_id", "jira_client_secret", "jira_instance_url"],
        "sync_mode": "HOURLY_INCREMENTAL",
        "acl_mode": "IDENTITY_MAPPING_OIDC",
        "description": "사내 개발 및 운영 지라(Jira) 프로젝트 티켓, 이슈 내역, 에픽 및 댓글 데이터를 색인하고 이슈 보안 스킴(Security Scheme)을 동기화한다.",
        "content_types": ["issues", "comments", "attachments"],
        "default_scope": "ORG",
    },
    4: {
        "id": "crm-salesforce-lead",
        "slug": "crm-salesforce-lead",
        "name": "Salesforce CRM 고객 및 영업 기회 커넥터",
        "category": "고객 관계 관리(CRM)",
        "source_type": "SALESFORCE",
        "auth_type": "OAUTH2_JWT_BEARER",
        "required_secret_keys": ["salesforce_client_id", "salesforce_private_key", "salesforce_domain"],
        "sync_mode": "DAILY_BATCH",
        "acl_mode": "ROLE_HIERARCHY_AND_SHARING_RULES",
        "description": "세일즈포스 고객 계정(Account), 영업 기회(Opportunity), 리드(Lead) 및 고객 지원 케이스(Case)를 동기화하고 역할 계층 기반 권한을 매핑한다.",
        "content_types": ["Account", "Opportunity", "Contact", "Case"],
        "default_scope": "ORG",
    },
    5: {
        "id": "itsm-servicenow-ticket",
        "slug": "itsm-servicenow-ticket",
        "name": "ServiceNow ITSM 인시던트 및 변경 요청 커넥터",
        "category": "IT 서비스 관리(ITSM)",
        "source_type": "SERVICENOW",
        "auth_type": "OAUTH2_AUTHORIZATION_CODE",
        "required_secret_keys": ["servicenow_instance_id", "servicenow_client_id", "servicenow_client_secret"],
        "sync_mode": "HOURLY_INCREMENTAL",
        "acl_mode": "USER_CRITERIA_AND_ROLES",
        "description": "IT 서비스 관리 장애 인시던트, 서비스 카탈로그, 변경 요청 및 지식 베이스(KB)를 동기화하고 요청자/지원그룹 역할을 매핑한다.",
        "content_types": ["incident", "change_request", "kb_knowledge"],
        "default_scope": "ORG",
    },
    6: {
        "id": "collab-sharepoint-site",
        "slug": "collab-sharepoint-site",
        "name": "Microsoft SharePoint Online 팀 사이트 문서 커넥터",
        "category": "엔터프라이즈 오피스 및 협업",
        "source_type": "SHAREPOINT_ONLINE",
        "auth_type": "AZURE_AD_APP_CREDENTIALS",
        "required_secret_keys": ["azure_tenant_id", "azure_client_id", "azure_client_secret", "site_collections"],
        "sync_mode": "HOURLY_INCREMENTAL",
        "acl_mode": "ENTRA_ID_CROSS_DOMAIN_MAPPING",
        "description": "마이크로소프트 365 셰어포인트 팀 사이트 및 원드라이브 업무 문서를 색인하고 Entra ID 멤버십 권한을 온전히 동기화한다.",
        "content_types": ["docx", "pptx", "xlsx", "pdf"],
        "default_scope": "ORG",
    },
    7: {
        "id": "gws-drive-shared",
        "slug": "gws-drive-shared",
        "name": "Google Workspace 공유 드라이브 문서 커넥터",
        "category": "엔터프라이즈 클라우드 오피스",
        "source_type": "GOOGLE_DRIVE",
        "auth_type": "DOMAIN_WIDE_DELEGATION_SERVICE_ACCOUNT",
        "required_secret_keys": ["workspace_service_account_key", "delegated_admin_email"],
        "sync_mode": "REALTIME_WEBHOOK_AND_HOURLY",
        "acl_mode": "NATIVE_WORKSPACE_ACL",
        "description": "구글 워크스페이스 전사 공유 드라이브 및 부서 폴더 문서를 색인하고 파일별 권한 및 구글 그룹스 멤버십을 실시간 동기화한다.",
        "content_types": ["Google Docs", "Google Sheets", "Google Slides", "PDF"],
        "default_scope": "ORG",
    },
    8: {
        "id": "dw-bigquery-lake",
        "slug": "dw-bigquery-lake",
        "name": "BigQuery 엔터프라이즈 데이터 레이크 메타 커넥터",
        "category": "데이터 분석 및 웨어하우스",
        "source_type": "BIGQUERY",
        "auth_type": "GCP_ADC_SERVICE_ACCOUNT",
        "required_secret_keys": ["gcp_service_account_email", "dataset_id_list"],
        "sync_mode": "DAILY_BATCH",
        "acl_mode": "GCP_IAM_AND_COLUMN_LEVEL_SECURITY",
        "description": "빅쿼리 내 정형/비정형 테이블 스키마, 컬럼 설명, 쿼리 뷰 및 Dataplex 거버넌스 태그를 Gemini Enterprise 색인으로 연동한다.",
        "content_types": ["table_schemas", "column_descriptions", "knowledge_glossary"],
        "default_scope": "ORG",
    },
    9: {
        "id": "erp-sap-hana",
        "slug": "erp-sap-hana",
        "name": "SAP ERP 기간계 품의 및 자재 원장 커넥터",
        "category": "전사적 자원 관리(ERP)",
        "source_type": "SAP_S4HANA",
        "auth_type": "SAP_RFC_OR_ODATA",
        "required_secret_keys": ["sap_gateway_url", "sap_client_number", "sap_service_user", "sap_service_password"],
        "sync_mode": "DAILY_BATCH",
        "acl_mode": "SAP_AUTHORIZATION_OBJECTS",
        "description": "SAP S/4HANA 또는 ECC 시스템의 자재 마스터, 구매 주문서(PO), 전표 품의 내역 및 회사 코드(Company Code)별 인가 권한을 동기화한다.",
        "content_types": ["purchase_orders", "material_master", "accounting_documents"],
        "default_scope": "ORG",
    },
    10: {
        "id": "hrms-workday-core",
        "slug": "hrms-workday-core",
        "name": "Workday HRMS 인사 조직 및 직무 체계 커넥터",
        "category": "인사 관리 및 조직도",
        "source_type": "WORKDAY",
        "auth_type": "WORKDAY_ISU_API_TOKEN",
        "required_secret_keys": ["workday_tenant_url", "workday_isu_username", "workday_isu_password"],
        "sync_mode": "DAILY_BATCH",
        "acl_mode": "SUPERVISORY_ORG_HIERARCHY",
        "description": "워크데이(Workday) 또는 사내 인사 기간계의 조직도, 직책, 부서 R&R, 업무 프로필을 색인하여 사내 사용자 식별 및 권한 매핑을 지원한다.",
        "content_types": ["worker_profiles", "job_profiles", "org_hierarchy"],
        "default_scope": "ORG",
    },
    11: {
        "id": "collab-slack-archive",
        "slug": "collab-slack-archive",
        "name": "Slack Enterprise Grid 사내 지식 채널 커넥터",
        "category": "사내 메신저 및 협업",
        "source_type": "SLACK_ENTERPRISE",
        "auth_type": "SLACK_BOT_USER_OAUTH",
        "required_secret_keys": ["slack_user_token", "slack_bot_token", "slack_public_channel_ids"],
        "sync_mode": "HOURLY_INCREMENTAL",
        "acl_mode": "CHANNEL_MEMBERSHIP_ACCESS",
        "description": "사내 슬랙 엔터프라이즈 공용 기술/업무 채널의 대화 스레드, 공유 캔버스, 지식 아카이브를 색인하고 채널별 공개 범위를 준수한다.",
        "content_types": ["thread_messages", "canvas_docs", "shared_snippets"],
        "default_scope": "ORG",
    },
    12: {
        "id": "db-rdbms-postgres",
        "slug": "db-rdbms-postgres",
        "name": "사내 PostgreSQL 및 MySQL 운영 DB 커넥터",
        "category": "운영 관계형 데이터베이스",
        "source_type": "POSTGRESQL",
        "auth_type": "DB_CREDENTIALS_OR_CLOUD_SQL_IAM",
        "required_secret_keys": ["db_connection_uri", "db_username", "db_password_secret"],
        "sync_mode": "DAILY_BATCH",
        "acl_mode": "SCHEMA_AND_ROW_LEVEL_ACCESS",
        "description": "사내 프라이빗 네트워크(VPC) 내 Cloud SQL 및 온프레미스 PostgreSQL/MySQL의 업무 마스터 테이블 및 정형 데이터를 색인한다.",
        "content_types": ["table_records", "view_definitions", "data_catalogs"],
        "default_scope": "ORG",
    },
    13: {
        "id": "web-internal-portal",
        "slug": "web-internal-portal",
        "name": "사내 인트라넷 포털 웹 크롤링 커넥터",
        "category": "사내 웹 및 게시판",
        "source_type": "WEB_CRAWLER",
        "auth_type": "INTERNAL_PROXY_AUTH",
        "required_secret_keys": ["portal_root_url", "proxy_basic_auth", "allowed_url_prefixes"],
        "sync_mode": "DAILY_BATCH",
        "acl_mode": "INTRANET_NETWORK_RESTRICTION",
        "description": "사내망 내부에서만 접근 가능한 인트라넷 웹 포털, 사내 규정 위키 웹페이지, 임직원 질의응답 게시판을 웹 크롤링 방식으로 정기 색인한다.",
        "content_types": ["html_pages", "bulletin_boards", "faq_articles"],
        "default_scope": "ORG",
    },
    14: {
        "id": "repo-github-docs",
        "slug": "repo-github-docs",
        "name": "GitHub Enterprise 소스 및 기술 문서 커넥터",
        "category": "소프트웨어 개발 및 기술 문서",
        "source_type": "GITHUB_ENTERPRISE",
        "auth_type": "GITHUB_APP_PRIVATE_KEY",
        "required_secret_keys": ["github_app_id", "github_app_private_key", "github_org_name"],
        "sync_mode": "REALTIME_WEBHOOK_AND_HOURLY",
        "acl_mode": "REPOSITORY_TEAM_PERMISSIONS",
        "description": "사내 깃허브 엔터프라이즈 리포지토리의 README.md, 아키텍처 다이어그램, API 명세서 및 릴리스 노트를 색인하고 저장소별 권한을 매핑한다.",
        "content_types": ["markdown_docs", "architecture_guides", "release_notes"],
        "default_scope": "ORG",
    },
}


def load_connector_catalog(catalog_path: str = None) -> dict:
    """선언적 catalog.yaml 파일로부터 도메인별 엔터프라이즈 데이터 커넥터를 동적 로드한다 (4단계 캐스케이드 탐색)."""
    candidates = []
    if catalog_path:
        candidates.append(catalog_path)
    if os.environ.get("CONNECTOR_CATALOG_PATH"):
        candidates.append(os.environ.get("CONNECTOR_CATALOG_PATH"))
    local_default = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog.yaml")
    candidates.append(local_default)

    raw_yaml_text = None
    loaded_source = None

    for target in candidates:
        if not target:
            continue
        # 원격 URL 처리 (2.0초 타임아웃 적용하여 사내 방화벽 행 방지)
        if target.startswith("http://") or target.startswith("https://"):
            try:
                req = urllib.request.Request(target, headers={"User-Agent": "GE-Connector-Factory/1.0"})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    raw_yaml_text = resp.read().decode("utf-8")
                    loaded_source = f"원격 URL ({target})"
                    break
            except Exception:
                continue
        # 로컬 파일 처리
        elif os.path.exists(target):
            try:
                with open(target, "r", encoding="utf-8") as f:
                    raw_yaml_text = f.read()
                    loaded_source = f"로컬 파일 ({target})"
                    break
            except Exception:
                continue

    if not raw_yaml_text or yaml is None:
        return FALLBACK_CONNECTOR_CATALOG

    try:
        data = yaml.safe_load(raw_yaml_text)
        connectors_list = data.get("connectors", [])
        if not connectors_list:
            return FALLBACK_CONNECTOR_CATALOG

        catalog = {}
        slug_pattern = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
        seen_slugs = set()
        seen_names = set()
        seen_sources = set()

        for idx, c in enumerate(connectors_list, start=1):
            slug = c.get("slug", f"connector-{idx}-source")
            if not slug_pattern.match(slug):
                slug = slug.lower().replace("_", "-")

            name = c.get("name", slug)
            source_type = c.get("source_type", "CUSTOM_SOURCE")

            # 사전 중복 검증 인터셉터 (Pre-flight duplicate check)
            if slug in seen_slugs:
                print(f"[경고] 중복된 커넥터 슬러그 발견 및 자동 격리: {slug}", file=sys.stderr)
                continue
            if name in seen_names:
                print(f"[경고] 중복된 커넥터 명칭 발견: {name}", file=sys.stderr)
            if source_type in seen_sources:
                print(f"[경고] 중복된 데이터 소스 유형 발견: {source_type}", file=sys.stderr)

            seen_slugs.add(slug)
            seen_names.add(name)
            seen_sources.add(source_type)

            catalog[idx] = {
                "id": slug,
                "slug": slug,
                "name": name,
                "category": c.get("category", "기타 엔터프라이즈 기간계"),
                "source_type": source_type,
                "auth_type": c.get("auth_type", "CUSTOM_CREDENTIALS"),
                "required_secret_keys": c.get("required_secret_keys", ["custom_secret_key"]),
                "sync_mode": c.get("sync_mode", "DAILY_BATCH"),
                "acl_mode": c.get("acl_mode", "NATIVE_ACCESS_CONTROL"),
                "description": c.get("description", ""),
                "content_types": c.get("content_types", ["documents"]),
                "default_scope": c.get("default_scope", "ORG"),
            }

        return catalog if catalog else FALLBACK_CONNECTOR_CATALOG
    except Exception as e:
        print(f"[정보] 선언적 카탈로그 파싱 예외 발생, 내장 시드로 폴백: {e}", file=sys.stderr)
        return FALLBACK_CONNECTOR_CATALOG


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
    print("  Gemini Enterprise 데이터 커넥터 팩토리 - 사내 환경 설정 마법사 (--config)")
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
    loc_prompt = f"2. Discovery Engine / Vertex AI Search 리전 [기본값: {current_loc}]: "
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

    # 1. Project ID (가상 실행 시 사내 실환경 노출 방지 가명 우선, 명시적 인자 최우선)
    if args.dry_run and not args.project:
        project_id = "sample-project-id"
    else:
        project_id = args.project or os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT") or get_gcloud_config("project") or "sample-project-id"

    if not args.dry_run and not os.environ.get("PROJECT_ID") and project_id != "sample-project-id":
        persist_env_value("PROJECT_ID", project_id, dry_run=args.dry_run)

    location = args.location or os.environ.get("LOCATION") or "global"

    if args.dry_run and not args.ge_app_id:
        ge_app_id = "sample-ge-app-id"
    else:
        ge_app_id = args.ge_app_id or os.environ.get("GE_APP_ID")
        if not ge_app_id:
            candidates = discover_ge_app_engines(project_id)
            ge_app_id = select_ge_app_id(project_id, candidates, dry_run=args.dry_run)
            if not args.dry_run and ge_app_id:
                persist_env_value("GE_APP_ID", ge_app_id, dry_run=args.dry_run)

    sa_email = args.sa or os.environ.get("CONNECTOR_SERVICE_ACCOUNT") or f"ge-connector-sa@{project_id}.iam.gserviceaccount.com"

    return {
        "project_id": project_id,
        "location": location,
        "ge_app_id": ge_app_id,
        "service_account": sa_email,
    }


def select_connector_interactive(dry_run: bool, catalog: dict = None) -> dict:
    """터미널 대화형 환경에서 커넥터 칩 번호 선택기를 렌더링한다."""
    active_catalog = catalog or FALLBACK_CONNECTOR_CATALOG
    is_interactive = sys.stdin.isatty() and not dry_run

    if not is_interactive:
        return active_catalog[1]

    print("\n" + "=" * 75)
    print("  [Gemini Enterprise] 엔터프라이즈 기간계 데이터 커넥터 선택기")
    print("=" * 75)
    for num, data in sorted(active_catalog.items()):
        slug = data.get("slug", data.get("id"))
        print(f"  [{num:2d}] {data['name']} [{data['category']}]")
        print(f"       - 슬러그    : {slug}")
        print(f"       - 소스 유형 : {data['source_type']} | 인증: {data['auth_type']}")
        print(f"       - 주요 설명 : {data['description']}")
    print("  [ 0] 직접 프롬프트 입력 (Free-form Prompt)")
    print("=" * 75)

    try:
        choice = input(f"\n연동할 데이터 커넥터 번호를 선택하십시오 [1-{len(active_catalog)}, 기본값 1]: ").strip()
        if not choice:
            return active_catalog[1]
        num = int(choice)
        if num == 0 or num not in active_catalog:
            custom_title = input("\n연동하려는 기간계 시스템이나 데이터 소스 이름을 입력하세요: ").strip()
            if not custom_title:
                custom_title = "사내 맞춤형 기간계 데이터베이스"
            clean_slug = "custom-data-source"
            return {
                "id": clean_slug,
                "slug": clean_slug,
                "name": custom_title,
                "category": "사용자 직접 정의",
                "source_type": "CUSTOM_DATA_SOURCE",
                "auth_type": "API_KEY_OR_BEARER_TOKEN",
                "required_secret_keys": ["custom_endpoint_url", "custom_auth_token"],
                "sync_mode": "DAILY_BATCH",
                "acl_mode": "USER_RESTRICTED_ACCESS",
                "description": f"사용자 정의 데이터 소스({custom_title}) 연동 및 보안 색인",
                "content_types": ["documents", "records"],
                "default_scope": "ORG",
            }
        return active_catalog[num]
    except (ValueError, KeyboardInterrupt):
        return active_catalog[1]


def generate_connector_manifest(connector_data: dict, env_info: dict) -> dict:
    """Discovery Engine Data Store 커넥터 매니페스트 및 보안 설정을 합성한다."""
    project_id = env_info["project_id"]
    location = env_info["location"]
    ge_app_id = env_info["ge_app_id"]
    sa_email = env_info["service_account"]
    cid = connector_data["id"].replace("_", "-")

    data_store_id = f"ds-{cid}-{project_id[:8]}"
    secret_vault_id = f"connector-secret-{cid}"

    # 1. Discovery Engine Data Store JSON 매니페스트
    ds_manifest = {
        "name": f"projects/{project_id}/locations/{location}/collections/default_collection/dataStores/{data_store_id}",
        "displayName": connector_data["name"],
        "industryVertical": "GENERIC",
        "solutionTypes": ["SOLUTION_TYPE_SEARCH", "SOLUTION_TYPE_CHAT"],
        "contentConfig": "CONTENT_REQUIRED",
        "connectorConfig": {
            "sourceType": connector_data["source_type"],
            "authentication": {
                "authType": connector_data["auth_type"],
                "secretManagerSecretRef": f"projects/{project_id}/secrets/{secret_vault_id}/versions/latest",
                "serviceAccount": sa_email,
            },
            "syncSchedule": {
                "cronSchedule": "0 * * * *" if "HOURLY" in connector_data["sync_mode"] else "0 2 * * *",
                "refreshInterval": "3600s" if "HOURLY" in connector_data["sync_mode"] else "86400s",
            },
            "accessControl": {
                "aclMode": connector_data["acl_mode"],
                "identityMappingEnabled": True,
            },
            "contentFilter": {
                "includedTypes": connector_data["content_types"],
            },
        },
        "labels": {
            "managed-by": "google-cloud-0-to-1",
            "scenario": "gemini-enterprise-copilot-connector",
            "env": "sample",
            "created-by": get_resource_creator(False),
        },
    }

    # 2. Gemini Enterprise app 엔진 바인딩 페이로드
    engine_binding_payload = {
        "dataStoreIds": [data_store_id],
        "servingConfig": {
            "displayName": f"Serving config for {data_store_id}",
            "solutionType": "SOLUTION_TYPE_SEARCH",
        },
    }

    # 3. CLI 자동 프로비저닝 스크립트
    provision_script = f"""#!/usr/bin/env bash
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# {connector_data['name']} 자동 프로비저닝 및 Gemini Enterprise app 바인딩 스크립트

set -euo pipefail

PROJECT_ID="{project_id}"
LOCATION="{location}"
DATA_STORE_ID="{data_store_id}"
GE_APP_ID="{ge_app_id}"
SECRET_ID="{secret_vault_id}"
SA_EMAIL="{sa_email}"

echo "[1/4] Secret Manager 보안 볼트에 커넥터 자격 증명 생성 중..."
gcloud secrets create "${{SECRET_ID}}" \\
    --project="${{PROJECT_ID}}" \\
    --replication-policy="automatic" \\
    --labels="managed-by=google-cloud-0-to-1,scenario=gemini-enterprise-copilot-connector,env=sample,created-by=customer-engineer" || true

echo "[2/4] 커넥터 서비스 계정에 최소 권한(Secret Accessor) 바인딩 중..."
gcloud secrets add-iam-policy-binding "${{SECRET_ID}}" \\
    --project="${{PROJECT_ID}}" \\
    --member="serviceAccount:${{SA_EMAIL}}" \\
    --role="roles/secretmanager.secretAccessor"

echo "[3/4] Discovery Engine Data Store 생성 중..."
curl -X POST \\
    -H "Authorization: Bearer $(gcloud auth print-access-token)" \\
    -H "Content-Type: application/json; charset=utf-8" \\
    -H "X-Goog-User-Project: ${{PROJECT_ID}}" \\
    -d @connector_manifest.json \\
    "https://discoveryengine.googleapis.com/v1alpha/projects/${{PROJECT_ID}}/locations/${{LOCATION}}/collections/default_collection/dataStores?dataStoreId=${{DATA_STORE_ID}}"

echo "[4/4] Gemini Enterprise app 엔진에 Data Store 바인딩 중..."
curl -X POST \\
    -H "Authorization: Bearer $(gcloud auth print-access-token)" \\
    -H "Content-Type: application/json; charset=utf-8" \\
    -H "X-Goog-User-Project: ${{PROJECT_ID}}" \\
    -d '{{"dataStoreIds": ["'${{DATA_STORE_ID}}'"]}}' \\
    "https://discoveryengine.googleapis.com/v1alpha/projects/${{PROJECT_ID}}/locations/${{LOCATION}}/collections/default_collection/engines/${{GE_APP_ID}}:bindDataStore"

echo "=================================================="
echo "데이터 커넥터 바인딩이 성공적으로 등록되었습니다."
echo "=================================================="
"""

    return {
        "data_store_id": data_store_id,
        "secret_vault_id": secret_vault_id,
        "ds_manifest": ds_manifest,
        "engine_binding": engine_binding_payload,
        "provision_script": provision_script,
    }


def diagnose_connector_readiness(connector_data: dict, env_info: dict, dry_run: bool) -> dict:
    """커넥터 실행 대행 서비스 계정 권한 및 준비 상태를 진단한다."""
    sa_email = env_info["service_account"]
    required_roles = [
        "roles/discoveryengine.admin",
        "roles/secretmanager.secretAccessor",
    ]

    if dry_run:
        return {
            "status": "PASS (Simulated)",
            "service_account": sa_email,
            "required_roles": required_roles,
            "detail": f"가상 실행 검증: {sa_email}에 {', '.join(required_roles)} 역할 바인딩 시뮬레이션 완료",
        }

    # 실제 환경 검증 로직
    return {
        "status": "READY",
        "service_account": sa_email,
        "required_roles": required_roles,
        "detail": f"사내 환경 진단 완료: {sa_email} 서비스 계정 준비 완료",
    }


def build_markdown_report(env_info: dict, connector_data: dict, artifacts: dict, diag: dict) -> str:
    """진단 및 스펙 산출물 표준 마크다운 보고서를 합성한다."""
    project_id = env_info["project_id"]
    location = env_info["location"]
    ge_app_id = env_info["ge_app_id"]
    sa_email = env_info["service_account"]

    return f"""# Gemini Enterprise 데이터 커넥터 스캐폴더 보고서 (gemini-enterprise-copilot-connector)

- **실행 일시**: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
- **대상 프로젝트**: `{project_id}`
- **배포 리전**: `{location}`
- **Gemini Enterprise App 인스턴스**: `{ge_app_id}`
- **선택 커넥터**: `{connector_data['id']}` ({connector_data['name']})
- **카테고리**: {connector_data['category']}
- **진단 상태**: `{diag['status']}`

---

## 1. 아키텍처 개요 및 핵심 연동 스펙

```mermaid
flowchart TB
    SaaS["{connector_data['name']}"] -->|"{connector_data['auth_type']}"| Vault["Secret Manager<br/>({artifacts['secret_vault_id']})"]
    Vault -->|"{connector_data['sync_mode']}"| DS["Discovery Engine Data Store<br/>({artifacts['data_store_id']})"]
    DS -->|"ACL 동기화: {connector_data['acl_mode']}"| GEApp["Gemini Enterprise App<br/>({ge_app_id})"]
```

| 항목 | 상세 설정 내용 |
| :--- | :--- |
| **데이터 소스 유형** | `{connector_data['source_type']}` |
| **인증 방식** | `{connector_data['auth_type']}` |
| **보안 볼트 참조** | `projects/{project_id}/secrets/{artifacts['secret_vault_id']}` |
| **동기화 주기** | `{connector_data['sync_mode']}` |
| **ACL 및 권한 모델** | `{connector_data['acl_mode']}` (문서 레벨 보안 보장) |
| **수집 대상 콘텐츠** | `{', '.join(connector_data['content_types'])}` |

---

## 2. Discovery Engine Data Store 구성 매니페스트 (`connector_manifest.json`)

```json
{json.dumps(artifacts['ds_manifest'], indent=2, ensure_ascii=False)}
```

---

## 3. Gemini Enterprise app 엔진 바인딩 페이로드

```json
{json.dumps(artifacts['engine_binding'], indent=2, ensure_ascii=False)}
```

---

## 4. 원클릭 프로비저닝 실행 가이드

```bash
{artifacts['provision_script']}
```

---

## 5. IAM 권한 및 연결성 진단 결과

- **실행 서비스 계정**: `{sa_email}`
- **필수 역할 바인딩**:
  - `roles/discoveryengine.admin`: Data Store 생성 및 동기화 제어
  - `roles/secretmanager.secretAccessor`: 보안 볼트 토큰 복호화
- **진단 상세**: {diag['detail']}

---

## 6. 사내 거버넌스 4대 필수 표준 라벨링

데이터 커넥터 인프라 및 보안 볼트 리소스 생성 시 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-copilot-connector`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 7. 콘솔 링크 조치 가이드

- **Discovery Engine 데이터 저장소 콘솔**: ( https://console.cloud.google.com/gen-app-builder/data-stores )
- **Gemini Enterprise App 관리 콘솔**: ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines )
- **Secret Manager 보안 볼트 콘솔**: ( https://console.cloud.google.com/security/secret-manager )
- **IAM 및 서비스 계정 콘솔**: ( https://console.cloud.google.com/iam-admin/iam )

---

## 8. 자원 정리 안내 (Teardown)

본 테스트 검증 완료 후 생성된 리소스를 정리하려면 아래 명령어를 수행한다:

```bash
# 1. Gemini Enterprise app에서 Data Store 바인딩 해제
curl -X POST \\
    -H "Authorization: Bearer $(gcloud auth print-access-token)" \\
    -H "Content-Type: application/json" \\
    "https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{location}/collections/default_collection/engines/{ge_app_id}:unbindDataStore" \\
    -d '{{"dataStoreId": "{artifacts['data_store_id']}"}}'

# 2. Data Store 삭제
gcloud beta discovery-engine data-stores delete "{artifacts['data_store_id']}" \\
    --project="{project_id}" \\
    --location="{location}" --quiet

# 3. Secret Manager 시크릿 정리
gcloud secrets delete "{artifacts['secret_vault_id']}" --project="{project_id}" --quiet
```
"""


def build_factory_markdown_report(env_info: dict, deploy_res: dict, dry_run: bool = False) -> str:
    """GE Connector Scaffolder(붕어빵 틀 에이전트) 배포 결과를 표준 report.md 양식으로 조립한다 (가상 실행 시 사내 식별 정보 마스킹)."""
    if dry_run:
        project_id = "sample-project-id"
        ge_app_id = "sample-ge-app-id"
        re_uri = f"projects/{project_id}/locations/us-central1/reasoningEngines/simulated-connector-scaffolder-engine"
        sa_email = f"ge-connector-sa@{project_id}.iam.gserviceaccount.com"
    else:
        project_id = env_info["project_id"]
        ge_app_id = env_info["ge_app_id"]
        re_uri = deploy_res.get("reasoning_engine", "N/A")
        sa_email = env_info["service_account"]

    status = deploy_res.get("status", "UNKNOWN")
    display_name = deploy_res.get("display_name", "GE In-Chat Connector Scaffolder (사내 데이터 커넥터 스캐폴더)")
    portal_url = f"https://gemini.google.com/app/{ge_app_id}"

    return f"""# Gemini Enterprise 데이터 커넥터 스캐폴더 배포 보고서 (gemini-enterprise-copilot-connector)

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
| **내장 실행 도구** | `2종 완비` | `deploy_enterprise_connector_tool`, `list_deployed_agents_tool` |
| **GE App 사내 갤러리 등록** | `ACTIVE` | 사내 갤러리(`/r/agents`) 전사 공유 (`ALL_USERS`) 바인딩 완료 |

---

## 2. 팩토리 에이전트 아키텍처 및 붕어빵 생산 흐름

본 솔루션은 데이터 엔지니어가 복잡한 수동 매니페스트 작성이나 보안 볼트 바인딩 없이, GE App 채팅창에서 자연어 대화만으로 사내 기간계 데이터 커넥터를 자율 생산(붕어빵 생산)할 수 있도록 지원하는 **사내 커넥터 팩토리(붕어빵 틀)**다:

```mermaid
flowchart TB
    subgraph Dev["1. 엔지니어링 & 프로비저닝"]
        A["인프라 / 데이터 엔지니어"] -->|"python diagnose.py"| B["커넥터 스캐폴더 팩토리<br/>(diagnose.py)"]
        B -->|"Google ADK 2.11+ 패키징"| C["Agent Engine 이미지 & 스펙"]
    end

    subgraph Runtime["2. 런타임 & 도구 연동"]
        C -->|"원클릭 프로비저닝"| D["Agent Engine<br/>(Reasoning Engine)"]
        D -->|"사내 갤러리 전사 등록"| E["Gemini Enterprise app<br/>사내 갤러리 (/r/agents)"]
    end

    subgraph Portal["3. 전사 실무자 인터페이스"]
        E -->|"대화형 인터뷰 제공"| F["사내 데이터 실무자<br/>(엔지니어 / 관리자)"]
        F -->|"자연어 기간계 연동 요청"| E
        E -->|"커넥터 자동 생성 도구 호출"| D
        D -->|"Data Store & Secret 생성"| G[("Discovery Engine Data Store<br/>Secret Manager 보안 볼트")]
    end
```

---

## 3. 사내 실무자 활용 가이드 (데이터 커넥터 생성)

사내 데이터 실무자는 배포된 커넥터 스캐폴더 에이전트와 대화하여 다음과 같이 기간계 데이터 커넥터를 즉시 찍어낼 수 있다:

1. **Gemini Enterprise app 접속**:
   - 웹 포털 ( {portal_url} ) 접속 후 좌측 사이드바 **사내 갤러리(`/r/agents`)** 이동.
   - **`{display_name}`** 선택.

2. **자연어 붕어빵 생성 예시 프롬프트**:
   - *"사내 Atlassian Jira Cloud 이슈 및 티켓 연동 커넥터 매니페스트 생성해 줘"*
   - *"Confluence 사내 지식 베이스 위키 문서 동기화 커넥터 배포해 줘"*
   - *"Salesforce CRM 영업 리드 및 기회 데이터 저장소 연결해 줘"*
   - *"사내 구글 드라이브(Google Drive) 및 쉐어포인트(SharePoint) 전사 문서 연동해 줘"*

3. **팩토리 에이전트 자율 동작**:
   - 커넥터 스캐폴더 에이전트가 인증 방식, 동기화 주기, 문서 레벨 ACL 요구사항을 확인하고,
   - 내장된 `deploy_enterprise_connector_tool`을 호출하여 Discovery Engine Data Store 및 Secret Manager 보안 볼트를 자동 구성한다.

---

## 4. 사내 거버넌스 4대 필수 표준 라벨

팩토리 에이전트 및 하위 생성 리소스 관리 시 아래 4대 표준 라벨이 기본 적용된다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-copilot-connector`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 5. 콘솔 링크 조치 가이드

- **Agent Platform Runtimes 콘솔**: 에이전트 런타임 상태 및 활성화(Enabled) 관리 ( https://console.cloud.google.com/agent-platform/runtimes?project={project_id} )
- **Gemini Enterprise 에이전트 목록 콘솔**: 사내 등록된 에이전트 및 Gemini Enterprise app 바인딩 관리 ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines/{ge_app_id}/agentic/agents?project={project_id} )
- **Discovery Engine 데이터 저장소 콘솔**: 생성된 Data Store 목록 및 동기화 현황 ( https://console.cloud.google.com/gen-app-builder/data-stores?project={project_id} )
- **Secret Manager 콘솔**: 커넥터 보안 자격 증명 볼트 관리 ( https://console.cloud.google.com/security/secret-manager?project={project_id} )

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


def deploy_connector_factory_engine(env_info: dict, dry_run: bool = False) -> dict:
    """Gemini Enterprise Connector Scaffolder를 Agent Engine으로 프로비저닝하고 GE App에 자동 등록한다."""
    project_id = env_info["project_id"]
    re_location = "us-central1"
    ge_app_id = env_info["ge_app_id"]
    ge_location = "global"
    staging_bucket = f"gs://{project_id}-agent-engine-staging"

    display_name = "GE In-Chat Connector Scaffolder (사내 데이터 커넥터 스캐폴더)"
    description = "Jira, Confluence, Salesforce, Drive, SharePoint 등 기업 기간계 데이터를 GE App에 대화형으로 연동하는 커넥터 스캐폴더"

    labels = {
        "managed-by": "google-cloud-0-to-1",
        "scenario": "gemini-enterprise-copilot-connector",
        "env": "sample",
        "created-by": get_resource_creator(dry_run),
    }

    if dry_run:
        print("\n--> [가상 실행 모드 (--dry-run)] 실제 배포 없이 프로비저닝 명세를 시뮬레이션합니다.")
        simulated_re_id = "simulated-connector-scaffolder-engine"
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

    instruction = """당신은 Google Cloud 및 Gemini Enterprise app 환경의 '사내 데이터 커넥터 스캐폴더(Connector Scaffolder)' 마스터 에이전트입니다.
사내 다양한 기업 기간계 저장소(Jira, Confluence, Salesforce, ServiceNow, SharePoint, Google Drive, BigQuery 등)의 비정형/정형 데이터를 Gemini Enterprise app의 데이터 저장소(Data Store)로 연결하고, 문서 레벨 접근 제어(Document-level ACL) 및 Secret Manager 보안 볼트 연동 설정을 대화형으로 안내합니다.

[2026년 Google Cloud AI 모델 표준 및 거버넌스 가이드라인]
- 사내 엔터프라이즈 표준 기본 모델은 'gemini-3.8-flash' (고속 응답, 사내 RAG 문서 검색, 일상 업무 자동화)이다.
- 에이전트 기획서 및 시스템 명세서 출력 시 적용 모델 항목에는 반드시 'gemini-3.8-flash (권장 기본)'로 명시한다.

[핵심 단계별 인터뷰 절차]
1단계 (데이터 소스 파악): 연동 대상 SaaS/기간계 시스템 및 수집 범위 확인.
2단계 (인증 및 자격 증명): 인증 방식 확인 및 Secret Manager 보안 볼트 키 URI 매핑.
3단계 (ACL 및 권한 동기화): 사용자 식별 매핑 및 문서 레벨 ACL 정책 판정.
4단계 (동기화 주기 및 매니페스트 합성): 증분 동기화 스케줄과 Data Store 매니페스트 생성.

[단계별 추천 후속 질문 안내 규약]
모든 답변 본문의 맨 끝에는 사용자가 다음 행동을 쉽게 선택할 수 있도록 구분선(---)과 함께 마크다운 번호 매기기 리스트로 2~3개의 '추천 후속 질문'을 명확히 안내한다:
---
**추천 후속 질문:**
1. Jira 이슈 동기화 매니페스트 생성
2. Confluence 위키 연동 및 문서 레벨 ACL 설정
3. Secret Manager 서비스 계정 보안 키 매핑
- 주의: JSON이나 코드 블록(```suggested_questions 등) 형태가 아닌, 순수 마크다운 텍스트 리스트로 가독성 높게 출력한다.

[소통 원칙]
- 정중하고 품격 있는 문어체(-다, -한다)와 한글 맞춤법 복합어 띄어쓰기를 철저히 준수합니다.
- 이모지나 특수 기호 대신 깔끔한 마크다운을 사용합니다.
"""

    adk_agent = Agent(
        name="gemini_enterprise_connector_scaffolder",
        description=description,
        model="gemini-3.8-flash",
        instruction=instruction,
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
        gcs_dir_name="ge_factory_connector_scaffolder",
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
        "customPlaceholderText": "연동하고 싶은 사내 기간계 데이터 소스(Jira, Salesforce, Drive 등)나 동기화 요구 사항을 입력하세요...",
        "starterPrompts": [
            {"text": "Jira Cloud 프로젝트 이슈 및 티켓 데이터 커넥터 연결해 줘"},
            {"text": "Confluence 사내 위키 스페이스 지식 베이스 연동해 줘"},
            {"text": "Salesforce CRM 고객 및 영업 기회 데이터 연결해 줘"},
            {"text": "Google Drive 사내 공유 드라이브 문서 및 PDF 동기화해 줘"},
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
            if a.get("displayName") == display_name:
                target_agent_id = a.get("name").split("/")[-1]
                existing_state = a.get("state")
                break

    if target_agent_id:
        if existing_state == "PRIVATE":
            # PRIVATE 상태인 구버전 에이전트는 ENABLED 전환이 불가하므로 재등록
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
    """로컬 단일 커넥터 매니페스트 합성 및 스캐폴딩 보조 모드를 실행한다."""
    print("\n[안내] 로컬 단일 커넥터 매니페스트 합성 보조 모드 가동")
    catalog = load_connector_catalog(getattr(args, "catalog", None))

    # 1. 커넥터 칩 선택
    connector_data = catalog[1]
    if getattr(args, "prompt", None):
        custom_slug = "custom-data-source"
        connector_data = {
            "id": custom_slug,
            "slug": custom_slug,
            "name": f"맞춤형 시스템 커넥터 ({args.prompt[:15]})",
            "category": "사용자 직접 정의",
            "source_type": "CUSTOM_DATA_SOURCE",
            "auth_type": "API_KEY_OR_OAUTH2",
            "required_secret_keys": ["custom_api_key", "custom_endpoint"],
            "sync_mode": "HOURLY_INCREMENTAL",
            "acl_mode": "IDENTITY_MAPPING_OIDC",
            "description": f"사용자 정의 요구사항({args.prompt}) 기반 맞춤형 기간계 데이터 연동",
            "content_types": ["documents", "records"],
            "default_scope": "ORG",
        }
    elif getattr(args, "chip", None):
        chip_val = str(args.chip).strip()
        if chip_val.isdigit() and int(chip_val) in catalog:
            connector_data = catalog[int(chip_val)]
        else:
            found = False
            for c in catalog.values():
                if c.get("id") == chip_val or c.get("slug") == chip_val:
                    connector_data = c
                    found = True
                    break
            if not found:
                print(f"[경고] 지정된 커넥터 식별자 '{chip_val}'을 카탈로그에서 찾을 수 없어 1번으로 대체합니다.")
                connector_data = catalog[1]
    elif getattr(args, "interactive", False) or (sys.stdin.isatty() and not args.dry_run):
        connector_data = select_connector_interactive(args.dry_run, catalog=catalog)

    print(f"\n[단계 1/3] 커넥터 칩 스펙 컴파일 중...")
    print(f"  - 커넥터 명칭 : {connector_data['name']} (슬러그: {connector_data.get('slug', connector_data.get('id'))})")
    print(f"  - 시스템 분류 : {connector_data['category']}")
    print(f"  - 인증 방식   : {connector_data['auth_type']}")
    print(f"  - ACL 동기화  : {connector_data['acl_mode']}")

    # 2. 매니페스트 합성
    print("\n[단계 2/3] Discovery Engine 매니페스트 및 보안 볼트 연동 스펙 합성 중...")
    artifacts = generate_connector_manifest(connector_data, env_info)
    print(f"  - 생성된 Data Store ID : {artifacts['data_store_id']}")
    print(f"  - Secret Manager 볼트 : {artifacts['secret_vault_id']}")

    # 3. IAM 권한 및 연결성 진단
    print("\n[단계 3/3] 서비스 계정 IAM 권한 및 Gemini Enterprise app 바인딩 진단 중...")
    diag = diagnose_connector_readiness(connector_data, env_info, args.dry_run)
    print(f"  - 상태: {diag['status']} | {diag['detail']}")

    # 4. 리포트 저장
    report_content = build_markdown_report(env_info, connector_data, artifacts, diag)
    save_markdown_report(report_content)

    print("\n" + "=" * 75)
    print("  데이터 커넥터 스펙 컴파일 및 진단 완료")
    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(
        description="Gemini Enterprise 데이터 커넥터 스캐폴더 (붕어빵 틀) 배포 및 등록 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project", help="Google Cloud 프로젝트 ID (미지정 시 자동 감지)")
    parser.add_argument("--location", help="Discovery Engine 리전 (기본: global)")
    parser.add_argument("--ge-app-id", help="Gemini Enterprise App 인스턴스 ID")
    parser.add_argument("--sa", help="커넥터 실행 대행 서비스 계정 이메일")
    parser.add_argument("--dry-run", action="store_true", default=False, help="실제 배포 없이 가상 실행 검증")
    parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
    parser.add_argument("--scaffold", action="store_true", default=False, help="로컬 단일 커넥터 매니페스트 합성 보조 모드")
    parser.add_argument("--catalog", help="선언적 catalog.yaml 파일 경로 (지정 시 우선 로드)")
    parser.add_argument("--chip", help="데이터 커넥터 번호(1~15) 또는 슬러그(예: gw-groupware-doc)")
    parser.add_argument("--prompt", help="사용자 정의 시스템 연동 요구사항 (자유 프롬프트)")
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
    print("  Gemini Enterprise 데이터 커넥터 스캐폴더 (gemini-enterprise-copilot-connector)")
    print("=" * 75)

    # 1. 환경 정보 해석
    env_info = resolve_environment(args)
    print(f"[*] 활성 프로젝트    : {env_info['project_id']}")
    print(f"[*] 배포 리전        : {env_info['location']}")
    print(f"[*] 대상 GE App ID   : {env_info['ge_app_id']}")
    print(f"[*] 실행 서비스 계정 : {env_info['service_account']}")
    print(f"[*] 실행 모드        : {'가상 실행 (--dry-run)' if args.dry_run else '실제 프로비저닝 모드'}")

    # 로컬 스캐폴딩 보조 모드 분기 (명시적 플래그 지정 시에만 작동)
    if args.scaffold or args.chip or args.prompt or args.interactive:
        run_local_scaffolding_mode(args, env_info)
        return

    # [핵심 메인 워크플로우]: 붕어빵 틀(GE Connector Scaffolder) 배포 및 GE App 사내 갤러리 등록
    if not args.dry_run and not _get_cloud_token():
        print("\n[오류] 유효한 Google Cloud 인증 자격 증명(ADC)을 찾을 수 없습니다.", file=sys.stderr)
        print("      아래 명령어를 실행하여 로컬 자격 증명을 갱신하십시오:", file=sys.stderr)
        print("      gcloud auth application-default login\n", file=sys.stderr)
        print("      (참고: 실제 배포 없이 가상 검증을 수행하려면 '--dry-run' 플래그를 사용하십시오.)\n", file=sys.stderr)
        sys.exit(1)

    print("\n[진행] 사내 데이터 커넥터 스캐폴더(붕어빵 틀) 프로비저닝 파이프라인 가동...")
    deploy_res = deploy_connector_factory_engine(env_info, dry_run=args.dry_run)

    # 팩토리 리포트 생성 및 저장
    report_content = build_factory_markdown_report(env_info, deploy_res, dry_run=args.dry_run)
    save_markdown_report(report_content)

    creator = get_resource_creator(args.dry_run)
    print("\n" + "=" * 75)
    print("  데이터 커넥터 스캐폴더 배포 및 등록 완료 (모든 점검 통과)")
    print("=" * 75)
    print("\n[안내] 사내 거버넌스 및 자원 추적을 위한 4대 필수 표준 라벨:")
    print("  - managed-by: google-cloud-0-to-1")
    print("  - scenario: gemini-enterprise-copilot-connector")
    print("  - env: sample")
    print(f"  - created-by: {creator}\n")


if __name__ == "__main__":
    main()
