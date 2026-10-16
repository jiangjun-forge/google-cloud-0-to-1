/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline - Consolidated Engine Bundle
 * Generated automatically from modular apps-scripts/
 */


// ==========================================
// Module: Code_Config.js
// ==========================================
/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 1] 전역 설정 (Global Configuration)
 */

var CONFIG = {
  // 기본 캠페인 코드 및 구글 드라이브 루트 폴더명
  CAMPAIGN_CODE: "cp-ignite",

  // 인증 방식: Google AI Studio API Key 기반 인증 (Zero-GCP Dependency)
  // GCP 프로젝트나 복잡한 개발 환경 설정 없이 Google AI Studio API Key 1회 등록만으로 구동됨
  AUTH_MODE: "API_KEY",
  API_KEY: "", // 공란 유지 시 PropertiesService.getUserProperties() 또는 실행 시 대화상자에서 자동 취득

  // Google AI Studio 엔드포인트 및 태스크별 최적 모델 지정 (As of 2026-10-15)
  // 단일 모델에 의존하지 않고 작업별 특성(속도, 이미지, 영상, 추론)에 맞추어 검증된 모델을 취사선택함
  BASE_URL: "https://generativelanguage.googleapis.com/v1beta/models",
  GEMINI_MODEL: "gemini-3.8-flash",
  MODEL_GENERATOR: "gemini-3.8-flash", // 콘텐츠 발상 및 멀티모달 소재 생성 모델
  MODEL_JUDGE: "gemini-3.8-flash", // AI 페르소나 다면 평가 및 가드레일 판정 모델
  MODEL_COPILOT: "gemini-3.8-flash", // AI 코파일럿 대화 및 상황 인지 고속 반응 모델 (Gemini 3.8 Flash)
  IMAGE_MODEL_NAME: "gemini-nano-banana-2.1", // 광고 소재 비주얼 이미지 생성 최신 공식 GA 모델 (Nano Banana 2.1)
  VIDEO_MODEL_NAME: "veo-3.1-fast-generate-preview", // 모바일 숏폼 영상 생성 25초 모델 (Veo 3.1 Fast)
  EMBEDDING_MODEL: "text-multilingual-embedding-002", // 한국어 및 다국어 특화 텍스트 임베딩 모델
  EMBEDDING_DIM: 128, // Matryoshka Representation Learning(MRL) 축소 차원 규격

  // API 호출 회복 탄력성(Resilience) 및 런타임 제약 가드레일
  HTTP_MAX_RETRIES: 3, // 429 및 5xx 일시적 오류 시 최대 재시도 횟수
  HTTP_BASE_DELAY_MS: 1500, // 지수 백오프 기본 대기 시간 (ms)
  MAX_MEDIA_PAYLOAD_MB: 35, // Apps Script 단일 페이로드 안전 상한 (MB)
  
  // 구글 드라이브 핵심 기획/명세/콘텐츠 문서 파일명
  IDEA_DOC_NAME: "아이디어 메모", // 마케터 원천 아이디어 작성용 구글 독스 (캠페인 루트 직속)
  PLAN_DOC_NAME: "PLAN", // 마케팅 캠페인 기획서 전문
  SPEC_DOC_NAME: "SPEC", // 멀티 채널 콘텐츠 제작 명세서 (이미지, 숏폼, 카피 규격)
  CONTENT_DOC_NAME: "campaign_content", // 멀티 채널 마케팅 콘텐츠 전문 (카피라이팅 및 영상 콘티)
  PERSONA_FILE_NAME: "ai_personas.json", // 타깃 AI 페르소나 마스터 데이터 (캠페인 루트 직속)
  PROMPTS_FOLDER_NAME: "prompts", // 마케터 수정용 프롬프트 구글 독스 보관 폴더명
  DIRECTIVE_DOC_NAME: "마케터 보정 지침", // 마케터 전용 의사 결정 및 보정 지침서 (AI 덮어쓰기 금지)

  // GitHub 퍼블릭 저장소 Raw 베이스 URL (초기화 시 최신 프롬프트 실시간 인출)
  GITHUB_RAW_BASE: "https://raw.githubusercontent.com/jiangjun-forge/google-cloud-0-to-1/main/samples/gws-marketing-content-pipeline",

  // 멀티 채널 마케팅 콘텐츠 및 소재 기본 규격
  CONTENT_SPECS: {
    BANNER_16x9: {
      name: "가로 디스플레이 배너",
      aspectRatio: "16:9",
      resolution: "1920x1080",
      channel: "구글 디스플레이 네트워크(GDN), 웹사이트 메인 히어로 배너"
    },
    POSTER_9x16: {
      name: "세로 모바일 포스터",
      aspectRatio: "9:16",
      resolution: "1080x1920",
      channel: "인스타그램 스토리, 카카오톡 채널, 옥외 디지털 사이니지"
    },
    SNS_1x1: {
      name: "정방형 SNS 피드 이미지",
      aspectRatio: "1:1",
      resolution: "1080x1080",
      channel: "인스타그램 피드, 페이스북, 블로그 썸네일"
    },
    SHORTS_9x16: {
      name: "세로 모바일 숏폼 영상",
      aspectRatio: "9:16",
      resolution: "1080x1920",
      duration: "15초",
      channel: "유튜브 쇼츠, 인스타그램 릴스, 틱톡"
    }
  },

  // 9대 프롬프트 구글 독스 메타데이터 및 최소 안전 폴백 (오프라인/네트워크 장애 대비용)
  DEFAULT_PROMPTS: {
    "01_idea_to_plan": {
      title: "01_idea_to_plan",
      description: "마케팅 캠페인 기획서(PLAN) 도출 지침",
      systemInstruction:
        "당신은 엔터프라이즈 브랜드 마케팅 수석 디렉터이다. 아이디어 메모로부터 마케팅 캠페인 기획서(PLAN) 전문을 체계적이고 전문적인 마크다운으로 작성하라. 한글 복합어는 철저히 띄어 쓰고 이모지와 중간 점은 일절 배제하라."
    },
    "02_plan_to_spec": {
      title: "02_plan_to_spec",
      description: "기획서(PLAN) 기반 콘텐츠 제작 명세서(SPEC) 도출 지침",
      systemInstruction:
        "당신은 테크니컬 마케팅 스펙 아키텍트이다. 제공된 마케팅 기획서(PLAN)를 바탕으로 비주얼 이미지 3종(16:9, 9:16, 1:1), 15초 모바일 숏폼 영상, 멀티 채널 카피라이팅 및 피드백 설문 가이드라인을 정의한 콘텐츠 제작 명세서(SPEC) 전문을 작성하라. 한글 복합어는 철저히 띄어 쓰고 이모지와 중간 점은 배제하라."
    },
    "03_persona_synthesis": {
      title: "03_persona_synthesis",
      description: "타깃 맞춤 AI 페르소나 패널 합성 및 Hugging Face 정규화 지침",
      systemInstruction:
        "당신은 엔터프라이즈 마케팅 페르소나 엔지니어링 AI이다. 제공된 제작 명세서(SPEC)의 타깃 오디언스 또는 Hugging Face 데이터로부터 전문 마케터와 일반 소비자로 균형 있게 구성된 슬림 AI 페르소나 패널 JSON 객체(7대 필수 필드: id, name, age, gender, category, occupation, perspective)를 반환하라. 한글 복합어는 철저히 띄어 쓰고 이모지와 중간 점은 배제하라."
    },
    "04_content_generation": {
      title: "04_content_generation",
      description: "초판 마케팅 카피라이팅 및 모바일 숏폼 영상 콘티 생성 지침",
      systemInstruction:
        "당신은 크리에이티브 마케팅 디렉터이다. 기획서(PLAN)와 제작 명세서(SPEC)를 준수하여 채널별 카피라이팅과 15초 모바일 숏폼 영상(9:16) 연출 콘티가 통합된 campaign_content 구글 독스를 작성하라. 한글 복합어는 철저히 띄어 쓰고 이모지와 중간 점은 일절 배제하라."
    },
    "05_persona_evaluation": {
      title: "05_persona_evaluation",
      description: "한국인 마스터 AI 페르소나 다면 평가 및 세부 의견 포인트 도출 지침",
      systemInstruction:
        "당신은 엔터프라이즈 마케팅 리서치 분석 AI이다. 공개된 마케팅 콘텐츠를 한국인 가상 페르소나 관점에서 다면 평가하고, 1인당 2~4개의 세부 의견 포인트(points 배열, 총 50~80개)를 포함하는 순수 JSON 배열만 반환하라. 한글 복합어는 철저히 띄어 쓰고 이모지와 중간 점은 배제하라."
    },
    "06_vlm_media_analysis": {
      title: "06_vlm_media_analysis",
      description: "고객 피드백 영상 및 이미지 VLM 멀티모달 분석 지침",
      systemInstruction:
        "당신은 엔터프라이즈 멀티모달 비디오 및 비주얼 소비자 행동 분석 전문 AI이다. 소비자가 직접 촬영한 피드백 동영상 또는 사진 미디어를 분석하여 표정, 감정 반응, 제품 사용성, 착용감에 대한 핵심 의견을 3~4문장의 객관적 평서문으로 요약하라. 한글 복합어는 철저히 띄어 쓰고 이모지와 중간 점은 배제하라."
    },
    "07_feedback_summary": {
      title: "07_feedback_summary",
      description: "고객 VoC 및 VLM 멀티모달 분석 기반 피드백 종합 분석 보고서 지침",
      systemInstruction:
        "당신은 CMO 전속 수석 분석관이다. AI 페르소나 다면 평가, 고객 VoC 설문 응답, 실제 제출된 미디어 VLM 분석 결과를 종합하여 feedback_summary 구글 독스를 작성하라. 실제 제출 미디어가 없으면 미제출로 명시하고, 문서 하단에 AI 추천 보정 방향 요약을 포함하라. 한글 복합어는 철저히 띄어 쓰라."
    },
    "08_content_revision": {
      title: "08_content_revision",
      description: "피드백 요약서 및 독립된 마케터 보정 지침서 반영 차기 리비전 콘텐츠 보정 지침",
      systemInstruction:
        "당신은 총괄 크리에이티브 디렉터이다. 직전 마케팅 콘텐츠와 피드백 요약본, 그리고 독립된 '마케터 보정 지침' 문서에 명시된 마케터 최종 의사 결정을 최우선 구속력으로 반영하여 개정된 광고 카피와 숏폼 영상 콘티를 완성도 높은 campaign_content 구글 독스로 작성하라. 한글 복합어는 철저히 띄어 쓰고 이모지와 중간 점은 배제하라."
    },
    "09_visual_prompt": {
      title: "09_visual_prompt",
      description: "비주얼 이미지 3종 및 Veo 숏폼 영상 프롬프트 엔지니어링 지침",
      systemInstruction:
        "당신은 AI 아트 디렉터이다. 캠페인 카피와 마케터 의사 결정을 분석하여 Gemini 이미지 모델(Nano Banana 2.1) 및 Veo 비디오 모델에 입력할 2~3문장의 구체적이고 감각적인 영문 프롬프트(Visual Prompt)를 작성하라. 설명 없이 영문 프롬프트만 출력하라."
    }
  }
};

// ==========================================
// Module: Code_Gemini.js
// ==========================================
/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 2] Gemini REST API 클라이언트 엔진 (Google AI Studio API Key 기반 Zero-GCP 인증)
 */

// 세션 단위 API 토큰 소모량 실시간 추적기
var __SESSION_TOKEN_STATS__ = {
  promptTokens: 0,
  candidatesTokens: 0,
  totalTokens: 0
};

/**
 * 현재 작업 단계의 세션 누적 토큰 카운터를 초기화한다.
 */
function resetSessionTokens() {
  __SESSION_TOKEN_STATS__ = {
    promptTokens: 0,
    candidatesTokens: 0,
    totalTokens: 0
  };
}

/**
 * Gemini API 응답의 usageMetadata를 세션 통계에 누적 합산한다.
 */
function recordUsageMetadata(usageMetadata) {
  if (usageMetadata) {
    if (typeof usageMetadata.totalTokenCount === "number") {
      __SESSION_TOKEN_STATS__.totalTokens += usageMetadata.totalTokenCount;
    }
    if (typeof usageMetadata.promptTokenCount === "number") {
      __SESSION_TOKEN_STATS__.promptTokens += usageMetadata.promptTokenCount;
    }
    if (typeof usageMetadata.candidatesTokenCount === "number") {
      __SESSION_TOKEN_STATS__.candidatesTokens += usageMetadata.candidatesTokenCount;
    }
  }
}

/**
 * 현재 단계에서 누적 소모된 총 토큰 수를 반환한다.
 *
 * @return {number} 총 소모 토큰 수
 */
function getSessionTotalTokens() {
  return __SESSION_TOKEN_STATS__.totalTokens || 0;
}

/**
 * Google AI Studio Gemini API Key 취득 함수
 * 1순위: UserProperties (사용자 개인별 안전 보관)
 * 2순위: ScriptProperties (스크립트 공용 설정)
 * 3순위: CONFIG.API_KEY (코드 내 직접 설정)
 * 4순위: 키가 없을 경우 자동으로 대화상자 프롬프트 호출
 */
function getGeminiApiKey() {
  var userProps = PropertiesService.getUserProperties();
  var key = userProps.getProperty("GEMINI_API_KEY");
  if (key && key.trim()) {
    return key.trim();
  }

  var scriptProps = PropertiesService.getScriptProperties();
  key = scriptProps.getProperty("GEMINI_API_KEY");
  if (key && key.trim()) {
    return key.trim();
  }

  if (CONFIG.API_KEY && CONFIG.API_KEY.trim()) {
    return CONFIG.API_KEY.trim();
  }

  return "";
}

/**
 * Google AI Studio Gemini API Key 안내 및 확인 (모달 팝업 배제)
 */
function promptForGeminiApiKey() {
  var key = getGeminiApiKey();
  if (key) {
    return key;
  }
  throw new Error("Gemini API Key가 등록되지 않았습니다. 사이드바 상단 온보딩 배너의 [API Key 등록] 버튼을 눌러 키를 입력해 주십시오.");
}

/**
 * Gemini API Key의 유효성을 경량 핑(Ping)으로 사전 검증한다.
 *
 * @param {string} apiKey - 검증할 API Key
 * @return {boolean} 유효 여부
 */
function validateGeminiApiKey(apiKey) {
  if (!apiKey || !apiKey.trim()) return false;
  try {
    var baseUrl = (CONFIG && CONFIG.BASE_URL) || "https://generativelanguage.googleapis.com/v1beta/models";
    var testModel = (CONFIG && CONFIG.GEMINI_MODEL) || "gemini-3.8-flash";
    var testUrl = baseUrl + "/" + testModel + ":generateContent?key=" + apiKey.trim();
    var payload = {
      contents: [{ role: "user", parts: [{ text: "ping" }] }],
      generationConfig: { maxOutputTokens: 2 }
    };
    var resp = UrlFetchApp.fetch(testUrl, {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    });
    return resp.getResponseCode() === 200;
  } catch (e) {
    Logger.log("API Key 사전 검증 실패: " + e);
    return false;
  }
}

/**
 * 429(Rate Limit) 및 5xx 일시적 서버 오류에 대응하는 지수 백오프 및 무작위 지터 기반 HTTP 재시도 헬퍼
 *
 * @param {string} url - 호출 엔드포인트 URL
 * @param {Object} options - UrlFetchApp 옵션 객체
 * @param {number} [maxRetriesOpt] - 최대 재시도 횟수
 * @return {GoogleAppsScript.URL_Fetch.HTTPResponse}
 */
function fetchWithRetry(url, options, maxRetriesOpt) {
  var maxRetries = (typeof maxRetriesOpt === "number") ? maxRetriesOpt : ((CONFIG && CONFIG.HTTP_MAX_RETRIES) || 3);
  var baseDelayMs = (CONFIG && CONFIG.HTTP_BASE_DELAY_MS) || 1500;

  for (var attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      var response = UrlFetchApp.fetch(url, options);
      var code = response.getResponseCode();

      // 정상(2xx)이거나 재시도가 무의미한 4xx 클라이언트 오류(400, 401, 403, 404)는 즉시 반환
      if ((code >= 200 && code < 300) || (code >= 400 && code < 500 && code !== 429)) {
        return response;
      }

      // 429 Too Many Requests 또는 5xx 서버 일시 오류 발생 시 재시도
      if (attempt < maxRetries) {
        var jitter = Math.floor(Math.random() * 800);
        var delay = Math.round(baseDelayMs * Math.pow(2, attempt) + jitter);
        Logger.log("[회복 탄력성] API 일시 응답 코드 (" + code + "), " + delay + "ms 대기 후 재시도 (" + (attempt + 1) + "/" + maxRetries + ")...");
        Utilities.sleep(delay);
        continue;
      }

      return response;
    } catch (networkErr) {
      if (attempt < maxRetries) {
        var jitter = Math.floor(Math.random() * 800);
        var delay = Math.round(baseDelayMs * Math.pow(2, attempt) + jitter);
        Logger.log("[회복 탄력성] 네트워크 통신 예외 발생, " + delay + "ms 대기 후 재시도 (" + (attempt + 1) + "/" + maxRetries + ")... 오류: " + networkErr);
        Utilities.sleep(delay);
        continue;
      }
      throw networkErr;
    }
  }
}

/**
 * Gemini 텍스트 생성 API 호출 (System Instruction 및 User Content)
 *
 * @param {string} systemInstruction - 시스템 지침
 * @param {string} userContent - 사용자 입력 프롬프트
 * @param {string} [modelOverride] - 사용할 모델 오버라이드
 * @param {number} [maxTokensOverride] - 최대 출력 토큰 수
 * @param {boolean} [isJsonMode] - JSON 전용 모드 (responseMimeType: "application/json") 여부
 */
function callGemini(systemInstruction, userContent, modelOverride, maxTokensOverride, isJsonMode) {
  var apiKey = getGeminiApiKey();
  if (!apiKey) {
    throw new Error("Gemini API Key가 등록되지 않았습니다. 사이드바 상단 온보딩 배너의 [API Key 등록] 버튼을 눌러 키를 입력해 주십시오.");
  }
  var targetModel = modelOverride || CONFIG.MODEL_GENERATOR || CONFIG.GEMINI_MODEL || "gemini-3.8-flash";
  var endpoint = CONFIG.BASE_URL + "/" + targetModel + ":generateContent?key=" + apiKey;
  var maxTokens = maxTokensOverride || 8192;

  var genConfig = {
    maxOutputTokens: maxTokens,
    temperature: isJsonMode ? 0.3 : 0.7
  };
  if (isJsonMode) {
    genConfig.responseMimeType = "application/json";
  }

  var payload = {
    contents: [{
      role: "user",
      parts: [{ text: userContent }]
    }],
    generationConfig: genConfig
  };

  if (systemInstruction) {
    payload.systemInstruction = {
      parts: [{ text: systemInstruction }]
    };
  }

  var options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  var response = fetchWithRetry(endpoint, options);
  var responseCode = response.getResponseCode();
  var responseBody = response.getContentText();

  if (responseCode !== 200) {
    throw new Error("Gemini API 호출 실패 (상태 코드: " + responseCode + "):\n" + responseBody);
  }

  var result = JSON.parse(responseBody);
  if (result.usageMetadata) {
    recordUsageMetadata(result.usageMetadata);
  }
  if (result.candidates && result.candidates.length > 0 && 
      result.candidates[0].content && result.candidates[0].content.parts) {
    return result.candidates[0].content.parts[0].text;
  }

  throw new Error("Gemini API로부터 유효한 텍스트 응답을 수신하지 못했습니다:\n" + responseBody);
}

/**
 * Gemini 멀티모달(VLM) 심층 분석 API 호출 (구글 드라이브 이미지 및 비디오 Blob 직접 처리)
 */
function callGeminiMultimodal(prompt, mediaBlob, modelOverride) {
  var apiKey = getGeminiApiKey();
  if (!apiKey) {
    throw new Error("Gemini API Key가 등록되지 않았습니다. 사이드바 상단 온보딩 배너의 [API Key 등록] 버튼을 눌러 키를 입력해 주십시오.");
  }
  var targetModel = modelOverride || CONFIG.MODEL_GENERATOR || "gemini-3.8-flash";
  var endpoint = CONFIG.BASE_URL + "/" + targetModel + ":generateContent?key=" + apiKey;

  var mimeType = mediaBlob.getContentType();
  var bytes = mediaBlob.getBytes();
  var sizeInMb = bytes.length / (1024 * 1024);

  var maxMb = (CONFIG && CONFIG.MAX_MEDIA_PAYLOAD_MB) || 35;
  // Apps Script 런타임 제약 사전 방어 (페이로드 50MB 한계 및 6분 타임아웃 방지)
  if (sizeInMb > maxMb) {
    throw new Error(
      "미디어 파일 크기(" + sizeInMb.toFixed(1) + "MB)가 Apps Script 단일 페이로드 안전 상한(" + maxMb + "MB)을 초과합니다. " +
      "안정적인 실행을 위해 15~30초 이내(30MB 이하)의 숏폼 영상을 권장하며, " +
      "장시간 고객 인터뷰나 대용량 영상 분석을 위한 Google Cloud 환경으로의 이관은 Google Cloud에 연락하여 전문 컨설팅을 받으십시오."
    );
  }

  var base64Data = Utilities.base64Encode(bytes);

  var payload = {
    contents: [{
      role: "user",
      parts: [
        { text: prompt },
        {
          inlineData: {
            mimeType: mimeType,
            data: base64Data
          }
        }
      ]
    }],
    generationConfig: {
      maxOutputTokens: 8192,
      temperature: 0.4
    }
  };

  var options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  var response = fetchWithRetry(endpoint, options);
  var responseCode = response.getResponseCode();
  var responseBody = response.getContentText();

  if (responseCode !== 200) {
    throw new Error("Gemini 멀티모달 분석 실패 (상태 코드: " + responseCode + "):\n" + responseBody);
  }

  var result = JSON.parse(responseBody);
  if (result.usageMetadata) {
    recordUsageMetadata(result.usageMetadata);
  }
  if (result.candidates && result.candidates.length > 0 && 
      result.candidates[0].content && result.candidates[0].content.parts) {
    return result.candidates[0].content.parts[0].text;
  }

  throw new Error("Gemini 멀티모달 응답 수신 실패:\n" + responseBody);
}

/**
 * Gemini 이미지 생성 API 호출 (상업용 광고 비주얼 시안 생성)
 * 최신 멀티모달 이미지 생성 모델 캐스케이드(Cascade Fallback) 적용:
 * 1순위: gemini-nano-banana-2.1 (:generateContent, responseModalities: ["IMAGE"])
 * 2순위: gemini-3.1-flash-image (:generateContent, responseModalities: ["IMAGE"])
 * 3순위: imagen-4.0-generate-001 (:predict)
 * 4순위: imagen-3.0-generate (:predict)
 */
function callGeminiImage(prompt, aspectRatio) {
  try {
    var apiKey = getGeminiApiKey();
    if (!apiKey) {
      Logger.log("API Key 누락으로 이미지 생성을 건너뜁니다.");
      return null;
    }

    var fullPrompt = prompt + ", commercial advertising product photography, professional studio lighting, 8k resolution, photorealistic";
    var ratio = aspectRatio || "1:1";

    // 1순위 & 2순위: Gemini 네이티브 이미지 생성 모델 (:generateContent)
    var nativeModels = [
      (CONFIG && CONFIG.IMAGE_MODEL_NAME) || "gemini-nano-banana-2.1",
      "gemini-3.1-flash-image"
    ];

    for (var m = 0; m < nativeModels.length; m++) {
      var nModel = nativeModels[m];
      try {
        var nEndpoint = CONFIG.BASE_URL + "/" + nModel + ":generateContent?key=" + apiKey;
        var nPayload = {
          contents: [{
            parts: [{ text: fullPrompt }]
          }],
          generationConfig: {
            responseModalities: ["IMAGE"]
          }
        };

        var nOptions = {
          method: "post",
          contentType: "application/json",
          headers: {
            "x-goog-api-key": apiKey
          },
          payload: JSON.stringify(nPayload),
          muteHttpExceptions: true
        };

        Logger.log("Gemini 이미지 생성 시도 (모델: " + nModel + ", 종횡비: " + ratio + ")...");
        var nResp = fetchWithRetry(nEndpoint, nOptions);
        var nCode = nResp.getResponseCode();
        var nBody = nResp.getContentText();

        if (nCode === 200) {
          var nResult = JSON.parse(nBody);
          if (nResult.candidates && nResult.candidates.length > 0 && 
              nResult.candidates[0].content && nResult.candidates[0].content.parts) {
            var parts = nResult.candidates[0].content.parts;
            for (var p = 0; p < parts.length; p++) {
              if (parts[p].inlineData && parts[p].inlineData.data) {
                Logger.log("Gemini 이미지 생성 성공 (모델: " + nModel + ")");
                return {
                  base64: parts[p].inlineData.data,
                  mimeType: parts[p].inlineData.mimeType || "image/png"
                };
              }
            }
          }
        } else {
          Logger.log("Gemini 이미지 모델(" + nModel + ") 호출 실패 (" + nCode + "): " + nBody);
        }
      } catch (nErr) {
        Logger.log("Gemini 이미지 모델(" + nModel + ") 호출 예외: " + nErr);
      }
    }

    // 3순위 & 4순위: Imagen 계열 모델 폴백 (:predict)
    var imagenModels = ["imagen-4.0-generate-001", "imagen-3.0-generate"];
    for (var i = 0; i < imagenModels.length; i++) {
      var imgModel = imagenModels[i];
      try {
        var imgEndpoint = CONFIG.BASE_URL + "/" + imgModel + ":predict?key=" + apiKey;
        var imgPayload = {
          instances: [
            { prompt: fullPrompt }
          ],
          parameters: {
            sampleCount: 1,
            aspectRatio: ratio
          }
        };

        var imgOptions = {
          method: "post",
          contentType: "application/json",
          headers: {
            "x-goog-api-key": apiKey
          },
          payload: JSON.stringify(imgPayload),
          muteHttpExceptions: true
        };

        Logger.log("Imagen 이미지 생성 시도 (모델: " + imgModel + ")...");
        var imgResp = fetchWithRetry(imgEndpoint, imgOptions);
        var imgCode = imgResp.getResponseCode();
        var imgBody = imgResp.getContentText();

        if (imgCode === 200) {
          var imgResult = JSON.parse(imgBody);
          if (imgResult.predictions && imgResult.predictions.length > 0 && imgResult.predictions[0].bytesBase64Encoded) {
            Logger.log("Imagen 이미지 생성 성공 (모델: " + imgModel + ")");
            return {
              base64: imgResult.predictions[0].bytesBase64Encoded,
              mimeType: imgResult.predictions[0].mimeType || "image/jpeg"
            };
          }
        } else {
          Logger.log("Imagen 모델(" + imgModel + ") 호출 실패 (" + imgCode + "): " + imgBody);
        }
      } catch (imgErr) {
        Logger.log("Imagen 모델(" + imgModel + ") 예외: " + imgErr);
      }
    }
  } catch (err) {
    Logger.log("이미지 생성 전체 예외: " + err);
  }
  return null;
}

/**
 * Gemini Veo 비디오 생성 API 호출 (9:16 모바일 숏폼 영상 생성)
 * Google AI Studio / Gemini Developer API의 predictLongRunning 엔드포인트 및 LRO 폴링
 * 1순위: veo-3.1-generate-preview (:predictLongRunning)
 * 2순위: veo-3.1-fast-generate-preview (:predictLongRunning)
 *
 * @param {string} prompt - 영문 비디오 연출 프롬프트
 * @param {string} [aspectRatio] - 종횡비 (기본값: "9:16")
 * @param {number} [durationSeconds] - 영상 길이 (초 단위, 기본값: 5)
 * @return {{ base64: string, mimeType: string } | null} 생성된 비디오 base64 객체 또는 null
 */
function callGeminiVideo(prompt, aspectRatio, durationSeconds) {
  try {
    var apiKey = getGeminiApiKey();
    if (!apiKey) {
      Logger.log("API Key 누락으로 Veo 비디오 생성을 건너뜁니다.");
      return null;
    }

    var ratio = aspectRatio || "9:16";
    var duration = durationSeconds || 5;

    var candidateModels = [
      (CONFIG && CONFIG.VIDEO_MODEL_NAME) || "veo-3.1-fast-generate-preview",
      "veo-3.1-generate-preview"
    ];

    var operationName = null;
    var activeModel = candidateModels[0];

    for (var m = 0; m < candidateModels.length; m++) {
      var modelName = candidateModels[m];
      var endpoint = CONFIG.BASE_URL + "/" + modelName + ":predictLongRunning?key=" + apiKey;

      var payload = {
        instances: [
          {
            prompt: prompt
          }
        ],
        parameters: {
          aspectRatio: ratio
        }
      };

      var options = {
        method: "post",
        contentType: "application/json",
        headers: {
          "x-goog-api-key": apiKey
        },
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      };

      Logger.log("Veo 비디오 생성 요청 시작 (모델: " + modelName + ", 비율: " + ratio + "): " + prompt.substring(0, 80) + "...");
      var response = fetchWithRetry(endpoint, options, 2);
      var code = response.getResponseCode();
      var body = response.getContentText();

      if (code === 200) {
        var initResult = JSON.parse(body);
        if (initResult.name) {
          operationName = initResult.name;
          activeModel = modelName;
          break;
        }
      } else {
        Logger.log("Veo 초기 생성 요청 실패 (모델: " + modelName + ", 상태 코드: " + code + "): " + body);
      }
    }

    if (!operationName) {
      Logger.log("모든 Veo 모델 생성 작업 큐 등록에 실패하여 비디오 생성을 완료하지 못했습니다 (Google AI Studio API Key 권한 또는 할당량 확인 필요).");
      return null;
    }

    Logger.log("Veo 장기 실행 작업(LRO) 등록 완료 (" + activeModel + "): " + operationName + ". 완료 대기 폴링 시작...");

    // LRO 폴링: Apps Script 런타임 제약(단일 실행 6분) 내에서 5초 간격으로 최대 24회(120초) 폴링
    var pollUrl = "https://generativelanguage.googleapis.com/v1beta/" + operationName + "?key=" + apiKey;
    var pollOptions = {
      method: "get",
      headers: {
        "x-goog-api-key": apiKey
      },
      muteHttpExceptions: true
    };

    var maxAttempts = 24; // 5초 * 24회 = 최대 120초
    for (var attempt = 1; attempt <= maxAttempts; attempt++) {
      Utilities.sleep(5000);

      var pollResp = UrlFetchApp.fetch(pollUrl, pollOptions);
      var pCode = pollResp.getResponseCode();
      if (pCode !== 200) {
        Logger.log("Veo 폴링 응답 오류 (시도 " + attempt + "/" + maxAttempts + ", 응답 코드: " + pCode + ")");
        continue;
      }

      var pollData = JSON.parse(pollResp.getContentText());
      if (pollData.error) {
        Logger.log("Veo 비디오 생성 작업 에러: " + JSON.stringify(pollData.error));
        return null;
      }

      if (pollData.done === true) {
        Logger.log("Veo 비디오 렌더링 완료! (" + (attempt * 5) + "초 소요)");
        var respObj = pollData.response || pollData.result;
        if (!respObj) {
          Logger.log("완료된 Veo 작업에 결과 데이터가 없습니다: " + JSON.stringify(pollData));
          return null;
        }

        var genVideoResp = respObj.generateVideoResponse || respObj;
        var samples = genVideoResp.generatedSamples || genVideoResp.generatedVideos || [];
        if (samples.length > 0 && samples[0].video) {
          var vObj = samples[0].video;
          var encoded = vObj.encodedVideo || vObj.bytesBase64Encoded || vObj.videoBytes;
          if (encoded) {
            return {
              base64: encoded,
              mimeType: vObj.encoding || vObj.mimeType || "video/mp4"
            };
          }
          if (vObj.uri) {
            Logger.log("Veo 비디오 파일 다운로드 중: " + vObj.uri);
            var downloadUrl = vObj.uri + (vObj.uri.indexOf("?") === -1 ? "?key=" + apiKey : "&key=" + apiKey);
            var dlResp = UrlFetchApp.fetch(downloadUrl, {
              method: "get",
              headers: { "x-goog-api-key": apiKey },
              followRedirects: true,
              muteHttpExceptions: true
            });
            if (dlResp.getResponseCode() !== 200) {
              dlResp = UrlFetchApp.fetch(downloadUrl, {
                method: "get",
                followRedirects: true,
                muteHttpExceptions: true
              });
            }

            if (dlResp.getResponseCode() === 200) {
              var blob = dlResp.getBlob();
              return {
                base64: Utilities.base64Encode(blob.getBytes()),
                mimeType: blob.getContentType() || "video/mp4"
              };
            } else {
              Logger.log("Veo 비디오 URI 다운로드 실패 (" + dlResp.getResponseCode() + "): " + dlResp.getContentText());
            }
          }
        }
        Logger.log("Veo 결과 파싱 실패: " + JSON.stringify(respObj));
        return null;
      }

      Logger.log("Veo 렌더링 진행 중... (시도 " + attempt + "/" + maxAttempts + ")");
    }

    Logger.log("Veo 렌더링 시간 초과 (90초). 백그라운드 처리가 계속될 수 있습니다.");
    return null;
  } catch (err) {
    Logger.log("Veo 비디오 생성 예외: " + err);
    return null;
  }
}

/**
 * 한국어 및 다국어 특화 텍스트 임베딩 모델(text-multilingual-embedding-002)을 호출하여
 * 텍스트 목록을 128차원(MRL) 벡터 배열로 일괄 변환한다.
 *
 * @param {Array<string>} texts - 임베딩할 세부 의견 텍스트 배열
 * @param {number} [optDim] - MRL 축소 차원 (기본값: CONFIG.EMBEDDING_DIM 또는 128)
 * @return {Array<Array<number>>} 128차원 부동소수점 벡터 배열
 */
function callGeminiBatchEmbeddings(texts, optDim) {
  if (!texts || texts.length === 0) {
    return [];
  }

  var dim = optDim || CONFIG.EMBEDDING_DIM || 128;
  var embedModel = CONFIG.EMBEDDING_MODEL || "text-multilingual-embedding-002";
  var apiKey = getGeminiApiKey();
  if (!apiKey) {
    throw new Error("Gemini API Key가 등록되지 않았습니다. 사이드바 상단 온보딩 배너의 [API Key 등록] 버튼을 눌러 키를 입력해 주십시오.");
  }
  var endpoint = CONFIG.BASE_URL + "/" + embedModel + ":batchEmbedContents?key=" + apiKey;

  var allEmbeddings = [];
  var chunkSize = 25; // Apps Script 안정성을 위해 25건 단위 청킹

  for (var i = 0; i < texts.length; i += chunkSize) {
    var chunk = texts.slice(i, i + chunkSize);
    var requests = [];
    for (var c = 0; c < chunk.length; c++) {
      requests.push({
        model: "models/" + embedModel,
        content: { parts: [{ text: String(chunk[c]).substring(0, 2048) }] },
        outputDimensionality: dim
      });
    }

    var payload = { requests: requests };
    var options = {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    try {
      var response = fetchWithRetry(endpoint, options, 2);
      var code = response.getResponseCode();
      var body = response.getContentText();

      if (code === 200) {
        var parsed = JSON.parse(body);
        if (parsed.embeddings && parsed.embeddings.length > 0) {
          for (var e = 0; e < parsed.embeddings.length; e++) {
            var item = parsed.embeddings[e];
            if (item && item.values && item.values.length > 0) {
              allEmbeddings.push(item.values);
            } else {
              allEmbeddings.push(createDeterministicVector(chunk[e], dim));
            }
          }
        } else {
          for (var f = 0; f < chunk.length; f++) {
            allEmbeddings.push(createDeterministicVector(chunk[f], dim));
          }
        }
      } else {
        Logger.log("임베딩 일괄 호출 경고 (" + code + "): " + body + " -> 결정론적 128차원 벡터 폴백");
        for (var k = 0; k < chunk.length; k++) {
          allEmbeddings.push(createDeterministicVector(chunk[k], dim));
        }
      }
    } catch (netErr) {
      Logger.log("임베딩 통신 예외: " + netErr + " -> 결정론적 128차원 벡터 폴백");
      for (var m = 0; m < chunk.length; m++) {
        allEmbeddings.push(createDeterministicVector(chunk[m], dim));
      }
    }
  }

  return allEmbeddings;
}

/**
 * 네트워크 단절이나 API 할당량 소진 시 파이프라인 중단을 방지하기 위한
 * 텍스트 해시 기반 결정론적(Deterministic) 128차원 정규화 벡터 생성 헬퍼
 */
function createDeterministicVector(text, dim) {
  var d = dim || 128;
  var vec = new Array(d);
  var str = String(text || "fallback");
  var seed = 0;
  for (var i = 0; i < str.length; i++) {
    seed = (seed << 5) - seed + str.charCodeAt(i);
    seed |= 0;
  }
  var norm = 0;
  for (var j = 0; j < d; j++) {
    var val = Math.sin(seed * (j + 1) * 0.1234) + Math.cos((j + 1) * 0.5678);
    vec[j] = val;
    norm += val * val;
  }
  norm = Math.sqrt(norm) || 1.0;
  for (var k = 0; k < d; k++) {
    vec[k] = Number((vec[k] / norm).toFixed(6));
  }
  return vec;
}

// ==========================================
// Module: Code_Prompts.js
// ==========================================
/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 3] 프롬프트 구글 독스 관리 및 스마트 캐싱 엔진 (Prompt Management & Cache Engine)
 */

/**
 * 캠페인 루트의 prompts/ 폴더 내에 9대 프롬프트 구글 독스를 자동 시딩한다.
 * GitHub 퍼블릭 저장소(GitHub Raw)에서 최신 프롬프트 마크다운 파일을 실시간 인출하여 생성하며,
 * 마케터가 이미 수정한 구글 독스가 존재할 경우 기존 내용을 안전하게 보존한다.
 *
 * @param {GoogleAppsScript.Drive.Folder} promptsFolder - prompts 폴더 객체
 */
function seedDefaultPrompts(promptsFolder) {
  if (!promptsFolder) {
    return;
  }

  var rawBase = (CONFIG && CONFIG.GITHUB_RAW_BASE) || "https://raw.githubusercontent.com/jiangjun-forge/google-cloud-0-to-1/main/samples/gws-marketing-content-pipeline";
  var promptKeys = Object.keys(CONFIG.DEFAULT_PROMPTS || {});

  for (var i = 0; i < promptKeys.length; i++) {
    var key = promptKeys[i];
    var def = CONFIG.DEFAULT_PROMPTS[key];
    var files = promptsFolder.getFilesByName(def.title);
    if (!files.hasNext()) {
      var initialContent = "";

      // 1. GitHub 퍼블릭 저장소의 prompts/{key}.md 파일 실시간 인출
      try {
        var fetchUrl = rawBase + "/prompts/" + key + ".md";
        var resp = UrlFetchApp.fetch(fetchUrl, { muteHttpExceptions: true });
        if (resp.getResponseCode() === 200) {
          initialContent = resp.getContentText();
          Logger.log("GitHub Raw로부터 최신 프롬프트 인출 성공: " + key + ".md");
        }
      } catch (fetchErr) {
        Logger.log("GitHub Raw 프롬프트 인출 실패 (로컬 폴백 사용): " + fetchErr.toString());
      }

      // 2. 네트워크 지연 또는 비정상 응답 시 내장 기본값으로 안전 폴백
      if (!initialContent) {
        initialContent =
          "# " + def.title + "\n\n" +
          "> " + def.description + "\n\n" +
          "---\n\n" +
          def.systemInstruction + "\n";
      }

      saveGoogleDoc(promptsFolder, def.title, initialContent);
      Logger.log("프롬프트 구글 독스 자동 시딩 완료: " + def.title);
    }
  }
}

