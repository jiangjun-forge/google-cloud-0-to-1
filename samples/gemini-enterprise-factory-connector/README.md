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

# Gemini Enterprise In-Chat Factory: 기간계 데이터 및 MCP 커넥터 모듈 (gemini-enterprise-factory-connector)

`Gemini Enterprise In-Chat Factory`의 5대 핵심 모듈 중 사내 기간계 데이터 연동을 담당하는 도구로, 구글 드라이브나 빅쿼리 같은 1P 자산 외에 지라(Jira), 컨플루언스(Confluence), 세일즈포스(Salesforce), 서비스나우(ServiceNow), 셰어포인트(SharePoint), SAP 등 14대 엔터프라이즈 3P SaaS 시스템의 데이터를 제미나이 엔터프라이즈 앱(Gemini Enterprise app)에 연결할 수 있도록 데이터 저장소(Data Store) 구성 매니페스트와 ACL 동기화 설정을 대화창 내에서 자율 생성해 주는 사내 커넥터 스캐폴더 엔지니어링 모듈이다. (As of 2026-11-10)

---

## 1. 발생 증상 및 진단 대상 체크리스트

사내 엔터프라이즈 에이전트 도입 후 다음과 같은 실무적 한계나 연동 난관이 발생하고 있다면 본 솔루션 도입이 필요하다:
- [ ] **기간계 데이터 파편화**: 사내 주요 지식이 지라, 컨플루언스, 세일즈포스, 셰어포인트 등 여러 SaaS에 분산되어 있어 AI 검색을 위한 단일 뷰 구성이 어려운 경우
- [ ] **인증 프로토콜 복잡성**: 각 데이터 소스마다 OAuth 2.0, API Token, JWT 등 인증 방식이 제각각이어서 커넥터 매니페스트 작성에 많은 시간이 소모되는 경우
- [ ] **문서 레벨 권한(ACL) 유실 우려**: 원본 SaaS의 사용자별 열람 권한이 동기화되지 않아 권한 없는 사용자에게 기밀 정보가 노출될 위험이 있는 경우
- [ ] **동기화 주기 및 증분 색인 미흡**: 변경 데이터가 실시간 또는 정기적으로 반영되지 않아 AI 에이전트가 과거 정보를 바탕으로 잘못된 답변을 생성하는 경우


### 1.1 도구의 본질 및 비즈니스 해결 과제 (What & Why)
- **대상 사용자 (Target)**: 엔터프라이즈 데이터 엔지니어, 사내 기간계 시스템 관리자, 솔루션 아키텍트
- **해결하는 핵심 문제 (Core Pain Points)**:
  1. Jira, Confluence, Salesforce, ServiceNow 등 사내 기간계 저장소를 Gemini Enterprise app에 연결하기 위한 데이터스토어 구성이 복잡한 문제
  2. 데이터 소스별 인증 파라미터, 동기화 주기, 수집 대상 콘텐츠 규격을 일일이 수작업으로 조합해야 하는 번거로움
  3. 원본 시스템의 문서 레벨 접근 권한(ACL)과 Cloud Identity 사용자 매핑 정책이 누락되어 검색 범위 정합성이 깨지는 현상
- **본 솔루션의 해결 방식 (Solution)**:
  - 대화형 추천 칩을 통해 대상 시스템(Jira, Confluence, Salesforce 등)을 선택하면 문서 레벨 ACL 동기화 설정과 Discovery Engine Data Store 프로비저닝 명세를 자동 생성하고 사내 앱에 바인딩한다.

### 1.2 최종 산출물 3종 세트 미리보기 (Deliverables & Visual Preview)
본 도구를 실행(`python diagnose.py`)하면 다음 3가지 구체적인 엔터프라이즈 자산이 생성된다:

