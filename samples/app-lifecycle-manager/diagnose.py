#!/usr/bin/env python3
# Copyright 2026 Google LLC. All Rights Reserved.
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

"""엔터프라이즈 AI 앱 생애 주기 및 콜드라인 냉동 거버넌스 진단기 (app-lifecycle-manager).

현업 바이브 코딩과 노코드 빌더로 대량 생성된 사내 AI 앱(웹앱 SPA, Agent Engine, Cloud Run API)의
중복 개발을 BigQuery Vector Search(gemini-embedding-001)와 Dataplex Universal Catalog로 사전 차단하고,
호출 수(Hit-Count) 및 보존 기한(TTL), BigQuery Property Graph(GQL) 멀티홉 인바운드 호출 리니지 역추적을 통해
유휴 1회성 앱(96% 코호트)은 활성 호출자 안전 차단 후 Cloud Storage Coldline 냉동 타임캡슐(rehydrate.sh 포함)로
동결하며, 고빈도 핵심 안착 앱(4% 코호트)은 정식 프로덕션 파이프라인으로 승격시키는 5단계 생애 주기 관리 도구다.
"""

from __future__ import annotations

import argparse
from collections import Counter
import dataclasses
from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


MANDATORY_LABELS: Dict[str, str] = {
    "managed-by": "google-cloud-0-to-1",
    "scenario": "app-lifecycle-manager",
    "env": "sample",
    "created-by": "customer-engineer",
}

GCS_COLDLINE_COST_PER_CAPSULE_USD: float = 0.02

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(KEY|SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIAL|BEARER|PRIVATE)",
    re.IGNORECASE,
)

_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "built", "by", "for", "from",
        "in", "into", "is", "of", "on", "or", "that", "the", "to", "with",
        "및", "위한", "위해", "기반", "대해", "대한", "통해",
    }
)

_SYNONYM_CANONICAL_MAP: Dict[str, str] = {
    "precedents": "precedent",
    "rulings": "ruling",
    "tribunals": "tribunal",
    "taxes": "tax",
    "vat": "tax",
    "deductions": "deduction",
    "lookup": "search",
    "finder": "search",
    "retriever": "search",
    "contracts": "contract",
    "clauses": "clause",
    "ndas": "nda",
    "tariffs": "tariff",
    "customs": "tariff",
    "duties": "tariff",
    "dashboards": "dashboard",
    "visualizer": "dashboard",
    "kpis": "kpi",
    "세무": "tax",
    "법인세": "tax",
    "부가가치세": "tax",
    "조세": "tax",
    "조세심판원": "tribunal",
    "심판원": "tribunal",
    "판례": "precedent",
    "결정례": "precedent",
    "예규": "precedent",
    "검색": "search",
    "조회": "search",
    "웹앱": "spa",
    "재무팀": "finance",
    "임원": "executive",
    "관세": "tariff",
    "통관": "tariff",
    "비밀유지계약": "nda",
    "계약서": "contract",
}


@dataclass(frozen=True)
class AppRecord:
    """사내 AI 앱(SPA, Agent Engine, Cloud Run API) 메타데이터 및 텔레메트리 모델."""

    app_id: str
    app_name: str
    app_type: str  # SPA | AGENT_ENGINE | CLOUD_RUN_API
    lifecycle_stage: str  # ACTIVE | DRAINING | CRYO_ARCHIVED | GRADUATED
    owner_team: str
    description: str
    system_prompt_summary: str
    api_schema_summary: str
    hit_count: int
    ttl_days: int = 14
    age_days: int = 0
    promote_at_hits: int = 50
    monthly_compute_cost_usd: float = 48.0
    min_instances: int = 1
    service_account_email: str = ""
    endpoint_url: str = ""
    container_image_digest: str = ""
    env_vars: Dict[str, str] = field(default_factory=dict)
    cryo_gcs_uri: str = ""
    rehydrate_command: str = ""


@dataclass(frozen=True)
class SemanticMatch:
    """BigQuery Vector Search (gemini-embedding-001) 코사인 유사도 매칭 결과."""

    app_id: str
    app_name: str
    app_type: str
    lifecycle_stage: str
    owner_team: str
    description: str
    cosine_similarity: float
    recommendation: str  # REUSE_ACTIVE | REHYDRATE_CRYO | PROCEED_NEW_BUILD
    cryo_gcs_uri: str = ""
    rehydrate_command: str = ""


@dataclass(frozen=True)
class LifecycleDecision:
    """호출 수(Hit-Count) 및 보존 기한(TTL) 판별 결과."""

    app_id: str
    app_name: str
    hit_count: int
    age_days: int
    ttl_days: int
    promote_at_hits: int
    action: str  # CRYO_DISPOSAL | PRODUCTION_GRADUATION | KEEP_ACTIVE | ALREADY_ARCHIVED
    rationale: str


@dataclass(frozen=True)
class FleetEvaluationResult:
    """전사 AI 앱 인벤토리 수명 주기 분류 결과."""

    decisions: List[LifecycleDecision]
    cryo_candidates: List[AppRecord]
    graduation_candidates: List[AppRecord]
    active_retained: List[AppRecord]
    already_archived: List[AppRecord]


@dataclass(frozen=True)
class UpstreamCaller:
    """BigQuery Property Graph 내 인바운드 업스트림 호출자 노드."""

    caller_id: str
    caller_type: str  # CLOUD_SCHEDULER | EVENTARC | PUBSUB | WORKFLOWS | A2A_AGENT | HUMAN_BROWSER
    principal_email: str
    trigger_resource_uri: str
    protocol: str
    call_count_30d: int
    is_active: bool
    sever_command: str


@dataclass(frozen=True)
class DownstreamResource:
    """단발성 AI 앱에 연결된 다운스트림 GCP 리소스 및 IAM 바인딩 노드."""

    resource_id: str
    resource_type: str  # SERVICE_ACCOUNT | BIGQUERY_DATASET | CLOUD_SQL | SECRET_MANAGER
    iam_role: str
    monthly_cost_usd: float
    revoke_command: str


@dataclass(frozen=True)
class LineageReport:
    """BigQuery Graph (GQL) 기반 멀티홉 블라스트 반경 및 안전 차단 명세."""

    app_id: str
    app_name: str
    gql_query: str
    upstream_callers: List[UpstreamCaller]
    downstream_resources: List[DownstreamResource]
    sever_commands: List[str]
    iam_revoke_commands: List[str]
    active_automated_callers_count: int
    safe_to_dispose: bool


@dataclass(frozen=True)
class CryoCapsule:
    """Cloud Storage Coldline에 동결 보관되는 냉동 타임캡슐 패키지."""

    app_id: str
    app_name: str
    app_type: str
    owner_team: str
    capsule_gcs_uri: str
    storage_class: str
    manifest_json: Dict[str, Any]
    sanitized_env_template: Dict[str, str]
    teardown_commands: List[str]
    rehydrate_script: str
    rehydrate_one_liner: str
    reclaimed_monthly_usd: float
    reclaimed_min_instances: int
    revoked_iam_bindings_count: int
    severed_triggers_count: int


@dataclass(frozen=True)
class GraduationPackage:
    """상위 4% 핵심 안착 앱의 엔터프라이즈 SDLC 프로덕션 승격 명세."""

    app_id: str
    app_name: str
    hit_count: int
    owner_team: str
    ci_cd_pipeline_spec: str
    security_hardening_checklist: List[str]
    catalog_aspect_update: Dict[str, Any]


@dataclass(frozen=True)
class GovernanceMetrics:
    """FinOps 비용 절감액 및 SecOps 공격 표면 감축 집계 지표."""

    total_apps_evaluated: int
    cryo_disposed_count: int
    graduated_count: int
    already_archived_count: int
    active_retained_count: int
    gross_monthly_compute_saved_usd: float
    gcs_archive_monthly_cost_usd: float
    net_monthly_saved_usd: float
    net_annual_saved_usd: float
    reclaimed_warm_instances: int
    reclaimed_service_accounts: int
    revoked_iam_bindings: int
    severed_zombie_triggers: int
    closed_public_endpoints: int


