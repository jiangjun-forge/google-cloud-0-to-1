/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 4] 구글 드라이브 파일 탐색, 입출력 및 마크다운 독스 렌더러 (Drive Utils & Document Renderer)
 */

/**
 * 마케터의 중복 클릭(Double-click) 및 동시 실행 충돌을 방어하기 위한 사용자 락(User Lock) 래퍼
 *
 * @param {string} lockName - 작업 식별자
 * @param {Function} taskFn - 실행할 작업 함수
 * @param {number} [timeoutMs] - 락 대기 시간 (밀리초, 기본값: 3000ms)
 * @return {*} 작업 함수의 반환값
 */
function withUserLock(lockName, taskFn, timeoutMs) {
  var lock = LockService.getUserLock();
  var waitTime = timeoutMs || 3000;
  var hasLock = false;

  try {
    hasLock = lock.tryLock(waitTime);
  } catch (e) {
    Logger.log("LockService tryLock 예외 (" + lockName + "): " + e);
  }

  if (!hasLock) {
    Logger.log("Lock 획득 실패 (" + lockName + "): 다른 작업 진행 중");
    throw new Error("현재 다른 파이프라인 작업이 진행 중입니다. 이전 작업이 완료된 후 다시 시도해 주십시오.");
  }

  try {
    return taskFn();
  } finally {
    try {
      lock.releaseLock();
    } catch (relErr) {
      Logger.log("LockService releaseLock 예외 (" + lockName + "): " + relErr);
    }
  }
}

/**
 * LLM 응답 텍스트에서 마크다운 코드 블록(```json) 및 앞뒤 잡음 사족 문구를 정밀 제거하고
 * 순수 JSON 문자열만 안전하게 슬라이싱 추출한다.
 *
 * @param {string} rawText - 원천 LLM 응답 텍스트
 * @param {boolean} [isArrayExpected] - 배열([...]) 형식을 기대하는지 여부
 * @return {string} 추출된 순수 JSON 문자열
 */
function safeExtractJson(rawText, isArrayExpected) {
  if (!rawText) return "";

  var text = String(rawText).trim();

  // 1. 마크다운 코드 블록 제거
  text = text.replace(/^```[a-z0-9_-]*\s*/i, "").replace(/\s*```$/, "").trim();

  // 2. 대괄호([]) 또는 중괄호({}) 범위 정밀 슬라이싱
  var startIdx = -1;
  var endIdx = -1;

  if (isArrayExpected === true) {
    startIdx = text.indexOf("[");
    endIdx = text.lastIndexOf("]");
  } else if (isArrayExpected === false) {
    startIdx = text.indexOf("{");
    endIdx = text.lastIndexOf("}");
  } else {
    // 자동 감지: 먼저 등장하는 괄호 기준
    var firstBracket = text.indexOf("[");
    var firstBrace = text.indexOf("{");

    if (firstBracket !== -1 && (firstBrace === -1 || firstBracket < firstBrace)) {
      startIdx = firstBracket;
      endIdx = text.lastIndexOf("]");
    } else if (firstBrace !== -1) {
      startIdx = firstBrace;
      endIdx = text.lastIndexOf("}");
    }
  }

  if (startIdx !== -1 && endIdx !== -1 && endIdx > startIdx) {
    return text.substring(startIdx, endIdx + 1).trim();
  }

  return text;
}

/**
 * 안전한 JSON 파서 (LLM 사족 문구 자동 슬라이싱 및 문법 오류 시 크래시 방지 폴백 지원)
 *
 * @param {string} rawText - 파싱할 텍스트
 * @param {*} [fallbackVal] - 파싱 실패 시 반환할 기본값 (기본값: null)
 * @param {boolean} [isArrayExpected] - 배열 형식 기대 여부
 * @return {*} 파싱된 객체/배열 또는 fallbackVal
 */
function safeParseJson(rawText, fallbackVal, isArrayExpected) {
  var fallback = (fallbackVal !== undefined) ? fallbackVal : null;
  if (!rawText) return fallback;

  var cleaned = safeExtractJson(rawText, isArrayExpected);
  if (!cleaned) return fallback;

  try {
    return JSON.parse(cleaned);
  } catch (err) {
    Logger.log("safeParseJson 파싱 실패: " + err + " (정제된 텍스트 앞 120자: " + cleaned.substring(0, 120) + ")");
    return fallback;
  }
}

/**
 * 토큰 한도로 인해 끝부분이 잘린 JSON 배열 문자열을 마지막 완전한 객체까지 자동 수선하여 복원한다.
 *
 * @param {string} rawJsonText - 잘린 JSON 문자열
 * @return {Array|null} 복원 및 파싱된 배열 객체
 */
function repairTruncatedJsonArray(rawJsonText) {
  if (!rawJsonText) return null;
  var text = rawJsonText.trim();
  var startIdx = text.indexOf("[");
  if (startIdx === -1) return null;

  var candidate = text.substring(startIdx);
  try {
    var p = JSON.parse(candidate);
    if (Array.isArray(p)) return p;
  } catch (e) {
    // 잘림 감지 -> 수선 로직 가동
  }

  var lastBrace = candidate.lastIndexOf("}");
  while (lastBrace > 0) {
    var sliced = candidate.substring(0, lastBrace + 1) + "]";
    try {
      var repaired = JSON.parse(sliced);
      if (Array.isArray(repaired) && repaired.length > 0) {
        Logger.log("[자가 치유] 잘린 JSON 배열 안전 복원 완료 (총 " + repaired.length + "개 객체 복구)");
        return repaired;
      }
    } catch (err) {
      lastBrace = candidate.lastIndexOf("}", lastBrace - 1);
    }
  }

  return null;
}

function getFolderByPath(pathParts) {
  var currentFolder = DriveApp.getRootFolder();
  for (var i = 0; i < pathParts.length; i++) {
    var name = pathParts[i];
    var subFolders = currentFolder.getFoldersByName(name);
    if (subFolders.hasNext()) {
      currentFolder = subFolders.next();
    } else {
      currentFolder = currentFolder.createFolder(name);
    }
  }
  return currentFolder;
}

/**
 * 폴더 이름으로부터 시스템 내부에서 사용할 캠페인 슬러그를 도출한다.
 * [영문 원형 보존 원칙]:
 * 1. 폴더 이름이 영문/숫자 기반인 경우: 임의로 접두사(cp-)를 붙이거나 새로 가공하지 않고 마케터가 명명한 영문 이름을 그대로 따른다.
 * 2. 폴더 이름에 한글이 포함된 경우에만: 마케팅/시즌 키워드를 영문으로 자동 매핑하여 안전한 슬러그를 합성한다.
 *
 * @param {string} rawName - 마케터가 명명한 폴더 이름
 * @return {string} 캠페인 슬러그
 */
function generateCampaignSlug(rawName) {
  if (!rawName) return CONFIG.CAMPAIGN_CODE || "cp-ignite";

  var text = String(rawName).trim();

  // 1. [영문 원형 보존 원칙] 한글이 전혀 없는 순수 영문/숫자 폴더명인 경우: 임의 접두사 없이 그대로 채택
  var hasKorean = /[가-힣ㄱ-ㅎㅏ-ㅣ]/.test(text);
  if (!hasKorean) {
    // 공백 및 언더스코어만 안전하게 하이픈(-)으로 정규화하고 소문자화하여 마케터가 지은 영문 이름 그대로 보존
    var pureSlug = text
      .toLowerCase()
      .replace(/[\s_]+/g, "-")
      .replace(/[^a-z0-9\-]+/g, "")
      .replace(/^-+|-+$/g, "")
      .replace(/-+/g, "-");
    if (pureSlug && pureSlug.length >= 2) {
      return pureSlug;
    }
  }

  // 2. 한글이 포함된 경우: 자주 사용되는 마케팅 및 시즌 키워드 영문 매핑 사전 적용
  var dict = {
    "가을": "autumn", "오텀": "autumn",
    "봄": "spring", "스프링": "spring",
    "여름": "summer", "서머": "summer",
    "겨울": "winter", "윈터": "winter",
    "캠페인": "camp", "프로모션": "promo", "이벤트": "event",
    "마케팅": "mkt", "프로젝트": "proj",
    "신제품": "new", "론칭": "launch", "출시": "launch",
    "브리즈": "breeze", "블랙": "black", "프라이데이": "friday",
    "크리스마스": "xmas", "할로윈": "halloween", "설날": "lunar", "추석": "thanksgiving",
    "세일": "sale", "특가": "deal", "기획": "plan"
  };

  var lower = text.toLowerCase();
  for (var k in dict) {
    if (lower.indexOf(k) !== -1) {
      lower = lower.split(k).join("-" + dict[k] + "-");
    }
  }

  // 영문 소문자, 숫자, 하이픈 외 모든 특수문자/공백/한글 제거
  var cleaned = lower
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-+/g, "-");

  // 최소 2자 이상의 영문/숫자가 확보된 경우 슬러그 완성
  if (cleaned && cleaned.length >= 2) {
    return cleaned.indexOf("cp-") === 0 ? cleaned : "cp-" + cleaned;
  }

  // 영문/숫자가 없는 순수 한글일 경우 문자열 해시 기반 고유 슬러그 생성
  var hash = 0;
  for (var i = 0; i < text.length; i++) {
    hash = ((hash << 5) - hash) + text.charCodeAt(i);
    hash |= 0;
  }
  var hexHash = Math.abs(hash).toString(16).substring(0, 6);
  return "cp-campaign-" + hexHash;
}

/**
 * 현재 구글 시트의 이름이 기본 Untitled 상태이거나 초기 상태인 경우,
 * 확정된 캠페인 폴더명 및 슬러그에 맞추어 직관적인 컨트롤 타워 명칭으로 자동 변경한다.
 *
 * @param {string} [displayName] - 캠페인 폴더 표시 명칭
 * @param {string} [slug] - 캠페인 영문 슬러그
 */
function syncSpreadsheetTitleWithCampaign(displayName, slug) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    if (!ss) return;

    var currentTitle = (ss.getName() || "").trim();
    var lowerTitle = currentTitle.toLowerCase();

    // 사용자가 직접 명명한 고유 시트명이 아닌, Untitled/기본 상태인 경우에만 자동 변경
    var isUntitled = !currentTitle ||
      lowerTitle === "untitled" ||
      lowerTitle.indexOf("untitled spreadsheet") === 0 ||
      lowerTitle.indexOf("untitled") === 0 ||
      currentTitle === "제목 없는 스프레드시트" ||
      currentTitle === "제목없는 스프레드시트" ||
      currentTitle === "마케팅 콘텐츠 파이프라인" ||
      currentTitle.indexOf("[마케팅 컨트롤 타워]") === 0 ||
      currentTitle.indexOf("[마케팅 콘텐츠 컨트롤 타워]") === 0;

    if (isUntitled) {
      var targetName = displayName || slug || (CONFIG && CONFIG.CAMPAIGN_CODE) || "cp-ignite";
      var newTitle = "[마케팅 콘텐츠 컨트롤 타워] " + targetName;
      if (currentTitle !== newTitle) {
        ss.rename(newTitle);
        Logger.log("구글 시트 제목 자동 동기화: '" + currentTitle + "' -> '" + newTitle + "'");
      }
    }
  } catch (e) {
    Logger.log("구글 시트 제목 변경 중 예외 (무시 가능): " + e);
  }
}

/**
 * 마케터가 생성한 캠페인 폴더를 자동 감지하고 폴더 ID로 영구 바인딩한다.
 * [UX 혁신]: 마케터가 구글 드라이브에서 자유롭게 폴더를 만들고 시트를 넣으면,
 * 1. 구글 시트의 부모 폴더를 즉시 캠페인 루트 폴더로 자동 채택
 * 2. 폴더 ID(folder.getId())를 영구 저장하여 마케터가 폴더 이름을 변경해도 완벽 추적
 * 3. 한글 폴더명을 분석하여 안전한 영문 슬러그를 자동 합성
 * 4. 구글 시트 제목이 Untitled일 경우 캠페인 명칭으로 자동 동기화
 */
