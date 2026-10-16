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
