/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline - Apps Script Single Bundle
 * (Merged from apps-scripts/ 8 core modules for easy copy-paste)
 * As of 2026-10-14
 */

// ============================================================================
// FILE: Code_Config.js
// ============================================================================

/**
 * Module: Code_Config.js
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
  MODEL_GENERATOR: "gemini-3.8-flash", // 콘텐츠 발상 및 멀티모달 소재 양산 모델
  MODEL_JUDGE: "gemini-3.8-flash", // 25인 AI 페르소나 다면 평가 및 가드레일 판정 모델
  IMAGE_MODEL_NAME: "gemini-nano-banana-2.1", // 광고 소재 비주얼 이미지 생성 최신 공식 GA 모델 (Nano Banana 2.1)
  VIDEO_MODEL_NAME: "veo-3.1-fast-generate-preview", // 모바일 숏폼 영상 생성 25초 초고속 모델 (Veo 3.1 Fast)
  EMBEDDING_MODEL: "text-multilingual-embedding-002", // 한국어 및 다국어 특화 텍스트 임베딩 모델
  EMBEDDING_DIM: 128, // Matryoshka Representation Learning(MRL) 축소 차원 규격
  
  // 구글 드라이브 핵심 기획/명세/콘텐츠 문서 파일명
  PLAN_DOC_NAME: "PLAN", // 마케팅 캠페인 기획서 전문
  SPEC_DOC_NAME: "SPEC", // 멀티 채널 콘텐츠 제작 명세서 (이미지, 숏폼, 카피 규격)
  CONTENT_DOC_NAME: "campaign_content", // 멀티 채널 마케팅 콘텐츠 전문 (카피라이팅 및 영상 콘티)
  PERSONA_FILE_NAME: "ai_personas.json", // 25인 타깃 AI 페르소나 마스터 데이터 (캠페인 루트 직속)
  PROMPTS_FOLDER_NAME: "prompts", // 마케터 수정용 프롬프트 구글 독스 보관 폴더명

  // GitHub 퍼블릭 저장소 Raw 베이스 URL (초기화 시 최신 프롬프트 및 페르소나 실시간 인출)
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

  // 6대 프롬프트 구글 독스 기본 템플릿 정의 (초기화 시 prompts/ 폴더에 구글 독스로 시딩됨)
  DEFAULT_PROMPTS: {
    "01_idea_to_plan": {
      title: "01_idea_to_plan",
      description: "자연어 아이디어로부터 마케팅 캠페인 기획서(PLAN) 및 콘텐츠 제작 명세서(SPEC)를 자동 도출하는 프롬프트",
      systemInstruction:
        "당신은 엔터프라이즈 브랜드 마케팅 전략 수석 디렉터이다.\n" +
        "사용자가 입력한 자연어 아이디어 메모를 기반으로, 마케팅 캠페인 기획서(PLAN)와 멀티 채널 콘텐츠 제작 명세서(SPEC)를 전문적이고 체계적인 마크다운 형식으로 도출하라.\n\n" +
        "엄격한 작성 규칙:\n" +
        "1. 기획서(PLAN)에는 캠페인 명칭, 목표 타깃 세그먼트, 핵심 가치 제안(USP), 메인 메시지, 채널별 롤아웃 일정을 포함하십시오.\n" +
        "2. 제작 명세서(SPEC)에는 디스플레이 배너(16:9), 모바일 포스터(9:16), SNS 피드(1:1), 모바일 숏폼 영상(9:16, 15초)의 구체적 규격과 톤앤매너 지침을 명시하십시오.\n" +
        "3. 이모지와 중간 점을 쓰지 말고 쉼표(,)를 사용하십시오.\n" +
        "4. 모든 서술은 단호한 문어체/평서문('-다' 체)으로 작성하십시오.\n" +
        "5. 한글 복합어는 철저하게 띄어 쓰십시오."
    },
    "02_content_generation": {
      title: "02_content_generation",
      description: "기획서(PLAN)와 명세서(SPEC)를 바탕으로 카피라이팅 및 숏폼 영상 콘티가 통합된 campaign_content를 작성하는 프롬프트",
      systemInstruction:
        "당신은 전문 크리에이티브 마케팅 디렉터이자 카피라이터이다.\n" +
        "주어진 마케팅 캠페인 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC)를 바탕으로 단일 캠페인 종합 마케팅 콘텐츠 문서(campaign_content)를 완성도 높은 마케팅 카피 형식으로 작성하라.\n\n" +
        "필수 구성:\n" +
        "1. 헤드카피 및 슬로건 (3종)\n" +
        "2. 인스타그램 카드뉴스 및 피드 카피 (SPEC 규격 준수)\n" +
        "3. 네이버 블로그 리뷰형 기고문 (SPEC 규격 준수)\n" +
        "4. 모바일 세로 숏폼 영상 제작 콘티 (SPEC에 명시된 러닝타임 15초 및 세로 9:16 규격, 씬별 화면 연출 및 오디오/나레이션 지시문)\n" +
        "5. 제미나이 이미지 생성용 비주얼 프롬프트 (가로 16:9, 세로 9:16, 정방형 1:1)\n\n" +
        "엄격한 작성 규칙:\n" +
        "1. 콘텐츠 제작 명세서(SPEC)에 정의된 채널 규격, 숏폼 러닝타임, 톤앤매너를 최우선으로 준수하십시오.\n" +
        "2. 이모지와 중간 점을 일절 쓰지 말고 쉼표(,)를 사용하십시오.\n" +
        "3. 모든 서술은 단호하고 격조 높은 문어체/평서문('-다' 체)으로 작성하십시오.\n" +
        "4. 한글 복합어는 철저하게 띄어 쓰십시오.\n" +
        "5. 분량 및 가독성: 각 채널별 카피와 콘티는 마케터가 한눈에 읽고 즉시 검토할 수 있도록 명쾌하고 컴팩트하게 작성하십시오."
    },
    "03_persona_evaluation": {
      title: "03_persona_evaluation",
      description: "25인 한국인 마스터 AI 페르소나의 관점에서 공개된 마케팅 콘텐츠(rv-xx)를 다면 평가하고 세부 의견 포인트를 도출하는 프롬프트",
      systemInstruction:
        "당신은 엔터프라이즈 마케팅 리서치 및 소비자 심리 분석 전문 AI이다.\n" +
        "소비자는 사내 기획서를 알지 못하며, 시장에 공개된 마케팅 캠페인 콘텐츠(카피 및 비주얼)만을 보고 반응한다.\n" +
        "제공된 마케팅 콘텐츠 산출물을 면밀히 검토하고, 한국인 25인 가상 페르소나 프로필의 관점에 깊이 빙의하여 피드백을 작성하라.\n\n" +
        "### 핵심 원칙: 열린 피드백 및 복수 의견 포인트(Multi-points) 도출:\n" +
        "- 각 페르소나는 자신의 연령, 성별, 직업, 라이프스타일 관점에서 호평, 비판, 가격 저항, 사용성 의문 등 다각도의 열린 의견을 자유롭게 개진하라.\n" +
        "- 페르소나 1인당 2개~4개의 구체적인 세부 의견 포인트(points 배열)를 제시하여 50~80개 이상의 다면적 여론 포인트를 도출하라.\n" +
        "- 출력은 마크다운 코드 블록 없이 순수 JSON 배열만 반환하라."
    },
    "04_feedback_summary": {
      title: "04_feedback_summary",
      description: "고객 VoC 설문 응답, 실제 업로드된 영상/이미지 VLM 분석, 25인 다면 평가 지형도를 통합 요약하는 feedback_summary 보고서 프롬프트",
      systemInstruction:
        "당신은 엔터프라이즈 최고 마케팅 책임자(CMO) 전속 수석 분석관이다.\n" +
        "25인 가상 페르소나 다면 평가 결과와 고객 설문 응답, 제출된 미디어(영상/이미지) 분석 결과를 종합하여 전문적인 피드백 종합 분석 보고서(feedback_summary)를 작성하라.\n\n" +
        "필수 포함 섹션:\n" +
        "1. 종합 평가 지수 및 감성 지형 요약\n" +
        "2. 페르소나 군집별 주요 피드백 분석 (호평 요인 vs 우려 요인)\n" +
        "3. 고객 제출 미디어 실데이터 VLM 분석 결과 (실제 업로드된 파일이 없는 경우 소설을 쓰지 말고 '미제출'로 명시)\n" +
        "4. 마케터 최종 의사 결정 및 보정 지침 (마케터가 직접 편집할 수 있도록 명확한 가이드라인 블록 제공)\n\n" +
        "엄격한 작성 규칙:\n" +
        "1. 허구의 데이터를 지어내지 말고 실제 수집된 데이터에만 엄격히 입각하여 분석하십시오.\n" +
        "2. 이모지와 중간 점을 배제하고 단호한 문어체/평서문('-다' 체)으로 작성하십시오.\n" +
        "3. 한글 복합어는 철저하게 띄어 쓰십시오."
    },
    "05_content_revision": {
      title: "05_content_revision",
      description: "고객 피드백 종합 요약본(feedback_summary)과 마케터 최종 의사 결정을 최우선 반영하여 마케팅 콘텐츠(campaign_content)를 완결 보정하는 프롬프트",
      systemInstruction:
        "당신은 데이터 드리븐 크리에이티브 디렉터이다.\n" +
        "원천 마케팅 캠페인 기획서(PLAN)의 핵심 비전과 콘텐츠 제작 명세서(SPEC)의 채널별 규격을 충실히 계승하면서, " +
        "이전 마케팅 콘텐츠와 고객 피드백 종합 요약본(feedback_summary)의 마케터 최종 의사 결정 지침을 충실히 반영하여 개정본(campaign_content) 구글 독스를 완성도 높은 마케팅 카피 형식으로 작성하라.\n\n" +
        "엄격한 작성 규칙:\n" +
        "1. 피드백 요약본의 '마케터 최종 의사 결정 및 보정 지침'에 명시된 마케터 코멘트는 최우선 순위 지침이다. 모델 변경, 소구점 변경, 톤앤매너 수정 등 마케터의 명시적 지침을 카피 본문과 숏폼 영상 콘티에 반드시 최우선으로 반영하십시오.\n" +
        "2. 허구의 소설 작성을 엄격히 금지하며, 원천 기획서와 피드백 문서에 실제로 명시된 사실과 수치에만 입각하여 보정하십시오.\n" +
        "3. 이모지와 중간 점을 쓰지 말고 쉼표(,)를 사용하십시오.\n" +
        "4. 모든 서술은 단호한 문어체/평서문('-다' 체)으로 작성하십시오.\n" +
        "5. 한글 복합어는 철저하게 띄어 쓰십시오."
    },
    "06_visual_prompt": {
      title: "06_visual_prompt",
      description: "캠페인 카피와 마케터 의사 결정으로부터 Gemini 이미지 모델(Nano Banana) 및 Veo 비디오 모델에 입력할 최적의 영문 비주얼 프롬프트를 동적 추출하는 프롬프트",
      systemInstruction:
        "당신은 글로벌 광고 비주얼 아트 디렉터이다.\n" +
        "제공된 캠페인 카피와 마케터 최종 의사 결정 지침을 정밀 분석하여, " +
        "이미지 및 비디오 생성 AI(Gemini Nano Banana 2.1 / Veo)에 입력할 2~3문장의 구체적이고 감각적인 영문 프롬프트(Visual Prompt)를 작성하라.\n\n" +
        "엄격한 작성 규칙:\n" +
        "1. 마케터 코멘트에 특정 모델(예: 20대 한국인 여성, 직장인, 특정 국적 등)이나 연출 상황(카페, 출퇴근, 여행 등)이 지정되어 있다면 이를 누락하지 않고 영문으로 명시하십시오.\n" +
        "2. 마케터 코멘트에 별도 언급이 없더라도 한국 시장 타깃 캠페인이므로 한국인(Korean) 모델 및 서울의 현대적인 일상/공간을 기본 배경으로 설정하십시오.\n" +
        "3. 피사체(인물/제품), 공간/조명, 분위기/스타일링을 2~3문장의 자연스러운 영문 묘사로 작성하십시오.\n" +
        "4. 출력은 설명이나 머리말 없이 오직 영문 프롬프트 텍스트만 출력하십시오."
    }
  }
};


// ============================================================================
// FILE: Code_Gemini.js
// ============================================================================

/**
 * Module: Code_Gemini.js
 */
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
      userProps.setProperty("GEMINI_API_KEY", inputKey);
      ui.alert("설정 완료", "Gemini API Key가 안전하게 저장되었습니다.\n파이프라인 단계를 계속 진행하십시오.", ui.ButtonSet.OK);
      return inputKey;
    } else {
      ui.alert("입력 오류", "유효한 API Key가 입력되지 않았습니다.", ui.ButtonSet.OK);
    }
  }

  throw new Error("Gemini API Key가 설정되지 않아 작업을 중단합니다. 메뉴의 [Gemini API Key 설정]에서 키를 등록하십시오.");
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

  var response = UrlFetchApp.fetch(endpoint, options);
  var responseCode = response.getResponseCode();
  var responseBody = response.getContentText();

  if (responseCode !== 200) {
    throw new Error("Gemini API 호출 실패 (상태 코드: " + responseCode + "):\n" + responseBody);
  }

  var result = JSON.parse(responseBody);
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

  // Apps Script 런타임 제약 사전 방어 (페이로드 50MB 한계 및 6분 타임아웃 방지)
  if (sizeInMb > 35) {
    throw new Error(
      "미디어 파일 크기(" + sizeInMb.toFixed(1) + "MB)가 Apps Script 단일 페이로드 한계(Base64 인코딩 기준 실질 35MB)를 초과합니다. " +
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

  var response = UrlFetchApp.fetch(endpoint, options);
  var responseCode = response.getResponseCode();
  var responseBody = response.getContentText();

  if (responseCode !== 200) {
    throw new Error("Gemini 멀티모달 분석 실패 (상태 코드: " + responseCode + "):\n" + responseBody);
  }

  var result = JSON.parse(responseBody);
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
        var nResp = UrlFetchApp.fetch(nEndpoint, nOptions);
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
        var imgResp = UrlFetchApp.fetch(imgEndpoint, imgOptions);
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
      var response = UrlFetchApp.fetch(endpoint, options);
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
      var response = UrlFetchApp.fetch(endpoint, options);
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
// FILE: Code_Prompts.js
// ============================================================================

/**
 * Module: Code_Prompts.js
 */
/**
 * 캠페인 루트의 prompts/ 폴더 내에 6대 프롬프트 구글 독스를 자동 시딩한다.
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
// FILE: Code_Utils.js
// ============================================================================

/**
 * Module: Code_Utils.js
 */
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
 * 대표 비주얼 이미지 3종 비율 세트 생성 (16:9 배너, 9:16 포스터, 1:1 SNS 피드)
 */
function generateAndSaveVisualAssets(targetFolder, prefix, visualBrief) {
  var brief = visualBrief || "A stylish 20s Korean female model enjoying cozy autumn commuter lifestyle with lightweight ANC headphones, warm golden hour sunlight, modern Seoul street";
  var items = [
    { name: prefix + "_banner_16x9.png", ratio: "16:9", prompt: brief + " Wide horizontal display banner (16:9)." },
    { name: prefix + "_poster_9x16.png", ratio: "9:16", prompt: brief + " Vertical mobile commercial poster (9:16)." },
    { name: prefix + "_sns_1x1.png", ratio: "1:1", prompt: brief + " Square social media feed photo (1:1)." }
  ];

  for (var i = 0; i < items.length; i++) {
    var item = items[i];
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
    } else {
      Logger.log("Gemini 비주얼 이미지 생성 응답 없음: " + item.name);
    }
  }

  // 4. Gemini Veo 비디오 생성 API 호출 및 실제 숏폼 비디오(${prefix}_shorts.mp4) 저장
  // (별도 txt 콘티 파일은 생성하지 않고 campaign_content 단일 구글 독스 문서에 통합됨)
  var videoFileName = prefix + "_shorts.mp4";
  try {
    if (typeof callGeminiVideo === "function") {
      var videoPrompt = brief + " Vertical mobile commercial video (9:16 aspect ratio), cinematic lighting, smooth camera movement, photorealistic quality.";
      var videoResult = callGeminiVideo(videoPrompt, "9:16", 4);
      if (videoResult && videoResult.base64) {
        saveBinaryFile(targetFolder, videoFileName, videoResult.base64, videoResult.mimeType || "video/mp4");
        Logger.log("Gemini Veo 비디오 생성 및 저장 완료: " + videoFileName);
      } else {
        Logger.log("Gemini Veo 비디오 생성 응답 없음 또는 무료 티어 제한 (campaign_content 문서의 숏폼 영상 콘티 참조).");
      }
    }
  } catch (veoErr) {
    Logger.log("Gemini Veo 비디오 생성 연동 예외: " + veoErr);
  }
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
    "  - **[04~10초 본문]**: 180g 초경량 착용감과 감성적 몰입 무드 부각 (자연스러운 미소와 서울 카페/지하철 일상 풍경)\n" +
    "  - **[11~15초 엔딩]**: 브랜드 시그니처 로고 노출 및 얼리버드 한정 혜택 자막 명시\n\n" +
    "* **실제 영상 운영 안내**:\n" +
    "  - Google AI Studio 유료 결제 계정 연동 API Key 환경에서는 Gemini Veo 모델이 위 콘티를 바탕으로 실제 비디오(" + videoFileName + ")를 자동 생성하여 폴더에 함께 저장합니다.\n" +
    "  - 무료 API Key 환경이거나 현장 촬영본이 있는 경우, 마케터 또는 고객이 직접 촬영한 실제 모바일 숏폼 영상(" + videoFileName + ")을 해당 폴더에 업로드하여 활용할 수 있습니다.\n";

  return content + shortsSection;
}

/**
 * 피드백 요약본 및 마케터 지침, 보정 카피로부터 Gemini를 호출하여 영문 이미지 생성 프롬프트를 동적 도출한다.
 */
function extractDynamicVisualPrompt(campaignAsset, feedbackSummary, defaultBrief) {
  try {
    var systemInstruction =
      "당신은 글로벌 광고 비주얼 아트 디렉터이다.\n" +
      "제공된 캠페인 카피와 고객 피드백 요약본(특히 마케터 최종 의사 결정 및 보정 지침)을 정밀 분석하여, " +
      "이미지 생성 AI(Gemini 2.5 Flash Image / Imagen)에 입력할 2~3문장의 구체적이고 감각적인 영문 프롬프트(Visual Prompt)를 작성하라.\n\n" +
      "엄격한 작성 규칙:\n" +
      "1. 마케터 코멘트에 특정 모델(예: 20대 한국인 여성, 직장인, 특정 국적 등)이나 연출 상황(카페, 출퇴근, 여행 등)이 지정되어 있다면 이를 누락하지 않고 영문(예: 'A stylish 20s Korean female model', 'A chic young Korean woman in Seoul')으로 명시하십시오.\n" +
      "2. 마케터 코멘트에 모델에 대한 별도 언급이 없더라도 한국 시장 타깃 캠페인이므로 한국인(Korean) 모델 및 서울의 현대적인 일상/공간을 기본 배경으로 설정하십시오.\n" +
      "3. 피사체(인물/제품), 공간/조명, 분위기/스타일링을 2~3문장의 자연스러운 영문 묘사로 작성하십시오.\n" +
      "4. 출력은 설명이나 머리말 없이 오직 영문 프롬프트 텍스트만 출력하십시오.";

    var userPrompt =
      "[캠페인 카피 콘텐츠]\n" + (campaignAsset || "") + "\n\n" +
      "[고객 피드백 종합 요약본 및 마케터 최종 의사 결정]\n" + (feedbackSummary || "") + "\n\n" +
      "위 내용을 바탕으로 마케터의 의도를 충실히 반영한 상업 광고 이미지 생성용 영문 프롬프트 1개를 작성하라.";

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
    if (!personasText) {
      var campaignDataFolder = getCampaignSubFolder(["data"]);
      personasText = readTextFile(campaignDataFolder, "ai_personas.json");
    }

    var specContent = readGoogleDoc(campaignFolder, CONFIG.SPEC_DOC_NAME || "SPEC") || "";
    var hasSpecificSurvey = (specContent.indexOf("설문 문항") !== -1 || specContent.indexOf("피드백 설문") !== -1);
    var openFeedbackGuideline = hasSpecificSurvey
      ? "- 콘텐츠 제작 명세서(SPEC)에 정의된 피드백 설문 항목을 충실히 반영하여 의견을 개진하라.\n"
      : "- 콘텐츠 제작 명세서(SPEC)에 특정 설문 문항이 고정되어 있지 않으므로, '열린 피드백(Open-ended Feedback)' 원칙을 적용한다. 각 페르소나는 자신의 연령, 성별, 직업, 라이프스타일 관점에서 장점 호평, 단점 비판, 가격 저항, 사용성 의문, 구매 전환 장벽 등 다각도의 열린 의견을 자유롭게 개진하라.\n";

    var promptDocTemplate = (typeof getPromptTemplate === "function") ? getPromptTemplate("03_persona_evaluation") : "";
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
      var cleanJson = rawOutput.replace(/^```json\s*/i, "").replace(/^```\s*/, "").replace(/\s*```$/, "").trim();
      var parsed = JSON.parse(cleanJson);
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

function initDashboardSheet() {
  var sheet = getDashboardSheet();
  if (!sheet) return;

  try {
    var val = sheet.getRange("A2").getValue();
    if (val === "실행 단계") return;

    sheet.clear();

    // 상단 타이틀 배너 (A1:D1)
    sheet.getRange("A1:D1").merge();
    sheet.getRange("A1").setValue("Google Drive 마케팅 콘텐츠 파이프라인 실행 대시보드");
    sheet.getRange("A1")
      .setFontWeight("bold")
      .setFontSize(12)
      .setBackground("#1E293B")
      .setFontColor("#FFFFFF")
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle");
    sheet.setRowHeight(1, 38);

    // 컬럼 헤더 행 (A2:D2)
    var headers = [["실행 단계", "진행 상태", "생성된 산출물 바로가기", "완료 시각"]];
    sheet.getRange("A2:D2").setValues(headers);
    sheet.getRange("A2:D2")
      .setFontWeight("bold")
      .setFontSize(10)
      .setBackground("#F1F5F9")
      .setFontColor("#334155")
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle");
    sheet.setRowHeight(2, 28);

    // 컬럼 너비
    sheet.setColumnWidth(1, 140);
    sheet.setColumnWidth(2, 90);
    sheet.setColumnWidth(3, 380);
    sheet.setColumnWidth(4, 180);

    sheet.getRange("A2:D2").setBorder(true, true, true, true, true, true, "#CBD5E1", SpreadsheetApp.BorderStyle.SOLID);
  } catch (e) {
    Logger.log("대시보드 시트 초기화 예외: " + e);
  }
}

function recordStepResultToSheet(stepId, stepName, status, linkUrl, linkText) {
  var sheet = getDashboardSheet();
  if (!sheet) return;

  try {
    initDashboardSheet();

    var lastRow = sheet.getLastRow();
    var targetRow = 0;

    if (lastRow >= 3) {
      var stepValues = sheet.getRange(3, 1, lastRow - 2, 1).getValues();
      for (var i = 0; i < stepValues.length; i++) {
        var currentStep = stepValues[i][0];
        if (currentStep === stepId || (stepId === "Step 2 (기획서)" && currentStep === "Step 2")) {
          targetRow = i + 3;
          break;
        }
      }
    }

    if (targetRow === 0) {
      targetRow = Math.max(3, lastRow + 1);
    }

    sheet.setRowHeight(targetRow, 28);

    sheet.getRange(targetRow, 1)
      .setValue(stepId)
      .setFontWeight("bold")
      .setFontSize(10)
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle");

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

    var linkCell = sheet.getRange(targetRow, 3);
    linkCell.setFontSize(10).setVerticalAlignment("middle");
    if (linkUrl) {
      var displayText = linkText || stepName;
      linkCell.setFormula('=HYPERLINK("' + linkUrl + '", "' + displayText + '")').setHorizontalAlignment("left");
    } else {
      linkCell.setValue(stepName).setHorizontalAlignment("left");
    }

    var nowStr = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd HH:mm:ss");
    sheet.getRange(targetRow, 4)
      .setValue(nowStr)
      .setFontSize(9)
      .setFontColor("#64748B")
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle");

    sheet.getRange(targetRow, 1, 1, 4).setBorder(true, true, true, true, true, true, "#E2E8F0", SpreadsheetApp.BorderStyle.SOLID);
  } catch (e) {
    Logger.log("대시보드 시트 결과 기록 예외: " + e);
  }
}

/**
 * 피드백 폴더 내의 고객 촬영 동영상(MP4)을 탐색하여 Gemini VLM 멀티모달 심층 분석을 실행하고,
 * 그 결과를 video_voc_analysis.json 파일로 저장 및 객체로 반환한다.
 */
/**
 * 피드백 폴더 내의 모든 고객 동영상(비디오 VoC)을 탐색하여 Gemini VLM 심층 분석 실행
 * - 각 동영상 파일마다 1:1로 [영상파일명]_vlm.json 생성 및 증분 캐싱
 * - 반환값: 각 영상별 VLM 분석 결과 객체들의 배열 (Array of VLM analysis objects)
 */
function analyzeVideoVocWithVlm(feedbackFolder) {
  var results = [];
  try {
    // 1. 피드백 폴더 내의 모든 동영상 파일 탐색 (*.mp4, *.mov, *.webm, video/*)
    var videoFiles = [];
    var allFiles = feedbackFolder.getFiles();
    while (allFiles.hasNext()) {
      var f = allFiles.next();
      var fName = f.getName().toLowerCase();
      var mime = f.getMimeType();
      if (fName.indexOf(".mp4") !== -1 || fName.indexOf(".mov") !== -1 || fName.indexOf(".webm") !== -1 || mime.indexOf("video/") === 0) {
        videoFiles.push(f);
      }
    }

    // 동영상 파일이 하나도 없으면 가짜 영상을 생성하지 않고 정직하게 빈 결과 반환
    if (videoFiles.length === 0) {
      Logger.log("피드백 폴더 내에 고객 업로드 동영상(MP4/MOV/WEBM)이 없습니다. 동영상 VoC VLM 분석을 건너뜁니다.");
      return [];
    }

    // 2. 각 동영상 파일별 VLM 분석 및 1:1 [파일명]_vlm.json 증분 캐싱
    for (var i = 0; i < videoFiles.length; i++) {
      var vFile = videoFiles[i];
      var rawName = vFile.getName();
      var baseName = rawName.replace(/\.[^/.]+$/, "");
      var vlmJsonFileName = baseName + "_vlm.json";

      // 이미 유효한 {baseName}_vlm.json이 존재하면 캐시 우선 반환 (증분 처리로 6분 타임아웃 방어 및 API 비용 절감)
      var existingJson = readTextFile(feedbackFolder, vlmJsonFileName);
      if (!existingJson && rawName === "feedback_sample.mp4") {
        existingJson = readTextFile(feedbackFolder, "video_voc_analysis.json");
      }

      if (existingJson && existingJson.length > 50) {
        try {
          var parsed = JSON.parse(existingJson);
          Logger.log("기존 VLM 캐시 로드 완료: " + vlmJsonFileName + " (" + rawName + ")");
          results.push(parsed);
          continue;
        } catch (pErr) {
          // 파싱 실패 시 재분석
        }
      }

      // Gemini VLM 멀티모달 심층 분석 호출
      var vlmPrompt =
        "당신은 엔터프라이즈 마케팅 VLM(비전-언어 멀티모달) 심층 분석관이다.\n" +
        "제공된 고객 직접 촬영 동영상 피드백(비디오 VoC: " + rawName + ")을 정밀 분석하여, " +
        "고객의 시각적 행동/표정, 음성 톤, 실제 발화 내용, 제품 개선 요구사항을 추출하라.\n\n" +
        "절대 주의 사항:\n" +
        "- 동영상에 실제로 등장하지 않는 허구의 발화나 상황을 임의로 지어내지 마십시오.\n" +
        "- 동영상 속 인물의 실제 발화(음성 전사), 표정, 음성 톤에만 엄격히 근거하여 작성하십시오.\n\n" +
        "엄격한 출력 형식:\n" +
        "반드시 다음 JSON 형식으로만 순수 JSON을 출력하라. 코드 블록(```json) 없이 유효한 JSON만 반환하라:\n" +
        "{\n" +
        "  \"video_metadata\": {\n" +
        "    \"file_name\": \"" + rawName + "\",\n" +
        "    \"video_type\": \"customer_video_voc\",\n" +
        "    \"duration_seconds\": 10,\n" +
        "    \"aspect_ratio\": \"9:16\"\n" +
        "  },\n" +
        "  \"speaker_analysis\": {\n" +
        "    \"role\": \"동영상 내 발화자 역할 (예: 20대 소비자, 직장인 등)\",\n" +
        "    \"speaker_name\": \"발화자 호칭\",\n" +
        "    \"transcribed_speech\": \"동영상에서 추출된 실제 음성 전사 텍스트\",\n" +
        "    \"speech_intent\": \"발화자의 실제 의도 및 핵심 메시지\",\n" +
        "    \"facial_expression\": {\n" +
        "      \"primary_emotion\": \"관찰된 주요 표정 및 감정\",\n" +
        "      \"eye_contact\": \"시선 처리\",\n" +
        "      \"confidence_score\": 0.9\n" +
        "    },\n" +
        "    \"voice_tone\": {\n" +
        "      \"tempo\": \"음성 빠르기\",\n" +
        "      \"tone\": \"음성 톤 및 어조\",\n" +
        "      \"energy_level\": \"에너지 수준\"\n" +
        "    }\n" +
        "  },\n" +
        "  \"multimodal_judging\": {\n" +
        "    \"text_relevance_score\": 4.5,\n" +
        "    \"expression_score\": 4.5,\n" +
        "    \"tone_score\": 4.5,\n" +
        "    \"overall_weighted_score\": 4.5,\n" +
        "    \"sentiment\": \"긍정, 중립, 또는 개선 제안\"\n" +
        "  },\n" +
        "  \"creative_direction_extracted\": {\n" +
        "    \"visual_action_items\": [\n" +
        "      \"영상에서 도출된 비주얼 개선 포인트 1\",\n" +
        "      \"영상에서 도출된 비주얼 개선 포인트 2\"\n" +
        "    ],\n" +
        "    \"copy_action_items\": [\n" +
        "      \"영상에서 도출된 카피 개선 포인트 1\",\n" +
        "      \"영상에서 도출된 카피 개선 포인트 2\"\n" +
        "    ]\n" +
        "  }\n" +
        "}";

      var vlmResult = "";
      try {
        var videoBlob = vFile.getBlob();
        vlmResult = callGeminiMultimodal(vlmPrompt, videoBlob, CONFIG.MODEL_JUDGE);
      } catch (vlmErr) {
        Logger.log("VLM 직접 호출 예외 (" + rawName + "): " + vlmErr);
      }

      var finalJsonObj = null;
      if (vlmResult) {
        try {
          var cleanVlm = vlmResult.replace(/^```json\s*/i, "").replace(/^```\s*/, "").replace(/\s*```$/, "").trim();
          finalJsonObj = JSON.parse(cleanVlm);
        } catch (jsonErr) {
          Logger.log("VLM 응답 JSON 파싱 예외 (" + rawName + "): " + jsonErr);
        }
      }

      // 파싱 실패 또는 미수신 시 사실 기반 기본 객체 반환 (허구의 소설 배제)
      if (!finalJsonObj) {
        finalJsonObj = {
          video_metadata: {
            file_name: rawName,
            video_type: "customer_video_voc",
            duration_seconds: 0,
            aspect_ratio: "unknown"
          },
          speaker_analysis: {
            role: "소비자",
            speaker_name: "고객",
            transcribed_speech: "VLM 음성 전사 미완료 또는 무음 영상",
            speech_intent: "영상 분석 미완료",
            facial_expression: {
              primary_emotion: "중립",
              eye_contact: "정면",
              confidence_score: 0.5
            },
            voice_tone: {
              tempo: "보통",
              tone: "중립",
              energy_level: "보통"
            }
          },
          multimodal_judging: {
            text_relevance_score: 3.0,
            expression_score: 3.0,
            tone_score: 3.0,
            overall_weighted_score: 3.0,
            sentiment: "중립"
          },
          creative_direction_extracted: {
            visual_action_items: [
              "영상 피드백 원본 수동 확인 권장"
            ],
            copy_action_items: [
              "영상 피드백 원본 수동 확인 권장"
            ]
          }
        };
      }

      var formattedStr = JSON.stringify(finalJsonObj, null, 2);
      saveTextFile(feedbackFolder, vlmJsonFileName, formattedStr);
      Logger.log(vlmJsonFileName + " 저장 완료 (" + rawName + ")");
      results.push(finalJsonObj);
    }
    return results;
  } catch (err) {
    Logger.log("analyzeVideoVocWithVlm 예외: " + err);
    return results;
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
 * 고객 제출 또는 수작업 투입 이미지 피드백 VLM 심층 분석
 */
function analyzeImageFeedbackWithVlm(imageFile) {
  try {
    var imgBlob = imageFile.getBlob();
    var bytes = imgBlob.getBytes();
    if (bytes.length > 25 * 1024 * 1024) {
      return "이미지 파일 크기가 25MB를 초과하여 VLM 분석을 건너뛰었습니다. (파일명: " + imageFile.getName() + ")";
    }

    var prompt =
      "당신은 엔터프라이즈 크리에이티브 디렉터이자 VLM 시각 분석 AI이다.\n" +
      "제공된 이미지는 마케팅 캠페인의 고객 피드백 또는 수작업 검토 자료이다.\n" +
      "이 이미지의 시각적 요소(제품 외관 디자인, 컬러감, 착용 샷 구도, 감성적 무드, 광고 비주얼 장단점)를 분석하여 " +
      "향후 마케팅 콘텐츠 개정에 반영할 핵심 비주얼 개선 포인트 2~3가지를 단호한 문어체 평서문('-다' 체)으로 간결하게 요약하라.\n" +
      "한글 복합어는 철저히 띄어 쓰고 이모지와 중간 점은 일절 배제하라.";

    var result = callGeminiMultimodal(prompt, imgBlob, CONFIG.MODEL_JUDGE || "gemini-3.8-flash");
    return result ? result.trim() : null;
  } catch (e) {
    Logger.log("이미지 VLM 분석 실패 (" + imageFile.getName() + "): " + e);
    return null;
  }
}

/**
 * input/fb-xx/ 폴더 내 수작업 투입 파일(이미지, 추가 영상, 메모 문서) 전수 스캔 및 피드백 추출
 */
function scanManualFeedbackFiles(feedbackFolder) {
  var manualResults = [];
  if (!feedbackFolder) return manualResults;

  var systemReservedNames = [
    "ai_persona_feedbacks.json",
    "feedback_points_128d.json",
    "feedback_clusters_map.png",
    "feedback_summary",
    "video_voc_analysis.json",
    "feedback_sample.mp4"
  ];

  try {
    var files = feedbackFolder.getFiles();
    while (files.hasNext()) {
      var file = files.next();
      var fileName = file.getName();

      // 시스템 기본 생성 산출물 및 VLM 분석 결과 JSON은 제외
      if (systemReservedNames.indexOf(fileName) !== -1 || /_vlm\.json$/i.test(fileName)) {
        continue;
      }

      var mimeType = file.getMimeType();

      // 1. 수작업 투입 이미지 파일 (VLM 분석 실행)
      if (mimeType.indexOf("image/") === 0 || /\.(png|jpg|jpeg|webp)$/i.test(fileName)) {
        var imgAnalysis = analyzeImageFeedbackWithVlm(file);
        if (imgAnalysis) {
          manualResults.push("- [수작업 투입 이미지 VLM 분석: " + fileName + "]\n  " + imgAnalysis);
        } else {
          manualResults.push("- [수작업 투입 이미지 등록: " + fileName + "] (이미지 파일 확인됨)");
        }
      }
      // 2. 수작업 투입 동영상 파일
      else if (mimeType.indexOf("video/") === 0 || /\.(mp4|mov|webm)$/i.test(fileName)) {
        manualResults.push("- [수작업 투입 동영상 등록: " + fileName + "] (추가 고객 비디오 VoC 파일)");
      }
      // 3. 수작업 투입 Google Docs 문서
      else if (mimeType === MimeType.GOOGLE_DOCS) {
        try {
          var doc = DocumentApp.openById(file.getId());
          var docText = doc.getBody().getText().trim();
          if (docText) {
            var snippet = docText.length > 1500 ? docText.substring(0, 1500) + "..." : docText;
            manualResults.push("- [수작업 투입 Google Docs 메모: " + fileName + "]\n  \"" + snippet + "\"");
          }
        } catch (docErr) {
          manualResults.push("- [수작업 투입 Google Docs: " + fileName + "] (문서 열람 실패)");
        }
      }
      // 4. 수작업 투입 일반 텍스트 문서 (txt, json, csv, md)
      else if (mimeType.indexOf("text/") === 0 || /\.(txt|json|csv|md)$/i.test(fileName)) {
        try {
          var textContent = file.getBlob().getDataAsString("UTF-8").trim();
          if (textContent) {
            var snippet = textContent.length > 1500 ? textContent.substring(0, 1500) + "..." : textContent;
            manualResults.push("- [수작업 투입 텍스트 메모: " + fileName + "]\n  \"" + snippet + "\"");
          }
        } catch (txtErr) {
          manualResults.push("- [수작업 투입 텍스트: " + fileName + "]");
        }
      }
      // 5. 기타 파일
      else {
        manualResults.push("- [수작업 투입 파일: " + fileName + " (" + mimeType + ")]");
      }
    }
  } catch (scanErr) {
    Logger.log("scanManualFeedbackFiles 예외: " + scanErr);
  }

  return manualResults;
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


// ============================================================================
// FILE: Code_Workspace.js
// ============================================================================

/**
 * Module: Code_Workspace.js
 */
/**
 * [캠페인 초기화] 구글 드라이브 폴더 트리, 루트 직속 25인 페르소나, 6대 프롬프트 구글 독스,
 * 그리고 고객 VoC 수집용 Google Forms 생성 및 시트 바인딩까지 초장에 100% 완결한다.
 */
function initCampaignWorkspace() {
  var ui = SpreadsheetApp.getUi();
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
      var rawBase = (CONFIG && CONFIG.GITHUB_RAW_BASE) || "https://raw.githubusercontent.com/jiangjun-forge/google-cloud-0-to-1/main/samples/drive-marketing-content-pipeline";
      var personaJsonText = "";

      // GitHub 퍼블릭 저장소의 data/ai_personas.json 파일 실시간 인출
      try {
        var personaUrl = rawBase + "/data/ai_personas.json";
        var pResp = UrlFetchApp.fetch(personaUrl, { muteHttpExceptions: true });
        if (pResp.getResponseCode() === 200) {
          personaJsonText = pResp.getContentText();
          Logger.log("GitHub Raw로부터 최신 25인 페르소나 데이터 인출 성공");
        }
      } catch (fetchErr) {
        Logger.log("GitHub Raw 페르소나 인출 실패 (로컬 폴백 사용): " + fetchErr.toString());
      }

      // 네트워크 불가 시 내장 기본값으로 안전 폴백
      if (!personaJsonText) {
        var masterPersonas = getMasterPersonas25();
        personaJsonText = JSON.stringify(masterPersonas, null, 2);
      }

      saveTextFile(campaignFolder, personaFileName, personaJsonText);
      Logger.log("루트 직속 25인 AI 페르소나 데이터셋 시딩 완료: " + personaFileName);
    }

    // 3. prompts/ 폴더 내 6대 프롬프트 구글 독스 자동 시딩 (기존 마케터 수정분 보존)
    seedDefaultPrompts(promptsFolder);

    // 4. 스타터 아이디어 메모 구글 독스 시딩 (input/아이디어 메모)
    if (!readGoogleDoc(inputFolder, "아이디어 메모")) {
      var rawBase = (CONFIG && CONFIG.GITHUB_RAW_BASE) || "https://raw.githubusercontent.com/jiangjun-forge/google-cloud-0-to-1/main/samples/drive-marketing-content-pipeline";
      var starterIdea = "";

      // GitHub 퍼블릭 저장소의 data/starter_idea.md 파일 실시간 인출
      try {
        var ideaUrl = rawBase + "/data/starter_idea.md";
        var iResp = UrlFetchApp.fetch(ideaUrl, { muteHttpExceptions: true });
        if (iResp.getResponseCode() === 200) {
          starterIdea = iResp.getContentText().replace("cp-ignite", campaignCode);
          Logger.log("GitHub Raw로부터 스타터 아이디어 메모 인출 성공");
        }
      } catch (ideaErr) {
        Logger.log("GitHub Raw 스타터 아이디어 인출 실패 (로컬 폴백 사용): " + ideaErr.toString());
      }

      // 폴백 템플릿
      if (!starterIdea) {
        starterIdea =
          "# 캠페인 아이디어 메모\n\n" +
          "* **캠페인 명칭**: 2026 가을 오텀 브리즈 캠페인 (" + campaignCode + ")\n" +
          "* **핵심 컨셉**: 선선한 가을 날씨에 어울리는 프리미엄 노이즈 캔슬링(ANC) 헤드폰 일상 탈출 컬렉션\n" +
          "* **타깃 고객**: 도심 속 워크앤라이프 밸런스를 추구하는 2040 직장인 및 통근자\n" +
          "* **핵심 소구점**: 180g 초경량 착용감, 45dB 차음 성능, 감성적 힐링 몰입 무드\n" +
          "* **목표 채널**: 유튜브 쇼츠 및 인스타그램 릴스(9:16), 디스플레이 배너(16:9), 블로그 브랜드 기고문\n";
      }

      saveGoogleDoc(inputFolder, "아이디어 메모", starterIdea);
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
    initDashboardSheet();
    recordStepResultToSheet("초기 환경 구축", "작업 공간 및 VoC 설문 폼", "완료", campaignFolder.getUrl(), "구글 드라이브 폴더 열기 (" + campaignCode + ")");
    if (formInfo && formInfo.publishedUrl) {
      recordStepResultToSheet("고객 피드백 채널", "VoC 구글 폼 및 모바일 QR", "활성", formInfo.publishedUrl, "온라인 설문지 열기");
    }

    ui.alert(
      "캠페인 초기 환경 구축 완료 (All-in-one)",
      "캠페인 작업 공간(" + campaignCode + ")이 완벽하게 준비되었습니다:\n\n" +
      "1. 캠페인 루트 직속 25인 페르소나(ai_personas.json) 완비\n" +
      "2. prompts/ 폴더 내 6대 프롬프트 구글 독스 시딩 완료 (언제든 직접 수정 가능)\n" +
      "3. 고객 VoC 수집용 구글 폼 생성 및 모바일 QR 코드 바인딩 완료\n\n" +
      "구글 시트의 [실행 대시보드] 표에서 바로가기 링크를 확인하십시오.",
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert("초기화 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
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
// FILE: Code_Content.js
// ============================================================================

/**
 * Module: Code_Content.js
 */
/**
 * [액션 1] 마케터 자연어 아이디어를 기반으로 캠페인 기획서(PLAN) 및 콘텐츠 제작 명세서(SPEC)를 자동 도출한다.
 */
function runIdeaToPlanConversion() {
  var ui = SpreadsheetApp.getUi();
  showProcessingToast("아이디어 기반 기획서(PLAN) 및 명세서(SPEC) 자동 도출 중...", 30);
  try {
    var campaignFolder = getCampaignFolder();
    var campaignCode = getCampaignCode();
    var inputFolder = getCampaignSubFolder(["input"]);

    // 1. input/아이디어 메모 읽기 또는 대화상자 프롬프트
    var ideaMemo = readGoogleDoc(inputFolder, "아이디어 메모");
    if (!ideaMemo || ideaMemo.trim().length < 10) {
      var promptResp = ui.prompt(
        "마케팅 캠페인 아이디어 입력",
        "캠페인 컨셉이나 아이디어 초안을 자유롭게 입력하십시오 (예: 2026 프리미엄 노이즈 캔슬링 헤드폰 론칭 프로모션):",
        ui.ButtonSet.OK_CANCEL
      );
      if (promptResp.getSelectedButton() === ui.Button.OK) {
        ideaMemo = promptResp.getResponseText().trim();
        if (ideaMemo) {
          saveGoogleDoc(inputFolder, "아이디어 메모", ideaMemo);
        }
      }
    }

    if (!ideaMemo || ideaMemo.trim().length < 5) {
      throw new Error("캠페인 아이디어가 입력되지 않아 기획서 생성을 중단합니다. [아이디어 메모] 문서를 확인하십시오.");
    }

    // 2. 구글 독스 기반 프롬프트 템플릿 로드 (마케터 수정분 자동 반영)
    var systemInstruction = getPromptTemplate("01_idea_to_plan");
    var userPrompt =
      "다음은 마케터가 작성한 캠페인 아이디어 초안 메모이다.\n\n" +
      "### [마케터 아이디어 메모]\n" + ideaMemo + "\n\n" +
      "위 아이디어를 정밀 분석하여 다음 두 개의 독립된 문서 본문을 마크다운으로 작성하라:\n\n" +
      "===DOCUMENT_SPLIT_PLAN===\n" +
      "(여기에 마케팅 캠페인 기획서 PLAN 본문 작성)\n\n" +
      "===DOCUMENT_SPLIT_SPEC===\n" +
      "(여기에 멀티 채널 콘텐츠 제작 명세서 SPEC 본문 작성: 가로 16:9 배너, 세로 9:16 포스터, 정사각 1:1 SNS 피드, 세로 9:16 모바일 숏폼 영상 15초 규격 포함)";

    var rawResponse = callGemini(systemInstruction, userPrompt);

    // 3. 기획서(PLAN)와 제작 명세서(SPEC) 분리 저장
    var planContent = "";
    var specContent = "";

    if (rawResponse.indexOf("===DOCUMENT_SPLIT_PLAN===") !== -1 && rawResponse.indexOf("===DOCUMENT_SPLIT_SPEC===") !== -1) {
      var parts = rawResponse.split("===DOCUMENT_SPLIT_SPEC===");
      planContent = parts[0].replace("===DOCUMENT_SPLIT_PLAN===", "").trim();
      specContent = parts[1].trim();
    } else {
      planContent = rawResponse;
      specContent =
        "# 콘텐츠 제작 명세서 (SPEC)\n\n" +
        "* 가로 배너: 16:9 (1920x1080) - 구글 디스플레이 네트워크\n" +
        "* 세로 포스터: 9:16 (1080x1920) - 모바일 스토리\n" +
        "* 정방형 SNS: 1:1 (1080x1080) - 인스타그램 피드\n" +
        "* 모바일 숏폼: 9:16 (1080x1920, 15초) - 유튜브 쇼츠, 인스타그램 릴스\n";
    }

    var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
    var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";

    var planFile = saveGoogleDoc(campaignFolder, planDocName, planContent);
    var specFile = saveGoogleDoc(campaignFolder, specDocName, specContent);

    // 4. 대시보드 시트에 링크 기록
    recordStepResultToSheet("기획서 (PLAN)", "마케팅 캠페인 기획서", "완료", planFile.getUrl(), "구글 독스 열기 (PLAN)");
    recordStepResultToSheet("제작 명세서 (SPEC)", "멀티 채널 콘텐츠 제작 명세서", "완료", specFile.getUrl(), "구글 독스 열기 (SPEC)");

    ui.alert(
      "기획서 및 명세서 생성 완료",
      "캠페인 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC) 구글 독스가 캠페인 폴더에 자동 생성되었습니다.\n\n" +
      "마케터는 브라우저에서 직접 SPEC 수치(해상도, 숏폼 길이 등)를 수정한 뒤 다음 단계를 진행할 수 있습니다.",
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert("기획서 도출 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
}

/**
 * [액션 2] 기획서(PLAN) 및 명세서(SPEC)를 기반으로 초판 마케팅 콘텐츠(rv-00)를 일괄 양산한다.
 */
function runInitialContentGeneration() {
  var ui = SpreadsheetApp.getUi();
  showProcessingToast("초판 마케팅 콘텐츠 양산 중 (rv-00)...", 60);
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

    // 1. 프롬프트 템플릿 로드 (구글 독스 스마트 캐싱)
    var systemInstruction = getPromptTemplate("02_content_generation");
    var promptText =
      "다음은 이번 캠페인의 마케팅 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC)이다.\n" +
      "명세서(SPEC)에 정의된 채널 규격, 영상 길이, 비주얼 가이드라인을 엄격히 준수하여 초판 campaign_content를 작성하라:\n\n" +
      "### [1. 마케팅 캠페인 기획서 (PLAN)]\n" + planContent + "\n\n" +
      "### [2. 멀티 채널 콘텐츠 제작 명세서 (SPEC)]\n" + (specContent || "기본 규격 준수");

    var generatedContent = callGemini(systemInstruction, promptText);

    // 2. 동적 비주얼 프롬프트 도출 및 숏폼 영상 콘티 완전 통합
    var visualBrief = extractDynamicVisualPrompt(
      generatedContent,
      planContent,
      "A stylish 20s Korean female commuter with lightweight premium ANC headphones in warm golden autumn sunlight on a modern Seoul street"
    );
    var finalizedContent = ensureShortsScriptInCampaignContent(generatedContent, "00", visualBrief);

    // 3. campaign_content 단일 구글 독스 문서 저장
    var contentDocName = (CONFIG && CONFIG.CONTENT_DOC_NAME) || "campaign_content";
    var contentDocFile = saveGoogleDoc(rv00Folder, contentDocName, finalizedContent);

    // 4. 실시간 대표 비주얼 이미지 3종 및 Veo 비디오 생성
    Logger.log("동적 도출된 비주얼 프롬프트 (rv-00): " + visualBrief);
    generateAndSaveVisualAssets(rv00Folder, "00", visualBrief);

    // 5. 실행 대시보드에 링크 기록
    recordStepResultToSheet("초판 마케팅 콘텐츠", "카피 및 비주얼 (rv-00)", "완료", rv00Folder.getUrl(), "구글 드라이브 폴더 열기 (rv-00)");

    ui.alert(
      "초판 마케팅 콘텐츠 양산 완료 (rv-00)",
      "초판 마케팅 카피 및 숏폼 영상 콘티가 통합된 구글 독스(campaign_content)와 대표 비주얼 이미지 3종 비율 세트 생성이 완료되었습니다.\n\n" +
      "구글 시트의 [실행 대시보드] 표에서 바로가기 링크를 확인하십시오.",
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert("초판 콘텐츠 양산 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
}

/**
 * [액션 3] 피드백 요약본(feedback_summary)과 마케터 지침을 반영하여 N차 개정본 마케팅 콘텐츠를 완결 보정한다.
 */
function runReviseContent(targetRoundOpt, isSilentOpt) {
  var ui = SpreadsheetApp.getUi();
  var isSilent = (isSilentOpt === true);
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

    showProcessingToast("피드백 반영 마케팅 콘텐츠 보정 중 (" + targetRvName + ")...", 75);

    var prevRvFolder = getCampaignSubFolder(["output", prevRvName]);
    var targetRvFolder = getCampaignSubFolder(["output", targetRvName]);
    var feedbackFolder = getCampaignSubFolder(["input", targetRound]);

    // 선결 조건 1: 이전 콘텐츠 확인
    var targetContentDocName = (CONFIG && CONFIG.CONTENT_DOC_NAME) || "campaign_content";
    var previousAsset = readGoogleDoc(prevRvFolder, targetContentDocName) || readGoogleDoc(prevRvFolder, "campaign_asset");
    if (!previousAsset) {
      throw new Error("이전 마케팅 콘텐츠(" + prevRvName + ")를 찾을 수 없습니다. [초판 콘텐츠 양산]을 먼저 실행하십시오.");
    }

    // 선결 조건 2: feedback_summary 확인
    var summaryContent = readGoogleDoc(feedbackFolder, "feedback_summary");
    if (!summaryContent) {
      throw new Error("피드백 요약본(" + targetRound + "/feedback_summary)을 찾을 수 없습니다. [피드백 종합 분석 보고서 생성]을 먼저 실행하십시오.");
    }

    var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
    var planContent = readGoogleDoc(campaignFolder, planDocName) || readGoogleDoc(campaignFolder, "BRD") || "마케팅 캠페인 기획서";
    var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";
    var specContent = readGoogleDoc(campaignFolder, specDocName) || "콘텐츠 제작 명세서";

    // 1. 프롬프트 템플릿 로드 (구글 독스 스마트 캐싱)
    var systemInstruction = getPromptTemplate("05_content_revision");
    var userPrompt =
      "다음은 원천 기획 명세(PLAN), 콘텐츠 제작 명세서(SPEC), 직전 마케팅 콘텐츠(" + prevRvName + "), 그리고 고객 피드백 종합 요약본(feedback_summary)이다.\n\n" +
      "### [1. 원천 마케팅 캠페인 기획서 (PLAN)]\n" + planContent + "\n\n" +
      "### [2. 콘텐츠 제작 명세서 (SPEC)]\n" + specContent + "\n\n" +
      "### [3. 직전 마케팅 콘텐츠 (" + prevRvName + ")]\n" + previousAsset + "\n\n" +
      "### [4. 고객 및 AI 페르소나 피드백 요약본 (feedback_summary)]\n" + summaryContent;

    var refinedAsset = callGemini(systemInstruction, userPrompt);

    // 2. 동적 비주얼 프롬프트 도출 및 숏폼 영상 콘티 완전 통합
    var prefix = (roundNum < 10 ? "0" + roundNum : "" + roundNum);
    var dynamicBrief = extractDynamicVisualPrompt(
      refinedAsset,
      summaryContent,
      "A stylish 20s Korean female model enjoying cozy autumn commuter lifestyle with lightweight ANC headphones in a chic Seoul cafe"
    );
    var finalizedContent = ensureShortsScriptInCampaignContent(refinedAsset, prefix, dynamicBrief);

    // 3. campaign_content 단일 구글 독스 문서 저장
    var assetDocFile = saveGoogleDoc(targetRvFolder, targetContentDocName, finalizedContent);

    // 4. 대시보드 시트에 링크 기록
    var stepTitle = roundNum + "차 마케팅 콘텐츠 개정본 (" + targetRvName + ")";
    recordStepResultToSheet(targetRvName, stepTitle, "완료", targetRvFolder.getUrl(), "구글 드라이브 폴더 열기 (" + targetRvName + ")");

    // 5. 신규 비주얼 이미지 3종 및 Veo 비디오 생성
    Logger.log("동적 도출된 비주얼 프롬프트 (" + targetRvName + "): " + dynamicBrief);
    generateAndSaveVisualAssets(targetRvFolder, prefix, dynamicBrief);

    if (!isSilent) {
      ui.alert(
        "마케팅 콘텐츠 반자율 보정 완료 (" + targetRvName + ")",
        "피드백과 마케터 지침이 반영된 개정본(" + targetRvName + ") 및 신규 비주얼 이미지 3종 비율 세트 생성이 완료되었습니다.\n\n구글 시트의 [실행 대시보드] 표에서 바로가기 링크를 확인하십시오.",
        ui.ButtonSet.OK
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
}


// ============================================================================
// FILE: Code_Feedback.js
// ============================================================================

/**
 * Module: Code_Feedback.js
 */
/**
 * [액션 4] 25인 AI 페르소나 다면 평가를 실행하고 128d 임베딩 기반 2D t-SNE 여론 지형도를 생성한다.
 *
 * @param {string} [targetRoundOpt] - 대상 피드백 라운드 (기본값: 자동 감지 fb-01, fb-02 ...)
 */
function runPersonaEvaluation(targetRoundOpt) {
  var ui = SpreadsheetApp.getUi();
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

    // 1. 25인 페르소나 피드백 데이터셋 로드 또는 실시간 생성 (50~80개 세부 의견 포인트 + 128d 임베딩)
    var jsonContent = readTextFile(feedbackFolder, "ai_persona_feedbacks.json");
    if (!jsonContent) {
      jsonContent = generateLivePersonaFeedbacks(campaignFolder, feedbackFolder, prevRvName);
    }

    // 2. 128d 임베딩 기반 t-SNE 다면 여론 지형도 차트 생성 (feedback_clusters_map.png)
    var clusterMapFile = null;
    var pointsJson = readTextFile(feedbackFolder, "feedback_points_128d.json");
    var parsedPoints = [];
    if (pointsJson) {
      try {
        parsedPoints = JSON.parse(pointsJson);
      } catch (e) {}
    }

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

    // 3. 대시보드 시트에 링크 기록
    var stepTitle = roundNum + "차 페르소나 다면 평가 및 t-SNE 지형도 (" + targetRound + ")";
    recordStepResultToSheet(
      targetRound,
      stepTitle,
      "완료",
      clusterMapFile.getUrl(),
      "t-SNE 지형도 이미지 열기 (" + targetRound + ")"
    );

    ui.alert(
      "25인 페르소나 다면 평가 및 지형도 생성 완료 (" + targetRound + ")",
      "한국인 25인 가상 페르소나로부터 50개 이상의 세부 의견 포인트와 128차원 임베딩 기반 t-SNE 여론 지형도가 성공적으로 도출되었습니다.\n\n" +
      "이어서 [피드백 종합 분석 보고서 생성]을 실행하여 전체 데이터를 통합하십시오.",
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert("페르소나 평가 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
}

/**
 * [액션 5] 고객 VoC 설문 응답, 제출된 미디어(영상/이미지) VLM 분석, t-SNE 지형도를 통합하여
 * 피드백 종합 분석 보고서(feedback_summary) 구글 독스를 자동 생성한다.
 *
 * @param {string} [targetRoundOpt] - 대상 피드백 라운드
 */
function runFeedbackSummaryReport(targetRoundOpt) {
  var ui = SpreadsheetApp.getUi();
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
            var vlmPrompt = "이 미디어는 소비자가 제품을 직접 체험하며 남긴 피드백 영상/사진이다. 표정, 감정, 사용성, 제품 착용감에 대한 핵심 의견을 3문장으로 객관적으로 요약하라.";
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
    var systemInstruction = getPromptTemplate("04_feedback_summary");
    var userPrompt =
      "다음은 " + prevRvName + " 마케팅 콘텐츠에 대한 25인 가상 페르소나 다면 평가 결과와 실제 고객 설문 응답, 미디어 VLM 분석 데이터이다.\n\n" +
      "### [1. 이전 마케팅 콘텐츠 (" + prevRvName + ")]\n" + (prevContent.substring(0, 1500) || "카피 및 비주얼") + "\n\n" +
      "### [2. 25인 가상 페르소나 다면 평가 데이터셋]\n" + (personaFeedbacksRaw.substring(0, 3000) || "평가 데이터") + "\n\n" +
      "### [3. 고객 구글 폼 응답 데이터]\n" + (formResponsesText || "접수된 고객 설문 응답 없음") + "\n\n" +
      "### [4. 고객 제출 미디어 VLM 분석 실데이터 (" + mediaAnalysisList.length + "건)]\n" +
      (mediaAnalysisList.length > 0 ? JSON.stringify(mediaAnalysisList, null, 2) : "실제 업로드된 고객 동영상 및 이미지 없음 (미제출)") + "\n\n" +
      "위 데이터를 종합하여 최고 마케팅 책임자(CMO) 및 담당 마케터가 검토할 피드백 종합 분석 보고서(feedback_summary)를 작성하라.\n" +
      "문서 맨 마지막에는 마케터가 직접 브라우저에서 수정할 수 있는 [마케터 최종 의사 결정 및 보정 지침] 섹션을 반드시 포함하라.";

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

    // 6. 대시보드 시트에 링크 기록
    var stepTitle = roundNum + "차 피드백 종합 분석 보고서 (" + targetRound + ")";
    recordStepResultToSheet(
      "피드백 보고서",
      stepTitle,
      "완료",
      summaryFile.getUrl(),
      "구글 독스 보고서 열기 (" + targetRound + ")"
    );

    ui.alert(
      "피드백 종합 분석 보고서 도출 완료 (" + targetRound + ")",
      "피드백 종합 요약서(feedback_summary) 구글 독스가 생성되었습니다:\n\n" +
      "1. 상단에 t-SNE 2D 여론 지형도 차트가 자동 삽입되었습니다.\n" +
      "2. 실제 업로드된 영상/이미지 VLM 분석과 25인 평가가 종합되었습니다.\n" +
      "3. [실행 대시보드]에서 구글 독스를 직접 열어 문서 하단의 [마케터 최종 의사 결정] 지침을 검토 및 수정한 뒤 [콘텐츠 보정]을 진행하십시오.",
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert("피드백 보고서 도출 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
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
// FILE: Code_Menu.js
// ============================================================================

/**
 * Module: Code_Menu.js
 */
/**
 * 스프레드시트 열림 시 액션 중심 커스텀 메뉴 자동 등록
 */
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("[마케팅 콘텐츠 파이프라인]")
    .addItem("[초기화] 캠페인 작업 공간 환경 구축 (All-in-one Setup)", "initCampaignWorkspace")
    .addItem("[설정] 캠페인 환경 설정 및 재설정 (Configure)", "runConfigureCampaignSettings")
    .addSeparator()
    .addItem("[기획] 기획서 및 콘텐츠 명세서 생성 (PLAN & SPEC)", "guardAndRunIdeaToPlan")
    .addItem("[양산] 초판 마케팅 콘텐츠 양산 (rv-00)", "guardAndRunInitialContent")
    .addItem("[평가] 25인 AI 페르소나 다면 평가 실행 (fb-xx)", "promptAndRunJudgeEvaluation")
    .addItem("[보고서] 피드백 종합 분석 보고서 생성 (feedback_summary)", "promptAndRunFeedbackSummary")
    .addItem("[보정] 피드백 반영 콘텐츠 보정 (rv-xx)", "promptAndRunReviseAssets")
    .addSeparator()
    .addItem("[설문 폼] 고객 VoC 설문 폼 열기", "openCustomerVocForm")
    .addItem("[페르소나] 25인 AI 페르소나 맞춤 재설정 (선택 사항)", "setCustomPersonasPrompt")
    .addItem("[API Key] Gemini API Key 설정 (Google AI Studio)", "promptForGeminiApiKey")
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
 * [가드레일] 초판 마케팅 콘텐츠 양산 선결 조건 검증 후 실행
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
        "기획서 없이 진행할 경우 기본 설정 템플릿으로 양산됩니다.\n\n" +
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
        "[양산] 초판 마케팅 콘텐츠 양산 메뉴를 먼저 실행하여 초판을 제작하십시오.",
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
    "(빈칸으로 두고 [확인] 클릭 시 rv-" + suggestedRvStr + " 개정본이 자동 양산됩니다)\n\n" +
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

    // 1. Hugging Face Server API 연동 여부 판별
    if (criteria.indexOf("hf:") === 0) {
      var datasetRepo = criteria.replace("hf:", "").trim();
      var hfUrl = "https://datasets-server.huggingface.co/rows?dataset=" + encodeURIComponent(datasetRepo) + "&config=default&split=train&offset=0&limit=25";
      var hfResp = UrlFetchApp.fetch(hfUrl, { muteHttpExceptions: true });
      if (hfResp.getResponseCode() === 200) {
        var hfData = JSON.parse(hfResp.getContentText());
        var rawRowsText = JSON.stringify(hfData.rows || hfData, null, 2);
        var normInstruction =
          "당신은 데이터 엔지니어이다. 제공된 Hugging Face 원본 데이터로부터 25인의 슬림 페르소나 JSON 배열을 추출 및 정규화하라.\n" +
          "반드시 id(p01~p25), name, age, gender, category(전문 마케터 또는 일반 소비자), occupation, perspective(핵심 관점 및 관심사 1줄) 7개 필드만 포함하는 JSON 배열로 출력하라.";
        generatedJson = callGemini(normInstruction, rawRowsText);
      } else {
        throw new Error("Hugging Face API 호출 실패 (응답 코드: " + hfResp.getResponseCode() + ")");
      }
    } else {
      // 2. Gemini 기반 자연어 타깃 페르소나 25인 즉시 합성
      var systemInstruction =
        "당신은 글로벌 소비자 리서치 및 엔터프라이즈 마케팅 페르소나 엔지니어링 AI이다.\n" +
        "사용자가 지정한 타깃 기준에 맞추어 마케팅 캠페인 콘텐츠와 광고 소재를 다면 평가할 25인의 슬림 AI 페르소나 패널을 도출하라.\n\n" +
        "필수 규칙:\n" +
        "1. 총 25인 구성: 전문 마케터 12인 + 일반 소비자 13인으로 안배하십시오.\n" +
        "2. 반드시 다음 7개 필드만 엄격히 포함하는 순수 JSON 객체로 출력하십시오:\n" +
        "{\n" +
        "  \"metadata\": { \"description\": \"타깃 맞춤 AI 페르소나 패널\", \"total\": 25 },\n" +
        "  \"personas\": [\n" +
        "    {\n" +
        "      \"id\": \"p01\",\n" +
        "      \"name\": \"이름\",\n" +
        "      \"age\": 30,\n" +
        "      \"gender\": \"남성/여성\",\n" +
        "      \"category\": \"전문 마케터 또는 일반 소비자\",\n" +
        "      \"occupation\": \"직업\",\n" +
        "      \"perspective\": \"핵심 성향 및 주요 관심사 요약 (1줄)\"\n" +
        "    }\n" +
        "  ]\n" +
        "}\n" +
        "3. 코드 블록(```json) 없이 유효한 JSON만 반환하십시오.\n" +
        "4. 불필요하게 긴 텍스트나 중복 필드를 배제하여 토큰 효율을 극대화하십시오.";

      var userPrompt = "타깃 페르소나 기준: " + criteria + "\n\n위 기준에 부합하는 정밀하고 다양한 25인 슬림 페르소나 JSON을 생성하라.";
      generatedJson = callGemini(systemInstruction, userPrompt);
    }

    if (generatedJson) {
      var cleanJson = generatedJson.replace(/^```json\s*/i, "").replace(/^```\s*/, "").replace(/\s*```$/, "").trim();
      var parsed = JSON.parse(cleanJson);
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