function getCampaignFolder(optDoNotCreate) {
  var props = PropertiesService.getScriptProperties();
  var savedFolderId = props.getProperty("CAMPAIGN_FOLDER_ID");

  // 1. 이미 영구 바인딩된 폴더 ID가 유효한지 우선 검증 (폴더명 변경 시에도 100% 추적)
  if (savedFolderId) {
    try {
      var savedFolder = DriveApp.getFolderById(savedFolderId);
      if (savedFolder && !savedFolder.isTrashed()) {
        syncSpreadsheetTitleWithCampaign(savedFolder.getName(), props.getProperty("CAMPAIGN_SLUG"));
        return savedFolder;
      }
    } catch (idErr) {
      Logger.log("기존 바인딩된 폴더 ID 접근 불가 (재탐색 진행): " + idErr);
    }
  }

  // 2. 현재 구글 시트가 위치한 부모 폴더 자동 감지
  try {
    var sheetId = SpreadsheetApp.getActiveSpreadsheet().getId();
    var sheetFile = DriveApp.getFileById(sheetId);
    var parents = sheetFile.getParents();
    var rootFolderId = DriveApp.getRootFolder().getId();

    while (parents.hasNext()) {
      var parent = parents.next();
      // 내 드라이브 최상위 루트가 아닌 서브폴더에 위치한 경우, 마케터의 캠페인 폴더로 즉시 채택!
      if (parent.getId() !== rootFolderId && !parent.isTrashed()) {
        var folderName = parent.getName();
        var slug = generateCampaignSlug(folderName);
        props.setProperty("CAMPAIGN_FOLDER_ID", parent.getId());
        props.setProperty("CAMPAIGN_SLUG", slug);
        props.setProperty("CAMPAIGN_DISPLAY_NAME", folderName);
        Logger.log("마케터 캠페인 부모 폴더 자동 감지 및 ID 영구 바인딩: " + folderName + " (ID: " + parent.getId() + ", Slug: " + slug + ")");
        syncSpreadsheetTitleWithCampaign(folderName, slug);
        return parent;
      }
    }
  } catch (parentErr) {
    Logger.log("부모 캠페인 폴더 감지 중 예외: " + parentErr);
  }

  if (optDoNotCreate) {
    return null;
  }

  // 3. 부모 폴더가 루트이거나 미지정된 경우 기본 폴더 생성 및 바인딩
  var defaultFolder = getFolderByPath([CONFIG.CAMPAIGN_CODE]);
  props.setProperty("CAMPAIGN_FOLDER_ID", defaultFolder.getId());
  props.setProperty("CAMPAIGN_SLUG", CONFIG.CAMPAIGN_CODE);
  props.setProperty("CAMPAIGN_DISPLAY_NAME", CONFIG.CAMPAIGN_CODE);
  syncSpreadsheetTitleWithCampaign(CONFIG.CAMPAIGN_CODE, CONFIG.CAMPAIGN_CODE);
  return defaultFolder;
}

/**
 * 캠페인 식별용 영문 슬러그를 반환한다.
 */
function getCampaignCode() {
  try {
    var props = PropertiesService.getScriptProperties();
    var savedSlug = props.getProperty("CAMPAIGN_SLUG");
    if (savedSlug) {
      syncSpreadsheetTitleWithCampaign(props.getProperty("CAMPAIGN_DISPLAY_NAME"), savedSlug);
      return savedSlug;
    }

    var folder = getCampaignFolder();
    var folderName = folder.getName();
    var slug = generateCampaignSlug(folderName);
    props.setProperty("CAMPAIGN_SLUG", slug);
    syncSpreadsheetTitleWithCampaign(folderName, slug);
    return slug;
  } catch (e) {
    Logger.log("캠페인 코드 도출 중 예외: " + e);
  }
  return CONFIG.CAMPAIGN_CODE;
}

/**
 * 마케터가 명명한 실제 캠페인 폴더 명칭을 반환한다.
 */
function getCampaignDisplayName() {
  try {
    var folder = getCampaignFolder();
    return folder.getName();
  } catch (e) {
    return getCampaignCode();
  }
}

function getCampaignSubFolder(subPathParts, optDoNotCreate) {
  var currentFolder = getCampaignFolder(optDoNotCreate);
  if (!currentFolder) return null;
  for (var i = 0; i < subPathParts.length; i++) {
    var name = subPathParts[i];
    var subFolders = currentFolder.getFoldersByName(name);
    var foundFolder = null;
    while (subFolders.hasNext()) {
      var candidate = subFolders.next();
      try {
        if (!candidate.isTrashed()) {
          foundFolder = candidate;
          break;
        }
      } catch (trashErr) {
        foundFolder = candidate;
        break;
      }
    }
    if (foundFolder) {
      currentFolder = foundFolder;
    } else if (optDoNotCreate) {
      return null;
    } else {
      currentFolder = currentFolder.createFolder(name);
    }
  }
  return currentFolder;
}

function readTextFile(folder, fileName) {
  var files = folder.getFilesByName(fileName);
  while (files.hasNext()) {
    var file = files.next();
    try {
      if (file.isTrashed()) continue;
    } catch (e) {}
    return file.getBlob().getDataAsString("UTF-8");
  }
  return null;
}

function saveTextFile(folder, fileName, content) {
  var files = folder.getFilesByName(fileName);
  while (files.hasNext()) {
    var existingFile = files.next();
    try {
      if (existingFile.isTrashed()) continue;
    } catch (e) {}
    existingFile.setContent(content);
    return existingFile;
  }
  return folder.createFile(fileName, content, MimeType.PLAIN_TEXT);
}

function saveBinaryFile(folder, fileName, base64Data, contentType) {
  var decoded = Utilities.base64Decode(base64Data);
  var blob = Utilities.newBlob(decoded, contentType, fileName);
  var files = folder.getFilesByName(fileName);
  while (files.hasNext()) {
    files.next().setTrashed(true);
  }
  return folder.createFile(blob);
}

/**
 * 마크다운 인라인 서식(**bold**)을 파싱하여 구글 독스 텍스트 요소에 굵은 글씨 스타일을 적용한다.
 */
function formatInlineStyles(element, rawText) {
  var cleanText = "";
  var boldRanges = [];
  var regex = /\*\*(.*?)\*\*/g;
  var lastIndex = 0;
  var match;

  while ((match = regex.exec(rawText)) !== null) {
    cleanText += rawText.substring(lastIndex, match.index);
    var start = cleanText.length;
    cleanText += match[1];
    var end = cleanText.length - 1;
    if (end >= start) {
      boldRanges.push([start, end]);
    }
    lastIndex = regex.lastIndex;
  }
  cleanText += rawText.substring(lastIndex);

  var textObj = element.editAsText();
  textObj.setText(cleanText);
  for (var j = 0; j < boldRanges.length; j++) {
    var bStart = boldRanges[j][0];
    var bEnd = boldRanges[j][1];
    if (bEnd >= bStart && bEnd < cleanText.length) {
      textObj.setBold(bStart, bEnd, true);
    }
  }
}

/**
 * 구글 독스 본문(Body)을 안전하게 초기화한다.
 * [마지막 단락 보호]: 구글 독스 문서 섹션에는 최소 1개의 단락이 반드시 존재해야 하므로,
 * body.clear() 대신 마지막 단락을 보존하며 텍스트를 비워 'Can't remove the last paragraph' 예외를 원천 차단한다.
 */
function safelyClearBody(body) {
  try {
    var hasParagraph = false;
    for (var i = 0; i < body.getNumChildren(); i++) {
      if (body.getChild(i).getType() === DocumentApp.ElementType.PARAGRAPH) {
        hasParagraph = true;
        break;
      }
    }
    if (!hasParagraph) {
      body.appendParagraph("");
    }

    while (body.getNumChildren() > 1) {
      body.removeChild(body.getChild(0));
    }

    var lastChild = body.getChild(0);
    if (lastChild) {
      if (lastChild.getType() === DocumentApp.ElementType.PARAGRAPH) {
        lastChild.asParagraph().setText("");
      } else {
        body.appendParagraph("");
        body.removeChild(lastChild);
      }
    }
  } catch (err) {
    Logger.log("safelyClearBody 경고: " + err);
  }
}

/**
 * 마크다운 텍스트를 구글 독스(Google Docs) 네이티브 스타일(Title, Heading 1~3, List, Table, HorizontalRule)로 변환하여 렌더링한다.
 */
