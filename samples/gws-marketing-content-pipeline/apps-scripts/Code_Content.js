/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 5] 기획서(PLAN/SPEC) 도출 및 멀티 채널 콘텐츠 생성/보정 엔진 (Content Engine)
 */

/**
 * [Step 1] 캠페인 아이디어 메모 구글 독스를 작성/저장한다.
 *
 * @param {string} [customIdea] - 마케터가 입력한 원천 아이디어
 */
function runCampaignIdeaMemo(customIdea) {
  return withUserLock("idea_memo", function() {
    var startTime = new Date().getTime();
    try {
      var campaignFolder = getCampaignFolder();
      var ideaDocName = (CONFIG && CONFIG.IDEA_DOC_NAME) || "아이디어 메모";
      var inputFolder = getCampaignSubFolder(["input"]);

      var inputVal = (customIdea || "").trim();
      var existingIdea = readGoogleDoc(campaignFolder, ideaDocName) || readGoogleDoc(inputFolder, ideaDocName) || "";
      var ideaMemo = inputVal || existingIdea.trim();

      if (!ideaMemo) {
        ideaMemo = "# " + campaignFolder.getName() + " 아이디어 메모\n\n* 캠페인 핵심 아이디어를 자유롭게 작성하십시오.";
      }

      var ideaFile = saveGoogleDoc(campaignFolder, ideaDocName, ideaMemo);
      var durationSec = Math.max(1, Math.round((new Date().getTime() - startTime) / 1000));

      recordStepResultToSheet(
        "Step 1",
        "캠페인 아이디어 메모",
        "완료",
        ideaFile.getUrl(),
        "[아이디어 메모] 구글 독스 열기",
        durationSec,
        0,
        "마케터 원천 아이디어 등록 완료 (구글 독스에서 직접 수정 가능)"
      );

      return {
        success: true,
        message: "캠페인 아이디어 메모가 준비되었습니다. 생성된 구글 독스에서 아이디어를 검토하신 후 [Step 2] 기획서(PLAN) 생성을 진행해 주십시오.",
        ideaDocUrl: ideaFile.getUrl(),
        ideaContent: ideaMemo
      };
    } catch (e) {
      throw e;
    }
  });
}

/**
 * [Step 2] 아이디어 메모를 기반으로 마케팅 캠페인 기획서(PLAN) 전문을 도출한다.
 *
 * @param {string} [customIdea] - 인라인 전달 아이디어 (선택)
 */
function runIdeaToPlan(customIdea) {
  return withUserLock("plan_generation", function() {
    var startTime = new Date().getTime();
    showProcessingToast("아이디어 기반 기획서(PLAN) 자동 생성 중...", 30);
    try {
      var campaignFolder = getCampaignFolder();
      var ideaDocName = (CONFIG && CONFIG.IDEA_DOC_NAME) || "아이디어 메모";
      var inputFolder = getCampaignSubFolder(["input"]);

      var inputVal = (customIdea || "").trim();
      var existingIdea = readGoogleDoc(campaignFolder, ideaDocName) || readGoogleDoc(inputFolder, ideaDocName) || "";
      var ideaMemo = inputVal || existingIdea.trim();

      if (!ideaMemo || ideaMemo.length < 5) {
        throw new Error("캠페인 아이디어가 비어 있습니다. [Step 1] 아이디어 메모를 작성해 주시거나 사이드바 대화창에 아이디어를 직접 입력해 주십시오.");
      }

      resetSessionTokens();
      var planSystemInstruction = getPromptTemplate("01_idea_to_plan");
      var planUserPrompt =
        "다음은 마케터가 작성한 캠페인 아이디어 초안 메모이다.\n\n" +
        "### [마케터 아이디어 메모]\n" + ideaMemo + "\n\n" +
        "위 아이디어를 정밀 분석하여 마케팅 캠페인 기획서(PLAN) 전문을 체계적인 마크다운으로 작성하라.";

      var planContent = callGemini(planSystemInstruction, planUserPrompt);
      var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
      var planFile = saveGoogleDoc(campaignFolder, planDocName, planContent);
      var durationSec = Math.max(1, Math.round((new Date().getTime() - startTime) / 1000));
      var tokens = getSessionTotalTokens();

      recordStepResultToSheet(
        "Step 2",
        "캠페인 기획서 (PLAN)",
        "완료",
        planFile.getUrl(),
        "기획서 독스 열기 (PLAN)",
        durationSec,
        tokens,
        "아이디어 기반 캠페인 기획서(PLAN) 독스 자동 생성 완료 (마케터 수정 가능)"
      );

      return {
        success: true,
        message: "캠페인 기획서(PLAN)가 생성되었습니다. 독스를 열어 검토 및 보완하신 후, [Step 3] 제작 명세서(SPEC) 생성을 진행해 주십시오.",
        planUrl: planFile.getUrl()
      };
    } catch (e) {
      var failDuration = Math.round((new Date().getTime() - startTime) / 1000);
      recordStepResultToSheet("Step 2", "캠페인 기획서 (PLAN)", "실패", "", "", failDuration, 0, "오류: " + (e.message || e.toString()));
      throw e;
    }
  });
}

