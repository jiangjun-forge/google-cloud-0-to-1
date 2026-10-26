<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 비즈니스 요구 사항 명세서 (BRD): 제미나이 엔터프라이즈(GE app) vs 버텍스 AI(Vertex AI) 지연 시간 및 플래너 궤적 분석기 (`gemini-enterprise-latency-profiler`)

## 1. 배경 및 목적
사내 엔터프라이즈 GE app(Gemini Enterprise app)의 공식 `streamAssist` 스트리밍 대화 엔드포인트와 버텍스 AI(Vertex AI) 순수 제미나이(Gemini) 파운데이션 모델의 `streamGenerateContent` 엔드포인트를 실측하여, 체감 초기 응답 지연(TTFT), 전체 E2E 완료 시간, 내부 플래너 궤적(Planner Steps), RAG 검색 및 거버넌스 오버헤드(Delta)를 정밀 계측하고 워터폴(Waterfall) 차트 및 궤적 리포트를 제공하는 실무 진단 도구다.

사내 클라우드 운영 환경에서 인프라 담당자와 보안 및 아키텍처 실무자가 수동 콘솔 점검에 의존할 경우 설정 누락, 장애 인지 지연, 불필요한 비용 누수가 발생할 수 있다. 본 미니 프로젝트(`gemini-enterprise-latency-profiler`)는 현장 실무에서 즉시 실행 가능한 자동화 진단 및 조치 가이드를 제공하여 운영 안정성을 체계적으로 확보한다.

---

## 2. 핵심 비즈니스 요구 사항 (Business Requirements)

| 요구 사항 ID | 요구 사항 명칭 | 상세 설명 | 우선순위 |
| :--- | :--- | :--- | :--- |
| **BR-01** | **GE App 실대화 스트리밍 E2E 실측** | 사내 GE app의 `streamAssist` 엔드포인트를 직접 호출하여 첫 청크 도달 시간(TTFT)과 전체 완료 시간을 정밀 계측하여야 한다. | 필수 (P0) |
| **BR-02** | **어시스턴트 플래너 실행 궤적(Trace) 추출** | `diagnosticInfo.plannerSteps`를 파싱하여 의도 분석, 검색 플래닝, 그라운딩 컨텍스트 수집 등 단계별 소요 시간을 타임라인으로 시각화하여야 한다. | 필수 (P0) |
| **BR-03** | **Vertex AI Gemini 순수 API 1:1 대조군 분석** | 동일 프롬프트로 버텍스 AI 순수 파운데이션 모델 스트리밍을 호출하여 엔터프라이즈 RAG/보안 계층에서 추가되는 오버헤드(Delta)를 정량화하여야 한다. | 필수 (P0) |
| **BR-04** | **가상 실행(Dry-run) 기반 무중단 사전 검증** | 실제 구글 클라우드(Google Cloud) 과금 및 호출 발생 전 가상 실행(--dry-run)으로 안전하게 궤적 및 리포트를 검증하여야 한다. | 필수 (P0) |
| **BR-05** | **사내 거버넌스 4대 필수 표준 라벨링 준수** | 사내 거버넌스, FinOps 비용 배분 및 자원 추적성을 위해 진단 리소스 생성 및 매니페스트에 4대 표준 라벨(`managed-by`, `scenario`, `env`, `created-by`)을 필수로 주입하여야 한다. | 필수 (P0) |

---

## 3. 대상 독자 및 이해관계자 (Target Audience)
- **인프라 및 플랫폼 아키텍트 (`#Architect`)**: GE App 대화창 체감 지연 원인 규명 및 아키텍처 최적화 수립
- **클라우드 개발 및 AI 엔지니어 (`#Developer`)**: Assistant 플래너 궤적 추적 및 Vertex AI 직결 레이턴시 비교
- **보안 및 거버넌스 담당자 (`#SecOps`, `#FinOps`)**: 사내 RAG 검색 및 출처 검증에 소요되는 엔터프라이즈 신뢰 비용 분석
