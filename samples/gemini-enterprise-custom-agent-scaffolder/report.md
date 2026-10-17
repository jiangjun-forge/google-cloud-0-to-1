# Gemini Enterprise 커스텀 에이전트 스캐폴더 보고서 (gemini-enterprise-custom-agent-scaffolder)

- **실행 일시**: 2026-10-17 04:59:40 UTC
- **대상 프로젝트**: `sample-project-id`
- **Gemini Enterprise app 인스턴스**: `sample-ge-app-id`
- **선택 아키텍처**: `bq_analytics_agent` (사내 BigQuery 데이터 웨어하우스 SQL 분석 및 지표 탐지 에이전트)

---

## 1. 종합 진단 및 스캐폴딩 상태 요약

| 진단 항목 | 상태 | 상세 결과 |
| :--- | :---: | :--- |
| **선택 아키텍처** | `COMPILED` | `사내 BigQuery 데이터 웨어하우스 SQL 분석 및 지표 탐지 에이전트` |
| **백엔드 기술 스택** | `READY` | `FastAPI + google-genai + google-cloud-bigquery` |
| **내장 도구 셋** | `3종 완비` | `query_bigquery_sql, get_dataset_schema, detect_metric_anomalies` |
| **IAM 권한 진단** | `PASS (Simulated)` | `가상 실행 검증: custom-agent-sa@sample-project-id.iam.gserviceaccount.com에 roles/bigquery.dataViewer, roles/bigquery.jobUser, roles/run.invoker 역할 바인딩 시뮬레이션 완료` |
| **Gemini Enterprise app 외부 연동** | `READY` | OIDC 토큰 기반 Cloud Run 엔드포인트 바인딩 매니페스트 도출 |

---

## 2. 생성된 하이코드 산출물 목록 (Scaffolded Artifacts)

본 도구를 통해 다음 4대 핵심 백엔드 소스 코드가 완벽하게 스캐폴딩되었다:

1. **`agent.py`**: 버텍스 AI `google-genai` 통일 SDK 및 FastAPI 기반 추론/서빙 엔드포인트
2. **`tools.py`**: 사내 시스템/BigQuery 직접 연동 도구 함수 및 Pydantic 스키마
3. **`Dockerfile`**: Python 3.11-slim 기반 경량 비루트 보안 컨테이너 이미지 빌드 파일
4. **`deploy.sh`**: Cloud Run 배포 및 서비스 계정 권한 바인딩 자동화 스크립트

---

## 3. Gemini Enterprise app 외부 에이전트 바인딩 매니페스트 (External Agent Manifest)

배포 완료 후 제미나이 엔터프라이즈 앱(Gemini Enterprise app) 카탈로그에 본 백엔드를 '외부 에이전트'로 등록하기 위한 JSON 페이로드다:

```json
{
  "displayName": "사내 BigQuery 데이터 웨어하우스 SQL 분석 및 지표 탐지 에이전트",
  "description": "빅쿼리(BigQuery) 데이터셋에 연결하여 자연어 질의를 SQL로 변환하고, 쿼리 실행 결과 및 이상 지표를 자동 분석하는 백엔드 에이전트",
  "externalEngine": {
    "endpointUri": "https://bq-analytics-agent-xyz-an.a.run.app/v1/chat",
    "serviceAccount": "custom-agent-sa@sample-project-id.iam.gserviceaccount.com",
    "authType": "OIDC_TOKEN"
  },
  "visibility": "ORGANIZATION",
  "labels": {
    "managed-by": "google-cloud-0-to-1",
    "scenario": "gemini-enterprise-custom-agent-scaffolder",
    "env": "sample"
  }
}
```

---

## 4. 핵심 소스 코드 미리보기 (agent.py)

```python
# Copyright 2026 Google LLC. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""사내 BigQuery 데이터 웨어하우스 SQL 분석 및 지표 탐지 에이전트 코어 서빙 애플리케이션."""

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from tools import get_custom_tools, execute_custom_tool

app = FastAPI(title="사내 BigQuery 데이터 웨어하우스 SQL 분석 및 지표 탐지 에이전트", version="1.0.0")

class AgentQueryRequest(BaseModel):
    prompt: str
    session_id: str | None = None

class AgentQueryResponse(BaseModel):
    response: str
    tools_called: list[str]
    session_id: str

# Google GenAI 최신 SDK 클라이언트 초기화 (글로벌 리전 권장)
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "sample-project-id")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

SYSTEM_INSTRUCTION = """너는 사내 엔터프라이즈 환경에서 구동하는 백엔드 커스
... [이하 생략: tools.py 및 deploy.sh 완비] ...
```

---

## 5. 권장 프로덕션 배포 가이드

1. **로컬 소스 파일 추출 (옵션)**:
   ```bash
   python diagnose.py --write-files
   ```
2. **Cloud Run 서비스 배포**:
   ```bash
   bash deploy.sh
   ```
3. **Gemini Enterprise app 카탈로그 외부 에이전트 등록**:
   - Agent Platform (GEAP) 콘솔 ( https://console.cloud.google.com/vertex-ai/agents/ )에서 'External Agent' 추가 후 상기 매니페스트 입력.