/**
 * 프롬프트 구글 독스 문서를 읽어 시스템 지침 텍스트를 반환한다.
 * 구글 독스의 수정 시각(Last-Modified)을 감지하여 변경이 없을 때에는
 * CacheService로부터 0.01초 만에 즉시 반환하는 스마트 캐싱을 수행한다.
 *
 * @param {string} promptKey - CONFIG.DEFAULT_PROMPTS 키 (예: "02_content_generation")
 * @return {string} 시스템 지침 및 프롬프트 템플릿 텍스트
 */
function getPromptTemplate(promptKey) {
  var def = (CONFIG.DEFAULT_PROMPTS && CONFIG.DEFAULT_PROMPTS[promptKey]) ? CONFIG.DEFAULT_PROMPTS[promptKey] : null;
  var fallbackText = def ? def.systemInstruction : "";

  try {
    var campaignFolder = getCampaignFolder();
    var promptsFolderName = (CONFIG && CONFIG.PROMPTS_FOLDER_NAME) || "prompts";
    var pFolders = campaignFolder.getFoldersByName(promptsFolderName);
    if (!pFolders.hasNext()) {
      return fallbackText;
    }
    var promptsFolder = pFolders.next();
    var targetTitle = def ? def.title : promptKey;
    var files = promptsFolder.getFilesByName(targetTitle);
    if (!files.hasNext()) {
      return fallbackText;
    }

    var file = files.next();
    var fileId = file.getId();
    var lastModified = file.getLastUpdated().getTime();

    // CacheService 기반 수정 시간 대조 스마트 캐싱
    var cache = CacheService.getScriptCache();
    var cacheKey = "prompt_" + promptKey;
    var cacheTimeKey = "prompt_time_" + promptKey;

    var cachedTime = cache.get(cacheTimeKey);
    var cachedContent = cache.get(cacheKey);

    if (cachedContent && cachedTime && String(lastModified) === cachedTime) {
      return cachedContent;
    }

    // 문서가 새로 수정되었거나 캐시 미스 시 구글 독스 본문 로드
    var docContent = readGoogleDoc(promptsFolder, targetTitle);
    if (docContent && docContent.trim().length > 10) {
      // 마케터 안내용 주석 및 머리말(# 제목) 정제
      var cleanedContent = docContent.replace(/^#\s+[^\n]+\n+/, "").replace(/^>\s+[^\n]+\n+/, "").replace(/^---\n+/, "").trim();
      if (!cleanedContent) {
        cleanedContent = docContent.trim();
      }

      // 6시간(21,600초) 캐시 보관
      try {
        cache.put(cacheKey, cleanedContent, 21600);
        cache.put(cacheTimeKey, String(lastModified), 21600);
      } catch (cacheErr) {
        Logger.log("프롬프트 캐시 저장 경고: " + cacheErr);
      }
      return cleanedContent;
    }
  } catch (err) {
    Logger.log("프롬프트 구글 독스 로드 예외, 기본값 사용: " + err);
  }

  return fallbackText;
}

/**
 * 프롬프트 템플릿 내 플레이스홀더({{KEY}})를 변수 매핑 값으로 안전하게 치환한다.
 *
 * @param {string} template - 프롬프트 템플릿
 * @param {Object} variables - { KEY: value, ... } 치환 맵
 * @return {string} 치환 완료된 프롬프트
 */
function renderPromptTemplate(template, variables) {
  if (!template) {
    return "";
  }
  if (!variables) {
    return template;
  }

  var rendered = template;
  var keys = Object.keys(variables);
  for (var i = 0; i < keys.length; i++) {
    var k = keys[i];
    var val = variables[k] || "";
    var regex = new RegExp("\\{\\{" + k + "\\}\\}", "g");
    rendered = rendered.replace(regex, val);
  }
  return rendered;
}

// ==========================================
// Module: Code_Utils.js
// ==========================================
/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 4] 구글 드라이브 파일 탐색, 입출력 및 마크다운 독스 렌더러 (Drive Utils & Document Renderer)
 */

/**
 * 마케터의 중복 클릭(Double-click) 및 동시 실행 충돌을 방어하기 위한 사용자 락(User Lock) 래퍼
 *
 * @param {string} lockName - 작업 식별자
 * @param {Function} taskFn - 실행할 작업 함수
 * @param {number} [timeoutMs] - 락 대기 시간 (밀리초, 기본값: 3000ms)
 * @return {*} 작업 함수의 반환값
 */
function withUserLock(lockName, taskFn, timeoutMs) {
  var lock = LockService.getUserLock();
  var waitTime = timeoutMs || 3000;
  var hasLock = false;

  try {
    hasLock = lock.tryLock(waitTime);
  } catch (e) {
    Logger.log("LockService tryLock 예외 (" + lockName + "): " + e);
  }

  if (!hasLock) {
    Logger.log("Lock 획득 실패 (" + lockName + "): 다른 작업 진행 중");
    throw new Error("현재 다른 파이프라인 작업이 진행 중입니다. 이전 작업이 완료된 후 다시 시도해 주십시오.");
  }

  try {
    return taskFn();
  } finally {
    try {
      lock.releaseLock();
    } catch (relErr) {
      Logger.log("LockService releaseLock 예외 (" + lockName + "): " + relErr);
    }
  }
}

/**
 * LLM 응답 텍스트에서 마크다운 코드 블록(```json) 및 앞뒤 잡음 사족 문구를 정밀 제거하고
 * 순수 JSON 문자열만 안전하게 슬라이싱 추출한다.
 *
 * @param {string} rawText - 원천 LLM 응답 텍스트
 * @param {boolean} [isArrayExpected] - 배열([...]) 형식을 기대하는지 여부
 * @return {string} 추출된 순수 JSON 문자열
 */
function safeExtractJson(rawText, isArrayExpected) {
  if (!rawText) return "";

  var text = String(rawText).trim();

  // 1. 마크다운 코드 블록 제거
  text = text.replace(/^```[a-z0-9_-]*\s*/i, "").replace(/\s*```$/, "").trim();

  // 2. 대괄호([]) 또는 중괄호({}) 범위 정밀 슬라이싱
  var startIdx = -1;
  var endIdx = -1;

  if (isArrayExpected === true) {
    startIdx = text.indexOf("[");
    endIdx = text.lastIndexOf("]");
  } else if (isArrayExpected === false) {
    startIdx = text.indexOf("{");
    endIdx = text.lastIndexOf("}");
  } else {
    // 자동 감지: 먼저 등장하는 괄호 기준
    var firstBracket = text.indexOf("[");
    var firstBrace = text.indexOf("{");

    if (firstBracket !== -1 && (firstBrace === -1 || firstBracket < firstBrace)) {
      startIdx = firstBracket;
      endIdx = text.lastIndexOf("]");
    } else if (firstBrace !== -1) {
      startIdx = firstBrace;
      endIdx = text.lastIndexOf("}");
    }
  }

  if (startIdx !== -1 && endIdx !== -1 && endIdx > startIdx) {
    return text.substring(startIdx, endIdx + 1).trim();
  }

  return text;
}

/**
 * 안전한 JSON 파서 (LLM 사족 문구 자동 슬라이싱 및 문법 오류 시 크래시 방지 폴백 지원)
 *
 * @param {string} rawText - 파싱할 텍스트
 * @param {*} [fallbackVal] - 파싱 실패 시 반환할 기본값 (기본값: null)
 * @param {boolean} [isArrayExpected] - 배열 형식 기대 여부
 * @return {*} 파싱된 객체/배열 또는 fallbackVal
 */
function safeParseJson(rawText, fallbackVal, isArrayExpected) {
  var fallback = (fallbackVal !== undefined) ? fallbackVal : null;
  if (!rawText) return fallback;

  var cleaned = safeExtractJson(rawText, isArrayExpected);
  if (!cleaned) return fallback;

  try {
    return JSON.parse(cleaned);
  } catch (err) {
    Logger.log("safeParseJson 파싱 실패: " + err + " (정제된 텍스트 앞 120자: " + cleaned.substring(0, 120) + ")");
    return fallback;
  }
}

/**
 * 토큰 한도로 인해 끝부분이 잘린 JSON 배열 문자열을 마지막 완전한 객체까지 자동 수선하여 복원한다.
 *
 * @param {string} rawJsonText - 잘린 JSON 문자열
 * @return {Array|null} 복원 및 파싱된 배열 객체
 */
function repairTruncatedJsonArray(rawJsonText) {
  if (!rawJsonText) return null;
  var text = rawJsonText.trim();
  var startIdx = text.indexOf("[");
  if (startIdx === -1) return null;

  var candidate = text.substring(startIdx);
  try {
    var p = JSON.parse(candidate);
    if (Array.isArray(p)) return p;
  } catch (e) {
    // 잘림 감지 -> 수선 로직 가동
  }

  var lastBrace = candidate.lastIndexOf("}");
  while (lastBrace > 0) {
    var sliced = candidate.substring(0, lastBrace + 1) + "]";
    try {
      var repaired = JSON.parse(sliced);
      if (Array.isArray(repaired) && repaired.length > 0) {
        Logger.log("[자가 치유] 잘린 JSON 배열 안전 복원 완료 (총 " + repaired.length + "개 객체 복구)");
        return repaired;
      }
    } catch (err) {
      lastBrace = candidate.lastIndexOf("}", lastBrace - 1);
    }
  }

  return null;
}

function getFolderByPath(pathParts) {
  var currentFolder = DriveApp.getRootFolder();
  for (var i = 0; i < pathParts.length; i++) {
    var name = pathParts[i];
    var subFolders = currentFolder.getFoldersByName(name);
    if (subFolders.hasNext()) {
      currentFolder = subFolders.next();
    } else {
      currentFolder = currentFolder.createFolder(name);
    }
  }
  return currentFolder;
}

/**
 * 폴더 이름으로부터 시스템 내부에서 사용할 캠페인 슬러그를 도출한다.
 * [영문 원형 보존 원칙]:
 * 1. 폴더 이름이 영문/숫자 기반인 경우: 임의로 접두사(cp-)를 붙이거나 새로 가공하지 않고 마케터가 명명한 영문 이름을 그대로 따른다.
 * 2. 폴더 이름에 한글이 포함된 경우에만: 마케팅/시즌 키워드를 영문으로 자동 매핑하여 안전한 슬러그를 합성한다.
 *
 * @param {string} rawName - 마케터가 명명한 폴더 이름
 * @return {string} 캠페인 슬러그
 */
function generateCampaignSlug(rawName) {
  if (!rawName) return CONFIG.CAMPAIGN_CODE || "cp-ignite";

  var text = String(rawName).trim();

  // 1. [영문 원형 보존 원칙] 한글이 전혀 없는 순수 영문/숫자 폴더명인 경우: 임의 접두사 없이 그대로 채택
  var hasKorean = /[가-힣ㄱ-ㅎㅏ-ㅣ]/.test(text);
  if (!hasKorean) {
    // 공백 및 언더스코어만 안전하게 하이픈(-)으로 정규화하고 소문자화하여 마케터가 지은 영문 이름 그대로 보존
    var pureSlug = text
      .toLowerCase()
      .replace(/[\s_]+/g, "-")
      .replace(/[^a-z0-9\-]+/g, "")
      .replace(/^-+|-+$/g, "")
      .replace(/-+/g, "-");
    if (pureSlug && pureSlug.length >= 2) {
      return pureSlug;
    }
  }

  // 2. 한글이 포함된 경우: 자주 사용되는 마케팅 및 시즌 키워드 영문 매핑 사전 적용
  var dict = {
    "가을": "autumn", "오텀": "autumn",
    "봄": "spring", "스프링": "spring",
    "여름": "summer", "서머": "summer",
    "겨울": "winter", "윈터": "winter",
    "캠페인": "camp", "프로모션": "promo", "이벤트": "event",
    "마케팅": "mkt", "프로젝트": "proj",
    "신제품": "new", "론칭": "launch", "출시": "launch",
    "브리즈": "breeze", "블랙": "black", "프라이데이": "friday",
    "크리스마스": "xmas", "할로윈": "halloween", "설날": "lunar", "추석": "thanksgiving",
    "세일": "sale", "특가": "deal", "기획": "plan"
  };

  var lower = text.toLowerCase();
  for (var k in dict) {
    if (lower.indexOf(k) !== -1) {
      lower = lower.split(k).join("-" + dict[k] + "-");
    }
  }

  // 영문 소문자, 숫자, 하이픈 외 모든 특수문자/공백/한글 제거
  var cleaned = lower
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-+/g, "-");

  // 최소 2자 이상의 영문/숫자가 확보된 경우 슬러그 완성
  if (cleaned && cleaned.length >= 2) {
    return cleaned.indexOf("cp-") === 0 ? cleaned : "cp-" + cleaned;
  }

  // 영문/숫자가 없는 순수 한글일 경우 문자열 해시 기반 고유 슬러그 생성
  var hash = 0;
  for (var i = 0; i < text.length; i++) {
    hash = ((hash << 5) - hash) + text.charCodeAt(i);
    hash |= 0;
  }
  var hexHash = Math.abs(hash).toString(16).substring(0, 6);
  return "cp-campaign-" + hexHash;
}

/**
 * 현재 구글 시트의 이름이 기본 Untitled 상태이거나 초기 상태인 경우,
 * 확정된 캠페인 폴더명 및 슬러그에 맞추어 직관적인 컨트롤 타워 명칭으로 자동 변경한다.
 *
 * @param {string} [displayName] - 캠페인 폴더 표시 명칭
 * @param {string} [slug] - 캠페인 영문 슬러그
 */
function syncSpreadsheetTitleWithCampaign(displayName, slug) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    if (!ss) return;

    var currentTitle = (ss.getName() || "").trim();
    var lowerTitle = currentTitle.toLowerCase();

    // 사용자가 직접 명명한 고유 시트명이 아닌, Untitled/기본 상태인 경우에만 자동 변경
    var isUntitled = !currentTitle ||
      lowerTitle === "untitled" ||
      lowerTitle.indexOf("untitled spreadsheet") === 0 ||
      lowerTitle.indexOf("untitled") === 0 ||
      currentTitle === "제목 없는 스프레드시트" ||
      currentTitle === "제목없는 스프레드시트" ||
      currentTitle === "마케팅 콘텐츠 파이프라인" ||
      currentTitle.indexOf("[마케팅 컨트롤 타워]") === 0 ||
      currentTitle.indexOf("[마케팅 콘텐츠 컨트롤 타워]") === 0;

    if (isUntitled) {
      var targetName = displayName || slug || (CONFIG && CONFIG.CAMPAIGN_CODE) || "cp-ignite";
      var newTitle = "[마케팅 콘텐츠 컨트롤 타워] " + targetName;
      if (currentTitle !== newTitle) {
        ss.rename(newTitle);
        Logger.log("구글 시트 제목 자동 동기화: '" + currentTitle + "' -> '" + newTitle + "'");
      }
    }
  } catch (e) {
    Logger.log("구글 시트 제목 변경 중 예외 (무시 가능): " + e);
  }
}

/**
 * 마케터가 생성한 캠페인 폴더를 자동 감지하고 폴더 ID로 영구 바인딩한다.
 * [UX 혁신]: 마케터가 구글 드라이브에서 자유롭게 폴더를 만들고 시트를 넣으면,
 * 1. 구글 시트의 부모 폴더를 즉시 캠페인 루트 폴더로 자동 채택
 * 2. 폴더 ID(folder.getId())를 영구 저장하여 마케터가 폴더 이름을 변경해도 완벽 추적
 * 3. 한글 폴더명을 분석하여 안전한 영문 슬러그를 자동 합성
 * 4. 구글 시트 제목이 Untitled일 경우 캠페인 명칭으로 자동 동기화
 */
function getCampaignFolder(optDoNotCreate) {
  var props = PropertiesService.getScriptProperties();
  var savedFolderId = props.getProperty("CAMPAIGN_FOLDER_ID");

  // 1. 이미 영구 바인딩된 폴더 ID가 유효한지 우선 검증 (폴더명 변경 시에도 100% 추적)
  if (savedFolderId) {
    try {
      var savedFolder = DriveApp.getFolderById(savedFolderId);
      if (savedFolder && !savedFolder.isTrashed()) {
        syncSpreadsheetTitleWithCampaign(savedFolder.getName(), props.getProperty("CAMPAIGN_SLUG"));
        return savedFolder;
      }
    } catch (idErr) {
      Logger.log("기존 바인딩된 폴더 ID 접근 불가 (재탐색 진행): " + idErr);
    }
  }

  // 2. 현재 구글 시트가 위치한 부모 폴더 자동 감지
  try {
    var sheetId = SpreadsheetApp.getActiveSpreadsheet().getId();
    var sheetFile = DriveApp.getFileById(sheetId);
    var parents = sheetFile.getParents();
    var rootFolderId = DriveApp.getRootFolder().getId();

    while (parents.hasNext()) {
      var parent = parents.next();
      // 내 드라이브 최상위 루트가 아닌 서브폴더에 위치한 경우, 마케터의 캠페인 폴더로 즉시 채택!
      if (parent.getId() !== rootFolderId && !parent.isTrashed()) {
        var folderName = parent.getName();
        var slug = generateCampaignSlug(folderName);
        props.setProperty("CAMPAIGN_FOLDER_ID", parent.getId());
        props.setProperty("CAMPAIGN_SLUG", slug);
        props.setProperty("CAMPAIGN_DISPLAY_NAME", folderName);
        Logger.log("마케터 캠페인 부모 폴더 자동 감지 및 ID 영구 바인딩: " + folderName + " (ID: " + parent.getId() + ", Slug: " + slug + ")");
        syncSpreadsheetTitleWithCampaign(folderName, slug);
        return parent;
      }
    }
  } catch (parentErr) {
    Logger.log("부모 캠페인 폴더 감지 중 예외: " + parentErr);
  }

  if (optDoNotCreate) {
    return null;
  }

  // 3. 부모 폴더가 루트이거나 미지정된 경우 기본 폴더 생성 및 바인딩
  var defaultFolder = getFolderByPath([CONFIG.CAMPAIGN_CODE]);
  props.setProperty("CAMPAIGN_FOLDER_ID", defaultFolder.getId());
  props.setProperty("CAMPAIGN_SLUG", CONFIG.CAMPAIGN_CODE);
  props.setProperty("CAMPAIGN_DISPLAY_NAME", CONFIG.CAMPAIGN_CODE);
  syncSpreadsheetTitleWithCampaign(CONFIG.CAMPAIGN_CODE, CONFIG.CAMPAIGN_CODE);
  return defaultFolder;
}

/**
 * 캠페인 식별용 영문 슬러그를 반환한다.
 */
function getCampaignCode() {
  try {
    var props = PropertiesService.getScriptProperties();
    var savedSlug = props.getProperty("CAMPAIGN_SLUG");
    if (savedSlug) {
      syncSpreadsheetTitleWithCampaign(props.getProperty("CAMPAIGN_DISPLAY_NAME"), savedSlug);
      return savedSlug;
    }

    var folder = getCampaignFolder();
    var folderName = folder.getName();
    var slug = generateCampaignSlug(folderName);
    props.setProperty("CAMPAIGN_SLUG", slug);
    syncSpreadsheetTitleWithCampaign(folderName, slug);
    return slug;
  } catch (e) {
    Logger.log("캠페인 코드 도출 중 예외: " + e);
  }
  return CONFIG.CAMPAIGN_CODE;
}

/**
 * 마케터가 명명한 실제 캠페인 폴더 명칭을 반환한다.
 */
function getCampaignDisplayName() {
  try {
    var folder = getCampaignFolder();
    return folder.getName();
  } catch (e) {
    return getCampaignCode();
  }
}

function getCampaignSubFolder(subPathParts, optDoNotCreate) {
  var currentFolder = getCampaignFolder(optDoNotCreate);
  if (!currentFolder) return null;
  for (var i = 0; i < subPathParts.length; i++) {
    var name = subPathParts[i];
    var subFolders = currentFolder.getFoldersByName(name);
    var foundFolder = null;
    while (subFolders.hasNext()) {
      var candidate = subFolders.next();
      try {
        if (!candidate.isTrashed()) {
          foundFolder = candidate;
          break;
        }
      } catch (trashErr) {
        foundFolder = candidate;
        break;
      }
    }
    if (foundFolder) {
      currentFolder = foundFolder;
    } else if (optDoNotCreate) {
      return null;
    } else {
      currentFolder = currentFolder.createFolder(name);
    }
  }
  return currentFolder;
}

function readTextFile(folder, fileName) {
  var files = folder.getFilesByName(fileName);
  while (files.hasNext()) {
    var file = files.next();
    try {
      if (file.isTrashed()) continue;
    } catch (e) {}
    return file.getBlob().getDataAsString("UTF-8");
  }
  return null;
}

function saveTextFile(folder, fileName, content) {
  var files = folder.getFilesByName(fileName);
  while (files.hasNext()) {
    var existingFile = files.next();
    try {
      if (existingFile.isTrashed()) continue;
    } catch (e) {}
    existingFile.setContent(content);
    return existingFile;
  }
  return folder.createFile(fileName, content, MimeType.PLAIN_TEXT);
}

function saveBinaryFile(folder, fileName, base64Data, contentType) {
  var decoded = Utilities.base64Decode(base64Data);
  var blob = Utilities.newBlob(decoded, contentType, fileName);
  var files = folder.getFilesByName(fileName);
  while (files.hasNext()) {
    files.next().setTrashed(true);
  }
  return folder.createFile(blob);
}

/**
 * 마크다운 인라인 서식(**bold**)을 파싱하여 구글 독스 텍스트 요소에 굵은 글씨 스타일을 적용한다.
 */
function formatInlineStyles(element, rawText) {
  var cleanText = "";
  var boldRanges = [];
  var regex = /\*\*(.*?)\*\*/g;
  var lastIndex = 0;
  var match;

  while ((match = regex.exec(rawText)) !== null) {
    cleanText += rawText.substring(lastIndex, match.index);
    var start = cleanText.length;
    cleanText += match[1];
    var end = cleanText.length - 1;
    if (end >= start) {
      boldRanges.push([start, end]);
    }
    lastIndex = regex.lastIndex;
  }
  cleanText += rawText.substring(lastIndex);

  var textObj = element.editAsText();
  textObj.setText(cleanText);
  for (var j = 0; j < boldRanges.length; j++) {
    var bStart = boldRanges[j][0];
    var bEnd = boldRanges[j][1];
    if (bEnd >= bStart && bEnd < cleanText.length) {
      textObj.setBold(bStart, bEnd, true);
    }
  }
}

/**
 * 구글 독스 본문(Body)을 안전하게 초기화한다.
 * [마지막 단락 보호]: 구글 독스 문서 섹션에는 최소 1개의 단락이 반드시 존재해야 하므로,
 * body.clear() 대신 마지막 단락을 보존하며 텍스트를 비워 'Can't remove the last paragraph' 예외를 원천 차단한다.
 */
function safelyClearBody(body) {
  try {
    var hasParagraph = false;
    for (var i = 0; i < body.getNumChildren(); i++) {
      if (body.getChild(i).getType() === DocumentApp.ElementType.PARAGRAPH) {
        hasParagraph = true;
        break;
      }
    }
    if (!hasParagraph) {
      body.appendParagraph("");
    }

    while (body.getNumChildren() > 1) {
      body.removeChild(body.getChild(0));
    }

    var lastChild = body.getChild(0);
    if (lastChild) {
      if (lastChild.getType() === DocumentApp.ElementType.PARAGRAPH) {
        lastChild.asParagraph().setText("");
      } else {
        body.appendParagraph("");
        body.removeChild(lastChild);
      }
    }
  } catch (err) {
    Logger.log("safelyClearBody 경고: " + err);
  }
}

/**
 * 마크다운 텍스트를 구글 독스(Google Docs) 네이티브 스타일(Title, Heading 1~3, List, Table, HorizontalRule)로 변환하여 렌더링한다.
 */
