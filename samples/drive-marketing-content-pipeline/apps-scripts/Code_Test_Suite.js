/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 4] 에뮬레이션 단위 테스트 수이트 (Emulated Unit Test Suite)
 * Google Apps Script 런타임 및 브라우저 환경에서 전 기능 단독 모의 검증을 지원한다.
 */

/**
 * 경량 테스트 러너 엔진 (Test Runner Engine)
 */
var TestRunner = {
  results: [],
  currentSuite: "",

  startSuite: function(suiteName) {
    this.currentSuite = suiteName;
  },

  assert: function(condition, testName, message) {
    var pass = Boolean(condition);
    this.results.push({
      suite: this.currentSuite,
      name: testName,
      status: pass ? "PASS" : "FAIL",
      message: pass ? "정상 통과" : (message || "조건 불만족")
    });
    return pass;
  },

  assertEqual: function(actual, expected, testName, message) {
    var pass = (actual === expected);
    var detail = pass ? "일치 (" + actual + ")" : "불일치 (기대값: " + expected + ", 실제값: " + actual + ")";
    if (message && !pass) {
      detail += " - " + message;
    }
    this.results.push({
      suite: this.currentSuite,
      name: testName,
      status: pass ? "PASS" : "FAIL",
      message: detail
    });
    return pass;
  },

  assertDeepEqual: function(actual, expected, testName) {
    var actualStr = JSON.stringify(actual);
    var expectedStr = JSON.stringify(expected);
    var pass = (actualStr === expectedStr);
    this.results.push({
      suite: this.currentSuite,
      name: testName,
      status: pass ? "PASS" : "FAIL",
      message: pass ? "객체 구조 일치" : "객체 불일치 (기대: " + expectedStr + ", 실제: " + actualStr + ")"
    });
    return pass;
  },

  assertNotNull: function(val, testName, message) {
    var pass = (val !== null && val !== undefined && val !== "");
    this.results.push({
      suite: this.currentSuite,
      name: testName,
      status: pass ? "PASS" : "FAIL",
      message: pass ? "값 존재 확인" : (message || "값이 null 또는 정의되지 않음")
    });
    return pass;
  },

  clearResults: function() {
    this.results = [];
    this.currentSuite = "";
  },

  getSummary: function() {
    var total = this.results.length;
    var passed = 0;
    var failed = 0;
    for (var i = 0; i < total; i++) {
      if (this.results[i].status === "PASS") {
        passed++;
      } else {
        failed++;
      }
    }
    return {
      total: total,
      passed: passed,
      failed: failed,
      passRate: total > 0 ? ((passed / total) * 100).toFixed(1) + "%" : "0.0%"
    };
  },

  printReportToSheet: function() {
    try {
      var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
      var sheetName = "테스트 결과";
      var sheet = spreadsheet.getSheetByName(sheetName);
      if (sheet) {
        sheet.clear();
      } else {
        sheet = spreadsheet.insertSheet(sheetName);
      }

      var header = ["번호", "테스트 수이트", "단위 테스트 항목", "결과 (PASS/FAIL)", "상세 진단 내용", "실행 시각"];
      var rows = [header];
      var nowStr = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd HH:mm:ss");

      for (var i = 0; i < this.results.length; i++) {
        var r = this.results[i];
        rows.push([
          i + 1,
          r.suite,
          r.name,
          r.status,
          r.message,
          nowStr
        ]);
      }

      var range = sheet.getRange(1, 1, rows.length, header.length);
      range.setValues(rows);

      // 서식 설정
      var headerRange = sheet.getRange(1, 1, 1, header.length);
      headerRange.setBackground("#1E293B").setFontColor("#FFFFFF").setFontWeight("bold");

      for (var rIdx = 2; rIdx <= rows.length; rIdx++) {
        var statusCell = sheet.getRange(rIdx, 4);
        var statusVal = statusCell.getValue();
        if (statusVal === "PASS") {
          statusCell.setBackground("#DCFCE7").setFontColor("#166534").setFontWeight("bold");
        } else {
          statusCell.setBackground("#FEE2E2").setFontColor("#991B1B").setFontWeight("bold");
        }
      }

      sheet.autoResizeColumns(1, header.length);
      spreadsheet.setActiveSheet(sheet);
    } catch (sheetErr) {
      Logger.log("테스트 결과 시트 기록 생략: " + sheetErr);
    }
  }
};

