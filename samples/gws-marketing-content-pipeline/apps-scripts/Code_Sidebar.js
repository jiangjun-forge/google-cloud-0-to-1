/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 9] 구글 시트 우측 패널(Sidebar) 모던 HTML 컨트롤 타워 UI
 */

/**
 * 우측 패널(사이드바) 인라인 입력창에서 전달된 Gemini API Key를 검증 및 저장한다.
 *
 * @param {string} apiKey - 입력된 API Key
 * @return {Object} 처리 결과 { success: boolean, message: string }
 */
function saveApiKeyInline(apiKey) {
  if (!apiKey || typeof apiKey !== "string") {
    return { success: false, message: "유효한 API Key를 입력해 주십시오." };
  }
  var cleanKey = apiKey.trim();
  if (cleanKey.length < 10) {
    return { success: false, message: "API Key 형식이 올바르지 않습니다. (최소 10자 이상)" };
  }

  try {
    PropertiesService.getUserProperties().setProperty("GEMINI_API_KEY", cleanKey);
    return { success: true, message: "Gemini API Key가 성공적으로 등록되었습니다." };
  } catch (e) {
    return { success: false, message: "API Key 저장 중 오류: " + e.toString() };
  }
}

/**
 * Gemini API 호출 실패 또는 파싱 오류 시 100% 무중단 안내를 보장하는 결정론적 룰 기반 폴백 엔진
 *
 * @param {string} userMessage - 마케터의 질문 텍스트
 * @param {Object} status - 현재 파이프라인 실제 상태 객체
 * @return {Object} { success: boolean, reply: string, action: string|null, actionLabel: string|null, taskName: string|null }
 */
function getDeterministicFallback(userMessage, status) {
  var q = (userMessage || "").toLowerCase().replace(/\s+/g, "");

  // 0. 산출물 조회 및 링크 요청 인터셉트 ("어디", "링크", "열어", "보여", "주소", "확인", "찾아", "열기")
  var isQueryForLocation = (
    q.indexOf("어디") !== -1 || q.indexOf("링크") !== -1 || q.indexOf("열어") !== -1 ||
    q.indexOf("보여") !== -1 || q.indexOf("주소") !== -1 || q.indexOf("확인") !== -1 ||
    q.indexOf("열기") !== -1 || q.indexOf("찾아") !== -1
  );

  if (isQueryForLocation) {
    if (q.indexOf("내역") !== -1 || q.indexOf("로그") !== -1 || q.indexOf("대시보드") !== -1) {
      return {
        success: true,
        reply: "파이프라인 단계별 처리 결과와 산출물 링크가 기록된 [실행 내역] 시트 탭이야.",
        action: "openDashboardSheet",
        actionLabel: "[실행 내역 열기]",
        taskName: "실행 내역 시트 열기"
      };
    }
    if ((q.indexOf("기획") !== -1 || q.indexOf("plan") !== -1) && status.planDocUrl) {
      return {
        success: true,
        reply: "캠페인 기획서(PLAN) 구글 독스 준비해 뒀어. 아래 링크 눌러서 바로 열어봐.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + status.planDocUrl + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[PLAN 기획서 열기]</a></div>"
      };
    }
    if ((q.indexOf("명세") !== -1 || q.indexOf("spec") !== -1) && status.specDocUrl) {
      return {
        success: true,
        reply: "멀티 채널 콘텐츠 제작 명세서(SPEC) 구글 독스야.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + status.specDocUrl + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[SPEC 명세서 열기]</a></div>"
      };
    }
    if (q.indexOf("아이디어") !== -1 && status.ideaDocUrl) {
      return {
        success: true,
        reply: "캠페인 원천 [아이디어 메모] 구글 독스야.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + status.ideaDocUrl + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[아이디어 메모 열기]</a></div>"
      };
    }
    if ((q.indexOf("콘텐츠") !== -1 || q.indexOf("카피") !== -1 || q.indexOf("초판") !== -1) && status.contentDocUrl) {
      var rvTag = status.latestRv || "rv-00";
      return {
        success: true,
        reply: "현재 최신 마케팅 콘텐츠(" + rvTag + ") 구글 독스야.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + status.contentDocUrl + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[콘텐츠 독스 열기 (" + rvTag + ")]</a></div>"
      };
    }
    if ((q.indexOf("보고서") !== -1 || q.indexOf("요약") !== -1 || q.indexOf("피드백") !== -1) && status.summaryDocUrl) {
      var fbTag = status.latestFb || "fb-01";
      return {
        success: true,
        reply: "피드백 종합 분석 보고서(feedback_summary) 구글 독스야.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + status.summaryDocUrl + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[피드백 보고서 열기 (" + fbTag + ")]</a></div>"
      };
    }
    if (q.indexOf("지침") !== -1 && status.directiveDocUrl) {
      var fbTag2 = status.latestFb || "fb-01";
      return {
        success: true,
        reply: "마케터 전용 [마케터 보정 지침] 구글 독스야.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + status.directiveDocUrl + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[마케터 보정 지침 열기 (" + fbTag2 + ")]</a></div>"
      };
    }
    if ((q.indexOf("설문") !== -1 || q.indexOf("폼") !== -1 || q.indexOf("form") !== -1) && status.formUrl) {
      return {
        success: true,
        reply: "고객 VoC 수집용 온라인 설문 폼(Google Forms)이야.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + status.formUrl + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[고객 설문 폼 열기]</a></div>"
      };
    }
    if ((q.indexOf("피드백") !== -1 || q.indexOf("json") !== -1 || q.indexOf("데이터셋") !== -1) && (status.feedbackJsonUrl || status.jsonUrl)) {
      var fbTag3 = status.latestFb || "fb-01";
      var jsonLink = status.feedbackJsonUrl || status.jsonUrl;
      return {
        success: true,
        reply: "타깃 AI 가상 페르소나 패널의 정밀 다면 평가 데이터셋(JSON) 원본 파일이야.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + jsonLink + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[AI 페르소나 피드백 JSON 열기 (" + fbTag3 + ")]</a></div>"
      };
    }
    if ((q.indexOf("폴더") !== -1 || q.indexOf("드라이브") !== -1) && status.folderUrl) {
      return {
        success: true,
        reply: "캠페인 구글 드라이브 루트 폴더야.",
        action: null,
        actionLabel: null,
        taskName: null,
        actionBtnHtml: "<div style='margin-top:6px;'><a href='" + status.folderUrl + "' target='_blank' style='display:inline-block; padding:4px 8px; font-size:11px; background:#1a73e8; color:#ffffff; border-radius:4px; text-decoration:none; font-weight:600;'>[드라이브 폴더 열기]</a></div>"
      };
    }
  }

  // 1. 현재 상태 질의 ("지금뭐해야", "다음단계", "어떻게", "순서")
  if (q.indexOf("지금") !== -1 || q.indexOf("다음") !== -1 || q.indexOf("순서") !== -1 || q.indexOf("뭐해") !== -1) {
    if (!status.folderUrl) {
      return {
        success: true,
        reply: "캠페인 작업 공간이 아직 안 만들어졌어. 먼저 [Step 0: 작업 공간 구축]을 진행해줘.",
        action: "initCampaignWorkspace",
        actionLabel: "[Step 0] 캠페인 작업 공간 구축",
        taskName: "캠페인 작업 공간 구축"
      };
    }
    if (!status.hasApiKey) {
      return {
        success: true,
        reply: "Gemini API Key가 등록되지 않았어. 사이드바 상단에서 API Key를 먼저 등록해줘.",
        action: "toggleApiKeyBox",
        actionLabel: "API Key 등록하기",
        taskName: "API Key 설정"
      };
    }
    if (!status.ideaDocUrl) {
      return {
        success: true,
        reply: "현재 캠페인 폴더에 아이디어 메모가 없어. [Step 1] 캠페인 아이디어 메모 작성을 진행해줘.",
        action: "promptAndRunIdeaMemo",
        actionLabel: "[Step 1] 아이디어 메모 작성하기",
        taskName: "아이디어 메모 작성"
      };
    }
    if (!status.planDocUrl) {
      return {
        success: true,
        reply: "캠페인 폴더에 아이디어 메모 확인 완료! 다음 단계인 [Step 2] 캠페인 기획서(PLAN) 생성을 진행하자.",
        action: "guardAndRunIdeaToPlan",
        actionLabel: "[Step 2] 기획서(PLAN) 생성하기",
        taskName: "캠페인 기획서 생성"
      };
    }
    if (!status.specDocUrl) {
      return {
        success: true,
        reply: "기획서(PLAN) 확인 완료! 다음 단계인 [Step 3] 콘텐츠 제작 명세서(SPEC) 생성을 진행할 차례야.",
        action: "guardAndRunPlanToSpec",
        actionLabel: "[Step 3] 제작 명세서(SPEC) 생성하기",
        taskName: "제작 명세서 생성"
      };
    }
    if (!status.personaUrl) {
      return {
        success: true,
        reply: "기획서(PLAN)랑 제작 명세서(SPEC) 확인 완료! 다음 단계인 [Step 4] 맞춤 AI 페르소나 패널 구성을 진행하자.",
        action: "guardAndRunPersonaSynthesis",
        actionLabel: "[Step 4] 맞춤 AI 페르소나 패널 구성하기",
        taskName: "AI 페르소나 패널 구성"
      };
    }
    if (!status.contentDocUrl) {
      return {
        success: true,
        reply: "기획서, 제작 명세서, 맞춤 AI 페르소나 패널이 모두 준비됐어. 이제 [Step 5: 초판 멀티 채널 콘텐츠(rv-00) 생성]을 진행할 차례야.",
        action: "guardAndRunInitialContent",
        actionLabel: "[Step 5] 초판 콘텐츠 (rv-00) 제작하기",
        taskName: "초판 콘텐츠 생성"
      };
    }
    var curStepNum = status.currentStep || 0;
    var targetFb = status.activeFbTag || "fb-01";
    var curRv = status.activeRvTag || (status.latestRv || "rv-00");
    var nextRv = status.nextRvTag || "rv-01";

    if (curStepNum === 6 || !status.feedbackJsonUrl) {
      var isRevision = (status.latestRvNum !== undefined && status.latestRvNum > 0);
      var msg6 = isRevision
        ? ("개정본 콘텐츠(" + curRv + ") 제작이 완료됐어! 이제 이 개정본에 대해 다음 차수 [Step 6: AI 페르소나 다면 평가(" + targetFb + ")]를 실행할 차례야.")
        : ("초판 마케팅 콘텐츠(rv-00) 확인 완료! 다음 단계인 [Step 6: AI 페르소나 다면 평가(" + targetFb + ") 실행]을 진행해줘.");
      return {
        success: true,
        reply: msg6,
        action: "promptAndRunJudgeEvaluation",
        actionLabel: "[Step 6] AI 페르소나 다면 평가 (" + targetFb + ") 실행하기",
        taskName: "AI 페르소나 다면 평가"
      };
    }
    if (curStepNum === 7 || !status.summaryDocUrl) {
      return {
        success: true,
        reply: "AI 페르소나 다면 평가 데이터(" + targetFb + ")가 확인됐어. 다음 단계인 [Step 7: 피드백 종합 분석 보고서 생성]을 진행할 차례야.",
        action: "promptAndRunFeedbackSummary",
        actionLabel: "[Step 7] 피드백 종합 보고서 (" + targetFb + ") 생성하기",
        taskName: "피드백 종합 보고서 생성"
      };
    }
    if (curStepNum === 8 || !status.directiveDocUrl) {
      return {
        success: true,
        reply: "피드백 종합 분석 보고서(" + targetFb + ") 확인 완료! 다음 단계인 [Step 8] 마케터 보정 지침 작성/확정을 진행하자.",
        action: "promptAndRunMarketerDirective",
        actionLabel: "[Step 8] 마케터 보정 지침 (" + targetFb + ") 작성하기",
        taskName: "마케터 보정 지침 작성"
      };
    }
    return {
      success: true,
      reply: "마케터 보정 지침(" + targetFb + ")이 확정됐어. 마지막 단계인 [Step 9: 피드백 반영 개정본(" + nextRv + ") 생성]을 진행하자.",
      action: "promptAndRunFeedbackRevision",
      actionLabel: "[Step 9] 피드백 반영 콘텐츠 (" + nextRv + ") 보정하기",
      taskName: "피드백 반영 콘텐츠 보정"
    };
  }

  // 2. 기획서 요청 ("기획", "plan")
  if (q.indexOf("기획") !== -1 || q.indexOf("plan") !== -1) {
    return {
      success: true,
      reply: "캠페인 기획서(PLAN)랑 콘텐츠 제작 명세서(SPEC) 도출을 시작할게.",
      action: "guardAndRunIdeaToPlan",
      actionLabel: "기획서 (PLAN & SPEC) 도출하기",
      taskName: "기획서 및 명세서 생성"
    };
  }

  // 3-1. 초판 강제 재생성 요청 ("다시", "덮어", "재생성")
  if ((q.indexOf("다시") !== -1 || q.indexOf("덮어") !== -1 || q.indexOf("재생성") !== -1) && (q.indexOf("초판") !== -1 || q.indexOf("콘텐츠") !== -1)) {
    return {
      success: true,
      reply: "기존 초판 콘텐츠(rv-00)를 새로 덮어쓰고 전체 에셋(카피, 이미지 3종, 숏폼 영상)을 다시 만들게.",
      action: "forceRunInitialContent",
      actionLabel: "초판 콘텐츠 전체 재생성하기",
      taskName: "초판 콘텐츠 전체 재생성"
    };
  }

  // 3. 초판/콘텐츠 요청 ("초판", "콘텐츠", "카피", "이미지", "영상", "제작")
  if (q.indexOf("초판") !== -1 || q.indexOf("콘텐츠") !== -1 || q.indexOf("제작") !== -1 || q.indexOf("카피") !== -1) {
    return {
      success: true,
      reply: "초판 마케팅 콘텐츠(카피라이팅, 비주얼 이미지 3종, Veo 숏폼 영상) 세트 생성을 시작할게.",
      action: "guardAndRunInitialContent",
      actionLabel: "초판 콘텐츠 (rv-00) 제작하기",
      taskName: "초판 콘텐츠 생성"
    };
  }

  // 4. 평가 요청 ("페르소나", "다면평가", "평가", "25인")
  if (q.indexOf("25인") !== -1 || q.indexOf("페르소나") !== -1 || q.indexOf("평가") !== -1) {
    if (q.indexOf("뭐야") !== -1 || q.indexOf("설명") !== -1) {
      return {
        success: true,
        reply: "AI 페르소나 다면 평가는 대한민국 시장 환경과 타깃 오디언스를 대변하는 맞춤 가상 소비자 패널이 정량 평점과 구체적인 VoC를 제공하는 다면 평가 시스템이야.",
        action: "promptAndRunPersonaEvaluation",
        actionLabel: "AI 페르소나 다면 평가 실행하기",
        taskName: "AI 페르소나 다면 평가"
      };
    }
    return {
      success: true,
      reply: "맞춤 AI 페르소나 다면 평가(fb-xx)를 실행할게.",
      action: "promptAndRunPersonaEvaluation",
      actionLabel: "AI 페르소나 다면 평가 실행하기",
      taskName: "AI 페르소나 다면 평가"
    };
  }

  // 5. 보고서 요청 ("보고서", "요약서", "피드백")
  if (q.indexOf("보고서") !== -1 || q.indexOf("피드백") !== -1 || q.indexOf("요약") !== -1) {
    return {
      success: true,
      reply: "고객 VoC 및 VLM 멀티모달 분석, AI 페르소나 다면 평가 데이터가 종합된 피드백 분석 보고서를 도출할게.",
      action: "promptAndRunFeedbackSummary",
      actionLabel: "피드백 종합 보고서 생성하기",
      taskName: "피드백 종합 보고서 생성"
    };
  }

  // 6. 보정 요청 ("보정", "개정", "리비전", "수정")
  if (q.indexOf("보정") !== -1 || q.indexOf("개정") !== -1 || q.indexOf("리비전") !== -1) {
    return {
      success: true,
      reply: "마케터 보정 지침을 최우선 반영해서 차기 리비전 마케팅 콘텐츠를 개정 보정할게.",
      action: "promptAndRunFeedbackRevision",
      actionLabel: "피드백 반영 콘텐츠 보정하기",
      taskName: "피드백 반영 콘텐츠 보정"
    };
  }

  // 7. 피드백 JSON 데이터셋 질문 ("json", "데이터셋", "피드백 데이터")
  if (q.indexOf("json") !== -1 || q.indexOf("데이터셋") !== -1 || q.indexOf("페르소나 데이터") !== -1 || q.indexOf("피드백 데이터") !== -1) {
    return {
      success: true,
      reply: "AI 페르소나 피드백 데이터셋은 맞춤 가상 소비자 패널의 정량 평점과 항목별 상세 정성 의견이 담긴 구조화된 JSON 데이터야.",
      action: null,
      actionLabel: null,
      taskName: null
    };
  }

  // 8. 초기화 요청 ("초기화", "구축", "셋업", "공간")
  if (q.indexOf("초기화") !== -1 || q.indexOf("구축") !== -1 || q.indexOf("셋업") !== -1) {
    return {
      success: true,
      reply: "캠페인 부모 폴더를 감지하고 누락된 리소스를 안전하게 핀포인트 복구할게.",
      action: "initCampaignWorkspace",
      actionLabel: "[초기화] 캠페인 작업 공간 구축",
      taskName: "캠페인 작업 공간 구축"
    };
  }

  // 9. 기본 fallback
  return {
    success: true,
    reply: "마케팅 콘텐츠 파이프라인 제어 패널이야. 원하는 작업을 아래 버튼에서 선택하거나 '지금 뭐 해야 돼?'라고 물어봐줘.",
    action: null,
    actionLabel: null,
    taskName: null
  };
}