| 산출물 구분 | 산출물 형태 및 명칭 | 주요 포함 내용 및 실무 활용 방안 |
| :--- | :--- | :--- |
| **① 터미널 콘솔 요약** | Visual CLI Table | 선택된 시스템 커넥터 유형, 인증 방식 및 ACL 설정, 데이터 저장소 생성 매니페스트 및 등록 결과 |
| **② 정규 진단 보고서** | 마크다운 파일 (`report.md`) | 데이터 커넥터 아키텍처 보고서, Discovery Engine Data Store 구성 매니페스트 및 동기화 스케줄 |
| **③ 후속 조치 및 배포 자산** | Actionable Asset Specs | • **데이터스토어 프로비저닝 매니페스트**: 기간계 시스템별 증분 색인 및 ACL 매핑 JSON<br/>• **실행 스크립트**: Data Store 생성 및 Gemini Enterprise app 바인딩 명령어<br/>• **사내 검색 엔진 원클릭 바인딩**: 생성된 데이터스토어를 Gemini Enterprise app에 연결하는 API 명세 |

---

## 2. 빠른 시작 (Quickstart)

> [!TIP]
> Cloud Shell 접속 환경 구성 및 저장소 클론(`git clone`) 방법은 루트의 [메인 README](../../README.md)를 참고한다.

### 1) 모의 데이터 가상 실행 (Dry-Run)
GCP API 호출 없이 내장된 가상 인프라 데이터로 정상 동작 여부를 즉시 검증한다:
```bash
python diagnose.py --dry-run
```

**터미널 진단 출력 미리보기:**
```text
===========================================================================
  Gemini Enterprise 데이터 커넥터 스캐폴더 (gemini-enterprise-factory-connector)
===========================================================================
[*] 활성 프로젝트    : sample-project-id
[*] 배포 리전        : global
[*] 대상 GE App ID   : sample-ge-app-id
[*] 실행 서비스 계정 : ge-connector-sa@sample-project-id.iam.gserviceaccount.com
[*] 실행 모드        : 가상 실행 (--dry-run)

[안내] 로컬 단일 커넥터 매니페스트 합성 보조 모드 가동

[단계 1/3] 커넥터 칩 스펙 컴파일 중...
  - 커넥터 명칭 : Confluence Cloud 사내 지식 베이스 커넥터 (슬러그: collab-confluence-wiki)
  - 시스템 분류 : 협업 도구 및 기술 문서
  - 인증 방식   : OAUTH2_CLIENT_CREDENTIALS
  - ACL 동기화  : SPACE_AND_PAGE_RESTRICTIONS

[단계 2/3] Discovery Engine Data Store 매니페스트 합성 중...
  - 생성된 Data Store ID : ds-collab-confluence-wiki-sample-p
  - 인증 방식            : OAUTH2_CLIENT_CREDENTIALS (ACL: SPACE_AND_PAGE_RESTRICTIONS)

[단계 3/3] 서비스 계정 IAM 권한 및 Gemini Enterprise app 바인딩 진단 중...
  - 상태: PASS (Simulated) | 가상 실행 검증 완료

[성공] 마크다운 진단 보고서가 저장되었습니다: report.md

===========================================================================
  데이터 커넥터 스펙 컴파일 및 진단 완료
===========================================================================
```


### 2) 사내 환경 대화형 설정 (Config Wizard, 선택 사항)
사내 활성 프로젝트, 리전 및 실시간 Gemini Enterprise App 목록을 감지하여 `.env`에 자동 저장한다:
```bash
python diagnose.py --config
```


### 3) 실제 사내 인프라 실시간 진단 및 팩토리 프로비저닝
```bash
python diagnose.py
```
> [!NOTE]
> 앞서 `python diagnose.py --config`로 환경 설정을 저장했거나 gcloud 활성 설정을 그대로 활용할 경우 별도의 `.env` 생성 없이 즉시 실행할 수 있다. (환경 변수를 텍스트 에디터로 직접 수동 편집하고자 할 때만 `cp -n .env.example .env` 실행 후 수정)

---

## 3. 솔루션 아키텍처 및 런타임 서비스 흐름

