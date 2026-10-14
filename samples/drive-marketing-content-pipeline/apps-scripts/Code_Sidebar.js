/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 9] 구글 시트 우측 패널(Sidebar) 모던 HTML 컨트롤 타워 UI
 */

/**
 * 우측 패널(사이드바) 인라인 입력창에서 전달된 Gemini API Key를 검증 및 저장한다.
 *
 * @param {string} apiKey - 입력된 API Key
 * @return {Object} 처리 결과 { success: boolean, message: string }
 */
function saveApiKeyInline(apiKey) {
  if (!apiKey || typeof apiKey !== "string") {
    return { success: false, message: "유효한 API Key를 입력해 주십시오." };
  }
  var cleanKey = apiKey.trim();
  if (cleanKey.length < 10) {
    return { success: false, message: "API Key 형식이 올바르지 않습니다. (최소 10자 이상)" };
  }

  try {
    PropertiesService.getUserProperties().setProperty("GEMINI_API_KEY", cleanKey);
    return { success: true, message: "Gemini API Key가 성공적으로 등록되었습니다." };
  } catch (e) {
    return { success: false, message: "API Key 저장 중 오류: " + e.toString() };
  }
}

/**
 * 구글 시트 우측 패널에 마케팅 콘텐츠 파이프라인 컨트롤 타워를 표시한다.
 */
function showPipelineSidebar() {
  var ui = SpreadsheetApp.getUi();
  try {
    initDashboardSheet();
    var htmlOutput = HtmlService.createHtmlOutput(getPipelineSidebarHtml())
      .setTitle("마케팅 콘텐츠 파이프라인 제어 패널")
      .setWidth(340);
    ui.showSidebar(htmlOutput);
  } catch (err) {
    ui.alert(
      "사이드바 실행 오류",
      "우측 패널(사이드바)을 여는 중 오류가 발생했습니다:\n" + err.toString(),
      ui.ButtonSet.OK
    );
  }
}

/**
 * 사이드바 화면 렌더링에 필요한 현재 캠페인 파이프라인 상태 정보를 반환한다.
 *
 * @return {Object} 캠페인 작업 공간 상태, 산출물 URL, 리비전, 토큰 통계 객체
 */
function getPipelineStatus() {
  try {
    initDashboardSheet();
  } catch (e) {
    // 무시
  }
  var status = {
    hasApiKey: !!getGeminiApiKey(),
    campaignCode: "CAMP-2026-AUTUMN",
    folderUrl: "",
    ideaDocUrl: "",
    planDocUrl: "",
    specDocUrl: "",
    contentDocUrl: "",
    formUrl: "",
    summaryDocUrl: "",
    mapUrl: "",
    latestRv: "rv-00",
    latestFb: "",
    totalTokens: getSessionTotalTokens() || 0
  };

  try {
    var folder = getCampaignFolder();
    if (folder) {
      status.folderUrl = folder.getUrl();
      var folderName = folder.getName();
      status.campaignCode = folderName.length > 20 ? folderName.substring(0, 18) + "..." : folderName;

      // 1. 아이디어 메모 탐색
      var ideaName = (CONFIG && CONFIG.IDEA_DOC_NAME) || "아이디어 메모";
      var ideaFiles = folder.getFilesByName(ideaName);
      if (!ideaFiles.hasNext()) {
        ideaFiles = folder.getFilesByName("[아이디어 메모] 2026 가을 오텀 브리즈 캠페인");
      }
      if (ideaFiles.hasNext()) status.ideaDocUrl = ideaFiles.next().getUrl();

      // 2. 기획서 (PLAN) 탐색 (확장자 유무 불문)
      var planFiles = folder.getFilesByName("PLAN");
      if (!planFiles.hasNext()) planFiles = folder.getFilesByName("PLAN.md");
      if (!planFiles.hasNext()) planFiles = folder.getFilesByName("마케팅 캠페인 기획서");
      if (planFiles.hasNext()) status.planDocUrl = planFiles.next().getUrl();

      // 3. 제작 명세서 (SPEC) 탐색 (확장자 유무 불문)
      var specFiles = folder.getFilesByName("SPEC");
      if (!specFiles.hasNext()) specFiles = folder.getFilesByName("SPEC.md");
      if (specFiles.hasNext()) status.specDocUrl = specFiles.next().getUrl();

      // 4. 고객 VoC 설문 폼 탐색
      var formFiles = folder.getFilesByType(MimeType.GOOGLE_FORMS);
      if (formFiles.hasNext()) status.formUrl = formFiles.next().getUrl();

      // 5. 최신 리비전 콘텐츠 탐색
      var latestRvNum = detectLatestRevisionRoundNum();
      if (latestRvNum >= 0) {
        status.latestRv = "rv-" + (latestRvNum < 10 ? "0" + latestRvNum : latestRvNum);
        var rvFolder = getCampaignSubFolder(["output", status.latestRv]);
        var contentDocName = (CONFIG && CONFIG.CONTENT_DOC_NAME) || "campaign_content";
        var contentFiles = rvFolder.getFilesByName(contentDocName);
        if (!contentFiles.hasNext()) contentFiles = rvFolder.getFilesByName("campaign_content.md");
        if (!contentFiles.hasNext()) contentFiles = rvFolder.getFilesByName("campaign_asset");
        if (contentFiles.hasNext()) status.contentDocUrl = contentFiles.next().getUrl();
      }

      // 6. 최신 피드백 종합 보고서 및 지형도 탐색
      var latestFbNum = detectLatestFeedbackRoundNum();
      if (latestFbNum > 0) {
        status.latestFb = "fb-" + (latestFbNum < 10 ? "0" + latestFbNum : latestFbNum);
        var fbFolder = getCampaignSubFolder(["input", status.latestFb]);
        var summaryFiles = fbFolder.getFilesByName("feedback_summary");
        if (!summaryFiles.hasNext()) summaryFiles = fbFolder.getFilesByName("feedback_summary.md");
        if (summaryFiles.hasNext()) status.summaryDocUrl = summaryFiles.next().getUrl();
        var mapFiles = fbFolder.getFilesByName("feedback_clusters_map.png");
        if (mapFiles.hasNext()) status.mapUrl = mapFiles.next().getUrl();
      }
    }
  } catch (e) {
    Logger.log("getPipelineStatus 예외: " + e);
  }

  return status;
}