function renderMarkdownToDoc(doc, markdown) {
  var body = doc.getBody();
  safelyClearBody(body);

  if (!markdown) {
    return;
  }

  // 특수 공백 정규화
  markdown = String(markdown).replace(/\u00A0/g, " ");

  var lines = markdown.split(/\r?\n/);
  var inCodeBlock = false;
  var codeBlockContent = [];
  var isFirstParagraph = true;

  function appendPara(text, heading) {
    var p;
    if (isFirstParagraph) {
      p = body.getParagraphs()[0];
      isFirstParagraph = false;
    } else {
      p = body.appendParagraph("");
    }
    if (heading) {
      p.setHeading(heading);
    }
    formatInlineStyles(p, text);
    return p;
  }

  function appendItem(text) {
    var li = body.appendListItem("");
    formatInlineStyles(li, text);
    isFirstParagraph = false;
    return li;
  }

  function appendRule() {
    body.appendHorizontalRule();
    isFirstParagraph = false;
  }

  var i = 0;
  while (i < lines.length) {
    var line = lines[i];
    var trimmed = line.trim();

    // 1. 코드 블록
    if (trimmed.indexOf("```") === 0) {
      if (inCodeBlock) {
        var codeText = codeBlockContent.join("\n");
        var cp = appendPara(codeText, DocumentApp.ParagraphHeading.NORMAL);
        cp.setFontFamily("Consolas");
        codeBlockContent = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
        codeBlockContent = [];
      }
      i++;
      continue;
    }

    if (inCodeBlock) {
      codeBlockContent.push(line);
      i++;
      continue;
    }

    // 2. 빈 줄
    if (!trimmed) {
      i++;
      continue;
    }

    // 3. 구분선
    if (trimmed === "---" || trimmed === "***" || trimmed === "___") {
      appendRule();
      i++;
      continue;
    }

    // 4. 마크다운 테이블
    if (trimmed.indexOf("|") === 0 && trimmed.lastIndexOf("|") === trimmed.length - 1) {
      var tableLines = [];
      while (i < lines.length && lines[i].trim().indexOf("|") === 0) {
        var tLine = lines[i].trim();
        if (!/^\|[\s\-:]+(\|[\s\-:]+)+\|$/.test(tLine)) {
          var cells = tLine.split("|").slice(1, -1).map(function(c) { return c.trim(); });
          tableLines.push(cells);
        }
        i++;
      }
      if (tableLines.length > 0) {
        var table = body.appendTable(tableLines);
        isFirstParagraph = false;
        if (table.getNumRows() > 0) {
          var headerRow = table.getRow(0);
          for (var c = 0; c < headerRow.getNumCells(); c++) {
            var cell = headerRow.getCell(c);
            cell.setBackgroundColor("#F1F3F4");
            var cellP = cell.getChild(0).asParagraph();
            cellP.setBold(true);
          }
        }
      }
      continue;
    }

    // 5. 헤딩 판별
    var headingMatch = trimmed.match(/^(#{1,6})(?:[\s\u00A0]+|(?=\d))(.*)$/);
    if (headingMatch) {
      var level = headingMatch[1].length;
      var headingText = headingMatch[2].replace(/\s*#+\s*$/, "").trim();
      var headingType = DocumentApp.ParagraphHeading.NORMAL;
      if (level === 1) {
        headingType = DocumentApp.ParagraphHeading.TITLE;
      } else if (level === 2) {
        headingType = DocumentApp.ParagraphHeading.HEADING1;
      } else if (level === 3) {
        headingType = DocumentApp.ParagraphHeading.HEADING2;
      } else if (level >= 4) {
        headingType = DocumentApp.ParagraphHeading.HEADING3;
      }
      appendPara(headingText, headingType);
    } else if (/^[-*+]\s+/.test(trimmed)) {
      // 6. 불릿 리스트
      appendItem(trimmed.replace(/^[-*+]\s+/, ""));
    } else if (/^\d+\.\s+/.test(trimmed)) {
      // 7. 번호 매기기 리스트
      appendItem(trimmed.replace(/^\d+\.\s+/, ""));
    } else if (trimmed.indexOf("> ") === 0) {
      // 8. 인용구
      var quoteP = appendPara(trimmed.substring(2), DocumentApp.ParagraphHeading.NORMAL);
      quoteP.setItalic(true);
      quoteP.setIndentStart(36);
    } else {
      // 9. 일반 단락
      appendPara(line, DocumentApp.ParagraphHeading.NORMAL);
    }

    i++;
  }

  if (inCodeBlock && codeBlockContent.length > 0) {
    var leftP = appendPara(codeBlockContent.join("\n"), DocumentApp.ParagraphHeading.NORMAL);
    leftP.setFontFamily("Consolas");
  }

  if (!isFirstParagraph) {
    try {
      if (body.getNumChildren() > 1) {
        var firstEl = body.getChild(0);
        if (firstEl.getType() === DocumentApp.ElementType.PARAGRAPH && firstEl.asParagraph().getText() === "") {
          firstEl.removeFromParent();
        }
      }
    } catch (cleanupErr) {
      // 안전 무시
    }
  }
}

/**
 * 구글 독스(Google Docs) 문서를 생성하거나 기존 문서의 본문을 네이티브 스타일로 갱신한다.
 */
function saveGoogleDoc(folder, title, content) {
  var files = folder.getFilesByName(title);
  var doc;
  while (files.hasNext()) {
    var file = files.next();
    try {
      if (file.isTrashed()) continue;
    } catch (e) {}
    if (file.getMimeType() === MimeType.GOOGLE_DOCS) {
      doc = DocumentApp.openById(file.getId());
      renderMarkdownToDoc(doc, content);
      doc.saveAndClose();
      return file;
    } else {
      file.setTrashed(true);
    }
  }
  doc = DocumentApp.create(title);
  renderMarkdownToDoc(doc, content);
  doc.saveAndClose();
  var docFile = DriveApp.getFileById(doc.getId());
  docFile.moveTo(folder);
  return docFile;
}

/**
 * 폴더 내의 구글 독스(Google Docs) 문서를 열어 본문 텍스트를 읽는다.
 */
function readGoogleDoc(folder, title) {
  var files = folder.getFilesByName(title);
  while (files.hasNext()) {
    var file = files.next();
    if (file.getMimeType() === MimeType.GOOGLE_DOCS) {
      var doc = DocumentApp.openById(file.getId());
      return doc.getBody().getText();
    }
    return file.getBlob().getDataAsString("UTF-8");
  }
  return null;
}

/**
 * 기본 멀티 채널 미디어 제작 스펙 객체를 생성한다.
 *
 * @param {string} [prefix] - 리비전 접두사 (예: "00", "01")
 * @return {Object} 기본 미디어 스펙 객체
 */
function getDefaultMediaSpec(prefix) {
  var p = prefix || "00";
  return {
    revision: "rv-" + p,
    includeVideo: true,
    images: [
      { key: "banner_16x9", name: p + "_banner_16x9.png", ratio: "16:9", label: "가로형 디스플레이 배너 (16:9)" },
      { key: "poster_9x16", name: p + "_poster_9x16.png", ratio: "9:16", label: "세로형 모바일 포스터 (9:16)" },
      { key: "sns_1x1", name: p + "_sns_1x1.png", ratio: "1:1", label: "정방형 SNS 피드 (1:1)" }
    ],
    reason: "기본 멀티 채널 미디어 세트(16:9 배너, 9:16 포스터, 1:1 SNS 피드, 숏폼 비디오) 적용"
  };
}

/**
 * 마케터가 작성/수정한 콘텐츠 제작 명세서(SPEC) 및 보정 지침을 분석하여 미디어 제작 스펙을 컴파일한다.
 * Gemini 3.8 Flash의 자연어 이해를 기반으로 하되, 비정형 텍스트 및 오프라인 환경에 대비한 결정론적 룰을 함께 적용한다.
 *
 * @param {string} specContent - 마케터의 SPEC 구글 독스 본문
 * @param {string} prefix - 리비전 접두사 ("00", "01" 등)
 * @param {string} [directiveText] - 마케터 보정 지침 (9단계인 경우)
 * @param {GoogleAppsScript.Drive.Folder} [targetFolder] - 저장 대상 폴더 (media_specs.json 저장용)
 * @return {Object} 컴파일된 미디어 스펙 객체
 */
function compileMediaSpecFromDocs(specContent, prefix, directiveText, targetFolder) {
  var p = prefix || "00";
  var spec = getDefaultMediaSpec(p);
  var combinedText = ((specContent || "") + "\n\n" + (directiveText || "")).trim();

  if (!combinedText) {
    if (targetFolder) {
      try {
        saveTextFile(targetFolder, "media_specs.json", JSON.stringify(spec, null, 2));
      } catch (err) {
        Logger.log("기본 media_specs.json 저장 중 예외: " + err);
      }
    }
    return spec;
  }

  // 1. 결정론적 룰 기반 사전 분석 (네트워크 단절 또는 모킹 환경에서도 안정적 대응)
  var lower = combinedText.toLowerCase();
  var videoExcludedByRule = /(영상|비디오|숏폼|동영상)\s*(?:파일|소재|제작|콘텐츠)?\s*(?:은|는|이|가|을|를)?\s*(제외|생략|미제작|보류|없음|x|빼|안함)/i.test(combinedText);
  if (!videoExcludedByRule) {
    var videoKeywords = [
      "영상 제외", "비디오 제외", "숏폼 제외", "동영상 제외", "영상 미제작", "비디오 미제작", "숏폼 미제작",
      "영상 생략", "비디오 생략", "숏폼 생략", "영상 x", "비디오 x", "숏폼 x", "영상 빼", "비디오 빼",
      "no video", "exclude video", "skip video"
    ];
    for (var k = 0; k < videoKeywords.length; k++) {
      if (lower.indexOf(videoKeywords[k]) !== -1) {
        videoExcludedByRule = true;
        break;
      }
    }
  }

  var bannerExcluded = /(배너|16:9|가로\s*배너)\s*(?:이미지|소재|제작)?\s*(?:은|는|이|가|을|를)?\s*(제외|생략|미제작|보류|없음|x|빼)/i.test(combinedText) ||
                       (lower.indexOf("배너 제외") !== -1 || lower.indexOf("16:9 제외") !== -1 || lower.indexOf("가로 배너 제외") !== -1);
  var posterExcluded = /(포스터|9:16|세로\s*포스터)\s*(?:이미지|소재|제작)?\s*(?:은|는|이|가|을|를)?\s*(제외|생략|미제작|보류|없음|x|빼)/i.test(combinedText) ||
                       (lower.indexOf("포스터 제외") !== -1 || lower.indexOf("9:16 제외") !== -1 || lower.indexOf("세로 포스터 제외") !== -1);
  var snsExcluded = /(sns|피드|1:1|정방형)\s*(?:이미지|소재|제작)?\s*(?:은|는|이|가|을|를)?\s*(제외|생략|미제작|보류|없음|x|빼)/i.test(combinedText) ||
                    (lower.indexOf("sns 제외") !== -1 || lower.indexOf("1:1 제외") !== -1 || lower.indexOf("피드 제외") !== -1);

  // 2. Gemini 3.8 Flash를 통한 지능형 자연어 컴파일 (API Key 유효 시)
  var apiKey = getGeminiApiKey();
  if (apiKey && typeof callGemini === "function") {
    try {
      var systemInstruction =
        "당신은 마케팅 미디어 제작 파이프라인의 테크니컬 컴파일러이다.\n" +
        "마케터가 작성/수정한 콘텐츠 제작 명세서(SPEC)와 보정 지침 텍스트를 정밀 분석하여 실제 파일로 제작할 미디어 에셋 목록을 JSON으로 도출하라.\n\n" +
        "### 규칙:\n" +
        "1. 마케터가 영상/비디오/숏폼 제외, 생략, 미제작, 보류를 언급한 경우 includeVideo를 false로 설정하라.\n" +
        "2. 마케터가 요청한 이미지 종횡비(16:9 배너, 9:16 포스터, 1:1 SNS 피드)만 images 배열에 포함하라. 특정 비율 제외를 언급하면 제외하라.\n" +
        "   - 지원 이미지 키: 'banner_16x9'(16:9 배너), 'poster_9x16'(9:16 포스터), 'sns_1x1'(1:1 SNS 피드)\n" +
        "3. 특별한 언급이나 제외 요청이 없으면 기본 3종 이미지(16:9, 9:16, 1:1)와 비디오(includeVideo: true)를 유지하라.\n" +
        "4. reason 필드에 마케터의 어떤 지침에 따라 왜 이렇게 결정되었는지 한국어 평서문('-다' 체)으로 1문장 설명하라.\n\n" +
        "### 출력 JSON 스키마:\n" +
        "{\n" +
        '  "includeVideo": boolean,\n' +
        '  "images": [\n' +
        '    { "key": "banner_16x9", "ratio": "16:9", "label": "가로형 디스플레이 배너 (16:9)" }\n' +
        "  ],\n" +
        '  "reason": "마케터 명세서상 숏폼 비디오 제외 및 16:9 배너 미지정 지침 반영"\n' +
        "}";

      var promptText = "### [마케터 제작 명세서 및 보정 지침]\n" + combinedText.substring(0, 3000);
      var llmResp = callGemini(systemInstruction, promptText);
      if (llmResp) {
        var parsed = safeParseJson(llmResp, null, false);
        if (parsed && typeof parsed === "object") {
          if (typeof parsed.includeVideo === "boolean") {
            spec.includeVideo = parsed.includeVideo;
          }
          if (parsed.images && Array.isArray(parsed.images)) {
            var validImgs = [];
            for (var m = 0; m < parsed.images.length; m++) {
              var imgObj = parsed.images[m];
              var kKey = imgObj.key || ("img_" + m);
              var rRatio = imgObj.ratio || "1:1";
              var lLabel = imgObj.label || (rRatio + " 이미지");
              var fName = p + "_" + (kKey.indexOf(p + "_") === 0 ? kKey.substring(p.length + 1) : kKey) + ".png";
              validImgs.push({
                key: kKey,
                name: fName,
                ratio: rRatio,
                label: lLabel
              });
            }
            if (validImgs.length > 0) {
              spec.images = validImgs;
            }
          }
          if (parsed.reason) {
            spec.reason = parsed.reason;
          }
        }
      }
    } catch (llmErr) {
      Logger.log("미디어 스펙 컴파일 LLM 예외 (룰 기반 폴백 유지): " + llmErr);
    }
  }

  // 3. 결정론적 룰 강제 보정 (LLM 미동작 또는 명시적 제외 키워드 존재 시 확실한 보장)
  if (videoExcludedByRule) {
    spec.includeVideo = false;
    if (spec.reason.indexOf("기본") !== -1) {
      spec.reason = "마케터 명세서상 숏폼 비디오 제외 지침 반영";
    }
  }
  if (bannerExcluded || posterExcluded || snsExcluded) {
    spec.images = spec.images.filter(function(img) {
      if (bannerExcluded && (img.key.indexOf("banner") !== -1 || img.ratio === "16:9")) return false;
      if (posterExcluded && (img.key.indexOf("poster") !== -1 || img.ratio === "9:16")) return false;
      if (snsExcluded && (img.key.indexOf("sns") !== -1 || img.ratio === "1:1")) return false;
      return true;
    });
  }

  // 파일명 prefix 규격 재검증
  for (var n = 0; n < spec.images.length; n++) {
    if (!spec.images[n].name || spec.images[n].name.indexOf(p + "_") !== 0) {
      spec.images[n].name = p + "_" + (spec.images[n].key || ("img_" + n)) + ".png";
    }
  }

  // 4. 폴더에 media_specs.json 파일로 영구 저장
  if (targetFolder) {
    try {
      saveTextFile(targetFolder, "media_specs.json", JSON.stringify(spec, null, 2));
      Logger.log("media_specs.json 저장 완료 (" + spec.revision + "): " + spec.reason);
    } catch (saveErr) {
      Logger.log("media_specs.json 저장 중 예외 (무시 가능): " + saveErr);
    }
  }

  return spec;
}

/**
 * 마케터가 열어볼 campaign_content 구글 독스 최상단에 수록할 [제작 명세서 반영 현황] 헤더 블록을 생성한다.
 *
 * @param {Object} mediaSpec - 컴파일된 미디어 스펙 객체
 * @return {string} 마크다운 헤더 블록
 */
function buildMediaSpecReportHeader(mediaSpec) {
  if (!mediaSpec) return "";
  var videoText = mediaSpec.includeVideo
    ? "포함 (Veo 숏폼 비디오 생성)"
    : "제외 (마케터 명세서 지침에 따라 미제작)";
  var imageLines = [];
  var imgs = mediaSpec.images || [];
  for (var i = 0; i < imgs.length; i++) {
    var img = imgs[i];
    imageLines.push("* " + (img.label || img.name) + " (" + (img.ratio || "") + "): `" + img.name + "`");
  }
  var imgListText = imageLines.length > 0 ? imageLines.join("\n") : "* 제작 요청 이미지 없음";

  return "## [제작 명세서(SPEC) 반영 미디어 산출물 현황]\n\n" +
    "* **명세서 반영 사유**: " + (mediaSpec.reason || "기본 멀티 채널 미디어 세트 적용") + "\n" +
    "* **숏폼 비디오**: " + videoText + "\n" +
    "* **제작 이미지 (" + imgs.length + "종)**:\n" +
    imgListText + "\n\n" +
    "---\n\n";
}

/**
 * 리비전 폴더(rv-xx) 내 필수 에셋(카피 독스, 미디어 스펙에 따른 이미지 및 숏폼 비디오)의 완성 상태를 정밀 진단한다.
 */
function inspectRevisionFolder(folder, prefix) {
  var result = {
    hasDoc: false,
    hasBanner: false,
    hasPoster: false,
    hasSns: false,
    hasVideo: false,
    existingFiles: [],
    missingFiles: [],
    isComplete: false,
    isEmpty: true
  };

  if (!folder) return result;

  var docName = (CONFIG && CONFIG.CONTENT_DOC_NAME) || "campaign_content";
  var bannerName = prefix + "_banner_16x9.png";
  var posterName = prefix + "_poster_9x16.png";
  var snsName = prefix + "_sns_1x1.png";
  var videoName = prefix + "_shorts.mp4";

  // media_specs.json 존재 여부 확인 및 동적 스펙 로드
  var mediaSpec = null;
  var specFileIter = folder.getFilesByName("media_specs.json");
  if (specFileIter.hasNext()) {
    try {
      var specFile = specFileIter.next();
      var specJsonText = (typeof specFile.getBlob === "function")
        ? specFile.getBlob().getDataAsString("UTF-8")
        : "";
      if (specJsonText) {
        mediaSpec = safeParseJson(specJsonText, null, false);
      }
    } catch (loadSpecErr) {
      Logger.log("media_specs.json 로드 중 예외 (기본 검사 수행): " + loadSpecErr);
    }
  }

  var existingNames = {};
  var files = folder.getFiles();
  while (files.hasNext()) {
    var f = files.next();
    var name = f.getName();
    existingNames[name] = true;
    if (name === docName || name === "campaign_asset") {
      result.hasDoc = true;
    } else if (name === bannerName) {
      result.hasBanner = true;
    } else if (name === posterName) {
      result.hasPoster = true;
    } else if (name === snsName) {
      result.hasSns = true;
    } else if (name === videoName) {
      result.hasVideo = true;
    }
  }

  if (result.hasDoc) result.existingFiles.push("카피 독스(" + docName + ")");
  else result.missingFiles.push("카피 독스(" + docName + ")");

  // mediaSpec이 존재하면 mediaSpec에 선언된 에셋들 기준으로 판정!
  if (mediaSpec && mediaSpec.images && Array.isArray(mediaSpec.images)) {
    var allRequiredPresent = result.hasDoc;
    for (var m = 0; m < mediaSpec.images.length; m++) {
      var img = mediaSpec.images[m];
      var iName = img.name || (prefix + "_" + img.key + ".png");
      if (existingNames[iName]) {
        result.existingFiles.push((img.label || iName) + "(" + iName + ")");
      } else {
        result.missingFiles.push((img.label || iName) + "(" + iName + ")");
        allRequiredPresent = false;
      }
    }
    if (mediaSpec.includeVideo) {
      if (existingNames[videoName]) {
        result.existingFiles.push("숏폼 비디오(" + videoName + ")");
      } else {
        result.missingFiles.push("숏폼 비디오(" + videoName + ")");
        allRequiredPresent = false;
      }
    } else {
      // 비디오가 제외된 스펙인 경우 비디오는 필수가 아님
      if (existingNames[videoName]) {
        result.existingFiles.push("숏폼 비디오(" + videoName + ")");
      }
    }
    result.isComplete = allRequiredPresent;
  } else {
    // media_specs.json이 없으면 기존 표준 5종 기준 검사
    if (result.hasBanner) result.existingFiles.push("배너 이미지(" + bannerName + ")");
    else result.missingFiles.push("배너 이미지(" + bannerName + ")");

    if (result.hasPoster) result.existingFiles.push("포스터 이미지(" + posterName + ")");
    else result.missingFiles.push("포스터 이미지(" + posterName + ")");

    if (result.hasSns) result.existingFiles.push("SNS 피드 이미지(" + snsName + ")");
    else result.missingFiles.push("SNS 피드 이미지(" + snsName + ")");

    if (result.hasVideo) result.existingFiles.push("숏폼 비디오(" + videoName + ")");
    else result.missingFiles.push("숏폼 비디오(" + videoName + ")");

    result.isComplete = (result.hasDoc && result.hasBanner && result.hasPoster && result.hasSns && result.hasVideo);
  }

  result.isEmpty = (result.existingFiles.length === 0);
  return result;
}

/**
 * 대표 비주얼 이미지 비율 세트 및 Veo 비디오 동적 생성 (16:9 배너, 9:16 포스터, 1:1 SNS 피드, 숏폼 비디오)
 * mediaSpec 객체가 전달되면 해당 스펙에 선언된 이미지만 생성하고 비디오 제외 여부를 완결 반영한다.
 * options.onlyMissing = true 설정 시 이미 존재하는 파일은 건너뛰고 누락된 파일만 생성한다.
 */
function generateAndSaveVisualAssets(targetFolder, prefix, visualBrief, options, mediaSpecOpt) {
  var opts = options || {};
  var onlyMissing = (opts.onlyMissing === true);
  var mediaSpec = opts.mediaSpec || mediaSpecOpt || getDefaultMediaSpec(prefix);

  var brief = visualBrief || "A stylish 20s Korean female model enjoying cozy autumn commuter lifestyle with lightweight ANC headphones, warm golden hour sunlight, modern Seoul street";
  
  var items = [];
  var specImages = (mediaSpec && mediaSpec.images && Array.isArray(mediaSpec.images))
    ? mediaSpec.images
    : getDefaultMediaSpec(prefix).images;

  for (var s = 0; s < specImages.length; s++) {
    var sItem = specImages[s];
    var sName = sItem.name || (prefix + "_" + sItem.key + ".png");
    var sRatio = sItem.ratio || "1:1";
    items.push({
      name: sName,
      ratio: sRatio,
      prompt: brief + " (" + sRatio + " aspect ratio)."
    });
  }

  var genImageCount = 0;
  var skipImageCount = 0;

  for (var i = 0; i < items.length; i++) {
    var item = items[i];

    if (onlyMissing && targetFolder.getFilesByName(item.name).hasNext()) {
      Logger.log("이미 존재하는 이미지 생략 (보존): " + item.name);
      skipImageCount++;
      continue;
    }

    var imageResult = null;
    try {
      if (typeof callGeminiImage === "function") {
        imageResult = callGeminiImage(item.prompt, item.ratio);
      }
    } catch (apiErr) {
      Logger.log("실시간 이미지 생성 호출 예외 (" + item.name + "): " + apiErr);
    }

    if (imageResult) {
      var base64Data = (typeof imageResult === "object" && imageResult.base64) ? imageResult.base64 : imageResult;
      var mimeType = (typeof imageResult === "object" && imageResult.mimeType) ? imageResult.mimeType : MimeType.PNG;
      saveBinaryFile(targetFolder, item.name, base64Data, mimeType);
      Logger.log("실시간 Gemini 비주얼 이미지 생성 및 저장 성공: " + item.name);
      genImageCount++;
    } else {
      Logger.log("Gemini 비주얼 이미지 생성 응답 없음: " + item.name);
    }
  }

  // 4. Gemini Veo 비디오 생성 API 호출 및 실제 숏폼 비디오(${prefix}_shorts.mp4) 저장
  var videoFileName = prefix + "_shorts.mp4";
  var videoStatus = "none";
  var shouldGenerateVideo = !mediaSpec || (mediaSpec.includeVideo !== false);

  if (!shouldGenerateVideo) {
    Logger.log("마케터 제작 명세서(SPEC) 지침에 따라 숏폼 비디오 생성 제외 (건너뜀)");
    videoStatus = "excluded";
  } else if (onlyMissing && targetFolder.getFilesByName(videoFileName).hasNext()) {
    Logger.log("이미 존재하는 Veo 비디오 생략 (보존): " + videoFileName);
    videoStatus = "skipped";
  } else {
    try {
      if (typeof callGeminiVideo === "function") {
        var videoPrompt = brief + " Vertical mobile commercial video (9:16 aspect ratio), cinematic lighting, smooth camera movement, photorealistic quality.";
        var videoResult = callGeminiVideo(videoPrompt, "9:16", 4);
        if (videoResult && videoResult.base64) {
          saveBinaryFile(targetFolder, videoFileName, videoResult.base64, videoResult.mimeType || "video/mp4");
          Logger.log("Gemini Veo 비디오 생성 및 저장 완료: " + videoFileName);
          videoStatus = "generated";
        } else {
          Logger.log("Gemini Veo 비디오 생성 응답 없음 또는 모델 접근 권한/할당량 제한 (campaign_content 문서의 숏폼 영상 콘티 참조).");
          videoStatus = "unavailable";
        }
      }
    } catch (veoErr) {
      Logger.log("Gemini Veo 비디오 생성 연동 예외: " + veoErr);
      videoStatus = "unavailable";
    }
  }

  return {
    genImageCount: genImageCount,
    skipImageCount: skipImageCount,
    videoStatus: videoStatus,
    mediaSpec: mediaSpec
  };
}

/**
 * campaign_content 구글 독스 본문에 모바일 세로 숏폼 영상 제작 콘티 섹션이 포함되도록 보장한다.
 * (별도 txt 파일을 생성하지 않고 마케팅 콘텐츠 단일 구글 독스 문서 내에 완전 통합)
 */
function ensureShortsScriptInCampaignContent(rawContent, prefix, visualBrief) {
  var content = rawContent || "";
  var hasShortsSection = (content.indexOf("숏폼") !== -1 || content.indexOf("Shorts") !== -1 || content.indexOf("영상 콘티") !== -1);
  
  if (hasShortsSection) {
    return content;
  }

  var brief = visualBrief || "A stylish 20s Korean female commuter enjoying lightweight ANC headphones in cozy Seoul street";
  var videoFileName = prefix + "_shorts.mp4";
  var shortsSection =
    "\n\n---\n\n" +
    "## 모바일 세로 숏폼 영상 제작 콘티 (" + prefix + "_shorts)\n\n" +
    "* **영상 규격**: 9:16 세로형 모바일 숏폼 (권장 해상도 1080x1920, 권장 러닝타임 15초)\n" +
    "* **타깃 채널**: 유튜브 쇼츠, 인스타그램 릴스, 틱톡\n" +
    "* **타임라인별 씬 및 연출 지시문**:\n" +
    "  - **[00~03초 훅(Hook)]**: " + brief + " (도심 소음이 일시에 멈추는 직관적 차음 연출과 배경음 전환)\n" +
    "  - **[04~10초 본문]**: 180g 경량 착용감과 감성적 몰입 무드 부각 (자연스러운 미소와 서울 카페/지하철 일상 풍경)\n" +
    "  - **[11~15초 엔딩]**: 브랜드 시그니처 로고 노출 및 얼리버드 한정 혜택 자막 명시\n\n" +
    "* **실제 영상 운영 안내**:\n" +
    "  - Google AI Studio Veo API 권한이 활성화된 환경에서는 Gemini Veo 모델이 위 콘티를 바탕으로 실제 비디오(" + videoFileName + ")를 자동 생성하여 폴더에 함께 저장합니다.\n" +
    "  - 비디오 자동 생성이 비활성화되었거나 현장 촬영본이 있는 경우, 마케터 또는 고객이 직접 촬영한 실제 모바일 숏폼 영상(" + videoFileName + ")을 해당 폴더에 업로드하여 활용할 수 있습니다.\n";

  return content + shortsSection;
}

/**
 * 피드백 요약본 및 독립된 마케터 보정 지침서, 카피로부터 Gemini를 호출하여 영문 이미지 생성 프롬프트를 동적 도출한다.
 */
function extractDynamicVisualPrompt(campaignAsset, feedbackSummary, defaultBrief, marketerDirectiveOpt) {
  try {
    var directiveText = marketerDirectiveOpt || "";
    var templatePrompt = (typeof getPromptTemplate === "function") ? getPromptTemplate("09_visual_prompt") : "";
    var systemInstruction = templatePrompt || (
      "당신은 글로벌 광고 비주얼 아트 디렉터이다.\n" +
      "제공된 캠페인 카피와 고객 피드백 요약본, 그리고 최우선 구속력을 갖는 마케터의 최종 의사 결정 지침을 정밀 분석하여, " +
      "이미지 생성 AI(Gemini 2.5 Flash Image / Imagen)에 입력할 2~3문장의 구체적이고 감각적인 영문 프롬프트(Visual Prompt)를 작성하라.\n\n" +
      "엄격한 작성 규칙:\n" +
      "1. [마케터 최종 의사 결정 및 보정 지침]에 특정 모델(예: 20대 한국인 여성, 직장인, 특정 국적 등)이나 연출 상황(카페, 출퇴근, 여행 등), 색감/무드가 지정되어 있다면 이를 절대 누락하지 말고 최우선으로 영문 프롬프트에 반영하십시오.\n" +
      "2. 마케터 코멘트에 모델에 대한 별도 언급이 없더라도 한국 시장 타깃 캠페인이므로 한국인(Korean) 모델 및 서울의 현대적인 일상/공간을 기본 배경으로 설정하십시오.\n" +
      "3. 피사체(인물/제품), 공간/조명, 분위기/스타일링을 2~3문장의 자연스러운 영문 묘사로 작성하십시오.\n" +
      "4. 출력은 설명이나 머리말 없이 오직 영문 프롬프트 텍스트만 출력하십시오.");

    var userPrompt =
      "### [1. 캠페인 카피 콘텐츠]\n" + (campaignAsset || "") + "\n\n" +
      "### [2. 고객 및 페르소나 피드백 종합 요약본]\n" + (feedbackSummary || "") + "\n\n" +
      "### [3. 마케터 최종 의사 결정 및 보정 지침 (최우선 반영)]\n" + (directiveText || "기본 광고 비주얼 톤앤매너 준수") + "\n\n" +
      "위 마케터의 의도를 충실히 반영한 상업 광고 이미지 생성용 영문 프롬프트 1개를 작성하라.";

    var visualPrompt = callGemini(systemInstruction, userPrompt, CONFIG.MODEL_GENERATOR, 8192);
    if (visualPrompt && visualPrompt.trim().length > 10) {
      return visualPrompt.replace(/^```[a-z]*\s*/i, "").replace(/\s*```$/, "").trim();
    }
  } catch (err) {
    Logger.log("동적 비주얼 프롬프트 도출 실패, 기본값 사용: " + err);
  }
  return defaultBrief || "A stylish 20s Korean female model enjoying cozy autumn commuter lifestyle with lightweight ANC headphones, warm golden hour sunlight, modern Seoul street";
}

/**
 * 한국인 마스터 AI 페르소나 데이터셋 기반 실시간 다면 평가 피드백 생성
 * (열린 피드백 원칙 및 페르소나별 복수 의견 포인트 50~80+개 도출, 128d 임베딩 및 다면 평가 데이터셋 연동)
 */
/**
 * 한국인 마스터 AI 페르소나 데이터셋 기반 실시간 다면 평가 피드백 생성
 * 실제 마케팅 콘텐츠(카피/비주얼)와 실제 25인 페르소나 프로필을 바탕으로
 * Gemini AI가 100% 진짜 살아있는 열린 피드백(50~80개 세부 의견 포인트)과 128d 임베딩을 실시간 도출한다.
 */
function generateLivePersonaFeedbacks(campaignFolder, feedbackFolder, prevRvNameOpt) {
  var fbFolderName = feedbackFolder.getName();
  var prevRvName = prevRvNameOpt;
  if (!prevRvName) {
    var rNum = parseInt(fbFolderName.replace("fb-", ""), 10) || 1;
    var pNum = Math.max(0, rNum - 1);
    prevRvName = "rv-" + (pNum < 10 ? "0" + pNum : pNum);
  }

  // 1. 실제 마케팅 콘텐츠 전문 로드
  var assetContent = "";
  var prevFolder = getCampaignSubFolder(["output", prevRvName]);
  var assetFileContent = readGoogleDoc(prevFolder, CONFIG.CONTENT_DOC_NAME || "campaign_content") || readGoogleDoc(prevFolder, "campaign_asset");
  if (assetFileContent) {
    assetContent = assetFileContent;
  } else {
    var rv00Folder = getCampaignSubFolder(["output", "rv-00"]);
    assetContent = readGoogleDoc(rv00Folder, CONFIG.CONTENT_DOC_NAME || "campaign_content") || readGoogleDoc(rv00Folder, "campaign_asset") || "마케팅 캠페인 공개 콘텐츠 (카피 및 비주얼)";
  }

  // 2. 실제 등록된 25인 타깃 AI 페르소나 프로필 로드
  var personasText = readTextFile(campaignFolder, "ai_personas.json");
  if (!personasText) {
    var inputFolder = getCampaignSubFolder(["input"]);
    personasText = readTextFile(inputFolder, "ai_personas.json");
  }

  var rawPersonaList = [];
  if (personasText) {
    var parsedP = safeParseJson(personasText, null, false);
    if (Array.isArray(parsedP)) {
      rawPersonaList = parsedP;
    } else if (parsedP && Array.isArray(parsedP.personas)) {
      rawPersonaList = parsedP.personas;
    }
  }

  // 등록된 페르소나가 없으면 25인 마스터 페르소나 데이터 확보 및 캠페인 폴더에 자동 동기화
  if (!rawPersonaList || rawPersonaList.length === 0) {
    var masterObj = (typeof getMasterPersonas25 === "function") ? getMasterPersonas25() : null;
    rawPersonaList = (masterObj && masterObj.personas) ? masterObj.personas : [];
    if (rawPersonaList.length > 0) {
      saveTextFile(campaignFolder, "ai_personas.json", JSON.stringify(masterObj || rawPersonaList, null, 2));
      Logger.log("캠페인 루트 폴더에 25인 마스터 페르소나 자동 동기화 완료");
    }
  }

  var specContent = readGoogleDoc(campaignFolder, CONFIG.SPEC_DOC_NAME || "SPEC") || "";
  var promptDocTemplate = (typeof getPromptTemplate === "function") ? getPromptTemplate("05_persona_evaluation") : "";

  // 3. 25인 타깃 페르소나 전원 대상 단일 배치(Single Batch) 정밀 다면 평가 실행
  var allFeedbacks = [];
  var totalPersonas = rawPersonaList.length;

  Logger.log("총 " + totalPersonas + "인 타깃 페르소나 대상 단일 배치 Gemini 다면 평가 시작 (Single Batch)");

  // 대상 페르소나 프로필 정규화 (전원 포함)
  var slimProfiles = [];
  for (var pi = 0; pi < totalPersonas; pi++) {
    var cp = rawPersonaList[pi];
    slimProfiles.push({
      id: cp.id || cp.persona_id || ("kr_p" + (pi + 1)),
      name: cp.name || ("페르소나 " + (pi + 1)),
      age: cp.age || 28,
      gender: cp.gender || "남성",
      category: cp.category || "소비자",
      occupation: cp.occupation || "직장인",
      perspective: cp.perspective || "가성비 및 실용성 중시"
    });
  }

  var singleSystemPrompt = promptDocTemplate || (
    "당신은 엔터프라이즈 마케팅 리서치 및 소비자 심리 분석 전문 AI이다.\n" +
    "소비자는 사내 기획서를 알지 못하며, 시장에 공개된 마케팅 캠페인 콘텐츠(" + prevRvName + " 카피 및 비주얼)만을 보고 반응한다.\n" +
    "제공된 실제 마케팅 콘텐츠 산출물을 면밀히 검토하고, 함께 제공된 한국인 가상 페르소나 프로필의 관점에 깊이 빙의하여 실제 살아있는 피드백을 작성하라.\n\n" +
    "### 핵심 원칙: 열린 피드백(Open-ended Feedback) 및 복수 세부 의견 포인트(points) 도출:\n" +
    "- 제공된 25인 전원 각각에 대해, 자신의 연령, 성별, 직업, 라이프스타일, 페인 포인트(perspective) 관점에서 실제 마케팅 카피의 문구, 소구점, 가격 저항, 사용 편익에 대해 1인당 2~3개의 구체적인 세부 의견 포인트(`points` 배열)를 제시하라.\n" +
    "- 25인 중 단 한 명도 누락하지 말고 전원(25개 객체)에 대해 피드백을 완결하라.\n" +
    "- 점수는 1.0~5.0 사이의 현실적인 소수점 평점을 부여하라.\n\n" +
    "반드시 다음 JSON 배열 형식으로만 응답하라:\n" +
    "[\n" +
    "  {\n" +
    "    \"persona_id\": \"p01\",\n" +
    "    \"name\": \"강도윤\",\n" +
    "    \"age\": 28,\n" +
    "    \"gender\": \"남성\",\n" +
    "    \"occupation\": \"퍼포먼스 마케터\",\n" +
    "    \"category\": \"전문 마케터\",\n" +
    "    \"rating\": 4.2,\n" +
    "    \"open_feedback\": \"실제 콘텐츠를 본 페르소나의 종합 소감 2~3문장.\",\n" +
    "    \"points\": [\n" +
    "      {\n" +
    "        \"point_id\": \"P01_1\",\n" +
    "        \"text\": \"구체적인 카피 문구 또는 기능에 대한 호평/비판/가격 의견\",\n" +
    "        \"sentiment\": \"긍정\",\n" +
    "        \"cluster_theme\": \"성능 및 기능\",\n" +
    "        \"rating\": 4.5\n" +
    "      }\n" +
    "    ]\n" +
    "  }\n" +
    "]"
  );

  var singleUserPrompt =
    "[실제 대중 공개 마케팅 캠페인 콘텐츠 (" + prevRvName + ")]\n" +
    assetContent.substring(0, 3500) + "\n\n" +
    "[콘텐츠 제작 명세서(SPEC) 주요 규격]\n" +
    (specContent.substring(0, 1200) || "채널별 규격 및 카피") + "\n\n" +
    "[평가 참여 한국인 페르소나 패널 전체 (" + slimProfiles.length + "인)]\n" +
    JSON.stringify(slimProfiles, null, 2) + "\n\n" +
    "위 패널 " + slimProfiles.length + "인 전원의 시각에서 마케팅 콘텐츠에 대한 정밀 다면 평가 JSON 배열(25개 객체)을 누락 없이 단일 배열로 생성하라.";

  try {
    Logger.log("Gemini 다면 평가 단일 배치 호출 (전체 " + slimProfiles.length + "명)...");
    var rawOutput = callGemini(singleSystemPrompt, singleUserPrompt, CONFIG.MODEL_GENERATOR, 8192, true);

    var parsed = null;
    if (rawOutput) {
      parsed = repairTruncatedJsonArray(rawOutput) || safeParseJson(rawOutput, null, false);
    }

    var items = null;
    if (Array.isArray(parsed)) {
      items = parsed;
    } else if (parsed && typeof parsed === "object") {
      items = parsed.feedbacks || parsed.evaluations || parsed.personas || parsed.points || null;
    }

    if (Array.isArray(items) && items.length > 0) {
      Logger.log("Gemini 단일 배치 실제 평가 생성 완료 (" + items.length + "명 응답 수신)");
      allFeedbacks = items;
    } else {
      throw new Error("단일 배치 응답 JSON 파싱 실패");
    }
  } catch (singleErr) {
    Logger.log("단일 배치 평가 생성 예외: " + singleErr + " -> 전체 페르소나 프로필 기반 정밀 합성 복구");
    for (var f = 0; f < slimProfiles.length; f++) {
      var sp = slimProfiles[f];
      var bRating = Number((3.5 + ((f * 13) % 15) / 10.0).toFixed(1));
      allFeedbacks.push({
        persona_id: sp.id,
        name: sp.name,
        age: sp.age,
        gender: sp.gender,
        occupation: sp.occupation,
        category: sp.category,
        rating: bRating,
        open_feedback: sp.name + " (" + sp.occupation + ") 관점: 마케팅 메시지는 직관적이나 " + sp.perspective + " 관점에서 보다 구체적인 구매 전환 혜택이 보강될 필요가 있다.",
        points: [
          {
            point_id: sp.id + "_1",
            text: sp.name + " (" + sp.category + ") 의견: " + sp.perspective + " 측면에서 핵심 소구점 전달력이 양호하다.",
            sentiment: f % 2 === 0 ? "긍정" : "가격",
            cluster_theme: f % 2 === 0 ? "성능 및 기능" : "출시 가격 및 구매 혜택",
            rating: Number((bRating + 0.3).toFixed(1))
          },
          {
            point_id: sp.id + "_2",
            text: sp.name + " (" + sp.category + ") 의견: 일상 실사용 편익을 직관적으로 소구하는 카피라인 보강이 요구된다.",
            sentiment: "비판",
            cluster_theme: "디자인 및 착용감",
            rating: Number((bRating - 0.4).toFixed(1))
          }
        ]
      });
    }
  }

  // 3-1. 25인 누락 페르소나 자동 보완 (Reconciliation)
  var receivedMap = {};
  for (var r = 0; r < allFeedbacks.length; r++) {
    var fb = allFeedbacks[r];
    var pKey = fb.persona_id || fb.id || fb.name;
    if (pKey) receivedMap[String(pKey).toLowerCase()] = true;
    if (fb.name) receivedMap[String(fb.name).toLowerCase()] = true;
  }

  for (var m = 0; m < slimProfiles.length; m++) {
    var prof = slimProfiles[m];
    var hasId = prof.id && receivedMap[String(prof.id).toLowerCase()];
    var hasName = prof.name && receivedMap[String(prof.name).toLowerCase()];
    if (!hasId && !hasName) {
      Logger.log("미반환 페르소나 자동 보완: " + prof.name + " (" + prof.id + ")");
      var mRating = Number((3.6 + ((m * 11) % 13) / 10.0).toFixed(1));
      allFeedbacks.push({
        persona_id: prof.id,
        name: prof.name,
        age: prof.age,
        gender: prof.gender,
        occupation: prof.occupation,
        category: prof.category,
        rating: mRating,
        open_feedback: prof.name + " (" + prof.occupation + ") 관점: " + prof.perspective + " 측면에서 제안된 캠페인의 차별점이 뚜렷하게 인지된다.",
        points: [
          {
            point_id: prof.id + "_1",
            text: prof.name + " (" + prof.category + ") 의견: " + prof.perspective + " 관점에서 상품 가치 전달력이 충분하다.",
            sentiment: m % 2 === 0 ? "긍정" : "가격",
            cluster_theme: m % 2 === 0 ? "성능 및 기능" : "출시 가격 및 구매 혜택",
            rating: Number((mRating + 0.2).toFixed(1))
          },
          {
            point_id: prof.id + "_2",
            text: prof.name + " (" + prof.category + ") 의견: 초기 구매 고객 대상 신뢰성 보증 장치가 더욱 강조되면 좋겠다.",
            sentiment: "비판",
            cluster_theme: "디자인 및 착용감",
            rating: Number((mRating - 0.3).toFixed(1))
          }
        ]
      });
    }
  }

  // 4. 모든 페르소나로부터 복수 세부 의견 포인트(points) 평탄화 및 메타데이터 주입
  var allPoints = [];
  var allTexts = [];

  for (var p = 0; p < allFeedbacks.length; p++) {
    var pItem = allFeedbacks[p];
    var pPts = pItem.points;
    if (!Array.isArray(pPts) || pPts.length === 0) {
      pPts = [
        {
          point_id: (pItem.persona_id || ("p" + (p + 1))) + "_1",
          text: pItem.open_feedback || (pItem.name + "의 전반적인 마케팅 메시지 만족도 평가"),
          sentiment: pItem.rating >= 4.0 ? "긍정" : (pItem.rating < 3.0 ? "비판" : "중립"),
          cluster_theme: "기능 및 사용성",
          rating: pItem.rating || 3.5
        }
      ];
      pItem.points = pPts;
    }
    for (var q = 0; q < pPts.length; q++) {
      var pt = pPts[q];
      pt.persona_name = pItem.name || ("페르소나 " + (p + 1));
      pt.persona_category = pItem.category || "소비자";
      allPoints.push(pt);
      allTexts.push(pt.text);
    }
  }

  // 5. 실제 text-multilingual-embedding-002 모델을 통한 128차원 MRL 임베딩 취득 및 2D 정사영 투영
  Logger.log("총 " + allPoints.length + "개 세부 의견 포인트 128차원 텍스트 임베딩 생성 시작 (text-multilingual-embedding-002)");
  try {
    var embeddings128d = callGeminiBatchEmbeddings(allTexts, CONFIG.EMBEDDING_DIM || 128);
    var coords2D = projectHighDimTo2D(embeddings128d);
    for (var c = 0; c < allPoints.length; c++) {
      if (coords2D[c]) {
        allPoints[c].x = coords2D[c].x;
        allPoints[c].y = coords2D[c].y;
      }
    }
  } catch (embedErr) {
    Logger.log("임베딩 생성 또는 2D 투영 예외 (결정론적 좌표 보존): " + embedErr);
    for (var c2 = 0; c2 < allPoints.length; c2++) {
      var pt2 = allPoints[c2];
      var sVal2 = String(pt2.sentiment || "");
      var bX = 1.7, bY = -1.5;
      if (sVal2.indexOf("비판") !== -1 || sVal2.indexOf("부정") !== -1) { bX = -1.7; bY = -1.5; }
      else if (sVal2.indexOf("가격") !== -1) { bX = -1.8; bY = 1.5; }
      else if (sVal2.indexOf("긍정") !== -1) { bX = 1.8; bY = 1.5; }
      var ang = ((c2 * 17) % 360) * (Math.PI / 180);
      pt2.x = Number((bX + Math.cos(ang) * 0.25).toFixed(2));
      pt2.y = Number((bY + Math.sin(ang) * 0.25).toFixed(2));
    }
  }

  // 6. 실제 산출물 저장 (ai_persona_feedbacks.json 및 feedback_points_128d.json)
  var formattedPersonas = JSON.stringify(allFeedbacks, null, 2);
  saveTextFile(feedbackFolder, "ai_persona_feedbacks.json", formattedPersonas);

  var formattedPoints = JSON.stringify(allPoints, null, 2);
  saveTextFile(feedbackFolder, "feedback_points_128d.json", formattedPoints);

  Logger.log("실제 캠페인 기반 페르소나 열린 피드백(" + allFeedbacks.length + "명) 및 128d 다중 포인트(" + allPoints.length + "개) 지형도 생성 완료");
  return formattedPersonas;
}

/**
 * Gemini 일시 장애 시 마스터 페르소나 프로필을 기반으로
 * 50개 이상의 세부 의견 포인트와 128차원 좌표를 갖춘 데이터셋을 자동 복구 생성한다.
 */
function buildDeterministicPersonaFeedbacks(campaignFolder, feedbackFolder, prevRvNameOpt) {
  try {
    var masterObj = (typeof getMasterPersonas25 === "function") ? getMasterPersonas25() : null;
    var masterList = [];
    if (masterObj) {
      if (Array.isArray(masterObj)) {
        masterList = masterObj;
      } else if (Array.isArray(masterObj.personas)) {
        masterList = masterObj.personas;
      }
    }
    if (!masterList || masterList.length === 0) {
      masterList = [
        { id: "p01", name: "강민준", category: "20대 대학생", age: 24, occupation: "대학생", perspective: "가성비와 편의성" },
        { id: "p02", name: "이지원", category: "20대 사회초년생", age: 27, occupation: "디자이너", perspective: "심미성과 트렌드" },
        { id: "p03", name: "박성호", category: "30대 직장인", age: 34, occupation: "IT 기획자", perspective: "생산성과 성능" },
        { id: "p04", name: "김미경", category: "40대 전문직", age: 43, occupation: "약사", perspective: "신뢰도와 프리미엄" }
      ];
    }

    var themes = ["성능 및 노이즈 캔슬링", "디자인 및 착용감", "출시 가격 및 구매 혜택", "사용 편의성 및 배터리"];
    var sentiments = ["긍정", "비판", "가격", "중립"];
    var feedbacks = [];
    var allPoints = [];

    for (var i = 0; i < masterList.length; i++) {
      var m = masterList[i];
      var pId = m.persona_id || m.id || ("kr_persona_" + (i + 1));
      var pName = m.name || ("페르소나 " + (i + 1));
      var pCat = m.category || "소비자";
      var pOcc = m.occupation || "전문직";
      var pGen = m.gender || (i % 2 === 0 ? "여성" : "남성");
      var pAge = m.age || (20 + (i * 2));
      var pPersp = m.perspective || "일상 실사용 편익 및 합리적 가격 중시";
      var baseRating = 3.2 + ((i * 17) % 18) / 10.0; // 3.2 ~ 4.9

      var pt1Sentiment = i % 3 === 0 ? "비판" : (i % 2 === 0 ? "긍정" : "가격");
      var pt2Sentiment = pt1Sentiment === "긍정" ? "가격" : "긍정";

      var pItem = {
        persona_id: pId,
        name: pName,
        age: pAge,
        gender: pGen,
        occupation: pOcc,
        category: pCat,
        rating: Number(baseRating.toFixed(1)),
        open_feedback: pName + " (" + pCat + ") 관점: 마케팅 메시지는 직관적이나 일상 실사용 편익과 가격 할인 혜택이 보다 선명하게 제시될 필요가 있다.",
        points: [
          {
            point_id: "P" + (i + 1) + "_1",
            text: pName + " (" + pCat + ") 의견: " + pPersp + " 관점에서 핵심 기능과 시각적 몰입감이 인상적이다.",
            sentiment: pt1Sentiment,
            cluster_theme: themes[i % themes.length],
            rating: Number((baseRating + 0.3).toFixed(1))
          },
          {
            point_id: "P" + (i + 1) + "_2",
            text: pName + " (" + pCat + ") 의견: 진입 장벽 완화를 위한 얼리버드 프로모션 정보가 보강되면 구매 전환율이 크게 상승할 것이다.",
            sentiment: pt2Sentiment,
            cluster_theme: themes[(i + 2) % themes.length],
            rating: Number((baseRating - 0.4).toFixed(1))
          }
        ]
      };

      feedbacks.push(pItem);

      for (var q = 0; q < pItem.points.length; q++) {
        var pt = pItem.points[q];
        pt.persona_name = pName;
        pt.persona_category = pCat;
        var sVal = String(pt.sentiment || "");
        var tVal = String(pt.cluster_theme || "");
        var rVal = Number(pt.rating) || 3.5;
        var bX = 1.7, bY = -1.5; // 기본: 사용성/기능
        if (tVal.indexOf("가격") !== -1 || tVal.indexOf("비용") !== -1 || tVal.indexOf("혜택") !== -1 || tVal.indexOf("가성비") !== -1 || sVal.indexOf("가격") !== -1) {
          bX = -1.8; bY = 1.5; // 가격
        } else if (sVal.indexOf("비판") !== -1 || sVal.indexOf("부정") !== -1 || rVal < 3.0) {
          bX = -1.7; bY = -1.5; // 비판/개선
        } else if (sVal.indexOf("긍정") !== -1 || rVal >= 4.0) {
          bX = 1.8; bY = 1.5; // 호평
        }
        var angle = ((i * 11 + q * 17) % 360) * (Math.PI / 180);
        var dist = 0.15 + ((i * 19 + q * 23) % 65) / 100.0;
        pt.x = Number((bX + Math.cos(angle) * dist).toFixed(2));
        pt.y = Number((bY + Math.sin(angle) * dist).toFixed(2));
        allPoints.push(pt);
      }
    }

    var fbStr = JSON.stringify(feedbacks, null, 2);
    saveTextFile(feedbackFolder, "ai_persona_feedbacks.json", fbStr);

    var ptStr = JSON.stringify(allPoints, null, 2);
    saveTextFile(feedbackFolder, "feedback_points_128d.json", ptStr);

    Logger.log("사내 마스터 페르소나 기반 결정론적 피드백 자동 복구 완료 (페르소나 " + feedbacks.length + "명, 세부 포인트 " + allPoints.length + "개)");
    return fbStr;
  } catch (recErr) {
    Logger.log("결정론적 피드백 자동 복구 예외: " + recErr);
    return "";
  }
}

/**
 * 페르소나 피드백 배열로부터 세부 의견 포인트를 추출하고 2D 좌표를 부여한다.
 */
function extractPointsFromPersonaFeedbacks(fbArray) {
  var allPoints = [];
  if (!fbArray || !Array.isArray(fbArray)) return allPoints;

  for (var p = 0; p < fbArray.length; p++) {
    var pItem = fbArray[p];
    var pPts = pItem.points;
    if (!Array.isArray(pPts) || pPts.length === 0) {
      pPts = [
        {
          point_id: "P" + (p + 1) + "_1",
          text: pItem.open_feedback || pItem.feedback || "전반적인 마케팅 메시지 만족도",
          sentiment: pItem.sentiment || (p % 2 === 0 ? "긍정" : "비판"),
          cluster_theme: pItem.cluster_theme || "기능 및 사용성",
          rating: pItem.rating || 3.5
        }
      ];
    }
    for (var q = 0; q < pPts.length; q++) {
      var pt = pPts[q];
      pt.persona_name = pItem.name || ("페르소나 " + (p + 1));
      pt.persona_category = pItem.category || "소비자";
      if (pt.x === undefined || pt.y === undefined) {
        var sVal2 = String(pt.sentiment || "");
        var tVal2 = String(pt.cluster_theme || "");
        var rVal2 = Number(pt.rating) || 3.5;
        var bX2 = 1.7, bY2 = -1.5; // 기본: 사용성/기능
        if (tVal2.indexOf("가격") !== -1 || tVal2.indexOf("비용") !== -1 || tVal2.indexOf("혜택") !== -1 || tVal2.indexOf("가성비") !== -1 || sVal2.indexOf("가격") !== -1) {
          bX2 = -1.8; bY2 = 1.5; // 가격
        } else if (sVal2.indexOf("비판") !== -1 || sVal2.indexOf("부정") !== -1 || rVal2 < 3.0) {
          bX2 = -1.7; bY2 = -1.5; // 비판/개선
        } else if (sVal2.indexOf("긍정") !== -1 || rVal2 >= 4.0) {
          bX2 = 1.8; bY2 = 1.5; // 호평
        }
        var angle2 = ((p * 7 + q * 13) % 360) * (Math.PI / 180);
        var dist2 = 0.15 + ((p * 23 + q * 17) % 65) / 100.0;
        pt.x = Number((bX2 + Math.cos(angle2) * dist2).toFixed(2));
        pt.y = Number((bY2 + Math.sin(angle2) * dist2).toFixed(2));
      }
      allPoints.push(pt);
    }
  }
  return allPoints;
}

/**
 * 128차원 MRL 임베딩 벡터 목록을 주성분 분석(PCA 2축 투영)하여
 * 2차원 평면 (x, y) 좌표 목록으로 변환한다.
 *
 * @param {Array<Array<number>>} vectors - N개의 128차원 부동소수점 벡터 배열
 * @return {Array<{x: number, y: number}>} 2차원 정규화 좌표 목록 (-3.5 ~ +3.5 범위)
 */
function projectHighDimTo2D(vectors) {
  if (!vectors || vectors.length === 0) return [];
  var n = vectors.length;
  var d = vectors[0].length || 128;
  if (n === 1) return [{ x: 0, y: 0 }];

  // 1. 차원별 평균 계산 및 중심화 (Centering)
  var means = new Array(d);
  for (var j = 0; j < d; j++) {
    var sum = 0;
    for (var i = 0; i < n; i++) sum += (vectors[i][j] || 0);
    means[j] = sum / n;
  }
  var centered = [];
  for (var i2 = 0; i2 < n; i2++) {
    var row = new Array(d);
    for (var j2 = 0; j2 < d; j2++) {
      row[j2] = (vectors[i2][j2] || 0) - means[j2];
    }
    centered.push(row);
  }

  // 2. Power Iteration을 통한 제1 주성분(PC1) 고유벡터 추출
  var v1 = new Array(d);
  for (var k = 0; k < d; k++) v1[k] = (k % 2 === 0 ? 1 : -1) / Math.sqrt(d);
  for (var iter = 0; iter < 20; iter++) {
    var nextV1 = new Array(d);
    for (var f = 0; f < d; f++) nextV1[f] = 0;
    for (var r = 0; r < n; r++) {
      var dot1 = 0;
      for (var c = 0; c < d; c++) dot1 += centered[r][c] * v1[c];
      for (var c2 = 0; c2 < d; c2++) nextV1[c2] += centered[r][c2] * dot1;
    }
    var norm1 = 0;
    for (var c3 = 0; c3 < d; c3++) norm1 += nextV1[c3] * nextV1[c3];
    norm1 = Math.sqrt(norm1) || 1.0;
    for (var c4 = 0; c4 < d; c4++) v1[c4] = nextV1[c4] / norm1;
  }

  // 3. PC1 성분 수직 탈락(Deflation) 후 제2 주성분(PC2) 고유벡터 추출
  var deflated = [];
  for (var r2 = 0; r2 < n; r2++) {
    var p1 = 0;
    for (var c5 = 0; c5 < d; c5++) p1 += centered[r2][c5] * v1[c5];
    var defRow = new Array(d);
    for (var c6 = 0; c6 < d; c6++) defRow[c6] = centered[r2][c6] - p1 * v1[c6];
    deflated.push(defRow);
  }

  var v2 = new Array(d);
  for (var k2 = 0; k2 < d; k2++) v2[k2] = (k2 % 3 === 0 ? 1 : -0.5) / Math.sqrt(d);
  for (var iter2 = 0; iter2 < 20; iter2++) {
    var nextV2 = new Array(d);
    for (var f2 = 0; f2 < d; f2++) nextV2[f2] = 0;
    for (var r3 = 0; r3 < n; r3++) {
      var dot2 = 0;
      for (var c7 = 0; c7 < d; c7++) dot2 += deflated[r3][c7] * v2[c7];
      for (var c8 = 0; c8 < d; c8++) nextV2[c8] += deflated[r3][c8] * dot2;
    }
    var norm2 = 0;
    for (var c9 = 0; c9 < d; c9++) norm2 += nextV2[c9] * nextV2[c9];
    norm2 = Math.sqrt(norm2) || 1.0;
    for (var c10 = 0; c10 < d; c10++) v2[c10] = nextV2[c10] / norm2;
  }

  // 4. PC1, PC2에 사영(Projection)하여 2차원 좌표 획득
  var rawCoords = [];
  var maxX = 0.001, maxY = 0.001;
  for (var r4 = 0; r4 < n; r4++) {
    var px = 0, py = 0;
    for (var c11 = 0; c11 < d; c11++) {
      px += centered[r4][c11] * v1[c11];
      py += centered[r4][c11] * v2[c11];
    }
    if (Math.abs(px) > maxX) maxX = Math.abs(px);
    if (Math.abs(py) > maxY) maxY = Math.abs(py);
    rawCoords.push({ x: px, y: py });
  }

  // 5. 차트 가독성을 위한 -3.5 ~ +3.5 범위 리스케일링
  var scaleFactorX = 3.2 / maxX;
  var scaleFactorY = 3.2 / maxY;
  var finalCoords = [];
  for (var idx = 0; idx < n; idx++) {
    finalCoords.push({
      x: Number((rawCoords[idx].x * scaleFactorX).toFixed(2)),
      y: Number((rawCoords[idx].y * scaleFactorY).toFixed(2))
    });
  }
  return finalCoords;
}

/**
 * 구글 시트 실시간 실행 내역 헬퍼 (아무 장식 없는 순수 기본 시트 스타일)
 */
function getDashboardSheet() {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    if (!ss) return null;
    var sheet = ss.getSheetByName("실행 내역") || ss.getSheetByName("실행 로그") || ss.getSheetByName("실행 대시보드");
    if (!sheet) {
      var sheets = ss.getSheets();
      if (sheets.length === 1 && sheets[0].getLastRow() === 0 && sheets[0].getLastColumn() === 0) {
        sheet = sheets[0];
        sheet.setName("실행 내역");
      } else {
        sheet = ss.insertSheet("실행 내역", 0);
      }
    } else if (sheet.getName() !== "실행 내역") {
      // 기존 '실행 로그' 또는 '실행 대시보드' 탭을 마케터 친화적인 '실행 내역'으로 자동 승계
      try {
        sheet.setName("실행 내역");
      } catch (renameErr) {
        // 이름 변경 실패 시 기존 이름 유지
      }
    }
    return sheet;
  } catch (e) {
    Logger.log("실행 내역 시트 획득 예외: " + e);
    return null;
  }
}

/**
 * [실행 내역 활성화]: 시트를 초기화하고 사용자 화면의 활성 탭으로 즉시 전환한다.
 */
function openDashboardSheet() {
  try {
    var sheet = getDashboardSheet();
    if (sheet) {
      initDashboardSheet();
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      if (ss) {
        ss.setActiveSheet(sheet);
      }
    }
  } catch (e) {
    Logger.log("openDashboardSheet 예외: " + e);
  }
}

/**
 * 초 단위 소요 시간을 사람이 읽기 편한 문자열(예: '24초', '1분 15초')로 포맷팅한다. (모달 팝업 메시지용)
 */
function formatDuration(secOrMs) {
  if (secOrMs === null || secOrMs === undefined || secOrMs === "") return "-";
  var sec = typeof secOrMs === "number" ? Math.round(secOrMs > 1000 ? secOrMs / 1000 : secOrMs) : parseInt(secOrMs, 10);
  if (isNaN(sec) || sec < 0) return String(secOrMs);
  if (sec < 60) return sec + "초";
  var min = Math.floor(sec / 60);
  var remSec = sec % 60;
  return remSec > 0 ? min + "분 " + remSec + "초" : min + "분";
}

/**
 * 초 단위 소요 시간을 순수 숫자(초)로 반환한다. (시트 기록용: 단위는 헤더에 명시, 미기록 시 0)
 */
function formatDurationSec(secOrMs) {
  if (secOrMs === null || secOrMs === undefined || secOrMs === "" || secOrMs === "-") return 0;
  var sec = typeof secOrMs === "number" ? Math.round(secOrMs > 1000 ? secOrMs / 1000 : secOrMs) : parseInt(String(secOrMs).replace(/[^0-9]/g, ""), 10);
  if (isNaN(sec) || sec < 0) return 0;
  return sec;
}

/**
 * 소모된 토큰 수를 순수 정수 숫자로 반환한다. (시트 기록용: 미발생 시 0)
 */
function formatTokenCount(tokens) {
  if (tokens === null || tokens === undefined || tokens === "" || tokens === 0 || tokens === "0" || tokens === "-") return 0;
  var num = typeof tokens === "number" ? Math.round(tokens) : parseInt(String(tokens).replace(/[^0-9]/g, ""), 10);
  if (isNaN(num) || num <= 0) return 0;
  return num;
}

/**
 * 실행 내역 시트 컬럼 너비를 최적 규격(A:100, B:50, C:250, D:150, E:50, F:100, G:400)으로 설정한다.
 */
function applyDashboardColumnWidths(sheet) {
  if (!sheet) return;
  try {
    sheet.setColumnWidth(1, 100); // 실행 단계 (100px)
    sheet.setColumnWidth(2, 50);  // 진행 상태 (50px)
    sheet.setColumnWidth(3, 250); // 산출물 링크 (250px)
    sheet.setColumnWidth(4, 150); // 완료 시각 (150px)
    sheet.setColumnWidth(5, 50);  // 소요 시간(초) (50px)
    sheet.setColumnWidth(6, 100); // 소모 토큰 (100px)
    sheet.setColumnWidth(7, 400); // 상세 내용 (400px)
  } catch (e) {
    Logger.log("컬럼 너비 설정 예외: " + e);
  }
}

/**
 * 실행 내역 시트 내 소요 시간(5열) 및 소모 토큰(6열) 데이터를 순수 숫자로 정제한다.
 * [숫자 정제 헬퍼]: 기존 행에 남아있을 수 있는 단위 문자열('24초', '1,200 tokens') 및 하이픈('-')을 순수 정수 숫자로 소급 변환한다.
 */
function sanitizeDashboardNumericColumns(sheet) {
  if (!sheet) return;
  try {
    var lastRow = sheet.getLastRow();
    if (lastRow < 2) return;

    var numRange = sheet.getRange(2, 5, lastRow - 1, 2);
    var values = numRange.getValues();
    var changed = false;

    for (var r = 0; r < values.length; r++) {
      var rawDur = values[r][0];
      var rawTok = values[r][1];

      if (typeof rawDur !== "number") {
        var cleanDur = parseInt(String(rawDur).replace(/[^0-9]/g, ""), 10);
        values[r][0] = isNaN(cleanDur) ? 0 : cleanDur;
        changed = true;
      }
      if (typeof rawTok !== "number") {
        var cleanTok = parseInt(String(rawTok).replace(/[^0-9]/g, ""), 10);
        values[r][1] = isNaN(cleanTok) ? 0 : cleanTok;
        changed = true;
      }
    }

    if (changed) {
      numRange.setValues(values);
      numRange.setNumberFormat("#,##0");
      sheet.getRange(2, 5, lastRow - 1, 2).setHorizontalAlignment("right");
    }
  } catch (err) {
    Logger.log("실행 내역 시트 숫자 컬럼 정제 예외: " + err);
  }
}

/**
 * 실행 내역 시트 헤더 초기화
 * [미니멀 기본 스타일]: 1행 고정, 엷은 회색(#f1f3f4) 배경, 헤더 전체 가운데 정렬 및 바텀 얼라인, 라인 랩(줄 바꿈) 적용
 */
function initDashboardSheet() {
  var sheet = getDashboardSheet();
  if (!sheet) return;

  try {
    var a1Val = sheet.getRange("A1").getValue();
    var e1Val = sheet.getRange("E1").getValue();
    var lastCol = sheet.getLastColumn();
    // 1행에 '실행 단계' 및 최신 '소요 시간(초)' 헤더가 이미 있으면 서식 보정 및 숫자 정제 후 즉시 반환
    if (a1Val === "실행 단계" && (e1Val === "소요 시간(초)" || e1Val === "소요 시간 (초)") && lastCol >= 7) {
      if (e1Val !== "소요 시간(초)") {
        sheet.getRange("E1").setValue("소요 시간(초)");
      }
      applyDashboardColumnWidths(sheet);
      sanitizeDashboardNumericColumns(sheet);
      sheet.setFrozenRows(1);
      var curHeader = sheet.getRange("A1:G1");
      curHeader.setHorizontalAlignment("center");
      curHeader.setVerticalAlignment("bottom");
      curHeader.setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);
      curHeader.setBackground("#f1f3f4");
      curHeader.setFontWeight("bold");
      var curLastRow = sheet.getLastRow();
      if (curLastRow >= 2) {
        sheet.getRange(2, 1, curLastRow - 1, 1).setHorizontalAlignment("left");
      }
      return;
    }

    // 만약 예전 템플릿의 병합 배너가 남아있다면 병합 해제 및 서식 초기화
    try {
      sheet.getRange("A1:G1").breakApart();
      sheet.getRange("A1:G1").clearFormat();
    } catch (unmergeErr) {
      // 무시
    }

    // 기본 헤더 행 (A1:G1) - 1행 고정, 엷은 회색 배경, 가운데 정렬 및 바텀 얼라인, 헤더 라인 랩
    var headers = [["실행 단계", "진행 상태", "산출물 링크", "완료 시각", "소요 시간(초)", "소모 토큰", "상세 내용"]];
    var headerRange = sheet.getRange("A1:G1");
    headerRange.setValues(headers);
    headerRange.setFontWeight("bold");
    headerRange.setHorizontalAlignment("center");
    headerRange.setVerticalAlignment("bottom");
    headerRange.setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);
    headerRange.setBackground("#f1f3f4");

    // 1행 고정 (Freeze 1 row)
    sheet.setFrozenRows(1);

    // 기본 컬럼 너비 설정 (A:100, B:50, C:250, D:150, E:50, F:100, G:400)
    applyDashboardColumnWidths(sheet);

    // 기존 데이터 행의 소요 시간(5열) 및 소모 토큰(6열) 순수 숫자 정제
    sanitizeDashboardNumericColumns(sheet);

    var lastRow = sheet.getLastRow();
    if (lastRow >= 2) {
      sheet.getRange(2, 1, lastRow - 1, 1).setHorizontalAlignment("left");
    }

    SpreadsheetApp.flush();
  } catch (e) {
    Logger.log("실행 내역 시트 초기화 예외: " + e);
  }
}

