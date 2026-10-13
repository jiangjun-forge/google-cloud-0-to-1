/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [Step 6] 마케터 피드백 검토 및 최종 의사 결정 (Human-in-the-loop)
 */

/**
 * [Step 6] 마케터 피드백 검토 및 최종 의사 결정 UI 프롬프트 (Human-in-the-loop)
 */
function runMarketerDecisionPrompt() {
  var ui = SpreadsheetApp.getUi();
  try {
    var campaignFolder = getCampaignFolder();
    var fb01Folder = getCampaignSubFolder(["input", "fb-01"]);
    var summaryContent = readGoogleDoc(fb01Folder, "feedback_summary");

    if (!summaryContent) {
      ui.alert(
        "선행 단계 필요",
        "먼저 [Step 5] 25인 AI 페르소나 다면 평가 및 t-SNE 지형도 생성을 실행하여 피드백 보고서를 도출하십시오.",
        ui.ButtonSet.OK
      );
      return;
    }

    var defaultComment = "20대 한국인 여성 모델이 세련된 서울 카페에서 초경량 노이즈 캔슬링을 켜고 몰입하는 순간을 헤드카피와 비주얼 전면에 내세울 것. 스펙 나열보다 감성적 힐링 공감을 극대화할 것.";

    var response = ui.prompt(
      "[Step 6] 마케터 최종 의사 결정 및 보정 지침 입력 (Human-in-the-loop)",
      "피드백 다면 평가 보고서와 t-SNE 여론 지형도를 검토한 후, 차기 마케팅 콘텐츠(rv-01)에 반영할 마케터 최종 보정 지침을 입력하십시오:\n\n" +
      "[확인]을 누르면 기본 지침으로 피드백 요약서(feedback_summary)가 즉시 갱신됩니다:",
      ui.ButtonSet.OK_CANCEL
    );

    if (response.getSelectedButton() !== ui.Button.OK) {
      return;
    }

    var marketerComment = response.getResponseText().trim();
    if (!marketerComment) {
      marketerComment = defaultComment;
    }

    // feedback_summary 문서의 마케터 최종 의사 결정 섹션 갱신
    var updatedSummary = summaryContent;
    var sectionHeader = (updatedSummary.indexOf("## 6. 마케터 최종 의사 결정") !== -1)
      ? "## 6. 마케터 최종 의사 결정 및 보정 지침"
      : "## 5. 마케터 최종 의사 결정 및 보정 지침";
    var commentBlock = "\n> **마케터 코멘트**: " + marketerComment + "\n";

    if (updatedSummary.indexOf(sectionHeader) !== -1) {
      var parts = updatedSummary.split(sectionHeader);
      updatedSummary = parts[0] + sectionHeader + " (Human-in-the-loop)\n" + commentBlock;
    } else {
      updatedSummary += "\n\n---\n\n" + sectionHeader + " (Human-in-the-loop)\n" + commentBlock;
    }

    var summaryDocFile = saveGoogleDoc(fb01Folder, "feedback_summary", updatedSummary);

    // 구글 시트 대시보드에 Step 6 완료 기록
    recordStepResultToSheet("Step 6", "마케터 피드백 검토 및 의사 결정", "완료", summaryDocFile.getUrl(), "피드백 요약서 열기 (마케터 지침 반영)");

    ui.alert(
      "마케터 의사 결정 반영 완료",
      "마케터 보정 지침이 피드백 요약서(feedback_summary)에 성공적으로 저장되었습니다.\n\n이제 [Step 7] 1차 마케팅 콘텐츠 반자율 보정(rv-01)을 실행하십시오.",
      ui.ButtonSet.OK
    );
  } catch (e) {
    ui.alert("마케터 의사 결정 반영 중 오류 발생", e.toString(), ui.ButtonSet.OK);
  }
}
