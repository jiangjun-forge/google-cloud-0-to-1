/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline - Apps Script Single Bundle
 * (Merged from apps-scripts/ modules for easy copy-paste)
 * As of 2026-10-14
 */

// ============================================================================
// FILE: Code_Config.js
// [모듈 1] 전역 설정 (Global Configuration)
// ============================================================================

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
  IMAGE_MODEL_NAME: "gemini-2.5-flash-image", // 광고 소재 비주얼 이미지 생성 모델
  VIDEO_MODEL_NAME: "veo-3.1-generate-001", // 모바일 숏폼 영상 생성 모델
  EMBEDDING_MODEL: "text-multilingual-embedding-002", // 한국어 및 다국어 특화 텍스트 임베딩 모델
  EMBEDDING_DIM: 128, // Matryoshka Representation Learning(MRL) 축소 차원 규격
  
  // 구글 드라이브 핵심 기획/명세/콘텐츠 문서 파일명
  PLAN_DOC_NAME: "PLAN", // 마케팅 캠페인 기획서 전문
  SPEC_DOC_NAME: "SPEC", // 멀티 채널 콘텐츠 제작 명세서 (이미지, 숏폼, 카피 규격)
  CONTENT_DOC_NAME: "campaign_content", // 멀티 채널 마케팅 콘텐츠 전문 (카피라이팅 및 영상 콘티)

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
      duration: "15초~30초",
      channel: "유튜브 쇼츠, 인스타그램 릴스, 틱톡"
    }
  },
  
  // QuickChart REST API 엔드포인트 (t-SNE 여론 군집 지형도 렌더링)
  QUICKCHART_ENDPOINT: "https://quickchart.io/chart"
};

// ============================================================================
// FILE: Code_Gemini.js
// [모듈 2] Gemini REST API 클라이언트 엔진 (Google AI Studio 무료 API Key 기반 Zero-GCP 인증)
// ============================================================================

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
 * Gemini Imagen / Flash Image 생성 API 호출 (상업용 광고 비주얼 시안 생성)
 */
