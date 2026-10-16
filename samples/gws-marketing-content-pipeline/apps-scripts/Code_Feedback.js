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
