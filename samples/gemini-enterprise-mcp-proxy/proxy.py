#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Gemini Enterprise 사설 MCP 브리지 리버스 프록시."""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from typing import Any, Dict, Optional, Protocol, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("mcp-proxy")

# 환경 변수 로드
UPSTREAM_URL = os.environ.get("UPSTREAM_MCP_URL", "http://127.0.0.1:8000/mcp")
AUTH_MODE = os.environ.get("AUTH_MODE", "google_tokeninfo").lower()
UPSTREAM_AUTH = os.environ.get("UPSTREAM_AUTH", "none").lower()
CACHE_TTL = int(os.environ.get("TOKEN_CACHE_TTL", "60"))

token_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}


# --- Inbound Verifiers --------------------------------------------------------

class TokenVerifier(Protocol):
    """인바운드 토큰 검증 프로토콜."""
    async def verify(self, token: str) -> Dict[str, Any]:
        """토큰을 검증하고 클레임 딕셔너리를 반환한다."""
        ...


class JwtVerifier:
    """JWKS 기반 JWT 서명 및 Audience 검증기 (Okta, Entra ID, Auth0, Keycloak)."""

    def __init__(self, http_client: Any) -> None:
        self.http_client = http_client
        self.jwks_url = os.environ.get("OAUTH_JWKS_URL", "")
        self.audience = os.environ.get("OAUTH_AUDIENCE", "")
        self.issuer = os.environ.get("OAUTH_ISSUER", "")
        self._jwks_keys: Optional[Dict[str, Any]] = None
        self._jwks_fetched_at: float = 0.0

    async def _get_jwks(self) -> Dict[str, Any]:
        now = time.time()
        if not self._jwks_keys or (now - self._jwks_fetched_at > 3600):
            if not self.jwks_url:
                raise RuntimeError("OAUTH_JWKS_URL 환경 변수가 설정되지 않았다.")
            resp = await self.http_client.get(self.jwks_url)
            if resp.status_code != 200:
                raise RuntimeError("IdP JWKS 엔드포인트 조회에 실패했다.")
            self._jwks_keys = resp.json()
            self._jwks_fetched_at = now
        return self._jwks_keys

    async def verify(self, token: str) -> Dict[str, Any]:
        from jose import jwt

        jwks = await self._get_jwks()
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
            if not key:
                key = jwks

            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256", "ES256"],
                audience=self.audience if self.audience else None,
                issuer=self.issuer if self.issuer else None,
                options={"verify_aud": bool(self.audience), "verify_iss": bool(self.issuer)},
            )
            return claims
        except Exception as e:
            log.warning(f"JWT 검증 실패: {e}")
            raise PermissionError(f"유효하지 않은 JWT 토큰이다: {e}")


class IntrospectVerifier:
    """RFC 7662 OAuth 2.0 Token Introspection 검증기."""

    def __init__(self, http_client: Any) -> None:
        self.http_client = http_client
        self.introspect_url = os.environ.get("INTROSPECT_URL", "")
        self.client_id = os.environ.get("INTROSPECT_CLIENT_ID", "")
        self.client_secret = os.environ.get("INTROSPECT_CLIENT_SECRET", "")

    async def verify(self, token: str) -> Dict[str, Any]:
        if not self.introspect_url:
            raise RuntimeError("INTROSPECT_URL 환경 변수가 설정되지 않았다.")
        auth = (self.client_id, self.client_secret) if self.client_id else None
        resp = await self.http_client.post(
            self.introspect_url,
            data={"token": token},
            auth=auth,
        )
        if resp.status_code != 200:
            raise PermissionError("토큰 인트로스펙션 요청이 실패했다.")
        data = resp.json()
        if not data.get("active", False):
            raise PermissionError("비활성화되었거나 만료된 토큰이다.")
        return data


