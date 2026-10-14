/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline - Ultra-light Bootstrap Loader
 *
 * [초경량 자동 갱신 부트스트랩 로더]
 * 사용자가 Google Sheets Apps Script 편집기에 단 1회만 붙여넣으면,
 * GitHub 퍼블릭 저장소의 최신 bundle_apps_script.js를 실시간으로 자동 동기화하여 구동합니다.
 * 이후 기능 개선이나 버그 패치가 발생해도 사용자는 Apps Script 코드를 다시 수정할 필요가 없습니다.
 */

var BOOTSTRAP_CONFIG = {
  BUNDLE_URL: "https://raw.githubusercontent.com/jiangjun-forge/google-cloud-0-to-1/main/samples/drive-marketing-content-pipeline/bundle_apps_script.js",
  CACHE_PREFIX: "PIPELINE_CHUNK_",
  CACHE_TTL_SEC: 21600 // 6시간 캐싱 (Google Apps Script 할당량 및 GitHub API 호출 보호)
};

/**
 * GitHub 퍼블릭 저장소로부터 최신 번들 엔진 코드를 가져와 글로벌 스코프에 동적 로드한다.
 *
 * @param {boolean} forceRefresh - 캐시를 무시하고 최신 코드를 강제 다운로드할지 여부
 */
function loadPipelineEngine(forceRefresh) {
  var cache = CacheService.getScriptCache();
  var fullCode = "";

  if (!forceRefresh) {
    var chunkCountStr = cache.get(BOOTSTRAP_CONFIG.CACHE_PREFIX + "COUNT");
    if (chunkCountStr) {
      var count = parseInt(chunkCountStr, 10);
      var parts = [];
      for (var i = 0; i < count; i++) {
        var part = cache.get(BOOTSTRAP_CONFIG.CACHE_PREFIX + i);
        if (part) {
          parts.push(part);
        }
      }
      if (parts.length === count) {
        fullCode = parts.join("");
      }
    }
  }

  if (!fullCode) {
    var resp = UrlFetchApp.fetch(BOOTSTRAP_CONFIG.BUNDLE_URL, { muteHttpExceptions: true });
    if (resp.getResponseCode() === 200) {
      fullCode = resp.getContentText();
      // CacheService 단일 값 100KB 제한을 방어하기 위한 90KB 청크 분할 캐싱
      var chunkSize = 90000;
      var chunks = [];
      for (var j = 0; j < fullCode.length; j += chunkSize) {
        chunks.push(fullCode.substring(j, j + chunkSize));
      }
      for (var k = 0; k < chunks.length; k++) {
        cache.put(BOOTSTRAP_CONFIG.CACHE_PREFIX + k, chunks[k], BOOTSTRAP_CONFIG.CACHE_TTL_SEC);
      }
      cache.put(BOOTSTRAP_CONFIG.CACHE_PREFIX + "COUNT", "" + chunks.length, BOOTSTRAP_CONFIG.CACHE_TTL_SEC);
    } else {
      throw new Error("GitHub 퍼블릭 저장소로부터 엔진 코드를 가져오지 못했습니다. (HTTP 응답 코드: " + resp.getResponseCode() + ")");
    }
  }

  // 간접 eval(Indirect eval)을 실행하여 전역(Global) 스코프에 모든 함수와 전역 객체를 등록
  (1, eval)(fullCode);
}

/**
 * 부트스트랩 프록시 디스패처 (런타임 함수 동적 호출)
 */
function dispatch(fnName, args) {
  loadPipelineEngine(false);
  if (typeof this[fnName] === "function") {
    return this[fnName].apply(this, args || []);
  } else {
    throw new Error("파이프라인 엔진 내에 함수 [" + fnName + "]가 정의되지 않았습니다.");
  }
}

// ============================================================================
// Google Sheets 커스텀 메뉴 트리거 및 프록시 함수 엔트리포인트
// ============================================================================

/**
 * 구글 시트 문서 열림 시 GitHub 최신 엔진을 로드하여 메뉴 등록
 */
function onOpen() {
  try {
    loadPipelineEngine(false);
    if (typeof this.onOpen === "function") {
      this.onOpen();
    }
  } catch (err) {
    var ui = SpreadsheetApp.getUi();
    ui.createMenu("[마케팅 콘텐츠 파이프라인]")
      .addItem("[엔진 최신 버전 동기화 및 복구]", "forceSyncEngine")
      .addToUi();
  }
}

// 액션 메뉴 디스패치 프록시 함수들
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
  loadPipelineEngine(true);
  SpreadsheetApp.getUi().alert(
    "엔진 동기화 완료",
    "GitHub 퍼블릭 저장소의 최신 버전 파이프라인 엔진 코드가 성공적으로 갱신되었습니다.",
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}
