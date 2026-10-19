<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

> [!IMPORTANT]
> **구글 (Google LLC) 참조용 샘플 고지 사항**:
> 본 프로젝트의 모든 소스 코드와 문서는 Google LLC의 소유이며, Apache-2.0 라이선스에 따라 오직 **참조용 샘플 (Sample / Reference Only)** 목적으로만 제공된다. 프로덕션 환경에 그대로 사용할 수 없으며, 사전 통지 없이 언제든 내용이 수정, 변경 또는 삭제될 수 있다.

# BigQuery Conversational Analytics Data Agent 45분 완성 스타터 가이드 (Standalone & Optional Gemini Enterprise app)

45분 핸즈온 워크숍 내에 참석자가 명령어 한 줄(`--setup-demo`)로 빅쿼리(BigQuery) 스몰셋 데이터셋(`cymbal_gold`)과 실데이터를 10초 만에 자동 구축하고, 구글 1P 완전 관리형 런타임(GDA `dataAgents` REST API)을 통해 CLI 원클릭(`--deploy-agent`)으로 데이터 에이전트를 프로비저닝하며, A2A 표준 규격 기반으로 제미나이 엔터프라이즈 앱(Gemini Enterprise app)에 직결 연동하거나 BigQuery Studio 콘솔 UI에서 단독(Standalone)으로 멀티턴 대화 질의를 완주할 수 있도록 설계된 실무 워크숍 스타터 키트다. (As of 2026-10-19)

**Audience**: `#Architect`, `#DataEngineer`, `#Developer`  
**Concern**: `#GenAI`, `#Governance`, `#Performance`  
**Service**: `#AgentPlatform`, `#BigQuery`, `#GeminiAPI`, `#VertexAI`

---

## 1. 이 가이드가 필요한 상황 (증상 체크리스트)

다음과 같은 요구 사항이 워크숍이나 사내 PoC에서 발생하고 있다면 즉시 본 스타터 키트를 활용해야 한다:

- [ ] 45분 내외의 짧은 핸즈온 세션 동안 참석자들이 BigQuery 데이터 준비부터 BigQuery Data Agent 생성 및 자연어 질의응답까지 막힘 없이 완주해야 하는 경우
- [ ] 별도의 컨테이너 빌드나 유휴 VM 비용 없이, 구글 관리형 테넌트 GDA(Gemini Data Analytics) `dataAgents` REST API를 통해 CLI 한 줄로 에이전트를 자동 프로비저닝하고자 하는 경우
- [ ] 제미나이 엔터프라이즈 앱에 올리지 않고 BigQuery Studio 내에서 단독(Standalone)으로 Data Agent를 쓰는 부서와, 제미나이 엔터프라이즈 앱에 직결 게시하려는 전사 배포 조직 모두를 하나의 워크숍 키트로 지원해야 하는 경우
- [ ] 별도의 GCP 과금이나 권한 부여 전, 가상 실행(`--dry-run`)으로 전체 SQL DDL/DML과 에이전트 시스템 지침, A2A Agent Card 명세를 사전 검토하고자 하는 경우

---

## 2. 45분 핸즈온 실습 흐름

```mermaid
flowchart TD
    A["실습 시작 (python diagnose.py)"] --> B["Step 1 [CLI 자동화]: cymbal_gold 4개 테이블 및 실데이터 구축 (--setup-demo)"]
    B --> C["pos_transactions_gold, gold_inventory_reconciliation_ledger 등 4개 테이블 + 실데이터 적재"]
    C --> D["v_cymbal_retail_semantic 시맨틱 뷰 생성 (순매출, 결품 커버 시간 공식 내장)"]
    D --> E["Step 2 [CLI 자동 배포 - 권장 골든 경로]: GDA dataAgents 원클릭 프로비저닝 (--deploy-agent)"]
    E --> F["A2A Agent Card 표준 규격 자동 생성 (a2a_agent_card.json)"]
    D -.-> G["Step 2 [보조 확인 경로]: BigQuery Studio 콘솔 UI 수동 생성 지침 출력 (--agent-config)"]
    F --> H{"선택 사항: Gemini Enterprise App 사내 갤러리 직결 연동 (--register-ge-app)"}
    H -- "예 (Discovery Engine API 직결)" --> I["A2A Agent Card 규격으로 GE App 사내 갤러리 자동 등록"]
    H -- "아니오 (Standalone 완주)" --> J["Data Agent 대화창에서 골든 프롬프트 3선 자연어 질의 실습"]
    I --> J
    J --> K["실습 종료 후 리소스 원클릭 정리 (--teardown)"]
```