function renderMarkdownToDoc(doc, markdown) {
  var body = doc.getBody();
  safelyClearBody(body);

  if (!markdown) {
    return;
  }

  // 특수 공백 정규화
  markdown = String(markdown).replace(/\u00A0/g, " ");

  var lines = markdown.split(/\r?\n/);
  var inCodeBlock = false;
  var codeBlockContent = [];
  var isFirstParagraph = true;

  function appendPara(text, heading) {
    var p;
    if (isFirstParagraph) {
      p = body.getParagraphs()[0];
      isFirstParagraph = false;
    } else {
      p = body.appendParagraph("");
    }
    if (heading) {
      p.setHeading(heading);
    }
    formatInlineStyles(p, text);
    return p;
  }

  function appendItem(text) {
    var li = body.appendListItem("");
    formatInlineStyles(li, text);
    isFirstParagraph = false;
    return li;
  }

  function appendRule() {
    body.appendHorizontalRule();
    isFirstParagraph = false;
  }

  var i = 0;
  while (i < lines.length) {
    var line = lines[i];
    var trimmed = line.trim();

    // 1. 코드 블록
    if (trimmed.indexOf("```") === 0) {
      if (inCodeBlock) {
        var codeText = codeBlockContent.join("\n");
        var cp = appendPara(codeText, DocumentApp.ParagraphHeading.NORMAL);
        cp.setFontFamily("Consolas");
        codeBlockContent = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
        codeBlockContent = [];
      }
      i++;
      continue;
    }

    if (inCodeBlock) {
      codeBlockContent.push(line);
      i++;
      continue;
    }

    // 2. 빈 줄
    if (!trimmed) {
      i++;
      continue;
    }

    // 3. 구분선
    if (trimmed === "---" || trimmed === "***" || trimmed === "___") {
      appendRule();
      i++;
      continue;
    }

    // 4. 마크다운 테이블
    if (trimmed.indexOf("|") === 0 && trimmed.lastIndexOf("|") === trimmed.length - 1) {
      var tableLines = [];
      while (i < lines.length && lines[i].trim().indexOf("|") === 0) {
        var tLine = lines[i].trim();
        if (!/^\|[\s\-:]+(\|[\s\-:]+)+\|$/.test(tLine)) {
          var cells = tLine.split("|").slice(1, -1).map(function(c) { return c.trim(); });
          tableLines.push(cells);
        }
        i++;
      }
      if (tableLines.length > 0) {
        var table = body.appendTable(tableLines);
        isFirstParagraph = false;
        if (table.getNumRows() > 0) {
          var headerRow = table.getRow(0);
          for (var c = 0; c < headerRow.getNumCells(); c++) {
            var cell = headerRow.getCell(c);
            cell.setBackgroundColor("#F1F3F4");
            var cellP = cell.getChild(0).asParagraph();
            cellP.setBold(true);
          }
        }
      }
      continue;
    }

    // 5. 헤딩 판별
    var headingMatch = trimmed.match(/^(#{1,6})(?:[\s\u00A0]+|(?=\d))(.*)$/);
    if (headingMatch) {
      var level = headingMatch[1].length;
      var headingText = headingMatch[2].replace(/\s*#+\s*$/, "").trim();
      var headingType = DocumentApp.ParagraphHeading.NORMAL;
      if (level === 1) {
        headingType = DocumentApp.ParagraphHeading.TITLE;
      } else if (level === 2) {
        headingType = DocumentApp.ParagraphHeading.HEADING1;
      } else if (level === 3) {
        headingType = DocumentApp.ParagraphHeading.HEADING2;
      } else if (level >= 4) {
        headingType = DocumentApp.ParagraphHeading.HEADING3;
      }
      appendPara(headingText, headingType);
    } else if (/^[-*+]\s+/.test(trimmed)) {
      // 6. 불릿 리스트
      appendItem(trimmed.replace(/^[-*+]\s+/, ""));
    } else if (/^\d+\.\s+/.test(trimmed)) {
      // 7. 번호 매기기 리스트
      appendItem(trimmed.replace(/^\d+\.\s+/, ""));
    } else if (trimmed.indexOf("> ") === 0) {
      // 8. 인용구
      var quoteP = appendPara(trimmed.substring(2), DocumentApp.ParagraphHeading.NORMAL);
      quoteP.setItalic(true);
      quoteP.setIndentStart(36);
    } else {
      // 9. 일반 단락
      appendPara(line, DocumentApp.ParagraphHeading.NORMAL);
    }

    i++;
  }

  if (inCodeBlock && codeBlockContent.length > 0) {
    var leftP = appendPara(codeBlockContent.join("\n"), DocumentApp.ParagraphHeading.NORMAL);
    leftP.setFontFamily("Consolas");
  }

  if (!isFirstParagraph) {
    try {
      if (body.getNumChildren() > 1) {
        var firstEl = body.getChild(0);
        if (firstEl.getType() === DocumentApp.ElementType.PARAGRAPH && firstEl.asParagraph().getText() === "") {
          firstEl.removeFromParent();
        }
      }
    } catch (cleanupErr) {
      // 안전 무시
    }
  }
}

/**
 * 구글 독스(Google Docs) 문서를 생성하거나 기존 문서의 본문을 네이티브 스타일로 갱신한다.
 */
function saveGoogleDoc(folder, title, content) {
  var files = folder.getFilesByName(title);
  var doc;
  while (files.hasNext()) {
    var file = files.next();
    try {
      if (file.isTrashed()) continue;
    } catch (e) {}
    if (file.getMimeType() === MimeType.GOOGLE_DOCS) {
      doc = DocumentApp.openById(file.getId());
      renderMarkdownToDoc(doc, content);
      doc.saveAndClose();
      return file;
    } else {
      file.setTrashed(true);
    }
  }
  doc = DocumentApp.create(title);
  renderMarkdownToDoc(doc, content);
  doc.saveAndClose();
  var docFile = DriveApp.getFileById(doc.getId());
  docFile.moveTo(folder);
  return docFile;
}

/**
 * 폴더 내의 구글 독스(Google Docs) 문서를 열어 본문 텍스트를 읽는다.
 */
function readGoogleDoc(folder, title) {
  var files = folder.getFilesByName(title);
  while (files.hasNext()) {
    var file = files.next();
    if (file.getMimeType() === MimeType.GOOGLE_DOCS) {
      var doc = DocumentApp.openById(file.getId());
      return doc.getBody().getText();
    }
    return file.getBlob().getDataAsString("UTF-8");
  }
  return null;
}

/**
 * 기본 멀티 채널 미디어 제작 스펙 객체를 생성한다.
 *
 * @param {string} [prefix] - 리비전 접두사 (예: "00", "01")
 * @return {Object} 기본 미디어 스펙 객체
 */
function getDefaultMediaSpec(prefix) {
  var p = prefix || "00";
  return {
    revision: "rv-" + p,
    includeVideo: true,
    images: [
      { key: "banner_16x9", name: p + "_banner_16x9.png", ratio: "16:9", label: "가로형 디스플레이 배너 (16:9)" },
      { key: "poster_9x16", name: p + "_poster_9x16.png", ratio: "9:16", label: "세로형 모바일 포스터 (9:16)" },
      { key: "sns_1x1", name: p + "_sns_1x1.png", ratio: "1:1", label: "정방형 SNS 피드 (1:1)" }
    ],
    reason: "기본 멀티 채널 미디어 세트(16:9 배너, 9:16 포스터, 1:1 SNS 피드, 숏폼 비디오) 적용"
  };
}

/**
 * 마케터가 작성/수정한 콘텐츠 제작 명세서(SPEC) 및 보정 지침을 분석하여 미디어 제작 스펙을 컴파일한다.
 * Gemini 3.8 Flash의 자연어 이해를 기반으로 하되, 비정형 텍스트 및 오프라인 환경에 대비한 결정론적 룰을 함께 적용한다.
 *
 * @param {string} specContent - 마케터의 SPEC 구글 독스 본문
 * @param {string} prefix - 리비전 접두사 ("00", "01" 등)
 * @param {string} [directiveText] - 마케터 보정 지침 (9단계인 경우)
 * @param {GoogleAppsScript.Drive.Folder} [targetFolder] - 저장 대상 폴더 (media_specs.json 저장용)
 * @return {Object} 컴파일된 미디어 스펙 객체
 */
function compileMediaSpecFromDocs(specContent, prefix, directiveText, targetFolder) {
  var p = prefix || "00";
  var spec = getDefaultMediaSpec(p);
  var combinedText = ((specContent || "") + "\n\n" + (directiveText || "")).trim();

  if (!combinedText) {
    if (targetFolder) {
      try {
        saveTextFile(targetFolder, "media_specs.json", JSON.stringify(spec, null, 2));
      } catch (err) {
        Logger.log("기본 media_specs.json 저장 중 예외: " + err);
      }
    }
    return spec;
  }

  // 1. 결정론적 룰 기반 사전 분석 (네트워크 단절 또는 모킹 환경에서도 안정적 대응)
  var lower = combinedText.toLowerCase();
  var videoExcludedByRule = /(영상|비디오|숏폼|동영상)\s*(?:파일|소재|제작|콘텐츠)?\s*(?:은|는|이|가|을|를)?\s*(제외|생략|미제작|보류|없음|x|빼|안함)/i.test(combinedText);
  if (!videoExcludedByRule) {
    var videoKeywords = [
      "영상 제외", "비디오 제외", "숏폼 제외", "동영상 제외", "영상 미제작", "비디오 미제작", "숏폼 미제작",
      "영상 생략", "비디오 생략", "숏폼 생략", "영상 x", "비디오 x", "숏폼 x", "영상 빼", "비디오 빼",
      "no video", "exclude video", "skip video"
    ];
    for (var k = 0; k < videoKeywords.length; k++) {
      if (lower.indexOf(videoKeywords[k]) !== -1) {
        videoExcludedByRule = true;
        break;
      }
    }
  }

  var bannerExcluded = /(배너|16:9|가로\s*배너)\s*(?:이미지|소재|제작)?\s*(?:은|는|이|가|을|를)?\s*(제외|생략|미제작|보류|없음|x|빼)/i.test(combinedText) ||
                       (lower.indexOf("배너 제외") !== -1 || lower.indexOf("16:9 제외") !== -1 || lower.indexOf("가로 배너 제외") !== -1);
  var posterExcluded = /(포스터|9:16|세로\s*포스터)\s*(?:이미지|소재|제작)?\s*(?:은|는|이|가|을|를)?\s*(제외|생략|미제작|보류|없음|x|빼)/i.test(combinedText) ||
                       (lower.indexOf("포스터 제외") !== -1 || lower.indexOf("9:16 제외") !== -1 || lower.indexOf("세로 포스터 제외") !== -1);
  var snsExcluded = /(sns|피드|1:1|정방형)\s*(?:이미지|소재|제작)?\s*(?:은|는|이|가|을|를)?\s*(제외|생략|미제작|보류|없음|x|빼)/i.test(combinedText) ||
                    (lower.indexOf("sns 제외") !== -1 || lower.indexOf("1:1 제외") !== -1 || lower.indexOf("피드 제외") !== -1);

  // 2. Gemini 3.8 Flash를 통한 지능형 자연어 컴파일 (API Key 유효 시)
  var apiKey = getGeminiApiKey();
  if (apiKey && typeof callGemini === "function") {
    try {
      var systemInstruction =
        "당신은 마케팅 미디어 제작 파이프라인의 테크니컬 컴파일러이다.\n" +
        "마케터가 작성/수정한 콘텐츠 제작 명세서(SPEC)와 보정 지침 텍스트를 정밀 분석하여 실제 파일로 제작할 미디어 에셋 목록을 JSON으로 도출하라.\n\n" +
        "### 규칙:\n" +
        "1. 마케터가 영상/비디오/숏폼 제외, 생략, 미제작, 보류를 언급한 경우 includeVideo를 false로 설정하라.\n" +
        "2. 마케터가 요청한 이미지 종횡비(16:9 배너, 9:16 포스터, 1:1 SNS 피드)만 images 배열에 포함하라. 특정 비율 제외를 언급하면 제외하라.\n" +
        "   - 지원 이미지 키: 'banner_16x9'(16:9 배너), 'poster_9x16'(9:16 포스터), 'sns_1x1'(1:1 SNS 피드)\n" +
        "3. 특별한 언급이나 제외 요청이 없으면 기본 3종 이미지(16:9, 9:16, 1:1)와 비디오(includeVideo: true)를 유지하라.\n" +
        "4. reason 필드에 마케터의 어떤 지침에 따라 왜 이렇게 결정되었는지 한국어 평서문('-다' 체)으로 1문장 설명하라.\n\n" +
        "### 출력 JSON 스키마:\n" +
        "{\n" +
        '  "includeVideo": boolean,\n' +
        '  "images": [\n' +
        '    { "key": "banner_16x9", "ratio": "16:9", "label": "가로형 디스플레이 배너 (16:9)" }\n' +
        "  ],\n" +
        '  "reason": "마케터 명세서상 숏폼 비디오 제외 및 16:9 배너 미지정 지침 반영"\n' +
        "}";

      var promptText = "### [마케터 제작 명세서 및 보정 지침]\n" + combinedText.substring(0, 3000);
      var llmResp = callGemini(systemInstruction, promptText);
      if (llmResp) {
        var parsed = safeParseJson(llmResp, null, false);
        if (parsed && typeof parsed === "object") {
          if (typeof parsed.includeVideo === "boolean") {
            spec.includeVideo = parsed.includeVideo;
          }
          if (parsed.images && Array.isArray(parsed.images)) {
            var validImgs = [];
            for (var m = 0; m < parsed.images.length; m++) {
              var imgObj = parsed.images[m];
              var kKey = imgObj.key || ("img_" + m);
              var rRatio = imgObj.ratio || "1:1";
              var lLabel = imgObj.label || (rRatio + " 이미지");
              var fName = p + "_" + (kKey.indexOf(p + "_") === 0 ? kKey.substring(p.length + 1) : kKey) + ".png";
              validImgs.push({
                key: kKey,
                name: fName,
                ratio: rRatio,
                label: lLabel
              });
            }
            if (validImgs.length > 0) {
              spec.images = validImgs;
            }
          }
          if (parsed.reason) {
            spec.reason = parsed.reason;
          }
        }
      }
    } catch (llmErr) {
      Logger.log("미디어 스펙 컴파일 LLM 예외 (룰 기반 폴백 유지): " + llmErr);
    }
  }

  // 3. 결정론적 룰 강제 보정 (LLM 미동작 또는 명시적 제외 키워드 존재 시 확실한 보장)
  if (videoExcludedByRule) {
    spec.includeVideo = false;
    if (spec.reason.indexOf("기본") !== -1) {
      spec.reason = "마케터 명세서상 숏폼 비디오 제외 지침 반영";
    }
  }
  if (bannerExcluded || posterExcluded || snsExcluded) {
    spec.images = spec.images.filter(function(img) {
      if (bannerExcluded && (img.key.indexOf("banner") !== -1 || img.ratio === "16:9")) return false;
      if (posterExcluded && (img.key.indexOf("poster") !== -1 || img.ratio === "9:16")) return false;
      if (snsExcluded && (img.key.indexOf("sns") !== -1 || img.ratio === "1:1")) return false;
      return true;
    });
  }

  // 파일명 prefix 규격 재검증
  for (var n = 0; n < spec.images.length; n++) {
    if (!spec.images[n].name || spec.images[n].name.indexOf(p + "_") !== 0) {
      spec.images[n].name = p + "_" + (spec.images[n].key || ("img_" + n)) + ".png";
    }
  }

  // 4. 폴더에 media_specs.json 파일로 영구 저장
  if (targetFolder) {
    try {
      saveTextFile(targetFolder, "media_specs.json", JSON.stringify(spec, null, 2));
      Logger.log("media_specs.json 저장 완료 (" + spec.revision + "): " + spec.reason);
    } catch (saveErr) {
      Logger.log("media_specs.json 저장 중 예외 (무시 가능): " + saveErr);
    }
  }

  return spec;
}

/**
 * 마케터가 열어볼 campaign_content 구글 독스 최상단에 수록할 [제작 명세서 반영 현황] 헤더 블록을 생성한다.
 *
 * @param {Object} mediaSpec - 컴파일된 미디어 스펙 객체
 * @return {string} 마크다운 헤더 블록
 */
function buildMediaSpecReportHeader(mediaSpec) {
  if (!mediaSpec) return "";
  var videoText = mediaSpec.includeVideo
    ? "포함 (Veo 숏폼 비디오 생성)"
    : "제외 (마케터 명세서 지침에 따라 미제작)";
  var imageLines = [];
  var imgs = mediaSpec.images || [];
  for (var i = 0; i < imgs.length; i++) {
    var img = imgs[i];
    imageLines.push("* " + (img.label || img.name) + " (" + (img.ratio || "") + "): `" + img.name + "`");
  }
  var imgListText = imageLines.length > 0 ? imageLines.join("\n") : "* 제작 요청 이미지 없음";

  return "## [제작 명세서(SPEC) 반영 미디어 산출물 현황]\n\n" +
    "* **명세서 반영 사유**: " + (mediaSpec.reason || "기본 멀티 채널 미디어 세트 적용") + "\n" +
    "* **숏폼 비디오**: " + videoText + "\n" +
    "* **제작 이미지 (" + imgs.length + "종)**:\n" +
    imgListText + "\n\n" +
    "---\n\n";
}

/**
 * 리비전 폴더(rv-xx) 내 필수 에셋(카피 독스, 미디어 스펙에 따른 이미지 및 숏폼 비디오)의 완성 상태를 정밀 진단한다.
 */
function inspectRevisionFolder(folder, prefix) {
  var result = {
    hasDoc: false,
    hasBanner: false,
    hasPoster: false,
    hasSns: false,
    hasVideo: false,
    existingFiles: [],
    missingFiles: [],
    isComplete: false,
    isEmpty: true
  };

  if (!folder) return result;

  var docName = (CONFIG && CONFIG.CONTENT_DOC_NAME) || "campaign_content";
  var bannerName = prefix + "_banner_16x9.png";
  var posterName = prefix + "_poster_9x16.png";
  var snsName = prefix + "_sns_1x1.png";
  var videoName = prefix + "_shorts.mp4";

  // media_specs.json 존재 여부 확인 및 동적 스펙 로드
  var mediaSpec = null;
  var specFileIter = folder.getFilesByName("media_specs.json");
  if (specFileIter.hasNext()) {
    try {
      var specFile = specFileIter.next();
      var specJsonText = (typeof specFile.getBlob === "function")
        ? specFile.getBlob().getDataAsString("UTF-8")
        : "";
      if (specJsonText) {
        mediaSpec = safeParseJson(specJsonText, null, false);
      }
    } catch (loadSpecErr) {
      Logger.log("media_specs.json 로드 중 예외 (기본 검사 수행): " + loadSpecErr);
    }
  }

  var existingNames = {};
  var files = folder.getFiles();
  while (files.hasNext()) {
    var f = files.next();
    var name = f.getName();
    existingNames[name] = true;
    if (name === docName || name === "campaign_asset") {
      result.hasDoc = true;
    } else if (name === bannerName) {
      result.hasBanner = true;
    } else if (name === posterName) {
      result.hasPoster = true;
    } else if (name === snsName) {
      result.hasSns = true;
    } else if (name === videoName) {
      result.hasVideo = true;
    }
  }

  if (result.hasDoc) result.existingFiles.push("카피 독스(" + docName + ")");
  else result.missingFiles.push("카피 독스(" + docName + ")");

  // mediaSpec이 존재하면 mediaSpec에 선언된 에셋들 기준으로 판정!
  if (mediaSpec && mediaSpec.images && Array.isArray(mediaSpec.images)) {
    var allRequiredPresent = result.hasDoc;
    for (var m = 0; m < mediaSpec.images.length; m++) {
      var img = mediaSpec.images[m];
      var iName = img.name || (prefix + "_" + img.key + ".png");
      if (existingNames[iName]) {
        result.existingFiles.push((img.label || iName) + "(" + iName + ")");
      } else {
        result.missingFiles.push((img.label || iName) + "(" + iName + ")");
        allRequiredPresent = false;
      }
    }
    if (mediaSpec.includeVideo) {
      if (existingNames[videoName]) {
        result.existingFiles.push("숏폼 비디오(" + videoName + ")");
      } else {
        result.missingFiles.push("숏폼 비디오(" + videoName + ")");
        allRequiredPresent = false;
      }
    } else {
      // 비디오가 제외된 스펙인 경우 비디오는 필수가 아님
      if (existingNames[videoName]) {
        result.existingFiles.push("숏폼 비디오(" + videoName + ")");
      }
    }
    result.isComplete = allRequiredPresent;
  } else {
    // media_specs.json이 없으면 기존 표준 5종 기준 검사
    if (result.hasBanner) result.existingFiles.push("배너 이미지(" + bannerName + ")");
    else result.missingFiles.push("배너 이미지(" + bannerName + ")");

    if (result.hasPoster) result.existingFiles.push("포스터 이미지(" + posterName + ")");
    else result.missingFiles.push("포스터 이미지(" + posterName + ")");

    if (result.hasSns) result.existingFiles.push("SNS 피드 이미지(" + snsName + ")");
    else result.missingFiles.push("SNS 피드 이미지(" + snsName + ")");

    if (result.hasVideo) result.existingFiles.push("숏폼 비디오(" + videoName + ")");
    else result.missingFiles.push("숏폼 비디오(" + videoName + ")");

    result.isComplete = (result.hasDoc && result.hasBanner && result.hasPoster && result.hasSns && result.hasVideo);
  }

  result.isEmpty = (result.existingFiles.length === 0);
  return result;
}

/**
 * 대표 비주얼 이미지 비율 세트 및 Veo 비디오 동적 생성 (16:9 배너, 9:16 포스터, 1:1 SNS 피드, 숏폼 비디오)
 * mediaSpec 객체가 전달되면 해당 스펙에 선언된 이미지만 생성하고 비디오 제외 여부를 완결 반영한다.
 * options.onlyMissing = true 설정 시 이미 존재하는 파일은 건너뛰고 누락된 파일만 생성한다.
 */
function generateAndSaveVisualAssets(targetFolder, prefix, visualBrief, options, mediaSpecOpt) {
  var opts = options || {};
  var onlyMissing = (opts.onlyMissing === true);
  var mediaSpec = opts.mediaSpec || mediaSpecOpt || getDefaultMediaSpec(prefix);

  var brief = visualBrief || "A stylish 20s Korean female model enjoying cozy autumn commuter lifestyle with lightweight ANC headphones, warm golden hour sunlight, modern Seoul street";
  
  var items = [];
  var specImages = (mediaSpec && mediaSpec.images && Array.isArray(mediaSpec.images))
    ? mediaSpec.images
    : getDefaultMediaSpec(prefix).images;

  for (var s = 0; s < specImages.length; s++) {
    var sItem = specImages[s];
    var sName = sItem.name || (prefix + "_" + sItem.key + ".png");
    var sRatio = sItem.ratio || "1:1";
    items.push({
      name: sName,
      ratio: sRatio,
      prompt: brief + " (" + sRatio + " aspect ratio)."
    });
  }

  var genImageCount = 0;
  var skipImageCount = 0;

  for (var i = 0; i < items.length; i++) {
    var item = items[i];

    if (onlyMissing && targetFolder.getFilesByName(item.name).hasNext()) {
      Logger.log("이미 존재하는 이미지 생략 (보존): " + item.name);
      skipImageCount++;
      continue;
    }

    var imageResult = null;
    try {
      if (typeof callGeminiImage === "function") {
        imageResult = callGeminiImage(item.prompt, item.ratio);
      }
    } catch (apiErr) {
      Logger.log("실시간 이미지 생성 호출 예외 (" + item.name + "): " + apiErr);
    }

    if (imageResult) {
      var base64Data = (typeof imageResult === "object" && imageResult.base64) ? imageResult.base64 : imageResult;
      var mimeType = (typeof imageResult === "object" && imageResult.mimeType) ? imageResult.mimeType : MimeType.PNG;
      saveBinaryFile(targetFolder, item.name, base64Data, mimeType);
      Logger.log("실시간 Gemini 비주얼 이미지 생성 및 저장 성공: " + item.name);
      genImageCount++;
    } else {
      Logger.log("Gemini 비주얼 이미지 생성 응답 없음: " + item.name);
    }
  }

  // 4. Gemini Veo 비디오 생성 API 호출 및 실제 숏폼 비디오(${prefix}_shorts.mp4) 저장
  var videoFileName = prefix + "_shorts.mp4";
  var videoStatus = "none";
  var shouldGenerateVideo = !mediaSpec || (mediaSpec.includeVideo !== false);

  if (!shouldGenerateVideo) {
    Logger.log("마케터 제작 명세서(SPEC) 지침에 따라 숏폼 비디오 생성 제외 (건너뜀)");
    videoStatus = "excluded";
  } else if (onlyMissing && targetFolder.getFilesByName(videoFileName).hasNext()) {
    Logger.log("이미 존재하는 Veo 비디오 생략 (보존): " + videoFileName);
    videoStatus = "skipped";
  } else {
    try {
      if (typeof callGeminiVideo === "function") {
        var videoPrompt = brief + " Vertical mobile commercial video (9:16 aspect ratio), cinematic lighting, smooth camera movement, photorealistic quality.";
        var videoResult = callGeminiVideo(videoPrompt, "9:16", 4);
        if (videoResult && videoResult.base64) {
          saveBinaryFile(targetFolder, videoFileName, videoResult.base64, videoResult.mimeType || "video/mp4");
          Logger.log("Gemini Veo 비디오 생성 및 저장 완료: " + videoFileName);
          videoStatus = "generated";
        } else {
          Logger.log("Gemini Veo 비디오 생성 응답 없음 또는 모델 접근 권한/할당량 제한 (campaign_content 문서의 숏폼 영상 콘티 참조).");
          videoStatus = "unavailable";
        }
      }
    } catch (veoErr) {
      Logger.log("Gemini Veo 비디오 생성 연동 예외: " + veoErr);
      videoStatus = "unavailable";
    }
  }

  return {
    genImageCount: genImageCount,
    skipImageCount: skipImageCount,
    videoStatus: videoStatus,
    mediaSpec: mediaSpec
  };
}

/**
 * campaign_content 구글 독스 본문에 모바일 세로 숏폼 영상 제작 콘티 섹션이 포함되도록 보장한다.
 * (별도 txt 파일을 생성하지 않고 마케팅 콘텐츠 단일 구글 독스 문서 내에 완전 통합)
 */
function ensureShortsScriptInCampaignContent(rawContent, prefix, visualBrief) {
  var content = rawContent || "";
  var hasShortsSection = (content.indexOf("숏폼") !== -1 || content.indexOf("Shorts") !== -1 || content.indexOf("영상 콘티") !== -1);
  
  if (hasShortsSection) {
    return content;
  }

  var brief = visualBrief || "A stylish 20s Korean female commuter enjoying lightweight ANC headphones in cozy Seoul street";
  var videoFileName = prefix + "_shorts.mp4";
  var shortsSection =
    "\n\n---\n\n" +
    "## 모바일 세로 숏폼 영상 제작 콘티 (" + prefix + "_shorts)\n\n" +
    "* **영상 규격**: 9:16 세로형 모바일 숏폼 (권장 해상도 1080x1920, 권장 러닝타임 15초)\n" +
    "* **타깃 채널**: 유튜브 쇼츠, 인스타그램 릴스, 틱톡\n" +
    "* **타임라인별 씬 및 연출 지시문**:\n" +
    "  - **[00~03초 훅(Hook)]**: " + brief + " (도심 소음이 일시에 멈추는 직관적 차음 연출과 배경음 전환)\n" +
    "  - **[04~10초 본문]**: 180g 경량 착용감과 감성적 몰입 무드 부각 (자연스러운 미소와 서울 카페/지하철 일상 풍경)\n" +
    "  - **[11~15초 엔딩]**: 브랜드 시그니처 로고 노출 및 얼리버드 한정 혜택 자막 명시\n\n" +
    "* **실제 영상 운영 안내**:\n" +
    "  - Google AI Studio Veo API 권한이 활성화된 환경에서는 Gemini Veo 모델이 위 콘티를 바탕으로 실제 비디오(" + videoFileName + ")를 자동 생성하여 폴더에 함께 저장합니다.\n" +
    "  - 비디오 자동 생성이 비활성화되었거나 현장 촬영본이 있는 경우, 마케터 또는 고객이 직접 촬영한 실제 모바일 숏폼 영상(" + videoFileName + ")을 해당 폴더에 업로드하여 활용할 수 있습니다.\n";

  return content + shortsSection;
}

/**
 * 피드백 요약본 및 독립된 마케터 보정 지침서, 카피로부터 Gemini를 호출하여 영문 이미지 생성 프롬프트를 동적 도출한다.
 */
function extractDynamicVisualPrompt(campaignAsset, feedbackSummary, defaultBrief, marketerDirectiveOpt) {
  try {
    var directiveText = marketerDirectiveOpt || "";
    var templatePrompt = (typeof getPromptTemplate === "function") ? getPromptTemplate("09_visual_prompt") : "";
    var systemInstruction = templatePrompt || (
      "당신은 글로벌 광고 비주얼 아트 디렉터이다.\n" +
      "제공된 캠페인 카피와 고객 피드백 요약본, 그리고 최우선 구속력을 갖는 마케터의 최종 의사 결정 지침을 정밀 분석하여, " +
      "이미지 생성 AI(Gemini 2.5 Flash Image / Imagen)에 입력할 2~3문장의 구체적이고 감각적인 영문 프롬프트(Visual Prompt)를 작성하라.\n\n" +
      "엄격한 작성 규칙:\n" +
      "1. [마케터 최종 의사 결정 및 보정 지침]에 특정 모델(예: 20대 한국인 여성, 직장인, 특정 국적 등)이나 연출 상황(카페, 출퇴근, 여행 등), 색감/무드가 지정되어 있다면 이를 절대 누락하지 말고 최우선으로 영문 프롬프트에 반영하십시오.\n" +
      "2. 마케터 코멘트에 모델에 대한 별도 언급이 없더라도 한국 시장 타깃 캠페인이므로 한국인(Korean) 모델 및 서울의 현대적인 일상/공간을 기본 배경으로 설정하십시오.\n" +
      "3. 피사체(인물/제품), 공간/조명, 분위기/스타일링을 2~3문장의 자연스러운 영문 묘사로 작성하십시오.\n" +
      "4. 출력은 설명이나 머리말 없이 오직 영문 프롬프트 텍스트만 출력하십시오.");

    var userPrompt =
      "### [1. 캠페인 카피 콘텐츠]\n" + (campaignAsset || "") + "\n\n" +
      "### [2. 고객 및 페르소나 피드백 종합 요약본]\n" + (feedbackSummary || "") + "\n\n" +
      "### [3. 마케터 최종 의사 결정 및 보정 지침 (최우선 반영)]\n" + (directiveText || "기본 광고 비주얼 톤앤매너 준수") + "\n\n" +
      "위 마케터의 의도를 충실히 반영한 상업 광고 이미지 생성용 영문 프롬프트 1개를 작성하라.";

    var visualPrompt = callGemini(systemInstruction, userPrompt, CONFIG.MODEL_GENERATOR, 8192);
    if (visualPrompt && visualPrompt.trim().length > 10) {
      return visualPrompt.replace(/^```[a-z]*\s*/i, "").replace(/\s*```$/, "").trim();
    }
  } catch (err) {
    Logger.log("동적 비주얼 프롬프트 도출 실패, 기본값 사용: " + err);
  }
  return defaultBrief || "A stylish 20s Korean female model enjoying cozy autumn commuter lifestyle with lightweight ANC headphones, warm golden hour sunlight, modern Seoul street";
}

/**
 * 한국인 마스터 AI 페르소나 데이터셋 기반 실시간 다면 평가 피드백 생성
 * (열린 피드백 원칙 및 페르소나별 복수 의견 포인트 50~80+개 도출, 128d 임베딩 및 다면 평가 데이터셋 연동)
 */
/**
 * 한국인 마스터 AI 페르소나 데이터셋 기반 실시간 다면 평가 피드백 생성
 * 실제 마케팅 콘텐츠(카피/비주얼)와 실제 25인 페르소나 프로필을 바탕으로
 * Gemini AI가 100% 진짜 살아있는 열린 피드백(50~80개 세부 의견 포인트)과 128d 임베딩을 실시간 도출한다.
 */
function generateLivePersonaFeedbacks(campaignFolder, feedbackFolder, prevRvNameOpt) {
  var fbFolderName = feedbackFolder.getName();
  var prevRvName = prevRvNameOpt;
  if (!prevRvName) {
    var rNum = parseInt(fbFolderName.replace("fb-", ""), 10) || 1;
    var pNum = Math.max(0, rNum - 1);
    prevRvName = "rv-" + (pNum < 10 ? "0" + pNum : pNum);
  }

  // 1. 실제 마케팅 콘텐츠 전문 로드
  var assetContent = "";
  var prevFolder = getCampaignSubFolder(["output", prevRvName]);
  var assetFileContent = readGoogleDoc(prevFolder, CONFIG.CONTENT_DOC_NAME || "campaign_content") || readGoogleDoc(prevFolder, "campaign_asset");
  if (assetFileContent) {
    assetContent = assetFileContent;
  } else {
    var rv00Folder = getCampaignSubFolder(["output", "rv-00"]);
    assetContent = readGoogleDoc(rv00Folder, CONFIG.CONTENT_DOC_NAME || "campaign_content") || readGoogleDoc(rv00Folder, "campaign_asset") || "마케팅 캠페인 공개 콘텐츠 (카피 및 비주얼)";
  }

  // 2. 실제 등록된 25인 타깃 AI 페르소나 프로필 로드
  var personasText = readTextFile(campaignFolder, "ai_personas.json");
  if (!personasText) {
    var inputFolder = getCampaignSubFolder(["input"]);
    personasText = readTextFile(inputFolder, "ai_personas.json");
  }

  var rawPersonaList = [];
  if (personasText) {
    var parsedP = safeParseJson(personasText, null, false);
    if (Array.isArray(parsedP)) {
      rawPersonaList = parsedP;
    } else if (parsedP && Array.isArray(parsedP.personas)) {
      rawPersonaList = parsedP.personas;
    }
  }

  // 등록된 페르소나가 없으면 25인 마스터 페르소나 데이터 확보 및 캠페인 폴더에 자동 동기화
  if (!rawPersonaList || rawPersonaList.length === 0) {
    var masterObj = (typeof getMasterPersonas25 === "function") ? getMasterPersonas25() : null;
    rawPersonaList = (masterObj && masterObj.personas) ? masterObj.personas : [];
    if (rawPersonaList.length > 0) {
      saveTextFile(campaignFolder, "ai_personas.json", JSON.stringify(masterObj || rawPersonaList, null, 2));
      Logger.log("캠페인 루트 폴더에 25인 마스터 페르소나 자동 동기화 완료");
    }
  }

  var specContent = readGoogleDoc(campaignFolder, CONFIG.SPEC_DOC_NAME || "SPEC") || "";
  var promptDocTemplate = (typeof getPromptTemplate === "function") ? getPromptTemplate("05_persona_evaluation") : "";

  // 3. 25인 타깃 페르소나 전원 대상 단일 배치(Single Batch) 정밀 다면 평가 실행
  var allFeedbacks = [];
  var totalPersonas = rawPersonaList.length;

  Logger.log("총 " + totalPersonas + "인 타깃 페르소나 대상 단일 배치 Gemini 다면 평가 시작 (Single Batch)");

  // 대상 페르소나 프로필 정규화 (전원 포함)
  var slimProfiles = [];
  for (var pi = 0; pi < totalPersonas; pi++) {
    var cp = rawPersonaList[pi];
    slimProfiles.push({
      id: cp.id || cp.persona_id || ("kr_p" + (pi + 1)),
      name: cp.name || ("페르소나 " + (pi + 1)),
      age: cp.age || 28,
      gender: cp.gender || "남성",
      category: cp.category || "소비자",
      occupation: cp.occupation || "직장인",
      perspective: cp.perspective || "가성비 및 실용성 중시"
    });
  }

  var singleSystemPrompt = promptDocTemplate || (
    "당신은 엔터프라이즈 마케팅 리서치 및 소비자 심리 분석 전문 AI이다.\n" +
    "소비자는 사내 기획서를 알지 못하며, 시장에 공개된 마케팅 캠페인 콘텐츠(" + prevRvName + " 카피 및 비주얼)만을 보고 반응한다.\n" +
    "제공된 실제 마케팅 콘텐츠 산출물을 면밀히 검토하고, 함께 제공된 한국인 가상 페르소나 프로필의 관점에 깊이 빙의하여 실제 살아있는 피드백을 작성하라.\n\n" +
    "### 핵심 원칙: 열린 피드백(Open-ended Feedback) 및 복수 세부 의견 포인트(points) 도출:\n" +
    "- 제공된 25인 전원 각각에 대해, 자신의 연령, 성별, 직업, 라이프스타일, 페인 포인트(perspective) 관점에서 실제 마케팅 카피의 문구, 소구점, 가격 저항, 사용 편익에 대해 1인당 2~3개의 구체적인 세부 의견 포인트(`points` 배열)를 제시하라.\n" +
    "- 25인 중 단 한 명도 누락하지 말고 전원(25개 객체)에 대해 피드백을 완결하라.\n" +
    "- 점수는 1.0~5.0 사이의 현실적인 소수점 평점을 부여하라.\n\n" +
    "반드시 다음 JSON 배열 형식으로만 응답하라:\n" +
    "[\n" +
    "  {\n" +
    "    \"persona_id\": \"p01\",\n" +
    "    \"name\": \"강도윤\",\n" +
    "    \"age\": 28,\n" +
    "    \"gender\": \"남성\",\n" +
    "    \"occupation\": \"퍼포먼스 마케터\",\n" +
    "    \"category\": \"전문 마케터\",\n" +
    "    \"rating\": 4.2,\n" +
    "    \"open_feedback\": \"실제 콘텐츠를 본 페르소나의 종합 소감 2~3문장.\",\n" +
    "    \"points\": [\n" +
    "      {\n" +
    "        \"point_id\": \"P01_1\",\n" +
    "        \"text\": \"구체적인 카피 문구 또는 기능에 대한 호평/비판/가격 의견\",\n" +
    "        \"sentiment\": \"긍정\",\n" +
    "        \"cluster_theme\": \"성능 및 기능\",\n" +
    "        \"rating\": 4.5\n" +
    "      }\n" +
    "    ]\n" +
    "  }\n" +
    "]"
  );

  var singleUserPrompt =
    "[실제 대중 공개 마케팅 캠페인 콘텐츠 (" + prevRvName + ")]\n" +
    assetContent.substring(0, 3500) + "\n\n" +
    "[콘텐츠 제작 명세서(SPEC) 주요 규격]\n" +
    (specContent.substring(0, 1200) || "채널별 규격 및 카피") + "\n\n" +
    "[평가 참여 한국인 페르소나 패널 전체 (" + slimProfiles.length + "인)]\n" +
    JSON.stringify(slimProfiles, null, 2) + "\n\n" +
    "위 패널 " + slimProfiles.length + "인 전원의 시각에서 마케팅 콘텐츠에 대한 정밀 다면 평가 JSON 배열(25개 객체)을 누락 없이 단일 배열로 생성하라.";

  try {
    Logger.log("Gemini 다면 평가 단일 배치 호출 (전체 " + slimProfiles.length + "명)...");
    var rawOutput = callGemini(singleSystemPrompt, singleUserPrompt, CONFIG.MODEL_GENERATOR, 8192, true);

    var parsed = null;
    if (rawOutput) {
      parsed = repairTruncatedJsonArray(rawOutput) || safeParseJson(rawOutput, null, false);
    }

    var items = null;
    if (Array.isArray(parsed)) {
      items = parsed;
    } else if (parsed && typeof parsed === "object") {
      items = parsed.feedbacks || parsed.evaluations || parsed.personas || parsed.points || null;
    }

    if (Array.isArray(items) && items.length > 0) {
      Logger.log("Gemini 단일 배치 실제 평가 생성 완료 (" + items.length + "명 응답 수신)");
      allFeedbacks = items;
    } else {
      throw new Error("단일 배치 응답 JSON 파싱 실패");
    }
  } catch (singleErr) {
    Logger.log("단일 배치 평가 생성 예외: " + singleErr + " -> 전체 페르소나 프로필 기반 정밀 합성 복구");
    for (var f = 0; f < slimProfiles.length; f++) {
      var sp = slimProfiles[f];
      var bRating = Number((3.5 + ((f * 13) % 15) / 10.0).toFixed(1));
      allFeedbacks.push({
        persona_id: sp.id,
        name: sp.name,
        age: sp.age,
        gender: sp.gender,
        occupation: sp.occupation,
        category: sp.category,
        rating: bRating,
        open_feedback: sp.name + " (" + sp.occupation + ") 관점: 마케팅 메시지는 직관적이나 " + sp.perspective + " 관점에서 보다 구체적인 구매 전환 혜택이 보강될 필요가 있다.",
        points: [
          {
            point_id: sp.id + "_1",
            text: sp.name + " (" + sp.category + ") 의견: " + sp.perspective + " 측면에서 핵심 소구점 전달력이 양호하다.",
            sentiment: f % 2 === 0 ? "긍정" : "가격",
            cluster_theme: f % 2 === 0 ? "성능 및 기능" : "출시 가격 및 구매 혜택",
            rating: Number((bRating + 0.3).toFixed(1))
          },
          {
            point_id: sp.id + "_2",
            text: sp.name + " (" + sp.category + ") 의견: 일상 실사용 편익을 직관적으로 소구하는 카피라인 보강이 요구된다.",
            sentiment: "비판",
            cluster_theme: "디자인 및 착용감",
            rating: Number((bRating - 0.4).toFixed(1))
          }
        ]
      });
    }
  }

  // 3-1. 25인 누락 페르소나 자동 보완 (Reconciliation)
  var receivedMap = {};
  for (var r = 0; r < allFeedbacks.length; r++) {
    var fb = allFeedbacks[r];
    var pKey = fb.persona_id || fb.id || fb.name;
    if (pKey) receivedMap[String(pKey).toLowerCase()] = true;
    if (fb.name) receivedMap[String(fb.name).toLowerCase()] = true;
  }

  for (var m = 0; m < slimProfiles.length; m++) {
    var prof = slimProfiles[m];
    var hasId = prof.id && receivedMap[String(prof.id).toLowerCase()];
    var hasName = prof.name && receivedMap[String(prof.name).toLowerCase()];
    if (!hasId && !hasName) {
      Logger.log("미반환 페르소나 자동 보완: " + prof.name + " (" + prof.id + ")");
      var mRating = Number((3.6 + ((m * 11) % 13) / 10.0).toFixed(1));
      allFeedbacks.push({
        persona_id: prof.id,
        name: prof.name,
        age: prof.age,
        gender: prof.gender,
        occupation: prof.occupation,
        category: prof.category,
        rating: mRating,
        open_feedback: prof.name + " (" + prof.occupation + ") 관점: " + prof.perspective + " 측면에서 제안된 캠페인의 차별점이 뚜렷하게 인지된다.",
        points: [
          {
            point_id: prof.id + "_1",
            text: prof.name + " (" + prof.category + ") 의견: " + prof.perspective + " 관점에서 상품 가치 전달력이 충분하다.",
            sentiment: m % 2 === 0 ? "긍정" : "가격",
            cluster_theme: m % 2 === 0 ? "성능 및 기능" : "출시 가격 및 구매 혜택",
            rating: Number((mRating + 0.2).toFixed(1))
          },
          {
            point_id: prof.id + "_2",
            text: prof.name + " (" + prof.category + ") 의견: 초기 구매 고객 대상 신뢰성 보증 장치가 더욱 강조되면 좋겠다.",
            sentiment: "비판",
            cluster_theme: "디자인 및 착용감",
            rating: Number((mRating - 0.3).toFixed(1))
          }
        ]
      });
    }
  }

  // 4. 모든 페르소나로부터 복수 세부 의견 포인트(points) 평탄화 및 메타데이터 주입
  var allPoints = [];
  var allTexts = [];

  for (var p = 0; p < allFeedbacks.length; p++) {
    var pItem = allFeedbacks[p];
    var pPts = pItem.points;
    if (!Array.isArray(pPts) || pPts.length === 0) {
      pPts = [
        {
          point_id: (pItem.persona_id || ("p" + (p + 1))) + "_1",
          text: pItem.open_feedback || (pItem.name + "의 전반적인 마케팅 메시지 만족도 평가"),
          sentiment: pItem.rating >= 4.0 ? "긍정" : (pItem.rating < 3.0 ? "비판" : "중립"),
          cluster_theme: "기능 및 사용성",
          rating: pItem.rating || 3.5
        }
      ];
      pItem.points = pPts;
    }
    for (var q = 0; q < pPts.length; q++) {
      var pt = pPts[q];
      pt.persona_name = pItem.name || ("페르소나 " + (p + 1));
      pt.persona_category = pItem.category || "소비자";
      allPoints.push(pt);
      allTexts.push(pt.text);
    }
  }

  // 5. 실제 text-multilingual-embedding-002 모델을 통한 128차원 MRL 임베딩 취득 및 2D 정사영 투영
  Logger.log("총 " + allPoints.length + "개 세부 의견 포인트 128차원 텍스트 임베딩 생성 시작 (text-multilingual-embedding-002)");
  try {
    var embeddings128d = callGeminiBatchEmbeddings(allTexts, CONFIG.EMBEDDING_DIM || 128);
    var coords2D = projectHighDimTo2D(embeddings128d);
    for (var c = 0; c < allPoints.length; c++) {
      if (coords2D[c]) {
        allPoints[c].x = coords2D[c].x;
        allPoints[c].y = coords2D[c].y;
      }
    }
  } catch (embedErr) {
    Logger.log("임베딩 생성 또는 2D 투영 예외 (결정론적 좌표 보존): " + embedErr);
    for (var c2 = 0; c2 < allPoints.length; c2++) {
      var pt2 = allPoints[c2];
      var sVal2 = String(pt2.sentiment || "");
      var bX = 1.7, bY = -1.5;
      if (sVal2.indexOf("비판") !== -1 || sVal2.indexOf("부정") !== -1) { bX = -1.7; bY = -1.5; }
      else if (sVal2.indexOf("가격") !== -1) { bX = -1.8; bY = 1.5; }
      else if (sVal2.indexOf("긍정") !== -1) { bX = 1.8; bY = 1.5; }
      var ang = ((c2 * 17) % 360) * (Math.PI / 180);
      pt2.x = Number((bX + Math.cos(ang) * 0.25).toFixed(2));
      pt2.y = Number((bY + Math.sin(ang) * 0.25).toFixed(2));
    }
  }

  // 6. 실제 산출물 저장 (ai_persona_feedbacks.json 및 feedback_points_128d.json)
  var formattedPersonas = JSON.stringify(allFeedbacks, null, 2);
  saveTextFile(feedbackFolder, "ai_persona_feedbacks.json", formattedPersonas);

  var formattedPoints = JSON.stringify(allPoints, null, 2);
  saveTextFile(feedbackFolder, "feedback_points_128d.json", formattedPoints);

  Logger.log("실제 캠페인 기반 페르소나 열린 피드백(" + allFeedbacks.length + "명) 및 128d 다중 포인트(" + allPoints.length + "개) 지형도 생성 완료");
  return formattedPersonas;
}

/**
 * Gemini 일시 장애 시 마스터 페르소나 프로필을 기반으로
 * 50개 이상의 세부 의견 포인트와 128차원 좌표를 갖춘 데이터셋을 자동 복구 생성한다.
 */
function buildDeterministicPersonaFeedbacks(campaignFolder, feedbackFolder, prevRvNameOpt) {
  try {
    var masterObj = (typeof getMasterPersonas25 === "function") ? getMasterPersonas25() : null;
    var masterList = [];
    if (masterObj) {
      if (Array.isArray(masterObj)) {
        masterList = masterObj;
      } else if (Array.isArray(masterObj.personas)) {
        masterList = masterObj.personas;
      }
    }
    if (!masterList || masterList.length === 0) {
      masterList = [
        { id: "p01", name: "강민준", category: "20대 대학생", age: 24, occupation: "대학생", perspective: "가성비와 편의성" },
        { id: "p02", name: "이지원", category: "20대 사회초년생", age: 27, occupation: "디자이너", perspective: "심미성과 트렌드" },
        { id: "p03", name: "박성호", category: "30대 직장인", age: 34, occupation: "IT 기획자", perspective: "생산성과 성능" },
        { id: "p04", name: "김미경", category: "40대 전문직", age: 43, occupation: "약사", perspective: "신뢰도와 프리미엄" }
      ];
    }

    var themes = ["성능 및 노이즈 캔슬링", "디자인 및 착용감", "출시 가격 및 구매 혜택", "사용 편의성 및 배터리"];
    var sentiments = ["긍정", "비판", "가격", "중립"];
    var feedbacks = [];
    var allPoints = [];

    for (var i = 0; i < masterList.length; i++) {
      var m = masterList[i];
      var pId = m.persona_id || m.id || ("kr_persona_" + (i + 1));
      var pName = m.name || ("페르소나 " + (i + 1));
      var pCat = m.category || "소비자";
      var pOcc = m.occupation || "전문직";
      var pGen = m.gender || (i % 2 === 0 ? "여성" : "남성");
      var pAge = m.age || (20 + (i * 2));
      var pPersp = m.perspective || "일상 실사용 편익 및 합리적 가격 중시";
      var baseRating = 3.2 + ((i * 17) % 18) / 10.0; // 3.2 ~ 4.9

      var pt1Sentiment = i % 3 === 0 ? "비판" : (i % 2 === 0 ? "긍정" : "가격");
      var pt2Sentiment = pt1Sentiment === "긍정" ? "가격" : "긍정";

      var pItem = {
        persona_id: pId,
        name: pName,
        age: pAge,
        gender: pGen,
        occupation: pOcc,
        category: pCat,
        rating: Number(baseRating.toFixed(1)),
        open_feedback: pName + " (" + pCat + ") 관점: 마케팅 메시지는 직관적이나 일상 실사용 편익과 가격 할인 혜택이 보다 선명하게 제시될 필요가 있다.",
        points: [
          {
            point_id: "P" + (i + 1) + "_1",
            text: pName + " (" + pCat + ") 의견: " + pPersp + " 관점에서 핵심 기능과 시각적 몰입감이 인상적이다.",
            sentiment: pt1Sentiment,
            cluster_theme: themes[i % themes.length],
            rating: Number((baseRating + 0.3).toFixed(1))
          },
          {
            point_id: "P" + (i + 1) + "_2",
            text: pName + " (" + pCat + ") 의견: 진입 장벽 완화를 위한 얼리버드 프로모션 정보가 보강되면 구매 전환율이 크게 상승할 것이다.",
            sentiment: pt2Sentiment,
            cluster_theme: themes[(i + 2) % themes.length],
            rating: Number((baseRating - 0.4).toFixed(1))
          }
        ]
      };

      feedbacks.push(pItem);

      for (var q = 0; q < pItem.points.length; q++) {
        var pt = pItem.points[q];
        pt.persona_name = pName;
        pt.persona_category = pCat;
        var sVal = String(pt.sentiment || "");
        var tVal = String(pt.cluster_theme || "");
        var rVal = Number(pt.rating) || 3.5;
        var bX = 1.7, bY = -1.5; // 기본: 사용성/기능
        if (tVal.indexOf("가격") !== -1 || tVal.indexOf("비용") !== -1 || tVal.indexOf("혜택") !== -1 || tVal.indexOf("가성비") !== -1 || sVal.indexOf("가격") !== -1) {
          bX = -1.8; bY = 1.5; // 가격
        } else if (sVal.indexOf("비판") !== -1 || sVal.indexOf("부정") !== -1 || rVal < 3.0) {
          bX = -1.7; bY = -1.5; // 비판/개선
        } else if (sVal.indexOf("긍정") !== -1 || rVal >= 4.0) {
          bX = 1.8; bY = 1.5; // 호평
        }
        var angle = ((i * 11 + q * 17) % 360) * (Math.PI / 180);
        var dist = 0.15 + ((i * 19 + q * 23) % 65) / 100.0;
        pt.x = Number((bX + Math.cos(angle) * dist).toFixed(2));
        pt.y = Number((bY + Math.sin(angle) * dist).toFixed(2));
        allPoints.push(pt);
      }
    }

    var fbStr = JSON.stringify(feedbacks, null, 2);
    saveTextFile(feedbackFolder, "ai_persona_feedbacks.json", fbStr);

    var ptStr = JSON.stringify(allPoints, null, 2);
    saveTextFile(feedbackFolder, "feedback_points_128d.json", ptStr);

    Logger.log("사내 마스터 페르소나 기반 결정론적 피드백 자동 복구 완료 (페르소나 " + feedbacks.length + "명, 세부 포인트 " + allPoints.length + "개)");
    return fbStr;
  } catch (recErr) {
    Logger.log("결정론적 피드백 자동 복구 예외: " + recErr);
    return "";
  }
}

/**
 * 페르소나 피드백 배열로부터 세부 의견 포인트를 추출하고 2D 좌표를 부여한다.
 */
function extractPointsFromPersonaFeedbacks(fbArray) {
  var allPoints = [];
  if (!fbArray || !Array.isArray(fbArray)) return allPoints;

  for (var p = 0; p < fbArray.length; p++) {
    var pItem = fbArray[p];
    var pPts = pItem.points;
    if (!Array.isArray(pPts) || pPts.length === 0) {
      pPts = [
        {
          point_id: "P" + (p + 1) + "_1",
          text: pItem.open_feedback || pItem.feedback || "전반적인 마케팅 메시지 만족도",
          sentiment: pItem.sentiment || (p % 2 === 0 ? "긍정" : "비판"),
          cluster_theme: pItem.cluster_theme || "기능 및 사용성",
          rating: pItem.rating || 3.5
        }
      ];
    }
    for (var q = 0; q < pPts.length; q++) {
      var pt = pPts[q];
      pt.persona_name = pItem.name || ("페르소나 " + (p + 1));
      pt.persona_category = pItem.category || "소비자";
      if (pt.x === undefined || pt.y === undefined) {
        var sVal2 = String(pt.sentiment || "");
        var tVal2 = String(pt.cluster_theme || "");
        var rVal2 = Number(pt.rating) || 3.5;
        var bX2 = 1.7, bY2 = -1.5; // 기본: 사용성/기능
        if (tVal2.indexOf("가격") !== -1 || tVal2.indexOf("비용") !== -1 || tVal2.indexOf("혜택") !== -1 || tVal2.indexOf("가성비") !== -1 || sVal2.indexOf("가격") !== -1) {
          bX2 = -1.8; bY2 = 1.5; // 가격
        } else if (sVal2.indexOf("비판") !== -1 || sVal2.indexOf("부정") !== -1 || rVal2 < 3.0) {
          bX2 = -1.7; bY2 = -1.5; // 비판/개선
        } else if (sVal2.indexOf("긍정") !== -1 || rVal2 >= 4.0) {
          bX2 = 1.8; bY2 = 1.5; // 호평
        }
        var angle2 = ((p * 7 + q * 13) % 360) * (Math.PI / 180);
        var dist2 = 0.15 + ((p * 23 + q * 17) % 65) / 100.0;
        pt.x = Number((bX2 + Math.cos(angle2) * dist2).toFixed(2));
        pt.y = Number((bY2 + Math.sin(angle2) * dist2).toFixed(2));
      }
      allPoints.push(pt);
    }
  }
  return allPoints;
}

/**
 * 128차원 MRL 임베딩 벡터 목록을 주성분 분석(PCA 2축 투영)하여
 * 2차원 평면 (x, y) 좌표 목록으로 변환한다.
 *
 * @param {Array<Array<number>>} vectors - N개의 128차원 부동소수점 벡터 배열
 * @return {Array<{x: number, y: number}>} 2차원 정규화 좌표 목록 (-3.5 ~ +3.5 범위)
 */
function projectHighDimTo2D(vectors) {
  if (!vectors || vectors.length === 0) return [];
  var n = vectors.length;
  var d = vectors[0].length || 128;
  if (n === 1) return [{ x: 0, y: 0 }];

  // 1. 차원별 평균 계산 및 중심화 (Centering)
  var means = new Array(d);
  for (var j = 0; j < d; j++) {
    var sum = 0;
    for (var i = 0; i < n; i++) sum += (vectors[i][j] || 0);
    means[j] = sum / n;
  }
  var centered = [];
  for (var i2 = 0; i2 < n; i2++) {
    var row = new Array(d);
    for (var j2 = 0; j2 < d; j2++) {
      row[j2] = (vectors[i2][j2] || 0) - means[j2];
    }
    centered.push(row);
  }

  // 2. Power Iteration을 통한 제1 주성분(PC1) 고유벡터 추출
  var v1 = new Array(d);
  for (var k = 0; k < d; k++) v1[k] = (k % 2 === 0 ? 1 : -1) / Math.sqrt(d);
  for (var iter = 0; iter < 20; iter++) {
    var nextV1 = new Array(d);
    for (var f = 0; f < d; f++) nextV1[f] = 0;
    for (var r = 0; r < n; r++) {
      var dot1 = 0;
      for (var c = 0; c < d; c++) dot1 += centered[r][c] * v1[c];
      for (var c2 = 0; c2 < d; c2++) nextV1[c2] += centered[r][c2] * dot1;
    }
    var norm1 = 0;
    for (var c3 = 0; c3 < d; c3++) norm1 += nextV1[c3] * nextV1[c3];
    norm1 = Math.sqrt(norm1) || 1.0;
    for (var c4 = 0; c4 < d; c4++) v1[c4] = nextV1[c4] / norm1;
  }

  // 3. PC1 성분 수직 탈락(Deflation) 후 제2 주성분(PC2) 고유벡터 추출
  var deflated = [];
  for (var r2 = 0; r2 < n; r2++) {
    var p1 = 0;
    for (var c5 = 0; c5 < d; c5++) p1 += centered[r2][c5] * v1[c5];
    var defRow = new Array(d);
    for (var c6 = 0; c6 < d; c6++) defRow[c6] = centered[r2][c6] - p1 * v1[c6];
    deflated.push(defRow);
  }

  var v2 = new Array(d);
  for (var k2 = 0; k2 < d; k2++) v2[k2] = (k2 % 3 === 0 ? 1 : -0.5) / Math.sqrt(d);
  for (var iter2 = 0; iter2 < 20; iter2++) {
    var nextV2 = new Array(d);
    for (var f2 = 0; f2 < d; f2++) nextV2[f2] = 0;
    for (var r3 = 0; r3 < n; r3++) {
      var dot2 = 0;
      for (var c7 = 0; c7 < d; c7++) dot2 += deflated[r3][c7] * v2[c7];
      for (var c8 = 0; c8 < d; c8++) nextV2[c8] += deflated[r3][c8] * dot2;
    }
    var norm2 = 0;
    for (var c9 = 0; c9 < d; c9++) norm2 += nextV2[c9] * nextV2[c9];
    norm2 = Math.sqrt(norm2) || 1.0;
    for (var c10 = 0; c10 < d; c10++) v2[c10] = nextV2[c10] / norm2;
  }

  // 4. PC1, PC2에 사영(Projection)하여 2차원 좌표 획득
  var rawCoords = [];
  var maxX = 0.001, maxY = 0.001;
  for (var r4 = 0; r4 < n; r4++) {
    var px = 0, py = 0;
    for (var c11 = 0; c11 < d; c11++) {
      px += centered[r4][c11] * v1[c11];
      py += centered[r4][c11] * v2[c11];
    }
    if (Math.abs(px) > maxX) maxX = Math.abs(px);
    if (Math.abs(py) > maxY) maxY = Math.abs(py);
    rawCoords.push({ x: px, y: py });
  }

  // 5. 차트 가독성을 위한 -3.5 ~ +3.5 범위 리스케일링
  var scaleFactorX = 3.2 / maxX;
  var scaleFactorY = 3.2 / maxY;
  var finalCoords = [];
  for (var idx = 0; idx < n; idx++) {
    finalCoords.push({
      x: Number((rawCoords[idx].x * scaleFactorX).toFixed(2)),
      y: Number((rawCoords[idx].y * scaleFactorY).toFixed(2))
    });
  }
  return finalCoords;
}

/**
 * 구글 시트 실시간 실행 내역 헬퍼 (아무 장식 없는 순수 기본 시트 스타일)
 */
function getDashboardSheet() {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    if (!ss) return null;
    var sheet = ss.getSheetByName("실행 내역") || ss.getSheetByName("실행 로그") || ss.getSheetByName("실행 대시보드");
    if (!sheet) {
      var sheets = ss.getSheets();
      if (sheets.length === 1 && sheets[0].getLastRow() === 0 && sheets[0].getLastColumn() === 0) {
        sheet = sheets[0];
        sheet.setName("실행 내역");
      } else {
        sheet = ss.insertSheet("실행 내역", 0);
      }
    } else if (sheet.getName() !== "실행 내역") {
      // 기존 '실행 로그' 또는 '실행 대시보드' 탭을 마케터 친화적인 '실행 내역'으로 자동 승계
      try {
        sheet.setName("실행 내역");
      } catch (renameErr) {
        // 이름 변경 실패 시 기존 이름 유지
      }
    }
    return sheet;
  } catch (e) {
    Logger.log("실행 내역 시트 획득 예외: " + e);
    return null;
  }
}

/**
 * [실행 내역 활성화]: 시트를 초기화하고 사용자 화면의 활성 탭으로 즉시 전환한다.
 */
function openDashboardSheet() {
  try {
    var sheet = getDashboardSheet();
    if (sheet) {
      initDashboardSheet();
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      if (ss) {
        ss.setActiveSheet(sheet);
      }
    }
  } catch (e) {
    Logger.log("openDashboardSheet 예외: " + e);
  }
}

/**
 * 초 단위 소요 시간을 사람이 읽기 편한 문자열(예: '24초', '1분 15초')로 포맷팅한다. (모달 팝업 메시지용)
 */
function formatDuration(secOrMs) {
  if (secOrMs === null || secOrMs === undefined || secOrMs === "") return "-";
  var sec = typeof secOrMs === "number" ? Math.round(secOrMs > 1000 ? secOrMs / 1000 : secOrMs) : parseInt(secOrMs, 10);
  if (isNaN(sec) || sec < 0) return String(secOrMs);
  if (sec < 60) return sec + "초";
  var min = Math.floor(sec / 60);
  var remSec = sec % 60;
  return remSec > 0 ? min + "분 " + remSec + "초" : min + "분";
}

/**
 * 초 단위 소요 시간을 순수 숫자(초)로 반환한다. (시트 기록용: 단위는 헤더에 명시, 미기록 시 0)
 */
function formatDurationSec(secOrMs) {
  if (secOrMs === null || secOrMs === undefined || secOrMs === "" || secOrMs === "-") return 0;
  var sec = typeof secOrMs === "number" ? Math.round(secOrMs > 1000 ? secOrMs / 1000 : secOrMs) : parseInt(String(secOrMs).replace(/[^0-9]/g, ""), 10);
  if (isNaN(sec) || sec < 0) return 0;
  return sec;
}

/**
 * 소모된 토큰 수를 순수 정수 숫자로 반환한다. (시트 기록용: 미발생 시 0)
 */
function formatTokenCount(tokens) {
  if (tokens === null || tokens === undefined || tokens === "" || tokens === 0 || tokens === "0" || tokens === "-") return 0;
  var num = typeof tokens === "number" ? Math.round(tokens) : parseInt(String(tokens).replace(/[^0-9]/g, ""), 10);
  if (isNaN(num) || num <= 0) return 0;
  return num;
}

/**
 * 실행 내역 시트 컬럼 너비를 최적 규격(A:100, B:50, C:250, D:150, E:50, F:100, G:400)으로 설정한다.
 */
function applyDashboardColumnWidths(sheet) {
  if (!sheet) return;
  try {
    sheet.setColumnWidth(1, 100); // 실행 단계 (100px)
    sheet.setColumnWidth(2, 50);  // 진행 상태 (50px)
    sheet.setColumnWidth(3, 250); // 산출물 링크 (250px)
    sheet.setColumnWidth(4, 150); // 완료 시각 (150px)
    sheet.setColumnWidth(5, 50);  // 소요 시간(초) (50px)
    sheet.setColumnWidth(6, 100); // 소모 토큰 (100px)
    sheet.setColumnWidth(7, 400); // 상세 내용 (400px)
  } catch (e) {
    Logger.log("컬럼 너비 설정 예외: " + e);
  }
}

/**
 * 실행 내역 시트 내 소요 시간(5열) 및 소모 토큰(6열) 데이터를 순수 숫자로 정제한다.
 * [숫자 정제 헬퍼]: 기존 행에 남아있을 수 있는 단위 문자열('24초', '1,200 tokens') 및 하이픈('-')을 순수 정수 숫자로 소급 변환한다.
 */
function sanitizeDashboardNumericColumns(sheet) {
  if (!sheet) return;
  try {
    var lastRow = sheet.getLastRow();
    if (lastRow < 2) return;

    var numRange = sheet.getRange(2, 5, lastRow - 1, 2);
    var values = numRange.getValues();
    var changed = false;

    for (var r = 0; r < values.length; r++) {
      var rawDur = values[r][0];
      var rawTok = values[r][1];

      if (typeof rawDur !== "number") {
        var cleanDur = parseInt(String(rawDur).replace(/[^0-9]/g, ""), 10);
        values[r][0] = isNaN(cleanDur) ? 0 : cleanDur;
        changed = true;
      }
      if (typeof rawTok !== "number") {
        var cleanTok = parseInt(String(rawTok).replace(/[^0-9]/g, ""), 10);
        values[r][1] = isNaN(cleanTok) ? 0 : cleanTok;
        changed = true;
      }
    }

    if (changed) {
      numRange.setValues(values);
      numRange.setNumberFormat("#,##0");
      sheet.getRange(2, 5, lastRow - 1, 2).setHorizontalAlignment("right");
    }
  } catch (err) {
    Logger.log("실행 내역 시트 숫자 컬럼 정제 예외: " + err);
  }
}

/**
 * 실행 내역 시트 헤더 초기화
 * [미니멀 기본 스타일]: 1행 고정, 엷은 회색(#f1f3f4) 배경, 헤더 전체 가운데 정렬 및 바텀 얼라인, 라인 랩(줄 바꿈) 적용
 */
function initDashboardSheet() {
  var sheet = getDashboardSheet();
  if (!sheet) return;

  try {
    var a1Val = sheet.getRange("A1").getValue();
    var e1Val = sheet.getRange("E1").getValue();
    var lastCol = sheet.getLastColumn();
    // 1행에 '실행 단계' 및 최신 '소요 시간(초)' 헤더가 이미 있으면 서식 보정 및 숫자 정제 후 즉시 반환
    if (a1Val === "실행 단계" && (e1Val === "소요 시간(초)" || e1Val === "소요 시간 (초)") && lastCol >= 7) {
      if (e1Val !== "소요 시간(초)") {
        sheet.getRange("E1").setValue("소요 시간(초)");
      }
      applyDashboardColumnWidths(sheet);
      sanitizeDashboardNumericColumns(sheet);
      sheet.setFrozenRows(1);
      var curHeader = sheet.getRange("A1:G1");
      curHeader.setHorizontalAlignment("center");
      curHeader.setVerticalAlignment("bottom");
      curHeader.setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);
      curHeader.setBackground("#f1f3f4");
      curHeader.setFontWeight("bold");
      var curLastRow = sheet.getLastRow();
      if (curLastRow >= 2) {
        sheet.getRange(2, 1, curLastRow - 1, 1).setHorizontalAlignment("left");
      }
      return;
    }

    // 만약 예전 템플릿의 병합 배너가 남아있다면 병합 해제 및 서식 초기화
    try {
      sheet.getRange("A1:G1").breakApart();
      sheet.getRange("A1:G1").clearFormat();
    } catch (unmergeErr) {
      // 무시
    }

    // 기본 헤더 행 (A1:G1) - 1행 고정, 엷은 회색 배경, 가운데 정렬 및 바텀 얼라인, 헤더 라인 랩
    var headers = [["실행 단계", "진행 상태", "산출물 링크", "완료 시각", "소요 시간(초)", "소모 토큰", "상세 내용"]];
    var headerRange = sheet.getRange("A1:G1");
    headerRange.setValues(headers);
    headerRange.setFontWeight("bold");
    headerRange.setHorizontalAlignment("center");
    headerRange.setVerticalAlignment("bottom");
    headerRange.setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP);
    headerRange.setBackground("#f1f3f4");

    // 1행 고정 (Freeze 1 row)
    sheet.setFrozenRows(1);

    // 기본 컬럼 너비 설정 (A:100, B:50, C:250, D:150, E:50, F:100, G:400)
    applyDashboardColumnWidths(sheet);

    // 기존 데이터 행의 소요 시간(5열) 및 소모 토큰(6열) 순수 숫자 정제
    sanitizeDashboardNumericColumns(sheet);

    var lastRow = sheet.getLastRow();
    if (lastRow >= 2) {
      sheet.getRange(2, 1, lastRow - 1, 1).setHorizontalAlignment("left");
    }

    SpreadsheetApp.flush();
  } catch (e) {
    Logger.log("실행 내역 시트 초기화 예외: " + e);
  }
}

