/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 5] 기획서(PLAN/SPEC) 도출 및 멀티 채널 콘텐츠 생성/보정 엔진 (Content Engine)
 */

/**
 * [액션 1] 마케터 자연어 아이디어를 기반으로 캠페인 기획서(PLAN) 및 콘텐츠 제작 명세서(SPEC)를 자동 도출한다.
 */
function runIdeaToPlanConversion() {
  return withUserLock("plan_generation", function() {
    var ui = SpreadsheetApp.getUi();
  var startTime = new Date().getTime();
  showProcessingToast("아이디어 기반 기획서(PLAN) 및 명세서(SPEC) 자동 도출 중...", 30);
  try {
    var campaignFolder = getCampaignFolder();
    var campaignCode = getCampaignCode();
    var inputFolder = getCampaignSubFolder(["input"]);
    var ideaDocName = (CONFIG && CONFIG.IDEA_DOC_NAME) || "아이디어 메모";

    // 1. 캠페인 루트 직속 [아이디어 메모] 읽기 (레거시 input/ 폴더도 보조 탐색)
    var existingIdea = readGoogleDoc(campaignFolder, ideaDocName) || readGoogleDoc(inputFolder, ideaDocName) || "";
    var existingPreview = existingIdea.replace(/\n+/g, " ").trim();
    if (existingPreview.length > 60) {
      existingPreview = existingPreview.substring(0, 60) + "...";
    }

    var promptMsg = existingPreview
      ? "현재 등록된 아이디어 메모:\n[" + existingPreview + "]\n\n" +
        "새로운 캠페인 아이디어를 입력하십시오:\n" +
        "(빈칸으로 두고 [확인]을 누르면 기존 아이디어 메모를 그대로 사용합니다)"
      : "캠페인 컨셉이나 아이디어 초안을 자유롭게 입력하십시오:\n(예: 2026 프리미엄 노이즈 캔슬링 헤드폰 론칭 프로모션)";

    var promptResp = ui.prompt("마케팅 캠페인 아이디어 확인", promptMsg, ui.ButtonSet.OK_CANCEL);
    if (promptResp.getSelectedButton() !== ui.Button.OK) {
      return;
    }

    var inputVal = promptResp.getResponseText().trim();
    var ideaMemo = inputVal || existingIdea;

    if (inputVal) {
      saveGoogleDoc(campaignFolder, ideaDocName, inputVal);
    }

    if (!ideaMemo || ideaMemo.trim().length < 5) {
      throw new Error("캠페인 아이디어가 입력되지 않아 기획서 생성을 중단합니다. 캠페인 루트의 [아이디어 메모] 문서를 확인하십시오.");
    }

    resetSessionTokens();

    // 2-1단계: 아이디어 메모로부터 마케팅 캠페인 기획서(PLAN) 전문 도출
    var planSystemInstruction = getPromptTemplate("01_idea_to_plan");
    var planUserPrompt =
      "다음은 마케터가 작성한 캠페인 아이디어 초안 메모이다.\n\n" +
      "### [마케터 아이디어 메모]\n" + ideaMemo + "\n\n" +
      "위 아이디어를 정밀 분석하여 마케팅 캠페인 기획서(PLAN) 전문을 체계적인 마크다운으로 작성하라.";

    var planContent = callGemini(planSystemInstruction, planUserPrompt);

    // 2-2단계: 도출된 기획서(PLAN)를 바탕으로 정밀한 콘텐츠 제작 명세서(SPEC) 도출 (독립 파이프라인)
    var specSystemInstruction = getPromptTemplate("02_plan_to_spec");
    var specUserPrompt =
      "다음은 이번 캠페인의 마케팅 기획서(PLAN) 전문이다.\n\n" +
      "### [마케팅 캠페인 기획서 (PLAN)]\n" + planContent + "\n\n" +
      "위 기획서의 타깃 오디언스, 핵심 USP, 캠페인 전략을 충실히 반영하여 제작 실무진(디자이너, 영상 PD, 카피라이터)을 위한 콘텐츠 제작 명세서(SPEC) 전문을 마크다운으로 작성하라:\n" +
      "- 가로 16:9 배너 (1920x1080), 세로 9:16 모바일 포스터 (1080x1920), 정방형 1:1 SNS 피드 (1080x1080)\n" +
      "- 15초 세로 9:16 모바일 숏폼 영상 콘티 규격 및 4대 평가 영역 설문 가이드라인 정의";

    var specContent = callGemini(specSystemInstruction, specUserPrompt);

    // 2-3단계: 제작 명세서(SPEC)의 타깃 오디언스에 맞춘 25인 AI 페르소나 패널 자동 합성 (온디맨드 동적 갱신)
    try {
      var personaSystemInstruction = getPromptTemplate("03_persona_synthesis");
      var personaUserPrompt =
        "다음은 이번 캠페인의 콘텐츠 제작 명세서(SPEC) 및 기획서(PLAN)이다.\n\n" +
        "### [마케팅 제작 명세서 발췌]\n" + (specContent.substring(0, 1800)) + "\n\n" +
        "위 명세서의 타깃 오디언스 프로파일 및 페인 포인트를 심층 분석하여, 콘텐츠를 다각도로 평가할 25인의 슬림 AI 페르소나 패널 JSON 객체(7대 필수 필드: id, name, age, gender, category, occupation, perspective)를 도출하라.";
      var synthesizedPersonasRaw = callGemini(personaSystemInstruction, personaUserPrompt);
      if (synthesizedPersonasRaw) {
        var parsedPersonas = safeParseJson(synthesizedPersonasRaw, null, false);
        if (parsedPersonas && (parsedPersonas.personas || Array.isArray(parsedPersonas))) {
          var personaFileName = (CONFIG && CONFIG.PERSONA_FILE_NAME) || "ai_personas.json";
          saveTextFile(campaignFolder, personaFileName, JSON.stringify(parsedPersonas, null, 2));
          Logger.log("제작 명세서 기반 25인 타깃 맞춤 페르소나 자동 합성 완료: " + personaFileName);
        }
      }
    } catch (personaErr) {
      Logger.log("타깃 페르소나 자동 합성 중 예외 (기존 페르소나 유지): " + personaErr);
    }

    var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
    var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";

    var planFile = saveGoogleDoc(campaignFolder, planDocName, planContent);
    var specFile = saveGoogleDoc(campaignFolder, specDocName, specContent);

    var durationSec = Math.round((new Date().getTime() - startTime) / 1000);
    var planTokens = getSessionTotalTokens();
    var halfTokens = Math.round(planTokens / 2);

    // 4. 대시보드 시트에 링크 및 소요 시간, 소모 토큰, 실행 로그 기록
    recordStepResultToSheet(
      "기획서 (PLAN)",
      "마케팅 캠페인 기획서",
      "완료",
      planFile.getUrl(),
      "구글 독스 열기 (PLAN)",
      durationSec,
      halfTokens,
      "마케터 아이디어 분석 기반 기획서(PLAN) 독스 자동 생성 완료"
    );
    recordStepResultToSheet(
      "제작 명세서 (SPEC)",
      "멀티 채널 콘텐츠 제작 명세서",
      "완료",
      specFile.getUrl(),
      "구글 독스 열기 (SPEC)",
      durationSec,
      halfTokens,
      "16:9 배너, 9:16 포스터, 1:1 SNS, 15초 숏폼 규격 명세서(SPEC) 독스 생성 완료"
    );

    showResultModal(
      "기획서 및 명세서 생성 완료",
      "캠페인 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC) 구글 독스가 준비되었습니다.\n\n" +
      "* 처리 소요 시간: " + formatDuration(durationSec) + "\n\n" +
      "아래 버튼을 클릭하여 기획서를 검토하거나 SPEC 수치를 직접 수정하십시오.",
      "기획서 구글 독스 열기 (PLAN)",
      planFile.getUrl()
    );
  } catch (e) {
    ui.alert("기획서 도출 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
  });
}

/**
 * [액션 2] 기획서(PLAN) 및 명세서(SPEC)를 기반으로 초판 마케팅 콘텐츠(rv-00)를 생성한다.
 */
function runInitialContentGeneration() {
  return withUserLock("content_generation", function() {
    var ui = SpreadsheetApp.getUi();
  var startTime = new Date().getTime();
  showProcessingToast("초판 마케팅 콘텐츠 생성 중 (rv-00)...", 60);
  try {
    var campaignFolder = getCampaignFolder();
    var campaignCode = getCampaignCode();
    var rv00Folder = getCampaignSubFolder(["output", "rv-00"]);

    // 폴더 내 기존 에셋 검사 및 스마트 분기
    var folderStatus = inspectRevisionFolder(rv00Folder, "00");
    var onlyMissing = false;

    if (!folderStatus.isEmpty) {
      if (folderStatus.isComplete) {
        var respComplete = ui.alert(
          "초판 콘텐츠(rv-00) 완비 안내",
          "초판 폴더(rv-00)에 모든 에셋(카피 독스, 이미지 3종, 숏폼 비디오)이 이미 완비되어 있습니다.\n\n" +
          "모든 에셋을 새로 덮어쓰시겠습니까?\n" +
          "([예]: 전체 새로 덮어쓰기 / [아니오]: 작업 중단)",
          ui.ButtonSet.YES_NO
        );
        if (respComplete !== ui.Button.YES) {
          return;
        }
      } else {
        var missingMsg = folderStatus.missingFiles.join(", ");
        var existingMsg = folderStatus.existingFiles.join(", ");
        var respMissing = ui.alert(
          "초판 콘텐츠(rv-00) 미완성 에셋 감지",
          "초판 폴더(rv-00)에 일부 에셋이 존재합니다.\n\n" +
          "* 보존 대상 기존 파일: " + existingMsg + "\n" +
          "* 누락된 미완성 파일: " + missingMsg + "\n\n" +
          "[예] 누락된 미완성 파일만 고속 보충 (권장, 기존 편집본 및 이미지 보존)\n" +
          "[아니오] 전체 덮어쓰기 (모든 에셋 새로 재생성)",
          ui.ButtonSet.YES_NO_CANCEL
        );
        if (respMissing === ui.Button.CANCEL) {
          return;
        } else if (respMissing === ui.Button.YES) {
          onlyMissing = true;
        }
      }
    }

    // 선결 조건 검사: PLAN 문서 확인
    var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
    var planContent = readGoogleDoc(campaignFolder, planDocName);
    if (!planContent) {
      planContent = readGoogleDoc(campaignFolder, "BRD");
    }
    if (!planContent) {
      var confirmGen = ui.alert(
        "기획서(PLAN) 누락 안내",
        "캠페인 기획서(PLAN) 문서를 찾을 수 없습니다.\n지금 [기획서 및 명세서 생성]을 먼저 실행하시겠습니까?",
        ui.ButtonSet.YES_NO
      );
      if (confirmGen === ui.Button.YES) {
        runIdeaToPlanConversion();
        return;
      } else {
        return;
      }
    }

    var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";
    var specContent = readGoogleDoc(campaignFolder, specDocName) || "";

    var contentDocName = (CONFIG && CONFIG.CONTENT_DOC_NAME) || "campaign_content";
    var finalizedContent = "";
    var visualBrief = "";

    resetSessionTokens();

    if (onlyMissing && folderStatus.hasDoc) {
      // 카피 독스가 이미 존재하면 기존 문서를 읽어 마케터의 수정본을 존중
      finalizedContent = readGoogleDoc(rv00Folder, contentDocName) || "";
      visualBrief = extractDynamicVisualPrompt(
        finalizedContent,
        planContent,
        "A stylish 20s Korean female commuter with lightweight premium ANC headphones in warm golden autumn sunlight on a modern Seoul street"
      );
    } else {
      // 1. 프롬프트 템플릿 로드 (구글 독스 스마트 캐싱)
      var systemInstruction = getPromptTemplate("04_content_generation");
      var promptText =
        "다음은 이번 캠페인의 마케팅 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC)이다.\n" +
        "명세서(SPEC)에 정의된 채널 규격, 영상 길이, 비주얼 가이드라인을 엄격히 준수하여 초판 campaign_content를 작성하라:\n\n" +
        "### [1. 마케팅 캠페인 기획서 (PLAN)]\n" + planContent + "\n\n" +
        "### [2. 멀티 채널 콘텐츠 제작 명세서 (SPEC)]\n" + (specContent || "기본 규격 준수");

      var generatedContent = callGemini(systemInstruction, promptText);

      // 2. 동적 비주얼 프롬프트 도출 및 숏폼 영상 콘티 완전 통합
      visualBrief = extractDynamicVisualPrompt(
        generatedContent,
        planContent,
        "A stylish 20s Korean female commuter with lightweight premium ANC headphones in warm golden autumn sunlight on a modern Seoul street"
      );
      finalizedContent = ensureShortsScriptInCampaignContent(generatedContent, "00", visualBrief);

      // 3. campaign_content 단일 구글 독스 문서 저장
      saveGoogleDoc(rv00Folder, contentDocName, finalizedContent);
    }

    // 4. 실시간 대표 비주얼 이미지 3종 및 Veo 비디오 생성
    Logger.log("동적 도출된 비주얼 프롬프트 (rv-00): " + visualBrief);
    var visResult = generateAndSaveVisualAssets(rv00Folder, "00", visualBrief, { onlyMissing: onlyMissing });

    var durationSec = Math.round((new Date().getTime() - startTime) / 1000);

    // 5. 상세 실행 로그 조립
    var logDetail = "";
    if (onlyMissing) {
      var totalSkipped = visResult.skipImageCount + (visResult.videoStatus === "skipped" ? 1 : 0);
      logDetail = "미완성 에셋 선별 보충 완료 (신규 이미지 " + visResult.genImageCount + "건 생성, 기존 에셋 " + totalSkipped + "건 보존)";
    } else {
      var videoDesc = visResult.videoStatus === "generated" ? "Veo 비디오 1건" : "숏폼 콘티 독스 수록";
      logDetail = "통합 카피 독스 1건, 대표 이미지 " + visResult.genImageCount + "종, " + videoDesc + " 정상 생성 완료";
    }

    // 6. 실행 대시보드에 링크 기록
    recordStepResultToSheet(
      "초판 마케팅 콘텐츠",
      "카피 및 비주얼 (rv-00)",
      "완료",
      rv00Folder.getUrl(),
      "구글 드라이브 폴더 열기 (rv-00)",
      durationSec,
      getSessionTotalTokens(),
      logDetail
    );

    showResultModal(
      "초판 마케팅 콘텐츠 생성 완료 (rv-00)",
      "카피 및 숏폼 영상 콘티가 통합된 구글 독스(campaign_content)와 대표 비주얼 이미지 3종, Veo 비디오가 준비되었습니다.\n\n" +
      "* 처리 소요 시간: " + formatDuration(durationSec) + "\n" +
      "* 실행 상세 내역: " + logDetail + "\n\n" +
      "아래 버튼을 눌러 초판 콘텐츠 폴더를 확인하십시오.",
      "초판 콘텐츠 폴더 열기 (rv-00)",
      rv00Folder.getUrl()
    );
  } catch (e) {
    ui.alert("초판 콘텐츠 생성 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
  });
}

/**
 * [액션 3] 피드백 요약본(feedback_summary)과 마케터 지침을 반영하여 N차 개정본 마케팅 콘텐츠를 완결 보정한다.
 */
function runReviseContent(targetRoundOpt, isSilentOpt) {
  return withUserLock("content_revision", function() {
    var ui = SpreadsheetApp.getUi();
    var isSilent = (isSilentOpt === true);
    var startTime = new Date().getTime();
    try {
    var campaignFolder = getCampaignFolder();

    // 회차 판별 (fb-01 -> rv-01, fb-02 -> rv-02 ...)
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
    var prefix = (roundNum < 10 ? "0" + roundNum : "" + roundNum);

    var targetRvFolder = getCampaignSubFolder(["output", targetRvName]);
    var onlyMissing = false;

    // 타깃 폴더 에셋 상태 검사 및 스마트 분기
    var folderStatus = inspectRevisionFolder(targetRvFolder, prefix);
    if (!folderStatus.isEmpty) {
      if (folderStatus.isComplete) {
        var nextRoundNum = roundNum + 1;
        var nextRvName = "rv-" + (nextRoundNum < 10 ? "0" + nextRoundNum : nextRoundNum);
        var respComplete = ui.alert(
          "개정본 콘텐츠(" + targetRvName + ") 완비 안내",
          "개정본 폴더(" + targetRvName + ")에 모든 에셋(카피 독스, 이미지 3종, 숏폼 비디오)이 이미 완비되어 있습니다.\n\n" +
          "[예] 다음 리비전(" + nextRvName + ")으로 안전 신규 생성 (권장, 기존 " + targetRvName + " 보존)\n" +
          "[아니오] 현재 리비전(" + targetRvName + ") 전체 새로 덮어쓰기\n" +
          "[취소] 작업 중단",
          ui.ButtonSet.YES_NO_CANCEL
        );
        if (respComplete === ui.Button.CANCEL) {
          return;
        } else if (respComplete === ui.Button.YES) {
          // 다음 리비전으로 타깃 전환
          roundNum = nextRoundNum;
          prevRvName = targetRvName;
          targetRvName = nextRvName;
          prefix = (roundNum < 10 ? "0" + roundNum : "" + roundNum);
          targetRvFolder = getCampaignSubFolder(["output", targetRvName]);
          folderStatus = inspectRevisionFolder(targetRvFolder, prefix);
        }
      } else {
        var missingMsg = folderStatus.missingFiles.join(", ");
        var existingMsg = folderStatus.existingFiles.join(", ");
        var respMissing = ui.alert(
          "개정본 콘텐츠(" + targetRvName + ") 미완성 에셋 감지",
          "개정본 폴더(" + targetRvName + ")에 일부 에셋이 이미 존재합니다.\n\n" +
          "* 보존 대상 기존 파일: " + existingMsg + "\n" +
          "* 누락된 미완성 파일: " + missingMsg + "\n\n" +
          "[예] 누락된 미완성 파일만 고속 보충 (권장, 기존 마케터 편집본 및 이미지 보존)\n" +
          "[아니오] 전체 덮어쓰기 (모든 에셋 새로 재생성)",
          ui.ButtonSet.YES_NO_CANCEL
        );
        if (respMissing === ui.Button.CANCEL) {
          return;
        } else if (respMissing === ui.Button.YES) {
          onlyMissing = true;
        }
      }
    }

    showProcessingToast("피드백 반영 마케팅 콘텐츠 보정 중 (" + targetRvName + ")...", 75);

    var prevRvFolder = getCampaignSubFolder(["output", prevRvName]);
    var feedbackFolder = getCampaignSubFolder(["input", targetRound]);

    // 선결 조건 1: 이전 콘텐츠 확인
    var targetContentDocName = (CONFIG && CONFIG.CONTENT_DOC_NAME) || "campaign_content";
    var previousAsset = readGoogleDoc(prevRvFolder, targetContentDocName) || readGoogleDoc(prevRvFolder, "campaign_asset");
    if (!previousAsset) {
      throw new Error("이전 마케팅 콘텐츠(" + prevRvName + ")를 찾을 수 없습니다. [초판 콘텐츠 생성]을 먼저 실행하십시오.");
    }

    // 선결 조건 2: feedback_summary 확인
    var summaryContent = readGoogleDoc(feedbackFolder, "feedback_summary");
    if (!summaryContent) {
      throw new Error("피드백 요약본(" + targetRound + "/feedback_summary)을 찾을 수 없습니다. [피드백 종합 분석 보고서 생성]을 먼저 실행하십시오.");
    }

    // 선결 조건 3: 마케터 보정 지침 확인 (독립 파일)
    var directiveDocName = (CONFIG && CONFIG.DIRECTIVE_DOC_NAME) || "마케터 보정 지침";
    var marketerDirective = readGoogleDoc(feedbackFolder, directiveDocName) || "";

    var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
    var planContent = readGoogleDoc(campaignFolder, planDocName) || readGoogleDoc(campaignFolder, "BRD") || "마케팅 캠페인 기획서";
    var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";
    var specContent = readGoogleDoc(campaignFolder, specDocName) || "콘텐츠 제작 명세서";

    var finalizedContent = "";
    var dynamicBrief = "";

    resetSessionTokens();

    if (onlyMissing && folderStatus.hasDoc) {
      // 카피 독스가 이미 있으면 기존 독스를 유지하고 비주얼 프롬프트만 재도출
      finalizedContent = readGoogleDoc(targetRvFolder, targetContentDocName) || "";
      dynamicBrief = extractDynamicVisualPrompt(
        finalizedContent,
        summaryContent,
        "A stylish 20s Korean female model enjoying cozy autumn commuter lifestyle with lightweight ANC headphones in a chic Seoul cafe",
        marketerDirective
      );
    } else {
      // 1. 프롬프트 템플릿 로드 (구글 독스 스마트 캐싱)
      var systemInstruction = getPromptTemplate("08_content_revision");
      var userPrompt =
        "다음은 원천 기획 명세(PLAN), 콘텐츠 제작 명세서(SPEC), 직전 마케팅 콘텐츠(" + prevRvName + "), " +
        "고객 피드백 종합 요약본(feedback_summary), 그리고 마케터의 최종 의사 결정 및 보정 지침이다.\n\n" +
        "### [1. 원천 마케팅 캠페인 기획서 (PLAN)]\n" + planContent + "\n\n" +
        "### [2. 콘텐츠 제작 명세서 (SPEC)]\n" + specContent + "\n\n" +
        "### [3. 직전 마케팅 콘텐츠 (" + prevRvName + ")]\n" + previousAsset + "\n\n" +
        "### [4. 고객 및 AI 페르소나 피드백 종합 분석 데이터 (feedback_summary)]\n" + summaryContent + "\n\n" +
        "### [5. 마케터 최종 의사 결정 및 보정 지침 (최우선 구속력 반영 필수 지침)]\n" +
        (marketerDirective || "고객 피드백 분석 보고서의 권장 보정 방향을 충실히 반영하여 품질을 고도화하라.");

      var refinedAsset = callGemini(systemInstruction, userPrompt);

      // 2. 동적 비주얼 프롬프트 도출 및 숏폼 영상 콘티 완전 통합
      dynamicBrief = extractDynamicVisualPrompt(
        refinedAsset,
        summaryContent,
        "A stylish 20s Korean female model enjoying cozy autumn commuter lifestyle with lightweight ANC headphones in a chic Seoul cafe",
        marketerDirective
      );
      finalizedContent = ensureShortsScriptInCampaignContent(refinedAsset, prefix, dynamicBrief);

      // 3. campaign_content 단일 구글 독스 문서 저장
      saveGoogleDoc(targetRvFolder, targetContentDocName, finalizedContent);
    }

    // 4. 신규 비주얼 이미지 3종 및 Veo 비디오 생성
    Logger.log("동적 도출된 비주얼 프롬프트 (" + targetRvName + "): " + dynamicBrief);
    var visResult = generateAndSaveVisualAssets(targetRvFolder, prefix, dynamicBrief, { onlyMissing: onlyMissing });

    var durationSec = Math.round((new Date().getTime() - startTime) / 1000);

    // 5. 상세 실행 로그 조립
    var logDetail = "";
    if (onlyMissing) {
      var totalSkipped = visResult.skipImageCount + (visResult.videoStatus === "skipped" ? 1 : 0);
      logDetail = "미완성 에셋 선별 보충 완료 (신규 이미지 " + visResult.genImageCount + "건 생성, 기존 에셋 " + totalSkipped + "건 보존)";
    } else {
      var videoDesc = visResult.videoStatus === "generated" ? "Veo 비디오 1건" : "숏폼 콘티 독스 수록";
      var directiveDesc = marketerDirective ? "마케터 지침서 100% 반영" : "권장 보정안 반영";
      logDetail = "개정본 독스 1건(" + directiveDesc + "), 신규 이미지 " + visResult.genImageCount + "종, " + videoDesc + " 생성 완료";
    }

    // 6. 대시보드 시트에 링크 기록
    var stepTitle = roundNum + "차 마케팅 콘텐츠 개정본 (" + targetRvName + ")";
    recordStepResultToSheet(
      targetRvName,
      stepTitle,
      "완료",
      targetRvFolder.getUrl(),
      "구글 드라이브 폴더 열기 (" + targetRvName + ")",
      durationSec,
      getSessionTotalTokens(),
      logDetail
    );

    if (!isSilent) {
      showResultModal(
        "마케팅 콘텐츠 보정 완료 (" + targetRvName + ")",
        "피드백 분석 보고서와 마케터 보정 지침이 반영된 개정본(" + targetRvName + ") 및 비주얼 에셋이 준비되었습니다.\n\n" +
        "* 처리 소요 시간: " + formatDuration(durationSec) + "\n" +
        "* 실행 상세 내역: " + logDetail + "\n\n" +
        "아래 버튼을 눌러 개정본 콘텐츠 폴더를 확인하십시오.",
        "개정본 콘텐츠 폴더 열기 (" + targetRvName + ")",
        targetRvFolder.getUrl()
      );
    }
    return finalizedContent;
  } catch (e) {
    if (!isSilent) {
      ui.alert("콘텐츠 보정 중 오류 발생", e.toString(), ui.ButtonSet.OK);
    } else {
      throw e;
    }
  }
  });
}