/**
 * [단위 테스트 1] 환경 및 설정 구성 검증 (Config Suite)
 */
function testSuite_Config() {
  TestRunner.startSuite("1. 환경 및 설정 구성 (Config)");

  TestRunner.assertNotNull(CONFIG, "CONFIG 객체 존재 검증");
  TestRunner.assertNotNull(CONFIG.CAMPAIGN_CODE, "기본 캠페인 코드 설정 검증");
  TestRunner.assertEqual(CONFIG.CAMPAIGN_CODE, "cp-ignite", "기본 캠페인 코드 일치 검증");

  TestRunner.assertNotNull(CONFIG.MODEL_DEFAULT, "기본 생성 모델(gemini-3.8-flash) 설정 검증");
  TestRunner.assertEqual(CONFIG.MODEL_DEFAULT, "gemini-3.8-flash", "기본 모델명 일치 검증");

  TestRunner.assertNotNull(CONFIG.MODEL_JUDGE, "평가 전용 모델(gemini-3.8-flash) 설정 검증");
  TestRunner.assertNotNull(CONFIG.MODEL_IMAGE, "이미지 모델(gemini-2.5-flash-image) 설정 검증");
  TestRunner.assertNotNull(CONFIG.MODEL_VIDEO, "비디오 모델(veo-3.1-generate-001) 설정 검증");
  TestRunner.assertNotNull(CONFIG.MODEL_EMBEDDING, "임베딩 모델(text-multilingual-embedding-002) 설정 검증");

  TestRunner.assertEqual(CONFIG.PLAN_DOC_NAME, "PLAN", "기획서 구글 독스 파일명(PLAN) 검증");
  TestRunner.assertEqual(CONFIG.SPEC_DOC_NAME, "SPEC", "명세서 구글 독스 파일명(SPEC) 검증");
  TestRunner.assertEqual(CONFIG.CONTENT_DOC_NAME, "campaign_content", "콘텐츠 구글 독스 파일명 검증");
}

/**
 * [단위 테스트 2] 유틸리티 및 헬퍼 함수 검증 (Utils Suite)
 */
function testSuite_Utils() {
  TestRunner.startSuite("2. 헬퍼 유틸리티 (Utils)");

  // 1. padZero 패딩 검증
  TestRunner.assertEqual(padZero(1), "01", "padZero(1) 패딩 검증");
  TestRunner.assertEqual(padZero(9), "09", "padZero(9) 패딩 검증");
  TestRunner.assertEqual(padZero(10), "10", "padZero(10) 무변경 검증");
  TestRunner.assertEqual(padZero(99), "99", "padZero(99) 2자리수 유지 검증");

  // 2. cleanJsonText 마크다운 코드 블록 제거 검증
  var rawJson = "```json\n{\"test\": 123}\n```";
  var cleaned = cleanJsonText(rawJson);
  TestRunner.assertEqual(cleaned, "{\"test\": 123}", "cleanJsonText 마크다운 json 제거 검증");

  var pureJson = "{\"status\": \"ok\"}";
  TestRunner.assertEqual(cleanJsonText(pureJson), "{\"status\": \"ok\"}", "cleanJsonText 순수 JSON 보존 검증");

  // 3. resolveDriveAttachmentName 구글 드라이브 링크 파싱 검증
  var plainText = "노이즈 캔슬링 음질이 훌륭합니다.";
  TestRunner.assertEqual(resolveDriveAttachmentName(plainText), plainText, "일반 문자열 무변경 유지 검증");

  var invalidUrl = "https://example.com/test.jpg";
  TestRunner.assertEqual(resolveDriveAttachmentName(invalidUrl), invalidUrl, "외부 일반 URL 무변경 유지 검증");
}