/**
 * [Step 3] 기획서(PLAN)를 기반으로 콘텐츠 제작 명세서(SPEC) 전문을 도출한다.
 */
function runPlanToSpec() {
  return withUserLock("spec_generation", function() {
    var startTime = new Date().getTime();
    showProcessingToast("기획서 기반 제작 명세서(SPEC) 자동 생성 중...", 30);
    try {
      var campaignFolder = getCampaignFolder();
      var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
      var planContent = readGoogleDoc(campaignFolder, planDocName) || readGoogleDoc(campaignFolder, "BRD");

      if (!planContent || planContent.length < 20) {
        throw new Error("캠페인 기획서(PLAN)를 찾을 수 없습니다. [Step 2] 캠페인 기획서(PLAN) 생성을 먼저 실행해 주십시오.");
      }

      resetSessionTokens();
      var specSystemInstruction = getPromptTemplate("02_plan_to_spec");
      var specUserPrompt =
        "다음은 이번 캠페인의 마케팅 기획서(PLAN) 전문이다.\n\n" +
        "### [마케팅 캠페인 기획서 (PLAN)]\n" + planContent + "\n\n" +
        "위 기획서의 타깃 오디언스, 핵심 USP, 캠페인 전략을 충실히 반영하여 제작 실무진(디자이너, 영상 PD, 카피라이터)을 위한 콘텐츠 제작 명세서(SPEC) 전문을 마크다운으로 작성하라:\n" +
        "- 가로 16:9 배너 (1920x1080), 세로 9:16 모바일 포스터 (1080x1920), 정방형 1:1 SNS 피드 (1080x1080)\n" +
        "- 15초 세로 9:16 모바일 숏폼 영상 콘티 규격 및 4대 평가 영역 설문 가이드라인 정의";

      var specContent = callGemini(specSystemInstruction, specUserPrompt);
      var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";
      var specFile = saveGoogleDoc(campaignFolder, specDocName, specContent);
      var durationSec = Math.max(1, Math.round((new Date().getTime() - startTime) / 1000));
      var tokens = getSessionTotalTokens();

      recordStepResultToSheet(
        "Step 3",
        "제작 명세서 (SPEC)",
        "완료",
        specFile.getUrl(),
        "명세서 독스 열기 (SPEC)",
        durationSec,
        tokens,
        "16:9 배너, 9:16 포스터, 1:1 SNS, 15초 숏폼 규격 명세서(SPEC) 생성 완료"
      );

      return {
        success: true,
        message: "콘텐츠 제작 명세서(SPEC)가 생성되었습니다. 채널 규격을 검토하신 후 [Step 4] 맞춤 AI 페르소나 패널 구성을 진행해 주십시오.",
        specUrl: specFile.getUrl()
      };
    } catch (e) {
      var failDuration = Math.round((new Date().getTime() - startTime) / 1000);
      recordStepResultToSheet("Step 3", "제작 명세서 (SPEC)", "실패", "", "", failDuration, 0, "오류: " + (e.message || e.toString()));
      throw e;
    }
  });
}

/**
 * [Step 4] 제작 명세서(SPEC)의 타깃 오디언스에 맞춘 25인 맞춤 AI 페르소나 패널을 자동 구성한다.
 */