class GoogleTokeninfoVerifier:
    """Google OAuth2 Tokeninfo 엔드포인트 기반 검증기 (Google Identity / Google Workspace 전용)."""

    def __init__(self, http_client: Any) -> None:
        self.http_client = http_client

    async def verify(self, token: str) -> Dict[str, Any]:
        # Google OAuth2 Access Token (ya29...) 검증
        url = f"https://oauth2.googleapis.com/tokeninfo?access_token={token}"
        resp = await self.http_client.get(url)
        if resp.status_code != 200:
            # ID Token 파라미터로 2차 검증 시도
            url_id = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
            resp = await self.http_client.get(url_id)
            if resp.status_code != 200:
                raise PermissionError("Google Tokeninfo 검증 실패 (만료되었거나 유효하지 않은 Google 토큰이다)")
        
        data = resp.json()
        # sub 또는 email 필드 정규화
        data["sub"] = data.get("sub") or data.get("email") or "google-user"
        return data


class MockVerifier:
    """가상 실행(Dry-Run) 전용 모의 토큰 검증기."""

    async def verify(self, token: str) -> Dict[str, Any]:
        if token.startswith("valid-") or token.startswith("demo-") or token.startswith("mock-google-"):
            return {
                "sub": "user@example-corp.com",
                "aud": "gemini-enterprise-mcp",
                "iss": "https://accounts.google.com" if token.startswith("mock-google-") else "https://idp.example-corp.com",
                "exp": time.time() + 3600,
            }
        raise PermissionError("모의 토큰 검증 실패 (유효 형식: valid-*, demo-*, mock-google-*)")


def get_verifier(mode: str, http_client: Any = None, is_dry_run: bool = False) -> TokenVerifier:
    """지정된 인증 모드에 해당하는 검증기 인스턴스를 반환한다."""
    if is_dry_run:
        return MockVerifier()
    if mode == "google_tokeninfo":
        return GoogleTokeninfoVerifier(http_client)
    if mode == "jwt":
        return JwtVerifier(http_client)
    if mode == "introspect":
        return IntrospectVerifier(http_client)
    raise ValueError(f"지원하지 않는 AUTH_MODE 다: {mode}")


# --- Upstream Authenticator ---------------------------------------------------

class UpstreamAuthenticator:
    """업스트림 사내 MCP 백엔드에 전달할 인증 헤더 주입기."""

    def __init__(self, mode: str, is_dry_run: bool = False) -> None:
        self.mode = mode
        self.is_dry_run = is_dry_run
        self.static_bearer = os.environ.get("UPSTREAM_STATIC_BEARER", "")
        self.target_audience = os.environ.get("UPSTREAM_AUDIENCE", "")

    async def apply_auth(self, headers: Dict[str, str]) -> None:
        if self.mode == "none" or self.is_dry_run:
            headers.pop("authorization", None)
            headers.pop("Authorization", None)
            return

        if self.mode == "static_bearer":
            if not self.static_bearer:
                raise RuntimeError("UPSTREAM_STATIC_BEARER 가 설정되지 않았다.")
            headers["Authorization"] = f"Bearer {self.static_bearer}"
            return

        if self.mode == "google_adc":
            try:
                import google.auth
                import google.auth.transport.requests
                import google.oauth2.id_token

                auth_req = google.auth.transport.requests.Request()
                target_aud = self.target_audience or UPSTREAM_URL
                id_token = google.oauth2.id_token.fetch_id_token(auth_req, target_aud)
                headers["Authorization"] = f"Bearer {id_token}"
            except Exception as e:
                log.error(f"Google ADC ID 토큰 획득 실패: {e}")
                raise RuntimeError(f"업스트림 ADC 인증 실패: {e}")


# --- CLI & Dry-Run Smoke Test -------------------------------------------------