---

## 3. 사전 준비 사항 (필요 IAM 권한)

45분 핸즈온 실습을 위해 참석자 계정 또는 서비스 계정에 요구되는 최소 IAM 권한은 다음과 같다:

| 역할 (Role) | 권한 (Permission) | 용도 |
| :--- | :--- | :--- |
| `roles/bigquery.dataEditor` | `bigquery.datasets.create`, `bigquery.tables.create` | `--setup-demo` 실행 시 `cymbal_gold` 4개 테이블, 실데이터, 시맨틱 뷰 생성 |
| `roles/bigquery.jobUser` | `bigquery.jobs.create` | BigQuery 쿼리 실행 및 Data Agent 시맨틱 뷰 조회 |
| `roles/geminidataanalytics.dataAgentCreator` | `geminidataanalytics.dataAgents.create` | 구글 1P 완전 관리형 GDA `dataAgents` REST API 호출 및 에이전트 자동 생성 |
| `roles/discoveryengine.admin` | `discoveryengine.engines.update`, `discoveryengine.agents.create` | `[선택 사항]` A2A Agent Card를 Gemini Enterprise App 사내 갤러리에 직결 등록 |

---

## 4. 45분 타임어택 핸즈온 실습 단계별 가이드

### 4.1 실습 환경 준비 (저장소 클론 및 디렉터리 이동)
Cloud Shell 또는 로컬 터미널에서 저장소를 클론하고 실습 샘플 디렉터리로 이동한다:

```bash
git clone https://github.com/jiangjun-forge/google-cloud-0-to-1.git
cd google-cloud-0-to-1/samples/bigquery-data-agent-starter
```

### 4.2 사전 가상 검증 모드 (Dry-run 스모크 테스트)
실제 GCP API 호출 없이 45분 실습 전체 흐름과 자동 생성될 SQL, GDA REST API 페이로드, A2A Agent Card 명세를 1초 만에 미리 확인할 수 있다:

```bash
# 전체 45분 워크숍 가이드 및 골든 프롬프트 3선 시뮬레이션
python diagnose.py --dry-run

# 스몰셋 테이블 생성 DDL 및 샘플 데이터 INSERT SQL 사전 확인
python diagnose.py --dry-run --setup-demo

# GDA dataAgents 자동 배포 페이로드 및 A2A 규격 시뮬레이션
python diagnose.py --dry-run --deploy-agent
```

### 4.3 Step 1 (00~05분, CLI 자동화): 스몰셋 데이터셋(`cymbal_gold`) 원클릭 구축
아래 명령어를 실행하면 BigQuery 데이터셋(`cymbal_gold`), 4개 스몰셋 테이블(`pos_transactions_gold`, `gold_inventory_reconciliation_ledger`, `pos_anomaly_alerts`, `historical_transactional_data`), 실제 샘플 데이터, 시맨틱 뷰(`v_cymbal_retail_semantic`)가 10초 내에 자동으로 구축된다:

```bash
# cymbal_gold 데이터셋 + 4개 테이블 + 실데이터 + 시맨틱 뷰 원클릭 구축
python diagnose.py --setup-demo
```

### 4.4 Step 2 (05~15분, CLI 자동화 권장): GDA `dataAgents` 원클릭 프로비저닝 (골든 경로)
별도의 컨테이너 빌드나 유휴 비용 없이, 구글 관리형 런타임 GDA REST API를 통해 1초 만에 빅쿼리 데이터 에이전트를 자동 생성하고 A2A 표준 명세(`a2a_agent_card.json`)를 로컬에 보존한다:

```bash
# GDA dataAgents 자동 생성 및 A2A 규격 저장 (권장 골든 경로)
python diagnose.py --deploy-agent
```

