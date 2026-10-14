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
    try {
      var ui = SpreadsheetApp.getUi();
      ui.alert(
        "작업 진행 중 안내",
        "현재 동일하거나 다른 파이프라인 작업이 이미 백그라운드에서 진행 중입니다.\n\n" +
        "중복 실행으로 인한 데이터 덮어쓰기를 방지하기 위해 새 요청을 차단했습니다.\n" +
        "이전 작업이 완료된 후 다시 시도해 주십시오.",
        ui.ButtonSet.OK
      );
    } catch (uiErr) {
      Logger.log("Lock 경고 알림 표시 불가: " + uiErr);
    }
    return null;
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

function getCampaignFolder() {
  try {
    var sheetId = SpreadsheetApp.getActiveSpreadsheet().getId();
    var sheetFile = DriveApp.getFileById(sheetId);
    var parents = sheetFile.getParents();
    while (parents.hasNext()) {
      var parent = parents.next();
      var parentName = parent.getName();
      if (parentName.indexOf("cp-") === 0) {
        return parent;
      }
    }
  } catch (e) {
    Logger.log("부모 캠페인 폴더 감지 중 예외: " + e);
  }
  return getFolderByPath([CONFIG.CAMPAIGN_CODE]);
}

function getCampaignCode() {
  try {
    var folder = getCampaignFolder();
    var folderName = folder.getName();
    if (folderName.indexOf("cp-") === 0) {
      return folderName;
    }
  } catch (e) {
    Logger.log("캠페인 코드 도출 중 예외: " + e);
  }
  return CONFIG.CAMPAIGN_CODE;
}

function getCampaignSubFolder(subPathParts) {
  var currentFolder = getCampaignFolder();
  for (var i = 0; i < subPathParts.length; i++) {
    var name = subPathParts[i];
    var subFolders = currentFolder.getFoldersByName(name);
    if (subFolders.hasNext()) {
      currentFolder = subFolders.next();
    } else {
      currentFolder = currentFolder.createFolder(name);
    }
  }
  return currentFolder;
}

function readTextFile(folder, fileName) {
  var files = folder.getFilesByName(fileName);
  if (files.hasNext()) {
    var file = files.next();
    return file.getBlob().getDataAsString("UTF-8");
  }
  return null;
}