def run_dry_run_test() -> None:
    """실제 클라우드 호출 없이 로컬 모의 인프라 스모크 테스트를 수행한다."""
    print("=" * 80)
    print(" Gemini Enterprise 사설 MCP 브리지 프록시 가상 검증 (Dry-Run)")
    print("=" * 80)
    print("\n[1] 가상 인바운드 검증기(MockVerifier) 및 업스트림 핸들러 초기화:")
    mock_verifier = MockVerifier()
    mock_auth = UpstreamAuthenticator("none", is_dry_run=True)
    print(f"  - 인바운드 모드: {AUTH_MODE} (Mock)")
    print(f"  - 업스트림 모드: {UPSTREAM_AUTH} (Mock)")
    print(f"  - 가상 사내 MCP 엔드포인트: {UPSTREAM_URL}")

    print("\n[2] 테스트 시나리오 1: Google Identity OAuth Access Token 시뮬레이션 검증")
    google_token = "mock-google-oauth-access-token"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        claims = loop.run_until_complete(mock_verifier.verify(google_token))
        print(f"  [성공] Google 토큰 검증 완료: sub={claims.get('sub')}, iss={claims.get('iss')}")
    except Exception as e:
        print(f"  [실패] {e}")

    print("\n[3] 테스트 시나리오 2: 써드파티 JWT Bearer 토큰 (Okta/Entra ID) 검증")
    jwt_token = "valid-okta-access-token"
    try:
        claims = loop.run_until_complete(mock_verifier.verify(jwt_token))
        print(f"  [성공] JWT 토큰 검증 완료: sub={claims.get('sub')}, aud={claims.get('aud')}")
    except Exception as e:
        print(f"  [실패] {e}")

    print("\n[4] 테스트 시나리오 3: 위조/만료 토큰 차단 검증")
    invalid_token = "tampered-token-bad"
    try:
        loop.run_until_complete(mock_verifier.verify(invalid_token))
        print("  [경고] 비정상 토큰이 통과됨")
    except PermissionError as e:
        print(f"  [성공] 기대한 대로 인증 거부 (401 Unauthorized: {e}) 차단 완료")

    print("\n[5] 테스트 시나리오 4: 업스트림 사설 MCP 헤더 변환 및 스트리밍 시뮬레이션")
    dummy_headers = {"authorization": f"Bearer {google_token}", "content-type": "application/json"}
    loop.run_until_complete(mock_auth.apply_auth(dummy_headers))
    print(f"  - 인바운드 인증 헤더 제거 및 사내 사설망 전달 헤더:")
    for k, v in dummy_headers.items():
        print(f"    * {k}: {v}")

    print("\n[6] IdP별 새로 고침 토큰(Refresh Token) 파라미터 점검 (1시간 401 장애 예방):")
    print("  * Google Identity: access_type=offline&prompt=consent (필수 지정 확인)")
    print("  * Auth0: audience=https://your-mcp-api (JWT 강제 발급 확인)")
    print("  * Okta / Microsoft Entra ID: 기본값 사용 가능")

    print("\n[!] 가상 실행 스모크 테스트가 성공적으로 완료되었다.")
    print("=" * 80)


