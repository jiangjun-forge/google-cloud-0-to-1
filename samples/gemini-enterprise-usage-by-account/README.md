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

# 제미나이 엔터프라이즈(Gemini Enterprise) Model Armor 감사 및 토큰 소모량 추정기 (`gemini-enterprise-usage-by-account`)

Model Armor의 살균(Sanitize) 검사 로그를 빅쿼리(BigQuery) 로그 싱크로 실시간 적재하여, **엔터프라이즈 Gemini 환경에서 사용자별 프롬프트 검사 이력과 추정 토큰 소모량을 1분 만에 분석**하는 가이드다. (As of 2026-07-01)

**Audience**: `#Architect`, `#FinOps`, `#SecOps`  
**Concern**: `#Billing`, `#Compliance`, `#Security`  
**Service**: `#BigQuery`, `#CloudLogging`, `#GeminiAPI`, `#ModelArmor`

---

## 1. 문제 증상 체크리스트

- **Gemini Enterprise 토큰 추적**: 엔터프라이즈 포털이나 사내 챗봇에서 사용자별로 소모된 토큰량을 상세히 추적 및 정산하고자 할 때
- **Model Armor 살균 이력 감사**: 보안 위협(탈옥, 프롬프트 인젝션, 민감 정보)으로 인해 Model Armor에서 살균되거나 차단된 프롬프트 본문을 영구 보관 및 감사할 때
- **비정형 프롬프트 기반 토큰 추정**: API 응답 메타데이터가 제한적인 환경에서 프롬프트/응답 문자 길이를 기반으로 정밀한 토큰 소비량을 가중 역산하고자 할 때

---

## 2. 처리 흐름도

```mermaid
flowchart TD
    Start(["사용자 Gemini Enterprise 프롬프트 입력"]) --> Armor["Model Armor 보안 검사 실행<br/>(Sanitize Operations)"]
    
    Armor --> GenerateLog["SanitizeOperationLogEntry 감사 로그 발생"]
    GenerateLog --> Sink["Cloud Logging 로그 싱크 라우팅<br/>(model-armor-logs-sink)"]
    
    Sink --> BigQueryTable[("BigQuery 파티션 테이블 적재<br/>(gcp_logs.modelarmor_..._sanitize_operations_*)")]
    
    BigQueryTable --> RunSQL["문자열 길이 기반 가중 토큰 역산 SQL 실행"]
    RunSQL --> OutputReport["사용자별 활동 횟수 및 추정 토큰량 순위 도출"]
    OutputReport --> Done(["[완료] 엔터프라이즈 AI 보안 감사 및 비용 정산"])

    classDef alert fill:#ffdddd,stroke:#f44336,stroke-width:2px;
    classDef success fill:#ddffdd,stroke:#4caf50,stroke-width:2px;
    classDef action fill:#e3f2fd,stroke:#2196f3,stroke-width:2px;
    class Start action;
    class Done success;
    class Armor,GenerateLog,Sink,BigQueryTable,RunSQL,OutputReport action;
```

---

## 3. 필요 IAM 권한

로그 싱크 생성 및 BigQuery 데이터세트 권한 위임을 위한 IAM 역할이다:

| 역할 (Role) | 권한 ID | 용도 |
| :--- | :--- | :--- |
| **로그 구성 작성자** | `roles/logging.configWriter` | Cloud Logging 로그 싱크 생성 및 라우팅 규칙 관리 |
| **BigQuery 관리자** | `roles/bigquery.admin` | BigQuery 데이터세트 생성 및 싱크 서비스 계정 권한 위임 |

> [!NOTE]
> `--dry-run` 모드로 실행할 경우 구글 클라우드 IAM 권한 없이도 파이프라인 구성과 토큰 추정 SQL 쿼리를 즉시 확인할 수 있다.

---

## 4. 원클릭 실행법

### 가상 검증 실행 (--dry-run)
실제 리소스 생성 및 쿼리 없이 가상 분석 리포트를 시뮬레이션한다. 실행 시 `report.md` 파일이 자동 생성된다:
```bash
python diagnose.py --dry-run
```

### 실제 환경 진단
사내 활성 프로젝트 대상 로그 싱크 구성 및 토큰 사용량을 분석한다. 진단 결과는 `report.md`에 자동으로 덮어써진다:
```bash
python diagnose.py --project="your-project-id" --dataset="gcp_logs" --days=7
```

---

## 5. 결과 확인 후 즉각 조치 가이드

스크립트가 완료되면 아래와 같이 **사용자별 검사 횟수 및 추정 토큰 소모량**이 출력된다:

```text
========================================================================
[진단 결과] 제미나이 엔터프라이즈 Model Armor 감사 및 토큰 통계
  - 대상 프로젝트: my-corp-ai
  - BigQuery 데이터세트: gcp_logs
  - 조회 기간: 최근 7일
========================================================================

[Model Armor 보안 검사 기반 사용자별 활동 및 추정 토큰량 순위]
┌───────────────────────────────────────────┬────────────┬──────────────────┬─────────────────┬──────────────────┐
│ 사용자/클라이언트 식별자 (Principal)     │ 검사 횟수  │ 추정 입력 토큰   │ 추정 출력 토큰  │ 총 추정 토큰     │
├───────────────────────────────────────────┼────────────┼──────────────────┼─────────────────┼──────────────────┤
│ enterprise-agent-bot@company.com          │ 5,420회    │ 16,260,000       │ 2,710,000       │ 18,970,000       │
│ finance-advisor@company.com               │ 1,120회    │  3,360,000       │   560,000       │  3,920,000       │
│ hr-assistant@company.com                  │   780회    │  1,560,000       │   390,000       │  1,950,000       │
│ external-partner-eval@partner.com         │   110회    │    220,000       │    55,000       │    275,000       │
└───────────────────────────────────────────┴────────────┴──────────────────┴─────────────────┴──────────────────┘
```

---

## 6. 자원 정리 안내 (Teardown)

테스트 완료 후 과금 방지 및 자원 잔존을 막기 위해 생성된 로그 싱크와 데이터세트를 삭제한다:

```bash
# 1. Cloud Logging 로그 싱크 삭제
gcloud logging sinks delete model-armor-logs-sink --project=YOUR_PROJECT_ID

# 2. BigQuery 데이터세트 삭제
bq rm -r -f -d YOUR_PROJECT_ID:gcp_logs
```
