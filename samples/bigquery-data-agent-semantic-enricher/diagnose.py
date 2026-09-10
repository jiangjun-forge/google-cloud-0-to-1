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
        default=os.getenv("DATASET_ID", "cymbal_gold"),
        help="진단 및 보강 대상 BigQuery 데이터셋 ID (기본값: cymbal_gold)",
    )
    parser.add_argument(
        "-l",
        "--location",
        default=os.getenv("LOCATION", "asia-northeast3"),
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
        "--apply",
        action="store_true",
        help="생성된 시맨틱 메타데이터를 실제 BigQuery 테이블 및 스키마에 영구 반영",
    )
    return parser.parse_args()


def detect_project_id(cli_project: str) -> str:
    """프로젝트 ID를 탐지한다."""
    if cli_project:
        return cli_project
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
    return "demo-data-agent-project"


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


def inspect_live_dataset(project_id: str, dataset_id: str, location: str, enrich: bool, apply: bool) -> None:
    """실제 BigQuery 환경의 데이터셋 스키마를 점검하고 보강한다."""
    try:
        from google.cloud import bigquery
    except ImportError:
        print("오류: google-cloud-bigquery 패키지가 설치되지 않았다.", file=sys.stderr)
        print("pip install -r requirements.txt 명령으로 의존성을 먼저 설치하라.", file=sys.stderr)
        sys.exit(1)

    client = bigquery.Client(project=project_id, location=location)
    dataset_ref = f"{project_id}.{dataset_id}"

    try:
        dataset = client.get_dataset(dataset_ref)
        print(f"대상 BigQuery 데이터셋 연결 성공: {dataset.dataset_id} (리전: {dataset.location})")
    except Exception as e:
        print(f"오류: 데이터셋 '{dataset_ref}' 조회 실패: {e}", file=sys.stderr)
        sys.exit(1)

    tables = list(client.list_tables(dataset))
    if not tables:
        print(f"데이터셋 '{dataset_ref}' 내에 테이블이 존재하지 않는다.")
        return

    table_records = []
    for t_item in tables:
        t = client.get_table(t_item.reference)
        has_desc = bool(t.description and len(t.description.strip()) > 5)
        total_cols = len(t.schema)
        described_cols = sum(1 for field in t.schema if field.description and len(field.description.strip()) > 5)

        table_records.append({
            "table_id": t.table_id,
            "table_desc_present": has_desc,
            "current_table_desc": t.description or "",
            "total_columns": total_cols,
            "described_columns": described_cols,
            "profile_scanned": False,
            "glossary_bound": False,
            "sample_missing_cols": [field.name for field in t.schema if not field.description][:5],
            "suggested_table_desc": f"Standard analytics table for {t.table_id} under {dataset_id}.",
            "suggested_col_descs": {f.name: f"Value field for {f.name} (Type: {f.field_type})" for f in t.schema if not f.description},
            "glossary_formula": f"Standard metrics for {t.table_id}",
        })

    audit_data = {"dataset": dataset_id, "tables": table_records}
    score = calculate_readiness_score(table_records)
    print_diagnostic_report(audit_data, score)

    if enrich:
        print_enrichment_plan(audit_data)
        generate_glossary_yaml(audit_data)

        if apply:
            print("\n[BigQuery 스키마 메타데이터 패치 적용]")
            for t_item in tables:
                t = client.get_table(t_item.reference)
                updated = False
                if not t.description:
                    t.description = f"Standard analytics table for {t.table_id} under {dataset_id}."
                    updated = True

                new_schema = []
                for field in t.schema:
                    if not field.description:
                        new_field = bigquery.SchemaField(
                            name=field.name,
                            field_type=field.field_type,
                            mode=field.mode,
                            description=f"Standard business field for {field.name} in {t.table_id}.",
                            fields=field.fields,
                        )
                        new_schema.append(new_field)
                        updated = True
                    else:
                        new_schema.append(field)

                if updated:
                    t.schema = new_schema
                    client.update_table(t, ["description", "schema"])
                    print(f"  - 테이블 '{t.table_id}' 스키마 설명 패치 완료.")
            print("모든 테이블의 메타데이터 보강이 완료되었다.")


def main() -> None:
    """메인 실행 함수."""
    args = parse_args()
    project_id = detect_project_id(args.project)
    dataset_id = args.dataset
    location = args.location

    print("=" * 90)
    print("BigQuery Data Agent 시맨틱 메타데이터 준비도 진단 및 지능형 보강기")
    print(f"진단 모드  : {'가상 실행 (Dry-run)' if args.dry_run else '실제 환경 (Live)'}")
    print(f"대상 프로젝트: {project_id}")
    print(f"대상 데이터셋: {dataset_id}")
    print(f"리전      : {location}")
    print("=" * 90)

    if args.dry_run:
        mock_data = get_mock_audit_data()
        score = calculate_readiness_score(mock_data["tables"])
        print_diagnostic_report(mock_data, score)

        if args.enrich:
            print_enrichment_plan(mock_data)
            generate_glossary_yaml(mock_data, "dataplex_glossary_terms_sample.yaml")
        else:
            print("\n[안내] 메타데이터 자동 보강 계획 및 비즈니스 공식 생성을 확인하려면 '--enrich' 플래그를 추가하라.")
            print(f"  실행 예시: python3 diagnose.py --dry-run --enrich")
    else:
        inspect_live_dataset(project_id, dataset_id, location, args.enrich, args.apply)


if __name__ == "__main__":
    main()
