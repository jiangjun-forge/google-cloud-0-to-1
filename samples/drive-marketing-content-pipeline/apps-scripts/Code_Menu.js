/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 3] Google Sheets 커스텀 메뉴 및 UI 대화상자 (Spreadsheet UI & Menu)
 */

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu(">> 마케팅 콘텐츠 파이프라인 <<")
    .addItem("[0. 타깃 AI 페르소나 패널 맞춤 재설정 (선택 사항)]", "setCustomPersonasPrompt")
    .addSeparator()
    .addItem("[Step 1] Google Drive 작업 공간 및 25인 페르소나 자동 생성", "createWorkspaceFolderTree")
    .addItem("[Step 2] 아이디어 기반 기획서(PLAN) 및 콘텐츠 명세서(SPEC) 자동 도출", "runIdeaToPlanConversion")
    .addItem("[Step 3] 기획서 및 명세서 기반 초판 마케팅 콘텐츠 양산 (rv-00)", "runInitialAssetGeneration")
    .addSeparator()
    .addItem("[Step 4] 고객 VoC 수집용 Google Forms 자동 생성 (이미지/비디오 업로드)", "createAndLinkGoogleForm")
    .addItem("[Step 5] 25인 AI 페르소나 1차 다면 평가 및 t-SNE 지형도 자동 렌더링 (fb-01)", "runJudgeEvaluationRound1")
    .addItem("[Step 6] 마케터 피드백 검토 및 최종 의사 결정 (Human-in-the-loop)", "runMarketerDecisionPrompt")
    .addItem("[Step 7] 다면 평가 피드백 기반 1차 마케팅 콘텐츠 반자율 보정 (rv-01)", "runReviseAssetsRound1")
    .addSeparator()
    .addItem("[Step 8] 2차 다면 평가 및 t-SNE 지형도 갱신 (fb-02)", "runJudgeEvaluationRound2")
    .addItem("[Step 9] 2차 마케팅 콘텐츠 반자율 보정 완결 (rv-02)", "runReviseAssetsRound2")
    .addToUi();
}

/**
 * 타깃 AI 페르소나 25인 패널 맞춤 재설정 UI 프롬프트 (Gemini 생성 또는 Hugging Face 동기화)
 */
function setCustomPersonasPrompt() {
  var ui = SpreadsheetApp.getUi();
  var response = ui.prompt(
    "타깃 AI 페르소나 25인 패널 맞춤 재설정",
    "새로 생성하고자 하는 타깃 페르소나 기준을 자유롭게 입력하십시오:\n" +
    "(예: '일본 20대 여성 뷰티 인플루언서 및 일반 소비자', '미국 실리콘밸리 30대 B2B SaaS 바이어', '한국 4050 골프 입문자')\n\n" +
    "* Hugging Face 연동: 'hf:nvidia/Nemotron-Personas-Korea' 형식으로 입력 시 공개 데이터셋에서 실시간 동기화합니다.",
    ui.ButtonSet.OK_CANCEL
  );

  if (response.getSelectedButton() !== ui.Button.OK) {
    return;
  }

  var criteria = response.getResponseText().trim();
  if (!criteria) {
    ui.alert("입력 취소", "기준이 입력되지 않아 기존 25인 페르소나 패널을 유지합니다.", ui.ButtonSet.OK);
    return;
  }

  try {
    var campaignFolder = getCampaignFolder();
    var campaignCode = getCampaignCode();
    var generatedJson = "";

    // 1. Hugging Face Server API 연동 여부 판별
    if (criteria.indexOf("hf:") === 0) {
      var datasetRepo = criteria.replace("hf:", "").trim();
      var hfUrl = "https://datasets-server.huggingface.co/rows?dataset=" + encodeURIComponent(datasetRepo) + "&config=default&split=train&offset=0&limit=25";
      var hfResp = UrlFetchApp.fetch(hfUrl, { muteHttpExceptions: true });
      if (hfResp.getResponseCode() === 200) {
        var hfData = JSON.parse(hfResp.getContentText());
        var rawRowsText = JSON.stringify(hfData.rows || hfData, null, 2);
        var normInstruction =
          "당신은 데이터 엔지니어이다. 제공된 Hugging Face 원본 데이터로부터 25인의 슬림 페르소나 JSON 배열을 추출 및 정규화하라.\n" +
          "반드시 id(p01~p25), name, age, gender, category(전문 마케터 또는 일반 소비자), occupation, perspective(핵심 관점 및 관심사 1줄) 7개 필드만 포함하는 JSON 배열로 출력하라.";
        generatedJson = callGemini(normInstruction, rawRowsText);
      } else {
        throw new Error("Hugging Face API 호출 실패 (응답 코드: " + hfResp.getResponseCode() + ")");
      }
    } else {
      // 2. Gemini 기반 자연어 타깃 페르소나 25인 즉시 합성
      var systemInstruction =
        "당신은 글로벌 소비자 리서치 및 엔터프라이즈 마케팅 페르소나 엔지니어링 인공 지능이다.\n" +
        "사용자가 지정한 타깃 기준에 맞추어 마케팅 캠페인 콘텐츠와 광고 소재를 다면 평가할 25인의 슬림 AI 페르소나 패널을 도출하라.\n\n" +
        "필수 규칙:\n" +
        "1. 총 25인 구성: 전문 마케터 12인 + 일반 소비자 13인으로 안배하십시오.\n" +
        "2. 반드시 다음 7개 필드만 엄격히 포함하는 순수 JSON 객체로 출력하십시오:\n" +
        "{\n" +
        "  \"metadata\": { \"description\": \"타깃 맞춤 AI 페르소나 패널\", \"total\": 25 },\n" +
        "  \"personas\": [\n" +
        "    {\n" +
        "      \"id\": \"p01\",\n" +
        "      \"name\": \"이름\",\n" +
        "      \"age\": 30,\n" +
        "      \"gender\": \"남성/여성\",\n" +
        "      \"category\": \"전문 마케터 또는 일반 소비자\",\n" +
        "      \"occupation\": \"직업\",\n" +
        "      \"perspective\": \"핵심 성향 및 주요 관심사 요약 (1줄)\"\n" +
        "    }\n" +
        "  ]\n" +
        "}\n" +
        "3. 코드 블록(```json) 없이 유효한 JSON만 반환하십시오.\n" +
        "4. 불필요하게 긴 텍스트나 중복 필드를 배제하여 토큰 효율을 극대화하십시오.";

      var userPrompt = "타깃 페르소나 기준: " + criteria + "\n\n위 기준에 부합하는 정밀하고 다양한 25인 슬림 페르소나 JSON을 생성하라.";
      generatedJson = callGemini(systemInstruction, userPrompt);
    }

    if (generatedJson) {
      var cleanJson = generatedJson.replace(/^```json\s*/i, "").replace(/^```\s*/, "").replace(/\s*```$/, "").trim();
      var parsed = JSON.parse(cleanJson);
      var formatted = JSON.stringify(parsed, null, 2);
      var inputFolder = getCampaignSubFolder(["input"]);
      saveTextFile(inputFolder, "ai_personas.json", formatted);

      ui.alert(
        "페르소나 패널 재설정 완료",
        "지정한 기준('" + criteria + "')에 맞추어 25인 맞춤 AI 페르소나 패널 데이터가 성공적으로 갱신되었습니다.\n(저장 경로: " + campaignCode + "/input/ai_personas.json)",
        ui.ButtonSet.OK
      );
    }
  } catch (err) {
    ui.alert("페르소나 재설정 중 오류 발생", err.toString(), ui.ButtonSet.OK);
  }
}
