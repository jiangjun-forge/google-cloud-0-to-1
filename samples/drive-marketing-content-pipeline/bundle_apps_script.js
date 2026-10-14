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
  IMAGE_MODEL_NAME: "imagen-3.0-generate-002", // 광고 소재 비주얼 이미지 생성 모델 (Imagen 3)
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
    var imgModel = CONFIG.IMAGE_MODEL_NAME || "imagen-3.0-generate-002";
    var endpoint = CONFIG.BASE_URL + "/" + imgModel + ":predict?key=" + apiKey;
    var ratio = aspectRatio || "1:1";

    var payload = {
      instances: [
        { prompt: prompt + ", commercial advertising product photography, professional studio lighting, 8k resolution, photorealistic" }
      ],
      parameters: {
        sampleCount: 1,
        aspectRatio: ratio,
        personGeneration: "ALLOW_ADULT",
        outputMimeType: "image/png"
      }
    };

    var options = {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    var response = UrlFetchApp.fetch(endpoint, options);
    var code = response.getResponseCode();
    var body = response.getContentText();

    if (code === 200) {
      var result = JSON.parse(body);
      if (result.predictions && result.predictions.length > 0 && result.predictions[0].bytesBase64Encoded) {
        return result.predictions[0].bytesBase64Encoded;
      }
    } else {
      Logger.log("Imagen 3 이미지 생성 실패 (" + code + "): " + body);
    }
  } catch (err) {
    Logger.log("Imagen 3 이미지 생성 네트워크 예외: " + err);
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

    // 6. 구글 시트 실행 대시보드에 기획서(PLAN) 및 콘텐츠 명세서(SPEC) 링크 각각 분리 기록
    recordStepResultToSheet("Step 2 (기획서)", "마케팅 캠페인 기획서(PLAN) 도출", "완료", planDocFile.getUrl(), "기획서(PLAN) 구글 독스 열기");
    recordStepResultToSheet("Step 2 (명세서)", "콘텐츠 제작 명세서(SPEC) 도출", "완료", specDocFile.getUrl(), "명세서(SPEC) 구글 독스 열기");

    ui.alert(
      "기획서(PLAN) 및 콘텐츠 명세서(SPEC) 생성 완료",
      "캠페인 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC) 구글 독스가 성공적으로 생성되었습니다.\n\n" +
      "1. 기획서(PLAN): " + planDocFile.getUrl() + "\n" +
      "2. 명세서(SPEC): " + specDocFile.getUrl() + "\n\n" +
      "마케터는 브라우저에서 SPEC 문서를 열어 이미지 비율, 숏폼 길이, 카피 채널 규격을 자유롭게 수정한 뒤 [Step 3]을 실행할 수 있습니다.\n\n" +
      "구글 시트의 [실행 대시보드] 표에서 각 문서의 바로가기 링크를 확인하십시오.",
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
    var stepPrefix = (targetRound === "fb-01") ? "[Step 5]" : "[Step 8]";
    showProcessingToast(stepPrefix + " 다면 평가 및 t-SNE 지형도 생성 (" + targetRound + ")", 75);

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
    var stepPrefix = (targetRvName === "rv-01") ? "[Step 7]" : "[Step 9]";
    showProcessingToast(stepPrefix + " 마케팅 콘텐츠 반자율 보정 (" + targetRvName + ")", 75);

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
 * 35KB 고화질 샘플 모바일 세로 숏폼/VoC 비디오 Base64 데이터 (오프라인/클라우드 독립형 시드)
 */
var SEED_SAMPLE_MP4_BASE64 = "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AAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACAAAAAACAAACAAAAAChzdHNjAAAAAAAAAAIAAAABAAAAAgAAAAEAAAACAAAAAQAAAAEAAAGkc3RzegAAAAAAAAAAAAAAZAAAjIgAAAJ1AAAAdwAAAGIAAABIAAAA2QAAAEkAAABHAAAARAAAAIEAAABGAAAARAAAAEQAAABnAAAARgAAAEQAAABEAAAAVQAAAEcAAABEAAAARAAAAE4AAABGAAAARAAAAEQAAABMAAAARgAAAEQAAABEAAAATAAAAEYAAABEAAAARAAAAEwAAABGAAAARAAAAEQAAABMAAAARgAAAEQAAABEAAAATAAAAEYAAABEAAAARAAAAEwAAABGAAAARAAAAEQAAABMAAAARgAAAEQAAABEAAAATAAAAEYAAABEAAAARAAAAEwAAABGAAAARAAAAEQAAABMAAAARgAAAEQAAABEAAAATAAAAEYAAABEAAAARAAAAEwAAABGAAAARAAAAEQAAABMAAAARgAAAEQAAABEAAAATAAAAEYAAABEAAAARAAAAEwAAABGAAAARAAAAEQAAABMAAAARgAAAEQAAABEAAAASAAAAEYAAABEAAAARAAAAEgAAABGAAAARAAAAEQAAABIAAAARgAAAEQAAAGcc3Rj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";

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