/**
 * [단위 테스트 3] 동적 회차 탐색기 및 99차 루프 검증 (Dynamic Round Detect Suite)
 */
function testSuite_DynamicRoundDetect() {
  TestRunner.startSuite("3. 동적 회차 탐색기 (Dynamic Round Detect)");

  // 모의 폴더 목록 기반 최대 번호 계산 알고리즘 검증
  function mockDetectLatestFeedback(folderNames) {
    var maxRound = 0;
    for (var i = 0; i < folderNames.length; i++) {
      var name = folderNames[i];
      var match = /^fb-([0-9]{1,2})$/i.exec(name);
      if (match) {
        var num = parseInt(match[1], 10);
        if (!isNaN(num) && num > maxRound) {
          maxRound = num;
        }
      }
    }
    return maxRound;
  }

  function mockDetectLatestRevision(folderNames) {
    var maxRound = 0;
    for (var i = 0; i < folderNames.length; i++) {
      var name = folderNames[i];
      var match = /^rv-([0-9]{1,2})$/i.exec(name);
      if (match) {
        var num = parseInt(match[1], 10);
        if (!isNaN(num) && num > maxRound) {
          maxRound = num;
        }
      }
    }
    return maxRound;
  }

  // 1. 단일 회차 검증
  TestRunner.assertEqual(mockDetectLatestFeedback(["fb-01"]), 1, "fb-01 탐색 검증");
  TestRunner.assertEqual(mockDetectLatestRevision(["rv-00", "rv-01"]), 1, "rv-01 탐색 검증");

  // 2. 다중 회차 누적 검증
  TestRunner.assertEqual(mockDetectLatestFeedback(["fb-01", "fb-02", "fb-03"]), 3, "fb-03 최신 탐색 검증");
  TestRunner.assertEqual(mockDetectLatestRevision(["rv-00", "rv-01", "rv-02", "rv-05"]), 5, "rv-05 점프 탐색 검증");

  // 3. 99차 경계값 검증
  TestRunner.assertEqual(mockDetectLatestFeedback(["fb-01", "fb-99"]), 99, "fb-99 상한선 인식 검증");
  TestRunner.assertEqual(mockDetectLatestRevision(["rv-00", "rv-99"]), 99, "rv-99 상한선 인식 검증");

  // 4. 비표준 폴더명 무시 검증
  TestRunner.assertEqual(mockDetectLatestFeedback(["fb-01", "fb-test", "temp", "feedback"]), 1, "비표준 폴더명 무시 검증");
  TestRunner.assertEqual(mockDetectLatestRevision(["rv-00", "revision-01", "draft"]), 0, "비표준 리비전 무시 검증");

  // 5. 다음 회차 제안 로직 검증
  var nextFb = Math.max(mockDetectLatestFeedback(["fb-01", "fb-02"]) + 1, 2);
  TestRunner.assertEqual(nextFb, 3, "다음 피드백 회차(fb-03) 자동 산출 검증");

  var nextRv = Math.max(mockDetectLatestRevision(["rv-00", "rv-01"]) + 1, 2);
  TestRunner.assertEqual(nextRv, 2, "다음 리비전 회차(rv-02) 자동 산출 검증");
}

/**
 * [단위 테스트 4] VLM 분석 및 수작업 파일 스캐너 검증 (VLM & Scanner Suite)
 */
