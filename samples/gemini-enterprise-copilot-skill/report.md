# Gemini Enterprise 사내 스킬 팩토리 배포 보고서 (gemini-enterprise-copilot-skill)

- **배포 일시**: 2026-10-20 02:38:34 UTC
- **대상 프로젝트**: `sample-project-id`
- **Gemini Enterprise app 인스턴스**: `sample-ge-app-id`
- **팩토리 에이전트**: `GE Skill Factory (사내 스킬 팩토리)`
- **배포 상태**: `DRY_RUN_PASSED`

---

## 1. 팩토리 에이전트(붕어빵 틀) 프로비저닝 결과 요약

| 항목 | 상태 | 세부 정보 |
| :--- | :---: | :--- |
| **에이전트 명칭** | `PROVISIONED` | `GE Skill Factory (사내 스킬 팩토리)` |
| **호스팅 런타임** | `Agent Engine` | `projects/sample-project-id/locations/us-central1/reasoningEngines/2791448937123987456` |
| **추론 파운데이션 모델** | `gemini-3.8-flash` | 위치: `global` (샌드박스 안정성 보장) |
| **내장 실행 도구** | `3종 완비` | `deploy_enterprise_skill_tool`, `list_enterprise_skills_tool`, `get_preset_skills_tool` |
| **GE App 사내 갤러리 등록** | `ACTIVE` | 사내 갤러리(`/r/agents`) 전사 공유 (`ALL_USERS`) 바인딩 완료 |

---

## 2. 팩토리 에이전트 아키텍처 및 스킬 제작 흐름

본 솔루션은 사내 개발자 및 임직원이 복잡한 OpenAPI 스펙이나 Secret Manager 권한을 일일이 수동 구성하지 않고, GE App 채팅창에서 자연어 대화만으로 사내 기간계 시스템 연동 도구(붕어빵)를 자율 제작 및 등록할 수 있도록 지원하는 **사내 스킬 팩토리(붕어빵 틀)**다:

```mermaid
flowchart TB
    subgraph Dev["1. 엔지니어링 & 프로비저닝"]
        A["인프라 / 플랫폼 엔지니어"] -->|"python diagnose.py"| B["스킬 팩토리<br/>(diagnose.py)"]
        B -->|"Google ADK 2.11+ 패키징"| C["Agent Engine 이미지 & 스펙"]
    end

    subgraph Runtime["2. 런타임 & 도구 연동"]
        C -->|"원클릭 프로비저닝"| D["Agent Engine<br/>(Reasoning Engine)"]
        D -->|"사내 갤러리 전사 등록"| E["Gemini Enterprise app<br/>사내 갤러리 (/r/agents)"]
    end

    subgraph Portal["3. 전사 임직원 인터페이스"]
        E -->|"대화형 스킬 빌더 제공"| F["사내 개발자 / 임직원<br/>(비즈니스 실무자)"]
        F -->|"자연어 도구 연동 요청"| E
        E -->|"스킬 자동 등록 도구 호출"| D
        D -->|"Secret 볼트 & 스킬 생성"| G[("Secret Manager 보안 볼트<br/>OpenAPI Tool 매니페스트")]
    end
```

---

## 3. 사내 실무자 활용 가이드 (도구 및 스킬 생성)

사내 임직원 및 개발자는 배포된 스킬 팩토리 에이전트와 대화하여 다음과 같이 사내 도구를 즉시 찍어낼 수 있다:

1. **Gemini Enterprise app 접속**:
   - 웹 포털 ( https://gemini.google.com/app/sample-ge-app-id ) 접속 후 좌측 사이드바 **사내 갤러리(`/r/agents`)** 이동.
   - **`GE Skill Factory (사내 스킬 팩토리)`** 선택.

2. **자연어 붕어빵 생성 예시 프롬프트**:
   - *"사내 Google Sheets 실적 및 명단 행 조회 스킬 만들어 줘"*
   - *"사내 인시던트 발생 시 슬랙(Slack) 채널 알림 발송 도구 배포해 줘"*
   - *"Jira Cloud 신규 이슈 및 결함 티켓 자동 생성 스킬 등록해 줘"*
   - *"ERP 구매 주문(PO) 승인 상태 조회 및 품의서 연동 도구 만들어 줘"*

3. **팩토리 에이전트 자율 동작**:
   - 스킬 팩토리 에이전트가 인증 방식, 엔드포인트 파라미터, Secret Manager 보안 키를 확인하고,
   - 내장된 `deploy_enterprise_skill_tool`을 호출하여 표준 OpenAPI Tool 매니페스트 생성 및 사내 등록을 자동 완결한다.

---

## 4. 사내 거버넌스 4대 필수 표준 라벨

팩토리 에이전트 및 하위 생성 리소스 관리 시 아래 4대 표준 라벨이 기본 적용된다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-copilot-skill`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 5. 콘솔 링크 조치 가이드

- **Agent Engine 콘솔**: 프로비저닝된 에이전트 엔진 런타임 상태 및 인스턴스 모니터링 ( https://console.cloud.google.com/vertex-ai/agents/agent-engines?project=sample-project-id )
- **Agent Platform 콘솔**: 사내 등록된 에이전트 및 Gemini Enterprise app 바인딩 관리 ( https://console.cloud.google.com/gen-app-builder/engines/sample-ge-app-id/assistants/default_assistant/agents?project=sample-project-id )
- **Secret Manager 콘솔**: 사내 시스템 API 키 및 보안 토큰 볼트 관리 ( https://console.cloud.google.com/security/secret-manager?project=sample-project-id )

---

## 6. 자원 정리 안내 (Teardown)

본 솔루션 검증 후 테스트용으로 생성된 Agent Engine 런타임 및 등록된 에이전트를 정리하고자 할 경우 아래 명령을 수행한다:

1. **Agent Engine 삭제**:
   ```bash
   # Agent Engine 인스턴스 삭제 (force=true)
   curl -X DELETE -H "Authorization: Bearer $(gcloud auth print-access-token)" \
     "https://us-central1-aiplatform.googleapis.com/v1/projects/sample-project-id/locations/us-central1/reasoningEngines/2791448937123987456?force=true"
   ```

2. **GE App 사내 갤러리 등록 해제**:
   ```bash
   # GE App 에이전트 삭제
   curl -X DELETE -H "Authorization: Bearer $(gcloud auth print-access-token)" \
     "https://discoveryengine.googleapis.com/v1alpha/projects/sample-project-id/locations/global/collections/default_collection/engines/sample-ge-app-id/assistants/default_assistant/agents/<AGENT_ID>"
   ```
