<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 비즈니스 요구 사항 명세서 (BRD): Gemini 도입을 위한 한국형 AI 보안성 심의 체크리스트 진단기

## 1. 비즈니스 배경 및 문제 정의
기업이 생성형 인공 지능(Gemini API, Vertex AI, Gemini Enterprise App)을 전사 도입할 때 마주하는 최대의 내부 관문은 사내 정보보호팀 및 CISO의 '보안성 심의' 절차다. 보안팀은 수십 개 항목의 보안 체크리스트를 요구하지만, 현업 부서와 도입 추진 엔지니어는 구글 클라우드의 공식 약관(No-Training, No Human Review), 공인 인증서(ISO 42001, K-ISMS) 및 사내 인프라의 실제 설정 증적을 신속하게 확보하지 못해 도입이 수개월간 지연된다.

따라서 구글 공식 보안 약관과 사내 GCP 프로젝트의 실제 기술적 통제(VPC-SC, CMEK, Audit Logs) 상태를 실시간 대조하여 20대 핵심 보안 체크리스트 완제품 소명서(`report.md`)를 1분 만에 자동 생성하는 자동화 컴플라이언스 솔루션이 필수적이다.

---

## 2. 비즈니스 요구 사항 목록

### BR-01: 20대 핵심 보안 심의 카탈로그 표준화
- 국내 개인정보보호위원회 「AI 프라이버시 리스크 관리 모델」, KISA AI 보안 요구사항 및 금융보안원 가이드라인을 분석하여 공통 20대 핵심 질의(SEC-01 ~ SEC-20)를 정규화해야 한다.

### BR-02: 구글 공식 보안 약관 및 국제 인증 소명 결합
- 고객 데이터의 모델 재학습 원천 배제(CDPA), 인적 검토 배제(No Human Review), ISO/IEC 42001 및 ISO 27001/17/18 인증에 관한 공식 URL과 법적 소명 문구를 자동으로 매핑해야 한다.

### BR-03: 사내 GCP 인프라의 기술적 보안 통제 실시간 감사
- 서울 리전(asia-northeast3) 엔드포인트 격리, 조직 정책(gcp.resourceLocations, disableServiceAccountKeyCreation 등), CMEK 암호화, VPC-SC, Audit Logs 활성화 상태를 실측 감사하여 증적으로 기재해야 한다.

### BR-04: CISO 및 보안팀 제출용 완제품 소명서 자동 생성
- 진단 실행 즉시 사내 보안팀이나 금융당국에 직접 제출할 수 있는 정형화된 마크다운 리포트(`report.md`)를 자동 덮어쓰기해야 한다.
