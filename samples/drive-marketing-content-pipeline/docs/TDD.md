<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 기술 상세 설계서 (TDD): 구글 드라이브 마케팅 콘텐츠 파이프라인 (`drive-marketing-content-pipeline`)

## 1. 시스템 아키텍처 및 동작 원리
본 솔루션은 Google Cloud 프로젝트 및 로컬 파이썬 런타임 환경에 의존하지 않는 100% 서버리스 웹 네이티브(Web-Native) Zero-GCP 아키텍처로 설계되었다. 사용자의 Google Sheets에 바인딩된 Apps Script 엔진을 컨트롤 타워로 삼아, Google Drive, Google Docs, Google Forms 및 Google AI Studio 무료 API Key 기반 Gemini REST API를 유기적으로 조율한다.

### 핵심 구성 요소 및 연동 체계
1. **Google Apps Script 런타임**:
   - 구글 시트 상단 액션 중심 커스텀 메뉴 (`[마케팅 콘텐츠 파이프라인]`) 제공
   - 도메인별 책임 분리 기반 8대 코어 모듈(`Code_Config.js`, `Code_Gemini.js`, `Code_Prompts.js`, `Code_Utils.js`, `Code_Workspace.js`, `Code_Content.js`, `Code_Feedback.js`, `Code_Menu.js`) 및 마케터 원클릭 배포용 단일 번들(`bundle_apps_script.js`), 초경량 무수정 부트스트랩(`bootstrap.js`), 로컬 고속 사전 검증기 지원
2. **Google AI Studio 무료 API Key 기반 Gemini REST 엔드포인트 직접 연동 (태스크별 최적 모델 선정, As of 2026-10-14)**:
   - Google Cloud 콘솔 프로젝트 및 결제 계정 등록 없이, 개인 구글 계정으로 Google AI Studio에서 무료 발급받은 API Key(`?key=...`)를 통해 `generativelanguage.googleapis.com` 엔드포인트를 직접 호출 (Zero-GCP Dependency)
   - 취득된 API Key는 Apps Script `UserProperties`에 사용자별로 안전하게 격리 보관되며, 미등록 시 대화상자 프롬프트를 통해 1회 입력받아 자동 영구 유지
   - 단일 모델에 의존하지 않고 각 작업의 속도, 처리 용량, 비용 효율성을 고려하여 검증된 모델을 취사선택하여 연동
   - `gemini-3.8-flash`: 빠른 응답 속도와 긴 컨텍스트 처리를 위한 아이디어 구체화, PLAN 기획서 및 SPEC 명세서 컴파일, 25인 AI 페르소나 다면 평가 및 VLM 비디오 VoC 심층 분석, 복합 피드백 기반 1차(rv-01), 2차(rv-02) 콘텐츠 심층 보정
   - `gemini-nano-banana-2.1`: 16:9 가로 배너, 9:16 모바일 포스터, 1:1 정방형 SNS 피드 이미지 규격에 최적화된 고효율 비주얼 소재 생성 (보조: `gemini-3.1-flash-image`, `imagen-4.0-generate-001`)
   - `veo-3.1-generate-preview`: 9:16 모바일 숏폼 영상(shorts) 콘티 기반 세로 비디오 소재 생성 (보조: `veo-3.1-fast-generate-preview`)
   - `text-multilingual-embedding-002`: 한국어 및 다국어 특화 텍스트 임베딩 모델로, 128차원 MRL(Matryoshka Representation Learning) 축소 차원을 적용하여 25인 페르소나로부터 도출된 50~80개 이상의 세부 의견 포인트를 고속 임베딩
3. **외부 경량 시각화 및 데이터 REST API**:
   - QuickChart REST API (`https://quickchart.io/chart`): 128d 임베딩 기반 PCA 2축 투영 좌표를 2D t-SNE 버블 산점도 차트 이미지(`feedback_clusters_map.png`)로 실시간 렌더링
   - Hugging Face Datasets Server REST API (`https://datasets-server.huggingface.co/rows`): 공개 데이터셋으로부터 타깃 인구통계 페르소나 데이터 직접 인출 및 표준 정규화
