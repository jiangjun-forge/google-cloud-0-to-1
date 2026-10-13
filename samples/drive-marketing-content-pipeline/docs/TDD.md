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
본 솔루션은 Google Cloud 프로젝트 및 로컬 파이썬 런타임 환경, 별도 API Key 관리에 의존하지 않는 100% 서버리스 웹 네이티브(Web-Native) 무키(Keyless) 아키텍처로 설계되었다. 사용자의 구글 스프레드시트(Google Sheets)에 바인딩된 Apps Script 엔진을 컨트롤 타워로 삼아, 구글 드라이브(Drive), 구글 독스(Docs), 구글 폼(Forms) 및 Gemini REST API를 구글 계정 OAuth 2.0 세션 기반으로 유기적으로 조율한다.

### 핵심 구성 요소 및 연동 체계
1. **Google Apps Script 런타임**:
   - 구글 시트 상단 커스텀 메뉴 (`>> 마케팅 콘텐츠 파이프라인 <<`) 제공
   - 모듈화된 11개 스크립트 로직(`Code_Config.js`, `Code_Gemini.js`, `Code_Utils.js`, `Code_Step1_Workspace.js`, `Code_Step2_IdeaToPlan.js`, `Code_Step3_ContentGen.js`, `Code_Step4_Form.js`, `Code_Step5_8_Judge.js`, `Code_Step6_Decision.js`, `Code_Step7_9_Refine.js`, `Code_Menu.js`) 및 원클릭 배포용 단일 번들(`bundle_apps_script.js`) 지원
2. **구글 계정 기반 Gemini REST 엔드포인트 직접 연동 (태스크별 최적 모델 선정, As of 2026-10-13)**:
   - `generativelanguage.googleapis.com` 호출 시 `ScriptApp.getOAuthToken()`으로 취득한 구글 로그인 계정의 OAuth 2.0 Access Token을 `Authorization: Bearer <token>` 헤더로 자동 주입하여 순수 무키(Keyless) 인증 수행
   - 단일 모델에 의존하지 않고 각 작업의 속도, 처리 용량, 비용 효율성을 고려하여 검증된 모델을 취사선택하여 연동
   - `gemini-3.8-flash`: 빠른 응답 속도와 긴 컨텍스트 처리를 위한 아이디어 구체화, PLAN 기획서 및 SPEC 명세서 컴파일, 25인 AI 페르소나 다면 평가 및 VLM 비디오 VoC 심층 분석, 복합 피드백 기반 1차(rv-01), 2차(rv-02) 콘텐츠 심층 보정
   - `gemini-2.5-flash-image`: 16:9 가로 배너, 9:16 모바일 포스터, 1:1 정방형 SNS 피드 이미지 규격에 최적화된 시각화 소재 생성
   - `veo-3.1-generate-001`: 9:16 모바일 숏폼 영상(shorts) 콘티 및 비디오 소재 생성에 적합
3. **외부 경량 시각화 및 데이터 REST API**:
   - QuickChart REST API (`https://quickchart.io/chart`): 25인 페르소나 평점 및 비디오 VoC 분석 결과를 2D t-SNE 버블 산점도 차트 이미지로 실시간 렌더링
   - Hugging Face Datasets Server REST API (`https://datasets-server.huggingface.co/rows`): 공개 데이터셋으로부터 타깃 인구통계 페르소나 데이터 직접 인출 및 표준 정규화
4. **마케터 제어 인터페이스**:
   - 스프레드시트 내 `실행 대시보드` 탭을 통한 실시간 진행 상태 모니터링 및 산출물 하이퍼링크 즉시 제공
   - 브라우저 모달 대화 상자를 통한 인간 참여형(Human-in-the-loop) 마케팅 콘텐츠 보정 지침 입력 및 즉각 반영

---

## 2. 기능적 기술 요구 사항 (Functional Requirements)