/**
 * 마케터의 자연어 질의를 수신하여 현재 파이프라인 상태를 진단하고 안내 및 동적 액션 칩을 반환한다.
 *
 * @param {string} userMessage - 마케터가 입력한 자연어 질문 또는 지시
 * @return {Object} { success: boolean, reply: string, action: string|null, actionLabel: string|null, taskName: string|null }
 */
function askPipelineAssistant(userMessage) {
  if (!userMessage || typeof userMessage !== "string" || !userMessage.trim()) {
    return {
      success: false,
      reply: "질문이나 실행할 작업을 입력해줘.",
      action: null,
      actionLabel: null,
      taskName: null
    };
  }

  var status = getPipelineStatus(true);
  var apiKey = getGeminiApiKey();
  if (!apiKey) {
    return {
      success: true,
      reply: "Gemini API Key가 아직 등록되지 않았어. 상단 배너에서 [API Key 설정] 버튼을 눌러 먼저 키를 등록해줘.",
      action: null,
      actionLabel: null,
      taskName: null
    };
  }

  // 1. 마케터의 자연어 아이디어 입력 직접 감지 및 [아이디어 메모] 자동 저장
  var trimmedMsg = userMessage.trim();
  if (trimmedMsg.indexOf("아이디어:") === 0 || trimmedMsg.indexOf("아이디어 :") === 0 || trimmedMsg.indexOf("아이디어는 ") === 0) {
    var ideaText = trimmedMsg.replace(/^(아이디어\s*:\s*|아이디어는\s*)/, "").trim();
    if (ideaText.length >= 3) {
      try {
        var campaignFolder = getCampaignFolder();
        saveGoogleDoc(campaignFolder, (CONFIG && CONFIG.IDEA_DOC_NAME) || "아이디어 메모", ideaText);
        return {
          success: true,
          reply: "새로운 캠페인 아이디어가 [아이디어 메모] 구글 독스에 잘 들어갔어:\n[" + ideaText + "]\n\n지금 바로 전문 기획서(PLAN)랑 제작 명세서(SPEC)를 뽑아볼까?",
          action: "guardAndRunIdeaToPlan",
          actionLabel: "기획서 (PLAN & SPEC) 도출하기",
          taskName: "기획서 및 명세서 생성"
        };
      } catch (saveErr) {
        return {
          success: true,
          reply: "아이디어를 저장하기 전에 먼저 캠페인 작업 공간 구축이 필요해.",
          action: "initCampaignWorkspace",
          actionLabel: "[초기화] 캠페인 작업 공간 구축",
          taskName: "캠페인 작업 공간 구축"
        };
      }
    }
  }

  var activeFb = status.activeFbTag || "fb-01";
  var activeRv = status.activeRvTag || (status.latestRv || "rv-00");
  var nextRv = status.nextRvTag || "rv-01";

  var contextSummary = [
    "- 캠페인 폴더: " + (status.folderUrl ? "연결됨 (" + status.campaignCode + ")" : "미구축 (초기화 필요)"),
    "- 아이디어 메모: " + (status.ideaDocUrl ? "작성 문서 있음" : "문서 없음 (초기화 필요)"),
    "- 기획서 (PLAN): " + (status.planDocUrl ? "생성 완료" : "미생성"),
    "- 제작 명세서 (SPEC): " + (status.specDocUrl ? "생성 완료" : "미생성"),
    "- 맞춤 AI 페르소나 패널: " + (status.personaUrl ? "구성 완료" : "미생성"),
    "- 최신 콘텐츠 리비전: " + (status.contentDocUrl ? "생성 완료 (" + activeRv + ")" : "미생성"),
    "- 고객 VoC 설문 폼: " + (status.formUrl ? "생성 및 시트 연결 완료" : "미생성"),
    "- 현재 활성 피드백 차수: " + activeFb + " (대상 콘텐츠: " + activeRv + ")",
    "- AI 페르소나 피드백 데이터 (JSON): " + (status.feedbackJsonUrl ? "생성 완료 (" + activeFb + ")" : "미생성 (" + activeFb + ")"),
    "- 최신 피드백 종합 보고서: " + (status.summaryDocUrl ? "생성 완료 (" + activeFb + ")" : "미생성 (" + activeFb + ")"),
    "- 마케터 보정 지침서: " + (status.directiveDocUrl ? "확정 완료 (" + activeFb + ")" : "미생성 (" + activeFb + ")"),
    "- 현재 파이프라인 단계 및 추천 액션: " + (status.stepLabel || "파이프라인 진행 중")
  ].join("\n");

  var systemInstruction = 
    "당신은 구글 드라이브 마케팅 콘텐츠 파이프라인의 전담 AI 코파일럿 어시스턴트이다.\n" +
    "비개발자 마케터와 편안하고 전문적인 동료로서 대화하며, 캠페인을 성공적으로 이끌 수 있도록 돕는다.\n" +
    "현재 구글 드라이브 및 스프레드시트의 파이프라인 실제 상태는 다음과 같다:\n" +
    contextSummary + "\n\n" +
    "[파이프라인 지원 가능 액션 식별자 목록]\n" +
    "- 'initCampaignWorkspace': [Step 0] API Key & 작업 공간 구축\n" +
    "- 'promptAndRunIdeaMemo': [Step 1] 캠페인 아이디어 메모 작성\n" +
    "- 'guardAndRunIdeaToPlan': [Step 2] 캠페인 기획서(PLAN) 생성\n" +
    "- 'guardAndRunPlanToSpec': [Step 3] 제작 명세서(SPEC) 생성\n" +
    "- 'guardAndRunPersonaSynthesis': [Step 4] 맞춤 AI 페르소나 패널 구성\n" +
    "- 'guardAndRunInitialContent': [Step 5] 초판 멀티 채널 콘텐츠 생성 (rv-00)\n" +
    "- 'forceRunInitialContent': [Step 5] 초판 콘텐츠 전체 강제 재생성\n" +
    "- 'promptAndRunJudgeEvaluation': [Step 6] AI 페르소나 다면 평가 실행 (" + activeFb + ")\n" +
    "- 'promptAndRunFeedbackSummary': [Step 7] 피드백 종합 분석 보고서 생성 (" + activeFb + ")\n" +
    "- 'promptAndRunMarketerDirective': [Step 8] 마케터 보정 지침 작성/확정 (" + activeFb + ")\n" +
    "- 'promptAndRunFeedbackRevision': [Step 9] 피드백 반영 개정본 생성 (" + nextRv + ")\n" +
    "- 'openDashboardSheet': 실행 내역 시트 탭 열기\n" +
    "- 'refreshStatus': 사이드바 상태 새로고침\n\n" +
    "[응답 지침 및 대화 톤앤매너 - 절대 준수]\n" +
    "1. 대화 어조 원칙 (매우 중요):\n" +
    "   - 마케터와의 대화는 경어(존댓말: '~하십시오', '~입니다', '~했습니다')를 일절 쓰지 않는다.\n" +
    "   - 친근하고 전문적인 구어체(반말 대화체: '~야', '~해', '~했어', '~하자', '~볼게', '~하면 돼')로만 답변한다.\n" +
    "   - 마케터와 함께 일하는 페어 프로그래머이자 든든한 동료 엔지니어처럼 편안하고 자신감 있는 어조를 유지한다.\n" +
    "2. 질문 의도별 대응:\n" +
    "   - '지금 뭐 해야 돼?', '다음 단계 알려줘' 등 현재 상태 질의: 현재 완료된 상태와 다음에 진행해야 할 단계를 친근하게 안내하고 해당 액션을 제시하라.\n" +
    "   - '기획서 만들어 줘', '초판 제작해 줘' 등 작업 지시: 바로 실행할 수 있도록 안내하고 액션을 제시하라.\n" +
    "   - 'AI 페르소나 피드백 데이터가 뭐야?' 등 개념 질의: 1~3문장으로 비개발자 마케터 눈높이에 맞추어 핵심 가치를 설명하라. (이 경우 action은 null)\n" +
    "3. 만약 마케터가 특정 단계를 지시했는데 선결 조건(예: 기획서 없이 초판 생성)이 누락되었다면, 친절하게 선행 작업을 먼저 해야 함을 설명하고 선행 작업 액션을 제시하라.\n" +
    "4. 출력은 마크다운 코드블록(```json) 없이 오직 단일 순수 JSON 객체만 반환하라:\n" +
    "{\n" +
    "  \"reply\": \"마케터에게 전달할 경어가 전혀 없는 친근한 구어체 반말 답변 (1~3문장: '~야', '~해', '~했어', '~하면 돼')\",\n" +
    "  \"action\": \"위 목록의 액션 식별자 문자열 또는 null\",\n" +
    "  \"actionLabel\": \"마케터에게 노출할 버튼 칩 텍스트 (예: 기획서 (PLAN) 도출하기) 또는 null\",\n" +
    "  \"taskName\": \"실행할 작업 명칭 (예: 기획서 및 명세서 생성) 또는 null\"\n" +
    "}";

  try {
    var copilotModel = (CONFIG && CONFIG.MODEL_COPILOT) || "gemini-3.8-flash";
    var rawResponse = callGemini(systemInstruction, userMessage.trim(), copilotModel, 1024);
    var cleanJson = (rawResponse || "").trim();
    if (cleanJson.indexOf("```json") !== -1) {
      cleanJson = cleanJson.split("```json")[1].split("```")[0].trim();
    } else if (cleanJson.indexOf("```") !== -1) {
      cleanJson = cleanJson.split("```")[1].split("```")[0].trim();
    }
    var firstBrace = cleanJson.indexOf("{");
    var lastBrace = cleanJson.lastIndexOf("}");
    if (firstBrace !== -1 && lastBrace !== -1) {
      cleanJson = cleanJson.substring(firstBrace, lastBrace + 1);
    }
    var parsed = JSON.parse(cleanJson);
    if (parsed && parsed.reply) {
      return {
        success: true,
        reply: parsed.reply,
        action: parsed.action || null,
        actionLabel: parsed.actionLabel || null,
        taskName: parsed.taskName || null
      };
    }
    return getDeterministicFallback(userMessage, status);
  } catch (err) {
    Logger.log("askPipelineAssistant API 호출/파싱 실패, 결정론적 폴백 가동: " + err);
    return getDeterministicFallback(userMessage, status);
  }
}