function runPersonaPanelSynthesis() {
  return withUserLock("persona_synthesis", function() {
    var startTime = new Date().getTime();
    showProcessingToast("제작 명세서 기반 맞춤 AI 페르소나 패널 자동 구성 중...", 30);
    try {
      var campaignFolder = getCampaignFolder();
      var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";
      var specContent = readGoogleDoc(campaignFolder, specDocName) || "";
      var planContent = readGoogleDoc(campaignFolder, (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN") || "";

      if (!specContent && !planContent) {
        throw new Error("제작 명세서(SPEC) 또는 기획서(PLAN)를 찾을 수 없습니다. [Step 3] 제작 명세서(SPEC) 생성을 먼저 실행해 주십시오.");
      }

      resetSessionTokens();
      var personaSystemInstruction = getPromptTemplate("03_persona_synthesis");
      var personaUserPrompt =
        "다음은 이번 캠페인의 콘텐츠 제작 명세서(SPEC) 및 기획서(PLAN)이다.\n\n" +
        "### [마케팅 제작 명세서 발췌]\n" + (specContent.substring(0, 1800) || planContent.substring(0, 1800)) + "\n\n" +
        "위 명세서의 타깃 오디언스 프로파일 및 페인 포인트를 심층 분석하여, 콘텐츠를 다각도로 평가할 슬림 AI 페르소나 패널 JSON 객체(7대 필수 필드: id, name, age, gender, category, occupation, perspective)를 도출하라.";

      var synthesizedPersonasRaw = callGemini(personaSystemInstruction, personaUserPrompt);
      var personaFileName = (CONFIG && CONFIG.PERSONA_FILE_NAME) || "ai_personas.json";
      var personaFile = null;

      if (synthesizedPersonasRaw) {
        var parsedPersonas = safeParseJson(synthesizedPersonasRaw, null, false);
        if (parsedPersonas && (parsedPersonas.personas || Array.isArray(parsedPersonas))) {
          personaFile = saveTextFile(campaignFolder, personaFileName, JSON.stringify(parsedPersonas, null, 2));
          Logger.log("제작 명세서 기반 타깃 맞춤 페르소나 자동 합성 완료: " + personaFileName);
        }
      }

      if (!personaFile) {
        var existing = campaignFolder.getFilesByName(personaFileName);
        if (existing.hasNext()) {
          personaFile = existing.next();
        } else {
          var master = getMasterPersonas25();
          personaFile = saveTextFile(campaignFolder, personaFileName, JSON.stringify(master, null, 2));
        }
      }

      var durationSec = Math.max(1, Math.round((new Date().getTime() - startTime) / 1000));
      var tokens = getSessionTotalTokens();

      recordStepResultToSheet(
        "Step 4",
        "맞춤 AI 페르소나 패널",
        "완료",
        personaFile.getUrl(),
        "AI 페르소나 JSON 열기",
        durationSec,
        tokens,
        "타깃 오디언스 맞춤 가상 소비자 패널(ai_personas.json) 자동 구성 완료"
      );

      return {
        success: true,
        message: "맞춤 AI 페르소나 패널이 구성되었습니다. 이제 [Step 5] 초판 멀티 채널 콘텐츠(rv-00) 생성을 진행해 주십시오.",
        personaUrl: personaFile.getUrl()
      };
    } catch (e) {
      var failDuration = Math.round((new Date().getTime() - startTime) / 1000);
      recordStepResultToSheet("Step 4", "맞춤 AI 페르소나 패널", "실패", "", "", failDuration, 0, "오류: " + (e.message || e.toString()));
      throw e;
    }
  });
}

/**
 * [Step 5] 기획서(PLAN) 및 명세서(SPEC)를 기반으로 초판 마케팅 콘텐츠(rv-00)를 생성한다.
 * (모달 팝업 없이 스마트 에셋 보존 및 누락 파일 고속 보충 자동 적용)
 *
 * @param {boolean} [forceOverwrite] - 기존 에셋 완비 시 전체 강제 새로고침 여부 (기본값: false, 기존 파일 안전 보존)
 */
function runInitialContentGeneration(forceOverwrite) {
  return withUserLock("content_generation", function() {
    var startTime = new Date().getTime();
    showProcessingToast("초판 마케팅 콘텐츠 생성 중 (rv-00)...", 60);
    try {
      var campaignFolder = getCampaignFolder();
      var campaignCode = getCampaignCode();
      var rv00Folder = getCampaignSubFolder(["output", "rv-00"]);

      // 선결 조건 검사: PLAN 문서 확인
      var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
      var planContent = readGoogleDoc(campaignFolder, planDocName);
      if (!planContent) {
        planContent = readGoogleDoc(campaignFolder, "BRD");
      }
      if (!planContent) {
        throw new Error("캠페인 기획서(PLAN) 문서를 찾을 수 없습니다. 사이드바의 [Step 2] 캠페인 기획서(PLAN) 생성을 먼저 실행해 주십시오.");
      }

      // 폴더 내 기존 에셋 검사 및 스마트 비차단 분기
      var folderStatus = inspectRevisionFolder(rv00Folder, "00");
      var onlyMissing = false;

      if (!folderStatus.isEmpty) {
        if (folderStatus.isComplete && !forceOverwrite) {
          return {
            success: true,
            status: "already_complete",
            message: "초판 콘텐츠(rv-00)의 모든 에셋(카피 독스, 이미지 3종, 숏폼 영상)이 이미 완비되어 있어 기존 자산을 안전하게 보존했습니다. 전체 새로 생성이 필요한 경우 아래 버튼을 클릭하십시오.",
            folderUrl: rv00Folder.getUrl(),
            actionChip: "<div style='margin-top:6px;'><button class='btn btn-primary btn-sm' onclick=\"callServer('forceRunInitialContent', '초판 콘텐츠 전체 재생성')\">[초판 전체 다시 제작]</button></div>"
          };
        } else if (!folderStatus.isComplete) {
          // 일부 에셋만 누락된 경우: 기존 마케터 수정본과 이미지를 완벽 보존하고 누락 파일만 스마트 고속 보충!
          onlyMissing = true;
        }
      }

    var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";
    var specContent = readGoogleDoc(campaignFolder, specDocName) || "";

    // 1. [스마트 컴파일] 마케터의 제작 명세서(SPEC)로부터 미디어 제작 스펙(비디오/이미지 비율) 지능형 컴파일 및 media_specs.json 저장
    var mediaSpec = compileMediaSpecFromDocs(specContent, "00", "", rv00Folder);

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
      // 2. 프롬프트 템플릿 로드 (구글 독스 스마트 캐싱)
      var systemInstruction = getPromptTemplate("04_content_generation");
      var promptText =
        "다음은 이번 캠페인의 마케팅 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC)이다.\n" +
        "명세서(SPEC)에 정의된 채널 규격, 영상 길이, 비주얼 가이드라인을 엄격히 준수하여 초판 campaign_content를 작성하라:\n\n" +
        "### [1. 마케팅 캠페인 기획서 (PLAN)]\n" + planContent + "\n\n" +
        "### [2. 멀티 채널 콘텐츠 제작 명세서 (SPEC)]\n" + (specContent || "기본 규격 준수");

      var generatedContent = callGemini(systemInstruction, promptText);

      // 3. 동적 비주얼 프롬프트 도출 및 숏폼 영상 콘티 완전 통합
      visualBrief = extractDynamicVisualPrompt(
        generatedContent,
        planContent,
        "A stylish 20s Korean female commuter with lightweight premium ANC headphones in warm golden autumn sunlight on a modern Seoul street"
      );
      finalizedContent = ensureShortsScriptInCampaignContent(generatedContent, "00", visualBrief);

      // 4. [UX 핵심] 마케터가 독스 열자마자 확인 가능한 [SPEC 반영 미디어 산출물 현황] 헤더를 독스 최상단에 포함하여 저장
      var specReportHeader = buildMediaSpecReportHeader(mediaSpec);
      saveGoogleDoc(rv00Folder, contentDocName, specReportHeader + finalizedContent);
    }

    // 5. 실시간 대표 비주얼 이미지 및 Veo 비디오 동적 생성 (마케터 명세서 지정 종횡비 및 비디오 제외 여부 100% 반영)
    Logger.log("동적 도출된 비주얼 프롬프트 (rv-00): " + visualBrief);
    var visResult = generateAndSaveVisualAssets(rv00Folder, "00", visualBrief, { onlyMissing: onlyMissing }, mediaSpec);

    var durationSec = Math.round((new Date().getTime() - startTime) / 1000);

    // 6. 상세 실행 내역 조립
    var logDetail = "";
    if (onlyMissing) {
      var totalSkipped = visResult.skipImageCount + (visResult.videoStatus === "skipped" ? 1 : 0);
      logDetail = "미완성 에셋 선별 보충 완료 (신규 이미지 " + visResult.genImageCount + "건 생성, 기존 에셋 " + totalSkipped + "건 보존)";
    } else {
      var videoDesc = (visResult.videoStatus === "generated")
        ? "Veo 비디오 1건"
        : (visResult.videoStatus === "excluded" ? "비디오 제외(명세서 반영)" : "숏폼 콘티 독스 수록");
      logDetail = "통합 카피 독스 1건, 대표 이미지 " + visResult.genImageCount + "종, " + videoDesc + " 생성 완료";
      if (mediaSpec && mediaSpec.reason) {
        logDetail += " [" + mediaSpec.reason + "]";
      }
    }

    // 6. 실행 대시보드에 링크 기록
    recordStepResultToSheet(
      "Step 5",
      "초판 멀티 채널 콘텐츠 (rv-00)",
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

    return {
      success: true,
      targetRv: "rv-00",
      message: "초판 마케팅 콘텐츠(rv-00) 생성이 완료되었습니다 (" + logDetail + "). 생성된 결과물을 확인하시고 [Step 6] AI 페르소나 다면 평가를 진행해 주십시오.",
      folderUrl: rv00Folder.getUrl()
    };
  } catch (e) {
    var failDuration = Math.round((new Date().getTime() - startTime) / 1000);
    recordStepResultToSheet(
      "초판 콘텐츠 (rv-00)",
      "멀티 채널 콘텐츠 생성",
      "실패",
      "",
      "",
      failDuration,
      0,
      "오류 발생: " + (e.message || e.toString())
    );
    throw e;
  }
  });
}

/**
 * [Step 9] 피드백 요약본(feedback_summary)과 마케터 지침을 반영하여 N차 개정본 마케팅 콘텐츠를 완결 보정한다.
 * (모달 팝업 없이 스마트 리비전 자동 승격 및 누락 파일 고속 보충 적용)
 *
 * @param {string} [targetRoundOpt] - 대상 피드백 라운드 (fb-01, fb-02 등)
 * @param {boolean} [isSilentOpt] - 무음 모드 여부
 * @param {boolean} [forceOverwrite] - 현재 리비전 강제 덮어쓰기 여부
 * @param {string} [customDirectiveOpt] - 인라인 입력 또는 대화창에서 전달된 마케터 수기 보정 지침 (선택)
 */
function runReviseContent(targetRoundOpt, isSilentOpt, forceOverwrite, customDirectiveOpt) {
  return withUserLock("content_revision", function() {
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

    // 타깃 폴더 에셋 상태 검사 및 스마트 분기 (모달 없이 자율 결정)
    var folderStatus = inspectRevisionFolder(targetRvFolder, prefix);
    if (!folderStatus.isEmpty) {
      if (folderStatus.isComplete && !forceOverwrite) {
        // 이미 완비되어 있으면 다음 신규 리비전으로 안전 자동 전환 (기존 리비전 100% 보존)
        var nextRoundNum = roundNum + 1;
        var nextRvName = "rv-" + (nextRoundNum < 10 ? "0" + nextRoundNum : nextRoundNum);
        roundNum = nextRoundNum;
        prevRvName = targetRvName;
        targetRvName = nextRvName;
        prefix = (roundNum < 10 ? "0" + roundNum : "" + roundNum);
        targetRvFolder = getCampaignSubFolder(["output", targetRvName]);
        folderStatus = inspectRevisionFolder(targetRvFolder, prefix);
      } else if (!folderStatus.isComplete) {
        // 일부 에셋만 누락된 경우: 기존 마케터 수정본과 이미지를 보존하고 누락 파일만 스마트 고속 보충
        onlyMissing = true;
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

    // 선결 조건 3: 마케터 보정 지침 확인 (인자 전달값 우선 및 독립 파일 보존)
    var directiveDocName = (CONFIG && CONFIG.DIRECTIVE_DOC_NAME) || "마케터 보정 지침";
    var inputDirective = (customDirectiveOpt || "").trim();
    if (inputDirective) {
      saveGoogleDoc(feedbackFolder, directiveDocName, inputDirective);
    }
    var marketerDirective = inputDirective || readGoogleDoc(feedbackFolder, directiveDocName) || "";

    var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
    var planContent = readGoogleDoc(campaignFolder, planDocName) || readGoogleDoc(campaignFolder, "BRD") || "마케팅 캠페인 기획서";
    var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";
    var specContent = readGoogleDoc(campaignFolder, specDocName) || "콘텐츠 제작 명세서";

    // 1. [스마트 컴파일] 명세서(SPEC) 및 마케터 보정 지침으로부터 개정본 미디어 제작 스펙 도출 및 media_specs.json 저장
    var mediaSpec = compileMediaSpecFromDocs(specContent, prefix, marketerDirective, targetRvFolder);

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
      // 2. 프롬프트 템플릿 로드 (구글 독스 스마트 캐싱)
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

      // 3. 동적 비주얼 프롬프트 도출 및 숏폼 영상 콘티 완전 통합
      dynamicBrief = extractDynamicVisualPrompt(
        refinedAsset,
        summaryContent,
        "A stylish 20s Korean female model enjoying cozy autumn commuter lifestyle with lightweight ANC headphones in a chic Seoul cafe",
        marketerDirective
      );
      finalizedContent = ensureShortsScriptInCampaignContent(refinedAsset, prefix, dynamicBrief);

      // 4. [UX 핵심] 마케터가 독스 열자마자 확인 가능한 [SPEC 반영 미디어 산출물 현황] 헤더를 독스 최상단에 포함하여 저장
      var specReportHeader = buildMediaSpecReportHeader(mediaSpec);
      saveGoogleDoc(targetRvFolder, targetContentDocName, specReportHeader + finalizedContent);
    }

    // 5. 신규 비주얼 이미지 및 Veo 비디오 동적 생성 (마케터 명세서 지정 종횡비 및 비디오 제외 여부 반영)
    Logger.log("동적 도출된 비주얼 프롬프트 (" + targetRvName + "): " + dynamicBrief);
    var visResult = generateAndSaveVisualAssets(targetRvFolder, prefix, dynamicBrief, { onlyMissing: onlyMissing }, mediaSpec);

    var durationSec = Math.round((new Date().getTime() - startTime) / 1000);

    // 6. 상세 실행 내역 조립
    var logDetail = "";
    if (onlyMissing) {
      var totalSkipped = visResult.skipImageCount + (visResult.videoStatus === "skipped" ? 1 : 0);
      logDetail = "미완성 에셋 선별 보충 완료 (신규 이미지 " + visResult.genImageCount + "건 생성, 기존 에셋 " + totalSkipped + "건 보존)";
    } else {
      var videoDesc = (visResult.videoStatus === "generated")
        ? "Veo 비디오 1건"
        : (visResult.videoStatus === "excluded" ? "비디오 제외(명세서 반영)" : "숏폼 콘티 독스 수록");
      var directiveDesc = marketerDirective ? "마케터 지침서 반영" : "권장 보정안 반영";
      logDetail = "개정본 독스 1건(" + directiveDesc + "), 대표 이미지 " + visResult.genImageCount + "종, " + videoDesc + " 생성 완료";
      if (mediaSpec && mediaSpec.reason) {
        logDetail += " [" + mediaSpec.reason + "]";
      }
    }

    // 6. 대시보드 시트에 링크 기록
    var stepTitle = roundNum + "차 마케팅 콘텐츠 개정본 (" + targetRvName + ")";
    recordStepResultToSheet(
      "Step 9",
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
        "[마케터 보정 지침] 구글 독스에서 언제든 수정 후 다시 보정할 수 있습니다.",
        "개정본 콘텐츠 폴더 열기 (" + targetRvName + ")",
        targetRvFolder.getUrl()
      );
    }
    return {
      success: true,
      message: "콘텐츠 보정(" + targetRvName + ")이 완료되었습니다. [마케터 보정 지침] 구글 독스에서 언제든 지침을 추가 수정할 수 있습니다.",
      targetRv: targetRvName,
      folderUrl: targetRvFolder.getUrl(),
      content: finalizedContent
    };
  } catch (e) {
    var failDuration = Math.round((new Date().getTime() - startTime) / 1000);
    recordStepResultToSheet(
      "콘텐츠 보정",
      "피드백 반영 개정본 생성",
      "실패",
      "",
      "",
      failDuration,
      0,
      "오류 발생: " + (e.message || e.toString())
    );
    throw e;
  }
  });
}
