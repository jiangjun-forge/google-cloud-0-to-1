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
    var systemInstruction = getPromptTemplate("05_feedback_summary");
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
