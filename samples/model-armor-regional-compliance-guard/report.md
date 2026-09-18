# 진단 및 분석 리포트: model-armor-regional-compliance-guard

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
Model Armor 서울 리전 규제 준수 정합성 진단 시작 (프로젝트: sample-project-id, 리전: asia-northeast3)
--> 가상 실행 모드 (--dry-run) 활성화: 사전 시뮬레이션 Model Armor 템플릿 데이터를 분석한다.

=========================================================================================================
템플릿 이름                           리전                 인포타입 수       프롬프트인젝션            심각도       
---------------------------------------------------------------------------------------------------------
ma-template-seoul-finance        asia-northeast3    3            ENABLED (지원불가)     CRITICAL  
ma-template-global-uncompliant   us-central1        6            ENABLED            CRITICAL  
ma-template-hybrid-hardened      asia-northeast3    6            DISABLED           HEALTHY   
=========================================================================================================

[발견된 주요 컴플라이언스 결함 및 처방 조치]

* [심각] ma-template-seoul-finance (리전: asia-northeast3)
  - 결함 원인: 서울 리전 Model Armor는 SDP만 로컬 지원하며, 활성화된 [프롬프트 인젝션/탈옥 탐지 (Prompt Injection/Jailbreak), 악성 URL 탐지 (SafeBrowsing DB 연계), 책임감 있는 AI 안전 필터 (RAI)] 필터는 서울 리전 로컬 엔진 부재로 인해 검사가 바이패스되거나 해외 리전 호출이 요구되는 사각지대 발생
  - 결함 원인: 국내 개인정보 보호법 핵심 마스킹 항목 중 [KOREA_PASSPORT, KOREA_DRIVERS_LICENSE_NUMBER, KOREA_ARN, KOREA_BRN, KOREA_NHI_NUMBER] 인포타입 설정이 누락됨
  - 처방 조치: 서울 리전 템플릿에서는 SDP(민감정보 마스킹)만 활성화하고, 프롬프트 인젝션 및 악성 URL 검사는 사내 애플리케이션 계층의 로컬 가드레일 라이브러리(Local Regex / Classifier)로 이관하는 하이브리드 파이프라인을 구축한다.
  - 처방 조치: Model Armor SDP 설정에 한국 전용 인포타입(KOREA_PASSPORT, KOREA_DRIVERS_LICENSE_NUMBER, KOREA_ARN, KOREA_BRN, KOREA_NHI_NUMBER)을 추가 바인딩한다.

* [심각] ma-template-global-uncompliant (리전: us-central1)
  - 결함 원인: 금융 규제 준수 대상 워크로드임에도 Model Armor 템플릿이 해외 리전(us-central1)에 배포되어 입력 프롬프트 및 개인정보의 국외 이전(Data Boundary 위반) 위험 발생
  - 처방 조치: Model Armor 템플릿을 서울 리전(asia-northeast3) 엔드포인트로 이전 재배포한다.
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