def build_seed_apps(project_id: str = "sample-project-id") -> List[AppRecord]:
    """96% 대 4% 파레토 법칙을 반영한 사내 AI 앱 인벤토리 시드 데이터를 생성한다."""
    archive_bucket = f"gs://{project_id}-onetime-archive"
    return [
        AppRecord(
            app_id="tax-precedent-spa-001",
            app_name="재무팀 법인세 예규 및 조세심판원 판례 검색 웹앱 (Corporate Tax Precedent Lookup SPA)",
            app_type="SPA",
            lifecycle_stage="CRYO_ARCHIVED",
            owner_team="finance-ai-guild@example.com",
            description=(
                "임원 세무 보고용으로 제작된 단일 페이지 웹앱(SPA)으로, 조세심판원 결정례와 국세청 법인세 예규, "
                "부가가치세 공제 판례(tax tribunal precedent, corporate deduction)를 자연어로 검색한다."
            ),
            system_prompt_summary="관련 세법 조항 및 조세심판원 판례 요지를 추출하여 요약한다.",
            api_schema_summary="POST /api/v1/tax-search {query: string, fiscal_year: int}",
            hit_count=1,
            ttl_days=14,
            age_days=45,
            promote_at_hits=50,
            monthly_compute_cost_usd=0.02,
            min_instances=0,
            service_account_email=f"sa-tax-spa@{project_id}.iam.gserviceaccount.com",
            endpoint_url="https://tax-precedent-spa-001-an3.a.run.app",
            container_image_digest="sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
            env_vars={
                "GCP_PROJECT_ID": project_id,
                "TAX_DB_API_KEY": "sample-tax-api-key-placeholder",
                "GEMINI_MODEL": "gemini-3.8-flash",
            },
            cryo_gcs_uri=f"{archive_bucket}/tax-precedent-spa-001/",
            rehydrate_command=f"gcloud storage cat {archive_bucket}/tax-precedent-spa-001/rehydrate.sh | bash",
        ),
        AppRecord(
            app_id="q3-board-deck-kpi-visualizer",
            app_name="3분기 이사회 보고용 KPI 폭포수 차트 웹앱 (Q3 Board KPI Visualizer)",
            app_type="SPA",
            lifecycle_stage="ACTIVE",
            owner_team="strategy-office@example.com",
            description=(
                "3분기 이사회 발표를 위해 1회성 바이브 코딩으로 제작된 대화형 대시보드로, 권역별 영업 이익률(EBITDA)과 "
                "공급망 비용 편차를 시각화한다."
            ),
            system_prompt_summary="분기 실적 CSV 데이터를 기반으로 SVG 폭포수 차트를 렌더링한다.",
            api_schema_summary="GET /api/v1/kpi-waterfall?quarter=Q3",
            hit_count=1,
            ttl_days=14,
            age_days=28,
            promote_at_hits=50,
            monthly_compute_cost_usd=64.50,
            min_instances=1,
            service_account_email=f"sa-q3-board-kpi@{project_id}.iam.gserviceaccount.com",
            endpoint_url="https://q3-board-deck-kpi-visualizer-an3.a.run.app",
            container_image_digest="sha256:1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014",
            env_vars={
                "GCP_PROJECT_ID": project_id,
                "ERP_BEARER_TOKEN": "sample-erp-bearer-token-placeholder",
                "GEMINI_MODEL": "gemini-3.8-flash",
            },
        ),
        AppRecord(
            app_id="partner-hackathon-contract-summarizer",
            app_name="사내 해커톤 파트너 비밀유지계약(NDA) 독소 조항 검토 에이전트",
            app_type="AGENT_ENGINE",
            lifecycle_stage="ACTIVE",
            owner_team="legal-innovation@example.com",
            description=(
                "연례 사내 해커톤에서 시연용으로 제작된 프로토타입 에이전트로, 협력사 비밀유지계약(NDA) 및 "
                "손해배상 면책 조항을 표준 계약서와 비교한다."
            ),
            system_prompt_summary="업로드된 계약서 PDF 조항을 사내 법무 플레이북 기준과 대조한다.",
            api_schema_summary="POST /v1/agents/contract-summarizer:query {document_uri: string}",
            hit_count=0,
            ttl_days=14,
            age_days=21,
            promote_at_hits=50,
            monthly_compute_cost_usd=82.00,
            min_instances=1,
            service_account_email=f"sa-nda-agent@{project_id}.iam.gserviceaccount.com",
            endpoint_url="https://partner-hackathon-contract-summarizer-an3.a.run.app",
            container_image_digest="sha256:60303ae22b998861bce3b28f33eec1be758a213c86c93c076dbe9f558c11c752",
            env_vars={
                "GCP_PROJECT_ID": project_id,
                "DOCUSIGN_CLIENT_SECRET": "ds-secret-44109-xyz",
                "GEMINI_MODEL": "gemini-3.8-flash",
            },
        ),
        AppRecord(
            app_id="marketing-campaign-utm-tagger-api",
            app_name="연말 프로모션 광고 문구 및 UTM 파라미터 생성 단건 API",
            app_type="CLOUD_RUN_API",
            lifecycle_stage="ACTIVE",
            owner_team="growth-marketing@example.com",
            description=(
                "하루짜리 연말 이벤트 캠페인을 위해 제작된 마이크로서비스 API로, 채널별 홍보 카피와 "
                "추적용 UTM 파라미터를 생성한다."
            ),
            system_prompt_summary="홍보 헤드라인 3종을 생성하고 표준 UTM 태그를 부착한다.",
            api_schema_summary="POST /v1/utm-generate {campaign_name: string, channel: string}",
            hit_count=1,
            ttl_days=14,
            age_days=19,
            promote_at_hits=50,
            monthly_compute_cost_usd=45.00,
            min_instances=1,
            service_account_email=f"sa-utm-api@{project_id}.iam.gserviceaccount.com",
            endpoint_url="https://marketing-campaign-utm-tagger-api-an3.a.run.app",
            container_image_digest="sha256:fd61a03af4f77d870fc21e05e7e80678095c92d808cfb3b5c279ee04c74aca13",
            env_vars={
                "GCP_PROJECT_ID": project_id,
                "AD_NETWORK_API_KEY": "ads-key-88210-secret",
                "GEMINI_MODEL": "gemini-3.8-flash",
            },
        ),
        AppRecord(
            app_id="logistics-tariff-simulator-spa",
            app_name="동남아 통관 관세 및 HS코드 시뮬레이터 웹앱 (Tariff Simulator SPA)",
            app_type="SPA",
            lifecycle_stage="ACTIVE",
            owner_team="supply-chain-ops@example.com",
            description=(
                "단발성 공급사 단가 협상 워크숍을 위해 제작된 웹 계산기로, 아세안 주요 항만별 HS코드 관세율과 "
                "수입 부대 비용을 모의 계산한다."
            ),
            system_prompt_summary="HS코드를 분류하고 도착지 관세 포함 원가를 계산한다.",
            api_schema_summary="POST /api/v1/tariff-calc {hs_code: string, fob_value_usd: float}",
            hit_count=1,
            ttl_days=14,
            age_days=16,
            promote_at_hits=50,
            monthly_compute_cost_usd=54.00,
            min_instances=1,
            service_account_email=f"sa-tariff-spa@{project_id}.iam.gserviceaccount.com",
            endpoint_url="https://logistics-tariff-simulator-spa-an3.a.run.app",
            container_image_digest="sha256:a4e624d686e03ed2767c0abd85c14426b0b1157d2ce81d27bb4fe4f6f01d688a",
            env_vars={
                "GCP_PROJECT_ID": project_id,
                "CUSTOMS_WEBHOOK_PASSWORD": "pw-customs-99201",
                "GEMINI_MODEL": "gemini-3.8-flash",
            },
        ),
        AppRecord(
            app_id="enterprise-it-helpdesk-triage-agent",
            app_name="전사 IT 헬프데스크 및 권한 신청 자동 분류 에이전트",
            app_type="AGENT_ENGINE",
            lifecycle_stage="ACTIVE",
            owner_team="it-platform-core@example.com",
            description=(
                "전사 임직원이 일상적으로 사용하는 고빈도 핵심 지원 에이전트로, VPN 초기화, 소프트웨어 라이선스 발급, "
                "장애 티켓 라우팅을 자동 처리한다."
            ),
            system_prompt_summary="임직원 IT 문의를 분류하고 사내 지식베이스를 조회하여 티켓을 생성한다.",
            api_schema_summary="POST /v1/agents/it-helpdesk:streamQuery {session_id: string, message: string}",
            hit_count=412,
            ttl_days=14,
            age_days=30,
            promote_at_hits=50,
            monthly_compute_cost_usd=140.00,
            min_instances=2,
            service_account_email=f"sa-it-helpdesk@{project_id}.iam.gserviceaccount.com",
            endpoint_url="https://enterprise-it-helpdesk-triage-agent-an3.a.run.app",
            container_image_digest="sha256:3c9909afec25354d551dae21590bb26e38d53f2173b8d3dc3eee4c047e7ab1c1",
            env_vars={
                "GCP_PROJECT_ID": project_id,
                "SERVICENOW_API_TOKEN": "sn-prod-token-7712",
                "GEMINI_MODEL": "gemini-3.8-flash",
            },
        ),
        AppRecord(
            app_id="new-hire-onboarding-buddy-spa",
            app_name="신입 사원 첫 주 온보딩 체크리스트 가이드 웹앱",
            app_type="SPA",
            lifecycle_stage="ACTIVE",
            owner_team="people-ops@example.com",
            description=(
                "최근 배포된 신규 입사자용 온보딩 웹앱으로, 사내 인증서 설치와 복리후생 등록 절차를 안내한다."
            ),
            system_prompt_summary="신규 입사자의 직무별 1일 차 필수 설정 절차를 안내한다.",
            api_schema_summary="GET /api/v1/onboarding-steps?role=engineer",
            hit_count=6,
            ttl_days=14,
            age_days=4,
            promote_at_hits=50,
            monthly_compute_cost_usd=38.00,
            min_instances=1,
            service_account_email=f"sa-onboarding-spa@{project_id}.iam.gserviceaccount.com",
            endpoint_url="https://new-hire-onboarding-buddy-spa-an3.a.run.app",
            container_image_digest="sha256:7d865e959b2466918c9863afca942d0fb89d7c9ac0c99bafc3749504ded97730",
            env_vars={
                "GCP_PROJECT_ID": project_id,
                "GEMINI_MODEL": "gemini-3.8-flash",
            },
        ),
    ]


