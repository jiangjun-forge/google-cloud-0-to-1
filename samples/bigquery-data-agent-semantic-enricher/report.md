# 진단 및 분석 리포트: bigquery-data-agent-semantic-enricher

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
==========================================================================================
BigQuery Data Agent 시맨틱 메타데이터 준비도 진단 및 지능형 보강기
진단 모드  : 모의 실행 (Dry-run)
대상 프로젝트: sample-project-id
대상 데이터셋: cymbal_gold
리전      : asia-northeast3
==========================================================================================

==========================================================================================
BigQuery Data Agent 시맨틱 메타데이터 준비도 진단 결과 표
대상 데이터셋: cymbal_gold
==========================================================================================
테이블 ID                              테이블 설명       컬럼 설명율         데이터 프로파일       용어집 바인딩
------------------------------------------------------------------------------------------
pos_transactions_gold               X (누락/부실)    2/18 (11%)     X (미수행)        X (미연동)
gold_inventory_reconciliation_ledger X (누락/부실)    1/14 (7%)      X (미수행)        X (미연동)
pos_anomaly_alerts                  O (적합)       3/11 (27%)     O (수집됨)        X (미연동)
historical_transactional_data       X (누락/부실)    0/22 (0%)      X (미수행)        X (미연동)
------------------------------------------------------------------------------------------

[영역별 평가 세부 내역 및 준비도 점수]
1. 테이블 수준 설명 (Table Description)    : 1/4개 충족 -> 7.5 / 30.0점
2. 컬럼 수준 설명 (Column Description)      : 6/65개 충족 -> 2.8 / 30.0점
3. 데이터 프로파일 통계 (Data Profile Stats) : 1/4개 수집 -> 5.0 / 20.0점
4. 비즈니스 용어집 공식 (Glossary Formula)   : 0/4개 연동 -> 0.0 / 20.0점
------------------------------------------------------------------------------------------
종합 준비도 점수: 15.3 / 100.0점  [FAIL (미달: Data Agent 라우팅 실패 및 SQL 수식 왜곡 주의 요구)]
==========================================================================================

==========================================================================================
Gemini 및 Dataplex 기반 시맨틱 메타데이터 지능형 보강 계획 (Enrichment Plan)
==========================================================================================

[1. 테이블: pos_transactions_gold]
  * 추천 테이블 표준 설명 (AI 라우팅 최적화):
    "Real-time streaming intraday POS sales transactions with customer PII for daily store revenue and sales KPI monitoring."
  * 누락 컬럼 표준 설명 및 제약조건 자동 보강 내역:
    - subtotal_amount     : Pre-tax merchandise item subtotal before any discounts are deducted. Valid range: >= 0.00.
    - discount            : Promotional or coupon discount amount subtracted from subtotal. Range: >= 0.00.
    - tax_amount          : Local and state sales tax applied to transaction.
    - total               : Final net payment collected. Formula: subtotal_amount - discount + tax_amount. Must match tender total.
    - tender_type         : Primary payment method (Enum: CASH, CREDIT_CARD, MOBILE_PAY, GIFT_CARD).
  * Dataplex 비즈니스 용어집(Glossary) 계산 공식 매핑:
    - 공식: Net Revenue = subtotal_amount - discount + tax_amount (Filter: total > 0)

[2. 테이블: gold_inventory_reconciliation_ledger]
  * 추천 테이블 표준 설명 (AI 라우팅 최적화):
    "Daily reconciled store inventory ledger tracking opening balance, shelf/backroom quantities, and remaining cover hours for stockout risk analysis."
  * 누락 컬럼 표준 설명 및 제약조건 자동 보강 내역:
    - shelf_qty           : Current physical item quantity available on display shelves for customer pickup.
    - backroom_qty        : Reserve inventory units stored in backroom storage warehouse.
    - total_units_sold_intraday: Cumulative unit count sold through checkout POS registers since start of business day.
    - est_cover_hours     : Estimated operational hours remaining before stockout. Formula: (shelf_qty + backroom_qty) / (total_units_sold_intraday / 12.0).
  * Dataplex 비즈니스 용어집(Glossary) 계산 공식 매핑:
    - 공식: Inventory Cover Hours = SAFE_DIVIDE((shelf_qty + backroom_qty), (total_units_sold_intraday / 12.0)) (Critical Flag: <= 6.0h)

