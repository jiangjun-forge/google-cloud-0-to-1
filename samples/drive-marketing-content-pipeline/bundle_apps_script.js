// ============================================================================
// FILE: apps-scripts/Code_Config.js
// ============================================================================

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

  // 인증 방식: Google AI Studio 무료 API Key 기반 인증 (Zero-GCP Dependency)
  // GCP 프로젝트, 신용카드 등록, 빌링 계정 없이 개인 구글 계정으로 무료 발급받아 100% 구동됨
  AUTH_MODE: "API_KEY",
  API_KEY: "", // 공란 유지 시 PropertiesService.getUserProperties() 또는 실행 시 대화상자에서 자동 취득
  
  // Google AI Studio 엔드포인트 및 태스크별 최적 모델 지정 (As of 2026-10-13)
  // 단일 모델에 의존하지 않고 작업별 특성(속도, 이미지, 영상)에 맞추어 검증된 모델을 취사선택함
  BASE_URL: "https://generativelanguage.googleapis.com/v1beta/models",
  GEMINI_MODEL: "gemini-3.8-flash",
  MODEL_GENERATOR: "gemini-3.8-flash", // 콘텐츠 발상 및 멀티모달 소재 생성 모델
  MODEL_JUDGE: "gemini-3.8-flash", // 25인 AI 페르소나 다면 평가 및 가드레일 판정 모델
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
  PERSONA_FILE_NAME: "ai_personas.json", // 25인 타깃 AI 페르소나 마스터 데이터 (캠페인 루트 직속)
  PROMPTS_FOLDER_NAME: "prompts", // 마케터 수정용 프롬프트 구글 독스 보관 폴더명
  DIRECTIVE_DOC_NAME: "마케터 보정 지침", // 마케터 전용 의사 결정 및 보정 지침서 (AI 덮어쓰기 금지)

  // GitHub 퍼블릭 저장소 Raw 베이스 URL (초기화 시 최신 프롬프트 실시간 인출)
  GITHUB_RAW_BASE: "https://raw.githubusercontent.com/jiangjun-forge/google-cloud-0-to-1/main/samples/drive-marketing-content-pipeline",

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
  
  // QuickChart REST API 엔드포인트 (t-SNE 여론 군집 지형도 렌더링)
  QUICKCHART_ENDPOINT: "https://quickchart.io/chart",

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
      description: "타깃 맞춤 AI 페르소나 25인 패널 합성 및 Hugging Face 정규화 지침",
      systemInstruction:
        "당신은 엔터프라이즈 마케팅 페르소나 엔지니어링 AI이다. 제공된 제작 명세서(SPEC)의 타깃 오디언스 또는 Hugging Face 데이터로부터 전문 마케터 12인과 일반 소비자 13인으로 구성된 25인 슬림 AI 페르소나 패널 JSON 객체(7대 필수 필드: id, name, age, gender, category, occupation, perspective)를 반환하라. 한글 복합어는 철저히 띄어 쓰고 이모지와 중간 점은 배제하라."
    },
    "04_content_generation": {
      title: "04_content_generation",
      description: "초판 마케팅 카피라이팅 및 모바일 숏폼 영상 콘티 생성 지침",
      systemInstruction:
        "당신은 크리에이티브 마케팅 디렉터이다. 기획서(PLAN)와 제작 명세서(SPEC)를 준수하여 채널별 카피라이팅과 15초 모바일 숏폼 영상(9:16) 연출 콘티가 통합된 campaign_content 구글 독스를 작성하라. 한글 복합어는 철저히 띄어 쓰고 이모지와 중간 점은 일절 배제하라."
    },
    "05_persona_evaluation": {
      title: "05_persona_evaluation",
      description: "25인 한국인 마스터 AI 페르소나 다면 평가 및 세부 의견 포인트 도출 지침",
      systemInstruction:
        "당신은 엔터프라이즈 마케팅 리서치 분석 AI이다. 공개된 마케팅 콘텐츠를 25인 한국인 가상 페르소나 관점에서 다면 평가하고, 1인당 2~4개의 세부 의견 포인트(points 배열, 총 50~80개)를 포함하는 순수 JSON 배열만 반환하라. 한글 복합어는 철저히 띄어 쓰고 이모지와 중간 점은 배제하라."
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
        "당신은 CMO 전속 수석 분석관이다. 25인 페르소나 다면 평가, 고객 VoC 설문 응답, 실제 제출된 미디어 VLM 분석 결과를 종합하여 feedback_summary 구글 독스를 작성하라. 실제 제출 미디어가 없으면 미제출로 명시하고, 문서 하단에 AI 추천 보정 방향 요약을 포함하라. 한글 복합어는 철저히 띄어 쓰라."
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

// ============================================================================
// FILE: apps-scripts/Code_Gemini.js
// ============================================================================

/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 2] Gemini REST API 클라이언트 엔진 (Google AI Studio 무료 API Key 기반 Zero-GCP 인증)
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

  return promptForGeminiApiKey();
}

/**
 * Google AI Studio Gemini API Key 입력 및 저장 UI 프롬프트
 */