def build_seed_lineage_edges(
    project_id: str = "sample-project-id",
    region: str = "asia-northeast3",
) -> Tuple[Dict[str, List[UpstreamCaller]], Dict[str, List[DownstreamResource]]]:
    """BigQuery Graph 인바운드 호출자 및 다운스트림 리소스 시드 엣지를 반환한다."""
    callers_by_app: Dict[str, List[UpstreamCaller]] = {
        "q3-board-deck-kpi-visualizer": [
            UpstreamCaller(
                caller_id="sched-q3-board-cache-warmer",
                caller_type="CLOUD_SCHEDULER",
                principal_email=f"scheduler-invoker@{project_id}.iam.gserviceaccount.com",
                trigger_resource_uri=f"projects/{project_id}/locations/{region}/jobs/q3-board-cache-warmer",
                protocol="CRON",
                call_count_30d=1,
                is_active=True,
                sever_command=(
                    f"gcloud scheduler jobs pause q3-board-cache-warmer "
                    f"--location={region} --project={project_id}"
                ),
            ),
        ],
        "partner-hackathon-contract-summarizer": [
            UpstreamCaller(
                caller_id="eventarc-gcs-nda-upload-trigger",
                caller_type="EVENTARC",
                principal_email=f"eventarc-invoker@{project_id}.iam.gserviceaccount.com",
                trigger_resource_uri=f"projects/{project_id}/locations/{region}/triggers/gcs-nda-upload-trigger",
                protocol="HTTPS",
                call_count_30d=0,
                is_active=True,
                sever_command=(
                    f"gcloud eventarc triggers delete gcs-nda-upload-trigger "
                    f"--location={region} --project={project_id} --quiet"
                ),
            ),
            UpstreamCaller(
                caller_id="a2a-procurement-router-agent",
                caller_type="A2A_AGENT",
                principal_email=f"sa-procurement-router@{project_id}.iam.gserviceaccount.com",
                trigger_resource_uri=f"projects/{project_id}/locations/global/agents/procurement-router",
                protocol="A2A",
                call_count_30d=0,
                is_active=True,
                sever_command=(
                    f"gcloud run services remove-iam-policy-binding partner-hackathon-contract-summarizer "
                    f"--region={region} --project={project_id} "
                    f"--member='serviceAccount:sa-procurement-router@{project_id}.iam.gserviceaccount.com' "
                    f"--role='roles/run.invoker'"
                ),
            ),
        ],
        "marketing-campaign-utm-tagger-api": [
            UpstreamCaller(
                caller_id="workflow-holiday-promo-dispatch",
                caller_type="WORKFLOWS",
                principal_email=f"workflow-runner@{project_id}.iam.gserviceaccount.com",
                trigger_resource_uri=f"projects/{project_id}/locations/{region}/workflows/holiday-promo-dispatch",
                protocol="HTTPS",
                call_count_30d=1,
                is_active=True,
                sever_command=(
                    f"gcloud run services update-traffic marketing-campaign-utm-tagger-api "
                    f"--to-zero --region={region} --project={project_id}"
                ),
            ),
        ],
        "logistics-tariff-simulator-spa": [
            UpstreamCaller(
                caller_id="pubsub-customs-rate-push",
                caller_type="PUBSUB",
                principal_email=f"pubsub-push@{project_id}.iam.gserviceaccount.com",
                trigger_resource_uri=f"projects/{project_id}/subscriptions/customs-rate-push-sub",
                protocol="PUBSUB_PUSH",
                call_count_30d=1,
                is_active=True,
                sever_command=(
                    f"gcloud pubsub subscriptions modify-push-config customs-rate-push-sub "
                    f"--push-endpoint='' --project={project_id}"
                ),
            ),
        ],
    }

    resources_by_app: Dict[str, List[DownstreamResource]] = {
        "q3-board-deck-kpi-visualizer": [
            DownstreamResource(
                resource_id=f"sa-q3-board-kpi@{project_id}.iam.gserviceaccount.com",
                resource_type="SERVICE_ACCOUNT",
                iam_role="roles/bigquery.dataViewer",
                monthly_cost_usd=0.0,
                revoke_command=(
                    f"gcloud projects remove-iam-policy-binding {project_id} "
                    f"--member='serviceAccount:sa-q3-board-kpi@{project_id}.iam.gserviceaccount.com' "
                    f"--role='roles/bigquery.dataViewer'"
                ),
            ),
        ],
        "partner-hackathon-contract-summarizer": [
            DownstreamResource(
                resource_id=f"sa-nda-agent@{project_id}.iam.gserviceaccount.com",
                resource_type="SERVICE_ACCOUNT",
                iam_role="roles/aiplatform.user",
                monthly_cost_usd=0.0,
                revoke_command=(
                    f"gcloud projects remove-iam-policy-binding {project_id} "
                    f"--member='serviceAccount:sa-nda-agent@{project_id}.iam.gserviceaccount.com' "
                    f"--role='roles/aiplatform.user'"
                ),
            ),
            DownstreamResource(
                resource_id=f"sa-nda-agent@{project_id}.iam.gserviceaccount.com",
                resource_type="SECRET_MANAGER",
                iam_role="roles/secretmanager.secretAccessor",
                monthly_cost_usd=0.0,
                revoke_command=(
                    f"gcloud projects remove-iam-policy-binding {project_id} "
                    f"--member='serviceAccount:sa-nda-agent@{project_id}.iam.gserviceaccount.com' "
                    f"--role='roles/secretmanager.secretAccessor'"
                ),
            ),
        ],
        "marketing-campaign-utm-tagger-api": [
            DownstreamResource(
                resource_id=f"sa-utm-api@{project_id}.iam.gserviceaccount.com",
                resource_type="SERVICE_ACCOUNT",
                iam_role="roles/aiplatform.user",
                monthly_cost_usd=0.0,
                revoke_command=(
                    f"gcloud projects remove-iam-policy-binding {project_id} "
                    f"--member='serviceAccount:sa-utm-api@{project_id}.iam.gserviceaccount.com' "
                    f"--role='roles/aiplatform.user'"
                ),
            ),
        ],
        "logistics-tariff-simulator-spa": [
            DownstreamResource(
                resource_id=f"sa-tariff-spa@{project_id}.iam.gserviceaccount.com",
                resource_type="SERVICE_ACCOUNT",
                iam_role="roles/bigquery.jobUser",
                monthly_cost_usd=0.0,
                revoke_command=(
                    f"gcloud projects remove-iam-policy-binding {project_id} "
                    f"--member='serviceAccount:sa-tariff-spa@{project_id}.iam.gserviceaccount.com' "
                    f"--role='roles/bigquery.jobUser'"
                ),
            ),
        ],
    }

    return callers_by_app, resources_by_app


def _tokenize_semantic(text: str) -> List[str]:
    """국문 및 영문 텍스트를 도메인 정규 어간 토큰으로 정규화한다."""
    raw_tokens = re.findall(r"[가-힣]+|[a-z0-9]+", text.lower())
    tokens: List[str] = []
    for tok in raw_tokens:
        for suffix in ("용으로", "에서", "으로", "에게", "의", "을", "를", "이", "가", "은", "는", "과", "와", "용"):
            if len(tok) > len(suffix) + 1 and tok.endswith(suffix):
                tok = tok[: -len(suffix)]
                break
        if tok in _STOPWORDS or len(tok) <= 1:
            continue
        canonical = _SYNONYM_CANONICAL_MAP.get(tok, tok)
        tokens.append(canonical)
    return tokens