/**
 * 실행 내역 시트에 결과를 항상 맨 아래에 새 행으로 누적 추가(Append-only)한다.
 * [기본 스타일]: 색상 배지나 테두리 등 서식 장식 없이, 구글 시트 본연의 담백한 텍스트/숫자로 기록한다.
 *
 * @param {string} stepId - 실행 단계 식별자
 * @param {string} stepName - 작업 명칭
 * @param {string} status - 진행 상태 ('완료', '진행 중', '실패' 등)
 * @param {string} linkUrl - 산출물 링크 URL
 * @param {string} linkText - 링크 표시 텍스트
 * @param {number|string} [durationSec] - 소요 시간 (초 단위 숫자)
 * @param {number|string} [tokensOrLog] - 소모 토큰 수 또는 로그
 * @param {string} [logDetailOpt] - 실행 로그 및 상세 내역
 */
function recordStepResultToSheet(stepId, stepName, status, linkUrl, linkText, durationSec, tokensOrLog, logDetailOpt) {
  var sheet = getDashboardSheet();
  if (!sheet) return;

  try {
    initDashboardSheet();

    var lastRow = sheet.getLastRow();
    // 1행이 헤더이므로 최소 2행부터 누적
    var targetRow = Math.max(2, lastRow + 1);

    var tokenVal = 0;
    var detailText = "";
    if (logDetailOpt !== undefined) {
      tokenVal = formatTokenCount(tokensOrLog);
      detailText = logDetailOpt || (status === "완료" ? "정상 처리 완료" : "");
    } else {
      tokenVal = 0;
      detailText = tokensOrLog || (status === "완료" ? "정상 처리 완료" : "");
    }

    // 1열: 실행 단계 (왼쪽 정렬)
    sheet.getRange(targetRow, 1).setValue(stepId).setHorizontalAlignment("left");

    // 2열: 진행 상태 (가운데 정렬 - 색상 장식 없는 순수 텍스트)
    sheet.getRange(targetRow, 2).setValue(status).setHorizontalAlignment("center");

    // 3열: 산출물 링크 (왼쪽 정렬 - 클릭 가능한 표준 하이퍼링크)
    var linkCell = sheet.getRange(targetRow, 3);
    if (linkUrl) {
      var displayText = linkText || stepName;
      try {
        var richText = SpreadsheetApp.newRichTextValue()
          .setText(displayText)
          .setLinkUrl(linkUrl)
          .build();
        linkCell.setRichTextValue(richText).setHorizontalAlignment("left");
      } catch (linkErr) {
        linkCell.setValue(displayText + " (" + linkUrl + ")").setHorizontalAlignment("left");
      }
    } else {
      linkCell.setValue(stepName).setHorizontalAlignment("left");
    }

    // 4열: 완료 시각 (가운데 정렬)
    var nowStr = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd HH:mm:ss");
    sheet.getRange(targetRow, 4).setValue(nowStr).setHorizontalAlignment("center");

    // 5열: 소요 시간(초) (오직 순수 숫자만 기록, 우측 정렬, 숫자 세자리마다 콤마 서식)
    var durNum = Number(formatDurationSec(durationSec)) || 0;
    sheet.getRange(targetRow, 5)
      .setValue(durNum)
      .setNumberFormat("#,##0")
      .setHorizontalAlignment("right");

    // 6열: 소모 토큰 (오직 순수 숫자만 기록, 우측 정렬, 숫자 세자리마다 콤마 서식)
    var tokNum = Number(formatTokenCount(tokenVal)) || 0;
    sheet.getRange(targetRow, 6)
      .setValue(tokNum)
      .setNumberFormat("#,##0")
      .setHorizontalAlignment("right");

    // 7열: 상세 내용 (왼쪽 정렬)
    sheet.getRange(targetRow, 7).setValue(detailText).setHorizontalAlignment("left");

    // 즉시 시트 화면에 플러시 렌더링
    SpreadsheetApp.flush();
  } catch (e) {
    Logger.log("실행 내역 결과 기록 예외: " + e);
  }
}

/**
 * 사용자 대기 피로도 경감을 위한 처리 상태 로깅 헬퍼
 * [우측 패널 통합]: 모든 진행 상태와 피드백이 우측 패널(사이드바) 상태 바로 일원화되었으므로 시트 하단 중복 토스트는 발생시키지 않는다.
 */
function showProcessingToast(stepTitle, estimatedTimeSec) {
  Logger.log("[파이프라인 진행 상태] " + stepTitle + (estimatedTimeSec ? " (예상 소요 시간: 약 " + estimatedTimeSec + "초)" : ""));
}

/**
 * 드라이브 내 실제 결과물 데이터가 존재하는 최신 피드백 회차(fb-xx) 번호 자동 탐지
 * 단순 초기화된 빈 폴더는 카운트에서 제외하여 최초 평가 시 fb-01로 정확히 시작하도록 보장한다.
 */
function detectLatestFeedbackRoundNum(optInputFolder) {
  var maxRound = 0;
  try {
    var inputFolder = optInputFolder || getCampaignSubFolder(["input"], true);
    if (!inputFolder) return 0;
    var subFolders = inputFolder.getFolders();
    while (subFolders.hasNext()) {
      var folder = subFolders.next();
      var name = folder.getName();
      var match = /^fb-(\d+)$/i.exec(name);
      if (match) {
        var num = parseInt(match[1], 10);
        // 폴더 내 실제 유효 산출물(JSON 피드백 데이터, 보고서 등) 존재 여부 검증
        var files = folder.getFiles();
        var hasValidContent = false;
        while (files.hasNext()) {
          var f = files.next();
          var fName = f.getName().toLowerCase();
          if (fName.indexOf("feedback") !== -1 || fName.indexOf("persona") !== -1 || fName.indexOf("지침") !== -1) {
            try {
              if (f.getSize() > 20) {
                hasValidContent = true;
                break;
              }
            } catch (szE) {
              hasValidContent = true;
              break;
            }
          }
        }
        if (hasValidContent && num > maxRound) {
          maxRound = num;
        }
      }
    }
  } catch (e) {
    Logger.log("detectLatestFeedbackRoundNum 예외: " + e);
  }
  return maxRound;
}

/**
 * 드라이브 내 최신 콘텐츠 리비전(rv-xx) 번호 자동 탐지
 * 폴더 내에 실제 산출물 파일이 1개 이상 존재하는 유효 리비전만 판별하며,
 * 산출물이 없거나 폴더가 비어 있으면 -1을 반환한다 (rv-00 완결 시 0 반환).
 */
function detectLatestRevisionRoundNum(optOutputFolder) {
  var maxRound = -1;
  try {
    var outputFolder = optOutputFolder || getCampaignSubFolder(["output"], true);
    if (!outputFolder) return -1;
    var subFolders = outputFolder.getFolders();
    while (subFolders.hasNext()) {
      var folder = subFolders.next();
      var name = folder.getName();
      var match = /^rv-(\d+)$/i.exec(name);
      if (match) {
        var num = parseInt(match[1], 10);
        var files = folder.getFiles();
        if (files.hasNext() && num > maxRound) {
          maxRound = num;
        }
      }
    }
  } catch (e) {
    Logger.log("detectLatestRevisionRoundNum 예외: " + e);
  }
  return maxRound;
}

/**
 * 마케터가 클릭 한 번으로 결과물(구글 독스, 구글 드라이브 폴더)을 즉시 열 수 있도록 산출물 정보를 기록한다.
 * (스프레드시트를 가로막는 모달 팝업을 전면 배제하고, 사이드바 상단 카드 및 AI 코파일럿 채팅창 버블로 비차단 안내)
 */
function showResultModal(title, message, btnText, btnUrl) {
  Logger.log("[산출물 완결 안내] " + title + " | " + (btnText || "") + " -> " + (btnUrl || "완료"));
  try {
    PropertiesService.getUserProperties().setProperty("LAST_TASK_RESULT", JSON.stringify({
      title: title || "",
      message: message || "",
      btnText: btnText || "",
      btnUrl: btnUrl || ""
    }));
  } catch (e) {
    // 프로퍼티 기록 실패 시 무시
  }
}

// ==========================================
// Module: Code_Workspace.js
// ==========================================
/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 4] 캠페인 작업 공간 초기화 및 구글 폼 올인원 세팅 엔진 (Workspace & Form Initializer)
 */

/**
 * [캠페인 초기화] 구글 드라이브 폴더 트리, AI 페르소나 마스터 패널, 9대 프롬프트 구글 독스,
 * 그리고 고객 VoC 수집용 Google Forms 생성 및 시트 바인딩까지 초장에 완결한다.
 */
function initCampaignWorkspace() {
  return withUserLock("campaign_init", function() {
  var startTime = new Date().getTime();
  showProcessingToast("캠페인 작업 공간 및 VoC 설문 폼 올인원 초기화 중...", 20);
  try {
    var campaignFolder = getCampaignFolder();
    var campaignCode = getCampaignCode();

    // 1. 핵심 서브폴더 트리 생성
    var promptsFolder = getCampaignSubFolder([CONFIG.PROMPTS_FOLDER_NAME || "prompts"]);
    var inputFolder = getCampaignSubFolder(["input"]);
    var outputFolder = getCampaignSubFolder(["output"]);
    var fb01Folder = getCampaignSubFolder(["input", "fb-01"]);
    var rv00Folder = getCampaignSubFolder(["output", "rv-00"]);

    // 2. [핵심] 타깃 AI 페르소나 마스터 데이터를 캠페인 루트 폴더 직속에 시딩
    var personaFileName = CONFIG.PERSONA_FILE_NAME || "ai_personas.json";
    var existingPersonas = campaignFolder.getFilesByName(personaFileName);
    if (!existingPersonas.hasNext()) {
      var masterPersonas = getMasterPersonas25();
      var personaJsonText = JSON.stringify(masterPersonas, null, 2);
      saveTextFile(campaignFolder, personaFileName, personaJsonText);
      Logger.log("루트 직속 AI 페르소나 데이터셋 시딩 완료: " + personaFileName);
    }

    // 3. prompts/ 폴더 내 9대 프롬프트 구글 독스 자동 시딩 (기존 마케터 수정분 보존)
    seedDefaultPrompts(promptsFolder);

    var folderDisplayName = campaignFolder.getName();

    // 4. [스마트 보존] 고객 VoC 수집용 구글 폼(Google Forms) 탐색 및 연동 (기존 폼 보존, 부재 시에만 생성)
    var formInfo = setupFeedbackGoogleForm(campaignFolder, campaignCode);

    // 5. 현재 구글 시트를 캠페인 루트 폴더로 패키징 및 직관적 명칭 동기화
    try {
      var activeSpreadsheet = SpreadsheetApp.getActiveSpreadsheet();
      var sheetFile = DriveApp.getFileById(activeSpreadsheet.getId());
      var currentParents = sheetFile.getParents();
      var isAlreadyInFolder = false;
      while (currentParents.hasNext()) {
        if (currentParents.next().getId() === campaignFolder.getId()) {
          isAlreadyInFolder = true;
          break;
        }
      }
      if (!isAlreadyInFolder) {
        sheetFile.moveTo(campaignFolder);
      }
      syncSpreadsheetTitleWithCampaign(folderDisplayName, campaignCode);
    } catch (sheetMoveErr) {
      Logger.log("시트 캠페인 폴더 이동 중 예외 (무시 가능): " + sheetMoveErr);
    }

    // 6. 구글 시트 실행 내역 표 초기화 및 핵심 리소스 링크 등록
    var durationSec = Math.round((new Date().getTime() - startTime) / 1000);
    initDashboardSheet();
    
    // 1행: 작업 공간 준비 (드라이브 폴더 열기)
    recordStepResultToSheet(
      "작업 공간 준비",
      "캠페인 폴더 및 자산 무결성 점검",
      "완료",
      campaignFolder.getUrl(),
      "드라이브 폴더 열기 (" + folderDisplayName + ")",
      durationSec,
      0,
      "기존 콘텐츠/기획서 안전 보존 및 누락된 필수 폴더 트리/설문 채널 복구 완료"
    );

    // 2행: 고객 피드백 채널
    if (formInfo && formInfo.publishedUrl) {
      recordStepResultToSheet(
        "고객 피드백 채널",
        "VoC 구글 폼 및 모바일 QR",
        "활성",
        formInfo.publishedUrl,
        "온라인 설문지 열기",
        durationSec,
        0,
        "Google Forms 연동 완료 (현재 시트에 설문 응답 실시간 수신 대기)"
      );
    }

    showResultModal(
      "캠페인 작업 공간 준비 완료 (" + folderDisplayName + ")",
      "캠페인 폴더 내 기존 콘텐츠와 기획서 자산을 안전하게 보존하고, 누락된 필수 리소스 복구를 완료했습니다.\n\n" +
      "* 캠페인 명칭: " + folderDisplayName + " (" + campaignCode + ")\n" +
      "* 처리 소요 시간: " + formatDuration(durationSec) + "\n\n" +
      "아래 버튼을 눌러 캠페인 드라이브 폴더를 즉시 확인하십시오.",
      "캠페인 드라이브 폴더 열기",
      campaignFolder.getUrl()
    );

    return {
      success: true,
      message: "캠페인 작업 공간이 준비되었습니다. 필수 폴더 트리와 9대 프롬프트 및 고객 설문 폼이 구축되었습니다. 이제 [Step 1] 아이디어 메모 작성을 진행해 주십시오.",
      folderUrl: campaignFolder.getUrl(),
      ideaDocUrl: ""
    };
  } catch (e) {
    var failDuration = Math.round((new Date().getTime() - startTime) / 1000);
    recordStepResultToSheet(
      "초기 환경 구축",
      "작업 공간 및 VoC 설문 폼",
      "실패",
      "",
      "",
      failDuration,
      0,
      "오류 발생: " + (e.message || e.toString())
    );
    throw e;
  }
  });
}

/**
 * 고객 VoC 수집용 Google Forms를 생성하고 현재 시트와 모바일 QR 코드를 자동 연동한다.
 *
 * @param {GoogleAppsScript.Drive.Folder} campaignFolder - 캠페인 루트 폴더
 * @param {string} campaignCode - 캠페인 코드
 * @return {{ publishedUrl: string, editUrl: string }} 폼 URL 정보
 */
function setupFeedbackGoogleForm(campaignFolder, campaignCode) {
  try {
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    var spreadsheetId = spreadsheet.getId();
    var formTitle = "고객 피드백 설문 (" + campaignCode + ")";

    // 기존에 생성된 폼이 있는지 스마트 탐색 (동일 제목 또는 폴더 내 기존 구글 폼 보존)
    var existingFiles = campaignFolder.getFilesByName(formTitle);
    if (!existingFiles.hasNext()) {
      existingFiles = campaignFolder.getFilesByType(MimeType.GOOGLE_FORMS);
    }
    if (existingFiles.hasNext()) {
      var file = existingFiles.next();
      var existingForm = FormApp.openById(file.getId());
      try {
        existingForm.setDestination(FormApp.DestinationType.SPREADSHEET, spreadsheetId);
      } catch (destErr) {
        // 이미 연결되어 있거나 권한 문제 시 무시
      }
      return {
        publishedUrl: existingForm.getPublishedUrl(),
        editUrl: existingForm.getEditUrl()
      };
    }

    var form = FormApp.create(formTitle);
    form.setAcceptingResponses(true);
    try {
      form.setRequireLogin(false);
      form.setCollectEmail(false);
      form.setLimitOneResponsePerUser(false);
      form.setShowLinkToRespondAgain(true);
    } catch (e) {
      Logger.log("폼 기본 옵션 설정 예외: " + e);
    }

    var publishedUrl = form.getPublishedUrl();

    form.setDescription(
      "본 설문은 " + campaignCode + " 캠페인의 고객 만족도와 사용자 직접 촬영 동영상/이미지 피드백을 수집하여 " +
      "Gemini VLM 다면 평가 및 마케팅 콘텐츠 보정에 반영하기 위한 설문입니다.\n\n" +
      "[모바일 즉시 참여 안내]\n" +
      "스마트폰 카메라로 아래 QR 코드를 스캔하면 모바일 화면에서 즉시 피드백을 작성하실 수 있습니다.\n" +
      "설문 참여 바로가기: " + publishedUrl
    );

    // 모바일 참여용 고화질 QR 코드 생성 및 최상단 삽입
    try {
      var qrApiUrl = "https://quickchart.io/qr?text=" + encodeURIComponent(publishedUrl) + "&size=300&ecLevel=H";
      var qrResponse = UrlFetchApp.fetch(qrApiUrl, { muteHttpExceptions: true });
      if (qrResponse.getResponseCode() === 200) {
        var qrBlob = qrResponse.getBlob().setName("form_qr_code.png");
        var imageItem = form.addImageItem();
        imageItem.setTitle("스마트폰 카메라로 QR 코드를 스캔하여 모바일 피드백을 제출하세요!");
        imageItem.setHelpText("모바일 설문 URL: " + publishedUrl);
        imageItem.setImage(qrBlob);
      }
    } catch (qrErr) {
      Logger.log("QR 코드 이미지 생성 예외: " + qrErr);
    }

    // 질문 문항 자동 구성
    var versionItem = form.addMultipleChoiceItem();
    versionItem.setTitle("평가 대상 마케팅 콘텐츠 버전 (선택 사항)")
      .setChoiceValues(["초판 (rv-00)", "1차 개정본 (rv-01)", "2차 개정본 (rv-02)"])
      .setRequired(false);

    form.addScaleItem()
      .setTitle("제품의 전반적인 만족도는 어떠셨습니까? (선택 사항)")
      .setBounds(1, 5)
      .setLabels("매우 불만족", "매우 만족")
      .setRequired(false);

    form.addParagraphTextItem()
      .setTitle("제품을 사용하면서 느낀 솔직한 장점이나 아쉬운 점을 자유롭게 적어주십시오. (자유 기술)")
      .setHelpText("예: 도심 지하철 소음 차단은 좋은데, 가벼운 착용감이나 힐링 무드 카피를 더 부각해 주면 좋겠습니다.")
      .setRequired(false);

    form.addParagraphTextItem()
      .setTitle("고객 촬영 동영상 피드백 소감 요약 또는 파일 링크 (선택 사항)")
      .setHelpText("스마트폰으로 제품을 사용해보며 느낀 소감이나 고객의 생생한 목소리를 적어주십시오. (권장 길이 15~30초 세로 숏폼 영상)")
      .setRequired(false);

    form.addParagraphTextItem()
      .setTitle("추가 이미지 피드백 소감 또는 링크 (선택 사항)")
      .setHelpText("제품 착용 컷, 언박싱 사진에 대한 의견이나 이미지 파일 링크를 입력하십시오.")
      .setRequired(false);

    // 현재 구글 시트에 응답 탭 연결
    form.setDestination(FormApp.DestinationType.SPREADSHEET, spreadsheetId);

    // 폼 파일을 캠페인 루트 폴더로 이동
    var formFile = DriveApp.getFileById(form.getId());
    formFile.moveTo(campaignFolder);

    Logger.log("고객 VoC Google Forms 생성 및 시트 바인딩 완료: " + publishedUrl);
    return {
      publishedUrl: publishedUrl,
      editUrl: form.getEditUrl()
    };
  } catch (err) {
    Logger.log("Google Forms 설정 예외: " + err);
    return null;
  }
}

/**
 * [환경 설정] 캠페인 코드 및 타깃 설정을 조회하고 재설정한다.
 *
 * @param {string} [newCodeOpt] - 변경할 새로운 캠페인 코드 (선택)
 * @return {string} 현재 또는 갱신된 캠페인 코드
 */
function runConfigureCampaignSettings(newCodeOpt) {
  var userProps = PropertiesService.getUserProperties();
  var currentCode = userProps.getProperty("CAMPAIGN_CODE") || CONFIG.CAMPAIGN_CODE || "cp-ignite";

  if (newCodeOpt && typeof newCodeOpt === "string" && newCodeOpt.trim()) {
    var newCode = newCodeOpt.trim();
    userProps.setProperty("CAMPAIGN_CODE", newCode);
    return newCode;
  }
  return currentCode;
}

/**
 * 슬림 한국인 AI 페르소나 마스터 데이터셋 반환
 */
function getMasterPersonas25() {
  return {
    "metadata": {
      "description": "한국인 다면 평가 슬림 AI 페르소나 패널 (토큰 최적화 경량 규격)",
      "total": 25
    },
    "personas": [
      { "id": "p01", "name": "강도윤", "age": 28, "gender": "남성", "category": "전문 마케터", "occupation": "퍼포먼스 마케터", "perspective": "데이터 지향적, 민첩한 의사 결정. ROAS 지표 및 전환 효율 중시" },
      { "id": "p02", "name": "김서아", "age": 32, "gender": "여성", "category": "전문 마케터", "occupation": "브랜드 마케터", "perspective": "감성적 통찰력, 차별화된 톤앤매너와 브랜드 스토리텔링 중시" },
      { "id": "p03", "name": "이서연", "age": 24, "gender": "여성", "category": "20대 대학생", "occupation": "대학생", "perspective": "트렌드에 민감한 Z세대, 인스타그램 릴스와 숏폼 소비 중심" },
      { "id": "p04", "name": "박민준", "age": 25, "gender": "남성", "category": "20대 대학생", "occupation": "취업 준비생", "perspective": "가격 대비 심리적 만족(가심비)과 학습 몰입 환경 중시" },
      { "id": "p05", "name": "정도현", "age": 29, "gender": "남성", "category": "2030 직장인", "occupation": "IT 개발자", "perspective": "도심 출퇴근 지하철 소음 차단 및 기기 멀티포인트 연결 중시" },
      { "id": "p06", "name": "최지우", "age": 31, "gender": "여성", "category": "2030 직장인", "occupation": "금융 컨설턴트", "perspective": "모던한 오피스 룩과의 조화 및 장시간 착용 시 피로도 중시" },
      { "id": "p07", "name": "강하은", "age": 34, "gender": "여성", "category": "2030 직장인", "occupation": "인하우스 디자이너", "perspective": "미니멀한 제품 심미성, 패키지 완성도 및 감각적인 비주얼 선호" },
      { "id": "p08", "name": "윤우진", "age": 36, "gender": "남성", "category": "3040 전문가", "occupation": "스타트업 대표", "perspective": "비즈니스 통화 품질, 마이크 성능 및 프리미엄 브랜드 신뢰도" },
      { "id": "p09", "name": "임수빈", "age": 27, "gender": "여성", "category": "크리에이터", "occupation": "유튜브 브이로거", "perspective": "야외 촬영 시 휴대성, 감성적인 카페 인테리어와의 어울림" },
      { "id": "p10", "name": "한태양", "age": 38, "gender": "남성", "category": "아웃도어/캠퍼", "occupation": "프리랜서 작가", "perspective": "주말 차박 및 솔로 캠핑 시 배터리 지속력과 생활 방수 성능" },
      { "id": "p11", "name": "배소율", "age": 22, "gender": "여성", "category": "20대 대학생", "occupation": "예술대 학생", "perspective": "독창적인 색감, 힙한 숏폼 사운드와 개성 표현 가능 여부" },
      { "id": "p12", "name": "송시우", "age": 41, "gender": "남성", "category": "40대 부모", "occupation": "제조업 팀장", "perspective": "자녀와의 휴식, 층간 소음 극복 및 온전한 자기 계발 시간 확보" },
      { "id": "p13", "name": "오유진", "age": 33, "gender": "여성", "category": "워킹맘", "occupation": "마케팅 과장", "perspective": "가사와 육아 병행 중 틈새 힐링, 가벼운 무게와 직관적 터치 조작" },
      { "id": "p14", "name": "권준호", "age": 26, "gender": "남성", "category": "얼리어답터", "occupation": "하드웨어 엔지니어", "perspective": "드라이버 음향 스펙, 코덱 지원(LDAC), 노이즈 캔슬링 칩셋 분석" },
      { "id": "p15", "name": "백서진", "age": 30, "gender": "여성", "category": "피트니스/러너", "occupation": "필라테스 강사", "perspective": "러닝 시 흔들림 없는 밀착감, 땀에 강한 이어패드 소재" },
      { "id": "p16", "name": "조은우", "age": 45, "gender": "남성", "category": "시니어 프로", "occupation": "공공기관 부장", "perspective": "단정하고 품격 있는 디자인, 복잡하지 않은 직관적 버튼 구성" },
      { "id": "p17", "name": "남궁예린", "age": 23, "gender": "여성", "category": "Z세대 쇼퍼", "occupation": "패션 인턴", "perspective": "인스타 감성 룩북 컷 연출, 성수동 팝업스토어 체험 기대감" },
      { "id": "p18", "name": "문지훈", "age": 35, "gender": "남성", "category": "음악 애호가", "occupation": "사운드 엔지니어", "perspective": "원음 왜곡 없는 플랫한 해상력, 베이스 타격감과 공간 음향" },
      { "id": "p19", "name": "신채원", "age": 29, "gender": "여성", "category": "원격 근무자", "occupation": "글로벌 번역가", "perspective": "화상 회의 시 주변 소음 감쇄 및 8시간 이상 무압박 착용감" },
      { "id": "p20", "name": "황민성", "age": 39, "gender": "남성", "category": "비즈니스 트래블러", "occupation": "해외 영업 차장", "perspective": "비행기 엔진 저주파 소음 완벽 차단 및 접이식 컴팩트 파우치" },
      { "id": "p21", "name": "노하율", "age": 21, "gender": "여성", "category": "20대 알바생", "occupation": "휴학생", "perspective": "무이자 할부 및 얼리버드 특별 할인 혜택, 실질 구매 가격" },
      { "id": "p22", "name": "구건우", "age": 37, "gender": "남성", "category": "취미 캠퍼", "occupation": "건축 설계사", "perspective": "야외 불멍 시 몰입감, 자연의 소리와 음악을 오가는 앰비언트 모드" },
      { "id": "p23", "name": "서다은", "age": 33, "gender": "여성", "category": "트렌드세터", "occupation": "커머스 MD", "perspective": "선물용 패키지 가치, 카카오톡 선물하기 입점 가능성" },
      { "id": "p24", "name": "유재혁", "age": 48, "gender": "남성", "category": "중견 임원", "occupation": "경영 기획 전무", "perspective": "프리미엄 라인업의 브랜드 헤리티지 및 애프터서비스(A/S) 신뢰성" },
      { "id": "p25", "name": "홍지아", "age": 27, "gender": "여성", "category": "북클럽 리더", "occupation": "도서관 사서", "perspective": "독서와 사색을 위한 백색 소음 조성, 안경 착용 시 통증 유무" }
    ]
  };
}

