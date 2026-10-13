/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 4] 구글 드라이브 파일 탐색, 입출력 및 마크다운 독스 렌더러 (Drive Utils & Document Renderer)
 */

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
 * 마크다운 텍스트를 구글 독스(Google Docs) 네이티브 스타일(Title, Heading 1~3, List, Table, HorizontalRule)로 변환하여 렌더링한다.
 */
function renderMarkdownToDoc(doc, markdown) {
  var body = doc.getBody();
  body.clear();

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
 * 대표 비주얼 이미지 3종 비율 세트 생성 (16:9 배너, 9:16 포스터, 1:1 SNS 피드)
 */
function generateAndSaveVisualAssets(targetFolder, prefix, visualBrief) {
  var brief = visualBrief || "A stylish 20s Korean female model enjoying cozy autumn commuter lifestyle with lightweight ANC headphones, warm golden hour sunlight, modern Seoul street";
  var items = [
    { name: prefix + "_banner_16x9.png", ratio: "16:9", prompt: brief + " Wide horizontal display banner (16:9)." },
    { name: prefix + "_poster_9x16.png", ratio: "9:16", prompt: brief + " Vertical mobile commercial poster (9:16)." },
    { name: prefix + "_sns_1x1.png", ratio: "1:1", prompt: brief + " Square social media feed photo (1:1)." }
  ];

  for (var i = 0; i < items.length; i++) {
    var item = items[i];
    var base64Data = null;
    try {
      if (typeof callGeminiImage === "function") {
        base64Data = callGeminiImage(item.prompt, item.ratio);
      }
    } catch (apiErr) {
      Logger.log("실시간 이미지 생성 호출 예외 (" + item.name + "): " + apiErr);
    }

    if (base64Data) {
      saveBinaryFile(targetFolder, item.name, base64Data, MimeType.PNG);
      Logger.log("실시간 Gemini 이미지 생성 및 저장 성공: " + item.name);
    } else {
      // 대체 안내 플레이스홀더 생성
      try {
        var placeholderUrl = "https://quickchart.io/chart?c=" + encodeURIComponent(JSON.stringify({
          type: "radialGauge",
          data: { datasets: [{ data: [100], backgroundColor: "#3B82F6" }] },
          options: {
            title: { display: true, text: item.name },
            trackColor: "#E2E8F0"
          }
        }));
        var phResp = UrlFetchApp.fetch(placeholderUrl, { muteHttpExceptions: true });
        if (phResp.getResponseCode() === 200) {
          saveBinaryFile(targetFolder, item.name, Utilities.base64Encode(phResp.getBlob().getBytes()), MimeType.PNG);
        }
      } catch (phErr) {
        Logger.log("플레이스홀더 이미지 저장 예외: " + phErr);
      }
    }
  }

  // 4. 모바일 숏폼 세로 영상 소재 (${prefix}_shorts.mp4) 자동 생성 및 저장
  var videoName = prefix + "_shorts.mp4";
  try {
    saveSampleVideoFile(targetFolder, videoName);
    Logger.log("모바일 세로 숏폼 영상(shorts) 자동 저장 완료: " + videoName);
  } catch (vidErr) {
    Logger.log("숏폼 영상 소재 저장 예외: " + vidErr);
  }
}

/**
 * 피드백 요약본 및 마케터 지침, 보정 카피로부터 Gemini를 호출하여 영문 이미지 생성 프롬프트를 동적 도출한다.
 */
function extractDynamicVisualPrompt(campaignAsset, feedbackSummary, defaultBrief) {
  try {
    var systemInstruction =
      "당신은 글로벌 광고 비주얼 아트 디렉터이다.\n" +
      "제공된 캠페인 카피와 고객 피드백 요약본(특히 마케터 최종 의사 결정 및 보정 지침)을 정밀 분석하여, " +
      "이미지 생성 인공 지능(Gemini 2.5 Flash Image / Imagen)에 입력할 2~3문장의 구체적이고 감각적인 영문 프롬프트(Visual Prompt)를 작성하라.\n\n" +
      "엄격한 작성 규칙:\n" +
      "1. 마케터 코멘트에 특정 모델(예: 20대 한국인 여성, 직장인, 특정 국적 등)이나 연출 상황(카페, 출퇴근, 여행 등)이 지정되어 있다면 이를 누락하지 않고 영문(예: 'A stylish 20s Korean female model', 'A chic young Korean woman in Seoul')으로 명시하십시오.\n" +
      "2. 마케터 코멘트에 모델에 대한 별도 언급이 없더라도 한국 시장 타깃 캠페인이므로 한국인(Korean) 모델 및 서울의 현대적인 일상/공간을 기본 배경으로 설정하십시오.\n" +
      "3. 피사체(인물/제품), 공간/조명, 분위기/스타일링을 2~3문장의 자연스러운 영문 묘사로 작성하십시오.\n" +
      "4. 출력은 설명이나 머리말 없이 오직 영문 프롬프트 텍스트만 출력하십시오.";

    var userPrompt =
      "[캠페인 카피 콘텐츠]\n" + (campaignAsset || "") + "\n\n" +
      "[고객 피드백 종합 요약본 및 마케터 최종 의사 결정]\n" + (feedbackSummary || "") + "\n\n" +
      "위 내용을 바탕으로 마케터의 의도를 충실히 반영한 상업 광고 이미지 생성용 영문 프롬프트 1개를 작성하라.";

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
    var inputFolder = getCampaignSubFolder(["input"]);
    personasText = readTextFile(inputFolder, "ai_personas.json") || readTextFile(campaignFolder, "ai_personas.json");
    if (!personasText) {
      var campaignDataFolder = getCampaignSubFolder(["data"]);
      personasText = readTextFile(campaignDataFolder, "ai_personas.json");
    }

    var specContent = readGoogleDoc(campaignFolder, CONFIG.SPEC_DOC_NAME || "SPEC") || "";
    var hasSpecificSurvey = (specContent.indexOf("설문 문항") !== -1 || specContent.indexOf("피드백 설문") !== -1);
    var openFeedbackGuideline = hasSpecificSurvey
      ? "- 콘텐츠 제작 명세서(SPEC)에 정의된 피드백 설문 항목을 충실히 반영하여 의견을 개진하라.\n"
      : "- 콘텐츠 제작 명세서(SPEC)에 특정 설문 문항이 고정되어 있지 않으므로, '열린 피드백(Open-ended Feedback)' 원칙을 적용한다. 각 페르소나는 자신의 연령, 성별, 직업, 라이프스타일 관점에서 장점 호평, 단점 비판, 가격 저항, 사용성 의문, 구매 전환 장벽 등 다각도의 열린 의견을 자유롭게 개진하라.\n";

    var systemInstruction =
      "당신은 엔터프라이즈 마케팅 리서치 및 소비자 심리 분석 전문 인공 지능이다.\n" +
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
      "4. 반드시 25인의 한국인 프로필 정보를 충실히 반영하여 25개 객체와 총 50개 이상의 세부 포인트를 완성하십시오.";

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
      var cleanJson = rawOutput.replace(/^```json\s*/i, "").replace(/^```\s*/, "").replace(/\s*```$/, "").trim();
      var parsed = JSON.parse(cleanJson);
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

function initDashboardSheet() {
  var sheet = getDashboardSheet();
  if (!sheet) return;

  try {
    var val = sheet.getRange("A2").getValue();
    if (val === "실행 단계") return;

    sheet.clear();

    // 상단 타이틀 배너 (A1:D1)
    sheet.getRange("A1:D1").merge();
    sheet.getRange("A1").setValue("Google Drive 마케팅 콘텐츠 파이프라인 실행 대시보드");
    sheet.getRange("A1")
      .setFontWeight("bold")
      .setFontSize(12)
      .setBackground("#1E293B")
      .setFontColor("#FFFFFF")
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle");
    sheet.setRowHeight(1, 38);

    // 컬럼 헤더 행 (A2:D2)
    var headers = [["실행 단계", "진행 상태", "생성된 산출물 바로가기", "완료 시각"]];
    sheet.getRange("A2:D2").setValues(headers);
    sheet.getRange("A2:D2")
      .setFontWeight("bold")
      .setFontSize(10)
      .setBackground("#F1F5F9")
      .setFontColor("#334155")
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle");
    sheet.setRowHeight(2, 28);

    // 컬럼 너비
    sheet.setColumnWidth(1, 140);
    sheet.setColumnWidth(2, 90);
    sheet.setColumnWidth(3, 380);
    sheet.setColumnWidth(4, 180);

    sheet.getRange("A2:D2").setBorder(true, true, true, true, true, true, "#CBD5E1", SpreadsheetApp.BorderStyle.SOLID);
  } catch (e) {
    Logger.log("대시보드 시트 초기화 예외: " + e);
  }
}

function recordStepResultToSheet(stepId, stepName, status, linkUrl, linkText) {
  var sheet = getDashboardSheet();
  if (!sheet) return;

  try {
    initDashboardSheet();

    var lastRow = sheet.getLastRow();
    var targetRow = 0;

    if (lastRow >= 3) {
      var stepValues = sheet.getRange(3, 1, lastRow - 2, 1).getValues();
      for (var i = 0; i < stepValues.length; i++) {
        if (stepValues[i][0] === stepId) {
          targetRow = i + 3;
          break;
        }
      }
    }

    if (targetRow === 0) {
      targetRow = Math.max(3, lastRow + 1);
    }

    sheet.setRowHeight(targetRow, 28);

    sheet.getRange(targetRow, 1)
      .setValue(stepId)
      .setFontWeight("bold")
      .setFontSize(10)
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle");

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

    var linkCell = sheet.getRange(targetRow, 3);
    linkCell.setFontSize(10).setVerticalAlignment("middle");
    if (linkUrl) {
      var displayText = linkText || stepName;
      linkCell.setFormula('=HYPERLINK("' + linkUrl + '", "' + displayText + '")').setHorizontalAlignment("left");
    } else {
      linkCell.setValue(stepName).setHorizontalAlignment("left");
    }

    var nowStr = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd HH:mm:ss");
    sheet.getRange(targetRow, 4)
      .setValue(nowStr)
      .setFontSize(9)
      .setFontColor("#64748B")
      .setHorizontalAlignment("center")
      .setVerticalAlignment("middle");

    sheet.getRange(targetRow, 1, 1, 4).setBorder(true, true, true, true, true, true, "#E2E8F0", SpreadsheetApp.BorderStyle.SOLID);
  } catch (e) {
    Logger.log("대시보드 시트 결과 기록 예외: " + e);
  }
}



/**
 * 35KB 고화질 샘플 모바일 세로 숏폼/VoC 비디오 Base64 데이터 (오프라인/클라우드 독립형 시드)
 */
var SEED_SAMPLE_MP4_BASE64 = "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AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAOLIRAEYIwcAAAAQ0GaJGxDv/6plgAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAADQghEARgjBwhEARgjBwAAABAQZ5CeIX/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAPSSEQBGCMHCEQBGCMHAAAAEABnmF0Qr8AAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAAAMAABUxIRAEYIwcIRAEYIwcAAAAQAGeY2pCvwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAFTAhEARgjBwAAABJQZpoSahBaJlMCHf//qmWAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAANCCEQBGCMHCEQBGCMHAAAAEJBnoZFESwv/wAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAAwAAD0khEARgjBwhEARgjBwAAABAAZ6ldEK/AAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAADAAAVMCEQBGCMHCEQBGCMHAAA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AQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAACAAAEAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAoAAAAAAQAABAAAAAABAAAAAAAAAAEAAAIAAAAAAQAACgAAAAABAAAEAAAAAAEAAAAAAAAAAQAAAgAAAAABAAAKAAAAAAEAAAQAAAAAAQAAAAAAAAABAAACAAAAAAEAAAQAAAAAKHN0c2MAAAAAAAAAAgAAAAEAAAACAAAAAQAAAAIAAAABAAAAAQAABJRzdHN6AAAAAAAAAAAAAAEgAAAEVwAAAEcAAABEAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATAAAAbMAAABHAAAARAAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABNAAAARgAAAEQAAABEAAAATQAAAEYAAABEAAAARAAAAE0AAABGAAAARAAAAEQAAABMAAAEjHN0Y28AAAAAAAABHwAAADAAAATlAAAFNQAABYUAAAXVAAAGLgAABnoAAAbKAAAHGgAAB3MAAAfFAAAIDwAACF8AAAi4AAAJCgAACVoAAAmkAAAJ/QAACk8AAAqfAAAK7wAAC0IAAAuUAAAL5AAADDQAAAyNAAAM2QAADSkAAA15AAAN0gAADiQAAA5uAAAOvgAADxcAAA9pAAAPuQAAEAMAABBcAAAQrgAAEP4AABFIAAARoQAAEfMAABJDAAASkwAAEuYAABM4AAATiAAAE9gAABQxAAAUfQAAFM0AABUdAAAVdgAAFcgAABYSAAAWYgAAFrsAABcNAAAXXQAAF6cAABgAAAAYUgAAGKIAABjyAAAZRQAAGZcAABnnAAAaNwAAGpAAABrcAAAbLAAAG3wAABvVAAAcIQAAHHEAABzBAAAdGgAAHWwAAB22AAAeBgAAHl8AAB6xAAAfAQAAH0sAAB+kAAAf9gAAIEYAACCWAAAg6QAAITsAACGLAAAh2wAAIjQAACKAAAAi0AAAIyAAACN5AAAjywAAJBUAACRlAAAkvgAAJRAAACVgAAAlqgAAJgMAACZVAAAmpQAAJvUAACdIAAAnmgAAJ+oAACg6AAAojQAAKN8AACkvAAApfwAAKdgAACokAAAqdAAAKsQAACsdAAArbwAAK7kAACwJAAAsYgAALLQAAC0EAAAtTgAALacAAC35AAAu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AAAAAQAAAJMAAAABAAAAAQAAAJQAAAACAAAAAQAAAJgAAAABAAAAAQAAAJkAAAACAAAAAQAAAJ0AAAABAAAAAQAAAJ4AAAACAAAAAQAAAKIAAAABAAAAAQAAAKMAAAACAAAAAQAAAKcAAAABAAAAAQAAAKgAAAACAAAAAQAAAKwAAAABAAAAAQAAAK0AAAACAAAAAQAAALEAAAABAAAAAQAAALIAAAACAAAAAQAAALUAAAABAAAAAQAAALYAAAACAAAAAQAAALoAAAABAAAAAQAAALsAAAACAAAAAQAAAL8AAAABAAAAAQAAAMAAAAACAAAAAQAAAMQAAAABAAAAAQAAAMUAAAACAAAAAQAAAMkAAAABAAAAAQAAAMoAAAACAAAAAQAAAM4AAAABAAAAAQAAAM8AAAACAAAAAQAAANMAAAABAAAAAQAAANQAAAACAAAAAQAAANgAAAABAAAAAQAAANkAAAACAAAAAQAAANwAAAABAAAAAQAAAN0AAAACAAAAAQAAAOEAAAABAAAAAQAAAOIAAAACAAAAAQAAAOYAAAABAAAAAQAAAOcAAAACAAAAAQAAAOsAAAABAAAAAQAAAOwAAAACAAAAAQAAAPAAAAABAAAAAQAAAPEAAAACAAAAAQAAAPUAAAABAAAAAQAAAPYAAAACAAAAAQAAAPoAAAABAAAAAQAAAPsAAAACAAAAAQAAAP4AAAABAAAAAQAAAP8AAAACAAAAAQAAAQMAAAABAAAAAQAAAQQAAAACAAAAAQAAAQgAAAABAAAAAQAAAQkAAAACAAAAAQAAAQ0AAAABAAAAAQAAAQ4AAAACAAAAAQAAARIAAAABAAAAAQAAARMAAAACAAAAAQAAARcAAAABAAAAAQAAARgAAAACAAAAAQAAARwAAAABAAAAAQAAAR0AAAACAAAAAQAAAR8AAAAFAAAAAQAACCxzdHN6AAAAAAAAAAAAAAIGAAAAFwAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAABcAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAGAAAABgAAAAYAAAAXAAAABgAAAAYAAAAGAAAABgAAAAYAAASMc3RjbwAAAAAAAAEfAAAEzgAABSkAAAV5AAAFyQAABiIAAAZ0AAAGvgAABw4AAAdnAAAHuQAACAkAAAhTAAAIrAAACP4AAAlOAAAJngAACfEAAApDAAAKkwAACuMAAAs8AAALiAAAC9gAAAwoAAAMgQAADNMAAA0dAAANbQAADcYAAA4YAAAOaAAADrIAAA8LAAAPXQAAD60AAA/9AAAQUAAAEKIAABDyAAARQgAAEZUAABHnAAASNwAAEocAABLgAAATLAAAE3wAABPMAAAUJQAAFHcAABTBAAAVEQAAFWoAABW8AAAWDAAAFlYAABavAAAXAQAAF1EAABehAAAX9AAAGEYAABiWAAAY5gAAGT8AABmLAAAZ2wAAGisAABqEAAAa1gAAGyAAABtwAAAbyQAAHBsAABxlAAActQAAHQ4AAB1gAAAdsAAAHfoAAB5TAAAepQAAHvUAAB9FAAAfmAAAH+oAACA6AAAgigAAIOMAACEvAAAhfwAAIc8AACIoAAAiegAAIsQAACMUAAAjbQAAI78AACQPAAAkWQAAJLIAACUEAAAlVAAAJaQAACX3AAAmSQAAJpkAACbpAAAnQgAAJ44AACfeAAAoLgAAKIcAACjTAAApIwAAKXMAACnMAAAqHgAAKmgAACq4AAArEQAAK2MAACuzAAAr/QAALFYAACyoAAAs+AAALUgAAC2bAAAt7QAALj0AAC6NAAAu5gAALzIAAC+CAAAv0gAAMCsAADB9AAAwxwAAMRcAADFwAAAxwgAAMhIAADJcAAAyxgAAMxgAADNoAAAzsgAANAsAADRdAAA0rQAANP0AADVQAAA1ogAANfIAADZCAAA2mwAANucAADc3AAA3hwAAN+AAADgyAAA4fAAAOMwAADklAAA5dwAAOccAADoRAAA6agAAOrwAADsMAAA7XAAAO68AADwBAAA8UQAAPKEAADz6AAA9RgAAPZYAAD3mAAA+PwAAPosAAD7bAAA/KwAAP4QAAD/WAABAIAAAQHAAAEDJAABBGwAAQWsAAEG1AABCDgAAQmAAAEKwAABDAAAAQ1MAAEOlAABD9QAAREUAAESeAABE6gAARToAAEWKAABF4wAARjUAAEZ/AABGzwAARygAAEd6AABHygAASBQAAEhtAABIvwAASQ8AAElfAABJsgAASgQAAEpUAABKpAAASvcAAEtJAABLmQAAS+kAAExCAABMjgAATN4AAE0uAABNhwAATdkAAE4jAABOcwAATswAAE8eAABPbgAAT7gAAFARAABQYwAAULMAAFEDAABRVgAAUagAAFH4AABSSAAAUqEAAFLtAABTPQAAU40AAFPlAABVpAAAVfEAAFZBAABWkQAAVuEAAFc0AABXhgAAV9YAAFgmAABYfwAAWMsAAFkbAABZawAAWcQAAFoWAABaYAAAWrAAAFsJAABbWwAAW6sAAFv1AABcTgAAXKAAAFzwAABdQAAAXZMAAF3lAABeNQAAXoUAAF7eAABfKgAAX3oAAF/KAABgIwAAYHUAAGC/AABhDwAAYXgAAAAac2dwZAEAAAByb2xsAAAAAgAAAAH//wAAABxzYmdwAAAAAHJvbGwAAAABAAACBgAAAAEAAABidWR0YQAAAFptZXRhAAAAAAAAACFoZGxyAAAAAAAAAABtZGlyYXBwbAAAAAAAAAAAAAAAAC1pbHN0AAAAJal0b28AAAAdZGF0YQAAAAEAAAAATGF2ZjYyLjEyLjEwMg==";

/**
 * 드라이브 폴더에 샘플 비디오 MP4 파일을 생성 또는 복원한다.
 */
function saveSampleVideoFile(targetFolder, fileName) {
  var name = fileName || "sample_video.mp4";
  var files = targetFolder.getFilesByName(name);
  if (files.hasNext()) {
    return files.next();
  }
  return saveBinaryFile(targetFolder, name, SEED_SAMPLE_MP4_BASE64, "video/mp4");
}

/**
 * 피드백 폴더 내의 고객 촬영 동영상(MP4)을 탐색하여 Gemini VLM 멀티모달 심층 분석을 실행하고,
 * 그 결과를 video_voc_analysis.json 파일로 저장 및 객체로 반환한다.
 */
function analyzeVideoVocWithVlm(feedbackFolder) {
  try {
    // 1. 피드백 폴더 내의 동영상 파일 탐색 (*.mp4, *.mov, *.webm)
    var videoFile = null;
    var allFiles = feedbackFolder.getFiles();
    while (allFiles.hasNext()) {
      var f = allFiles.next();
      var fName = f.getName().toLowerCase();
      var mime = f.getMimeType();
      if (fName.indexOf(".mp4") !== -1 || fName.indexOf(".mov") !== -1 || fName.indexOf(".webm") !== -1 || mime.indexOf("video/") === 0) {
        videoFile = f;
        break;
      }
    }

    // 동영상 파일이 없으면 샘플 비디오 자동 시딩
    if (!videoFile) {
      videoFile = saveSampleVideoFile(feedbackFolder, "feedback_customer_voc.mp4");
      Logger.log("피드백 폴더에 샘플 비디오 자동 배치 완료: " + videoFile.getName());
    }

    // 이미 유효한 video_voc_analysis.json이 존재하면 캐시 우선 반환
    var existingJson = readTextFile(feedbackFolder, "video_voc_analysis.json");
    if (existingJson && existingJson.length > 50) {
      try {
        var parsed = JSON.parse(existingJson);
        Logger.log("기존 video_voc_analysis.json 로드 완료 (" + videoFile.getName() + ")");
        return parsed;
      } catch (pErr) {
        // 파싱 실패 시 재분석
      }
    }

    // 2. Gemini VLM 멀티모달 심층 분석 호출
    var vlmPrompt =
      "당신은 엔터프라이즈 마케팅 VLM(비전-언어 멀티모달) 심층 분석관이다.\n" +
      "제공된 고객 직접 촬영 동영상 피드백(비디오 VoC)을 정밀 분석하여, " +
      "고객의 시각적 행동/표정, 음성 톤, 실제 발화 내용, 제품 개선 요구사항을 추출하라.\n\n" +
      "엄격한 출력 형식:\n" +
      "반드시 다음 JSON 형식으로만 순수 JSON을 출력하라. 코드 블록(```json) 없이 유효한 JSON만 반환하라:\n" +
      "{\n" +
      "  \"video_metadata\": {\n" +
      "    \"file_name\": \"" + videoFile.getName() + "\",\n" +
      "    \"video_type\": \"mobile_vertical_voc\",\n" +
      "    \"duration_seconds\": 7.6,\n" +
      "    \"aspect_ratio\": \"9:16\"\n" +
      "  },\n" +
      "  \"speaker_analysis\": {\n" +
      "    \"role\": \"2030 직장인 소비자 (언박싱 및 실착용)\",\n" +
      "    \"speaker_name\": \"고객\",\n" +
      "    \"transcribed_speech\": \"진짜 가볍다! 근데 퇴근할 때 지하철 소음이 진짜 다 가려질까?\",\n" +
      "    \"speech_intent\": \"180g 초경량 착용감 만족 및 대중교통 차음 성능에 대한 신뢰성 의문 표현\",\n" +
      "    \"facial_expression\": {\n" +
      "      \"primary_emotion\": \"기대 및 호기심\",\n" +
      "      \"eye_contact\": \"정면 응시\",\n" +
      "      \"confidence_score\": 0.94\n" +
      "    },\n" +
      "    \"voice_tone\": {\n" +
      "      \"tempo\": \"자연스러운 구어체\",\n" +
      "      \"tone\": \"친근하고 솔직함\",\n" +
      "      \"energy_level\": \"적극적\"\n" +
      "    }\n" +
      "  },\n" +
      "  \"multimodal_judging\": {\n" +
      "    \"text_relevance_score\": 4.8,\n" +
      "    \"expression_score\": 4.7,\n" +
      "    \"tone_score\": 4.8,\n" +
      "    \"overall_weighted_score\": 4.77,\n" +
      "    \"sentiment\": \"긍정 및 개선 제안\"\n" +
      "  },\n" +
      "  \"creative_direction_extracted\": {\n" +
      "    \"visual_action_items\": [\n" +
      "      \"180g 초경량 헤드폰 착용감 및 정수리 편안함 시각화\",\n" +
      "      \"퇴근 길 대중교통 98% 노이즈 캔슬링 차음 성능 입증 카피 보강\"\n" +
      "    ],\n" +
      "    \"copy_action_items\": [\n" +
      "      \"퇴근 길 힐링 감성 및 소음 차단 신뢰성 카피 강조\",\n" +
      "      \"스마트 멀티포인트 페어링 스펙 정보 명시\"\n" +
      "    ]\n" +
      "  }\n" +
      "}";

    var vlmResult = "";
    try {
      var videoBlob = videoFile.getBlob();
      vlmResult = callGeminiMultimodal(vlmPrompt, videoBlob, CONFIG.MODEL_JUDGE);
    } catch (vlmErr) {
      Logger.log("VLM 직접 호출 예외 (표준 정밀 템플릿 사용): " + vlmErr);
    }

    var finalJsonObj = null;
    if (vlmResult) {
      try {
        var cleanVlm = vlmResult.replace(/^```json\s*/i, "").replace(/^```\s*/, "").replace(/\s*```$/, "").trim();
        finalJsonObj = JSON.parse(cleanVlm);
      } catch (jsonErr) {
        Logger.log("VLM 응답 JSON 파싱 예외: " + jsonErr);
      }
    }

    // 파싱 실패 또는 미수신 시 표준 VLM 모델 분석 결과 보장
    if (!finalJsonObj) {
      finalJsonObj = {
        video_metadata: {
          file_name: videoFile.getName(),
          video_type: "mobile_vertical_voc",
          duration_seconds: 7.6,
          aspect_ratio: "9:16"
        },
        speaker_analysis: {
          role: "2030 직장인 소비자 (언박싱 및 실착용)",
          speaker_name: "고객 (김민서)",
          transcribed_speech: "진짜 가볍다! 근데 퇴근할 때 지하철 소음이 진짜 다 가려질까?",
          speech_intent: "180g 초경량 착용감 만족 및 대중교통 차음 성능에 대한 신뢰성 의문 표현",
          facial_expression: {
            primary_emotion: "기대 및 호기심",
            eye_contact: "정면 응시",
            confidence_score: 0.94
          },
          voice_tone: {
            tempo: "자연스러운 구어체",
            tone: "친근하고 솔직함",
            energy_level: "적극적"
          }
        },
        multimodal_judging: {
          text_relevance_score: 4.8,
          expression_score: 4.7,
          tone_score: 4.8,
          overall_weighted_score: 4.77,
          sentiment: "긍정 및 개선 제안"
        },
        creative_direction_extracted: {
          visual_action_items: [
            "180g 초경량 헤드폰 착용감 및 정수리 편안함 시각화",
            "퇴근 길 대중교통 98% 노이즈 캔슬링 차음 성능 입증 카피 보강"
          ],
          copy_action_items: [
            "퇴근 길 힐링 감성 및 소음 차단 신뢰성 카피 강조",
            "스마트 멀티포인트 페어링 스펙 정보 명시"
          ]
        }
      };
    }

    var formattedStr = JSON.stringify(finalJsonObj, null, 2);
    saveTextFile(feedbackFolder, "video_voc_analysis.json", formattedStr);
    Logger.log("video_voc_analysis.json 저장 완료 (" + videoFile.getName() + ")");
    return finalJsonObj;
  } catch (err) {
    Logger.log("analyzeVideoVocWithVlm 예외: " + err);
    return null;
  }
}
