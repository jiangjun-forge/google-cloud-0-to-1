<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# Gemini Enterprise 공식 프롬프트/응답 로깅 및 계정별 사용량 분석기 비즈니스 요구 사항 명세서 (BRD)

본 문서는 사내 제미나이 엔터프라이즈 앱(Gemini Enterprise app) 환경에서 공식 내장 '프롬프트 및 응답 로깅(Prompt & Response Logging)' 기능을 활용하여 빅쿼리(BigQuery)로 적재되는 데이터를 기반으로 계정별 토큰 소모량과 사용 패턴을 정량 분석하기 위한 비즈니스 요구 사항 명세서(Business Requirements Document)다.

---

## 1. 추진 배경 및 비즈니스 동기

1. **엔터프라이즈 생성형 AI 사용량 측정 및 비용 내부 정산**:
   - 사내 전 부서에 Gemini Enterprise app이 도입됨에 따라, 어떤 부서와 계정이 AI 모델을 얼마나 활용하고 있는지 파악하여 라이선스 비용 분배 및 내부 정산을 수행해야 하는 FinOps 요구가 급증하고 있다.
   - 복잡한 프록시나 서드파티 로깅 도구 없이 구글 클라우드 공식 내장 로깅 기능을 활성화하고 즉시 표준 리포트를 추출할 수 있는 체계가 필수적이다.

2. **사내 규정 준수 및 보안 감사 이력 확보**:
   - 임직원이 AI 모델과 나눈 대화 프롬프트와 모델 응답 텍스트를 장기 보관하고, 규정 위반이나 보안 감사 발생 시 신속하게 역추적할 수 있는 중앙 로그 저장소가 요구된다.

---

## 2. 핵심 비즈니스 요구 사항 목록 (Business Requirements)

| 요구 사항 ID | 구분 | 핵심 비즈니스 목표 및 요구 명세 |
| :--- | :--- | :--- |
| **BR-01** | 공식 내장 로깅 활성화 안내 | Gemini Enterprise app 관리 콘솔에서 BigQuery 직접 내보내기(Direct Export)를 활성화하는 표준 절차를 제공해야 한다. |
| **BR-02** | 계정별 토큰 소모량 집계 | BigQuery에 수집된 원천 로그를 기반으로 사용자 계정별 호출 횟수, 입력/출력/총 토큰량, 평균 지연시간을 1분 내에 산출해야 한다. |
| **BR-03** | 가상 실행 스모크 테스트 | 실제 BigQuery 권한이나 데이터가 없는 환경에서도 `--dry-run`을 통해 표준 집계 쿼리와 모의 분석 리포트를 즉시 검증할 수 있어야 한다. |
| **BR-04** | 최소 권한 및 무중단 운영 | 로그 수집은 구글 관리형 파이프라인으로 무중단 구동되며, 분석가는 단순 BigQuery 뷰어 권한(`roles/bigquery.dataViewer`)만으로 조회 가능해야 한다. |

---

## 3. 기대 효과 및 비즈니스 KPI

1. **로깅 인프라 구축 공수 100% 절감**: 별도 프록시 서버나 로그 싱크 파이프라인 개발 없이 콘솔 토글 1회로 구축 완료.
2. **부서별 AI 비용 정산 정확도 100% 확보**: 추정치가 아닌 실제 공식 토큰 카운트 기반 정밀 정산 달성.