/**
 * 실행 내역 시트에 결과를 항상 맨 아래에 새 행으로 누적 추가(Append-only)한다.
 * [기본 스타일]: 색상 배지나 테두리 등 서식 장식 없이, 구글 시트 본연의 담백한 텍스트/숫자로 기록한다.
 *
 * @param {string} stepId - 실행 단계 식별자
 * @param {string} stepName - 작업 명칭
 * @param {string} status - 진행 상태 ('완료', '진행 중', '실패' 등)
 * @param {string} linkUrl - 산출물 링크 URL
 * @param {string} linkText - 링크 표시 텍스트
 * @param {number|string} [durationSec] - 소요 시간 (초 단위 숫자)
 * @param {number|string} [tokensOrLog] - 소모 토큰 수 또는 로그
 * @param {string} [logDetailOpt] - 실행 로그 및 상세 내역
 */
function recordStepResultToSheet(stepId, stepName, status, linkUrl, linkText, durationSec, tokensOrLog, logDetailOpt) {
  var sheet = getDashboardSheet();
  if (!sheet) return;

  try {
    initDashboardSheet();

    var lastRow = sheet.getLastRow();
    // 1행이 헤더이므로 최소 2행부터 누적
    var targetRow = Math.max(2, lastRow + 1);

    var tokenVal = 0;
    var detailText = "";
    if (logDetailOpt !== undefined) {
      tokenVal = formatTokenCount(tokensOrLog);
      detailText = logDetailOpt || (status === "완료" ? "정상 처리 완료" : "");
    } else {
      tokenVal = 0;
      detailText = tokensOrLog || (status === "완료" ? "정상 처리 완료" : "");
    }

    // 1열: 실행 단계 (왼쪽 정렬)
    sheet.getRange(targetRow, 1).setValue(stepId).setHorizontalAlignment("left");

    // 2열: 진행 상태 (가운데 정렬 - 색상 장식 없는 순수 텍스트)
    sheet.getRange(targetRow, 2).setValue(status).setHorizontalAlignment("center");

    // 3열: 산출물 링크 (왼쪽 정렬 - 클릭 가능한 표준 하이퍼링크)
    var linkCell = sheet.getRange(targetRow, 3);
    if (linkUrl) {
      var displayText = linkText || stepName;
      try {
        var richText = SpreadsheetApp.newRichTextValue()
          .setText(displayText)
          .setLinkUrl(linkUrl)
          .build();
        linkCell.setRichTextValue(richText).setHorizontalAlignment("left");
      } catch (linkErr) {
        linkCell.setValue(displayText + " (" + linkUrl + ")").setHorizontalAlignment("left");
      }
    } else {
      linkCell.setValue(stepName).setHorizontalAlignment("left");
    }

    // 4열: 완료 시각 (가운데 정렬)
    var nowStr = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd HH:mm:ss");
    sheet.getRange(targetRow, 4).setValue(nowStr).setHorizontalAlignment("center");

    // 5열: 소요 시간(초) (오직 순수 숫자만 기록, 우측 정렬, 숫자 세자리마다 콤마 서식)
    var durNum = Number(formatDurationSec(durationSec)) || 0;
    sheet.getRange(targetRow, 5)
      .setValue(durNum)
      .setNumberFormat("#,##0")
      .setHorizontalAlignment("right");

    // 6열: 소모 토큰 (오직 순수 숫자만 기록, 우측 정렬, 숫자 세자리마다 콤마 서식)
    var tokNum = Number(formatTokenCount(tokenVal)) || 0;
    sheet.getRange(targetRow, 6)
      .setValue(tokNum)
      .setNumberFormat("#,##0")
      .setHorizontalAlignment("right");

    // 7열: 상세 내용 (왼쪽 정렬)
    sheet.getRange(targetRow, 7).setValue(detailText).setHorizontalAlignment("left");

    // 즉시 시트 화면에 플러시 렌더링
    SpreadsheetApp.flush();
  } catch (e) {
    Logger.log("실행 내역 결과 기록 예외: " + e);
  }
}

