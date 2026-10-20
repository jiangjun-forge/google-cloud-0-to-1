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
# SPDX-License-Identifier: Apache-2.0

"""
BigQuery Data Agent 45-Minute Hands-on Starter Kit (Standalone & Optional Gemini Enterprise app).

45분 핸즈온 워크숍 내에 참석자(실무자)가 CLI 명령어 한 줄(--setup-demo)로 BigQuery 스몰셋 데이터셋(cymbal_gold)과
실데이터를 자동 구축하고, 완전 관리형 에이전트 엔진(GDA dataAgents REST API)을 통해 CLI 원클릭(--deploy-agent)으로
빅쿼리 데이터 에이전트를 자동 프로비저닝하며, A2A 표준 규격 기반으로 Gemini Enterprise App에 직결 연동하거나
BigQuery Studio Agents 콘솔 UI에서 단독(Standalone)으로 실습할 수 있도록 설계된 실무 스타터 키트다.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


# ==============================================================================
# 1. 환경 변수 및 gcloud 설정 캐스케이드 탐색 (Cascade Fallback & Interactive Selector)
# ==============================================================================
def run_gcloud_cmd(args: List[str]) -> Optional[str]:
    """gcloud CLI 명령어를 실행하고 표준 출력을 반환한다."""
    try:
        result = subprocess.run(
            ["gcloud"] + args,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_resource_creator(dry_run: bool = False) -> str:
    """CLI 실행 계정으로부터 GCP 표준 라벨 형식에 부합하는 풀 프린시펄(Full Principal) 문자열을 추출한다."""
    if dry_run:
        return "customer-engineer"
    account = run_gcloud_cmd(["config", "get-value", "account"]) or os.environ.get("USER") or "customer-engineer"
    clean = account.lower().replace("@", "-at-").replace(".", "-").replace(":", "-").replace("_", "-")
    sanitized = "".join(c for c in clean if c.isalnum() or c == "-").strip("-")
    return sanitized[:63] if sanitized else "customer-engineer"


def interactive_select(prompt_msg: str, candidates: List[str], default_idx: int = 0) -> str:
    """터미널 대화형 환경에서 번호 선택기를 제공한다."""
    if not candidates:
        return ""
    if not sys.stdin.isatty():
        return candidates[default_idx]

    print(f"\n[선택] {prompt_msg}")
    for idx, val in enumerate(candidates, start=1):
        marker = " (기본값)" if (idx - 1) == default_idx else ""
        print(f"  [{idx}] {val}{marker}")
    try:
        choice = input(f"선택할 번호를 입력한다 [Enter 입력 시 {default_idx + 1}번 자동 선택]: ").strip()
        if not choice:
            return candidates[default_idx]
        selected = int(choice) - 1
        if 0 <= selected < len(candidates):
            return candidates[selected]
    except Exception:
        pass
    return candidates[default_idx]


def load_env_file(filepath: str = ".env") -> None:
    """로컬 .env 파일이 존재하는 경우 환경 변수를 메모리에 로드한다."""
    p = Path(filepath)
    if not p.is_file():
        script_dir = Path(__file__).resolve().parent
        p = script_dir / filepath
    if p.is_file():
        try:
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key and key not in os.environ:
                            os.environ[key] = val
        except Exception:
            pass


def resolve_config(cli_args: argparse.Namespace) -> Dict[str, Any]:
    """CLI 인자 > .env > gcloud config > 대화형 선택기 > 사내 권장 기본값 순으로 설정을 확정한다."""
    load_env_file()
    project_id = cli_args.project or os.environ.get("PROJECT_ID", "").strip()
    if cli_args.dry_run:
        project_id = project_id or "sample-project-id"
    elif not project_id:
        gcloud_proj = run_gcloud_cmd(["config", "get-value", "project"])
        if gcloud_proj and gcloud_proj != "(unset)":
            project_id = gcloud_proj
        else:
            proj_list_str = run_gcloud_cmd(["projects", "list", "--format=value(projectId)", "--limit=5"])
            if proj_list_str:
                candidates = [p.strip() for p in proj_list_str.splitlines() if p.strip()]
                project_id = interactive_select("대상 Google Cloud 프로젝트를 선택하시오:", candidates)
    if not project_id:
        project_id = "sample-project-id"

    project_number = getattr(cli_args, "project_number", None) or os.environ.get("PROJECT_NUMBER", "").strip()
    if not project_number and not cli_args.dry_run:
        gcloud_pnum = run_gcloud_cmd(["projects", "describe", project_id, "--format=value(projectNumber)"])
        if gcloud_pnum:
            project_number = gcloud_pnum
    if not project_number:
        project_number = "123456789012"

    location = cli_args.location or os.environ.get("LOCATION", "").strip()
    if not location and not cli_args.dry_run:
        gcloud_loc = run_gcloud_cmd(["config", "get-value", "compute/region"])
        if gcloud_loc and gcloud_loc != "(unset)":
            location = gcloud_loc
    if not location:
        location = "asia-northeast3"

    dataset_id = cli_args.dataset or os.environ.get("BQ_DATASET_ID", "").strip() or "cymbal_gold"
    ge_app_id = (
        cli_args.ge_app_id
        or os.environ.get("GE_APP_ID", "").strip()
        or "omni-retail-ge-app"
    )
    data_agent_name = cli_args.agent_name or os.environ.get("DATA_AGENT_NAME", "").strip() or "cymbal-retail-data-agent"
    gda_location = getattr(cli_args, "gda_location", None) or os.environ.get("GDA_LOCATION", "").strip() or "global"

    # 대상 데이터셋이 BigQuery에 이미 존재하는 경우 실제 리전 위치로 자동 동기화
    if not cli_args.dry_run and not cli_args.location and not os.environ.get("LOCATION"):
        try:
            from google.cloud import bigquery  # type: ignore
            bq_probe = bigquery.Client(project=project_id)
            existing_ds = bq_probe.get_dataset(f"{project_id}.{dataset_id}")
            if existing_ds.location and existing_ds.location != location:
                print(f"[자동 감지] 기존 데이터셋({dataset_id})의 리전({existing_ds.location})을 자동 감지하여 적용한다.")
                location = existing_ds.location
        except Exception:
            pass

    return {
        "project_id": project_id,
        "project_number": project_number,
        "location": location,
        "gda_location": gda_location,
        "dataset_id": dataset_id,
        "ge_app_id": ge_app_id,
        "data_agent_name": data_agent_name,
        "dry_run": cli_args.dry_run,
    }


# ==============================================================================
# 2. BigQuery Data Agent UI 입력용 System Instructions 및 Verified Queries 3선
# ==============================================================================
SYSTEM_INSTRUCTIONS_TEMPLATE = """당신은 엔터프라이즈 옴니채널 유통 그룹의 공식 BigQuery 데이터 에이전트(cymbal-retail-data-agent)다.
사용자의 자연어 질문에 답변할 때 반드시 아래의 비즈니스 계산 공식과 스키마 규칙을 엄격히 준수하여 SQL을 생성한다.

[핵심 비즈니스 계산 공식 (Business Formulas)]
1. 순매출액(Net Revenue, 원화):
   - 공식: SUM(subtotal_amount - discount + tax_amount) AS net_revenue
   - 대상 테이블/뷰: `{project_id}.{dataset_id}.v_cymbal_retail_semantic` (또는 `pos_transactions_gold`)
2. 결품 예상 커버 시간(Inventory Cover Hours, 시간):
   - 공식: ROUND(SAFE_DIVIDE((shelf_qty + backroom_qty), (total_units_sold_intraday / 12.0)), 1) AS est_cover_hours
   - 설명: 매장 진열 재고(shelf_qty)와 창고 재고(backroom_qty)의 합계를 시간당 평균 판매량(total_units_sold_intraday / 12.0)으로 나누어 산출하며, 6.0시간 이하일 경우 '긴급 발주 대상(CRITICAL_STOCKOUT_RISK)'으로 분류한다.
   - 대상 테이블/뷰: `{project_id}.{dataset_id}.v_cymbal_retail_semantic` (또는 `gold_inventory_reconciliation_ledger`)
