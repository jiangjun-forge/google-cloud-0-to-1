/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline - Ultra-light Bootstrap Loader
 *
 * [경량 자동 갱신 부트스트랩 로더]
 * 사용자가 Google Sheets Apps Script 편집기에 단 1회만 붙여넣으면,
 * GitHub 퍼블릭 저장소의 최신 bundle_apps_script.js를 실시간으로 자동 동기화하여 구동합니다.
 * 이후 기능 개선이나 버그 패치가 발생해도 사용자는 Apps Script 코드를 다시 수정할 필요가 없습니다.
 */

var BOOTSTRAP_CONFIG = {
  VERSION: "2026.10.15.zero-modal-v53",
  BUNDLE_URL: "https://raw.githubusercontent.com/jiangjun-forge/google-cloud-0-to-1/main/samples/gws-marketing-content-pipeline/bundle_apps_script.js",
  PROP_PREFIX: "ENGINE_CHUNK_",
  PROP_COUNT: "ENGINE_CHUNK_COUNT",
  PROP_SYNC_DATE: "ENGINE_LAST_SYNCED",
  PROP_VERSION: "ENGINE_BOOTSTRAP_VERSION"
};

// 단일 실행 세션 내 고속 재사용을 위한 인메모리 캐시 (0ms)
var __PIPELINE_IN_MEMORY_CODE__ = null;

/**
 * 파이프라인 엔진 코드를 로드한다.
 * [영구 재사용 및 버전 자동 무효화]:
 * 1. 영구 저장소의 엔진 버전이 최신과 일치할 때 로컬 코드 즉시 복원 (GitHub 네트워크 호출 0회).
 * 2. 버전 불일치 또는 명시적 갱신 시 GitHub 퍼블릭 저장소로부터 최신 번들을 자동 1회 다운로드하여 즉시 반영.
 *
 * @param {boolean} forceRefresh - 캐시를 무시하고 GitHub 최신 코드를 강제 다운로드할지 여부
 */
function loadPipelineEngine(forceRefresh) {
  // 1. 현재 세션 메모리에 이미 로드되어 있는 경우 즉시 전역 실행 (0ms)
  if (!forceRefresh && __PIPELINE_IN_MEMORY_CODE__) {
    (1, eval)(__PIPELINE_IN_MEMORY_CODE__);
    return;
  }

  var scriptProps = PropertiesService.getScriptProperties();
  var savedVersion = scriptProps.getProperty(BOOTSTRAP_CONFIG.PROP_VERSION);
  var isVersionMatch = (savedVersion === BOOTSTRAP_CONFIG.VERSION);
  var fullCode = "";

  // 2. 영구 저장소(ScriptProperties)에서 로컬 코드 즉시 복원
  if (!forceRefresh && isVersionMatch) {
    var chunkCountStr = scriptProps.getProperty(BOOTSTRAP_CONFIG.PROP_COUNT);
    if (chunkCountStr) {
      var count = parseInt(chunkCountStr, 10);
      var allProps = scriptProps.getProperties();
      var parts = [];
      for (var i = 0; i < count; i++) {
        var part = allProps[BOOTSTRAP_CONFIG.PROP_PREFIX + i];
        if (part) {
          parts.push(part);
        }
      }
      if (parts.length === count) {
        fullCode = parts.join("");
        Logger.log("구글 시트 영구 저장소로부터 로컬 엔진 고속 로드 완료 (버전: " + savedVersion + ")");
      }
    }
  }

  // 3. 영구 저장소에 코드가 없거나, 버전 불일치, 또는 사용자가 명시적 동기화를 요청한 경우 GitHub 1회 호출
  if (!fullCode) {
    Logger.log("GitHub 퍼블릭 저장소로부터 최신 파이프라인 엔진 다운로드 시작 (" + BOOTSTRAP_CONFIG.VERSION + "): " + BOOTSTRAP_CONFIG.BUNDLE_URL);
    var resp = UrlFetchApp.fetch(BOOTSTRAP_CONFIG.BUNDLE_URL, { muteHttpExceptions: true });
    if (resp.getResponseCode() === 200) {
      fullCode = resp.getContentText();

      // PropertiesService 키당 9KB 용량 제한을 준수하기 위해 8KB 단위로 청크 분할 영구 저장
      var chunkSize = 8000;
      var newProps = {};
      var chunkIdx = 0;
      for (var j = 0; j < fullCode.length; j += chunkSize) {
        newProps[BOOTSTRAP_CONFIG.PROP_PREFIX + chunkIdx] = fullCode.substring(j, j + chunkSize);
        chunkIdx++;
      }
      newProps[BOOTSTRAP_CONFIG.PROP_COUNT] = "" + chunkIdx;
      newProps[BOOTSTRAP_CONFIG.PROP_SYNC_DATE] = new Date().toISOString();
      newProps[BOOTSTRAP_CONFIG.PROP_VERSION] = BOOTSTRAP_CONFIG.VERSION;

      scriptProps.setProperties(newProps);
      Logger.log("GitHub 최신 엔진 구글 시트 영구 저장 완료 (총 " + chunkIdx + "개 청크 저장, 버전: " + BOOTSTRAP_CONFIG.VERSION + ")");
    } else {
      throw new Error("GitHub 퍼블릭 저장소로부터 엔진 코드를 가져오지 못했습니다. (HTTP 응답 코드: " + resp.getResponseCode() + ")");
    }
  }

  __PIPELINE_IN_MEMORY_CODE__ = fullCode;

  // 간접 eval을 실행하여 전역(Global) 스코프에 모든 함수와 전역 객체를 등록
  (1, eval)(fullCode);
}