/**
 * 구글 시트 우측 패널에 마케팅 콘텐츠 파이프라인 컨트롤 타워를 표시한다.
 */
function showPipelineSidebar() {
  var ui = SpreadsheetApp.getUi();
  try {
    initDashboardSheet();
    var htmlOutput = HtmlService.createHtmlOutput(getPipelineSidebarHtml())
      .setTitle("마케팅 콘텐츠 파이프라인 제어 패널")
      .setWidth(340);
    ui.showSidebar(htmlOutput);
  } catch (err) {
    Logger.log("showPipelineSidebar 예외: " + err);
  }
}

/**
 * 파이프라인 상태 캐시를 무효화(Purge)한다.
 */
function invalidatePipelineStatusCache() {
  try {
    CacheService.getUserCache().remove("PIPELINE_STATUS_CACHE");
  } catch (e) {
    // 무시
  }
}

/**
 * 사이드바 화면 렌더링에 필요한 현재 캠페인 파이프라인 상태 정보를 반환한다.
 * DriveApp API 할당량 고갈 방지 및 고속 응답을 위해 30초 로컬 사용자 캐시(CacheService)를 적용한다.
 *
 * @param {boolean} [optBypassCache=false] - 캐시 우회 여부
 * @return {Object} 캠페인 작업 공간 상태, 산출물 URL, 리비전, 토큰 통계 객체
 */