3. 캐셔 프로모션 남용률(Cashier Promo Override Rate, %):
   - 공식: ROUND(SAFE_DIVIDE(COUNTIF(alert_type = 'cashier_promo_abuse'), COUNT(*)) * 100, 2) AS promo_override_rate_pct
   - 대상 테이블/뷰: `{project_id}.{dataset_id}.v_cymbal_retail_semantic` (또는 `pos_anomaly_alerts`)
"""

GOLDEN_PROMPTS: List[Dict[str, Any]] = [
    {
        "id": "PROMPT-01",
        "title": "지점 및 결제 수단별 순매출(Net Revenue) 및 할인 금액 집계",
        "user_prompt": "지점(store_branch) 및 결제 수단(tender_type)별 총상품 금액(subtotal_amount), 할인 금액(discount), 세금(tax_amount)을 반영한 순매출(Net Revenue)을 비교해 줘.",
        "expected_sql": (
            "SELECT store_branch, tender_type, "
            "SUM(subtotal_amount) AS gross_subtotal, "
            "SUM(discount) AS total_discount, "
            "SUM(net_revenue) AS net_revenue "
            "FROM `{project_id}.{dataset_id}.v_cymbal_retail_semantic` "
            "GROUP BY store_branch, tender_type ORDER BY net_revenue DESC;"
        ),
        "sample_rows": [
            {"store_branch": "백화점 본점", "tender_type": "CREDIT_CARD", "gross_subtotal": 520000000, "total_discount": 35000000, "net_revenue": 533500000},
            {"store_branch": "백화점 잠실점", "tender_type": "MOBILE_PAY", "gross_subtotal": 330000000, "total_discount": 25000000, "net_revenue": 335500000},
            {"store_branch": "하이퍼마켓 서울역점", "tender_type": "CREDIT_CARD", "gross_subtotal": 310000000, "total_discount": 40000000, "net_revenue": 297000000},
        ],
    },
    {
        "id": "PROMPT-02",
        "title": "결품 예상 커버 시간(Cover Hours) 6시간 이하 긴급 보충 품목 탐지",
        "user_prompt": "현재 진열 재고(shelf_qty)와 창고 재고(backroom_qty) 합계를 시간당 판매 속도로 나눴을 때, 결품 예상 커버 시간(est_cover_hours)이 6시간 이하인 긴급 보충 대상 지점과 품목(item_sku)을 알려 줘.",
        "expected_sql": (
            "SELECT DISTINCT store_branch, item_sku, category, shelf_qty, backroom_qty, total_units_sold_intraday, est_cover_hours "
            "FROM `{project_id}.{dataset_id}.v_cymbal_retail_semantic` "
            "WHERE est_cover_hours <= 6.0 "
            "ORDER BY est_cover_hours ASC;"
        ),
        "sample_rows": [
            {"store_branch": "하이퍼마켓 서울역점", "item_sku": "SKU-FRESH-001", "category": "Fresh_Food (신선식품)", "shelf_qty": 20, "backroom_qty": 40, "total_units_sold_intraday": 144, "est_cover_hours": 5.0},
            {"store_branch": "백화점 잠실점", "item_sku": "SKU-LUX-088", "category": "Luxury_Cosmetics (명품화장품)", "shelf_qty": 8, "backroom_qty": 12, "total_units_sold_intraday": 42, "est_cover_hours": 5.7},
        ],
    },
    {
        "id": "PROMPT-03",
        "title": "캐셔 프로모션 임의 할인 남용(cashier_promo_abuse) 이상 거래 진단",
        "user_prompt": "이상 거래 경보 테이블(pos_anomaly_alerts)에서 프로모션 남용(cashier_promo_abuse) 경보가 발생한 지점과 담당 캐셔 ID, 심각도(severity)를 보여 줘.",
        "expected_sql": (
            "SELECT DISTINCT store_branch, cashier_id, alert_type, severity, promo_override_rate "
            "FROM `{project_id}.{dataset_id}.v_cymbal_retail_semantic` "
            "WHERE alert_type = 'cashier_promo_abuse' "
            "ORDER BY promo_override_rate DESC;"
        ),
        "sample_rows": [
            {"store_branch": "하이퍼마켓 부산점", "cashier_id": "EMP-9012", "alert_type": "cashier_promo_abuse", "severity": "CRITICAL", "promo_override_rate": 0.28},
            {"store_branch": "백화점 본점", "cashier_id": "EMP-3314", "alert_type": "cashier_promo_abuse", "severity": "HIGH", "promo_override_rate": 0.19},
        ],
    },
]


# ==============================================================================
# 3. [CLI 자동화 구간] 스몰셋 데이터셋(cymbal_gold) + 4개 테이블 + 실데이터 구축 (--setup-demo)
# ==============================================================================
def setup_smallset_demo(cfg: Dict[str, Any]) -> None:
    """실제 BigQuery에 cymbal_gold 데이터셋과 4개 스몰셋 테이블 및 실데이터를 원클릭 구축한다."""
    project_id = cfg["project_id"]
    dataset_id = cfg["dataset_id"]
    location = cfg["location"]
    creator = get_resource_creator(cfg["dry_run"])

    print("=" * 88)
    print(" [Step 1: CLI 자동화 구간] 45분 워크숍용 BigQuery 스몰셋 데이터셋(cymbal_gold) 구축")
    print(f"  - 대상 프로젝트 : {project_id}")
    print(f"  - 대상 데이터셋 : {dataset_id} (리전: {location})")
    print("  - 특징         : 4개 원천 테이블 + 실데이터 적재 + 즉시 실습용 시맨틱 뷰 생성")
    print("=" * 88)

    ddl_and_dml_statements = [
        (
            "1. POS 거래 원천 테이블 생성 (pos_transactions_gold - 메타데이터 보강 전 상태)",
            f"""
CREATE OR REPLACE TABLE `{project_id}.{dataset_id}.pos_transactions_gold` (
    transaction_id STRING OPTIONS(description="POS 거래 고유 번호"),
    sale_date DATE OPTIONS(description="거래 일자"),
    store_branch STRING,
    tender_type STRING,
    subtotal_amount NUMERIC,
    discount NUMERIC,
    tax_amount NUMERIC,
    total NUMERIC
)
OPTIONS(
    description="POS 거래 원천 테이블",
    labels=[("managed-by", "google-cloud-0-to-1"), ("scenario", "bigquery-data-agent-starter"), ("env", "sample"), ("created-by", "{creator}")]
);
""",
        ),
        (
            "2. 매장 재고 대사 원장 테이블 생성 (gold_inventory_reconciliation_ledger - 메타데이터 보강 전 상태)",
            f"""
CREATE OR REPLACE TABLE `{project_id}.{dataset_id}.gold_inventory_reconciliation_ledger` (
    store_branch STRING OPTIONS(description="오프라인 매장 지점명"),
    item_sku STRING,
    category STRING,
    shelf_qty INT64,
    backroom_qty INT64,
    total_units_sold_intraday INT64,
    est_cover_hours FLOAT64
)
OPTIONS(
    description="매장 재고 대사 원장 테이블",
    labels=[("managed-by", "google-cloud-0-to-1"), ("scenario", "bigquery-data-agent-starter"), ("env", "sample"), ("created-by", "{creator}")]
);
""",
        ),
        (
            "3. POS 이상 거래 경보 테이블 생성 (pos_anomaly_alerts - 메타데이터 보강 전 상태)",
            f"""
CREATE OR REPLACE TABLE `{project_id}.{dataset_id}.pos_anomaly_alerts` (
    alert_id STRING OPTIONS(description="경보 고유 ID"),
    store_branch STRING OPTIONS(description="발생 지점명"),
    alert_date DATE OPTIONS(description="발생 일자"),
    cashier_id STRING,
    alert_type STRING,
    severity STRING,
    promo_override_rate FLOAT64
)
OPTIONS(
    description="POS 이상 거래 경보 테이블",
    labels=[("managed-by", "google-cloud-0-to-1"), ("scenario", "bigquery-data-agent-starter"), ("env", "sample"), ("created-by", "{creator}")]
);
""",
        ),
        (
            "4. 고객 구매 및 보증 이력 테이블 생성 (historical_transactional_data - 메타데이터 보강 전 상태)",
            f"""