4. **마케터 제어 인터페이스**:
   - 구글 시트 내 `실행 대시보드` 탭을 통한 실시간 진행 상태 모니터링 및 산출물 하이퍼링크 즉시 제공
   - 브라우저 모달 대화 상자를 통한 인간 참여형(Human-in-the-loop) 마케팅 콘텐츠 보정 지침 입력 및 즉각 반영

---

## 2. 기능적 기술 요구 사항 (Functional Requirements)

| 요구 사항 ID | 연관 BR | 기술 요구 사항 명칭 | 구현 상세 및 검증 기준 |
| :--- | :--- | :--- | :--- |
| **FR-01** | **BR-01** | **Zero-GCP 런타임 및 Google AI Studio 무료 API Key 인증** | Google Cloud 프로젝트 생성이나 결제 카드 등록 없이, 개인 구글 계정으로 무료 발급받은 Google AI Studio API Key(`?key=...`)를 Apps Script `UserProperties`에 1회 등록하여 엔드포인트를 호출함으로써 비개발자 마케터의 진입 장벽을 완전히 제거하고 Zero-GCP 자율 구동을 보장한다. |
| **FR-02** | **BR-01, BR-03, BR-11, BR-13** | **구글 드라이브 작업 폴더, 루트 페르소나 및 6대 프롬프트 독스 자동 시딩** | 초기화 실행 시 캠페인 루트 폴더(`cp-ignite/`), `prompts/`, `input/`, `output/` 트리를 생성하고, 캠페인 루트 직속 25인 마스터 페르소나(`ai_personas.json`), 마케터 아이디어 초안(`input/아이디어 메모`), 6대 프롬프트 구글 독스를 자동 시딩하며, 고객 피드백 폴더(`input/fb-01/`)는 가짜 영상 없이 실제 피드백 투입 대기 상태로 구성한다. |
| **FR-03** | **BR-02** | **명세 주도 기획서(PLAN) 및 콘텐츠 제작 명세서(SPEC) 자동 도출** | [기획] 메뉴 실행 시 자연어 아이디어를 구글 독스 `PLAN` 및 `SPEC`으로 변환하여 캠페인 배경, 타깃 USP, 채널별 생성 명세(배너 16:9, 포스터 9:16, SNS 1:1, 모바일 숏폼 9:16)를 확정한다. 마케터가 `SPEC` 문서를 수정한 내용은 후속 단계에 즉시 반영된다. |
| **FR-04** | **BR-02** | **멀티 채널 마케팅 콘텐츠(카피, 이미지, 세로 숏폼 영상) 자동 생성** | [생성] 메뉴 실행 시 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC)에 따라 광고 카피 및 숏폼 영상 연출 콘티가 통합된 구글 독스(`campaign_content`), 3개 종횡비 이미지(`00_banner_16x9.png`, `00_poster_9x16.png`, `00_sns_1x1.png`), 그리고 Gemini Veo 3.1 Fast 비디오 생성 API를 호출하여 생성한 세로 9:16 모바일 숏폼 실제 영상(`00_shorts.mp4`)을 콘텐츠 폴더에 자동 생성한다. |
| **FR-05** | **BR-03** | **타깃 AI 페르소나 패널 맞춤 재설정** | 커스텀 메뉴를 통해 마케터가 특정 타깃 기준을 자연어로 입력하면 Gemini가 7대 핵심 필드(`id, name, age, gender, category, occupation, perspective`)로 정규화된 25인 패널을 즉시 합성하고, `hf:repo` 입력 시 Hugging Face REST API를 통해 실데이터를 추출하여 캠페인 루트의 `ai_personas.json`을 갱신한다. |
| **FR-06** | **BR-04, BR-13** | **Google Forms 자동 생성 및 모바일 QR 코드 바인딩 (초기화 올인원 연동)** | 초기화 실행 시 설문 문항(정량 평점, 정성 피드백, 미디어 파일 업로드)을 포함한 Google Forms를 동적 생성하고, Google Sheets 내 응답 탭 연결 및 QuickChart API 기반 모바일 접속용 QR 코드를 스프레드시트와 폼에 자동 바인딩한다. |
| **FR-07** | **BR-04, BR-07** | **25인 페르소나 128d t-SNE 지형도 렌더링 및 Gemini VLM 비디오 VoC 종합 요약서 도출** | Step 5에서 '열린 피드백(Open-ended Feedback)' 원칙에 따라 25인 페르소나로부터 다중 세부 의견 포인트를 도출하고 한국어 특화 `text-multilingual-embedding-002` 모델의 128차원 MRL 임베딩 및 PCA 2축 투영을 거쳐 QuickChart 다면 여론 지형도(`feedback_clusters_map.png`)를 생성한다. 이어 Step 6에서 실제 업로드된 동영상 VLM 분석(미제출 시 정직하게 미제출 명시 및 소설 배제), 이미지 VLM 분석, 수작업 자료를 종합하여 t-SNE 지형도가 문서 본문 가로폭에 맞추어 상단에 삽입된 피드백 종합 요약서(`feedback_summary`) 구글 독스를 자동 생성한다. |
| **FR-08** | **BR-05** | **인간 참여형(HITL) 마케터 직접 검토 및 반자율 마케팅 콘텐츠 보정** | Step 6에서 마케터가 브라우저로 `feedback_summary` 구글 독스를 직접 열어 분석 결과와 t-SNE 지형도를 검토하고 문서 하단의 마케터 최종 의사 결정 섹션을 직접 수정하며, Step 7(rv-01) 및 Step 9(rv-02)에서 수정된 마케터 지침을 최우선 반영하여 카피, 비주얼 이미지 3종, 숏폼 콘티 및 Gemini Veo 숏폼 비디오를 완결 보정한다. |
| **FR-09** | **BR-06** | **실시간 대시보드 상태 동기화 및 하이퍼링크 갱신** | 매 단계 완료 시 Google Sheets의 `실행 대시보드` 탭에 진행 상태(`COMPLETED`, `IN_PROGRESS`) 및 생성된 Google Docs, Google Drive 폴더, Google Forms의 직접 링크를 실시간 표기한다. |
| **FR-10** | **BR-08** | **고객 제출 이미지 VLM 시각 분석 및 수작업 피드백 자료 스캔 엔진** | 25MB 이하 이미지의 Base64 인코딩 및 Gemini VLM 시각 분석(`analyzeImageFeedbackWithVlm`)을 수행하고, `input/{targetRound}/` 폴더 내 시스템 예약 파일을 제외한 모든 파일(이미지, 동영상, Google Docs, 텍스트 메모)의 동적 스캔 및 구조화 데이터 추출(`scanManualFeedbackFiles`)을 지원한다. |
| **FR-11** | **BR-09** | **다이나믹 N차 회차 탐지 및 99차 무제한 피드백 루프** | Google Drive 폴더 트리를 실시간 스캔하여 최신 회차 번호를 파악(`detectLatestFeedbackRoundNum`, `detectLatestRevisionRoundNum`)하고, 사용자 대화형 UI를 통해 기본값 자동 채택 또는 1~99 범위 내 수기 입력을 처리하여 무제한 리비전 파이프라인 구동을 보장한다. |
| **FR-12** | **BR-09** | **비차단 실시간 진행 안내 토스트 시스템** | `SpreadsheetApp.getActiveSpreadsheet().toast()`를 활용(`showProcessingToast`)하여 스크립트 실행을 방해하지 않고 화면 우측 하단에 각 단계별 예상 소요 시간(초 단위)과 진행 상태를 즉각 노출하는 비차단 UX를 구현한다. |
| **FR-13** | **BR-10** | **개발자 사전 검증용 로컬 에뮬레이션 테스트 러너** | 마케터 배포 번들(`bundle_apps_script.js`)의 경량성을 완벽히 보존하기 위해 브라우저 런타임에서 테스트 코드를 전면 배제하고, 개발자가 깃 푸시 전 로컬 터미널에서 `python3 test_suite.py --all` 또는 `--unit` 명령어로 8대 단위 테스트 수이트(총 66개 항목)를 100% 모의(Mocking)하여 고속 검증할 수 있는 독립 파이썬 테스트 러너를 제공한다. |
| **FR-14** | **BR-11** | **마케터 직접 편집 가능한 6대 프롬프트 구글 독스 외부화 및 스마트 캐싱 엔진** | 6대 핵심 프롬프트(기획, 생성, 평가, 종합 보고, 보정, 비주얼)를 `prompts/` 폴더 내 구글 독스로 자동 시딩하여 마케터가 브라우저에서 직접 편집할 수 있도록 하고, Apps Script 실행 시 `CacheService`를 적용하여 문서 수정 시에만 캐시를 즉시 무효화하고 미수정 시 0.01초 만에 템플릿을 반환하는 고속 스마트 캐싱을 보장한다. |
| **FR-15** | **BR-12** | **실사용 솔루션 액션 중심 메뉴 및 선결 가드레일 체계** | 워크숍용 순차 단계를 탈피하여 초기화, 설정, 기획, 생성, 평가, 보고서, 보정 메뉴를 순서 없이 자유롭게 호출할 수 있도록 하고, 필수 선결 산출물(기획서 누락, 초판 콘텐츠 누락, 다면 평가 데이터 누락 등)이 없을 때 프로세스 멈춤 없이 친절한 모달 알럿으로 선행 작업을 안내하는 가드레일을 제공한다. |
| **FR-16** | **BR-13** | **캠페인 루트 직속 페르소나 및 구글 폼 올인원 세팅 엔진** | 초기화 한 번으로 캠페인 루트 폴더 직속에 25인 한국인 마스터 AI 페르소나 패널(`ai_personas.json`)을 즉시 배포하고, 고객 VoC 설문 폼(Google Forms) 생성, 스프레드시트 응답 탭 연결 및 모바일 QR 코드 생성을 10초 만에 완결한다. |
| **FR-17** | **BR-14** | **GitHub Raw 기반 프롬프트 및 페르소나 실시간 인출 엔진** | 초기화(`initCampaignWorkspace`, `seedDefaultPrompts`) 실행 시 GitHub 퍼블릭 저장소의 Raw 엔드포인트(`https://raw.githubusercontent.com/.../main/samples/...`)를 호출하여 `prompts/*.md` 마크다운 파일 6종과 `data/ai_personas.json`을 실시간 인출하여 구글 독스 및 파일로 자동 시딩하며, 네트워크 예외 시 내장 안전 폴백으로 전환하여 안정성을 보장한다. |
| **FR-18** | **BR-14** | **초경량 자동 갱신 부트스트랩 로더 (Dynamic Bootstrap Loader)** | 사용자가 Google Sheets Apps Script 편집기에 단 100줄의 `bootstrap.js`만 붙여넣으면, 간접 eval 및 90KB 청크 캐싱(`CacheService`) 기반 프록시 디스패처를 통해 GitHub 최신 번들 엔진을 실시간 자동 로드하여 구동함으로써 이후 기능 추가나 패치 시에도 사용자 측의 수동 코드 재배포를 완전히 불필요하게 만든다. |

