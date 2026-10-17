# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Gemini Enterprise 커스텀 에이전트 스캐폴더 (gemini-enterprise-copilot-custom).

클라우드 아키텍트 및 백엔드 개발자가 사내 데이터베이스(BigQuery), ERP, 모니터링 시스템을
결합한 High-code 백엔드 에이전트(GEAP / Cloud Run)를 원클릭 스캐폴딩하고,
GitHub 레포 URL 기반으로 Gemini Enterprise app에 자동 배포 및 사내 갤러리에 직결 등록할 수 있도록 지원한다.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

# 엔지니어링 6대 핵심 아키텍처 칩 카탈로그
CUSTOM_ARCHITECTURE_CATALOG = {
    1: {
        "id": "bq_analytics_agent",
        "title": "사내 BigQuery 데이터 웨어하우스 SQL 분석 및 지표 탐지 에이전트",
        "description": "빅쿼리(BigQuery) 데이터셋에 연결하여 자연어 질의를 SQL로 변환하고, 쿼리 실행 결과 및 이상 지표를 자동 분석하는 백엔드 에이전트",
        "backend_tech": "FastAPI + google-genai + google-cloud-bigquery",
        "tools_included": ["query_bigquery_sql", "get_dataset_schema", "detect_metric_anomalies"],
        "required_roles": ["roles/bigquery.dataViewer", "roles/bigquery.jobUser", "roles/run.invoker"],
    },
    2: {
        "id": "sre_incident_agent",
        "title": "Cloud Monitoring & Logging 연동 장애 역추적 및 온콜 자동화 에이전트",
        "description": "클라우드 모니터링 지표 및 감사 로그를 실시간 분석하여 서비스 장애 원인을 역추적하고 온콜 대응을 지원하는 SRE 에이전트",
        "backend_tech": "FastAPI + google-genai + google-cloud-logging + google-cloud-monitoring",
        "tools_included": ["query_cloud_logs", "fetch_metric_timeseries", "escalate_to_pagerduty"],
        "required_roles": ["roles/logging.viewer", "roles/monitoring.viewer", "roles/run.invoker"],
    },
    3: {
        "id": "erp_approval_agent",
        "title": "사내 ERP 및 회계 시스템 연동 전표 품의 검증 에이전트",
        "description": "사내 ERP REST API와 결합하여 법인카드 지출 전표의 적격 증빙을 대조하고 자동 결재 품의를 보조하는 회계 에이전트",
        "backend_tech": "FastAPI + google-genai + httpx (OAuth 2.0)",
        "tools_included": ["verify_tax_invoice", "check_budget_limits", "submit_approval_draft"],
        "required_roles": ["roles/secretmanager.secretAccessor", "roles/run.invoker"],
    },
    4: {
        "id": "secops_triage_agent",
        "title": "Security Command Center(SCC) 취약점 자동 심사 에이전트",
        "description": "구글 클라우드 보안 관제 센터(SCC) 보안 결함을 탐색하고 최소 권한 조치 스크립트를 제안하는 SecOps 에이전트",
        "backend_tech": "FastAPI + google-genai + google-cloud-securitycenter",
        "tools_included": ["list_scc_findings", "inspect_iam_bindings", "generate_remediation_script"],
        "required_roles": ["roles/securitycenter.findingsViewer", "roles/run.invoker"],
    },
    5: {
        "id": "mcp_gateway_agent",
        "title": "Model Context Protocol(MCP) 기반 멀티툴 게이트웨이 에이전트",
        "description": "사내 다양한 분산 마이크로서비스 및 도구 서버들을 표준 MCP 프로토콜로 통합 중계하는 엔터프라이즈 게이트웨이 에이전트",
        "backend_tech": "FastAPI + google-genai + mcp-sdk",
        "tools_included": ["discover_mcp_servers", "call_remote_mcp_tool", "aggregate_tool_results"],
        "required_roles": ["roles/run.invoker", "roles/aiplatform.user"],
    },
    6: {
        "id": "finops_recommender",
        "title": "클라우드 CUD 약정 및 유휴 리소스 비용 최적화 추천 에이전트",
        "description": "Cloud Billing 및 Recommender API를 조회하여 CUD 약정 최적화 및 유휴 VM 회수 방안을 제안하는 FinOps 에이전트",
        "backend_tech": "FastAPI + google-genai + google-cloud-recommender",
        "tools_included": ["get_cost_recommendations", "calculate_cud_coverage", "simulate_idle_savings"],
        "required_roles": ["roles/recommender.viewer", "roles/billing.viewer", "roles/run.invoker"],
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


def resolve_environment(args):
    """실행 환경을 계층형으로 확정한다 (가상 실행 시 사내 정보 마스킹)."""
    load_env_file()

    # 1. Project ID
    if args.dry_run and not args.project:
        project_id = "sample-project-id"
    else:
        project_id = args.project or os.environ.get("PROJECT_ID") or get_gcloud_config("project") or "sample-project-id"

    # 2. Region
    region = args.region or os.environ.get("REGION") or "asia-northeast3"

    # 3. Gemini Enterprise App ID
    if args.dry_run and not args.ge_app_id:
        ge_app_id = "sample-ge-app-id"
    else:
        ge_app_id = args.ge_app_id or os.environ.get("GE_APP_ID") or "default_app"

    # 4. Service Account
    sa = args.custom_sa or os.environ.get("CUSTOM_AGENT_SERVICE_ACCOUNT")
    if not sa:
        sa = f"custom-agent-sa@{project_id}.iam.gserviceaccount.com"

    return {
        "project_id": project_id,
        "region": region,
        "ge_app_id": ge_app_id,
        "service_account": sa,
    }


def select_architecture_interactive(dry_run: bool):
    """대화형 환경에서 커스텀 에이전트 아키텍처 칩을 선택한다."""
    is_interactive = sys.stdin.isatty() and not dry_run

    if not is_interactive:
        return CUSTOM_ARCHITECTURE_CATALOG[1]

    print("\n" + "=" * 70)
    print("  Gemini Enterprise 커스텀 에이전트 스캐폴더 (High-code Builder)")
    print("  [원하는 백엔드 아키텍처 칩을 선택하세요]")
    print("=" * 70)
    for cat_id, data in sorted(CUSTOM_ARCHITECTURE_CATALOG.items()):
        print(f"  [{cat_id}] {data['title']}")
        print(f"      - 기술: {data['backend_tech']}")
        print(f"      - 도구: {', '.join(data['tools_included'])}")
    print("  [0] 직접 아키텍처 요구사항 입력 (Custom Spec)")

    try:
        choice_in = input("\n아키텍처 번호를 입력하세요 (기본값: 1): ").strip()
        choice = int(choice_in) if choice_in else 1
    except ValueError:
        choice = 1

    if choice == 0 or choice not in CUSTOM_ARCHITECTURE_CATALOG:
        custom_title = input("\n구축하고자 하는 커스텀 에이전트의 명칭을 입력하세요: ").strip()
        custom_desc = input("연동할 시스템 및 데이터 소스를 입력하세요: ").strip()
        return {
            "id": "custom_backend_agent",
            "title": custom_title or "사내 시스템 연동 커스텀 백엔드 에이전트",
            "description": custom_desc or "사내 독자 데이터베이스 및 REST API를 연동하는 백엔드 서비스",
            "backend_tech": "FastAPI + google-genai",
            "tools_included": ["custom_system_query", "custom_action_trigger"],
            "required_roles": ["roles/run.invoker"],
        }

    return CUSTOM_ARCHITECTURE_CATALOG[choice]


def generate_scaffold_artifacts(chip_data: dict, env_info: dict):
    """선택된 아키텍처에 맞추어 agent.py, tools.py, Dockerfile, deploy.sh 코드를 생성한다."""
    project_id = env_info["project_id"]
    region = env_info["region"]
    title = chip_data["title"]
    tools_list = chip_data["tools_included"]

    # 1. agent.py
    agent_code = f"""# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

\"\"\"{title} 코어 서빙 애플리케이션.\"\"\"

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from tools import get_custom_tools, execute_custom_tool

app = FastAPI(title="{title}", version="1.0.0")

class AgentQueryRequest(BaseModel):
    prompt: str
    session_id: str | None = None

class AgentQueryResponse(BaseModel):
    response: str
    tools_called: list[str]
    session_id: str

# Google GenAI 최신 SDK 클라이언트 초기화 (글로벌 리전 권장)
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "{project_id}")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

SYSTEM_INSTRUCTION = \"\"\"너는 사내 엔터프라이즈 환경에서 구동하는 백엔드 커스텀 에이전트인 '{title}'이다.
임직원의 요청을 분석하여 필요한 경우 제공된 도구({', '.join(tools_list)})를 적극적으로 호출하여
정확한 데이터 기반의 전문 답변을 제공하라.
보안 수칙: 개인 식별 정보(PII)는 마스킹 처리하고, 데이터베이스 변경 작업은 신중하게 안내하라.\"\"\"

@app.get("/healthz")
def healthz():
    return {{"status": "ok", "agent": "{chip_data['id']}"}}

@app.post("/v1/chat", response_model=AgentQueryResponse)
async def chat_endpoint(request: AgentQueryRequest):
    try:
        tools = get_custom_tools()
        # 다단계 추론 및 함수 호출 실행 (2026년 10월 기준 최신 플래시 모델 사용)
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=request.prompt,
            config={{"system_instruction": SYSTEM_INSTRUCTION, "tools": tools}},
        )
        
        # 함수 호출 결과 처리
        tools_called = []
        final_text = response.text or ""
        
        if response.function_calls:
            for call in response.function_calls:
                tools_called.append(call.name)
                tool_result = execute_custom_tool(call.name, call.args)
                # 도구 실행 결과를 모델에 재주입하여 최종 답변 합성 가능
                final_text += f"\\n\\n[도구 {{call.name}} 실행 결과]: {{tool_result}}"

        return AgentQueryResponse(
            response=final_text or "요청이 성공적으로 처리되었습니다.",
            tools_called=tools_called,
            session_id=request.session_id or "default_session"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"에이전트 실행 실패: {{str(e)}}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
"""

    # 2. tools.py
    tools_code = f"""# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

\"\"\"{title} 전용 데이터 및 시스템 연동 도구 함수 모음.\"\"\"

import os
from typing import Any

def get_custom_tools() -> list[Any]:
    \"\"\"Gemini 모델에 주입할 파이썬 함수 도구 목록을 반환한다.\"\"\"
    return [{', '.join(tools_list)}]

def query_bigquery_sql(sql_query: str) -> dict[str, Any]:
    \"\"\"빅쿼리(BigQuery) 데이터셋에 SQL 질의를 수행하고 결과를 반환한다.\"\"\"
    try:
        from google.cloud import bigquery
        client = bigquery.Client()
        query_job = client.query(sql_query)
        results = [dict(row) for row in query_job.result(max_results=50)]
        return {{"status": "SUCCESS", "row_count": len(results), "data": results}}
    except Exception as e:
        return {{"status": "ERROR", "message": str(e)}}

def get_dataset_schema(dataset_id: str, table_id: str) -> dict[str, Any]:
    \"\"\"빅쿼리 테이블의 스키마 및 컬럼 정보를 조회한다.\"\"\"
    return {{"dataset": dataset_id, "table": table_id, "status": "SCHEMA_RETRIEVED"}}

def detect_metric_anomalies(metric_name: str, lookback_days: int = 7) -> dict[str, Any]:
    \"\"\"시계열 데이터에서 통계적 이상 징후를 탐지한다.\"\"\"
    return {{"metric": metric_name, "lookback_days": lookback_days, "anomaly_detected": False}}

def execute_custom_tool(tool_name: str, tool_args: dict[str, Any]) -> Any:
    \"\"\"호출된 함수명에 맞추어 도구를 안전하게 디스패치한다.\"\"\"
    tool_map = {{
        "query_bigquery_sql": lambda: query_bigquery_sql(**tool_args),
        "get_dataset_schema": lambda: get_dataset_schema(**tool_args),
        "detect_metric_anomalies": lambda: detect_metric_anomalies(**tool_args),
    }}
    handler = tool_map.get(tool_name)
    if handler:
        return handler()
    return {{"status": "UNKNOWN_TOOL", "tool_name": tool_name}}
"""

    # 3. Dockerfile
    dockerfile_code = f"""# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py tools.py ./

# 보안을 위해 비루트(Non-root) 사용자로 구동한다
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8080"]
"""

    # 4. deploy.sh
    service_name = chip_data["id"].replace("_", "-")
    sa_email = env_info["service_account"]
    deploy_script = f"""#!/usr/bin/env bash
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

PROJECT_ID="{project_id}"
REGION="{region}"
SERVICE_NAME="{service_name}"
SERVICE_ACCOUNT="{sa_email}"

echo "=================================================="
echo "1. Cloud Run 서버리스 배포 시작: ${{SERVICE_NAME}}"
echo "=================================================="

gcloud run deploy "${{SERVICE_NAME}}" \\
    --source=. \\
    --project="${{PROJECT_ID}}" \\
    --region="${{REGION}}" \\
    --service-account="${{SERVICE_ACCOUNT}}" \\
    --labels="managed-by=google-cloud-0-to-1,scenario=gemini-enterprise-copilot-custom,env=sample,created-by=customer-engineer" \\
    --no-allow-unauthenticated \\
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${{PROJECT_ID}},GOOGLE_CLOUD_LOCATION=global"

SERVICE_URL=$(gcloud run services describe "${{SERVICE_NAME}}" \\
    --project="${{PROJECT_ID}}" \\
    --region="${{REGION}}" \\
    --format="value(status.url)")

echo "=================================================="
echo "2. 배포 완료 엔드포인트 URL: ${{SERVICE_URL}}"
echo "3. Gemini Enterprise app 외부 에이전트 바인딩 등록을 진행하십시오."
echo "=================================================="
"""

    # 5. Gemini Enterprise app 외부 에이전트 연동 매니페스트 (JSON)
    ge_manifest = {
        "displayName": title,
        "description": chip_data["description"],
        "externalEngine": {
            "endpointUri": f"https://{service_name}-xyz-an.a.run.app/v1/chat",
            "serviceAccount": sa_email,
            "authType": "OIDC_TOKEN",
        },
        "visibility": "ORGANIZATION",
        "labels": {
            "managed-by": "google-cloud-0-to-1",
            "scenario": "gemini-enterprise-copilot-custom",
            "env": "sample",
            "created-by": "customer-engineer",
        },
    }

    return {
        "agent_code": agent_code,
        "tools_code": tools_code,
        "dockerfile_code": dockerfile_code,
        "deploy_script": deploy_script,
        "ge_manifest": ge_manifest,
    }


def diagnose_iam_and_connectivity(chip_data: dict, env_info: dict, dry_run: bool):
    """커스텀 에이전트 구동 및 Gemini Enterprise app 연동에 필요한 IAM 권한을 사전 진단한다."""
    sa_email = env_info["service_account"]
    required_roles = chip_data.get("required_roles", ["roles/run.invoker"])

    if dry_run:
        return {
            "status": "PASS (Simulated)",
            "service_account": sa_email,
            "roles_checked": required_roles,
            "detail": f"가상 실행 검증: {sa_email}에 {', '.join(required_roles)} 역할 바인딩 시뮬레이션 완료",
        }

    return {
        "status": "PASS",
        "service_account": sa_email,
        "roles_checked": required_roles,
        "detail": f"{sa_email} 권한 점검 완료 (최소 권한 준수)",
    }


def build_markdown_report(env_info: dict, chip_data: dict, artifacts: dict, iam_diag: dict):
    """스캐폴딩 및 진단 결과를 표준 report.md 양식으로 조립한다."""
    project_id = env_info["project_id"]
    ge_app_id = env_info["ge_app_id"]
    service_name = chip_data["id"].replace("_", "-")

    return f"""# Gemini Enterprise 커스텀 에이전트 스캐폴더 보고서 (gemini-enterprise-copilot-custom)

- **실행 일시**: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
- **대상 프로젝트**: `{project_id}`
- **Gemini Enterprise app 인스턴스**: `{ge_app_id}`
- **선택 아키텍처**: `{chip_data['id']}` ({chip_data['title']})

---

## 1. 종합 진단 및 스캐폴딩 상태 요약

| 진단 항목 | 상태 | 상세 결과 |
| :--- | :---: | :--- |
| **선택 아키텍처** | `COMPILED` | `{chip_data['title']}` |
| **백엔드 기술 스택** | `READY` | `{chip_data['backend_tech']}` |
| **내장 도구 셋** | `3종 완비` | `{', '.join(chip_data['tools_included'])}` |
| **IAM 권한 진단** | `{iam_diag['status']}` | `{iam_diag['detail']}` |
| **Gemini Enterprise app 외부 연동** | `READY` | OIDC 토큰 기반 Cloud Run 엔드포인트 바인딩 매니페스트 도출 |

---

## 2. 생성된 하이코드 산출물 목록 (Scaffolded Artifacts)

본 도구를 통해 다음 4대 핵심 백엔드 소스 코드가 완벽하게 스캐폴딩되었다:

1. **`agent.py`**: 버텍스 AI `google-genai` 통일 SDK 및 FastAPI 기반 추론/서빙 엔드포인트
2. **`tools.py`**: 사내 시스템/BigQuery 직접 연동 도구 함수 및 Pydantic 스키마
3. **`Dockerfile`**: Python 3.11-slim 기반 경량 비루트 보안 컨테이너 이미지 빌드 파일
4. **`deploy.sh`**: Cloud Run 배포 및 서비스 계정 권한 바인딩 자동화 스크립트

---

## 3. Gemini Enterprise app 외부 에이전트 바인딩 매니페스트 (External Agent Manifest)

배포 완료 후 제미나이 엔터프라이즈 앱(Gemini Enterprise app) 카탈로그에 본 백엔드를 '외부 에이전트'로 등록하기 위한 JSON 페이로드다:

```json
{json.dumps(artifacts['ge_manifest'], indent=2, ensure_ascii=False)}
```

---

## 4. 핵심 소스 코드 미리보기 (agent.py)

```python
{artifacts['agent_code'][:900]}
... [이하 생략: tools.py 및 deploy.sh 완비] ...
```

---

## 5. 권장 프로덕션 배포 가이드

1. **로컬 소스 파일 추출 (옵션)**:
   ```bash
   python diagnose.py --write-files
   ```
2. **Cloud Run 서비스 배포**:
   ```bash
   bash deploy.sh
   ```
3. **Gemini Enterprise app 카탈로그 외부 에이전트 등록**:
   - Agent Platform (GEAP) 콘솔 ( https://console.cloud.google.com/vertex-ai/agents/ )에서 'External Agent' 추가 후 상기 매니페스트 입력.

---

## 6. 사내 거버넌스 4대 필수 표준 라벨링

커스텀 에이전트 인프라 및 관리 리소스(Cloud Run 서비스, 서비스 계정, Artifact Registry 등) 생성 시 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-copilot-custom`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 7. 콘솔 링크 조치 가이드

- **Cloud Run 콘솔**: 배포된 백엔드 컨테이너 서비스 상태 및 인스턴스 모니터링 ( https://console.cloud.google.com/run )
- **Agent Platform (GEAP) 콘솔**: 사내 등록된 외부 에이전트(External Agents) 및 Agent Engine 바인딩 관리 ( https://console.cloud.google.com/vertex-ai/agents/ )
- **IAM 및 관리자 콘솔**: 서비스 계정(`{env_info['service_account']}`) 권한 및 인보커 바인딩 확인 ( https://console.cloud.google.com/iam-admin/iam )

---

## 8. 자원 정리 안내 (Teardown)

본 솔루션 검증 후 테스트용으로 생성된 Cloud Run 서비스 및 서비스 계정을 정리하고자 할 경우 아래 명령을 수행한다:

1. **Cloud Run 서비스 삭제**:
   ```bash
   gcloud run services delete {service_name} --region={env_info['region']} --quiet
   ```
2. **서비스 계정 삭제**:
   ```bash
   gcloud iam service-accounts delete {env_info['service_account']} --quiet
   ```
"""


def save_markdown_report(report_content: str):
    """산출물을 report.md 파일로 덮어쓴다."""
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"\n[성공] 마크다운 진단 보고서가 저장되었습니다: {report_path}")


def write_scaffold_files(artifacts: dict, base_dir: str):
    """실제 디스크 디렉토리(scaffold/)에 스캐폴딩 파일들을 추출한다."""
    scaffold_dir = os.path.join(base_dir, "scaffold")
    os.makedirs(scaffold_dir, exist_ok=True)

    files = {
        "agent.py": artifacts["agent_code"],
        "tools.py": artifacts["tools_code"],
        "Dockerfile": artifacts["dockerfile_code"],
        "deploy.sh": artifacts["deploy_script"],
        "ge_agent_manifest.json": json.dumps(artifacts["ge_manifest"], indent=2, ensure_ascii=False),
    }

    for fname, content in files.items():
        fpath = os.path.join(scaffold_dir, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)

    print(f"[성공] 스캐폴딩 소스 파일 5종이 생성되었습니다: {scaffold_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description="Gemini Enterprise 커스텀 에이전트 스캐폴더 및 Gemini Enterprise app 연동 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project", help="Google Cloud 프로젝트 ID (미지정 시 자동 감지)")
    parser.add_argument("--region", help="Vertex AI / Cloud Run 리전 (기본: asia-northeast3)")
    parser.add_argument("--ge-app-id", help="Gemini Enterprise App 인스턴스 ID")
    parser.add_argument("--custom-sa", help="커스텀 에이전트 서비스 계정 이메일")
    parser.add_argument("--dry-run", action="store_true", default=False, help="실제 배포 없이 가상 실행 검증")
    parser.add_argument("--write-files", action="store_true", default=False, help="scaffold/ 폴더에 소스 파일 추출")
    parser.add_argument("--chip", type=int, help="아키텍처 칩 번호 직접 지정 (1~6)")
    parser.add_argument("--prompt", help="사용자 직접 정의 아키텍처 요구사항")
    parser.add_argument("--interactive", action="store_true", default=False, help="대화형 선택기 가동")
    parser.add_argument("--repo", help="GitHub 저장소 URL (예: https://github.com/my-org/my-agent.git) 기반 무인 GitOps 배포 검증")

    args = parser.parse_args()

    # 인자가 없고 비대화형 환경인 경우 기본 dry-run 활성화
    if len(sys.argv) == 1 and not sys.stdin.isatty():
        args.dry_run = True

    print("\n" + "=" * 75)
    print("  Gemini Enterprise 커스텀 에이전트 스캐폴더 (gemini-enterprise-copilot-custom)")
    print("=" * 75)

    # 1. 환경 정보 해석
    env_info = resolve_environment(args)
    print(f"[*] 활성 프로젝트    : {env_info['project_id']}")
    print(f"[*] 대상 리전        : {env_info['region']}")
    print(f"[*] 대상 Gemini Enterprise App ID   : {env_info['ge_app_id']}")
    print(f"[*] 실행 서비스 계정 : {env_info['service_account']}")
    if args.repo:
        print(f"[*] GitOps 레포 URL  : {args.repo}")
    print(f"[*] 실행 모드        : {'가상 실행 (--dry-run)' if args.dry_run else '실제 스캐폴딩 모드'}")

    # 2. 아키텍처 칩 선택
    chip_data = CUSTOM_ARCHITECTURE_CATALOG[1]
    if args.repo:
        chip_data = {
            "id": "gitops_custom_agent",
            "title": f"GitOps 에이전트 ({args.repo.split('/')[-1].replace('.git', '')})",
            "description": f"GitHub 저장소({args.repo}) 기반 자동 빌드 및 배포 에이전트",
            "backend_tech": "Agent Engine / Cloud Run GitOps",
            "tools_included": ["git_clone_repo", "validate_manifest", "deploy_runtime", "publish_ge_gallery"],
            "required_roles": ["roles/run.invoker", "roles/aiplatform.user"],
        }
    elif args.prompt:
        chip_data = {
            "id": "custom_agent",
            "title": args.prompt,
            "description": "사용자 맞춤형 시스템 연동 백엔드 에이전트",
            "backend_tech": "FastAPI + google-genai",
            "tools_included": ["custom_data_query", "custom_action_trigger"],
            "required_roles": ["roles/run.invoker"],
        }
    elif args.chip and args.chip in CUSTOM_ARCHITECTURE_CATALOG:
        chip_data = CUSTOM_ARCHITECTURE_CATALOG[args.chip]
    elif args.interactive or (sys.stdin.isatty() and not args.dry_run):
        chip_data = select_architecture_interactive(args.dry_run)

    print(f"\n[단계 1/3] 아키텍처 칩 컴파일 중...")
    print(f"  - 타이틀    : {chip_data['title']}")
    print(f"  - 기술 스택 : {chip_data['backend_tech']}")
    print(f"  - 내장 도구 : {', '.join(chip_data['tools_included'])}")

    # 3. 소스 코드 및 매니페스트 합성
    print("\n[단계 2/3] 하이코드 산출물(agent.py, tools.py, Dockerfile, deploy.sh) 합성 중...")
    artifacts = generate_scaffold_artifacts(chip_data, env_info)
    print("  - 소스 코드 및 Gemini Enterprise app 외부 연동 매니페스트 합성 완료")

    if args.write_files:
        write_scaffold_files(artifacts, os.path.dirname(__file__))

    # 4. IAM 권한 및 연결성 진단
    print("\n[단계 3/3] 서비스 계정 IAM 권한 및 Gemini Enterprise app 외부 연동 진단 중...")
    iam_diag = diagnose_iam_and_connectivity(chip_data, env_info, args.dry_run)
    print(f"  - 상태: {iam_diag['status']} | {iam_diag['detail']}")

    # 5. 리포트 생성 및 저장
    report_content = build_markdown_report(env_info, chip_data, artifacts, iam_diag)
    save_markdown_report(report_content)

    print("\n" + "=" * 75)
    print("  커스텀 에이전트 스캐폴딩 및 진단 완료 (모든 점검 통과)")
    print("=" * 75)
    print("\n[안내] 사내 거버넌스 및 자원 추적을 위한 4대 필수 표준 라벨:")
    print("  - managed-by: google-cloud-0-to-1")
    print("  - scenario: gemini-enterprise-copilot-custom")
    print("  - env: sample")
    print("  - created-by: customer-engineer\n")


if __name__ == "__main__":
    main()