CREATE OR REPLACE TABLE `{project_id}.{dataset_id}.historical_transactional_data` (
    customer_id STRING,
    purchase_date DATE,
    item_sku STRING,
    warranty_duration_months INT64,
    warranty_eligible BOOL
)
OPTIONS(
    description="고객 구매 및 보증 이력 테이블",
    labels=[("managed-by", "google-cloud-0-to-1"), ("scenario", "bigquery-data-agent-starter"), ("env", "sample"), ("created-by", "{creator}")]
);
""",
        ),
        (
            "5. POS 거래 샘플 데이터 적재 (INSERT INTO pos_transactions_gold)",
            f"""
INSERT INTO `{project_id}.{dataset_id}.pos_transactions_gold`
(transaction_id, sale_date, store_branch, tender_type, subtotal_amount, discount, tax_amount, total)
VALUES
  ('TX-1001', CURRENT_DATE(), '백화점 본점', 'CREDIT_CARD', 520000000, 35000000, 48500000, 533500000),
  ('TX-1002', CURRENT_DATE(), '백화점 잠실점', 'MOBILE_PAY', 330000000, 25000000, 30500000, 335500000),
  ('TX-1003', CURRENT_DATE(), '하이퍼마켓 서울역점', 'CREDIT_CARD', 310000000, 40000000, 27000000, 297000000),
  ('TX-1004', CURRENT_DATE(), '하이퍼마켓 부산점', 'CASH', 230000000, 30000000, 20000000, 220000000),
  ('TX-1005', CURRENT_DATE(), '옴니채널 온라인몰', 'CREDIT_CARD', 240000000, 40000000, 20000000, 220000000),
  ('TX-1006', CURRENT_DATE(), '옴니채널 온라인몰', 'GIFT_CARD', 180000000, 30000000, 15000000, 165000000);
""",
        ),
        (
            "6. 매장 재고 샘플 데이터 적재 (INSERT INTO gold_inventory_reconciliation_ledger)",
            f"""
INSERT INTO `{project_id}.{dataset_id}.gold_inventory_reconciliation_ledger`
(store_branch, item_sku, category, shelf_qty, backroom_qty, total_units_sold_intraday, est_cover_hours)
VALUES
  ('하이퍼마켓 서울역점', 'SKU-FRESH-001', 'Fresh_Food (신선식품)', 20, 40, 144, 5.0),
  ('백화점 잠실점', 'SKU-LUX-088', 'Luxury_Cosmetics (명품화장품)', 8, 12, 42, 5.7),
  ('백화점 본점', 'SKU-WATCH-010', 'Luxury_Watch (명품시계)', 15, 30, 18, 30.0),
  ('하이퍼마켓 부산점', 'SKU-ELEC-204', 'Electronics (가전제품)', 30, 90, 60, 24.0),
  ('옴니채널 온라인몰', 'SKU-FASH-512', 'Fashion_Apparel (패션의류)', 100, 280, 220, 20.7);
""",
        ),
        (
            "7. POS 이상 거래 경보 샘플 데이터 적재 (INSERT INTO pos_anomaly_alerts)",
            f"""
INSERT INTO `{project_id}.{dataset_id}.pos_anomaly_alerts`
(alert_id, store_branch, alert_date, cashier_id, alert_type, severity, promo_override_rate)
VALUES
  ('ALT-01', '하이퍼마켓 부산점', CURRENT_DATE(), 'EMP-9012', 'cashier_promo_abuse', 'CRITICAL', 0.28),
  ('ALT-02', '백화점 본점', CURRENT_DATE(), 'EMP-3314', 'cashier_promo_abuse', 'HIGH', 0.19),
  ('ALT-03', '하이퍼마켓 서울역점', CURRENT_DATE(), 'EMP-1044', 'manual_price_override', 'MEDIUM', 0.08);
""",
        ),
        (
            "8. 고객 보증 이력 샘플 데이터 적재 (INSERT INTO historical_transactional_data)",
            f"""
INSERT INTO `{project_id}.{dataset_id}.historical_transactional_data`
(customer_id, purchase_date, item_sku, warranty_duration_months, warranty_eligible)
VALUES
  ('CUST-7701', DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH), 'SKU-WATCH-010', 24, TRUE),
  ('CUST-8812', DATE_SUB(CURRENT_DATE(), INTERVAL 18 MONTH), 'SKU-ELEC-204', 12, FALSE);
""",
        ),
        (
            "9. Data Agent 즉시 실습용 통합 시맨틱 뷰 생성 (v_cymbal_retail_semantic)",
            f"""
CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.v_cymbal_retail_semantic`
OPTIONS(
    description="BigQuery Data Agent 단독 및 Gemini Enterprise app 연동 실습용 시맨틱 골드 뷰. 순매출(net_revenue), 결품 커버 시간(est_cover_hours), 이상 거래 경보(alert_type) 내장.",
    labels=[("managed-by", "google-cloud-0-to-1"), ("scenario", "bigquery-data-agent-starter"), ("env", "sample"), ("created-by", "{creator}")]
) AS
SELECT
    p.transaction_id,
    p.sale_date,
    p.store_branch,
    p.tender_type,
    p.subtotal_amount,
    p.discount,
    p.tax_amount,
    (p.subtotal_amount - p.discount + p.tax_amount) AS net_revenue,
    i.item_sku,
    i.category,
    i.shelf_qty,
    i.backroom_qty,
    i.total_units_sold_intraday,
    ROUND(SAFE_DIVIDE((i.shelf_qty + i.backroom_qty), (i.total_units_sold_intraday / 12.0)), 1) AS est_cover_hours,
    a.alert_id,
    a.cashier_id,
    a.alert_type,
    a.severity,
    a.promo_override_rate
FROM `{project_id}.{dataset_id}.pos_transactions_gold` p
LEFT JOIN `{project_id}.{dataset_id}.gold_inventory_reconciliation_ledger` i
  ON p.store_branch = i.store_branch
LEFT JOIN `{project_id}.{dataset_id}.pos_anomaly_alerts` a
  ON p.store_branch = a.store_branch;
""",
        ),
    ]

    if cfg["dry_run"]:
        print("[가상 실행] --dry-run 모드가 활성화되어 실제 BigQuery DDL/DML을 실행하지 않고 SQL 스크립트를 출력한다.\n")
        for title, sql in ddl_and_dml_statements:
            print(f"--- {title} ---")
            print(sql.strip())
            print()
        print("[완료] 가상 실행(--dry-run) 데이터셋 및 시맨틱 뷰 구축 계획 출력이 완료되었다.")
        return

    try:
        from google.cloud import bigquery  # type: ignore

        client = bigquery.Client(project=project_id, location=location)
        dataset_ref = bigquery.Dataset(f"{project_id}.{dataset_id}")
        dataset_ref.location = location
        dataset_ref.description = "BigQuery Data Agent 45-min Workshop Dataset"
        dataset_ref.labels = {
            "managed-by": "google-cloud-0-to-1",
            "scenario": "bigquery-data-agent-starter",
            "env": "sample",
            "created-by": get_resource_creator(cfg["dry_run"]),
        }
        client.create_dataset(dataset_ref, exists_ok=True)
        print(f"  -> [성공] BigQuery 데이터셋 확인/생성 완료: {project_id}.{dataset_id}")

        for title, sql in ddl_and_dml_statements:
            print(f"  -> [실행 중] {title}...")
            job = client.query(sql)
            job.result()
            print(f"     [성공] {title} 반영 완료.")

        print("\n[완료] 45분 워크숍용 BigQuery 스몰셋 테이블 4개, 실데이터, 시맨틱 뷰 1개가 정상 구축되었다.")
    except Exception as exc:
        print(f"\n[경고] BigQuery 스몰셋 구축 중 오류가 발생하였다: {exc}")
        print("       자격 증명(gcloud auth application-default login) 또는 IAM 권한을 확인한다.")


# ==============================================================================
# 4. [REST API 자동 배포] 완전 관리형 BigQuery Data Agent (GDA dataAgents) 및 A2A 연동
# ==============================================================================
def get_access_token() -> str:
    """gcloud CLI 또는 구글 인증 라이브러리를 통해 액세스 토큰을 획득한다."""
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"],
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        ).strip()
        if token:
            return token
    except Exception:
        pass

    try:
        import google.auth  # type: ignore
        import google.auth.transport.requests  # type: ignore

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        req = google.auth.transport.requests.Request()
        credentials.refresh(req)
        return credentials.token
    except Exception as exc:
        print(f"[경고] 액세스 토큰 획득 실패: {exc}", file=sys.stderr)
        return ""


def discover_ge_app_engines(project_id: str) -> List[Dict[str, str]]:
    """현재 프로젝트에 프로비저닝된 Gemini Enterprise App (Discovery Engine) 목록을 실시간 조회한다."""
    if not project_id or project_id == "sample-project-id":
        return []

    token = get_access_token()
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


def send_request(
    url: str,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """구글 클라우드 REST API 요청을 송신하고 JSON 응답을 반환한다."""
    if token is None:
        token = get_access_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if project_id:
        headers["X-Goog-User-Project"] = project_id

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_body = resp.read().decode("utf-8")
            return json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        error_content = e.read().decode("utf-8")
        print(f"[API 요청 실패] [{method} {url}]: HTTP {e.code} {e.reason}", file=sys.stderr)
        print(f"  응답 본문: {error_content}", file=sys.stderr)
        raise
    except Exception as exc:
        print(f"[네트워크 오류] [{method} {url}]: {exc}", file=sys.stderr)
        raise


def poll_operation(operation_url: str, token: str, project_id: str, timeout_seconds: int = 120) -> Dict[str, Any]:
    """장기 실행 작업(LRO)의 완료를 폴링하여 대기한다."""
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        resp = send_request(operation_url, method="GET", token=token, project_id=project_id)
        if resp.get("done", False):
            if "error" in resp:
                raise RuntimeError(f"LRO 작업 실행 실패: {resp['error']}")
            return resp
        time.sleep(3)
    raise TimeoutError(f"작업 대기 시간 초과 ({timeout_seconds}초): {operation_url}")


def list_existing_gda_agents(project_id: str, location: str, token: str) -> Dict[str, str]:
    """기존 생성된 GDA dataAgent 목록을 조회하여 표시 이름 기준 맵을 반환한다."""
    url = f"https://geminidataanalytics.googleapis.com/v1beta/projects/{project_id}/locations/{location}/dataAgents"
    try:
        resp = send_request(url, method="GET", token=token, project_id=project_id)
        agents = resp.get("dataAgents", [])
        return {a.get("displayName"): a.get("name") for a in agents if "displayName" in a}
    except Exception as e:
        print(f"[안내] GDA 에이전트 목록 조회 참고: {e}", file=sys.stderr)
        return {}


def create_gda_data_agent(cfg: Dict[str, Any], token: Optional[str] = None) -> str:
    """GDA dataAgents REST API를 호출하여 완전 관리형 BigQuery Data Agent를 자동 생성한다."""
    project_id = cfg["project_id"]
    dataset_id = cfg["dataset_id"]
    location = cfg["gda_location"]
    agent_name = cfg["data_agent_name"]

    print("=" * 88)
    print(" [Step 2: CLI 자동화 구간] 구글 완전 관리형 테넌트 GDA dataAgents 원클릭 프로비저닝")
    print(f"  - 대상 프로젝트 : {project_id}")
    print(f"  - 대상 데이터셋 : {dataset_id}")
    print(f"  - GDA 런타임 리전: {location}")
    print(f"  - 에이전트 표시명: {agent_name}")
    print("=" * 88)

    tables = [
        "v_cymbal_retail_semantic",
        "pos_transactions_gold",
        "gold_inventory_reconciliation_ledger",
        "pos_anomaly_alerts",
        "historical_transactional_data",
    ]
    table_refs = [
        {"projectId": project_id, "datasetId": dataset_id, "tableId": tbl}
        for tbl in tables
    ]

    example_queries = [
        {
            "naturalLanguageQuestion": p["user_prompt"],
            "sqlQuery": p["expected_sql"].format(project_id=project_id, dataset_id=dataset_id),
        }
        for p in GOLDEN_PROMPTS
    ]

    sys_inst = SYSTEM_INSTRUCTIONS_TEMPLATE.format(project_id=project_id, dataset_id=dataset_id)
    context_payload = {
        "systemInstruction": sys_inst,
        "options": {
            "datasource": {},
            "model": "MODEL_UNSPECIFIED",
        },
        "exampleQueries": example_queries,
        "datasourceReferences": {
            "bq": {
                "tableReferences": table_refs
            }
        },
    }

    payload = {
        "displayName": agent_name,
        "description": "Cymbal Retail Omnichannel BigQuery Data Agent (45-min Workshop)",
        "labels": {
            "managed-by": "google-cloud-0-to-1",
            "scenario": "bigquery-data-agent-starter",
            "env": "sample",
            "created-by": get_resource_creator(cfg["dry_run"]),
        },
        "dataAnalyticsAgent": {
            "stagingContext": context_payload,
            "publishedContext": context_payload,
        },
    }

    if cfg["dry_run"]:
        print("[가상 실행] --dry-run 모드가 활성화되어 GDA REST API 호출 페이로드를 시뮬레이션 출력한다.\n")
        print(f"POST https://geminidataanalytics.googleapis.com/v1beta/projects/{project_id}/locations/{location}/dataAgents")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        mock_resource = f"projects/{project_id}/locations/{location}/dataAgents/{agent_name}-mock-id"
        print(f"\n[완료] 가상 실행 GDA Data Agent 리소스 경로: {mock_resource}")
        return mock_resource

    if token is None:
        token = get_access_token()
        if not token:
            print("[오류] Google Cloud 인증 토큰을 획득할 수 없다. gcloud auth application-default login을 수행하라.", file=sys.stderr)
            return ""

    existing = list_existing_gda_agents(project_id, location, token)
    if agent_name in existing:
        resource_name = existing[agent_name]
        print(f"  -> [재사용] 기존 GDA Data Agent 발견: {agent_name} -> {resource_name}")
        return resource_name

    url = f"https://geminidataanalytics.googleapis.com/v1beta/projects/{project_id}/locations/{location}/dataAgents"
    print(f"  -> [요청 중] GDA Data Agent 리소스 프로비저닝 시작: {agent_name}...")
    try:
        lro = send_request(url, method="POST", payload=payload, token=token, project_id=project_id)
        op_name = lro.get("name")
        print(f"  -> [LRO 진행 중] 장기 실행 작업 폴링: {op_name}")
        op_url = f"https://geminidataanalytics.googleapis.com/v1beta/{op_name}"
        completed_op = poll_operation(op_url, token=token, project_id=project_id)

        target_resource = (
            completed_op.get("response", {}).get("name")
            or completed_op.get("metadata", {}).get("target")
            or f"projects/{project_id}/locations/{location}/dataAgents/{agent_name}"
        )
        print(f"  -> [성공] GDA Data Agent 생성 완료: {target_resource}")
        return target_resource
    except Exception as exc:
        print(f"  -> [경고] GDA REST API 자동 생성 실패: {exc}", file=sys.stderr)
        print("       (사내 환경에 GDA API 활성화 또는 권한이 부족한 경우 콘솔 UI 보조 경로를 사용할 수 있다: python diagnose.py --agent-config)")
        return ""


def build_a2a_agent_card(cfg: Dict[str, Any], gda_resource_name: str) -> Dict[str, Any]:
    """A2A Agent Card 표준 규격 딕셔너리를 생성하고 로컬 파일(a2a_agent_card.json)로 저장한다."""
    project_id = cfg["project_id"]
    agent_name = cfg["data_agent_name"]

    a2a_url = f"https://geminidataanalytics.googleapis.com/v1beta/a2a/{gda_resource_name}"
    extensions = [
        {
            "uri": "https://www.googleapis.com/gemini-enterprise/a2a/extensions/full_history_when_stateless/v1",
            "description": "Communicate in a stateless mode",
            "required": True,
        },
        {
            "uri": "https://docs.cloud.google.com/gemini/docs/conversational-analytics-api/reference/a2a/extensions/client-id/v1",
            "description": "GDA API client ID",
            "required": True,
        },
        {
            "uri": "https://a2ui.org/a2a-extension/a2ui/v0.8",
            "description": "Ability to render A2UI",
            "required": False,
            "params": {
                "supportedCatalogIds": [
                    "https://a2ui.org/specification/v0_8/standard_catalog_definition.json"
                ],
                "acceptsInlineCatalogs": True,
            },
        },
        {
            "uri": "https://www.googleapis.com/gemini-enterprise/a2a/extensions/starter_prompts/v1",
            "description": "Recommended starter prompts for UI chips",
            "required": False,
            "params": {
                "prompts": [p["user_prompt"] for p in GOLDEN_PROMPTS],
            },
        },
    ]

    skills = [
        {
            "id": "sales-net-revenue-analytics",
            "name": "Omnichannel Sales & Net Revenue Analysis",
            "description": "Analyzes store branches, tender types, discounts, taxes, and net revenue.",
            "inputModes": ["text/plain", "application/json"],
            "outputModes": ["text/plain", "application/json"],
            "tags": ["sales", "revenue", "retail", "omnichannel"],
        },
        {
            "id": "inventory-cover-hours-guard",
            "name": "Inventory Stockout Risk & Cover Hours Evaluation",
            "description": "Calculates remaining shelf and backroom inventory cover hours based on hourly sales velocity.",
            "inputModes": ["text/plain", "application/json"],
            "outputModes": ["text/plain", "application/json"],
            "tags": ["inventory", "stockout", "supplychain"],
        },
        {
            "id": "pos-anomaly-cashier-audit",
            "name": "POS Anomaly Alerts & Cashier Promo Abuse Detection",
            "description": "Identifies suspicious cashier promo overrides, manual price changes, and anomaly severity.",
            "inputModes": ["text/plain", "application/json"],
            "outputModes": ["text/plain", "application/json"],
            "tags": ["fraud", "anomaly", "audit", "compliance"],
        },
    ]

    card: Dict[str, Any] = {
        "name": agent_name,
        "displayName": "Cymbal Retail Conversational Analytics Agent",
        "description": "엔터프라이즈 옴니채널 유통 그룹의 공식 BigQuery 대화형 데이터 분석 에이전트.",
        "url": a2a_url,
        "version": "1.0",
        "protocolVersion": "1.0",
        "preferredTransport": "INTERNAL_HTTP+JSON",
        "defaultInputModes": ["text/plain", "application/json"],
        "defaultOutputModes": ["text/plain", "application/json"],
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
            "extensions": extensions,
        },
        "skills": skills,
    }

    card_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "a2a_agent_card.json")
    try:
        with open(card_path, "w", encoding="utf-8") as f:
            json.dump(card, f, indent=2, ensure_ascii=False)
        print(f"  -> [파일 저장] A2A Agent Card 표준 규격 JSON 저장 완료: {card_path}")
    except Exception as exc:
        print(f"  -> [경고] Agent Card 파일 저장 실패: {exc}", file=sys.stderr)

    return card


def register_agent_to_ge_app_api(
    cfg: Dict[str, Any],
    card_content: Dict[str, Any],
    token: Optional[str] = None,
) -> Optional[str]:
    """Discovery Engine REST API를 호출하여 Gemini Enterprise App 엔진에 A2A 에이전트를 직결 등록한다."""
    project_number = cfg["project_number"]
    engine_id = cfg["ge_app_id"]
    agent_name = cfg["data_agent_name"]
    project_id = cfg["project_id"]

    print("=" * 88)
    print(f" [Step 3: 선택 사항 (Optional)] Discovery Engine API 기반 Gemini Enterprise App ({engine_id}) 직결 등록")
    print("=" * 88)

    ge_app_agents_url = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_number}/"
        f"locations/global/collections/default_collection/engines/{engine_id}/"
        f"assistants/default_assistant/agents"
    )

    starter_prompts = [p["user_prompt"] for p in GOLDEN_PROMPTS]
    payload: Dict[str, Any] = {
        "displayName": "Cymbal Retail Conversational Analytics Agent",
        "description": "BigQuery cymbal_gold 데이터셋 기반 대화형 데이터 분석 에이전트",
        "state": "ENABLED",
        "a2aAgentDefinition": {
            "jsonAgentCard": json.dumps(card_content, ensure_ascii=False),
        },
        "agentInvocationSpec": {
            "invocationMode": "AUTOMATIC",
        },
        "starterPrompts": [{"text": p} for p in starter_prompts],
    }

    if cfg["dry_run"]:
        print("[가상 실행] --dry-run 모드가 활성화되어 Discovery Engine 등록 페이로드를 출력한다.\n")
        print(f"POST {ge_app_agents_url}")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        mock_ge_resource = f"projects/{project_number}/locations/global/collections/default_collection/engines/{engine_id}/assistants/default_assistant/agents/mock-a2a-agent"
        print(f"\n[완료] 가상 실행 GE App 에이전트 등록 경로: {mock_ge_resource}")
        return mock_ge_resource

    if token is None:
        token = get_access_token()

    try:
        resp = send_request(ge_app_agents_url, method="POST", payload=payload, token=token, project_id=project_id)
        registered_name = resp.get("name", "")
        print(f"  -> [성공] Gemini Enterprise App 사내 갤러리 등록 완료: {registered_name}")
        return registered_name
    except urllib.error.HTTPError as e:
        print(f"  -> [안내] Discovery Engine 직결 등록 API 반환 (HTTP {e.code}): 콘솔 UI 수동 등록 보조 가이드를 안내한다.")
        register_agent_to_ge_app_ui_guide(cfg)
        return None
    except Exception as exc:
        print(f"  -> [안내] Discovery Engine 직결 등록 건너뜀 ({exc}): 콘솔 UI 수동 등록 보조 가이드를 안내한다.")
        register_agent_to_ge_app_ui_guide(cfg)
        return None


def export_data_agent_config(cfg: Dict[str, Any]) -> None:
    """BigQuery Studio > Agents 콘솔 UI 수동 등록 시 복사/붙여넣기할 System Instructions와 Verified Queries를 출력한다 (보조 확인 경로)."""
    project_id = cfg["project_id"]
    dataset_id = cfg["dataset_id"]
    agent_name = cfg["data_agent_name"]

    sys_inst = SYSTEM_INSTRUCTIONS_TEMPLATE.format(project_id=project_id, dataset_id=dataset_id)

    print("=" * 88)
    print(f" [Step 2 보조 확인 경로: 콘솔 UI 수동 입력] BigQuery Studio > Agents 단독(Standalone) 에이전트 생성 가이드")
    print("=" * 88)
    print(" [안내] CLI 자동 배포(python diagnose.py --deploy-agent)를 권장하며,")
    print("       콘솔 UI에서 직접 확인하거나 수동으로 생성할 경우 아래 절차를 따른다.")
    print("-" * 88)
    print(" [콘솔 UI 클릭 순서 (소요 시간: 5분)]")
    print("  1) Google Cloud 콘솔 > BigQuery > Studio 화면 상단 [Create new] 영역에서 [AI and knowledge] 드롭다운 > [Agent] 클릭")
    print("     (또는 좌측 탐색 바에서 [Agents] 아이콘 클릭 후 상단 [+ Create Data Agent] 클릭)")
    print(f"  2) Agent name(이름)에 `{agent_name}` (또는 자유로운 실습명) 입력")
    print(f"  3) [Knowledge sources] > [Add source] 클릭 후 `{project_id}.{dataset_id}` 내 `v_cymbal_retail_semantic` 뷰(또는 원천 테이블 전체)를 체크")
    print("  4) [Instructions (지침)] 입력란에 아래 텍스트를 그대로 복사하여 붙여넣기:")
    print("-" * 88)
    print(sys_inst.strip())
    print("-" * 88)
    print("  5) [Verified queries (검증된 쿼리)] 영역에서 [Add query]를 클릭하여 아래 대표 질문-SQL 3쌍을 추가 후 상단 [Save]를 클릭한다:")
    for idx, p in enumerate(GOLDEN_PROMPTS, start=1):
        sql_clean = p["expected_sql"].format(project_id=project_id, dataset_id=dataset_id)
        print(f"\n     [Verified Query #{idx}]")
        print(f"      * Question : {p['user_prompt']}")
        print(f"      * SQL Query: {sql_clean}")
    print("\n" + "=" * 88)


def register_agent_to_ge_app_ui_guide(cfg: Dict[str, Any]) -> None:
    """[콘솔 UI 보조 경로] BigQuery Studio Agents에서 생성한 Data Agent를 Gemini Enterprise App에 A2A 방식으로 등록하는 UI 절차를 안내한다."""
    ge_app_id = cfg["ge_app_id"]
    agent_name = cfg["data_agent_name"]

    print("=" * 88)
    print(f" [Step 3 보조 확인 경로: 콘솔 UI 수동 등록] BigQuery Data Agent -> Gemini Enterprise App ({ge_app_id}) A2A 연동")
    print("=" * 88)
    print(" [안내] BigQuery Studio 내에서 단독(Standalone)으로 에이전트를 사용할 경우 본 단계는 생략 가능하다.")
    print("       생성한 에이전트를 Gemini Enterprise 웹 앱 대화창에 붙여 전사 공유하고자 할 때 콘솔 UI에서 아래 절차를 수행한다.")
    print("-" * 88)
    print(" [Phase A: BigQuery Studio > Agents에서 Agent Card (A2A JSON) 확인 및 복사]")
    print(f"  1) BigQuery Studio > 좌측 메뉴 [Agents (에이전트 / Agent Platform)] > [{agent_name}] 상세 페이지 진입")
    print("  2) 에이전트 상세 화면에서 [Publish (게시)]를 완료한 후 제공되는 [Agent Card (A2A JSON)] 텍스트 복사")
    print("     (또는 diagnose.py가 자동 생성한 a2a_agent_card.json 파일 내용 활용)")
    print("-" * 88)
    print(" [Phase B: Gemini Enterprise 관리 콘솔에서 'Custom agent via A2A'로 에이전트 등록]")
    print("  1) Google Cloud 콘솔 탐색 메뉴 > [Gemini Enterprise (또는 Agent Platform > Applications)] 메뉴 이동")
    print(f"  2) 대상 웹 앱 [{ge_app_id}] 클릭 > 좌측 관리 메뉴에서 [Agents (에이전트)] 탭 클릭")
    print("  3) 상단 [+ Add agent (에이전트 추가)] 클릭 > 'Choose an agent type' 화면에서 [Custom agent via A2A]의 [Add] 선택")
    print(f"  4) 복사해 둔 Agent Card JSON을 입력란에 붙여넣고 인증(Authentication) 설정 확인 후 [Register / Save] 클릭")
    print(f"  5) 등록 완료 후 에이전트 목록에서 [{agent_name}]의 상태 토글이 [Enabled (활성)]로 켜져 있는지 확인")
    print(f"  6) 좌측 메뉴 [Preview (미리보기)] 또는 웹 앱 URL 대화창에서 `@{agent_name}` 호출 또는 골든 프롬프트 질의 테스트를 수행한다.")
    print("=" * 88)


def deploy_full_agent_workflow(cfg: Dict[str, Any]) -> None:
    """Step 2(GDA dataAgent 배포) 및 Step 3(A2A Agent Card 생성 및 GE App 직결 등록)를 통합 수행한다."""
    token = get_access_token() if not cfg["dry_run"] else "mock-token"
    gda_resource = create_gda_data_agent(cfg, token=token)
    if not gda_resource:
        print("[경고] GDA Data Agent 리소스 경로를 획득하지 못하여 A2A Agent Card 생성을 건너뛴다.")
        return

    card = build_a2a_agent_card(cfg, gda_resource)
    register_agent_to_ge_app_api(cfg, card, token=token)


# ==============================================================================
# 5. 실습용 골든 프롬프트 3선 및 Before/After 연계 시연 가이드 (--query / 기본 진단)
# ==============================================================================
def print_workshop_guide_and_prompts(cfg: Dict[str, Any], custom_query: Optional[str] = None) -> None:
    """45분 타임어택 워크숍 전체 요약 및 골든 프롬프트 3선과 Before/After 연계 가이드를 출력한다."""
    project_id = cfg["project_id"]
    dataset_id = cfg["dataset_id"]

    print("=" * 88)
    print(" [BigQuery Data Agent 45분 완성 스몰셋 핸즈온 스타터 키트 (Standalone & Optional Gemini Enterprise app)]")
    print("=" * 88)
    print(f" - 대상 프로젝트 : {project_id} (프로젝트 번호: {cfg['project_number']})")
    print(f" - 빅쿼리 리전   : {cfg['location']} (데이터셋: {dataset_id})")
    print(f" - GDA 런타임   : {cfg['gda_location']} (에이전트 이름: {cfg['data_agent_name']})")
    print(f" - GE App 엔진  : {cfg['ge_app_id']}")
    print(f" - 실행 모드     : {'가상 모의 실행 (--dry-run)' if cfg['dry_run'] else '실제 GCP 연동 실행'}")
    print("-" * 88)

    print("\n [45분 핸즈온 워크숍 역할 분담 타임라인 (GDA 완전 관리형 골든 아키텍처)]")
    print("  * 00~05분 [Step 1 CLI 데이터 패브릭]: cymbal_gold 스몰셋 4개 테이블, 실데이터, 시맨틱 뷰 원클릭 구축 (python diagnose.py --setup-demo)")
    print("  * 05~15분 [Step 2 CLI 에이전트 엔진]: 구글 1P 완전 관리형 GDA dataAgents 원클릭 프로비저닝 (python diagnose.py --deploy-agent)")
    print("            [보조 확인 경로]: BigQuery Studio 콘솔 UI 수동 생성 지침 출력 (python diagnose.py --agent-config)")
    print("  * 15~25분 [Step 3 A2A 직결 연동]   : A2A 표준 규격 기반 Gemini Enterprise App 사내 갤러리 등록 (python diagnose.py --register-ge-app)")
    print("  * 25~45분 [Step 4 멀티턴 실습 및 종료]: 골든 프롬프트 3선 대화 질의 및 실습 종료 후 자원 정리 (python diagnose.py --teardown)")
    print("  * [올인원 모드]: Step 1~3 전체 일괄 자동 배포 실행 (python diagnose.py --all)")
    print("-" * 88)

    print("\n [실습 검증용 골든 프롬프트 3선 (Data Agent 대화창 또는 Gemini Enterprise app 공용)]")
    for p in GOLDEN_PROMPTS:
        sql_formatted = p["expected_sql"].format(project_id=project_id, dataset_id=dataset_id)
        print(f"\n  [{p['id']}] {p['title']}")
        print(f"    - 자연어 질문(Prompt) : \"{p['user_prompt']}\"")
        print(f"    - 에이전트 생성 SQL   : {sql_formatted}")
        print(f"    - 실데이터 응답 결과  :")
        for row in p["sample_rows"]:
            print(f"        {json.dumps(row, ensure_ascii=False)}")

    if custom_query:
        print("\n" + "-" * 88)
        print(f" [사용자 입력 질문 실시간 테스트]: \"{custom_query}\"")
        matched = GOLDEN_PROMPTS[0]
        if "커버" in custom_query or "재고" in custom_query or "결품" in custom_query:
            matched = GOLDEN_PROMPTS[1]
        elif "남용" in custom_query or "경보" in custom_query or "캐셔" in custom_query:
            matched = GOLDEN_PROMPTS[2]
        print(f"  -> 매칭 시맨틱 SQL: {matched['expected_sql'].format(project_id=project_id, dataset_id=dataset_id)}")
        for row in matched["sample_rows"]:
            print(f"     {json.dumps(row, ensure_ascii=False)}")

    print("\n" + "=" * 88)


def build_markdown_report(cfg: Dict[str, Any]) -> str:
    """워크숍 가이드 및 골든 프롬프트 3선 출력을 표준 마크다운 리포트로 구성한다."""
    project_id = cfg["project_id"]
    dataset_id = cfg["dataset_id"]
    mode_str = "모의 실행 (Dry-run)" if cfg["dry_run"] else "실제 GCP 연동 실행"

    lines = [
        "# 진단 및 분석 리포트: bigquery-data-agent-starter",
        "",
        f"- **생성 모드**: {mode_str}",
        f"- **대상 프로젝트**: `{project_id}`",
        f"- **빅쿼리 리전**: `{cfg['location']}` (데이터셋: `{dataset_id}`)",
        f"- **GDA 런타임**: `{cfg['gda_location']}` (에이전트 이름: `{cfg['data_agent_name']}`)",
        "- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용",
        "",
        "---",
        "",
        "## 1. 진단 실행 콘솔 출력 결과",
        "",
        "```text",
        "=" * 88,
        " [BigQuery Data Agent 45분 완성 스몰셋 핸즈온 스타터 키트 (Standalone & Optional Gemini Enterprise app)]",
        "=" * 88,
        f" - 대상 프로젝트 : {project_id} (프로젝트 번호: {cfg['project_number']})",
        f" - 빅쿼리 리전   : {cfg['location']} (데이터셋: {dataset_id})",
        f" - GDA 런타임   : {cfg['gda_location']} (에이전트 이름: {cfg['data_agent_name']})",
        f" - GE App 엔진  : {cfg['ge_app_id']}",
        f" - 실행 모드     : {'가상 모의 실행 (--dry-run)' if cfg['dry_run'] else '실제 GCP 연동 실행'}",
        "-" * 88,
        "",
        " [45분 핸즈온 워크숍 역할 분담 타임라인 (GDA 완전 관리형 골든 아키텍처)]",
        "  * 00~05분 [Step 1 CLI 데이터 패브릭]: cymbal_gold 스몰셋 4개 테이블, 실데이터, 시맨틱 뷰 원클릭 구축 (python diagnose.py --setup-demo)",
        "  * 05~15분 [Step 2 CLI 에이전트 엔진]: 구글 1P 완전 관리형 GDA dataAgents 원클릭 프로비저닝 (python diagnose.py --deploy-agent)",
        "            [보조 확인 경로]: BigQuery Studio 콘솔 UI 수동 생성 지침 출력 (python diagnose.py --agent-config)",
        "  * 15~25분 [Step 3 A2A 직결 연동]   : A2A 표준 규격 기반 Gemini Enterprise App 사내 갤러리 등록 (python diagnose.py --register-ge-app)",
        "  * 25~45분 [Step 4 멀티턴 실습 및 종료]: 골든 프롬프트 3선 대화 질의 및 실습 종료 후 자원 정리 (python diagnose.py --teardown)",
        "  * [올인원 모드]: Step 1~3 전체 일괄 자동 배포 실행 (python diagnose.py --all)",
        "-" * 88,
        "",
        " [실습 검증용 골든 프롬프트 3선 (Data Agent 대화창 또는 Gemini Enterprise app 공용)]",
    ]

    for p in GOLDEN_PROMPTS:
        sql_formatted = p["expected_sql"].format(project_id=project_id, dataset_id=dataset_id)
        lines.extend([
            f"\n  [{p['id']}] {p['title']}",
            f"    - 자연어 질문(Prompt) : \"{p['user_prompt']}\"",
            f"    - 에이전트 생성 SQL   : {sql_formatted}",
            f"    - 실데이터 응답 결과  :",
        ])
        for row in p["sample_rows"]:
            lines.append(f"        {json.dumps(row, ensure_ascii=False)}")

    lines.extend([
        "",
        "=" * 88,
        "```",
        "",
        "---",
        "",
        "## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)",
        "",
        "실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.",
        "실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:",
        "",
        "```bash",
        "python diagnose.py",
        "```",
        "",
        "---",
        "",
        "## 3. 실무자 즉각 조치 가이드 및 처방전",
        "",
        "### 1단계: 스몰셋 데이터셋 및 시맨틱 뷰 원클릭 배포",
        "명령어 한 줄로 BigQuery 스몰셋 4개 테이블, 실데이터 및 `v_cymbal_retail_semantic` 시맨틱 뷰를 자동 구축한다:",
        "```bash",
        "python diagnose.py --setup-demo",
        "```",
        "",
        "### 2단계: 구글 완전 관리형 GDA Data Agent 원클릭 프로비저닝 (권장 골든 경로)",
        "별도 컨테이너 빌드나 유휴 비용 없이 GDA `dataAgents` REST API를 통해 1초 만에 데이터 에이전트를 자동 생성하고 A2A 표준 명세를 저장한다:",
        "```bash",
        "python diagnose.py --deploy-agent",
        "```",
        "> [보조 확인 경로] 콘솔 UI에서 직접 확인하거나 수동으로 생성할 경우 `python diagnose.py --agent-config` 명령으로 System Instructions와 Verified Queries를 화면에 출력할 수 있다.",
        "",
        "### 3단계: [선택 사항] Gemini Enterprise App 사내 갤러리 A2A 직결 등록",
        "Discovery Engine REST API를 통해 전사 대화 포털의 사내 갤러리에 `a2aAgentDefinition`으로 직결 등록한다:",
        "```bash",
        "python diagnose.py --register-ge-app",
        "```",
        "",
        "### [올인원 모드] 1~3단계 통합 일괄 배포",
        "워크숍 시간 단축을 위해 데이터셋 구축, GDA 에이전트 배포, GE App 등록을 한 번에 실행한다:",
        "```bash",
        "python diagnose.py --all",
        "```",
        "",
        "### 4단계: 4대 표준 라벨 준수 및 실습 종료 후 자원 정리",
        "- 사내 거버넌스 준수를 위해 데이터셋 및 뷰 생성 시 4대 표준 라벨(`managed-by=google-cloud-0-to-1`, `scenario=bigquery-data-agent-starter`, `env=sample`, `created-by=customer-engineer`)을 누락 없이 유지한다.",
        "- 핸즈온 종료 후 불필요한 과금을 차단하기 위해 아래 명령어로 스몰셋 데이터셋을 일괄 삭제한다:",
        "```bash",
        "python diagnose.py --teardown",
        "```",
        "",
    ])

    return "\n".join(lines)


