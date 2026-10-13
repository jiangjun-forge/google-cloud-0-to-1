/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [Step 3] 기획서(PLAN) 및 명세서(SPEC) 기반 초판 마케팅 콘텐츠 양산 엔진 (rv-00 Initial Content Generation)
 */

function runInitialAssetGeneration() {
  var ui = SpreadsheetApp.getUi();
  try {
    var campaignFolder = getCampaignFolder();
    var campaignCode = getCampaignCode();
    var inputFolder = getCampaignSubFolder(["input"]);
    var rv00Folder = getCampaignSubFolder(["output", "rv-00"]);

    // 1. 내장 시스템 지침 (Zero-Prompt No-Code)
    var systemInstruction =
      "당신은 전문 크리에이티브 마케팅 디렉터이자 카피라이터이다.\n" +
      "주어진 마케팅 캠페인 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC)를 바탕으로 단일 캠페인 종합 마케팅 콘텐츠 문서(campaign_content) 1본을 완성도 높은 마케팅 카피 형식으로 작성하라.\n\n" +
      "필수 구성:\n" +
      "1. 헤드카피 및 슬로건 (3종)\n" +
      "2. 인스타그램 카드뉴스 및 피드 카피 (SPEC 규격 준수)\n" +
      "3. 네이버 블로그 리뷰형 기고문 (SPEC 규격 준수)\n" +
      "4. 모바일 숏폼 영상 콘티 (SPEC에 명시된 러닝타임 및 세로 9:16 규격, 타임라인별 나레이션 및 화면 연출 지시문)\n" +
      "5. 제미나이 이미지 생성용 비주얼 프롬프트 (가로 16:9, 세로 9:16, 정방형 1:1)\n\n" +
      "엄격한 작성 규칙:\n" +
      "1. 콘텐츠 제작 명세서(SPEC)에 정의된 채널 규격, 숏폼 러닝타임, 톤앤매너를 최우선으로 준수하십시오.\n" +
      "2. 이모지와 중간 점을 일절 쓰지 말고 쉼표(,)를 사용하십시오.\n" +
      "3. 모든 서술은 단호하고 격조 높은 문어체/평서문('-다' 체)으로 작성하십시오.\n" +
      "4. 한글 복합어는 철저하게 띄어 쓰십시오.\n" +
      "5. 분량 및 가독성: 각 채널별 카피와 콘티는 마케터가 한눈에 읽고 즉시 검토할 수 있도록, 불필요한 미사여구를 배제하고 핵심 메시지 중심으로 명쾌하고 컴팩트하게 작성하십시오.";

    // 2. 캠페인 루트의 PLAN 및 SPEC 구글 독스 읽기
    var planDocName = (CONFIG && CONFIG.PLAN_DOC_NAME) || "PLAN";
    var planContent = readGoogleDoc(campaignFolder, planDocName);
    if (!planContent) {
      planContent = readGoogleDoc(campaignFolder, "BRD");
    }
    if (!planContent) {
      throw new Error("마케팅 캠페인 기획서(PLAN) 구글 독스 문서를 찾을 수 없습니다. [Step 1]을 먼저 실행하여 기획서(PLAN)를 생성하십시오.");
    }

    var specDocName = (CONFIG && CONFIG.SPEC_DOC_NAME) || "SPEC";
    var specContent = readGoogleDoc(campaignFolder, specDocName) || "";

    // 3. Gemini 호출
    var promptText = "다음은 이번 캠페인의 마케팅 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC)이다.\n" +
                     "명세서(SPEC)에 정의된 채널 규격, 영상 길이, 비주얼 가이드라인을 엄격히 준수하여 초판 campaign_content를 작성하라:\n\n" +
                     "### [1. 마케팅 캠페인 기획서 (PLAN)]\n" + planContent + "\n\n" +
                     "### [2. 멀티 채널 콘텐츠 제작 명세서 (SPEC)]\n" + (specContent || "기본 규격 준수");
    var generatedContent = callGemini(systemInstruction, promptText);

    // 4. 저장: output/rv-00/에 campaign_content 구글 독스 단일 저장
    var contentDocName = (CONFIG && CONFIG.CONTENT_DOC_NAME) || "campaign_content";
    saveGoogleDoc(rv00Folder, contentDocName, generatedContent);

    // 5. 실시간 대표 비주얼 이미지 3종 비율 세트 생성 (rv-00: 가로 16:9, 세로 9:16, 정사각 1:1)
    var visualBrief = extractDynamicVisualPrompt(
      generatedContent,
      planContent,
      "A stylish 20s Korean female commuter with lightweight premium ANC headphones in warm golden autumn sunlight on a modern Seoul street"
    );
    Logger.log("동적 도출된 비주얼 프롬프트 (rv-00): " + visualBrief);
    generateAndSaveVisualAssets(rv00Folder, "00", visualBrief);

    // 6. 실제 캠페인 초판 콘텐츠 기반 25인 가상 페르소나 피드백 실시간 도출
    try {
      var fb01Folder = getCampaignSubFolder(["input", "fb-01"]);
      generateLivePersonaFeedbacks(campaignFolder, fb01Folder, "rv-00");
    } catch (fbGenErr) {
      Logger.log("25인 가상 페르소나 피드백 실시간 도출 예외: " + fbGenErr);
    }

    // 7. 구글 시트 실행 대시보드에 Step 2 완료 및 링크 기록
    recordStepResultToSheet("Step 3", "초판 마케팅 콘텐츠 양산 (rv-00)", "완료", rv00Folder.getUrl(), "구글 드라이브 폴더 열기 (rv-00)");

    ui.alert(
      "초판 마케팅 콘텐츠 양산 완료 (rv-00)",
      "초판 마케팅 카피, 대표 비주얼 이미지 3종 및 세로 숏폼 영상(00_shorts.mp4) 생성이 완료되었습니다.\n\n구글 시트의 [실행 대시보드] 표에서 바로가기 링크를 확인하십시오.",
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert("초판 콘텐츠 양산 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
}
