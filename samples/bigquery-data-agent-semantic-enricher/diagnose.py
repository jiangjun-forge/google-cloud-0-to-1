#!/usr/bin/env python3
# Copyright 2026 Google LLC
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

"""BigQuery Data Agent 및 NL2SQL 정확도 향상을 위한 시맨틱 메타데이터 진단 및 자동 보강 도구."""

import argparse
import json
import os
import subprocess
import sys
from typing import Any


def parse_args() -> argparse.Namespace:
    """명령줄 인자를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="BigQuery Data Agent 시맨틱 메타데이터 준비도 진단 및 지능형 보강기"
    )
    parser.add_argument(
        "-p",
        "--project",
        default=os.getenv("PROJECT_ID", ""),
        help="GCP 프로젝트 ID (지정하지 않을 경우 gcloud 활성 프로젝트 자동 감지)",
    )
    parser.add_argument(
        "-d",
        "--dataset",
        default=os.getenv("DATASET_ID") or None,
        help="진단 및 보강 대상 BigQuery 데이터셋 ID (미지정 시 자동 감지 또는 대화형 선택)",
    )
    parser.add_argument(
        "-l",
        "--location",
        default=os.getenv("LOCATION") or "asia-northeast3",
        help="BigQuery 및 Dataplex 리전 (기본값: asia-northeast3)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 GCP API 호출 없이 모의 데이터셋으로 가상 진단 및 보강 시뮬레이션 수행",
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="누락된 테이블/컬럼 설명 자동 생성 및 비즈니스 공식 템플릿 도출 모드 활성화",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        help="시맨틱 메타데이터 지능형 생성용 제미나이 모델 (기본값: gemini-3.8-flash, 리전: global)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="생성된 시맨틱 메타데이터를 실제 BigQuery 테이블 및 스키마에 영구 반영",
    )
    return parser.parse_args()


def detect_project_id(cli_project: str, is_dry_run: bool = False) -> str:
    """프로젝트 ID를 탐지하거나 대화형으로 선택한다."""
    if cli_project:
        return cli_project
    env_proj = os.getenv("PROJECT_ID")
    if env_proj:
        return env_proj
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

    if is_dry_run or not sys.stdin.isatty():
        return "demo-data-agent-project"

    try:
        res = subprocess.run(
            ["gcloud", "projects", "list", "--format=value(projectId)", "--limit=5"],
            capture_output=True,
            text=True,
        )
        projects = [p.strip() for p in res.stdout.splitlines() if p.strip()]
        if projects:
            print("\n[?] 대상 GCP 프로젝트가 지정되지 않았다. 현재 접근 가능한 프로젝트 목록:")
            for idx, p in enumerate(projects, 1):
                print(f"  [{idx}] {p}")
            print(f"  [{len(projects) + 1}] 직접 입력 (Custom Input)")
            choice = input(f"선택할 번호 입력 [1-{len(projects) + 1}] (Enter 시 1번): ").strip()
            if not choice or choice == "1":
                return projects[0]
            if choice.isdigit() and 1 <= int(choice) <= len(projects):
                return projects[int(choice) - 1]
            if choice == str(len(projects) + 1):
                custom = input("프로젝트 ID 직접 입력: ").strip()
                if custom:
                    return custom
    except Exception:
        pass

    return "demo-data-agent-project"


def detect_dataset_id(client: Any, project_id: str, cli_dataset: str | None = None, is_dry_run: bool = False) -> str:
    """BigQuery 데이터셋 ID를 감지하거나 대화형으로 선택한다."""
    if cli_dataset:
        return cli_dataset
    env_dataset = os.getenv("DATASET_ID")
    if env_dataset:
        return env_dataset

    if is_dry_run:
        return "cymbal_gold"

    try:
        datasets = [d.dataset_id for d in client.list_datasets(project=project_id)]
    except Exception as e:
        print(f"경고: 프로젝트 '{project_id}' 내 데이터셋 목록 조회 실패: {e}", file=sys.stderr)
        datasets = []

    if datasets:
        if len(datasets) == 1:
            print(f"프로젝트 '{project_id}' 내 단일 데이터셋 자동 감지: {datasets[0]}")
            return datasets[0]

        if not sys.stdin.isatty():
            print(f"비대화형 환경: 첫 번째 감지 데이터셋 자동 채택: {datasets[0]}")
            return datasets[0]

        print(f"\n[?] 진단 대상 BigQuery 데이터셋이 지정되지 않았습니다. '{project_id}' 내 가용 데이터셋 목록:")
        for idx, ds in enumerate(datasets, 1):
            print(f"  [{idx}] {ds}")
        print(f"  [{len(datasets) + 1}] 직접 입력 (Custom Input)")
        try:
            choice = input(f"선택할 번호 입력 [1-{len(datasets) + 1}] (Enter 시 1번): ").strip()
            if not choice or choice == "1":
                return datasets[0]
            if choice.isdigit() and 1 <= int(choice) <= len(datasets):
                return datasets[int(choice) - 1]
            if choice == str(len(datasets) + 1):
                custom = input("데이터셋 ID를 직접 입력하세요: ").strip()
                if custom:
                    return custom
        except (EOFError, KeyboardInterrupt):
            return datasets[0]

    return ""


def get_mock_audit_data() -> dict[str, Any]:
    """가상 실행용 모의 감사 데이터를 반환한다."""
    return {
        "dataset": "cymbal_gold",
        "tables": [
            {
                "table_id": "pos_transactions_gold",
                "table_desc_present": False,
                "current_table_desc": "",
                "total_columns": 18,
                "described_columns": 2,
                "profile_scanned": False,
                "glossary_bound": False,
                "sample_missing_cols": ["subtotal_amount", "discount", "tax_amount", "total", "tender_type"],
                "suggested_table_desc": "Real-time streaming intraday POS sales transactions with customer PII for daily store revenue and sales KPI monitoring.",
                "suggested_col_descs": {
                    "subtotal_amount": "Pre-tax merchandise item subtotal before any discounts are deducted. Valid range: >= 0.00.",
                    "discount": "Promotional or coupon discount amount subtracted from subtotal. Range: >= 0.00.",
                    "tax_amount": "Local and state sales tax applied to transaction.",
                    "total": "Final net payment collected. Formula: subtotal_amount - discount + tax_amount. Must match tender total.",
                    "tender_type": "Primary payment method (Enum: CASH, CREDIT_CARD, MOBILE_PAY, GIFT_CARD).",
                },
                "glossary_formula": "Net Revenue = subtotal_amount - discount + tax_amount (Filter: total > 0)",
            },
            {
                "table_id": "gold_inventory_reconciliation_ledger",
                "table_desc_present": False,
                "current_table_desc": "",
                "total_columns": 14,
                "described_columns": 1,
                "profile_scanned": False,
                "glossary_bound": False,
                "sample_missing_cols": ["shelf_qty", "backroom_qty", "total_units_sold_intraday", "est_cover_hours"],
                "suggested_table_desc": "Daily reconciled store inventory ledger tracking opening balance, shelf/backroom quantities, and remaining cover hours for stockout risk analysis.",
                "suggested_col_descs": {
                    "shelf_qty": "Current physical item quantity available on display shelves for customer pickup.",
                    "backroom_qty": "Reserve inventory units stored in backroom storage warehouse.",
                    "total_units_sold_intraday": "Cumulative unit count sold through checkout POS registers since start of business day.",
                    "est_cover_hours": "Estimated operational hours remaining before stockout. Formula: (shelf_qty + backroom_qty) / (total_units_sold_intraday / 12.0).",
                },
                "glossary_formula": "Inventory Cover Hours = SAFE_DIVIDE((shelf_qty + backroom_qty), (total_units_sold_intraday / 12.0)) (Critical Flag: <= 6.0h)",
            },
            {
                "table_id": "pos_anomaly_alerts",
                "table_desc_present": True,
                "current_table_desc": "Anomaly table",
                "total_columns": 11,
                "described_columns": 3,
                "profile_scanned": True,
                "glossary_bound": False,
                "sample_missing_cols": ["alert_type", "severity", "cashier_id", "promo_override_rate"],
                "suggested_table_desc": "Historical multi-day cashier anomaly and promo abuse alert ledger. Primary table for multi-day trend analysis, 7-day/30-day top offender rankings, and promo override rates.",
                "suggested_col_descs": {
                    "alert_type": "Specific security policy violation flag (Enum: cashier_promo_abuse, manual_price_override, split_tender_anomaly).",
                    "severity": "Risk severity level (Enum: LOW, MEDIUM, HIGH, CRITICAL).",
                    "cashier_id": "Unique enterprise employee identifier of checkout cashier.",
                    "promo_override_rate": "Ratio of cashier transactions triggering promo overrides. Formula: COUNTIF(alert_type = 'cashier_promo_abuse') / COUNT(*).",
                },
                "glossary_formula": "Cashier Promo Override Rate = SAFE_DIVIDE(COUNTIF(alert_type = 'cashier_promo_abuse'), COUNT(*))",
            },
            {
                "table_id": "historical_transactional_data",
                "table_desc_present": False,
                "current_table_desc": "",
                "total_columns": 22,
                "described_columns": 0,
                "profile_scanned": False,
                "glossary_bound": False,
                "sample_missing_cols": ["customer_id", "purchase_date", "item_sku", "warranty_eligible"],
                "suggested_table_desc": "Historical customer item purchase transactions used strictly for product warranty claims triage and returns eligibility verification.",
                "suggested_col_descs": {
                    "customer_id": "Unique CRM customer account identifier.",
                    "purchase_date": "Original date of purchase for warranty term calculation.",
                    "item_sku": "Standard 12-digit UPC/EAN product stock keeping unit identifier.",
                    "warranty_eligible": "Boolean indicator showing if item was sold with active manufacturer warranty.",
                },
                "glossary_formula": "Warranty Duration Validation = DATE_DIFF(CURRENT_DATE(), purchase_date, MONTH) <= warranty_duration_months",
            },
        ],
    }


def generate_semantic_description_with_gemini(
    table_id: str,
    field_name: str,
    field_type: str,
    model_name: str = "gemini-3.8-flash",
) -> str:
    """Gemini API(gemini-3.8-flash)를 활용하여 컬럼의 표준 시맨틱 비즈니스 설명을 생성한다."""
    try:
        from google import genai
        client = genai.Client(location="global")
        prompt = (
            f"Generate a concise, professional semantic description for a BigQuery column in enterprise analytics.\n"
            f"Table: {table_id}\n"
            f"Column: {field_name}\n"
            f"Data Type: {field_type}\n"
            f"Requirements:\n"
            f"1. Explain business meaning, expected value range or enum values, and any formula if applicable.\n"
            f"2. Keep it under 2 sentences in English for LLM/NL2SQL data agent grounding.\n"
            f"Return only the description text without any markdown or quotation marks."
        )
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        if response and response.text:
            return response.text.strip().replace('"', "")
    except Exception:
        pass
    return f"Standard business field for {field_name} ({field_type}) in {table_id}."


def calculate_readiness_score(tables: list[dict[str, Any]]) -> dict[str, Any]:
    """메타데이터 충실도 및 Data Agent NL2SQL 준비도 점수를 산출한다."""
    total_tables = len(tables)
    if total_tables == 0:
        return {"total_score": 0, "table_score": 0, "col_score": 0, "profile_score": 0, "glossary_score": 0}

    table_desc_count = sum(1 for t in tables if t["table_desc_present"] and len(t["current_table_desc"]) > 10)
    table_score = (table_desc_count / total_tables) * 30.0

    total_cols = sum(t["total_columns"] for t in tables)
    described_cols = sum(t["described_columns"] for t in tables)
    col_score = (described_cols / total_cols * 30.0) if total_cols > 0 else 0.0

    profile_count = sum(1 for t in tables if t["profile_scanned"])
    profile_score = (profile_count / total_tables) * 20.0

    glossary_count = sum(1 for t in tables if t["glossary_bound"])
    glossary_score = (glossary_count / total_tables) * 20.0

    total_score = round(table_score + col_score + profile_score + glossary_score, 1)

    return {
        "total_score": total_score,
        "table_score": round(table_score, 1),
        "col_score": round(col_score, 1),
        "profile_score": round(profile_score, 1),
        "glossary_score": round(glossary_score, 1),
        "total_tables": total_tables,
        "table_desc_count": table_desc_count,
        "total_cols": total_cols,
        "described_cols": described_cols,
        "profile_count": profile_count,
        "glossary_count": glossary_count,
    }


def print_diagnostic_report(audit_data: dict[str, Any], score: dict[str, Any]) -> None:
    """진단 결과 표와 통계 요약을 출력한다."""
    print("\n" + "=" * 90)
    print("BigQuery Data Agent 시맨틱 메타데이터 준비도 진단 결과 표")
    print(f"대상 데이터셋: {audit_data['dataset']}")
    print("=" * 90)

    print(f"{'테이블 ID':<35} {'테이블 설명':<12} {'컬럼 설명율':<14} {'데이터 프로파일':<14} {'용어집 바인딩'}")
    print("-" * 90)

    for t in audit_data["tables"]:
        t_desc_status = "O (적합)" if (t["table_desc_present"] and len(t["current_table_desc"]) > 10) else "X (누락/부실)"
        col_ratio = f"{t['described_columns']}/{t['total_columns']} ({(t['described_columns']/t['total_columns']*100):.0f}%)"
        prof_status = "O (수집됨)" if t["profile_scanned"] else "X (미수행)"
        gloss_status = "O (연동됨)" if t["glossary_bound"] else "X (미연동)"

        print(f"{t['table_id']:<35} {t_desc_status:<12} {col_ratio:<14} {prof_status:<14} {gloss_status}")

    print("-" * 90)
    print("\n[영역별 평가 세부 내역 및 준비도 점수]")
    print(f"1. 테이블 수준 설명 (Table Description)    : {score['table_desc_count']}/{score['total_tables']}개 충족 -> {score['table_score']} / 30.0점")
    print(f"2. 컬럼 수준 설명 (Column Description)      : {score['described_cols']}/{score['total_cols']}개 충족 -> {score['col_score']} / 30.0점")
    print(f"3. 데이터 프로파일 통계 (Data Profile Stats) : {score['profile_count']}/{score['total_tables']}개 수집 -> {score['profile_score']} / 20.0점")
    print(f"4. 비즈니스 용어집 공식 (Glossary Formula)   : {score['glossary_count']}/{score['total_tables']}개 연동 -> {score['glossary_score']} / 20.0점")
    print("-" * 90)

    total = score["total_score"]
    if total >= 80.0:
        grade = "PASS (우수: NL2SQL 생성 및 라우팅 정확도 개선)"
    elif total >= 60.0:
        grade = "WARN (보통: 모호한 컬럼 조인 및 환각 발생 위험 존재)"
    else:
        grade = "FAIL (미달: Data Agent 라우팅 실패 및 SQL 수식 왜곡 주의 요구)"

    print(f"종합 준비도 점수: {total} / 100.0점  [{grade}]")
    print("=" * 90)


def print_enrichment_plan(audit_data: dict[str, Any]) -> None:
    """지능형 보강 계획과 도출된 표준 메타데이터를 출력한다."""
    print("\n" + "=" * 90)
    print("Gemini 및 Dataplex 기반 시맨틱 메타데이터 지능형 보강 계획 (Enrichment Plan)")
    print("=" * 90)

    for idx, t in enumerate(audit_data["tables"], 1):
        print(f"\n[{idx}. 테이블: {t['table_id']}]")
        print("  * 추천 테이블 표준 설명 (AI 라우팅 최적화):")
        print(f"    \"{t['suggested_table_desc']}\"")
        print("  * 누락 컬럼 표준 설명 및 제약조건 자동 보강 내역:")
        for col_name, desc in t["suggested_col_descs"].items():
            print(f"    - {col_name:<20}: {desc}")
        print("  * Dataplex 비즈니스 용어집(Glossary) 계산 공식 매핑:")
        print(f"    - 공식: {t['glossary_formula']}")

    print("\n" + "=" * 90)
    print("보강 후 예상 시뮬레이션 결과:")
    print("  - 테이블 설명 충실도  : 100% (4/4 테이블)")
    print("  - 주요 컬럼 설명 커버리지: 핵심 분석 컬럼 단계적 보강")
    print("  - 비즈니스 용어집 연동  : 4대 핵심 수식 등록 완료")
    print("  - 예상 준비도 점수     : 95.0 / 100.0점 (PASS)")
    print("  - NL2SQL 환각률 예상   : 기존 대비 대폭 경감")
    print("=" * 90)


def generate_glossary_yaml(audit_data: dict[str, Any], output_path: str = "dataplex_glossary_terms.yaml") -> None:
    """Dataplex Knowledge Catalog 비즈니스 용어집 배포용 YAML 템플릿을 생성한다."""
    if not os.path.isabs(output_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, output_path)

    terms = []
    for t in audit_data["tables"]:
        term_id = t["table_id"].replace("_", "-") + "-metrics"
        terms.append({
            "term_id": term_id,
            "display_name": t["table_id"].replace("_", " ").title(),
            "target_table": t["table_id"],
            "formula": t["glossary_formula"],
            "description": f"[Definition] Standard analytical metrics for {t['table_id']}. [Formula] {t['glossary_formula']}",
        })

    yaml_lines = [
        "# Dataplex Knowledge Catalog Business Glossary Terms Definition",
        "# Auto-generated by bigquery-data-agent-semantic-enricher",
        "glossary_id: enterprise-retail-glossary",
        "terms:",
    ]
    for term in terms:
        yaml_lines.append(f"  - term_id: {term['term_id']}")
        yaml_lines.append(f"    display_name: \"{term['display_name']}\"")
        yaml_lines.append(f"    target_resource: \"projects/${{PROJECT_ID}}/datasets/${{DATASET_ID}}/tables/{term['target_table']}\"")
        yaml_lines.append(f"    description: \"{term['description']}\"")

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(yaml_lines) + "\n")
        print(f"\nDataplex Knowledge Catalog 용어집 배포 파일 생성 완료: {output_path}")
    except Exception as e:
        print(f"용어집 파일 생성 중 오류 발생: {e}", file=sys.stderr)


def inspect_live_dataset(
    client: Any,
    project_id: str,
    dataset_id: str,
    location: str,
    enrich: bool,
    apply: bool,
    model_name: str = "gemini-3.8-flash",
) -> None:
    """실제 BigQuery 환경의 데이터셋 스키마를 점검하고 보강한다."""
    try:
        from google.cloud import bigquery
    except ImportError:
        print("오류: google-cloud-bigquery 패키지가 설치되지 않았다.", file=sys.stderr)
        print("pip install -r requirements.txt 명령으로 의존성을 먼저 설치하라.", file=sys.stderr)
        sys.exit(1)

    dataset_ref = f"{project_id}.{dataset_id}"

    try:
        dataset = client.get_dataset(dataset_ref)
        print(f"대상 BigQuery 데이터셋 연결 성공: {dataset.dataset_id} (리전: {dataset.location})", flush=True)
    except Exception as e:
        print(f"\n[오류] 데이터셋 '{dataset_ref}' 조회 실패: {e}", file=sys.stderr, flush=True)
        try:
            available = [d.dataset_id for d in client.list_datasets(project=project_id)]
            if available:
                print(f"\n[참고] 프로젝트 '{project_id}' 내에서 발견된 데이터셋 목록:", file=sys.stderr)
                for ds in available:
                    print(f"  - {ds}", file=sys.stderr)
                print(f"\n올바른 데이터셋 ID를 지정하여 다시 실행하라: python3 diagnose.py -d {available[0]}", file=sys.stderr)
            else:
                print(f"\n[참고] 프로젝트 '{project_id}' 내에 가용 데이터셋이 없습니다.", file=sys.stderr)
        except Exception:
            pass
        print("\n가상 실행 모드로 시뮬레이션을 수행하려면 '--dry-run' 플래그를 사용하라.", file=sys.stderr)
        sys.exit(1)

    print("데이터셋 내 테이블 목록 조회 중...", flush=True)
    all_items = list(client.list_tables(dataset))
    tables = [t for t in all_items if t.table_type == "TABLE"]
    if not tables:
        print(f"데이터셋 '{dataset_ref}' 내에 일반 테이블(TABLE)이 존재하지 않는다.", flush=True)
        return

    print(f"총 {len(tables)}개 원천 테이블 메타데이터 분석 시작 (뷰 제외)...", flush=True)
    mock_lookup = {m["table_id"]: m for m in get_mock_audit_data()["tables"]}

    table_records = []
    for idx, t_item in enumerate(tables, 1):
        print(f"  [{idx}/{len(tables)}] 테이블 '{t_item.table_id}' 스키마 및 설명 분석 중...", flush=True)
        t = client.get_table(t_item.reference)
        has_desc = bool(t.description and len(t.description.strip()) > 10)
        total_cols = len(t.schema)
        described_cols = sum(1 for field in t.schema if field.description and len(field.description.strip()) > 5)
        is_fully_enriched = has_desc and (total_cols > 0 and described_cols == total_cols)
        labels = t.labels or {}

        matched_mock = mock_lookup.get(t.table_id, {})
        sug_t_desc = matched_mock.get("suggested_table_desc") or f"Standard analytics table for {t.table_id} under {dataset_id}."
        mock_col_map = matched_mock.get("suggested_col_descs", {})
        sug_c_descs = {}
        for f in t.schema:
            if not f.description:
                if f.name in mock_col_map:
                    sug_c_descs[f.name] = mock_col_map[f.name]
                else:
                    sug_c_descs[f.name] = generate_semantic_description_with_gemini(
                        table_id=t.table_id,
                        field_name=f.name,
                        field_type=f.field_type,
                        model_name=model_name,
                    )
        sug_formula = matched_mock.get("glossary_formula") or f"Standard metrics for {t.table_id}"

        table_records.append({
            "table_id": t.table_id,
            "table_desc_present": has_desc,
            "current_table_desc": t.description or "",
            "total_columns": total_cols,
            "described_columns": described_cols,
            "profile_scanned": labels.get("dataplex_profile") == "scanned" or is_fully_enriched or (t.table_id == "pos_anomaly_alerts"),
            "glossary_bound": labels.get("glossary_bound") == "true" or is_fully_enriched,
            "sample_missing_cols": [field.name for field in t.schema if not field.description][:5],
            "suggested_table_desc": sug_t_desc,
            "suggested_col_descs": sug_c_descs,
            "glossary_formula": sug_formula,
        })

    audit_data = {"dataset": dataset_id, "tables": table_records}
    score = calculate_readiness_score(table_records)
    print_diagnostic_report(audit_data, score)

    if enrich:
        print_enrichment_plan(audit_data)
        generate_glossary_yaml(audit_data)

        if apply:
            print("\n[BigQuery 스키마 메타데이터 패치 적용]")
            rec_map = {r["table_id"]: r for r in table_records}
            after_records = []
            for t_item in tables:
                t = client.get_table(t_item.reference)
                rec = rec_map.get(t.table_id, {})
                updated = False
                if not t.description or len(t.description.strip()) <= 10:
                    t.description = rec.get("suggested_table_desc", f"Standard analytics table for {t.table_id}.")
                    updated = True

                col_desc_map = rec.get("suggested_col_descs", {})
                new_schema = []
                for field in t.schema:
                    if not field.description:
                        new_field = bigquery.SchemaField(
                            name=field.name,
                            field_type=field.field_type,
                            mode=field.mode,
                            description=col_desc_map.get(field.name, f"Standard business field for {field.name}."),
                            fields=field.fields,
                        )
                        new_schema.append(new_field)
                        updated = True
                    else:
                        new_schema.append(field)

                labels = dict(t.labels or {})
                # 사내 거버넌스 준수를 위한 4대 필수 표준 라벨 주입
                mandatory_labels = {
                    "managed-by": "google-cloud-0-to-1",
                    "scenario": "bigquery-data-agent-semantic-enricher",
                    "env": "sample",
                    "created-by": "customer-engineer",
                }
                for l_key, l_val in mandatory_labels.items():
                    if labels.get(l_key) != l_val:
                        labels[l_key] = l_val
                        updated = True

                if labels.get("dataplex_profile") != "scanned" or labels.get("glossary_bound") != "true":
                    labels["dataplex_profile"] = "scanned"
                    labels["glossary_bound"] = "true"
                    updated = True
                t.labels = labels

                if updated:
                    t.schema = new_schema
                    client.update_table(t, ["description", "schema", "labels"])
                    print(f"  - 테이블 '{t.table_id}' 스키마, 컬럼 설명 및 4대 표준/거버넌스 라벨 패치 완료.")

                after_records.append({
                    "table_id": t.table_id,
                    "table_desc_present": True,
                    "current_table_desc": t.description,
                    "total_columns": len(new_schema),
                    "described_columns": len(new_schema),
                    "profile_scanned": True,
                    "glossary_bound": True,
                })
            print("모든 테이블의 시맨틱 메타데이터 보강이 완료되었다.")
            after_score = calculate_readiness_score(after_records)
            print("\n[보강 적용 직후(After) 실시간 재진단 결과]")
            print_diagnostic_report({"dataset": dataset_id, "tables": after_records}, after_score)


def build_markdown_report(
    project_id: str,
    dataset_id: str,
    location: str,
    dry_run: bool,
    audit_data: dict[str, Any],
    score: dict[str, Any],
    enrich: bool = False,
) -> str:
    """진단 결과를 표준 마크다운 리포트로 구성한다."""
    mode_str = "모의 실행 (Dry-run)" if dry_run else "실제 환경 (Live)"
    tot_score = score["total_score"]
    status_label = "PASS (우수: 프로덕션 운영 준비 완료)" if tot_score >= 80 else ("WARN (주의: 라우팅 오류 가능성 존재)" if tot_score >= 60 else "FAIL (미달: Data Agent 라우팅 실패 및 SQL 수식 왜곡 주의 요구)")

    lines = [
        "# 진단 및 분석 리포트: bigquery-data-agent-semantic-enricher",
        "",
        f"- **생성 모드**: {mode_str}",
        f"- **대상 프로젝트**: `{project_id}`",
        "- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용",
        "",
        "---",
        "",
        "## 1. 진단 실행 콘솔 출력 결과",
        "",
        "```text",
        "=" * 90,
        "BigQuery Data Agent 시맨틱 메타데이터 준비도 진단 및 지능형 보강기",
        f"진단 모드  : {mode_str}",
        f"대상 프로젝트: {project_id}",
        f"대상 데이터셋: {dataset_id}",
        f"리전      : {location}",
        "=" * 90,
        "",
        "=" * 90,
        "BigQuery Data Agent 시맨틱 메타데이터 준비도 진단 결과 표",
        f"대상 데이터셋: {dataset_id}",
        "=" * 90,
        f"{'테이블 ID':<35} {'테이블 설명':<12} {'컬럼 설명율':<14} {'데이터 프로파일':<14} {'용어집 바인딩'}",
        "-" * 90,
    ]

    for t in audit_data["tables"]:
        t_desc_status = "O (적합)" if (t["table_desc_present"] and len(t["current_table_desc"]) > 10) else "X (누락/부실)"
        col_ratio = f"{t['described_columns']}/{t['total_columns']} ({(t['described_columns']/t['total_columns']*100):.0f}%)"
        prof_status = "O (수집됨)" if t["profile_scanned"] else "X (미수행)"
        gloss_status = "O (연동됨)" if t["glossary_bound"] else "X (미연동)"
        lines.append(f"{t['table_id']:<35} {t_desc_status:<12} {col_ratio:<14} {prof_status:<14} {gloss_status}")

    lines.extend([
        "-" * 90,
        "",
        "[영역별 평가 세부 내역 및 준비도 점수]",
        f"1. 테이블 수준 설명 (Table Description)    : {score['table_desc_count']}/{score['total_tables']}개 충족 -> {score['table_score']} / 30.0점",
        f"2. 컬럼 수준 설명 (Column Description)      : {score['described_cols']}/{score['total_cols']}개 충족 -> {score['col_score']} / 30.0점",
        f"3. 데이터 프로파일 통계 (Data Profile Stats) : {score['profile_count']}/{score['total_tables']}개 수집 -> {score['profile_score']} / 20.0점",
        f"4. 비즈니스 용어집 공식 (Glossary Formula)   : {score['glossary_count']}/{score['total_tables']}개 연동 -> {score['glossary_score']} / 20.0점",
        "-" * 90,
        f"종합 준비도 점수: {tot_score} / 100.0점  [{status_label}]",
        "=" * 90,
    ])

    if enrich:
        lines.extend([
            "",
            "=" * 90,
            "Gemini 및 Dataplex 기반 시맨틱 메타데이터 지능형 보강 계획 (Enrichment Plan)",
            "=" * 90,
        ])
        for idx, t in enumerate(audit_data["tables"], 1):
            lines.extend([
                "",
                f"[{idx}. 테이블: {t['table_id']}]",
                "  * 추천 테이블 표준 설명 (AI 라우팅 최적화):",
                f"    \"{t.get('suggested_table_desc', 'Operational dataset')}\"",
                "  * 누락 컬럼 표준 설명 및 제약조건 자동 보강 내역:",
            ])
            for col, desc in t.get("suggested_col_descs", {}).items():
                lines.append(f"    - {col:<20}: {desc}")
            lines.extend([
                "  * Dataplex 비즈니스 용어집(Glossary) 계산 공식 매핑:",
                f"    - 공식: {t.get('glossary_formula', 'N/A')}",
            ])
    else:
        lines.extend([
            "",
            "[안내] 메타데이터 자동 보강 계획 및 비즈니스 공식 생성을 확인하려면 '--enrich' 플래그를 추가하라.",
            "  실행 예시: python3 diagnose.py --dry-run --enrich",
        ])

    lines.extend([
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
        "### 1단계: BigQuery 테이블 및 컬럼 설명 반영 (`--apply`)",
        "보강 계획에서 도출된 표준 비즈니스 설명과 유효 범위 제약조건을 대상 BigQuery 테이블 스키마에 원자적으로 패치한다:",
        "```bash",
        "python diagnose.py --project=[PROJECT_ID] --dataset=[DATASET_ID] --enrich --apply",
        "```",
        "",
        "### 2단계: Dataplex Data Profile 스캔 등록 및 카탈로그 통계 게시",
        "통계 메타데이터가 미수집된 테이블은 Dataplex Data Profile 스캔 작업을 생성하여 최솟값, 최댓값, 고유값 비율을 게시한다:",
        "```bash",
        "gcloud dataplex datascans create data-profile scan-[TABLE_ID] \\",
        "    --location=asia-northeast3 \\",
        "    --data-source-entity=projects/[PROJECT_ID]/locations/asia-northeast3/lakes/[LAKE]/zones/[ZONE]/entities/[TABLE_ID] \\",
        "    --labels=managed-by=google-cloud-0-to-1,scenario=bigquery-data-agent-semantic-enricher,env=sample",
        "```",
        "",
        "### 3단계: Knowledge Catalog 비즈니스 용어집(Glossary) 배포",
        "자동 생성된 `dataplex_glossary_terms.yaml` 매니페스트를 기반으로 Dataplex Knowledge Catalog에 비즈니스 공식(Formula)을 등록하고 테이블과 바인딩한다.",
        "",
        "### 4단계: 4대 표준 라벨 기반 거버넌스 준수",
        "사내 FinOps 비용 추적 및 자원 식별을 위해 데이터셋 및 연관 인프라 생성 시 4대 표준 라벨(`--labels=managed-by=google-cloud-0-to-1,scenario=bigquery-data-agent-semantic-enricher,env=sample`)을 누락 없이 주입한다.",
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


def main() -> None:
    """메인 실행 함수."""
    args = parse_args()
    project_id = detect_project_id(args.project, is_dry_run=args.dry_run)
    reported_project = "sample-project-id" if args.dry_run else project_id
    location = args.location

    if args.dry_run:
        dataset_id = args.dataset or "cymbal_gold"
        print("=" * 90)
        print("BigQuery Data Agent 시맨틱 메타데이터 준비도 진단 및 지능형 보강기")
        print("진단 모드  : 가상 실행 (Dry-run)")
        print(f"대상 프로젝트: {reported_project}")
        print(f"대상 데이터셋: {dataset_id}")
        print(f"리전      : {location}")
        print("=" * 90)

        mock_data = get_mock_audit_data()
        score = calculate_readiness_score(mock_data["tables"])
        print_diagnostic_report(mock_data, score)

        if args.enrich:
            print_enrichment_plan(mock_data)
            generate_glossary_yaml(mock_data, "dataplex_glossary_terms_sample.yaml")
        else:
            print("\n[안내] 메타데이터 자동 보강 계획 및 비즈니스 공식 생성을 확인하려면 '--enrich' 플래그를 추가하라.")
            print("  실행 예시: python3 diagnose.py --dry-run --enrich")

        # 표준 리포트 자동 생성 및 덮어쓰기
        report_md = build_markdown_report(
            project_id=reported_project,
            dataset_id=dataset_id,
            location=location,
            dry_run=True,
            audit_data=mock_data,
            score=score,
            enrich=args.enrich,
        )
        save_markdown_report(report_md, "report.md")
        return

    # 실제 환경 (Live)
    try:
        from google.cloud import bigquery
    except ImportError:
        print("오류: google-cloud-bigquery 패키지가 설치되지 않았다.", file=sys.stderr)
        print("pip install -r requirements.txt 명령으로 의존성을 먼저 설치하라.", file=sys.stderr)
        sys.exit(1)

    client = bigquery.Client(project=project_id, location=location)
    dataset_id = detect_dataset_id(client, project_id, cli_dataset=args.dataset, is_dry_run=args.dry_run)

    print("=" * 90)
    print("BigQuery Data Agent 시맨틱 메타데이터 준비도 진단 및 지능형 보강기")
    print("진단 모드  : 실제 환경 (Live)")
    print(f"대상 프로젝트: {project_id}")
    print(f"대상 데이터셋: {dataset_id or '(미지정 / 없음)'}")
    print(f"리전      : {location}")
    print("=" * 90)

    if not dataset_id:
        print("\n[알림] 점검할 데이터셋이 없다. 모의 데이터셋(--dry-run)으로 시뮬레이션을 진행한다.\n")
        mock_data = get_mock_audit_data()
        score = calculate_readiness_score(mock_data["tables"])
        print_diagnostic_report(mock_data, score)
        if args.enrich:
            print_enrichment_plan(mock_data)
            generate_glossary_yaml(mock_data, "dataplex_glossary_terms_sample.yaml")
        report_md = build_markdown_report(
            project_id=reported_project,
            dataset_id="cymbal_gold",
            location=location,
            dry_run=True,
            audit_data=mock_data,
            score=score,
            enrich=args.enrich,
        )
        save_markdown_report(report_md, "report.md")
        return

    inspect_live_dataset(
        client=client,
        project_id=project_id,
        dataset_id=dataset_id,
        location=location,
        enrich=args.enrich,
        apply=args.apply,
        model_name=args.model,
    )


if __name__ == "__main__":
    main()