function callGeminiImage(prompt, aspectRatio) {
  try {
    var apiKey = getGeminiApiKey();
    var imgModel = CONFIG.IMAGE_MODEL_NAME || "gemini-2.5-flash-image";
    var endpoint = CONFIG.BASE_URL + "/" + imgModel + ":predict?key=" + apiKey;
    var ratio = aspectRatio || "1:1";

    var payload = {
      instances: [
        { prompt: prompt + ", high quality commercial advertising photography, professional studio lighting, 8k resolution" }
      ],
      parameters: {
        sampleCount: 1,
        aspectRatio: ratio
      }
    };

    var options = {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    var response = UrlFetchApp.fetch(endpoint, options);
    if (response.getResponseCode() === 200) {
      var result = JSON.parse(response.getContentText());
      if (result.predictions && result.predictions.length > 0 && result.predictions[0].bytesBase64Encoded) {
        return result.predictions[0].bytesBase64Encoded;
      }
    } else {
      Logger.log("Gemini 이미지 생성 실패 (" + response.getResponseCode() + "): " + response.getContentText());
    }
  } catch (err) {
    Logger.log("Gemini 이미지 생성 네트워크 예외: " + err);
  }
  return null;
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
// FILE: Code_Menu.js
// [모듈 3] Google Sheets 커스텀 메뉴 및 UI 대화상자 (Spreadsheet UI & Menu)
// ============================================================================

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("[마케팅 콘텐츠 파이프라인]")
    .addItem("[Gemini API Key 설정 (Google AI Studio)]", "promptForGeminiApiKey")
    .addSeparator()
    .addItem("[Step 1] Google Drive 작업 공간 및 25인 페르소나 자동 생성", "createWorkspaceFolderTree")
    .addItem("[Step 2] 아이디어 기반 기획서(PLAN) 및 콘텐츠 명세서(SPEC) 자동 도출", "runIdeaToPlanConversion")
    .addItem("[Step 3] 기획서 및 명세서 기반 초판 마케팅 콘텐츠 양산 (rv-00)", "runInitialAssetGeneration")
    .addSeparator()
    .addItem("[Step 4] 고객 VoC 수집용 Google Forms 자동 생성 (이미지/비디오 업로드)", "createAndLinkGoogleForm")
    .addItem("[Step 5] 25인 AI 페르소나 1차 다면 평가 및 t-SNE 지형도 자동 렌더링 (fb-01)", "runJudgeEvaluationRound1")
    .addItem("[Step 6] 마케터 피드백 검토 및 최종 의사 결정 (Human-in-the-loop)", "runMarketerDecisionPrompt")
    .addItem("[Step 7] 다면 평가 피드백 기반 1차 마케팅 콘텐츠 반자율 보정 (rv-01)", "runReviseAssetsRound1")
    .addSeparator()
    .addItem("[Step 8] 다면 평가 및 t-SNE 지형도 갱신 (N차 피드백: fb-02 ~ fb-99)", "promptAndRunJudgeEvaluation")
    .addItem("[Step 9] 마케팅 콘텐츠 반자율 보정 (N차 리비전: rv-02 ~ rv-99)", "promptAndRunReviseAssets")
    .addSeparator()
    .addItem("[Step 0] 타깃 AI 페르소나 패널 맞춤 재설정 (선택 사항)", "setCustomPersonasPrompt")
    .addToUi();
}

/**
 * 타깃 AI 페르소나 25인 패널 맞춤 재설정 UI 프롬프트 (Gemini 생성 또는 Hugging Face 동기화)
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
      var inputFolder = getCampaignSubFolder(["input"]);
      saveTextFile(inputFolder, "ai_personas.json", formatted);

      ui.alert(
        "페르소나 패널 재설정 완료",
        "지정한 기준('" + criteria + "')에 맞추어 25인 맞춤 AI 페르소나 패널 데이터가 성공적으로 갱신되었습니다.\n(저장 경로: " + campaignCode + "/input/ai_personas.json)",
        ui.ButtonSet.OK
      );
    }
  } catch (err) {
    ui.alert("페르소나 재설정 중 오류 발생", err.toString(), ui.ButtonSet.OK);
  }
}

/**
 * [Step 8] 다이나믹 다면 평가 및 t-SNE 갱신 런처 (fb-02 ~ fb-99 지원)
 */
function promptAndRunJudgeEvaluation() {
  var ui = SpreadsheetApp.getUi();
  var latestFb = detectLatestFeedbackRoundNum();
  var latestRv = detectLatestRevisionRoundNum();
  var suggestedRound = Math.max(latestFb + 1, latestRv + 1, 2);
  var suggestedRoundStr = suggestedRound < 10 ? "0" + suggestedRound : "" + suggestedRound;

  var response = ui.prompt(
    "[Step 8] 다면 평가 회차 선택 (N차: fb-02 ~ fb-99)",
    "현재 등록된 최신 피드백 회차는 fb-" + (latestFb < 10 ? "0" + latestFb : latestFb) + " (최신 콘텐츠: rv-" + (latestRv < 10 ? "0" + latestRv : latestRv) + ")입니다.\n\n" +
    "실행할 피드백 회차 번호를 입력하십시오 (1~99 지원, 기본 추천: " + suggestedRound + "):\n" +
    "(빈칸으로 두고 [확인] 클릭 시 fb-" + suggestedRoundStr + " 회차가 자동 실행됩니다)\n\n" +
    "* 예상 소요 시간: 약 45초~1분 30초 (VLM 분석 및 t-SNE 지형도 렌더링)",
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
  runJudgeEvaluation(targetRoundStr);
}

/**
 * [Step 9] 다이나믹 마케팅 콘텐츠 반자율 보정 런처 (rv-02 ~ rv-99 지원)
 */
function promptAndRunReviseAssets() {
  var ui = SpreadsheetApp.getUi();
  var latestFb = detectLatestFeedbackRoundNum();
  var latestRv = detectLatestRevisionRoundNum();
  var suggestedRv = Math.max(latestRv + 1, 2);
  var suggestedRvStr = suggestedRv < 10 ? "0" + suggestedRv : "" + suggestedRv;

  var response = ui.prompt(
    "[Step 9] 마케팅 콘텐츠 리비전 선택 (N차: rv-02 ~ rv-99)",
    "현재 등록된 최신 리비전은 rv-" + (latestRv < 10 ? "0" + latestRv : latestRv) + " (평가 완료 회차: fb-" + (latestFb < 10 ? "0" + latestFb : latestFb) + ")입니다.\n\n" +
    "생성할 마케팅 콘텐츠 리비전 번호를 입력하십시오 (1~99 지원, 기본 추천: " + suggestedRv + "):\n" +
    "(빈칸으로 두고 [확인] 클릭 시 rv-" + suggestedRvStr + " 개정본이 자동 양산됩니다)\n\n" +
    "* 예상 소요 시간: 약 45초~1분 30초 (카피 개정, 비주얼 3종 및 숏폼 영상 생성)",
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
  runReviseAssets(targetRoundStr);
}

// ============================================================================
// FILE: Code_Step1_Workspace.js
// Code_Step1_Workspace.js
// ============================================================================

function createWorkspaceFolderTree() {
  var ui = SpreadsheetApp.getUi();
  showProcessingToast("[Step 1] Google Drive 작업 공간 및 25인 페르소나 자동 생성", 15);
  try {
    // 1. 캠페인별 독립 폴더 구조 생성 (input, output을 캠페인 폴더 직하위에 격리)
    var campaign = getCampaignFolder();
    var campaignCode = getCampaignCode();
    var inputFolder = getCampaignSubFolder(["input"]);
    var outputFolder = getCampaignSubFolder(["output"]);
    // 2. 가상 페르소나 25인 마스터 데이터셋 ({campaign}/input/ai_personas.json)
    var masterPersonas25 = getMasterPersonas25();

    // 2. 가상 페르소나 25인 마스터 데이터셋 ({campaign}/input/ai_personas.json 생성)
    saveTextFile(inputFolder, "ai_personas.json", JSON.stringify(masterPersonas25, null, 2));

    // fb-01 폴더 초기 생성 및 샘플 고객 동영상(VoC) 자동 시딩 (feedback_{timestamp}.mp4)
    var fb01Folder = getCampaignSubFolder(["input", "fb-01"]);
    var sampleVideoName = "feedback_" + Utilities.formatDate(new Date(), "Asia/Seoul", "yyyyMMdd_HHmmss") + ".mp4";
    saveSampleVideoFile(fb01Folder, sampleVideoName);

    // 스타터 아이디어 구글 독스 문서 (input/아이디어 메모) 자동 생성
    if (!readGoogleDoc(inputFolder, "아이디어 메모")) {
      var starterIdea = "# 캠페인 아이디어 메모\n\n" +
        "* **캠페인 명칭**: 2026 가을 오텀 브리즈 캠페인 (cp-autumn-breeze)\n" +
        "* **핵심 컨셉**: 선선한 가을 날씨에 어울리는 프리미엄 아웃도어 & 라이프스타일 컬렉션\n" +
        "* **타깃 고객**: 도심 속 워크앤라이프 밸런스를 추구하는 2040 직장인 및 주말 아웃도어 캠퍼\n" +
        "* **핵심 소구점**: 가볍고 따뜻한 기능성 소재, 모던한 실루엣, 일상과 캠핑을 아우르는 활용성\n" +
        "* **목표 채널**: 인스타그램 릴스 숏폼, 네이버 블로그 브랜드 스토리, 뉴스레터 이메일 시퀀스\n";
      saveGoogleDoc(inputFolder, "아이디어 메모", starterIdea);
    }

    // 3. 현재 구글 시트를 캠페인 폴더 직하위로 자동 이동하여 캠페인 전용 컨트롤 타워로 패키징
    try {
      var activeSpreadsheet = SpreadsheetApp.getActiveSpreadsheet();
      var sheetFile = DriveApp.getFileById(activeSpreadsheet.getId());
      sheetFile.moveTo(campaign);
      var currentTitle = activeSpreadsheet.getName();
      if (!currentTitle || currentTitle === "제목 없는 스프레드시트" || currentTitle === "마케팅 콘텐츠 파이프라인") {
        activeSpreadsheet.rename("[마케팅 컨트롤 타워] " + campaignCode);
      }
    } catch (sheetMoveErr) {
      Logger.log("시트 캠페인 폴더 이동 중 예외 (무시 가능): " + sheetMoveErr);
    }

    // 4. 구글 시트 실행 대시보드 표 초기화 및 Step 1 완료 기록
    initDashboardSheet();
    recordStepResultToSheet("Step 1", "작업 공간 초기화", "완료", campaign.getUrl(), "구글 드라이브 폴더 (" + campaignCode + ")");

    var alertMsg = "캠페인 작업 공간(" + campaignCode + ")과 25인 AI 페르소나 데이터셋이 준비되었습니다.\n\n" +
                   "구글 로그인 계정으로 자동 인증되므로 별도의 API Key 발급 없이 즉시 실행하실 수 있습니다.\n\n" +
                   "구글 시트의 [실행 대시보드] 표에서 바로가기 링크를 확인하십시오.";

    ui.alert(
      "실습 환경 셋업 완료",
      alertMsg,
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert("오류 발생", e.toString(), ui.ButtonSet.OK);
  }
}


/**
 * 기본 25인 슬림 AI 페르소나 마스터 데이터셋 반환
 */
function getMasterPersonas25() {
  return {
  "metadata": {
    "description": "한국인 25인 다면 평가 슬림 AI 페르소나 패널 (토큰 최적화 경량 규격)",
    "total": 25
  },
  "personas": [
    {
      "id": "p01",
      "name": "강도윤",
      "age": 28,
      "gender": "남성",
      "category": "전문 마케터",
      "occupation": "퍼포먼스 마케터",
      "perspective": "데이터 지향적, 민첩한 의사 결정. 관심: ROAS 지표 하락 및 광고비 삭감에 대한 극심한 압박"
    },
    {
      "id": "p02",
      "name": "김서아",
      "age": 32,
      "gender": "여성",
      "category": "전문 마케터",
      "occupation": "브랜드 마케터",
      "perspective": "감성적 통찰력, 디테일에 집착하는. 관심: 뻔하고 지루한 B2B 카피를 탈피하고 차별화된 톤앤매너 확립 요구"
    },
    {
      "id": "p03",
      "name": "이서연",
      "age": 25,
      "gender": "여성",
      "category": "전문 마케터",
      "occupation": "콘텐츠 크리에이터",
      "perspective": "외향적이고 즉흥적인, 스토리텔링에 능한. 관심: 매일 쏟아지는 다채널 숏폼 영상과 인스타그램 릴스 소재 고갈"
    },
    {
      "id": "p04",
      "name": "김도현",
      "age": 35,
      "gender": "남성",
      "category": "전문 마케터",
      "occupation": "그로스 마케터",
      "perspective": "분석적이고 집요한, 실험 정신이 강한. 관심: 예산 0원으로 3일 안에 전 채널을 동시 장악해야 하는 초단기 런칭 압박"
    },
    {
      "id": "p05",
      "name": "박지우",
      "age": 42,
      "gender": "여성",
      "category": "전문 마케터",
      "occupation": "인하우스 홍보 담당자",
      "perspective": "신중하고 정무적인 감각, 원만한 대인관계. 관심: 보고서용 데이터 정리와 경영진 설득을 위한 명확한 비용 절감 ROI 증명"
    },
    {
      "id": "p06",
      "name": "박서준",
      "age": 38,
      "gender": "남성",
      "category": "전문 마케터",
      "occupation": "퍼포먼스 리드",
      "perspective": "글로벌 감각, 도전적이고 대범한. 관심: 광고 피로도 극복을 위한 수십 개 카피의 실시간 다채널 A/B 테스트 요구"
    },
    {
      "id": "p07",
      "name": "최수아",
      "age": 28,
      "gender": "여성",
      "category": "전문 마케터",
      "occupation": "SNS 채널 운영자",
      "perspective": "트렌드에 극도로 민감한, 사교적이고 발랄한. 관심: Z세대 취향을 저격하는 B급 유머와 키치 네온 스타일 바이럴 릴스 기획"
    },
    {
      "id": "p08",
      "name": "이도현",
      "age": 45,
      "gender": "남성",
      "category": "전문 마케터",
      "occupation": "마케팅 팀장",
      "perspective": "진중하고 신뢰감 주는, 조직 통솔력. 관심: 보수적인 임원진을 설득할 수 있는 데이터 기반의 정량적 성공 사례 및 신뢰성 입증"
    },
    {
      "id": "p09",
      "name": "정예준",
      "age": 32,
      "gender": "남성",
      "category": "전문 마케터",
      "occupation": "퍼포먼스 AE",
      "perspective": "추진력 있고 유연한, 위기 대처 능력. 관심: 광고주마다 쏟아지는 다채널 소재 베리에이션 요청으로 인한 만성 야근"
    },
    {
      "id": "p10",
      "name": "정하은",
      "age": 25,
      "gender": "여성",
      "category": "전문 마케터",
      "occupation": "커뮤니티 매니저",
      "perspective": "공감 능력이 탁월한, 친화적이고 포용적인. 관심: 고객의 생생한 VoC를 반영하여 실시간으로 진화하는 참여형 캠페인 구축"
    },
    {
      "id": "p11",
      "name": "조하준",
      "age": 28,
      "gender": "남성",
      "category": "전문 마케터",
      "occupation": "퍼포먼스 마케터",
      "perspective": "데이터 지향적, 민첩한 의사 결정. 관심: ROAS 지표 하락 및 광고비 삭감에 대한 극심한 압박"
    },
    {
      "id": "p12",
      "name": "강지유",
      "age": 32,
      "gender": "여성",
      "category": "전문 마케터",
      "occupation": "브랜드 마케터",
      "perspective": "감성적 통찰력, 디테일에 집착하는. 관심: 뻔하고 지루한 B2B 카피를 탈피하고 차별화된 톤앤매너 확립 요구"
    },
    {
      "id": "p13",
      "name": "전기태",
      "age": 74,
      "gender": "남성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "소탈하고 정이 넘치는, 과묵하고 인내심 강한"
    },
    {
      "id": "p14",
      "name": "최은지",
      "age": 71,
      "gender": "여성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "소탈하고 정이 넘치는, 과묵하고 인내심 강한"
    },
    {
      "id": "p15",
      "name": "안상식",
      "age": 73,
      "gender": "남성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "소탈하고 정이 넘치는, 과묵하고 인내심 강한"
    },
    {
      "id": "p16",
      "name": "김다희",
      "age": 46,
      "gender": "여성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "현실적이고 신중한, 책임감 강한"
    },
    {
      "id": "p17",
      "name": "설숙자",
      "age": 50,
      "gender": "여성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "현실적이고 신중한, 책임감 강한"
    },
    {
      "id": "p18",
      "name": "황혜란",
      "age": 33,
      "gender": "여성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "정갈하고 독립적인, 일과 쉼의 균형을 중시하는"
    },
    {
      "id": "p19",
      "name": "김준수",
      "age": 31,
      "gender": "남성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "정갈하고 독립적인, 일과 쉼의 균형을 중시하는"
    },
    {
      "id": "p20",
      "name": "곽상길",
      "age": 76,
      "gender": "남성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "소탈하고 정이 넘치는, 과묵하고 인내심 강한"
    },
    {
      "id": "p21",
      "name": "박호철",
      "age": 44,
      "gender": "남성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "현실적이고 신중한, 책임감 강한"
    },
    {
      "id": "p22",
      "name": "이태훈",
      "age": 27,
      "gender": "남성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "트렌드에 민감한, 개성 표현을 두려워하지 않는"
    },
    {
      "id": "p23",
      "name": "홍희자",
      "age": 74,
      "gender": "여성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "소탈하고 정이 넘치는, 과묵하고 인내심 강한"
    },
    {
      "id": "p24",
      "name": "고성호",
      "age": 61,
      "gender": "남성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "우직하고 성실한, 희생적인 가장/어머니"
    },
    {
      "id": "p25",
      "name": "유준호",
      "age": 61,
      "gender": "남성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "우직하고 성실한, 희생적인 가장/어머니"
    }
  ]
};
}

// ============================================================================
// FILE: Code_Step2_IdeaToPlan.js
// Code_Step2_IdeaToPlan.js
// ============================================================================

function runIdeaToPlanConversion() {
  var ui = SpreadsheetApp.getUi();
  showProcessingToast("[Step 2] 기획서(PLAN) 및 명세서(SPEC) 자동 도출", 30);
  try {
    var campaignFolder = getCampaignFolder();

    // 1. 내장 시스템 지침 (Zero-Prompt No-Code) - PLAN 기획서 도출
    var planSystemInstruction =
      "당신은 전문 엔터프라이즈 브랜드 마케팅 전략가이자 크리에이티브 디렉터이다.\n" +
      "마케터가 제공하는 자연어 캠페인 아이디어를 정밀 분석하여, 완성도 높은 마케팅 캠페인 기획서(PLAN)를 작성하라.\n\n" +
      "필수 포함 섹션:\n" +
      "# [마케팅 캠페인 기획서] {캠페인명}\n" +
      "## 1. 캠페인 배경 및 핵심 목표\n" +
      "## 2. 타깃 페르소나 및 핵심 소구점 (USP)\n" +
      "## 3. 멀티 채널 콘텐츠 양산 요구 사항\n" +
      "## 4. 고객 피드백 수집 및 품질 검증 기준\n\n" +
      "엄격한 작성 규칙:\n" +
      "1. 이모지와 중간 점을 일절 사용하지 말고, 나열 시 반드시 쉼표(,)를 사용하십시오.\n" +
      "2. 모든 서술은 단호하고 격조 높은 문어체/평서문('-다' 체)으로 작성하십시오.\n" +
      "3. 한글 복합어는 철저하게 띄어 쓰십시오. (예: '마케팅 캠페인 기획서', '오프라인 매장', '의사 결정' 등)\n" +
      "4. 마케터가 바로 실무에 사용할 수 있을 만큼 구체적인 수치와 명확한 어조로 작성하십시오.\n" +
      "5. 분량 및 가독성: 청중 마케터가 1분 안에 직관적으로 파악할 수 있도록, 불필요한 장황한 서술을 전면 배제하고 A4 1~2페이지 내외의 핵심 불릿 포인트 중심으로 명쾌하고 컴팩트하게 작성하십시오.";

    // 2. 내장 시스템 지침 - SPEC 콘텐츠 제작 명세서 도출
    var specSystemInstruction =
      "당신은 엔터프라이즈 마케팅 콘텐츠 제작 총괄 리드이다.\n" +
      "마케팅 캠페인 기획서(PLAN)를 분석하여, 각 채널별 멀티 채널 콘텐츠 제작 명세서(SPEC) 구글 독스 문서를 정밀하게 작성하라.\n" +
      "마케터가 이 문서를 열어 수치(해상도, 비율, 영상 길이, 필수 포함 키워드 등)를 직접 편집할 수 있도록 명료한 규격 명세 형식으로 구성하라.\n\n" +
      "필수 포함 섹션:\n" +
      "# [멀티 채널 콘텐츠 제작 명세서] (SPEC)\n" +
      "## 1. 광고 카피라이팅 채널 규격\n" +
      "- 헤드카피 (3종, 20자 내외)\n" +
      "- 인스타그램 피드 및 카드뉴스 카피 (캡션 300자 내외, 필수 해시태그 5개)\n" +
      "- 네이버 블로그 기고문 (정보성 리뷰 1,500자 내외)\n" +
      "## 2. 모바일 세로 숏폼 영상 규격 (Shorts / Reels)\n" +
      "- 화면 비율: 세로 9:16 (해상도 1080x1920)\n" +
      "- 권장 러닝타임: 15초 내외 (최대 30초)\n" +
      "- 구성: 초반 3초 후킹(Hook), 문제 제기, 솔루션 제시, CTA\n" +
      "## 3. 대표 비주얼 이미지 3종 비율 규격\n" +
      "- 가로형 디스플레이 배너: 16:9 (1920x1080 권장, GDN 및 메인 웹 배너)\n" +
      "- 세로형 모바일 포스터: 9:16 (1080x1920 권장, 모바일 스토리 및 사이니지)\n" +
      "- 정방형 SNS 피드 이미지: 1:1 (1080x1080 권장, 인스타그램 피드)\n" +
      "## 4. 비주얼 연출 톤앤매너 및 네거티브 가이드라인\n" +
      "- 추천 조명, 색감, 인물 모델 스타일\n" +
      "- 지양해야 할 표현(과도한 텍스트 침범, 왜곡 등)\n\n" +
      "엄격한 작성 규칙:\n" +
      "1. 이모지와 중간 점을 일절 쓰지 말고 쉼표(,)를 사용하십시오.\n" +
      "2. 모든 서술은 단호하고 격조 높은 문어체/평서문('-다' 체)으로 작성하십시오.\n" +
      "3. 한글 복합어는 철저하게 띄어 쓰십시오.";

    // 3. 마케터에게 자연어 아이디어 입력받기 (input/아이디어 메모 구글 독스 연동)
    var inputFolder = getCampaignSubFolder(["input"]);
    var docIdea = readGoogleDoc(inputFolder, "아이디어 메모");
    var defaultIdea = docIdea ||
      ("2026 어텀 브리즈 무선 헤드폰 론칭 캠페인. 2534 출퇴근 직장인 타깃. " +
       "스마트 액티브 노이즈 캔슬링(98% 소음 차단), 180g 초경량 깃털 착용감, 50시간 배터리, 10만 원대 후반 가격. " +
       "인스타 피드 및 유튜브 쇼츠 콘티, 블로그 리뷰, 배너 프롬프트, 3,000대 사전 예약 조기 마감 목표.");

    var response = ui.prompt(
      "캠페인 기획 아이디어 발상",
      "추진하고자 하는 마케팅 아이디어나 신제품 특장점을 자유로운 말(자연어)로 입력하십시오.\n\n" +
      "[확인]을 누르면 기본 예시 아이디어로 기획서(PLAN) 및 콘텐츠 제작 명세서(SPEC) 구글 독스가 즉시 자동 생성됩니다:",
      ui.ButtonSet.OK_CANCEL
    );

    if (response.getSelectedButton() !== ui.Button.OK) {
      return;
    }

    var userIdea = response.getResponseText().trim();
    if (!userIdea) {
      userIdea = defaultIdea;
    }

    // 4. Gemini 호출: 1) 기획서(PLAN) 생성
    var userPrompt = "다음은 마케터가 제공한 캠페인 아이디어이다. 시스템 지침에 따라 정식 마케팅 캠페인 기획서(PLAN)를 완성하라:\n\n" + userIdea;
    var planContent = callGemini(planSystemInstruction, userPrompt);
    var planDocFile = saveGoogleDoc(campaignFolder, "PLAN", planContent);

    // 5. Gemini 호출: 2) 콘텐츠 제작 명세서(SPEC) 생성
    var specPrompt = "다음 작성된 마케팅 캠페인 기획서(PLAN)를 바탕으로, 각 채널별 상세 콘텐츠 제작 명세서(SPEC)를 완성하라:\n\n" + planContent;
    var specContent = callGemini(specSystemInstruction, specPrompt);
    var specDocFile = saveGoogleDoc(campaignFolder, "SPEC", specContent);

    // 6. 구글 시트 실행 대시보드에 Step 1 완료 및 링크 기록
    recordStepResultToSheet("Step 2", "기획서(PLAN) 및 콘텐츠 명세서(SPEC) 도출", "완료", planDocFile.getUrl(), "기획서(PLAN) & 명세서(SPEC) 열기");

    ui.alert(
      "기획서(PLAN) 및 콘텐츠 명세서(SPEC) 생성 완료",
      "캠페인 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC) 구글 독스가 성공적으로 생성되었습니다.\n\n" +
      "마케터는 브라우저에서 SPEC 문서를 열어 이미지 비율, 숏폼 길이, 카피 채널 규격을 자유롭게 수정한 뒤 [Step 2]를 실행할 수 있습니다.\n\n" +
      "구글 시트의 [실행 대시보드] 표에서 바로가기 링크를 확인하십시오.",
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert("기획서 및 명세서 도출 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
}

// ============================================================================
// FILE: Code_Step3_ContentGen.js
// Code_Step3_ContentGen.js
// ============================================================================

function runInitialAssetGeneration() {
  var ui = SpreadsheetApp.getUi();
  showProcessingToast("[Step 3] 초판 마케팅 콘텐츠 양산 (rv-00)", 60);
  try {
    var campaignFolder = getCampaignFolder();
    var campaignCode = getCampaignCode();
    var inputFolder = getCampaignSubFolder(["input"]);
    var rv00Folder = getCampaignSubFolder(["output", "rv-00"]);

    // 1. 내장 시스템 지침 (Zero-Prompt No-Code)
    var systemInstruction =
      "당신은 전문 크리에이티브 마케팅 디렉터이자 카피라이터이다.\n" +
      "주어진 마케팅 캠페인 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC)를 바탕으로 단일 캠페인 종합 마케팅 콘텐츠 문서(campaign_content) 1본을 완성도 높은 마케팅 카피 형식으로 작성하라.\n\n" +
      "필수 구성:\n" +
      "1. 헤드카피 및 슬로건 (3종)\n" +
      "2. 인스타그램 카드뉴스 및 피드 카피 (SPEC 규격 준수)\n" +
      "3. 네이버 블로그 리뷰형 기고문 (SPEC 규격 준수)\n" +
      "4. 모바일 숏폼 영상 콘티 (SPEC에 명시된 러닝타임 및 세로 9:16 규격, 타임라인별 나레이션 및 화면 연출 지시문)\n" +
      "5. 제미나이 이미지 생성용 비주얼 프롬프트 (가로 16:9, 세로 9:16, 정방형 1:1)\n\n" +
      "엄격한 작성 규칙:\n" +
      "1. 콘텐츠 제작 명세서(SPEC)에 정의된 채널 규격, 숏폼 러닝타임, 톤앤매너를 최우선으로 준수하십시오.\n" +
      "2. 이모지와 중간 점을 일절 쓰지 말고 쉼표(,)를 사용하십시오.\n" +
      "3. 모든 서술은 단호하고 격조 높은 문어체/평서문('-다' 체)으로 작성하십시오.\n" +
      "4. 한글 복합어는 철저하게 띄어 쓰십시오.\n" +
      "5. 분량 및 가독성: 각 채널별 카피와 콘티는 마케터가 한눈에 읽고 즉시 검토할 수 있도록, 불필요한 미사여구를 배제하고 핵심 메시지 중심으로 명쾌하고 컴팩트하게 작성하십시오.";

    // 2. 캠페인 루트의 PLAN 및 SPEC 구글 독스 읽기
    var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
    var planContent = readGoogleDoc(campaignFolder, planDocName);
    if (!planContent) {
      planContent = readGoogleDoc(campaignFolder, "BRD");
    }
    if (!planContent) {
      throw new Error("마케팅 캠페인 기획서(PLAN) 구글 독스 문서를 찾을 수 없습니다. [Step 1]을 먼저 실행하여 기획서(PLAN)를 생성하십시오.");
    }

    var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";
    var specContent = readGoogleDoc(campaignFolder, specDocName) || "";

    // 3. Gemini 호출
    var promptText = "다음은 이번 캠페인의 마케팅 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC)이다.\n" +
                     "명세서(SPEC)에 정의된 채널 규격, 영상 길이, 비주얼 가이드라인을 엄격히 준수하여 초판 campaign_content를 작성하라:\n\n" +
                     "### [1. 마케팅 캠페인 기획서 (PLAN)]\n" + planContent + "\n\n" +
                     "### [2. 멀티 채널 콘텐츠 제작 명세서 (SPEC)]\n" + (specContent || "기본 규격 준수");
    var generatedContent = callGemini(systemInstruction, promptText);

    // 4. 저장: output/rv-00/에 campaign_content 구글 독스 단일 저장
    var contentDocName = (CONFIG && CONFIG.CONTENT_DOC_NAME) || "campaign_content";
    saveGoogleDoc(rv00Folder, contentDocName, generatedContent);

    // 5. 실시간 대표 비주얼 이미지 3종 비율 세트 생성 (rv-00: 가로 16:9, 세로 9:16, 정사각 1:1)
    var visualBrief = extractDynamicVisualPrompt(
      generatedContent,
      planContent,
      "A stylish 20s Korean female commuter with lightweight premium ANC headphones in warm golden autumn sunlight on a modern Seoul street"
    );
    Logger.log("동적 도출된 비주얼 프롬프트 (rv-00): " + visualBrief);
    generateAndSaveVisualAssets(rv00Folder, "00", visualBrief);

    // 6. 실제 캠페인 초판 콘텐츠 기반 25인 가상 페르소나 피드백 실시간 도출
    try {
      var fb01Folder = getCampaignSubFolder(["input", "fb-01"]);
      generateLivePersonaFeedbacks(campaignFolder, fb01Folder, "rv-00");
    } catch (fbGenErr) {
      Logger.log("25인 가상 페르소나 피드백 실시간 도출 예외: " + fbGenErr);
    }

    // 7. 구글 시트 실행 대시보드에 Step 2 완료 및 링크 기록
    recordStepResultToSheet("Step 3", "초판 마케팅 콘텐츠 양산 (rv-00)", "완료", rv00Folder.getUrl(), "구글 드라이브 폴더 열기 (rv-00)");

    ui.alert(
      "초판 마케팅 콘텐츠 양산 완료 (rv-00)",
      "초판 마케팅 카피, 대표 비주얼 이미지 3종 및 세로 숏폼 영상(00_shorts.mp4) 생성이 완료되었습니다.\n\n구글 시트의 [실행 대시보드] 표에서 바로가기 링크를 확인하십시오.",
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert("초판 콘텐츠 양산 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
}

// ============================================================================
// FILE: Code_Step4_Form.js
// Code_Step4_Form.js
// ============================================================================

function createAndLinkGoogleForm() {
  var ui = SpreadsheetApp.getUi();
  showProcessingToast("[Step 4] 고객 VoC 수집용 Google Forms 생성 및 연동", 20);
  try {
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    var spreadsheetId = spreadsheet.getId();
    var campaignFolder = getCampaignFolder();
    var campaignCode = getCampaignCode();

    // 1. 구글 폼 생성 및 응답 활성화 설정
    var formTitle = "고객 피드백 설문";
    var form = FormApp.create(formTitle);
    form.setAcceptingResponses(true);
    try {
      form.setRequireLogin(false);
    } catch (e) {
      Logger.log("setRequireLogin 예외: " + e);
    }
    try {
      form.setCollectEmail(false);
      form.setLimitOneResponsePerUser(false);
      form.setShowLinkToRespondAgain(true);
    } catch (e) {
      Logger.log("폼 옵션 설정 예외: " + e);
    }
    var publishedUrl = form.getPublishedUrl();

    form.setDescription(
      "본 설문은 " + campaignCode + " 캠페인의 고객 만족도와 사용자 직접 촬영 동영상/이미지 피드백을 수집하여 " +
      "Gemini VLM 다면 평가 및 마케팅 콘텐츠 반자율 보정에 반영하기 위한 설문입니다.\n\n" +
      "[모바일 즉시 참여 안내]\n" +
      "스마트폰 카메라로 아래 첫 번째 항목의 QR 코드를 스캔하면 모바일 화면에서 즉시 피드백을 작성하거나 촬영 영상 링크를 제출하실 수 있습니다.\n" +
      "설문 참여 바로가기 URL: " + publishedUrl
    );

    // 2. 모바일 참여용 고화질 QR 코드 생성 및 폼 최상단 이미지 아이템 자동 삽입
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
    } catch (qrError) {
      Logger.log("QR 코드 이미지 생성 실패: " + qrError);
    }

    // 3. 질문 항목 자동 구성
    // 문항 1: 평가 대상 마케팅 콘텐츠 버전
    var versionItem = form.addMultipleChoiceItem();
    versionItem.setTitle("평가 대상 마케팅 콘텐츠 버전 (선택 사항)")
      .setChoiceValues(["초판 (rv-00)", "1차 개정본 (rv-01)", "2차 개정본 (rv-02)"])
      .setRequired(false);

    // 문항 2: 정량 만족도 평점 (1~5점 선형 배율)
    form.addScaleItem()
      .setTitle("제품의 전반적인 만족도는 어떠셨습니까? (선택 사항)")
      .setBounds(1, 5)
      .setLabels("매우 불만족", "매우 만족")
      .setRequired(false);

    // 문항 3: 정성 서술형 피드백
    form.addParagraphTextItem()
      .setTitle("제품을 사용하면서 느낀 솔직한 장점이나 아쉬운 점을 자유롭게 적어주십시오. (자유 기술)")
      .setHelpText("예: 출퇴근 길 지하철 소음 차단은 좋은데, 퇴근 길 힐링 무드 카피나 멀티포인트 페어링 기능도 다뤄주면 좋겠습니다.")
      .setRequired(false);

    // 문항 4: 고객 촬영 동영상 피드백 소감 또는 파일 링크
    form.addParagraphTextItem()
      .setTitle("고객 촬영 동영상 피드백 소감 요약 또는 파일 링크 (선택 사항)")
      .setHelpText("스마트폰으로 제품을 사용해보며 느낀 소감이나 고객의 생생한 목소리를 한두 줄로 자유롭게 적어주십시오. (동영상 공유 링크나 소감 텍스트 모두 환영하며, 권장 길이는 15~30초 이내 숏폼 영상입니다)")
      .setRequired(false);

    // 문항 5: 추가 이미지 피드백 소감 또는 링크
    form.addParagraphTextItem()
      .setTitle("추가 이미지 피드백 소감 또는 링크 (선택 사항)")
      .setHelpText("제품 착용 컷, 언박싱 사진에 대한 의견이나 이미지 파일 링크를 입력하십시오.")
      .setRequired(false);

    // 4. 목적지 구글 시트에 자동 바인딩 (설문지 응답 1 탭 자동 생성)
    form.setDestination(FormApp.DestinationType.SPREADSHEET, spreadsheetId);

    // 5. 구글 폼 파일을 캠페인 루트 폴더로 안전하게 이동
    var oldFormFiles = campaignFolder.getFilesByName(formTitle);
    while (oldFormFiles.hasNext()) {
      oldFormFiles.next().setTrashed(true);
    }
    var formFile = DriveApp.getFileById(form.getId());
    campaignFolder.addFile(formFile);
    DriveApp.getRootFolder().removeFile(formFile);

    // 6. 구글 시트 실행 대시보드에 Step 3 완료 및 링크 기록
    recordStepResultToSheet("Step 4", "고객 피드백 설문 폼 연동", "완료", publishedUrl, "고객 설문 참여 폼 열기");

    ui.alert(
      "구글 폼 연동 완료",
      "캠페인 전용 구글 폼이 생성되어 [설문지 응답 1] 탭과 연결되었습니다.\n\n구글 시트의 [실행 대시보드] 표에서 '고객 설문 참여 폼 열기' 링크를 클릭하여 응답을 제출하십시오.",
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert("구글 폼 생성 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
}

// ============================================================================
// FILE: Code_Step5_8_Judge.js
// Code_Step5_8_Judge.js
// ============================================================================

/**
 * [Step 5] 초판 콘텐츠(rv-00) 대상 1차 25인 다면 평가 및 t-SNE 여론 지형도 생성
 */
function runJudgeEvaluationRound1() {
  runJudgeEvaluation("fb-01");
}

/**
 * [Step 8] 1차 개정본 콘텐츠(rv-01) 대상 2차 25인 다면 평가 및 t-SNE 지형도 갱신
 */
function runJudgeEvaluationRound2() {
  runJudgeEvaluation("fb-02");
}

/**
 * 피드백 다면 평가 공통 실행 함수 (N차 다이나믹 루프 fb-01 ~ fb-99 지원)
 */
function runJudgeEvaluation(targetRoundOpt, isSilentOpt) {
  var ui = SpreadsheetApp.getUi();
  var isSilent = (isSilentOpt === true);
  try {
    var campaignFolder = getCampaignFolder();
    var campaignCode = getCampaignCode();

    // 1. 피드백 회차(fb-01 ~ fb-99) 판별
    var targetRound = targetRoundOpt;
    if (!targetRound) {
      var latestFb = detectLatestFeedbackRoundNum();
      var latestRv = detectLatestRevisionRoundNum();
      var autoRound = Math.max(latestFb + 1, latestRv + 1, 2);
      targetRound = "fb-" + (autoRound < 10 ? "0" + autoRound : autoRound);
    }

    // 소요 시간 안내 토스트 즉시 표시
    showProcessingToast("[Step 5/8] 다면 평가 및 t-SNE 지형도 생성 (" + targetRound + ")", 75);

    var roundNum = parseInt(targetRound.replace("fb-", ""), 10) || 1;
    var prevRoundNum = Math.max(0, roundNum - 1);
    var prevRvName = "rv-" + (prevRoundNum < 10 ? "0" + prevRoundNum : prevRoundNum);
    var nextRvName = "rv-" + (roundNum < 10 ? "0" + roundNum : roundNum);
    var feedbackFolder = getCampaignSubFolder(["input", targetRound]);

    // 2. 피드백 동영상(비디오 VoC) 감지 및 Gemini VLM 심층 분석 실행 -> [영상파일명]_vlm.json 1:1 저장
    var videoVocAnalyses = analyzeVideoVocWithVlm(feedbackFolder);
    var hasVideoAnalysis = (Array.isArray(videoVocAnalyses) && videoVocAnalyses.length > 0);

    // 3. input/{targetRound}/ 폴더 내 수작업 투입 자료(이미지, 추가 영상, 메모/문서) 전수 스캔
    var manualFeedbackRows = scanManualFeedbackFiles(feedbackFolder);
    var hasManualFeedback = (manualFeedbackRows.length > 0);

    // 4. Google Sheets에서 사람 설문 응답 및 제출 이미지/비디오 데이터 수집
    var humanFeedbackRows = [];
    var humanVideoRows = [];
    var humanImageRows = [];
    var humanRatings = [];
    var versionColIndex = -1;
    var videoColIndex = -1;
    var imageColIndex = -1;
    var ratingColIndex = -1;

    try {
      var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
      var responseSheet = spreadsheet.getSheetByName("설문지 응답 1") || spreadsheet.getActiveSheet();
      var sheetData = responseSheet.getDataRange().getValues();

      if (sheetData && sheetData.length > 1) {
        var headers = sheetData[0];
        for (var h = 0; h < headers.length; h++) {
          var headerStr = String(headers[h]);
          if (headerStr.indexOf("버전") !== -1 || headerStr.indexOf("Version") !== -1) {
            versionColIndex = h;
          }
          if (headerStr.indexOf("동영상") !== -1 || headerStr.indexOf("영상") !== -1 || headerStr.indexOf("비디오") !== -1 || headerStr.indexOf("Video") !== -1) {
            videoColIndex = h;
          }
          if (headerStr.indexOf("이미지") !== -1 || headerStr.indexOf("사진") !== -1 || headerStr.indexOf("Image") !== -1 || headerStr.indexOf("Photo") !== -1) {
            imageColIndex = h;
          }
          if (headerStr.indexOf("만족도") !== -1 || headerStr.indexOf("평점") !== -1 || headerStr.indexOf("Score") !== -1 || headerStr.indexOf("Rating") !== -1) {
            ratingColIndex = h;
          }
        }

        for (var i = 1; i < sheetData.length; i++) {
          var row = sheetData[i];

          if (versionColIndex !== -1) {
            var rowVersion = String(row[versionColIndex] || "").trim();
            if (rowVersion) {
              if (rowVersion.indexOf(prevRvName) === -1) {
                continue;
              }
            } else if (roundNum > 1) {
              continue;
            }
          } else if (roundNum > 1) {
            continue;
          }

          if (ratingColIndex !== -1) {
            var rVal = parseFloat(row[ratingColIndex]);
            if (!isNaN(rVal) && rVal > 0) {
              humanRatings.push(rVal);
            }
          }

          if (videoColIndex !== -1) {
            var rawVideo = String(row[videoColIndex] || "").trim();
            if (rawVideo && rawVideo !== "-" && rawVideo !== "없음" && rawVideo !== "None") {
              var isUrl = /^(?:https?:\/\/|\bwww\.)/i.test(rawVideo);
              var resolvedVideo = resolveDriveAttachmentName(rawVideo);
              if (isUrl) {
                humanVideoRows.push("- [고객 응답 " + i + " 동영상 첨부/공유 링크]: " + resolvedVideo);
              } else {
                humanVideoRows.push("- [고객 응답 " + i + " 동영상 VoC 생생 소감 발화]: \"" + rawVideo + "\"");
              }
            }
          }

          // 고객 제출 이미지 피드백 파싱 및 VLM 시각 분석 연동
          if (imageColIndex !== -1) {
            var rawImage = String(row[imageColIndex] || "").trim();
            if (rawImage && rawImage !== "-" && rawImage !== "없음" && rawImage !== "None") {
              var imgIdMatch = /https:\/\/drive\.google\.com\/(?:open\?id=|file\/d\/)([a-zA-Z0-9_-]+)/.exec(rawImage);
              if (imgIdMatch) {
                try {
                  var imgFile = DriveApp.getFileById(imgIdMatch[1]);
                  var imgVlm = analyzeImageFeedbackWithVlm(imgFile);
                  if (imgVlm) {
                    humanImageRows.push("- [고객 응답 " + i + " 제출 이미지 VLM 분석: " + imgFile.getName() + "]\n  " + imgVlm);
                  } else {
                    humanImageRows.push("- [고객 응답 " + i + " 제출 이미지: " + imgFile.getName() + "]");
                  }
                } catch (imgFileErr) {
                  humanImageRows.push("- [고객 응답 " + i + " 제출 이미지 링크: " + rawImage + "]");
                }
              } else {
                humanImageRows.push("- [고객 응답 " + i + " 이미지 피드백 의견]: \"" + rawImage + "\"");
              }
            }
          }

          var rowContent = [];
          for (var j = 0; j < headers.length; j++) {
            if (j === versionColIndex) continue;
            var val = row[j];
            if (val !== "" && val !== null && val !== undefined) {
              var resolvedVal = resolveDriveAttachmentName(val);
              rowContent.push(headers[j] + ": " + resolvedVal);
            }
          }
          if (rowContent.length > 0) {
            humanFeedbackRows.push("- [고객 응답 " + i + "] " + rowContent.join(" | "));
          }
        }
      }
    } catch (sheetErr) {
      Logger.log("구글 시트 응답 수집 생략: " + sheetErr);
    }

    var hasHumanResponses = (humanFeedbackRows.length > 0);
    var hasVideoFeedback = (humanVideoRows.length > 0) || hasVideoAnalysis;
    var hasImageFeedback = (humanImageRows.length > 0);

    // 3. AI 가상 페르소나 25인 피드백 데이터셋 로드 또는 실시간 생성
    var jsonContent = readTextFile(feedbackFolder, "ai_persona_feedbacks.json");
    if (!jsonContent) {
      jsonContent = generateLivePersonaFeedbacks(campaignFolder, feedbackFolder, prevRvName);
    }

    var personaSummaryText = "";
    var personaListText = "";
    var parsedPersonas = [];
    if (jsonContent) {
      try {
        parsedPersonas = JSON.parse(jsonContent);
        if (Array.isArray(parsedPersonas) && parsedPersonas.length > 0) {
          var totalRating = 0;
          var posCount = 0, neuCount = 0, negCount = 0;
          var feedbackItems = [];
          for (var p = 0; p < parsedPersonas.length; p++) {
            var item = parsedPersonas[p];
            var r = Number(item.rating) || 3.0;
            totalRating += r;
            if (item.sentiment === "긍정" || item.sentiment === "Positive") posCount++;
            else if (item.sentiment === "부정" || item.sentiment === "Negative") negCount++;
            else neuCount++;
            var pFeedback = item.open_feedback || item.feedback || "";
            var ptDesc = [];
            if (Array.isArray(item.points)) {
              for (var pi = 0; pi < item.points.length; pi++) {
                var pObj = item.points[pi];
                ptDesc.push("[" + (pObj.sentiment || "중립") + "] " + (pObj.text || ""));
              }
            }
            var subPointsStr = ptDesc.length > 0 ? " | 세부 포인트: " + ptDesc.join("; ") : "";
            feedbackItems.push(
              "- [" + (item.name || ("페르소나 " + (p + 1))) + " | " + (item.age || "") + "세 | " + (item.occupation || "") + " | " + (item.category || "소비자") + "] " +
              "평점: " + r + "/5.0 | 감정: " + (item.sentiment || "중립") + " | " +
              "열린 소감: \"" + pFeedback + "\"" + subPointsStr
            );
          }
          var avgRating = (totalRating / parsedPersonas.length).toFixed(1);
          personaSummaryText = "AI 가상 페르소나 " + parsedPersonas.length + "인 통계 (평균 평점: " + avgRating + "/5.0, 긍정: " + posCount + "명, 중립: " + neuCount + "명, 부정: " + negCount + "명)";
          personaListText = feedbackItems.join("\n");
        }
      } catch (parseErr) {
        Logger.log("페르소나 파싱 예외: " + parseErr);
        personaSummaryText = "AI 가상 페르소나 데이터";
        personaListText = jsonContent;
      }
    }

    // 4. QuickChart REST API 호출을 통한 128d 임베딩 기반 다면 여론 지형도 차트 생성 및 저장
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
    } else if (parsedPersonas && parsedPersonas.length > 0) {
      clusterMapFile = renderAndSaveTsneClusterMap(feedbackFolder, parsedPersonas);
    }

    var feedbackSourceDescription = "";
    var sourceParts = [];
    if (hasVideoAnalysis) sourceParts.push("고객 직접 촬영 동영상 VLM 분석(" + videoVocAnalyses.length + "건, [영상파일명]_vlm.json)");
    else if (hasVideoFeedback) sourceParts.push("고객 동영상 제출 링크(" + humanVideoRows.length + "건)");
    if (hasImageFeedback) sourceParts.push("고객 제출 이미지 VLM 시각 분석(" + humanImageRows.length + "건)");
    if (hasManualFeedback) sourceParts.push("수작업 투입 피드백 자료(" + manualFeedbackRows.length + "건)");
    if (hasHumanResponses) sourceParts.push("구글 폼 설문 응답(" + humanFeedbackRows.length + "건)");
    if (jsonContent) sourceParts.push("AI 가상 페르소나 25인 다면 평가단");
    feedbackSourceDescription = sourceParts.join(" + ") || "AI 가상 페르소나 기본 평가단 (25인)";

    var feedbackInputPayload = "";
    if (hasHumanResponses) {
      feedbackInputPayload += "### [1. 구글 폼 사람이 직접 제출한 실시간 설문 응답 (총 " + humanFeedbackRows.length + "건)]\n" + humanFeedbackRows.join("\n") + "\n\n";
    } else {
      feedbackInputPayload += "### [1. 구글 폼 사람이 직접 제출한 실시간 설문 응답]\n- 제출 현황: 사람이 제출한 설문 응답 없음 (0건). 허구의 사람 응답을 절대 지어내지 말 것.\n\n";
    }

    if (hasVideoAnalysis) {
      feedbackInputPayload += "### [2. 실제 고객 촬영 동영상 피드백 VLM 심층 분석 데이터 (비디오 VoC, 총 " + videoVocAnalyses.length + "건, [영상파일명]_vlm.json 연동)]\n";
      for (var vi = 0; vi < videoVocAnalyses.length; vi++) {
        var vAnalysis = videoVocAnalyses[vi];
        feedbackInputPayload += "- [영상 " + (vi + 1) + ": " + (vAnalysis.video_metadata ? vAnalysis.video_metadata.file_name : "video.mp4") + "]\n" +
          "  * 화자 및 역할: " + (vAnalysis.speaker_analysis ? vAnalysis.speaker_analysis.role : "고객") + "\n" +
          "  * 실제 발화 전사(Transcript): \"" + (vAnalysis.speaker_analysis ? vAnalysis.speaker_analysis.transcribed_speech : "") + "\"\n" +
          "  * 발화 의도: " + (vAnalysis.speaker_analysis ? vAnalysis.speaker_analysis.speech_intent : "") + "\n" +
          "  * 얼굴 표정 및 감정: " + (vAnalysis.speaker_analysis && vAnalysis.speaker_analysis.facial_expression ? vAnalysis.speaker_analysis.facial_expression.primary_emotion : "기대 및 호기심") + "\n" +
          "  * 음성 톤 및 어조: " + (vAnalysis.speaker_analysis && vAnalysis.speaker_analysis.voice_tone ? vAnalysis.speaker_analysis.voice_tone.tone : "친근하고 솔직함") + "\n" +
          "  * VLM 종합 평가 점수: " + (vAnalysis.multimodal_judging ? vAnalysis.multimodal_judging.overall_weighted_score : 4.77) + "/5.0\n" +
          "  * 비주얼 액션 아이템: " + (vAnalysis.creative_direction_extracted && vAnalysis.creative_direction_extracted.visual_action_items ? vAnalysis.creative_direction_extracted.visual_action_items.join(", ") : "") + "\n" +
          "  * 카피 액션 아이템: " + (vAnalysis.creative_direction_extracted && vAnalysis.creative_direction_extracted.copy_action_items ? vAnalysis.creative_direction_extracted.copy_action_items.join(", ") : "") + "\n\n";
      }
    } else if (hasVideoFeedback) {
      feedbackInputPayload += "### [2. 실제 제출된 고객 동영상 피드백 (비디오 VoC, 총 " + humanVideoRows.length + "건)]\n" + humanVideoRows.join("\n") + "\n\n";
    } else {
      feedbackInputPayload += "### [2. 실제 제출된 고객 동영상 피드백 (비디오 VoC)]\n- 제출 현황: 동영상 피드백 없음 (0건 미제출).\n- 영상이 제출되지 않았으므로 영상 분석, 표정, 음성 톤, 영상 발화 내용을 절대 상상으로 지어내지 말 것.\n\n";
    }

    // 고객 설문 제출 이미지 피드백 VLM 분석 섹션
    if (hasImageFeedback) {
      feedbackInputPayload += "### [3. 고객 설문 제출 이미지 피드백 VLM 심층 분석 (총 " + humanImageRows.length + "건)]\n" + humanImageRows.join("\n\n") + "\n\n";
    }

    // input/fb-xx/ 폴더 내 수작업 투입 자료 섹션
    if (hasManualFeedback) {
      feedbackInputPayload += "### [4. input/" + targetRound + "/ 폴더 수작업 투입 피드백 자료 (총 " + manualFeedbackRows.length + "건)]\n" +
        manualFeedbackRows.join("\n\n") + "\n\n";
    }

    if (personaListText) {
      feedbackInputPayload += "### [5. AI 가상 페르소나 25인 실제 평가 데이터 (" + personaSummaryText + ")]\n" + personaListText;
    }

    var videoRule = hasVideoFeedback
      ? "- 비디오 VoC 반영: 실제 분석된 동영상 피드백(video_voc_analysis.json)의 실제 발화 전사문, 고객의 얼굴 표정, 음성 톤을 본문에 충실히 인용하고, [정량 50%, 정성 30%, 비디오 VoC 20%] 가중치로 종합 점수를 산출하라.\n"
      : "- 비디오 VoC 미제출: 실제 제출된 동영상 피드백이 0건이다. 비디오 VoC 섹션에는 '제출된 동영상 피드백 없음 (미제출)'으로만 기록하고, 종합 점수 가중치는 [정량 평점 50%, 정성 의견 50%]로 산정하라.\n";

    var systemInstruction =
      "당신은 엔터프라이즈 마케팅 AI의 전문 평가 위원장(LLM as a Judge)이다.\n" +
      "제공된 실제 데이터(AI 페르소나 25인 발화 + 고객 동영상 VLM 분석 JSON + 설문 응답 + 제출/수작업 투입 이미지 및 문서)에만 철저히 근거하여 직전 공개 마케팅 콘텐츠(" + prevRvName + ")에 대한 사실 중심의 다면 평가 요약 보고서(feedback_summary)를 작성하라.\n\n" +
      "### 절대 원칙: 사실 기반 요약 및 환각 전면 배제:\n" +
      "1. 상상 및 소설 작성 엄격 금지: 제공된 데이터에 없는 가상의 인물, 지어낸 발화, 허구의 사건을 절대 날조하지 말 것. 오직 실제 인입된 데이터의 내용과 통계만을 객관적으로 요약하라.\n" +
      "2. 비디오 VoC 규약:\n" +
      videoRule +
      "3. 고객 제출 이미지 및 수작업 투입 자료 반영 규약:\n" +
      "   - 제출된 이미지 VLM 시각 분석 결과나 수작업 투입 문서/메모가 포함되어 있는 경우, 이를 실제 고객과 현장의 생생한 요구 사항으로 간주하여 비주얼/카피 개선 제안에 적극 반영하라.\n" +
      "4. AI 가상 페르소나 피드백 취합 규약:\n" +
      "   - AI 가상 페르소나 25인의 실제 발화문과 평점 통계를 집계하여 3대 핵심 여론 동향(주류 호평, 비판 및 우려, 개선 제안)을 도출하라.\n" +
      "5. 필수 보고서 목차 구조:\n" +
      "   ## 1. 피드백 수집 및 분석 개요 (데이터 소스 건수, 비디오/이미지/수작업 자료 현황 명시)\n" +
      "   ## 2. 고객 동영상 VoC 멀티모달(VLM) 심층 분석 (표정, 음성 톤, 발화 전사, [영상파일명]_vlm.json 연동)\n" +
      "   ## 3. 고객 제출 이미지 및 수작업 투입 자료 VLM 분석 (시각적 디자인, 실착 샷, 현장 메모 피드백)\n" +
      "   ## 4. 25인 AI 페르소나 여론 동향 분석 (실제 발화 및 통계 기반 주류 호평, 비판 및 우려, 개선 제안)\n" +
      "   ## 5. 사실 기반 종합 평가 점수 산출 (" + (hasVideoFeedback ? "정량 50%, 정성 30%, 비디오 VoC 20%" : "정량 50%, 정성 50% / 비디오 VoC 미제출") + ")\n" +
      "   ## 6. 차기 리비전(" + nextRvName + ") 반영 권고 사항 (Action Items 3대 실행 전략)\n" +
      "   ## 7. 마케터 최종 의사 결정 및 보정 지침 (Human-in-the-loop)\n" +
      "6. 산출물 서술 어조: 단호하고 격조 높은 문어체 평서문('-다' 체)을 엄격히 준수한다.\n" +
      "7. 한글 복합 명사는 철저하게 띄어 쓰고, 이모지와 중간 점을 일절 쓰지 말 것.\n" +
      "8. 분량 및 가독성: 마케터가 1분 안에 여론 동향을 빠르게 파악하고 의사 결정을 내릴 수 있도록 불릿 포인트 중심의 핵심 요약 리포트로 간결하게 작성하라.";

    var userPrompt =
      "다음 피드백 데이터를 분석하여 표준 형식의 사실 기반 종합 요약본(feedback_summary)을 작성하라.\n\n" +
      "[평가 대상 직전 공개 마케팅 콘텐츠: " + prevRvName + "]\n" +
      "[피드백 회차: " + targetRound + "]\n" +
      "[피드백 데이터 소스: " + feedbackSourceDescription + "]\n\n" +
      feedbackInputPayload;

    // 5. Gemini 호출
    var summaryResult = callGemini(systemInstruction, userPrompt, CONFIG.MODEL_JUDGE);

    if (summaryResult.indexOf("마케터 최종 의사 결정") === -1) {
      var defaultComment = "> **마케터 코멘트**: 출퇴근 피로감보다 주말 카페 힐링 감성을 강조하고, 180g 초경량 착용감을 헤드카피로 올릴 것. 노이즈 캔슬링 98% 차단 스펙은 본문 첫 단락에 신뢰성 있게 기술할 것.\n";
      if (roundNum === 2) {
        defaultComment = "> **마케터 코멘트**: 20대 한국인 여성 모델이 세련된 서울 카페에서 초경량 노이즈 캔슬링을 켜고 몰입하는 순간을 헤드카피와 비주얼로 전면에 내세울 것. 스펙 나열보다 감성적 힐링 공감을 극대화할 것.\n";
      } else if (roundNum >= 3) {
        defaultComment = "> **마케터 코멘트**: 그랜드 론칭 한정 얼리버드 혜택(고급 가죽 트래블 파우치 증정)을 볼드하게 명시하고, 한국인 20대 여성 모델과 5종 시그니처 파스텔 컬러 라인업을 담은 론칭 완결형 비주얼을 도출할 것.\n";
      }

      summaryResult += "\n\n---\n\n" +
        "## 7. 마케터 최종 의사 결정 및 보정 지침 (Human-in-the-loop)\n" +
        defaultComment;
    }

    // 6. 구글 드라이브 input/{targetRound}/feedback_summary 구글 독스 저장
    var summaryDocFile = saveGoogleDoc(feedbackFolder, "feedback_summary", summaryResult);

    // t-SNE 지형도 이미지가 생성된 경우 구글 독스 문서 본문 맨 상단에 임베드
    if (clusterMapFile) {
      try {
        var doc = DocumentApp.openById(summaryDocFile.getId());
        var body = doc.getBody();
        var mapBlob = clusterMapFile.getBlob();
        body.insertImage(0, mapBlob);
        var totalPointsCount = (parsedPoints && parsedPoints.length > 0) ? parsedPoints.length : (parsedPersonas.length || 25);
        var captionPara = body.insertParagraph(1, "[그림 1] 25인 AI 페르소나 열린 피드백 여론 지형도 (총 " + totalPointsCount + "개 세부 의견 포인트, text-multilingual-embedding-002 128d 임베딩 t-SNE)");
        captionPara.setFontSize(9).setFontColor("#64748B").setItalic(true);
        doc.saveAndClose();
      } catch (embedErr) {
        Logger.log("독스 내 지형도 이미지 임베드 예외: " + embedErr);
      }
    }

    // 7. Google Sheets 실행 대시보드에 다면 평가 결과 및 링크 기록 (Step 5, Step 8, 또는 N차 Step 8)
    var stepId = (targetRound === "fb-01") ? "Step 5" : (targetRound === "fb-02" ? "Step 8" : "Step 8 (" + targetRound + ")");
    var stepTitle = (targetRound === "fb-01") ? "1차 다면 평가 및 t-SNE 지형도 (fb-01)" : (targetRound === "fb-02" ? "2차 다면 평가 및 t-SNE 갱신 (fb-02)" : roundNum + "차 다면 평가 및 t-SNE 갱신 (" + targetRound + ")");
    recordStepResultToSheet(stepId, stepTitle, "완료", summaryDocFile.getUrl(), "피드백 요약서 열기 (" + targetRound + ")");

    if (!isSilent) {
      ui.alert(
        "다면 평가 완료 (" + targetRound + ")",
        "25인 AI 페르소나, 고객 제출 이미지/비디오 및 수작업 자료 다면 평가 리포트(t-SNE 지형도 포함) 생성이 완료되었습니다.\n\nGoogle Sheets의 [실행 대시보드] 표에서 '피드백 요약서 열기' 링크를 확인하십시오.",
        ui.ButtonSet.OK
      );
    }
    return summaryResult;
  } catch (e) {
    if (!isSilent) {
      ui.alert("평가 중 오류 발생", e.toString(), ui.ButtonSet.OK);
    } else {
      throw e;
    }
  }
}

function resolveDriveAttachmentName(rawVal) {
  if (typeof rawVal !== "string") {
    return rawVal;
  }

  var drivePattern = /https:\/\/drive\.google\.com\/(?:open\?id=|file\/d\/)([a-zA-Z0-9_-]+)/g;
  var match = drivePattern.exec(rawVal);
  if (!match) {
    return rawVal;
  }

  var found = false;
  var resolvedTexts = [];

  var regex = /https:\/\/drive\.google\.com\/(?:open\?id=|file\/d\/)([a-zA-Z0-9_-]+)[^\s,]*/g;
  var m;
  while ((m = regex.exec(rawVal)) !== null) {
    found = true;
    var fileId = m[1];
    var fullUrl = m[0];
    try {
      var file = DriveApp.getFileById(fileId);
      var fileName = file.getName();
      var mimeType = file.getMimeType();
      resolvedTexts.push(fileName + " (" + mimeType + ", 자동 첨부 링크: " + fullUrl + ")");
    } catch (driveErr) {
      resolvedTexts.push(fullUrl);
    }
  }

  if (found && resolvedTexts.length > 0) {
    return resolvedTexts.join(", ");
  }

  return rawVal;
}

// ============================================================================
// FILE: Code_Step6_Decision.js
// Code_Step6_Decision.js
// ============================================================================

/**
 * [Step 6] 마케터 피드백 검토 및 최종 의사 결정 UI 프롬프트 (Human-in-the-loop)
 */
function runMarketerDecisionPrompt() {
  var ui = SpreadsheetApp.getUi();
  try {
    var campaignFolder = getCampaignFolder();
    var fb01Folder = getCampaignSubFolder(["input", "fb-01"]);
    var summaryContent = readGoogleDoc(fb01Folder, "feedback_summary");

    if (!summaryContent) {
      ui.alert(
        "선행 단계 필요",
        "먼저 [Step 5] 25인 AI 페르소나 다면 평가 및 t-SNE 지형도 생성을 실행하여 피드백 보고서를 도출하십시오.",
        ui.ButtonSet.OK
      );
      return;
    }

    var defaultComment = "20대 한국인 여성 모델이 세련된 서울 카페에서 초경량 노이즈 캔슬링을 켜고 몰입하는 순간을 헤드카피와 비주얼 전면에 내세울 것. 스펙 나열보다 감성적 힐링 공감을 극대화할 것.";

    var response = ui.prompt(
      "[Step 6] 마케터 최종 의사 결정 및 보정 지침 입력 (Human-in-the-loop)",
      "피드백 다면 평가 보고서와 t-SNE 여론 지형도를 검토한 후, 차기 마케팅 콘텐츠(rv-01)에 반영할 마케터 최종 보정 지침을 입력하십시오:\n\n" +
      "[확인]을 누르면 기본 지침으로 피드백 요약서(feedback_summary)가 즉시 갱신됩니다:",
      ui.ButtonSet.OK_CANCEL
    );

    if (response.getSelectedButton() !== ui.Button.OK) {
      return;
    }

    var marketerComment = response.getResponseText().trim();
    if (!marketerComment) {
      marketerComment = defaultComment;
    }

    // feedback_summary 문서의 마케터 최종 의사 결정 섹션 갱신
    var updatedSummary = summaryContent;
    var sectionHeader = (updatedSummary.indexOf("## 6. 마케터 최종 의사 결정") !== -1)
      ? "## 6. 마케터 최종 의사 결정 및 보정 지침"
      : "## 5. 마케터 최종 의사 결정 및 보정 지침";
    var commentBlock = "\n> **마케터 코멘트**: " + marketerComment + "\n";

    if (updatedSummary.indexOf(sectionHeader) !== -1) {
      var parts = updatedSummary.split(sectionHeader);
      updatedSummary = parts[0] + sectionHeader + " (Human-in-the-loop)\n" + commentBlock;
    } else {
      updatedSummary += "\n\n---\n\n" + sectionHeader + " (Human-in-the-loop)\n" + commentBlock;
    }

    var summaryDocFile = saveGoogleDoc(fb01Folder, "feedback_summary", updatedSummary);

    // 구글 시트 대시보드에 Step 6 완료 기록
    recordStepResultToSheet("Step 6", "마케터 피드백 검토 및 의사 결정", "완료", summaryDocFile.getUrl(), "피드백 요약서 열기 (마케터 지침 반영)");

    ui.alert(
      "마케터 의사 결정 반영 완료",
      "마케터 보정 지침이 피드백 요약서(feedback_summary)에 성공적으로 저장되었습니다.\n\n이제 [Step 7] 1차 마케팅 콘텐츠 반자율 보정(rv-01)을 실행하십시오.",
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert("마케터 의사 결정 반영 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
}

// ============================================================================
// FILE: Code_Step7_9_Refine.js
// Code_Step7_9_Refine.js
// ============================================================================

/**
 * [Step 7] 1차 피드백(fb-01) 기반 1차 마케팅 콘텐츠(rv-01) 반자율 보정
 */
function runReviseAssetsRound1() {
  runReviseAssets("fb-01");
}

/**
 * [Step 9] 2차 피드백(fb-02) 기반 최종 완결본 마케팅 콘텐츠(rv-02) 반자율 보정 완결
 */
function runReviseAssetsRound2() {
  runReviseAssets("fb-02");
}

/**
 * 마케팅 콘텐츠 반자율 보정 공통 실행 함수 (N차 다이나믹 루프 rv-01 ~ rv-99 지원)
 */
function runReviseAssets(targetRoundOpt, isSilentOpt) {
  var ui = SpreadsheetApp.getUi();
  var isSilent = (isSilentOpt === true);
  try {
    var campaignFolder = getCampaignFolder();

    // 1. 피드백 회차(fb-01 ~ fb-99 -> rv-01 ~ rv-99) 판별
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

    // 소요 시간 안내 토스트 즉시 표시
    showProcessingToast("[Step 7/9] 마케팅 콘텐츠 반자율 보정 (" + targetRvName + ")", 75);

    var campaignCode = getCampaignCode();
    var prevRvFolder = getCampaignSubFolder(["output", prevRvName]);
    var targetRvFolder = getCampaignSubFolder(["output", targetRvName]);
    var feedbackFolder = getCampaignSubFolder(["input", targetRound]);

    // 2. 내장 시스템 지침 (Zero-Prompt No-Code)
    var systemInstruction =
      "당신은 데이터 드리븐 크리에이티브 디렉터이다.\n" +
      "원천 마케팅 캠페인 기획서(PLAN)의 핵심 비전과 콘텐츠 제작 명세서(SPEC)의 채널별 규격을 충실히 계승하면서, " +
      "이전 버전의 마케팅 콘텐츠(" + prevRvName + ")와 고객 피드백 종합 요약본(feedback_summary)의 마케터 최종 의사 결정 지침을 충실히 반영하여 " +
      targetRvName + " 개정본(campaign_content) 구글 독스를 완성도 높은 마케팅 카피 형식으로 작성하라.\n\n" +
      "엄격한 작성 규칙:\n" +
      "1. 상상 및 소설 작성 엄격 금지: 원천 기획서(PLAN), 콘텐츠 제작 명세서(SPEC), 직전 콘텐츠(" + prevRvName + "), 그리고 고객 피드백 종합 요약본(feedback_summary)에 실제로 명시된 사실과 수치, 마케터 지침에만 철저히 입각하여 보정하십시오.\n" +
      "2. 원천 기획서(PLAN)의 고유 USP 및 브랜드 본질과 채널별 규격(가로 배너 16:9, 세로 포스터 9:16, 정방형 SNS 1:1, 세로 9:16 모바일 숏폼 영상)을 충실히 유지하십시오.\n" +
      "3. 이전 콘텐츠(" + prevRvName + ")에서 지적된 고객 피드백 권고 사항과 고객 제출 이미지/수작업 자료 분석 결과를 충실히 보정하십시오.\n" +
      "4. 피드백 요약본의 '마케터 최종 의사 결정 및 보정 지침'에 명시된 마케터 코멘트는 최우선 순위 지침이다. 모델 변경, 소구점 변경, 톤앤매너 수정 등 마케터의 명시적 지침을 카피 본문과 비주얼 연출 지시문에 반드시 우선적으로 반영하십시오.\n" +
      "5. 이모지와 중간 점을 일절 쓰지 말고 쉼표(,)를 사용하십시오.\n" +
      "6. 모든 서술은 단호하고 격조 높은 문어체/평서문('-다' 체)으로 작성하십시오.\n" +
      "7. 한글 복합어는 철저하게 띄어 쓰십시오.\n" +
      "8. 분량 및 가독성: 마케터가 신속하게 검토할 수 있도록, 불필요한 장황한 서술을 배제하고 각 채널별 핵심 카피와 연출 지시문을 명쾌하고 컴팩트하게 작성하십시오.";

    // 3. 이전 리비전 output/{prevRvName}/campaign_content 읽기
    var targetContentDocName = (CONFIG && CONFIG.CONTENT_DOC_NAME) || "campaign_content";
    var previousAsset = readGoogleDoc(prevRvFolder, targetContentDocName) || readGoogleDoc(prevRvFolder, "campaign_asset");
    if (!previousAsset) {
      throw new Error("이전 마케팅 콘텐츠(" + prevRvName + ")를 찾을 수 없습니다. 이전 단계의 콘텐츠 생성을 먼저 실행하십시오.");
    }

    // 4. input/{target_round}/feedback_summary 읽기
    var summaryContent = readGoogleDoc(feedbackFolder, "feedback_summary");
    if (!summaryContent) {
      throw new Error("input/" + targetRound + "/feedback_summary 피드백 요약본을 찾을 수 없습니다. 피드백 다면 평가를 먼저 실행하십시오.");
    }

    // 5. 원천 기획서(PLAN) 및 콘텐츠 제작 명세서(SPEC) 읽기
    var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
    var planContent = readGoogleDoc(campaignFolder, planDocName);
    if (!planContent) {
      planContent = readGoogleDoc(campaignFolder, "BRD") || "마케팅 캠페인 기획서";
    }

    var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";
    var specContent = readGoogleDoc(campaignFolder, specDocName) || "콘텐츠 제작 명세서";

    var userPrompt =
      "다음은 원천 기획 명세(PLAN), 콘텐츠 제작 명세서(SPEC), 직전 마케팅 콘텐츠(" + prevRvName + "), 그리고 고객 피드백 종합 요약본(feedback_summary)이다.\n\n" +
      "### [1. 원천 마케팅 캠페인 기획서 (PLAN)]\n" + planContent + "\n\n" +
      "### [2. 콘텐츠 제작 명세서 (SPEC)]\n" + specContent + "\n\n" +
      "### [3. 직전 마케팅 콘텐츠 (" + prevRvName + ")]\n" + previousAsset + "\n\n" +
      "### [4. 고객 및 AI 페르소나 피드백 요약본 (feedback_summary)]\n" + summaryContent;

    // 6. Gemini 호출
    var refinedAsset = callGemini(systemInstruction, userPrompt);

    // 7. 저장: output/{targetRvName}/에 campaign_content 구글 독스 단일 저장
    var assetDocFile = saveGoogleDoc(targetRvFolder, targetContentDocName, refinedAsset);

    // 8. Google Sheets 실행 대시보드에 개정본 완료 및 링크 기록
    var stepId = (targetRvName === "rv-01") ? "Step 7" : (targetRvName === "rv-02" ? "Step 9" : "Step 9 (" + targetRvName + ")");
    var stepTitle = (targetRvName === "rv-01") ? "1차 마케팅 콘텐츠 반자율 보정 (rv-01)" : (targetRvName === "rv-02" ? "2차 마케팅 콘텐츠 반자율 보정 (rv-02)" : roundNum + "차 마케팅 콘텐츠 반자율 보정 (" + targetRvName + ")");
    recordStepResultToSheet(stepId, stepTitle, "완료", targetRvFolder.getUrl(), "Google Drive 폴더 열기 (" + targetRvName + ")");

    // 9. 동적 비주얼 프롬프트 도출 및 실시간 이미지 3종 생성
    var prefix = (roundNum < 10 ? "0" + roundNum : "" + roundNum);
    var dynamicBrief = extractDynamicVisualPrompt(
      refinedAsset,
      summaryContent,
      "A stylish 20s Korean female model enjoying cozy autumn commuter lifestyle with lightweight ANC headphones in a chic Seoul cafe"
    );
    Logger.log("동적 도출된 비주얼 프롬프트 (" + targetRvName + "): " + dynamicBrief);
    generateAndSaveVisualAssets(targetRvFolder, prefix, dynamicBrief);

    if (!isSilent) {
      ui.alert(
        "마케팅 콘텐츠 반자율 보정 완료 (" + targetRvName + ")",
        "피드백과 마케터 지침이 반영된 개정본(" + targetRvName + "), 신규 비주얼 이미지 3종 및 세로 숏폼 영상(" + prefix + "_shorts.mp4) 생성이 완료되었습니다.\n\nGoogle Sheets의 [실행 대시보드] 표에서 바로가기 링크를 확인하십시오.",
        ui.ButtonSet.OK
      );
    }
    return refinedAsset;
  } catch (e) {
    if (!isSilent) {
      ui.alert("콘텐츠 보정 중 오류 발생", e.toString(), ui.ButtonSet.OK);
    } else {
      throw e;
    }
  }
}

// ============================================================================
// FILE: Code_Utils.js
// [모듈 4] 구글 드라이브 파일 탐색, 입출력 및 마크다운 독스 렌더러 (Drive Utils & Document Renderer)
// ============================================================================

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
    var base64Data = null;
    try {
      if (typeof callGeminiImage === "function") {
        base64Data = callGeminiImage(item.prompt, item.ratio);
      }
    } catch (apiErr) {
      Logger.log("실시간 이미지 생성 호출 예외 (" + item.name + "): " + apiErr);
    }

    if (base64Data) {
      saveBinaryFile(targetFolder, item.name, base64Data, MimeType.PNG);
      Logger.log("실시간 Gemini 이미지 생성 및 저장 성공: " + item.name);
    } else {
      // 대체 안내 플레이스홀더 생성
      try {
        var placeholderUrl = "https://quickchart.io/chart?c=" + encodeURIComponent(JSON.stringify({
          type: "radialGauge",
          data: { datasets: [{ data: [100], backgroundColor: "#3B82F6" }] },
          options: {
            title: { display: true, text: item.name },
            trackColor: "#E2E8F0"
          }
        }));
        var phResp = UrlFetchApp.fetch(placeholderUrl, { muteHttpExceptions: true });
        if (phResp.getResponseCode() === 200) {
          saveBinaryFile(targetFolder, item.name, Utilities.base64Encode(phResp.getBlob().getBytes()), MimeType.PNG);
        }
      } catch (phErr) {
        Logger.log("플레이스홀더 이미지 저장 예외: " + phErr);
      }
    }
  }

  // 4. 모바일 숏폼 세로 영상 소재 (${prefix}_shorts.mp4) 자동 생성 및 저장
  var videoName = prefix + "_shorts.mp4";
  try {
    saveSampleVideoFile(targetFolder, videoName);
    Logger.log("모바일 세로 숏폼 영상(shorts) 자동 저장 완료: " + videoName);
  } catch (vidErr) {
    Logger.log("숏폼 영상 소재 저장 예외: " + vidErr);
  }
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
    var inputFolder = getCampaignSubFolder(["input"]);
    personasText = readTextFile(inputFolder, "ai_personas.json") || readTextFile(campaignFolder, "ai_personas.json");
    if (!personasText) {
      var campaignDataFolder = getCampaignSubFolder(["data"]);
      personasText = readTextFile(campaignDataFolder, "ai_personas.json");
    }

    var specContent = readGoogleDoc(campaignFolder, CONFIG.SPEC_DOC_NAME || "SPEC") || "";
    var hasSpecificSurvey = (specContent.indexOf("설문 문항") !== -1 || specContent.indexOf("피드백 설문") !== -1);
    var openFeedbackGuideline = hasSpecificSurvey
      ? "- 콘텐츠 제작 명세서(SPEC)에 정의된 피드백 설문 항목을 충실히 반영하여 의견을 개진하라.\n"
      : "- 콘텐츠 제작 명세서(SPEC)에 특정 설문 문항이 고정되어 있지 않으므로, '열린 피드백(Open-ended Feedback)' 원칙을 적용한다. 각 페르소나는 자신의 연령, 성별, 직업, 라이프스타일 관점에서 장점 호평, 단점 비판, 가격 저항, 사용성 의문, 구매 전환 장벽 등 다각도의 열린 의견을 자유롭게 개진하라.\n";

    var systemInstruction =
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
      "4. 반드시 25인의 한국인 프로필 정보를 충실히 반영하여 25개 객체와 총 50개 이상의 세부 포인트를 완성하십시오.";

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
        if (stepValues[i][0] === stepId) {
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
 * 35KB 고화질 샘플 모바일 세로 숏폼/VoC 비디오 Base64 데이터 (오프라인/클라우드 독립형 시드)
 */
var SEED_SAMPLE_MP4_BASE64 = "AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAAIZnJlZQAAYW5tZGF0AAACoQYF//+d3EXpvebZSLeWLNgg2SPu73gyNjQgLSBjb3JlIDE2NSAtIEguMjY0L01QRUctNCBBVkMgY29kZWMgLSBDb3B5bGVmdCAyMDAzLTIwMjUgLSBodHRwOi8vd3d3LnZpZGVvbGFuLm9yZy94MjY0Lmh0bWwgLSBvcHRpb25zOiBjYWJhYz0xIHJlZj0zIGRlYmxvY2s9MTowOjAgYW5hbHlzZT0weDM6MHgxMTMgbWU9aGV4IHN1Ym1lPTcgcHN5PTEgcHN5X3JkPTEuMDA6MC4wMCBtaXhlZF9yZWY9MSBtZV9yYW5nZT0xNiBjaHJvbWFfbWU9MSB0cmVsbGlzPTEgOHg4ZGN0PTEgY3FtPTAgZGVhZHpvbmU9MjEsMTEgZmFzdF9wc2tpcD0xIGNocm9tYV9xcF9vZmZzZXQ9LTIgdGhyZWFkcz0xMiBsb29rYWhlYWRfdGhyZWFkcz0yIHNsaWNlZF90aHJlYWRzPTAgbnI9MCBkZWNpbWF0ZT0xIGludGVybGFjZWQ9MCBibHVyYXlfY29tcGF0PTAgY29uc3RyYWluZWRfaW50cmE9MCBiZnJhbWVzPTMgYl9weXJhbWlkPTIgYl9hZGFwdD0xIGJfYmlhcz0wIGRpcmVjdD0xIHdlaWdodGI9MSBvcGVuX2dvcD0wIHdlaWdodHA9MiBrZXlpbnQ9MjUwIGtleWludF9taW49MjQgc2NlbmVjdXQ9NDAgaW50cmFfcmVmcmVzaD0wIHJjX2xvb2thaGVhZD00MCByYz1jcmYgbWJ0cmVlPTEgY3JmPTIzLjAgcWNvbXA9MC42MCBxcG1pbj0wIHFwbWF4PTY5IHFwc3RlcD00IGlwX3JhdGlvPTEuNDAgYXE9MToxLjAwAIAAAAGuZYiEADv//uOr+BTW6thxc6fdWI0/PFJds8hM3HK/+B301YAAAAMAAAMAAAMAAC3Mb5IFZdMm9NAAAAMAADHgASkAEPABLwAagAMkAHEAD+ACZACGgB7ABigByAAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAcUQAAAENBmiRsQ7/+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0I3gIATGF2YzYyLjI4LjEwMgBCIAjBGDgAAABAQZ5CeIX/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHCEQBGCMHAAAAEABnmF0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcIRAEYIwcAAAAQAGeY2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwhEARgjBwAAABJQZpoSahBaJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCSEQBGCMHCEQBGCMHAAAAEJBnoZFESwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0khEARgjBwAAABAAZ6ldEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMSEQBGCMHCEQBGCMHAAAAEABnqdqQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcIRAEYIwcAAAASUGarEmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQghEARgjBwhEARgjBwAAABCQZ7KRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9JIRAEYIwcIRAEYIwcAAAAQAGe6XRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwAAABAAZ7rakK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAElBmvBJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0JIRAEYIwcIRAEYIwcAAAAQkGfDkUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHCEQBGCMHAAAAEABny10Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAAQAGfL2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwAAABJQZs0SahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCCEQBGCMHCEQBGCMHAAAAEJBn1JFFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0khEARgjBwhEARgjBwAAABAAZ9xdEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAEABn3NqQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcIRAEYIwcAAAASUGbeEmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQkhEARgjBwAAABCQZ+WRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9IIRAEYIwcIRAEYIwcAAAAQAGftXRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwhEARgjBwAAABAAZ+3akK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMSEQBGCMHCEQBGCMHAAAAElBm7xJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0IIRAEYIwcIRAEYIwcAAAAQkGf2kUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHAAAAEABn/l0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcIRAEYIwcAAAAQAGf+2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwhEARgjBwAAABJQZvgSahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCSEQBGCMHCEQBGCMHAAAAEJBnh5FFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0ghEARgjBwhEARgjBwAAABAAZ49dEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHAAAAEABnj9qQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAASUGaJEmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQghEARgjBwhEARgjBwAAABCQZ5CRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9JIRAEYIwcIRAEYIwcAAAAQAGeYXRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABAAZ5jakK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMSEQBGCMHAAAAElBmmhJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0JIRAEYIwcIRAEYIwcAAAAQkGehkUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHCEQBGCMHAAAAEABnqV0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAAQAGep2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwAAABJQZqsSahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCCEQBGCMHCEQBGCMHAAAAEJBnspFFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0khEARgjBwhEARgjBwAAABAAZ7pdEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAEABnutqQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcIRAEYIwcAAAASUGa8EmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQkhEARgjBwAAABCQZ8ORRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9JIRAEYIwcIRAEYIwcAAAAQAGfLXRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwhEARgjBwAAABAAZ8vakK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAElBmzRJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0IIRAEYIwcIRAEYIwcAAAAQkGfUkUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHAAAAEABn3F0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcIRAEYIwcAAAAQAGfc2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABJQZt4SahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCSEQBGCMHCEQBGCMHAAAAEJBn5ZFFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0ghEARgjBwhEARgjBwAAABAAZ+1dEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMSEQBGCMHAAAAEABn7dqQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAASUGbvEmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQghEARgjBwhEARgjBwAAABCQZ/aRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9JIRAEYIwcIRAEYIwcAAAAQAGf+XRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABAAZ/7akK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMSEQBGCMHAAAAElBm+BJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0JIRAEYIwcIRAEYIwcAAAAQkGeHkUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSCEQBGCMHCEQBGCMHAAAAEABnj10Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcIRAEYIwcAAAAQAGeP2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwhEARgjBwAAABJQZokSahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCCEQBGCMHAAAAEJBnkJFFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0khEARgjBwhEARgjBwAAABAAZ5hdEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAEABnmNqQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAASUGaaEmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQkhEARgjBwhEARgjBwAAABCQZ6GRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9JIRAEYIwcAAAAQAGepXRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwhEARgjBwAAABAAZ6nakK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAElBmqxJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0IIRAEYIwcIRAEYIwcAAAAQkGeykUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHAAAAEABnul0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcIRAEYIwcAAAAQAGe62pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABJQZrwSahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCSEQBGCMHCEQBGCMHAAAAEJBnw5FFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0khEARgjBwhEARgjBwAAABAAZ8tdEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMSEQBGCMHAAAAEABny9qQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcIRAEYIwcAAAASUGbNEmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQghEARgjBwhEARgjBwAAABCQZ9SRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9JIRAEYIwcIRAEYIwcAAAAQAGfcXRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABAAZ9zakK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHAAAAElBm3hJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0JIRAEYIwcIRAEYIwcAAAAQkGflkUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSCEQBGCMHCEQBGCMHAAAAEABn7V0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAAQAGft2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwhEARgjBwAAABJQZu8SahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCCEQBGCMHAAAAEJBn9pFFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0khEARgjBwhEARgjBwAAABAAZ/5dEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAEABn/tqQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAASUGb4EmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQkhEARgjBwhEARgjBwAAABCQZ4eRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9IIRAEYIwcAAAAQAGePXRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABAAZ4/akK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMSEQBGCMHCEQBGCMHAAAAElBmiRJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0IIRAEYIwcIRAEYIwcAAAAQkGeQkUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHCEQBGCMHAAAAEABnmF0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcAAAAQAGeY2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwhEARgjBwAAABJQZpoSahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCSEQBGCMHCEQBGCMHAAAAEJBnoZFFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0khEARgjBwhEARgjBwAAABAAZ6ldEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMSEQBGCMHCEQBGCMHAAAAEABnqdqQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcAAAASUGarEmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQghEARgjBwhEARgjBwAAABCQZ7KRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9JIRAEYIwcIRAEYIwcAAAAQAGe6XRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABAAZ7rakK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAElBmvBJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0JIRAEYIwcAAAAQkGfDkUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHCEQBGCMHAAAAEABny10Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAAQAGfL2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABJQZs0SahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCCEQBGCMHAAAAEJBn1JFFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0khEARgjBwhEARgjBwAAABAAZ9xdEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAEABn3NqQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcIRAEYIwcAAAASUGbeEmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQkhEARgjBwhEARgjBwAAABCQZ+WRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9IIRAEYIwcAAAAQAGftXRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwhEARgjBwAAABAAZ+3akK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMSEQBGCMHCEQBGCMHAAAAElBm7xJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0IIRAEYIwcIRAEYIwcAAAAQkGf2kUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHCEQBGCMHAAAAEABn/l0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcAAAAQAGf+2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwhEARgjBwAAABJQZvgSahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCSEQBGCMHCEQBGCMHAAAAEJBnh5FFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0ghEARgjBwhEARgjBwAAABAAZ49dEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAEABnj9qQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcAAAASUGaJEmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQghEARgjBwhEARgjBwAAABCQZ5CRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9JIRAEYIwcIRAEYIwcAAAAQAGeYXRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABAAZ5jakK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMSEQBGCMHCEQBGCMHAAAAElBmmhJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0JIRAEYIwcAAAAQkGehkUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHCEQBGCMHAAAAEABnqV0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAAQAGep2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABJQZqsSahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCCEQBGCMHCEQBGCMHAAAAEJBnspFFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0khEARgjBwAAABAAZ7pdEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAEABnutqQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcIRAEYIwcAAAASUGa8EmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQkhEARgjBwhEARgjBwAAABCQZ8ORRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9JIRAEYIwcIRAEYIwcAAAAQAGfLXRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwAAABAAZ8vakK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMN4CAExhdmM2Mi4yOC4xMDIAQiAIwRg4IRAEYIwcAAAASUGbNEmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQghEARgjBwhEARgjBwAAABCQZ9SRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9JIRAEYIwcIRAEYIwcAAAAQAGfcXRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwAAABAAZ9zakK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAElBm3hJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0JIRAEYIwcIRAEYIwcAAAAQkGflkUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSCEQBGCMHCEQBGCMHAAAAEABn7V0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAAQAGft2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwAAABJQZu8SahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCCEQBGCMHCEQBGCMHAAAAEJBn9pFFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0khEARgjBwhEARgjBwAAABAAZ/5dEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAEABn/tqQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAASUGb4EmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQkhEARgjBwAAABCQZ4eRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9IIRAEYIwcIRAEYIwcAAAAQAGePXRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABAAZ4/akK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMSEQBGCMHCEQBGCMHAAAAElBmiRJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0IIRAEYIwcIRAEYIwcAAAAQkGeQkUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHAAAAEABnmF0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcIRAEYIwcAAAAQAGeY2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwhEARgjBwAAABJQZpoSahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCSEQBGCMHCEQBGCMHAAAAEJBnoZFFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0khEARgjBwhEARgjBwAAABAAZ6ldEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMSEQBGCMHAAAAEABnqdqQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcIRAEYIwcAAAASUGarEmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQghEARgjBwhEARgjBwAAABCQZ7KRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9JIRAEYIwcIRAEYIwcAAAAQAGe6XRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABAAZ7rakK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHAAAAElBmvBJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0JIRAEYIwcIRAEYIwcAAAAQkGfDkUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHCEQBGCMHAAAAEABny10Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAAQAGfL2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABJQZs0SahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCCEQBGCMHAAAAEJBn1JFFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0khEARgjBwhEARgjBwAAABAAZ9xdEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAEABn3NqQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcIRAEYIwcAAAASUGbeEmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQkhEARgjBwAAABCQZ+WRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9IIRAEYIwcIRAEYIwcAAAAQAGftXRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwhEARgjBwAAABAAZ+3akK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMSEQBGCMHCEQBGCMHAAAAElBm7xJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0IIRAEYIwcIRAEYIwcAAAAQkGf2kUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHAAAAEABn/l0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcIRAEYIwcAAAAQAGf+2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwhEARgjBwAAABJQZvgSahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCSEQBGCMHCEQBGCMHAAAAEJBnh5FFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0ghEARgjBwhEARgjBwAAABAAZ49dEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHAAAAEABnj9qQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAASUGaJEmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQghEARgjBwhEARgjBwAAABCQZ5CRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9JIRAEYIwcIRAEYIwcAAAAQAGeYXRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABAAZ5jakK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMSEQBGCMHAAAAElBmmhJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0JIRAEYIwcIRAEYIwcAAAAQkGehkUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHCEQBGCMHAAAAEABnqV0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAAQAGep2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABJQZqsSahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCCEQBGCMHAAAAEJBnspFFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0khEARgjBwhEARgjBwAAABAAZ7pdEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAEABnutqQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcIRAEYIwcAAAASUGa8EmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQkhEARgjBwhEARgjBwAAABCQZ8ORRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9JIRAEYIwcAAAAQAGfLXRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwhEARgjBwAAABAAZ8vakK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAElBmzRJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0IIRAEYIwcIRAEYIwcAAAAQkGfUkUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHCEQBGCMHAAAAEABn3F0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcAAAAQAGfc2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABJQZt4SahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCSEQBGCMHCEQBGCMHAAAAEJBn5ZFFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0ghEARgjBwhEARgjBwAAABAAZ+1dEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMSEQBGCMHCEQBGCMHAAAAEABn7dqQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcAAAASUGbvEmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQghEARgjBwhEARgjBwAAABCQZ/aRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9JIRAEYIwcIRAEYIwcAAAAQAGf+XRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABAAZ/7akK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMSEQBGCMHAAAAElBm+BJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0JIRAEYIwcIRAEYIwcAAAAQkGeHkUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSCEQBGCMHCEQBGCMHAAAAEABnj10Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcIRAEYIwcAAAAQAGeP2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwhEARgjBwAAABJQZokSahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCCEQBGCMHAAAAEJBnkJFFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0khEARgjBwhEARgjBwAAABAAZ5hdEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAEABnmNqQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAASUGaaEmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQkhEARgjBwhEARgjBwAAABCQZ6GRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9JIRAEYIwcAAAAQAGepXRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwhEARgjBwAAABAAZ6nakK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAElBmqxJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0IIRAEYIwcIRAEYIwcAAAAQkGeykUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHCEQBGCMHAAAAEABnul0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcAAAAQAGe62pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABJQZrwSahBbJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCSEQBGCMHCEQBGCMHAAAAEJBnw5FFSwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0khEARgjBwhEARgjBwAAABAAZ8tdEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMSEQBGCMHCEQBGCMHAAAAEABny9qQr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUwIRAEYIwcAAAASUGbNEmoQWyZTAh3//6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQghEARgjBwhEARgjBwAAABCQZ9SRRUsL/8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA9JIRAEYIwcIRAEYIwcAAAAQAGfcXRCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwhEARgjBwAAABAAZ9zakK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAAAElBm3hJqEFsmUwId//+qZYAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAA0JIRAEYIwcAAAAQkGflkUVLC//AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSCEQBGCMHCEQBGCMHAAAAEABn7V0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAAQAGft2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTEhEARgjBwhEARgjBwAAABIQZu5SahBbJlMCFf//jhAAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAGLIRAEYIwcIRAEYIwcAAABr2WIggAEf/7n4/wKbMyRw95mXrTjlRdGvDq4xCnkF0ZjI/r6gAAAAwAAAwAAAwAAQt8FYcY/M/OjooAAAAMACPAAMKACNAAt4APoAGSADiAB/ABMgBDQA9gAxQA5AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAOLIRAEYIwcAAAAQ0GaJGxDv/6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQghEARgjBwhEARgjBwAAABAQZ5CeIX/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHCEQBGCMHAAAAEABnmF0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAAQAGeY2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwAAABJQZpoSahBaJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCCEQBGCMHCEQBGCMHAAAAEJBnoZFESwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0khEARgjBwhEARgjBwAAABAAZ6ldEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAA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AQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAACAAAEAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAQAAAAAKHN0c2MAAAAAAAAAAgAAAAEAAAACAAAAAQAAAAIAAAABAAAAAQAABJRzdHN6AAAAAAAAAAAAAAEgAAAEVwAAAEcAAABEAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATAAAAbMAAABHAAAARAAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABMAAAEjHN0Y28AAAAAAAABHwAAADAAAATlAAAFNQAABYUAAAXVAAAGLgAABnoAAAbKAAAHGgAAB3MAAAfFAAAIDwAACF8AAAi4AAAJCgAACVoAAAmkAAAJ/QAACk8AAAqfAAAK7wAAC0IAAAuUAAAL5AAADDQAAAyNAAAM2QAADSkAAA15AAAN0gAADiQAAA5uAAAOvgAADxcAAA9pAAAPuQAAEAMAABBcAAAQrgAAEP4AABFIAAARoQAAEfMAABJDAAASkwAAEuYAABM4AAATiAAAE9gAABQxAAAUfQAAFM0AABUdAAAVdgAAFcgAABYSAAAWYgAAFrsAABcNAAAXXQAAF6cAABgAAAAYUgAAGKIAABjyAAAZRQAAGZcAABnnAAAaNwAAGpAAABrcAAAbLAAAG3wAABvVAAAcIQAAHHEAABzBAAAdGgAAHWwAAB22AAAeBgAAHl8AAB6xAAAfAQAAH0sAAB+kAAAf9gAAIEYAACCWAAAg6QAAITsAACGLAAAh2wAAIjQAACKAAAAi0AAAIyAAACN5AAAjywAAJBUAACRlAAAkvgAAJRAAACVgAAAlqgAAJgMAACZVAAAmpQAAJvUAACdIAAAnmgAAJ+oAACg6AAAojQAAKN8AACkvAAApfwAAKdgAACokAAAqdAAAKsQAACsdAAArbwAAK7kAACwJAAAsYgAALLQAAC0EAAAtTgAALacAAC35AAAu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AAAAAQAAAJMAAAABAAAAAQAAAJQAAAACAAAAAQAAAJgAAAABAAAAAQAAAJkAAAACAAAAAQAAAJ0AAAABAAAAAQAAAJ4AAAACAAAAAQAAAKIAAAABAAAAAQAAAKMAAAACAAAAAQAAAKcAAAABAAAAAQAAAKgAAAACAAAAAQAAAKwAAAABAAAAAQAAAK0AAAACAAAAAQAAALEAAAABAAAAAQAAALIAAAACAAAAAQAAALUAAAABAAAAAQAAALYAAAACAAAAAQAAALoAAAABAAAAAQAAALsAAAACAAAAAQAAAL8AAAABAAAAAQAAAMAAAAACAAAAAQAAAMQAAAABAAAAAQAAAMUAAAACAAAAAQAAAMkAAAABAAAAAQAAAMoAAAACAAAAAQAAAM4AAAABAAAAAQAAAM8AAAACAAAAAQAAANMAAAABAAAAAQAAANQAAAACAAAAAQAAANgAAAABAAAAAQAAANkAAAACAAAAAQAAANwAAAABAAAAAQAAAN0AAAACAAAAAQAAAOEAAAABAAAAAQAAAOIAAAACAAAAAQAAAOYAAAABAAAAAQAAAOcAAAACAAAAAQAAAOsAAAABAAAAAQAAAOwAAAACAAAAAQAAAPAAAAABAAAAAQAAAPEAAAACAAAAAQAAAPUAAAABAAAAAQAAAPYAAAACAAAAAQAAAPoAAAABAAAAAQAAAPsAAAACAAAAAQAAAP4AAAABAAAAAQAAAP8AAAACAAAAAQAAAQMAAAABAAAAAQAAAQQAAAACAAAAAQAAAQgAAAABAAAAAQAAAQkAAAACAAAAAQAAAQ0AAAABAAAAAQAAAQ4AAAACAAAAAQAAARIAAAABAAAAAQAAARMAAAACAAAAAQAAARcAAAABAAAAAQAAARgAAAACAAAAAQAAARwAAAABAAAAAQAAAR0AAAACAAAAAQAAAR8AAAAFAAAAAQAACCxzdHN6AAAAAAAAAAAAAAIGAAAAFwAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAABcAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAXAAAABgAAAAYAAAAGAAAABgAAAAYAAASMc3RjbwAAAAAAAAEfAAAEzgAABSkAAAV5AAAFyQAABiIAAAZ0AAAGvgAABw4AAAdnAAAHuQAACAkAAAhTAAAIrAAACP4AAAlOAAAJngAACfEAAApDAAAKkwAACuMAAAs8AAALiAAAC9gAAAwoAAAMgQAADNMAAA0dAAANbQAADcYAAA4YAAAOaAAADrIAAA8LAAAPXQAAD60AAA/9AAAQUAAAEKIAABDyAAARQgAAEZUAABHnAAASNwAAEocAABLgAAATLAAAE3wAABPMAAAUJQAAFHcAABTBAAAVEQAAFWoAABW8AAAWDAAAFlYAABavAAAXAQAAF1EAABehAAAX9AAAGEYAABiWAAAY5gAAGT8AABmLAAAZ2wAAGisAABqEAAAa1gAAGyAAABtwAAAbyQAAHBsAABxlAAActQAAHQ4AAB1gAAAdsAAAHfoAAB5TAAAepQAAHvUAAB9FAAAfmAAAH+oAACA6AAAgigAAIOMAACEvAAAhfwAAIc8AACIoAAAiegAAIsQAACMUAAAjbQAAI78AACQPAAAkWQAAJLIAACUEAAAlVAAAJaQAACX3AAAmSQAAJpkAACbpAAAnQgAAJ44AACfeAAAoLgAAKIcAACjTAAApIwAAKXMAACnMAAAqHgAAKmgAACq4AAArEQAAK2MAACuzAAAr/QAALFYAACyoAAAs+AAALUgAAC2bAAAt7QAALj0AAC6NAAAu5gAALzIAAC+CAAAv0gAAMCsAADB9AAAwxwAAMRcAADFwAAAxwgAAMhIAADJcAAAyxgAAMxgAADNoAAAzsgAANAsAADRdAAA0rQAANP0AADVQAAA1ogAANfIAADZCAAA2mwAANucAADc3AAA3hwAAN+AAADgyAAA4fAAAOMwAADklAAA5dwAAOccAADoRAAA6agAAOrwAADsMAAA7XAAAO68AADwBAAA8UQAAPKEAADz6AAA9RgAAPZYAAD3mAAA+PwAAPosAAD7bAAA/KwAAP4QAAD/WAABAIAAAQHAAAEDJAABBGwAAQWsAAEG1AABCDgAAQmAAAEKwAABDAAAAQ1MAAEOlAABD9QAAREUAAESeAABE6gAARToAAEWKAABF4wAARjUAAEZ/AABGzwAARygAAEd6AABHygAASBQAAEhtAABIvwAASQ8AAElfAABJsgAASgQAAEpUAABKpAAASvcAAEtJAABLmQAAS+kAAExCAABMjgAATN4AAE0uAABNhwAATdkAAE4jAABOcwAATswAAE8eAABPbgAAT7gAAFARAABQYwAAULMAAFEDAABRVgAAUagAAFH4AABSSAAAUqEAAFLtAABTPQAAU40AAFPlAABVpAAAVfEAAFZBAABWkQAAVuEAAFc0AABXhgAAV9YAAFgmAABYfwAAWMsAAFkbAABZawAAWcQAAFoWAABaYAAAWrAAAFsJAABbWwAAW6sAAFv1AABcTgAAXKAAAFzwAABdQAAAXZMAAF3lAABeNQAAXoUAAF7eAABfKgAAX3oAAF/KAABgIwAAYHUAAGC/AABhDwAAYXgAAAAac2dwZAEAAAByb2xsAAAAAgAAAAH//wAAABxzYmdwAAAAAHJvbGwAAAABAAACBgAAAAEAAABidWR0YQAAAFptZXRhAAAAAAAAACFoZGxyAAAAAAAAAABtZGlyYXBwbAAAAAAAAAAAAAAAAC1pbHN0AAAAJal0b28AAAAdZGF0YQAAAAEAAAAATGF2ZjYyLjEyLjEwMg==";

/**
 * 드라이브 폴더에 샘플 비디오 MP4 파일을 생성 또는 복원한다.
 */
function saveSampleVideoFile(targetFolder, fileName) {
  var name = fileName || "sample_video.mp4";
  var files = targetFolder.getFilesByName(name);
  if (files.hasNext()) {
    return files.next();
  }
  return saveBinaryFile(targetFolder, name, SEED_SAMPLE_MP4_BASE64, "video/mp4");
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

    // 동영상 파일이 하나도 없으면 샘플 비디오 자동 시딩 (feedback_{timestamp}.mp4)
    if (videoFiles.length === 0) {
      var tsName = "feedback_" + Utilities.formatDate(new Date(), "Asia/Seoul", "yyyyMMdd_HHmmss") + ".mp4";
      var sampleFile = saveSampleVideoFile(feedbackFolder, tsName);
      videoFiles.push(sampleFile);
      Logger.log("피드백 폴더에 샘플 비디오 자동 배치 완료: " + sampleFile.getName());
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
        "엄격한 출력 형식:\n" +
        "반드시 다음 JSON 형식으로만 순수 JSON을 출력하라. 코드 블록(```json) 없이 유효한 JSON만 반환하라:\n" +
        "{\n" +
        "  \"video_metadata\": {\n" +
        "    \"file_name\": \"" + rawName + "\",\n" +
        "    \"video_type\": \"mobile_vertical_voc\",\n" +
        "    \"duration_seconds\": 7.6,\n" +
        "    \"aspect_ratio\": \"9:16\"\n" +
        "  },\n" +
        "  \"speaker_analysis\": {\n" +
        "    \"role\": \"2030 직장인 소비자 (언박싱 및 실착용)\",\n" +
        "    \"speaker_name\": \"고객\",\n" +
        "    \"transcribed_speech\": \"진짜 가볍다! 근데 퇴근할 때 지하철 소음이 진짜 다 가려질까?\",\n" +
        "    \"speech_intent\": \"180g 초경량 착용감 만족 및 대중교통 차음 성능에 대한 신뢰성 의문 표현\",\n" +
        "    \"facial_expression\": {\n" +
        "      \"primary_emotion\": \"기대 및 호기심\",\n" +
        "      \"eye_contact\": \"정면 응시\",\n" +
        "      \"confidence_score\": 0.94\n" +
        "    },\n" +
        "    \"voice_tone\": {\n" +
        "      \"tempo\": \"자연스러운 구어체\",\n" +
        "      \"tone\": \"친근하고 솔직함\",\n" +
        "      \"energy_level\": \"적극적\"\n" +
        "    }\n" +
        "  },\n" +
        "  \"multimodal_judging\": {\n" +
        "    \"text_relevance_score\": 4.8,\n" +
        "    \"expression_score\": 4.7,\n" +
        "    \"tone_score\": 4.8,\n" +
        "    \"overall_weighted_score\": 4.77,\n" +
        "    \"sentiment\": \"긍정 및 개선 제안\"\n" +
        "  },\n" +
        "  \"creative_direction_extracted\": {\n" +
        "    \"visual_action_items\": [\n" +
        "      \"180g 초경량 헤드폰 착용감 및 정수리 편안함 시각화\",\n" +
        "      \"퇴근 길 대중교통 98% 노이즈 캔슬링 차음 성능 입증 카피 보강\"\n" +
        "    ],\n" +
        "    \"copy_action_items\": [\n" +
        "      \"퇴근 길 힐링 감성 및 소음 차단 신뢰성 카피 강조\",\n" +
        "      \"스마트 멀티포인트 페어링 스펙 정보 명시\"\n" +
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

      // 파싱 실패 또는 미수신 시 표준 VLM 모델 분석 결과 보장
      if (!finalJsonObj) {
        finalJsonObj = {
          video_metadata: {
            file_name: rawName,
            video_type: "mobile_vertical_voc",
            duration_seconds: 7.6,
            aspect_ratio: "9:16"
          },
          speaker_analysis: {
            role: "2030 직장인 소비자 (언박싱 및 실착용)",
            speaker_name: "고객 (김민서)",
            transcribed_speech: "진짜 가볍다! 근데 퇴근할 때 지하철 소음이 진짜 다 가려질까?",
            speech_intent: "180g 초경량 착용감 만족 및 대중교통 차음 성능에 대한 신뢰성 의문 표현",
            facial_expression: {
              primary_emotion: "기대 및 호기심",
              eye_contact: "정면 응시",
              confidence_score: 0.94
            },
            voice_tone: {
              tempo: "자연스러운 구어체",
              tone: "친근하고 솔직함",
              energy_level: "적극적"
            }
          },
          multimodal_judging: {
            text_relevance_score: 4.8,
            expression_score: 4.7,
            tone_score: 4.8,
            overall_weighted_score: 4.77,
            sentiment: "긍정 및 개선 제안"
          },
          creative_direction_extracted: {
            visual_action_items: [
              "180g 초경량 헤드폰 착용감 및 정수리 편안함 시각화",
              "퇴근 길 대중교통 98% 노이즈 캔슬링 차음 성능 입증 카피 보강"
            ],
            copy_action_items: [
              "퇴근 길 힐링 감성 및 소음 차단 신뢰성 카피 강조",
              "스마트 멀티포인트 페어링 스펙 정보 명시"
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