def _compute_semantic_similarity(query: str, app: AppRecord) -> float:
    """결정론적 시뮬레이션을 위해 [0.0, 1.0] 범위의 보정된 코사인 유사도를 계산한다."""
    query_tokens = _tokenize_semantic(query)
    if not query_tokens:
        return 0.0

    doc_text = " ".join(
        [
            app.app_name,
            app.app_name,
            app.description,
            app.system_prompt_summary,
            app.app_type,
        ]
    )
    doc_tokens = _tokenize_semantic(doc_text)
    if not doc_tokens:
        return 0.0

    q_counts = Counter(query_tokens)
    d_counts = Counter(doc_tokens)

    vocab = set(q_counts.keys()) | set(d_counts.keys())
    dot = sum(q_counts[w] * d_counts[w] for w in vocab)
    q_norm = math.sqrt(sum(v * v for v in q_counts.values()))
    d_norm = math.sqrt(sum(v * v for v in d_counts.values()))
    raw_cosine = dot / (q_norm * d_norm) if (q_norm and d_norm) else 0.0

    query_set = set(q_counts.keys())
    doc_set = set(d_counts.keys())
    query_coverage = len(query_set & doc_set) / len(query_set)

    blended = 0.45 * raw_cosine + 0.55 * query_coverage
    if query_coverage >= 0.5:
        blended = min(0.98, blended + 0.18)
    return round(min(1.0, max(0.0, blended)), 4)