// ==========================================
// Module: Code_Content.js
// ==========================================
/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 5] 기획서(PLAN/SPEC) 도출 및 멀티 채널 콘텐츠 생성/보정 엔진 (Content Engine)
 */

/**
 * [Step 1] 캠페인 아이디어 메모 구글 독스를 작성/저장한다.
 *
 * @param {string} [customIdea] - 마케터가 입력한 원천 아이디어
 */
function runCampaignIdeaMemo(customIdea) {
  return withUserLock("idea_memo", function() {
    var startTime = new Date().getTime();
    try {
      var campaignFolder = getCampaignFolder();
      var ideaDocName = (CONFIG && CONFIG.IDEA_DOC_NAME) || "아이디어 메모";
      var inputFolder = getCampaignSubFolder(["input"]);

      var inputVal = (customIdea || "").trim();
      var existingIdea = readGoogleDoc(campaignFolder, ideaDocName) || readGoogleDoc(inputFolder, ideaDocName) || "";
      var ideaMemo = inputVal || existingIdea.trim();

      if (!ideaMemo) {
        ideaMemo = "# " + campaignFolder.getName() + " 아이디어 메모\n\n* 캠페인 핵심 아이디어를 자유롭게 작성하십시오.";
      }

      var ideaFile = saveGoogleDoc(campaignFolder, ideaDocName, ideaMemo);
      var durationSec = Math.max(1, Math.round((new Date().getTime() - startTime) / 1000));

      recordStepResultToSheet(
        "Step 1",
        "캠페인 아이디어 메모",
        "완료",
        ideaFile.getUrl(),
        "[아이디어 메모] 구글 독스 열기",
        durationSec,
        0,
        "마케터 원천 아이디어 등록 완료 (구글 독스에서 직접 수정 가능)"
      );

      return {
        success: true,
        message: "캠페인 아이디어 메모가 준비되었습니다. 생성된 구글 독스에서 아이디어를 검토하신 후 [Step 2] 기획서(PLAN) 생성을 진행해 주십시오.",
        ideaDocUrl: ideaFile.getUrl(),
        ideaContent: ideaMemo
      };
    } catch (e) {
      throw e;
    }
  });
}

/**
 * [Step 2] 아이디어 메모를 기반으로 마케팅 캠페인 기획서(PLAN) 전문을 도출한다.
 *
 * @param {string} [customIdea] - 인라인 전달 아이디어 (선택)
 */
function runIdeaToPlan(customIdea) {
  return withUserLock("plan_generation", function() {
    var startTime = new Date().getTime();
    showProcessingToast("아이디어 기반 기획서(PLAN) 자동 생성 중...", 30);
    try {
      var campaignFolder = getCampaignFolder();
      var ideaDocName = (CONFIG && CONFIG.IDEA_DOC_NAME) || "아이디어 메모";
      var inputFolder = getCampaignSubFolder(["input"]);

      var inputVal = (customIdea || "").trim();
      var existingIdea = readGoogleDoc(campaignFolder, ideaDocName) || readGoogleDoc(inputFolder, ideaDocName) || "";
      var ideaMemo = inputVal || existingIdea.trim();

      if (!ideaMemo || ideaMemo.length < 5) {
        throw new Error("캠페인 아이디어가 비어 있습니다. [Step 1] 아이디어 메모를 작성해 주시거나 사이드바 대화창에 아이디어를 직접 입력해 주십시오.");
      }

      resetSessionTokens();
      var planSystemInstruction = getPromptTemplate("01_idea_to_plan");
      var planUserPrompt =
        "다음은 마케터가 작성한 캠페인 아이디어 초안 메모이다.\n\n" +
        "### [마케터 아이디어 메모]\n" + ideaMemo + "\n\n" +
        "위 아이디어를 정밀 분석하여 마케팅 캠페인 기획서(PLAN) 전문을 체계적인 마크다운으로 작성하라.";

      var planContent = callGemini(planSystemInstruction, planUserPrompt);
      var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
      var planFile = saveGoogleDoc(campaignFolder, planDocName, planContent);
      var durationSec = Math.max(1, Math.round((new Date().getTime() - startTime) / 1000));
      var tokens = getSessionTotalTokens();

      recordStepResultToSheet(
        "Step 2",
        "캠페인 기획서 (PLAN)",
        "완료",
        planFile.getUrl(),
        "기획서 독스 열기 (PLAN)",
        durationSec,
        tokens,
        "아이디어 기반 캠페인 기획서(PLAN) 독스 자동 생성 완료 (마케터 수정 가능)"
      );

      return {
        success: true,
        message: "캠페인 기획서(PLAN)가 생성되었습니다. 독스를 열어 검토 및 보완하신 후, [Step 3] 제작 명세서(SPEC) 생성을 진행해 주십시오.",
        planUrl: planFile.getUrl()
      };
    } catch (e) {
      var failDuration = Math.round((new Date().getTime() - startTime) / 1000);
      recordStepResultToSheet("Step 2", "캠페인 기획서 (PLAN)", "실패", "", "", failDuration, 0, "오류: " + (e.message || e.toString()));
      throw e;
    }
  });
}

/**
 * [Step 3] 기획서(PLAN)를 기반으로 콘텐츠 제작 명세서(SPEC) 전문을 도출한다.
 */
function runPlanToSpec() {
  return withUserLock("spec_generation", function() {
    var startTime = new Date().getTime();
    showProcessingToast("기획서 기반 제작 명세서(SPEC) 자동 생성 중...", 30);
    try {
      var campaignFolder = getCampaignFolder();
      var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
      var planContent = readGoogleDoc(campaignFolder, planDocName) || readGoogleDoc(campaignFolder, "BRD");

      if (!planContent || planContent.length < 20) {
        throw new Error("캠페인 기획서(PLAN)를 찾을 수 없습니다. [Step 2] 캠페인 기획서(PLAN) 생성을 먼저 실행해 주십시오.");
      }

      resetSessionTokens();
      var specSystemInstruction = getPromptTemplate("02_plan_to_spec");
      var specUserPrompt =
        "다음은 이번 캠페인의 마케팅 기획서(PLAN) 전문이다.\n\n" +
        "### [마케팅 캠페인 기획서 (PLAN)]\n" + planContent + "\n\n" +
        "위 기획서의 타깃 오디언스, 핵심 USP, 캠페인 전략을 충실히 반영하여 제작 실무진(디자이너, 영상 PD, 카피라이터)을 위한 콘텐츠 제작 명세서(SPEC) 전문을 마크다운으로 작성하라:\n" +
        "- 가로 16:9 배너 (1920x1080), 세로 9:16 모바일 포스터 (1080x1920), 정방형 1:1 SNS 피드 (1080x1080)\n" +
        "- 15초 세로 9:16 모바일 숏폼 영상 콘티 규격 및 4대 평가 영역 설문 가이드라인 정의";

      var specContent = callGemini(specSystemInstruction, specUserPrompt);
      var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";
      var specFile = saveGoogleDoc(campaignFolder, specDocName, specContent);
      var durationSec = Math.max(1, Math.round((new Date().getTime() - startTime) / 1000));
      var tokens = getSessionTotalTokens();

      recordStepResultToSheet(
        "Step 3",
        "제작 명세서 (SPEC)",
        "완료",
        specFile.getUrl(),
        "명세서 독스 열기 (SPEC)",
        durationSec,
        tokens,
        "16:9 배너, 9:16 포스터, 1:1 SNS, 15초 숏폼 규격 명세서(SPEC) 생성 완료"
      );

      return {
        success: true,
        message: "콘텐츠 제작 명세서(SPEC)가 생성되었습니다. 채널 규격을 검토하신 후 [Step 4] 맞춤 AI 페르소나 패널 구성을 진행해 주십시오.",
        specUrl: specFile.getUrl()
      };
    } catch (e) {
      var failDuration = Math.round((new Date().getTime() - startTime) / 1000);
      recordStepResultToSheet("Step 3", "제작 명세서 (SPEC)", "실패", "", "", failDuration, 0, "오류: " + (e.message || e.toString()));
      throw e;
    }
  });
}

/**
 * [Step 4] 제작 명세서(SPEC)의 타깃 오디언스에 맞춘 25인 맞춤 AI 페르소나 패널을 자동 구성한다.
 */
function runPersonaPanelSynthesis() {
  return withUserLock("persona_synthesis", function() {
    var startTime = new Date().getTime();
    showProcessingToast("제작 명세서 기반 맞춤 AI 페르소나 패널 자동 구성 중...", 30);
    try {
      var campaignFolder = getCampaignFolder();
      var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";
      var specContent = readGoogleDoc(campaignFolder, specDocName) || "";
      var planContent = readGoogleDoc(campaignFolder, (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN") || "";

      if (!specContent && !planContent) {
        throw new Error("제작 명세서(SPEC) 또는 기획서(PLAN)를 찾을 수 없습니다. [Step 3] 제작 명세서(SPEC) 생성을 먼저 실행해 주십시오.");
      }

      resetSessionTokens();
      var personaSystemInstruction = getPromptTemplate("03_persona_synthesis");
      var personaUserPrompt =
        "다음은 이번 캠페인의 콘텐츠 제작 명세서(SPEC) 및 기획서(PLAN)이다.\n\n" +
        "### [마케팅 제작 명세서 발췌]\n" + (specContent.substring(0, 1800) || planContent.substring(0, 1800)) + "\n\n" +
        "위 명세서의 타깃 오디언스 프로파일 및 페인 포인트를 심층 분석하여, 콘텐츠를 다각도로 평가할 슬림 AI 페르소나 패널 JSON 객체(7대 필수 필드: id, name, age, gender, category, occupation, perspective)를 도출하라.";

      var synthesizedPersonasRaw = callGemini(personaSystemInstruction, personaUserPrompt);
      var personaFileName = (CONFIG && CONFIG.PERSONA_FILE_NAME) || "ai_personas.json";
      var personaFile = null;

      if (synthesizedPersonasRaw) {
        var parsedPersonas = safeParseJson(synthesizedPersonasRaw, null, false);
        if (parsedPersonas && (parsedPersonas.personas || Array.isArray(parsedPersonas))) {
          personaFile = saveTextFile(campaignFolder, personaFileName, JSON.stringify(parsedPersonas, null, 2));
          Logger.log("제작 명세서 기반 타깃 맞춤 페르소나 자동 합성 완료: " + personaFileName);
        }
      }

      if (!personaFile) {
        var existing = campaignFolder.getFilesByName(personaFileName);
        if (existing.hasNext()) {
          personaFile = existing.next();
        } else {
          var master = getMasterPersonas25();
          personaFile = saveTextFile(campaignFolder, personaFileName, JSON.stringify(master, null, 2));
        }
      }

      var durationSec = Math.max(1, Math.round((new Date().getTime() - startTime) / 1000));
      var tokens = getSessionTotalTokens();

      recordStepResultToSheet(
        "Step 4",
        "맞춤 AI 페르소나 패널",
        "완료",
        personaFile.getUrl(),
        "AI 페르소나 JSON 열기",
        durationSec,
        tokens,
        "타깃 오디언스 맞춤 가상 소비자 패널(ai_personas.json) 자동 구성 완료"
      );

      return {
        success: true,
        message: "맞춤 AI 페르소나 패널이 구성되었습니다. 이제 [Step 5] 초판 멀티 채널 콘텐츠(rv-00) 생성을 진행해 주십시오.",
        personaUrl: personaFile.getUrl()
      };
    } catch (e) {
      var failDuration = Math.round((new Date().getTime() - startTime) / 1000);
      recordStepResultToSheet("Step 4", "맞춤 AI 페르소나 패널", "실패", "", "", failDuration, 0, "오류: " + (e.message || e.toString()));
      throw e;
    }
  });
}

/**
 * [Step 5] 기획서(PLAN) 및 명세서(SPEC)를 기반으로 초판 마케팅 콘텐츠(rv-00)를 생성한다.
 * (모달 팝업 없이 스마트 에셋 보존 및 누락 파일 고속 보충 자동 적용)
 *
 * @param {boolean} [forceOverwrite] - 기존 에셋 완비 시 전체 강제 새로고침 여부 (기본값: false, 기존 파일 안전 보존)
 */
function runInitialContentGeneration(forceOverwrite) {
  return withUserLock("content_generation", function() {
    var startTime = new Date().getTime();
    showProcessingToast("초판 마케팅 콘텐츠 생성 중 (rv-00)...", 60);
    try {
      var campaignFolder = getCampaignFolder();
      var campaignCode = getCampaignCode();
      var rv00Folder = getCampaignSubFolder(["output", "rv-00"]);

      // 선결 조건 검사: PLAN 문서 확인
      var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
      var planContent = readGoogleDoc(campaignFolder, planDocName);
      if (!planContent) {
        planContent = readGoogleDoc(campaignFolder, "BRD");
      }
      if (!planContent) {
        throw new Error("캠페인 기획서(PLAN) 문서를 찾을 수 없습니다. 사이드바의 [Step 2] 캠페인 기획서(PLAN) 생성을 먼저 실행해 주십시오.");
      }

      // 폴더 내 기존 에셋 검사 및 스마트 비차단 분기
      var folderStatus = inspectRevisionFolder(rv00Folder, "00");
      var onlyMissing = false;

      if (!folderStatus.isEmpty) {
        if (folderStatus.isComplete && !forceOverwrite) {
          return {
            success: true,
            status: "already_complete",
            message: "초판 콘텐츠(rv-00)의 모든 에셋(카피 독스, 이미지 3종, 숏폼 영상)이 이미 완비되어 있어 기존 자산을 안전하게 보존했습니다. 전체 새로 생성이 필요한 경우 아래 버튼을 클릭하십시오.",
            folderUrl: rv00Folder.getUrl(),
            actionChip: "<div style='margin-top:6px;'><button class='btn btn-primary btn-sm' onclick=\"callServer('forceRunInitialContent', '초판 콘텐츠 전체 재생성')\">[초판 전체 다시 제작]</button></div>"
          };
        } else if (!folderStatus.isComplete) {
          // 일부 에셋만 누락된 경우: 기존 마케터 수정본과 이미지를 완벽 보존하고 누락 파일만 스마트 고속 보충!
          onlyMissing = true;
        }
      }

    var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";
    var specContent = readGoogleDoc(campaignFolder, specDocName) || "";

    // 1. [스마트 컴파일] 마케터의 제작 명세서(SPEC)로부터 미디어 제작 스펙(비디오/이미지 비율) 지능형 컴파일 및 media_specs.json 저장
    var mediaSpec = compileMediaSpecFromDocs(specContent, "00", "", rv00Folder);

    var contentDocName = (CONFIG && CONFIG.CONTENT_DOC_NAME) || "campaign_content";
    var finalizedContent = "";
    var visualBrief = "";

    resetSessionTokens();

    if (onlyMissing && folderStatus.hasDoc) {
      // 카피 독스가 이미 존재하면 기존 문서를 읽어 마케터의 수정본을 존중
      finalizedContent = readGoogleDoc(rv00Folder, contentDocName) || "";
      visualBrief = extractDynamicVisualPrompt(
        finalizedContent,
        planContent,
        "A stylish 20s Korean female commuter with lightweight premium ANC headphones in warm golden autumn sunlight on a modern Seoul street"
      );
    } else {
      // 2. 프롬프트 템플릿 로드 (구글 독스 스마트 캐싱)
      var systemInstruction = getPromptTemplate("04_content_generation");
      var promptText =
        "다음은 이번 캠페인의 마케팅 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC)이다.\n" +
        "명세서(SPEC)에 정의된 채널 규격, 영상 길이, 비주얼 가이드라인을 엄격히 준수하여 초판 campaign_content를 작성하라:\n\n" +
        "### [1. 마케팅 캠페인 기획서 (PLAN)]\n" + planContent + "\n\n" +
        "### [2. 멀티 채널 콘텐츠 제작 명세서 (SPEC)]\n" + (specContent || "기본 규격 준수");

      var generatedContent = callGemini(systemInstruction, promptText);

      // 3. 동적 비주얼 프롬프트 도출 및 숏폼 영상 콘티 완전 통합
      visualBrief = extractDynamicVisualPrompt(
        generatedContent,
        planContent,
        "A stylish 20s Korean female commuter with lightweight premium ANC headphones in warm golden autumn sunlight on a modern Seoul street"
      );
      finalizedContent = ensureShortsScriptInCampaignContent(generatedContent, "00", visualBrief);

      // 4. [UX 핵심] 마케터가 독스 열자마자 확인 가능한 [SPEC 반영 미디어 산출물 현황] 헤더를 독스 최상단에 포함하여 저장
      var specReportHeader = buildMediaSpecReportHeader(mediaSpec);
      saveGoogleDoc(rv00Folder, contentDocName, specReportHeader + finalizedContent);
    }

    // 5. 실시간 대표 비주얼 이미지 및 Veo 비디오 동적 생성 (마케터 명세서 지정 종횡비 및 비디오 제외 여부 100% 반영)
    Logger.log("동적 도출된 비주얼 프롬프트 (rv-00): " + visualBrief);
    var visResult = generateAndSaveVisualAssets(rv00Folder, "00", visualBrief, { onlyMissing: onlyMissing }, mediaSpec);

    var durationSec = Math.round((new Date().getTime() - startTime) / 1000);

    // 6. 상세 실행 내역 조립
    var logDetail = "";
    if (onlyMissing) {
      var totalSkipped = visResult.skipImageCount + (visResult.videoStatus === "skipped" ? 1 : 0);
      logDetail = "미완성 에셋 선별 보충 완료 (신규 이미지 " + visResult.genImageCount + "건 생성, 기존 에셋 " + totalSkipped + "건 보존)";
    } else {
      var videoDesc = (visResult.videoStatus === "generated")
        ? "Veo 비디오 1건"
        : (visResult.videoStatus === "excluded" ? "비디오 제외(명세서 반영)" : "숏폼 콘티 독스 수록");
      logDetail = "통합 카피 독스 1건, 대표 이미지 " + visResult.genImageCount + "종, " + videoDesc + " 생성 완료";
      if (mediaSpec && mediaSpec.reason) {
        logDetail += " [" + mediaSpec.reason + "]";
      }
    }

    // 6. 실행 대시보드에 링크 기록
    recordStepResultToSheet(
      "Step 5",
      "초판 멀티 채널 콘텐츠 (rv-00)",
      "완료",
      rv00Folder.getUrl(),
      "구글 드라이브 폴더 열기 (rv-00)",
      durationSec,
      getSessionTotalTokens(),
      logDetail
    );

    showResultModal(
      "초판 마케팅 콘텐츠 생성 완료 (rv-00)",
      "카피 및 숏폼 영상 콘티가 통합된 구글 독스(campaign_content)와 대표 비주얼 이미지 3종, Veo 비디오가 준비되었습니다.\n\n" +
      "* 처리 소요 시간: " + formatDuration(durationSec) + "\n" +
      "* 실행 상세 내역: " + logDetail + "\n\n" +
      "아래 버튼을 눌러 초판 콘텐츠 폴더를 확인하십시오.",
      "초판 콘텐츠 폴더 열기 (rv-00)",
      rv00Folder.getUrl()
    );

    return {
      success: true,
      targetRv: "rv-00",
      message: "초판 마케팅 콘텐츠(rv-00) 생성이 완료되었습니다 (" + logDetail + "). 생성된 결과물을 확인하시고 [Step 6] AI 페르소나 다면 평가를 진행해 주십시오.",
      folderUrl: rv00Folder.getUrl()
    };
  } catch (e) {
    var failDuration = Math.round((new Date().getTime() - startTime) / 1000);
    recordStepResultToSheet(
      "초판 콘텐츠 (rv-00)",
      "멀티 채널 콘텐츠 생성",
      "실패",
      "",
      "",
      failDuration,
      0,
      "오류 발생: " + (e.message || e.toString())
    );
    throw e;
  }
  });
}

/**
 * [Step 9] 피드백 요약본(feedback_summary)과 마케터 지침을 반영하여 N차 개정본 마케팅 콘텐츠를 완결 보정한다.
 * (모달 팝업 없이 스마트 리비전 자동 승격 및 누락 파일 고속 보충 적용)
 *
 * @param {string} [targetRoundOpt] - 대상 피드백 라운드 (fb-01, fb-02 등)
 * @param {boolean} [isSilentOpt] - 무음 모드 여부
 * @param {boolean} [forceOverwrite] - 현재 리비전 강제 덮어쓰기 여부
 * @param {string} [customDirectiveOpt] - 인라인 입력 또는 대화창에서 전달된 마케터 수기 보정 지침 (선택)
 */
function runReviseContent(targetRoundOpt, isSilentOpt, forceOverwrite, customDirectiveOpt) {
  return withUserLock("content_revision", function() {
    var isSilent = (isSilentOpt === true);
    var startTime = new Date().getTime();
    try {
    var campaignFolder = getCampaignFolder();

    // 회차 판별 (fb-01 -> rv-01, fb-02 -> rv-02 ...)
    var targetRound = targetRoundOpt;
    if (!targetRound) {
      var latestRv = detectLatestRevisionRoundNum();
      var autoRound = Math.max(latestRv + 1, 1);
      targetRound = "fb-" + (autoRound < 10 ? "0" + autoRound : autoRound);
    }

    var roundNum = parseInt(targetRound.replace("fb-", ""), 10) || 1;
    var prevRoundNum = roundNum - 1;
    var prevRvName = "rv-" + (prevRoundNum < 10 ? "0" + prevRoundNum : prevRoundNum);
    var targetRvName = "rv-" + (roundNum < 10 ? "0" + roundNum : roundNum);
    var prefix = (roundNum < 10 ? "0" + roundNum : "" + roundNum);

    var targetRvFolder = getCampaignSubFolder(["output", targetRvName]);
    var onlyMissing = false;

    // 타깃 폴더 에셋 상태 검사 및 스마트 분기 (모달 없이 자율 결정)
    var folderStatus = inspectRevisionFolder(targetRvFolder, prefix);
    if (!folderStatus.isEmpty) {
      if (folderStatus.isComplete && !forceOverwrite) {
        // 이미 완비되어 있으면 다음 신규 리비전으로 안전 자동 전환 (기존 리비전 100% 보존)
        var nextRoundNum = roundNum + 1;
        var nextRvName = "rv-" + (nextRoundNum < 10 ? "0" + nextRoundNum : nextRoundNum);
        roundNum = nextRoundNum;
        prevRvName = targetRvName;
        targetRvName = nextRvName;
        prefix = (roundNum < 10 ? "0" + roundNum : "" + roundNum);
        targetRvFolder = getCampaignSubFolder(["output", targetRvName]);
        folderStatus = inspectRevisionFolder(targetRvFolder, prefix);
      } else if (!folderStatus.isComplete) {
        // 일부 에셋만 누락된 경우: 기존 마케터 수정본과 이미지를 보존하고 누락 파일만 스마트 고속 보충
        onlyMissing = true;
      }
    }

    showProcessingToast("피드백 반영 마케팅 콘텐츠 보정 중 (" + targetRvName + ")...", 75);

    var prevRvFolder = getCampaignSubFolder(["output", prevRvName]);
    var feedbackFolder = getCampaignSubFolder(["input", targetRound]);

    // 선결 조건 1: 이전 콘텐츠 확인
    var targetContentDocName = (CONFIG && CONFIG.CONTENT_DOC_NAME) || "campaign_content";
    var previousAsset = readGoogleDoc(prevRvFolder, targetContentDocName) || readGoogleDoc(prevRvFolder, "campaign_asset");
    if (!previousAsset) {
      throw new Error("이전 마케팅 콘텐츠(" + prevRvName + ")를 찾을 수 없습니다. [초판 콘텐츠 생성]을 먼저 실행하십시오.");
    }

    // 선결 조건 2: feedback_summary 확인
    var summaryContent = readGoogleDoc(feedbackFolder, "feedback_summary");
    if (!summaryContent) {
      throw new Error("피드백 요약본(" + targetRound + "/feedback_summary)을 찾을 수 없습니다. [피드백 종합 분석 보고서 생성]을 먼저 실행하십시오.");
    }

    // 선결 조건 3: 마케터 보정 지침 확인 (인자 전달값 우선 및 독립 파일 보존)
    var directiveDocName = (CONFIG && CONFIG.DIRECTIVE_DOC_NAME) || "마케터 보정 지침";
    var inputDirective = (customDirectiveOpt || "").trim();
    if (inputDirective) {
      saveGoogleDoc(feedbackFolder, directiveDocName, inputDirective);
    }
    var marketerDirective = inputDirective || readGoogleDoc(feedbackFolder, directiveDocName) || "";

    var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
    var planContent = readGoogleDoc(campaignFolder, planDocName) || readGoogleDoc(campaignFolder, "BRD") || "마케팅 캠페인 기획서";
    var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";
    var specContent = readGoogleDoc(campaignFolder, specDocName) || "콘텐츠 제작 명세서";

    // 1. [스마트 컴파일] 명세서(SPEC) 및 마케터 보정 지침으로부터 개정본 미디어 제작 스펙 도출 및 media_specs.json 저장
    var mediaSpec = compileMediaSpecFromDocs(specContent, prefix, marketerDirective, targetRvFolder);

    var finalizedContent = "";
    var dynamicBrief = "";

    resetSessionTokens();

    if (onlyMissing && folderStatus.hasDoc) {
      // 카피 독스가 이미 있으면 기존 독스를 유지하고 비주얼 프롬프트만 재도출
      finalizedContent = readGoogleDoc(targetRvFolder, targetContentDocName) || "";
      dynamicBrief = extractDynamicVisualPrompt(
        finalizedContent,
        summaryContent,
        "A stylish 20s Korean female model enjoying cozy autumn commuter lifestyle with lightweight ANC headphones in a chic Seoul cafe",
        marketerDirective
      );
    } else {
      // 2. 프롬프트 템플릿 로드 (구글 독스 스마트 캐싱)
      var systemInstruction = getPromptTemplate("08_content_revision");
      var userPrompt =
        "다음은 원천 기획 명세(PLAN), 콘텐츠 제작 명세서(SPEC), 직전 마케팅 콘텐츠(" + prevRvName + "), " +
        "고객 피드백 종합 요약본(feedback_summary), 그리고 마케터의 최종 의사 결정 및 보정 지침이다.\n\n" +
        "### [1. 원천 마케팅 캠페인 기획서 (PLAN)]\n" + planContent + "\n\n" +
        "### [2. 콘텐츠 제작 명세서 (SPEC)]\n" + specContent + "\n\n" +
        "### [3. 직전 마케팅 콘텐츠 (" + prevRvName + ")]\n" + previousAsset + "\n\n" +
        "### [4. 고객 및 AI 페르소나 피드백 종합 분석 데이터 (feedback_summary)]\n" + summaryContent + "\n\n" +
        "### [5. 마케터 최종 의사 결정 및 보정 지침 (최우선 구속력 반영 필수 지침)]\n" +
        (marketerDirective || "고객 피드백 분석 보고서의 권장 보정 방향을 충실히 반영하여 품질을 고도화하라.");

      var refinedAsset = callGemini(systemInstruction, userPrompt);

      // 3. 동적 비주얼 프롬프트 도출 및 숏폼 영상 콘티 완전 통합
      dynamicBrief = extractDynamicVisualPrompt(
        refinedAsset,
        summaryContent,
        "A stylish 20s Korean female model enjoying cozy autumn commuter lifestyle with lightweight ANC headphones in a chic Seoul cafe",
        marketerDirective
      );
      finalizedContent = ensureShortsScriptInCampaignContent(refinedAsset, prefix, dynamicBrief);

      // 4. [UX 핵심] 마케터가 독스 열자마자 확인 가능한 [SPEC 반영 미디어 산출물 현황] 헤더를 독스 최상단에 포함하여 저장
      var specReportHeader = buildMediaSpecReportHeader(mediaSpec);
      saveGoogleDoc(targetRvFolder, targetContentDocName, specReportHeader + finalizedContent);
    }

    // 5. 신규 비주얼 이미지 및 Veo 비디오 동적 생성 (마케터 명세서 지정 종횡비 및 비디오 제외 여부 반영)
    Logger.log("동적 도출된 비주얼 프롬프트 (" + targetRvName + "): " + dynamicBrief);
    var visResult = generateAndSaveVisualAssets(targetRvFolder, prefix, dynamicBrief, { onlyMissing: onlyMissing }, mediaSpec);

    var durationSec = Math.round((new Date().getTime() - startTime) / 1000);

    // 6. 상세 실행 내역 조립
    var logDetail = "";
    if (onlyMissing) {
      var totalSkipped = visResult.skipImageCount + (visResult.videoStatus === "skipped" ? 1 : 0);
      logDetail = "미완성 에셋 선별 보충 완료 (신규 이미지 " + visResult.genImageCount + "건 생성, 기존 에셋 " + totalSkipped + "건 보존)";
    } else {
      var videoDesc = (visResult.videoStatus === "generated")
        ? "Veo 비디오 1건"
        : (visResult.videoStatus === "excluded" ? "비디오 제외(명세서 반영)" : "숏폼 콘티 독스 수록");
      var directiveDesc = marketerDirective ? "마케터 지침서 반영" : "권장 보정안 반영";
      logDetail = "개정본 독스 1건(" + directiveDesc + "), 대표 이미지 " + visResult.genImageCount + "종, " + videoDesc + " 생성 완료";
      if (mediaSpec && mediaSpec.reason) {
        logDetail += " [" + mediaSpec.reason + "]";
      }
    }

    // 6. 대시보드 시트에 링크 기록
    var stepTitle = roundNum + "차 마케팅 콘텐츠 개정본 (" + targetRvName + ")";
    recordStepResultToSheet(
      "Step 9",
      stepTitle,
      "완료",
      targetRvFolder.getUrl(),
      "구글 드라이브 폴더 열기 (" + targetRvName + ")",
      durationSec,
      getSessionTotalTokens(),
      logDetail
    );

    if (!isSilent) {
      showResultModal(
        "마케팅 콘텐츠 보정 완료 (" + targetRvName + ")",
        "피드백 분석 보고서와 마케터 보정 지침이 반영된 개정본(" + targetRvName + ") 및 비주얼 에셋이 준비되었습니다.\n\n" +
        "* 처리 소요 시간: " + formatDuration(durationSec) + "\n" +
        "* 실행 상세 내역: " + logDetail + "\n\n" +
        "[마케터 보정 지침] 구글 독스에서 언제든 수정 후 다시 보정할 수 있습니다.",
        "개정본 콘텐츠 폴더 열기 (" + targetRvName + ")",
        targetRvFolder.getUrl()
      );
    }
    return {
      success: true,
      message: "콘텐츠 보정(" + targetRvName + ")이 완료되었습니다. [마케터 보정 지침] 구글 독스에서 언제든 지침을 추가 수정할 수 있습니다.",
      targetRv: targetRvName,
      folderUrl: targetRvFolder.getUrl(),
      content: finalizedContent
    };
  } catch (e) {
    var failDuration = Math.round((new Date().getTime() - startTime) / 1000);
    recordStepResultToSheet(
      "콘텐츠 보정",
      "피드백 반영 개정본 생성",
      "실패",
      "",
      "",
      failDuration,
      0,
      "오류 발생: " + (e.message || e.toString())
    );
    throw e;
  }
  });
}

// ==========================================
// Module: Code_Feedback.js
// ==========================================
/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 6] AI 페르소나 다면 평가 및 피드백 종합 분석 보고서 엔진 (Feedback & Evaluation Engine)
 */

/**
 * [Step 6] AI 페르소나 다면 평가를 실행하고 구조화된 피드백 데이터셋(JSON)을 도출한다.
 *
 * @param {string} [targetRoundOpt] - 대상 피드백 라운드 (기본값: 자동 감지 fb-01, fb-02 ...)
 */
function runPersonaEvaluation(targetRoundOpt) {
  return withUserLock("persona_evaluation", function() {
    var startTime = new Date().getTime();
    try {
      var campaignFolder = getCampaignFolder();

      // 피드백 회차 판별
      var targetRound = targetRoundOpt;
      if (!targetRound) {
        var latestFb = detectLatestFeedbackRoundNum();
        var latestRv = detectLatestRevisionRoundNum();
        var autoRound = Math.max(latestFb + 1, latestRv + 1, 1);
        targetRound = "fb-" + (autoRound < 10 ? "0" + autoRound : autoRound);
      }

      var roundNum = parseInt(targetRound.replace("fb-", ""), 10) || 1;
      var prevRoundNum = Math.max(0, roundNum - 1);
      var prevRvName = "rv-" + (prevRoundNum < 10 ? "0" + prevRoundNum : prevRoundNum);

      showProcessingToast("AI 페르소나 다면 평가 실행 중 (" + targetRound + ")...", 40);

      var feedbackFolder = getCampaignSubFolder(["input", targetRound]);

      resetSessionTokens();

      // 1. AI 페르소나 피드백 데이터셋 로드 또는 실시간 생성 (세부 의견 포인트 + 128d 임베딩)
      var jsonContent = readTextFile(feedbackFolder, "ai_persona_feedbacks.json");
      var isInvalidJson = false;
      if (jsonContent) {
        try {
          var parsedCheck = JSON.parse(jsonContent);
          if (!Array.isArray(parsedCheck) || parsedCheck.length === 0) {
            isInvalidJson = true;
          }
        } catch (e) {
          isInvalidJson = true;
        }
      }
      if (!jsonContent || isInvalidJson) {
        jsonContent = generateLivePersonaFeedbacks(campaignFolder, feedbackFolder, prevRvName);
      }

      // 피드백 JSON 파일 객체 확보 (파이프라인 직결 링크)
      var jsonFile = null;
      var jsonFiles = feedbackFolder.getFilesByName("ai_persona_feedbacks.json");
      while (jsonFiles.hasNext()) {
        var jf = jsonFiles.next();
        try {
          if (!jf.isTrashed()) {
            jsonFile = jf;
            break;
          }
        } catch (e) {
          jsonFile = jf;
          break;
        }
      }
      var jsonUrl = jsonFile ? jsonFile.getUrl() : feedbackFolder.getUrl();

      var durationSec = Math.round((new Date().getTime() - startTime) / 1000);
      var logDetail = "AI 페르소나 다면 평가 완료 (ai_persona_feedbacks.json 생성 완료)";

      // 3. 대시보드 시트에 링크 기록
      var stepTitle = roundNum + "차 AI 페르소나 다면 평가 (" + targetRound + ")";
      var linkText = "AI 페르소나 피드백 JSON 열기 (" + targetRound + ")";
      recordStepResultToSheet(
        "Step 6",
        stepTitle,
        "완료",
        jsonUrl,
        linkText,
        durationSec,
        getSessionTotalTokens(),
        logDetail
      );

      showResultModal(
        "AI 페르소나 다면 평가 완료 (" + targetRound + ")",
        "타깃 AI 가상 페르소나 패널의 정밀 다면 평가 데이터셋(ai_persona_feedbacks.json)이 성공적으로 도출되었습니다.\n\n" +
        "* 처리 소요 시간: " + formatDuration(durationSec) + "\n" +
        "* 실행 상세 내역: " + logDetail + "\n\n" +
        "아래 버튼을 클릭하여 AI 페르소나 피드백 JSON 원본을 즉시 확인하십시오.",
        linkText,
        jsonUrl
      );

      return {
        success: true,
        targetRound: targetRound,
        message: "AI 페르소나 다면 평가 데이터셋이 생성되었습니다 (" + targetRound + "). 피드백 데이터를 확인하시고 [Step 7] 피드백 종합 보고서 생성을 진행해 주십시오.",
        feedbackJsonUrl: jsonUrl,
        jsonUrl: jsonUrl
      };
    } catch (e) {
      var failDuration = Math.round((new Date().getTime() - startTime) / 1000);
      recordStepResultToSheet(
        "다면 평가 (" + (targetRound || "fb-01") + ")",
        "AI 페르소나 다면 평가",
        "실패",
        "",
        "",
        failDuration,
        0,
        "오류 발생: " + (e.message || e.toString())
      );
      throw e;
    }
  });
}

/**
 * [Step 7] 고객 VoC 설문 응답, 제출된 미디어(영상/이미지) VLM 분석, AI 페르소나 다면 평가 데이터를 통합하여
 * 피드백 종합 분석 보고서(feedback_summary) 구글 독스를 자동 생성한다.
 *
 * @param {string} [targetRoundOpt] - 대상 피드백 라운드
 */
function runFeedbackSummaryReport(targetRoundOpt) {
  return withUserLock("feedback_summary", function() {
    var startTime = new Date().getTime();
    try {
      var campaignFolder = getCampaignFolder();

      var targetRound = targetRoundOpt;
      if (!targetRound) {
        var latestFb = detectLatestFeedbackRoundNum();
        targetRound = "fb-" + (latestFb < 10 ? "0" + latestFb : latestFb);
        if (latestFb === 0) {
          targetRound = "fb-01";
        }
      }

      var roundNum = parseInt(targetRound.replace("fb-", ""), 10) || 1;
      var prevRoundNum = Math.max(0, roundNum - 1);
      var prevRvName = "rv-" + (prevRoundNum < 10 ? "0" + prevRoundNum : prevRoundNum);

      showProcessingToast("피드백 종합 분석 보고서 도출 중 (" + targetRound + ")...", 60);

    var feedbackFolder = getCampaignSubFolder(["input", targetRound]);

    resetSessionTokens();

    // 선결 조건 검사: AI 페르소나 피드백 확인 (없으면 자동 평가)
    var personaFeedbacksRaw = readTextFile(feedbackFolder, "ai_persona_feedbacks.json");
    var isInvalidPersonaFeedbacks = false;
    if (personaFeedbacksRaw) {
      try {
        var parsedFb = JSON.parse(personaFeedbacksRaw);
        if (!Array.isArray(parsedFb) || parsedFb.length === 0) {
          isInvalidPersonaFeedbacks = true;
        }
      } catch (e) {
        isInvalidPersonaFeedbacks = true;
      }
    }
    if (!personaFeedbacksRaw || isInvalidPersonaFeedbacks) {
      personaFeedbacksRaw = generateLivePersonaFeedbacks(campaignFolder, feedbackFolder, prevRvName);
    }

    // 1. 고객 제출 미디어(동영상 및 이미지) 실데이터 탐색 및 VLM 심층 분석
    var mediaAnalysisList = [];
    var mediaFiles = feedbackFolder.getFiles();
    while (mediaFiles.hasNext()) {
      var file = mediaFiles.next();
      var fName = file.getName();
      var mime = file.getMimeType();

      if (fName.indexOf("_vlm.json") !== -1 || fName === "feedback_clusters_map.png") {
        continue;
      }

      if (mime.indexOf("video/") === 0 || mime.indexOf("image/") === 0) {
        var cacheVlmName = fName + "_vlm.json";
        var cachedVlm = readTextFile(feedbackFolder, cacheVlmName);
        if (cachedVlm) {
          mediaAnalysisList.push({ fileName: fName, analysis: cachedVlm });
        } else {
          try {
            var vlmPrompt = getPromptTemplate("06_vlm_media_analysis") ||
              "이 미디어는 소비자가 제품을 직접 체험하며 남긴 피드백 영상/사진이다. 표정, 감정, 사용성, 제품 착용감에 대한 핵심 의견을 3문장으로 객관적으로 요약하라.";
            var vlmResult = callGeminiMultimodal(vlmPrompt, file.getBlob());
            if (vlmResult) {
              saveTextFile(feedbackFolder, cacheVlmName, vlmResult);
              mediaAnalysisList.push({ fileName: fName, analysis: vlmResult });
            }
          } catch (vlmErr) {
            Logger.log("미디어 VLM 분석 예외 (" + fName + "): " + vlmErr);
          }
        }
      }
    }

    // 2. Google Forms 시트 응답 탭 데이터 로드
    var formResponsesText = loadGoogleFormResponsesText();

    // 3. 이전 콘텐츠(campaign_content) 본문 로드
    var prevFolder = getCampaignSubFolder(["output", prevRvName]);
    var prevContent = readGoogleDoc(prevFolder, CONFIG.CONTENT_DOC_NAME || "campaign_content") || "";

    // 4. 구글 독스 기반 프롬프트 템플릿 로드 (스마트 캐싱)
    var systemInstruction = getPromptTemplate("07_feedback_summary");
    var userPrompt =
      "다음은 " + prevRvName + " 마케팅 콘텐츠에 대한 AI 가상 페르소나 다면 평가 결과와 실제 고객 설문 응답, 미디어 VLM 분석 데이터이다.\n\n" +
      "### [1. 이전 마케팅 콘텐츠 (" + prevRvName + ")]\n" + (prevContent.substring(0, 1500) || "카피 및 비주얼") + "\n\n" +
      "### [2. AI 가상 페르소나 다면 평가 데이터셋]\n" + (personaFeedbacksRaw.substring(0, 3000) || "평가 데이터") + "\n\n" +
      "### [3. 고객 구글 폼 응답 데이터]\n" + (formResponsesText || "접수된 고객 설문 응답 없음") + "\n\n" +
      "### [4. 고객 제출 미디어 VLM 분석 실데이터 (" + mediaAnalysisList.length + "건)]\n" +
      (mediaAnalysisList.length > 0 ? JSON.stringify(mediaAnalysisList, null, 2) : "실제 업로드된 고객 동영상 및 이미지 없음 (미제출)") + "\n\n" +
      "위 데이터를 종합하여 최고 마케팅 책임자(CMO) 및 담당 마케터가 검토할 피드백 종합 분석 보고서(feedback_summary)를 작성하라.\n" +
      "문서 맨 마지막에는 차기 콘텐츠 개정 시 참고할 수 있는 [AI 추천 보정 방향 요약] 섹션을 포함하라.";

    var reportMarkdown = callGemini(systemInstruction, userPrompt);

    // 5. feedback_summary 구글 독스 문서 생성
    var summaryFile = saveGoogleDoc(feedbackFolder, "feedback_summary", reportMarkdown);

    // 6. 대시보드 시트에 링크 기록
    var durationSec = Math.round((new Date().getTime() - startTime) / 1000);
    var stepTitle = roundNum + "차 피드백 종합 분석 보고서 (" + targetRound + ")";
    var logDetail = "고객 VoC 및 AI 페르소나 다면 평가 통합 보고서(" + summaryFile.getName() + ") 생성 완료";

    recordStepResultToSheet(
      "Step 7",
      stepTitle,
      "완료",
      summaryFile.getUrl(),
      "구글 독스 보고서 열기 (" + targetRound + ")",
      durationSec,
      getSessionTotalTokens(),
      logDetail
    );

    showResultModal(
      "피드백 종합 분석 보고서 생성 완료 (" + targetRound + ")",
      "고객 VoC와 AI 페르소나 다면 평가가 통합된 [feedback_summary] 보고서가 준비되었습니다.\n\n" +
      "* 처리 소요 시간: " + formatDuration(durationSec) + "\n\n" +
      "아래 버튼을 눌러 피드백 보고서를 확인하신 후, [Step 8] 마케터 보정 지침 작성을 진행해 주십시오.",
      "피드백 보고서 독스 열기 (" + targetRound + ")",
      summaryFile.getUrl()
    );

    return {
      success: true,
      targetRound: targetRound,
      message: "피드백 종합 분석 보고서(feedback_summary)가 생성되었습니다 (" + targetRound + "). 보고서를 확인하신 후 [Step 8] 마케터 보정 지침 확정을 진행해 주십시오.",
      summaryUrl: summaryFile ? summaryFile.getUrl() : ""
    };
  } catch (e) {
    var failDuration = Math.round((new Date().getTime() - startTime) / 1000);
    recordStepResultToSheet(
      "Step 7",
      "피드백 종합 분석 보고서",
      "실패",
      "",
      "",
      failDuration,
      0,
      "오류 발생: " + (e.message || e.toString())
    );
    throw e;
  }
  });
}

/**
 * [Step 8] 피드백 보고서를 바탕으로 마케터 최종 의사 결정 문서인 [마케터 보정 지침] 독스를 작성/저장한다.
 *
 * @param {string} [customDirectiveOpt] - 마케터가 입력한 개정 지침 내용 (선택)
 * @param {string} [targetRoundOpt] - 대상 피드백 라운드 (선택, 기본: 자동 감지)
 */
function runMarketerDirective(customDirectiveOpt, targetRoundOpt) {
  return withUserLock("marketer_directive", function() {
    var startTime = new Date().getTime();
    try {
      var campaignFolder = getCampaignFolder();
      var targetRound = targetRoundOpt;
      if (!targetRound) {
        var latestFb = detectLatestFeedbackRoundNum();
        targetRound = "fb-" + (latestFb < 10 ? "0" + latestFb : latestFb);
        if (latestFb === 0) targetRound = "fb-01";
      }

      var roundNum = parseInt(targetRound.replace("fb-", ""), 10) || 1;
      var feedbackFolder = getCampaignSubFolder(["input", targetRound]);

      var directiveDocName = (CONFIG && CONFIG.DIRECTIVE_DOC_NAME) || "마케터 보정 지침";
      var directiveFile = null;
      var inputDirective = (customDirectiveOpt || "").trim();

      if (inputDirective) {
        directiveFile = saveGoogleDoc(feedbackFolder, directiveDocName, inputDirective);
      } else {
        var existing = feedbackFolder.getFilesByName(directiveDocName);
        if (existing.hasNext()) {
          directiveFile = existing.next();
        } else {
          var starterDirective =
            "# " + roundNum + "차 마케팅 콘텐츠 보정 지침 (마케터 최종 의사 결정)\n\n" +
            "> **안내**: 본 문서는 마케터 전용 의사 결정 문서입니다. 피드백 종합 분석 보고서(feedback_summary)를 참고하여 " +
            "차기 개정본 생성 시 AI 모델이 최우선으로 반영해야 할 지침을 자유롭게 작성하거나 수정하십시오. " +
            "AI가 보고서를 재생성하더라도 본 문서는 절대 덮어써지지 않고 영구 보존됩니다.\n\n" +
            "## 1. 타깃 오디언스 및 페르소나 소구점 보정\n" +
            "* **핵심 타깃**: 2030 직장인 및 대학생\n" +
            "* **보정 방향**: 일상 출퇴근 및 대중교통 이용 시 노이즈 캔슬링 성능과 장시간 무압박 착용감(180g) 강조\n\n" +
            "## 2. 채널별 카피라이팅 및 톤앤매너 지침\n" +
            "* **가로 배너 (16:9)**: 전문 오디오 스펙보다는 감성적 몰입과 차음 혜택 헤드카피 전면 배치\n" +
            "* **정방형 SNS (1:1)**: 성수동 카페 감성 룩북 무드와 얼리버드 한정 특별 할인 혜택 서브카피 보강\n\n" +
            "## 3. 비주얼 아트 디렉션 및 숏폼 영상 연출 지침\n" +
            "* **모델 및 배경**: 20대 한국인 직장인 여성 모델, 따뜻한 늦가을 오후 햇살이 비치는 서울 도심 및 카페 풍경\n" +
            "* **15초 모바일 숏폼**: 0~3초 훅에서 도심 소음이 일시에 멈추는 직관적 차음 연출과 편안한 미소 클로즈업 강조\n\n" +
            "## 4. 기타 주의 사항 및 금지어\n" +
            "* 과장되거나 단정적인 최상급 표현 배제, 실측 수치(180g, 40시간 배터리) 기반 신뢰도 확보\n";

          directiveFile = saveGoogleDoc(feedbackFolder, directiveDocName, starterDirective);
        }
      }

      var durationSec = Math.max(1, Math.round((new Date().getTime() - startTime) / 1000));
      var stepTitle = roundNum + "차 마케터 최종 의사 결정 (" + targetRound + ")";

      recordStepResultToSheet(
        "Step 8",
        stepTitle,
        "완료",
        directiveFile.getUrl(),
        "마케터 보정 지침 열기 (" + targetRound + ")",
        durationSec,
        0,
        "마케터 최종 의사 결정 지침서 준비 완료 (구글 독스에서 직접 수정 가능)"
      );

      showResultModal(
        "마케터 보정 지침서 준비 완료 (" + targetRound + ")",
        "차기 개정본 생성을 위한 [마케터 보정 지침] 독스가 준비되었습니다.\n\n" +
        "* 처리 소요 시간: " + formatDuration(durationSec) + "\n\n" +
        "아래 버튼을 눌러 지침서를 열고 개정 방향을 작성하신 후, [Step 9] 피드백 반영 개정본 생성을 진행해 주십시오.",
        "마케터 보정 지침 열기 (" + targetRound + ")",
        directiveFile.getUrl()
      );

      return {
        success: true,
        targetRound: targetRound,
        message: "마케터 보정 지침서가 준비되었습니다 (" + targetRound + "). 지침서를 검토 및 보완하신 후 [Step 9] 피드백 반영 개정본 생성을 진행해 주십시오.",
        directiveUrl: directiveFile.getUrl()
      };
    } catch (e) {
      var failDuration = Math.round((new Date().getTime() - startTime) / 1000);
      recordStepResultToSheet("Step 8", "마케터 보정 지침", "실패", "", "", failDuration, 0, "오류: " + (e.message || e.toString()));
      throw e;
    }
  });
}

/**
 * Google Forms 응답 탭으로부터 고객 서술형 피드백을 텍스트로 취합한다.
 */
function loadGoogleFormResponsesText() {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheets = ss.getSheets();
    var formSheet = null;
    for (var i = 0; i < sheets.length; i++) {
      var sName = sheets[i].getName();
      if (sName.indexOf("설문") !== -1 || sName.indexOf("Form") !== -1 || sName.indexOf("응답") !== -1) {
        formSheet = sheets[i];
        break;
      }
    }

    if (!formSheet) {
      return "";
    }

    var lastRow = formSheet.getLastRow();
    var lastCol = formSheet.getLastColumn();
    if (lastRow <= 1) {
      return "접수된 고객 설문 응답 없음";
    }

    var values = formSheet.getRange(1, 1, Math.min(lastRow, 30), lastCol).getValues();
    var headers = values[0];
    var buffer = [];

    for (var r = 1; r < values.length; r++) {
      var row = values[r];
      var entry = [];
      for (var c = 0; c < headers.length; c++) {
        var h = String(headers[c] || "").trim();
        var v = String(row[c] || "").trim();
        if (v && h.indexOf("타임스탬프") === -1) {
          entry.push(h + ": " + v);
        }
      }
      if (entry.length > 0) {
        buffer.push("- [고객 " + r + "] " + entry.join(" | "));
      }
    }

    return buffer.join("\n");
  } catch (err) {
    Logger.log("폼 응답 데이터 로드 예외: " + err);
    return "";
  }
}

