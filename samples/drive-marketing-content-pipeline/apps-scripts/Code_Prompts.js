/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 3] 프롬프트 구글 독스 관리 및 스마트 캐싱 엔진 (Prompt Management & Cache Engine)
 */

/**
 * 캠페인 루트의 prompts/ 폴더 내에 6대 프롬프트 구글 독스를 자동 시딩한다.
 * GitHub 퍼블릭 저장소(GitHub Raw)에서 최신 프롬프트 마크다운 파일을 실시간 인출하여 생성하며,
 * 마케터가 이미 수정한 구글 독스가 존재할 경우 기존 내용을 안전하게 보존한다.
 *
 * @param {GoogleAppsScript.Drive.Folder} promptsFolder - prompts 폴더 객체
 */
function seedDefaultPrompts(promptsFolder) {
  if (!promptsFolder) {
    return;
  }

  var rawBase = (CONFIG && CONFIG.GITHUB_RAW_BASE) || "https://raw.githubusercontent.com/jiangjun-forge/google-cloud-0-to-1/main/samples/drive-marketing-content-pipeline";
  var promptKeys = Object.keys(CONFIG.DEFAULT_PROMPTS || {});

  for (var i = 0; i < promptKeys.length; i++) {
    var key = promptKeys[i];
    var def = CONFIG.DEFAULT_PROMPTS[key];
    var files = promptsFolder.getFilesByName(def.title);
    if (!files.hasNext()) {
      var initialContent = "";

      // 1. GitHub 퍼블릭 저장소의 prompts/{key}.md 파일 실시간 인출
      try {
        var fetchUrl = rawBase + "/prompts/" + key + ".md";
        var resp = UrlFetchApp.fetch(fetchUrl, { muteHttpExceptions: true });
        if (resp.getResponseCode() === 200) {
          initialContent = resp.getContentText();
          Logger.log("GitHub Raw로부터 최신 프롬프트 인출 성공: " + key + ".md");
        }
      } catch (fetchErr) {
        Logger.log("GitHub Raw 프롬프트 인출 실패 (로컬 폴백 사용): " + fetchErr.toString());
      }

      // 2. 네트워크 지연 또는 비정상 응답 시 내장 기본값으로 안전 폴백
      if (!initialContent) {
        initialContent =
          "# " + def.title + "\n\n" +
          "> " + def.description + "\n\n" +
          "---\n\n" +
          def.systemInstruction + "\n";
      }

      saveGoogleDoc(promptsFolder, def.title, initialContent);
      Logger.log("프롬프트 구글 독스 자동 시딩 완료: " + def.title);
    }
  }
}

/**
 * 프롬프트 구글 독스 문서를 읽어 시스템 지침 텍스트를 반환한다.
 * 구글 독스의 수정 시각(Last-Modified)을 감지하여 변경이 없을 때에는
 * CacheService로부터 0.01초 만에 즉시 반환하는 스마트 캐싱을 수행한다.
 *
 * @param {string} promptKey - CONFIG.DEFAULT_PROMPTS 키 (예: "02_content_generation")
 * @return {string} 시스템 지침 및 프롬프트 템플릿 텍스트
 */
function getPromptTemplate(promptKey) {
  var def = (CONFIG.DEFAULT_PROMPTS && CONFIG.DEFAULT_PROMPTS[promptKey]) ? CONFIG.DEFAULT_PROMPTS[promptKey] : null;
  var fallbackText = def ? def.systemInstruction : "";

  try {
    var campaignFolder = getCampaignFolder();
    var promptsFolderName = (CONFIG && CONFIG.PROMPTS_FOLDER_NAME) || "prompts";
    var pFolders = campaignFolder.getFoldersByName(promptsFolderName);
    if (!pFolders.hasNext()) {
      return fallbackText;
    }
    var promptsFolder = pFolders.next();
    var targetTitle = def ? def.title : promptKey;
    var files = promptsFolder.getFilesByName(targetTitle);
    if (!files.hasNext()) {
      return fallbackText;
    }

    var file = files.next();
    var fileId = file.getId();
    var lastModified = file.getLastUpdated().getTime();

    // CacheService 기반 수정 시간 대조 스마트 캐싱
    var cache = CacheService.getScriptCache();
    var cacheKey = "prompt_" + promptKey;
    var cacheTimeKey = "prompt_time_" + promptKey;

    var cachedTime = cache.get(cacheTimeKey);
    var cachedContent = cache.get(cacheKey);

    if (cachedContent && cachedTime && String(lastModified) === cachedTime) {
      return cachedContent;
    }

    // 문서가 새로 수정되었거나 캐시 미스 시 구글 독스 본문 로드
    var docContent = readGoogleDoc(promptsFolder, targetTitle);
    if (docContent && docContent.trim().length > 10) {
      // 마케터 안내용 주석 및 머리말(# 제목) 정제
      var cleanedContent = docContent.replace(/^#\s+[^\n]+\n+/, "").replace(/^>\s+[^\n]+\n+/, "").replace(/^---\n+/, "").trim();
      if (!cleanedContent) {
        cleanedContent = docContent.trim();
      }

      // 6시간(21,600초) 캐시 보관
      try {
        cache.put(cacheKey, cleanedContent, 21600);
        cache.put(cacheTimeKey, String(lastModified), 21600);
      } catch (cacheErr) {
        Logger.log("프롬프트 캐시 저장 경고: " + cacheErr);
      }
      return cleanedContent;
    }
  } catch (err) {
    Logger.log("프롬프트 구글 독스 로드 예외, 기본값 사용: " + err);
  }

  return fallbackText;
}

/**
 * 프롬프트 템플릿 내 플레이스홀더({{KEY}})를 변수 매핑 값으로 안전하게 치환한다.
 *
 * @param {string} template - 프롬프트 템플릿
 * @param {Object} variables - { KEY: value, ... } 치환 맵
 * @return {string} 치환 완료된 프롬프트
 */
function renderPromptTemplate(template, variables) {
  if (!template) {
    return "";
  }
  if (!variables) {
    return template;
  }

  var rendered = template;
  var keys = Object.keys(variables);
  for (var i = 0; i < keys.length; i++) {
    var k = keys[i];
    var val = variables[k] || "";
    var regex = new RegExp("\\{\\{" + k + "\\}\\}", "g");
    rendered = rendered.replace(regex, val);
  }
  return rendered;
}