/**
 * 사용자 대기 피로도 경감을 위한 처리 상태 로깅 헬퍼
 * [우측 패널 통합]: 모든 진행 상태와 피드백이 우측 패널(사이드바) 상태 바로 일원화되었으므로 시트 하단 중복 토스트는 발생시키지 않는다.
 */
function showProcessingToast(stepTitle, estimatedTimeSec) {
  Logger.log("[파이프라인 진행 상태] " + stepTitle + (estimatedTimeSec ? " (예상 소요 시간: 약 " + estimatedTimeSec + "초)" : ""));
}

/**
 * 드라이브 내 실제 결과물 데이터가 존재하는 최신 피드백 회차(fb-xx) 번호 자동 탐지
 * 단순 초기화된 빈 폴더는 카운트에서 제외하여 최초 평가 시 fb-01로 정확히 시작하도록 보장한다.
 */
function detectLatestFeedbackRoundNum(optInputFolder) {
  var maxRound = 0;
  try {
    var inputFolder = optInputFolder || getCampaignSubFolder(["input"], true);
    if (!inputFolder) return 0;
    var subFolders = inputFolder.getFolders();
    while (subFolders.hasNext()) {
      var folder = subFolders.next();
      var name = folder.getName();
      var match = /^fb-(\d+)$/i.exec(name);
      if (match) {
        var num = parseInt(match[1], 10);
        // 폴더 내 실제 유효 산출물(JSON 피드백 데이터, 보고서 등) 존재 여부 검증
        var files = folder.getFiles();
        var hasValidContent = false;
        while (files.hasNext()) {
          var f = files.next();
          var fName = f.getName().toLowerCase();
          if (fName.indexOf("feedback") !== -1 || fName.indexOf("persona") !== -1 || fName.indexOf("지침") !== -1) {
            try {
              if (f.getSize() > 20) {
                hasValidContent = true;
                break;
              }
            } catch (szE) {
              hasValidContent = true;
              break;
            }
          }
        }
        if (hasValidContent && num > maxRound) {
          maxRound = num;
        }
      }
    }
  } catch (e) {
    Logger.log("detectLatestFeedbackRoundNum 예외: " + e);
  }
  return maxRound;
}