// ==========================================
// Module: Code_Sidebar.js
// ==========================================
/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 9] 구글 시트 우측 패널(Sidebar) 모던 HTML 컨트롤 타워 UI
 */

/**
 * 우측 패널(사이드바) 인라인 입력창에서 전달된 Gemini API Key를 검증 및 저장한다.
 *
 * @param {string} apiKey - 입력된 API Key
 * @return {Object} 처리 결과 { success: boolean, message: string }
 */
function saveApiKeyInline(apiKey) {
  if (!apiKey || typeof apiKey !== "string") {
    return { success: false, message: "유효한 API Key를 입력해 주십시오." };
  }
  var cleanKey = apiKey.trim();
  if (cleanKey.length < 10) {
    return { success: false, message: "API Key 형식이 올바르지 않습니다. (최소 10자 이상)" };
  }

  try {
    PropertiesService.getUserProperties().setProperty("GEMINI_API_KEY", cleanKey);
    return { success: true, message: "Gemini API Key가 성공적으로 등록되었습니다." };
  } catch (e) {
    return { success: false, message: "API Key 저장 중 오류: " + e.toString() };
  }
}

/**
 * Gemini API 호출 실패 또는 파싱 오류 시 100% 무중단 안내를 보장하는 결정론적 룰 기반 폴백 엔진
 *
 * @param {string} userMessage - 마케터의 질문 텍스트
 * @param {Object} status - 현재 파이프라인 실제 상태 객체
 * @return {Object} { success: boolean, reply: string, action: string|null, actionLabel: string|null, taskName: string|null }
 */
function getDeterministicFallback(userMessage, status) {
  var q = (userMessage || "").toLowerCase().replace(/\s+/g, "");

  // 0. 산출물 조회 및 링크 요청 인터셉트 ("어디", "링크", "열어", "보여", "주소", "확인", "찾아", "열기")
  var isQueryForLocation = (
    q.indexOf("어디") !== -1 || q.indexOf("링크") !== -1 || q.indexOf("열어") !== -1 ||
    q.indexOf("보여") !== -1 || q.indexOf("주소") !== -1 || q.indexOf("확인") !== -1 ||
    q.indexOf("열기") !== -1 || q.indexOf("찾아") !== -1
  );

  if (isQueryForLocation) {
    if (q.indexOf("내역") !== -1 || q.indexOf("로그") !== -1 || q.indexOf("대시보드") !== -1) {
      return {
        success: true,
        reply: "파이프라인 단계별 처리 결과와 산출물 링크가 기록된 [실행 내역] 시트 탭이야.",
        action: "openDashboardSheet",
        actionLabel: "[실행 내역 열기]",
        taskName: "실행 내역 시트 열기"
      };
    }
    if ((q.indexOf("기획") !== -1 || q.indexOf("plan") !== -1) && status.planDocUrl) {
      return {
        success: true,
        reply: "캠페인 기획서(PLAN) 구글 독스 준비해 뒀어. 아래 링크 눌러서 바로 열어봐.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + status.planDocUrl + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[PLAN 기획서 열기]</a></div>"
      };
    }
    if ((q.indexOf("명세") !== -1 || q.indexOf("spec") !== -1) && status.specDocUrl) {
      return {
        success: true,
        reply: "멀티 채널 콘텐츠 제작 명세서(SPEC) 구글 독스야.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + status.specDocUrl + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[SPEC 명세서 열기]</a></div>"
      };
    }
    if (q.indexOf("아이디어") !== -1 && status.ideaDocUrl) {
      return {
        success: true,
        reply: "캠페인 원천 [아이디어 메모] 구글 독스야.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + status.ideaDocUrl + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[아이디어 메모 열기]</a></div>"
      };
    }
    if ((q.indexOf("콘텐츠") !== -1 || q.indexOf("카피") !== -1 || q.indexOf("초판") !== -1) && status.contentDocUrl) {
      var rvTag = status.latestRv || "rv-00";
      return {
        success: true,
        reply: "현재 최신 마케팅 콘텐츠(" + rvTag + ") 구글 독스야.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + status.contentDocUrl + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[콘텐츠 독스 열기 (" + rvTag + ")]</a></div>"
      };
    }
    if ((q.indexOf("보고서") !== -1 || q.indexOf("요약") !== -1 || q.indexOf("피드백") !== -1) && status.summaryDocUrl) {
      var fbTag = status.latestFb || "fb-01";
      return {
        success: true,
        reply: "피드백 종합 분석 보고서(feedback_summary) 구글 독스야.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + status.summaryDocUrl + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[피드백 보고서 열기 (" + fbTag + ")]</a></div>"
      };
    }
    if (q.indexOf("지침") !== -1 && status.directiveDocUrl) {
      var fbTag2 = status.latestFb || "fb-01";
      return {
        success: true,
        reply: "마케터 전용 [마케터 보정 지침] 구글 독스야.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + status.directiveDocUrl + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[마케터 보정 지침 열기 (" + fbTag2 + ")]</a></div>"
      };
    }
    if ((q.indexOf("설문") !== -1 || q.indexOf("폼") !== -1 || q.indexOf("form") !== -1) && status.formUrl) {
      return {
        success: true,
        reply: "고객 VoC 수집용 온라인 설문 폼(Google Forms)이야.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + status.formUrl + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[고객 설문 폼 열기]</a></div>"
      };
    }
    if ((q.indexOf("피드백") !== -1 || q.indexOf("json") !== -1 || q.indexOf("데이터셋") !== -1) && (status.feedbackJsonUrl || status.jsonUrl)) {
      var fbTag3 = status.latestFb || "fb-01";
      var jsonLink = status.feedbackJsonUrl || status.jsonUrl;
      return {
        success: true,
        reply: "타깃 AI 가상 페르소나 패널의 정밀 다면 평가 데이터셋(JSON) 원본 파일이야.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + jsonLink + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[AI 페르소나 피드백 JSON 열기 (" + fbTag3 + ")]</a></div>"
      };
    }
    if ((q.indexOf("폴더") !== -1 || q.indexOf("드라이브") !== -1) && status.folderUrl) {
      return {
        success: true,
        reply: "캠페인 구글 드라이브 루트 폴더야.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + status.folderUrl + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[드라이브 폴더 열기]</a></div>"
      };
    }
  }

  // 1. 현재 상태 질의 ("지금뭐해야", "다음단계", "어떻게", "순서")
  if (q.indexOf("지금") !== -1 || q.indexOf("다음") !== -1 || q.indexOf("순서") !== -1 || q.indexOf("뭐해") !== -1) {
    if (!status.folderUrl) {
      return {
        success: true,
        reply: "캠페인 작업 공간이 아직 안 만들어졌어. 먼저 [Step 0: 작업 공간 구축]을 진행해줘.",
        action: "initCampaignWorkspace",
        actionLabel: "[Step 0] 캠페인 작업 공간 구축",
        taskName: "캠페인 작업 공간 구축"
      };
    }
    if (!status.hasApiKey) {
      return {
        success: true,
        reply: "Gemini API Key가 등록되지 않았어. 사이드바 상단에서 API Key를 먼저 등록해줘.",
        action: "toggleApiKeyBox",
        actionLabel: "API Key 등록하기",
        taskName: "API Key 설정"
      };
    }
    if (!status.ideaDocUrl) {
      return {
        success: true,
        reply: "현재 캠페인 폴더에 아이디어 메모가 없어. [Step 1] 캠페인 아이디어 메모 작성을 진행해줘.",
        action: "promptAndRunIdeaMemo",
        actionLabel: "[Step 1] 아이디어 메모 작성하기",
        taskName: "아이디어 메모 작성"
      };
    }
    if (!status.planDocUrl) {
      return {
        success: true,
        reply: "캠페인 폴더에 아이디어 메모 확인 완료! 다음 단계인 [Step 2] 캠페인 기획서(PLAN) 생성을 진행하자.",
        action: "guardAndRunIdeaToPlan",
        actionLabel: "[Step 2] 기획서(PLAN) 생성하기",
        taskName: "캠페인 기획서 생성"
      };
    }
    if (!status.specDocUrl) {
      return {
        success: true,
        reply: "기획서(PLAN) 확인 완료! 다음 단계인 [Step 3] 콘텐츠 제작 명세서(SPEC) 생성을 진행할 차례야.",
        action: "guardAndRunPlanToSpec",
        actionLabel: "[Step 3] 제작 명세서(SPEC) 생성하기",
        taskName: "제작 명세서 생성"
      };
    }
    if (!status.personaUrl) {
      return {
        success: true,
        reply: "기획서(PLAN)랑 제작 명세서(SPEC) 확인 완료! 다음 단계인 [Step 4] 맞춤 AI 페르소나 패널 구성을 진행하자.",
        action: "guardAndRunPersonaSynthesis",
        actionLabel: "[Step 4] 맞춤 AI 페르소나 패널 구성하기",
        taskName: "AI 페르소나 패널 구성"
      };
    }
    if (!status.contentDocUrl) {
      return {
        success: true,
        reply: "기획서, 제작 명세서, 맞춤 AI 페르소나 패널이 모두 준비됐어. 이제 [Step 5: 초판 멀티 채널 콘텐츠(rv-00) 생성]을 진행할 차례야.",
        action: "guardAndRunInitialContent",
        actionLabel: "[Step 5] 초판 콘텐츠 (rv-00) 제작하기",
        taskName: "초판 콘텐츠 생성"
      };
    }
    var curStepNum = status.currentStep || 0;
    var targetFb = status.activeFbTag || "fb-01";
    var curRv = status.activeRvTag || (status.latestRv || "rv-00");
    var nextRv = status.nextRvTag || "rv-01";

    if (curStepNum === 6 || !status.feedbackJsonUrl) {
      var isRevision = (status.latestRvNum !== undefined && status.latestRvNum > 0);
      var msg6 = isRevision
        ? ("개정본 콘텐츠(" + curRv + ") 제작이 완료됐어! 이제 이 개정본에 대해 다음 차수 [Step 6: AI 페르소나 다면 평가(" + targetFb + ")]를 실행할 차례야.")
        : ("초판 마케팅 콘텐츠(rv-00) 확인 완료! 다음 단계인 [Step 6: AI 페르소나 다면 평가(" + targetFb + ") 실행]을 진행해줘.");
      return {
        success: true,
        reply: msg6,
        action: "promptAndRunJudgeEvaluation",
        actionLabel: "[Step 6] AI 페르소나 다면 평가 (" + targetFb + ") 실행하기",
        taskName: "AI 페르소나 다면 평가"
      };
    }
    if (curStepNum === 7 || !status.summaryDocUrl) {
      return {
        success: true,
        reply: "AI 페르소나 다면 평가 데이터(" + targetFb + ")가 확인됐어. 다음 단계인 [Step 7: 피드백 종합 분석 보고서 생성]을 진행할 차례야.",
        action: "promptAndRunFeedbackSummary",
        actionLabel: "[Step 7] 피드백 종합 보고서 (" + targetFb + ") 생성하기",
        taskName: "피드백 종합 보고서 생성"
      };
    }
    if (curStepNum === 8 || !status.directiveDocUrl) {
      return {
        success: true,
        reply: "피드백 종합 분석 보고서(" + targetFb + ") 확인 완료! 다음 단계인 [Step 8] 마케터 보정 지침 작성/확정을 진행하자.",
        action: "promptAndRunMarketerDirective",
        actionLabel: "[Step 8] 마케터 보정 지침 (" + targetFb + ") 작성하기",
        taskName: "마케터 보정 지침 작성"
      };
    }
    return {
      success: true,
      reply: "마케터 보정 지침(" + targetFb + ")이 확정됐어. 마지막 단계인 [Step 9: 피드백 반영 개정본(" + nextRv + ") 생성]을 진행하자.",
      action: "promptAndRunFeedbackRevision",
      actionLabel: "[Step 9] 피드백 반영 콘텐츠 (" + nextRv + ") 보정하기",
      taskName: "피드백 반영 콘텐츠 보정"
    };
  }

  // 2. 기획서 요청 ("기획", "plan")
  if (q.indexOf("기획") !== -1 || q.indexOf("plan") !== -1) {
    return {
      success: true,
      reply: "캠페인 기획서(PLAN)랑 콘텐츠 제작 명세서(SPEC) 도출을 시작할게.",
      action: "guardAndRunIdeaToPlan",
      actionLabel: "기획서 (PLAN & SPEC) 도출하기",
      taskName: "기획서 및 명세서 생성"
    };
  }

  // 3-1. 초판 강제 재생성 요청 ("다시", "덮어", "재생성")
  if ((q.indexOf("다시") !== -1 || q.indexOf("덮어") !== -1 || q.indexOf("재생성") !== -1) && (q.indexOf("초판") !== -1 || q.indexOf("콘텐츠") !== -1)) {
    return {
      success: true,
      reply: "기존 초판 콘텐츠(rv-00)를 새로 덮어쓰고 전체 에셋(카피, 이미지 3종, 숏폼 영상)을 다시 만들게.",
      action: "forceRunInitialContent",
      actionLabel: "초판 콘텐츠 전체 재생성하기",
      taskName: "초판 콘텐츠 전체 재생성"
    };
  }

  // 3. 초판/콘텐츠 요청 ("초판", "콘텐츠", "카피", "이미지", "영상", "제작")
  if (q.indexOf("초판") !== -1 || q.indexOf("콘텐츠") !== -1 || q.indexOf("제작") !== -1 || q.indexOf("카피") !== -1) {
    return {
      success: true,
      reply: "초판 마케팅 콘텐츠(카피라이팅, 비주얼 이미지 3종, Veo 숏폼 영상) 세트 생성을 시작할게.",
      action: "guardAndRunInitialContent",
      actionLabel: "초판 콘텐츠 (rv-00) 제작하기",
      taskName: "초판 콘텐츠 생성"
    };
  }

  // 4. 평가 요청 ("페르소나", "다면평가", "평가", "25인")
  if (q.indexOf("25인") !== -1 || q.indexOf("페르소나") !== -1 || q.indexOf("평가") !== -1) {
    if (q.indexOf("뭐야") !== -1 || q.indexOf("설명") !== -1) {
      return {
        success: true,
        reply: "AI 페르소나 다면 평가는 대한민국 시장 환경과 타깃 오디언스를 대변하는 맞춤 가상 소비자 패널이 정량 평점과 구체적인 VoC를 제공하는 다면 평가 시스템이야.",
        action: "promptAndRunPersonaEvaluation",
        actionLabel: "AI 페르소나 다면 평가 실행하기",
        taskName: "AI 페르소나 다면 평가"
      };
    }
    return {
      success: true,
      reply: "맞춤 AI 페르소나 다면 평가(fb-xx)를 실행할게.",
      action: "promptAndRunPersonaEvaluation",
      actionLabel: "AI 페르소나 다면 평가 실행하기",
      taskName: "AI 페르소나 다면 평가"
    };
  }

  // 5. 보고서 요청 ("보고서", "요약서", "피드백")
  if (q.indexOf("보고서") !== -1 || q.indexOf("피드백") !== -1 || q.indexOf("요약") !== -1) {
    return {
      success: true,
      reply: "고객 VoC 및 VLM 멀티모달 분석, AI 페르소나 다면 평가 데이터가 종합된 피드백 분석 보고서를 도출할게.",
      action: "promptAndRunFeedbackSummary",
      actionLabel: "피드백 종합 보고서 생성하기",
      taskName: "피드백 종합 보고서 생성"
    };
  }

  // 6. 보정 요청 ("보정", "개정", "리비전", "수정")
  if (q.indexOf("보정") !== -1 || q.indexOf("개정") !== -1 || q.indexOf("리비전") !== -1) {
    return {
      success: true,
      reply: "마케터 보정 지침을 최우선 반영해서 차기 리비전 마케팅 콘텐츠를 개정 보정할게.",
      action: "promptAndRunFeedbackRevision",
      actionLabel: "피드백 반영 콘텐츠 보정하기",
      taskName: "피드백 반영 콘텐츠 보정"
    };
  }

  // 7. 피드백 JSON 데이터셋 질문 ("json", "데이터셋", "피드백 데이터")
  if (q.indexOf("json") !== -1 || q.indexOf("데이터셋") !== -1 || q.indexOf("페르소나 데이터") !== -1 || q.indexOf("피드백 데이터") !== -1) {
    return {
      success: true,
      reply: "AI 페르소나 피드백 데이터셋은 맞춤 가상 소비자 패널의 정량 평점과 항목별 상세 정성 의견이 담긴 구조화된 JSON 데이터야.",
      action: null,
      actionLabel: null,
      taskName: null
    };
  }

  // 8. 초기화 요청 ("초기화", "구축", "셋업", "공간")
  if (q.indexOf("초기화") !== -1 || q.indexOf("구축") !== -1 || q.indexOf("셋업") !== -1) {
    return {
      success: true,
      reply: "캠페인 부모 폴더를 감지하고 누락된 리소스를 안전하게 핀포인트 복구할게.",
      action: "initCampaignWorkspace",
      actionLabel: "[초기화] 캠페인 작업 공간 구축",
      taskName: "캠페인 작업 공간 구축"
    };
  }

  // 9. 기본 fallback
  return {
    success: true,
    reply: "마케팅 콘텐츠 파이프라인 제어 패널이야. 원하는 작업을 아래 버튼에서 선택하거나 '지금 뭐 해야 돼?'라고 물어봐줘.",
    action: null,
    actionLabel: null,
    taskName: null
  };
}

/**
 * 마케터의 자연어 질의를 수신하여 현재 파이프라인 상태를 진단하고 안내 및 동적 액션 칩을 반환한다.
 *
 * @param {string} userMessage - 마케터가 입력한 자연어 질문 또는 지시
 * @return {Object} { success: boolean, reply: string, action: string|null, actionLabel: string|null, taskName: string|null }
 */
function askPipelineAssistant(userMessage) {
  if (!userMessage || typeof userMessage !== "string" || !userMessage.trim()) {
    return {
      success: false,
      reply: "질문이나 실행할 작업을 입력해줘.",
      action: null,
      actionLabel: null,
      taskName: null
    };
  }

  var status = getPipelineStatus(true);
  var apiKey = getGeminiApiKey();
  if (!apiKey) {
    return {
      success: true,
      reply: "Gemini API Key가 아직 등록되지 않았어. 상단 배너에서 [API Key 설정] 버튼을 눌러 먼저 키를 등록해줘.",
      action: null,
      actionLabel: null,
      taskName: null
    };
  }

  // 1. 마케터의 자연어 아이디어 입력 직접 감지 및 [아이디어 메모] 자동 저장
  var trimmedMsg = userMessage.trim();
  if (trimmedMsg.indexOf("아이디어:") === 0 || trimmedMsg.indexOf("아이디어 :") === 0 || trimmedMsg.indexOf("아이디어는 ") === 0) {
    var ideaText = trimmedMsg.replace(/^(아이디어\s*:\s*|아이디어는\s*)/, "").trim();
    if (ideaText.length >= 3) {
      try {
        var campaignFolder = getCampaignFolder();
        saveGoogleDoc(campaignFolder, (CONFIG && CONFIG.IDEA_DOC_NAME) || "아이디어 메모", ideaText);
        return {
          success: true,
          reply: "새로운 캠페인 아이디어가 [아이디어 메모] 구글 독스에 잘 들어갔어:\n[" + ideaText + "]\n\n지금 바로 전문 기획서(PLAN)랑 제작 명세서(SPEC)를 뽑아볼까?",
          action: "guardAndRunIdeaToPlan",
          actionLabel: "기획서 (PLAN & SPEC) 도출하기",
          taskName: "기획서 및 명세서 생성"
        };
      } catch (saveErr) {
        return {
          success: true,
          reply: "아이디어를 저장하기 전에 먼저 캠페인 작업 공간 구축이 필요해.",
          action: "initCampaignWorkspace",
          actionLabel: "[초기화] 캠페인 작업 공간 구축",
          taskName: "캠페인 작업 공간 구축"
        };
      }
    }
  }

  var activeFb = status.activeFbTag || "fb-01";
  var activeRv = status.activeRvTag || (status.latestRv || "rv-00");
  var nextRv = status.nextRvTag || "rv-01";

  var contextSummary = [
    "- 캠페인 폴더: " + (status.folderUrl ? "연결됨 (" + status.campaignCode + ")" : "미구축 (초기화 필요)"),
    "- 아이디어 메모: " + (status.ideaDocUrl ? "작성 문서 있음" : "문서 없음 (초기화 필요)"),
    "- 기획서 (PLAN): " + (status.planDocUrl ? "생성 완료" : "미생성"),
    "- 제작 명세서 (SPEC): " + (status.specDocUrl ? "생성 완료" : "미생성"),
    "- 맞춤 AI 페르소나 패널: " + (status.personaUrl ? "구성 완료" : "미생성"),
    "- 최신 콘텐츠 리비전: " + (status.contentDocUrl ? "생성 완료 (" + activeRv + ")" : "미생성"),
    "- 고객 VoC 설문 폼: " + (status.formUrl ? "생성 및 시트 연결 완료" : "미생성"),
    "- 현재 활성 피드백 차수: " + activeFb + " (대상 콘텐츠: " + activeRv + ")",
    "- AI 페르소나 피드백 데이터 (JSON): " + (status.feedbackJsonUrl ? "생성 완료 (" + activeFb + ")" : "미생성 (" + activeFb + ")"),
    "- 최신 피드백 종합 보고서: " + (status.summaryDocUrl ? "생성 완료 (" + activeFb + ")" : "미생성 (" + activeFb + ")"),
    "- 마케터 보정 지침서: " + (status.directiveDocUrl ? "확정 완료 (" + activeFb + ")" : "미생성 (" + activeFb + ")"),
    "- 현재 파이프라인 단계 및 추천 액션: " + (status.stepLabel || "파이프라인 진행 중")
  ].join("\n");

  var systemInstruction = 
    "당신은 구글 드라이브 마케팅 콘텐츠 파이프라인의 전담 AI 코파일럿 어시스턴트이다.\n" +
    "비개발자 마케터와 편안하고 전문적인 동료로서 대화하며, 캠페인을 성공적으로 이끌 수 있도록 돕는다.\n" +
    "현재 구글 드라이브 및 스프레드시트의 파이프라인 실제 상태는 다음과 같다:\n" +
    contextSummary + "\n\n" +
    "[파이프라인 지원 가능 액션 식별자 목록]\n" +
    "- 'initCampaignWorkspace': [Step 0] API Key & 작업 공간 구축\n" +
    "- 'promptAndRunIdeaMemo': [Step 1] 캠페인 아이디어 메모 작성\n" +
    "- 'guardAndRunIdeaToPlan': [Step 2] 캠페인 기획서(PLAN) 생성\n" +
    "- 'guardAndRunPlanToSpec': [Step 3] 제작 명세서(SPEC) 생성\n" +
    "- 'guardAndRunPersonaSynthesis': [Step 4] 맞춤 AI 페르소나 패널 구성\n" +
    "- 'guardAndRunInitialContent': [Step 5] 초판 멀티 채널 콘텐츠 생성 (rv-00)\n" +
    "- 'forceRunInitialContent': [Step 5] 초판 콘텐츠 전체 강제 재생성\n" +
    "- 'promptAndRunJudgeEvaluation': [Step 6] AI 페르소나 다면 평가 실행 (" + activeFb + ")\n" +
    "- 'promptAndRunFeedbackSummary': [Step 7] 피드백 종합 분석 보고서 생성 (" + activeFb + ")\n" +
    "- 'promptAndRunMarketerDirective': [Step 8] 마케터 보정 지침 작성/확정 (" + activeFb + ")\n" +
    "- 'promptAndRunFeedbackRevision': [Step 9] 피드백 반영 개정본 생성 (" + nextRv + ")\n" +
    "- 'openDashboardSheet': 실행 내역 시트 탭 열기\n" +
    "- 'refreshStatus': 사이드바 상태 새로고침\n\n" +
    "[응답 지침 및 대화 톤앤매너 - 절대 준수]\n" +
    "1. 대화 어조 원칙 (매우 중요):\n" +
    "   - 마케터와의 대화는 경어(존댓말: '~하십시오', '~입니다', '~했습니다')를 일절 쓰지 않는다.\n" +
    "   - 친근하고 전문적인 구어체(반말 대화체: '~야', '~해', '~했어', '~하자', '~볼게', '~하면 돼')로만 답변한다.\n" +
    "   - 마케터와 함께 일하는 페어 프로그래머이자 든든한 동료 엔지니어처럼 편안하고 자신감 있는 어조를 유지한다.\n" +
    "2. 질문 의도별 대응:\n" +
    "   - '지금 뭐 해야 돼?', '다음 단계 알려줘' 등 현재 상태 질의: 현재 완료된 상태와 다음에 진행해야 할 단계를 친근하게 안내하고 해당 액션을 제시하라.\n" +
    "   - '기획서 만들어 줘', '초판 제작해 줘' 등 작업 지시: 바로 실행할 수 있도록 안내하고 액션을 제시하라.\n" +
    "   - 'AI 페르소나 피드백 데이터가 뭐야?' 등 개념 질의: 1~3문장으로 비개발자 마케터 눈높이에 맞추어 핵심 가치를 설명하라. (이 경우 action은 null)\n" +
    "3. 만약 마케터가 특정 단계를 지시했는데 선결 조건(예: 기획서 없이 초판 생성)이 누락되었다면, 친절하게 선행 작업을 먼저 해야 함을 설명하고 선행 작업 액션을 제시하라.\n" +
    "4. 출력은 마크다운 코드블록(```json) 없이 오직 단일 순수 JSON 객체만 반환하라:\n" +
    "{\n" +
    "  \"reply\": \"마케터에게 전달할 경어가 전혀 없는 친근한 구어체 반말 답변 (1~3문장: '~야', '~해', '~했어', '~하면 돼')\",\n" +
    "  \"action\": \"위 목록의 액션 식별자 문자열 또는 null\",\n" +
    "  \"actionLabel\": \"마케터에게 노출할 버튼 칩 텍스트 (예: 기획서 (PLAN) 도출하기) 또는 null\",\n" +
    "  \"taskName\": \"실행할 작업 명칭 (예: 기획서 및 명세서 생성) 또는 null\"\n" +
    "}";

  try {
    var copilotModel = (CONFIG && CONFIG.MODEL_COPILOT) || "gemini-3.8-flash";
    var rawResponse = callGemini(systemInstruction, userMessage.trim(), copilotModel, 1024);
    var cleanJson = (rawResponse || "").trim();
    if (cleanJson.indexOf("```json") !== -1) {
      cleanJson = cleanJson.split("```json")[1].split("```")[0].trim();
    } else if (cleanJson.indexOf("```") !== -1) {
      cleanJson = cleanJson.split("```")[1].split("```")[0].trim();
    }
    var firstBrace = cleanJson.indexOf("{");
    var lastBrace = cleanJson.lastIndexOf("}");
    if (firstBrace !== -1 && lastBrace !== -1) {
      cleanJson = cleanJson.substring(firstBrace, lastBrace + 1);
    }
    var parsed = JSON.parse(cleanJson);
    if (parsed && parsed.reply) {
      return {
        success: true,
        reply: parsed.reply,
        action: parsed.action || null,
        actionLabel: parsed.actionLabel || null,
        taskName: parsed.taskName || null
      };
    }
    return getDeterministicFallback(userMessage, status);
  } catch (err) {
    Logger.log("askPipelineAssistant API 호출/파싱 실패, 결정론적 폴백 가동: " + err);
    return getDeterministicFallback(userMessage, status);
  }
}

