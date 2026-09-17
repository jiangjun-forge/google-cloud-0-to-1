# 기술 상세 설계서 (TDD): stt-lro-quota-guard

## 1. 아키텍처 개요 및 설계 원칙
본 시스템은 Speech-to-Text V2 LRO 비동기 작업 처리 시 클라이언트 SDK의 내부 폴링 주기가 유발하는 쿼터 초과 현상을 분석하는 단일 파이썬 진단 도구(`diagnose.py`)와 배시 래퍼(`run.sh`)로 구성된다.

---

## 2. 기능 요구 사항 (Functional Requirements)

### FR-01: 동시성 기반 LRO 폴링 트래픽 모델링
- 동시 작업 수 $N$에 대해 기본 SDK 폴링 호출량 $R_{default} = N \times 17 \text{ RPM}$ 및 최적화 폴링 호출량 $R_{opt} = N \times 2.5 \text{ RPM}$을 계산한다.
- 리전 기본 할당량 $Q_{limit} = 150 \text{ RPM}$ 대비 소진율을 산출하여 100% 이상 시 `CRITICAL_RISK`, 70% 이상 시 `WARNING_RISK`, 미만 시 `SAFE`로 판정한다.

### FR-02: 진단 리포트 및 RCA 출력
- `speech.googleapis.com/batch_recognize_requests`와 `speech.googleapis.com/operation_requests`를 구분한 매트릭스 표를 출력한다.
- 429 오류의 근본 원인을 설명하는 RCA 텍스트를 구성한다.

### FR-03: SDK 커스텀 Polling 코드 스니펫 자동 생성
- `google.api_core.polling.DEFAULT_POLLING.with_delay(initial=15.0, maximum=30.0, multiplier=1.5)` 적용 코드를 화면에 출력한다.

---

## 3. 비기능 요구 사항 (Non-Functional Requirements)

### NFR-01: 무버퍼링 실시간 터미널 출력
- `run.sh`에서 `export PYTHONUNBUFFERED=1`을 선언하고 파이썬 프로세스를 직결 실행하여 지연 없이 결과를 스트리밍한다.

### NFR-02: 가상 실행 모드 (--dry-run)
- 실제 클라우드 API 호출이나 권한 요구 없이 모의 계산 데이터를 통해 결과를 즉시 검증할 수 있어야 한다.

### NFR-03: 자동 탐지 우선 (Auto-Discovery First)
- CLI 인자가 생략되었을 때 gcloud 활성 프로젝트 및 리전 설정을 계층적으로 탐색하여 자동 설정한다.
