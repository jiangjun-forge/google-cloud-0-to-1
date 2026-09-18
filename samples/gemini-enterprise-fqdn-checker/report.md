# 진단 및 분석 리포트: gemini-enterprise-fqdn-checker

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
Gemini Enterprise 필수 FQDN 사내망 연결성 진단 시작
--> 가상 실행 모드 (--dry-run) 활성화: 모의 방화벽 차단 시나리오를 분석한다.

=========================================================================================================
카테고리             FQDN                                       DNS    TLS/443  지연(ms)     결과        
---------------------------------------------------------------------------------------------------------
Core API         discoveryengine.googleapis.com             OK     OK       32.5       [정상]      
Core API         global-discoveryengine.googleapis.com      OK     OK       32.5       [정상]      
Core API         us-discoveryengine.googleapis.com          OK     OK       32.5       [정상]      
Core API         eu-discoveryengine.googleapis.com          OK     OK       32.5       [정상]      
Core API         content-discoveryengine.googleapis.com     OK     OK       32.5       [정상]      
Core API         vertexaisearch.cloud.google.com            OK     OK       32.5       [정상]      
Core API         discoveryengine.clients6.google.com        OK     FAIL     2005.12    [차단]      
Auth & Session   accounts.google.com                        OK     OK       32.5       [정상]      
Auth & Session   apis.google.com                            OK     OK       32.5       [정상]      
Auth & Session   auth.cloud.google.com                      OK     OK       32.5       [정상]      
Auth & Session   console.cloud.google.com                   OK     OK       32.5       [정상]      
Auth & Session   reauth.cloud.google.com                    OK     OK       32.5       [정상]      
Static Assets    www.gstatic.com                            OK     OK       32.5       [정상]      
Static Assets    ssl.gstatic.com                            FAIL   FAIL     15.42      [차단]      
Static Assets    fonts.gstatic.com                          OK     OK       32.5       [정상]      
Static Assets    fonts.googleapis.com                       OK     OK       32.5       [정상]      
User Content     lh3.googleusercontent.com                  OK     OK       32.5       [정상]      
User Content     lh4.googleusercontent.com                  OK     OK       32.5       [정상]      
User Content     lh5.googleusercontent.com                  OK     OK       32.5       [정상]      
User Content     lh6.googleusercontent.com                  OK     OK       32.5       [정상]      
=========================================================================================================

[진단 요약] 총 20개 FQDN 중 18개 정상, 2개 차단 또는 실패

[발견된 방화벽 차단 항목 및 처방]

* [심각-서비스불가] discoveryengine.clients6.google.com (카테고리: Core API, 용도: UI 렌더링, Deep Research 및 동적 에셋 처리 (필수))
  - 증상: TCP 연결 타임아웃 (방화벽 아웃바운드 443 차단 의심)
  - 처방: 본 FQDN은 Gemini Enterprise App 웹 UI 렌더링, Deep Research 및 동적 에셋 처리에 필수적이다.
         사내 방화벽 및 프록시 Allowlist에 TCP 443 아웃바운드 규칙을 즉시 추가한다.

* [심각-서비스불가] ssl.gstatic.com (카테고리: Static Assets, 용도: 보안 웹 컴포넌트 정적 라이브러리)
  - 증상: DNS 해석 실패: Name or service not known
  - 처방: 사내 방화벽 아웃바운드 규칙(TCP 443) 또는 프록시 허용 목록에 해당 FQDN을 등록한다.
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
