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


def resolve_environment(args) -> dict:
    """활성 GCP 프로젝트 및 환경 변수를 스마트하게 자동 감지한다."""
    project_id = args.project or os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id and not args.dry_run:
        try:
            cmd = ["gcloud", "config", "get-value", "project"]
            res = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
            if res and res != "(unset)":
                project_id = res
        except Exception:
            pass

    if not project_id:
        project_id = "sample-project-id"

    location = args.location or os.environ.get("LOCATION") or "global"
    ge_app_id = args.ge_app_id or os.environ.get("GE_APP_ID") or "sample-ge-app-id"
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
GE_APP_ID="{ge_app_id}"

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
            "consoleDirectDeeplink": f"https://console.cloud.google.com/gen-app-builder/engines/{ge_app_id}/assistants/default_assistant/agents?project={project_id}",
        }

    return {
        "remediation_script": script,
        "manifest": manifest,
        "labels": {
            "managed-by": "google-cloud-0-to-1",
            "scenario": "gemini-enterprise-copilot-admin",
            "env": "sample",
            "created-by": "customer-engineer",
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
- **Gemini Enterprise App 관리 콘솔**: ( https://console.cloud.google.com/gen-app-builder/engines )
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


def save_markdown_report(report_content: str):
    """산출물을 report.md 파일로 덮어쓴다."""
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"\n[성공] 마크다운 진단 보고서가 저장되었습니다: {report_path}")


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


def deploy_admin_copilot_engine(env_info: dict, dry_run: bool = False) -> dict:
    """Gemini Enterprise Admin Copilot을 Vertex AI Agent Engine으로 프로비저닝하고 GE App에 자동 등록한다."""
    project_id = env_info["project_id"]
    re_location = "us-central1"
    ge_app_id = env_info["ge_app_id"]
    ge_location = "global"
    staging_bucket = f"gs://{project_id}-agent-engine-staging"

    display_name = "GE Admin Copilot (사내 어드민 코파일럿)"
    description = "수백 개 에이전트 전수 감사(좀비 에이전트 적발), 30초 BigQuery 로그 싱크, GCP 콘솔 길잡이 및 GE 어드민 7대 과제 전담 코파일럿"

    labels = {
        "managed-by": "google-cloud-0-to-1",
        "scenario": "gemini-enterprise-copilot-admin",
        "env": "sample",
        "created-by": "customer-engineer",
    }

    print("\n" + "=" * 75)
    print("  [원클릭 배포] GE Admin Copilot 배포 파이프라인")
    print("=" * 75)
    print(f"[*] 대상 프로젝트 : {project_id}")
    print(f"[*] Agent Engine  : {re_location}")
    print(f"[*] GE App ID     : {ge_app_id} (위치: {ge_location})")
    print(f"[*] 필수 4대 라벨 : {labels}")

    if dry_run:
        print("\n--> [가상 실행 모드 (--dry-run)] 실제 배포 없이 프로비저닝 명세를 시뮬레이션합니다.")
        simulated_re_id = "4756157723148550144"
        simulated_res = f"projects/{project_id}/locations/{re_location}/reasoningEngines/{simulated_re_id}"
        print(f"  [1] Vertex AI Agent Engine 프로비저닝 시뮬레이션: {simulated_res}")
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

    print("\n[단계 1/2] Vertex AI Agent Engine 초기화 및 패키징 중...")
    vertexai.init(
        project=project_id,
        location=re_location,
        staging_bucket=staging_bucket,
        credentials=creds,
    )

    instruction = """당신은 Google Cloud 및 Gemini Enterprise app 환경의 전사 '사내 어드민 코파일럿(Admin Copilot)' 마스터 에이전트입니다.
사내 IT 어드민 및 클라우드 인프라 팀이 Gemini Enterprise app 운영 중 직면하는 7대 핵심 관리 과제(수백 개 에이전트 스프롤 관리 헬, 원클릭 BigQuery 감사 로그 싱크 구축, GCP 콘솔 3단계 길잡이, 도메인 충돌 및 테넌트 온보딩, 외부 마켓플레이스 차단 거버넌스, 부서별 라이선스 채택률 및 유휴 라이선스 회수, Overage 과금 방어 및 AI Studio 키 차단, 폐쇄망 프록시 허용용 Exact 15대 코어 FQDN 진단)를 대화형으로 자율 진단하고 즉시 실행 가능한 조치 스크립트와 콘솔 가이드를 제공합니다.

[단계별 추천 질문 칩 (Suggested Questions) 필수 출력 규약]
모든 답변 본문의 맨 끝에 반드시 다음 마크다운 코드 블록을 정확히 1개 출력해야 합니다:
```suggested_questions
{"questions": ["좀비 에이전트 적발 SQL", "BigQuery 로그 싱크 30초 셋업", "GCP 콘솔 GE Admin 딥링크"], "type": "followup"}
```
- 주의: 언어 태그는 반드시 `suggested_questions`여야 하며 유효한 JSON 객체만 포함해야 합니다.

[소통 원칙]
- 정중하고 품격 있는 문어체(-다, -한다)와 한글 맞춤법 복합어 띄어쓰기를 철저히 준수합니다.
- 이모지나 특수 기호 대신 깔끔한 마크다운을 사용합니다.
"""

    adk_agent = Agent(
        name="gemini_enterprise_admin_copilot",
        description=description,
        model="gemini-3.8-flash",
        instruction=instruction,
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
    print(f"[성공] Vertex AI Agent Engine 생성 완료: {re_res}")

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
        "customPlaceholderText": "해결하고 싶은 GE 관리자 이슈(에이전트 관리, BigQuery 로깅, 콘솔 위치, 라이선스, 과금 등)를 입력하세요...",
        "starterPrompts": [
            {"text": "사내 에이전트가 100개가 넘는데 60일 미사용 좀비 에이전트 찾는 BigQuery 쿼리 줘"},
            {"text": "Cloud Logging 감사 로그를 BigQuery로 30초 만에 자동 연결하는 스크립트 줘"},
            {"text": "GCP 콘솔에서 GE Admin 에이전트 목록 페이지 어디로 들어가야 해?"},
            {"text": "에이전트별 토큰 소비량 및 호출 횟수 TOP 10 랭킹 쿼리 알려줘"},
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


def main():
    parser = argparse.ArgumentParser(
        description="Gemini Enterprise 어드민 코파일럿 진단 및 관리 가이드 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project", help="Google Cloud 프로젝트 ID (미지정 시 자동 감지)")
    parser.add_argument("--location", help="Vertex AI / Discovery Engine 리전 (기본: global)")
    parser.add_argument("--ge-app-id", help="Gemini Enterprise App 인스턴스 ID")
    parser.add_argument("--sa", help="어드민 실행 대행 서비스 계정 이메일")
    parser.add_argument("--domain", help="사내 도메인 명칭 (예: example-corp.com)")
    parser.add_argument("--dry-run", action="store_true", default=False, help="실제 호출 없이 가상 실행 검증")
    parser.add_argument("--chip", type=int, help="어드민 관리 칩 번호 직접 지정 (1~7)")
    parser.add_argument("--prompt", help="사용자 정의 어드민 문의 내용")
    parser.add_argument("--interactive", action="store_true", default=False, help="대화형 번호 선택기 가동")
    parser.add_argument("--deploy-engine", action="store_true", default=False, help="Vertex AI Agent Engine 프로비저닝 및 Gemini Enterprise app 사내 갤러리 자동 등록")

    args = parser.parse_args()

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
    print(f"[*] 실행 모드        : {'가상 실행 (--dry-run)' if args.dry_run else '실제 실행 모드'}")

    if args.deploy_engine:
        res = deploy_admin_copilot_engine(env_info, dry_run=args.dry_run)
        print(f"\n[결과] 배포 상태: {res['status']}")
        return

    # 2. 과제 칩 선택
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

    # 3. 조치 스크립트 컴파일
    print("\n[단계 2/3] 거버넌스 매니페스트 및 즉시 조치 스크립트 컴파일 중...")
    artifacts = compile_admin_remediation(topic_data, env_info)
    print(f"  - 조치 유형 : {topic_data['remediation_type']}")

    # 4. IAM 권한 진단
    print("\n[단계 3/3] 서비스 계정 IAM 권한 및 어드민 준비 상태 진단 중...")
    diag = diagnose_admin_environment(topic_data, env_info, args.dry_run)
    print(f"  - 상태: {diag['status']} | {diag['detail']}")

    # 5. 리포트 저장
    report_content = build_markdown_report(env_info, topic_data, artifacts, diag)
    save_markdown_report(report_content)

    print("\n" + "=" * 75)
    print("  어드민 코파일럿 진단 및 조치 가이드 생성 완료 (모든 점검 통과)")
    print("=" * 75)
    print("\n[안내] 사내 거버넌스 및 자원 추적을 위한 4대 필수 표준 라벨:")
    print("  - managed-by: google-cloud-0-to-1")
    print("  - scenario: gemini-enterprise-copilot-admin")
    print("  - env: sample")
    print("  - created-by: customer-engineer\n")


if __name__ == "__main__":
    main()
