# 진단 및 분석 리포트: gemini-legacy-sdk-scanner

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
[데모 실행] --dry-run 모드가 활성화되어 가상 분석 결과를 시뮬레이션한다.
========================================================================
[진단 결과] 구형 제미나이(Gemini) SDK 코드 정적 진단 리포트
========================================================================

검출된 구형 SDK 사용 파일: 2건 (총 5개 라인)

[파일: app/services/chat_bot.py]
  - [1행] 구형 AI Studio SDK 임포트 (google.generativeai)
    코드: import google.generativeai as genai
  - [5행] 구형 AI Studio 설정 함수 (genai.configure)
    코드: genai.configure(api_key=os.environ['GEMINI_API_KEY'])
  - [12행] 구형 모델 객체 생성자 (genai.GenerativeModel)
    코드: model = genai.GenerativeModel('gemini-1.5-flash')
------------------------------------------------------------------------
[파일: pipelines/evaluate.py]
  - [3행] 구형 Vertex AI SDK 임포트 (vertexai.generative_models)
    코드: from vertexai.generative_models import GenerativeModel
  - [8행] 구형 모델 객체 생성자 (GenerativeModel)
    코드: model = GenerativeModel('gemini-1.5-pro')
------------------------------------------------------------------------

========================================================================
[최신 google-genai SDK 마이그레이션 가이드]
========================================================================
[패키지 설치 및 변경]
기존: pip install google-generativeai
      pip install google-cloud-aiplatform
신규: pip install google-genai

[코드 변환 예시 - Gemini Developer API 및 Vertex AI 단일 통일]
------------------------------------------------------------------------
# 1. 신규 통일 SDK 임포트 및 클라이언트 초기화
from google import genai
from google.genai import types

# API 키 기반 (AI Studio)
client = genai.Client(api_key="YOUR_API_KEY")

# 또는 GCP 프로젝트 기반 (Vertex AI)
# client = genai.Client(vertexai=True, project="YOUR_PROJECT_ID", location="us-central1")

# 2. 콘텐츠 생성 호출
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="최신 SDK 적용 테스트용 프롬프트다."
)
print(response.text)

========================================================================
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
