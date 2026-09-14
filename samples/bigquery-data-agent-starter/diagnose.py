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
BigQuery Data Agent 45-Minute Hands-on Starter Kit (Standalone & Optional GE App).

45분 핸즈온 워크숍 내에 참석자(고객)가 CLI 명령어 한 줄로 BigQuery 스몰셋 데이터셋(cymbal_gold)과
실데이터를 자동 구축하고, BigQuery Studio 내 Agents (Agent Catalog)에서 단독(Standalone)으로 Data Agent를 생성 및
실습하며, 필요 시 선택 사항(Optional)으로 Gemini Enterprise App에 게시하여 실무 시나리오를
시연할 수 있도록 설계된 스타터 키트다.
"""

import argparse
import json
import os
import subprocess
import sys
import time
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
        choice = input(f"번호를 선택하시오 [Enter 입력 시 {default_idx + 1}번 자동 선택]: ").strip()
        if not choice:
            return candidates[default_idx]
        selected = int(choice) - 1
        if 0 <= selected < len(candidates):
            return candidates[selected]
    except Exception:
        pass
    return candidates[default_idx]


def resolve_config(cli_args: argparse.Namespace) -> Dict[str, Any]:
    """CLI 인자 > .env > gcloud config > 대화형 선택기 > 사내 권장 기본값 순으로 설정을 확정한다."""
    project_id = cli_args.project or os.environ.get("PROJECT_ID", "").strip()
    if not project_id and not cli_args.dry_run:
        gcloud_proj = run_gcloud_cmd(["config", "get-value", "project"])
        if gcloud_proj and gcloud_proj != "(unset)":
            project_id = gcloud_proj
        else:
            proj_list_str = run_gcloud_cmd(["projects", "list", "--format=value(projectId)", "--limit=5"])
            if proj_list_str:
                candidates = [p.strip() for p in proj_list_str.splitlines() if p.strip()]
                project_id = interactive_select("대상 Google Cloud 프로젝트를 선택하시오:", candidates)
    if not project_id:
        project_id = "demo-data-agent-project"

    location = cli_args.location or os.environ.get("LOCATION", "").strip()
    if not location and not cli_args.dry_run:
        gcloud_loc = run_gcloud_cmd(["config", "get-value", "compute/region"])
        if gcloud_loc and gcloud_loc != "(unset)":
            location = gcloud_loc
    if not location:
        location = "asia-northeast3"

    dataset_id = cli_args.dataset or os.environ.get("DATASET_ID", "").strip() or "cymbal_gold"
    ge_app_id = cli_args.app_id or os.environ.get("GE_APP_ID", "").strip() or "omni-retail-ge-app"
    data_agent_name = cli_args.agent_name or os.environ.get("DATA_AGENT_NAME", "").strip() or "cymbal-retail-data-agent"

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
        "location": location,
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
OPTIONS(description="Anomaly table");
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
OPTIONS(description="BigQuery Data Agent 단독 및 GE App 연동 실습용 시맨틱 골드 뷰. 순매출(net_revenue), 결품 커버 시간(est_cover_hours), 이상 거래 경보(alert_type) 내장.") AS
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
        client.create_dataset(dataset_ref, exists_ok=True)
        print(f"  -> [성공] BigQuery 데이터셋 확인/생성 완료: {project_id}.{dataset_id}")

        for title, sql in ddl_and_dml_statements:
            print(f"  -> [실행 중] {title}...")
            job = client.query(sql)
            job.result()
            print(f"     [성공] {title} 반영 완료.")

        print("\n[완료] 45분 워크숍용 BigQuery 스몰셋 테이블 4개, 실데이터, 시맨틱 뷰 1개가 정상 구축되었다!")
    except Exception as exc:
        print(f"\n[경고] BigQuery 스몰셋 구축 중 오류가 발생하였다: {exc}")
        print("       자격 증명(gcloud auth application-default login) 또는 IAM 권한을 확인하시오.")


# ==============================================================================
# 4. [UI 전용 조작 가이드] BigQuery Studio Agents 단독 생성 및 GE App 선택 연동
# ==============================================================================
def export_data_agent_config(cfg: Dict[str, Any]) -> None:
    """BigQuery Studio > Agents (콘솔 UI 전용)에서 복사/붙여넣기할 System Instructions와 Verified Queries를 출력한다."""
    project_id = cfg["project_id"]
    dataset_id = cfg["dataset_id"]
    agent_name = cfg["data_agent_name"]

    sys_inst = SYSTEM_INSTRUCTIONS_TEMPLATE.format(project_id=project_id, dataset_id=dataset_id)

    print("=" * 88)
    print(f" [Step 2: 콘솔 UI 전용 구간] BigQuery Studio > Agents 단독(Standalone) 에이전트 생성 가이드")
    print("=" * 88)
    print(" [중요 안내] BigQuery Data Agent 생성 및 테이블 바인딩은 CLI(gcloud) 명령어가 지원되지 않으며,")
    print("            반드시 Google Cloud 콘솔 UI(BigQuery Studio)에서 아래 순서로 클릭하여 진행한다.")
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
    print("  5) [Verified queries (검증된 쿼리)] 영역에서 [Add query]를 클릭하여 아래 대표 질문-SQL 3쌍을 추가 후 상단 [Save] 클릭:")
    for idx, p in enumerate(GOLDEN_PROMPTS, start=1):
        sql_clean = p["expected_sql"].format(project_id=project_id, dataset_id=dataset_id)
        print(f"\n     [Verified Query #{idx}]")
        print(f"      * Question : {p['user_prompt']}")
        print(f"      * SQL Query: {sql_clean}")
    print("\n" + "=" * 88)


def register_agent_to_ge_app(cfg: Dict[str, Any]) -> None:
    """[선택 사항] BigQuery Studio Agents에서 생성한 Data Agent를 Gemini Enterprise App에 게시하는 UI 절차를 안내한다."""
    ge_app_id = cfg["ge_app_id"]
    agent_name = cfg["data_agent_name"]

    print("=" * 88)
    print(f" [Step 3: 선택 사항 (Optional)] BigQuery Data Agent -> Gemini Enterprise App ({ge_app_id}) 게시")
    print("=" * 88)
    print(" [안내] BigQuery Studio 내에서 단독(Standalone)으로 에이전트를 사용할 경우 본 단계는 생략 가능하다.")
    print("       생성한 에이전트를 Gemini Enterprise 웹 앱 대화창에 붙여 전사 공유하고자 할 때만 아래 UI 절차를 수행한다.")
    print("-" * 88)
    print(" [Phase A: BigQuery Studio > Agents에서 Gemini Enterprise로 게시 (Publish)]")
    print(f"  1) BigQuery Studio > 좌측 [Agents] > 방금 저장한 [{agent_name}] 클릭")
    print("  2) 에이전트 상세 화면 우측 상단의 [Publish (게시)] 버튼 클릭")
    print("  3) 게시 대상 채널에서 [Gemini Enterprise] 체크박스 선택")
    print(f"  4) 드롭다운 메뉴에서 대상 Gemini Enterprise App [{ge_app_id}] 선택 후 [Publish] 버튼 클릭")
    print("-" * 88)
    print(" [Phase B: Gemini Enterprise (AI Applications) 콘솔에서 에이전트 활성화 확인]")
    print("  1) Google Cloud 콘솔 > [AI Applications (또는 Gemini Enterprise)] 메뉴로 이동")
    print(f"  2) 대상 앱 [{ge_app_id}] 클릭 > 좌측 메뉴에서 [Agents (에이전트)] 탭 클릭")
    print(f"  3) 목록에 게시된 [{agent_name}]의 상태 토글이 [Enabled (활성)]로 켜져 있는지 확인")
    print(f"  4) 좌측 메뉴 [Preview (미리보기)] 또는 웹 앱 URL로 접속하여 `@{agent_name}` 호출 테스트!")
    print("=" * 88)


# ==============================================================================
# 5. 실습용 골든 프롬프트 3선 및 Before/After 연계 시연 가이드 (--query / 기본 진단)
# ==============================================================================
def print_workshop_guide_and_prompts(cfg: Dict[str, Any], custom_query: Optional[str] = None) -> None:
    """45분 타임어택 워크숍 전체 요약 및 골든 프롬프트 3선과 Before/After 연계 가이드를 출력한다."""
    project_id = cfg["project_id"]
    dataset_id = cfg["dataset_id"]

    print("=" * 88)
    print(" [BigQuery Data Agent 45분 완성 스몰셋 핸즈온 스타터 키트 (Standalone & Optional GE App)]")
    print("=" * 88)
    print(f" - 대상 프로젝트 : {project_id} (리전: {cfg['location']})")
    print(f" - 호환 데이터셋 : {dataset_id} (테이블 4개 + 시맨틱 뷰 1개 + 실데이터 적재 완료)")
    print(f" - 데이터 에이전트: {cfg['data_agent_name']} (단독 실행 가능 / 선택 시 GE App 연동: {cfg['ge_app_id']})")
    print(f" - 실행 모드     : {'가상 모의 실행 (--dry-run)' if cfg['dry_run'] else '실제 GCP 연동 실행'}")
    print("-" * 88)

    print("\n [45분 핸즈온 워크숍 역할 분담 타임라인 (CLI 자동화 vs 콘솔 UI 전용 조작)]")
    print("  * 00~05분 [CLI 자동화] : cymbal_gold 스몰셋 테이블 4개, 실데이터, 시맨틱 뷰 원클릭 구축 (./run.sh --setup-demo)")
    print("  * 05~10분 [CLI -> UI]  : Agents에 붙여넣을 System Instructions 및 Verified Queries 출력 (./run.sh --agent-config)")
    print("  * 10~30분 [콘솔 UI 전용]: BigQuery Studio > Agents에서 단독(Standalone) Data Agent 생성 및 질의 테스트")
    print("  * 30~45분 [선택 사항]  : 필요 시 Gemini Enterprise App에 게시 및 활성화 (./run.sh --register-ge-app)")
    print("-" * 88)

    print("\n [실습 검증용 골든 프롬프트 3선 (Data Agent 대화창 또는 GE App 공용)]")
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


def teardown_demo_environment(cfg: Dict[str, Any]) -> None:
    """실습 종료 후 생성된 BigQuery 데모 데이터셋을 삭제하여 비용 발생을 차단한다."""
    project_id = cfg["project_id"]
    dataset_id = cfg["dataset_id"]

    print("=" * 88)
    print(f"[자원 정리] BigQuery 스몰셋 데이터셋({project_id}.{dataset_id}) 삭제 시작")
    print("=" * 88)

    if cfg["dry_run"]:
        print(f"[가상 실행] DROP SCHEMA IF EXISTS `{project_id}.{dataset_id}` CASCADE;")
        print("[완료] 가상 실행(--dry-run) 자원 정리 시뮬레이션이 완료되었다.")
        return

    try:
        from google.cloud import bigquery  # type: ignore

        client = bigquery.Client(project=project_id, location=cfg["location"])
        client.delete_dataset(f"{project_id}.{dataset_id}", delete_contents=True, not_found_ok=True)
        print(f"[완료] `{project_id}.{dataset_id}` 데이터셋 및 하위 테이블/뷰가 모두 삭제되었다.")
    except Exception as exc:
        print(f"[경고] 데이터셋 삭제 중 오류가 발생하였다: {exc}")


# ==============================================================================
# 6. CLI 진입점 (Main Entrypoint)
# ==============================================================================
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="BigQuery Data Agent 45-Minute Hands-on Starter Kit (Standalone & Optional GE App)"
    )
    parser.add_argument("-p", "--project", type=str, help="대상 Google Cloud 프로젝트 ID")
    parser.add_argument("-d", "--dataset", type=str, help="스몰셋 BigQuery 데이터셋 ID (기본값: cymbal_gold)")
    parser.add_argument("-l", "--location", type=str, help="BigQuery 리전 (기본값: asia-northeast3)")
    parser.add_argument("--app-id", type=str, help="[선택 사항] 등록할 Gemini Enterprise App (Engine) ID")
    parser.add_argument("--agent-name", type=str, help="BigQuery Data Agent 이름 (기본값: cymbal-retail-data-agent)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 GCP API 호출 없이 가상 모의 실행으로 전체 45분 워크숍 가이드와 SQL/지침 구성을 출력",
    )
    parser.add_argument(
        "--setup-demo",
        action="store_true",
        help="[CLI 자동화] 실제 BigQuery에 cymbal_gold 스몰셋 테이블 4개, 실데이터, 시맨틱 뷰 1개를 원클릭 구축",
    )
    parser.add_argument(
        "--agent-config",
        action="store_true",
        help="[UI 입력용 재료 출력] BigQuery Studio > Agents에서 복사/붙여넣기할 System Instructions 및 Verified Queries 출력",
    )
    parser.add_argument(
        "--register-ge-app",
        action="store_true",
        help="[선택 사항] BigQuery Data Agent를 Gemini Enterprise App에 게시(Publish) 및 활성화하는 UI 클릭 절차 안내",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="대화창에 입력할 자연어 질문을 미리 테스트",
    )
    parser.add_argument(
        "--teardown",
        action="store_true",
        help="실습 완료 후 생성된 BigQuery 스몰셋 데이터셋(cymbal_gold)을 삭제하여 비용 누수 차단",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = resolve_config(args)

    if args.teardown:
        teardown_demo_environment(cfg)
        return

    if args.setup_demo:
        setup_smallset_demo(cfg)
        return

    if args.agent_config:
        export_data_agent_config(cfg)
        return

    if args.register_ge_app:
        register_agent_to_ge_app(cfg)
        return

    print_workshop_guide_and_prompts(cfg, custom_query=args.query)


if __name__ == "__main__":
    main()