- **[보조 확인 경로] 콘솔 UI 수동 생성 (선택 사항)**:
  사내망 정책상 REST API 직접 호출이 제한되는 환경에서는 콘솔 UI 수동 생성 지침을 출력하여 진행할 수 있다:
  ```bash
  python diagnose.py --agent-config
  ```
  1. Google Cloud 콘솔 > BigQuery 좌측 탐색 바에서 **Agents (에이전트 / Agent Catalog)** 메뉴를 클릭한다.
  2. 상단 **[+ Create Data Agent (데이터 에이전트 만들기)]** 버튼을 클릭한다.
  3. 에이전트 이름에 `cymbal-retail-data-agent`를 입력한다.
  4. **[Select data sources (데이터 소스 선택)]**에서 `cymbal_gold.v_cymbal_retail_semantic` 뷰를 체크한다.
  5. **[Instructions (지침)]** 및 **[Verified Queries]**에 터미널 출력 내용을 복사하여 붙여넣고 저장한다.
  6. 참조 문서: BigQuery Conversational Analytics 가이드 ( https://cloud.google.com/bigquery/docs/conversational-analytics )

### 4.5 Step 3 (15~25분, 선택 사항 / Optional): Gemini Enterprise App 사내 갤러리 A2A 직결 연동
BigQuery Studio 내 단독 사용으로 충분한 경우 본 단계는 건너뛸 수 있다. 생성된 에이전트를 Gemini Enterprise 웹 앱 대화창에 직결 연동하여 전사 공유하고자 할 경우 아래 명령어를 실행한다:

```bash
# Discovery Engine REST API 기반 GE App 사내 갤러리 직결 등록
python diagnose.py --register-ge-app
```
> Discovery Engine API 권한이 없거나 웹 앱이 미배포된 경우, 자동으로 콘솔 UI 수동 등록 가이드(Phase A/B)를 출력하는 안전한 Fallback이 동작한다.

### 4.6 [올인원 모드]: Step 1~3 전체 일괄 자동 배포
핸즈온 세션 시간을 극대화하기 위해 데이터셋 구축, GDA 에이전트 프로비저닝, GE App 사내 갤러리 등록을 한 번에 실행할 수 있다:

```bash
python diagnose.py --all
```

---

## 5. 실습 검증용 골든 프롬프트 3선

- **골든 프롬프트 1 (지점 및 결제 수단별 순매출 비교)**:
  ```text
  지점(store_branch) 및 결제 수단(tender_type)별 총상품 금액(subtotal_amount), 할인 금액(discount), 세금(tax_amount)을 반영한 순매출(Net Revenue)을 비교해 줘.
  ```
- **골든 프롬프트 2 (결품 예상 커버 시간 6시간 이하 긴급 보충 품목 탐지)**:
  ```text
  현재 진열 재고(shelf_qty)와 창고 재고(backroom_qty) 합계를 시간당 판매 속도로 나눴을 때, 결품 예상 커버 시간(est_cover_hours)이 6시간 이하인 긴급 보충 대상 지점과 품목(item_sku)을 알려 줘.
  ```
- **골든 프롬프트 3 (캐셔 프로모션 임의 할인 남용 이상 거래 진단)**:
  ```text
  이상 거래 경보 테이블(pos_anomaly_alerts)에서 프로모션 남용(cashier_promo_abuse) 경보가 발생한 지점과 담당 캐셔 ID, 심각도(severity)를 보여 줘.
  ```

---

## 6. GCP 리소스 생성 시 4대 필수 표준 라벨링 준수

사내 FinOps 비용 추적 및 워크숍 자원 자동 식별을 위해 본 도구가 생성하는 모든 BigQuery 데이터셋, 테이블, 시맨틱 뷰에는 다음 4대 표준 라벨이 필수로 주입된다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `bigquery-data-agent-starter`
- `env`: `sample`
- `created-by`: `customer-engineer`

---

## 7. 자원 정리 (Teardown)

45분 핸즈온 실습이 끝난 후 불필요한 클라우드 리소스 과금을 예방하기 위해 아래 명령어로 스몰셋 데이터셋을 즉시 정리한다:

```bash
# 생성된 실습 데이터셋(cymbal_gold) 및 하위 테이블/뷰 일괄 삭제
python diagnose.py --teardown
```