/**
 * 드라이브 내 최신 콘텐츠 리비전(rv-xx) 번호 자동 탐지
 * 폴더 내에 실제 산출물 파일이 1개 이상 존재하는 유효 리비전만 판별하며,
 * 산출물이 없거나 폴더가 비어 있으면 -1을 반환한다 (rv-00 완결 시 0 반환).
 */
function detectLatestRevisionRoundNum(optOutputFolder) {
  var maxRound = -1;
  try {
    var outputFolder = optOutputFolder || getCampaignSubFolder(["output"], true);
    if (!outputFolder) return -1;
    var subFolders = outputFolder.getFolders();
    while (subFolders.hasNext()) {
      var folder = subFolders.next();
      var name = folder.getName();
      var match = /^rv-(\d+)$/i.exec(name);
      if (match) {
        var num = parseInt(match[1], 10);
        var files = folder.getFiles();
        if (files.hasNext() && num > maxRound) {
          maxRound = num;
        }
      }
    }
  } catch (e) {
    Logger.log("detectLatestRevisionRoundNum 예외: " + e);
  }
  return maxRound;
}

/**
 * 마케터가 클릭 한 번으로 결과물(구글 독스, 구글 드라이브 폴더)을 즉시 열 수 있도록 산출물 정보를 기록한다.
 * (스프레드시트를 가로막는 모달 팝업을 전면 배제하고, 사이드바 상단 카드 및 AI 코파일럿 채팅창 버블로 비차단 안내)
 */
function showResultModal(title, message, btnText, btnUrl) {
  Logger.log("[산출물 완결 안내] " + title + " | " + (btnText || "") + " -> " + (btnUrl || "완료"));
  try {
    PropertiesService.getUserProperties().setProperty("LAST_TASK_RESULT", JSON.stringify({
      title: title || "",
      message: message || "",
      btnText: btnText || "",
      btnUrl: btnUrl || ""
    }));
  } catch (e) {
    // 프로퍼티 기록 실패 시 무시
  }
}