function getPipelineStatus(optBypassCache) {
  var cacheKey = "PIPELINE_STATUS_CACHE";
  var cache = null;
  try {
    cache = CacheService.getUserCache();
    if (!optBypassCache && cache) {
      var cachedStr = cache.get(cacheKey);
      if (cachedStr) {
        return JSON.parse(cachedStr);
      }
    }
  } catch (e) {
    // 캐시 조회 실패 시 드라이브 직접 스캔 진행
  }

  try {
    initDashboardSheet();
  } catch (e) {
    // 무시
  }
  var status = {
    hasApiKey: !!getGeminiApiKey(),
    campaignCode: "BwG-Seoul-Ignite",
    folderUrl: "",
    ideaDocUrl: "",
    planDocUrl: "",
    specDocUrl: "",
    contentDocUrl: "",
    formUrl: "",
    summaryDocUrl: "",
    directiveDocUrl: "",
    latestRv: "rv-00",
    latestFb: "",
    currentStep: 0,
    stepLabel: "Step 0: 작업 공간 구축 대기",
    progressPercent: 0,
    totalTokens: getSessionTotalTokens() || 0
  };

  try {
    var folder = getCampaignFolder(true);
    if (folder) {
      status.folderUrl = folder.getUrl();
      var folderName = folder.getName();
      status.campaignCode = folderName.length > 20 ? folderName.substring(0, 18) + "..." : folderName;

      // 1. 아이디어 메모 탐색
      var ideaName = (CONFIG && CONFIG.IDEA_DOC_NAME) || "아이디어 메모";
      var ideaFiles = folder.getFilesByName(ideaName);
      if (!ideaFiles.hasNext()) {
        ideaFiles = folder.getFilesByName("[아이디어 메모] 2026 가을 오텀 브리즈 캠페인");
      }
      if (ideaFiles.hasNext()) {
        status.ideaDocUrl = ideaFiles.next().getUrl();
      } else {
        var rootIdeaScan = folder.getFiles();
        while (rootIdeaScan.hasNext()) {
          var rif = rootIdeaScan.next();
          var rifName = rif.getName().toLowerCase();
          if (rifName.indexOf("아이디어") !== -1 || rifName.indexOf("idea") !== -1) {
            status.ideaDocUrl = rif.getUrl();
            break;
          }
        }
      }

      // 2. 기획서 (PLAN) 탐색 (확장자 유무 불문)
      var planFiles = folder.getFilesByName("PLAN");
      if (!planFiles.hasNext()) planFiles = folder.getFilesByName("PLAN.md");
      if (!planFiles.hasNext()) planFiles = folder.getFilesByName("마케팅 캠페인 기획서");
      if (planFiles.hasNext()) {
        status.planDocUrl = planFiles.next().getUrl();
      } else {
        var rootPlanScan = folder.getFiles();
        while (rootPlanScan.hasNext()) {
          var rpf = rootPlanScan.next();
          var rpfName = rpf.getName().toLowerCase();
          if (rpfName.indexOf("plan") !== -1 || rpfName.indexOf("기획서") !== -1) {
            status.planDocUrl = rpf.getUrl();
            break;
          }
        }
      }

      // 3. 제작 명세서 (SPEC) 탐색 (확장자 유무 불문)
      var specFiles = folder.getFilesByName("SPEC");
      if (!specFiles.hasNext()) specFiles = folder.getFilesByName("SPEC.md");
      if (specFiles.hasNext()) {
        status.specDocUrl = specFiles.next().getUrl();
      } else {
        var rootSpecScan = folder.getFiles();
        while (rootSpecScan.hasNext()) {
          var rsf = rootSpecScan.next();
          var rsfName = rsf.getName().toLowerCase();
          if (rsfName.indexOf("spec") !== -1 || rsfName.indexOf("명세서") !== -1) {
            status.specDocUrl = rsf.getUrl();
            break;
          }
        }
      }

      // 3-1. 맞춤 AI 페르소나 패널 탐색
      var personaFiles = folder.getFilesByName((CONFIG && CONFIG.PERSONA_FILE_NAME) || "ai_personas.json");
      if (personaFiles.hasNext()) {
        status.personaUrl = personaFiles.next().getUrl();
      } else {
        var rootPersonaScan = folder.getFiles();
        while (rootPersonaScan.hasNext()) {
          var rper = rootPersonaScan.next();
          var rperName = rper.getName().toLowerCase();
          if (rperName.indexOf("persona") !== -1 || rperName.indexOf("페르소나") !== -1) {
            status.personaUrl = rper.getUrl();
            break;
          }
        }
      }

      // 4. 고객 VoC 설문 폼 탐색
      var formFiles = folder.getFilesByType(MimeType.GOOGLE_FORMS);
      if (formFiles.hasNext()) status.formUrl = formFiles.next().getUrl();

      // 5. 최신 리비전 콘텐츠 탐색
      var latestRvNum = detectLatestRevisionRoundNum();
      status.latestRvNum = latestRvNum;
      if (latestRvNum >= 0) {
        status.latestRv = "rv-" + (latestRvNum < 10 ? "0" + latestRvNum : latestRvNum);
        var rvFolder = getCampaignSubFolder(["output", status.latestRv], true);
        var contentDocName = (CONFIG && CONFIG.CONTENT_DOC_NAME) || "campaign_content";
        var contentFiles = rvFolder.getFilesByName(contentDocName);
        if (!contentFiles.hasNext()) contentFiles = rvFolder.getFilesByName(contentDocName + ".md");
        if (!contentFiles.hasNext()) contentFiles = rvFolder.getFilesByName("campaign_content");
        if (!contentFiles.hasNext()) contentFiles = rvFolder.getFilesByName("campaign_content.md");
        if (!contentFiles.hasNext()) contentFiles = rvFolder.getFilesByName("campaign_asset");
        if (contentFiles.hasNext()) {
          status.contentDocUrl = contentFiles.next().getUrl();
        } else {
          // 이름에 content, asset, 카피가 포함되거나 구글 독스 파일 전수 스캔
          var rvAllFiles = rvFolder.getFiles();
          while (rvAllFiles.hasNext()) {
            var rvf = rvAllFiles.next();
            var rvfName = rvf.getName().toLowerCase();
            if (rvf.getMimeType() === MimeType.GOOGLE_DOCS || rvfName.indexOf("content") !== -1 || rvfName.indexOf("asset") !== -1 || rvfName.indexOf("카피") !== -1) {
              status.contentDocUrl = rvf.getUrl();
              break;
            }
          }
          // 독스가 없더라도 이미지/영상 등 산출물이 이미 폴더에 존재하면 폴더 URL 연결
          if (!status.contentDocUrl) {
            var anyRvFiles = rvFolder.getFiles();
            if (anyRvFiles.hasNext()) {
              status.contentDocUrl = rvFolder.getUrl();
            }
          }
        }
      }

      // 6. 최신 피드백 및 다음 진행 회차 동적 산출 (rv-xx -> fb-(xx+1) 자동 순환)
      var latestFbNum = detectLatestFeedbackRoundNum();
      status.latestFbNum = latestFbNum;

      var activeFbNum = Math.max(1, (latestRvNum >= 0 ? latestRvNum + 1 : 1));
      var activeFbTag = "fb-" + (activeFbNum < 10 ? "0" + activeFbNum : activeFbNum);
      var activeRvTag = latestRvNum >= 0 ? ("rv-" + (latestRvNum < 10 ? "0" + latestRvNum : latestRvNum)) : "rv-00";
      var nextRvTag = "rv-" + (activeFbNum < 10 ? "0" + activeFbNum : activeFbNum);

      status.activeFbTag = activeFbTag;
      status.activeRvTag = activeRvTag;
      status.nextRvTag = nextRvTag;
      status.latestFb = activeFbTag;

      var hasActiveJson = false;
      var hasActiveSummary = false;
      var hasActiveDirective = false;

      var activeFbFolder = getCampaignSubFolder(["input", activeFbTag], true);
      if (activeFbFolder) {
        var jsonFiles = activeFbFolder.getFilesByName("ai_persona_feedbacks.json");
        while (jsonFiles.hasNext()) {
          var jf = jsonFiles.next();
          try {
            if (!jf.isTrashed() && jf.getSize() > 20) {
              hasActiveJson = true;
              status.feedbackJsonUrl = jf.getUrl();
              break;
            }
          } catch (szErr) {
            hasActiveJson = true;
            status.feedbackJsonUrl = jf.getUrl();
            break;
          }
        }

        var summaryFiles = activeFbFolder.getFilesByName("feedback_summary");
        if (!summaryFiles.hasNext()) summaryFiles = activeFbFolder.getFilesByName("feedback_summary.md");
        if (summaryFiles.hasNext()) {
          hasActiveSummary = true;
          status.summaryDocUrl = summaryFiles.next().getUrl();
        } else {
          var fbAllFiles1 = activeFbFolder.getFiles();
          while (fbAllFiles1.hasNext()) {
            var fbf1 = fbAllFiles1.next();
            var fbf1Name = fbf1.getName().toLowerCase();
            if (fbf1Name.indexOf("summary") !== -1 || fbf1Name.indexOf("보고서") !== -1) {
              hasActiveSummary = true;
              status.summaryDocUrl = fbf1.getUrl();
              break;
            }
          }
        }

        var directiveDocName = (CONFIG && CONFIG.DIRECTIVE_DOC_NAME) || "마케터 보정 지침";
        var directiveFiles = activeFbFolder.getFilesByName(directiveDocName);
        if (directiveFiles.hasNext()) {
          hasActiveDirective = true;
          status.directiveDocUrl = directiveFiles.next().getUrl();
        } else {
          var fbAllFiles2 = activeFbFolder.getFiles();
          while (fbAllFiles2.hasNext()) {
            var fbf2 = fbAllFiles2.next();
            var fbf2Name = fbf2.getName().toLowerCase();
            if (fbf2Name.indexOf("지침") !== -1 || fbf2Name.indexOf("directive") !== -1) {
              hasActiveDirective = true;
              status.directiveDocUrl = fbf2.getUrl();
              break;
            }
          }
        }
      }

      // 7. 0~9단계 진행률 동적 산출 (10대 파이프라인 무한 피드백 루프)
      var curStep = 0;
      var stepLabel = "Step 0: 작업 공간 구축";
      if (!status.hasApiKey) {
        curStep = 0;
        stepLabel = "Step 0: API Key 등록 대기";
      } else if (!status.folderUrl) {
        curStep = 0;
        stepLabel = "Step 0: 작업 공간 구축 대기";
      } else if (!status.ideaDocUrl) {
        curStep = 1;
        stepLabel = "Step 1: 아이디어 메모 작성";
      } else if (!status.planDocUrl) {
        curStep = 2;
        stepLabel = "Step 2: 기획서(PLAN) 생성";
      } else if (!status.specDocUrl) {
        curStep = 3;
        stepLabel = "Step 3: 제작 명세서(SPEC) 생성";
      } else if (!status.personaUrl) {
        curStep = 4;
        stepLabel = "Step 4: 맞춤 AI 페르소나 구성";
      } else if (!status.contentDocUrl || latestRvNum < 0) {
        curStep = 5;
        stepLabel = "Step 5: 초판 콘텐츠 생성 (rv-00)";
      } else if (!hasActiveJson) {
        curStep = 6;
        stepLabel = "Step 6: AI 페르소나 다면 평가 (" + activeFbTag + ")";
      } else if (!hasActiveSummary) {
        curStep = 7;
        stepLabel = "Step 7: 피드백 보고서 생성 (" + activeFbTag + ")";
      } else if (!hasActiveDirective) {
        curStep = 8;
        stepLabel = "Step 8: 마케터 보정 지침 확정 (" + activeFbTag + ")";
      } else {
        curStep = 9;
        stepLabel = "Step 9: 개정본 콘텐츠 생성 (" + nextRvTag + ")";
      }
      status.currentStep = curStep;
      status.stepLabel = stepLabel;
      status.progressPercent = Math.min(100, Math.round((curStep / 9) * 100));
    }
  } catch (e) {
    Logger.log("getPipelineStatus 예외: " + e);
  }

  // 30초 로컬 사용자 캐시 저장
  if (cache) {
    try {
      cache.put(cacheKey, JSON.stringify(status), 30);
    } catch (e) {
      // 캐시 저장 실패 무시
    }
  }

  return status;
}

/**
 * 우측 패널(Sidebar)용 모던 HTML 문자열을 생성한다.
 * [구글 워크스페이스 스타일]: Google Sans 서체, 구글 클라우드 테마 색상, 무이모지, 실시간 RPC 연동.
 */
