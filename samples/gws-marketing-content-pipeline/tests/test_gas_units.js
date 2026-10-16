/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline - Apps Script Modular Unit Tests
 * Node.js 런타임에서 apps-scripts/ 9대 코어 모듈의 실제 자바스크립트 함수들을
 * 직접 호출하여 상태 머신, 회차 루프, 대시보드 컬럼, 메뉴 매핑, JSON 파서를 0.05초 만에 전수 검증한다.
 */

const { describe, it } = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const { loadGasModules } = require("./load_gas_modules");
const { createGasMockEnvironment, MockFolder, MockFile, MockDocument } = require("./gas_mock");

describe("1. Code_Utils.js 단위 검증", () => {
  it("safeExtractJson: 마크다운 코드블록 및 앞뒤 설명 사족 텍스트 안전 제거", () => {
    const { context } = loadGasModules();
    const raw = "안녕하세요! 요청하신 JSON입니다.\n```json\n{\"campaign\": \"cp-ignite\", \"score\": 95}\n```\n추가 문의는 말씀해주세요.";
    const extracted = context.safeExtractJson(raw, false);
    assert.ok(extracted.startsWith("{"));
    assert.ok(extracted.endsWith("}"));
    const parsed = JSON.parse(extracted);
    assert.strictEqual(parsed.campaign, "cp-ignite");
    assert.strictEqual(parsed.score, 95);
  });

  it("safeParseJson: 깨진 텍스트 유입 시 fallback 기본값 반환", () => {
    const { context } = loadGasModules();
    const raw = "이 문장은 JSON 구조가 전혀 없는 일반 텍스트입니다.";
    const fallback = { fallback: true };
    const res = context.safeParseJson(raw, fallback, false);
    assert.deepStrictEqual(res, fallback);
  });

  it("formatDurationSec & formatTokenCount: 숫자 및 단위 포함 문자열 순수 숫자 정제", () => {
    const { context } = loadGasModules();
    assert.strictEqual(context.formatDurationSec("25초"), 25);
    assert.strictEqual(context.formatDurationSec(14500), 15); // ms -> sec
    assert.strictEqual(context.formatDurationSec(null), 0);

    assert.strictEqual(context.formatTokenCount("1,250 tokens"), 1250);
    assert.strictEqual(context.formatTokenCount(3500), 3500);
    assert.strictEqual(context.formatTokenCount("-"), 0);
  });

  it("applyDashboardColumnWidths: 칼럼 너비 규격 (A:100, B:50, C:250, D:150, E:50, F:100, G:400) 검증", () => {
    const { context, env } = loadGasModules();
    const sheet = env.SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    context.applyDashboardColumnWidths(sheet);

    assert.strictEqual(sheet.columnWidths[1], 100, "1열(A열: 실행 단계)은 100px이어야 함");
    assert.strictEqual(sheet.columnWidths[2], 50, "2열(B열: 진행 상태)은 50px이어야 함");
    assert.strictEqual(sheet.columnWidths[3], 250, "3열(C열: 산출물 링크)은 250px이어야 함");
    assert.strictEqual(sheet.columnWidths[4], 150, "4열(D열: 완료 시각)은 150px이어야 함");
    assert.strictEqual(sheet.columnWidths[5], 50, "5열(E열: 소요 시간)은 50px이어야 함");
    assert.strictEqual(sheet.columnWidths[6], 100, "6열(F열: 소모 토큰)은 100px이어야 함");
    assert.strictEqual(sheet.columnWidths[7], 400, "7열(G열: 상세 내용)은 400px이어야 함");
  });

  it("initDashboardSheet: '실행 내역' 탭 생성, 1행 고정 및 헤더 서식 검증", () => {
    const { context, env } = loadGasModules();
    context.initDashboardSheet();

    const sheet = env.SpreadsheetApp.getActiveSpreadsheet().getSheetByName("실행 내역");
    assert.ok(sheet, "'실행 내역' 시트 탭이 생성되어야 함");
    assert.strictEqual(sheet.frozenRows, 1, "1행이 고정(Freeze)되어야 함");

    // 헤더 값 검증
    assert.strictEqual(sheet.getCellValue(1, 1), "실행 단계");
    assert.strictEqual(sheet.getCellValue(1, 2), "진행 상태");
    assert.strictEqual(sheet.getCellValue(1, 3), "산출물 링크");
    assert.strictEqual(sheet.getCellValue(1, 4), "완료 시각");
    assert.strictEqual(sheet.getCellValue(1, 5), "소요 시간(초)");
    assert.strictEqual(sheet.getCellValue(1, 6), "소모 토큰");
    assert.strictEqual(sheet.getCellValue(1, 7), "상세 내용");

    // 1행 헤더 서식 검증 (셀 단위 스타일 확인)
    assert.strictEqual(sheet.getCellStyle(1, 1, "background"), "#f1f3f4", "헤더 배경색은 회색(#f1f3f4)이어야 함");
    assert.strictEqual(sheet.getCellStyle(1, 1, "horizontalAlignment"), "center", "헤더 수평 정렬은 center이어야 함");
    assert.strictEqual(sheet.getCellStyle(1, 1, "verticalAlignment"), "bottom", "헤더 수직 정렬은 bottom이어야 함");
    assert.strictEqual(sheet.getCellStyle(1, 1, "wrapStrategy"), "WRAP", "헤더 줄 바꿈은 WRAP이어야 함");
  });

  it("getDashboardSheet: 기존 '실행 로그' 탭이 있을 때 '실행 내역'으로 자동 이름 승계", () => {
    const env = createGasMockEnvironment();
    const ss = env.SpreadsheetApp.getActiveSpreadsheet();
    // 기존에 '실행 로그'라는 이름의 시트가 존재하는 시나리오
    ss.insertSheet("실행 로그", 0);
    const { context } = loadGasModules(env);

    const sheet = context.getDashboardSheet();
    assert.strictEqual(sheet.getName(), "실행 내역", "기존 '실행 로그' 탭이 '실행 내역'으로 자동 변경되어야 함");
  });

  it("initDashboardSheet: 기존 '소요 시간 (초)' 헤더가 있을 때 콤팩트한 '소요 시간(초)'로 자동 갱신", () => {
    const env = createGasMockEnvironment();
    const ss = env.SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.insertSheet("실행 내역", 0);
    // 기존 헤더 설정
    const headers = [["실행 단계", "진행 상태", "산출물 링크", "완료 시각", "소요 시간 (초)", "소모 토큰", "상세 내용"]];
    sheet.getRange("A1:G1").setValues(headers);

    const { context } = loadGasModules(env);
    context.initDashboardSheet();

    assert.strictEqual(sheet.getCellValue(1, 5), "소요 시간(초)", "공백 포함 헤더가 '소요 시간(초)'로 자동 보정되어야 함");
  });

  it("recordStepResultToSheet: 결과 행 2행부터 누적 추가 및 숫자 컬럼 서식 검증", () => {
    const { context, env } = loadGasModules();
    context.initDashboardSheet();

    context.recordStepResultToSheet(
      "Step 4",
      "초판 콘텐츠 생성",
      "완료",
      "https://docs.google.com/document/d/test_content",
      "초판 콘텐츠 세트 (rv-00)",
      25,
      1200,
      "정상 생성 완료"
    );

    const sheet = env.SpreadsheetApp.getActiveSpreadsheet().getSheetByName("실행 내역");
    assert.strictEqual(sheet.getLastRow(), 2, "결과는 2행에 기록되어야 함");
    assert.strictEqual(sheet.getCellValue(2, 1), "Step 4");
    assert.strictEqual(sheet.getCellValue(2, 2), "완료");
    assert.strictEqual(sheet.getCellValue(2, 5), 25, "소요 시간은 순수 숫자 25여야 함");
    assert.strictEqual(sheet.getCellValue(2, 6), 1200, "소모 토큰은 순수 숫자 1200이어야 함");
    assert.strictEqual(sheet.getCellValue(2, 7), "정상 생성 완료");

    // CoC 준수: GA4 및 원격 텔레메트리 호출 일절 미발생 검증
    const calls = env._internals.fetchCalls;
    const gaCalls = calls.filter(c => c.url.includes("google-analytics.com"));
    assert.strictEqual(gaCalls.length, 0, "CoC 준수: 단계 완료 시 외부 추적/GA4 호출이 일절 없어야 함");
  });

  it("CoC 및 프라이버시 준수: GA4 및 원격 추적 설정/코드 완전 배제 검증", () => {
    const { context } = loadGasModules();
    assert.strictEqual(context.CONFIG.GA4_MEASUREMENT_ID, undefined, "CONFIG에 GA4_MEASUREMENT_ID가 존재하지 않아야 함");
    assert.strictEqual(context.CONFIG.GA4_API_SECRET, undefined, "CONFIG에 GA4_API_SECRET이 존재하지 않아야 함");
    assert.strictEqual(typeof context.sendAnalyticsEvent, "undefined", "sendAnalyticsEvent 함수가 제거되어야 함");
    assert.strictEqual(typeof context.getAnonymousClientId, "undefined", "getAnonymousClientId 함수가 제거되어야 함");
  });

  it("detectLatestFeedbackRoundNum & detectLatestRevisionRoundNum: 폴더 파일 존재 유무에 따른 정확한 회차 계산", () => {
    const { context } = loadGasModules();
    const parentFolder = new MockFolder("parent");

    // 1. 하위 폴더 없는 경우: 피드백 기본값 0, 리비전 기본값 -1
    assert.strictEqual(context.detectLatestFeedbackRoundNum(parentFolder), 0);
    assert.strictEqual(context.detectLatestRevisionRoundNum(parentFolder), -1);

    // 2. 빈 폴더만 있는 경우: 산출물 없으므로 여전히 0과 -1
    const fb01 = parentFolder.createFolder("fb-01");
    const rv00 = parentFolder.createFolder("rv-00");
    assert.strictEqual(context.detectLatestFeedbackRoundNum(parentFolder), 0);
    assert.strictEqual(context.detectLatestRevisionRoundNum(parentFolder), -1);

    // 3. 파일이 있는 경우: 해당 회차 번호 반환 (20바이트 초과 유효 데이터)
    fb01.createFile("ai_persona_feedbacks.json", '{"personas": [{"id": "p01", "score": 90}]}', "application/json");
    rv00.createFile("campaign_content.gdoc", "content", "application/vnd.google-apps.document");
    assert.strictEqual(context.detectLatestFeedbackRoundNum(parentFolder), 1);
    assert.strictEqual(context.detectLatestRevisionRoundNum(parentFolder), 0);

    // 4. rv-01 추가 시 최신 리비전 1 반환
    const rv01 = parentFolder.createFolder("rv-01");
    rv01.createFile("campaign_content.gdoc", "revision 1", "application/vnd.google-apps.document");
    assert.strictEqual(context.detectLatestRevisionRoundNum(parentFolder), 1);
  });
});