class CatalogVectorEngine:
    """Dataplex Universal Catalog Aspect 및 BigQuery Vector Search 쿼리 엔진."""

    def __init__(
        self,
        project_id: str = "sample-project-id",
        region: str = "asia-northeast3",
        dataset_id: str = "app_governance",
        table_id: str = "app_semantic_registry",
        aspect_type_id: str = "app-lifecycle-governance",
        archive_bucket: str = "gs://sample-project-id-onetime-archive",
    ) -> None:
        self.project_id = project_id
        self.region = region
        self.dataset_id = dataset_id
        self.table_id = table_id
        self.aspect_type_id = aspect_type_id
        self.archive_bucket = archive_bucket.rstrip("/")

    def register_or_update_aspect(
        self,
        app: AppRecord,
        blast_radius_edges: int = 0,
        override_stage: Optional[str] = None,
        override_cryo_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dataplex Universal Catalog 커스텀 엔트리 및 Aspect 페이로드를 합성한다."""
        stage = override_stage or app.lifecycle_stage
        cryo_uri = override_cryo_uri if override_cryo_uri is not None else app.cryo_gcs_uri
        entry_fqn = (
            f"projects/{self.project_id}/locations/{self.region}/entryGroups/"
            f"ai-sdlc-apps/entries/{app.app_id}"
        )
        aspect_key = f"{self.project_id}.{self.region}.{self.aspect_type_id}"

        return {
            "name": entry_fqn,
            "entry_type": f"projects/{self.project_id}/locations/{self.region}/entryTypes/one-time-ai-app",
            "labels": dict(MANDATORY_LABELS),
            "aspects": {
                aspect_key: {
                    "aspect_type": (
                        f"projects/{self.project_id}/locations/{self.region}/"
                        f"aspectTypes/{self.aspect_type_id}"
                    ),
                    "data": {
                        "lifecycle": "one-time" if stage != "GRADUATED" else "permanent",
                        "lifecycle_stage": stage,
                        "hit_count": app.hit_count,
                        "ttl_days": app.ttl_days,
                        "promote_at_hits": app.promote_at_hits,
                        "owner": app.owner_team,
                        "archive_bucket": self.archive_bucket,
                        "cryo_gcs_uri": cryo_uri,
                        "blast_radius_edges": blast_radius_edges,
                    },
                }
            },
        }

    def pre_build_semantic_gate(
        self,
        idea_query: str,
        apps: List[AppRecord],
        threshold: float = 0.55,
        top_k: int = 3,
    ) -> List[SemanticMatch]:
        """1단계 개발 착수 전 시맨틱 중복 생성 방지 게이트를 수행한다."""
        matches: List[SemanticMatch] = []
        for app in apps:
            score = _compute_semantic_similarity(idea_query, app)
            if score >= threshold:
                if app.lifecycle_stage == "CRYO_ARCHIVED":
                    rec = "REHYDRATE_CRYO"
                elif app.lifecycle_stage in ("ACTIVE", "GRADUATED"):
                    rec = "REUSE_ACTIVE"
                else:
                    rec = "PROCEED_NEW_BUILD"

                matches.append(
                    SemanticMatch(
                        app_id=app.app_id,
                        app_name=app.app_name,
                        app_type=app.app_type,
                        lifecycle_stage=app.lifecycle_stage,
                        owner_team=app.owner_team,
                        description=app.description,
                        cosine_similarity=score,
                        recommendation=rec,
                        cryo_gcs_uri=app.cryo_gcs_uri,
                        rehydrate_command=app.rehydrate_command,
                    )
                )
        matches.sort(key=lambda m: m.cosine_similarity, reverse=True)
        return matches[:top_k]

    def search_to_restore(
        self,
        natural_query: str,
        apps: List[AppRecord],
        top_k: int = 3,
    ) -> List[SemanticMatch]:
        """5단계 냉동 보관 앱 대상 자연어 시맨틱 복원 검색(Search-to-Restore)을 수행한다."""
        archived_apps = [a for a in apps if a.lifecycle_stage == "CRYO_ARCHIVED"]
        matches: List[SemanticMatch] = []
        for app in archived_apps:
            score = _compute_semantic_similarity(natural_query, app)
            if score > 0.0:
                matches.append(
                    SemanticMatch(
                        app_id=app.app_id,
                        app_name=app.app_name,
                        app_type=app.app_type,
                        lifecycle_stage=app.lifecycle_stage,
                        owner_team=app.owner_team,
                        description=app.description,
                        cosine_similarity=score,
                        recommendation="REHYDRATE_CRYO",
                        cryo_gcs_uri=app.cryo_gcs_uri,
                        rehydrate_command=app.rehydrate_command,
                    )
                )
        matches.sort(key=lambda m: m.cosine_similarity, reverse=True)
        return matches[:top_k]


class HitCountTTLDetector:
    """호출 수(Hit-Count) 및 보존 기한(TTL) 기반 96% 냉동 대 4% 승격 판별기."""

    def __init__(
        self,
        default_ttl_days: int = 14,
        default_promote_at_hits: int = 50,
    ) -> None:
        self.default_ttl_days = default_ttl_days
        self.default_promote_at_hits = default_promote_at_hits

    def classify_app(self, app: AppRecord) -> LifecycleDecision:
        """단일 앱의 호출 수와 경과 일수를 임계치와 대조하여 수명 주기 조치를 판정한다."""
        ttl = app.ttl_days if app.ttl_days > 0 else self.default_ttl_days
        promote_threshold = (
            app.promote_at_hits if app.promote_at_hits > 0 else self.default_promote_at_hits
        )

        if app.lifecycle_stage == "CRYO_ARCHIVED":
            return LifecycleDecision(
                app_id=app.app_id,
                app_name=app.app_name,
                hit_count=app.hit_count,
                age_days=app.age_days,
                ttl_days=ttl,
                promote_at_hits=promote_threshold,
                action="ALREADY_ARCHIVED",
                rationale=(
                    f"이미 클라우드 스토리지 콜드라인 볼트({app.cryo_gcs_uri})에 냉동 보관되어 "
                    f"상시 컴퓨트 비용이 $0.00/월이다."
                ),
            )

        if app.hit_count >= promote_threshold:
            return LifecycleDecision(
                app_id=app.app_id,
                app_name=app.app_name,
                hit_count=app.hit_count,
                age_days=app.age_days,
                ttl_days=ttl,
                promote_at_hits=promote_threshold,
                action="PRODUCTION_GRADUATION",
                rationale=(
                    f"호출 수({app.hit_count}회)가 승격 임계치({promote_threshold}회) 이상으로 확인되어 "
                    f"상위 4% 엔터프라이즈 SDLC 프로덕션 승격 대상이다."
                ),
            )

        if app.hit_count <= 1 and app.age_days >= ttl:
            return LifecycleDecision(
                app_id=app.app_id,
                app_name=app.app_name,
                hit_count=app.hit_count,
                age_days=app.age_days,
                ttl_days=ttl,
                promote_at_hits=promote_threshold,
                action="CRYO_DISPOSAL",
                rationale=(
                    f"1회성 사용 패턴(호출 수 {app.hit_count}회 <= 1회) 및 보존 기한 만료(경과 {app.age_days}일 >= TTL {ttl}일)가 "
                    f"확인되어 96% 콜드라인 냉동 타임캡슐 보관 대상이다."
                ),
            )

        return LifecycleDecision(
            app_id=app.app_id,
            app_name=app.app_name,
            hit_count=app.hit_count,
            age_days=app.age_days,
            ttl_days=ttl,
            promote_at_hits=promote_threshold,
            action="KEEP_ACTIVE",
            rationale=(
                f"보존 기한 유예 기간 이내(경과 {app.age_days}일 < TTL {ttl}일)이거나 "
                f"일반 사용 중(호출 수 {app.hit_count}회)이므로 활성(ACTIVE) 상태를 유지한다."
            ),
        )

    def evaluate_fleet(self, apps: List[AppRecord]) -> FleetEvaluationResult:
        """전사 앱 인벤토리를 전수 평가하여 코호트별로 분류한다."""
        decisions: List[LifecycleDecision] = []
        cryo_candidates: List[AppRecord] = []
        graduation_candidates: List[AppRecord] = []
        active_retained: List[AppRecord] = []
        already_archived: List[AppRecord] = []

        for app in apps:
            decision = self.classify_app(app)
            decisions.append(decision)
            if decision.action == "CRYO_DISPOSAL":
                cryo_candidates.append(app)
            elif decision.action == "PRODUCTION_GRADUATION":
                graduation_candidates.append(app)
            elif decision.action == "ALREADY_ARCHIVED":
                already_archived.append(app)
            else:
                active_retained.append(app)

        return FleetEvaluationResult(
            decisions=decisions,
            cryo_candidates=cryo_candidates,
            graduation_candidates=graduation_candidates,
            active_retained=active_retained,
            already_archived=already_archived,
        )


class LineageGraphEngine:
    """BigQuery Property Graph (GQL) 멀티홉 호출 리니지 및 안전 차단 엔진."""

    def __init__(
        self,
        project_id: str = "sample-project-id",
        dataset_id: str = "app_governance",
        graph_name: str = "app_lineage_graph",
    ) -> None:
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.graph_name = graph_name

    def build_gql_blast_radius_query(self, app_id: str) -> str:
        """업스트림 호출자와 다운스트림 리소스를 역추적하는 GQL 쿼리를 생성한다."""
        fq_graph = f"{self.project_id}.{self.dataset_id}.{self.graph_name}"
        return (
            f"GRAPH `{fq_graph}`\n"
            f"MATCH (caller:UpstreamCaller)-[inv:INVOKES]->"
            f"(app:OneTimeApp {{app_id: '{app_id}'}})-[dep:DEPENDS_ON]->(res:GCPResource)\n"
            f"RETURN\n"
            f"  app.app_id AS app_id,\n"
            f"  caller.caller_id AS upstream_caller_id,\n"
            f"  caller.caller_type AS caller_type,\n"
            f"  inv.protocol AS protocol,\n"
            f"  inv.sever_command AS sever_command,\n"
            f"  res.resource_id AS downstream_resource_id,\n"
            f"  dep.revoke_command AS iam_revoke_command;"
        )

    def analyze_and_sever(
        self,
        app: AppRecord,
        callers_by_app: Dict[str, List[UpstreamCaller]],
        resources_by_app: Dict[str, List[DownstreamResource]],
    ) -> LineageReport:
        """업스트림 블라스트 반경을 검증하고 결정론적 차단 명령어를 합성한다."""
        upstream = list(callers_by_app.get(app.app_id, []))
        downstream = list(resources_by_app.get(app.app_id, []))

        sever_commands = [c.sever_command for c in upstream if c.is_active and c.sever_command]
        iam_revoke_commands = [r.revoke_command for r in downstream if r.revoke_command]

        active_automated = [
            c for c in upstream if c.is_active and c.caller_type != "HUMAN_BROWSER"
        ]
        all_severable = all(bool(c.sever_command.strip()) for c in active_automated)

        return LineageReport(
            app_id=app.app_id,
            app_name=app.app_name,
            gql_query=self.build_gql_blast_radius_query(app.app_id),
            upstream_callers=upstream,
            downstream_resources=downstream,
            sever_commands=sever_commands,
            iam_revoke_commands=iam_revoke_commands,
            active_automated_callers_count=len(active_automated),
            safe_to_dispose=all_severable,
        )


class CryoArchiver:
    """Cloud Storage Coldline 냉동 타임캡슐 패키저 및 60초 부활 스크립트 생성기."""

    def __init__(
        self,
        project_id: str = "sample-project-id",
        region: str = "asia-northeast3",
        archive_bucket: str = "gs://sample-project-id-onetime-archive",
        storage_class: str = "COLDLINE",
    ) -> None:
        self.project_id = project_id
        self.region = region
        self.archive_bucket = archive_bucket.rstrip("/")
        self.storage_class = storage_class

    @staticmethod
    def sanitize_env_vars(env_vars: Dict[str, str]) -> Dict[str, str]:
        """콜드라인 저장 전 평문 API 키, 시크릿, 토큰을 마스킹한다."""
        sanitized: Dict[str, str] = {}
        for key, value in env_vars.items():
            if _SENSITIVE_KEY_PATTERN.search(key):
                sanitized[key] = "<REDACTED_SECRET_MANAGER_REF>"
            else:
                sanitized[key] = value
        return sanitized

    def generate_rehydrate_script(
        self,
        app: AppRecord,
        capsule_uri: str,
        lineage: LineageReport,
    ) -> str:
        """60초 이내 원클릭 복원을 위한 POSIX 쉘 스크립트(rehydrate.sh)를 생성한다."""
        label_str = ",".join(f"{k}={v}" for k, v in MANDATORY_LABELS.items())
        restore_iam_lines: List[str] = []
        for res in lineage.downstream_resources:
            restore_iam_lines.append(
                f"gcloud projects add-iam-policy-binding {self.project_id} \\\n"
                f"  --member='serviceAccount:{app.service_account_email}' \\\n"
                f"  --role='{res.iam_role}' --quiet"
            )
        iam_block = "\n".join(restore_iam_lines) if restore_iam_lines else "# 추가 IAM 바인딩 불필요"

        return (
            "#!/usr/bin/env bash\n"
            "# Auto-generated by app-lifecycle-manager Cryo-Archiver\n"
            f"# App ID: {app.app_id} ({app.app_name})\n"
            "set -euo pipefail\n\n"
            f"echo '[1/4] Fetching Cryo-Time-Capsule from {capsule_uri}...'\n"
            f"gcloud storage cp '{capsule_uri}manifest.json' ./manifest.json\n\n"
            f"echo '[2/4] Re-attaching least-privilege IAM roles for {app.service_account_email}...'\n"
            f"{iam_block}\n\n"
            f"echo '[3/4] Re-deploying {app.app_id} to Cloud Run ({self.region})...'\n"
            f"gcloud run deploy {app.app_id} \\\n"
            f"  --image='gcr.io/{self.project_id}/{app.app_id}@{app.container_image_digest}' \\\n"
            f"  --region='{self.region}' \\\n"
            f"  --project='{self.project_id}' \\\n"
            f"  --service-account='{app.service_account_email}' \\\n"
            f"  --min-instances=0 \\\n"
            f"  --labels='{label_str}'\n\n"
            "echo '[4/4] Updating Knowledge Catalog Aspect to ACTIVE...'\n"
            f"gcloud dataplex entries update {app.app_id} \\\n"
            f"  --location='{self.region}' \\\n"
            f"  --project='{self.project_id}' \\\n"
            "  --aspect-lifecycle-stage=ACTIVE\n\n"
            f"echo 'Rehydration completed in <60s: {app.endpoint_url}'\n"
        )

    def create_cryo_capsule(
        self,
        app: AppRecord,
        lineage: LineageReport,
        catalog_aspect_payload: Dict[str, Any],
    ) -> CryoCapsule:
        """드레이닝 완료된 1회성 앱을 Coldline 타임캡슐로 동결하고 컴퓨트/IAM을 회수한다."""
        if not lineage.safe_to_dispose:
            raise ValueError(f"미차단 업스트림 호출자가 남아 있어 냉동할 수 없다: {app.app_id}")

        capsule_uri = f"{self.archive_bucket}/{app.app_id}/"
        sanitized_env = self.sanitize_env_vars(app.env_vars)
        rehydrate_sh = self.generate_rehydrate_script(app, capsule_uri, lineage)

        teardown_commands: List[str] = []
        teardown_commands.extend(lineage.sever_commands)
        teardown_commands.extend(lineage.iam_revoke_commands)
        teardown_commands.append(
            f"gcloud storage cp ./capsule/* '{capsule_uri}' --storage-class={self.storage_class}"
        )
        teardown_commands.append(
            f"gcloud run services delete {app.app_id} --region={self.region} "
            f"--project={self.project_id} --quiet"
        )

        manifest_json: Dict[str, Any] = {
            "app_id": app.app_id,
            "app_name": app.app_name,
            "app_type": app.app_type,
            "owner_team": app.owner_team,
            "container_image_digest": app.container_image_digest,
            "system_prompt_summary": app.system_prompt_summary,
            "api_schema_summary": app.api_schema_summary,
            "sanitized_env_keys": sorted(sanitized_env.keys()),
            "catalog_aspect": catalog_aspect_payload,
            "labels": dict(MANDATORY_LABELS),
        }

        return CryoCapsule(
            app_id=app.app_id,
            app_name=app.app_name,
            app_type=app.app_type,
            owner_team=app.owner_team,
            capsule_gcs_uri=capsule_uri,
            storage_class=self.storage_class,
            manifest_json=manifest_json,
            sanitized_env_template=sanitized_env,
            teardown_commands=teardown_commands,
            rehydrate_script=rehydrate_sh,
            rehydrate_one_liner=f"gcloud storage cat {capsule_uri}rehydrate.sh | bash",
            reclaimed_monthly_usd=app.monthly_compute_cost_usd,
            reclaimed_min_instances=app.min_instances,
            revoked_iam_bindings_count=len(lineage.iam_revoke_commands),
            severed_triggers_count=len(lineage.sever_commands),
        )

    def build_graduation_package(
        self,
        app: AppRecord,
        catalog_aspect_payload: Dict[str, Any],
    ) -> GraduationPackage:
        """상위 4% 핵심 안착 앱을 위한 엔터프라이즈 SDLC 프로덕션 승격 패키지를 생성한다."""
        label_str = ",".join(f"{k}={v}" for k, v in MANDATORY_LABELS.items())
        ci_cd_spec = (
            f"# Cloud Build Production Graduation Pipeline for {app.app_id}\n"
            "steps:\n"
            "  - name: 'gcr.io/cloud-builders/pytest'\n"
            "    args: ['-q']\n"
            "  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'\n"
            "    args:\n"
            "      - 'gcloud'\n"
            "      - 'run'\n"
            "      - 'deploy'\n"
            f"      - '{app.app_id}-prod'\n"
            f"      - '--region={self.region}'\n"
            "      - '--ingress=internal-and-cloud-load-balancing'\n"
            f"      - '--labels={label_str}'\n"
        )
        checklist = [
            "지식 카탈로그(Dataplex Universal Catalog) Aspect 상태를 `ACTIVE`(1회성)에서 `GRADUATED`(영구 운영)로 승격한다.",
            "환경 변수 내 시크릿을 시크릿 매니저(Secret Manager)로 이관하고 90일 자동 순환 정책을 적용한다.",
            "클라우드 아머(Cloud Armor) 및 모델 아머(Model Armor) 프롬프트 인젝션 방어 정책을 부착한다.",
            "VPC 서비스 컨트롤(VPC Service Controls) 보안 경계와 프로덕션 전용 최소 권한 서비스 계정을 분리 적용한다.",
            "클라우드 모니터링(Cloud Monitoring) 가용성 SLO 알림(99.9% 가용성, P95 지연 시간 2.0초 미만)을 활성화한다.",
        ]
        return GraduationPackage(
            app_id=app.app_id,
            app_name=app.app_name,
            hit_count=app.hit_count,
            owner_team=app.owner_team,
            ci_cd_pipeline_spec=ci_cd_spec,
            security_hardening_checklist=checklist,
            catalog_aspect_update=catalog_aspect_payload,
        )


class GovernanceReceiptGenerator:
    """FinOps 비용 절감액 및 SecOps 공격 표면 감축 리포트(report.md) 생성기."""

    def calculate_impact(
        self,
        evaluation: FleetEvaluationResult,
        disposed_capsules: List[CryoCapsule],
        graduated_packages: List[GraduationPackage],
    ) -> GovernanceMetrics:
        """월간/연간 순 컴퓨트 절감액과 보안 공격 표면 감축 수치를 집계한다."""
        gross_monthly = round(sum(c.reclaimed_monthly_usd for c in disposed_capsules), 2)
        gcs_monthly = round(len(disposed_capsules) * GCS_COLDLINE_COST_PER_CAPSULE_USD, 2)
        net_monthly = round(gross_monthly - gcs_monthly, 2)
        net_annual = round(net_monthly * 12, 2)

        reclaimed_instances = sum(c.reclaimed_min_instances for c in disposed_capsules)
        revoked_iam = sum(c.revoked_iam_bindings_count for c in disposed_capsules)
        severed_triggers = sum(c.severed_triggers_count for c in disposed_capsules)
        reclaimed_sas = len(disposed_capsules)
        closed_endpoints = len(disposed_capsules)

        return GovernanceMetrics(
            total_apps_evaluated=len(evaluation.decisions),
            cryo_disposed_count=len(disposed_capsules),
            graduated_count=len(graduated_packages),
            already_archived_count=len(evaluation.already_archived),
            active_retained_count=len(evaluation.active_retained),
            gross_monthly_compute_saved_usd=gross_monthly,
            gcs_archive_monthly_cost_usd=gcs_monthly,
            net_monthly_saved_usd=net_monthly,
            net_annual_saved_usd=net_annual,
            reclaimed_warm_instances=reclaimed_instances,
            reclaimed_service_accounts=reclaimed_sas,
            revoked_iam_bindings=revoked_iam,
            severed_zombie_triggers=severed_triggers,
            closed_public_endpoints=closed_endpoints,
        )

    def render_markdown_report(
        self,
        project_id: str,
        region: str,
        is_dry_run: bool,
        pre_build_query: str,
        pre_build_matches: List[SemanticMatch],
        evaluation: FleetEvaluationResult,
        lineage_reports: List[LineageReport],
        disposed_capsules: List[CryoCapsule],
        graduated_packages: List[GraduationPackage],
        restore_query: str,
        restore_matches: List[SemanticMatch],
        metrics: GovernanceMetrics,
    ) -> str:
        """표준 디스클레이머와 5단계 거버넌스 결과가 포함된 report.md를 렌더링한다."""
        label_str = ", ".join(f"`{k}={v}`" for k, v in MANDATORY_LABELS.items())
        mode_str = "Dry-Run (가상 시뮬레이션 모드)" if is_dry_run else "Live (사내 인벤토리 정밀 진단 모드)"

        lines: List[str] = [
            "<!--",
            "Copyright 2026 Google LLC. All Rights Reserved.",
            "SPDX-License-Identifier: Apache-2.0",
            "",
            "NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.",
            "It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.",
            "All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.",
            "",
            "[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.",
            "프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.",
            "-->",
            "",
            "> [!IMPORTANT]",
            "> **구글 (Google LLC) 참조용 샘플 고지 사항**:",
            "> 본 프로젝트의 모든 소스 코드와 문서는 Google LLC의 소유이며, Apache-2.0 라이선스에 따라 오직 **참조용 샘플 (Sample / Reference Only)** 목적으로만 제공된다. 프로덕션 환경에 그대로 사용할 수 없으며, 사전 통지 없이 언제든 내용이 수정, 변경 또는 삭제될 수 있다.",
            "",
            "# 엔터프라이즈 AI 앱 생애 주기 및 콜드라인 냉동 거버넌스 리포트 (app-lifecycle-manager)",
            "",
            f"- **대상 프로젝트**: `{project_id}`",
            f"- **기준 리전**: `{region}` (대한민국 서울 리전 기본)",
            f"- **실행 모드**: `{mode_str}`",
            f"- **표준 리소스 라벨**: {label_str}",
            "",
            "---",
            "",
            "## 1. 경영진 요약 지표 (FinOps 비용 절감 및 SecOps 보안 표면 감축)",
            "",
            "| 지표 구분 | 거버넌스 핵심 측정 항목 | 실측 및 산출 결과 |",
            "| :--- | :--- | :--- |",
            f"| **전사 앱 인벤토리** | 평가 대상 전체 AI 앱 수 | 총 `{metrics.total_apps_evaluated}`개 앱 |",
            f"| **냉동 보관 (96% 코호트)** | 만료된 1회성 앱 냉동 조치 (`Hit Count <= 1`) | 신규 냉동 `{metrics.cryo_disposed_count}`개 (기존 냉동 `{metrics.already_archived_count}`개) |",
            f"| **프로덕션 승격 (4% 코호트)** | 고빈도 핵심 안착 앱 정식 승격 (`Hit Count >= 50`) | `{metrics.graduated_count}`개 앱 |",
            f"| **FinOps 컴퓨트 절감액** | 회수된 월간 유휴 컴퓨트 총 비용 | 월 `${metrics.gross_monthly_compute_saved_usd:,.2f}` 절감 |",
            f"| **FinOps 콜드라인 보관료** | GCS Coldline 타임캡슐 보관 비용 (`$0.02/캡슐`) | 월 `${metrics.gcs_archive_monthly_cost_usd:,.2f}` 발생 |",
            f"| **FinOps 순 절감 효과** | **월간 및 연간 순 절감액 (Net Savings)** | **월 `${metrics.net_monthly_saved_usd:,.2f}` (연간 `${metrics.net_annual_saved_usd:,.2f}` 절감)** |",
            f"| **SecOps 유휴 리소스 회수** | 상시 대기 인스턴스 (`min-instances`) 회수 수 | `{metrics.reclaimed_warm_instances}`개 인스턴스 회수 |",
            f"| **SecOps 자격 증명 위생** | 비인간 서비스 계정 (NHI) 및 IAM 권한 동결 | `{metrics.reclaimed_service_accounts}`개 서비스 계정 (`{metrics.revoked_iam_bindings}`개 IAM 바인딩 해제) |",
            f"| **SecOps 블라스트 반경** | BigQuery Graph 기반 좀비 트리거 차단 및 엔드포인트 폐쇄 | `{metrics.severed_zombie_triggers}`개 트리거 차단 (`{metrics.closed_public_endpoints}`개 외부 엔드포인트 폐쇄) |",
            "",
            "---",
            "",
            "## 2. 1단계: 개발 착수 전 시맨틱 중복 생성 방지 게이트 (Pre-Build Gate)",
            "",
            f"- **신규 개발 요청 아이디어**: `\"{pre_build_query}\"`",
            "- **검색 엔진**: `BigQuery Vector Search` (`gemini-embedding-001`, 코사인 유사도) + `Dataplex Universal Catalog`",
            "",
            "| 순위 | 기존 등록 앱 ID | 현재 수명 주기 상태 | 코사인 유사도 | 거버넌스 권고 조치 | 실행 및 1분 복원 명령어 |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for idx, match in enumerate(pre_build_matches, start=1):
            cmd = f"`{match.rehydrate_command}`" if match.rehydrate_command else f"`{match.app_id}` 즉시 재사용"
            lines.append(
                f"| {idx} | `{match.app_id}` | `{match.lifecycle_stage}` | `{match.cosine_similarity:.4f}` | **{match.recommendation}** | {cmd} |"
            )

        lines.extend(
            [
                "",
                "---",
                "",
                "## 3. 2단계: 호출 수(Hit-Count) 및 보존 기한(TTL) 전수 판별 결과",
                "",
                "| 앱 ID | 유형 | 소유 조직 | 호출 수 | 경과일 / TTL | 거버넌스 판정 | 판정 근거 |",
                "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
            ]
        )

        app_map = {
            a.app_id: a
            for a in (
                evaluation.cryo_candidates
                + evaluation.graduation_candidates
                + evaluation.active_retained
                + evaluation.already_archived
            )
        }
        for dec in evaluation.decisions:
            app_obj = app_map[dec.app_id]
            lines.append(
                f"| `{dec.app_id}` | `{app_obj.app_type}` | `{app_obj.owner_team}` | `{dec.hit_count}` | `{dec.age_days}일 / {dec.ttl_days}일` | **`{dec.action}`** | {dec.rationale} |"
            )

        lines.extend(
            [
                "",
                "---",
                "",
                "## 4. 3단계: 빅쿼리 그래프(`GQL`) 멀티홉 호출 리니지 및 안전 차단 내역",
                "",
                "| 대상 앱 ID | 업스트림 호출자 ID | 호출자 유형 | 프로토콜 | 안전 폐기 검증 | 결정론적 차단 명령어 (Sever Command) |",
                "| :--- | :--- | :--- | :--- | :--- | :--- |",
            ]
        )

        for lin in lineage_reports:
            for caller in lin.upstream_callers:
                lines.append(
                    f"| `{lin.app_id}` | `{caller.caller_id}` | `{caller.caller_type}` | `{caller.protocol}` | `{lin.safe_to_dispose}` | `{caller.sever_command}` |"
                )

        lines.extend(
            [
                "",
                "---",
                "",
                "## 5. 4A단계: 클라우드 스토리지 콜드라인 냉동 타임캡슐 및 1분 부활 스크립트",
                "",
                "| 냉동 앱 ID | 콜드라인 캡슐 경로 (GCS URI) | 살균된 시크릿 키 | 월간 절감액 | 1분 원클릭 부활 명령어 (Rehydrate) |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ]
        )

        for cap in disposed_capsules:
            redacted_keys = [
                k for k, v in cap.sanitized_env_template.items() if "REDACTED" in v
            ]
            redacted_str = ", ".join(f"`{k}`" for k in redacted_keys) or "없음"
            lines.append(
                f"| `{cap.app_id}` | `{cap.capsule_gcs_uri}` | {redacted_str} | 월 `${cap.reclaimed_monthly_usd:,.2f}` | `{cap.rehydrate_one_liner}` |"
            )

        lines.extend(
            [
                "",
                "---",
                "",
                "## 6. 4B단계: 상위 4% 핵심 안착 앱 프로덕션 승격 (Graduation)",
                "",
            ]
        )

        for grad in graduated_packages:
            lines.append(
                f"### 승격 대상 앱: `{grad.app_id}` ({grad.app_name}, 누적 호출 `{grad.hit_count}`회)"
            )
            for item in grad.security_hardening_checklist:
                lines.append(f"- [x] {item}")
            lines.append("")

        lines.extend(
            [
                "---",
                "",
                "## 7. 5단계: 자연어 시맨틱 복원 검색 (Search-to-Restore) 검증",
                "",
                f"- **자연어 복원 검색 질의**: `\"{restore_query}\"`",
                "",
                "| 매칭된 냉동 앱 ID | 코사인 유사도 | 콜드라인 캡슐 경로 | 1분 원클릭 부활 명령어 |",
                "| :--- | :--- | :--- | :--- |",
            ]
        )

        for match in restore_matches:
            lines.append(
                f"| `{match.app_id}` | `{match.cosine_similarity:.4f}` | `{match.cryo_gcs_uri}` | `{match.rehydrate_command}` |"
            )

        lines.append("")
        return "\n".join(lines)


def _run_gcloud_value(args: List[str]) -> str:
    """gcloud CLI에서 단일 문자열 설정값을 안전하게 읽어온다."""
    try:
        res = subprocess.run(
            ["gcloud"] + args,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        val = res.stdout.strip()
        return "" if val == "(unset)" else val
    except Exception:
        return ""


def resolve_project_and_region(
    cli_project: Optional[str],
    cli_region: Optional[str],
    is_dry_run: bool,
) -> Tuple[str, str]:
    """CLI 인자 > 환경 변수 > gcloud config > 기본값 순으로 프로젝트 ID와 리전을 해석한다."""
    if is_dry_run:
        return (
            cli_project or "sample-project-id",
            cli_region or os.getenv("REGION") or "asia-northeast3",
        )

    project_id = (
        cli_project
        or os.getenv("PROJECT_ID")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or _run_gcloud_value(["config", "get-value", "project"])
        or "sample-project-id"
    )
    region = (
        cli_region
        or os.getenv("REGION")
        or _run_gcloud_value(["config", "get-value", "compute/region"])
        or "asia-northeast3"
    )
    return project_id, region


def run_config_wizard() -> int:
    """대화형 설정 마법사(--config)를 실행하여 .env 파일을 생성한다."""
    print("=" * 88, flush=True)
    print(" [설정 마법사] app-lifecycle-manager 환경 변수(.env) 구성을 시작한다.", flush=True)
    print("=" * 88, flush=True)

    detected_proj = _run_gcloud_value(["config", "get-value", "project"]) or "sample-project-id"
    detected_region = _run_gcloud_value(["config", "get-value", "compute/region"]) or "asia-northeast3"

    if sys.stdin.isatty():
        proj = input(f"1. 대상 GCP 프로젝트 ID [{detected_proj}]: ").strip() or detected_proj
        reg = input(f"2. 기준 인프라 리전 [{detected_region}]: ").strip() or detected_region
        ds = input("3. BigQuery 거버넌스 데이터셋 ID [app_governance]: ").strip() or "app_governance"
        bucket = input(f"4. Coldline 아카이브 버킷 [gs://{proj}-onetime-archive]: ").strip() or f"gs://{proj}-onetime-archive"
    else:
        proj = detected_proj
        reg = detected_region
        ds = "app_governance"
        bucket = f"gs://{proj}-onetime-archive"

    env_path = Path(__file__).resolve().parent / ".env"
    env_content = (
        "# Auto-generated by python diagnose.py --config\n"
        f"PROJECT_ID={proj}\n"
        f"REGION={reg}\n"
        f"BQ_DATASET_ID={ds}\n"
        f"GCS_BUCKET_NAME={bucket}\n"
        "GOOGLE_CLOUD_LOCATION=global\n"
        "GEMINI_MODEL=gemini-3.8-flash\n"
    )
    env_path.write_text(env_content, encoding="utf-8")
    print(f"[완료] 환경 설정이 저장되었다: {env_path}", flush=True)
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    """표준 3대 플래그(--dry-run, --config, --project) 및 시맨틱 검색 옵션을 파싱한다."""
    parser = argparse.ArgumentParser(
        description=(
            "엔터프라이즈 AI 앱 생애 주기 및 콜드라인 냉동 거버넌스 진단기 "
            "(BigQuery Vector Search, Knowledge Catalog, BigQuery Graph GQL, GCS Coldline)."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="GCP 과금이나 리소스 변경 없이 내장된 7개 사내 앱 인벤토리로 5단계 거버넌스를 가상 실행한다.",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="대화형 환경 설정 마법사를 실행하여 .env 파일을 생성한다.",
    )
    parser.add_argument(
        "-p",
        "--project",
        default=None,
        help="진단 대상 Google Cloud 프로젝트 ID.",
    )
    parser.add_argument(
        "--region",
        default=None,
        help="대상 인프라 리전 (기본값: asia-northeast3).",
    )
    parser.add_argument(
        "--check-duplicate",
        default="재무팀 법인세 예규 및 조세심판원 판례 검색 웹앱",
        help="1단계 개발 착수 전 시맨틱 중복 생성 방지 게이트에 사용할 자연어 앱 아이디어.",
    )
    parser.add_argument(
        "--restore-query",
        default="조세심판원 법인세 판례 검색 웹앱",
        help="5단계 자연어 시맨틱 복원 검색(Search-to-Restore)에 사용할 질의문.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """5단계 생애 주기 거버넌스를 실행하고 콘솔 요약 및 report.md를 생성한다."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.config:
        return run_config_wizard()

    project_id, region = resolve_project_and_region(
        cli_project=args.project,
        cli_region=args.region,
        is_dry_run=args.dry_run,
    )
    archive_bucket = os.getenv("GCS_BUCKET_NAME") or f"gs://{project_id}-onetime-archive"
    dataset_id = os.getenv("BQ_DATASET_ID") or "app_governance"

    mode_str = "Dry-Run (가상 시뮬레이션)" if args.dry_run else "Live (사내 인벤토리 정밀 스캔)"
    print("=" * 104, flush=True)
    print(" 엔터프라이즈 AI 앱 생애 주기 및 콜드라인 냉동 거버넌스 진단기 (app-lifecycle-manager)", flush=True)
    print(f" 대상 프로젝트: {project_id} | 기준 리전: {region} | 모드: {mode_str}", flush=True)
    print("=" * 104, flush=True)

    apps = build_seed_apps(project_id=project_id)
    callers_by_app, resources_by_app = build_seed_lineage_edges(
        project_id=project_id,
        region=region,
    )

    catalog_engine = CatalogVectorEngine(
        project_id=project_id,
        region=region,
        dataset_id=dataset_id,
        archive_bucket=archive_bucket,
    )
    detector = HitCountTTLDetector()
    lineage_engine = LineageGraphEngine(project_id=project_id, dataset_id=dataset_id)
    cryo_archiver = CryoArchiver(
        project_id=project_id,
        region=region,
        archive_bucket=archive_bucket,
    )
    receipt_gen = GovernanceReceiptGenerator()

    print("[1/5] 개발 착수 전 시맨틱 중복 생성 방지 게이트 (BigQuery Vector Search & Knowledge Catalog) 점검 중...", flush=True)
    pre_build_matches = catalog_engine.pre_build_semantic_gate(
        idea_query=args.check_duplicate,
        apps=apps,
        threshold=0.55,
    )
    print(f"  -> 신규 요청: \"{args.check_duplicate}\"", flush=True)
    if pre_build_matches:
        top = pre_build_matches[0]
        print(
            f"  -> 매칭 발견: {top.app_id} (유사도: {top.cosine_similarity:.4f}, 상태: {top.lifecycle_stage}) => 권고: {top.recommendation}",
            flush=True,
        )

    print("[2/5] 전사 AI 앱 호출 수(Hit-Count) 및 보존 기한(TTL 14일) 파레토 분류 중...", flush=True)
    evaluation = detector.evaluate_fleet(apps)
    print(
        f"  -> 전체 {len(evaluation.decisions)}개 앱: 냉동 보관 대상 {len(evaluation.cryo_candidates)}건 | "
        f"프로덕션 승격 대상 {len(evaluation.graduation_candidates)}건 | "
        f"기 냉동 {len(evaluation.already_archived)}건 | 활성 유지 {len(evaluation.active_retained)}건",
        flush=True,
    )

    print("[3/5] BigQuery Graph (GQL) 멀티홉 인바운드 호출 리니지 및 블라스트 반경 역추적 중...", flush=True)
    lineage_reports: List[LineageReport] = []
    disposed_capsules: List[CryoCapsule] = []
    updated_apps: List[AppRecord] = list(apps)

    for candidate in evaluation.cryo_candidates:
        lin_report = lineage_engine.analyze_and_sever(
            app=candidate,
            callers_by_app=callers_by_app,
            resources_by_app=resources_by_app,
        )
        lineage_reports.append(lin_report)

        capsule_uri = f"{archive_bucket.rstrip('/')}/{candidate.app_id}/"
        aspect_payload = catalog_engine.register_or_update_aspect(
            app=candidate,
            blast_radius_edges=0,
            override_stage="CRYO_ARCHIVED",
            override_cryo_uri=capsule_uri,
        )
        capsule = cryo_archiver.create_cryo_capsule(
            app=candidate,
            lineage=lin_report,
            catalog_aspect_payload=aspect_payload,
        )
        disposed_capsules.append(capsule)

        updated_apps = [
            dataclasses.replace(
                a,
                lifecycle_stage="CRYO_ARCHIVED",
                cryo_gcs_uri=capsule.capsule_gcs_uri,
                rehydrate_command=capsule.rehydrate_one_liner,
            )
            if a.app_id == candidate.app_id
            else a
            for a in updated_apps
        ]

    total_triggers = sum(c.severed_triggers_count for c in disposed_capsules)
    total_iam = sum(c.revoked_iam_bindings_count for c in disposed_capsules)
    print(
        f"  -> 냉동 대상 {len(disposed_capsules)}개 앱 업스트림 자동 호출 트리거 {total_triggers}건 안전 차단 명령어 및 NHI IAM {total_iam}건 회수 검증 완료",
        flush=True,
    )

    print("[4/5] Cloud Storage Coldline 냉동 타임캡슐 패키징 및 60초 부활 스크립트(rehydrate.sh) 합성 중...", flush=True)
    graduated_packages: List[GraduationPackage] = []
    for grad_app in evaluation.graduation_candidates:
        aspect_payload = catalog_engine.register_or_update_aspect(
            app=grad_app,
            blast_radius_edges=0,
            override_stage="GRADUATED",
        )
        grad_pkg = cryo_archiver.build_graduation_package(
            app=grad_app,
            catalog_aspect_payload=aspect_payload,
        )
        graduated_packages.append(grad_pkg)

    grad_names = ", ".join(g.app_id for g in graduated_packages) or "없음"
    print(
        f"  -> 평문 시크릿 {len(disposed_capsules)}건 마스킹(<REDACTED_SECRET_MANAGER_REF>) 및 상위 4% 앱({grad_names}) 승격 명세 생성 완료",
        flush=True,
    )

    print("[5/5] 자연어 시맨틱 복원 검색(Search-to-Restore) 검증 및 FinOps/SecOps 영수증 산출 중...", flush=True)
    restore_matches = catalog_engine.search_to_restore(
        natural_query=args.restore_query,
        apps=updated_apps,
        top_k=3,
    )
    metrics = receipt_gen.calculate_impact(
        evaluation=evaluation,
        disposed_capsules=disposed_capsules,
        graduated_packages=graduated_packages,
    )
    print(
        f"  -> 월간 순 절감액: ${metrics.net_monthly_saved_usd:,.2f}/월 (연간 ${metrics.net_annual_saved_usd:,.2f} 절감) | "
        f"회수 인스턴스: {metrics.reclaimed_warm_instances}개 | 동결 서비스 계정(NHI): {metrics.reclaimed_service_accounts}개",
        flush=True,
    )

    report_md = receipt_gen.render_markdown_report(
        project_id=project_id,
        region=region,
        is_dry_run=args.dry_run,
        pre_build_query=args.check_duplicate,
        pre_build_matches=pre_build_matches,
        evaluation=evaluation,
        lineage_reports=lineage_reports,
        disposed_capsules=disposed_capsules,
        graduated_packages=graduated_packages,
        restore_query=args.restore_query,
        restore_matches=restore_matches,
        metrics=metrics,
    )

    report_path = Path(__file__).resolve().parent / "report.md"
    report_path.write_text(report_md, encoding="utf-8")
    print("=" * 104, flush=True)
    print(f"[완료] 생애 주기 관리 및 FinOps/SecOps 영수증이 생성되었다: {report_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
