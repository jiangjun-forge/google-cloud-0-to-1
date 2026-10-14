/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 9] 구글 시트 우측 패널(Sidebar) 모던 HTML 컨트롤 타워 UI
 */

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
    var code = getCampaignCode();
    if (code) status.campaignCode = code;

    var folder = getCampaignFolder();
    if (folder) {
      status.folderUrl = folder.getUrl();

      var ideaFiles = folder.getFilesByName("[아이디어 메모] 2026 가을 오텀 브리즈 캠페인");
      if (ideaFiles.hasNext()) status.ideaDocUrl = ideaFiles.next().getUrl();

      var planFiles = folder.getFilesByName("PLAN.md");
      if (planFiles.hasNext()) status.planDocUrl = planFiles.next().getUrl();

      var specFiles = folder.getFilesByName("SPEC.md");
      if (specFiles.hasNext()) status.specDocUrl = specFiles.next().getUrl();

      var formFiles = folder.getFilesByType(MimeType.GOOGLE_FORMS);
      if (formFiles.hasNext()) status.formUrl = formFiles.next().getUrl();

      var latestRvNum = detectLatestRevisionRoundNum();
      if (latestRvNum >= 0) {
        status.latestRv = "rv-" + (latestRvNum < 10 ? "0" + latestRvNum : latestRvNum);
        var rvFolder = getCampaignSubFolder(["output", status.latestRv]);
        var contentFiles = rvFolder.getFilesByName("campaign_content.md");
        if (contentFiles.hasNext()) status.contentDocUrl = contentFiles.next().getUrl();
      }

      var latestFbNum = detectLatestFeedbackRoundNum();
      if (latestFbNum > 0) {
        status.latestFb = "fb-" + (latestFbNum < 10 ? "0" + latestFbNum : latestFbNum);
        var fbFolder = getCampaignSubFolder(["input", status.latestFb]);
        var summaryFiles = fbFolder.getFilesByName("feedback_summary.md");
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
    "      padding-bottom: 12px;\n" +
    "      margin-bottom: 14px;\n" +
    "      border-bottom: 1px solid #dadce0;\n" +
    "    }\n" +
    "    .header h2 {\n" +
    "      font-size: 15px;\n" +
    "      font-weight: 700;\n" +
    "      color: #1a73e8;\n" +
    "      margin-bottom: 6px;\n" +
    "      letter-spacing: -0.3px;\n" +
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
    "    .badge.warn { background: #fef7e0; color: #b06000; }\n" +
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
    "    <h2>마케팅 콘텐츠 파이프라인</h2>\n" +
    "    <div class='header-sub'>\n" +
    "      <span id='campaignCodeBadge' class='badge'>CAMP-2026-AUTUMN</span>\n" +
    "      <span id='apiKeyBadge' class='badge warn'>API Key 확인 중</span>\n" +
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
    "    <button class='btn btn-step' onclick=\"callServer('guardAndRunIdeaToPlan')\">\n" +
    "      <span>[1단계] 기획서 및 명세서 생성</span>\n" +
    "      <span class='step-tag'>PLAN</span>\n" +
    "    </button>\n" +
    "    <button class='btn btn-step' onclick=\"callServer('guardAndRunInitialContent')\">\n" +
    "      <span>[2단계] 초판 콘텐츠 생성</span>\n" +
    "      <span class='step-tag'>rv-00</span>\n" +
    "    </button>\n" +
    "    <button class='btn btn-step' onclick=\"callServer('promptAndRunJudgeEvaluation')\">\n" +
    "      <span>[3단계] 25인 AI 페르소나 평가</span>\n" +
    "      <span class='step-tag'>Judge</span>\n" +
    "    </button>\n" +
    "    <button class='btn btn-step' onclick=\"callServer('promptAndRunFeedbackSummary')\">\n" +
    "      <span>[4단계] 피드백 종합 보고서</span>\n" +
    "      <span class='step-tag'>Report</span>\n" +
    "    </button>\n" +
    "    <button class='btn btn-step' onclick=\"callServer('promptAndRunReviseAssets')\">\n" +
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
    "    <a id='linkFolder' class='link-card disabled' href='#'>캠페인 드라이브 폴더 열기</a>\n" +
    "    <a id='linkPlan' class='link-card disabled' href='#'>기획서 (PLAN.md) 열기</a>\n" +
    "    <a id='linkContent' class='link-card disabled' href='#'>최신 콘텐츠 (rv-xx) 열기</a>\n" +
    "    <a id='linkForm' class='link-card disabled' href='#'>고객 VoC 설문 폼 열기</a>\n" +
    "    <a id='linkSummary' class='link-card disabled' href='#'>피드백 종합 보고서 열기</a>\n" +
    "    <a id='linkMap' class='link-card disabled' href='#'>t-SNE 여론 지형도 이미지 열기</a>\n" +
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
    "  <details class='setup-box'>\n" +
    "    <summary>\n" +
    "      <span>환경 설정 및 초기화 (최초 1회)</span>\n" +
    "      <span class='step-tag'>Setup ▼</span>\n" +
    "    </summary>\n" +
    "    <div class='setup-content'>\n" +
    "      <button id='btnApiKey' class='btn' onclick=\"callServer('promptForGeminiApiKey')\">Gemini API Key 설정</button>\n" +
    "      <button id='btnInit' class='btn btn-primary' onclick=\"callServer('initCampaignWorkspace')\">[초기화] 캠페인 작업 공간 구축</button>\n" +
    "    </div>\n" +
    "  </details>\n" +
    "\n" +
    "  <div class='footer-actions'>\n" +
    "    <button class='footer-btn' onclick='refreshStatus()'>패널 상태 새로고침</button>\n" +
    "     | \n" +
    "    <button class='footer-btn' onclick=\"callServer('openDashboardSheet')\">실행 로그 열기</button>\n" +
    "     | \n" +
    "    <button class='footer-btn' onclick=\"callServer('forceSyncEngine')\">GitHub 최신 엔진 동기화</button>\n" +
    "  </div>\n" +
    "\n" +
    "  <script>\n" +
    "    function setStatus(msg, isError) {\n" +
    "      var el = document.getElementById('statusBar');\n" +
    "      if (!msg) {\n" +
    "        el.className = 'status-bar';\n" +
    "        el.textContent = '';\n" +
    "        return;\n" +
    "      }\n" +
    "      el.className = 'status-bar show' + (isError ? ' error' : '');\n" +
    "      el.textContent = msg;\n" +
    "    }\n" +
    "\n" +
    "    function setButtonsDisabled(disabled) {\n" +
    "      var btns = document.querySelectorAll('button');\n" +
    "      btns.forEach(function(b) { b.disabled = disabled; });\n" +
    "    }\n" +
    "\n" +
    "    function updateUI(status) {\n" +
    "      if (!status) return;\n" +
    "\n" +
    "      var keyBadge = document.getElementById('apiKeyBadge');\n" +
    "      if (status.hasApiKey) {\n" +
    "        keyBadge.className = 'badge active';\n" +
    "        keyBadge.textContent = 'API Key 등록됨';\n" +
    "      } else {\n" +
    "        keyBadge.className = 'badge warn';\n" +
    "        keyBadge.textContent = 'API Key 필요';\n" +
    "      }\n" +
    "\n" +
    "      if (status.campaignCode) {\n" +
    "        document.getElementById('campaignCodeBadge').textContent = status.campaignCode;\n" +
    "      }\n" +
    "\n" +
    "      updateLink('linkFolder', status.folderUrl);\n" +
    "      updateLink('linkPlan', status.planDocUrl);\n" +
    "      updateLink('linkContent', status.contentDocUrl);\n" +
    "      updateLink('linkForm', status.formUrl);\n" +
    "      updateLink('linkSummary', status.summaryDocUrl);\n" +
    "      updateLink('linkMap', status.mapUrl);\n" +
    "\n" +
    "      document.getElementById('valRv').textContent = status.latestRv || '-';\n" +
    "      document.getElementById('valFb').textContent = status.latestFb || '-';\n" +
    "      document.getElementById('valTokens').textContent = (status.totalTokens || 0).toLocaleString();\n" +
    "    }\n" +
    "\n" +
    "    function updateLink(id, url) {\n" +
    "      var el = document.getElementById(id);\n" +
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
    "      setStatus('상태 갱신 중...', false);\n" +
    "      google.script.run\n" +
    "        .withSuccessHandler(function(status) {\n" +
    "          updateUI(status);\n" +
    "          setStatus('', false);\n" +
    "        })\n" +
    "        .withFailureHandler(function(err) {\n" +
    "          setStatus('상태 갱신 오류: ' + (err.message || err), true);\n" +
    "        })\n" +
    "        .getPipelineStatus();\n" +
    "    }\n" +
    "\n" +
    "    function callServer(fnName) {\n" +
    "      setButtonsDisabled(true);\n" +
    "      setStatus('작업 실행 중입니다. 잠시만 기다려주십시오...', false);\n" +
    "      google.script.run\n" +
    "        .withSuccessHandler(function() {\n" +
    "          setButtonsDisabled(false);\n" +
    "          setStatus('작업이 성공적으로 완결되었습니다.', false);\n" +
    "          refreshStatus();\n" +
    "        })\n" +
    "        .withFailureHandler(function(err) {\n" +
    "          setButtonsDisabled(false);\n" +
    "          setStatus('오류 발생: ' + (err.message || err), true);\n" +
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