describe("2. Code_Sidebar.js 상태 머신 및 N차 루프 전이 검증", () => {
  it("getPipelineStatus: 0단계(폴더 미구축) 상태 정확 판정", () => {
    const { context } = loadGasModules();
    const status = context.getPipelineStatus();
    assert.strictEqual(status.currentStep, 0);
    assert.strictEqual(status.folderUrl, "");
  });

  it("getPipelineStatus: 기획서 완료(Step 2) -> 다음 Step 3 (제작 명세서 생성) 상태 전이", () => {
    const env = createGasMockEnvironment();
    env.PropertiesService.getUserProperties().setProperty("GEMINI_API_KEY", "test_key");
    const root = env.DriveApp.getRootFolder();
    const campaignFolder = root.createFolder("cp-test-campaign");
    env.PropertiesService.getScriptProperties().setProperty("CAMPAIGN_FOLDER_ID", campaignFolder.getId());

    // 아이디어 메모와 PLAN 문서 생성
    campaignFolder.createFile("아이디어 메모", "아이디어", "application/vnd.google-apps.document");
    campaignFolder.createFile("PLAN", "기획서 전문", "application/vnd.google-apps.document");

    const { context } = loadGasModules(env);
    const status = context.getPipelineStatus(true);
    assert.strictEqual(status.currentStep, 3, "PLAN이 있으면 다음 단계는 Step 3(SPEC 생성)이어야 함");
    assert.ok(status.planDocUrl);
    assert.strictEqual(status.specDocUrl, "");
  });

  it("getPipelineStatus: 초판(rv-00) 완료 시 -> Step 6 (fb-01 다면 평가) 상태 전이", () => {
    const env = createGasMockEnvironment();
    env.PropertiesService.getUserProperties().setProperty("GEMINI_API_KEY", "test_key");
    const root = env.DriveApp.getRootFolder();
    const campaignFolder = root.createFolder("cp-test-campaign");
    env.PropertiesService.getScriptProperties().setProperty("CAMPAIGN_FOLDER_ID", campaignFolder.getId());

    campaignFolder.createFile("아이디어 메모", "아이디어", "application/vnd.google-apps.document");
    campaignFolder.createFile("PLAN", "기획서", "application/vnd.google-apps.document");
    campaignFolder.createFile("SPEC", "명세서", "application/vnd.google-apps.document");
    campaignFolder.createFile("ai_personas.json", "[]", "application/json");

    const outFolder = campaignFolder.createFolder("output");
    const rv00 = outFolder.createFolder("rv-00");
    rv00.createFile("campaign_content", "초판", "application/vnd.google-apps.document");

    const { context } = loadGasModules(env);
    const status = context.getPipelineStatus(true);
    assert.strictEqual(status.currentStep, 6, "rv-00 완료 시 다음 단계는 Step 6이어야 함");
    assert.strictEqual(status.activeFbTag, "fb-01");
    assert.strictEqual(status.nextRvTag, "rv-01");
    assert.strictEqual(status.latestRv, "rv-00");
  });

  it("getPipelineStatus: [N차 무한 루프 핵심] 개정본(rv-01) 완료 시 Step 9에 고착되지 않고 Step 6(fb-02)로 정상 전이", () => {
    const env = createGasMockEnvironment();
    env.PropertiesService.getUserProperties().setProperty("GEMINI_API_KEY", "test_key");
    const root = env.DriveApp.getRootFolder();
    const campaignFolder = root.createFolder("cp-test-campaign");
    env.PropertiesService.getScriptProperties().setProperty("CAMPAIGN_FOLDER_ID", campaignFolder.getId());

    campaignFolder.createFile("아이디어 메모", "아이디어", "application/vnd.google-apps.document");
    campaignFolder.createFile("PLAN", "기획서", "application/vnd.google-apps.document");
    campaignFolder.createFile("SPEC", "명세서", "application/vnd.google-apps.document");
    campaignFolder.createFile("ai_personas.json", "[]", "application/json");

    // 1차 피드백 폴더 (fb-01) 내 모든 산출물 존재
    const inFolder = campaignFolder.createFolder("input");
    const fb01 = inFolder.createFolder("fb-01");
    fb01.createFile("ai_persona_feedbacks.json", "[]", "application/json");
    fb01.createFile("feedback_summary.gdoc", "요약 보고서", "application/vnd.google-apps.document");
    fb01.createFile("marketer_directive.gdoc", "보정 지침서", "application/vnd.google-apps.document");

    // 1차 개정본 폴더 (rv-01) 및 초판 (rv-00) 완성
    const outFolder = campaignFolder.createFolder("output");
    const rv00 = outFolder.createFolder("rv-00");
    rv00.createFile("campaign_content", "초판", "application/vnd.google-apps.document");
    const rv01 = outFolder.createFolder("rv-01");
    rv01.createFile("campaign_content", "1차 개정본", "application/vnd.google-apps.document");

    const { context } = loadGasModules(env);
    const status = context.getPipelineStatus(true);

    // 검증: rv-01 완료 시 대상 피드백 차수는 반드시 fb-02이어야 하며, 단계는 Step 6이어야 함!
    assert.strictEqual(status.latestRvNum, 1, "최신 리비전 번호는 1(rv-01)이어야 함");
    assert.strictEqual(status.activeFbTag, "fb-02", "다음 활성 피드백 차수는 fb-02이어야 함");
    assert.strictEqual(status.nextRvTag, "rv-02", "차기 개정본 태그는 rv-02이어야 함");
    assert.strictEqual(status.currentStep, 6, "rv-01 제작 완료 후에는 Step 6(fb-02 다면 평가)으로 순환 전이되어야 함");
  });

  it("getDeterministicFallback: '지금 뭐 해야 돼?' 질의 시 rv-01 완료 상태에서 Step 6(fb-02) 정확 안내", () => {
    const { context } = loadGasModules();
    const status = {
      hasApiKey: true,
      folderUrl: "https://drive.google.com/test",
      ideaDocUrl: "https://docs.google.com/idea",
      planDocUrl: "https://docs.google.com/plan",
      specDocUrl: "https://docs.google.com/spec",
      personaUrl: "https://drive.google.com/personas",
      contentDocUrl: "https://docs.google.com/content",
      latestRv: "rv-01",
      latestRvNum: 1,
      activeFbTag: "fb-02",
      activeRvTag: "rv-01",
      nextRvTag: "rv-02",
      currentStep: 6,
      feedbackJsonUrl: "",
      summaryDocUrl: "",
      directiveDocUrl: ""
    };

    const res = context.getDeterministicFallback("지금 뭐 해야 돼?", status);
    assert.ok(res.success);
    assert.strictEqual(res.action, "promptAndRunJudgeEvaluation");
    assert.ok(res.actionLabel.includes("fb-02"), "액션 레이블에 fb-02가 명시되어야 함");
    assert.ok(res.reply.includes("rv-01"), "답변에 이전 완료된 rv-01이 언급되어야 함");
    assert.ok(res.reply.includes("fb-02"), "답변에 다음 차수 fb-02 다면 평가가 명시되어야 함");
  });

  it("getDeterministicFallback: 링크 조회 의도 인터셉트 ('기획서 어디 있어?', '실행 내역 열어줘')", () => {
    const { context } = loadGasModules();
    const status = {
      hasApiKey: true,
      folderUrl: "https://drive.google.com/test",
      planDocUrl: "https://docs.google.com/document/d/plan123/edit",
      contentDocUrl: "https://docs.google.com/document/d/content123/edit"
    };

    const planRes = context.getDeterministicFallback("기획서 어디 있어?", status);
    assert.ok(planRes.success);
    assert.ok(planRes.actionBtnHtml.includes(status.planDocUrl), "버튼 HTML에 기획서 링크가 포함되어야 함");

    const sheetRes = context.getDeterministicFallback("실행 내역 열어줘", status);
    assert.ok(sheetRes.success);
    assert.strictEqual(sheetRes.action, "openDashboardSheet");
  });

  it("getPipelineSidebarHtml & showPipelineSidebar: 사이드바 HTML 내 외부 추적 스크립트 배제 및 오픈 시 텔레메트리 미발생 검증", () => {
    const { context, env } = loadGasModules();
    const html = context.getPipelineSidebarHtml();

    assert.ok(!html.includes("googletagmanager"), "사이드바 HTML에 googletagmanager 스크립트가 일절 없어야 함");
    assert.ok(!html.includes("gtag"), "사이드바 HTML에 gtag 호출이 일절 없어야 함");

    // showPipelineSidebar 호출 시 외부 텔레메트리 fetch 미발생 검증
    context.showPipelineSidebar();
    const calls = env._internals.fetchCalls;
    const gaCalls = calls.filter(c => c.url.includes("google-analytics.com"));
    assert.strictEqual(gaCalls.length, 0, "showPipelineSidebar 호출 시 외부 GA4/텔레메트리 호출이 일절 없어야 함");
  });
});