function saveTextFile(folder, fileName, content) {
  var files = folder.getFilesByName(fileName);
  if (files.hasNext()) {
    var existingFile = files.next();
    existingFile.setContent(content);
    return existingFile;
  } else {
    return folder.createFile(fileName, content, MimeType.PLAIN_TEXT);
  }
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
 * 리비전 폴더(rv-xx) 내 필수 에셋 5종(카피 독스, 이미지 3종, 숏폼 비디오)의 완성 상태를 정밀 진단한다.
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

  var files = folder.getFiles();
  while (files.hasNext()) {
    var f = files.next();
    var name = f.getName();
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

  if (result.hasBanner) result.existingFiles.push("배너 이미지(" + bannerName + ")");
  else result.missingFiles.push("배너 이미지(" + bannerName + ")");

  if (result.hasPoster) result.existingFiles.push("포스터 이미지(" + posterName + ")");
  else result.missingFiles.push("포스터 이미지(" + posterName + ")");

  if (result.hasSns) result.existingFiles.push("SNS 피드 이미지(" + snsName + ")");
  else result.missingFiles.push("SNS 피드 이미지(" + snsName + ")");

  if (result.hasVideo) result.existingFiles.push("숏폼 비디오(" + videoName + ")");
  else result.missingFiles.push("숏폼 비디오(" + videoName + ")");

  result.isComplete = (result.hasDoc && result.hasBanner && result.hasPoster && result.hasSns && result.hasVideo);
  result.isEmpty = (result.existingFiles.length === 0);

  return result;
}

/**
 * 대표 비주얼 이미지 3종 비율 세트 및 Veo 비디오 생성 (16:9 배너, 9:16 포스터, 1:1 SNS 피드, 숏폼 비디오)
 * options.onlyMissing = true 설정 시 이미 존재하는 파일은 건너뛰고 누락된 파일만 생성한다.
 */
function generateAndSaveVisualAssets(targetFolder, prefix, visualBrief, options) {
  var opts = options || {};
  var onlyMissing = (opts.onlyMissing === true);

  var brief = visualBrief || "A stylish 20s Korean female model enjoying cozy autumn commuter lifestyle with lightweight ANC headphones, warm golden hour sunlight, modern Seoul street";
  var items = [
    { name: prefix + "_banner_16x9.png", ratio: "16:9", prompt: brief + " Wide horizontal display banner (16:9)." },
    { name: prefix + "_poster_9x16.png", ratio: "9:16", prompt: brief + " Vertical mobile commercial poster (9:16)." },
    { name: prefix + "_sns_1x1.png", ratio: "1:1", prompt: brief + " Square social media feed photo (1:1)." }
  ];

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

  if (onlyMissing && targetFolder.getFilesByName(videoFileName).hasNext()) {
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
          Logger.log("Gemini Veo 비디오 생성 응답 없음 또는 무료 티어 제한 (campaign_content 문서의 숏폼 영상 콘티 참조).");
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
    videoStatus: videoStatus
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
    "  - Google AI Studio 유료 결제 계정 연동 API Key 환경에서는 Gemini Veo 모델이 위 콘티를 바탕으로 실제 비디오(" + videoFileName + ")를 자동 생성하여 폴더에 함께 저장합니다.\n" +
    "  - 무료 API Key 환경이거나 현장 촬영본이 있는 경우, 마케터 또는 고객이 직접 촬영한 실제 모바일 숏폼 영상(" + videoFileName + ")을 해당 폴더에 업로드하여 활용할 수 있습니다.\n";

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
 * 25인 한국인 마스터 AI 페르소나 데이터셋 기반 실시간 다면 평가 피드백 생성
 * (열린 피드백 원칙 및 페르소나별 복수 의견 포인트 50~80+개 도출, 128d 임베딩 t-SNE 지형도 연동)
 */
function generateLivePersonaFeedbacks(campaignFolder, feedbackFolder, prevRvNameOpt) {
  try {
    var fbFolderName = feedbackFolder.getName();
    var prevRvName = prevRvNameOpt;
    if (!prevRvName) {
      var rNum = parseInt(fbFolderName.replace("fb-", ""), 10) || 1;
      var pNum = Math.max(0, rNum - 1);
      prevRvName = "rv-" + (pNum < 10 ? "0" + pNum : pNum);
    }

    var assetContent = "";
    var prevFolder = getCampaignSubFolder(["output", prevRvName]);
    var assetFileContent = readGoogleDoc(prevFolder, CONFIG.CONTENT_DOC_NAME || "campaign_content") || readGoogleDoc(prevFolder, "campaign_asset");
    if (assetFileContent) {
      assetContent = assetFileContent;
    } else {
      var rv00Folder = getCampaignSubFolder(["output", "rv-00"]);
      assetContent = readGoogleDoc(rv00Folder, CONFIG.CONTENT_DOC_NAME || "campaign_content") || readGoogleDoc(rv00Folder, "campaign_asset") || "마케팅 캠페인 공개 콘텐츠 (카피 및 비주얼)";
    }

    var personasText = "";
    personasText = readTextFile(campaignFolder, "ai_personas.json");
    if (!personasText) {
      var inputFolder = getCampaignSubFolder(["input"]);
      personasText = readTextFile(inputFolder, "ai_personas.json");
    }
    // 마케터 파일 삭제 또는 파싱 실패 시 기본 25인 마스터 페르소나로 자동 복구
    if (!personasText || personasText.trim().length < 20) {
      try {
        var masterPersonas = (typeof getMasterPersonas25 === "function") ? getMasterPersonas25() : null;
        if (masterPersonas) {
          personasText = JSON.stringify(masterPersonas, null, 2);
          saveTextFile(campaignFolder, "ai_personas.json", personasText);
          Logger.log("ai_personas.json 누락 감지 -> 25인 기본 마스터 페르소나 자동 복구 완료");
        }
      } catch (recErr) {
        Logger.log("페르소나 자동 복구 예외: " + recErr);
      }
    }

    var specContent = readGoogleDoc(campaignFolder, CONFIG.SPEC_DOC_NAME || "SPEC") || "";
    var hasSpecificSurvey = (specContent.indexOf("설문 문항") !== -1 || specContent.indexOf("피드백 설문") !== -1);
    var openFeedbackGuideline = hasSpecificSurvey
      ? "- 콘텐츠 제작 명세서(SPEC)에 정의된 피드백 설문 항목을 충실히 반영하여 의견을 개진하라.\n"
      : "- 콘텐츠 제작 명세서(SPEC)에 특정 설문 문항이 고정되어 있지 않으므로, '열린 피드백(Open-ended Feedback)' 원칙을 적용한다. 각 페르소나는 자신의 연령, 성별, 직업, 라이프스타일 관점에서 장점 호평, 단점 비판, 가격 저항, 사용성 의문, 구매 전환 장벽 등 다각도의 열린 의견을 자유롭게 개진하라.\n";

    var promptDocTemplate = (typeof getPromptTemplate === "function") ? getPromptTemplate("05_persona_evaluation") : "";
    var systemInstruction = promptDocTemplate || (
      "당신은 엔터프라이즈 마케팅 리서치 및 소비자 심리 분석 전문 AI이다.\n" +
      "소비자는 사내 기획서를 알지 못하며, 시장에 공개된 마케팅 캠페인 콘텐츠(" + prevRvName + " 카피 및 비주얼)만을 보고 반응한다.\n" +
      "제공된 마케팅 콘텐츠(" + prevRvName + ") 산출물을 면밀히 검토하고, 함께 제공된 한국인 25인 가상 페르소나 프로필의 관점에 깊이 빙의하여 피드백을 작성하라.\n\n" +
      "### 핵심 원칙: 열린 피드백 및 복수 의견 포인트(Multi-points) 도출:\n" +
      openFeedbackGuideline +
      "- 페르소나 1명이 1개의 단편적 소감만 남기지 않고, 제품 및 콘텐츠의 다양한 측면(예: 노이즈 캔슬링 호평, 착용감 우려, 출시가 부담 등)에 대해 1인당 2개~4개의 구체적인 세부 의견 포인트(`points` 배열)를 제시해야 한다.\n" +
      "- 25인 평가단 전체로부터 총 50개 이상의 세부 의견 포인트를 도출하여 다면적 여론 지형도를 풍부하게 구성하라.\n\n" +
      "엄격한 출력 형식:\n" +
      "반드시 다음 JSON 배열 형식으로만 순수 JSON을 출력하라. 코드 블록(```json) 없이 유효한 JSON만 반환하라:\n" +
      "[\n" +
      "  {\n" +
      "    \"persona_id\": \"kr_persona_00001\",\n" +
      "    \"name\": \"강민준\",\n" +
      "    \"age\": 24,\n" +
      "    \"gender\": \"남자\",\n" +
      "    \"occupation\": \"대학생\",\n" +
      "    \"category\": \"20대 대학생\",\n" +
      "    \"rating\": 4.2,\n" +
      "    \"open_feedback\": \"열린 피드백 관점에서의 종합 소감 (2~3문장)\",\n" +
      "    \"points\": [\n" +
      "      {\n" +
      "        \"point_id\": \"P01_1\",\n" +
      "        \"text\": \"노이즈 캔슬링 성능은 학습 및 몰입 환경에서 매우 유용할 것으로 기대된다.\",\n" +
      "        \"sentiment\": \"긍정\",\n" +
      "        \"cluster_theme\": \"성능 및 기능\",\n" +
      "        \"rating\": 4.8\n" +
      "      },\n" +
      "      {\n" +
      "        \"point_id\": \"P01_2\",\n" +
      "        \"text\": \"출시 가격이 대학생 기준 다소 부담스러워 얼리버드 혜택 강조가 필수적이다.\",\n" +
      "        \"sentiment\": \"부정\",\n" +
      "        \"cluster_theme\": \"가격 및 구매 혜택\",\n" +
      "        \"rating\": 3.0\n" +
      "      }\n" +
      "    ]\n" +
      "  }\n" +
      "]\n\n" +
      "작성 규칙:\n" +
      "1. 이모지와 중간 점을 일절 쓰지 말고 쉼표(,)를 사용하십시오.\n" +
      "2. 모든 서술은 단호하고 격조 높은 문어체/평서문('-다' 체)으로 작성하십시오.\n" +
      "3. 한글 복합어는 철저하게 띄어 쓰십시오.\n" +
      "4. 반드시 25인의 한국인 프로필 정보를 충실히 반영하여 25개 객체와 총 50개 이상의 세부 포인트를 완성하십시오."
    );

    var userPrompt =
      "[대중에게 공개된 마케팅 캠페인 콘텐츠 (" + prevRvName + ")]\n" +
      assetContent + "\n\n" +
      "[콘텐츠 제작 명세서(SPEC) 발췌]\n" +
      (specContent.substring(0, 1500) || "SPEC 문서 기본 규격") + "\n\n" +
      "[한국인 25인 가상 페르소나 프로필 데이터]\n" +
      (personasText || "25인 한국인 소비자 프로필") + "\n\n" +
      "위 마케팅 콘텐츠(" + prevRvName + ")를 본 25인 평가단의 열린 피드백 및 복수 세부 의견 포인트(총 50~80개)를 JSON 배열로 실시간 도출하라.";

    var rawOutput = callGemini(systemInstruction, userPrompt, CONFIG.MODEL_GENERATOR);
    if (rawOutput) {
      var parsed = safeParseJson(rawOutput, [], true);
      if (Array.isArray(parsed) && parsed.length > 0) {
        // 복수 의견 포인트 평탄화(Flatten)
        var allPoints = [];
        var allTexts = [];
        for (var p = 0; p < parsed.length; p++) {
          var pItem = parsed[p];
          var pPts = pItem.points;
          if (!Array.isArray(pPts) || pPts.length === 0) {
            pPts = [
              {
                point_id: "P" + (p + 1) + "_1",
                text: pItem.open_feedback || pItem.feedback || "전반적인 마케팅 메시지 만족도",
                sentiment: pItem.sentiment || "중립",
                cluster_theme: pItem.cluster_theme || "기능 및 사용성",
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

        // 한국어 특화 text-multilingual-embedding-002 모델을 통한 128차원 MRL 임베딩 취득
        Logger.log("총 " + allPoints.length + "개 세부 의견 포인트 128차원 텍스트 임베딩 일괄 생성 시작 (text-multilingual-embedding-002)");
        var embeddings128d = callGeminiBatchEmbeddings(allTexts, CONFIG.EMBEDDING_DIM || 128);

        // 128차원 고차원 벡터를 2차원 평면 (x, y)으로 정사영 투영
        var coords2D = projectHighDimTo2D(embeddings128d);
        for (var c = 0; c < allPoints.length; c++) {
          if (coords2D[c]) {
            allPoints[c].x = coords2D[c].x;
            allPoints[c].y = coords2D[c].y;
          }
        }

        var formattedPersonas = JSON.stringify(parsed, null, 2);
        saveTextFile(feedbackFolder, "ai_persona_feedbacks.json", formattedPersonas);

        var formattedPoints = JSON.stringify(allPoints, null, 2);
        saveTextFile(feedbackFolder, "feedback_points_128d.json", formattedPoints);

        // 128d 임베딩 투영 좌표 기반 QuickChart 다면 여론 지형도 차트 생성
        renderAndSaveTsneClusterMap(feedbackFolder, allPoints);

        Logger.log("실제 캠페인 기반 25인 페르소나 열린 피드백(" + parsed.length + "명) 및 128d 다중 포인트(" + allPoints.length + "개) 지형도 생성 완료");
        return formattedPersonas;
      }
    }
  } catch (err) {
    Logger.log("AI 가상 페르소나 피드백 실시간 생성 예외: " + err);
  }
  return "";
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
 * QuickChart REST API를 호출하여 세부 의견 포인트(128d 임베딩 기반 2D 투영)
 * 다면 여론 지형도(t-SNE / PCA 클러스터 맵) PNG를 생성하고 드라이브에 저장한다.
 *
 * @param {Folder} feedbackFolder - 차트 이미지가 저장될 구글 드라이브 폴더
 * @param {Array<Object>} pointsList - 2D 좌표와 메타데이터가 결합된 의견 포인트 목록
 * @return {File|null} 생성된 이미지 파일 객체
 */
function renderAndSaveTsneClusterMap(feedbackFolder, pointsList) {
  try {
    if (!pointsList || pointsList.length === 0) {
      return null;
    }

    // 4대 의견 성향별 데이터셋 분기
    var datasets = [
      { label: "호평 및 긍정 반응", data: [], backgroundColor: "rgba(37, 99, 235, 0.75)", borderColor: "#1D4ED8", borderWidth: 1.2, pointRadius: [] },
      { label: "비판 및 개선 제안", data: [], backgroundColor: "rgba(220, 38, 38, 0.75)", borderColor: "#B91C1C", borderWidth: 1.2, pointRadius: [] },
      { label: "가격 및 구매 장벽", data: [], backgroundColor: "rgba(217, 119, 6, 0.75)", borderColor: "#B45309", borderWidth: 1.2, pointRadius: [] },
      { label: "중립 및 기능적 사용성", data: [], backgroundColor: "rgba(5, 150, 105, 0.75)", borderColor: "#047857", borderWidth: 1.2, pointRadius: [] }
    ];

    for (var i = 0; i < pointsList.length; i++) {
      var pt = pointsList[i];
      var sentiment = String(pt.sentiment || "");
      var theme = String(pt.cluster_theme || "");
      var rating = Number(pt.rating) || 3.5;
      var radius = Math.max(5, Math.min(15, rating * 2.5));

      var targetIndex = 3; // 기본: 중립/기능
      if (theme.indexOf("가격") !== -1 || theme.indexOf("비용") !== -1 || theme.indexOf("혜택") !== -1 || theme.indexOf("가성비") !== -1) {
        targetIndex = 2; // 가격
      } else if (sentiment.indexOf("부정") !== -1 || sentiment.indexOf("비판") !== -1 || rating < 3.0) {
        targetIndex = 1; // 비판/개선
      } else if (sentiment.indexOf("긍정") !== -1 || rating >= 4.0) {
        targetIndex = 0; // 호평
      }

      datasets[targetIndex].data.push({
        x: pt.x !== undefined ? pt.x : Number((Math.sin(i * 1.5) * 2.8).toFixed(2)),
        y: pt.y !== undefined ? pt.y : Number((Math.cos(i * 2.1) * 2.8).toFixed(2))
      });
      datasets[targetIndex].pointRadius.push(radius);
    }

    var chartConfig = {
      type: "bubble",
      data: {
        datasets: datasets
      },
      options: {
        title: {
          display: true,
          text: "25인 페르소나 열린 피드백 여론 지형도 (총 " + pointsList.length + "개 포인트, 128d 임베딩)",
          fontSize: 16,
          fontColor: "#1E293B"
        },
        legend: {
          position: "bottom",
          labels: { fontSize: 11, fontColor: "#475569" }
        },
        scales: {
          xAxes: [{
            scaleLabel: { display: true, labelString: "차원 1: 의미론적 유사도 (t-SNE / PCA 1축)", fontColor: "#64748B" },
            gridLines: { color: "#F1F5F9" },
            ticks: { min: -4.5, max: 4.5, fontColor: "#94A3B8" }
          }],
          yAxes: [{
            scaleLabel: { display: true, labelString: "차원 2: 평가 감정 및 태도 (t-SNE / PCA 2축)", fontColor: "#64748B" },
            gridLines: { color: "#F1F5F9" },
            ticks: { min: -4.0, max: 4.0, fontColor: "#94A3B8" }
          }]
        }
      }
    };

    var quickChartUrl = "https://quickchart.io/chart";
    var payload = {
      chart: chartConfig,
      width: 780,
      height: 480,
      backgroundColor: "#FFFFFF"
    };

    var fetchOptions = {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    var response = UrlFetchApp.fetch(quickChartUrl, fetchOptions);
    if (response.getResponseCode() === 200) {
      var imageBlob = response.getBlob().setName("feedback_clusters_map.png");
      var existing = feedbackFolder.getFilesByName("feedback_clusters_map.png");
      if (existing.hasNext()) {
        existing.next().setTrashed(true);
      }
      var savedFile = feedbackFolder.createFile(imageBlob);
      Logger.log("128d 임베딩 기반 다면 여론 지형도 저장 완료: " + savedFile.getName() + " (포인트 " + pointsList.length + "개)");
      return savedFile;
    } else {
      Logger.log("QuickChart API 오류 (" + response.getResponseCode() + "): " + response.getContentText());
    }
  } catch (err) {
    Logger.log("다면 여론 지형도 차트 생성 예외: " + err);
  }
  return null;
}

/**
 * 구글 시트 실시간 실행 대시보드 헬퍼
 */
function getDashboardSheet() {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    if (!ss) return null;
    var sheet = ss.getSheetByName("실행 대시보드");
    if (!sheet) {
      sheet = ss.getSheets()[0];
      sheet.setName("실행 대시보드");
    }
    return sheet;
  } catch (e) {
    Logger.log("대시보드 시트 획득 예외: " + e);
    return null;
  }
}

/**
 * 초 단위 소요 시간을 사람이 읽기 편한 문자열(예: '24초', '1분 15초')로 포맷팅한다.
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
 * 소모된 토큰 수를 사람이 읽기 편한 문자열(예: '2,450 tokens')로 포맷팅한다.
 */
function formatTokenCount(tokens) {
  if (tokens === null || tokens === undefined || tokens === "" || tokens === 0) return "-";
  if (typeof tokens === "string") return tokens;
  var num = parseInt(tokens, 10);
  if (isNaN(num) || num <= 0) return "-";
  return num.toLocaleString() + " tokens";
}

function initDashboardSheet() {
  var sheet = getDashboardSheet();
  if (!sheet) return;

  try {
    var val = sheet.getRange("A2").getValue();
    var lastCol = sheet.getLastColumn();
    if (val === "실행 단계" && lastCol >= 7) return;

    sheet.clear();

    // 상단 타이틀 배너 (A1:G1)
    sheet.getRange("A1:G1").merge();
    sheet.getRange("A1").setValue("Google Drive 마케팅 콘텐츠 파이프라인 실행 대시보드");
    sheet.getRange("A1")
      .setFontWeight("bold")
      .setFontSize(12)
      .setBackground("#1E293B")
      .setFontColor("#FFFFFF")
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle")
      .setWrap(false);
    sheet.setRowHeight(1, 38);

    // 컬럼 헤더 행 (A2:G2) - 7대 핵심 컬럼
    var headers = [["실행 단계", "진행 상태", "생성된 산출물 바로가기", "완료 시각", "소요 시간", "소모 토큰", "실행 로그 및 상세 내역"]];
    sheet.getRange("A2:G2").setValues(headers);
    sheet.getRange("A2:G2")
      .setFontWeight("bold")
      .setFontSize(10)
      .setBackground("#F1F5F9")
      .setFontColor("#334155")
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle")
      .setWrap(false);
    // 숫자 컬럼(소요 시간, 소모 토큰) 헤더 우측 정렬
    sheet.getRange("E2:F2").setHorizontalAlignment("right");
    sheet.setRowHeight(2, 28);

    // 컬럼 너비 설정 (사용자 지정: 150, 100, 300, 150, 100, 150, 450)
    sheet.setColumnWidth(1, 150);
    sheet.setColumnWidth(2, 100);
    sheet.setColumnWidth(3, 300);
    sheet.setColumnWidth(4, 150);
    sheet.setColumnWidth(5, 100);
    sheet.setColumnWidth(6, 150); // 소요 시간 다음 칼럼: 소모 토큰 (150px)
    sheet.setColumnWidth(7, 450); // 실행 로그 및 상세 내역 (450px)

    sheet.getRange("A2:G2").setBorder(true, true, true, true, true, true, "#CBD5E1", SpreadsheetApp.BorderStyle.SOLID);
  } catch (e) {
    Logger.log("대시보드 시트 초기화 예외: " + e);
  }
}

/**
 * 실행 대시보드 시트에 결과를 항상 맨 아래에 새 행으로 누적 추가(Append-only)한다.
 *
 * @param {string} stepId - 실행 단계 식별자
 * @param {string} stepName - 작업 명칭
 * @param {string} status - 진행 상태 ('완료', '진행 중' 등)
 * @param {string} linkUrl - 산출물 링크 URL
 * @param {string} linkText - 링크 표시 텍스트
 * @param {number|string} [durationSec] - 소요 시간 (초 단위 숫자 또는 문자열)
 * @param {number|string} [tokensOrLog] - 소모 토큰 수 또는 로그 (오버로딩 방어)
 * @param {string} [logDetailOpt] - 실행 로그 및 상세 내역
 */
function recordStepResultToSheet(stepId, stepName, status, linkUrl, linkText, durationSec, tokensOrLog, logDetailOpt) {
  var sheet = getDashboardSheet();
  if (!sheet) return;

  try {
    initDashboardSheet();

    var lastRow = sheet.getLastRow();
    // 항상 맨 아래에 새 행으로 누적 추가 (헤더가 2행이므로 최소 3행부터 시작)
    var targetRow = Math.max(3, lastRow + 1);

    sheet.setRowHeight(targetRow, 28);

    var tokenVal = "-";
    var detailText = "";
    if (logDetailOpt !== undefined) {
      tokenVal = formatTokenCount(tokensOrLog);
      detailText = logDetailOpt || (status === "완료" ? "정상 처리 완료" : "");
    } else {
      tokenVal = "-";
      detailText = tokensOrLog || (status === "완료" ? "정상 처리 완료" : "");
    }

    // 1열: 실행 단계 (150)
    sheet.getRange(targetRow, 1)
      .setValue(stepId)
      .setFontWeight("bold")
      .setFontSize(10)
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle");

    // 2열: 진행 상태 (100)
    var statusCell = sheet.getRange(targetRow, 2);
    statusCell.setValue(status)
      .setFontSize(10)
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle");
    if (status === "완료") {
      statusCell.setBackground("#DCFCE7").setFontColor("#15803D").setFontWeight("bold");
    } else if (status === "진행 중") {
      statusCell.setBackground("#FEF9C3").setFontColor("#A16207").setFontWeight("bold");
    }

    // 3열: 생성된 산출물 바로가기 (300)
    var linkCell = sheet.getRange(targetRow, 3);
    linkCell.setFontSize(10).setVerticalAlignment("middle");
    if (linkUrl) {
      var displayText = linkText || stepName;
      linkCell.setFormula('=HYPERLINK("' + linkUrl + '", "' + displayText + '")').setHorizontalAlignment("left");
    } else {
      linkCell.setValue(stepName).setHorizontalAlignment("left");
    }

    // 4열: 완료 시각 (150)
    var nowStr = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd HH:mm:ss");
    sheet.getRange(targetRow, 4)
      .setValue(nowStr)
      .setFontSize(9)
      .setFontColor("#64748B")
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle");

    // 5열: 소요 시간 (100) - 숫자 메트릭 우측 정렬
    var durText = formatDuration(durationSec);
    sheet.getRange(targetRow, 5)
      .setValue(durText)
      .setFontSize(9)
      .setFontColor("#334155")
      .setHorizontalAlignment("right")
      .setVerticalAlignment("middle");

    // 6열: 소모 토큰 (150) - 숫자 메트릭 우측 정렬
    sheet.getRange(targetRow, 6)
      .setValue(tokenVal)
      .setFontSize(9)
      .setFontColor("#334155")
      .setHorizontalAlignment("right")
      .setVerticalAlignment("middle");

    // 7열: 실행 로그 및 상세 내역 (450)
    sheet.getRange(targetRow, 7)
      .setValue(detailText)
      .setFontSize(9)
      .setFontColor("#475569")
      .setHorizontalAlignment("left")
      .setVerticalAlignment("middle");

    // 라인 랩 방지 (CLIP) 및 테두리 설정 (1~7열)
    var rowRange = sheet.getRange(targetRow, 1, 1, 7);
    rowRange.setWrap(false);
    rowRange.setBorder(true, true, true, true, true, true, "#E2E8F0", SpreadsheetApp.BorderStyle.SOLID);
  } catch (e) {
    Logger.log("대시보드 시트 결과 기록 예외: " + e);
  }
}

/**
 * 사용자 대기 피로도 경감을 위한 실시간 토스트 알림 헬퍼
 */
function showProcessingToast(stepTitle, estimatedTimeSec) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    if (ss) {
      var secText = estimatedTimeSec ? " (예상 소요 시간: 약 " + estimatedTimeSec + "초)" : "";
      ss.toast("Apps Script 엔진이 작업을 시작했습니다" + secText + ". 잠시만 기다려 주십시오...", stepTitle || "파이프라인 실행 중", estimatedTimeSec || 30);
    }
  } catch (e) {
    Logger.log("토스트 알림 표시 예외: " + e);
  }
}

/**
 * 드라이브 내 최신 피드백 회차(fb-xx) 번호 자동 탐지
 */
function detectLatestFeedbackRoundNum() {
  var maxRound = 1;
  try {
    var inputFolder = getCampaignSubFolder(["input"]);
    var subFolders = inputFolder.getFolders();
    while (subFolders.hasNext()) {
      var folder = subFolders.next();
      var name = folder.getName();
      var match = /^fb-(\d+)$/i.exec(name);
      if (match) {
        var num = parseInt(match[1], 10);
        if (num > maxRound) {
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
 */
function detectLatestRevisionRoundNum() {
  var maxRound = 0;
  try {
    var outputFolder = getCampaignSubFolder(["output"]);
    var subFolders = outputFolder.getFolders();
    while (subFolders.hasNext()) {
      var folder = subFolders.next();
      var name = folder.getName();
      var match = /^rv-(\d+)$/i.exec(name);
      if (match) {
        var num = parseInt(match[1], 10);
        if (num > maxRound) {
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
 * 마케터가 클릭 한 번으로 결과물(구글 독스, 구글 드라이브 폴더)을 즉시 열 수 있는 결과 안내 모달을 띄운다.
 */
function showResultModal(title, message, btnText, btnUrl) {
  var ui = SpreadsheetApp.getUi();
  if (!btnUrl) {
    ui.alert(title, message, ui.ButtonSet.OK);
    return;
  }

  var htmlContent =
    "<div style='font-family:sans-serif; padding:18px; line-height:1.6;'>" +
    "<h3 style='margin:0 0 10px 0; color:#1a73e8; font-size:16px;'>" + title + "</h3>" +
    "<p style='color:#3c4043; font-size:13px; margin:0 0 16px 0; white-space:pre-line;'>" + message + "</p>" +
    "<div style='margin-top:16px;'>" +
    "<a href='" + btnUrl + "' target='_blank' style='display:inline-block; padding:10px 20px; background:#1a73e8; color:#ffffff; text-decoration:none; border-radius:4px; font-weight:bold; font-size:13px;'>" + btnText + "</a>" +
    "</div>" +
    "<p style='color:#70757a; font-size:11px; margin-top:14px; word-break:break-all;'>URL: " + btnUrl + "</p>" +
    "</div>";

  try {
    var htmlOutput = HtmlService.createHtmlOutput(htmlContent)
      .setWidth(480)
      .setHeight(210);
    ui.showModalDialog(htmlOutput, title);
  } catch (err) {
    ui.alert(title, message + "\n\n" + btnText + ": " + btnUrl, ui.ButtonSet.OK);
  }
}