def save_markdown_report(report_md: str, output_path: str = "report.md") -> None:
    """리포트 내용을 파일에 저장한다."""
    if not os.path.isabs(output_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, output_path)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"[안내] 복습 및 사내 공유용 진단 리포트가 생성(덮어쓰기)되었다: {output_path}")
    except Exception as e:
        print(f"[경고] 리포트 파일 저장 실패 ({output_path}): {e}")


def teardown_demo_environment(cfg: Dict[str, Any]) -> None:
    """실습 종료 후 생성된 BigQuery 데모 데이터셋을 삭제하여 비용 발생을 차단한다."""
    project_id = cfg["project_id"]
    dataset_id = cfg["dataset_id"]
    agent_name = cfg["data_agent_name"]
    location = cfg["gda_location"]

    print("=" * 88)
    print(f"[자원 정리] BigQuery 스몰셋 데이터셋({project_id}.{dataset_id}) 삭제 시작")
    print("=" * 88)

    if cfg["dry_run"]:
        print(f"[가상 실행] DROP SCHEMA IF EXISTS `{project_id}.{dataset_id}` CASCADE;")
        print(f"[가상 실행] DELETE https://geminidataanalytics.googleapis.com/v1beta/projects/{project_id}/locations/{location}/dataAgents/{agent_name}")
        print("[완료] 가상 실행(--dry-run) 자원 정리 시뮬레이션이 완료되었다.")
        return

    try:
        from google.cloud import bigquery  # type: ignore

        client = bigquery.Client(project=project_id, location=cfg["location"])
        client.delete_dataset(f"{project_id}.{dataset_id}", delete_contents=True, not_found_ok=True)
        print(f"  -> [완료] `{project_id}.{dataset_id}` 데이터셋 및 하위 테이블/뷰가 모두 삭제되었다.")
    except Exception as exc:
        print(f"  -> [경고] 데이터셋 삭제 중 오류가 발생하였다: {exc}")

    # GDA 에이전트 삭제 시도
    try:
        token = get_access_token()
        existing = list_existing_gda_agents(project_id, location, token)
        if agent_name in existing:
            resource_name = existing[agent_name]
            del_url = f"https://geminidataanalytics.googleapis.com/v1beta/{resource_name}"
            print(f"  -> [요청 중] GDA Data Agent 삭제 요청: {resource_name}...")
            send_request(del_url, method="DELETE", token=token, project_id=project_id)
            print(f"  -> [완료] GDA Data Agent ({agent_name}) 삭제 완료.")
    except Exception as exc:
        print(f"  -> [참고] GDA Data Agent 삭제 참고: {exc}")


