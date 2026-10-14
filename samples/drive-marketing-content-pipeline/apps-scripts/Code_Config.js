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
  MODEL_GENERATOR: "gemini-3.8-flash", // 콘텐츠 발상 및 멀티모달 소재 생성 모델
  MODEL_JUDGE: "gemini-3.8-flash", // 25인 AI 페르소나 다면 평가 및 가드레일 판정 모델
  IMAGE_MODEL_NAME: "gemini-nano-banana-2.1", // 광고 소재 비주얼 이미지 생성 최신 공식 GA 모델 (Nano Banana 2.1)
  VIDEO_MODEL_NAME: "veo-3.1-fast-generate-preview", // 모바일 숏폼 영상 생성 25초 초고속 모델 (Veo 3.1 Fast)
  EMBEDDING_MODEL: "text-multilingual-embedding-002", // 한국어 및 다국어 특화 텍스트 임베딩 모델
  EMBEDDING_DIM: 128, // Matryoshka Representation Learning(MRL) 축소 차원 규격

  // API 호출 회복 탄력성(Resilience) 및 런타임 제약 가드레일
  HTTP_MAX_RETRIES: 3, // 429 및 5xx 일시적 오류 시 최대 재시도 횟수
  HTTP_BASE_DELAY_MS: 1500, // 지수 백오프 기본 대기 시간 (ms)
  MAX_MEDIA_PAYLOAD_MB: 35, // Apps Script 단일 페이로드 안전 상한 (MB)
  
  // 구글 드라이브 핵심 기획/명세/콘텐츠 문서 파일명
  PLAN_DOC_NAME: "PLAN", // 마케팅 캠페인 기획서 전문
  SPEC_DOC_NAME: "SPEC", // 멀티 채널 콘텐츠 제작 명세서 (이미지, 숏폼, 카피 규격)
  CONTENT_DOC_NAME: "campaign_content", // 멀티 채널 마케팅 콘텐츠 전문 (카피라이팅 및 영상 콘티)
  PERSONA_FILE_NAME: "ai_personas.json", // 25인 타깃 AI 페르소나 마스터 데이터 (캠페인 루트 직속)
  PROMPTS_FOLDER_NAME: "prompts", // 마케터 수정용 프롬프트 구글 독스 보관 폴더명
  DIRECTIVE_DOC_NAME: "마케터 보정 지침", // 마케터 전용 의사 결정 및 보정 지침서 (AI 덮어쓰기 금지)

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

  // 6대 프롬프트 구글 독스 메타데이터 및 최소 안전 폴백 (오프라인/네트워크 장애 대비용)
  DEFAULT_PROMPTS: {
    "01_idea_to_plan": {
      title: "01_idea_to_plan",
      description: "마케팅 캠페인 기획서(PLAN) 및 콘텐츠 제작 명세서(SPEC) 도출 지침",
      systemInstruction:
        "당신은 엔터프라이즈 브랜드 마케팅 수석 디렉터이다. 아이디어 메모로부터 마케팅 캠페인 기획서(PLAN)와 제작 명세서(SPEC)를 '===SPEC_DELIMITER===' 구분자로 분리하여 전문적인 마크다운으로 작성하라. 한글 복합어는 철저히 띄어 쓰고 이모지와 중간 점은 일절 배제하라."
    },
    "02_content_generation": {
      title: "02_content_generation",
      description: "초판 마케팅 카피라이팅 및 모바일 숏폼 영상 콘티 생성 지침",
      systemInstruction:
        "당신은 크리에이티브 마케팅 디렉터이다. 기획서(PLAN)와 제작 명세서(SPEC)를 준수하여 채널별 카피라이팅과 15초 모바일 숏폼 영상(9:16) 연출 콘티가 통합된 campaign_content 구글 독스를 작성하라. 한글 복합어는 철저히 띄어 쓰고 이모지와 중간 점은 일절 배제하라."
    },
    "03_persona_evaluation": {
      title: "03_persona_evaluation",
      description: "25인 한국인 마스터 AI 페르소나 다면 평가 및 세부 의견 포인트 도출 지침",
      systemInstruction:
        "당신은 엔터프라이즈 마케팅 리서치 분석 AI이다. 공개된 마케팅 콘텐츠를 25인 한국인 가상 페르소나 관점에서 다면 평가하고, 1인당 2~4개의 세부 의견 포인트(points 배열, 총 50~80개)를 포함하는 순수 JSON 배열만 반환하라. 한글 복합어는 철저히 띄어 쓰고 이모지와 중간 점은 배제하라."
    },
    "04_feedback_summary": {
      title: "04_feedback_summary",
      description: "고객 VoC 및 VLM 멀티모달 분석 기반 피드백 종합 분석 보고서 지침",
      systemInstruction:
        "당신은 CMO 전속 수석 분석관이다. 25인 페르소나 다면 평가, 고객 VoC 설문 응답, 실제 제출된 미디어 VLM 분석 결과를 종합하여 feedback_summary 구글 독스를 작성하라. 실제 제출 미디어가 없으면 미제출로 명시하고, 문서 하단에 AI 추천 보정 방향 요약을 포함하라. 한글 복합어는 철저히 띄어 쓰라."
    },
    "05_content_revision": {
      title: "05_content_revision",
      description: "피드백 요약서 및 독립된 마케터 보정 지침서 반영 차기 리비전 콘텐츠 보정 지침",
      systemInstruction:
        "당신은 총괄 크리에이티브 디렉터이다. 직전 마케팅 콘텐츠와 피드백 요약본, 그리고 독립된 '마케터 보정 지침' 문서에 명시된 마케터 최종 의사 결정을 최우선 구속력으로 반영하여 개정된 광고 카피와 숏폼 영상 콘티를 완성도 높은 campaign_content 구글 독스로 작성하라. 한글 복합어는 철저히 띄어 쓰고 이모지와 중간 점은 배제하라."
    },
    "06_visual_prompt": {
      title: "06_visual_prompt",
      description: "비주얼 이미지 3종 및 Veo 숏폼 영상 프롬프트 엔지니어링 지침",
      systemInstruction:
        "당신은 AI 아트 디렉터이다. 캠페인 카피와 마케터 의사 결정을 분석하여 Gemini 이미지 모델(Nano Banana 2.1) 및 Veo 비디오 모델에 입력할 2~3문장의 구체적이고 감각적인 영문 프롬프트(Visual Prompt)를 작성하라. 설명 없이 영문 프롬프트만 출력하라."
    }
  }
};