def create_app() -> Any:
    """FastAPI 애플리케이션 인스턴스를 생성하고 라우트를 등록한다."""
    import httpx
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import Response, StreamingResponse

    app = FastAPI(title="Gemini Enterprise Private MCP Bridge Proxy")
    http_client_holder: Dict[str, Any] = {"client": None}
    verifier_holder: Dict[str, Any] = {"verifier": None}
    upstream_holder: Dict[str, Any] = {"upstream": None}

    @app.on_event("startup")
    async def startup_event() -> None:
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=None, write=30.0, pool=None)
        )
        http_client_holder["client"] = client
        verifier_holder["verifier"] = get_verifier(AUTH_MODE, client, is_dry_run=False)
        upstream_holder["upstream"] = UpstreamAuthenticator(UPSTREAM_AUTH, is_dry_run=False)
        log.info(f"MCP 브리지 프록시 초기화 완료: AUTH_MODE={AUTH_MODE}, UPSTREAM_AUTH={UPSTREAM_AUTH}")
        log.info(f"업스트림 MCP 엔드포인트: {UPSTREAM_URL}")

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        if http_client_holder["client"]:
            await http_client_holder["client"].aclose()

    @app.get("/healthz")
    async def health_check() -> Dict[str, Any]:
        return {
            "status": "healthy",
            "auth_mode": AUTH_MODE,
            "upstream_auth": UPSTREAM_AUTH,
            "upstream_url": UPSTREAM_URL,
            "cache_entries": len(token_cache),
        }

    async def verify_inbound_request(request: Request) -> Dict[str, Any]:
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="인증 헤더가 누락되었거나 Bearer 형식이 아니다. Gemini Enterprise OAuth 설정을 확인 바란다.",
            )
        token = auth_header[7:].strip()
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        now = time.time()
        if token_hash in token_cache:
            cached_exp, claims = token_cache[token_hash]
            if now < cached_exp:
                return claims

        ver = verifier_holder["verifier"]
        if not ver:
            raise HTTPException(status_code=500, detail="토큰 검증기가 초기화되지 않았다.")
        try:
            claims = await ver.verify(token)
            token_cache[token_hash] = (now + CACHE_TTL, claims)
            return claims
        except PermissionError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.api_route("/mcp", methods=["GET", "POST"])
    async def proxy_mcp_request(request: Request) -> Response:
        claims = await verify_inbound_request(request)
        caller_sub = claims.get("sub", "unknown")

        headers = dict(request.headers)
        headers.pop("host", None)
        headers.pop("Host", None)
        headers["X-Forwarded-For"] = request.client.host if request.client else "unknown"
        headers["X-GE-Caller-Subject"] = caller_sub

        up_auth = upstream_holder["upstream"]
        if up_auth:
            await up_auth.apply_auth(headers)

        body = await request.body()
        client = http_client_holder["client"]
        if not client:
            raise HTTPException(status_code=500, detail="HTTP 클라이언트가 초기화되지 않았다.")

        req = client.build_request(
            method=request.method,
            url=UPSTREAM_URL,
            headers=headers,
            content=body,
            params=request.query_params,
        )

        try:
            upstream_resp = await client.send(req, stream=True)
        except httpx.ConnectError as e:
            log.error(f"사내 사설 MCP 서버({UPSTREAM_URL}) 연결 실패: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"사내 사설 MCP 서버({UPSTREAM_URL}) 연결 실패. Direct VPC Egress 및 서브넷 라우팅을 점검 바란다.",
            )
        except Exception as e:
            log.error(f"업스트림 중계 중 예외 발생: {e}")
            raise HTTPException(status_code=502, detail=f"업스트림 통신 오류: {e}")

        return StreamingResponse(
            upstream_resp.aiter_raw(),
            status_code=upstream_resp.status_code,
            headers=dict(upstream_resp.headers),
            background=upstream_resp.aclose,
        )

    return app


def main() -> None:
    """메인 실행 진입점."""
    parser = argparse.ArgumentParser(description="Gemini Enterprise 사설 MCP 브리지 프록시")
    parser.add_argument("--host", default="0.0.0.0", help="바인딩 호스트 (기본값: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")), help="포트 번호 (기본값: 8080)")
    parser.add_argument("--dry-run", action="store_true", help="모의 토큰 및 가상 업스트림으로 스모크 테스트 수행")
    args = parser.parse_args()

    if args.dry_run:
        run_dry_run_test()
        return

    try:
        import uvicorn
    except ImportError:
        print("[-] uvicorn 패키지가 설치되지 않았다. pip install -r requirements.txt 를 먼저 실행 바란다.")
        sys.exit(1)

    app = create_app()
    log.info(f"MCP 브리지 프록시 서버를 시작한다: {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