describe("3. Code_Menu.js 메뉴 매핑 무결성 검증", () => {
  it("onOpen: 메뉴 항목에 등록된 모든 Apps Script 함수가 실제 스코프에 존재하는지 전수 검증", () => {
    const env = createGasMockEnvironment();
    let registeredItems = [];

    // 메뉴 빌더 인터셉트
    env.SpreadsheetApp.getUi = () => ({
      createMenu: (menuName) => {
        const builder = {
          addItem: (caption, funcName) => {
            registeredItems.push({ caption, funcName });
            return builder;
          },
          addSeparator: () => builder,
          addToUi: () => {}
        };
        return builder;
      }
    });

    const { context } = loadGasModules(env);
    context.onOpen();

    assert.ok(registeredItems.length > 0, "상단 메뉴 항목이 1개 이상 등록되어야 함");

    // 등록된 모든 함수명이 context에 실제로 존재하는 함수인지 전수 검증!
    for (const item of registeredItems) {
      assert.strictEqual(
        typeof context[item.funcName],
        "function",
        `메뉴 항목 '${item.caption}'에 연결된 함수 '${item.funcName}'이(가) 실제로 정의되어 있어야 함`
      );
    }
  });
});

describe("4. Code_Utils.js 슬러그 생성 검증", () => {
  it("generateCampaignSlug: 한글 및 특수문자 폴더명 안전 영문 슬러그 변환", () => {
    const { context } = loadGasModules();
    const slug1 = context.generateCampaignSlug("2026 가을 오텀 브리즈 캠페인");
    assert.ok(slug1.includes("2026") || slug1.includes("autumn"), `슬러그에 의미론적 키워드 반영: ${slug1}`);
    assert.ok(!/[ㄱ-ㅎㅏ-ㅣ가-힣]/.test(slug1), "슬러그에 한글이 포함되지 않아야 함");

    const slug2 = context.generateCampaignSlug("cp-ignite-spring");
    assert.strictEqual(slug2, "cp-ignite-spring", "영문 슬러그는 원형이 유지되어야 함");
  });
});