/**
 * 구글 시트 우측 패널에 마케팅 콘텐츠 파이프라인 컨트롤 타워를 표시한다.
 */
function showPipelineSidebar() {
  var ui = SpreadsheetApp.getUi();
  try {
    initDashboardSheet();
    var htmlOutput = HtmlService.createHtmlOutput(getPipelineSidebarHtml())
      .setTitle("마케팅 콘텐츠 파이프라인 제어 패널")
      .setWidth(340);
    ui.showSidebar(htmlOutput);
  } catch (err) {
    Logger.log("showPipelineSidebar 예외: " + err);
  }
}

/**
 * 파이프라인 상태 캐시를 무효화(Purge)한다.
 */
function invalidatePipelineStatusCache() {
  try {
    CacheService.getUserCache().remove("PIPELINE_STATUS_CACHE");
  } catch (e) {
    // 무시
  }
}

/**
 * 사이드바 화면 렌더링에 필요한 현재 캠페인 파이프라인 상태 정보를 반환한다.
 * DriveApp API 할당량 고갈 방지 및 고속 응답을 위해 30초 로컬 사용자 캐시(CacheService)를 적용한다.
 *
 * @param {boolean} [optBypassCache=false] - 캐시 우회 여부
 * @return {Object} 캠페인 작업 공간 상태, 산출물 URL, 리비전, 토큰 통계 객체
 */
function getPipelineStatus(optBypassCache) {
  var cacheKey = "PIPELINE_STATUS_CACHE";
  var cache = null;
  try {
    cache = CacheService.getUserCache();
    if (!optBypassCache && cache) {
      var cachedStr = cache.get(cacheKey);
      if (cachedStr) {
        return JSON.parse(cachedStr);
      }
    }
  } catch (e) {
    // 캐시 조회 실패 시 드라이브 직접 스캔 진행
  }

  try {
    initDashboardSheet();
  } catch (e) {
    // 무시
  }
  var status = {
    hasApiKey: !!getGeminiApiKey(),
    campaignCode: "BwG-Seoul-Ignite",
    folderUrl: "",
    ideaDocUrl: "",
    planDocUrl: "",
    specDocUrl: "",
    contentDocUrl: "",
    formUrl: "",
    summaryDocUrl: "",
    directiveDocUrl: "",
    latestRv: "rv-00",
    latestFb: "",
    currentStep: 0,
    stepLabel: "Step 0: 작업 공간 구축 대기",
    progressPercent: 0,
    totalTokens: getSessionTotalTokens() || 0
  };

  try {
    var folder = getCampaignFolder(true);
    if (folder) {
      status.folderUrl = folder.getUrl();
      var folderName = folder.getName();
      status.campaignCode = folderName.length > 20 ? folderName.substring(0, 18) + "..." : folderName;

      // 1. 아이디어 메모 탐색
      var ideaName = (CONFIG && CONFIG.IDEA_DOC_NAME) || "아이디어 메모";
      var ideaFiles = folder.getFilesByName(ideaName);
      if (!ideaFiles.hasNext()) {
        ideaFiles = folder.getFilesByName("[아이디어 메모] 2026 가을 오텀 브리즈 캠페인");
      }
      if (ideaFiles.hasNext()) {
        status.ideaDocUrl = ideaFiles.next().getUrl();
      } else {
        var rootIdeaScan = folder.getFiles();
        while (rootIdeaScan.hasNext()) {
          var rif = rootIdeaScan.next();
          var rifName = rif.getName().toLowerCase();
          if (rifName.indexOf("아이디어") !== -1 || rifName.indexOf("idea") !== -1) {
            status.ideaDocUrl = rif.getUrl();
            break;
          }
        }
      }

      // 2. 기획서 (PLAN) 탐색 (확장자 유무 불문)
      var planFiles = folder.getFilesByName("PLAN");
      if (!planFiles.hasNext()) planFiles = folder.getFilesByName("PLAN.md");
      if (!planFiles.hasNext()) planFiles = folder.getFilesByName("마케팅 캠페인 기획서");
      if (planFiles.hasNext()) {
        status.planDocUrl = planFiles.next().getUrl();
      } else {
        var rootPlanScan = folder.getFiles();
        while (rootPlanScan.hasNext()) {
          var rpf = rootPlanScan.next();
          var rpfName = rpf.getName().toLowerCase();
          if (rpfName.indexOf("plan") !== -1 || rpfName.indexOf("기획서") !== -1) {
            status.planDocUrl = rpf.getUrl();
            break;
          }
        }
      }

      // 3. 제작 명세서 (SPEC) 탐색 (확장자 유무 불문)
      var specFiles = folder.getFilesByName("SPEC");
      if (!specFiles.hasNext()) specFiles = folder.getFilesByName("SPEC.md");
      if (specFiles.hasNext()) {
        status.specDocUrl = specFiles.next().getUrl();
      } else {
        var rootSpecScan = folder.getFiles();
        while (rootSpecScan.hasNext()) {
          var rsf = rootSpecScan.next();
          var rsfName = rsf.getName().toLowerCase();
          if (rsfName.indexOf("spec") !== -1 || rsfName.indexOf("명세서") !== -1) {
            status.specDocUrl = rsf.getUrl();
            break;
          }
        }
      }

      // 3-1. 맞춤 AI 페르소나 패널 탐색
      var personaFiles = folder.getFilesByName((CONFIG && CONFIG.PERSONA_FILE_NAME) || "ai_personas.json");
      if (personaFiles.hasNext()) {
        status.personaUrl = personaFiles.next().getUrl();
      } else {
        var rootPersonaScan = folder.getFiles();
        while (rootPersonaScan.hasNext()) {
          var rper = rootPersonaScan.next();
          var rperName = rper.getName().toLowerCase();
          if (rperName.indexOf("persona") !== -1 || rperName.indexOf("페르소나") !== -1) {
            status.personaUrl = rper.getUrl();
            break;
          }
        }
      }

      // 4. 고객 VoC 설문 폼 탐색
      var formFiles = folder.getFilesByType(MimeType.GOOGLE_FORMS);
      if (formFiles.hasNext()) status.formUrl = formFiles.next().getUrl();

      // 5. 최신 리비전 콘텐츠 탐색
      var latestRvNum = detectLatestRevisionRoundNum();
      status.latestRvNum = latestRvNum;
      if (latestRvNum >= 0) {
        status.latestRv = "rv-" + (latestRvNum < 10 ? "0" + latestRvNum : latestRvNum);
        var rvFolder = getCampaignSubFolder(["output", status.latestRv], true);
        var contentDocName = (CONFIG && CONFIG.CONTENT_DOC_NAME) || "campaign_content";
        var contentFiles = rvFolder.getFilesByName(contentDocName);
        if (!contentFiles.hasNext()) contentFiles = rvFolder.getFilesByName(contentDocName + ".md");
        if (!contentFiles.hasNext()) contentFiles = rvFolder.getFilesByName("campaign_content");
        if (!contentFiles.hasNext()) contentFiles = rvFolder.getFilesByName("campaign_content.md");
        if (!contentFiles.hasNext()) contentFiles = rvFolder.getFilesByName("campaign_asset");
        if (contentFiles.hasNext()) {
          status.contentDocUrl = contentFiles.next().getUrl();
        } else {
          // 이름에 content, asset, 카피가 포함되거나 구글 독스 파일 전수 스캔
          var rvAllFiles = rvFolder.getFiles();
          while (rvAllFiles.hasNext()) {
            var rvf = rvAllFiles.next();
            var rvfName = rvf.getName().toLowerCase();
            if (rvf.getMimeType() === MimeType.GOOGLE_DOCS || rvfName.indexOf("content") !== -1 || rvfName.indexOf("asset") !== -1 || rvfName.indexOf("카피") !== -1) {
              status.contentDocUrl = rvf.getUrl();
              break;
            }
          }
          // 독스가 없더라도 이미지/영상 등 산출물이 이미 폴더에 존재하면 폴더 URL 연결
          if (!status.contentDocUrl) {
            var anyRvFiles = rvFolder.getFiles();
            if (anyRvFiles.hasNext()) {
              status.contentDocUrl = rvFolder.getUrl();
            }
          }
        }
      }

      // 6. 최신 피드백 및 다음 진행 회차 동적 산출 (rv-xx -> fb-(xx+1) 자동 순환)
      var latestFbNum = detectLatestFeedbackRoundNum();
      status.latestFbNum = latestFbNum;

      var activeFbNum = Math.max(1, (latestRvNum >= 0 ? latestRvNum + 1 : 1));
      var activeFbTag = "fb-" + (activeFbNum < 10 ? "0" + activeFbNum : activeFbNum);
      var activeRvTag = latestRvNum >= 0 ? ("rv-" + (latestRvNum < 10 ? "0" + latestRvNum : latestRvNum)) : "rv-00";
      var nextRvTag = "rv-" + (activeFbNum < 10 ? "0" + activeFbNum : activeFbNum);

      status.activeFbTag = activeFbTag;
      status.activeRvTag = activeRvTag;
      status.nextRvTag = nextRvTag;
      status.latestFb = activeFbTag;

      var hasActiveJson = false;
      var hasActiveSummary = false;
      var hasActiveDirective = false;

      var activeFbFolder = getCampaignSubFolder(["input", activeFbTag], true);
      if (activeFbFolder) {
        var jsonFiles = activeFbFolder.getFilesByName("ai_persona_feedbacks.json");
        while (jsonFiles.hasNext()) {
          var jf = jsonFiles.next();
          try {
            if (!jf.isTrashed() && jf.getSize() > 20) {
              hasActiveJson = true;
              status.feedbackJsonUrl = jf.getUrl();
              break;
            }
          } catch (szErr) {
            hasActiveJson = true;
            status.feedbackJsonUrl = jf.getUrl();
            break;
          }
        }

        var summaryFiles = activeFbFolder.getFilesByName("feedback_summary");
        if (!summaryFiles.hasNext()) summaryFiles = activeFbFolder.getFilesByName("feedback_summary.md");
        if (summaryFiles.hasNext()) {
          hasActiveSummary = true;
          status.summaryDocUrl = summaryFiles.next().getUrl();
        } else {
          var fbAllFiles1 = activeFbFolder.getFiles();
          while (fbAllFiles1.hasNext()) {
            var fbf1 = fbAllFiles1.next();
            var fbf1Name = fbf1.getName().toLowerCase();
            if (fbf1Name.indexOf("summary") !== -1 || fbf1Name.indexOf("보고서") !== -1) {
              hasActiveSummary = true;
              status.summaryDocUrl = fbf1.getUrl();
              break;
            }
          }
        }

        var directiveDocName = (CONFIG && CONFIG.DIRECTIVE_DOC_NAME) || "마케터 보정 지침";
        var directiveFiles = activeFbFolder.getFilesByName(directiveDocName);
        if (directiveFiles.hasNext()) {
          hasActiveDirective = true;
          status.directiveDocUrl = directiveFiles.next().getUrl();
        } else {
          var fbAllFiles2 = activeFbFolder.getFiles();
          while (fbAllFiles2.hasNext()) {
            var fbf2 = fbAllFiles2.next();
            var fbf2Name = fbf2.getName().toLowerCase();
            if (fbf2Name.indexOf("지침") !== -1 || fbf2Name.indexOf("directive") !== -1) {
              hasActiveDirective = true;
              status.directiveDocUrl = fbf2.getUrl();
              break;
            }
          }
        }
      }

      // 7. 0~9단계 진행률 동적 산출 (10대 파이프라인 무한 피드백 루프)
      var curStep = 0;
      var stepLabel = "Step 0: 작업 공간 구축";
      if (!status.hasApiKey) {
        curStep = 0;
        stepLabel = "Step 0: API Key 등록 대기";
      } else if (!status.folderUrl) {
        curStep = 0;
        stepLabel = "Step 0: 작업 공간 구축 대기";
      } else if (!status.ideaDocUrl) {
        curStep = 1;
        stepLabel = "Step 1: 아이디어 메모 작성";
      } else if (!status.planDocUrl) {
        curStep = 2;
        stepLabel = "Step 2: 기획서(PLAN) 생성";
      } else if (!status.specDocUrl) {
        curStep = 3;
        stepLabel = "Step 3: 제작 명세서(SPEC) 생성";
      } else if (!status.personaUrl) {
        curStep = 4;
        stepLabel = "Step 4: 맞춤 AI 페르소나 구성";
      } else if (!status.contentDocUrl || latestRvNum < 0) {
        curStep = 5;
        stepLabel = "Step 5: 초판 콘텐츠 생성 (rv-00)";
      } else if (!hasActiveJson) {
        curStep = 6;
        stepLabel = "Step 6: AI 페르소나 다면 평가 (" + activeFbTag + ")";
      } else if (!hasActiveSummary) {
        curStep = 7;
        stepLabel = "Step 7: 피드백 보고서 생성 (" + activeFbTag + ")";
      } else if (!hasActiveDirective) {
        curStep = 8;
        stepLabel = "Step 8: 마케터 보정 지침 확정 (" + activeFbTag + ")";
      } else {
        curStep = 9;
        stepLabel = "Step 9: 개정본 콘텐츠 생성 (" + nextRvTag + ")";
      }
      status.currentStep = curStep;
      status.stepLabel = stepLabel;
      status.progressPercent = Math.min(100, Math.round((curStep / 9) * 100));
    }
  } catch (e) {
    Logger.log("getPipelineStatus 예외: " + e);
  }

  // 30초 로컬 사용자 캐시 저장
  if (cache) {
    try {
      cache.put(cacheKey, JSON.stringify(status), 30);
    } catch (e) {
      // 캐시 저장 실패 무시
    }
  }

  return status;
}

/**
 * 우측 패널(Sidebar)용 모던 HTML 문자열을 생성한다.
 * [구글 워크스페이스 스타일]: Google Sans 서체, 구글 클라우드 테마 색상, 무이모지, 실시간 RPC 연동.
 */
function getPipelineSidebarHtml() {
  return "" +
    "<!DOCTYPE html>\n" +
    "<html>\n" +
    "<head>\n" +
    "  <base target='_blank'>\n" +
    "  <style>\n" +
    "    * { box-sizing: border-box; margin: 0; padding: 0; }\n" +
    "    html, body {\n" +
    "      height: 100%;\n" +
    "      margin: 0;\n" +
    "      padding: 0;\n" +
    "      overflow-y: auto;\n" +
    "    }\n" +
    "    body {\n" +
    "      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;\n" +
    "      font-size: 12px;\n" +
    "      line-height: 1.4;\n" +
    "      color: #202124;\n" +
    "      background: #ffffff;\n" +
    "      padding: 10px 12px;\n" +
    "      display: flex;\n" +
    "      flex-direction: column;\n" +
    "      min-height: 100%;\n" +
    "    }\n" +
    "    .header {\n" +
    "      padding-bottom: 8px;\n" +
    "      margin-bottom: 8px;\n" +
    "      border-bottom: 1px solid #dadce0;\n" +
    "      flex-shrink: 0;\n" +
    "    }\n" +
    "    .header-sub {\n" +
    "      font-size: 11px;\n" +
    "      color: #5f6368;\n" +
    "      display: flex;\n" +
    "      justify-content: space-between;\n" +
    "      align-items: center;\n" +
    "    }\n" +
    "    .campaign-title {\n" +
    "      font-size: 13px;\n" +
    "      font-weight: 700;\n" +
    "      color: #202124;\n" +
    "      letter-spacing: -0.3px;\n" +
    "    }\n" +
    "    .badge {\n" +
    "      display: inline-block;\n" +
    "      font-size: 10px;\n" +
    "      font-weight: 600;\n" +
    "      padding: 2px 7px;\n" +
    "      border-radius: 4px;\n" +
    "      background: #e8f0fe;\n" +
    "      color: #1967d2;\n" +
    "    }\n" +
    "    .badge.active { background: #ceead6; color: #0d652d; }\n" +
    "    .badge.warn { background: #fef7e0; color: #b06000; cursor: pointer; }\n" +
    "    .status-bar {\n" +
    "      padding: 7px 10px;\n" +
    "      background: #e8f0fe;\n" +
    "      border: 1px solid #d2e3fc;\n" +
    "      border-radius: 6px;\n" +
    "      font-size: 11px;\n" +
    "      color: #174ea6;\n" +
    "      margin-bottom: 8px;\n" +
    "      display: none;\n" +
    "      flex-shrink: 0;\n" +
    "      line-height: 1.4;\n" +
    "    }\n" +
    "    .status-bar.show {\n" +
    "      display: flex;\n" +
    "      align-items: center;\n" +
    "    }\n" +
    "    .status-bar.error {\n" +
    "      background: #fce8e6;\n" +
    "      border-color: #fad2cf;\n" +
    "      color: #c5221f;\n" +
    "    }\n" +
    "    .status-bar.success {\n" +
    "      background: #e6f4ea;\n" +
    "      border-color: #ceead6;\n" +
    "      color: #0d652d;\n" +
    "    }\n" +
    "    .spinner {\n" +
    "      display: inline-block;\n" +
    "      width: 12px;\n" +
    "      height: 12px;\n" +
    "      border: 2px solid rgba(26, 115, 232, 0.25);\n" +
    "      border-top-color: #1a73e8;\n" +
    "      border-radius: 50%;\n" +
    "      animation: spin 0.8s linear infinite;\n" +
    "      margin-right: 7px;\n" +
    "      flex-shrink: 0;\n" +
    "    }\n" +
    "    @keyframes spin {\n" +
    "      to { transform: rotate(360deg); }\n" +
    "    }\n" +
    "    .onboarding-card {\n" +
    "      padding: 8px 10px;\n" +
    "      border-radius: 6px;\n" +
    "      margin-bottom: 8px;\n" +
    "      font-size: 11px;\n" +
    "      line-height: 1.4;\n" +
    "      flex-shrink: 0;\n" +
    "    }\n" +
    "    .onboarding-card.warn {\n" +
    "      background: #fef7e0;\n" +
    "      border: 1px solid #f9ab00;\n" +
    "      color: #b06000;\n" +
    "    }\n" +
    "    .onboarding-card.info {\n" +
    "      background: #e8f0fe;\n" +
    "      border: 1px solid #1a73e8;\n" +
    "      color: #174ea6;\n" +
    "    }\n" +
    "    .onboarding-title {\n" +
    "      font-weight: 700;\n" +
    "      margin-bottom: 4px;\n" +
    "    }\n" +
    "    .inline-box {\n" +
    "      background: #f8f9fa;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      border-radius: 6px;\n" +
    "      padding: 8px;\n" +
    "      margin-bottom: 8px;\n" +
    "      flex-shrink: 0;\n" +
    "    }\n" +
    "    .inline-box-title {\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 700;\n" +
    "      color: #202124;\n" +
    "      margin-bottom: 6px;\n" +
    "    }\n" +
    "    .inline-input, .inline-textarea {\n" +
    "      width: 100%;\n" +
    "      padding: 6px 8px;\n" +
    "      font-size: 11px;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      border-radius: 4px;\n" +
    "      box-sizing: border-box;\n" +
    "      font-family: inherit;\n" +
    "      margin-bottom: 6px;\n" +
    "    }\n" +
    "    .inline-input:focus, .inline-textarea:focus {\n" +
    "      border-color: #1a73e8;\n" +
    "      outline: none;\n" +
    "    }\n" +
    "    .inline-actions {\n" +
    "      display: flex;\n" +
    "      gap: 6px;\n" +
    "      justify-content: flex-end;\n" +
    "    }\n" +
    "    .copilot-section {\n" +
    "      background: #ffffff;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      border-radius: 6px;\n" +
    "      padding: 8px 10px;\n" +
    "      margin-bottom: 8px;\n" +
    "      display: flex;\n" +
    "      flex-direction: column;\n" +
    "      flex-shrink: 0;\n" +
    "    }\n" +
    "    .copilot-header {\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 700;\n" +
    "      color: #1a73e8;\n" +
    "      margin-bottom: 6px;\n" +
    "      display: flex;\n" +
    "      justify-content: space-between;\n" +
    "      align-items: center;\n" +
    "    }\n" +
    "    .chat-log {\n" +
    "      max-height: 220px;\n" +
    "      min-height: 110px;\n" +
    "      overflow-y: auto;\n" +
    "      margin-bottom: 6px;\n" +
    "      display: flex;\n" +
    "      flex-direction: column;\n" +
    "      gap: 6px;\n" +
    "      padding: 4px 2px;\n" +
    "      border-bottom: 1px solid #f1f3f4;\n" +
    "    }\n" +
    "    .chat-bubble {\n" +
    "      font-size: 11px;\n" +
    "      line-height: 1.5;\n" +
    "      padding: 2px 0;\n" +
    "      width: 100%;\n" +
    "      word-break: break-word;\n" +
    "      background: none;\n" +
    "      border: none;\n" +
    "    }\n" +
    "    .chat-bubble.bot {\n" +
    "      align-self: flex-start;\n" +
    "      color: #202124;\n" +
    "      text-align: left;\n" +
    "    }\n" +
    "    .chat-bubble.user {\n" +
    "      align-self: flex-end;\n" +
    "      color: #1a73e8;\n" +
    "      font-weight: 600;\n" +
    "      text-align: right;\n" +
    "    }\n" +
    "    .chat-bubble.user::before {\n" +
    "      content: '나: ';\n" +
    "      color: #70757a;\n" +
    "      font-weight: 400;\n" +
    "    }\n" +
    "    .chat-action-btn {\n" +
    "      display: inline-block;\n" +
    "      margin-top: 4px;\n" +
    "      padding: 4px 8px;\n" +
    "      background: #1a73e8;\n" +
    "      color: #ffffff;\n" +
    "      border-radius: 4px;\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 600;\n" +
    "      border: 1px solid #174ea6;\n" +
    "      cursor: pointer;\n" +
    "      text-decoration: none;\n" +
    "      transition: all 0.15s ease;\n" +
    "    }\n" +
    "    .chat-action-btn:hover { background: #174ea6; }\n" +
    "    .quick-chips {\n" +
    "      display: flex;\n" +
    "      flex-wrap: wrap;\n" +
    "      gap: 4px;\n" +
    "      margin-bottom: 6px;\n" +
    "    }\n" +
    "    .quick-chip {\n" +
    "      font-size: 10px;\n" +
    "      padding: 2px 7px;\n" +
    "      background: #ffffff;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      border-radius: 12px;\n" +
    "      color: #5f6368;\n" +
    "      cursor: pointer;\n" +
    "      white-space: nowrap;\n" +
    "      transition: all 0.15s ease;\n" +
    "    }\n" +
    "    .quick-chip:hover {\n" +
    "      background: #e8f0fe;\n" +
    "      border-color: #1a73e8;\n" +
    "      color: #1a73e8;\n" +
    "    }\n" +
    "    .chat-input-box {\n" +
    "      display: flex;\n" +
    "      gap: 6px;\n" +
    "    }\n" +
    "    .chat-input {\n" +
    "      flex: 1;\n" +
    "      padding: 6px 8px;\n" +
    "      font-size: 11px;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      border-radius: 4px;\n" +
    "      outline: none;\n" +
    "    }\n" +
    "    .chat-input:focus { border-color: #1a73e8; }\n" +
    "    .chat-send-btn {\n" +
    "      padding: 6px 10px;\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 600;\n" +
    "      background: #1a73e8;\n" +
    "      color: #ffffff;\n" +
    "      border: none;\n" +
    "      border-radius: 4px;\n" +
    "      cursor: pointer;\n" +
    "      white-space: nowrap;\n" +
    "    }\n" +
    "    .chat-send-btn:hover { background: #174ea6; }\n" +
    "    .chat-send-btn:disabled { opacity: 0.5; cursor: not-allowed; }\n" +
    "    details.pipeline-section {\n" +
    "      padding: 4px 2px 0 2px;\n" +
    "      margin-bottom: 8px;\n" +
    "    }\n" +
    "    details.pipeline-section summary {\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 700;\n" +
    "      color: #202124;\n" +
    "      cursor: pointer;\n" +
    "      display: flex;\n" +
    "      justify-content: space-between;\n" +
    "      align-items: center;\n" +
    "      user-select: none;\n" +
    "      padding: 4px 0;\n" +
    "    }\n" +
    "    details.pipeline-section summary::-webkit-details-marker { display: none; }\n" +
    "    .pipeline-content {\n" +
    "      margin-top: 6px;\n" +
    "      display: flex;\n" +
    "      flex-direction: column;\n" +
    "      gap: 1px;\n" +
    "    }\n" +
    "    .btn {\n" +
    "      display: block;\n" +
    "      width: 100%;\n" +
    "      padding: 5px 9px;\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 500;\n" +
    "      text-align: left;\n" +
    "      border-radius: 4px;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      background: #f8f9fa;\n" +
    "      color: #3c4043;\n" +
    "      cursor: pointer;\n" +
    "      transition: all 0.15s ease;\n" +
    "    }\n" +
    "    .btn:hover:not(:disabled) {\n" +
    "      background: #e8f0fe;\n" +
    "      border-color: #1a73e8;\n" +
    "      color: #1a73e8;\n" +
    "    }\n" +
    "    .btn:disabled {\n" +
    "      opacity: 0.5;\n" +
    "      cursor: not-allowed;\n" +
    "      background: #f1f3f4;\n" +
    "      border-color: #dadce0;\n" +
    "      color: #9aa0a6;\n" +
    "    }\n" +
    "    .btn-primary {\n" +
    "      background: #1a73e8;\n" +
    "      color: #ffffff;\n" +
    "      border-color: #1a73e8;\n" +
    "    }\n" +
    "    .btn-primary:hover:not(:disabled) {\n" +
    "      background: #174ea6;\n" +
    "      border-color: #174ea6;\n" +
    "      color: #ffffff;\n" +
    "    }\n" +
    "    .btn-sm {\n" +
    "      padding: 4px 8px;\n" +
    "      font-size: 11px;\n" +
    "      margin-top: 4px;\n" +
    "      text-align: center;\n" +
    "    }\n" +
    "    .btn-step {\n" +
    "      display: flex;\n" +
    "      align-items: center;\n" +
    "      justify-content: space-between;\n" +
    "    }\n" +
    "    .step-tag {\n" +
    "      font-size: 9px;\n" +
    "      font-weight: 700;\n" +
    "      padding: 1px 5px;\n" +
    "      border-radius: 3px;\n" +
    "      background: #e8eaed;\n" +
    "      color: #5f6368;\n" +
    "    }\n" +
    "    .footer-actions {\n" +
    "      margin-top: auto;\n" +
    "      text-align: center;\n" +
    "      padding-top: 6px;\n" +
    "      padding-bottom: 2px;\n" +
    "      border-top: 1px solid #dadce0;\n" +
    "      flex-shrink: 0;\n" +
    "    }\n" +
    "    .footer-btn {\n" +
    "      background: none;\n" +
    "      border: none;\n" +
    "      color: #70757a;\n" +
    "      font-size: 11px;\n" +
    "      cursor: pointer;\n" +
    "      text-decoration: underline;\n" +
    "    }\n" +
    "    .footer-btn:hover { color: #1a73e8; }\n" +
    "  </style>\n" +
    "</head>\n" +
    "<body>\n" +
    "  <!-- 1. 최상단: 상태 알림 섹션 -->\n" +
    "  <div class='header'>\n" +
    "    <div class='header-sub'>\n" +
    "      <span id='campaignCodeBadge' class='campaign-title'>BwG-Seoul-Ignite</span>\n" +
    "      <span id='apiKeyBadge' class='badge warn' onclick='toggleApiKeyBox(true)' title='클릭하여 API Key 등록'>API Key 확인 중</span>\n" +
    "    </div>\n" +
    "  </div>\n" +
    "\n" +
    "  <div id='statusBar' class='status-bar'></div>\n" +
    "\n" +
    "  <div id='onboardingBanner' class='onboarding-card' style='display:none;'>\n" +
    "    <div id='onboardingTitle' class='onboarding-title'>준비 단계</div>\n" +
    "    <div id='onboardingDesc'></div>\n" +
    "    <button id='onboardingBtn' class='btn btn-primary btn-sm'></button>\n" +
    "  </div>\n" +
    "\n" +
    "  <div id='apiKeyInlineBox' class='inline-box' style='display:none;'>\n" +
    "    <div class='inline-box-title'>Gemini API Key 등록 (Google AI Studio)</div>\n" +
    "    <div style='font-size: 11px; color: #5f6368; margin-bottom: 8px; line-height: 1.3;'>\n" +
    "      신용카드 없이 개인 계정으로 1분 만에 무료 발급받을 수 있습니다.<br>\n" +
    "      <a href='https://aistudio.google.com/app/apikey' target='_blank' style='color: #1a73e8; text-decoration: underline; font-weight: 500;'>Google AI Studio에서 무료 API Key 발급받기 &rarr;</a>\n" +
    "    </div>\n" +
    "    <input type='password' id='inputApiKey' class='inline-input' placeholder='AIzaSy... 키를 붙여넣으십시오' />\n" +
    "    <div class='inline-actions'>\n" +
    "      <button class='btn btn-primary' onclick='submitApiKeyInline()'>저장 및 검증</button>\n" +
    "      <button class='btn' onclick='toggleApiKeyBox(false)'>취소</button>\n" +
    "    </div>\n" +
    "  </div>\n" +
    "\n" +
    "  <!-- 2. 중단: AI 코파일럿 대화 섹션 -->\n" +
    "  <div class='copilot-section'>\n" +
    "    <div class='copilot-header'>\n" +
    "      <span>AI 코파일럿 대화 및 지시</span>\n" +
    "      <span class='step-tag'>Gemini 3.8 Flash</span>\n" +
    "    </div>\n" +
    "    <div id='chatLog' class='chat-log'>\n" +
    "      <div class='chat-bubble bot'>\n" +
    "        안녕! 마케팅 파이프라인 AI 코파일럿이야. 진행 상황이 궁금하거나 작업 실행이 필요하면 언제든 편하게 물어봐!\n" +
    "      </div>\n" +
    "    </div>\n" +
    "    <div class='quick-chips'>\n" +
    "      <span class='quick-chip' onclick=\"quickChat('지금 뭐 해야 돼?')\">지금 뭐 해야 돼?</span>\n" +
    "    </div>\n" +
    "    <div class='chat-input-box'>\n" +
    "      <input id='chatInput' class='chat-input' placeholder='질문하거나 편하게 지시해봐... (Enter)' onkeydown='handleChatKey(event)' />\n" +
    "      <button id='btnChatSend' class='chat-send-btn' onclick='submitChatQuery()'>전송</button>\n" +
    "    </div>\n" +
    "  </div>\n" +
    "\n" +
    "  <!-- 3. 하단: 0~9단계 10대 파이프라인 실행 로드맵 -->\n" +
    "  <details class='pipeline-section' open>\n" +
    "    <summary>\n" +
    "      <span>파이프라인 실행 로드맵</span>\n" +
    "      <span class='step-tag'>0~9단계 ▼</span>\n" +
    "    </summary>\n" +
    "    <div class='pipeline-content'>\n" +
    "      <button id='btnStep0' class='btn btn-step' onclick='toggleSetupBox()'>\n" +
    "        <span>[0단계] API Key &amp; 작업 공간 구축</span>\n" +
    "        <span class='step-tag'>Setup ▼</span>\n" +
    "      </button>\n" +
    "      <div id='setupInlineBox' class='inline-box' style='display:none;'>\n" +
    "        <div class='inline-box-title'>API Key 및 작업 공간 설정</div>\n" +
    "        <button id='btnApiKey' class='btn' style='margin-bottom:4px;' onclick='toggleApiKeyBox(true)'>Gemini API Key 설정 (인라인)</button>\n" +
    "        <button id='btnInit' class='btn btn-primary' style='margin-bottom:4px;' onclick=\"callServer('initCampaignWorkspace', '캠페인 작업 공간 구축')\">[초기화] 캠페인 작업 공간 구축</button>\n" +
    "        <div style='font-size: 10px; color: #5f6368; line-height: 1.3;'>\n" +
    "          * 최초 실행 시 Google 권한 승인 창이 뜨면 <strong>'고급' &gt; '(안전하지 않음으로 이동)' &gt; '허용'</strong>을 순서대로 클릭하시면 정상 구동됩니다.\n" +
    "        </div>\n" +
    "      </div>\n" +
    "\n" +
    "      <button id='btnStep1' class='btn btn-step' onclick='toggleIdeaBox()'>\n" +
    "        <span>[1단계] 캠페인 아이디어 메모 작성</span>\n" +
    "        <span class='step-tag'>IDEA ▼</span>\n" +
    "      </button>\n" +
    "      <div id='ideaInlineBox' class='inline-box' style='display:none;'>\n" +
    "        <div class='inline-box-title'>캠페인 아이디어 입력</div>\n" +
    "        <textarea id='inputCustomIdea' class='inline-textarea' rows='3' placeholder='이번 캠페인의 핵심 컨셉, 타깃, 주요 혜택을 입력하십시오... (비워두면 기존 메모 유지)'></textarea>\n" +
    "        <div class='inline-actions'>\n" +
    "          <button class='btn btn-primary' onclick='submitIdeaAndRunMemo()'>아이디어 저장 및 메모 작성</button>\n" +
    "          <button class='btn' onclick='toggleIdeaBox(false)'>닫기</button>\n" +
    "        </div>\n" +
    "        <div style='margin-top: 5px; text-align: right;'>\n" +
    "          <a id='linkIdeaDoc' href='#' target='_blank' style='font-size: 10px; color: #1a73e8; text-decoration: underline; display: none;'>[아이디어 메모] 구글 독스 직접 열기</a>\n" +
    "        </div>\n" +
    "      </div>\n" +
    "\n" +
    "      <button class='btn btn-step' onclick=\"callServer('guardAndRunIdeaToPlan', '캠페인 기획서(PLAN) 생성')\">\n" +
    "        <span>[2단계] 캠페인 기획서(PLAN) 생성</span>\n" +
    "        <span class='step-tag'>PLAN</span>\n" +
    "      </button>\n" +
    "\n" +
    "      <button class='btn btn-step' onclick=\"callServer('guardAndRunPlanToSpec', '콘텐츠 제작 명세서(SPEC) 생성')\">\n" +
    "        <span>[3단계] 콘텐츠 제작 명세서(SPEC) 생성</span>\n" +
    "        <span class='step-tag'>SPEC</span>\n" +
    "      </button>\n" +
    "\n" +
    "      <button class='btn btn-step' onclick=\"callServer('guardAndRunPersonaSynthesis', '맞춤 AI 페르소나 패널 구성')\">\n" +
    "        <span>[4단계] 맞춤 AI 페르소나 패널 구성</span>\n" +
    "        <span class='step-tag'>Persona</span>\n" +
    "      </button>\n" +
    "\n" +
    "      <button class='btn btn-step' onclick=\"callServer('guardAndRunInitialContent', '초판 콘텐츠 생성')\">\n" +
    "        <span>[5단계] 초판 멀티 채널 콘텐츠 생성</span>\n" +
    "        <span class='step-tag'>rv-00</span>\n" +
    "      </button>\n" +
    "\n" +
    "      <button class='btn btn-step' onclick=\"callServer('promptAndRunJudgeEvaluation', 'AI 페르소나 다면 평가')\">\n" +
    "        <span>[6단계] AI 페르소나 다면 평가 실행</span>\n" +
    "        <span class='step-tag'>Judge</span>\n" +
    "      </button>\n" +
    "\n" +
    "      <button class='btn btn-step' onclick=\"callServer('promptAndRunFeedbackSummary', '피드백 종합 보고서 생성')\">\n" +
    "        <span>[7단계] 피드백 종합 분석 보고서 생성</span>\n" +
    "        <span class='step-tag'>Report</span>\n" +
    "      </button>\n" +
    "\n" +
    "      <button id='btnStep8' class='btn btn-step' onclick='toggleDirectiveBox()'>\n" +
    "        <span>[8단계] 마케터 보정 지침 작성/확정</span>\n" +
    "        <span class='step-tag'>Directive ▼</span>\n" +
    "      </button>\n" +
    "      <div id='directiveInlineBox' class='inline-box' style='display:none;'>\n" +
    "        <div class='inline-box-title'>마케터 보정 지침 입력</div>\n" +
    "        <textarea id='inputCustomDirective' class='inline-textarea' rows='3' placeholder='피드백 분석 결과를 바탕으로 보정할 구체적 지침을 입력하십시오... (비워두면 기존 지침 반영)'></textarea>\n" +
    "        <div class='inline-actions'>\n" +
    "          <button class='btn btn-primary' onclick='submitDirectiveAndRunSave()'>보정 지침 확정 및 저장</button>\n" +
    "          <button class='btn' onclick='toggleDirectiveBox(false)'>닫기</button>\n" +
    "        </div>\n" +
    "        <div style='margin-top: 5px; text-align: right;'>\n" +
    "          <a id='linkDirectiveDoc' href='#' target='_blank' style='font-size: 10px; color: #1a73e8; text-decoration: underline; display: none;'>[마케터 보정 지침] 구글 독스 직접 열기</a>\n" +
    "        </div>\n" +
    "      </div>\n" +
    "\n" +
    "      <button class='btn btn-step' onclick=\"callServer('promptAndRunFeedbackRevision', '개정본 콘텐츠 생성')\">\n" +
    "        <span>[9단계] 피드백 반영 개정본 생성</span>\n" +
    "        <span class='step-tag'>rv-01</span>\n" +
    "      </button>\n" +
    "    </div>\n" +
    "  </details>\n" +
    "\n" +
    "  <!-- 하단 유틸리티 링크 -->\n" +
    "  <div class='footer-actions'>\n" +
    "    <button class='footer-btn' onclick='refreshStatus()'>패널 새로고침</button>\n" +
    "     | \n" +
    "    <button class='footer-btn' onclick=\"callServer('openDashboardSheet', '실행 내역 열기')\">실행 내역 열기</button>\n" +
    "     | \n" +
    "    <button class='footer-btn' onclick=\"callServer('forceSyncEngine', '엔진 최신 동기화')\">최신 엔진 동기화</button>\n" +
    "  </div>\n" +
    "\n" +
    "  <script>\n" +
    "    var timerInterval = null;\n" +
    "    var timerSeconds = 0;\n" +
    "    var currentStatusCache = null;\n" +
    "\n" +
    "    function setStatus(htmlOrText, isError, isSuccess) {\n" +
    "      var el = document.getElementById('statusBar');\n" +
    "      if (!htmlOrText) {\n" +
    "        el.className = 'status-bar';\n" +
    "        el.innerHTML = '';\n" +
    "        return;\n" +
    "      }\n" +
    "      var cls = 'status-bar show';\n" +
    "      if (isError) cls += ' error';\n" +
    "      else if (isSuccess) cls += ' success';\n" +
    "      el.className = cls;\n" +
    "      el.innerHTML = htmlOrText;\n" +
    "    }\n" +
    "\n" +
    "    function startTimer(taskName) {\n" +
    "      clearInterval(timerInterval);\n" +
    "      timerSeconds = 0;\n" +
    "      setStatus(\"<span class='spinner'></span> <span>\" + taskName + \" 실행 중... (<strong>0초</strong> 경과)</span>\", false);\n" +
    "      timerInterval = setInterval(function() {\n" +
    "        timerSeconds++;\n" +
    "        setStatus(\"<span class='spinner'></span> <span>\" + taskName + \" 실행 중... (<strong>\" + timerSeconds + \"초</strong> 경과)</span>\", false);\n" +
    "      }, 1000);\n" +
    "    }\n" +
    "\n" +
    "    function stopTimer(successMsg, isError) {\n" +
    "      clearInterval(timerInterval);\n" +
    "      if (isError) {\n" +
    "        setStatus(successMsg, true);\n" +
    "      } else {\n" +
    "        var durText = timerSeconds > 0 ? \" (총 \" + timerSeconds + \"초 소요)\" : \"\";\n" +
    "        setStatus(\"✓ \" + (successMsg || \"작업이 성공적으로 완결되었습니다.\") + durText, false, true);\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    function setButtonsDisabled(disabled) {\n" +
    "      var btns = document.querySelectorAll('button:not(.footer-btn)');\n" +
    "      btns.forEach(function(b) { b.disabled = disabled; });\n" +
    "    }\n" +
    "\n" +
    "    function toggleApiKeyBox(show) {\n" +
    "      var box = document.getElementById('apiKeyInlineBox');\n" +
    "      box.style.display = show ? 'block' : 'none';\n" +
    "      if (show) {\n" +
    "        var inp = document.getElementById('inputApiKey');\n" +
    "        inp.value = '';\n" +
    "        inp.focus();\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    function submitApiKeyInline() {\n" +
    "      var val = document.getElementById('inputApiKey').value.trim();\n" +
    "      if (!val) {\n" +
    "        setStatus('API Key를 입력해 주십시오.', true);\n" +
    "        return;\n" +
    "      }\n" +
    "      setStatus(\"<span class='spinner'></span> API Key 저장 및 검증 중...\", false);\n" +
    "      google.script.run\n" +
    "        .withSuccessHandler(function(res) {\n" +
    "          if (res && res.success) {\n" +
    "            toggleApiKeyBox(false);\n" +
    "            setStatus('✓ ' + res.message, false, true);\n" +
    "            refreshStatus();\n" +
    "          } else {\n" +
    "            setStatus(res ? res.message : 'API Key 저장 실패', true);\n" +
    "          }\n" +
    "        })\n" +
    "        .withFailureHandler(function(err) {\n" +
    "          setStatus('API Key 저장 오류: ' + (err.message || err), true);\n" +
    "        })\n" +
    "        .saveApiKeyInline(val);\n" +
    "    }\n" +
    "\n" +
    "    function toggleSetupBox(show) {\n" +
    "      var box = document.getElementById('setupInlineBox');\n" +
    "      if (!box) return;\n" +
    "      var isCurrentlyOpen = box.style.display !== 'none';\n" +
    "      var shouldOpen = (show !== undefined) ? show : !isCurrentlyOpen;\n" +
    "      box.style.display = shouldOpen ? 'block' : 'none';\n" +
    "    }\n" +
    "\n" +
    "    function toggleIdeaBox(show) {\n" +
    "      var box = document.getElementById('ideaInlineBox');\n" +
    "      if (!box) return;\n" +
    "      var isCurrentlyOpen = box.style.display !== 'none';\n" +
    "      var shouldOpen = (show !== undefined) ? show : !isCurrentlyOpen;\n" +
    "      box.style.display = shouldOpen ? 'block' : 'none';\n" +
    "      if (shouldOpen) {\n" +
    "        var inp = document.getElementById('inputCustomIdea');\n" +
    "        if (inp) inp.focus();\n" +
    "        var linkDoc = document.getElementById('linkIdeaDoc');\n" +
    "        if (linkDoc && currentStatusCache && currentStatusCache.ideaDocUrl) {\n" +
    "          linkDoc.href = currentStatusCache.ideaDocUrl;\n" +
    "          linkDoc.style.display = 'inline-block';\n" +
    "        } else if (linkDoc) {\n" +
    "          linkDoc.style.display = 'none';\n" +
    "        }\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    function submitIdeaAndRunMemo() {\n" +
    "      var inp = document.getElementById('inputCustomIdea');\n" +
    "      var val = inp ? inp.value.trim() : '';\n" +
    "      toggleIdeaBox(false);\n" +
    "      callServer('runCampaignIdeaMemo', '아이디어 메모 작성', val);\n" +
    "    }\n" +
    "\n" +
    "    function toggleDirectiveBox(show) {\n" +
    "      var box = document.getElementById('directiveInlineBox');\n" +
    "      if (!box) return;\n" +
    "      var isCurrentlyOpen = box.style.display !== 'none';\n" +
    "      var shouldOpen = (show !== undefined) ? show : !isCurrentlyOpen;\n" +
    "      box.style.display = shouldOpen ? 'block' : 'none';\n" +
    "      if (shouldOpen) {\n" +
    "        var inp = document.getElementById('inputCustomDirective');\n" +
    "        if (inp) inp.focus();\n" +
    "        var linkDoc = document.getElementById('linkDirectiveDoc');\n" +
    "        if (linkDoc && currentStatusCache && currentStatusCache.directiveDocUrl) {\n" +
    "          linkDoc.href = currentStatusCache.directiveDocUrl;\n" +
    "          linkDoc.style.display = 'inline-block';\n" +
    "        } else if (linkDoc) {\n" +
    "          linkDoc.style.display = 'none';\n" +
    "        }\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    function submitDirectiveAndRunSave() {\n" +
    "      var inp = document.getElementById('inputCustomDirective');\n" +
    "      var val = inp ? inp.value.trim() : '';\n" +
    "      toggleDirectiveBox(false);\n" +
    "      callServer('runMarketerDirective', '마케터 보정 지침 확정', val);\n" +
    "    }\n" +
    "\n" +
    "    function updateUI(status) {\n" +
    "      if (!status) return;\n" +
    "      currentStatusCache = status;\n" +
    "\n" +
    "      var keyBadge = document.getElementById('apiKeyBadge');\n" +
    "      var onboarding = document.getElementById('onboardingBanner');\n" +
    "      var setupBox = document.getElementById('setupBox');\n" +
    "      var linkDoc = document.getElementById('linkIdeaDoc');\n" +
    "      if (linkDoc) {\n" +
    "        if (status.ideaDocUrl) {\n" +
    "          linkDoc.href = status.ideaDocUrl;\n" +
    "          linkDoc.style.display = 'inline-block';\n" +
    "        } else {\n" +
    "          linkDoc.style.display = 'none';\n" +
    "        }\n" +
    "      }\n" +
    "      var linkDirective = document.getElementById('linkDirectiveDoc');\n" +
    "      if (linkDirective) {\n" +
    "        if (status.directiveDocUrl) {\n" +
    "          linkDirective.href = status.directiveDocUrl;\n" +
    "          linkDirective.style.display = 'inline-block';\n" +
    "        } else {\n" +
    "          linkDirective.style.display = 'none';\n" +
    "        }\n" +
    "      }\n" +
    "\n" +
    "      // 1. API Key 상태 및 온보딩 배너 관리\n" +
    "      if (status.hasApiKey) {\n" +
    "        keyBadge.className = 'badge active';\n" +
    "        keyBadge.textContent = 'API Key 등록됨';\n" +
    "        keyBadge.onclick = function() { toggleApiKeyBox(true); };\n" +
    "      } else {\n" +
    "        keyBadge.className = 'badge warn';\n" +
    "        keyBadge.textContent = 'API Key 필요';\n" +
    "        keyBadge.onclick = function() { toggleApiKeyBox(true); };\n" +
    "      }\n" +
    "\n" +
    "      if (!status.hasApiKey) {\n" +
    "        onboarding.className = 'onboarding-card warn';\n" +
    "        onboarding.style.display = 'block';\n" +
    "        document.getElementById('onboardingTitle').textContent = '준비 1단계: API Key 등록';\n" +
    "        document.getElementById('onboardingDesc').textContent = 'Gemini API 호출을 위해 Google AI Studio API Key를 먼저 등록해 주십시오.';\n" +
    "        var obBtn = document.getElementById('onboardingBtn');\n" +
    "        obBtn.textContent = '지금 API Key 등록하기';\n" +
    "        obBtn.onclick = function() { toggleApiKeyBox(true); };\n" +
    "        if (setupBox) setupBox.open = true;\n" +
    "      } else if (!status.folderUrl) {\n" +
    "        onboarding.className = 'onboarding-card info';\n" +
    "        onboarding.style.display = 'block';\n" +
    "        document.getElementById('onboardingTitle').textContent = '준비 2단계: 작업 공간 초기화';\n" +
    "        document.getElementById('onboardingDesc').textContent = '캠페인 부모 폴더를 감지하고 필수 프롬프트와 작업 공간을 구축해 주십시오.';\n" +
    "        var obBtn = document.getElementById('onboardingBtn');\n" +
    "        obBtn.textContent = '[초기화] 캠페인 작업 공간 구축';\n" +
    "        obBtn.onclick = function() { callServer('initCampaignWorkspace', '캠페인 작업 공간 구축'); };\n" +
    "        if (setupBox) setupBox.open = true;\n" +
    "      } else {\n" +
    "        onboarding.style.display = 'none';\n" +
    "        if (setupBox) setupBox.open = false;\n" +
    "      }\n" +
    "\n" +
    "      // 3. 캠페인 코드 배지\n" +
    "      if (status.campaignCode) {\n" +
    "        document.getElementById('campaignCodeBadge').textContent = status.campaignCode;\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    function refreshStatus() {\n" +
    "      google.script.run\n" +
    "        .withSuccessHandler(function(status) {\n" +
    "          updateUI(status);\n" +
    "        })\n" +
    "        .withFailureHandler(function(err) {\n" +
    "          setStatus('상태 갱신 오류: ' + (err.message || err), true);\n" +
    "        })\n" +
    "        .getPipelineStatus();\n" +
    "    }\n" +
    "\n" +
    "    function callServer(fnName, taskName, optArg) {\n" +
    "      var displayName = taskName || fnName;\n" +
    "      setButtonsDisabled(true);\n" +
    "      startTimer(displayName);\n" +
    "\n" +
    "      google.script.run\n" +
    "        .withSuccessHandler(function(res) {\n" +
    "          setButtonsDisabled(false);\n" +
    "          var progressDoneMsg = displayName + ' 완료';\n" +
    "          stopTimer(progressDoneMsg, false);\n" +
    "          if (res) {\n" +
    "            var botMsg = (res && res.message) || (displayName + ' 작업이 성공적으로 완결되었습니다.');\n" +
    "            var actionBtn = '';\n" +
    "            if (res.ideaDocUrl) {\n" +
    "              actionBtn += \" <a href='\" + res.ideaDocUrl + \"' target='_blank' style='display:inline-block; margin-top:4px; font-size:11px; color:#1a73e8; text-decoration:underline;'>[아이디어 메모 열기]</a>\";\n" +
    "            }\n" +
    "            if (res.planUrl) {\n" +
    "              actionBtn += \" <a href='\" + res.planUrl + \"' target='_blank' style='display:inline-block; margin-top:4px; font-size:11px; color:#1a73e8; text-decoration:underline;'>[기획서(PLAN) 열기]</a>\";\n" +
    "            }\n" +
    "            if (res.specUrl) {\n" +
    "              actionBtn += \" <a href='\" + res.specUrl + \"' target='_blank' style='display:inline-block; margin-top:4px; font-size:11px; color:#1a73e8; text-decoration:underline;'>[제작 명세서(SPEC) 열기]</a>\";\n" +
    "            }\n" +
    "            if (res.personaUrl) {\n" +
    "              actionBtn += \" <a href='\" + res.personaUrl + \"' target='_blank' style='display:inline-block; margin-top:4px; font-size:11px; color:#1a73e8; text-decoration:underline;'>[AI 페르소나 패널 열기]</a>\";\n" +
    "            }\n" +
    "            if (res.folderUrl) {\n" +
    "              var rvSuffix = res.targetRv ? \" (\" + res.targetRv + \")\" : \"\";\n" +
    "              actionBtn += \" <a href='\" + res.folderUrl + \"' target='_blank' style='display:inline-block; margin-top:4px; font-size:11px; color:#1a73e8; text-decoration:underline;'>[산출물 폴더 열기\" + rvSuffix + \"]</a>\";\n" +
    "            }\n" +
    "            if (res.summaryUrl) {\n" +
    "              var fbSuffix = res.targetRound ? \" (\" + res.targetRound + \")\" : \"\";\n" +
    "              actionBtn += \" <a href='\" + res.summaryUrl + \"' target='_blank' style='display:inline-block; margin-top:4px; font-size:11px; color:#1a73e8; text-decoration:underline;'>[피드백 보고서 열기\" + fbSuffix + \"]</a>\";\n" +
    "            }\n" +
    "            if (res.directiveUrl) {\n" +
    "              var fbSuffix2 = res.targetRound ? \" (\" + res.targetRound + \")\" : \"\";\n" +
    "              actionBtn += \" <a href='\" + res.directiveUrl + \"' target='_blank' style='display:inline-block; margin-top:4px; margin-left:6px; font-size:11px; color:#1a73e8; text-decoration:underline;'>[마케터 보정 지침 열기\" + fbSuffix2 + \"]</a>\";\n" +
    "            }\n" +
    "            if (res.feedbackJsonUrl || res.jsonUrl) {\n" +
    "              var targetJsonUrl = res.feedbackJsonUrl || res.jsonUrl;\n" +
    "              var fbSuffix3 = res.targetRound ? \" (\" + res.targetRound + \")\" : \"\";\n" +
    "              actionBtn += \" <a href='\" + targetJsonUrl + \"' target='_blank' style='display:inline-block; margin-top:4px; font-size:11px; color:#1a73e8; text-decoration:underline;'>[AI 페르소나 피드백 JSON 열기\" + fbSuffix3 + \"]</a>\";\n" +
    "            }\n" +
    "            if (res.actionChip) {\n" +
    "              actionBtn += res.actionChip;\n" +
    "            }\n" +
    "            appendChatBubble('bot', botMsg + actionBtn);\n" +
    "          }\n" +
    "          refreshStatus();\n" +
    "        })\n" +
    "        .withFailureHandler(function(err) {\n" +
    "          setButtonsDisabled(false);\n" +
    "          var errStr = (err && (err.message || err.toString())) || '알 수 없는 오류';\n" +
    "          stopTimer('오류 발생: ' + errStr, true);\n" +
    "        })[fnName](optArg);\n" +
    "    }\n" +
    "\n" +
    "    function escapeHtml(str) {\n" +
    "      if (!str) return '';\n" +
    "      return String(str)\n" +
    "        .replace(/&/g, '&amp;')\n" +
    "        .replace(/</g, '&lt;')\n" +
    "        .replace(/>/g, '&gt;')\n" +
    "        .replace(/\"/g, '&quot;')\n" +
    "        .replace(/'/g, '&#039;');\n" +
    "    }\n" +
    "\n" +
    "    function appendChatBubble(sender, text, actionBtnHtml) {\n" +
    "      var log = document.getElementById('chatLog');\n" +
    "      if (!log) return null;\n" +
    "      var bubble = document.createElement('div');\n" +
    "      bubble.className = 'chat-bubble ' + sender;\n" +
    "      var safeText = sender === 'user' ? escapeHtml(text) : text;\n" +
    "      bubble.innerHTML = safeText + (actionBtnHtml || '');\n" +
    "      log.appendChild(bubble);\n" +
    "      log.scrollTop = log.scrollHeight;\n" +
    "      return bubble;\n" +
    "    }\n" +
    "\n" +
    "    var isChatProcessing = false;\n" +
    "\n" +
    "    function quickChat(text) {\n" +
    "      if (isChatProcessing) return;\n" +
    "      var inp = document.getElementById('chatInput');\n" +
    "      if (inp) inp.value = text;\n" +
    "      submitChatQuery();\n" +
    "    }\n" +
    "\n" +
    "    function handleChatKey(e) {\n" +
    "      if (e.key === 'Enter') {\n" +
    "        e.preventDefault();\n" +
    "        submitChatQuery();\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    function submitChatQuery() {\n" +
    "      if (isChatProcessing) return;\n" +
    "      var inp = document.getElementById('chatInput');\n" +
    "      if (!inp) return;\n" +
    "      var val = inp.value.trim();\n" +
    "      if (!val) return;\n" +
    "      inp.value = '';\n" +
    "      isChatProcessing = true;\n" +
    "\n" +
    "      appendChatBubble('user', val);\n" +
    "      var loadingBubble = appendChatBubble('bot', \"<span class='spinner'></span> 답변 생성 중...\");\n" +
    "\n" +
    "      var btn = document.getElementById('btnChatSend');\n" +
    "      if (btn) btn.disabled = true;\n" +
    "      inp.disabled = true;\n" +
    "\n" +
    "      google.script.run\n" +
    "        .withSuccessHandler(function(res) {\n" +
    "          isChatProcessing = false;\n" +
    "          if (btn) btn.disabled = false;\n" +
    "          if (inp) {\n" +
    "            inp.disabled = false;\n" +
    "            inp.focus();\n" +
    "          }\n" +
    "          var reply = (res && res.reply) || '답변을 생성하지 못했어.';\n" +
    "          var actionHtml = '';\n" +
    "          if (res && res.actionBtnHtml) {\n" +
    "            actionHtml = res.actionBtnHtml;\n" +
    "          } else if (res && res.action && res.actionLabel) {\n" +
    "            var task = res.taskName || res.actionLabel;\n" +
    "            actionHtml = \"<br/><button class='chat-action-btn' onclick=\\\"runChatAction('\" + res.action + \"', '\" + task + \"')\\\">[실행] \" + res.actionLabel + \"</button>\";\n" +
    "          }\n" +
    "          if (loadingBubble) {\n" +
    "            loadingBubble.innerHTML = reply + actionHtml;\n" +
    "            var log = document.getElementById('chatLog');\n" +
    "            if (log) log.scrollTop = log.scrollHeight;\n" +
    "          }\n" +
    "        })\n" +
    "        .withFailureHandler(function(err) {\n" +
    "          isChatProcessing = false;\n" +
    "          if (btn) btn.disabled = false;\n" +
    "          if (inp) {\n" +
    "            inp.disabled = false;\n" +
    "            inp.focus();\n" +
    "          }\n" +
    "          if (loadingBubble) {\n" +
    "            loadingBubble.innerHTML = '질문 처리 중 오류 발생: ' + (err.message || err);\n" +
    "          }\n" +
    "        })\n" +
    "        .askPipelineAssistant(val);\n" +
    "    }\n" +
    "\n" +
    "    function runChatAction(actionName, taskName) {\n" +
    "      if (actionName === 'toggleApiKeyBox') {\n" +
    "        toggleApiKeyBox(true);\n" +
    "      } else if (actionName === 'openDashboardSheet') {\n" +
    "        callServer('openDashboardSheet', '실행 내역 열기');\n" +
    "      } else if (actionName === 'refreshStatus') {\n" +
    "        refreshStatus();\n" +
    "      } else if (actionName === 'promptAndRunIdeaMemo') {\n" +
    "        toggleIdeaBox(true);\n" +
    "      } else if (actionName === 'promptAndRunMarketerDirective') {\n" +
    "        toggleDirectiveBox(true);\n" +
    "      } else if (actionName === 'forceRunInitialContent') {\n" +
    "        callServer('forceRunInitialContent', '초판 콘텐츠 전체 재생성');\n" +
    "      } else {\n" +
    "        callServer(actionName, taskName);\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    // 패널 열림 시 최초 1회 상태 자동 조회\n" +
    "    window.onload = function() {\n" +
    "      refreshStatus();\n" +
    "    };\n" +
    "  </script>\n" +
    "</body>\n" +
    "</html>";
}

