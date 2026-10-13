/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [Step 4] 고객 VoC 수집용 구글 폼 자동 생성 및 현재 구글 시트 연동 엔진 (Form Initializer & Linker)
 */

function createAndLinkGoogleForm() {
  var ui = SpreadsheetApp.getUi();
  showProcessingToast("[Step 4] 고객 VoC 수집용 Google Forms 생성 및 연동", 20);
  try {
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    var spreadsheetId = spreadsheet.getId();
    var campaignFolder = getCampaignFolder();
    var campaignCode = getCampaignCode();

    // 1. 구글 폼 생성 및 응답 활성화 설정
    var formTitle = "고객 피드백 설문";
    var form = FormApp.create(formTitle);
    form.setAcceptingResponses(true);
    try {
      form.setRequireLogin(false);
    } catch (e) {
      Logger.log("setRequireLogin 예외: " + e);
    }
    try {
      form.setCollectEmail(false);
      form.setLimitOneResponsePerUser(false);
      form.setShowLinkToRespondAgain(true);
    } catch (e) {
      Logger.log("폼 옵션 설정 예외: " + e);
    }
    var publishedUrl = form.getPublishedUrl();

    form.setDescription(
      "본 설문은 " + campaignCode + " 캠페인의 고객 만족도와 사용자 직접 촬영 동영상/이미지 피드백을 수집하여 " +
      "Gemini VLM 다면 평가 및 마케팅 콘텐츠 반자율 보정에 반영하기 위한 설문입니다.\n\n" +
      "[모바일 즉시 참여 안내]\n" +
      "스마트폰 카메라로 아래 첫 번째 항목의 QR 코드를 스캔하면 모바일 화면에서 즉시 피드백을 작성하거나 촬영 영상 링크를 제출하실 수 있습니다.\n" +
      "설문 참여 바로가기 URL: " + publishedUrl
    );

    // 2. 모바일 참여용 고화질 QR 코드 생성 및 폼 최상단 이미지 아이템 자동 삽입
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
    } catch (qrError) {
      Logger.log("QR 코드 이미지 생성 실패: " + qrError);
    }

    // 3. 질문 항목 자동 구성
    // 문항 1: 평가 대상 마케팅 콘텐츠 버전
    var versionItem = form.addMultipleChoiceItem();
    versionItem.setTitle("평가 대상 마케팅 콘텐츠 버전 (선택 사항)")
      .setChoiceValues(["초판 (rv-00)", "1차 개정본 (rv-01)", "2차 개정본 (rv-02)"])
      .setRequired(false);

    // 문항 2: 정량 만족도 평점 (1~5점 선형 배율)
    form.addScaleItem()
      .setTitle("제품의 전반적인 만족도는 어떠셨습니까? (선택 사항)")
      .setBounds(1, 5)
      .setLabels("매우 불만족", "매우 만족")
      .setRequired(false);

    // 문항 3: 정성 서술형 피드백
    form.addParagraphTextItem()
      .setTitle("제품을 사용하면서 느낀 솔직한 장점이나 아쉬운 점을 자유롭게 적어주십시오. (자유 기술)")
      .setHelpText("예: 출퇴근 길 지하철 소음 차단은 좋은데, 퇴근 길 힐링 무드 카피나 멀티포인트 페어링 기능도 다뤄주면 좋겠습니다.")
      .setRequired(false);

    // 문항 4: 고객 촬영 동영상 피드백 소감 또는 파일 링크
    form.addParagraphTextItem()
      .setTitle("고객 촬영 동영상 피드백 소감 요약 또는 파일 링크 (선택 사항)")
      .setHelpText("스마트폰으로 제품을 사용해보며 느낀 소감이나 고객의 생생한 목소리를 한두 줄로 자유롭게 적어주십시오. (동영상 공유 링크나 소감 텍스트 모두 환영하며, 권장 길이는 15~30초 이내 숏폼 영상입니다)")
      .setRequired(false);

    // 문항 5: 추가 이미지 피드백 소감 또는 링크
    form.addParagraphTextItem()
      .setTitle("추가 이미지 피드백 소감 또는 링크 (선택 사항)")
      .setHelpText("제품 착용 컷, 언박싱 사진에 대한 의견이나 이미지 파일 링크를 입력하십시오.")
      .setRequired(false);

    // 4. 목적지 구글 시트에 자동 바인딩 (설문지 응답 1 탭 자동 생성)
    form.setDestination(FormApp.DestinationType.SPREADSHEET, spreadsheetId);

    // 5. 구글 폼 파일을 캠페인 루트 폴더로 안전하게 이동
    var oldFormFiles = campaignFolder.getFilesByName(formTitle);
    while (oldFormFiles.hasNext()) {
      oldFormFiles.next().setTrashed(true);
    }
    var formFile = DriveApp.getFileById(form.getId());
    campaignFolder.addFile(formFile);
    DriveApp.getRootFolder().removeFile(formFile);

    // 6. 구글 시트 실행 대시보드에 Step 3 완료 및 링크 기록
    recordStepResultToSheet("Step 4", "고객 피드백 설문 폼 연동", "완료", publishedUrl, "고객 설문 참여 폼 열기");

    ui.alert(
      "구글 폼 연동 완료",
      "캠페인 전용 구글 폼이 생성되어 [설문지 응답 1] 탭과 연결되었습니다.\n\n구글 시트의 [실행 대시보드] 표에서 '고객 설문 참여 폼 열기' 링크를 클릭하여 응답을 제출하십시오.",
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert("구글 폼 생성 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
}