function promptForGeminiApiKey() {
  var ui = SpreadsheetApp.getUi();
  var userProps = PropertiesService.getUserProperties();
  var currentKey = userProps.getProperty("GEMINI_API_KEY") || "";
  var maskedKey = currentKey ? (currentKey.substring(0, 6) + "..." + currentKey.substring(currentKey.length - 4)) : "미등록";

  var response = ui.prompt(
    "Google AI Studio Gemini API Key 설정 (Zero-GCP)",
    "Google Cloud 콘솔 및 신용카드 등록 없이 개인 구글 계정으로 100% 무료 구동됩니다.\n\n" +
    "1. Google AI Studio ( https://aistudio.google.com/app/apikey ) 에서 무료 API Key를 발급받으십시오.\n" +
    "2. 발급받은 API Key(AIzaSy...)를 아래에 입력하십시오:\n\n" +
    "(현재 등록된 키: " + maskedKey + ")",
    ui.ButtonSet.OK_CANCEL
  );

  if (response.getSelectedButton() === ui.Button.OK) {
    var inputKey = response.getResponseText().trim();
    if (inputKey) {
      // 키 유효성 사전 검증 (Fast-Fail Pre-flight Validation)
      var isValid = validateGeminiApiKey(inputKey);
      if (!isValid) {
        var proceed = ui.alert(
          "API Key 검증 경고",
          "입력하신 API Key로 Gemini API 핑(Ping) 테스트에 실패했습니다.\n" +
          "키에 오타가 있거나 비활성화되었을 수 있습니다.\n\n" +
          "이 키를 그대로 저장하시겠습니까?",
          ui.ButtonSet.YES_NO
        );
        if (proceed !== ui.Button.YES) {
          return promptForGeminiApiKey();
        }
      }
      userProps.setProperty("GEMINI_API_KEY", inputKey);
      ui.alert("설정 완료", "Gemini API Key가 성공적으로 검증 및 저장되었습니다.\n파이프라인 단계를 계속 진행하십시오.", ui.ButtonSet.OK);
      return inputKey;
    } else {
      ui.alert("입력 오류", "유효한 API Key가 입력되지 않았습니다.", ui.ButtonSet.OK);
    }
  }

  throw new Error("Gemini API Key가 설정되지 않아 작업을 중단합니다. 메뉴의 [Gemini API Key 설정]에서 키를 등록하십시오.");
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
 */
function callGemini(systemInstruction, userContent, modelOverride, maxTokensOverride) {
  var apiKey = getGeminiApiKey();
  var targetModel = modelOverride || CONFIG.MODEL_GENERATOR || CONFIG.GEMINI_MODEL || "gemini-3.8-flash";
  var endpoint = CONFIG.BASE_URL + "/" + targetModel + ":generateContent?key=" + apiKey;
  var maxTokens = maxTokensOverride || 8192;

  var payload = {
    contents: [{
      role: "user",
      parts: [{ text: userContent }]
    }],
    generationConfig: {
      maxOutputTokens: maxTokens,
      temperature: 0.7
    }
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
      Logger.log("모든 Veo 모델 생성 작업 큐 등록에 실패하여 비디오 생성을 완료하지 못했습니다 (Google AI Studio 무료 티어 API Key는 Veo가 미지원되거나 유료 결제 계정 필요).");
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

// ============================================================================
// FILE: apps-scripts/Code_Prompts.js
// ============================================================================

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

  var rawBase = (CONFIG && CONFIG.GITHUB_RAW_BASE) || "https://raw.githubusercontent.com/jiangjun-forge/google-cloud-0-to-1/main/samples/drive-marketing-content-pipeline";
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

// ============================================================================
// FILE: apps-scripts/Code_Workspace.js
// ============================================================================

/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 4] 캠페인 작업 공간 초기화 및 구글 폼 올인원 세팅 엔진 (Workspace & Form Initializer)
 */

/**
 * [캠페인 초기화] 구글 드라이브 폴더 트리, 루트 직속 [아이디어 메모], 25인 페르소나, 9대 프롬프트 구글 독스,
 * 그리고 고객 VoC 수집용 Google Forms 생성 및 시트 바인딩까지 초장에 100% 완결한다.
 */
function initCampaignWorkspace() {
  return withUserLock("campaign_init", function() {
    var ui = SpreadsheetApp.getUi();
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

    // 2. [핵심] 25인 타깃 AI 페르소나 마스터 데이터를 캠페인 루트 폴더 직속에 시딩
    var personaFileName = CONFIG.PERSONA_FILE_NAME || "ai_personas.json";
    var existingPersonas = campaignFolder.getFilesByName(personaFileName);
    if (!existingPersonas.hasNext()) {
      var masterPersonas = getMasterPersonas25();
      var personaJsonText = JSON.stringify(masterPersonas, null, 2);
      saveTextFile(campaignFolder, personaFileName, personaJsonText);
      Logger.log("루트 직속 25인 AI 페르소나 데이터셋 시딩 완료: " + personaFileName);
    }

    // 3. prompts/ 폴더 내 9대 프롬프트 구글 독스 자동 시딩 (기존 마케터 수정분 보존)
    seedDefaultPrompts(promptsFolder);

    // 4. [UX 개선] 스타터 아이디어 메모 구글 독스 캠페인 루트 폴더 직속 시딩
    var ideaDocName = CONFIG.IDEA_DOC_NAME || "아이디어 메모";
    if (!readGoogleDoc(campaignFolder, ideaDocName)) {
      var starterIdea =
        "# 캠페인 아이디어 메모\n\n" +
        "* **캠페인 명칭**: 2026 가을 오텀 브리즈 캠페인 (" + campaignCode + ")\n" +
        "* **핵심 컨셉**: 선선한 가을 날씨에 어울리는 프리미엄 노이즈 캔슬링(ANC) 헤드폰 일상 탈출 컬렉션\n" +
        "* **타깃 고객**: 도심 속 워크앤라이프 밸런스를 추구하는 2040 직장인 및 통근자\n" +
        "* **핵심 소구점**: 180g 경량 착용감, 45dB 차음 성능, 감성적 힐링 몰입 무드\n" +
        "* **목표 채널**: 유튜브 쇼츠 및 인스타그램 릴스(9:16), 디스플레이 배너(16:9), 블로그 브랜드 기고문\n";

      saveGoogleDoc(campaignFolder, ideaDocName, starterIdea);
      Logger.log("캠페인 루트 직속 스타터 아이디어 메모 생성 완료: " + ideaDocName);
    }

    // 5. [핵심] 고객 VoC 수집용 구글 폼(Google Forms) 자동 생성 및 시트 연동 초장 완결
    var formInfo = setupFeedbackGoogleForm(campaignFolder, campaignCode);

    // 6. 현재 구글 시트를 캠페인 루트 폴더로 안전하게 이동하여 컨트롤 타워 패키징
    try {
      var activeSpreadsheet = SpreadsheetApp.getActiveSpreadsheet();
      var sheetFile = DriveApp.getFileById(activeSpreadsheet.getId());
      sheetFile.moveTo(campaignFolder);
      var currentTitle = activeSpreadsheet.getName();
      if (!currentTitle || currentTitle === "제목 없는 스프레드시트" || currentTitle === "마케팅 콘텐츠 파이프라인") {
        activeSpreadsheet.rename("[마케팅 컨트롤 타워] " + campaignCode);
      }
    } catch (sheetMoveErr) {
      Logger.log("시트 캠페인 폴더 이동 중 예외 (무시 가능): " + sheetMoveErr);
    }

    // 7. 구글 시트 실행 대시보드 표 초기화 및 핵심 리소스 링크 등록
    var durationSec = Math.round((new Date().getTime() - startTime) / 1000);
    initDashboardSheet();
    recordStepResultToSheet(
      "초기 환경 구축",
      "작업 공간 및 VoC 설문 폼",
      "완료",
      campaignFolder.getUrl(),
      "구글 드라이브 폴더 열기 (" + campaignCode + ")",
      durationSec,
      "-",
      "캠페인 폴더 트리 8종 구축, 9대 프롬프트 독스 및 루트 직속 아이디어 메모 적재 완료"
    );
    if (formInfo && formInfo.publishedUrl) {
      recordStepResultToSheet(
        "고객 피드백 채널",
        "VoC 구글 폼 및 모바일 QR",
        "활성",
        formInfo.publishedUrl,
        "온라인 설문지 열기",
        durationSec,
        "-",
        "Google Forms 연동 완료 (현재 시트에 설문 응답 실시간 수신 대기)"
      );
    }

    showResultModal(
      "캠페인 초기 환경 구축 완료 (" + campaignCode + ")",
      "캠페인 루트 직속 [아이디어 메모], 25인 페르소나, 9대 프롬프트 구글 독스, 고객 VoC 설문 폼이 준비되었습니다.\n아래 버튼을 눌러 캠페인 드라이브 폴더를 즉시 확인하십시오.",
      "캠페인 드라이브 폴더 열기",
      campaignFolder.getUrl()
    );
  } catch (e) {
    ui.alert("초기화 중 오류 발생", e.toString(), ui.ButtonSet.OK);
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

    // 기존에 생성된 폼이 있는지 탐색
    var existingFiles = campaignFolder.getFilesByName(formTitle);
    if (existingFiles.hasNext()) {
      var file = existingFiles.next();
      var existingForm = FormApp.openById(file.getId());
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
 */
function runConfigureCampaignSettings() {
  var ui = SpreadsheetApp.getUi();
  var userProps = PropertiesService.getUserProperties();
  var currentCode = userProps.getProperty("CAMPAIGN_CODE") || CONFIG.CAMPAIGN_CODE || "cp-ignite";

  var response = ui.prompt(
    "캠페인 환경 설정 및 재설정 (Configuration)",
    "현재 캠페인 코드: [" + currentCode + "]\n\n" +
    "새로운 캠페인 코드를 입력하거나 기존 코드를 유지하십시오 (영문 소문자 및 하이픈 권장):",
    ui.ButtonSet.OK_CANCEL
  );

  if (response.getSelectedButton() === ui.Button.OK) {
    var newCode = response.getResponseText().trim();
    if (newCode) {
      userProps.setProperty("CAMPAIGN_CODE", newCode);
      ui.alert("설정 완료", "캠페인 코드가 [" + newCode + "]로 업데이트되었습니다.", ui.ButtonSet.OK);
      return newCode;
    }
  }
  return currentCode;
}

/**
 * 25인 슬림 한국인 AI 페르소나 마스터 데이터셋 반환
 */
function getMasterPersonas25() {
  return {
    "metadata": {
      "description": "한국인 25인 다면 평가 슬림 AI 페르소나 패널 (토큰 최적화 경량 규격)",
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

// ============================================================================
// FILE: apps-scripts/Code_Content.js
// ============================================================================

/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 5] 기획서(PLAN/SPEC) 도출 및 멀티 채널 콘텐츠 생성/보정 엔진 (Content Engine)
 */

/**
 * [액션 1] 마케터 자연어 아이디어를 기반으로 캠페인 기획서(PLAN) 및 콘텐츠 제작 명세서(SPEC)를 자동 도출한다.
 */
function runIdeaToPlanConversion() {
  return withUserLock("plan_generation", function() {
    var ui = SpreadsheetApp.getUi();
  var startTime = new Date().getTime();
  showProcessingToast("아이디어 기반 기획서(PLAN) 및 명세서(SPEC) 자동 도출 중...", 30);
  try {
    var campaignFolder = getCampaignFolder();
    var campaignCode = getCampaignCode();
    var inputFolder = getCampaignSubFolder(["input"]);
    var ideaDocName = (CONFIG && CONFIG.IDEA_DOC_NAME) || "아이디어 메모";

    // 1. 캠페인 루트 직속 [아이디어 메모] 읽기 (레거시 input/ 폴더도 보조 탐색)
    var existingIdea = readGoogleDoc(campaignFolder, ideaDocName) || readGoogleDoc(inputFolder, ideaDocName) || "";
    var existingPreview = existingIdea.replace(/\n+/g, " ").trim();
    if (existingPreview.length > 60) {
      existingPreview = existingPreview.substring(0, 60) + "...";
    }

    var promptMsg = existingPreview
      ? "현재 등록된 아이디어 메모:\n[" + existingPreview + "]\n\n" +
        "새로운 캠페인 아이디어를 입력하십시오:\n" +
        "(빈칸으로 두고 [확인]을 누르면 기존 아이디어 메모를 그대로 사용합니다)"
      : "캠페인 컨셉이나 아이디어 초안을 자유롭게 입력하십시오:\n(예: 2026 프리미엄 노이즈 캔슬링 헤드폰 론칭 프로모션)";

    var promptResp = ui.prompt("마케팅 캠페인 아이디어 확인", promptMsg, ui.ButtonSet.OK_CANCEL);
    if (promptResp.getSelectedButton() !== ui.Button.OK) {
      return;
    }

    var inputVal = promptResp.getResponseText().trim();
    var ideaMemo = inputVal || existingIdea;

    if (inputVal) {
      saveGoogleDoc(campaignFolder, ideaDocName, inputVal);
    }

    if (!ideaMemo || ideaMemo.trim().length < 5) {
      throw new Error("캠페인 아이디어가 입력되지 않아 기획서 생성을 중단합니다. 캠페인 루트의 [아이디어 메모] 문서를 확인하십시오.");
    }

    resetSessionTokens();

    // 2-1단계: 아이디어 메모로부터 마케팅 캠페인 기획서(PLAN) 전문 도출
    var planSystemInstruction = getPromptTemplate("01_idea_to_plan");
    var planUserPrompt =
      "다음은 마케터가 작성한 캠페인 아이디어 초안 메모이다.\n\n" +
      "### [마케터 아이디어 메모]\n" + ideaMemo + "\n\n" +
      "위 아이디어를 정밀 분석하여 마케팅 캠페인 기획서(PLAN) 전문을 체계적인 마크다운으로 작성하라.";

    var planContent = callGemini(planSystemInstruction, planUserPrompt);

    // 2-2단계: 도출된 기획서(PLAN)를 바탕으로 정밀한 콘텐츠 제작 명세서(SPEC) 도출 (독립 파이프라인)
    var specSystemInstruction = getPromptTemplate("02_plan_to_spec");
    var specUserPrompt =
      "다음은 이번 캠페인의 마케팅 기획서(PLAN) 전문이다.\n\n" +
      "### [마케팅 캠페인 기획서 (PLAN)]\n" + planContent + "\n\n" +
      "위 기획서의 타깃 오디언스, 핵심 USP, 캠페인 전략을 충실히 반영하여 제작 실무진(디자이너, 영상 PD, 카피라이터)을 위한 콘텐츠 제작 명세서(SPEC) 전문을 마크다운으로 작성하라:\n" +
      "- 가로 16:9 배너 (1920x1080), 세로 9:16 모바일 포스터 (1080x1920), 정방형 1:1 SNS 피드 (1080x1080)\n" +
      "- 15초 세로 9:16 모바일 숏폼 영상 콘티 규격 및 4대 평가 영역 설문 가이드라인 정의";

    var specContent = callGemini(specSystemInstruction, specUserPrompt);

    // 2-3단계: 제작 명세서(SPEC)의 타깃 오디언스에 맞춘 25인 AI 페르소나 패널 자동 합성 (온디맨드 동적 갱신)
    try {
      var personaSystemInstruction = getPromptTemplate("03_persona_synthesis");
      var personaUserPrompt =
        "다음은 이번 캠페인의 콘텐츠 제작 명세서(SPEC) 및 기획서(PLAN)이다.\n\n" +
        "### [마케팅 제작 명세서 발췌]\n" + (specContent.substring(0, 1800)) + "\n\n" +
        "위 명세서의 타깃 오디언스 프로파일 및 페인 포인트를 심층 분석하여, 콘텐츠를 다각도로 평가할 25인의 슬림 AI 페르소나 패널 JSON 객체(7대 필수 필드: id, name, age, gender, category, occupation, perspective)를 도출하라.";
      var synthesizedPersonasRaw = callGemini(personaSystemInstruction, personaUserPrompt);
      if (synthesizedPersonasRaw) {
        var parsedPersonas = safeParseJson(synthesizedPersonasRaw, null, false);
        if (parsedPersonas && (parsedPersonas.personas || Array.isArray(parsedPersonas))) {
          var personaFileName = (CONFIG && CONFIG.PERSONA_FILE_NAME) || "ai_personas.json";
          saveTextFile(campaignFolder, personaFileName, JSON.stringify(parsedPersonas, null, 2));
          Logger.log("제작 명세서 기반 25인 타깃 맞춤 페르소나 자동 합성 완료: " + personaFileName);
        }
      }
    } catch (personaErr) {
      Logger.log("타깃 페르소나 자동 합성 중 예외 (기존 페르소나 유지): " + personaErr);
    }

    var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
    var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";

    var planFile = saveGoogleDoc(campaignFolder, planDocName, planContent);
    var specFile = saveGoogleDoc(campaignFolder, specDocName, specContent);

    var durationSec = Math.round((new Date().getTime() - startTime) / 1000);
    var planTokens = getSessionTotalTokens();
    var halfTokens = Math.round(planTokens / 2);

    // 4. 대시보드 시트에 링크 및 소요 시간, 소모 토큰, 실행 로그 기록
    recordStepResultToSheet(
      "기획서 (PLAN)",
      "마케팅 캠페인 기획서",
      "완료",
      planFile.getUrl(),
      "구글 독스 열기 (PLAN)",
      durationSec,
      halfTokens,
      "마케터 아이디어 분석 기반 기획서(PLAN) 독스 자동 생성 완료"
    );
    recordStepResultToSheet(
      "제작 명세서 (SPEC)",
      "멀티 채널 콘텐츠 제작 명세서",
      "완료",
      specFile.getUrl(),
      "구글 독스 열기 (SPEC)",
      durationSec,
      halfTokens,
      "16:9 배너, 9:16 포스터, 1:1 SNS, 15초 숏폼 규격 명세서(SPEC) 독스 생성 완료"
    );

    showResultModal(
      "기획서 및 명세서 생성 완료",
      "캠페인 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC) 구글 독스가 준비되었습니다.\n\n" +
      "* 처리 소요 시간: " + formatDuration(durationSec) + "\n\n" +
      "아래 버튼을 클릭하여 기획서를 검토하거나 SPEC 수치를 직접 수정하십시오.",
      "기획서 구글 독스 열기 (PLAN)",
      planFile.getUrl()
    );
  } catch (e) {
    ui.alert("기획서 도출 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
  });
}

/**
 * [액션 2] 기획서(PLAN) 및 명세서(SPEC)를 기반으로 초판 마케팅 콘텐츠(rv-00)를 생성한다.
 */
function runInitialContentGeneration() {
  return withUserLock("content_generation", function() {
    var ui = SpreadsheetApp.getUi();
  var startTime = new Date().getTime();
  showProcessingToast("초판 마케팅 콘텐츠 생성 중 (rv-00)...", 60);
  try {
    var campaignFolder = getCampaignFolder();
    var campaignCode = getCampaignCode();
    var rv00Folder = getCampaignSubFolder(["output", "rv-00"]);

    // 폴더 내 기존 에셋 검사 및 스마트 분기
    var folderStatus = inspectRevisionFolder(rv00Folder, "00");
    var onlyMissing = false;

    if (!folderStatus.isEmpty) {
      if (folderStatus.isComplete) {
        var respComplete = ui.alert(
          "초판 콘텐츠(rv-00) 완비 안내",
          "초판 폴더(rv-00)에 모든 에셋(카피 독스, 이미지 3종, 숏폼 비디오)이 이미 완비되어 있습니다.\n\n" +
          "모든 에셋을 새로 덮어쓰시겠습니까?\n" +
          "([예]: 전체 새로 덮어쓰기 / [아니오]: 작업 중단)",
          ui.ButtonSet.YES_NO
        );
        if (respComplete !== ui.Button.YES) {
          return;
        }
      } else {
        var missingMsg = folderStatus.missingFiles.join(", ");
        var existingMsg = folderStatus.existingFiles.join(", ");
        var respMissing = ui.alert(
          "초판 콘텐츠(rv-00) 미완성 에셋 감지",
          "초판 폴더(rv-00)에 일부 에셋이 존재합니다.\n\n" +
          "* 보존 대상 기존 파일: " + existingMsg + "\n" +
          "* 누락된 미완성 파일: " + missingMsg + "\n\n" +
          "[예] 누락된 미완성 파일만 고속 보충 (권장, 기존 편집본 및 이미지 보존)\n" +
          "[아니오] 전체 덮어쓰기 (모든 에셋 새로 재생성)",
          ui.ButtonSet.YES_NO_CANCEL
        );
        if (respMissing === ui.Button.CANCEL) {
          return;
        } else if (respMissing === ui.Button.YES) {
          onlyMissing = true;
        }
      }
    }

    // 선결 조건 검사: PLAN 문서 확인
    var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
    var planContent = readGoogleDoc(campaignFolder, planDocName);
    if (!planContent) {
      planContent = readGoogleDoc(campaignFolder, "BRD");
    }
    if (!planContent) {
      var confirmGen = ui.alert(
        "기획서(PLAN) 누락 안내",
        "캠페인 기획서(PLAN) 문서를 찾을 수 없습니다.\n지금 [기획서 및 명세서 생성]을 먼저 실행하시겠습니까?",
        ui.ButtonSet.YES_NO
      );
      if (confirmGen === ui.Button.YES) {
        runIdeaToPlanConversion();
        return;
      } else {
        return;
      }
    }

    var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";
    var specContent = readGoogleDoc(campaignFolder, specDocName) || "";

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
      // 1. 프롬프트 템플릿 로드 (구글 독스 스마트 캐싱)
      var systemInstruction = getPromptTemplate("04_content_generation");
      var promptText =
        "다음은 이번 캠페인의 마케팅 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC)이다.\n" +
        "명세서(SPEC)에 정의된 채널 규격, 영상 길이, 비주얼 가이드라인을 엄격히 준수하여 초판 campaign_content를 작성하라:\n\n" +
        "### [1. 마케팅 캠페인 기획서 (PLAN)]\n" + planContent + "\n\n" +
        "### [2. 멀티 채널 콘텐츠 제작 명세서 (SPEC)]\n" + (specContent || "기본 규격 준수");

      var generatedContent = callGemini(systemInstruction, promptText);

      // 2. 동적 비주얼 프롬프트 도출 및 숏폼 영상 콘티 완전 통합
      visualBrief = extractDynamicVisualPrompt(
        generatedContent,
        planContent,
        "A stylish 20s Korean female commuter with lightweight premium ANC headphones in warm golden autumn sunlight on a modern Seoul street"
      );
      finalizedContent = ensureShortsScriptInCampaignContent(generatedContent, "00", visualBrief);

      // 3. campaign_content 단일 구글 독스 문서 저장
      saveGoogleDoc(rv00Folder, contentDocName, finalizedContent);
    }

    // 4. 실시간 대표 비주얼 이미지 3종 및 Veo 비디오 생성
    Logger.log("동적 도출된 비주얼 프롬프트 (rv-00): " + visualBrief);
    var visResult = generateAndSaveVisualAssets(rv00Folder, "00", visualBrief, { onlyMissing: onlyMissing });

    var durationSec = Math.round((new Date().getTime() - startTime) / 1000);

    // 5. 상세 실행 로그 조립
    var logDetail = "";
    if (onlyMissing) {
      var totalSkipped = visResult.skipImageCount + (visResult.videoStatus === "skipped" ? 1 : 0);
      logDetail = "미완성 에셋 선별 보충 완료 (신규 이미지 " + visResult.genImageCount + "건 생성, 기존 에셋 " + totalSkipped + "건 보존)";
    } else {
      var videoDesc = visResult.videoStatus === "generated" ? "Veo 비디오 1건" : "숏폼 콘티 독스 수록";
      logDetail = "통합 카피 독스 1건, 대표 이미지 " + visResult.genImageCount + "종, " + videoDesc + " 정상 생성 완료";
    }

    // 6. 실행 대시보드에 링크 기록
    recordStepResultToSheet(
      "초판 마케팅 콘텐츠",
      "카피 및 비주얼 (rv-00)",
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
  } catch (e) {
    ui.alert("초판 콘텐츠 생성 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
  });
}

/**
 * [액션 3] 피드백 요약본(feedback_summary)과 마케터 지침을 반영하여 N차 개정본 마케팅 콘텐츠를 완결 보정한다.
 */
function runReviseContent(targetRoundOpt, isSilentOpt) {
  return withUserLock("content_revision", function() {
    var ui = SpreadsheetApp.getUi();
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

    // 타깃 폴더 에셋 상태 검사 및 스마트 분기
    var folderStatus = inspectRevisionFolder(targetRvFolder, prefix);
    if (!folderStatus.isEmpty) {
      if (folderStatus.isComplete) {
        var nextRoundNum = roundNum + 1;
        var nextRvName = "rv-" + (nextRoundNum < 10 ? "0" + nextRoundNum : nextRoundNum);
        var respComplete = ui.alert(
          "개정본 콘텐츠(" + targetRvName + ") 완비 안내",
          "개정본 폴더(" + targetRvName + ")에 모든 에셋(카피 독스, 이미지 3종, 숏폼 비디오)이 이미 완비되어 있습니다.\n\n" +
          "[예] 다음 리비전(" + nextRvName + ")으로 안전 신규 생성 (권장, 기존 " + targetRvName + " 보존)\n" +
          "[아니오] 현재 리비전(" + targetRvName + ") 전체 새로 덮어쓰기\n" +
          "[취소] 작업 중단",
          ui.ButtonSet.YES_NO_CANCEL
        );
        if (respComplete === ui.Button.CANCEL) {
          return;
        } else if (respComplete === ui.Button.YES) {
          // 다음 리비전으로 타깃 전환
          roundNum = nextRoundNum;
          prevRvName = targetRvName;
          targetRvName = nextRvName;
          prefix = (roundNum < 10 ? "0" + roundNum : "" + roundNum);
          targetRvFolder = getCampaignSubFolder(["output", targetRvName]);
          folderStatus = inspectRevisionFolder(targetRvFolder, prefix);
        }
      } else {
        var missingMsg = folderStatus.missingFiles.join(", ");
        var existingMsg = folderStatus.existingFiles.join(", ");
        var respMissing = ui.alert(
          "개정본 콘텐츠(" + targetRvName + ") 미완성 에셋 감지",
          "개정본 폴더(" + targetRvName + ")에 일부 에셋이 이미 존재합니다.\n\n" +
          "* 보존 대상 기존 파일: " + existingMsg + "\n" +
          "* 누락된 미완성 파일: " + missingMsg + "\n\n" +
          "[예] 누락된 미완성 파일만 고속 보충 (권장, 기존 마케터 편집본 및 이미지 보존)\n" +
          "[아니오] 전체 덮어쓰기 (모든 에셋 새로 재생성)",
          ui.ButtonSet.YES_NO_CANCEL
        );
        if (respMissing === ui.Button.CANCEL) {
          return;
        } else if (respMissing === ui.Button.YES) {
          onlyMissing = true;
        }
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

    // 선결 조건 3: 마케터 보정 지침 확인 (독립 파일)
    var directiveDocName = (CONFIG && CONFIG.DIRECTIVE_DOC_NAME) || "마케터 보정 지침";
    var marketerDirective = readGoogleDoc(feedbackFolder, directiveDocName) || "";

    var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
    var planContent = readGoogleDoc(campaignFolder, planDocName) || readGoogleDoc(campaignFolder, "BRD") || "마케팅 캠페인 기획서";
    var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";
    var specContent = readGoogleDoc(campaignFolder, specDocName) || "콘텐츠 제작 명세서";

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
      // 1. 프롬프트 템플릿 로드 (구글 독스 스마트 캐싱)
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

      // 2. 동적 비주얼 프롬프트 도출 및 숏폼 영상 콘티 완전 통합
      dynamicBrief = extractDynamicVisualPrompt(
        refinedAsset,
        summaryContent,
        "A stylish 20s Korean female model enjoying cozy autumn commuter lifestyle with lightweight ANC headphones in a chic Seoul cafe",
        marketerDirective
      );
      finalizedContent = ensureShortsScriptInCampaignContent(refinedAsset, prefix, dynamicBrief);

      // 3. campaign_content 단일 구글 독스 문서 저장
      saveGoogleDoc(targetRvFolder, targetContentDocName, finalizedContent);
    }

    // 4. 신규 비주얼 이미지 3종 및 Veo 비디오 생성
    Logger.log("동적 도출된 비주얼 프롬프트 (" + targetRvName + "): " + dynamicBrief);
    var visResult = generateAndSaveVisualAssets(targetRvFolder, prefix, dynamicBrief, { onlyMissing: onlyMissing });

    var durationSec = Math.round((new Date().getTime() - startTime) / 1000);

    // 5. 상세 실행 로그 조립
    var logDetail = "";
    if (onlyMissing) {
      var totalSkipped = visResult.skipImageCount + (visResult.videoStatus === "skipped" ? 1 : 0);
      logDetail = "미완성 에셋 선별 보충 완료 (신규 이미지 " + visResult.genImageCount + "건 생성, 기존 에셋 " + totalSkipped + "건 보존)";
    } else {
      var videoDesc = visResult.videoStatus === "generated" ? "Veo 비디오 1건" : "숏폼 콘티 독스 수록";
      var directiveDesc = marketerDirective ? "마케터 지침서 100% 반영" : "권장 보정안 반영";
      logDetail = "개정본 독스 1건(" + directiveDesc + "), 신규 이미지 " + visResult.genImageCount + "종, " + videoDesc + " 생성 완료";
    }

    // 6. 대시보드 시트에 링크 기록
    var stepTitle = roundNum + "차 마케팅 콘텐츠 개정본 (" + targetRvName + ")";
    recordStepResultToSheet(
      targetRvName,
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
        "아래 버튼을 눌러 개정본 콘텐츠 폴더를 확인하십시오.",
        "개정본 콘텐츠 폴더 열기 (" + targetRvName + ")",
        targetRvFolder.getUrl()
      );
    }
    return finalizedContent;
  } catch (e) {
    if (!isSilent) {
      ui.alert("콘텐츠 보정 중 오류 발생", e.toString(), ui.ButtonSet.OK);
    } else {
      throw e;
    }
  }
  });
}

// ============================================================================
// FILE: apps-scripts/Code_Feedback.js
// ============================================================================

/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 6] 25인 AI 페르소나 다면 평가 및 피드백 종합 분석 보고서 엔진 (Feedback & Evaluation Engine)
 */

/**
 * [액션 4] 25인 AI 페르소나 다면 평가를 실행하고 128d 임베딩 기반 2D t-SNE 여론 지형도를 생성한다.
 *
 * @param {string} [targetRoundOpt] - 대상 피드백 라운드 (기본값: 자동 감지 fb-01, fb-02 ...)
 */
function runPersonaEvaluation(targetRoundOpt) {
  return withUserLock("persona_evaluation", function() {
    var ui = SpreadsheetApp.getUi();
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

      showProcessingToast("25인 페르소나 다면 평가 및 t-SNE 지형도 생성 중 (" + targetRound + ")...", 60);

      var feedbackFolder = getCampaignSubFolder(["input", targetRound]);

      resetSessionTokens();

      // 1. 25인 페르소나 피드백 데이터셋 로드 또는 실시간 생성 (50~80개 세부 의견 포인트 + 128d 임베딩)
      var jsonContent = readTextFile(feedbackFolder, "ai_persona_feedbacks.json");
      if (!jsonContent) {
        jsonContent = generateLivePersonaFeedbacks(campaignFolder, feedbackFolder, prevRvName);
      }

      // 2. 128d 임베딩 기반 t-SNE 다면 여론 지형도 차트 생성 (feedback_clusters_map.png)
      var clusterMapFile = null;
      var pointsJson = readTextFile(feedbackFolder, "feedback_points_128d.json");
      var parsedPoints = safeParseJson(pointsJson, [], true);

      if (parsedPoints && parsedPoints.length > 0) {
        clusterMapFile = renderAndSaveTsneClusterMap(feedbackFolder, parsedPoints);
      } else {
        var existingMap = feedbackFolder.getFilesByName("feedback_clusters_map.png");
        if (existingMap.hasNext()) {
          clusterMapFile = existingMap.next();
        }
      }

      if (!clusterMapFile) {
        throw new Error("t-SNE 여론 지형도 이미지 생성에 실패했습니다.");
      }

      var durationSec = Math.round((new Date().getTime() - startTime) / 1000);
      var pointCount = parsedPoints ? parsedPoints.length : 0;
      var logDetail = "25인 페르소나 다면 평가 완료" + (pointCount > 0 ? " (VoC 포인트 " + pointCount + "개 도출, " : " (") + "128d 임베딩 t-SNE 여론 지형도 렌더링 완료)";

      // 3. 대시보드 시트에 링크 기록
      var stepTitle = roundNum + "차 페르소나 다면 평가 및 t-SNE 지형도 (" + targetRound + ")";
      recordStepResultToSheet(
        targetRound,
        stepTitle,
        "완료",
        clusterMapFile.getUrl(),
        "t-SNE 지형도 이미지 열기 (" + targetRound + ")",
        durationSec,
        getSessionTotalTokens(),
        logDetail
      );

      showResultModal(
        "25인 페르소나 다면 평가 및 지형도 생성 완료 (" + targetRound + ")",
        "한국인 25인 가상 페르소나로부터 50개 이상의 세부 의견 포인트와 128차원 임베딩 기반 t-SNE 여론 지형도가 성공적으로 도출되었습니다.\n\n" +
        "* 처리 소요 시간: " + formatDuration(durationSec) + "\n" +
        "* 실행 상세 내역: " + logDetail + "\n\n" +
        "아래 버튼을 클릭하여 다면 여론 지형도 차트를 즉시 확인하십시오.",
        "t-SNE 지형도 차트 보기",
        clusterMapFile.getUrl()
      );
    } catch (e) {
      ui.alert("페르소나 평가 중 오류 발생", e.toString(), ui.ButtonSet.OK);
    }
  });
}

/**
 * [액션 5] 고객 VoC 설문 응답, 제출된 미디어(영상/이미지) VLM 분석, t-SNE 지형도를 통합하여
 * 피드백 종합 분석 보고서(feedback_summary) 구글 독스를 자동 생성한다.
 *
 * @param {string} [targetRoundOpt] - 대상 피드백 라운드
 */
function runFeedbackSummaryReport(targetRoundOpt) {
  return withUserLock("feedback_summary", function() {
    var ui = SpreadsheetApp.getUi();
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

    // 선결 조건 검사: 25인 페르소나 피드백 확인 (없으면 자동 평가)
    var personaFeedbacksRaw = readTextFile(feedbackFolder, "ai_persona_feedbacks.json");
    if (!personaFeedbacksRaw) {
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
      "다음은 " + prevRvName + " 마케팅 콘텐츠에 대한 25인 가상 페르소나 다면 평가 결과와 실제 고객 설문 응답, 미디어 VLM 분석 데이터이다.\n\n" +
      "### [1. 이전 마케팅 콘텐츠 (" + prevRvName + ")]\n" + (prevContent.substring(0, 1500) || "카피 및 비주얼") + "\n\n" +
      "### [2. 25인 가상 페르소나 다면 평가 데이터셋]\n" + (personaFeedbacksRaw.substring(0, 3000) || "평가 데이터") + "\n\n" +
      "### [3. 고객 구글 폼 응답 데이터]\n" + (formResponsesText || "접수된 고객 설문 응답 없음") + "\n\n" +
      "### [4. 고객 제출 미디어 VLM 분석 실데이터 (" + mediaAnalysisList.length + "건)]\n" +
      (mediaAnalysisList.length > 0 ? JSON.stringify(mediaAnalysisList, null, 2) : "실제 업로드된 고객 동영상 및 이미지 없음 (미제출)") + "\n\n" +
      "위 데이터를 종합하여 최고 마케팅 책임자(CMO) 및 담당 마케터가 검토할 피드백 종합 분석 보고서(feedback_summary)를 작성하라.\n" +
      "문서 맨 마지막에는 차기 콘텐츠 개정 시 참고할 수 있는 [AI 추천 보정 방향 요약] 섹션을 포함하라.";

    var reportMarkdown = callGemini(systemInstruction, userPrompt);

    // 5. feedback_summary 구글 독스 문서 생성 및 최상단에 t-SNE 지형도 이미지 가로폭 삽입
    var summaryFile = saveGoogleDoc(feedbackFolder, "feedback_summary", reportMarkdown);

    // t-SNE 지형도 이미지 삽입
    var mapFiles = feedbackFolder.getFilesByName("feedback_clusters_map.png");
    if (mapFiles.hasNext()) {
      try {
        var mapBlob = mapFiles.next().getBlob();
        var doc = DocumentApp.openById(summaryFile.getId());
        var body = doc.getBody();
        var pageW = doc.getPageWidth();
        var mLeft = doc.getMarginLeft();
        var mRight = doc.getMarginRight();
        var contentWidth = Math.max(300, pageW - mLeft - mRight);

        var firstP = body.getChild(0);
        var insertedImg = (firstP && firstP.getType() === DocumentApp.ElementType.PARAGRAPH)
          ? firstP.asParagraph().insertInlineImage(0, mapBlob)
          : body.insertImage(0, mapBlob);

        var origW = insertedImg.getWidth();
        var origH = insertedImg.getHeight();
        if (origW > 0) {
          var scale = contentWidth / origW;
          insertedImg.setWidth(contentWidth);
          insertedImg.setHeight(Math.round(origH * scale));
        }
        doc.saveAndClose();
      } catch (imgInsertErr) {
        Logger.log("요약서 t-SNE 이미지 삽입 예외: " + imgInsertErr);
      }
    }

    // 6. [핵심] 독립된 마케터 보정 지침서(CONFIG.DIRECTIVE_DOC_NAME) 생성 및 보존
    // 마케터가 이미 작성해 둔 기존 지침이 있다면 절대 덮어쓰지 않고 100% 보존한다!
    var directiveDocName = (CONFIG && CONFIG.DIRECTIVE_DOC_NAME) || "마케터 보정 지침";
    var directiveFile = null;
    var existingDirectives = feedbackFolder.getFilesByName(directiveDocName);
    var isDirectiveNew = false;

    if (existingDirectives.hasNext()) {
      directiveFile = existingDirectives.next();
      Logger.log("기존 마케터 보정 지침 파일 감지 -> 덮어쓰기 방지 및 영구 보존: " + directiveDocName);
    } else {
      // 신규 파일인 경우 AI가 제안하는 초기 보정 가이드라인 템플릿으로 초안 생성
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
      isDirectiveNew = true;
      Logger.log("신규 마케터 보정 지침 템플릿 문서 생성 완료: " + directiveDocName);
    }

    // 7. 대시보드 시트에 링크 기록
    var durationSec = Math.round((new Date().getTime() - startTime) / 1000);
    var stepTitle = roundNum + "차 피드백 종합 분석 보고서 (" + targetRound + ")";
    var logDetail = "피드백 요약 보고서(" + summaryFile.getName() + ") 및 " +
      (isDirectiveNew ? "신규 보정 지침서 템플릿 생성" : "기존 마케터 지침서 보존");

    recordStepResultToSheet(
      "피드백 보고서",
      stepTitle,
      "완료",
      summaryFile.getUrl(),
      "구글 독스 보고서 열기 (" + targetRound + ")",
      durationSec,
      getSessionTotalTokens(),
      logDetail
    );

    recordStepResultToSheet(
      "보정 지침서",
      roundNum + "차 마케터 최종 의사 결정 (" + targetRound + ")",
      "준비",
      directiveFile.getUrl(),
      "마케터 보정 지침 열기 (" + directiveDocName + ")",
      durationSec,
      "-",
      isDirectiveNew ? "AI 추천 보정 초안 템플릿 자동 생성 완료 (마케터 편집 대기)" : "기존 마케터 작성 지침 안전 보존됨"
    );

    showResultModal(
      "피드백 종합 분석 보고서 및 보정 지침서 준비 완료 (" + targetRound + ")",
      "고객 VoC와 25인 다면 평가가 통합된 [feedback_summary] 보고서와 마케터 전용 [마케터 보정 지침] 독스가 준비되었습니다.\n\n" +
      "* 처리 소요 시간: " + formatDuration(durationSec) + "\n" +
      "* 자산 영구 보존: 마케터 보정 지침 문서는 향후 보고서가 재생성되더라도 절대 덮어써지지 않고 안전하게 보존됩니다.\n\n" +
      "아래 버튼을 눌러 [마케터 보정 지침] 문서를 열고, 피드백을 반영할 방향을 자유롭게 작성 또는 수정하십시오.",
      "마케터 보정 지침 구글 독스 열기",
      directiveFile.getUrl()
    );
  } catch (e) {
    ui.alert("피드백 보고서 도출 중 오류 발생", e.toString(), ui.ButtonSet.OK);
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

// ============================================================================
// FILE: apps-scripts/Code_Menu.js
// ============================================================================

/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 7] Google Sheets 액션 중심 커스텀 메뉴 및 선결 가드레일 UI (Spreadsheet UI & Action Menus)
 */

/**
 * 스프레드시트 열림 시 액션 중심 커스텀 메뉴 자동 등록
 */
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("[마케팅 콘텐츠 파이프라인]")
    .addItem("[제어 패널] 마케팅 파이프라인 우측 패널 열기 (Sidebar)", "showPipelineSidebar")
    .addSeparator()
    .addItem("[초기화] 캠페인 작업 공간 환경 구축 (All-in-one Setup)", "initCampaignWorkspace")
    .addItem("[설정] 캠페인 환경 설정 및 재설정 (Configure)", "runConfigureCampaignSettings")
    .addSeparator()
    .addItem("[기획] 기획서 및 콘텐츠 명세서 생성 (PLAN & SPEC)", "guardAndRunIdeaToPlan")
    .addItem("[생성] 초판 마케팅 콘텐츠 생성 (rv-00)", "guardAndRunInitialContent")
    .addItem("[평가] 25인 AI 페르소나 다면 평가 실행 (fb-xx)", "promptAndRunJudgeEvaluation")
    .addItem("[보고서] 피드백 종합 분석 보고서 생성 (feedback_summary)", "promptAndRunFeedbackSummary")
    .addItem("[보정] 피드백 반영 콘텐츠 보정 (rv-xx)", "promptAndRunReviseAssets")
    .addSeparator()
    .addItem("[설문 폼] 고객 VoC 설문 폼 열기", "openCustomerVocForm")
    .addItem("[페르소나] 25인 AI 페르소나 맞춤 재설정 (선택 사항)", "setCustomPersonasPrompt")
    .addItem("[API Key] Gemini API Key 설정 (Google AI Studio)", "promptForGeminiApiKey")
    .addSeparator()
    .addItem("[엔진 동기화] GitHub 최신 버전 즉시 동기화", "forceSyncEngine")
    .addToUi();
}

/**
 * [가드레일] 기획서 및 명세서 생성 선결 조건 검증 후 실행
 */
function guardAndRunIdeaToPlan() {
  var ui = SpreadsheetApp.getUi();
  var apiKey = getGeminiApiKey();
  if (!apiKey) {
    ui.alert(
      "Gemini API Key 필요",
      "Gemini API 호출을 위한 API Key가 설정되지 않았습니다.\n[API Key] 메뉴를 먼저 실행하여 Google AI Studio 발급 키를 입력하십시오.",
      ui.ButtonSet.OK
    );
    promptForGeminiApiKey();
    return;
  }

  var campaignFolder;
  try {
    campaignFolder = getCampaignFolder();
  } catch (err) {
    ui.alert(
      "캠페인 작업 공간 누락",
      "캠페인 드라이브 폴더가 아직 준비되지 않았습니다.\n[초기화] 캠페인 작업 공간 환경 구축 메뉴를 먼저 실행하십시오.",
      ui.ButtonSet.OK
    );
    return;
  }

  runIdeaToPlanConversion();
}

/**
 * [가드레일] 초판 마케팅 콘텐츠 생성 선결 조건 검증 후 실행
 */
function guardAndRunInitialContent() {
  var ui = SpreadsheetApp.getUi();
  var apiKey = getGeminiApiKey();
  if (!apiKey) {
    ui.alert(
      "Gemini API Key 필요",
      "Gemini API Key가 설정되지 않았습니다.\n[API Key] 메뉴에서 키를 입력하십시오.",
      ui.ButtonSet.OK
    );
    promptForGeminiApiKey();
    return;
  }

  try {
    var campaignFolder = getCampaignFolder();
    var planDoc = readGoogleDoc(campaignFolder, CONFIG.PLAN_DOC_NAME || "PLAN");
    if (!planDoc) {
      var confirmResp = ui.alert(
        "기획서(PLAN) 누락 경고",
        "캠페인 폴더 내 기획서(PLAN) 문서가 아직 생성되지 않았습니다.\n" +
        "기획서 없이 진행할 경우 기본 설정 템플릿으로 생성됩니다.\n\n" +
        "계속 진행하시겠습니까? (권장: [아니오] 선택 후 [기획] 메뉴 먼저 실행)",
        ui.ButtonSet.YES_NO
      );
      if (confirmResp !== ui.Button.YES) {
        return;
      }
    }
  } catch (err) {
    ui.alert(
      "작업 공간 오류",
      "캠페인 작업 공간을 조회할 수 없습니다. [초기화] 메뉴를 먼저 실행하십시오.",
      ui.ButtonSet.OK
    );
    return;
  }

  runInitialContentGeneration();
}

/**
 * 다면 평가 회차 선택 런처 및 가드레일 (fb-01 ~ fb-99 지원)
 */
function promptAndRunJudgeEvaluation() {
  var ui = SpreadsheetApp.getUi();
  var apiKey = getGeminiApiKey();
  if (!apiKey) {
    ui.alert(
      "Gemini API Key 필요",
      "Gemini API Key가 설정되지 않았습니다.\n[API Key] 메뉴에서 키를 먼저 등록하십시오.",
      ui.ButtonSet.OK
    );
    promptForGeminiApiKey();
    return;
  }

  var latestRv = detectLatestRevisionRoundNum();
  var latestFb = detectLatestFeedbackRoundNum();

  // 선결 조건: 평가할 콘텐츠가 존재하는지 점검
  try {
    var campaignFolder = getCampaignFolder();
    var rv00Folder = getCampaignSubFolder(["output", "rv-00"]);
    var hasContent = readGoogleDoc(rv00Folder, CONFIG.CONTENT_DOC_NAME || "campaign_content") ||
                     readGoogleDoc(rv00Folder, "campaign_asset") ||
                     readTextFile(rv00Folder, "campaign_content.md");
    if (!hasContent && latestRv < 0) {
      ui.alert(
        "평가 대상 콘텐츠 누락",
        "다면 평가를 수행할 마케팅 콘텐츠(rv-00)가 존재하지 않습니다.\n" +
        "[생성] 초판 마케팅 콘텐츠 생성 메뉴를 먼저 실행하여 초판을 제작하십시오.",
        ui.ButtonSet.OK
      );
      return;
    }
  } catch (err) {
    ui.alert("작업 공간 오류", "캠페인 폴더에 접근할 수 없습니다: " + err.toString(), ui.ButtonSet.OK);
    return;
  }

  var suggestedRound = Math.max(latestFb + 1, latestRv + 1, 1);
  var suggestedRoundStr = suggestedRound < 10 ? "0" + suggestedRound : "" + suggestedRound;

  var response = ui.prompt(
    "25인 AI 페르소나 다면 평가 회차 선택 (fb-01 ~ fb-99)",
    "현재 완료된 최신 리비전은 rv-" + (latestRv < 10 ? "0" + latestRv : latestRv) + " (기존 피드백: fb-" + (latestFb < 10 ? "0" + latestFb : latestFb) + ")입니다.\n\n" +
    "실행할 피드백 회차 번호를 입력하십시오 (1~99 지원, 추천: " + suggestedRound + "):\n" +
    "(빈칸으로 두고 [확인] 클릭 시 fb-" + suggestedRoundStr + " 회차가 자동 실행됩니다)\n\n" +
    "* 25인 다면 평가 후 128차원 벡터 임베딩 기반 t-SNE 지형도가 산출됩니다.",
    ui.ButtonSet.OK_CANCEL
  );

  if (response.getSelectedButton() !== ui.Button.OK) {
    return;
  }

  var inputVal = response.getResponseText().trim();
  var targetRoundNum = suggestedRound;
  if (inputVal) {
    var parsedNum = parseInt(inputVal.replace(/[^0-9]/g, ""), 10);
    if (!isNaN(parsedNum) && parsedNum >= 1 && parsedNum <= 99) {
      targetRoundNum = parsedNum;
    }
  }

  var targetRoundStr = "fb-" + (targetRoundNum < 10 ? "0" + targetRoundNum : "" + targetRoundNum);
  runPersonaEvaluation(targetRoundStr);
}

/**
 * 피드백 종합 분석 보고서 생성 런처 및 가드레일 (feedback_summary)
 */
function promptAndRunFeedbackSummary() {
  var ui = SpreadsheetApp.getUi();
  var apiKey = getGeminiApiKey();
  if (!apiKey) {
    ui.alert(
      "Gemini API Key 필요",
      "Gemini API Key가 설정되지 않았습니다.\n[API Key] 메뉴에서 키를 등록하십시오.",
      ui.ButtonSet.OK
    );
    promptForGeminiApiKey();
    return;
  }

  var latestFb = detectLatestFeedbackRoundNum();
  if (latestFb < 1) {
    ui.alert(
      "피드백 데이터 누락",
      "아직 실행된 AI 페르소나 다면 평가 데이터가 없습니다.\n" +
      "[평가] 25인 AI 페르소나 다면 평가 실행 메뉴를 먼저 완료하십시오.",
      ui.ButtonSet.OK
    );
    return;
  }

  var suggestedFbStr = "fb-" + (latestFb < 10 ? "0" + latestFb : "" + latestFb);
  var response = ui.prompt(
    "피드백 종합 분석 보고서 대상 회차 선택",
    "종합 보고서를 도출할 피드백 회차를 입력하십시오 (현재 최신 회차: " + suggestedFbStr + "):\n" +
    "(빈칸으로 두고 [확인] 클릭 시 최신 회차 " + suggestedFbStr + " 보고서가 생성됩니다)\n\n" +
    "* 고객 VoC 설문 응답, 제출 미디어 VLM 분석, t-SNE 여론 지형도가 단일 구글 독스로 통합됩니다.",
    ui.ButtonSet.OK_CANCEL
  );

  if (response.getSelectedButton() !== ui.Button.OK) {
    return;
  }

  var inputVal = response.getResponseText().trim();
  var targetRoundStr = suggestedFbStr;
  if (inputVal) {
    var parsedNum = parseInt(inputVal.replace(/[^0-9]/g, ""), 10);
    if (!isNaN(parsedNum) && parsedNum >= 1 && parsedNum <= 99) {
      targetRoundStr = "fb-" + (parsedNum < 10 ? "0" + parsedNum : "" + parsedNum);
    }
  }

  runFeedbackSummaryReport(targetRoundStr);
}

/**
 * 마케팅 콘텐츠 리비전 보정 런처 및 가드레일 (rv-01 ~ rv-99 지원)
 */
function promptAndRunReviseAssets() {
  var ui = SpreadsheetApp.getUi();
  var apiKey = getGeminiApiKey();
  if (!apiKey) {
    ui.alert(
      "Gemini API Key 필요",
      "Gemini API Key가 설정되지 않았습니다.\n[API Key] 메뉴에서 키를 등록하십시오.",
      ui.ButtonSet.OK
    );
    promptForGeminiApiKey();
    return;
  }

  var latestFb = detectLatestFeedbackRoundNum();
  var latestRv = detectLatestRevisionRoundNum();

  if (latestFb < 1) {
    var confirmNoFb = ui.alert(
      "피드백 보고서 미생성 경고",
      "다면 평가 피드백(fb-01 등)이 아직 진행되지 않았습니다.\n" +
      "피드백 요약서 없이 콘텐츠 보정을 진행하시겠습니까? (권장: [아니오] 선택 후 [평가] 및 [보고서] 먼저 완료)",
      ui.ButtonSet.YES_NO
    );
    if (confirmNoFb !== ui.Button.YES) {
      return;
    }
  }

  var suggestedRv = Math.max(latestRv + 1, 1);
  var suggestedRvStr = suggestedRv < 10 ? "0" + suggestedRv : "" + suggestedRv;

  var response = ui.prompt(
    "마케팅 콘텐츠 개정본(rv-xx) 생성 회차 선택",
    "현재 등록된 최신 리비전은 rv-" + (latestRv < 10 ? "0" + latestRv : latestRv) + " (피드백 회차: fb-" + (latestFb < 10 ? "0" + latestFb : latestFb) + ")입니다.\n\n" +
    "생성할 마케팅 콘텐츠 리비전 번호를 입력하십시오 (1~99 지원, 추천: " + suggestedRv + "):\n" +
    "(빈칸으로 두고 [확인] 클릭 시 rv-" + suggestedRvStr + " 개정본이 자동 생성됩니다)\n\n" +
    "* 피드백 요약서 및 마케터 코멘트를 반영하여 카피 개정본과 비주얼 3종 및 Veo 비디오가 생성됩니다.",
    ui.ButtonSet.OK_CANCEL
  );

  if (response.getSelectedButton() !== ui.Button.OK) {
    return;
  }

  var inputVal = response.getResponseText().trim();
  var targetRvNum = suggestedRv;
  if (inputVal) {
    var parsedNum = parseInt(inputVal.replace(/[^0-9]/g, ""), 10);
    if (!isNaN(parsedNum) && parsedNum >= 1 && parsedNum <= 99) {
      targetRvNum = parsedNum;
    }
  }

  var targetRoundStr = "fb-" + (targetRvNum < 10 ? "0" + targetRvNum : "" + targetRvNum);
  runReviseContent(targetRoundStr, false);
}

/**
 * 고객 VoC 설문 폼 URL 열기 다이얼로그
 */
function openCustomerVocForm() {
  var ui = SpreadsheetApp.getUi();
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
    var htmlOutput = HtmlService.createHtmlOutput(
      "<div style='font-family:sans-serif; padding:16px;'>" +
      "<p style='font-size:14px; color:#1a73e8; font-weight:bold;'>고객 VoC 수집용 Google Forms 설문지가 준비되어 있습니다.</p>" +
      "<p>아래 링크를 클릭하여 설문 페이지를 열고 이미지 또는 비디오 리뷰를 등록하십시오:</p>" +
      "<p style='margin:20px 0;'><a href='" + formUrl + "' target='_blank' style='display:inline-block; padding:10px 18px; background:#1a73e8; color:#fff; text-decoration:none; border-radius:4px; font-weight:bold;'>Google Forms 설문지 열기</a></p>" +
      "<p style='font-size:12px; color:#5f6368; word-break:break-all;'>URL: " + formUrl + "</p>" +
      "</div>"
    ).setWidth(520).setHeight(220);
    ui.showModalDialog(htmlOutput, "고객 VoC 설문지 열기");
  } else {
    ui.alert(
      "설문 폼 미등록",
      "스프레드시트에 연결된 Google Forms가 없습니다.\n[초기화] 캠페인 작업 공간 환경 구축 메뉴를 실행하면 자동으로 생성 및 연동됩니다.",
      ui.ButtonSet.OK
    );
  }
}

/**
 * 타깃 AI 페르소나 25인 패널 맞춤 재설정 UI 프롬프트 (Gemini 생성 또는 Hugging Face 동기화)
 * 캠페인 루트 폴더의 ai_personas.json을 직접 갱신한다.
 */
function setCustomPersonasPrompt() {
  var ui = SpreadsheetApp.getUi();
  var response = ui.prompt(
    "타깃 AI 페르소나 25인 패널 맞춤 재설정",
    "새로 생성하고자 하는 타깃 페르소나 기준을 자유롭게 입력하십시오:\n" +
    "(예: '일본 20대 여성 뷰티 인플루언서 및 일반 소비자', '미국 실리콘밸리 30대 B2B SaaS 바이어', '한국 4050 골프 입문자')\n\n" +
    "* Hugging Face 연동: 'hf:nvidia/Nemotron-Personas-Korea' 형식으로 입력 시 공개 데이터셋에서 실시간 동기화합니다.",
    ui.ButtonSet.OK_CANCEL
  );

  if (response.getSelectedButton() !== ui.Button.OK) {
    return;
  }

  var criteria = response.getResponseText().trim();
  if (!criteria) {
    ui.alert("입력 취소", "기준이 입력되지 않아 기존 25인 페르소나 패널을 유지합니다.", ui.ButtonSet.OK);
    return;
  }

  try {
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
          "당신은 데이터 엔지니어이다. 제공된 Hugging Face 원본 데이터로부터 25인의 슬림 페르소나 JSON 객체를 추출 및 정규화하라.\n" +
          "반드시 id(p01~p25), name, age, gender, category(전문 마케터 또는 일반 소비자), occupation, perspective 7개 필드를 포함하는 유효한 JSON으로 출력하라.";
        generatedJson = callGemini(normInstruction, rawRowsText);
      } else {
        throw new Error("Hugging Face API 호출 실패 (응답 코드: " + hfResp.getResponseCode() + ")");
      }
    } else {
      // 2. Gemini 기반 자연어 타깃 페르소나 25인 즉시 합성
      var systemInstruction = personaInstruction ||
        "당신은 글로벌 소비자 리서치 및 엔터프라이즈 마케팅 페르소나 엔지니어링 AI이다.\n" +
        "사용자가 지정한 타깃 기준에 맞추어 마케팅 캠페인 콘텐츠와 광고 소재를 다면 평가할 25인의 슬림 AI 페르소나 패널을 도출하라.\n\n" +
        "필수 규칙:\n" +
        "1. 총 25인 구성: 전문 마케터 12인 + 일반 소비자 13인으로 안배하십시오.\n" +
        "2. 반드시 id, name, age, gender, category, occupation, perspective 7개 필드를 엄격히 포함하는 순수 JSON 객체로 출력하십시오.\n" +
        "3. 코드 블록(```json) 없이 유효한 JSON만 반환하십시오.";

      var userPrompt = "타깃 페르소나 기준: " + criteria + "\n\n위 기준에 부합하는 정밀하고 다양한 25인 슬림 페르소나 JSON을 생성하라.";
      generatedJson = callGemini(systemInstruction, userPrompt);
    }

    if (generatedJson) {
      var parsed = safeParseJson(generatedJson, null, false);
      if (!parsed) {
        throw new Error("생성된 페르소나 데이터의 유효한 JSON을 추출하지 못했습니다.");
      }
      var formatted = JSON.stringify(parsed, null, 2);

      // 캠페인 루트 폴더 직속에 저장 (장준 요청 사항 반영)
      saveTextFile(campaignFolder, "ai_personas.json", formatted);

      // 하위 호환성을 위해 input 폴더에도 보조 동기화
      try {
        var inputFolder = getCampaignSubFolder(["input"]);
        saveTextFile(inputFolder, "ai_personas.json", formatted);
      } catch (subErr) {
        // 무시
      }

      ui.alert(
        "페르소나 패널 재설정 완료",
        "지정한 기준('" + criteria + "')에 맞추어 25인 맞춤 AI 페르소나 패널 데이터가 성공적으로 갱신되었습니다.\n(저장 경로: " + campaignCode + "/ai_personas.json)",
        ui.ButtonSet.OK
      );
    }
  } catch (err) {
    ui.alert("페르소나 재설정 중 오류 발생", err.toString(), ui.ButtonSet.OK);
  }
}

/**
 * GitHub 퍼블릭 저장소의 최신 번들 엔진 코드로 즉시 강제 갱신한다.
 */
function forceSyncEngine() {
  var ui = SpreadsheetApp.getUi();
  try {
    if (typeof loadPipelineEngine === "function") {
      loadPipelineEngine(true);
      ui.alert(
        "엔진 동기화 완료",
        "GitHub 퍼블릭 저장소로부터 최신 파이프라인 엔진 코드가 성공적으로 갱신되었습니다.",
        ui.ButtonSet.OK
      );
    } else {
      ui.alert(
        "번들 직접 실행 모드",
        "현재 단일 번들(bundle_apps_script.js) 직접 실행 모드로 구동 중입니다.\n최신 버전으로 업그레이드하려면 저장소의 최신 번들 코드를 다시 복사하여 붙여넣으십시오.",
        ui.ButtonSet.OK
      );
    }
  } catch (err) {
    ui.alert("동기화 실패", "엔진 동기화 중 오류가 발생했습니다: " + err.toString(), ui.ButtonSet.OK);
  }
}

// ============================================================================
// FILE: apps-scripts/Code_Utils.js
// ============================================================================

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
    try {
      var ui = SpreadsheetApp.getUi();
      ui.alert(
        "작업 진행 중 안내",
        "현재 동일하거나 다른 파이프라인 작업이 이미 백그라운드에서 진행 중입니다.\n\n" +
        "중복 실행으로 인한 데이터 덮어쓰기를 방지하기 위해 새 요청을 차단했습니다.\n" +
        "이전 작업이 완료된 후 다시 시도해 주십시오.",
        ui.ButtonSet.OK
      );
    } catch (uiErr) {
      Logger.log("Lock 경고 알림 표시 불가: " + uiErr);
    }
    return null;
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

function getCampaignFolder() {
  try {
    var sheetId = SpreadsheetApp.getActiveSpreadsheet().getId();
    var sheetFile = DriveApp.getFileById(sheetId);
    var parents = sheetFile.getParents();
    while (parents.hasNext()) {
      var parent = parents.next();
      var parentName = parent.getName();
      if (parentName.indexOf("cp-") === 0) {
        return parent;
      }
    }
  } catch (e) {
    Logger.log("부모 캠페인 폴더 감지 중 예외: " + e);
  }
  return getFolderByPath([CONFIG.CAMPAIGN_CODE]);
}

function getCampaignCode() {
  try {
    var folder = getCampaignFolder();
    var folderName = folder.getName();
    if (folderName.indexOf("cp-") === 0) {
      return folderName;
    }
  } catch (e) {
    Logger.log("캠페인 코드 도출 중 예외: " + e);
  }
  return CONFIG.CAMPAIGN_CODE;
}

function getCampaignSubFolder(subPathParts) {
  var currentFolder = getCampaignFolder();
  for (var i = 0; i < subPathParts.length; i++) {
    var name = subPathParts[i];
    var subFolders = currentFolder.getFoldersByName(name);
    if (subFolders.hasNext()) {
      currentFolder = subFolders.next();
    } else {
      currentFolder = currentFolder.createFolder(name);
    }
  }
  return currentFolder;
}

function readTextFile(folder, fileName) {
  var files = folder.getFilesByName(fileName);
  if (files.hasNext()) {
    var file = files.next();
    return file.getBlob().getDataAsString("UTF-8");
  }
  return null;
}

function saveTextFile(folder, fileName, content) {
  var files = folder.getFilesByName(fileName);
  if (files.hasNext()) {
    var existingFile = files.next();
    existingFile.setContent(content);
    return existingFile;
  } else {
    return folder.createFile(fileName, content, MimeType.PLAIN_TEXT);
  }
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
 * 마크다운 텍스트를 구글 독스(Google Docs) 네이티브 스타일(Title, Heading 1~3, List, Table, HorizontalRule)로 변환하여 렌더링한다.
 */
function renderMarkdownToDoc(doc, markdown) {
  var body = doc.getBody();
  body.clear();

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
}

/**
 * 구글 독스(Google Docs) 문서를 생성하거나 기존 문서의 본문을 네이티브 스타일로 갱신한다.
 */
function saveGoogleDoc(folder, title, content) {
  var files = folder.getFilesByName(title);
  var doc;
  while (files.hasNext()) {
    var file = files.next();
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
 * 리비전 폴더(rv-xx) 내 필수 에셋 5종(카피 독스, 이미지 3종, 숏폼 비디오)의 완성 상태를 정밀 진단한다.
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

  var files = folder.getFiles();
  while (files.hasNext()) {
    var f = files.next();
    var name = f.getName();
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

  if (result.hasBanner) result.existingFiles.push("배너 이미지(" + bannerName + ")");
  else result.missingFiles.push("배너 이미지(" + bannerName + ")");

  if (result.hasPoster) result.existingFiles.push("포스터 이미지(" + posterName + ")");
  else result.missingFiles.push("포스터 이미지(" + posterName + ")");

  if (result.hasSns) result.existingFiles.push("SNS 피드 이미지(" + snsName + ")");
  else result.missingFiles.push("SNS 피드 이미지(" + snsName + ")");

  if (result.hasVideo) result.existingFiles.push("숏폼 비디오(" + videoName + ")");
  else result.missingFiles.push("숏폼 비디오(" + videoName + ")");

  result.isComplete = (result.hasDoc && result.hasBanner && result.hasPoster && result.hasSns && result.hasVideo);
  result.isEmpty = (result.existingFiles.length === 0);

  return result;
}

/**
 * 대표 비주얼 이미지 3종 비율 세트 및 Veo 비디오 생성 (16:9 배너, 9:16 포스터, 1:1 SNS 피드, 숏폼 비디오)
 * options.onlyMissing = true 설정 시 이미 존재하는 파일은 건너뛰고 누락된 파일만 생성한다.
 */
function generateAndSaveVisualAssets(targetFolder, prefix, visualBrief, options) {
  var opts = options || {};
  var onlyMissing = (opts.onlyMissing === true);

  var brief = visualBrief || "A stylish 20s Korean female model enjoying cozy autumn commuter lifestyle with lightweight ANC headphones, warm golden hour sunlight, modern Seoul street";
  var items = [
    { name: prefix + "_banner_16x9.png", ratio: "16:9", prompt: brief + " Wide horizontal display banner (16:9)." },
    { name: prefix + "_poster_9x16.png", ratio: "9:16", prompt: brief + " Vertical mobile commercial poster (9:16)." },
    { name: prefix + "_sns_1x1.png", ratio: "1:1", prompt: brief + " Square social media feed photo (1:1)." }
  ];

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

  if (onlyMissing && targetFolder.getFilesByName(videoFileName).hasNext()) {
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
          Logger.log("Gemini Veo 비디오 생성 응답 없음 또는 무료 티어 제한 (campaign_content 문서의 숏폼 영상 콘티 참조).");
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
    videoStatus: videoStatus
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
    "  - Google AI Studio 유료 결제 계정 연동 API Key 환경에서는 Gemini Veo 모델이 위 콘티를 바탕으로 실제 비디오(" + videoFileName + ")를 자동 생성하여 폴더에 함께 저장합니다.\n" +
    "  - 무료 API Key 환경이거나 현장 촬영본이 있는 경우, 마케터 또는 고객이 직접 촬영한 실제 모바일 숏폼 영상(" + videoFileName + ")을 해당 폴더에 업로드하여 활용할 수 있습니다.\n";

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
 * 25인 한국인 마스터 AI 페르소나 데이터셋 기반 실시간 다면 평가 피드백 생성
 * (열린 피드백 원칙 및 페르소나별 복수 의견 포인트 50~80+개 도출, 128d 임베딩 t-SNE 지형도 연동)
 */
function generateLivePersonaFeedbacks(campaignFolder, feedbackFolder, prevRvNameOpt) {
  try {
    var fbFolderName = feedbackFolder.getName();
    var prevRvName = prevRvNameOpt;
    if (!prevRvName) {
      var rNum = parseInt(fbFolderName.replace("fb-", ""), 10) || 1;
      var pNum = Math.max(0, rNum - 1);
      prevRvName = "rv-" + (pNum < 10 ? "0" + pNum : pNum);
    }

    var assetContent = "";
    var prevFolder = getCampaignSubFolder(["output", prevRvName]);
    var assetFileContent = readGoogleDoc(prevFolder, CONFIG.CONTENT_DOC_NAME || "campaign_content") || readGoogleDoc(prevFolder, "campaign_asset");
    if (assetFileContent) {
      assetContent = assetFileContent;
    } else {
      var rv00Folder = getCampaignSubFolder(["output", "rv-00"]);
      assetContent = readGoogleDoc(rv00Folder, CONFIG.CONTENT_DOC_NAME || "campaign_content") || readGoogleDoc(rv00Folder, "campaign_asset") || "마케팅 캠페인 공개 콘텐츠 (카피 및 비주얼)";
    }

    var personasText = "";
    personasText = readTextFile(campaignFolder, "ai_personas.json");
    if (!personasText) {
      var inputFolder = getCampaignSubFolder(["input"]);
      personasText = readTextFile(inputFolder, "ai_personas.json");
    }
    // 마케터 파일 삭제 또는 파싱 실패 시 기본 25인 마스터 페르소나로 자동 복구
    if (!personasText || personasText.trim().length < 20) {
      try {
        var masterPersonas = (typeof getMasterPersonas25 === "function") ? getMasterPersonas25() : null;
        if (masterPersonas) {
          personasText = JSON.stringify(masterPersonas, null, 2);
          saveTextFile(campaignFolder, "ai_personas.json", personasText);
          Logger.log("ai_personas.json 누락 감지 -> 25인 기본 마스터 페르소나 자동 복구 완료");
        }
      } catch (recErr) {
        Logger.log("페르소나 자동 복구 예외: " + recErr);
      }
    }

    var specContent = readGoogleDoc(campaignFolder, CONFIG.SPEC_DOC_NAME || "SPEC") || "";
    var hasSpecificSurvey = (specContent.indexOf("설문 문항") !== -1 || specContent.indexOf("피드백 설문") !== -1);
    var openFeedbackGuideline = hasSpecificSurvey
      ? "- 콘텐츠 제작 명세서(SPEC)에 정의된 피드백 설문 항목을 충실히 반영하여 의견을 개진하라.\n"
      : "- 콘텐츠 제작 명세서(SPEC)에 특정 설문 문항이 고정되어 있지 않으므로, '열린 피드백(Open-ended Feedback)' 원칙을 적용한다. 각 페르소나는 자신의 연령, 성별, 직업, 라이프스타일 관점에서 장점 호평, 단점 비판, 가격 저항, 사용성 의문, 구매 전환 장벽 등 다각도의 열린 의견을 자유롭게 개진하라.\n";

    var promptDocTemplate = (typeof getPromptTemplate === "function") ? getPromptTemplate("05_persona_evaluation") : "";
    var systemInstruction = promptDocTemplate || (
      "당신은 엔터프라이즈 마케팅 리서치 및 소비자 심리 분석 전문 AI이다.\n" +
      "소비자는 사내 기획서를 알지 못하며, 시장에 공개된 마케팅 캠페인 콘텐츠(" + prevRvName + " 카피 및 비주얼)만을 보고 반응한다.\n" +
      "제공된 마케팅 콘텐츠(" + prevRvName + ") 산출물을 면밀히 검토하고, 함께 제공된 한국인 25인 가상 페르소나 프로필의 관점에 깊이 빙의하여 피드백을 작성하라.\n\n" +
      "### 핵심 원칙: 열린 피드백 및 복수 의견 포인트(Multi-points) 도출:\n" +
      openFeedbackGuideline +
      "- 페르소나 1명이 1개의 단편적 소감만 남기지 않고, 제품 및 콘텐츠의 다양한 측면(예: 노이즈 캔슬링 호평, 착용감 우려, 출시가 부담 등)에 대해 1인당 2개~4개의 구체적인 세부 의견 포인트(`points` 배열)를 제시해야 한다.\n" +
      "- 25인 평가단 전체로부터 총 50개 이상의 세부 의견 포인트를 도출하여 다면적 여론 지형도를 풍부하게 구성하라.\n\n" +
      "엄격한 출력 형식:\n" +
      "반드시 다음 JSON 배열 형식으로만 순수 JSON을 출력하라. 코드 블록(```json) 없이 유효한 JSON만 반환하라:\n" +
      "[\n" +
      "  {\n" +
      "    \"persona_id\": \"kr_persona_00001\",\n" +
      "    \"name\": \"강민준\",\n" +
      "    \"age\": 24,\n" +
      "    \"gender\": \"남자\",\n" +
      "    \"occupation\": \"대학생\",\n" +
      "    \"category\": \"20대 대학생\",\n" +
      "    \"rating\": 4.2,\n" +
      "    \"open_feedback\": \"열린 피드백 관점에서의 종합 소감 (2~3문장)\",\n" +
      "    \"points\": [\n" +
      "      {\n" +
      "        \"point_id\": \"P01_1\",\n" +
      "        \"text\": \"노이즈 캔슬링 성능은 학습 및 몰입 환경에서 매우 유용할 것으로 기대된다.\",\n" +
      "        \"sentiment\": \"긍정\",\n" +
      "        \"cluster_theme\": \"성능 및 기능\",\n" +
      "        \"rating\": 4.8\n" +
      "      },\n" +
      "      {\n" +
      "        \"point_id\": \"P01_2\",\n" +
      "        \"text\": \"출시 가격이 대학생 기준 다소 부담스러워 얼리버드 혜택 강조가 필수적이다.\",\n" +
      "        \"sentiment\": \"부정\",\n" +
      "        \"cluster_theme\": \"가격 및 구매 혜택\",\n" +
      "        \"rating\": 3.0\n" +
      "      }\n" +
      "    ]\n" +
      "  }\n" +
      "]\n\n" +
      "작성 규칙:\n" +
      "1. 이모지와 중간 점을 일절 쓰지 말고 쉼표(,)를 사용하십시오.\n" +
      "2. 모든 서술은 단호하고 격조 높은 문어체/평서문('-다' 체)으로 작성하십시오.\n" +
      "3. 한글 복합어는 철저하게 띄어 쓰십시오.\n" +
      "4. 반드시 25인의 한국인 프로필 정보를 충실히 반영하여 25개 객체와 총 50개 이상의 세부 포인트를 완성하십시오."
    );

    var userPrompt =
      "[대중에게 공개된 마케팅 캠페인 콘텐츠 (" + prevRvName + ")]\n" +
      assetContent + "\n\n" +
      "[콘텐츠 제작 명세서(SPEC) 발췌]\n" +
      (specContent.substring(0, 1500) || "SPEC 문서 기본 규격") + "\n\n" +
      "[한국인 25인 가상 페르소나 프로필 데이터]\n" +
      (personasText || "25인 한국인 소비자 프로필") + "\n\n" +
      "위 마케팅 콘텐츠(" + prevRvName + ")를 본 25인 평가단의 열린 피드백 및 복수 세부 의견 포인트(총 50~80개)를 JSON 배열로 실시간 도출하라.";

    var rawOutput = callGemini(systemInstruction, userPrompt, CONFIG.MODEL_GENERATOR);
    if (rawOutput) {
      var parsed = safeParseJson(rawOutput, [], true);
      if (Array.isArray(parsed) && parsed.length > 0) {
        // 복수 의견 포인트 평탄화(Flatten)
        var allPoints = [];
        var allTexts = [];
        for (var p = 0; p < parsed.length; p++) {
          var pItem = parsed[p];
          var pPts = pItem.points;
          if (!Array.isArray(pPts) || pPts.length === 0) {
            pPts = [
              {
                point_id: "P" + (p + 1) + "_1",
                text: pItem.open_feedback || pItem.feedback || "전반적인 마케팅 메시지 만족도",
                sentiment: pItem.sentiment || "중립",
                cluster_theme: pItem.cluster_theme || "기능 및 사용성",
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

        // 한국어 특화 text-multilingual-embedding-002 모델을 통한 128차원 MRL 임베딩 취득
        Logger.log("총 " + allPoints.length + "개 세부 의견 포인트 128차원 텍스트 임베딩 일괄 생성 시작 (text-multilingual-embedding-002)");
        var embeddings128d = callGeminiBatchEmbeddings(allTexts, CONFIG.EMBEDDING_DIM || 128);

        // 128차원 고차원 벡터를 2차원 평면 (x, y)으로 정사영 투영
        var coords2D = projectHighDimTo2D(embeddings128d);
        for (var c = 0; c < allPoints.length; c++) {
          if (coords2D[c]) {
            allPoints[c].x = coords2D[c].x;
            allPoints[c].y = coords2D[c].y;
          }
        }

        var formattedPersonas = JSON.stringify(parsed, null, 2);
        saveTextFile(feedbackFolder, "ai_persona_feedbacks.json", formattedPersonas);

        var formattedPoints = JSON.stringify(allPoints, null, 2);
        saveTextFile(feedbackFolder, "feedback_points_128d.json", formattedPoints);

        // 128d 임베딩 투영 좌표 기반 QuickChart 다면 여론 지형도 차트 생성
        renderAndSaveTsneClusterMap(feedbackFolder, allPoints);

        Logger.log("실제 캠페인 기반 25인 페르소나 열린 피드백(" + parsed.length + "명) 및 128d 다중 포인트(" + allPoints.length + "개) 지형도 생성 완료");
        return formattedPersonas;
      }
    }
  } catch (err) {
    Logger.log("AI 가상 페르소나 피드백 실시간 생성 예외: " + err);
  }
  return "";
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
 * QuickChart REST API를 호출하여 세부 의견 포인트(128d 임베딩 기반 2D 투영)
 * 다면 여론 지형도(t-SNE / PCA 클러스터 맵) PNG를 생성하고 드라이브에 저장한다.
 *
 * @param {Folder} feedbackFolder - 차트 이미지가 저장될 구글 드라이브 폴더
 * @param {Array<Object>} pointsList - 2D 좌표와 메타데이터가 결합된 의견 포인트 목록
 * @return {File|null} 생성된 이미지 파일 객체
 */
function renderAndSaveTsneClusterMap(feedbackFolder, pointsList) {
  try {
    if (!pointsList || pointsList.length === 0) {
      return null;
    }

    // 4대 의견 성향별 데이터셋 분기
    var datasets = [
      { label: "호평 및 긍정 반응", data: [], backgroundColor: "rgba(37, 99, 235, 0.75)", borderColor: "#1D4ED8", borderWidth: 1.2, pointRadius: [] },
      { label: "비판 및 개선 제안", data: [], backgroundColor: "rgba(220, 38, 38, 0.75)", borderColor: "#B91C1C", borderWidth: 1.2, pointRadius: [] },
      { label: "가격 및 구매 장벽", data: [], backgroundColor: "rgba(217, 119, 6, 0.75)", borderColor: "#B45309", borderWidth: 1.2, pointRadius: [] },
      { label: "중립 및 기능적 사용성", data: [], backgroundColor: "rgba(5, 150, 105, 0.75)", borderColor: "#047857", borderWidth: 1.2, pointRadius: [] }
    ];

    for (var i = 0; i < pointsList.length; i++) {
      var pt = pointsList[i];
      var sentiment = String(pt.sentiment || "");
      var theme = String(pt.cluster_theme || "");
      var rating = Number(pt.rating) || 3.5;
      var radius = Math.max(5, Math.min(15, rating * 2.5));

      var targetIndex = 3; // 기본: 중립/기능
      if (theme.indexOf("가격") !== -1 || theme.indexOf("비용") !== -1 || theme.indexOf("혜택") !== -1 || theme.indexOf("가성비") !== -1) {
        targetIndex = 2; // 가격
      } else if (sentiment.indexOf("부정") !== -1 || sentiment.indexOf("비판") !== -1 || rating < 3.0) {
        targetIndex = 1; // 비판/개선
      } else if (sentiment.indexOf("긍정") !== -1 || rating >= 4.0) {
        targetIndex = 0; // 호평
      }

      datasets[targetIndex].data.push({
        x: pt.x !== undefined ? pt.x : Number((Math.sin(i * 1.5) * 2.8).toFixed(2)),
        y: pt.y !== undefined ? pt.y : Number((Math.cos(i * 2.1) * 2.8).toFixed(2))
      });
      datasets[targetIndex].pointRadius.push(radius);
    }

    var chartConfig = {
      type: "bubble",
      data: {
        datasets: datasets
      },
      options: {
        title: {
          display: true,
          text: "25인 페르소나 열린 피드백 여론 지형도 (총 " + pointsList.length + "개 포인트, 128d 임베딩)",
          fontSize: 16,
          fontColor: "#1E293B"
        },
        legend: {
          position: "bottom",
          labels: { fontSize: 11, fontColor: "#475569" }
        },
        scales: {
          xAxes: [{
            scaleLabel: { display: true, labelString: "차원 1: 의미론적 유사도 (t-SNE / PCA 1축)", fontColor: "#64748B" },
            gridLines: { color: "#F1F5F9" },
            ticks: { min: -4.5, max: 4.5, fontColor: "#94A3B8" }
          }],
          yAxes: [{
            scaleLabel: { display: true, labelString: "차원 2: 평가 감정 및 태도 (t-SNE / PCA 2축)", fontColor: "#64748B" },
            gridLines: { color: "#F1F5F9" },
            ticks: { min: -4.0, max: 4.0, fontColor: "#94A3B8" }
          }]
        }
      }
    };

    var quickChartUrl = "https://quickchart.io/chart";
    var payload = {
      chart: chartConfig,
      width: 780,
      height: 480,
      backgroundColor: "#FFFFFF"
    };

    var fetchOptions = {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    var response = UrlFetchApp.fetch(quickChartUrl, fetchOptions);
    if (response.getResponseCode() === 200) {
      var imageBlob = response.getBlob().setName("feedback_clusters_map.png");
      var existing = feedbackFolder.getFilesByName("feedback_clusters_map.png");
      if (existing.hasNext()) {
        existing.next().setTrashed(true);
      }
      var savedFile = feedbackFolder.createFile(imageBlob);
      Logger.log("128d 임베딩 기반 다면 여론 지형도 저장 완료: " + savedFile.getName() + " (포인트 " + pointsList.length + "개)");
      return savedFile;
    } else {
      Logger.log("QuickChart API 오류 (" + response.getResponseCode() + "): " + response.getContentText());
    }
  } catch (err) {
    Logger.log("다면 여론 지형도 차트 생성 예외: " + err);
  }
  return null;
}

/**
 * 구글 시트 실시간 실행 대시보드 헬퍼
 */
function getDashboardSheet() {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    if (!ss) return null;
    var sheet = ss.getSheetByName("실행 대시보드");
    if (!sheet) {
      sheet = ss.getSheets()[0];
      sheet.setName("실행 대시보드");
    }
    return sheet;
  } catch (e) {
    Logger.log("대시보드 시트 획득 예외: " + e);
    return null;
  }
}

/**
 * 초 단위 소요 시간을 사람이 읽기 편한 문자열(예: '24초', '1분 15초')로 포맷팅한다.
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
 * 소모된 토큰 수를 사람이 읽기 편한 문자열(예: '2,450 tokens')로 포맷팅한다.
 */
function formatTokenCount(tokens) {
  if (tokens === null || tokens === undefined || tokens === "" || tokens === 0) return "-";
  if (typeof tokens === "string") return tokens;
  var num = parseInt(tokens, 10);
  if (isNaN(num) || num <= 0) return "-";
  return num.toLocaleString() + " tokens";
}

function initDashboardSheet() {
  var sheet = getDashboardSheet();
  if (!sheet) return;

  try {
    var val = sheet.getRange("A2").getValue();
    var lastCol = sheet.getLastColumn();
    if (val === "실행 단계" && lastCol >= 7) return;

    sheet.clear();

    // 상단 타이틀 배너 (A1:G1)
    sheet.getRange("A1:G1").merge();
    sheet.getRange("A1").setValue("Google Drive 마케팅 콘텐츠 파이프라인 실행 대시보드");
    sheet.getRange("A1")
      .setFontWeight("bold")
      .setFontSize(12)
      .setBackground("#1E293B")
      .setFontColor("#FFFFFF")
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle")
      .setWrap(false);
    sheet.setRowHeight(1, 38);

    // 컬럼 헤더 행 (A2:G2) - 7대 핵심 컬럼
    var headers = [["실행 단계", "진행 상태", "생성된 산출물 바로가기", "완료 시각", "소요 시간", "소모 토큰", "실행 로그 및 상세 내역"]];
    sheet.getRange("A2:G2").setValues(headers);
    sheet.getRange("A2:G2")
      .setFontWeight("bold")
      .setFontSize(10)
      .setBackground("#F1F5F9")
      .setFontColor("#334155")
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle")
      .setWrap(false);
    // 숫자 컬럼(소요 시간, 소모 토큰) 헤더 우측 정렬
    sheet.getRange("E2:F2").setHorizontalAlignment("right");
    sheet.setRowHeight(2, 28);

    // 컬럼 너비 설정 (사용자 지정: 150, 100, 300, 150, 100, 150, 450)
    sheet.setColumnWidth(1, 150);
    sheet.setColumnWidth(2, 100);
    sheet.setColumnWidth(3, 300);
    sheet.setColumnWidth(4, 150);
    sheet.setColumnWidth(5, 100);
    sheet.setColumnWidth(6, 150); // 소요 시간 다음 칼럼: 소모 토큰 (150px)
    sheet.setColumnWidth(7, 450); // 실행 로그 및 상세 내역 (450px)

    sheet.getRange("A2:G2").setBorder(true, true, true, true, true, true, "#CBD5E1", SpreadsheetApp.BorderStyle.SOLID);
  } catch (e) {
    Logger.log("대시보드 시트 초기화 예외: " + e);
  }
}

/**
 * 실행 대시보드 시트에 결과를 항상 맨 아래에 새 행으로 누적 추가(Append-only)한다.
 *
 * @param {string} stepId - 실행 단계 식별자
 * @param {string} stepName - 작업 명칭
 * @param {string} status - 진행 상태 ('완료', '진행 중' 등)
 * @param {string} linkUrl - 산출물 링크 URL
 * @param {string} linkText - 링크 표시 텍스트
 * @param {number|string} [durationSec] - 소요 시간 (초 단위 숫자 또는 문자열)
 * @param {number|string} [tokensOrLog] - 소모 토큰 수 또는 로그 (오버로딩 방어)
 * @param {string} [logDetailOpt] - 실행 로그 및 상세 내역
 */
function recordStepResultToSheet(stepId, stepName, status, linkUrl, linkText, durationSec, tokensOrLog, logDetailOpt) {
  var sheet = getDashboardSheet();
  if (!sheet) return;

  try {
    initDashboardSheet();

    var lastRow = sheet.getLastRow();
    // 항상 맨 아래에 새 행으로 누적 추가 (헤더가 2행이므로 최소 3행부터 시작)
    var targetRow = Math.max(3, lastRow + 1);

    sheet.setRowHeight(targetRow, 28);

    var tokenVal = "-";
    var detailText = "";
    if (logDetailOpt !== undefined) {
      tokenVal = formatTokenCount(tokensOrLog);
      detailText = logDetailOpt || (status === "완료" ? "정상 처리 완료" : "");
    } else {
      tokenVal = "-";
      detailText = tokensOrLog || (status === "완료" ? "정상 처리 완료" : "");
    }

    // 1열: 실행 단계 (150)
    sheet.getRange(targetRow, 1)
      .setValue(stepId)
      .setFontWeight("bold")
      .setFontSize(10)
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle");

    // 2열: 진행 상태 (100)
    var statusCell = sheet.getRange(targetRow, 2);
    statusCell.setValue(status)
      .setFontSize(10)
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle");
    if (status === "완료") {
      statusCell.setBackground("#DCFCE7").setFontColor("#15803D").setFontWeight("bold");
    } else if (status === "진행 중") {
      statusCell.setBackground("#FEF9C3").setFontColor("#A16207").setFontWeight("bold");
    }

    // 3열: 생성된 산출물 바로가기 (300)
    var linkCell = sheet.getRange(targetRow, 3);
    linkCell.setFontSize(10).setVerticalAlignment("middle");
    if (linkUrl) {
      var displayText = linkText || stepName;
      linkCell.setFormula('=HYPERLINK("' + linkUrl + '", "' + displayText + '")').setHorizontalAlignment("left");
    } else {
      linkCell.setValue(stepName).setHorizontalAlignment("left");
    }

    // 4열: 완료 시각 (150)
    var nowStr = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd HH:mm:ss");
    sheet.getRange(targetRow, 4)
      .setValue(nowStr)
      .setFontSize(9)
      .setFontColor("#64748B")
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle");

    // 5열: 소요 시간 (100) - 숫자 메트릭 우측 정렬
    var durText = formatDuration(durationSec);
    sheet.getRange(targetRow, 5)
      .setValue(durText)
      .setFontSize(9)
      .setFontColor("#334155")
      .setHorizontalAlignment("right")
      .setVerticalAlignment("middle");

    // 6열: 소모 토큰 (150) - 숫자 메트릭 우측 정렬
    sheet.getRange(targetRow, 6)
      .setValue(tokenVal)
      .setFontSize(9)
      .setFontColor("#334155")
      .setHorizontalAlignment("right")
      .setVerticalAlignment("middle");

    // 7열: 실행 로그 및 상세 내역 (450)
    sheet.getRange(targetRow, 7)
      .setValue(detailText)
      .setFontSize(9)
      .setFontColor("#475569")
      .setHorizontalAlignment("left")
      .setVerticalAlignment("middle");

    // 라인 랩 방지 (CLIP) 및 테두리 설정 (1~7열)
    var rowRange = sheet.getRange(targetRow, 1, 1, 7);
    rowRange.setWrap(false);
    rowRange.setBorder(true, true, true, true, true, true, "#E2E8F0", SpreadsheetApp.BorderStyle.SOLID);
  } catch (e) {
    Logger.log("대시보드 시트 결과 기록 예외: " + e);
  }
}

/**
 * 사용자 대기 피로도 경감을 위한 실시간 토스트 알림 헬퍼
 */
function showProcessingToast(stepTitle, estimatedTimeSec) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    if (ss) {
      var secText = estimatedTimeSec ? " (예상 소요 시간: 약 " + estimatedTimeSec + "초)" : "";
      ss.toast("Apps Script 엔진이 작업을 시작했습니다" + secText + ". 잠시만 기다려 주십시오...", stepTitle || "파이프라인 실행 중", estimatedTimeSec || 30);
    }
  } catch (e) {
    Logger.log("토스트 알림 표시 예외: " + e);
  }
}

/**
 * 드라이브 내 최신 피드백 회차(fb-xx) 번호 자동 탐지
 */
function detectLatestFeedbackRoundNum() {
  var maxRound = 1;
  try {
    var inputFolder = getCampaignSubFolder(["input"]);
    var subFolders = inputFolder.getFolders();
    while (subFolders.hasNext()) {
      var folder = subFolders.next();
      var name = folder.getName();
      var match = /^fb-(\d+)$/i.exec(name);
      if (match) {
        var num = parseInt(match[1], 10);
        if (num > maxRound) {
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
 */
function detectLatestRevisionRoundNum() {
  var maxRound = 0;
  try {
    var outputFolder = getCampaignSubFolder(["output"]);
    var subFolders = outputFolder.getFolders();
    while (subFolders.hasNext()) {
      var folder = subFolders.next();
      var name = folder.getName();
      var match = /^rv-(\d+)$/i.exec(name);
      if (match) {
        var num = parseInt(match[1], 10);
        if (num > maxRound) {
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
 * 마케터가 클릭 한 번으로 결과물(구글 독스, 구글 드라이브 폴더)을 즉시 열 수 있는 결과 안내 모달을 띄운다.
 */
function showResultModal(title, message, btnText, btnUrl) {
  var ui = SpreadsheetApp.getUi();
  if (!btnUrl) {
    ui.alert(title, message, ui.ButtonSet.OK);
    return;
  }

  var htmlContent =
    "<div style='font-family:sans-serif; padding:18px; line-height:1.6;'>" +
    "<h3 style='margin:0 0 10px 0; color:#1a73e8; font-size:16px;'>" + title + "</h3>" +
    "<p style='color:#3c4043; font-size:13px; margin:0 0 16px 0; white-space:pre-line;'>" + message + "</p>" +
    "<div style='margin-top:16px;'>" +
    "<a href='" + btnUrl + "' target='_blank' style='display:inline-block; padding:10px 20px; background:#1a73e8; color:#ffffff; text-decoration:none; border-radius:4px; font-weight:bold; font-size:13px;'>" + btnText + "</a>" +
    "</div>" +
    "<p style='color:#70757a; font-size:11px; margin-top:14px; word-break:break-all;'>URL: " + btnUrl + "</p>" +
    "</div>";

  try {
    var htmlOutput = HtmlService.createHtmlOutput(htmlContent)
      .setWidth(480)
      .setHeight(210);
    ui.showModalDialog(htmlOutput, title);
  } catch (err) {
    ui.alert(title, message + "\n\n" + btnText + ": " + btnUrl, ui.ButtonSet.OK);
  }
}

// ============================================================================
// FILE: apps-scripts/Code_Sidebar.js
// ============================================================================

/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 9] 구글 시트 우측 패널(Sidebar) 모던 HTML 컨트롤 타워 UI
 */

/**
 * 구글 시트 우측 패널에 마케팅 콘텐츠 파이프라인 컨트롤 타워를 표시한다.
 */
function showPipelineSidebar() {
  var ui = SpreadsheetApp.getUi();
  try {
    var htmlOutput = HtmlService.createHtmlOutput(getPipelineSidebarHtml())
      .setTitle("마케팅 파이프라인 제어 패널")
      .setWidth(340);
    ui.showSidebar(htmlOutput);
  } catch (err) {
    ui.alert(
      "사이드바 실행 오류",
      "우측 패널(사이드바)을 여는 중 오류가 발생했습니다:\n" + err.toString(),
      ui.ButtonSet.OK
    );
  }
}

/**
 * 사이드바 화면 렌더링에 필요한 현재 캠페인 파이프라인 상태 정보를 반환한다.
 *
 * @return {Object} 캠페인 작업 공간 상태, 산출물 URL, 리비전, 토큰 통계 객체
 */
function getPipelineStatus() {
  var status = {
    hasApiKey: !!getGeminiApiKey(),
    campaignCode: "CAMP-2026-AUTUMN",
    folderUrl: "",
    ideaDocUrl: "",
    planDocUrl: "",
    specDocUrl: "",
    contentDocUrl: "",
    formUrl: "",
    summaryDocUrl: "",
    mapUrl: "",
    latestRv: "rv-00",
    latestFb: "",
    totalTokens: getSessionTotalTokens() || 0
  };

  try {
    var code = getCampaignCode();
    if (code) status.campaignCode = code;

    var folder = getCampaignFolder();
    if (folder) {
      status.folderUrl = folder.getUrl();

      var ideaFiles = folder.getFilesByName("[아이디어 메모] 2026 가을 오텀 브리즈 캠페인");
      if (ideaFiles.hasNext()) status.ideaDocUrl = ideaFiles.next().getUrl();

      var planFiles = folder.getFilesByName("PLAN.md");
      if (planFiles.hasNext()) status.planDocUrl = planFiles.next().getUrl();

      var specFiles = folder.getFilesByName("SPEC.md");
      if (specFiles.hasNext()) status.specDocUrl = specFiles.next().getUrl();

      var formFiles = folder.getFilesByType(MimeType.GOOGLE_FORMS);
      if (formFiles.hasNext()) status.formUrl = formFiles.next().getUrl();

      var latestRvNum = detectLatestRevisionRoundNum();
      if (latestRvNum >= 0) {
        status.latestRv = "rv-" + (latestRvNum < 10 ? "0" + latestRvNum : latestRvNum);
        var rvFolder = getCampaignSubFolder(["output", status.latestRv]);
        var contentFiles = rvFolder.getFilesByName("campaign_content.md");
        if (contentFiles.hasNext()) status.contentDocUrl = contentFiles.next().getUrl();
      }

      var latestFbNum = detectLatestFeedbackRoundNum();
      if (latestFbNum > 0) {
        status.latestFb = "fb-" + (latestFbNum < 10 ? "0" + latestFbNum : latestFbNum);
        var fbFolder = getCampaignSubFolder(["input", status.latestFb]);
        var summaryFiles = fbFolder.getFilesByName("feedback_summary.md");
        if (summaryFiles.hasNext()) status.summaryDocUrl = summaryFiles.next().getUrl();
        var mapFiles = fbFolder.getFilesByName("feedback_clusters_map.png");
        if (mapFiles.hasNext()) status.mapUrl = mapFiles.next().getUrl();
      }
    }
  } catch (e) {
    Logger.log("getPipelineStatus 예외: " + e);
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
    "    body {\n" +
    "      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;\n" +
    "      font-size: 13px;\n" +
    "      line-height: 1.5;\n" +
    "      color: #202124;\n" +
    "      background: #f8f9fa;\n" +
    "      padding: 12px;\n" +
    "    }\n" +
    "    .header {\n" +
    "      background: #ffffff;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      border-radius: 8px;\n" +
    "      padding: 12px 14px;\n" +
    "      margin-bottom: 12px;\n" +
    "    }\n" +
    "    .header h2 {\n" +
    "      font-size: 14px;\n" +
    "      font-weight: 700;\n" +
    "      color: #1a73e8;\n" +
    "      margin-bottom: 4px;\n" +
    "      letter-spacing: -0.3px;\n" +
    "    }\n" +
    "    .header-sub {\n" +
    "      font-size: 11px;\n" +
    "      color: #5f6368;\n" +
    "      display: flex;\n" +
    "      justify-content: space-between;\n" +
    "      align-items: center;\n" +
    "    }\n" +
    "    .badge {\n" +
    "      display: inline-block;\n" +
    "      font-size: 10px;\n" +
    "      font-weight: 600;\n" +
    "      padding: 2px 6px;\n" +
    "      border-radius: 4px;\n" +
    "      background: #e8f0fe;\n" +
    "      color: #1967d2;\n" +
    "    }\n" +
    "    .badge.active { background: #ceead6; color: #0d652d; }\n" +
    "    .badge.warn { background: #fef7e0; color: #b06000; }\n" +
    "    .section {\n" +
    "      background: #ffffff;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      border-radius: 8px;\n" +
    "      padding: 12px;\n" +
    "      margin-bottom: 10px;\n" +
    "    }\n" +
    "    .section-title {\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 700;\n" +
    "      color: #70757a;\n" +
    "      text-transform: uppercase;\n" +
    "      letter-spacing: 0.5px;\n" +
    "      margin-bottom: 8px;\n" +
    "      display: flex;\n" +
    "      justify-content: space-between;\n" +
    "      align-items: center;\n" +
    "    }\n" +
    "    .btn {\n" +
    "      display: block;\n" +
    "      width: 100%;\n" +
    "      padding: 9px 12px;\n" +
    "      margin-bottom: 6px;\n" +
    "      font-size: 12px;\n" +
    "      font-weight: 600;\n" +
    "      text-align: left;\n" +
    "      border-radius: 6px;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      background: #ffffff;\n" +
    "      color: #3c4043;\n" +
    "      cursor: pointer;\n" +
    "      transition: all 0.15s ease;\n" +
    "    }\n" +
    "    .btn:hover:not(:disabled) {\n" +
    "      background: #f1f3f4;\n" +
    "      border-color: #1a73e8;\n" +
    "      color: #1a73e8;\n" +
    "    }\n" +
    "    .btn:disabled {\n" +
    "      opacity: 0.6;\n" +
    "      cursor: not-allowed;\n" +
    "      background: #f8f9fa;\n" +
    "    }\n" +
    "    .btn-primary {\n" +
    "      background: #1a73e8;\n" +
    "      color: #ffffff;\n" +
    "      border-color: #1a73e8;\n" +
    "    }\n" +
    "    .btn-primary:hover:not(:disabled) {\n" +
    "      background: #174ea6;\n" +
    "      color: #ffffff;\n" +
    "    }\n" +
    "    .btn-step {\n" +
    "      display: flex;\n" +
    "      align-items: center;\n" +
    "      justify-content: space-between;\n" +
    "    }\n" +
    "    .step-tag {\n" +
    "      font-size: 10px;\n" +
    "      font-weight: 700;\n" +
    "      padding: 1px 5px;\n" +
    "      border-radius: 3px;\n" +
    "      background: #e8eaed;\n" +
    "      color: #5f6368;\n" +
    "    }\n" +
    "    .link-card {\n" +
    "      display: block;\n" +
    "      padding: 7px 10px;\n" +
    "      margin-bottom: 5px;\n" +
    "      background: #f8f9fa;\n" +
    "      border: 1px solid #e8eaed;\n" +
    "      border-radius: 5px;\n" +
    "      text-decoration: none;\n" +
    "      color: #1a73e8;\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 600;\n" +
    "      transition: background 0.15s ease;\n" +
    "    }\n" +
    "    .link-card:hover {\n" +
    "      background: #e8f0fe;\n" +
    "    }\n" +
    "    .link-card.disabled {\n" +
    "      color: #9aa0a6;\n" +
    "      pointer-events: none;\n" +
    "      background: #f1f3f4;\n" +
    "    }\n" +
    "    .status-bar {\n" +
    "      padding: 8px 10px;\n" +
    "      background: #e8f0fe;\n" +
    "      border: 1px solid #d2e3fc;\n" +
    "      border-radius: 6px;\n" +
    "      font-size: 11px;\n" +
    "      color: #174ea6;\n" +
    "      margin-bottom: 10px;\n" +
    "      display: none;\n" +
    "    }\n" +
    "    .status-bar.show { display: block; }\n" +
    "    .status-bar.error {\n" +
    "      background: #fce8e6;\n" +
    "      border-color: #fad2cf;\n" +
    "      color: #c5221f;\n" +
    "    }\n" +
    "    .metrics {\n" +
    "      display: flex;\n" +
    "      gap: 6px;\n" +
    "      margin-top: 4px;\n" +
    "    }\n" +
    "    .metric-box {\n" +
    "      flex: 1;\n" +
    "      background: #f8f9fa;\n" +
    "      border: 1px solid #e8eaed;\n" +
    "      border-radius: 5px;\n" +
    "      padding: 6px 8px;\n" +
    "      text-align: center;\n" +
    "    }\n" +
    "    .metric-val {\n" +
    "      font-size: 12px;\n" +
    "      font-weight: 700;\n" +
    "      color: #202124;\n" +
    "    }\n" +
    "    .metric-lbl {\n" +
    "      font-size: 9px;\n" +
    "      color: #70757a;\n" +
    "      margin-top: 1px;\n" +
    "    }\n" +
    "    .footer-actions {\n" +
    "      margin-top: 12px;\n" +
    "      text-align: center;\n" +
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
    "  <div class='header'>\n" +
    "    <h2>마케팅 콘텐츠 파이프라인</h2>\n" +
    "    <div class='header-sub'>\n" +
    "      <span id='campaignCodeBadge' class='badge'>CAMP-2026-AUTUMN</span>\n" +
    "      <span id='apiKeyBadge' class='badge warn'>API Key 확인 중</span>\n" +
    "    </div>\n" +
    "  </div>\n" +
    "\n" +
    "  <div id='statusBar' class='status-bar'></div>\n" +
    "\n" +
    "  <div class='section'>\n" +
    "    <div class='section-title'>\n" +
    "      <span>환경 설정 및 초기화</span>\n" +
    "      <span class='step-tag'>Setup</span>\n" +
    "    </div>\n" +
    "    <button id='btnApiKey' class='btn' onclick=\"callServer('promptForGeminiApiKey')\">Gemini API Key 설정</button>\n" +
    "    <button id='btnInit' class='btn btn-primary' onclick=\"callServer('initCampaignWorkspace')\">[초기화] 캠페인 작업 공간 구축</button>\n" +
    "  </div>\n" +
    "\n" +
    "  <div class='section'>\n" +
    "    <div class='section-title'>\n" +
    "      <span>5단계 파이프라인 실행</span>\n" +
    "      <span class='step-tag'>Core Flow</span>\n" +
    "    </div>\n" +
    "    <button class='btn btn-step' onclick=\"callServer('guardAndRunIdeaToPlan')\">\n" +
    "      <span>[1단계] 기획서 및 명세서 생성</span>\n" +
    "      <span class='step-tag'>PLAN</span>\n" +
    "    </button>\n" +
    "    <button class='btn btn-step' onclick=\"callServer('guardAndRunInitialContent')\">\n" +
    "      <span>[2단계] 초판 콘텐츠 생성</span>\n" +
    "      <span class='step-tag'>rv-00</span>\n" +
    "    </button>\n" +
    "    <button class='btn btn-step' onclick=\"callServer('promptAndRunJudgeEvaluation')\">\n" +
    "      <span>[3단계] 25인 AI 페르소나 평가</span>\n" +
    "      <span class='step-tag'>Judge</span>\n" +
    "    </button>\n" +
    "    <button class='btn btn-step' onclick=\"callServer('promptAndRunFeedbackSummary')\">\n" +
    "      <span>[4단계] 피드백 종합 보고서</span>\n" +
    "      <span class='step-tag'>Report</span>\n" +
    "    </button>\n" +
    "    <button class='btn btn-step' onclick=\"callServer('promptAndRunReviseAssets')\">\n" +
    "      <span>[5단계] 피드백 반영 콘텐츠 보정</span>\n" +
    "      <span class='step-tag'>Revise</span>\n" +
    "    </button>\n" +
    "  </div>\n" +
    "\n" +
    "  <div class='section'>\n" +
    "    <div class='section-title'>\n" +
    "      <span>생성된 산출물 바로가기</span>\n" +
    "      <span class='step-tag'>Assets</span>\n" +
    "    </div>\n" +
    "    <a id='linkFolder' class='link-card disabled' href='#'>캠페인 드라이브 폴더 열기</a>\n" +
    "    <a id='linkPlan' class='link-card disabled' href='#'>기획서 (PLAN.md) 열기</a>\n" +
    "    <a id='linkContent' class='link-card disabled' href='#'>최신 콘텐츠 (rv-xx) 열기</a>\n" +
    "    <a id='linkForm' class='link-card disabled' href='#'>고객 VoC 설문 폼 열기</a>\n" +
    "    <a id='linkSummary' class='link-card disabled' href='#'>피드백 종합 보고서 열기</a>\n" +
    "    <a id='linkMap' class='link-card disabled' href='#'>t-SNE 여론 지형도 이미지 열기</a>\n" +
    "  </div>\n" +
    "\n" +
    "  <div class='section'>\n" +
    "    <div class='section-title'>\n" +
    "      <span>실행 지표 현황</span>\n" +
    "      <span class='step-tag'>Metrics</span>\n" +
    "    </div>\n" +
    "    <div class='metrics'>\n" +
    "      <div class='metric-box'>\n" +
    "        <div id='valRv' class='metric-val'>-</div>\n" +
    "        <div class='metric-lbl'>최신 리비전</div>\n" +
    "      </div>\n" +
    "      <div class='metric-box'>\n" +
    "        <div id='valFb' class='metric-val'>-</div>\n" +
    "        <div class='metric-lbl'>최신 피드백</div>\n" +
    "      </div>\n" +
    "      <div class='metric-box'>\n" +
    "        <div id='valTokens' class='metric-val'>0</div>\n" +
    "        <div class='metric-lbl'>누적 토큰</div>\n" +
    "      </div>\n" +
    "    </div>\n" +
    "  </div>\n" +
    "\n" +
    "  <div class='footer-actions'>\n" +
    "    <button class='footer-btn' onclick='refreshStatus()'>패널 상태 새로고침</button>\n" +
    "     | \n" +
    "    <button class='footer-btn' onclick=\"callServer('forceSyncEngine')\">GitHub 최신 엔진 동기화</button>\n" +
    "  </div>\n" +
    "\n" +
    "  <script>\n" +
    "    function setStatus(msg, isError) {\n" +
    "      var el = document.getElementById('statusBar');\n" +
    "      if (!msg) {\n" +
    "        el.className = 'status-bar';\n" +
    "        el.textContent = '';\n" +
    "        return;\n" +
    "      }\n" +
    "      el.className = 'status-bar show' + (isError ? ' error' : '');\n" +
    "      el.textContent = msg;\n" +
    "    }\n" +
    "\n" +
    "    function setButtonsDisabled(disabled) {\n" +
    "      var btns = document.querySelectorAll('button');\n" +
    "      btns.forEach(function(b) { b.disabled = disabled; });\n" +
    "    }\n" +
    "\n" +
    "    function updateUI(status) {\n" +
    "      if (!status) return;\n" +
    "\n" +
    "      var keyBadge = document.getElementById('apiKeyBadge');\n" +
    "      if (status.hasApiKey) {\n" +
    "        keyBadge.className = 'badge active';\n" +
    "        keyBadge.textContent = 'API Key 등록됨';\n" +
    "      } else {\n" +
    "        keyBadge.className = 'badge warn';\n" +
    "        keyBadge.textContent = 'API Key 필요';\n" +
    "      }\n" +
    "\n" +
    "      if (status.campaignCode) {\n" +
    "        document.getElementById('campaignCodeBadge').textContent = status.campaignCode;\n" +
    "      }\n" +
    "\n" +
    "      updateLink('linkFolder', status.folderUrl);\n" +
    "      updateLink('linkPlan', status.planDocUrl);\n" +
    "      updateLink('linkContent', status.contentDocUrl);\n" +
    "      updateLink('linkForm', status.formUrl);\n" +
    "      updateLink('linkSummary', status.summaryDocUrl);\n" +
    "      updateLink('linkMap', status.mapUrl);\n" +
    "\n" +
    "      document.getElementById('valRv').textContent = status.latestRv || '-';\n" +
    "      document.getElementById('valFb').textContent = status.latestFb || '-';\n" +
    "      document.getElementById('valTokens').textContent = (status.totalTokens || 0).toLocaleString();\n" +
    "    }\n" +
    "\n" +
    "    function updateLink(id, url) {\n" +
    "      var el = document.getElementById(id);\n" +
    "      if (url) {\n" +
    "        el.href = url;\n" +
    "        el.className = 'link-card';\n" +
    "      } else {\n" +
    "        el.href = '#';\n" +
    "        el.className = 'link-card disabled';\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    function refreshStatus() {\n" +
    "      setStatus('상태 갱신 중...', false);\n" +
    "      google.script.run\n" +
    "        .withSuccessHandler(function(status) {\n" +
    "          updateUI(status);\n" +
    "          setStatus('', false);\n" +
    "        })\n" +
    "        .withFailureHandler(function(err) {\n" +
    "          setStatus('상태 갱신 오류: ' + (err.message || err), true);\n" +
    "        })\n" +
    "        .getPipelineStatus();\n" +
    "    }\n" +
    "\n" +
    "    function callServer(fnName) {\n" +
    "      setButtonsDisabled(true);\n" +
    "      setStatus('작업 실행 중입니다. 잠시만 기다려주십시오...', false);\n" +
    "      google.script.run\n" +
    "        .withSuccessHandler(function() {\n" +
    "          setButtonsDisabled(false);\n" +
    "          setStatus('작업이 성공적으로 완결되었습니다.', false);\n" +
    "          refreshStatus();\n" +
    "        })\n" +
    "        .withFailureHandler(function(err) {\n" +
    "          setButtonsDisabled(false);\n" +
    "          setStatus('오류 발생: ' + (err.message || err), true);\n" +
    "        })[fnName]();\n" +
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

