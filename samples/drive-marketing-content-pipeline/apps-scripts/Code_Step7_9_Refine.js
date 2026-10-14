/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [Step 7 / Step 9] 다면 평가 피드백 기반 마케팅 콘텐츠 반자율 보정 통합 엔진 (Revise Content)
 */

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

    // 7. 저장: output/{targetRvName}/에 campaign_content 구글 독스 단일 저장 (쇼츠 영상 콘티 완전 통합)
    var prefix = (roundNum < 10 ? "0" + roundNum : "" + roundNum);
    var dynamicBrief = extractDynamicVisualPrompt(
      refinedAsset,
      summaryContent,
      "A stylish 20s Korean female model enjoying cozy autumn commuter lifestyle with lightweight ANC headphones in a chic Seoul cafe"
    );
    var finalizedContent = ensureShortsScriptInCampaignContent(refinedAsset, prefix, dynamicBrief);
    var assetDocFile = saveGoogleDoc(targetRvFolder, targetContentDocName, finalizedContent);

    // 8. Google Sheets 실행 대시보드에 개정본 완료 및 링크 기록
    var stepId = (targetRvName === "rv-01") ? "Step 7" : (targetRvName === "rv-02" ? "Step 9" : "Step 9 (" + targetRvName + ")");
    var stepTitle = (targetRvName === "rv-01") ? "1차 마케팅 콘텐츠 반자율 보정 (rv-01)" : (targetRvName === "rv-02" ? "2차 마케팅 콘텐츠 반자율 보정 (rv-02)" : roundNum + "차 마케팅 콘텐츠 반자율 보정 (" + targetRvName + ")");
    recordStepResultToSheet(stepId, stepTitle, "완료", targetRvFolder.getUrl(), "Google Drive 폴더 열기 (" + targetRvName + ")");

    // 9. 실시간 이미지 3종 및 Veo 비디오 생성
    Logger.log("동적 도출된 비주얼 프롬프트 (" + targetRvName + "): " + dynamicBrief);
    generateAndSaveVisualAssets(targetRvFolder, prefix, dynamicBrief);

    if (!isSilent) {
      ui.alert(
        "마케팅 콘텐츠 반자율 보정 완료 (" + targetRvName + ")",
        "피드백과 마케터 지침이 반영된 개정본(" + targetRvName + ") 및 신규 비주얼 이미지 3종 비율 세트 생성이 완료되었습니다.\n\nGoogle Sheets의 [실행 대시보드] 표에서 바로가기 링크를 확인하십시오.",
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