---

## 3. 비기능적 기술 요구 사항 (Non-Functional Requirements)

| 요구 사항 ID | 요구 사항 명칭 | 상세 기준 |
| :--- | :--- | :--- |
| **NFR-01** | **브라우저 실행 성능 및 타임아웃 방어** | Apps Script의 단일 실행 시간 제약(6분)을 초과하지 않도록 전체 파이프라인을 9개 독립 메뉴 단계(Step 1~Step 9)로 분할하고, 이미지 및 텍스트 생성 API 호출 시 실패 재시도 지수 백오프 로직을 적용한다. |
| **NFR-02** | **보안 및 자격 증명 안전성** | 사용자 API Key는 클라이언트 코드에 하드코딩되지 않고 Apps Script의 사용자별 격리 저장소(`PropertiesService.getUserProperties()`)에 안전하게 보관되며, Google Cloud 콘솔이나 프로젝트 결제 정보 노출 위험을 원천 방어한다. |
| **NFR-03** | **한글 맞춤법 복합어 띄어쓰기 및 문서 표준 준수** | 모든 생성 문서(PLAN, SPEC, 피드백 보고서, 카피라이팅)와 코드 주석은 한글 맞춤법 복합 명사 띄어쓰기 규정을 철저히 준수하고, 일체의 이모지 및 중간 점을 배제한다. |
| **NFR-04** | **자원 격리 및 원클릭 무잔재 정리 (Teardown)** | 모든 산출물은 단일 캠페인 루트 폴더(`cp-ignite/`) 내에 격리 생성되어, 테스트 완료 후 해당 폴더 1개만 휴지통으로 이동하면 100% 무잔재 정리가 가능해야 한다. |
| **NFR-05** | **비디오 처리 제약 방어 및 Google Cloud 엔터프라이즈 확장 경로** | Apps Script의 단일 실행 시간 제한(6분) 및 `UrlFetchApp`의 페이로드 제한(최대 50MB, Base64 직렬화 시 실질 35MB)을 고려하여 브라우저 내에서는 15~30초 이내(30MB 이하) 숏폼 영상으로 크기를 사전 검증하고 초과 시 즉시 안내 예외를 반환한다. 1분 이상의 장문 인터뷰나 대용량 고해상도 영상을 다루어야 하는 엔터프라이즈 환경에서는 Google Cloud 환경으로의 이관을 위해 Google Cloud에 연락하여 전문 컨설팅을 받도록 안내한다. |