/**
 * 우측 패널(Sidebar)용 모던 HTML 문자열을 생성한다.
 * [구글 워크스페이스 스타일]: Google Sans 서체, 구글 클라우드 테마 색상, 무이모지, 실시간 RPC 연동.
 */
function getPipelineSidebarHtml() {
  return "" +
    "<!DOCTYPE html>\n" +
    "<html>\n" +
    "<head>\n" +
    "  <base target='_blank'>\n" +
    "  <style>\n" +
    "    * { box-sizing: border-box; margin: 0; padding: 0; }\n" +
    "    body {\n" +
    "      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;\n" +
    "      font-size: 13px;\n" +
    "      line-height: 1.5;\n" +
    "      color: #202124;\n" +
    "      background: #ffffff;\n" +
    "      padding: 16px 14px;\n" +
    "    }\n" +
    "    .header {\n" +
    "      padding-bottom: 8px;\n" +
    "      margin-bottom: 10px;\n" +
    "      border-bottom: 1px solid #dadce0;\n" +
    "    }\n" +
    "    .header-sub {\n" +
    "      font-size: 11px;\n" +
    "      color: #5f6368;\n" +
    "      display: flex;\n" +
    "      justify-content: space-between;\n" +
    "      align-items: center;\n" +
    "    }\n" +
    "    .badge {\n" +
    "      display: inline-block;\n" +
    "      font-size: 10px;\n" +
    "      font-weight: 600;\n" +
    "      padding: 2px 7px;\n" +
    "      border-radius: 4px;\n" +
    "      background: #e8f0fe;\n" +
    "      color: #1967d2;\n" +
    "    }\n" +
    "    .badge.active { background: #ceead6; color: #0d652d; }\n" +
    "    .badge.warn { background: #fef7e0; color: #b06000; cursor: pointer; }\n" +
    "    .onboarding-card {\n" +
    "      padding: 10px 12px;\n" +
    "      border-radius: 6px;\n" +
    "      margin-bottom: 12px;\n" +
    "      font-size: 11px;\n" +
    "      line-height: 1.4;\n" +
    "    }\n" +
    "    .onboarding-card.warn {\n" +
    "      background: #fef7e0;\n" +
    "      border: 1px solid #f9ab00;\n" +
    "      color: #b06000;\n" +
    "    }\n" +
    "    .onboarding-card.info {\n" +
    "      background: #e8f0fe;\n" +
    "      border: 1px solid #1a73e8;\n" +
    "      color: #174ea6;\n" +
    "    }\n" +
    "    .onboarding-title {\n" +
    "      font-weight: 700;\n" +
    "      margin-bottom: 4px;\n" +
    "      display: flex;\n" +
    "      justify-content: space-between;\n" +
    "      align-items: center;\n" +
    "    }\n" +
    "    .inline-box {\n" +
    "      padding: 10px 12px;\n" +
    "      background: #f8f9fa;\n" +
    "      border: 1px solid #1a73e8;\n" +
    "      border-radius: 6px;\n" +
    "      margin-bottom: 12px;\n" +
    "    }\n" +
    "    .inline-box-title {\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 700;\n" +
    "      color: #1a73e8;\n" +
    "      margin-bottom: 6px;\n" +
    "    }\n" +
    "    .inline-input {\n" +
    "      width: 100%;\n" +
    "      padding: 7px 9px;\n" +
    "      font-size: 11px;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      border-radius: 4px;\n" +
    "      margin-bottom: 6px;\n" +
    "      outline: none;\n" +
    "    }\n" +
    "    .inline-input:focus { border-color: #1a73e8; }\n" +
    "    .inline-actions {\n" +
    "      display: flex;\n" +
    "      gap: 6px;\n" +
    "    }\n" +
    "    .inline-actions button {\n" +
    "      flex: 1;\n" +
    "      padding: 6px 8px;\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 600;\n" +
    "      border-radius: 4px;\n" +
    "      cursor: pointer;\n" +
    "    }\n" +
    "    .notice-card {\n" +
    "      padding: 10px 12px;\n" +
    "      border-radius: 6px;\n" +
    "      margin-bottom: 12px;\n" +
    "      font-size: 11px;\n" +
    "      background: #e6f4ea;\n" +
    "      border: 1px solid #34a853;\n" +
    "      color: #137333;\n" +
    "      display: none;\n" +
    "    }\n" +
    "    .notice-card.show { display: block; }\n" +
    "    .notice-card .notice-title {\n" +
    "      font-weight: 700;\n" +
    "      font-size: 12px;\n" +
    "      margin-bottom: 4px;\n" +
    "    }\n" +
    "    .notice-card .notice-actions {\n" +
    "      margin-top: 8px;\n" +
    "      display: flex;\n" +
    "      gap: 6px;\n" +
    "    }\n" +
    "    .section {\n" +
    "      padding-bottom: 14px;\n" +
    "      margin-bottom: 14px;\n" +
    "      border-bottom: 1px solid #f1f3f4;\n" +
    "    }\n" +
    "    .section:last-of-type {\n" +
    "      border-bottom: none;\n" +
    "      margin-bottom: 6px;\n" +
    "    }\n" +
    "    .section-title {\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 700;\n" +
    "      color: #5f6368;\n" +
    "      text-transform: uppercase;\n" +
    "      letter-spacing: 0.5px;\n" +
    "      margin-bottom: 8px;\n" +
    "      display: flex;\n" +
    "      justify-content: space-between;\n" +
    "      align-items: center;\n" +
    "    }\n" +
    "    .btn {\n" +
    "      display: block;\n" +
    "      width: 100%;\n" +
    "      padding: 9px 12px;\n" +
    "      margin-bottom: 6px;\n" +
    "      font-size: 12px;\n" +
    "      font-weight: 600;\n" +
    "      text-align: left;\n" +
    "      border-radius: 6px;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      background: #f8f9fa;\n" +
    "      color: #3c4043;\n" +
    "      cursor: pointer;\n" +
    "      transition: all 0.15s ease;\n" +
    "    }\n" +
    "    .btn:hover:not(:disabled) {\n" +
    "      background: #e8f0fe;\n" +
    "      border-color: #1a73e8;\n" +
    "      color: #1a73e8;\n" +
    "    }\n" +
    "    .btn:disabled {\n" +
    "      opacity: 0.5;\n" +
    "      cursor: not-allowed;\n" +
    "      background: #f1f3f4;\n" +
    "      border-color: #dadce0;\n" +
    "      color: #9aa0a6;\n" +
    "    }\n" +
    "    .btn-primary {\n" +
    "      background: #1a73e8;\n" +
    "      color: #ffffff;\n" +
    "      border-color: #1a73e8;\n" +
    "    }\n" +
    "    .btn-primary:hover:not(:disabled) {\n" +
    "      background: #174ea6;\n" +
    "      border-color: #174ea6;\n" +
    "      color: #ffffff;\n" +
    "    }\n" +
    "    .btn-sm {\n" +
    "      padding: 5px 8px;\n" +
    "      font-size: 11px;\n" +
    "      margin-top: 6px;\n" +
    "      text-align: center;\n" +
    "    }\n" +
    "    .btn-step {\n" +
    "      display: flex;\n" +
    "      align-items: center;\n" +
    "      justify-content: space-between;\n" +
    "    }\n" +
    "    .step-tag {\n" +
    "      font-size: 10px;\n" +
    "      font-weight: 700;\n" +
    "      padding: 1px 6px;\n" +
    "      border-radius: 3px;\n" +
    "      background: #e8eaed;\n" +
    "      color: #5f6368;\n" +
    "    }\n" +
    "    .link-card {\n" +
    "      display: block;\n" +
    "      padding: 8px 12px;\n" +
    "      margin-bottom: 6px;\n" +
    "      background: #f8f9fa;\n" +
    "      border: 1px solid #e8eaed;\n" +
    "      border-radius: 6px;\n" +
    "      text-decoration: none;\n" +
    "      color: #1a73e8;\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 600;\n" +
    "      transition: all 0.15s ease;\n" +
    "    }\n" +
    "    .link-card:hover {\n" +
    "      background: #e8f0fe;\n" +
    "      border-color: #d2e3fc;\n" +
    "    }\n" +
    "    .link-card.disabled {\n" +
    "      color: #9aa0a6;\n" +
    "      pointer-events: none;\n" +
    "      background: #f8f9fa;\n" +
    "      border-color: #f1f3f4;\n" +
    "    }\n" +
    "    .status-bar {\n" +
    "      padding: 8px 12px;\n" +
    "      background: #e8f0fe;\n" +
    "      border: 1px solid #d2e3fc;\n" +
    "      border-radius: 6px;\n" +
    "      font-size: 11px;\n" +
    "      color: #174ea6;\n" +
    "      margin-bottom: 12px;\n" +
    "      display: none;\n" +
    "    }\n" +
    "    .status-bar.show { display: block; }\n" +
    "    .status-bar.error {\n" +
    "      background: #fce8e6;\n" +
    "      border-color: #fad2cf;\n" +
    "      color: #c5221f;\n" +
    "    }\n" +
    "    .status-bar.success {\n" +
    "      background: #e6f4ea;\n" +
    "      border-color: #ceead6;\n" +
    "      color: #0d652d;\n" +
    "    }\n" +
    "    .spinner {\n" +
    "      display: inline-block;\n" +
    "      width: 11px;\n" +
    "      height: 11px;\n" +
    "      border: 2px solid rgba(26, 115, 232, 0.25);\n" +
    "      border-top-color: #1a73e8;\n" +
    "      border-radius: 50%;\n" +
    "      animation: spin 0.8s linear infinite;\n" +
    "      margin-right: 6px;\n" +
    "      vertical-align: middle;\n" +
    "    }\n" +
    "    @keyframes spin {\n" +
    "      to { transform: rotate(360deg); }\n" +
    "    }\n" +
    "    .metrics {\n" +
    "      display: flex;\n" +
    "      gap: 6px;\n" +
    "      margin-top: 4px;\n" +
    "    }\n" +
    "    .metric-box {\n" +
    "      flex: 1;\n" +
    "      background: #f8f9fa;\n" +
    "      border: 1px solid #e8eaed;\n" +
    "      border-radius: 6px;\n" +
    "      padding: 8px 6px;\n" +
    "      text-align: center;\n" +
    "    }\n" +
    "    .metric-val {\n" +
    "      font-size: 12px;\n" +
    "      font-weight: 700;\n" +
    "      color: #202124;\n" +
    "    }\n" +
    "    .metric-lbl {\n" +
    "      font-size: 9px;\n" +
    "      color: #70757a;\n" +
    "      margin-top: 2px;\n" +
    "    }\n" +
    "    .footer-actions {\n" +
    "      margin-top: 14px;\n" +
    "      text-align: center;\n" +
    "      padding-top: 10px;\n" +
    "    }\n" +
    "    .footer-btn {\n" +
    "      background: none;\n" +
    "      border: none;\n" +
    "      color: #70757a;\n" +
    "      font-size: 11px;\n" +
    "      cursor: pointer;\n" +
    "      text-decoration: underline;\n" +
    "    }\n" +
    "    .footer-btn:hover { color: #1a73e8; }\n" +
    "    details.setup-box {\n" +
    "      margin-top: 14px;\n" +
    "      margin-bottom: 12px;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      border-radius: 6px;\n" +
    "      background: #f8f9fa;\n" +
    "      padding: 8px 10px;\n" +
    "    }\n" +
    "    details.setup-box summary {\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 700;\n" +
    "      color: #5f6368;\n" +
    "      cursor: pointer;\n" +
    "      display: flex;\n" +
    "      justify-content: space-between;\n" +
    "      align-items: center;\n" +
    "      user-select: none;\n" +
    "    }\n" +
    "    details.setup-box summary::-webkit-details-marker { display: none; }\n" +
    "    details.setup-box[open] {\n" +
    "      background: #ffffff;\n" +
    "      border-color: #1a73e8;\n" +
    "    }\n" +
    "    details.setup-box .setup-content {\n" +
    "      margin-top: 10px;\n" +
    "      padding-top: 8px;\n" +
    "      border-top: 1px solid #f1f3f4;\n" +
    "    }\n" +
    "  </style>\n" +
    "</head>\n" +
    "<body>\n" +
    "  <div class='header'>\n" +
    "    <div class='header-sub'>\n" +
    "      <span id='campaignCodeBadge' class='badge'>CAMP-2026-AUTUMN</span>\n" +
    "      <span id='apiKeyBadge' class='badge warn' onclick='toggleApiKeyBox(true)' title='클릭하여 API Key 등록'>API Key 확인 중</span>\n" +
    "    </div>\n" +
    "  </div>\n" +
    "\n" +
    "  <div id='onboardingBanner' class='onboarding-card' style='display:none;'>\n" +
    "    <div id='onboardingTitle' class='onboarding-title'>준비 단계</div>\n" +
    "    <div id='onboardingDesc'></div>\n" +
    "    <button id='onboardingBtn' class='btn btn-primary btn-sm'></button>\n" +
    "  </div>\n" +
    "\n" +
    "  <div id='apiKeyInlineBox' class='inline-box' style='display:none;'>\n" +
    "    <div class='inline-box-title'>Gemini API Key 등록 (Google AI Studio)</div>\n" +
    "    <input type='password' id='inputApiKey' class='inline-input' placeholder='AIzaSy... 키를 붙여넣으십시오' />\n" +
    "    <div class='inline-actions'>\n" +
    "      <button class='btn btn-primary' onclick='submitApiKeyInline()'>저장 및 검증</button>\n" +
    "      <button class='btn' onclick='toggleApiKeyBox(false)'>취소</button>\n" +
    "    </div>\n" +
    "  </div>\n" +
    "\n" +
    "  <div id='noticeCard' class='notice-card'>\n" +
    "    <div id='noticeTitle' class='notice-title'>작업 완료</div>\n" +
    "    <div id='noticeDesc'>결과물이 생성되었습니다.</div>\n" +
    "    <div class='notice-actions'>\n" +
    "      <a id='noticeBtn' class='btn btn-primary' target='_blank' href='#'>산출물 바로 열기</a>\n" +
    "      <button class='btn' style='width:auto; padding:6px 12px;' onclick='dismissNotice()'>닫기</button>\n" +
    "    </div>\n" +
    "  </div>\n" +
    "\n" +
    "  <div id='statusBar' class='status-bar'></div>\n" +
    "\n" +
    "  <div class='section'>\n" +
    "    <div class='section-title'>\n" +
    "      <span>5단계 파이프라인 실행</span>\n" +
    "      <span class='step-tag'>Core Flow</span>\n" +
    "    </div>\n" +
    "    <button class='btn btn-step' onclick=\"callServer('guardAndRunIdeaToPlan', '기획서 및 명세서 생성')\">\n" +
    "      <span>[1단계] 기획서 및 명세서 생성</span>\n" +
    "      <span class='step-tag'>PLAN</span>\n" +
    "    </button>\n" +
    "    <button class='btn btn-step' onclick=\"callServer('guardAndRunInitialContent', '초판 콘텐츠 생성')\">\n" +
    "      <span>[2단계] 초판 콘텐츠 생성</span>\n" +
    "      <span class='step-tag'>rv-00</span>\n" +
    "    </button>\n" +
    "    <button class='btn btn-step' onclick=\"callServer('promptAndRunJudgeEvaluation', '25인 AI 페르소나 평가')\">\n" +
    "      <span>[3단계] 25인 AI 페르소나 평가</span>\n" +
    "      <span class='step-tag'>Judge</span>\n" +
    "    </button>\n" +
    "    <button class='btn btn-step' onclick=\"callServer('promptAndRunFeedbackSummary', '피드백 종합 보고서 생성')\">\n" +
    "      <span>[4단계] 피드백 종합 보고서</span>\n" +
    "      <span class='step-tag'>Report</span>\n" +
    "    </button>\n" +
    "    <button class='btn btn-step' onclick=\"callServer('promptAndRunReviseAssets', '피드백 반영 콘텐츠 보정')\">\n" +
    "      <span>[5단계] 피드백 반영 콘텐츠 보정</span>\n" +
    "      <span class='step-tag'>Revise</span>\n" +
    "    </button>\n" +
    "  </div>\n" +
    "\n" +
    "  <div class='section'>\n" +
    "    <div class='section-title'>\n" +
    "      <span>생성된 산출물 바로가기</span>\n" +
    "      <span class='step-tag'>Assets</span>\n" +
    "    </div>\n" +
    "    <a id='linkIdea' class='link-card disabled' href='#'>[아이디어 메모] 구글 독스 열기</a>\n" +
    "    <a id='linkPlan' class='link-card disabled' href='#'>기획서 (PLAN) 열기</a>\n" +
    "    <a id='linkContent' class='link-card disabled' href='#'>최신 콘텐츠 열기 (rv-00)</a>\n" +
    "    <a id='linkForm' class='link-card disabled' href='#'>고객 VoC 설문 폼 열기</a>\n" +
    "    <a id='linkSummary' class='link-card disabled' href='#'>피드백 종합 보고서 열기</a>\n" +
    "    <a id='linkMap' class='link-card disabled' href='#'>t-SNE 여론 지형도 이미지 열기</a>\n" +
    "    <a id='linkFolder' class='link-card disabled' href='#'>캠페인 드라이브 폴더 열기</a>\n" +
    "  </div>\n" +
    "\n" +
    "  <div class='section'>\n" +
    "    <div class='section-title'>\n" +
    "      <span>실행 지표 현황</span>\n" +
    "      <span class='step-tag'>Metrics</span>\n" +
    "    </div>\n" +
    "    <div class='metrics'>\n" +
    "      <div class='metric-box'>\n" +
    "        <div id='valRv' class='metric-val'>-</div>\n" +
    "        <div class='metric-lbl'>최신 리비전</div>\n" +
    "      </div>\n" +
    "      <div class='metric-box'>\n" +
    "        <div id='valFb' class='metric-val'>-</div>\n" +
    "        <div class='metric-lbl'>최신 피드백</div>\n" +
    "      </div>\n" +
    "      <div class='metric-box'>\n" +
    "        <div id='valTokens' class='metric-val'>0</div>\n" +
    "        <div class='metric-lbl'>누적 토큰</div>\n" +
    "      </div>\n" +
    "    </div>\n" +
    "  </div>\n" +
    "\n" +
    "  <details id='setupBox' class='setup-box'>\n" +
    "    <summary>\n" +
    "      <span>환경 설정 및 초기화 (최초 1회)</span>\n" +
    "      <span class='step-tag'>Setup ▼</span>\n" +
    "    </summary>\n" +
    "    <div class='setup-content'>\n" +
    "      <button id='btnApiKey' class='btn' onclick='toggleApiKeyBox(true)'>Gemini API Key 설정 (인라인)</button>\n" +
    "      <button id='btnInit' class='btn btn-primary' onclick=\"callServer('initCampaignWorkspace', '캠페인 작업 공간 구축')\">[초기화] 캠페인 작업 공간 구축</button>\n" +
    "    </div>\n" +
    "  </details>\n" +
    "\n" +
    "  <div class='footer-actions'>\n" +
    "    <button class='footer-btn' onclick='refreshStatus()'>패널 새로고침</button>\n" +
    "     | \n" +
    "    <button class='footer-btn' onclick=\"callServer('openDashboardSheet', '실행 로그 열기')\">실행 로그 열기</button>\n" +
    "     | \n" +
    "    <button class='footer-btn' onclick=\"callServer('forceSyncEngine', '엔진 최신 동기화')\">최신 엔진 동기화</button>\n" +
    "  </div>\n" +
    "\n" +
    "  <script>\n" +
    "    var timerInterval = null;\n" +
    "    var timerSeconds = 0;\n" +
    "    var currentStatusCache = null;\n" +
    "\n" +
    "    function setStatus(htmlOrText, isError, isSuccess) {\n" +
    "      var el = document.getElementById('statusBar');\n" +
    "      if (!htmlOrText) {\n" +
    "        el.className = 'status-bar';\n" +
    "        el.innerHTML = '';\n" +
    "        return;\n" +
    "      }\n" +
    "      var cls = 'status-bar show';\n" +
    "      if (isError) cls += ' error';\n" +
    "      else if (isSuccess) cls += ' success';\n" +
    "      el.className = cls;\n" +
    "      el.innerHTML = htmlOrText;\n" +
    "    }\n" +
    "\n" +
    "    function startTimer(taskName) {\n" +
    "      clearInterval(timerInterval);\n" +
    "      timerSeconds = 0;\n" +
    "      dismissNotice();\n" +
    "      setStatus(\"<span class='spinner'></span> <span>\" + taskName + \" 실행 중... (<strong>0초</strong> 경과)</span>\", false);\n" +
    "      timerInterval = setInterval(function() {\n" +
    "        timerSeconds++;\n" +
    "        setStatus(\"<span class='spinner'></span> <span>\" + taskName + \" 실행 중... (<strong>\" + timerSeconds + \"초</strong> 경과)</span>\", false);\n" +
    "      }, 1000);\n" +
    "    }\n" +
    "\n" +
    "    function stopTimer(successMsg, isError) {\n" +
    "      clearInterval(timerInterval);\n" +
    "      if (isError) {\n" +
    "        setStatus(successMsg, true);\n" +
    "      } else {\n" +
    "        var durText = timerSeconds > 0 ? \" (총 \" + timerSeconds + \"초 소요)\" : \"\";\n" +
    "        setStatus(\"✓ \" + (successMsg || \"작업이 성공적으로 완결되었습니다.\") + durText, false, true);\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    function setButtonsDisabled(disabled) {\n" +
    "      var btns = document.querySelectorAll('button:not(.footer-btn)');\n" +
    "      btns.forEach(function(b) { b.disabled = disabled; });\n" +
    "    }\n" +
    "\n" +
    "    function toggleApiKeyBox(show) {\n" +
    "      var box = document.getElementById('apiKeyInlineBox');\n" +
    "      box.style.display = show ? 'block' : 'none';\n" +
    "      if (show) {\n" +
    "        var inp = document.getElementById('inputApiKey');\n" +
    "        inp.value = '';\n" +
    "        inp.focus();\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    function submitApiKeyInline() {\n" +
    "      var val = document.getElementById('inputApiKey').value.trim();\n" +
    "      if (!val) {\n" +
    "        alert('API Key를 입력해 주십시오.');\n" +
    "        return;\n" +
    "      }\n" +
    "      setStatus(\"<span class='spinner'></span> API Key 저장 및 검증 중...\", false);\n" +
    "      google.script.run\n" +
    "        .withSuccessHandler(function(res) {\n" +
    "          if (res && res.success) {\n" +
    "            toggleApiKeyBox(false);\n" +
    "            setStatus('✓ ' + res.message, false, true);\n" +
    "            refreshStatus();\n" +
    "          } else {\n" +
    "            setStatus(res ? res.message : 'API Key 저장 실패', true);\n" +
    "          }\n" +
    "        })\n" +
    "        .withFailureHandler(function(err) {\n" +
    "          setStatus('API Key 저장 오류: ' + (err.message || err), true);\n" +
    "        })\n" +
    "        .saveApiKeyInline(val);\n" +
    "    }\n" +
    "\n" +
    "    function showNoticeCard(title, desc, btnText, btnUrl) {\n" +
    "      var card = document.getElementById('noticeCard');\n" +
    "      document.getElementById('noticeTitle').textContent = title;\n" +
    "      document.getElementById('noticeDesc').textContent = desc;\n" +
    "      var btn = document.getElementById('noticeBtn');\n" +
    "      if (btnUrl) {\n" +
    "        btn.href = btnUrl;\n" +
    "        btn.textContent = btnText || '산출물 열기';\n" +
    "        btn.style.display = 'inline-block';\n" +
    "      } else {\n" +
    "        btn.style.display = 'none';\n" +
    "      }\n" +
    "      card.className = 'notice-card show';\n" +
    "    }\n" +
    "\n" +
    "    function dismissNotice() {\n" +
    "      document.getElementById('noticeCard').className = 'notice-card';\n" +
    "    }\n" +
    "\n" +
    "    function updateUI(status) {\n" +
    "      if (!status) return;\n" +
    "      currentStatusCache = status;\n" +
    "\n" +
    "      var keyBadge = document.getElementById('apiKeyBadge');\n" +
    "      var onboarding = document.getElementById('onboardingBanner');\n" +
    "      var setupBox = document.getElementById('setupBox');\n" +
    "\n" +
    "      // 1. API Key 상태 및 온보딩 배너 관리\n" +
    "      if (status.hasApiKey) {\n" +
    "        keyBadge.className = 'badge active';\n" +
    "        keyBadge.textContent = 'API Key 등록됨';\n" +
    "        keyBadge.onclick = function() { toggleApiKeyBox(true); };\n" +
    "      } else {\n" +
    "        keyBadge.className = 'badge warn';\n" +
    "        keyBadge.textContent = 'API Key 필요';\n" +
    "        keyBadge.onclick = function() { toggleApiKeyBox(true); };\n" +
    "      }\n" +
    "\n" +
    "      if (!status.hasApiKey) {\n" +
    "        onboarding.className = 'onboarding-card warn';\n" +
    "        onboarding.style.display = 'block';\n" +
    "        document.getElementById('onboardingTitle').textContent = '준비 1단계: API Key 등록';\n" +
    "        document.getElementById('onboardingDesc').textContent = 'Gemini API 호출을 위해 Google AI Studio 무료 API Key를 먼저 등록해 주십시오.';\n" +
    "        var obBtn = document.getElementById('onboardingBtn');\n" +
    "        obBtn.textContent = '지금 API Key 등록하기';\n" +
    "        obBtn.onclick = function() { toggleApiKeyBox(true); };\n" +
    "        setupBox.open = true;\n" +
    "      } else if (!status.folderUrl) {\n" +
    "        onboarding.className = 'onboarding-card info';\n" +
    "        onboarding.style.display = 'block';\n" +
    "        document.getElementById('onboardingTitle').textContent = '준비 2단계: 작업 공간 초기화';\n" +
    "        document.getElementById('onboardingDesc').textContent = '캠페인 부모 폴더를 감지하고 필수 프롬프트와 작업 공간을 구축해 주십시오.';\n" +
    "        var obBtn = document.getElementById('onboardingBtn');\n" +
    "        obBtn.textContent = '[초기화] 캠페인 작업 공간 구축';\n" +
    "        obBtn.onclick = function() { callServer('initCampaignWorkspace', '캠페인 작업 공간 구축'); };\n" +
    "        setupBox.open = true;\n" +
    "      } else {\n" +
    "        onboarding.style.display = 'none';\n" +
    "        setupBox.open = false;\n" +
    "      }\n" +
    "\n" +
    "      // 2. 캠페인 코드 배지\n" +
    "      if (status.campaignCode) {\n" +
    "        document.getElementById('campaignCodeBadge').textContent = status.campaignCode;\n" +
    "      }\n" +
    "\n" +
    "      // 3. 생성된 산출물 바로가기 카드 갱신 (명칭 정제 및 실제 회차 번호 바인딩)\n" +
    "      updateLink('linkIdea', status.ideaDocUrl, '[아이디어 메모] 구글 독스 열기');\n" +
    "      updateLink('linkPlan', status.planDocUrl, '기획서 (PLAN) 열기');\n" +
    "      var rvLabel = '최신 콘텐츠 열기 (' + (status.latestRv || 'rv-00') + ')';\n" +
    "      updateLink('linkContent', status.contentDocUrl, rvLabel);\n" +
    "      updateLink('linkForm', status.formUrl, '고객 VoC 설문 폼 열기');\n" +
    "      updateLink('linkSummary', status.summaryDocUrl, '피드백 종합 보고서 열기');\n" +
    "      updateLink('linkMap', status.mapUrl, 't-SNE 여론 지형도 이미지 열기');\n" +
    "      updateLink('linkFolder', status.folderUrl, '캠페인 드라이브 폴더 열기');\n" +
    "\n" +
    "      // 4. 지표 현황\n" +
    "      document.getElementById('valRv').textContent = status.latestRv || '-';\n" +
    "      document.getElementById('valFb').textContent = status.latestFb || '-';\n" +
    "      document.getElementById('valTokens').textContent = (status.totalTokens || 0).toLocaleString();\n" +
    "    }\n" +
    "\n" +
    "    function updateLink(id, url, customText) {\n" +
    "      var el = document.getElementById(id);\n" +
    "      if (!el) return;\n" +
    "      if (customText) el.textContent = customText;\n" +
    "      if (url) {\n" +
    "        el.href = url;\n" +
    "        el.className = 'link-card';\n" +
    "      } else {\n" +
    "        el.href = '#';\n" +
    "        el.className = 'link-card disabled';\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    function refreshStatus() {\n" +
    "      google.script.run\n" +
    "        .withSuccessHandler(function(status) {\n" +
    "          updateUI(status);\n" +
    "        })\n" +
    "        .withFailureHandler(function(err) {\n" +
    "          setStatus('상태 갱신 오류: ' + (err.message || err), true);\n" +
    "        })\n" +
    "        .getPipelineStatus();\n" +
    "    }\n" +
    "\n" +
    "    function callServer(fnName, taskName) {\n" +
    "      var displayName = taskName || fnName;\n" +
    "      setButtonsDisabled(true);\n" +
    "      startTimer(displayName);\n" +
    "\n" +
    "      google.script.run\n" +
    "        .withSuccessHandler(function(res) {\n" +
    "          setButtonsDisabled(false);\n" +
    "          stopTimer(displayName + ' 작업이 성공적으로 완결되었습니다.', false);\n" +
    "          refreshStatus();\n" +
    "\n" +
    "          // 완료 직후 최신 산출물 바로가기 카드 띄우기\n" +
    "          setTimeout(function() {\n" +
    "            if (currentStatusCache) {\n" +
    "              if (fnName === 'guardAndRunIdeaToPlan' && currentStatusCache.planDocUrl) {\n" +
    "                showNoticeCard('기획서 도출 완료', '캠페인 기획서(PLAN)와 제작 명세서(SPEC)가 준비되었습니다.', '기획서 (PLAN) 열기', currentStatusCache.planDocUrl);\n" +
    "              } else if (fnName === 'guardAndRunInitialContent' && currentStatusCache.contentDocUrl) {\n" +
    "                showNoticeCard('초판 콘텐츠 제작 완료', '멀티 채널 카피, 비주얼 이미지 3종, 숏폼 영상이 완성되었습니다.', '최신 콘텐츠 열기', currentStatusCache.contentDocUrl);\n" +
    "              } else if (fnName === 'promptAndRunFeedbackSummary' && currentStatusCache.summaryDocUrl) {\n" +
    "                showNoticeCard('피드백 종합 보고서 완료', 't-SNE 여론 지형도와 25인 다면 평가 분석이 완료되었습니다.', '피드백 보고서 열기', currentStatusCache.summaryDocUrl);\n" +
    "              } else if (fnName === 'initCampaignWorkspace' && currentStatusCache.ideaDocUrl) {\n" +
    "                showNoticeCard('작업 공간 구축 완료', '아이디어 메모 및 필수 작업 환경 구축이 완료되었습니다.', '[아이디어 메모] 열기', currentStatusCache.ideaDocUrl);\n" +
    "              }\n" +
    "            }\n" +
    "          }, 800);\n" +
    "        })\n" +
    "        .withFailureHandler(function(err) {\n" +
    "          setButtonsDisabled(false);\n" +
    "          stopTimer('오류 발생: ' + (err.message || err), true);\n" +
    "        })[fnName]();\n" +
    "    }\n" +
    "\n" +
    "    // 패널 열림 시 최초 1회 상태 자동 조회\n" +
    "    window.onload = function() {\n" +
    "      refreshStatus();\n" +
    "    };\n" +
    "  </script>\n" +
    "</body>\n" +
    "</html>";
}
