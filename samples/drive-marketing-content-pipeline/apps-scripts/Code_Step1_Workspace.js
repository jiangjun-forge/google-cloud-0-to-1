/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [Step 1] 구글 드라이브 작업 공간 폴더 구조 및 25인 AI 페르소나 데이터셋 자동 생성 (Workspace Initializer)
 */

function createWorkspaceFolderTree() {
  var ui = SpreadsheetApp.getUi();
  showProcessingToast("[Step 1] Google Drive 작업 공간 및 25인 페르소나 자동 생성", 15);
  try {
    // 1. 캠페인별 독립 폴더 구조 생성 (input, output을 캠페인 폴더 직하위에 격리)
    var campaign = getCampaignFolder();
    var campaignCode = getCampaignCode();
    var inputFolder = getCampaignSubFolder(["input"]);
    var outputFolder = getCampaignSubFolder(["output"]);
    // 2. 가상 페르소나 25인 마스터 데이터셋 ({campaign}/input/ai_personas.json)
    var masterPersonas25 = getMasterPersonas25();

    // 2. 가상 페르소나 25인 마스터 데이터셋 ({campaign}/input/ai_personas.json 생성)
    saveTextFile(inputFolder, "ai_personas.json", JSON.stringify(masterPersonas25, null, 2));

    // fb-01 폴더 초기 생성 및 샘플 고객 동영상(VoC) 자동 시딩 (feedback_{timestamp}.mp4)
    var fb01Folder = getCampaignSubFolder(["input", "fb-01"]);
    var sampleVideoName = "feedback_" + Utilities.formatDate(new Date(), "Asia/Seoul", "yyyyMMdd_HHmmss") + ".mp4";
    saveSampleVideoFile(fb01Folder, sampleVideoName);

    // 스타터 아이디어 구글 독스 문서 (input/아이디어 메모) 자동 생성
    if (!readGoogleDoc(inputFolder, "아이디어 메모")) {
      var starterIdea = "# 캠페인 아이디어 메모\n\n" +
        "* **캠페인 명칭**: 2026 가을 오텀 브리즈 캠페인 (cp-autumn-breeze)\n" +
        "* **핵심 컨셉**: 선선한 가을 날씨에 어울리는 프리미엄 아웃도어 & 라이프스타일 컬렉션\n" +
        "* **타깃 고객**: 도심 속 워크앤라이프 밸런스를 추구하는 2040 직장인 및 주말 아웃도어 캠퍼\n" +
        "* **핵심 소구점**: 가볍고 따뜻한 기능성 소재, 모던한 실루엣, 일상과 캠핑을 아우르는 활용성\n" +
        "* **목표 채널**: 인스타그램 릴스 숏폼, 네이버 블로그 브랜드 스토리, 뉴스레터 이메일 시퀀스\n";
      saveGoogleDoc(inputFolder, "아이디어 메모", starterIdea);
    }

    // 3. 현재 구글 시트를 캠페인 폴더 직하위로 자동 이동하여 캠페인 전용 컨트롤 타워로 패키징
    try {
      var activeSpreadsheet = SpreadsheetApp.getActiveSpreadsheet();
      var sheetFile = DriveApp.getFileById(activeSpreadsheet.getId());
      sheetFile.moveTo(campaign);
      var currentTitle = activeSpreadsheet.getName();
      if (!currentTitle || currentTitle === "제목 없는 스프레드시트" || currentTitle === "마케팅 콘텐츠 파이프라인") {
        activeSpreadsheet.rename("[마케팅 컨트롤 타워] " + campaignCode);
      }
    } catch (sheetMoveErr) {
      Logger.log("시트 캠페인 폴더 이동 중 예외 (무시 가능): " + sheetMoveErr);
    }

    // 4. 구글 시트 실행 대시보드 표 초기화 및 Step 1 완료 기록
    initDashboardSheet();
    recordStepResultToSheet("Step 1", "작업 공간 초기화", "완료", campaign.getUrl(), "구글 드라이브 폴더 (" + campaignCode + ")");

    var alertMsg = "캠페인 작업 공간(" + campaignCode + ")과 25인 AI 페르소나 데이터셋이 준비되었습니다.\n\n" +
                   "구글 로그인 계정으로 자동 인증되므로 별도의 API Key 발급 없이 즉시 실행하실 수 있습니다.\n\n" +
                   "구글 시트의 [실행 대시보드] 표에서 바로가기 링크를 확인하십시오.";

    ui.alert(
      "실습 환경 셋업 완료",
      alertMsg,
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert("오류 발생", e.toString(), ui.ButtonSet.OK);
  }
}


/**
 * 기본 25인 슬림 AI 페르소나 마스터 데이터셋 반환
 */
function getMasterPersonas25() {
  return {
  "metadata": {
    "description": "한국인 25인 다면 평가 슬림 AI 페르소나 패널 (토큰 최적화 경량 규격)",
    "total": 25
  },
  "personas": [
    {
      "id": "p01",
      "name": "강도윤",
      "age": 28,
      "gender": "남성",
      "category": "전문 마케터",
      "occupation": "퍼포먼스 마케터",
      "perspective": "데이터 지향적, 민첩한 의사 결정. 관심: ROAS 지표 하락 및 광고비 삭감에 대한 극심한 압박"
    },
    {
      "id": "p02",
      "name": "김서아",
      "age": 32,
      "gender": "여성",
      "category": "전문 마케터",
      "occupation": "브랜드 마케터",
      "perspective": "감성적 통찰력, 디테일에 집착하는. 관심: 뻔하고 지루한 B2B 카피를 탈피하고 차별화된 톤앤매너 확립 요구"
    },
    {
      "id": "p03",
      "name": "이서연",
      "age": 25,
      "gender": "여성",
      "category": "전문 마케터",
      "occupation": "콘텐츠 크리에이터",
      "perspective": "외향적이고 즉흥적인, 스토리텔링에 능한. 관심: 매일 쏟아지는 다채널 숏폼 영상과 인스타그램 릴스 소재 고갈"
    },
    {
      "id": "p04",
      "name": "김도현",
      "age": 35,
      "gender": "남성",
      "category": "전문 마케터",
      "occupation": "그로스 마케터",
      "perspective": "분석적이고 집요한, 실험 정신이 강한. 관심: 예산 0원으로 3일 안에 전 채널을 동시 장악해야 하는 초단기 런칭 압박"
    },
    {
      "id": "p05",
      "name": "박지우",
      "age": 42,
      "gender": "여성",
      "category": "전문 마케터",
      "occupation": "인하우스 홍보 담당자",
      "perspective": "신중하고 정무적인 감각, 원만한 대인관계. 관심: 보고서용 데이터 정리와 경영진 설득을 위한 명확한 비용 절감 ROI 증명"
    },
    {
      "id": "p06",
      "name": "박서준",
      "age": 38,
      "gender": "남성",
      "category": "전문 마케터",
      "occupation": "퍼포먼스 리드",
      "perspective": "글로벌 감각, 도전적이고 대범한. 관심: 광고 피로도 극복을 위한 수십 개 카피의 실시간 다채널 A/B 테스트 요구"
    },
    {
      "id": "p07",
      "name": "최수아",
      "age": 28,
      "gender": "여성",
      "category": "전문 마케터",
      "occupation": "SNS 채널 운영자",
      "perspective": "트렌드에 극도로 민감한, 사교적이고 발랄한. 관심: Z세대 취향을 저격하는 B급 유머와 키치 네온 스타일 바이럴 릴스 기획"
    },
    {
      "id": "p08",
      "name": "이도현",
      "age": 45,
      "gender": "남성",
      "category": "전문 마케터",
      "occupation": "마케팅 팀장",
      "perspective": "진중하고 신뢰감 주는, 조직 통솔력. 관심: 보수적인 임원진을 설득할 수 있는 데이터 기반의 정량적 성공 사례 및 신뢰성 입증"
    },
    {
      "id": "p09",
      "name": "정예준",
      "age": 32,
      "gender": "남성",
      "category": "전문 마케터",
      "occupation": "퍼포먼스 AE",
      "perspective": "추진력 있고 유연한, 위기 대처 능력. 관심: 광고주마다 쏟아지는 다채널 소재 베리에이션 요청으로 인한 만성 야근"
    },
    {
      "id": "p10",
      "name": "정하은",
      "age": 25,
      "gender": "여성",
      "category": "전문 마케터",
      "occupation": "커뮤니티 매니저",
      "perspective": "공감 능력이 탁월한, 친화적이고 포용적인. 관심: 고객의 생생한 VoC를 반영하여 실시간으로 진화하는 참여형 캠페인 구축"
    },
    {
      "id": "p11",
      "name": "조하준",
      "age": 28,
      "gender": "남성",
      "category": "전문 마케터",
      "occupation": "퍼포먼스 마케터",
      "perspective": "데이터 지향적, 민첩한 의사 결정. 관심: ROAS 지표 하락 및 광고비 삭감에 대한 극심한 압박"
    },
    {
      "id": "p12",
      "name": "강지유",
      "age": 32,
      "gender": "여성",
      "category": "전문 마케터",
      "occupation": "브랜드 마케터",
      "perspective": "감성적 통찰력, 디테일에 집착하는. 관심: 뻔하고 지루한 B2B 카피를 탈피하고 차별화된 톤앤매너 확립 요구"
    },
    {
      "id": "p13",
      "name": "전기태",
      "age": 74,
      "gender": "남성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "소탈하고 정이 넘치는, 과묵하고 인내심 강한"
    },
    {
      "id": "p14",
      "name": "최은지",
      "age": 71,
      "gender": "여성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "소탈하고 정이 넘치는, 과묵하고 인내심 강한"
    },
    {
      "id": "p15",
      "name": "안상식",
      "age": 73,
      "gender": "남성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "소탈하고 정이 넘치는, 과묵하고 인내심 강한"
    },
    {
      "id": "p16",
      "name": "김다희",
      "age": 46,
      "gender": "여성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "현실적이고 신중한, 책임감 강한"
    },
    {
      "id": "p17",
      "name": "설숙자",
      "age": 50,
      "gender": "여성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "현실적이고 신중한, 책임감 강한"
    },
    {
      "id": "p18",
      "name": "황혜란",
      "age": 33,
      "gender": "여성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "정갈하고 독립적인, 일과 쉼의 균형을 중시하는"
    },
    {
      "id": "p19",
      "name": "김준수",
      "age": 31,
      "gender": "남성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "정갈하고 독립적인, 일과 쉼의 균형을 중시하는"
    },
    {
      "id": "p20",
      "name": "곽상길",
      "age": 76,
      "gender": "남성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "소탈하고 정이 넘치는, 과묵하고 인내심 강한"
    },
    {
      "id": "p21",
      "name": "박호철",
      "age": 44,
      "gender": "남성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "현실적이고 신중한, 책임감 강한"
    },
    {
      "id": "p22",
      "name": "이태훈",
      "age": 27,
      "gender": "남성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "트렌드에 민감한, 개성 표현을 두려워하지 않는"
    },
    {
      "id": "p23",
      "name": "홍희자",
      "age": 74,
      "gender": "여성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "소탈하고 정이 넘치는, 과묵하고 인내심 강한"
    },
    {
      "id": "p24",
      "name": "고성호",
      "age": 61,
      "gender": "남성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "우직하고 성실한, 희생적인 가장/어머니"
    },
    {
      "id": "p25",
      "name": "유준호",
      "age": 61,
      "gender": "남성",
      "category": "일반 소비자",
      "occupation": "소비자",
      "perspective": "우직하고 성실한, 희생적인 가장/어머니"
    }
  ]
};
}