/**
 * 전역 스코프에서 타깃 함수를 안전하게 탐색한다.
 */
function findTargetFunction(fnName) {
  if (typeof globalThis !== "undefined" && typeof globalThis[fnName] === "function") {
    return globalThis[fnName];
  }
  if (typeof this !== "undefined" && typeof this[fnName] === "function") {
    return this[fnName];
  }
  try {
    var fn = eval(fnName);
    if (typeof fn === "function") return fn;
  } catch (e) {
    // 무시
  }
  return null;
}

/**
 * 부트스트랩 프록시 디스패처 (런타임 함수 동적 호출)
 * [자가 치유(Self-Healing) 엔진]:
 * 1. 로컬 캐시에서 코드를 로드하여 실행을 시도한다.
 * 2. 만약 해당 함수가 로컬 캐시에 없다면(신규 기능 추가 등), 즉시 GitHub에서 최신 엔진을 1회 자동 다운로드하여 자가 치유 갱신 후 실행한다.
 * 3. 예외 발생 시 구글 시트 알림 대화상자로 명확한 원인을 즉각 안내한다.
 */
function dispatch(fnName, args) {
  try {
    loadPipelineEngine(false);
    var targetFn = findTargetFunction(fnName);

    // [핵심] 캐시된 로컬 코드에 해당 함수가 없는 경우, GitHub 최신 코드를 즉시 자동 갱신!
    if (!targetFn) {
      Logger.log("함수 [" + fnName + "] 미발견, GitHub 최신 엔진 자동 동기화 시도...");
      loadPipelineEngine(true);
      targetFn = findTargetFunction(fnName);
    }

    if (typeof targetFn === "function") {
      return targetFn.apply(this, args || []);
    } else {
      throw new Error("파이프라인 엔진 내에 함수 [" + fnName + "]가 정의되지 않았습니다.");
    }
  } catch (err) {
    Logger.log("dispatch 오류 [" + fnName + "]: " + err);
    throw err;
  }
}

// ============================================================================
// Google Sheets 커스텀 메뉴 트리거 및 프록시 함수 엔트리포인트
// ============================================================================

/**
 * Google Sheets 액션 중심 커스텀 메뉴 렌더링
 * [단일 엔트리포인트]: 모든 제어 기능이 우측 패널(사이드바)에 완비되어 있으므로,
 * 상단 메뉴는 오직 패널 재진입용 단 1개 버튼만 미니멀하게 제공한다.
 */
function renderPipelineMenu() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("[마케팅 콘텐츠 파이프라인]")
    .addItem("제어 패널 열기 (Open Panel)", "showPipelineSidebar")
    .addToUi();
}

/**
 * 구글 시트 문서 열림 시 메뉴 자동 등록 및 사이드바 표시 시도 (단순 트리거)
 */
function onOpen() {
  renderPipelineMenu();
  try {
    showPipelineSidebar();
  } catch (e) {
    // 단순 트리거 환경에서의 권한 제약 시 무시
  }
}