[3. 테이블: pos_anomaly_alerts]
  * 추천 테이블 표준 설명 (AI 라우팅 최적화):
    "Historical multi-day cashier anomaly and promo abuse alert ledger. Primary table for multi-day trend analysis, 7-day/30-day top offender rankings, and promo override rates."
  * 누락 컬럼 표준 설명 및 제약조건 자동 보강 내역:
    - alert_type          : Specific security policy violation flag (Enum: cashier_promo_abuse, manual_price_override, split_tender_anomaly).
    - severity            : Risk severity level (Enum: LOW, MEDIUM, HIGH, CRITICAL).
    - cashier_id          : Unique enterprise employee identifier of checkout cashier.
    - promo_override_rate : Ratio of cashier transactions triggering promo overrides. Formula: COUNTIF(alert_type = 'cashier_promo_abuse') / COUNT(*).
  * Dataplex 비즈니스 용어집(Glossary) 계산 공식 매핑:
    - 공식: Cashier Promo Override Rate = SAFE_DIVIDE(COUNTIF(alert_type = 'cashier_promo_abuse'), COUNT(*))

[4. 테이블: historical_transactional_data]
  * 추천 테이블 표준 설명 (AI 라우팅 최적화):
    "Historical customer item purchase transactions used strictly for product warranty claims triage and returns eligibility verification."
  * 누락 컬럼 표준 설명 및 제약조건 자동 보강 내역:
    - customer_id         : Unique CRM customer account identifier.
    - purchase_date       : Original date of purchase for warranty term calculation.
    - item_sku            : Standard 12-digit UPC/EAN product stock keeping unit identifier.
    - warranty_eligible   : Boolean indicator showing if item was sold with active manufacturer warranty.
  * Dataplex 비즈니스 용어집(Glossary) 계산 공식 매핑:
    - 공식: Warranty Duration Validation = DATE_DIFF(CURRENT_DATE(), purchase_date, MONTH) <= warranty_duration_months
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```

---

## 3. 실무자 즉각 조치 가이드 및 처방전

### 1단계: BigQuery 테이블 및 컬럼 설명 반영 (`--apply`)
보강 계획에서 도출된 표준 비즈니스 설명과 유효 범위 제약조건을 대상 BigQuery 테이블 스키마에 원자적으로 패치한다:
```bash
python diagnose.py --project=[PROJECT_ID] --dataset=[DATASET_ID] --enrich --apply
```

### 2단계: Dataplex Data Profile 스캔 등록 및 카탈로그 통계 게시
통계 메타데이터가 미수집된 테이블은 Dataplex Data Profile 스캔 작업을 생성하여 최솟값, 최댓값, 고유값 비율을 게시한다:
```bash
gcloud dataplex datascans create data-profile scan-[TABLE_ID] \
    --location=asia-northeast3 \
    --data-source-entity=projects/[PROJECT_ID]/locations/asia-northeast3/lakes/[LAKE]/zones/[ZONE]/entities/[TABLE_ID] \
    --labels=managed-by=google-cloud-0-to-1,scenario=bigquery-data-agent-semantic-enricher,env=sample
```

### 3단계: Knowledge Catalog 비즈니스 용어집(Glossary) 배포
자동 생성된 `dataplex_glossary_terms.yaml` 매니페스트를 기반으로 Dataplex Knowledge Catalog에 비즈니스 공식(Formula)을 등록하고 테이블과 바인딩한다.

### 4단계: 4대 표준 라벨 기반 거버넌스 준수
사내 FinOps 비용 추적 및 자원 식별을 위해 데이터셋 및 연관 인프라 생성 시 4대 표준 라벨(`--labels=managed-by=google-cloud-0-to-1,scenario=bigquery-data-agent-semantic-enricher,env=sample`)을 누락 없이 주입한다.