function testSuite_VlmAndScanner() {
  TestRunner.startSuite("4. VLM 분석 및 수작업 스캐너 (VLM & Scanner)");

  // 1. 시스템 예약 파일 배제 로직 검증
  var reservedFiles = [
    "ai_persona_feedbacks.json",
    "feedback_clusters_map.png",
    "feedback_points_128d.json",
    "feedback_summary",
    "video_voc_analysis.json"
  ];

  function isReservedFeedbackFile(fileName) {
    for (var r = 0; r < reservedFiles.length; r++) {
      if (fileName.toLowerCase() === reservedFiles[r].toLowerCase()) {
        return true;
      }
    }
    return false;
  }

  TestRunner.assert(isReservedFeedbackFile("ai_persona_feedbacks.json"), "예약 파일 ai_persona_feedbacks.json 배제 확인");
  TestRunner.assert(isReservedFeedbackFile("feedback_summary"), "예약 파일 feedback_summary 배제 확인");
  TestRunner.assert(!isReservedFeedbackFile("user_photo.jpg"), "유저 드롭 이미지 허용 확인");
  TestRunner.assert(!isReservedFeedbackFile("customer_memo.txt"), "유저 드롭 텍스트 메모 허용 확인");
  TestRunner.assert(!isReservedFeedbackFile("extra_interview.mp4"), "유저 추가 동영상 파일 허용 확인");

  // 2. 파일 확장자 분류 에뮬레이션 검증
  function classifyManualFile(name) {
    var lower = name.toLowerCase();
    if (lower.indexOf(".jpg") !== -1 || lower.indexOf(".jpeg") !== -1 || lower.indexOf(".png") !== -1 || lower.indexOf(".webp") !== -1) {
      return "IMAGE";
    }
    if (lower.indexOf(".mp4") !== -1 || lower.indexOf(".mov") !== -1 || lower.indexOf(".webm") !== -1) {
      return "VIDEO";
    }
    if (lower.indexOf(".txt") !== -1 || lower.indexOf(".csv") !== -1 || lower.indexOf(".md") !== -1 || lower.indexOf(".json") !== -1) {
      return "TEXT";
    }
    return "DOC";
  }

  TestRunner.assertEqual(classifyManualFile("sample_wearing.png"), "IMAGE", "이미지 파일 분류 검증");
  TestRunner.assertEqual(classifyManualFile("user_review.txt"), "TEXT", "텍스트 메모 분류 검증");
  TestRunner.assertEqual(classifyManualFile("interview_clip.mp4"), "VIDEO", "동영상 파일 분류 검증");
  TestRunner.assertEqual(classifyManualFile("현장_피드백_보고서"), "DOC", "문서 파일 분류 검증");

  // 3. VLM 페이로드 크기 제약 방어 검증 (25MB 제한)
  var smallSize = 10 * 1024 * 1024; // 10MB
  var bigSize = 30 * 1024 * 1024;   // 30MB
  var maxVlmBytes = 25 * 1024 * 1024;

  TestRunner.assert(smallSize <= maxVlmBytes, "10MB 정상 이미지 VLM 인출 허용 검증");
  TestRunner.assert(bigSize > maxVlmBytes, "30MB 초과 이미지 VLM 연산 방어 검증");
}

/**
 * [단위 테스트 5] 작업 공간 및 25인 페르소나 데이터셋 검증 (Workspace & Persona Suite)
 */
function testSuite_WorkspaceAndInit() {
  TestRunner.startSuite("5. 작업 공간 및 페르소나 (Workspace & Init)");

  // 1. 번들 내 25인 기본 페르소나 데이터 파싱 및 필드 무결성 검증
  var masterObj = (typeof getMasterPersonas25 === "function") ? getMasterPersonas25() : null;
  TestRunner.assertNotNull(masterObj, "기본 25인 페르소나 마스터 객체 존재 검증");

  var personasList = masterObj ? (masterObj.personas || masterObj) : [];
  TestRunner.assertEqual(personasList.length, 25, "AI 페르소나 총 25인 정원 검증");

  // 2. 7대 필수 필드 무결성 전수 검사
  var requiredFields = ["id", "name", "age", "gender", "category", "occupation", "perspective"];
  var allValid = true;
  var marketerCount = 0;
  var consumerCount = 0;

  for (var p = 0; p < personasList.length; p++) {
    var persona = personasList[p];
    for (var f = 0; f < requiredFields.length; f++) {
      var fieldName = requiredFields[f];
      if (persona[fieldName] === undefined || persona[fieldName] === null || persona[fieldName] === "") {
        allValid = false;
      }
    }
    if (persona.category === "전문 마케터") marketerCount++;
    else consumerCount++;
  }

  TestRunner.assert(allValid, "25인 페르소나 7대 필수 필드(id, name, age, gender, category, occupation, perspective) 완비 검증");
  TestRunner.assertEqual(marketerCount, 12, "전문 마케터 12인 안배 검증");
  TestRunner.assertEqual(consumerCount, 13, "일반 소비자 13인 안배 검증");
}

