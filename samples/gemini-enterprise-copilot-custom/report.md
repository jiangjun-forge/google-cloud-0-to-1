# Gemini Enterprise 커스텀 에이전트 팩토리 보고서 (gemini-enterprise-copilot-custom)

- **실행 일시**: 2026-10-19 06:45:10 UTC
- **대상 프로젝트**: `sample-project-id`
- **Gemini Enterprise app 인스턴스**: `sample-ge-app-id`
- **선택 아키텍처**: `bq_analytics_agent` (사내 BigQuery 데이터 웨어하우스 SQL 분석 및 지표 탐지 에이전트)

---

## 1. 종합 진단 및 스캐폴딩 상태 요약

| 진단 항목 | 상태 | 상세 결과 |
| :--- | :---: | :--- |
| **선택 아키텍처** | `COMPILED` | `사내 BigQuery 데이터 웨어하우스 SQL 분석 및 지표 탐지 에이전트` |
| **백엔드 기술 스택** | `READY` | `Agent Engine (ADK 2.11+) + google-genai + google-cloud-bigquery` |
| **내장 도구 셋** | `3종 완비` | `query_bigquery_sql, get_dataset_schema, detect_metric_anomalies` |
| **IAM 권한 진단** | `PASS (Simulated)` | `가상 실행 검증: custom-agent-sa@sample-project-id.iam.gserviceaccount.com에 roles/aiplatform.user, roles/discoveryengine.editor, roles/bigquery.dataViewer, roles/bigquery.jobUser 역할 바인딩 시뮬레이션 완료` |
| **Agent Engine 호스팅 연동** | `READY` | Google ADK 기반 Agent Engine 프로비저닝 및 사내 갤러리 등록 매니페스트 도출 |

---

## 2. 생성된 하이코드 산출물 목록 (Scaffolded Artifacts)

본 도구를 통해 다음 5대 핵심 Agent Engine 소스 코드가 완벽하게 스캐폴딩되었다:

1. **`agent.py`**: Google ADK 및 `agent_engines.AdkApp` 기반 에이전트 정의 코드
2. **`tools.py`**: 사내 시스템/BigQuery 직접 연동 도구 함수 모음
3. **`requirements.txt`**: Agent Engine 런타임 최소 의존성 정의
4. **`deploy.py`**: Agent Engine 프로비저닝 및 Gemini Enterprise app 전사 갤러리 자동 등록 스크립트
5. **`ge_agent_manifest.json`**: Gemini Enterprise app ADK 에이전트 연동 등록 JSON

---

## 3. Gemini Enterprise app ADK 에이전트 바인딩 매니페스트 (ADK Agent Manifest)

배포 완료 후 제미나이 엔터프라이즈 앱(Gemini Enterprise app) 사내 갤러리에 본 에이전트를 등록하기 위한 JSON 페이로드다:

```json
{
  "displayName": "사내 BigQuery 데이터 웨어하우스 SQL 분석 및 지표 탐지 에이전트",
  "description": "빅쿼리(BigQuery) 데이터셋에 연결하여 자연어 질의를 SQL로 변환하고, 쿼리 실행 결과 및 이상 지표를 자동 분석하는 에이전트",
  "sharingConfig": {
    "scope": "ALL_USERS"
  },
  "adkAgentDefinition": {
    "toolSettings": {
      "toolDescription": "빅쿼리(BigQuery) 데이터셋에 연결하여 자연어 질의를 SQL로 변환하고, 쿼리 실행 결과 및 이상 지표를 자동 분석하는 에이전트"
    },
    "provisionedReasoningEngine": {
      "reasoningEngine": "projects/sample-project-id/locations/us-central1/reasoningEngines/1673971543794778112"
    }
  },
  "labels": {
    "managed-by": "google-cloud-0-to-1",
    "scenario": "gemini-enterprise-copilot-custom",
    "env": "sample",
    "created-by": "customer-engineer"
  }
}
```

