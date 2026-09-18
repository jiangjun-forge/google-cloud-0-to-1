# 진단 및 분석 리포트: gemini-enterprise-governance-guard

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
Gemini Enterprise 에이전트 거버넌스 및 SSO 상태 진단 시작 (프로젝트: sample-project-id, 앱: default-enterprise-agent-app)
--> 가상 실행 모드 (--dry-run) 활성화: 사전 시뮬레이션 거버넌스 및 WIF 데이터를 분석한다.

=========================================================================================================
Gemini Enterprise 애플리케이션 거버넌스 진단 리포트 (default-enterprise-agent-app)
=========================================================================================================
거버넌스 점검 범주                       상태           진단 내용
---------------------------------------------------------------------------------------------------------
에이전트 마켓플레이스 통제                   CRITICAL     공개 에이전트 마켓플레이스 접근이 허용되어 임직원이 검증되지 않은 서드파티 에이전트에 사내 데이터를 전송할 위험 존재
사내 스킬 거버넌스                       CRITICAL     사내 미검증 외부 스킬/에이전트(third-party-web-scraper-skill, public-pdf-converter-agent)가 활성화되어 워크플로우에 결합 가능함
Workforce Identity SSO 인증        CRITICAL     WIF 풀 속성 매핑에 필수 클레임(attribute.user_email, attribute.display_name)이 누락되어 Entra ID 로그인 시 HTTP 400 오류 발생
=========================================================================================================

[발견된 거버넌스 취약점 및 권고 조치]

* [심각] 에이전트 마켓플레이스 통제
  - 위험: 공개 에이전트 마켓플레이스 접근이 허용되어 임직원이 검증되지 않은 서드파티 에이전트에 사내 데이터를 전송할 위험 존재
  - 처방: Gemini Enterprise 콘솔 [에이전트] -> [조달 및 통합 설정]에서 공개 마켓플레이스 에이전트 신청을 비활성화하고 사내 승인 에이전트만 노출하도록 제한한다.

* [심각] 사내 스킬 거버넌스
  - 위험: 사내 미검증 외부 스킬/에이전트(third-party-web-scraper-skill, public-pdf-converter-agent)가 활성화되어 워크플로우에 결합 가능함
  - 처방: Gemini Enterprise [스킬 관리] 콘솔에서 해당 외부 스킬을 즉시 일시중지(Suspend) 처리하고, 스킬 추가 시 관리자 승인 절차를 필수로 강제한다.

* [심각] Workforce Identity SSO 인증
  - 위험: WIF 풀 속성 매핑에 필수 클레임(attribute.user_email, attribute.display_name)이 누락되어 Entra ID 로그인 시 HTTP 400 오류 발생
  - 처방: GCP WIF 공급업체 매핑에 attribute.user_email='assertion.email' 및 attribute.display_name='assertion.name'을 추가하고, Entra ID 앱 등록 토큰 구성에서 email 클레임 발행을 활성화한다.
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