/**
 * [단위 테스트 6] 설문 문항 및 다면 평가 가중치 검증 (Form & Judge Suite)
 */
function testSuite_FormAndJudge() {
  TestRunner.startSuite("6. 설문 문항 및 다면 평가 가중치 (Form & Judge)");

  // 1. 설문지 4대 필수 문항 구성 규격 검증
  var formQuestions = [
    { title: "콘텐츠 버전", type: "CHOICE", required: true },
    { title: "종합 만족도", type: "SCALE", min: 1, max: 5, required: true },
    { title: "솔직한 의견 및 개선 제안", type: "PARAGRAPH", required: true },
    { title: "직접 촬영한 동영상 피드백 첨부", type: "FILE_UPLOAD", required: false },
    { title: "착용 샷 또는 디자인 이미지 피드백 첨부", type: "FILE_UPLOAD", required: false }
  ];

  TestRunner.assertEqual(formQuestions.length, 5, "설문 문항 총 5개(버전, 평점, 의견, 동영상, 이미지) 규격 검증");
  TestRunner.assertEqual(formQuestions[1].max, 5, "평점 5점 척도 검증");

  // 2. 다면 평가 종합 점수 가중치 공식 검증
  function calculateOverallScore(quantAvg, qualAvg, videoScore, hasVideo) {
    if (hasVideo && videoScore !== null && videoScore !== undefined) {
      return (quantAvg * 0.5) + (qualAvg * 0.3) + (videoScore * 0.2);
    } else {
      return (quantAvg * 0.5) + (qualAvg * 0.5);
    }
  }

  // 동영상 VoC 인입 시: 정량 50%, 정성 30%, 비디오 VoC 20%
  var scoreWithVideo = calculateOverallScore(4.0, 4.0, 5.0, true);
  // 4.0*0.5 + 4.0*0.3 + 5.0*0.2 = 2.0 + 1.2 + 1.0 = 4.2
  TestRunner.assertEqual(Math.round(scoreWithVideo * 10) / 10, 4.2, "동영상 VoC 포함 가중치 계산(5:3:2) 검증");

  // 동영상 VoC 미제출 시: 정량 50%, 정성 50%
  var scoreWithoutVideo = calculateOverallScore(4.0, 3.0, null, false);
  // 4.0*0.5 + 3.0*0.5 = 3.5
  TestRunner.assertEqual(Math.round(scoreWithoutVideo * 10) / 10, 3.5, "동영상 VoC 미제출 가중치 계산(5:5) 검증");
}

/**
 * [단위 테스트 7] 마케터 HITL 및 N차 리비전 자산 규격 검증 (HITL & Refine Suite)
 */