```mermaid
flowchart TB
    subgraph Client["1. 사용자 인터랙션 (Gemini Enterprise app)"]
        DataAdmin["데이터 관리자 / 엔지니어"] -->|"1. 사내 기간계 연결 요청"| GEApp["Gemini Enterprise app<br/>웹 대화형 포털 (/r/agents)"]
    end

    subgraph Runtime["2. Agent Engine 호스팅 런타임"]
        GEApp -->|"2. 대화형 스캐폴딩 세션 인입"| Engine["Agent Engine 런타임<br/>(ResilientAdkApp / gemini-3.8-flash)"]
        Templates["14대 기간계 커넥터 카탈로그<br/>(Jira/Confluence/Salesforce 등)"] --- Engine
        Tools["bind_enterprise_datastore_tool<br/>(대행 SA: ge-connector-sa)"] --> Engine
    end

    subgraph Backend["3. Discovery Engine Data Store & 기간계 연동"]
        Tools -->|"3. Data Store 프로비저닝 및 엔진 바인딩"| DiscEng["Discovery Engine Data Store<br/>(문서 레벨 ACL 동기화)"]
        SaaSAssets["사내 기간계 SaaS<br/>(Jira, Confluence, Salesforce, SharePoint 등)"] -.->|"증분 색인 동기화"| DiscEng
        DiscEng -->|"4. RAG 검색 색인 및 그라운딩"| GEApp
    end

    classDef portal fill:#e8f0fe,stroke:#4285f4,stroke-width:2px;
    classDef runtime fill:#e6f4ea,stroke:#34a853,stroke-width:2px;
    classDef backend fill:#fce8e6,stroke:#ea4335,stroke-width:2px;

    class DataAdmin,GEApp portal;
    class Engine,Templates,Tools runtime;
    class DiscEng,SaaSAssets backend;
```

---

## 4. 조치 가이드 및 권장 설정

- **Discovery Engine 데이터 저장소 콘솔**: ( https://console.cloud.google.com/gen-app-builder/data-stores )
- **Gemini Enterprise App 관리 콘솔**: ( https://console.cloud.google.com/gemini-enterprise/locations/global/engines )
- **IAM 및 서비스 계정 콘솔**: ( https://console.cloud.google.com/iam-admin/iam )

---
## 5. 사전 준비 사항 (필요 IAM 권한)

본 도구를 실행하고 실제 리소스를 배포하기 위해 필요한 최소 IAM 역할은 다음과 같다:

| 역할 (Role) | 권한 및 용도 |
| :--- | :--- |
| `roles/discoveryengine.admin` | Discovery Engine Data Store 생성, 스케줄 설정 및 엔진 바인딩 |
| `roles/iam.serviceAccountUser` | 커넥터 실행 대행 서비스 계정 가장 실행 |

---

## 6. 기술적 배경 및 아키텍처 원리 (Deep Dive)

### 관련 상세 설계 및 요구 사항 명세
- [비즈니스 요구 사항 명세서 (BRD)](docs/BRD.md): 비즈니스 배경, 성공 지표 및 요구 사항(BR-01~) 명세
- [기술 상세 설계서 (TDD)](docs/TDD.md): 시스템 아키텍처, 기능(FR-01~) 및 비기능(NFR-01~) 설계 명세

데이터 커넥터 인프라 및 리소스(Discovery Engine Data Store 등) 생성 시 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-factory-connector`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---
## 7. 리소스 정리 (Teardown) 안내

본 도구로 생성된 테스트 데이터 저장소를 정리하고자 할 경우 아래 명령어를 순차적으로 실행한다:

```bash
# 1. Gemini Enterprise app에서 Data Store 바인딩 해제
curl -X POST \
    -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    -H "Content-Type: application/json" \
    "https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/engines/${GE_APP_ID}:unbindDataStore" \
    -d '{"dataStoreId": "'${DATA_STORE_ID}'"}'

# 2. Discovery Engine Data Store 삭제
gcloud beta discovery-engine data-stores delete "${DATA_STORE_ID}" \
    --project="${PROJECT_ID}" \
    --location="${LOCATION}" --quiet
```