---

## 4. 개발자 사전 검증: 로컬 에뮬레이션 및 실제 구글 드라이브 라이브 E2E 테스트 러너 명세 (test_suite.py)

마케터 배포용 Apps Script 코드(`bundle_apps_script.js`)의 경량성을 완벽히 보존하기 위해, 브라우저 런타임에는 일체의 무거운 테스트 코드를 포함하지 않는다. 대신 개발자가 깃 푸시(Git Push)를 집행하기 전 로컬 환경에서 8대 오프라인 핵심 영역(총 66개 항목) 및 실제 구글 드라이브(Google Drive) REST API 기반의 종단간(E2E) 라이브 연동(8개 항목)을 포함한 총 74개 항목을 고속 검증할 수 있는 독립 파이썬 테스트 러너(`test_suite.py`)를 제공한다.

### 9대 테스트 수이트 (총 74개 항목 검증)

1. **Config & Manifest Suite (7개 검증)**:
   - Apps Script 매니페스트(`appsscript.json`) 필수 OAuth 스코프 및 런타임 버전 유효성
   - 캠페인 기본 코드(`cp-ignite`) 및 4대 서브 디렉터리 경로 상수 매핑 검증
2. **Utils & Formatting Suite (7개 검증)**:
   - 숫자 제로 패딩 포맷팅(`padZero`, 1 -> "01", 99 -> "99")
   - PCA 2축 투영 및 좌표 변환 알고리즘 수학적 정합성 검증
   - 비차단 토스트 시간 산출 로직 검증