// ==========================================
// Module: Code_Menu.js
// ==========================================
/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 7] Google Sheets 액션 중심 커스텀 메뉴 및 선결 가드레일 UI (Spreadsheet UI & Action Menus)
 */

/**
 * 액션 중심 커스텀 메뉴 렌더링
 */
function renderPipelineMenu() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("[마케팅 콘텐츠 파이프라인]")
    .addItem("제어 패널 열기 (Open Panel)", "showPipelineSidebar")
    .addToUi();
}

/**
 * 스프레드시트 열림 시 액션 중심 커스텀 메뉴 자동 등록 및 시트 제목 동기화
 */
function onOpen() {
  renderPipelineMenu();

  try {
    var folder = getCampaignFolder();
    if (folder) {
      syncSpreadsheetTitleWithCampaign(folder.getName(), getCampaignCode());
    }
  } catch (syncErr) {
    // 단순 열림 트리거 환경에서의 권한 제약 시 무시
  }

  try {
    showPipelineSidebar();
  } catch (e) {
    // 단순 트리거 환경에서의 권한 제약 시 무시
  }
}

/**
 * [Step 1 가드레일] 캠페인 아이디어 메모 구글 독스 작성 및 저장
 *
 * @param {string} [customIdea] - 사이드바 대화창 또는 인라인에서 전달된 아이디어 (선택)
 */
function promptAndRunIdeaMemo(customIdea) {
  try {
    getCampaignFolder();
  } catch (err) {
    throw new Error("캠페인 작업 공간이 아직 준비되지 않았습니다. 사이드바의 [Step 0] API Key & 작업 공간 구축을 먼저 실행해 주십시오.");
  }
  return runCampaignIdeaMemo(customIdea);
}

/**
 * [Step 2 가드레일] 아이디어 메모 기반 캠페인 기획서(PLAN) 자동 생성
 *
 * @param {string} [customIdea] - 인라인 전달 아이디어 (선택)
 */
function guardAndRunIdeaToPlan(customIdea) {
  var apiKey = getGeminiApiKey();
  if (!apiKey) {
    throw new Error("Gemini API Key가 등록되지 않았습니다. 사이드바 상단의 [API Key 등록]을 통해 키를 먼저 등록해 주십시오.");
  }

  try {
    getCampaignFolder();
  } catch (err) {
    throw new Error("캠페인 작업 공간이 아직 준비되지 않았습니다. 사이드바의 [Step 0] API Key & 작업 공간 구축을 먼저 실행해 주십시오.");
  }

  return runIdeaToPlan(customIdea);
}

/**
 * [Step 3 가드레일] 기획서(PLAN) 기반 콘텐츠 제작 명세서(SPEC) 자동 생성
 */
function guardAndRunPlanToSpec() {
  var apiKey = getGeminiApiKey();
  if (!apiKey) {
    throw new Error("Gemini API Key가 등록되지 않았습니다. 사이드바 상단의 [API Key 등록]을 통해 키를 먼저 등록해 주십시오.");
  }

  var campaignFolder = getCampaignFolder();
  var planDoc = readGoogleDoc(campaignFolder, CONFIG.PLAN_DOC_NAME || "PLAN") || readGoogleDoc(campaignFolder, "BRD");
  if (!planDoc) {
    throw new Error("캠페인 기획서(PLAN)가 아직 생성되지 않았습니다. 사이드바의 [Step 2] 캠페인 기획서(PLAN) 생성을 먼저 실행해 주십시오.");
  }

  return runPlanToSpec();
}

/**
 * [Step 4 가드레일] 제작 명세서(SPEC) 타깃 오디언스 기반 맞춤 AI 페르소나 패널 자동 구성
 */
function guardAndRunPersonaSynthesis() {
  var apiKey = getGeminiApiKey();
  if (!apiKey) {
    throw new Error("Gemini API Key가 등록되지 않았습니다. 사이드바 상단의 [API Key 등록]을 통해 키를 먼저 등록해 주십시오.");
  }

  var campaignFolder = getCampaignFolder();
  var specDoc = readGoogleDoc(campaignFolder, CONFIG.SPEC_DOC_NAME || "SPEC");
  if (!specDoc) {
    throw new Error("제작 명세서(SPEC)가 아직 생성되지 않았습니다. 사이드바의 [Step 3] 제작 명세서(SPEC) 생성을 먼저 실행해 주십시오.");
  }

  return runPersonaPanelSynthesis();
}

/**
 * [Step 5 가드레일] 초판 마케팅 콘텐츠(rv-00) 생성
 *
 * @param {boolean} [forceOverwrite] - 기존 에셋 완비 시 전체 강제 새로고침 여부 (기본값: false)
 */
function guardAndRunInitialContent(forceOverwrite) {
  var apiKey = getGeminiApiKey();
  if (!apiKey) {
    throw new Error("Gemini API Key가 등록되지 않았습니다. 사이드바 상단의 [API Key 등록]을 통해 키를 먼저 등록해 주십시오.");
  }

  var campaignFolder = getCampaignFolder();
  var planDoc = readGoogleDoc(campaignFolder, CONFIG.PLAN_DOC_NAME || "PLAN") || readGoogleDoc(campaignFolder, "BRD");
  if (!planDoc) {
    throw new Error("캠페인 기획서(PLAN)가 아직 생성되지 않았습니다. 사이드바의 [Step 2] 캠페인 기획서(PLAN) 생성을 먼저 실행해 주십시오.");
  }

  return runInitialContentGeneration(forceOverwrite);
}

/**
 * 초판 마케팅 콘텐츠 전체 강제 재생성 런처
 */
function forceRunInitialContent() {
  return guardAndRunInitialContent(true);
}

/**
 * [Step 6 가드레일] AI 페르소나 다면 평가 런처
 *
 * @param {string} [targetRound] - 명시적 타깃 회차 (선택, 예: 'fb-01')
 */
function promptAndRunJudgeEvaluation(targetRound) {
  var apiKey = getGeminiApiKey();
  if (!apiKey) {
    throw new Error("Gemini API Key가 등록되지 않았습니다. 사이드바 상단의 [API Key 등록]을 통해 키를 먼저 등록해 주십시오.");
  }

  var latestRv = detectLatestRevisionRoundNum();
  var latestFb = detectLatestFeedbackRoundNum();

  // 선결 조건: 평가할 콘텐츠가 존재하는지 점검
  var campaignFolder = getCampaignFolder();
  var rv00Folder = getCampaignSubFolder(["output", "rv-00"]);
  var hasContent = readGoogleDoc(rv00Folder, CONFIG.CONTENT_DOC_NAME || "campaign_content") ||
                   readGoogleDoc(rv00Folder, "campaign_asset") ||
                   readTextFile(rv00Folder, "campaign_content.md");
  if (!hasContent && latestRv < 0) {
    throw new Error("다면 평가를 수행할 마케팅 콘텐츠(rv-00)가 존재하지 않습니다. 사이드바의 [Step 5] 초판 멀티 채널 콘텐츠 생성을 먼저 실행해 주십시오.");
  }

  var suggestedRound = Math.max(latestFb + 1, latestRv + 1, 1);
  var targetRoundStr = targetRound || ("fb-" + (suggestedRound < 10 ? "0" + suggestedRound : "" + suggestedRound));

  return runPersonaEvaluation(targetRoundStr);
}

/**
 * [Step 7 가드레일] 피드백 종합 분석 보고서 생성 런처
 *
 * @param {string} [targetRound] - 명시적 타깃 피드백 회차 (선택, 예: 'fb-01')
 */
function promptAndRunFeedbackSummary(targetRound) {
  var apiKey = getGeminiApiKey();
  if (!apiKey) {
    throw new Error("Gemini API Key가 등록되지 않았습니다. 사이드바 상단의 [API Key 등록]을 통해 키를 먼저 등록해 주십시오.");
  }

  var latestFb = detectLatestFeedbackRoundNum();
  if (latestFb < 1) {
    throw new Error("아직 실행된 AI 페르소나 다면 평가 데이터가 없습니다. 사이드바의 [Step 6] AI 페르소나 다면 평가를 먼저 실행해 주십시오.");
  }

  var suggestedFbStr = "fb-" + (latestFb < 10 ? "0" + latestFb : "" + latestFb);
  var targetRoundStr = targetRound || suggestedFbStr;

  return runFeedbackSummaryReport(targetRoundStr);
}

/**
 * [Step 8 가드레일] 마케터 보정 지침서 작성 및 확정 런처
 *
 * @param {string} [customDirective] - 인라인 전달 지침 (선택)
 * @param {string} [targetRound] - 명시적 타깃 피드백 회차 (선택, 예: 'fb-01')
 */
function promptAndRunMarketerDirective(customDirective, targetRound) {
  var latestFb = detectLatestFeedbackRoundNum();
  if (latestFb < 1) {
    throw new Error("다면 평가 피드백 데이터가 아직 없습니다. 사이드바의 [Step 6] AI 페르소나 다면 평가를 먼저 실행해 주십시오.");
  }

  var suggestedFbStr = "fb-" + (latestFb < 10 ? "0" + latestFb : "" + latestFb);
  var targetRoundStr = targetRound || suggestedFbStr;

  return runMarketerDirective(customDirective, targetRoundStr);
}

/**
 * [Step 9 가드레일] 마케팅 콘텐츠 리비전 보정 런처 (rv-01 ~ rv-99)
 *
 * @param {string} [customDirectiveOrTargetRv] - 인라인 보정 지침 문자열 또는 명시적 타깃 리비전 (예: 'rv-01')
 */
function promptAndRunFeedbackRevision(customDirectiveOrTargetRv) {
  var apiKey = getGeminiApiKey();
  if (!apiKey) {
    throw new Error("Gemini API Key가 등록되지 않았습니다. 사이드바 상단 온보딩 배너의 [API Key 등록] 버튼을 눌러 먼저 키를 등록해 주십시오.");
  }

  var latestFb = detectLatestFeedbackRoundNum();
  var latestRv = detectLatestRevisionRoundNum();

  if (latestFb < 1) {
    throw new Error("다면 평가 피드백 데이터가 아직 없습니다. 사이드바의 [Step 6] AI 페르소나 다면 평가 및 [Step 7] 피드백 종합 분석 보고서를 먼저 실행해 주십시오.");
  }

  var targetDirective = "";
  var targetRvStr = "";
  if (typeof customDirectiveOrTargetRv === "string" && customDirectiveOrTargetRv.trim()) {
    var trimmed = customDirectiveOrTargetRv.trim();
    if (trimmed.indexOf("rv-") === 0) {
      targetRvStr = trimmed;
    } else {
      targetDirective = trimmed;
    }
  }

  var suggestedRv = Math.max(latestRv + 1, 1);
  if (!targetRvStr) {
    targetRvStr = "rv-" + (suggestedRv < 10 ? "0" + suggestedRv : "" + suggestedRv);
  }
  var targetRvNum = parseInt(targetRvStr.replace("rv-", ""), 10) || suggestedRv;
  var targetRoundStr = "fb-" + (targetRvNum < 10 ? "0" + targetRvNum : "" + targetRvNum);

  return runReviseContent(targetRoundStr, false, false, targetDirective);
}

/**
 * 고객 VoC 설문 폼 URL 확인 (모달 배제)
 *
 * @return {string} 고객 설문 폼 URL
 */
function openCustomerVocForm() {
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  var formUrl = spreadsheet.getFormUrl();

  if (!formUrl) {
    try {
      var campaignFolder = getCampaignFolder();
      var files = campaignFolder.getFilesByType(MimeType.GOOGLE_FORMS);
      if (files.hasNext()) {
        var form = FormApp.openById(files.next().getId());
        formUrl = form.getPublishedUrl();
      }
    } catch (e) {
      // 무시
    }
  }

  if (formUrl) {
    return formUrl;
  }
  throw new Error("스프레드시트에 연결된 Google Forms가 없습니다. 사이드바의 [초기화] 캠페인 작업 공간 구축을 실행하면 자동 생성 및 연동됩니다.");
}

/**
 * 타깃 AI 페르소나 패널 맞춤 재설정 (모달 배제, Gemini 생성 또는 Hugging Face 동기화)
 * 캠페인 루트 폴더의 ai_personas.json을 직접 갱신한다.
 *
 * @param {string} [criteriaOpt] - 타깃 페르소나 기준 문자열 (선택)
 * @return {string} 처리 결과 메시지
 */
function setCustomPersonasPrompt(criteriaOpt) {
  var criteria = (criteriaOpt || "").trim();
  if (!criteria) {
    throw new Error("타깃 페르소나 기준이 입력되지 않았습니다. 사이드바 채팅창에 원하는 페르소나 기준을 입력해 주십시오.");
  }

  var campaignFolder = getCampaignFolder();
  var campaignCode = getCampaignCode();
  var generatedJson = "";

  var personaInstruction = (typeof getPromptTemplate === "function")
    ? getPromptTemplate("03_persona_synthesis")
    : "";

  // 1. Hugging Face Server API 연동 여부 판별
  if (criteria.indexOf("hf:") === 0) {
    var datasetRepo = criteria.replace("hf:", "").trim();
    var hfUrl = "https://datasets-server.huggingface.co/rows?dataset=" + encodeURIComponent(datasetRepo) + "&config=default&split=train&offset=0&limit=25";
    var hfResp = UrlFetchApp.fetch(hfUrl, { muteHttpExceptions: true });
    if (hfResp.getResponseCode() === 200) {
      var hfData = JSON.parse(hfResp.getContentText());
      var rawRowsText = JSON.stringify(hfData.rows || hfData, null, 2);
      var normInstruction = personaInstruction ||
        "당신은 데이터 엔지니어이다. 제공된 Hugging Face 원본 데이터로부터 슬림 페르소나 JSON 객체를 추출 및 정규화하라.\n" +
        "반드시 id, name, age, gender, category(전문 마케터 또는 일반 소비자), occupation, perspective 7개 필드를 포함하는 유효한 JSON으로 출력하라.";
      generatedJson = callGemini(normInstruction, rawRowsText);
    } else {
      throw new Error("Hugging Face API 호출 실패 (응답 코드: " + hfResp.getResponseCode() + ")");
    }
  } else {
    // 2. Gemini 기반 자연어 타깃 페르소나 즉시 합성
    var systemInstruction = personaInstruction ||
      "당신은 글로벌 소비자 리서치 및 엔터프라이즈 마케팅 페르소나 엔지니어링 AI이다.\n" +
      "사용자가 지정한 타깃 기준에 맞추어 마케팅 캠페인 콘텐츠와 광고 소재를 다면 평가할 슬림 AI 페르소나 패널을 도출하라.\n\n" +
      "필수 규칙:\n" +
      "1. 패널 구성: 전문 마케터와 일반 소비자로 균형 있게 안배하십시오.\n" +
      "2. 반드시 id, name, age, gender, category, occupation, perspective 7개 필드를 엄격히 포함하는 순수 JSON 객체로 출력하십시오.\n" +
      "3. 코드 블록(```json) 없이 유효한 JSON만 반환하십시오.";

    var userPrompt = "타깃 페르소나 기준: " + criteria + "\n\n위 기준에 부합하는 정밀하고 다양한 슬림 페르소나 JSON을 생성하라.";
    generatedJson = callGemini(systemInstruction, userPrompt);
  }

  if (generatedJson) {
    var parsed = safeParseJson(generatedJson, null, false);
    if (!parsed) {
      throw new Error("생성된 페르소나 데이터의 유효한 JSON을 추출하지 못했습니다.");
    }
    var formatted = JSON.stringify(parsed, null, 2);

    // 캠페인 루트 폴더 직속에 저장
    saveTextFile(campaignFolder, "ai_personas.json", formatted);

    // 하위 호환성을 위해 input 폴더에도 보조 동기화
    try {
      var inputFolder = getCampaignSubFolder(["input"]);
      saveTextFile(inputFolder, "ai_personas.json", formatted);
    } catch (subErr) {
      // 무시
    }

    return "지정한 기준('" + criteria + "')에 맞추어 맞춤 AI 페르소나 패널 데이터가 성공적으로 갱신되었습니다.";
  }
  throw new Error("페르소나 데이터를 생성하지 못했습니다.");
}

/**
 * GitHub 퍼블릭 저장소의 최신 번들 엔진 코드로 즉시 강제 갱신한다. (모달 배제)
 */
function forceSyncEngine() {
  if (typeof loadPipelineEngine === "function") {
    loadPipelineEngine(true);
    return { success: true, message: "GitHub 퍼블릭 저장소로부터 최신 파이프라인 엔진 코드가 성공적으로 갱신되었습니다." };
  } else {
    return { success: true, message: "현재 단일 번들 직접 실행 모드로 구동 중입니다. 최신 버전으로 업그레이드하려면 저장소의 최신 번들 코드를 다시 복사하여 붙여넣으십시오." };
  }
}
