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

  // 인증 방식: 현재 로그인된 구글 계정의 OAuth 2.0 Access Token 기반 자동 인증 (Keyless Zero-Setup)
  // 비개발자 마케터가 API Key를 발급받을 필요 없이 구글 계정 로그인 권한으로 직접 안전하게 호출됨
  AUTH_MODE: "OAUTH",
  
  // Google AI Studio 엔드포인트 및 태스크별 최적 모델 지정 (As of 2026-10-13)
  // 단일 모델에 의존하지 않고 작업별 특성(속도, 이미지, 영상)에 맞추어 검증된 모델을 취사선택함
  BASE_URL: "https://generativelanguage.googleapis.com/v1beta/models",
  GEMINI_MODEL: "gemini-3.8-flash",
  MODEL_GENERATOR: "gemini-3.8-flash", // 콘텐츠 발상 및 멀티모달 소재 양산 모델
  MODEL_JUDGE: "gemini-3.8-flash",     // 25인 AI 페르소나 다면 평가 및 가드레일 판정 모델
  IMAGE_MODEL_NAME: "gemini-2.5-flash-image", // 광고 소재 비주얼 이미지 생성 모델
  VIDEO_MODEL_NAME: "veo-3.1-generate-001",   // 모바일 숏폼 영상 생성 모델
  EMBEDDING_MODEL: "text-multilingual-embedding-002", // 한국어 및 다국어 특화 텍스트 임베딩 모델
  EMBEDDING_DIM: 128,                         // Matryoshka Representation Learning(MRL) 축소 차원 규격
  
  // 구글 드라이브 핵심 기획/명세/콘텐츠 문서 파일명
  PLAN_DOC_NAME: "PLAN",               // 마케팅 캠페인 기획서 전문
  SPEC_DOC_NAME: "SPEC",               // 멀티 채널 콘텐츠 제작 명세서 (이미지, 숏폼, 카피 규격)
  CONTENT_DOC_NAME: "campaign_content", // 멀티 채널 마케팅 콘텐츠 전문 (카피라이팅 및 영상 콘티)

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
      duration: "15초~30초",
      channel: "유튜브 쇼츠, 인스타그램 릴스, 틱톡"
    }
  },
  
  // QuickChart REST API 엔드포인트 (t-SNE 여론 군집 지형도 렌더링)
  QUICKCHART_ENDPOINT: "https://quickchart.io/chart"
};