3. **Dynamic Round Detect Suite (7개 검증)**:
   - 빈 디렉터리 초기값 탐색(`detectLatestFeedbackRoundNum` -> 1, `detectLatestRevisionRoundNum` -> 0)
   - 불규칙한 회차 폴더 혼재 시 최신 회차 번호 계산 및 다음 회차 자동 증분 추천 검증
   - 99차 극단 경계값 및 비숫자 폴더 무시 방어 로직 검증
4. **VLM & Manual Scanner Suite (11개 검증)**:
   - 지원 이미지 MIME 타입(JPEG, PNG, WEBP) 판별 및 25MB 초과 파일 차단 검증
   - 수작업 피드백 스캐너의 시스템 예약 파일(`feedback_sample.mp4` 등) 제외 및 신규 사용자 파일(이미지, 텍스트 메모, 추가 비디오) 동적 감지 검증
5. **Persona Dataset Suite (5개 검증)**:
   - 25인 마스터 페르소나 데이터셋 무결성(전문 마케터 12인, 일반 소비자 13인 구성 안배)
   - 7대 필수 필드(`id, name, age, gender, category, occupation, perspective`) 누락 여부 전수 검증
6. **Form & Judge Logic Suite (3개 검증)**:
   - 구글 폼(Google Forms) 질문 규격 및 미디어 파일 업로드 허용 확장자 검증
   - 4대 가중치(타깃 적합성, 차별성, 브랜드 일관성, 즉각 반응도) 합산 100% 검증