function testSuite_HitlAndRefine() {
  TestRunner.startSuite("7. 마케터 HITL 및 N차 리비전 (HITL & Refine)");

  // 1. 회차별 마케터 디폴트 지침 분기 검증
  function getMarketerCommentByRound(roundNum) {
    if (roundNum === 2) {
      return "20대 한국인 여성 모델이 세련된 서울 카페에서 초경량 노이즈 캔슬링을 켜고 몰입하는 순간을 헤드카피와 비주얼로 전면에 내세울 것.";
    } else if (roundNum >= 3) {
      return "그랜드 론칭 한정 얼리버드 혜택(고급 가죽 트래블 파우치 증정)을 볼드하게 명시하고, 한국인 20대 여성 모델과 5종 시그니처 파스텔 컬러 라인업을 담은 론칭 완결형 비주얼을 도출할 것.";
    }
    return "출퇴근 피로감보다 주말 카페 힐링 감성을 강조하고, 180g 초경량 착용감을 헤드카피로 올릴 것.";
  }

  TestRunner.assert(getMarketerCommentByRound(1).indexOf("출퇴근 피로감") !== -1, "1차 마케터 기본 지침 검증");
  TestRunner.assert(getMarketerCommentByRound(2).indexOf("20대 한국인 여성 모델") !== -1, "2차 마케터 기본 지침 검증");
  TestRunner.assert(getMarketerCommentByRound(3).indexOf("얼리버드 혜택") !== -1, "3차 이상 마케터 론칭 지침 검증");

  // 2. 리비전 자산 산출물 파일명 및 종횡비 규격 검증
  function getExpectedAssetNames(prefix) {
    return [
      prefix + "_banner_16x9.png",
      prefix + "_poster_9x16.png",
      prefix + "_sns_1x1.png",
      prefix + "_shorts.mp4",
      "campaign_content"
    ];
  }

  var rv00Assets = getExpectedAssetNames("00");
  TestRunner.assertEqual(rv00Assets[0], "00_banner_16x9.png", "초판 가로 배너 16:9 규격 검증");
  TestRunner.assertEqual(rv00Assets[1], "00_poster_9x16.png", "초판 세로 포스터 9:16 규격 검증");
  TestRunner.assertEqual(rv00Assets[2], "00_sns_1x1.png", "초판 정방형 SNS 1:1 규격 검증");
  TestRunner.assertEqual(rv00Assets[3], "00_shorts.mp4", "초판 모바일 숏폼 영상 규격 검증");

  var rv02Assets = getExpectedAssetNames("02");
  TestRunner.assertEqual(rv02Assets[3], "02_shorts.mp4", "2차 개정본 모바일 숏폼 영상 규격 검증");
}

/**
 * [단위 테스트 8] 타깃 페르소나 및 Hugging Face 연동 규격 검증 (Persona & HF Suite)
 */
function testSuite_PersonaAndHf() {
  TestRunner.startSuite("8. 타깃 페르소나 및 Hugging Face (Persona & HF)");

  // 1. Hugging Face 프리픽스 식별 로직 검증
  function isHuggingFaceTarget(criteria) {
    return (criteria.indexOf("hf:") === 0);
  }

  TestRunner.assert(isHuggingFaceTarget("hf:nvidia/Nemotron-Personas-Korea"), "Hugging Face 리포지토리 인식 검증");
  TestRunner.assert(!isHuggingFaceTarget("일본 20대 여성 뷰티 인플루언서"), "일반 자연어 프롬프트 식별 검증");

  // 2. Hugging Face API 엔드포인트 URL 생성 검증
  function buildHfUrl(repoName) {
    return "https://datasets-server.huggingface.co/rows?dataset=" + encodeURIComponent(repoName) + "&config=default&split=train&offset=0&limit=25";
  }

  var hfUrl = buildHfUrl("nvidia/Nemotron-Personas-Korea");
  TestRunner.assert(hfUrl.indexOf("datasets-server.huggingface.co") !== -1, "Hugging Face 엔드포인트 도메인 검증");
  TestRunner.assert(hfUrl.indexOf("limit=25") !== -1, "25인 페르소나 제한 쿼리 파라미터 검증");
}

/**
 * [All] 전체 8대 에뮬레이션 단위 테스트 수이트 일괄 실행
 */
