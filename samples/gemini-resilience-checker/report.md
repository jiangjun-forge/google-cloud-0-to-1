# 진단 및 분석 리포트: gemini-resilience-checker

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
[데모 실행] --dry-run 모드가 활성화되어 가상 분석 결과를 시뮬레이션한다.
========================================================================
[진단 결과] 제미나이(Gemini) API 호출 복원력(Resilience) 진단 리포트
========================================================================

진단된 API 호출 소스 파일: 2건

[파일: app/services/llm_client.py]
  - 지수 백오프 및 재시도: [경고] 누락
  - 지터 무작위 대기 제어: [경고] 누락
  - 최대 재시도 횟수 제한: [경고] 누락
  - 폴백 모델 예외 체인  : [권장] 미적용
------------------------------------------------------------------------
[파일: batch_worker.py]
  - 지수 백오프 및 재시도: 통과
  - 지터 무작위 대기 제어: [경고] 누락
  - 최대 재시도 횟수 제한: 통과
  - 폴백 모델 예외 체인  : [권장] 미적용
------------------------------------------------------------------------

========================================================================
[추천 표준 처방 가이드 - 파이썬 tenacity 라이브러리 연동]
========================================================================
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_random_exponential

# 1. 지수 백오프, 지터, 최대 5회 재시도 제약 표준 결합 예시
@retry(
    wait=wait_random_exponential(min=1, max=60), # 지수 백오프 및 무작위성(지터) 추가
    stop=stop_after_attempt(5)                    # 최대 5회까지만 재시도 제한
)
def generate_with_retry(client, model_id, prompt):
  return client.models.generate_content(
      model=model_id,
      contents=prompt
  )

# 2. 주 모델(Gemini 2.5 Pro) 실패 시 경량 모델(Gemini 2.5 Flash)로 자동 우회
def generate_with_fallback(client, prompt):
  try:
    return generate_with_retry(client, 'gemini-2.5-pro', prompt)
  except Exception as e:
    print(f'[안내] 주 모델 호출 실패로 폴백 모델로 즉시 우회한다: {e}')
    return generate_with_retry(client, 'gemini-2.5-flash', prompt)

========================================================================
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
