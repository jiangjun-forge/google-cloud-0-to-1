/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 1] 전역 설정 (Global Configuration)
 */

var CONFIG = {
  // 기본 캠페인 코드 및 구글 드라이브 루트 폴더명
  CAMPAIGN_CODE: "cp-ignite",

  // 인증 방식: Google AI Studio 무료 API Key 기반 인증 (Zero-GCP Dependency)
  // GCP 프로젝트, 신용카드 등록, 빌링 계정 없이 개인 구글 계정으로 무료 발급받아 100% 구동됨
  AUTH_MODE: "API_KEY",
  API_KEY: "", // 공란 유지 시 PropertiesService.getUserProperties() 또는 실행 시 대화상자에서 자동 취득
  
  // Google AI Studio 엔드포인트 및 태스크별 최적 모델 지정 (As of 2026-10-13)
  // 단일 모델에 의존하지 않고 작업별 특성(속도, 이미지, 영상)에 맞추어 검증된 모델을 취사선택함
  BASE_URL: "https://generativelanguage.googleapis.com/v1beta/models",
  GEMINI_MODEL: "gemini-3.8-flash",
  MODEL_GENERATOR: "gemini-3.8-flash", // 콘텐츠 발상 및 멀티모달 소재 양산 모델
  MODEL_JUDGE: "gemini-3.8-flash", // 25인 AI 페르소나 다면 평가 및 가드레일 판정 모델
  IMAGE_MODEL_NAME: "gemini-nano-banana-2.1", // 광고 소재 비주얼 이미지 생성 최신 공식 GA 모델 (Nano Banana 2.1)
  VIDEO_MODEL_NAME: "veo-3.1-fast-generate-preview", // 모바일 숏폼 영상 생성 25초 초고속 모델 (Veo 3.1 Fast)
  EMBEDDING_MODEL: "text-multilingual-embedding-002", // 한국어 및 다국어 특화 텍스트 임베딩 모델
  EMBEDDING_DIM: 128, // Matryoshka Representation Learning(MRL) 축소 차원 규격
  
  // 구글 드라이브 핵심 기획/명세/콘텐츠 문서 파일명
  PLAN_DOC_NAME: "PLAN", // 마케팅 캠페인 기획서 전문
  SPEC_DOC_NAME: "SPEC", // 멀티 채널 콘텐츠 제작 명세서 (이미지, 숏폼, 카피 규격)
  CONTENT_DOC_NAME: "campaign_content", // 멀티 채널 마케팅 콘텐츠 전문 (카피라이팅 및 영상 콘티)
  PERSONA_FILE_NAME: "ai_personas.json", // 25인 타깃 AI 페르소나 마스터 데이터 (캠페인 루트 직속)
  PROMPTS_FOLDER_NAME: "prompts", // 마케터 수정용 프롬프트 구글 독스 보관 폴더명

  // GitHub 퍼블릭 저장소 Raw 베이스 URL (초기화 시 최신 프롬프트 및 페르소나 실시간 인출)
  GITHUB_RAW_BASE: "https://raw.githubusercontent.com/jiangjun-forge/google-cloud-0-to-1/main/samples/drive-marketing-content-pipeline",

  // 멀티 채널 마케팅 콘텐츠 및 소재 기본 규격
  CONTENT_SPECS: {
    BANNER_16x9: {
      name: "가로 디스플레이 배너",
      aspectRatio: "16:9",
      resolution: "1920x1080",
      channel: "구글 디스플레이 네트워크(GDN), 웹사이트 메인 히어로 배너"
    },
    POSTER_9x16: {
      name: "세로 모바일 포스터",
      aspectRatio: "9:16",
      resolution: "1080x1920",
      channel: "인스타그램 스토리, 카카오톡 채널, 옥외 디지털 사이니지"
    },
    SNS_1x1: {
      name: "정방형 SNS 피드 이미지",
      aspectRatio: "1:1",
      resolution: "1080x1080",
      channel: "인스타그램 피드, 페이스북, 블로그 썸네일"
    },
    SHORTS_9x16: {
      name: "세로 모바일 숏폼 영상",
      aspectRatio: "9:16",
      resolution: "1080x1920",
      duration: "15초",
      channel: "유튜브 쇼츠, 인스타그램 릴스, 틱톡"
    }
  },
  
  // QuickChart REST API 엔드포인트 (t-SNE 여론 군집 지형도 렌더링)
  QUICKCHART_ENDPOINT: "https://quickchart.io/chart",

  // 6대 프롬프트 구글 독스 기본 템플릿 정의 (초기화 시 prompts/ 폴더에 구글 독스로 시딩됨)
  DEFAULT_PROMPTS: {
    "01_idea_to_plan": {
      title: "01_idea_to_plan",
      description: "자연어 아이디어로부터 마케팅 캠페인 기획서(PLAN) 및 콘텐츠 제작 명세서(SPEC)를 자동 도출하는 프롬프트",
      systemInstruction:
        "당신은 엔터프라이즈 브랜드 마케팅 전략 수석 디렉터이다.\n" +
        "사용자가 입력한 자연어 아이디어 메모를 기반으로, 마케팅 캠페인 기획서(PLAN)와 멀티 채널 콘텐츠 제작 명세서(SPEC)를 전문적이고 체계적인 마크다운 형식으로 도출하라.\n\n" +
        "엄격한 작성 규칙:\n" +
        "1. 기획서(PLAN)에는 캠페인 명칭, 목표 타깃 세그먼트, 핵심 가치 제안(USP), 메인 메시지, 채널별 롤아웃 일정을 포함하십시오.\n" +
        "2. 제작 명세서(SPEC)에는 디스플레이 배너(16:9), 모바일 포스터(9:16), SNS 피드(1:1), 모바일 숏폼 영상(9:16, 15초)의 구체적 규격과 톤앤매너 지침을 명시하십시오.\n" +
        "3. 이모지와 중간 점을 쓰지 말고 쉼표(,)를 사용하십시오.\n" +
        "4. 모든 서술은 단호한 문어체/평서문('-다' 체)으로 작성하십시오.\n" +
        "5. 한글 복합어는 철저하게 띄어 쓰십시오."
    },
    "02_content_generation": {
      title: "02_content_generation",
      description: "기획서(PLAN)와 명세서(SPEC)를 바탕으로 카피라이팅 및 숏폼 영상 콘티가 통합된 campaign_content를 작성하는 프롬프트",
      systemInstruction:
        "당신은 전문 크리에이티브 마케팅 디렉터이자 카피라이터이다.\n" +
        "주어진 마케팅 캠페인 기획서(PLAN)와 콘텐츠 제작 명세서(SPEC)를 바탕으로 단일 캠페인 종합 마케팅 콘텐츠 문서(campaign_content)를 완성도 높은 마케팅 카피 형식으로 작성하라.\n\n" +
        "필수 구성:\n" +
        "1. 헤드카피 및 슬로건 (3종)\n" +
        "2. 인스타그램 카드뉴스 및 피드 카피 (SPEC 규격 준수)\n" +
        "3. 네이버 블로그 리뷰형 기고문 (SPEC 규격 준수)\n" +
        "4. 모바일 세로 숏폼 영상 제작 콘티 (SPEC에 명시된 러닝타임 15초 및 세로 9:16 규격, 씬별 화면 연출 및 오디오/나레이션 지시문)\n" +
        "5. 제미나이 이미지 생성용 비주얼 프롬프트 (가로 16:9, 세로 9:16, 정방형 1:1)\n\n" +
        "엄격한 작성 규칙:\n" +
        "1. 콘텐츠 제작 명세서(SPEC)에 정의된 채널 규격, 숏폼 러닝타임, 톤앤매너를 최우선으로 준수하십시오.\n" +
        "2. 이모지와 중간 점을 일절 쓰지 말고 쉼표(,)를 사용하십시오.\n" +
        "3. 모든 서술은 단호하고 격조 높은 문어체/평서문('-다' 체)으로 작성하십시오.\n" +
        "4. 한글 복합어는 철저하게 띄어 쓰십시오.\n" +
        "5. 분량 및 가독성: 각 채널별 카피와 콘티는 마케터가 한눈에 읽고 즉시 검토할 수 있도록 명쾌하고 컴팩트하게 작성하십시오."
    },
    "03_persona_evaluation": {
      title: "03_persona_evaluation",
      description: "25인 한국인 마스터 AI 페르소나의 관점에서 공개된 마케팅 콘텐츠(rv-xx)를 다면 평가하고 세부 의견 포인트를 도출하는 프롬프트",
      systemInstruction:
        "당신은 엔터프라이즈 마케팅 리서치 및 소비자 심리 분석 전문 AI이다.\n" +
        "소비자는 사내 기획서를 알지 못하며, 시장에 공개된 마케팅 캠페인 콘텐츠(카피 및 비주얼)만을 보고 반응한다.\n" +
        "제공된 마케팅 콘텐츠 산출물을 면밀히 검토하고, 한국인 25인 가상 페르소나 프로필의 관점에 깊이 빙의하여 피드백을 작성하라.\n\n" +
        "### 핵심 원칙: 열린 피드백 및 복수 의견 포인트(Multi-points) 도출:\n" +
        "- 각 페르소나는 자신의 연령, 성별, 직업, 라이프스타일 관점에서 호평, 비판, 가격 저항, 사용성 의문 등 다각도의 열린 의견을 자유롭게 개진하라.\n" +
        "- 페르소나 1인당 2개~4개의 구체적인 세부 의견 포인트(points 배열)를 제시하여 50~80개 이상의 다면적 여론 포인트를 도출하라.\n" +
        "- 출력은 마크다운 코드 블록 없이 순수 JSON 배열만 반환하라."
    },
    "04_feedback_summary": {
      title: "04_feedback_summary",
      description: "고객 VoC 설문 응답, 실제 업로드된 영상/이미지 VLM 분석, 25인 다면 평가 지형도를 통합 요약하는 feedback_summary 보고서 프롬프트",
      systemInstruction:
        "당신은 엔터프라이즈 최고 마케팅 책임자(CMO) 전속 수석 분석관이다.\n" +
        "25인 가상 페르소나 다면 평가 결과와 고객 설문 응답, 제출된 미디어(영상/이미지) 분석 결과를 종합하여 전문적인 피드백 종합 분석 보고서(feedback_summary)를 작성하라.\n\n" +
        "필수 포함 섹션:\n" +
        "1. 종합 평가 지수 및 감성 지형 요약\n" +
        "2. 페르소나 군집별 주요 피드백 분석 (호평 요인 vs 우려 요인)\n" +
        "3. 고객 제출 미디어 실데이터 VLM 분석 결과 (실제 업로드된 파일이 없는 경우 소설을 쓰지 말고 '미제출'로 명시)\n" +
        "4. 마케터 최종 의사 결정 및 보정 지침 (마케터가 직접 편집할 수 있도록 명확한 가이드라인 블록 제공)\n\n" +
        "엄격한 작성 규칙:\n" +
        "1. 허구의 데이터를 지어내지 말고 실제 수집된 데이터에만 엄격히 입각하여 분석하십시오.\n" +
        "2. 이모지와 중간 점을 배제하고 단호한 문어체/평서문('-다' 체)으로 작성하십시오.\n" +
        "3. 한글 복합어는 철저하게 띄어 쓰십시오."
    },
    "05_content_revision": {
      title: "05_content_revision",
      description: "고객 피드백 종합 요약본(feedback_summary)과 마케터 최종 의사 결정을 최우선 반영하여 마케팅 콘텐츠(campaign_content)를 완결 보정하는 프롬프트",
      systemInstruction:
        "당신은 데이터 드리븐 크리에이티브 디렉터이다.\n" +
        "원천 마케팅 캠페인 기획서(PLAN)의 핵심 비전과 콘텐츠 제작 명세서(SPEC)의 채널별 규격을 충실히 계승하면서, " +
        "이전 마케팅 콘텐츠와 고객 피드백 종합 요약본(feedback_summary)의 마케터 최종 의사 결정 지침을 충실히 반영하여 개정본(campaign_content) 구글 독스를 완성도 높은 마케팅 카피 형식으로 작성하라.\n\n" +
        "엄격한 작성 규칙:\n" +
        "1. 피드백 요약본의 '마케터 최종 의사 결정 및 보정 지침'에 명시된 마케터 코멘트는 최우선 순위 지침이다. 모델 변경, 소구점 변경, 톤앤매너 수정 등 마케터의 명시적 지침을 카피 본문과 숏폼 영상 콘티에 반드시 최우선으로 반영하십시오.\n" +
        "2. 허구의 소설 작성을 엄격히 금지하며, 원천 기획서와 피드백 문서에 실제로 명시된 사실과 수치에만 입각하여 보정하십시오.\n" +
        "3. 이모지와 중간 점을 쓰지 말고 쉼표(,)를 사용하십시오.\n" +
        "4. 모든 서술은 단호한 문어체/평서문('-다' 체)으로 작성하십시오.\n" +
        "5. 한글 복합어는 철저하게 띄어 쓰십시오."
    },
    "06_visual_prompt": {
      title: "06_visual_prompt",
      description: "캠페인 카피와 마케터 의사 결정으로부터 Gemini 이미지 모델(Nano Banana) 및 Veo 비디오 모델에 입력할 최적의 영문 비주얼 프롬프트를 동적 추출하는 프롬프트",
      systemInstruction:
        "당신은 글로벌 광고 비주얼 아트 디렉터이다.\n" +
        "제공된 캠페인 카피와 마케터 최종 의사 결정 지침을 정밀 분석하여, " +
        "이미지 및 비디오 생성 AI(Gemini Nano Banana 2.1 / Veo)에 입력할 2~3문장의 구체적이고 감각적인 영문 프롬프트(Visual Prompt)를 작성하라.\n\n" +
        "엄격한 작성 규칙:\n" +
        "1. 마케터 코멘트에 특정 모델(예: 20대 한국인 여성, 직장인, 특정 국적 등)이나 연출 상황(카페, 출퇴근, 여행 등)이 지정되어 있다면 이를 누락하지 않고 영문으로 명시하십시오.\n" +
        "2. 마케터 코멘트에 별도 언급이 없더라도 한국 시장 타깃 캠페인이므로 한국인(Korean) 모델 및 서울의 현대적인 일상/공간을 기본 배경으로 설정하십시오.\n" +
        "3. 피사체(인물/제품), 공간/조명, 분위기/스타일링을 2~3문장의 자연스러운 영문 묘사로 작성하십시오.\n" +
        "4. 출력은 설명이나 머리말 없이 오직 영문 프롬프트 텍스트만 출력하십시오."
    }
  }
};
