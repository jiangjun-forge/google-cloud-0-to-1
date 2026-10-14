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

    showResultModal(
      "25인 페르소나 다면 평가 및 지형도 생성 완료 (" + targetRound + ")",
      "한국인 25인 가상 페르소나로부터 50개 이상의 세부 의견 포인트와 128차원 임베딩 기반 t-SNE 여론 지형도가 성공적으로 도출되었습니다.\n아래 버튼을 클릭하여 다면 여론 지형도 차트를 즉시 확인하십시오.",
      "t-SNE 지형도 차트 보기",
      chartFile ? chartFile.getUrl() : feedbackFolder.getUrl()
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

    showResultModal(
      "피드백 종합 분석 보고서 도출 완료 (" + targetRound + ")",
      "피드백 종합 보고서(feedback_summary) 구글 독스가 생성되었습니다.\n문서 하단의 [마케터 최종 의사 결정] 지침을 브라우저에서 직접 검토 및 수정한 뒤 [보정] 메뉴를 진행하십시오.",
      "피드백 요약서 구글 독스 열기",
      summaryFile.getUrl()
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
