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

# Gemini Enterprise 사설 MCP 브리지 프록시

Gemini Enterprise의 공개 HTTPS 및 OAuth 2.0 전용 제약을 극복하고, 사내 VPC 사설망 또는 온프레미스 환경에 위치한 모델 컨텍스트 프로토콜(MCP) 서버를 Direct VPC Egress 기반 Cloud Run 리버스 프록시를 통해 안전하게 연동하며, 새로 고침 토큰 누락으로 인한 1시간 후 401 대량 만료 장애를 선제 예방하는 엔터프라이즈 통합 브리지다. (As of 2026-09-11)

**Audience**: `#Architect`, `#Developer`, `#SecOps`  
**Concern**: `#Compliance`, `#Resilience`, `#Security`  
**Service**: `#CloudRun`, `#GeminiEnterprise`

---

## 1. 이 가이드가 필요한 상황

- Gemini Enterprise의 커스텀 MCP 서버(Custom MCP Server, Preview) 등록 시 **공개 HTTPS 엔드포인트**와 **OAuth 2.0**만 요구되어, 사내 사설망(Private VPC)이나 온프레미스 데이터 센터에 위치한 사내 MCP 서버를 직접 등록할 수 없는 경우
- 사내 DB, 내부 지라, 사내 위키 등 민감 데이터가 포함된 백엔드 MCP 서버를 공용 인터넷에 노출하지 않고 사설 IP로만 안전하게 유지해야 하는 경우
- 기업의 사내 표준 계정 공급자(IdP: Google Identity, Google Workspace, Okta, Microsoft Entra ID, Auth0, Keycloak 등)의 인바운드 OAuth 토큰과 사내 백엔드가 요구하는 인증(무인증, 정적 API 토큰, Google ADC) 간의 유연한 변환이 필요한 경우
- Gemini Enterprise에 MCP 서버 등록 후 정확히 1시간 뒤 새로 고침 토큰(Refresh Token) 부재로 인해 대량의 `401 Unauthorized` 오류가 발생하며 서비스가 마비되는 현상을 사전에 방지하려는 경우
- Gemini Enterprise 조직 정책(`constraints/gemini.disableCustomMcpServerConnector`)으로 인해 커스텀 커넥터 생성이 차단된 환경을 진단하고 인가하려는 경우

---

## 2. 아키텍처 및 처리 흐름

```mermaid
graph TD
    A["Gemini Enterprise"] -->|"1. 공개 HTTPS + OAuth 2.0 호출"| B["Cloud Run MCP 브리지 프록시"]
    B -->|"2. 인바운드 토큰 검증 (Google Tokeninfo / JWT / Introspect)"| C{"토큰 유효성 검증"}
    C -- "만료 또는 위조 (401)" --> D["요청 즉시 차단"]
    C -- "정상 인증 완료" --> E["업스트림 헤더 변환 및 인증 주입"]
    E -->|"3. Direct VPC Egress 사설망 라우팅"| F["사내 사설망 / 온프레미스 MCP 백엔드"]
    F -->|"4. Streamable HTTP / SSE 스트리밍 응답"| B
    B -->|"5. 실시간 데이터 중계"| A
```

---

## 3. 사전 준비 사항

