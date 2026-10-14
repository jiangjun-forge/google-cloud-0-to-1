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
  BUNDLE_URL: "https://raw.githubusercontent.com/jiangjun-forge/google-cloud-0-to-1/main/samples/drive-marketing-content-pipeline/bundle_apps_script.js",
  PROP_PREFIX: "ENGINE_CHUNK_",
  PROP_COUNT: "ENGINE_CHUNK_COUNT",
  PROP_SYNC_DATE: "ENGINE_LAST_SYNCED"
};

// 단일 실행 세션 내 고속 재사용을 위한 인메모리 캐시 (0ms)
var __PIPELINE_IN_MEMORY_CODE__ = null;

/**
 * 파이프라인 엔진 코드를 로드한다.
 * [영구 재사용 원칙]:
 * 1. 최초 1회 실행 시에만 GitHub 퍼블릭 저장소로부터 코드를 땡겨와 Google Sheets 영구 저장소(ScriptProperties)에 저장한다.
 * 2. 이후 모든 기능 실행(기획, 생성, 평가, 보고서, 보정) 시에는 GitHub을 일절 호출하지 않고(호출 0회),
 *    구글 시트 영구 저장소로부터 0.001초 만에 로컬 코드를 꺼내어 즉시 실행한다.
 * 3. 사용자가 [엔진 최신 버전 동기화] 메뉴를 명시적으로 클릭할 때에만 GitHub에서 최신 코드를 다시 땡겨와 갱신한다.
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
  var fullCode = "";

  // 2. [핵심] 영구 저장소(ScriptProperties)에서 로컬 코드 즉시 복원 (GitHub 호출 0회)
  if (!forceRefresh) {
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
        Logger.log("구글 시트 영구 저장소로부터 로컬 엔진 고속 로드 완료 (GitHub 네트워크 호출 0회)");
      }
    }
  }

  // 3. 영구 저장소에 코드가 없거나(최초 1회), 사용자가 명시적 동기화를 요청한 경우에만 GitHub 1회 호출
  if (!fullCode) {
    Logger.log("GitHub 퍼블릭 저장소로부터 최신 파이프라인 엔진 1회 다운로드 시작: " + BOOTSTRAP_CONFIG.BUNDLE_URL);
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

      scriptProps.setProperties(newProps);
      Logger.log("GitHub 최신 엔진 구글 시트 영구 저장 완료 (총 " + chunkIdx + "개 청크 저장, 영구 보존)");
    } else {
      throw new Error("GitHub 퍼블릭 저장소로부터 엔진 코드를 가져오지 못했습니다. (HTTP 응답 코드: " + resp.getResponseCode() + ")");
    }
  }

  __PIPELINE_IN_MEMORY_CODE__ = fullCode;

  // 간접 eval을 실행하여 전역(Global) 스코프에 모든 함수와 전역 객체를 등록
  (1, eval)(fullCode);
}

/**
 * 부트스트랩 프록시 디스패처 (런타임 함수 동적 호출)
 * 지연 로딩(Lazy Loading): 사용자가 메뉴를 클릭할 때 최신 코드를 로드하므로 단순 트리거(onOpen)의 권한 제약을 완벽히 우회한다.
 */
function dispatch(fnName, args) {
  loadPipelineEngine(false);
  var targetFn = (typeof globalThis !== "undefined" && typeof globalThis[fnName] === "function") ? globalThis[fnName]
               : (typeof this !== "undefined" && typeof this[fnName] === "function") ? this[fnName]
               : null;
  if (!targetFn) {
    try {
      targetFn = eval(fnName);
    } catch (e) {
      targetFn = null;
    }
  }
  if (typeof targetFn === "function") {
    return targetFn.apply(this, args || []);
  } else {
    throw new Error("파이프라인 엔진 내에 함수 [" + fnName + "]가 정의되지 않았습니다.");
  }
}

// ============================================================================
// Google Sheets 커스텀 메뉴 트리거 및 프록시 함수 엔트리포인트
// ============================================================================

/**
 * Google Sheets 액션 중심 커스텀 메뉴 렌더링
 * [단순 트리거 호환]: 네트워크(UrlFetchApp)나 민감 권한 호출 없이 순수 UI 메뉴만 즉시 생성하므로,
 * 문서 열림(onOpen) 시 권한 에러 없이 12대 정식 메뉴가 즉시 표시된다.
 */
function renderPipelineMenu() {
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
 * 구글 시트 문서 열림 시 메뉴 자동 등록 (단순 트리거)
 */
function onOpen() {
  renderPipelineMenu();
}

// 액션 메뉴 디스패치 프록시 함수들 (사용자 클릭 시 지연 로드 및 실행)
function initCampaignWorkspace() { dispatch("initCampaignWorkspace"); }
function runConfigureCampaignSettings() { dispatch("runConfigureCampaignSettings"); }
function guardAndRunIdeaToPlan() { dispatch("guardAndRunIdeaToPlan"); }
function guardAndRunInitialContent() { dispatch("guardAndRunInitialContent"); }
function promptAndRunJudgeEvaluation() { dispatch("promptAndRunJudgeEvaluation"); }
function promptAndRunFeedbackSummary() { dispatch("promptAndRunFeedbackSummary"); }
function promptAndRunReviseAssets() { dispatch("promptAndRunReviseAssets"); }
function openCustomerVocForm() { dispatch("openCustomerVocForm"); }
function setCustomPersonasPrompt() { dispatch("setCustomPersonasPrompt"); }
function promptForGeminiApiKey() { dispatch("promptForGeminiApiKey"); }

/**
 * GitHub 퍼블릭 저장소 최신 엔진 코드 즉시 강제 갱신
 */
function forceSyncEngine() {
  var ui = SpreadsheetApp.getUi();
  try {
    loadPipelineEngine(true);
    renderPipelineMenu();
    ui.alert(
      "엔진 동기화 완료",
      "GitHub 퍼블릭 저장소의 최신 버전 파이프라인 엔진 코드가 성공적으로 갱신되었습니다.\n상단 메뉴를 클릭하여 작업을 시작할 수 있습니다.",
      ui.ButtonSet.OK
    );
  } catch (err) {
    ui.alert(
      "동기화 실패",
      "엔진 동기화 중 오류가 발생했습니다: " + err.toString(),
      ui.ButtonSet.OK
    );
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
    DriveApp.getRootFolder();
    DocumentApp.create("dummy");
    FormApp.create("dummy");
    UrlFetchApp.fetch("https://raw.githubusercontent.com");
    PropertiesService.getUserProperties();
    CacheService.getScriptCache();
  }
}