# ==============================================================================
# 6. CLI 진입점 (Main Entrypoint)
# ==============================================================================
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="BigQuery Data Agent 45-Minute Hands-on Starter Kit (Standalone & Optional Gemini Enterprise app)"
    )
    parser.add_argument("-p", "--project", type=str, help="대상 Google Cloud 프로젝트 ID")
    parser.add_argument("--project-number", type=str, help="Google Cloud 프로젝트 번호 (미지정 시 자동 조회)")
    parser.add_argument("-d", "--dataset", type=str, help="스몰셋 BigQuery 데이터셋 ID (기본값: cymbal_gold)")
    parser.add_argument("-l", "--location", type=str, help="BigQuery 리전 (기본값: asia-northeast3)")
    parser.add_argument("--gda-location", type=str, help="GDA 런타임 리전 (기본값: global)")
    parser.add_argument("--ge-app-id", type=str, help="[선택 사항] 등록할 Gemini Enterprise App 인스턴스 ID")
    parser.add_argument("--agent-name", type=str, help="BigQuery Data Agent 이름 (기본값: cymbal-retail-data-agent)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 GCP API 호출 없이 가상 모의 실행으로 전체 45분 워크숍 가이드와 SQL/지침 구성을 출력",
    )
    parser.add_argument("--config", action="store_true", default=False, help="사내 환경 대화형 설정 마법사 실행 및 .env 자동 저장")
    parser.add_argument(
        "--setup-demo",
        action="store_true",
        help="[Step 1] 실제 BigQuery에 cymbal_gold 스몰셋 테이블 4개, 실데이터, 시맨틱 뷰 1개를 원클릭 구축",
    )
    parser.add_argument(
        "--deploy-agent",
        "--deploy",
        action="store_true",
        help="[Step 2 권장] 구글 완전 관리형 GDA dataAgents REST API로 데이터 에이전트 자동 생성 및 A2A 규격 저장",
    )
    parser.add_argument(
        "--agent-card",
        action="store_true",
        help="A2A Agent Card 표준 규격 JSON 파일(a2a_agent_card.json) 단독 생성",
    )
    parser.add_argument(
        "--agent-config",
        action="store_true",
        help="[Step 2 보조] BigQuery Studio > Agents 콘솔 UI 수동 입력용 System Instructions 및 Verified Queries 출력",
    )
    parser.add_argument(
        "--register-ge-app",
        action="store_true",
        help="[Step 3 선택] Discovery Engine REST API를 통해 Gemini Enterprise App 사내 갤러리에 직결 등록",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="[올인원 모드] Step 1(스몰셋 구축) + Step 2(GDA 에이전트 배포) + Step 3(GE App 직결 연동) 일괄 자동 실행",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="대화창에 입력할 자연어 질문을 미리 테스트",
    )
    parser.add_argument(
        "--teardown",
        action="store_true",
        help="실습 완료 후 생성된 BigQuery 스몰셋 데이터셋 및 GDA Data Agent를 삭제하여 비용 누수 차단",
    )
    return parser.parse_args()



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

        if key == "GE_APP_ID":
            target_proj = new_values.get("PROJECT_ID") or gcloud_project or default_val or "sample-project-id"
            if is_interactive:
                print("  [*] 사내 Gemini Enterprise App (Discovery Engine) 목록 실시간 스캔 중...")
                candidate_apps = discover_ge_app_engines(target_proj)
                if candidate_apps:
                    print(f"  [*] {len(candidate_apps)}개의 Gemini Enterprise App 인스턴스를 발견했습니다:")
                    for app_idx, app in enumerate(candidate_apps, 1):
                        disp = app.get("displayName") or "무제"
                        app_id = app.get("id")
                        print(f"      [{app_idx}] {app_id} (표시 이름: {disp})")
                    choice = ""
                    try:
                        choice = input(f"\n  연결할 Gemini Enterprise App 번호 [1-{len(candidate_apps)}, 단독 사용 시 Enter(비워둠)]: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        choice = ""
                    if choice.isdigit() and 1 <= int(choice) <= len(candidate_apps):
                        final_val = candidate_apps[int(choice) - 1]["id"]
                    else:
                        final_val = default_val
                else:
                    print("  [-] 현재 프로젝트에서 프로비저닝된 Gemini Enterprise App을 발견하지 못했습니다.")
                    print("  [*] BigQuery Data Agent를 Gemini Enterprise App에 직결 연동하려면 공식 콘솔 경로를 참고하십시오:")
                    print("      Google Cloud 콘솔 ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines )")
                    print("  [*] 단독(Standalone, BigQuery Studio 전용)으로 사용할 경우 Enter를 눌러 비워둘 수 있습니다.")
                    prompt_str = f"  입력 [기본값: {default_val}]: " if default_val else f"  입력 [Enter 시 비워둠]: "
                    try:
                        user_val = input(prompt_str).strip()
                        final_val = user_val if user_val else default_val
                    except (EOFError, KeyboardInterrupt):
                        final_val = default_val
            else:
                final_val = default_val
        elif is_interactive:
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
    args = parse_args()
    if getattr(args, "config", False):
        run_config_mode("bigquery-data-agent-starter")
        return
    cfg = resolve_config(args)

    if args.teardown:
        teardown_demo_environment(cfg)
        return

    if args.all:
        print("[올인원 워크숍 모드] Step 1 -> Step 2 -> Step 3 전체 자동 프로비저닝을 순차 실행한다.\n")
        setup_smallset_demo(cfg)
        print()
        deploy_full_agent_workflow(cfg)
        report_md = build_markdown_report(cfg)
        save_markdown_report(report_md, "report.md")
        return

    if args.setup_demo:
        setup_smallset_demo(cfg)
        return

    if getattr(args, "deploy_agent", False) or getattr(args, "deploy", False):
        token = get_access_token() if not cfg["dry_run"] else "mock-token"
        gda_resource = create_gda_data_agent(cfg, token=token)
        if gda_resource:
            build_a2a_agent_card(cfg, gda_resource)
        return

    if args.agent_card:
        mock_res = f"projects/{cfg['project_id']}/locations/{cfg['gda_location']}/dataAgents/{cfg['data_agent_name']}"
        build_a2a_agent_card(cfg, mock_res)
        return

    if args.agent_config:
        export_data_agent_config(cfg)
        return

    if args.register_ge_app:
        mock_res = f"projects/{cfg['project_id']}/locations/{cfg['gda_location']}/dataAgents/{cfg['data_agent_name']}"
        card = build_a2a_agent_card(cfg, mock_res)
        token = get_access_token() if not cfg["dry_run"] else "mock-token"
        register_agent_to_ge_app_api(cfg, card, token=token)
        return

    print_workshop_guide_and_prompts(cfg, custom_query=args.query)
    report_md = build_markdown_report(cfg)
    save_markdown_report(report_md, "report.md")


if __name__ == "__main__":
    main()