### 3.1 라이선스 및 에디션 요건
- Gemini Enterprise 에디션: **Standard**, **Plus**, **Frontline** 에디션에서만 커스텀 MCP 서버 메뉴가 활성화된다. (Business 에디션은 미지원)
- 관리 콘솔 경로: Gemini Enterprise 콘솔 ( https://console.cloud.google.com/gemini-enterprise/ )
- 데이터 원본 콘솔 경로: Gemini Enterprise Data stores 콘솔 ( https://console.cloud.google.com/gemini-enterprise/data-stores )
- 공식 문서 참조: Gemini Enterprise 앱 생성 공식 가이드 ( https://cloud.google.com/gemini-enterprise/docs/create-app )

### 3.2 필수 API 활성화 및 조직 정책 해제
프로젝트 관리자 권한으로 아래 명령어를 실행한다:
```bash
# 1. 필수 API 활성화
gcloud services enable run.googleapis.com discoveryengine.googleapis.com --project "[PROJECT_ID]"

# 2. 커스텀 MCP 커넥터 차단 조직 정책 비활성화 (Org Policy Administrator 필요)
gcloud resource-manager org-policies disable-enforce \
  constraints/gemini.disableCustomMcpServerConnector \
  --project "[PROJECT_ID]"
```
- 조직 정책 확인 콘솔 경로: 조직 정책 콘솔 ( https://console.cloud.google.com/iam-admin/orgpolicies )

### 3.3 필요 IAM 권한

| 서비스 | 필요 역할 (Role) | 최소 IAM 권한 |
| :--- | :--- | :--- |
| `Discovery Engine` | `roles/discoveryengine.editor` | `discoveryengine.dataStores.create`, `discoveryengine.dataStores.get` |
| `Cloud Run` | `roles/run.admin` | `run.services.create`, `run.services.get` |
| `Compute Engine` | `roles/compute.networkViewer` | `compute.networks.get`, `compute.subnetworks.get` |

---

## 4. 계정 공급자(IdP) 설정 및 1시간 401 장애 방지 매핑

### 4.1 계정 공급자(IdP)가 Google Identity / Google Workspace인 경우 (상세 가이드)

Google Identity를 사내 IdP로 활용하여 Gemini Enterprise 사용자를 인증할 때의 구체적인 설정 절차는 다음과 같다:

#### 1단계: Google Cloud 콘솔에서 OAuth 2.0 클라이언트 자격 증명 생성
1. Google Cloud Credentials 콘솔 ( https://console.cloud.google.com/apis/credentials )로 이동한다.
2. 상단의 **사용자 인증 정보 만들기 (Create Credentials)** 버튼을 클릭하고 **OAuth 클라이언트 ID (OAuth client ID)**를 선택한다.
3. 애플리케이션 유형으로 **웹 애플리케이션 (Web Application)**을 선택한다.
4. **승인된 리디렉션 URI (Authorized redirect URIs)** 섹션에 아래 URI를 정확히 추가한다:
   - `https://vertexaisearch.cloud.google.com/oauth-redirect`
5. 생성을 완료하고 화면에 표시되는 **클라이언트 ID (Client ID)**와 **클라이언트 보안 비밀번호 (Client Secret)**를 안전하게 보관한다.

#### 2단계: 프록시 인증 모드 설정 (`AUTH_MODE=google_tokeninfo`)
- Google OAuth 2.0이 클라이언트에 발급하는 액세스 토큰은 불투명 토큰(Opaque Token, `ya29.` 접두어로 시작) 형태다.
- 따라서 공개키(JWKS)를 통한 오프라인 서명 검증(`AUTH_MODE=jwt`)을 수행할 수 없으며, 반드시 Google Tokeninfo 엔드포인트(`https://oauth2.googleapis.com/tokeninfo`)를 통해 실시간 검증해야 한다.
- Cloud Run 프록시의 `.env` 파일에 아래와 같이 설정한다:
  ```env
  AUTH_MODE=google_tokeninfo
  UPSTREAM_MCP_URL=http://10.10.0.5:8000/mcp
  UPSTREAM_AUTH=none
  ```

#### 3단계: Gemini Enterprise 콘솔 커스텀 MCP 서버 등록 필드 값
Gemini Enterprise Data stores 콘솔 ( https://console.cloud.google.com/gemini-enterprise/data-stores )에서 아래 필드를 정확하게 입력한다:
- **MCP Server URL**: `https://[CLOUD_RUN_SERVICE_URL]/mcp` (끝에 `/mcp` 경로 필수 포함)
- **Authorization URL**: `https://accounts.google.com/o/oauth2/v2/auth`
- **Token URL**: `https://oauth2.googleapis.com/token`
- **Client ID**: 1단계에서 생성한 클라이언트 ID
- **Client Secret**: 1단계에서 생성한 클라이언트 보안 비밀번호
- **Scopes**: `openid email profile`
- **Authorization URL Parameters (필수)**: `access_type=offline&prompt=consent`
  - **장애 방지 핵심**: Google OAuth 2.0은 `access_type=offline`이 전달되지 않으면 새로 고침 토큰(Refresh Token)을 일절 발급하지 않는다. 또한 `prompt=consent`가 없으면 최초 1회 승인 이후 새로 고침 토큰 재발급을 건너뛰므로, 토큰 만료 주기인 **정확히 1시간 뒤 모든 후속 도구 호출이 401 오류로 차단**된다.

---

### 4.2 계정 공급자(IdP)가 써드파티(Okta, Entra ID, Auth0 등)인 경우

#### IdP 측 공통 등록 정보
웹 애플리케이션(Web Application) 유형의 OAuth 클라이언트를 생성할 때 아래의 리디렉션 URI를 필수로 지정해야 한다:
- **승인된 리디렉션 URI (Authorized redirect URI)**:
  `https://vertexaisearch.cloud.google.com/oauth-redirect`

#### IdP별 필수 Authorization URL Parameters (1시간 만료 방지 매핑)
Gemini Enterprise 콘솔에서 커스텀 MCP 서버를 등록할 때, `Authorization URL Parameters`를 알맞게 지정하지 않으면 새로 고침 토큰이 누락되어 1시간 뒤 서비스 단절이 발생한다:

| 계정 공급자 (IdP) | 권장 AUTH_MODE | 필수 Authorization URL Parameters | 비고 및 장애 예방 사유 |
| :--- | :--- | :--- | :--- |
| `Google Identity` | `google_tokeninfo` | `access_type=offline&prompt=consent` | `ya29.` 불투명 토큰 검증, 미지정 시 새로 고침 토큰 미발급으로 1시간 후 단절 |
| `Auth0` | `jwt` | `audience=https://your-mcp-api` | Audience 미지정 시 불투명 토큰 발급으로 JWT 서명 검증 불가 |
| `Microsoft Entra ID` | `jwt` | 지정 불필요 (또는 `prompt=consent`) | 스코프에 `offline_access` 포함 시 기본 발급 |
| `Okta` | `jwt` | 지정 불필요 | Authorization Server 설정에 따라 기본 발급 |
| `Keycloak` | `jwt` | 지정 불필요 | 스코프에 `offline_access` 추가 권장 |

---

## 5. 빠른 시작 및 실행 방법

### 단계 1: 환경 변수 설정
`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 사내 환경에 맞게 값을 기재한다:
```bash
cp .env.example .env
```

주요 설정 항목 예시 (Google Identity 사용 시):
```env
UPSTREAM_MCP_URL=http://10.10.0.5:8000/mcp
AUTH_MODE=google_tokeninfo
UPSTREAM_AUTH=none
VPC_NETWORK=projects/example-project/global/networks/default
VPC_SUBNET=projects/example-project/regions/asia-northeast3/subnetworks/default
```

주요 설정 항목 예시 (Okta / Entra ID 사용 시):
```env
UPSTREAM_MCP_URL=http://10.10.0.5:8000/mcp
AUTH_MODE=jwt
UPSTREAM_AUTH=none
OAUTH_JWKS_URL=https://idp.example.com/.well-known/jwks.json
OAUTH_AUDIENCE=gemini-enterprise-mcp
VPC_NETWORK=projects/example-project/global/networks/default
VPC_SUBNET=projects/example-project/regions/asia-northeast3/subnetworks/default
```

### 단계 2: 모의 데이터 로컬 가상 실행 (Dry-Run)
외부 IdP나 실제 업스트림 백엔드 없이 내장된 가상 토큰과 모의 검증기로 스모크 테스트를 수행한다:
```bash
./run.sh --dry-run
```

### 단계 3: Cloud Run Direct VPC Egress 자동 배포
```bash
./run.sh --deploy
```
- Direct VPC Egress 네트워크 설정 참조: Cloud Run Direct VPC Egress 공식 가이드 ( https://cloud.google.com/run/docs/configuring/vpc-direct-vpc )

배포 완료 후 터미널에 출력된 Cloud Run 서비스 URL(예: `https://gemini-enterprise-mcp-proxy-xxxx.a.run.app`)을 확인한다.

---

## 6. Gemini Enterprise 콘솔 데이터 저장소 등록 절차

Cloud Run 배포가 완료되면 Gemini Enterprise 관리 콘솔에서 사설 MCP 서버를 등록한다:

1. **콘솔 접속**:
   Gemini Enterprise Data stores 콘솔 ( https://console.cloud.google.com/gemini-enterprise/data-stores )로 이동한다.
2. **커넥터 생성**:
   **Create** 버튼 클릭 후 데이터 원본 목록에서 **Custom MCP server**를 선택한다.
3. **상세 필드 입력**:
   - **MCP Server URL**: `https://[CLOUD_RUN_SERVICE_URL]/mcp` (끝에 `/mcp` 경로 필수 포함)
   - **Authorization URL**: 4.1단계 또는 4.2단계의 IdP별 인가 엔드포인트 URL
   - **Token URL**: 4.1단계 또는 4.2단계의 IdP별 토큰 엔드포인트 URL
   - **Client ID / Secret**: 발급받은 OAuth 클라이언트 자격 증명
   - **Scopes**: `openid email profile` (사내 필요 스코프 추가)
   - **Authorization URL Parameters**: 4.1단계 및 4.2단계 표를 참조하여 IdP별 필수 파라미터 입력
4. **저장 및 연동 검증**:
   저장 완료 후 Gemini Enterprise 에이전트 대화창에서 사내 MCP 도구가 정상적으로 도구 호출(Tool Calling)되는지 확인한다.
- Model Context Protocol 사양 참조: Model Context Protocol 공식 가이드 ( https://modelcontextprotocol.io )

---

## 7. 리소스 정리 (Teardown) 안내

테스트 완료 후 클라우드 리소스 비용을 방지하기 위해 배포된 Cloud Run 서비스를 삭제한다:
```bash
gcloud run services delete gemini-enterprise-mcp-proxy \
  --project="[PROJECT_ID]" \
  --region="asia-northeast3" \
  --quiet
```

로컬 임시 설정 파일 삭제:
```bash
rm -f .env
```
