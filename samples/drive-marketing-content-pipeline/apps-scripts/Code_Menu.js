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