function getPipelineSidebarHtml() {
  return "" +
    "<!DOCTYPE html>\n" +
    "<html>\n" +
    "<head>\n" +
    "  <base target='_blank'>\n" +
    "  <style>\n" +
    "    * { box-sizing: border-box; margin: 0; padding: 0; }\n" +
    "    html, body {\n" +
    "      height: 100%;\n" +
    "      margin: 0;\n" +
    "      padding: 0;\n" +
    "      overflow-y: auto;\n" +
    "    }\n" +
    "    body {\n" +
    "      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;\n" +
    "      font-size: 12px;\n" +
    "      line-height: 1.4;\n" +
    "      color: #202124;\n" +
    "      background: #ffffff;\n" +
    "      padding: 10px 12px;\n" +
    "      display: flex;\n" +
    "      flex-direction: column;\n" +
    "      min-height: 100%;\n" +
    "    }\n" +
    "    .header {\n" +
    "      padding-bottom: 8px;\n" +
    "      margin-bottom: 8px;\n" +
    "      border-bottom: 1px solid #dadce0;\n" +
    "      flex-shrink: 0;\n" +
    "    }\n" +
    "    .header-sub {\n" +
    "      font-size: 11px;\n" +
    "      color: #5f6368;\n" +
    "      display: flex;\n" +
    "      justify-content: space-between;\n" +
    "      align-items: center;\n" +
    "    }\n" +
    "    .campaign-title {\n" +
    "      font-size: 13px;\n" +
    "      font-weight: 700;\n" +
    "      color: #202124;\n" +
    "      letter-spacing: -0.3px;\n" +
    "    }\n" +
    "    .badge {\n" +
    "      display: inline-block;\n" +
    "      font-size: 10px;\n" +
    "      font-weight: 600;\n" +
    "      padding: 2px 7px;\n" +
    "      border-radius: 4px;\n" +
    "      background: #e8f0fe;\n" +
    "      color: #1967d2;\n" +
    "    }\n" +
    "    .badge.active { background: #ceead6; color: #0d652d; }\n" +
    "    .badge.warn { background: #fef7e0; color: #b06000; cursor: pointer; }\n" +
    "    .status-bar {\n" +
    "      padding: 7px 10px;\n" +
    "      background: #e8f0fe;\n" +
    "      border: 1px solid #d2e3fc;\n" +
    "      border-radius: 6px;\n" +
    "      font-size: 11px;\n" +
    "      color: #174ea6;\n" +
    "      margin-bottom: 8px;\n" +
    "      display: none;\n" +
    "      flex-shrink: 0;\n" +
    "      line-height: 1.4;\n" +
    "    }\n" +
    "    .status-bar.show {\n" +
    "      display: flex;\n" +
    "      align-items: center;\n" +
    "    }\n" +
    "    .status-bar.error {\n" +
    "      background: #fce8e6;\n" +
    "      border-color: #fad2cf;\n" +
    "      color: #c5221f;\n" +
    "    }\n" +
    "    .status-bar.success {\n" +
    "      background: #e6f4ea;\n" +
    "      border-color: #ceead6;\n" +
    "      color: #0d652d;\n" +
    "    }\n" +
    "    .spinner {\n" +
    "      display: inline-block;\n" +
    "      width: 12px;\n" +
    "      height: 12px;\n" +
    "      border: 2px solid rgba(26, 115, 232, 0.25);\n" +
    "      border-top-color: #1a73e8;\n" +
    "      border-radius: 50%;\n" +
    "      animation: spin 0.8s linear infinite;\n" +
    "      margin-right: 7px;\n" +
    "      flex-shrink: 0;\n" +
    "    }\n" +
    "    @keyframes spin {\n" +
    "      to { transform: rotate(360deg); }\n" +
    "    }\n" +
    "    .onboarding-card {\n" +
    "      padding: 8px 10px;\n" +
    "      border-radius: 6px;\n" +
    "      margin-bottom: 8px;\n" +
    "      font-size: 11px;\n" +
    "      line-height: 1.4;\n" +
    "      flex-shrink: 0;\n" +
    "    }\n" +
    "    .onboarding-card.warn {\n" +
    "      background: #fef7e0;\n" +
    "      border: 1px solid #f9ab00;\n" +
    "      color: #b06000;\n" +
    "    }\n" +
    "    .onboarding-card.info {\n" +
    "      background: #e8f0fe;\n" +
    "      border: 1px solid #1a73e8;\n" +
    "      color: #174ea6;\n" +
    "    }\n" +
    "    .onboarding-title {\n" +
    "      font-weight: 700;\n" +
    "      margin-bottom: 4px;\n" +
    "    }\n" +
    "    .inline-box {\n" +
    "      background: #f8f9fa;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      border-radius: 6px;\n" +
    "      padding: 8px;\n" +
    "      margin-bottom: 8px;\n" +
    "      flex-shrink: 0;\n" +
    "    }\n" +
    "    .inline-box-title {\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 700;\n" +
    "      color: #202124;\n" +
    "      margin-bottom: 6px;\n" +
    "    }\n" +
    "    .inline-input, .inline-textarea {\n" +
    "      width: 100%;\n" +
    "      padding: 6px 8px;\n" +
    "      font-size: 11px;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      border-radius: 4px;\n" +
    "      box-sizing: border-box;\n" +
    "      font-family: inherit;\n" +
    "      margin-bottom: 6px;\n" +
    "    }\n" +
    "    .inline-input:focus, .inline-textarea:focus {\n" +
    "      border-color: #1a73e8;\n" +
    "      outline: none;\n" +
    "    }\n" +
    "    .inline-actions {\n" +
    "      display: flex;\n" +
    "      gap: 6px;\n" +
    "      justify-content: flex-end;\n" +
    "    }\n" +
    "    .copilot-section {\n" +
    "      background: #ffffff;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      border-radius: 6px;\n" +
    "      padding: 8px 10px;\n" +
    "      margin-bottom: 8px;\n" +
    "      display: flex;\n" +
    "      flex-direction: column;\n" +
    "      flex-shrink: 0;\n" +
    "    }\n" +
    "    .copilot-header {\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 700;\n" +
    "      color: #1a73e8;\n" +
    "      margin-bottom: 6px;\n" +
    "      display: flex;\n" +
    "      justify-content: space-between;\n" +
    "      align-items: center;\n" +
    "    }\n" +
    "    .chat-log {\n" +
    "      max-height: 220px;\n" +
    "      min-height: 110px;\n" +
    "      overflow-y: auto;\n" +
    "      margin-bottom: 6px;\n" +
    "      display: flex;\n" +
    "      flex-direction: column;\n" +
    "      gap: 6px;\n" +
    "      padding: 4px 2px;\n" +
    "      border-bottom: 1px solid #f1f3f4;\n" +
    "    }\n" +
    "    .chat-bubble {\n" +
    "      font-size: 11px;\n" +
    "      line-height: 1.5;\n" +
    "      padding: 2px 0;\n" +
    "      width: 100%;\n" +
    "      word-break: break-word;\n" +
    "      background: none;\n" +
    "      border: none;\n" +
    "    }\n" +
    "    .chat-bubble.bot {\n" +
    "      align-self: flex-start;\n" +
    "      color: #202124;\n" +
    "      text-align: left;\n" +
    "    }\n" +
    "    .chat-bubble.user {\n" +
    "      align-self: flex-end;\n" +
    "      color: #1a73e8;\n" +
    "      font-weight: 600;\n" +
    "      text-align: right;\n" +
    "    }\n" +
    "    .chat-bubble.user::before {\n" +
    "      content: '나: ';\n" +
    "      color: #70757a;\n" +
    "      font-weight: 400;\n" +
    "    }\n" +
    "    .chat-action-btn {\n" +
    "      display: inline-block;\n" +
    "      margin-top: 4px;\n" +
    "      padding: 4px 8px;\n" +
    "      background: #1a73e8;\n" +
    "      color: #ffffff;\n" +
    "      border-radius: 4px;\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 600;\n" +
    "      border: 1px solid #174ea6;\n" +
    "      cursor: pointer;\n" +
    "      text-decoration: none;\n" +
    "      transition: all 0.15s ease;\n" +
    "    }\n" +
    "    .chat-action-btn:hover { background: #174ea6; }\n" +
    "    .quick-chips {\n" +
    "      display: flex;\n" +
    "      flex-wrap: wrap;\n" +
    "      gap: 4px;\n" +
    "      margin-bottom: 6px;\n" +
    "    }\n" +
    "    .quick-chip {\n" +
    "      font-size: 10px;\n" +
    "      padding: 2px 7px;\n" +
    "      background: #ffffff;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      border-radius: 12px;\n" +
    "      color: #5f6368;\n" +
    "      cursor: pointer;\n" +
    "      white-space: nowrap;\n" +
    "      transition: all 0.15s ease;\n" +
    "    }\n" +
    "    .quick-chip:hover {\n" +
    "      background: #e8f0fe;\n" +
    "      border-color: #1a73e8;\n" +
    "      color: #1a73e8;\n" +
    "    }\n" +
    "    .chat-input-box {\n" +
    "      display: flex;\n" +
    "      gap: 6px;\n" +
    "    }\n" +
    "    .chat-input {\n" +
    "      flex: 1;\n" +
    "      padding: 6px 8px;\n" +
    "      font-size: 11px;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      border-radius: 4px;\n" +
    "      outline: none;\n" +
    "    }\n" +
    "    .chat-input:focus { border-color: #1a73e8; }\n" +
    "    .chat-send-btn {\n" +
    "      padding: 6px 10px;\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 600;\n" +
    "      background: #1a73e8;\n" +
    "      color: #ffffff;\n" +
    "      border: none;\n" +
    "      border-radius: 4px;\n" +
    "      cursor: pointer;\n" +
    "      white-space: nowrap;\n" +
    "    }\n" +
    "    .chat-send-btn:hover { background: #174ea6; }\n" +
    "    .chat-send-btn:disabled { opacity: 0.5; cursor: not-allowed; }\n" +
    "    details.pipeline-section {\n" +
    "      padding: 4px 2px 0 2px;\n" +
    "      margin-bottom: 8px;\n" +
    "    }\n" +
    "    details.pipeline-section summary {\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 700;\n" +
    "      color: #202124;\n" +
    "      cursor: pointer;\n" +
    "      display: flex;\n" +
    "      justify-content: space-between;\n" +
    "      align-items: center;\n" +
    "      user-select: none;\n" +
    "      padding: 4px 0;\n" +
    "    }\n" +
    "    details.pipeline-section summary::-webkit-details-marker { display: none; }\n" +
    "    .pipeline-content {\n" +
    "      margin-top: 6px;\n" +
    "      display: flex;\n" +
    "      flex-direction: column;\n" +
    "      gap: 1px;\n" +
    "    }\n" +
    "    .btn {\n" +
    "      display: block;\n" +
    "      width: 100%;\n" +
    "      padding: 5px 9px;\n" +
    "      font-size: 11px;\n" +
    "      font-weight: 500;\n" +
    "      text-align: left;\n" +
    "      border-radius: 4px;\n" +
    "      border: 1px solid #dadce0;\n" +
    "      background: #f8f9fa;\n" +
    "      color: #3c4043;\n" +
    "      cursor: pointer;\n" +
    "      transition: all 0.15s ease;\n" +
    "    }\n" +
    "    .btn:hover:not(:disabled) {\n" +
    "      background: #e8f0fe;\n" +
    "      border-color: #1a73e8;\n" +
    "      color: #1a73e8;\n" +
    "    }\n" +
    "    .btn:disabled {\n" +
    "      opacity: 0.5;\n" +
    "      cursor: not-allowed;\n" +
    "      background: #f1f3f4;\n" +
    "      border-color: #dadce0;\n" +
    "      color: #9aa0a6;\n" +
    "    }\n" +
    "    .btn-primary {\n" +
    "      background: #1a73e8;\n" +
    "      color: #ffffff;\n" +
    "      border-color: #1a73e8;\n" +
    "    }\n" +
    "    .btn-primary:hover:not(:disabled) {\n" +
    "      background: #174ea6;\n" +
    "      border-color: #174ea6;\n" +
    "      color: #ffffff;\n" +
    "    }\n" +
    "    .btn-sm {\n" +
    "      padding: 4px 8px;\n" +
    "      font-size: 11px;\n" +
    "      margin-top: 4px;\n" +
    "      text-align: center;\n" +
    "    }\n" +
    "    .btn-step {\n" +
    "      display: flex;\n" +
    "      align-items: center;\n" +
    "      justify-content: space-between;\n" +
    "    }\n" +
    "    .step-tag {\n" +
    "      font-size: 9px;\n" +
    "      font-weight: 700;\n" +
    "      padding: 1px 5px;\n" +
    "      border-radius: 3px;\n" +
    "      background: #e8eaed;\n" +
    "      color: #5f6368;\n" +
    "    }\n" +
    "    .footer-actions {\n" +
    "      margin-top: auto;\n" +
    "      text-align: center;\n" +
    "      padding-top: 6px;\n" +
    "      padding-bottom: 2px;\n" +
    "      border-top: 1px solid #dadce0;\n" +
    "      flex-shrink: 0;\n" +
    "    }\n" +
    "    .footer-btn {\n" +
    "      background: none;\n" +
    "      border: none;\n" +
    "      color: #70757a;\n" +
    "      font-size: 11px;\n" +
    "      cursor: pointer;\n" +
    "      text-decoration: underline;\n" +
    "    }\n" +
    "    .footer-btn:hover { color: #1a73e8; }\n" +
    "  </style>\n" +
    "</head>\n" +
    "<body>\n" +
    "  <!-- 1. 최상단: 상태 알림 섹션 -->\n" +
    "  <div class='header'>\n" +
    "    <div class='header-sub'>\n" +
    "      <span id='campaignCodeBadge' class='campaign-title'>BwG-Seoul-Ignite</span>\n" +
    "      <span id='apiKeyBadge' class='badge warn' onclick='toggleApiKeyBox(true)' title='클릭하여 API Key 등록'>API Key 확인 중</span>\n" +
    "    </div>\n" +
    "  </div>\n" +
    "\n" +
    "  <div id='statusBar' class='status-bar'></div>\n" +
    "\n" +
    "  <div id='onboardingBanner' class='onboarding-card' style='display:none;'>\n" +
    "    <div id='onboardingTitle' class='onboarding-title'>준비 단계</div>\n" +
    "    <div id='onboardingDesc'></div>\n" +
    "    <button id='onboardingBtn' class='btn btn-primary btn-sm'></button>\n" +
    "  </div>\n" +
    "\n" +
    "  <div id='apiKeyInlineBox' class='inline-box' style='display:none;'>\n" +
    "    <div class='inline-box-title'>Gemini API Key 등록 (Google AI Studio)</div>\n" +
    "    <div style='font-size: 11px; color: #5f6368; margin-bottom: 8px; line-height: 1.3;'>\n" +
    "      신용카드 없이 개인 계정으로 1분 만에 무료 발급받을 수 있습니다.<br>\n" +
    "      <a href='https://aistudio.google.com/app/apikey' target='_blank' style='color: #1a73e8; text-decoration: underline; font-weight: 500;'>Google AI Studio에서 무료 API Key 발급받기 &rarr;</a>\n" +
    "    </div>\n" +
    "    <input type='password' id='inputApiKey' class='inline-input' placeholder='AIzaSy... 키를 붙여넣으십시오' />\n" +
    "    <div class='inline-actions'>\n" +
    "      <button class='btn btn-primary' onclick='submitApiKeyInline()'>저장 및 검증</button>\n" +
    "      <button class='btn' onclick='toggleApiKeyBox(false)'>취소</button>\n" +
    "    </div>\n" +
    "  </div>\n" +
    "\n" +
    "  <!-- 2. 중단: AI 코파일럿 대화 섹션 -->\n" +
    "  <div class='copilot-section'>\n" +
    "    <div class='copilot-header'>\n" +
    "      <span>AI 코파일럿 대화 및 지시</span>\n" +
    "      <span class='step-tag'>Gemini 3.8 Flash</span>\n" +
    "    </div>\n" +
    "    <div id='chatLog' class='chat-log'>\n" +
    "      <div class='chat-bubble bot'>\n" +
    "        안녕! 마케팅 파이프라인 AI 코파일럿이야. 진행 상황이 궁금하거나 작업 실행이 필요하면 언제든 편하게 물어봐!\n" +
    "      </div>\n" +
    "    </div>\n" +
    "    <div class='quick-chips'>\n" +
    "      <span class='quick-chip' onclick=\"quickChat('지금 뭐 해야 돼?')\">지금 뭐 해야 돼?</span>\n" +
    "    </div>\n" +
    "    <div class='chat-input-box'>\n" +
    "      <input id='chatInput' class='chat-input' placeholder='질문하거나 편하게 지시해봐... (Enter)' onkeydown='handleChatKey(event)' />\n" +
    "      <button id='btnChatSend' class='chat-send-btn' onclick='submitChatQuery()'>전송</button>\n" +
    "    </div>\n" +
    "  </div>\n" +
    "\n" +
    "  <!-- 3. 하단: 0~9단계 10대 파이프라인 실행 로드맵 -->\n" +
    "  <details class='pipeline-section' open>\n" +
    "    <summary>\n" +
    "      <span>파이프라인 실행 로드맵</span>\n" +
    "      <span class='step-tag'>0~9단계 ▼</span>\n" +
    "    </summary>\n" +
    "    <div class='pipeline-content'>\n" +
    "      <button id='btnStep0' class='btn btn-step' onclick='toggleSetupBox()'>\n" +
    "        <span>[0단계] API Key &amp; 작업 공간 구축</span>\n" +
    "        <span class='step-tag'>Setup ▼</span>\n" +
    "      </button>\n" +
    "      <div id='setupInlineBox' class='inline-box' style='display:none;'>\n" +
    "        <div class='inline-box-title'>API Key 및 작업 공간 설정</div>\n" +
    "        <button id='btnApiKey' class='btn' style='margin-bottom:4px;' onclick='toggleApiKeyBox(true)'>Gemini API Key 설정 (인라인)</button>\n" +
    "        <button id='btnInit' class='btn btn-primary' style='margin-bottom:4px;' onclick=\"callServer('initCampaignWorkspace', '캠페인 작업 공간 구축')\">[초기화] 캠페인 작업 공간 구축</button>\n" +
    "        <div style='font-size: 10px; color: #5f6368; line-height: 1.3;'>\n" +
    "          * 최초 실행 시 Google 권한 승인 창이 뜨면 <strong>'고급' &gt; '(안전하지 않음으로 이동)' &gt; '허용'</strong>을 순서대로 클릭하시면 정상 구동됩니다.\n" +
    "        </div>\n" +
    "      </div>\n" +
    "\n" +
    "      <button id='btnStep1' class='btn btn-step' onclick='toggleIdeaBox()'>\n" +
    "        <span>[1단계] 캠페인 아이디어 메모 작성</span>\n" +
    "        <span class='step-tag'>IDEA ▼</span>\n" +
    "      </button>\n" +
    "      <div id='ideaInlineBox' class='inline-box' style='display:none;'>\n" +
    "        <div class='inline-box-title'>캠페인 아이디어 입력</div>\n" +
    "        <textarea id='inputCustomIdea' class='inline-textarea' rows='3' placeholder='이번 캠페인의 핵심 컨셉, 타깃, 주요 혜택을 입력하십시오... (비워두면 기존 메모 유지)'></textarea>\n" +
    "        <div class='inline-actions'>\n" +
    "          <button class='btn btn-primary' onclick='submitIdeaAndRunMemo()'>아이디어 저장 및 메모 작성</button>\n" +
    "          <button class='btn' onclick='toggleIdeaBox(false)'>닫기</button>\n" +
    "        </div>\n" +
    "        <div style='margin-top: 5px; text-align: right;'>\n" +
    "          <a id='linkIdeaDoc' href='#' target='_blank' style='font-size: 10px; color: #1a73e8; text-decoration: underline; display: none;'>[아이디어 메모] 구글 독스 직접 열기</a>\n" +
    "        </div>\n" +
    "      </div>\n" +
    "\n" +
    "      <button class='btn btn-step' onclick=\"callServer('guardAndRunIdeaToPlan', '캠페인 기획서(PLAN) 생성')\">\n" +
    "        <span>[2단계] 캠페인 기획서(PLAN) 생성</span>\n" +
    "        <span class='step-tag'>PLAN</span>\n" +
    "      </button>\n" +
    "\n" +
    "      <button class='btn btn-step' onclick=\"callServer('guardAndRunPlanToSpec', '콘텐츠 제작 명세서(SPEC) 생성')\">\n" +
    "        <span>[3단계] 콘텐츠 제작 명세서(SPEC) 생성</span>\n" +
    "        <span class='step-tag'>SPEC</span>\n" +
    "      </button>\n" +
    "\n" +
    "      <button class='btn btn-step' onclick=\"callServer('guardAndRunPersonaSynthesis', '맞춤 AI 페르소나 패널 구성')\">\n" +
    "        <span>[4단계] 맞춤 AI 페르소나 패널 구성</span>\n" +
    "        <span class='step-tag'>Persona</span>\n" +
    "      </button>\n" +
    "\n" +
    "      <button class='btn btn-step' onclick=\"callServer('guardAndRunInitialContent', '초판 콘텐츠 생성')\">\n" +
    "        <span>[5단계] 초판 멀티 채널 콘텐츠 생성</span>\n" +
    "        <span class='step-tag'>rv-00</span>\n" +
    "      </button>\n" +
    "\n" +
    "      <button class='btn btn-step' onclick=\"callServer('promptAndRunJudgeEvaluation', 'AI 페르소나 다면 평가')\">\n" +
    "        <span>[6단계] AI 페르소나 다면 평가 실행</span>\n" +
    "        <span class='step-tag'>Judge</span>\n" +
    "      </button>\n" +
    "\n" +
    "      <button class='btn btn-step' onclick=\"callServer('promptAndRunFeedbackSummary', '피드백 종합 보고서 생성')\">\n" +
    "        <span>[7단계] 피드백 종합 분석 보고서 생성</span>\n" +
    "        <span class='step-tag'>Report</span>\n" +
    "      </button>\n" +
    "\n" +
    "      <button id='btnStep8' class='btn btn-step' onclick='toggleDirectiveBox()'>\n" +
    "        <span>[8단계] 마케터 보정 지침 작성/확정</span>\n" +
    "        <span class='step-tag'>Directive ▼</span>\n" +
    "      </button>\n" +
    "      <div id='directiveInlineBox' class='inline-box' style='display:none;'>\n" +
    "        <div class='inline-box-title'>마케터 보정 지침 입력</div>\n" +
    "        <textarea id='inputCustomDirective' class='inline-textarea' rows='3' placeholder='피드백 분석 결과를 바탕으로 보정할 구체적 지침을 입력하십시오... (비워두면 기존 지침 반영)'></textarea>\n" +
    "        <div class='inline-actions'>\n" +
    "          <button class='btn btn-primary' onclick='submitDirectiveAndRunSave()'>보정 지침 확정 및 저장</button>\n" +
    "          <button class='btn' onclick='toggleDirectiveBox(false)'>닫기</button>\n" +
    "        </div>\n" +
    "        <div style='margin-top: 5px; text-align: right;'>\n" +
    "          <a id='linkDirectiveDoc' href='#' target='_blank' style='font-size: 10px; color: #1a73e8; text-decoration: underline; display: none;'>[마케터 보정 지침] 구글 독스 직접 열기</a>\n" +
    "        </div>\n" +
    "      </div>\n" +
    "\n" +
    "      <button class='btn btn-step' onclick=\"callServer('promptAndRunFeedbackRevision', '개정본 콘텐츠 생성')\">\n" +
    "        <span>[9단계] 피드백 반영 개정본 생성</span>\n" +
    "        <span class='step-tag'>rv-01</span>\n" +
    "      </button>\n" +
    "    </div>\n" +
    "  </details>\n" +
    "\n" +
    "  <!-- 하단 유틸리티 링크 -->\n" +
    "  <div class='footer-actions'>\n" +
    "    <button class='footer-btn' onclick='refreshStatus()'>패널 새로고침</button>\n" +
    "     | \n" +
    "    <button class='footer-btn' onclick=\"callServer('openDashboardSheet', '실행 내역 열기')\">실행 내역 열기</button>\n" +
    "     | \n" +
    "    <button class='footer-btn' onclick=\"callServer('forceSyncEngine', '엔진 최신 동기화')\">최신 엔진 동기화</button>\n" +
    "  </div>\n" +
    "\n" +
    "  <script>\n" +
    "    var timerInterval = null;\n" +
    "    var timerSeconds = 0;\n" +
    "    var currentStatusCache = null;\n" +
    "\n" +
    "    function setStatus(htmlOrText, isError, isSuccess) {\n" +
    "      var el = document.getElementById('statusBar');\n" +
    "      if (!htmlOrText) {\n" +
    "        el.className = 'status-bar';\n" +
    "        el.innerHTML = '';\n" +
    "        return;\n" +
    "      }\n" +
    "      var cls = 'status-bar show';\n" +
    "      if (isError) cls += ' error';\n" +
    "      else if (isSuccess) cls += ' success';\n" +
    "      el.className = cls;\n" +
    "      el.innerHTML = htmlOrText;\n" +
    "    }\n" +
    "\n" +
    "    function startTimer(taskName) {\n" +
    "      clearInterval(timerInterval);\n" +
    "      timerSeconds = 0;\n" +
    "      setStatus(\"<span class='spinner'></span> <span>\" + taskName + \" 실행 중... (<strong>0초</strong> 경과)</span>\", false);\n" +
    "      timerInterval = setInterval(function() {\n" +
    "        timerSeconds++;\n" +
    "        setStatus(\"<span class='spinner'></span> <span>\" + taskName + \" 실행 중... (<strong>\" + timerSeconds + \"초</strong> 경과)</span>\", false);\n" +
    "      }, 1000);\n" +
    "    }\n" +
    "\n" +
    "    function stopTimer(successMsg, isError) {\n" +
    "      clearInterval(timerInterval);\n" +
    "      if (isError) {\n" +
    "        setStatus(successMsg, true);\n" +
    "      } else {\n" +
    "        var durText = timerSeconds > 0 ? \" (총 \" + timerSeconds + \"초 소요)\" : \"\";\n" +
    "        setStatus(\"✓ \" + (successMsg || \"작업이 성공적으로 완결되었습니다.\") + durText, false, true);\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    function setButtonsDisabled(disabled) {\n" +
    "      var btns = document.querySelectorAll('button:not(.footer-btn)');\n" +
    "      btns.forEach(function(b) { b.disabled = disabled; });\n" +
    "    }\n" +
    "\n" +
    "    function toggleApiKeyBox(show) {\n" +
    "      var box = document.getElementById('apiKeyInlineBox');\n" +
    "      box.style.display = show ? 'block' : 'none';\n" +
    "      if (show) {\n" +
    "        var inp = document.getElementById('inputApiKey');\n" +
    "        inp.value = '';\n" +
    "        inp.focus();\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    function submitApiKeyInline() {\n" +
    "      var val = document.getElementById('inputApiKey').value.trim();\n" +
    "      if (!val) {\n" +
    "        setStatus('API Key를 입력해 주십시오.', true);\n" +
    "        return;\n" +
    "      }\n" +
    "      setStatus(\"<span class='spinner'></span> API Key 저장 및 검증 중...\", false);\n" +
    "      google.script.run\n" +
    "        .withSuccessHandler(function(res) {\n" +
    "          if (res && res.success) {\n" +
    "            toggleApiKeyBox(false);\n" +
    "            setStatus('✓ ' + res.message, false, true);\n" +
    "            refreshStatus();\n" +
    "          } else {\n" +
    "            setStatus(res ? res.message : 'API Key 저장 실패', true);\n" +
    "          }\n" +
    "        })\n" +
    "        .withFailureHandler(function(err) {\n" +
    "          setStatus('API Key 저장 오류: ' + (err.message || err), true);\n" +
    "        })\n" +
    "        .saveApiKeyInline(val);\n" +
    "    }\n" +
    "\n" +
    "    function toggleSetupBox(show) {\n" +
    "      var box = document.getElementById('setupInlineBox');\n" +
    "      if (!box) return;\n" +
    "      var isCurrentlyOpen = box.style.display !== 'none';\n" +
    "      var shouldOpen = (show !== undefined) ? show : !isCurrentlyOpen;\n" +
    "      box.style.display = shouldOpen ? 'block' : 'none';\n" +
    "    }\n" +
    "\n" +
    "    function toggleIdeaBox(show) {\n" +
    "      var box = document.getElementById('ideaInlineBox');\n" +
    "      if (!box) return;\n" +
    "      var isCurrentlyOpen = box.style.display !== 'none';\n" +
    "      var shouldOpen = (show !== undefined) ? show : !isCurrentlyOpen;\n" +
    "      box.style.display = shouldOpen ? 'block' : 'none';\n" +
    "      if (shouldOpen) {\n" +
    "        var inp = document.getElementById('inputCustomIdea');\n" +
    "        if (inp) inp.focus();\n" +
    "        var linkDoc = document.getElementById('linkIdeaDoc');\n" +
    "        if (linkDoc && currentStatusCache && currentStatusCache.ideaDocUrl) {\n" +
    "          linkDoc.href = currentStatusCache.ideaDocUrl;\n" +
    "          linkDoc.style.display = 'inline-block';\n" +
    "        } else if (linkDoc) {\n" +
    "          linkDoc.style.display = 'none';\n" +
    "        }\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    function submitIdeaAndRunMemo() {\n" +
    "      var inp = document.getElementById('inputCustomIdea');\n" +
    "      var val = inp ? inp.value.trim() : '';\n" +
    "      toggleIdeaBox(false);\n" +
    "      callServer('runCampaignIdeaMemo', '아이디어 메모 작성', val);\n" +
    "    }\n" +
    "\n" +
    "    function toggleDirectiveBox(show) {\n" +
    "      var box = document.getElementById('directiveInlineBox');\n" +
    "      if (!box) return;\n" +
    "      var isCurrentlyOpen = box.style.display !== 'none';\n" +
    "      var shouldOpen = (show !== undefined) ? show : !isCurrentlyOpen;\n" +
    "      box.style.display = shouldOpen ? 'block' : 'none';\n" +
    "      if (shouldOpen) {\n" +
    "        var inp = document.getElementById('inputCustomDirective');\n" +
    "        if (inp) inp.focus();\n" +
    "        var linkDoc = document.getElementById('linkDirectiveDoc');\n" +
    "        if (linkDoc && currentStatusCache && currentStatusCache.directiveDocUrl) {\n" +
    "          linkDoc.href = currentStatusCache.directiveDocUrl;\n" +
    "          linkDoc.style.display = 'inline-block';\n" +
    "        } else if (linkDoc) {\n" +
    "          linkDoc.style.display = 'none';\n" +
    "        }\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    function submitDirectiveAndRunSave() {\n" +
    "      var inp = document.getElementById('inputCustomDirective');\n" +
    "      var val = inp ? inp.value.trim() : '';\n" +
    "      toggleDirectiveBox(false);\n" +
    "      callServer('runMarketerDirective', '마케터 보정 지침 확정', val);\n" +
    "    }\n" +
    "\n" +
    "    function updateUI(status) {\n" +
    "      if (!status) return;\n" +
    "      currentStatusCache = status;\n" +
    "\n" +
    "      var keyBadge = document.getElementById('apiKeyBadge');\n" +
    "      var onboarding = document.getElementById('onboardingBanner');\n" +
    "      var setupBox = document.getElementById('setupBox');\n" +
    "      var linkDoc = document.getElementById('linkIdeaDoc');\n" +
    "      if (linkDoc) {\n" +
    "        if (status.ideaDocUrl) {\n" +
    "          linkDoc.href = status.ideaDocUrl;\n" +
    "          linkDoc.style.display = 'inline-block';\n" +
    "        } else {\n" +
    "          linkDoc.style.display = 'none';\n" +
    "        }\n" +
    "      }\n" +
    "      var linkDirective = document.getElementById('linkDirectiveDoc');\n" +
    "      if (linkDirective) {\n" +
    "        if (status.directiveDocUrl) {\n" +
    "          linkDirective.href = status.directiveDocUrl;\n" +
    "          linkDirective.style.display = 'inline-block';\n" +
    "        } else {\n" +
    "          linkDirective.style.display = 'none';\n" +
    "        }\n" +
    "      }\n" +
    "\n" +
    "      // 1. API Key 상태 및 온보딩 배너 관리\n" +
    "      if (status.hasApiKey) {\n" +
    "        keyBadge.className = 'badge active';\n" +
    "        keyBadge.textContent = 'API Key 등록됨';\n" +
    "        keyBadge.onclick = function() { toggleApiKeyBox(true); };\n" +
    "      } else {\n" +
    "        keyBadge.className = 'badge warn';\n" +
    "        keyBadge.textContent = 'API Key 필요';\n" +
    "        keyBadge.onclick = function() { toggleApiKeyBox(true); };\n" +
    "      }\n" +
    "\n" +
    "      if (!status.hasApiKey) {\n" +
    "        onboarding.className = 'onboarding-card warn';\n" +
    "        onboarding.style.display = 'block';\n" +
    "        document.getElementById('onboardingTitle').textContent = '준비 1단계: API Key 등록';\n" +
    "        document.getElementById('onboardingDesc').textContent = 'Gemini API 호출을 위해 Google AI Studio API Key를 먼저 등록해 주십시오.';\n" +
    "        var obBtn = document.getElementById('onboardingBtn');\n" +
    "        obBtn.textContent = '지금 API Key 등록하기';\n" +
    "        obBtn.onclick = function() { toggleApiKeyBox(true); };\n" +
    "        if (setupBox) setupBox.open = true;\n" +
    "      } else if (!status.folderUrl) {\n" +
    "        onboarding.className = 'onboarding-card info';\n" +
    "        onboarding.style.display = 'block';\n" +
    "        document.getElementById('onboardingTitle').textContent = '준비 2단계: 작업 공간 초기화';\n" +
    "        document.getElementById('onboardingDesc').textContent = '캠페인 부모 폴더를 감지하고 필수 프롬프트와 작업 공간을 구축해 주십시오.';\n" +
    "        var obBtn = document.getElementById('onboardingBtn');\n" +
    "        obBtn.textContent = '[초기화] 캠페인 작업 공간 구축';\n" +
    "        obBtn.onclick = function() { callServer('initCampaignWorkspace', '캠페인 작업 공간 구축'); };\n" +
    "        if (setupBox) setupBox.open = true;\n" +
    "      } else {\n" +
    "        onboarding.style.display = 'none';\n" +
    "        if (setupBox) setupBox.open = false;\n" +
    "      }\n" +
    "\n" +
    "      // 3. 캠페인 코드 배지\n" +
    "      if (status.campaignCode) {\n" +
    "        document.getElementById('campaignCodeBadge').textContent = status.campaignCode;\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    function refreshStatus() {\n" +
    "      google.script.run\n" +
    "        .withSuccessHandler(function(status) {\n" +
    "          updateUI(status);\n" +
    "        })\n" +
    "        .withFailureHandler(function(err) {\n" +
    "          setStatus('상태 갱신 오류: ' + (err.message || err), true);\n" +
    "        })\n" +
    "        .getPipelineStatus();\n" +
    "    }\n" +
    "\n" +
    "    function callServer(fnName, taskName, optArg) {\n" +
    "      var displayName = taskName || fnName;\n" +
    "      setButtonsDisabled(true);\n" +
    "      startTimer(displayName);\n" +
    "\n" +
    "      google.script.run\n" +
    "        .withSuccessHandler(function(res) {\n" +
    "          setButtonsDisabled(false);\n" +
    "          var progressDoneMsg = displayName + ' 완료';\n" +
    "          stopTimer(progressDoneMsg, false);\n" +
    "          if (res) {\n" +
    "            var botMsg = (res && res.message) || (displayName + ' 작업이 성공적으로 완결되었습니다.');\n" +
    "            var actionBtn = '';\n" +
    "            if (res.ideaDocUrl) {\n" +
    "              actionBtn += \" <a href='\" + res.ideaDocUrl + \"' target='_blank' style='display:inline-block; margin-top:4px; font-size:11px; color:#1a73e8; text-decoration:underline;'>[아이디어 메모 열기]</a>\";\n" +
    "            }\n" +
    "            if (res.planUrl) {\n" +
    "              actionBtn += \" <a href='\" + res.planUrl + \"' target='_blank' style='display:inline-block; margin-top:4px; font-size:11px; color:#1a73e8; text-decoration:underline;'>[기획서(PLAN) 열기]</a>\";\n" +
    "            }\n" +
    "            if (res.specUrl) {\n" +
    "              actionBtn += \" <a href='\" + res.specUrl + \"' target='_blank' style='display:inline-block; margin-top:4px; font-size:11px; color:#1a73e8; text-decoration:underline;'>[제작 명세서(SPEC) 열기]</a>\";\n" +
    "            }\n" +
    "            if (res.personaUrl) {\n" +
    "              actionBtn += \" <a href='\" + res.personaUrl + \"' target='_blank' style='display:inline-block; margin-top:4px; font-size:11px; color:#1a73e8; text-decoration:underline;'>[AI 페르소나 패널 열기]</a>\";\n" +
    "            }\n" +
    "            if (res.folderUrl) {\n" +
    "              var rvSuffix = res.targetRv ? \" (\" + res.targetRv + \")\" : \"\";\n" +
    "              actionBtn += \" <a href='\" + res.folderUrl + \"' target='_blank' style='display:inline-block; margin-top:4px; font-size:11px; color:#1a73e8; text-decoration:underline;'>[산출물 폴더 열기\" + rvSuffix + \"]</a>\";\n" +
    "            }\n" +
    "            if (res.summaryUrl) {\n" +
    "              var fbSuffix = res.targetRound ? \" (\" + res.targetRound + \")\" : \"\";\n" +
    "              actionBtn += \" <a href='\" + res.summaryUrl + \"' target='_blank' style='display:inline-block; margin-top:4px; font-size:11px; color:#1a73e8; text-decoration:underline;'>[피드백 보고서 열기\" + fbSuffix + \"]</a>\";\n" +
    "            }\n" +
    "            if (res.directiveUrl) {\n" +
    "              var fbSuffix2 = res.targetRound ? \" (\" + res.targetRound + \")\" : \"\";\n" +
    "              actionBtn += \" <a href='\" + res.directiveUrl + \"' target='_blank' style='display:inline-block; margin-top:4px; margin-left:6px; font-size:11px; color:#1a73e8; text-decoration:underline;'>[마케터 보정 지침 열기\" + fbSuffix2 + \"]</a>\";\n" +
    "            }\n" +
    "            if (res.feedbackJsonUrl || res.jsonUrl) {\n" +
    "              var targetJsonUrl = res.feedbackJsonUrl || res.jsonUrl;\n" +
    "              var fbSuffix3 = res.targetRound ? \" (\" + res.targetRound + \")\" : \"\";\n" +
    "              actionBtn += \" <a href='\" + targetJsonUrl + \"' target='_blank' style='display:inline-block; margin-top:4px; font-size:11px; color:#1a73e8; text-decoration:underline;'>[AI 페르소나 피드백 JSON 열기\" + fbSuffix3 + \"]</a>\";\n" +
    "            }\n" +
    "            if (res.actionChip) {\n" +
    "              actionBtn += res.actionChip;\n" +
    "            }\n" +
    "            appendChatBubble('bot', botMsg + actionBtn);\n" +
    "          }\n" +
    "          refreshStatus();\n" +
    "        })\n" +
    "        .withFailureHandler(function(err) {\n" +
    "          setButtonsDisabled(false);\n" +
    "          var errStr = (err && (err.message || err.toString())) || '알 수 없는 오류';\n" +
    "          stopTimer('오류 발생: ' + errStr, true);\n" +
    "        })[fnName](optArg);\n" +
    "    }\n" +
    "\n" +
    "    function escapeHtml(str) {\n" +
    "      if (!str) return '';\n" +
    "      return String(str)\n" +
    "        .replace(/&/g, '&amp;')\n" +
    "        .replace(/</g, '&lt;')\n" +
    "        .replace(/>/g, '&gt;')\n" +
    "        .replace(/\"/g, '&quot;')\n" +
    "        .replace(/'/g, '&#039;');\n" +
    "    }\n" +
    "\n" +
    "    function appendChatBubble(sender, text, actionBtnHtml) {\n" +
    "      var log = document.getElementById('chatLog');\n" +
    "      if (!log) return null;\n" +
    "      var bubble = document.createElement('div');\n" +
    "      bubble.className = 'chat-bubble ' + sender;\n" +
    "      var safeText = sender === 'user' ? escapeHtml(text) : text;\n" +
    "      bubble.innerHTML = safeText + (actionBtnHtml || '');\n" +
    "      log.appendChild(bubble);\n" +
    "      log.scrollTop = log.scrollHeight;\n" +
    "      return bubble;\n" +
    "    }\n" +
    "\n" +
    "    var isChatProcessing = false;\n" +
    "\n" +
    "    function quickChat(text) {\n" +
    "      if (isChatProcessing) return;\n" +
    "      var inp = document.getElementById('chatInput');\n" +
    "      if (inp) inp.value = text;\n" +
    "      submitChatQuery();\n" +
    "    }\n" +
    "\n" +
    "    function handleChatKey(e) {\n" +
    "      if (e.key === 'Enter') {\n" +
    "        e.preventDefault();\n" +
    "        submitChatQuery();\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    function submitChatQuery() {\n" +
    "      if (isChatProcessing) return;\n" +
    "      var inp = document.getElementById('chatInput');\n" +
    "      if (!inp) return;\n" +
    "      var val = inp.value.trim();\n" +
    "      if (!val) return;\n" +
    "      inp.value = '';\n" +
    "      isChatProcessing = true;\n" +
    "\n" +
    "      appendChatBubble('user', val);\n" +
    "      var loadingBubble = appendChatBubble('bot', \"<span class='spinner'></span> 답변 생성 중...\");\n" +
    "\n" +
    "      var btn = document.getElementById('btnChatSend');\n" +
    "      if (btn) btn.disabled = true;\n" +
    "      inp.disabled = true;\n" +
    "\n" +
    "      google.script.run\n" +
    "        .withSuccessHandler(function(res) {\n" +
    "          isChatProcessing = false;\n" +
    "          if (btn) btn.disabled = false;\n" +
    "          if (inp) {\n" +
    "            inp.disabled = false;\n" +
    "            inp.focus();\n" +
    "          }\n" +
    "          var reply = (res && res.reply) || '답변을 생성하지 못했어.';\n" +
    "          var actionHtml = '';\n" +
    "          if (res && res.actionBtnHtml) {\n" +
    "            actionHtml = res.actionBtnHtml;\n" +
    "          } else if (res && res.action && res.actionLabel) {\n" +
    "            var task = res.taskName || res.actionLabel;\n" +
    "            actionHtml = \"<br/><button class='chat-action-btn' onclick=\\\"runChatAction('\" + res.action + \"', '\" + task + \"')\\\">[실행] \" + res.actionLabel + \"</button>\";\n" +
    "          }\n" +
    "          if (loadingBubble) {\n" +
    "            loadingBubble.innerHTML = reply + actionHtml;\n" +
    "            var log = document.getElementById('chatLog');\n" +
    "            if (log) log.scrollTop = log.scrollHeight;\n" +
    "          }\n" +
    "        })\n" +
    "        .withFailureHandler(function(err) {\n" +
    "          isChatProcessing = false;\n" +
    "          if (btn) btn.disabled = false;\n" +
    "          if (inp) {\n" +
    "            inp.disabled = false;\n" +
    "            inp.focus();\n" +
    "          }\n" +
    "          if (loadingBubble) {\n" +
    "            loadingBubble.innerHTML = '질문 처리 중 오류 발생: ' + (err.message || err);\n" +
    "          }\n" +
    "        })\n" +
    "        .askPipelineAssistant(val);\n" +
    "    }\n" +
    "\n" +
    "    function runChatAction(actionName, taskName) {\n" +
    "      if (actionName === 'toggleApiKeyBox') {\n" +
    "        toggleApiKeyBox(true);\n" +
    "      } else if (actionName === 'openDashboardSheet') {\n" +
    "        callServer('openDashboardSheet', '실행 내역 열기');\n" +
    "      } else if (actionName === 'refreshStatus') {\n" +
    "        refreshStatus();\n" +
    "      } else if (actionName === 'promptAndRunIdeaMemo') {\n" +
    "        toggleIdeaBox(true);\n" +
    "      } else if (actionName === 'promptAndRunMarketerDirective') {\n" +
    "        toggleDirectiveBox(true);\n" +
    "      } else if (actionName === 'forceRunInitialContent') {\n" +
    "        callServer('forceRunInitialContent', '초판 콘텐츠 전체 재생성');\n" +
    "      } else {\n" +
    "        callServer(actionName, taskName);\n" +
    "      }\n" +
    "    }\n" +
    "\n" +
    "    // 패널 열림 시 최초 1회 상태 자동 조회\n" +
    "    window.onload = function() {\n" +
    "      refreshStatus();\n" +
    "    };\n" +
    "  </script>\n" +
    "</body>\n" +
    "</html>";
}

