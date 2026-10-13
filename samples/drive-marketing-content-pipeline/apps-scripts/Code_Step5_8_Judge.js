/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [Step 5 / Step 8] 25인 AI 페르소나 및 고객 피드백 다면 평가 통합 엔진 (Feedback Judge & Synthesizer)
 */

/**
 * [Step 5] 초판 콘텐츠(rv-00) 대상 1차 25인 다면 평가 및 t-SNE 여론 지형도 생성
 */
function runJudgeEvaluationRound1() {
  runJudgeEvaluation("fb-01");
}

/**
 * [Step 8] 1차 개정본 콘텐츠(rv-01) 대상 2차 25인 다면 평가 및 t-SNE 지형도 갱신
 */
function runJudgeEvaluationRound2() {
  runJudgeEvaluation("fb-02");
}

/**
 * 피드백 다면 평가 공통 실행 함수
 */
function runJudgeEvaluation(targetRoundOpt, isSilentOpt) {
  var ui = SpreadsheetApp.getUi();
  var isSilent = (isSilentOpt === true);
  try {
    var campaignFolder = getCampaignFolder();
    var campaignCode = getCampaignCode();

    // 1. 피드백 회차(fb-01, fb-02, fb-03) 판별
    var targetRound = targetRoundOpt;
    if (!targetRound) {
      var targetContentDocName = (CONFIG && CONFIG.CONTENT_DOC_NAME) || "campaign_content";
      var rv02Folder = getCampaignSubFolder(["output", "rv-02"]);
      var rv02Asset = readGoogleDoc(rv02Folder, targetContentDocName) || readGoogleDoc(rv02Folder, "campaign_asset");
      var rv01Folder = getCampaignSubFolder(["output", "rv-01"]);
      var rv01Asset = readGoogleDoc(rv01Folder, targetContentDocName) || readGoogleDoc(rv01Folder, "campaign_asset");

      if (rv02Asset) {
        targetRound = "fb-03";
      } else if (rv01Asset) {
        targetRound = "fb-02";
      } else {
        targetRound = "fb-01";
      }
    }

    var roundNum = parseInt(targetRound.replace("fb-", ""), 10) || 1;
    var prevRoundNum = Math.max(0, roundNum - 1);
    var prevRvName = "rv-" + (prevRoundNum < 10 ? "0" + prevRoundNum : prevRoundNum);
    var nextRvName = "rv-" + (roundNum < 10 ? "0" + roundNum : roundNum);
    var feedbackFolder = getCampaignSubFolder(["input", targetRound]);

    // 2. 피드백 동영상(비디오 VoC) 감지 및 Gemini VLM 심층 분석 실행 -> video_voc_analysis.json 저장
    var videoVocAnalysis = analyzeVideoVocWithVlm(feedbackFolder);
    var hasVideoAnalysis = (videoVocAnalysis !== null && videoVocAnalysis.speaker_analysis !== undefined);

    // 3. 구글 시트에서 사람 응답 데이터 수집
    var humanFeedbackRows = [];
    var humanVideoRows = [];
    var humanRatings = [];
    var versionColIndex = -1;
    var videoColIndex = -1;
    var ratingColIndex = -1;

    try {
      var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
      var responseSheet = spreadsheet.getSheetByName("설문지 응답 1") || spreadsheet.getActiveSheet();
      var sheetData = responseSheet.getDataRange().getValues();

      if (sheetData && sheetData.length > 1) {
        var headers = sheetData[0];
        for (var h = 0; h < headers.length; h++) {
          var headerStr = String(headers[h]);
          if (headerStr.indexOf("버전") !== -1 || headerStr.indexOf("Version") !== -1) {
            versionColIndex = h;
          }
          if (headerStr.indexOf("동영상") !== -1 || headerStr.indexOf("영상") !== -1 || headerStr.indexOf("비디오") !== -1 || headerStr.indexOf("Video") !== -1) {
            videoColIndex = h;
          }
          if (headerStr.indexOf("만족도") !== -1 || headerStr.indexOf("평점") !== -1 || headerStr.indexOf("Score") !== -1 || headerStr.indexOf("Rating") !== -1) {
            ratingColIndex = h;
          }
        }

        for (var i = 1; i < sheetData.length; i++) {
          var row = sheetData[i];

          if (versionColIndex !== -1) {
            var rowVersion = String(row[versionColIndex] || "").trim();
            if (rowVersion) {
              if (rowVersion.indexOf(prevRvName) === -1) {
                continue;
              }
            } else if (roundNum > 1) {
              continue;
            }
          } else if (roundNum > 1) {
            continue;
          }

          if (ratingColIndex !== -1) {
            var rVal = parseFloat(row[ratingColIndex]);
            if (!isNaN(rVal) && rVal > 0) {
              humanRatings.push(rVal);
            }
          }

          if (videoColIndex !== -1) {
            var rawVideo = String(row[videoColIndex] || "").trim();
            if (rawVideo && rawVideo !== "-" && rawVideo !== "없음" && rawVideo !== "None") {
              var isUrl = /^(?:https?:\/\/|\bwww\.)/i.test(rawVideo);
              var resolvedVideo = resolveDriveAttachmentName(rawVideo);
              if (isUrl) {
                humanVideoRows.push("- [고객 응답 " + i + " 동영상 첨부/공유 링크]: " + resolvedVideo);
              } else {
                humanVideoRows.push("- [고객 응답 " + i + " 동영상 VoC 생생 소감 발화]: \"" + rawVideo + "\"");
              }
            }
          }

          var rowContent = [];
          for (var j = 0; j < headers.length; j++) {
            if (j === versionColIndex) continue;
            var val = row[j];
            if (val !== "" && val !== null && val !== undefined) {
              var resolvedVal = resolveDriveAttachmentName(val);
              rowContent.push(headers[j] + ": " + resolvedVal);
            }
          }
          if (rowContent.length > 0) {
            humanFeedbackRows.push("- [고객 응답 " + i + "] " + rowContent.join(" | "));
          }
        }
      }
    } catch (sheetErr) {
      Logger.log("구글 시트 응답 수집 생략: " + sheetErr);
    }

    var hasHumanResponses = (humanFeedbackRows.length > 0);
    var hasVideoFeedback = (humanVideoRows.length > 0) || hasVideoAnalysis;

    // 3. AI 가상 페르소나 25인 피드백 데이터셋 로드 또는 실시간 생성
    var jsonContent = readTextFile(feedbackFolder, "ai_persona_feedbacks.json");
    if (!jsonContent) {
      jsonContent = generateLivePersonaFeedbacks(campaignFolder, feedbackFolder, prevRvName);
    }

    var personaSummaryText = "";
    var personaListText = "";
    var parsedPersonas = [];
    if (jsonContent) {
      try {
        parsedPersonas = JSON.parse(jsonContent);
        if (Array.isArray(parsedPersonas) && parsedPersonas.length > 0) {
          var totalRating = 0;
          var posCount = 0, neuCount = 0, negCount = 0;
          var feedbackItems = [];
          for (var p = 0; p < parsedPersonas.length; p++) {
            var item = parsedPersonas[p];
            var r = Number(item.rating) || 3.0;
            totalRating += r;
            if (item.sentiment === "긍정" || item.sentiment === "Positive") posCount++;
            else if (item.sentiment === "부정" || item.sentiment === "Negative") negCount++;
            else neuCount++;
            var pFeedback = item.open_feedback || item.feedback || "";
            var ptDesc = [];
            if (Array.isArray(item.points)) {
              for (var pi = 0; pi < item.points.length; pi++) {
                var pObj = item.points[pi];
                ptDesc.push("[" + (pObj.sentiment || "중립") + "] " + (pObj.text || ""));
              }
            }
            var subPointsStr = ptDesc.length > 0 ? " | 세부 포인트: " + ptDesc.join("; ") : "";
            feedbackItems.push(
              "- [" + (item.name || ("페르소나 " + (p + 1))) + " | " + (item.age || "") + "세 | " + (item.occupation || "") + " | " + (item.category || "소비자") + "] " +
              "평점: " + r + "/5.0 | 감정: " + (item.sentiment || "중립") + " | " +
              "열린 소감: \"" + pFeedback + "\"" + subPointsStr
            );
          }
          var avgRating = (totalRating / parsedPersonas.length).toFixed(1);
          personaSummaryText = "AI 가상 페르소나 " + parsedPersonas.length + "인 통계 (평균 평점: " + avgRating + "/5.0, 긍정: " + posCount + "명, 중립: " + neuCount + "명, 부정: " + negCount + "명)";
          personaListText = feedbackItems.join("\n");
        }
      } catch (parseErr) {
        Logger.log("페르소나 파싱 예외: " + parseErr);
        personaSummaryText = "AI 가상 페르소나 데이터";
        personaListText = jsonContent;
      }
    }

    // 4. QuickChart REST API 호출을 통한 128d 임베딩 기반 다면 여론 지형도 차트 생성 및 저장
    var clusterMapFile = null;
    var pointsJson = readTextFile(feedbackFolder, "feedback_points_128d.json");
    var parsedPoints = [];
    if (pointsJson) {
      try {
        parsedPoints = JSON.parse(pointsJson);
      } catch (e) {}
    }
    if (parsedPoints && parsedPoints.length > 0) {
      clusterMapFile = renderAndSaveTsneClusterMap(feedbackFolder, parsedPoints);
    } else if (parsedPersonas && parsedPersonas.length > 0) {
      clusterMapFile = renderAndSaveTsneClusterMap(feedbackFolder, parsedPersonas);
    }

    var feedbackSourceDescription = "";
    if (hasVideoAnalysis && jsonContent) {
      feedbackSourceDescription = "고객 직접 촬영 동영상 VLM 분석(video_voc_analysis.json) 및 AI 가상 페르소나 25인 다면 평가단";
    } else if (hasHumanResponses && jsonContent) {
      feedbackSourceDescription = "구글 폼 실시간 고객 응답 (" + humanFeedbackRows.length + "건) 및 AI 가상 페르소나 25인 다면 평가단";
    } else if (jsonContent) {
      feedbackSourceDescription = "AI 가상 페르소나 전문 평가단 25인 실시간 피드백";
    } else {
      feedbackSourceDescription = "AI 가상 페르소나 기본 평가단 (25인)";
    }

    var feedbackInputPayload = "";
    if (hasHumanResponses) {
      feedbackInputPayload += "### [1. 구글 폼 사람이 직접 제출한 실시간 설문 응답 (총 " + humanFeedbackRows.length + "건)]\n" + humanFeedbackRows.join("\n") + "\n\n";
    } else {
      feedbackInputPayload += "### [1. 구글 폼 사람이 직접 제출한 실시간 설문 응답]\n- 제출 현황: 사람이 제출한 설문 응답 없음 (0건). 허구의 사람 응답을 절대 지어내지 말 것.\n\n";
    }

    if (hasVideoAnalysis && videoVocAnalysis) {
      feedbackInputPayload += "### [2. 실제 고객 촬영 동영상 피드백 VLM 심층 분석 데이터 (비디오 VoC, video_voc_analysis.json 연동)]\n" +
        "- 대상 영상 파일: " + (videoVocAnalysis.video_metadata ? videoVocAnalysis.video_metadata.file_name : "feedback_sample.mp4") + "\n" +
        "- 화자 및 역할: " + (videoVocAnalysis.speaker_analysis ? videoVocAnalysis.speaker_analysis.role : "고객") + "\n" +
        "- 실제 발화 전사(Transcript): \"" + (videoVocAnalysis.speaker_analysis ? videoVocAnalysis.speaker_analysis.transcribed_speech : "") + "\"\n" +
        "- 발화 의도: " + (videoVocAnalysis.speaker_analysis ? videoVocAnalysis.speaker_analysis.speech_intent : "") + "\n" +
        "- 얼굴 표정 및 감정: " + (videoVocAnalysis.speaker_analysis && videoVocAnalysis.speaker_analysis.facial_expression ? videoVocAnalysis.speaker_analysis.facial_expression.primary_emotion : "기대 및 호기심") + "\n" +
        "- 음성 톤 및 어조: " + (videoVocAnalysis.speaker_analysis && videoVocAnalysis.speaker_analysis.voice_tone ? videoVocAnalysis.speaker_analysis.voice_tone.tone : "친근하고 솔직함") + "\n" +
        "- VLM 종합 평가 점수: " + (videoVocAnalysis.multimodal_judging ? videoVocAnalysis.multimodal_judging.overall_weighted_score : 4.77) + "/5.0\n" +
        "- 비주얼 액션 아이템: " + (videoVocAnalysis.creative_direction_extracted && videoVocAnalysis.creative_direction_extracted.visual_action_items ? videoVocAnalysis.creative_direction_extracted.visual_action_items.join(", ") : "") + "\n" +
        "- 카피 액션 아이템: " + (videoVocAnalysis.creative_direction_extracted && videoVocAnalysis.creative_direction_extracted.copy_action_items ? videoVocAnalysis.creative_direction_extracted.copy_action_items.join(", ") : "") + "\n\n";
    } else if (hasVideoFeedback) {
      feedbackInputPayload += "### [2. 실제 제출된 고객 동영상 피드백 (비디오 VoC, 총 " + humanVideoRows.length + "건)]\n" + humanVideoRows.join("\n") + "\n\n";
    } else {
      feedbackInputPayload += "### [2. 실제 제출된 고객 동영상 피드백 (비디오 VoC)]\n- 제출 현황: 동영상 피드백 없음 (0건 미제출).\n- 영상이 제출되지 않았으므로 영상 분석, 표정, 음성 톤, 영상 발화 내용을 절대 상상으로 지어내지 말 것.\n\n";
    }

    if (personaListText) {
      feedbackInputPayload += "### [3. AI 가상 페르소나 25인 실제 평가 데이터 (" + personaSummaryText + ")]\n" + personaListText;
    }

    var videoRule = hasVideoFeedback
      ? "- 비디오 VoC 반영: 실제 분석된 동영상 피드백(video_voc_analysis.json)의 실제 발화 전사문, 고객의 얼굴 표정, 음성 톤을 본문에 충실히 인용하고, [정량 50%, 정성 30%, 비디오 VoC 20%] 가중치로 종합 점수를 산출하라.\n"
      : "- 비디오 VoC 미제출: 실제 제출된 동영상 피드백이 0건이다. 비디오 VoC 섹션에는 '제출된 동영상 피드백 없음 (미제출)'으로만 기록하고, 종합 점수 가중치는 [정량 평점 50%, 정성 의견 50%]로 산정하라.\n";

    var systemInstruction =
      "당신은 엔터프라이즈 마케팅 인공 지능의 전문 평가 위원장(LLM as a Judge)이다.\n" +
      "제공된 실제 데이터(AI 페르소나 25인 발화 + 고객 동영상 VLM 분석 JSON + 설문 응답)에만 철저히 근거하여 직전 공개 마케팅 콘텐츠(" + prevRvName + ")에 대한 사실 중심의 다면 평가 요약 보고서(feedback_summary)를 작성하라.\n\n" +
      "### 절대 원칙: 사실 기반 요약 및 환각 전면 배제:\n" +
      "1. 상상 및 소설 작성 엄격 금지: 제공된 데이터에 없는 가상의 인물, 지어낸 발화, 허구의 사건을 절대 날조하지 말 것. 오직 실제 인입된 데이터의 내용과 통계만을 객관적으로 요약하라.\n" +
      "2. 비디오 VoC 규약:\n" +
      videoRule +
      "3. 사람 설문 응답 및 AI 가상 페르소나 피드백 취합 규약:\n" +
      "   - 동영상 VoC가 있는 경우, 고객의 생생한 발화(\"...\")와 표정/음성 톤을 보고서 2번에 상세히 기술하라.\n" +
      "   - AI 가상 페르소나 25인의 실제 발화문과 평점 통계를 집계하여 3대 핵심 여론 동향(주류 호평, 비판 및 우려, 개선 제안)을 도출하라.\n" +
      "4. 필수 보고서 목차 구조:\n" +
      "   ## 1. 피드백 수집 및 분석 개요 (데이터 소스 건수, 비디오 VoC 제출 여부 명시)\n" +
      "   ## 2. 고객 동영상 VoC 멀티모달(VLM) 심층 분석 (표정, 음성 톤, 발화 전사, video_voc_analysis.json 연동)\n" +
      "   ## 3. 25인 AI 페르소나 여론 동향 분석 (실제 발화 및 통계 기반 주류 호평, 비판 및 우려, 개선 제안)\n" +
      "   ## 4. 사실 기반 종합 평가 점수 산출 (" + (hasVideoFeedback ? "정량 50%, 정성 30%, 비디오 VoC 20%" : "정량 50%, 정성 50% / 비디오 VoC 미제출") + ")\n" +
      "   ## 5. 차기 리비전(" + nextRvName + ") 반영 권고 사항 (Action Items 3대 실행 전략)\n" +
      "   ## 6. 마케터 최종 의사 결정 및 보정 지침 (Human-in-the-loop)\n" +
      "5. 산출물 서술 어조: 단호하고 격조 높은 문어체 평서문('-다' 체)을 엄격히 준수한다.\n" +
      "6. 한글 복합 명사는 철저하게 띄어 쓰고, 이모지와 중간 점을 일절 쓰지 말 것.\n" +
      "7. 분량 및 가독성: 마케터가 1분 안에 여론 동향을 빠르게 파악하고 의사 결정을 내릴 수 있도록 불릿 포인트 중심의 핵심 요약 리포트로 간결하게 작성하라.";

    var userPrompt =
      "다음 피드백 데이터를 분석하여 표준 형식의 사실 기반 종합 요약본(feedback_summary)을 작성하라.\n\n" +
      "[평가 대상 직전 공개 마케팅 콘텐츠: " + prevRvName + "]\n" +
      "[피드백 회차: " + targetRound + "]\n" +
      "[피드백 데이터 소스: " + feedbackSourceDescription + "]\n\n" +
      feedbackInputPayload;

    // 5. Gemini 호출
    var summaryResult = callGemini(systemInstruction, userPrompt, CONFIG.MODEL_JUDGE);

    if (summaryResult.indexOf("마케터 최종 의사 결정") === -1) {
      var defaultComment = "> **마케터 코멘트**: 출퇴근 피로감보다 주말 카페 힐링 감성을 강조하고, 180g 초경량 착용감을 헤드카피로 올릴 것. 노이즈 캔슬링 98% 차단 스펙은 본문 첫 단락에 신뢰성 있게 기술할 것.\n";
      if (roundNum === 2) {
        defaultComment = "> **마케터 코멘트**: 20대 한국인 여성 모델이 세련된 서울 카페에서 초경량 노이즈 캔슬링을 켜고 몰입하는 순간을 헤드카피와 비주얼로 전면에 내세울 것. 스펙 나열보다 감성적 힐링 공감을 극대화할 것.\n";
      } else if (roundNum >= 3) {
        defaultComment = "> **마케터 코멘트**: 그랜드 론칭 한정 얼리버드 혜택(고급 가죽 트래블 파우치 증정)을 볼드하게 명시하고, 한국인 20대 여성 모델과 5종 시그니처 파스텔 컬러 라인업을 담은 론칭 완결형 비주얼을 도출할 것.\n";
      }

      summaryResult += "\n\n---\n\n" +
        "## 6. 마케터 최종 의사 결정 및 보정 지침 (Human-in-the-loop)\n" +
        defaultComment;
    }

    // 6. 구글 드라이브 input/{targetRound}/feedback_summary 구글 독스 저장
    var summaryDocFile = saveGoogleDoc(feedbackFolder, "feedback_summary", summaryResult);

    // t-SNE 지형도 이미지가 생성된 경우 구글 독스 문서 본문 맨 상단에 임베드
    if (clusterMapFile) {
      try {
        var doc = DocumentApp.openById(summaryDocFile.getId());
        var body = doc.getBody();
        var mapBlob = clusterMapFile.getBlob();
        body.insertImage(0, mapBlob);
        var totalPointsCount = (parsedPoints && parsedPoints.length > 0) ? parsedPoints.length : (parsedPersonas.length || 25);
        var captionPara = body.insertParagraph(1, "[그림 1] 25인 AI 페르소나 열린 피드백 여론 지형도 (총 " + totalPointsCount + "개 세부 의견 포인트, text-multilingual-embedding-002 128d 임베딩 t-SNE)");
        captionPara.setFontSize(9).setFontColor("#64748B").setItalic(true);
        doc.saveAndClose();
      } catch (embedErr) {
        Logger.log("독스 내 지형도 이미지 임베드 예외: " + embedErr);
      }
    }

    // 7. 구글 시트 실행 대시보드에 다면 평가 결과 및 링크 기록
    var stepId = (targetRound === "fb-01") ? "Step 5" : "Step 8";
    var stepTitle = (targetRound === "fb-01") ? "1차 다면 평가 및 t-SNE 지형도 (fb-01)" : "2차 다면 평가 및 t-SNE 갱신 (fb-02)";
    recordStepResultToSheet(stepId, stepTitle, "완료", summaryDocFile.getUrl(), "피드백 요약서 열기 (" + targetRound + ")");

    if (!isSilent) {
      ui.alert(
        "다면 평가 완료 (" + targetRound + ")",
        "25인 AI 페르소나 및 고객 피드백 다면 평가 리포트(t-SNE 지형도 포함) 생성이 완료되었습니다.\n\n구글 시트의 [실행 대시보드] 표에서 '피드백 요약서 열기' 링크를 확인하십시오.",
        ui.ButtonSet.OK
      );
    }
    return summaryResult;
  } catch (e) {
    if (!isSilent) {
      ui.alert("평가 중 오류 발생", e.toString(), ui.ButtonSet.OK);
    } else {
      throw e;
    }
  }
}

function resolveDriveAttachmentName(rawVal) {
  if (typeof rawVal !== "string") {
    return rawVal;
  }

  var drivePattern = /https:\/\/drive\.google\.com\/(?:open\?id=|file\/d\/)([a-zA-Z0-9_-]+)/g;
  var match = drivePattern.exec(rawVal);
  if (!match) {
    return rawVal;
  }

  var found = false;
  var resolvedTexts = [];

  var regex = /https:\/\/drive\.google\.com\/(?:open\?id=|file\/d\/)([a-zA-Z0-9_-]+)[^\s,]*/g;
  var m;
  while ((m = regex.exec(rawVal)) !== null) {
    found = true;
    var fileId = m[1];
    var fullUrl = m[0];
    try {
      var file = DriveApp.getFileById(fileId);
      var fileName = file.getName();
      var mimeType = file.getMimeType();
      resolvedTexts.push(fileName + " (" + mimeType + ", 자동 첨부 링크: " + fullUrl + ")");
    } catch (driveErr) {
      resolvedTexts.push(fullUrl);
    }
  }

  if (found && resolvedTexts.length > 0) {
    return resolvedTexts.join(", ");
  }

  return rawVal;
}
