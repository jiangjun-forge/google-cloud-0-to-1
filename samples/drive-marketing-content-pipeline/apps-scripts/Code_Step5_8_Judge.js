/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [Step 5 / Step 8] 25인 AI 페르소나 다면 평가 및 t-SNE 여론 지형도 통합 엔진 (Feedback Persona Judge & t-SNE Mapper)
 */

/**
 * [Step 5] 초판 콘텐츠(rv-00) 대상 1차 25인 다면 평가 및 t-SNE 여론 지형도 렌더링
 */
function runJudgeEvaluationRound1() {
  runStep5PersonaEvaluation("fb-01");
}

/**
 * [Step 8] 1차 개정본 콘텐츠(rv-01) 대상 2차 25인 다면 평가 및 t-SNE 지형도 갱신
 */
function runJudgeEvaluationRound2() {
  runStep5PersonaEvaluation("fb-02");
}

/**
 * [Step 5 / Step 8 공통] 25인 AI 페르소나 다면 평가 및 128d t-SNE 여론 지형도 생성
 */
function runStep5PersonaEvaluation(targetRoundOpt, isSilentOpt) {
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
      var autoRound = Math.max(latestFb + 1, latestRv + 1, 1);
      targetRound = "fb-" + (autoRound < 10 ? "0" + autoRound : autoRound);
    }

    var roundNum = parseInt(targetRound.replace("fb-", ""), 10) || 1;
    var prevRoundNum = Math.max(0, roundNum - 1);
    var prevRvName = "rv-" + (prevRoundNum < 10 ? "0" + prevRoundNum : prevRoundNum);
    var stepPrefix = (targetRound === "fb-01") ? "[Step 5]" : "[Step 8]";

    // 대기 토스트 즉시 표시
    showProcessingToast(stepPrefix + " 25인 페르소나 다면 평가 및 t-SNE 지형도 생성 (" + targetRound + ")", 60);

    var feedbackFolder = getCampaignSubFolder(["input", targetRound]);

    // 2. AI 가상 페르소나 25인 피드백 데이터셋 로드 또는 실시간 생성 (열린 피드백 50~80+개 세부 포인트 및 128d 임베딩)
    var jsonContent = readTextFile(feedbackFolder, "ai_persona_feedbacks.json");
    if (!jsonContent) {
      jsonContent = generateLivePersonaFeedbacks(campaignFolder, feedbackFolder, prevRvName);
    }

    // 3. 128d 임베딩 기반 다면 여론 지형도 차트 생성 및 저장 (feedback_clusters_map.png)
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

    // 4. Google Sheets 실행 대시보드에 Step 5 (또는 Step 8) 완료 기록
    var stepId = (targetRound === "fb-01") ? "Step 5" : (targetRound === "fb-02" ? "Step 8" : "Step 8 (" + targetRound + ")");
    var stepTitle = (targetRound === "fb-01")
      ? "1차 페르소나 다면 평가 및 t-SNE 지형도 (" + targetRound + ")"
      : roundNum + "차 페르소나 다면 평가 및 t-SNE 갱신 (" + targetRound + ")";

    recordStepResultToSheet(
      stepId,
      stepTitle,
      "완료",
      clusterMapFile.getUrl(),
      "t-SNE 지형도 이미지 열기 (" + targetRound + ")"
    );

    if (!isSilent) {
      var nextStepDesc = (targetRound === "fb-01")
        ? "상단 메뉴에서 [Step 6] 피드백 종합 요약서(fb-01) 자동 도출 및 마케터 검토를 실행하십시오."
        : "상단 메뉴에서 피드백 종합 요약서 도출 또는 마케팅 콘텐츠 보정을 이어서 진행하십시오.";

      ui.alert(
        "페르소나 평가 및 t-SNE 지형도 생성 완료 (" + targetRound + ")",
        "25인 AI 페르소나 다면 평가 및 128d 임베딩 t-SNE 여론 지형도(feedback_clusters_map.png) 생성이 완료되었습니다.\n\n" +
        "1. Google Sheets의 [실행 대시보드] 표에서 't-SNE 지형도 이미지 열기 (" + targetRound + ")' 링크를 클릭하여 지형도를 확인하십시오.\n" +
        "2. 다음 단계로 " + nextStepDesc,
        ui.ButtonSet.OK
      );
    }
    return clusterMapFile;
  } catch (e) {
    if (!isSilent) {
      ui.alert("다면 평가 및 지형도 생성 중 오류 발생", e.toString(), ui.ButtonSet.OK);
    } else {
      throw e;
    }
  }
}

/**
 * [호환성 유지] 피드백 다면 평가 공통 실행 함수
 */
function runJudgeEvaluation(targetRoundOpt, isSilentOpt) {
  return runStep5PersonaEvaluation(targetRoundOpt, isSilentOpt);
}

/**
 * Google Drive 파일 첨부 링크 문자열로부터 실제 파일명을 추출 및 정규화한다.
 */
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
