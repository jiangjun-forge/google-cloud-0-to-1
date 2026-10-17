# Gemini Enterprise 자율형 사내 스킬 팩토리 진단 및 배포 보고서

- **실행 일시**: 2026-10-17 06:38:53 UTC
- **대상 프로젝트**: `sample-project-id`
- **Gemini Enterprise app 인스턴스**: `sample-ge-app-id`
- **스킬 실행 서비스 계정**: `ge-skill-invoker-sa@sample-project-id.iam.gserviceaccount.com`
- **생성된 도구**: `sheets_data_lookup` (Google Sheets 사내 실적 및 명단 행 조회 스킬)

---

## 1. 종합 진단 및 스킬 배포 상태 요약

| 진단 항목 | 상태 | 상세 결과 |
| :--- | :---: | :--- |
| **도구 분류 및 작업 유형** | `READ` | `Google Workspace 연동` (GET /api/v1/sheets/lookup) |
| **OpenAPI 3.0 스키마** | `SYNTHESIZED` | 엔터프라이즈 Function Calling 호환 JSON 스펙 합성 완료 |
| **보안 볼트(Secret Manager)** | `BOUND` | `gcp_secret_manager://projects/sample-project-id/secrets/workspace-service-account-key/versions/latest` 연동 |
| **거버넌스 승인 상태** | `ACTIVE (즉시 활성화)` | 단순 데이터 조회 스킬로서 자율 생성 즉시 사내 에이전트에 바인딩 가능 |
| **IAM 자격 증명 진단** | `PASS (Simulated)` | `ge-skill-invoker-sa@sample-project-id.iam.gserviceaccount.com` / `roles/secretmanager.secretAccessor` 점검 통과 |

---

## 2. 생성된 OpenAPI 3.0 스키마 매니페스트 (Tool Manifest)

Gemini Enterprise app 도구 레지스트리에 배포되는 정량 스키마 전문이다:

```json
{
  "openapi": "3.0.3",
  "info": {
    "title": "Google Sheets 사내 실적 및 명단 행 조회 스킬",
    "description": "지정된 구글 스프레드시트에서 사원명, 주문번호, 자산번호 등 키워드를 기준으로 대상 행 데이터를 검색 및 추출하는 조회 도구",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://api.sample-project-id.example.com"
    }
  ],
  "paths": {
    "/api/v1/sheets/lookup": {
      "get": {
        "operationId": "sheets_data_lookup",
        "summary": "Google Sheets 사내 실적 및 명단 행 조회 스킬",
        "description": "지정된 구글 스프레드시트에서 사원명, 주문번호, 자산번호 등 키워드를 기준으로 대상 행 데이터를 검색 및 추출하는 조회 도구",
        "parameters": [
          {
            "name": "spreadsheet_url",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "sheet_name",
            "in": "query",
            "required": false,
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "search_key",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "search_value",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": null,
        "responses": {
          "200": {
            "description": "성공적인 처리 결과 반환",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "status": {
                      "type": "string"
                    },
                    "result": {
                      "type": "object"
                    }
                  }
                }
              }
            }
          }
        },
        "security": [
          {
            "SecretManagerAuth": []
          }
        ]
      }
    }
  },
  "components": {
    "securitySchemes": {
      "SecretManagerAuth": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "Cloud Secret Manager에서 동적으로 주입되는 자격 증명: gcp_secret_manager://projects/sample-project-id/secrets/workspace-service-account-key/versions/latest"
      }
    }
  }
}
```

---

## 3. 엔터프라이즈 보안 및 자격 증명 통제

1. **평문 노출 제로(Zero-Plaintext) 원칙**:
   - 본 도구 명세에는 API 키나 토큰이 일절 하드코딩되지 않으며, 구글 클라우드 Secret Manager 볼트 URI를 통해서만 런타임에 안전하게 복호화된다.
2. **최소 권한 격리**:
   - 실행 서비스 계정(`ge-skill-invoker-sa@sample-project-id.iam.gserviceaccount.com`)은 대상 시크릿 읽기(`roles/secretmanager.secretAccessor`) 외의 불필요한 관리자 권한을 보유하지 않는다.

---

## 4. 권장 후속 조치 및 에이전트 바인딩 가이드

1. **Gemini Enterprise app 도구 레지스트리 확인**:
   - Agent 콘솔 ( https://console.cloud.google.com/vertex-ai/agents/ )에 접속하여 'Tools' 메뉴에서 등록된 `sheets_data_lookup`를 확인한다.
2. **사내 에이전트에 스킬 장착**:
   - `gemini-enterprise-copilot-agent`로 제작된 기존 노코드 에이전트 또는 커스텀 에이전트의 설정 화면에서 본 스킬을 활성화(Toggle ON)하여 즉시 실무에 투입한다.

---

## 5. 사내 거버넌스 4대 필수 표준 라벨링

사내 스킬 인프라 및 보안 볼트 리소스(Secret Manager 시크릿, 대행 서비스 계정 등) 생성 시 4대 표준 라벨을 반드시 적용한다:
- `managed-by`: `google-cloud-0-to-1`
- `scenario`: `gemini-enterprise-copilot-skill`
- `env`: `sample` (또는 `poc`)
- `created-by`: `customer-engineer`

---

## 6. 콘솔 링크 조치 가이드

- **Agent 콘솔**: 사내 등록된 도구(Tools) 및 확장 기능 관리 ( https://console.cloud.google.com/vertex-ai/agents/ )
- **Secret Manager 콘솔**: 사내 API 토큰 및 웹훅 URL 보안 볼트 관리 ( https://console.cloud.google.com/security/secret-manager )
- **IAM 및 관리자 콘솔**: 스킬 대행 서비스 계정(`ge-skill-invoker-sa@sample-project-id.iam.gserviceaccount.com`) 역할 및 바인딩 상태 확인 ( https://console.cloud.google.com/iam-admin/iam )

---

## 7. 자원 정리 안내 (Teardown)

본 솔루션 검증 후 테스트용으로 등록된 도구 매니페스트나 서비스 계정을 정리하고자 할 경우 아래 절차를 수행한다:

1. **대행 서비스 계정 삭제**:
   ```bash
   gcloud iam service-accounts delete ge-skill-invoker-sa@sample-project-id.iam.gserviceaccount.com --quiet
   ```
2. **Secret Manager 테스트 시크릿 정리**:
   ```bash
   gcloud secrets delete workspace-service-account-key --quiet
   ```