// 액션 메뉴 디스패치 및 사이드바 RPC 프록시 함수들 (사용자 클릭 시 지연 로드 및 실행)
function showPipelineSidebar() { dispatch("showPipelineSidebar"); }
function getPipelineStatus() { return dispatch("getPipelineStatus"); }
function initCampaignWorkspace() { return dispatch("initCampaignWorkspace"); }
function runConfigureCampaignSettings(newCode) { return dispatch("runConfigureCampaignSettings", [newCode]); }
function runCampaignIdeaMemo(customIdea) { return dispatch("runCampaignIdeaMemo", [customIdea]); }
function promptAndRunIdeaMemo(customIdea) { return dispatch("promptAndRunIdeaMemo", [customIdea]); }
function runIdeaToPlan(customIdea) { return dispatch("runIdeaToPlan", [customIdea]); }
function guardAndRunIdeaToPlan(customIdea) { return dispatch("guardAndRunIdeaToPlan", [customIdea]); }
function runPlanToSpec() { return dispatch("runPlanToSpec"); }
function guardAndRunPlanToSpec() { return dispatch("guardAndRunPlanToSpec"); }
function runPersonaPanelSynthesis() { return dispatch("runPersonaPanelSynthesis"); }
function guardAndRunPersonaSynthesis() { return dispatch("guardAndRunPersonaSynthesis"); }
function runInitialContentGeneration(forceOverwrite) { return dispatch("runInitialContentGeneration", [forceOverwrite]); }
function guardAndRunInitialContent(forceOverwrite) { return dispatch("guardAndRunInitialContent", [forceOverwrite]); }
function forceRunInitialContent() { return dispatch("forceRunInitialContent"); }
function runPersonaEvaluation(targetRound) { return dispatch("runPersonaEvaluation", [targetRound]); }
function promptAndRunJudgeEvaluation(targetRound) { return dispatch("promptAndRunJudgeEvaluation", [targetRound]); }
function runFeedbackSummaryReport(targetRound) { return dispatch("runFeedbackSummaryReport", [targetRound]); }
function promptAndRunFeedbackSummary(targetRound) { return dispatch("promptAndRunFeedbackSummary", [targetRound]); }
function runMarketerDirective(customDirective, targetRound) { return dispatch("runMarketerDirective", [customDirective, targetRound]); }
function promptAndRunMarketerDirective(customDirective, targetRound) { return dispatch("promptAndRunMarketerDirective", [customDirective, targetRound]); }
function runReviseContent(targetRound, isSilent, forceAll, customDirective) { return dispatch("runReviseContent", [targetRound, isSilent, forceAll, customDirective]); }
function promptAndRunFeedbackRevision(customDirectiveOrTargetRv) { return dispatch("promptAndRunFeedbackRevision", [customDirectiveOrTargetRv]); }
function openCustomerVocForm() { return dispatch("openCustomerVocForm"); }
function setCustomPersonasPrompt(criteria) { return dispatch("setCustomPersonasPrompt", [criteria]); }
function promptForGeminiApiKey() { return dispatch("promptForGeminiApiKey"); }
function openDashboardSheet() { dispatch("openDashboardSheet"); }
function saveApiKeyInline(apiKey) { return dispatch("saveApiKeyInline", [apiKey]); }
function askPipelineAssistant(userMessage) { return dispatch("askPipelineAssistant", [userMessage]); }

/**
 * GitHub 퍼블릭 저장소 최신 엔진 코드 즉시 강제 갱신 (모달 배제)
 */
function forceSyncEngine() {
  try {
    loadPipelineEngine(true);

    try {
      if (typeof this.renderPipelineMenu === "function") {
        this.renderPipelineMenu();
      } else {
        renderPipelineMenu();
      }
    } catch (menuErr) {
      renderPipelineMenu();
    }

    try {
      showPipelineSidebar();
    } catch (sidebarErr) {
      // 무시
    }

    return {
      success: true,
      message: "GitHub 퍼블릭 저장소의 최신 버전 파이프라인 엔진 코드가 성공적으로 갱신되었습니다."
    };
  } catch (err) {
    Logger.log("엔진 동기화 실패: " + err);
    throw err;
  }
}

/**
 * [자동 스코프 감지용 정적 더미 함수]
 * 사용자가 appsscript.json 매니페스트 설정을 실수로 건너뛰더라도,
 * Google Apps Script 엔진이 정적으로 필요한 OAuth 권한(Drive, Docs, Forms, Sheets, UrlFetch)을
 * 자동으로 감지하여 최초 1회 승인 팝업에 모두 포함하도록 보장한다.
 */
function __staticOAuthScopeDeclarations() {
  if (false) {
    SpreadsheetApp.getActiveSpreadsheet();
    SpreadsheetApp.getUi().showSidebar(HtmlService.createHtmlOutput(""));
    HtmlService.createHtmlOutput("");
    DriveApp.getRootFolder();
    DocumentApp.create("dummy");
    FormApp.create("dummy");
    UrlFetchApp.fetch("https://raw.githubusercontent.com");
    PropertiesService.getUserProperties();
    CacheService.getScriptCache();
  }
}