7. **HITL & Asset Refinement Suite (7개 검증)**:
   - 마케터 피드백 지침 텍스트 유효성 검증
   - 멀티 채널 콘텐츠 제작 명세서(배너 16:9, 포스터 9:16, SNS 1:1, 숏폼 9:16) 규격 정합성 검증
8. **Bundle Synchronization Suite (19개 검증)**:
   - 11개 코어 Apps Script 모듈 헤더 및 파일 분할 정합성 검증
   - 번들 내 7대 핵심 신규 함수(`showProcessingToast`, `analyzeImageFeedbackWithVlm`, `scanManualFeedbackFiles`, `detectLatestFeedbackRoundNum`, `detectLatestRevisionRoundNum`, `promptAndRunJudgeEvaluation`, `promptAndRunReviseAssets`) 누락 여부 전수 검증
9. **Live Google Drive & Workspace Suite (8개 검증, --live)**:
   - 실제 Google Drive API 사용자 인증 및 토큰 유효성 검증
   - 실제 구글 드라이브 임시 루트 폴더(`[LiveTest] cp-ignite-probe`) 및 `input/`, `output/` 서브 폴더 트리 생성
   - 실제 구글 시트(Google Sheets) 및 구글 독스(Google Docs) 파일 생성
   - 부모-자식 트리 관계 실시간 조회 및 메타데이터 일치 검증
   - 검증 완료 직후 테스트 리소스 자동 정리(Teardown)를 통한 구글 드라이브 잔재 0개 보장

### 로컬 터미널 실행 명령어

```bash
# 전체 8대 오프라인 에뮬레이션 수이트 일괄 실행 (0.01초 소요)
python3 test_suite.py --all

# 실제 Google Drive 및 Workspace REST API 라이브 연동 E2E 테스트 실행
python3 test_suite.py --live --token "ya29..."

# 오프라인 8대 수이트 + 실제 드라이브 라이브 연동 E2E 전수 동시 실행
python3 test_suite.py --all --live --token "ya29..."

# 특정 단위 테스트만 단독 실행
python3 test_suite.py --unit round     # 동적 회차 탐색기 검증
python3 test_suite.py --unit vlm       # VLM 분석 및 수작업 스캐너 검증
python3 test_suite.py --unit persona   # 25인 페르소나 데이터셋 규격 검증
python3 test_suite.py --unit sync      # 번들과 서브 모듈 간 동기화 검증
python3 test_suite.py --unit live      # 실제 드라이브 라이브 연동 검증
```
