/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 4] 캠페인 작업 공간 초기화 및 구글 폼 올인원 세팅 엔진 (Workspace & Form Initializer)
 */

/**
 * [캠페인 초기화] 구글 드라이브 폴더 트리, 루트 직속 25인 페르소나, 6대 프롬프트 구글 독스,
 * 그리고 고객 VoC 수집용 Google Forms 생성 및 시트 바인딩까지 초장에 100% 완결한다.
 */
function initCampaignWorkspace() {
  var ui = SpreadsheetApp.getUi();
  showProcessingToast("캠페인 작업 공간 및 VoC 설문 폼 올인원 초기화 중...", 20);
  try {
    var campaignFolder = getCampaignFolder();
    var campaignCode = getCampaignCode();

    // 1. 핵심 서브폴더 트리 생성
    var promptsFolder = getCampaignSubFolder([CONFIG.PROMPTS_FOLDER_NAME || "prompts"]);
    var inputFolder = getCampaignSubFolder(["input"]);
    var outputFolder = getCampaignSubFolder(["output"]);
    var fb01Folder = getCampaignSubFolder(["input", "fb-01"]);
    var rv00Folder = getCampaignSubFolder(["output", "rv-00"]);

    // 2. [핵심] 25인 타깃 AI 페르소나 마스터 데이터를 캠페인 루트 폴더 직속에 시딩
    var personaFileName = CONFIG.PERSONA_FILE_NAME || "ai_personas.json";
    var existingPersonas = campaignFolder.getFilesByName(personaFileName);
    if (!existingPersonas.hasNext()) {
      var rawBase = (CONFIG && CONFIG.GITHUB_RAW_BASE) || "https://raw.githubusercontent.com/jiangjun-forge/google-cloud-0-to-1/main/samples/drive-marketing-content-pipeline";
      var personaJsonText = "";

      // GitHub 퍼블릭 저장소의 data/ai_personas.json 파일 실시간 인출
      try {
        var personaUrl = rawBase + "/data/ai_personas.json";
        var pResp = UrlFetchApp.fetch(personaUrl, { muteHttpExceptions: true });
        if (pResp.getResponseCode() === 200) {
          personaJsonText = pResp.getContentText();
          Logger.log("GitHub Raw로부터 최신 25인 페르소나 데이터 인출 성공");
        }
      } catch (fetchErr) {
        Logger.log("GitHub Raw 페르소나 인출 실패 (로컬 폴백 사용): " + fetchErr.toString());
      }

      // 네트워크 불가 시 내장 기본값으로 안전 폴백
      if (!personaJsonText) {
        var masterPersonas = getMasterPersonas25();
        personaJsonText = JSON.stringify(masterPersonas, null, 2);
      }

      saveTextFile(campaignFolder, personaFileName, personaJsonText);
      Logger.log("루트 직속 25인 AI 페르소나 데이터셋 시딩 완료: " + personaFileName);
    }

    // 3. prompts/ 폴더 내 6대 프롬프트 구글 독스 자동 시딩 (기존 마케터 수정분 보존)
    seedDefaultPrompts(promptsFolder);

    // 4. 스타터 아이디어 메모 구글 독스 시딩 (input/아이디어 메모)
    if (!readGoogleDoc(inputFolder, "아이디어 메모")) {
      var rawBase = (CONFIG && CONFIG.GITHUB_RAW_BASE) || "https://raw.githubusercontent.com/jiangjun-forge/google-cloud-0-to-1/main/samples/drive-marketing-content-pipeline";
      var starterIdea = "";

      // GitHub 퍼블릭 저장소의 data/starter_idea.md 파일 실시간 인출
      try {
        var ideaUrl = rawBase + "/data/starter_idea.md";
        var iResp = UrlFetchApp.fetch(ideaUrl, { muteHttpExceptions: true });
        if (iResp.getResponseCode() === 200) {
          starterIdea = iResp.getContentText().replace("cp-ignite", campaignCode);
          Logger.log("GitHub Raw로부터 스타터 아이디어 메모 인출 성공");
        }
      } catch (ideaErr) {
        Logger.log("GitHub Raw 스타터 아이디어 인출 실패 (로컬 폴백 사용): " + ideaErr.toString());
      }

      // 폴백 템플릿
      if (!starterIdea) {
        starterIdea =
          "# 캠페인 아이디어 메모\n\n" +
          "* **캠페인 명칭**: 2026 가을 오텀 브리즈 캠페인 (" + campaignCode + ")\n" +
          "* **핵심 컨셉**: 선선한 가을 날씨에 어울리는 프리미엄 노이즈 캔슬링(ANC) 헤드폰 일상 탈출 컬렉션\n" +
          "* **타깃 고객**: 도심 속 워크앤라이프 밸런스를 추구하는 2040 직장인 및 통근자\n" +
          "* **핵심 소구점**: 180g 초경량 착용감, 45dB 차음 성능, 감성적 힐링 몰입 무드\n" +
          "* **목표 채널**: 유튜브 쇼츠 및 인스타그램 릴스(9:16), 디스플레이 배너(16:9), 블로그 브랜드 기고문\n";
      }

      saveGoogleDoc(inputFolder, "아이디어 메모", starterIdea);
    }

    // 5. [핵심] 고객 VoC 수집용 구글 폼(Google Forms) 자동 생성 및 시트 연동 초장 완결
    var formInfo = setupFeedbackGoogleForm(campaignFolder, campaignCode);

    // 6. 현재 구글 시트를 캠페인 루트 폴더로 안전하게 이동하여 컨트롤 타워 패키징
    try {
      var activeSpreadsheet = SpreadsheetApp.getActiveSpreadsheet();
      var sheetFile = DriveApp.getFileById(activeSpreadsheet.getId());
      sheetFile.moveTo(campaignFolder);
      var currentTitle = activeSpreadsheet.getName();
      if (!currentTitle || currentTitle === "제목 없는 스프레드시트" || currentTitle === "마케팅 콘텐츠 파이프라인") {
        activeSpreadsheet.rename("[마케팅 컨트롤 타워] " + campaignCode);
      }
    } catch (sheetMoveErr) {
      Logger.log("시트 캠페인 폴더 이동 중 예외 (무시 가능): " + sheetMoveErr);
    }

    // 7. 구글 시트 실행 대시보드 표 초기화 및 핵심 리소스 링크 등록
    initDashboardSheet();
    recordStepResultToSheet("초기 환경 구축", "작업 공간 및 VoC 설문 폼", "완료", campaignFolder.getUrl(), "구글 드라이브 폴더 열기 (" + campaignCode + ")");
    if (formInfo && formInfo.publishedUrl) {
      recordStepResultToSheet("고객 피드백 채널", "VoC 구글 폼 및 모바일 QR", "활성", formInfo.publishedUrl, "온라인 설문지 열기");
    }

    ui.alert(
      "캠페인 초기 환경 구축 완료 (All-in-one)",
      "캠페인 작업 공간(" + campaignCode + ")이 완벽하게 준비되었습니다:\n\n" +
      "1. 캠페인 루트 직속 25인 페르소나(ai_personas.json) 완비\n" +
      "2. prompts/ 폴더 내 6대 프롬프트 구글 독스 시딩 완료 (언제든 직접 수정 가능)\n" +
      "3. 고객 VoC 수집용 구글 폼 생성 및 모바일 QR 코드 바인딩 완료\n\n" +
      "구글 시트의 [실행 대시보드] 표에서 바로가기 링크를 확인하십시오.",
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert("초기화 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
}

/**
 * 고객 VoC 수집용 Google Forms를 생성하고 현재 시트와 모바일 QR 코드를 자동 연동한다.
 *
 * @param {GoogleAppsScript.Drive.Folder} campaignFolder - 캠페인 루트 폴더
 * @param {string} campaignCode - 캠페인 코드
 * @return {{ publishedUrl: string, editUrl: string }} 폼 URL 정보
 */
function setupFeedbackGoogleForm(campaignFolder, campaignCode) {
  try {
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    var spreadsheetId = spreadsheet.getId();
    var formTitle = "고객 피드백 설문 (" + campaignCode + ")";

    // 기존에 생성된 폼이 있는지 탐색
    var existingFiles = campaignFolder.getFilesByName(formTitle);
    if (existingFiles.hasNext()) {
      var file = existingFiles.next();
      var existingForm = FormApp.openById(file.getId());
      return {
        publishedUrl: existingForm.getPublishedUrl(),
        editUrl: existingForm.getEditUrl()
      };
    }

    var form = FormApp.create(formTitle);
    form.setAcceptingResponses(true);
    try {
      form.setRequireLogin(false);
      form.setCollectEmail(false);
      form.setLimitOneResponsePerUser(false);
      form.setShowLinkToRespondAgain(true);
    } catch (e) {
      Logger.log("폼 기본 옵션 설정 예외: " + e);
    }

    var publishedUrl = form.getPublishedUrl();

    form.setDescription(
      "본 설문은 " + campaignCode + " 캠페인의 고객 만족도와 사용자 직접 촬영 동영상/이미지 피드백을 수집하여 " +
      "Gemini VLM 다면 평가 및 마케팅 콘텐츠 보정에 반영하기 위한 설문입니다.\n\n" +
      "[모바일 즉시 참여 안내]\n" +
      "스마트폰 카메라로 아래 QR 코드를 스캔하면 모바일 화면에서 즉시 피드백을 작성하실 수 있습니다.\n" +
      "설문 참여 바로가기: " + publishedUrl
    );

    // 모바일 참여용 고화질 QR 코드 생성 및 최상단 삽입
    try {
      var qrApiUrl = "https://quickchart.io/qr?text=" + encodeURIComponent(publishedUrl) + "&size=300&ecLevel=H";
      var qrResponse = UrlFetchApp.fetch(qrApiUrl, { muteHttpExceptions: true });
      if (qrResponse.getResponseCode() === 200) {
        var qrBlob = qrResponse.getBlob().setName("form_qr_code.png");
        var imageItem = form.addImageItem();
        imageItem.setTitle("스마트폰 카메라로 QR 코드를 스캔하여 모바일 피드백을 제출하세요!");
        imageItem.setHelpText("모바일 설문 URL: " + publishedUrl);
        imageItem.setImage(qrBlob);
      }
    } catch (qrErr) {
      Logger.log("QR 코드 이미지 생성 예외: " + qrErr);
    }

    // 질문 문항 자동 구성
    var versionItem = form.addMultipleChoiceItem();
    versionItem.setTitle("평가 대상 마케팅 콘텐츠 버전 (선택 사항)")
      .setChoiceValues(["초판 (rv-00)", "1차 개정본 (rv-01)", "2차 개정본 (rv-02)"])
      .setRequired(false);

    form.addScaleItem()
      .setTitle("제품의 전반적인 만족도는 어떠셨습니까? (선택 사항)")
      .setBounds(1, 5)
      .setLabels("매우 불만족", "매우 만족")
      .setRequired(false);

    form.addParagraphTextItem()
      .setTitle("제품을 사용하면서 느낀 솔직한 장점이나 아쉬운 점을 자유롭게 적어주십시오. (자유 기술)")
      .setHelpText("예: 도심 지하철 소음 차단은 좋은데, 가벼운 착용감이나 힐링 무드 카피를 더 부각해 주면 좋겠습니다.")
      .setRequired(false);

    form.addParagraphTextItem()
      .setTitle("고객 촬영 동영상 피드백 소감 요약 또는 파일 링크 (선택 사항)")
      .setHelpText("스마트폰으로 제품을 사용해보며 느낀 소감이나 고객의 생생한 목소리를 적어주십시오. (권장 길이 15~30초 세로 숏폼 영상)")
      .setRequired(false);

    form.addParagraphTextItem()
      .setTitle("추가 이미지 피드백 소감 또는 링크 (선택 사항)")
      .setHelpText("제품 착용 컷, 언박싱 사진에 대한 의견이나 이미지 파일 링크를 입력하십시오.")
      .setRequired(false);

    // 현재 구글 시트에 응답 탭 연결
    form.setDestination(FormApp.DestinationType.SPREADSHEET, spreadsheetId);

    // 폼 파일을 캠페인 루트 폴더로 이동
    var formFile = DriveApp.getFileById(form.getId());
    formFile.moveTo(campaignFolder);

    Logger.log("고객 VoC Google Forms 생성 및 시트 바인딩 완료: " + publishedUrl);
    return {
      publishedUrl: publishedUrl,
      editUrl: form.getEditUrl()
    };
  } catch (err) {
    Logger.log("Google Forms 설정 예외: " + err);
    return null;
  }
}

/**
 * [환경 설정] 캠페인 코드 및 타깃 설정을 조회하고 재설정한다.
 */
function runConfigureCampaignSettings() {
  var ui = SpreadsheetApp.getUi();
  var userProps = PropertiesService.getUserProperties();
  var currentCode = userProps.getProperty("CAMPAIGN_CODE") || CONFIG.CAMPAIGN_CODE || "cp-ignite";

  var response = ui.prompt(
    "캠페인 환경 설정 및 재설정 (Configuration)",
    "현재 캠페인 코드: [" + currentCode + "]\n\n" +
    "새로운 캠페인 코드를 입력하거나 기존 코드를 유지하십시오 (영문 소문자 및 하이픈 권장):",
    ui.ButtonSet.OK_CANCEL
  );

  if (response.getSelectedButton() === ui.Button.OK) {
    var newCode = response.getResponseText().trim();
    if (newCode) {
      userProps.setProperty("CAMPAIGN_CODE", newCode);
      ui.alert("설정 완료", "캠페인 코드가 [" + newCode + "]로 업데이트되었습니다.", ui.ButtonSet.OK);
      return newCode;
    }
  }
  return currentCode;
}

/**
 * 25인 슬림 한국인 AI 페르소나 마스터 데이터셋 반환
 */
function getMasterPersonas25() {
  return {
    "metadata": {
      "description": "한국인 25인 다면 평가 슬림 AI 페르소나 패널 (토큰 최적화 경량 규격)",
      "total": 25
    },
    "personas": [
      { "id": "p01", "name": "강도윤", "age": 28, "gender": "남성", "category": "전문 마케터", "occupation": "퍼포먼스 마케터", "perspective": "데이터 지향적, 민첩한 의사 결정. ROAS 지표 및 전환 효율 중시" },
      { "id": "p02", "name": "김서아", "age": 32, "gender": "여성", "category": "전문 마케터", "occupation": "브랜드 마케터", "perspective": "감성적 통찰력, 차별화된 톤앤매너와 브랜드 스토리텔링 중시" },
      { "id": "p03", "name": "이서연", "age": 24, "gender": "여성", "category": "20대 대학생", "occupation": "대학생", "perspective": "트렌드에 민감한 Z세대, 인스타그램 릴스와 숏폼 소비 중심" },
      { "id": "p04", "name": "박민준", "age": 25, "gender": "남성", "category": "20대 대학생", "occupation": "취업 준비생", "perspective": "가격 대비 심리적 만족(가심비)과 학습 몰입 환경 중시" },
      { "id": "p05", "name": "정도현", "age": 29, "gender": "남성", "category": "2030 직장인", "occupation": "IT 개발자", "perspective": "도심 출퇴근 지하철 소음 차단 및 기기 멀티포인트 연결 중시" },
      { "id": "p06", "name": "최지우", "age": 31, "gender": "여성", "category": "2030 직장인", "occupation": "금융 컨설턴트", "perspective": "모던한 오피스 룩과의 조화 및 장시간 착용 시 피로도 중시" },
      { "id": "p07", "name": "강하은", "age": 34, "gender": "여성", "category": "2030 직장인", "occupation": "인하우스 디자이너", "perspective": "미니멀한 제품 심미성, 패키지 완성도 및 감각적인 비주얼 선호" },
      { "id": "p08", "name": "윤우진", "age": 36, "gender": "남성", "category": "3040 전문가", "occupation": "스타트업 대표", "perspective": "비즈니스 통화 품질, 마이크 성능 및 프리미엄 브랜드 신뢰도" },
      { "id": "p09", "name": "임수빈", "age": 27, "gender": "여성", "category": "크리에이터", "occupation": "유튜브 브이로거", "perspective": "야외 촬영 시 휴대성, 감성적인 카페 인테리어와의 어울림" },
      { "id": "p10", "name": "한태양", "age": 38, "gender": "남성", "category": "아웃도어/캠퍼", "occupation": "프리랜서 작가", "perspective": "주말 차박 및 솔로 캠핑 시 배터리 지속력과 생활 방수 성능" },
      { "id": "p11", "name": "배소율", "age": 22, "gender": "여성", "category": "20대 대학생", "occupation": "예술대 학생", "perspective": "독창적인 색감, 힙한 숏폼 사운드와 개성 표현 가능 여부" },
      { "id": "p12", "name": "송시우", "age": 41, "gender": "남성", "category": "40대 부모", "occupation": "제조업 팀장", "perspective": "자녀와의 휴식, 층간 소음 극복 및 온전한 자기 계발 시간 확보" },
      { "id": "p13", "name": "오유진", "age": 33, "gender": "여성", "category": "워킹맘", "occupation": "마케팅 과장", "perspective": "가사와 육아 병행 중 틈새 힐링, 가벼운 무게와 직관적 터치 조작" },
      { "id": "p14", "name": "권준호", "age": 26, "gender": "남성", "category": "얼리어답터", "occupation": "하드웨어 엔지니어", "perspective": "드라이버 음향 스펙, 코덱 지원(LDAC), 노이즈 캔슬링 칩셋 분석" },
      { "id": "p15", "name": "백서진", "age": 30, "gender": "여성", "category": "피트니스/러너", "occupation": "필라테스 강사", "perspective": "러닝 시 흔들림 없는 밀착감, 땀에 강한 이어패드 소재" },
      { "id": "p16", "name": "조은우", "age": 45, "gender": "남성", "category": "시니어 프로", "occupation": "공공기관 부장", "perspective": "단정하고 품격 있는 디자인, 복잡하지 않은 직관적 버튼 구성" },
      { "id": "p17", "name": "남궁예린", "age": 23, "gender": "여성", "category": "Z세대 쇼퍼", "occupation": "패션 인턴", "perspective": "인스타 감성 룩북 컷 연출, 성수동 팝업스토어 체험 기대감" },
      { "id": "p18", "name": "문지훈", "age": 35, "gender": "남성", "category": "음악 애호가", "occupation": "사운드 엔지니어", "perspective": "원음 왜곡 없는 플랫한 해상력, 베이스 타격감과 공간 음향" },
      { "id": "p19", "name": "신채원", "age": 29, "gender": "여성", "category": "원격 근무자", "occupation": "글로벌 번역가", "perspective": "화상 회의 시 주변 소음 감쇄 및 8시간 이상 무압박 착용감" },
      { "id": "p20", "name": "황민성", "age": 39, "gender": "남성", "category": "비즈니스 트래블러", "occupation": "해외 영업 차장", "perspective": "비행기 엔진 저주파 소음 완벽 차단 및 접이식 컴팩트 파우치" },
      { "id": "p21", "name": "노하율", "age": 21, "gender": "여성", "category": "20대 알바생", "occupation": "휴학생", "perspective": "무이자 할부 및 얼리버드 특별 할인 혜택, 실질 구매 가격" },
      { "id": "p22", "name": "구건우", "age": 37, "gender": "남성", "category": "취미 캠퍼", "occupation": "건축 설계사", "perspective": "야외 불멍 시 몰입감, 자연의 소리와 음악을 오가는 앰비언트 모드" },
      { "id": "p23", "name": "서다은", "age": 33, "gender": "여성", "category": "트렌드세터", "occupation": "커머스 MD", "perspective": "선물용 패키지 가치, 카카오톡 선물하기 입점 가능성" },
      { "id": "p24", "name": "유재혁", "age": 48, "gender": "남성", "category": "중견 임원", "occupation": "경영 기획 전무", "perspective": "프리미엄 라인업의 브랜드 헤리티지 및 애프터서비스(A/S) 신뢰성" },
      { "id": "p25", "name": "홍지아", "age": 27, "gender": "여성", "category": "북클럽 리더", "occupation": "도서관 사서", "perspective": "독서와 사색을 위한 백색 소음 조성, 안경 착용 시 통증 유무" }
    ]
  };
}