| 요구 사항 ID | 연관 BR | 기술 요구 사항 명칭 | 구현 상세 및 검증 기준 |
| :--- | :--- | :--- | :--- |
| **FR-01** | **BR-01** | **Zero-GCP 런타임 및 무키(Keyless) OAuth 2.0 자동 인증** | 별도의 API Key 발급 절차 없이, 구글 스프레드시트에 로그인된 현재 계정의 OAuth 2.0 Access Token(`ScriptApp.getOAuthToken()`)을 `Authorization: Bearer <token>` 헤더로 자동 주입하여 비개발자 마케터의 진입 장벽을 완전히 제거하고 보안성을 보장한다. |
| **FR-02** | **BR-01, BR-03** | **구글 드라이브 작업 폴더 및 리소스 자동 시딩** | Step 1 실행 시 캠페인 루트 폴더(`cp-ignite/`), `input/`, `output/` 트리를 생성하고, 스크립트 내장 데이터를 기반으로 25인 마스터 페르소나(`input/ai_personas.json`), 마케터 아이디어 초안(`input/아이디어 메모`), 비디오 VoC 샘플(`input/fb-01/feedback_sample.mp4`)을 Base64로부터 자동 복원 시딩한다. |
| **FR-03** | **BR-02** | **명세 주도 기획서(PLAN) 및 콘텐츠 제작 명세서(SPEC) 자동 도출** | Step 2에서 자연어 아이디어를 구글 독스 `PLAN` 및 `SPEC`으로 변환하여 캠페인 배경, 타깃 USP, 채널별 양산 명세(배너 16:9, 포스터 9:16, SNS 1:1, 모바일 숏폼 9:16)를 확정한다. 마케터가 `SPEC` 문서를 수정한 내용은 후속 단계에 즉시 반영된다. |
| **FR-04** | **BR-02** | **멀티 채널 마케팅 콘텐츠(카피, 이미지, 세로 숏폼 영상) 자동 양산** | Step 3에서 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC)에 따라 광고 카피 구글 독스(`campaign_content`), 3개 종횡비 이미지(`00_banner_16x9.png`, `00_poster_9x16.png`, `00_sns_1x1.png`), 그리고 세로 9:16 모바일 숏폼 영상(`00_shorts.mp4`)을 콘텐츠 폴더에 자동 생성한다. |
| **FR-05** | **BR-03** | **타깃 AI 페르소나 패널 맞춤 재설정** | 커스텀 메뉴를 통해 마케터가 특정 타깃 기준을 자연어로 입력하면 Gemini가 7대 핵심 필드(`id, name, age, gender, category, occupation, perspective`)로 정규화된 25인 패널을 즉시 합성하고, `hf:repo` 입력 시 Hugging Face REST API를 통해 실데이터를 추출하여 캠페인 전용 `input/ai_personas.json`을 갱신한다. |
| **FR-06** | **BR-04** | **구글 폼 자동 생성 및 모바일 QR 코드 바인딩** | Step 4에서 설문 문항(정량 평점, 정성 피드백, 미디어 파일 업로드)을 포함한 구글 폼을 동적 생성하고, 구글 시트 내 응답 탭 연결 및 QuickChart API 기반 모바일 접속용 QR 코드를 폼 상단에 자동 삽입한다. |
| **FR-07** | **BR-04** | **Gemini VLM 비디오 VoC 분석 및 t-SNE 지형도 렌더링** | Step 5/Step 8에서 `feedback_sample.mp4`를 Gemini 2.5 Flash VLM에 전송하여 표정, 음성 톤, 발화 내용을 `video_voc_analysis.json`으로 저장하고, 25인 페르소나 평점과 결합하여 QuickChart t-SNE 여론 지형도(`feedback_clusters_map.png`)를 생성한 뒤 종합 평가 독스(`feedback_summary`)에 자동 삽입한다. |
| **FR-08** | **BR-05** | **인간 참여형(HITL) 의사 결정 및 반자율 마케팅 콘텐츠 보정** | Step 6에서 마케터 전용 검토 모달을 띄워 보정 지침을 입력받아 `feedback_summary`에 기록하고, Step 7(rv-01) 및 Step 9(rv-02)에서 이전 평가 결과와 마케터 지침을 반영하여 카피, 비주얼 이미지, 숏폼 영상을 순차적으로 완결 보정한다. |
| **FR-09** | **BR-06** | **실시간 대시보드 상태 동기화 및 하이퍼링크 갱신** | 매 단계 완료 시 구글 시트의 `실행 대시보드` 탭에 진행 상태(`COMPLETED`, `IN_PROGRESS`) 및 생성된 구글 독스, 구글 드라이브 폴더, 구글 폼의 직접 링크를 실시간 표기한다. |

---

## 3. 비기능적 기술 요구 사항 (Non-Functional Requirements)

| 요구 사항 ID | 요구 사항 명칭 | 상세 기준 |
| :--- | :--- | :--- |
| **NFR-01** | **브라우저 실행 성능 및 타임아웃 방어** | Apps Script의 단일 실행 시간 제약(6분)을 초과하지 않도록 전체 파이프라인을 9개 독립 메뉴 단계(Step 1~Step 9)로 분할하고, 이미지 및 텍스트 생성 API 호출 시 실패 재시도 지수 백오프 로직을 적용한다. |
| **NFR-02** | **보안 및 무키(Keyless) 자격 증명 안전성** | 사용자 API Key 발급 및 수동 관리 부담을 전면 배제하고, 구글 계정 OAuth 2.0 Access Token(`Authorization: Bearer <token>` 헤더) 자동 주입 방식을 디폴트로 채택하여 자격 증명 탈취 위험을 원천 방어한다. |
| **NFR-03** | **한글 맞춤법 복합어 띄어쓰기 및 문서 표준 준수** | 모든 생성 문서(PLAN, SPEC, 피드백 보고서, 카피라이팅)와 코드 주석은 한글 맞춤법 복합 명사 띄어쓰기 규정을 철저히 준수하고, 일체의 이모지 및 중간 점을 배제한다. |
| **NFR-04** | **자원 격리 및 원클릭 무잔재 정리 (Teardown)** | 모든 산출물은 단일 캠페인 루트 폴더(`cp-ignite/`) 내에 격리 생성되어, 테스트 완료 후 해당 폴더 1개만 휴지통으로 이동하면 100% 무잔재 정리가 가능해야 한다. |
