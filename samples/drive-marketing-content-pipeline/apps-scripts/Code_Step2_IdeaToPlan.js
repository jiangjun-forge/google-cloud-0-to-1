/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [Step 2] 자연어 아이디어 기반 기획서(PLAN) 및 콘텐츠 명세서(SPEC) 자동 도출 엔진 (Idea to PLAN & SPEC)
 */

function runIdeaToPlanConversion() {
  var ui = SpreadsheetApp.getUi();
  showProcessingToast("[Step 2] 기획서(PLAN) 및 명세서(SPEC) 자동 도출", 30);
  try {
    var campaignFolder = getCampaignFolder();

    // 1. 내장 시스템 지침 (Zero-Prompt No-Code) - PLAN 기획서 도출
    var planSystemInstruction =
      "당신은 전문 엔터프라이즈 브랜드 마케팅 전략가이자 크리에이티브 디렉터이다.\n" +
      "마케터가 제공하는 자연어 캠페인 아이디어를 정밀 분석하여, 완성도 높은 마케팅 캠페인 기획서(PLAN)를 작성하라.\n\n" +
      "필수 포함 섹션:\n" +
      "# [마케팅 캠페인 기획서] {캠페인명}\n" +
      "## 1. 캠페인 배경 및 핵심 목표\n" +
      "## 2. 타깃 페르소나 및 핵심 소구점 (USP)\n" +
      "## 3. 멀티 채널 콘텐츠 양산 요구 사항\n" +
      "## 4. 고객 피드백 수집 및 품질 검증 기준\n\n" +
      "엄격한 작성 규칙:\n" +
      "1. 이모지와 중간 점을 일절 사용하지 말고, 나열 시 반드시 쉼표(,)를 사용하십시오.\n" +
      "2. 모든 서술은 단호하고 격조 높은 문어체/평서문('-다' 체)으로 작성하십시오.\n" +
      "3. 한글 복합어는 철저하게 띄어 쓰십시오. (예: '마케팅 캠페인 기획서', '오프라인 매장', '의사 결정' 등)\n" +
      "4. 마케터가 바로 실무에 사용할 수 있을 만큼 구체적인 수치와 명확한 어조로 작성하십시오.\n" +
      "5. 분량 및 가독성: 청중 마케터가 1분 안에 직관적으로 파악할 수 있도록, 불필요한 장황한 서술을 전면 배제하고 A4 1~2페이지 내외의 핵심 불릿 포인트 중심으로 명쾌하고 컴팩트하게 작성하십시오.";

    // 2. 내장 시스템 지침 - SPEC 콘텐츠 제작 명세서 도출
    var specSystemInstruction =
      "당신은 엔터프라이즈 마케팅 콘텐츠 제작 총괄 리드이다.\n" +
      "마케팅 캠페인 기획서(PLAN)를 분석하여, 각 채널별 멀티 채널 콘텐츠 제작 명세서(SPEC) 구글 독스 문서를 정밀하게 작성하라.\n" +
      "마케터가 이 문서를 열어 수치(해상도, 비율, 영상 길이, 필수 포함 키워드 등)를 직접 편집할 수 있도록 명료한 규격 명세 형식으로 구성하라.\n\n" +
      "필수 포함 섹션:\n" +
      "# [멀티 채널 콘텐츠 제작 명세서] (SPEC)\n" +
      "## 1. 광고 카피라이팅 채널 규격\n" +
      "- 헤드카피 (3종, 20자 내외)\n" +
      "- 인스타그램 피드 및 카드뉴스 카피 (캡션 300자 내외, 필수 해시태그 5개)\n" +
      "- 네이버 블로그 기고문 (정보성 리뷰 1,500자 내외)\n" +
      "## 2. 모바일 세로 숏폼 영상 규격 (Shorts / Reels)\n" +
      "- 화면 비율: 세로 9:16 (해상도 1080x1920)\n" +
      "- 권장 러닝타임: 15초 내외 (최대 30초)\n" +
      "- 구성: 초반 3초 후킹(Hook), 문제 제기, 솔루션 제시, CTA\n" +
      "## 3. 대표 비주얼 이미지 3종 비율 규격\n" +
      "- 가로형 디스플레이 배너: 16:9 (1920x1080 권장, GDN 및 메인 웹 배너)\n" +
      "- 세로형 모바일 포스터: 9:16 (1080x1920 권장, 모바일 스토리 및 사이니지)\n" +
      "- 정방형 SNS 피드 이미지: 1:1 (1080x1080 권장, 인스타그램 피드)\n" +
      "## 4. 비주얼 연출 톤앤매너 및 네거티브 가이드라인\n" +
      "- 추천 조명, 색감, 인물 모델 스타일\n" +
      "- 지양해야 할 표현(과도한 텍스트 침범, 왜곡 등)\n\n" +
      "엄격한 작성 규칙:\n" +
      "1. 이모지와 중간 점을 일절 쓰지 말고 쉼표(,)를 사용하십시오.\n" +
      "2. 모든 서술은 단호하고 격조 높은 문어체/평서문('-다' 체)으로 작성하십시오.\n" +
      "3. 한글 복합어는 철저하게 띄어 쓰십시오.";

    // 3. 마케터에게 자연어 아이디어 입력받기 (input/아이디어 메모 구글 독스 연동)
    var inputFolder = getCampaignSubFolder(["input"]);
    var docIdea = readGoogleDoc(inputFolder, "아이디어 메모");
    var defaultIdea = docIdea ||
      ("2026 어텀 브리즈 무선 헤드폰 론칭 캠페인. 2534 출퇴근 직장인 타깃. " +
       "스마트 액티브 노이즈 캔슬링(98% 소음 차단), 180g 초경량 깃털 착용감, 50시간 배터리, 10만 원대 후반 가격. " +
       "인스타 피드 및 유튜브 쇼츠 콘티, 블로그 리뷰, 배너 프롬프트, 3,000대 사전 예약 조기 마감 목표.");

    var response = ui.prompt(
      "캠페인 기획 아이디어 발상",
      "추진하고자 하는 마케팅 아이디어나 신제품 특장점을 자유로운 말(자연어)로 입력하십시오.\n\n" +
      "[확인]을 누르면 기본 예시 아이디어로 기획서(PLAN) 및 콘텐츠 제작 명세서(SPEC) 구글 독스가 즉시 자동 생성됩니다:",
      ui.ButtonSet.OK_CANCEL
    );

    if (response.getSelectedButton() !== ui.Button.OK) {
      return;
    }

    var userIdea = response.getResponseText().trim();
    if (!userIdea) {
      userIdea = defaultIdea;
    }

    // 4. Gemini 호출: 1) 기획서(PLAN) 생성
    var userPrompt = "다음은 마케터가 제공한 캠페인 아이디어이다. 시스템 지침에 따라 정식 마케팅 캠페인 기획서(PLAN)를 완성하라:\n\n" + userIdea;
    var planContent = callGemini(planSystemInstruction, userPrompt);
    var planDocFile = saveGoogleDoc(campaignFolder, "PLAN", planContent);

    // 5. Gemini 호출: 2) 콘텐츠 제작 명세서(SPEC) 생성
    var specPrompt = "다음 작성된 마케팅 캠페인 기획서(PLAN)를 바탕으로, 각 채널별 상세 콘텐츠 제작 명세서(SPEC)를 완성하라:\n\n" + planContent;
    var specContent = callGemini(specSystemInstruction, specPrompt);
    var specDocFile = saveGoogleDoc(campaignFolder, "SPEC", specContent);

    // 6. 구글 시트 실행 대시보드에 기획서(PLAN) 및 콘텐츠 명세서(SPEC) 링크 각각 분리 기록
    recordStepResultToSheet("Step 2 (기획서)", "마케팅 캠페인 기획서(PLAN) 도출", "완료", planDocFile.getUrl(), "기획서(PLAN) 구글 독스 열기");
    recordStepResultToSheet("Step 2 (명세서)", "콘텐츠 제작 명세서(SPEC) 도출", "완료", specDocFile.getUrl(), "명세서(SPEC) 구글 독스 열기");

    ui.alert(
      "기획서(PLAN) 및 콘텐츠 명세서(SPEC) 생성 완료",
      "캠페인 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC) 구글 독스가 성공적으로 생성되었습니다.\n\n" +
      "1. 기획서(PLAN): " + planDocFile.getUrl() + "\n" +
      "2. 명세서(SPEC): " + specDocFile.getUrl() + "\n\n" +
      "마케터는 브라우저에서 SPEC 문서를 열어 이미지 비율, 숏폼 길이, 카피 채널 규격을 자유롭게 수정한 뒤 [Step 3]을 실행할 수 있습니다.\n\n" +
      "구글 시트의 [실행 대시보드] 표에서 각 문서의 바로가기 링크를 확인하십시오.",
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert("기획서 및 명세서 도출 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
}
