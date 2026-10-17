# 진단 및 분석 리포트: bigquery-data-agent-starter

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
========================================================================================
 [BigQuery Data Agent 45분 완성 스몰셋 핸즈온 스타터 키트 (Standalone & Optional Gemini Enterprise app)]
========================================================================================
 - 대상 프로젝트 : sample-project-id (리전: asia-northeast3)
 - 호환 데이터셋 : cymbal_gold (테이블 4개 + 시맨틱 뷰 1개 + 실데이터 적재 완료)
 - 데이터 에이전트: cymbal-retail-data-agent (단독 실행 가능 / 선택 시 Gemini Enterprise app 연동: omni-retail-ge-app)
 - 실행 모드     : 가상 모의 실행 (--dry-run)
----------------------------------------------------------------------------------------

 [45분 핸즈온 워크숍 역할 분담 타임라인 (CLI 자동화 vs 콘솔 UI 전용 조작)]
  * 00~05분 [CLI 자동화] : cymbal_gold 스몰셋 테이블 4개, 실데이터, 시맨틱 뷰 원클릭 구축 (python diagnose.py --setup-demo)
  * 05~10분 [CLI -> UI]  : Agents에 붙여넣을 System Instructions 및 Verified Queries 출력 (python diagnose.py --agent-config)
  * 10~30분 [콘솔 UI 전용]: BigQuery Studio > Agents에서 단독(Standalone) Data Agent 생성 및 질의 테스트
  * 30~45분 [선택 사항]  : 필요 시 Gemini Enterprise App에 게시 및 추가 연동 (python diagnose.py --register-ge-app)
----------------------------------------------------------------------------------------

 [실습 검증용 골든 프롬프트 3선 (Data Agent 대화창 또는 Gemini Enterprise app 공용)]

  [PROMPT-01] 지점 및 결제 수단별 순매출(Net Revenue) 및 할인 금액 집계
    - 자연어 질문(Prompt) : "지점(store_branch) 및 결제 수단(tender_type)별 총상품 금액(subtotal_amount), 할인 금액(discount), 세금(tax_amount)을 반영한 순매출(Net Revenue)을 비교해 줘."
    - 에이전트 생성 SQL   : SELECT store_branch, tender_type, SUM(subtotal_amount) AS gross_subtotal, SUM(discount) AS total_discount, SUM(net_revenue) AS net_revenue FROM `sample-project-id.cymbal_gold.v_cymbal_retail_semantic` GROUP BY store_branch, tender_type ORDER BY net_revenue DESC;
    - 실데이터 응답 결과  :
        {"store_branch": "백화점 본점", "tender_type": "CREDIT_CARD", "gross_subtotal": 520000000, "total_discount": 35000000, "net_revenue": 533500000}
        {"store_branch": "백화점 잠실점", "tender_type": "MOBILE_PAY", "gross_subtotal": 330000000, "total_discount": 25000000, "net_revenue": 335500000}
        {"store_branch": "하이퍼마켓 서울역점", "tender_type": "CREDIT_CARD", "gross_subtotal": 310000000, "total_discount": 40000000, "net_revenue": 297000000}

  [PROMPT-02] 결품 예상 커버 시간(Cover Hours) 6시간 이하 긴급 보충 품목 탐지
    - 자연어 질문(Prompt) : "현재 진열 재고(shelf_qty)와 창고 재고(backroom_qty) 합계를 시간당 판매 속도로 나눴을 때, 결품 예상 커버 시간(est_cover_hours)이 6시간 이하인 긴급 보충 대상 지점과 품목(item_sku)을 알려 줘."
    - 에이전트 생성 SQL   : SELECT DISTINCT store_branch, item_sku, category, shelf_qty, backroom_qty, total_units_sold_intraday, est_cover_hours FROM `sample-project-id.cymbal_gold.v_cymbal_retail_semantic` WHERE est_cover_hours <= 6.0 ORDER BY est_cover_hours ASC;
    - 실데이터 응답 결과  :
        {"store_branch": "하이퍼마켓 서울역점", "item_sku": "SKU-FRESH-001", "category": "Fresh_Food (신선식품)", "shelf_qty": 20, "backroom_qty": 40, "total_units_sold_intraday": 144, "est_cover_hours": 5.0}
        {"store_branch": "백화점 잠실점", "item_sku": "SKU-LUX-088", "category": "Luxury_Cosmetics (명품화장품)", "shelf_qty": 8, "backroom_qty": 12, "total_units_sold_intraday": 42, "est_cover_hours": 5.7}

  [PROMPT-03] 캐셔 프로모션 임의 할인 남용(cashier_promo_abuse) 이상 거래 진단
    - 자연어 질문(Prompt) : "이상 거래 경보 테이블(pos_anomaly_alerts)에서 프로모션 남용(cashier_promo_abuse) 경보가 발생한 지점과 담당 캐셔 ID, 심각도(severity)를 보여 줘."
    - 에이전트 생성 SQL   : SELECT DISTINCT store_branch, cashier_id, alert_type, severity, promo_override_rate FROM `sample-project-id.cymbal_gold.v_cymbal_retail_semantic` WHERE alert_type = 'cashier_promo_abuse' ORDER BY promo_override_rate DESC;
    - 실데이터 응답 결과  :
        {"store_branch": "하이퍼마켓 부산점", "cashier_id": "EMP-9012", "alert_type": "cashier_promo_abuse", "severity": "CRITICAL", "promo_override_rate": 0.28}
        {"store_branch": "백화점 본점", "cashier_id": "EMP-3314", "alert_type": "cashier_promo_abuse", "severity": "HIGH", "promo_override_rate": 0.19}

========================================================================================
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

### 1단계: 스몰셋 데이터셋 및 시맨틱 뷰 원클릭 배포
명령어 한 줄로 BigQuery 스몰셋 4개 테이블, 실데이터 및 `v_cymbal_retail_semantic` 시맨틱 뷰를 자동 구축한다:
```bash
python diagnose.py --setup-demo
```

### 2단계: BigQuery Studio > Agents (Agent Catalog) 단독 에이전트 생성
터미널에 출력된 System Instructions와 Verified Queries를 BigQuery Studio 대화형 에이전트 설정창에 복사/붙여넣기하여 즉시 활성화한다:
```bash
python diagnose.py --agent-config
```

### 3단계: [선택 사항] Gemini Enterprise App 연동 및 전사 공유
전사 대화 포털에서 본 Data Agent를 멘션(@)하거나 활용할 수 있도록 A2A 프로토콜 기반으로 게시한다:
```bash
python diagnose.py --register-ge-app --app-id [GE_APP_ID]
```

### 4단계: 4대 표준 라벨 준수 및 실습 종료 후 자원 정리
- 사내 거버넌스 준수를 위해 데이터셋 및 뷰 생성 시 4대 표준 라벨(`managed-by=google-cloud-0-to-1`, `scenario=bigquery-data-agent-starter`, `env=sample`, `created-by=customer-engineer`)을 누락 없이 유지한다.
- 핸즈온 종료 후 불필요한 과금을 차단하기 위해 아래 명령어로 스몰셋 데이터셋을 일괄 삭제한다:
```bash
python diagnose.py --teardown
```