---

## 4. 핵심 소스 코드 미리보기 (agent.py)

```python
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""사내 BigQuery 데이터 웨어하우스 SQL 분석 및 지표 탐지 에이전트 코어 에이전트 정의 (Agent Engine ADK)."""

import os
from google.adk.agents import Agent
from vertexai import agent_engines
from tools import query_bigquery_sql, get_dataset_schema, detect_metric_anomalies

SYSTEM_INSTRUCTION = """너는 사내 엔터프라이즈 환경에서 구동하는 사내 BigQuery 데이터 웨어하우스 SQL 분석 및 지표 탐지 에이전트이다.
임직원의 요청을 분석하여 필요한 경우 제공된 도구(query_bigquery_sql, get_dataset_schema, detect_metric_anomalies)를 적극적으로 호출하여
정확한 데이터 기반의 전문 답변을 제공하라.
보안 수칙: 개인 식별 정보(PII)는 마스킹 처리하고, 데이터베이스 변경 작업은 신중하게 안내하라."""

agent = Agent(
    name="bq_analytics_agent",
    description="빅쿼리(BigQuery) 데이터셋에 연결하여 자연어 질의를 SQL로 변환하고, 쿼리 실행 결과 및 이상 지표를 자동 분석하는 에이전트",
    model="gemini-3.8-flash",
    instruction=SYSTEM_INSTRUCTION,
    tools=[query_bigquery_sql, get_dataset_schema, detect_metric_anomalies],
)
... [이하 생략: tools.py 및 deploy.py 완비] ...
```

---

## 5. 권장 프로덕션 배포 가이드

1. **로컬 소스 파일 추출 (옵션)**:
   ```bash
   python diagnose.py --write-files
   ```
2. **Agent Engine 및 Gemini Enterprise app 원클릭 배포**:
   ```bash
   cd scaffold
   python deploy.py
   ```
3. **Gemini Enterprise app 웹 대화 포털 확인**:
   - 사내 포털 ( https://gemini.google.com/app/sample-ge-app-id ) 접속 후 사내 갤러리(`/r/agents`)에서 에이전트 확인.

---

## 6. 사내 거버넌스 4대 필수 표준 라벨링

커스텀 에이전트 인프라 및 관리 리소스(Agent Engine, 서비스 계정 등) 생성 시 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-copilot-custom`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 7. 콘솔 링크 조치 가이드

- **Agent Engine 콘솔**: 프로비저닝된 에이전트 엔진 런타임 상태 및 인스턴스 모니터링 ( https://console.cloud.google.com/vertex-ai/agents/agent-engines?project=sample-project-id )
- **Agent Platform 콘솔**: 사내 등록된 에이전트 및 Gemini Enterprise app 바인딩 관리 ( https://console.cloud.google.com/gen-app-builder/engines/sample-ge-app-id/assistants/default_assistant/agents?project=sample-project-id )
- **IAM 및 관리자 콘솔**: 서비스 계정(`custom-agent-sa@sample-project-id.iam.gserviceaccount.com`) 권한 확인 ( https://console.cloud.google.com/iam-admin/iam?project=sample-project-id )

---

## 8. 자원 정리 안내 (Teardown)

본 솔루션 검증 후 테스트용으로 생성된 Agent Engine 런타임 및 등록된 에이전트를 정리하고자 할 경우 아래 명령을 수행한다:

1. **Agent Engine 삭제**:
   ```python
   import vertexai
   from vertexai import agent_engines

   vertexai.init(project="sample-project-id", location="us-central1")
   # agent_engines.delete(resource_name="projects/sample-project-id/locations/us-central1/reasoningEngines/<ENGINE_ID>")
   ```
2. **서비스 계정 삭제**:
   ```bash
   gcloud iam service-accounts delete custom-agent-sa@sample-project-id.iam.gserviceaccount.com --quiet
   ```