describe("5. 번들 파일(bundle_apps_script.js, bootstrap.js) 구문 및 무결성 검증", () => {
  const rootDir = path.resolve(__dirname, "..");

  it("bundle_apps_script.js: 자바스크립트 문법 오류(SyntaxError) 제로 검증", () => {
    const bundlePath = path.join(rootDir, "bundle_apps_script.js");
    assert.ok(fs.existsSync(bundlePath), "bundle_apps_script.js 파일이 존재해야 함");
    const code = fs.readFileSync(bundlePath, "utf8");
    assert.doesNotThrow(() => {
      new vm.Script(code, { filename: "bundle_apps_script.js" });
    }, "bundle_apps_script.js에 문법 오류가 없어야 함");
  });

  it("bootstrap.js: 자바스크립트 문법 오류(SyntaxError) 제로 검증", () => {
    const bootstrapPath = path.join(rootDir, "bootstrap.js");
    assert.ok(fs.existsSync(bootstrapPath), "bootstrap.js 파일이 존재해야 함");
    const code = fs.readFileSync(bootstrapPath, "utf8");
    assert.doesNotThrow(() => {
      new vm.Script(code, { filename: "bootstrap.js" });
    }, "bootstrap.js에 문법 오류가 없어야 함");
  });
});

describe("6. 미디어 제작 스펙 자연어 동적 컴파일 및 독스 보고서 헤더 검증", () => {
  it("compileMediaSpecFromDocs: '영상 제외' 자연어 지침 시 includeVideo false 및 사유 도출 검증", () => {
    const { context } = loadGasModules();
    const mockSpec = "# 제작 명세서\n이번 캠페인은 숏폼 영상 제작 제외하고 1:1 피드와 16:9 배너만 제작함.";
    const spec = context.compileMediaSpecFromDocs(mockSpec, "00");

    assert.strictEqual(spec.includeVideo, false, "영상 제외 지침 시 includeVideo는 false이어야 함");
    assert.ok(spec.reason.includes("제외") || spec.reason.includes("반영"), "사유에 제외 지침이 반영되어야 함");
    assert.ok(spec.images.length >= 1, "요청된 이미지는 포함되어야 함");
  });

  it("compileMediaSpecFromDocs: '배너 제외' 지침 시 16:9 배너 미디어 목록에서 배제 검증", () => {
    const { context } = loadGasModules();
    const mockSpec = "# 제작 명세서\n가로 배너 제외하고 모바일 포스터(9:16)와 인스타 피드(1:1)만 진행.";
    const spec = context.compileMediaSpecFromDocs(mockSpec, "01");

    const hasBanner = spec.images.some(img => img.key.includes("banner") || img.ratio === "16:9");
    assert.strictEqual(hasBanner, false, "배너 제외 지침 시 16:9 배너는 images 목록에 없어야 함");
    const hasPoster = spec.images.some(img => img.key.includes("poster") || img.ratio === "9:16");
    assert.strictEqual(hasPoster, true, "포스터는 정상 포함되어야 함");
  });

  it("buildMediaSpecReportHeader: 독스 최상단에 수록될 미디어 산출물 현황 헤더 블록 포맷 검증", () => {
    const { context } = loadGasModules();
    const spec = {
      revision: "rv-00",
      includeVideo: false,
      reason: "마케터 명세서상 숏폼 비디오 제외 지침 반영",
      images: [
        { key: "sns_1x1", name: "00_sns_1x1.png", ratio: "1:1", label: "정방형 SNS 피드" }
      ]
    };
    const header = context.buildMediaSpecReportHeader(spec);

    assert.ok(header.includes("[제작 명세서(SPEC) 반영 미디어 산출물 현황]"), "헤더 타이틀 포함 필수");
    assert.ok(header.includes("숏폼 비디오") && header.includes("제외"), "비디오 제외 명시 필수");
    assert.ok(header.includes("00_sns_1x1.png"), "생성 이미지 파일명 포함 필수");
    assert.ok(header.includes("---"), "구분선 포함 필수");
  });

  it("inspectRevisionFolder: media_specs.json에 영상 제외 설정 시 영상 없어도 isComplete true 판정", () => {
    const { context } = loadGasModules();
    const mediaSpec = {
      revision: "rv-00",
      includeVideo: false,
      images: [
        { key: "banner_16x9", name: "00_banner_16x9.png", ratio: "16:9" },
        { key: "poster_9x16", name: "00_poster_9x16.png", ratio: "9:16" },
        { key: "sns_1x1", name: "00_sns_1x1.png", ratio: "1:1" }
      ]
    };

    // 가상 모킹 폴더
    const mockFiles = [
      { getName: () => "campaign_content", getBlob: () => ({ getDataAsString: () => "" }) },
      { getName: () => "media_specs.json", getBlob: () => ({ getDataAsString: () => JSON.stringify(mediaSpec) }) },
      { getName: () => "00_banner_16x9.png", getBlob: () => ({ getDataAsString: () => "" }) },
      { getName: () => "00_poster_9x16.png", getBlob: () => ({ getDataAsString: () => "" }) },
      { getName: () => "00_sns_1x1.png", getBlob: () => ({ getDataAsString: () => "" }) }
      // 00_shorts.mp4는 없음!
    ];

    const mockFolder = {
      getFiles: () => {
        let idx = 0;
        return {
          hasNext: () => idx < mockFiles.length,
          next: () => mockFiles[idx++]
        };
      },
      getFilesByName: (name) => {
        const matches = mockFiles.filter(f => f.getName() === name);
        let idx = 0;
        return {
          hasNext: () => idx < matches.length,
          next: () => matches[idx++]
        };
      }
    };

    const status = context.inspectRevisionFolder(mockFolder, "00");
    assert.strictEqual(status.isComplete, true, "영상 제외 스펙 시 비디오 파일이 없어도 완비(isComplete: true) 판정이어야 함");
  });
});