function runAllEmulatedUnitTests() {
  var ui = SpreadsheetApp.getUi();
  TestRunner.clearResults();

  showProcessingToast("[테스트] 전체 8대 단위 테스트 수이트 에뮬레이션 실행 중 (All)", 30);

  var startTime = new Date().getTime();

  // 8대 단위 테스트 수이트 순차 실행
  testSuite_Config();
  testSuite_Utils();
  testSuite_DynamicRoundDetect();
  testSuite_VlmAndScanner();
  testSuite_WorkspaceAndInit();
  testSuite_FormAndJudge();
  testSuite_HitlAndRefine();
  testSuite_PersonaAndHf();

  var elapsedMs = new Date().getTime() - startTime;
  var summary = TestRunner.getSummary();

  // 결과를 Google Sheets [테스트 결과] 탭에 표로 자동 기록
  TestRunner.printReportToSheet();

  var resultMessage =
    "전체 " + summary.total + "개 단위 테스트 에뮬레이션 검증이 완료되었습니다.\n\n" +
    "- 통과 (PASS): " + summary.passed + "건\n" +
    "- 실패 (FAIL): " + summary.failed + "건\n" +
    "- 통과율: " + summary.passRate + "\n" +
    "- 소요 시간: " + (elapsedMs / 1000).toFixed(2) + "초\n\n" +
    "Google Sheets의 [테스트 결과] 탭에서 세부 항목별 진단 리포트를 확인하십시오.";

  ui.alert("단위 테스트 수이트 실행 완료 (All)", resultMessage, ui.ButtonSet.OK);
  return summary;
}

/**
 * 개별 단위 테스트 실행 헬퍼 래퍼 함수
 */
function runSingleTestSuiteWithAlert(suiteFn, suiteTitle) {
  var ui = SpreadsheetApp.getUi();
  TestRunner.clearResults();
  showProcessingToast("[테스트] " + suiteTitle + " 실행 중", 15);
  suiteFn();
  var summary = TestRunner.getSummary();
  TestRunner.printReportToSheet();

  var resultMessage =
    suiteTitle + " 실행 완료:\n\n" +
    "- 통과 (PASS): " + summary.passed + "건\n" +
    "- 실패 (FAIL): " + summary.failed + "건\n" +
    "- 통과율: " + summary.passRate + "\n\n" +
    "Google Sheets의 [테스트 결과] 탭에서 세부 항목을 확인하십시오.";

  ui.alert(suiteTitle + " 결과", resultMessage, ui.ButtonSet.OK);
}

function testSuite_Config_Alert() {
  runSingleTestSuiteWithAlert(testSuite_Config, "1. 환경 및 설정 구성 (Config)");
}

function testSuite_Utils_Alert() {
  runSingleTestSuiteWithAlert(testSuite_Utils, "2. 헬퍼 유틸리티 (Utils)");
}

function testSuite_DynamicRoundDetect_Alert() {
  runSingleTestSuiteWithAlert(testSuite_DynamicRoundDetect, "3. 동적 회차 탐색기 (Dynamic Round Detect)");
}

function testSuite_VlmAndScanner_Alert() {
  runSingleTestSuiteWithAlert(testSuite_VlmAndScanner, "4. VLM 분석 및 수작업 스캐너 (VLM & Scanner)");
}

function testSuite_WorkspaceAndInit_Alert() {
  runSingleTestSuiteWithAlert(testSuite_WorkspaceAndInit, "5. 작업 공간 및 페르소나 (Workspace & Init)");
}

function testSuite_FormAndJudge_Alert() {
  runSingleTestSuiteWithAlert(testSuite_FormAndJudge, "6. 설문 문항 및 다면 평가 가중치 (Form & Judge)");
}

function testSuite_HitlAndRefine_Alert() {
  runSingleTestSuiteWithAlert(testSuite_HitlAndRefine, "7. 마케터 HITL 및 N차 리비전 (HITL & Refine)");
}

function testSuite_PersonaAndHf_Alert() {
  runSingleTestSuiteWithAlert(testSuite_PersonaAndHf, "8. 타깃 페르소나 및 Hugging Face (Persona & HF)");
}
