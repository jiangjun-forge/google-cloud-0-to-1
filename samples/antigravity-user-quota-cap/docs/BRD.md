<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 비즈니스 요구 사항 명세서 (BRD): Antigravity 사용자별 사용량 모니터링 및 쿼터 캡 진단기

## 1. 비즈니스 배경 및 문제 정의
Google Antigravity(데스크톱, CLI, IDE 확장 프로그램)를 전사 도입한 기업에서 개발자들의 프롬프트 및 코드 자동완성 트래픽이 증가함에 따라, 특정 헤비 유저의 과도한 토큰 소모로 인해 조직 전체의 풀링 쿼터가 조기 소진되거나 예산이 초과되는 위험이 발생한다.

현재 Google Cloud 콘솔은 프로젝트 단위 총량 모니터링만 기본 제공하며 개발자 개인별 사용량 제한(Per-user Quota Cap) 기능을 직접 제공하지 않는다. 따라서 인프라 및 FinOps 관리자가 사용자별 토큰 소비량을 실시간으로 파악하고, 일일 임계치를 초과한 사용자를 식별하여 안전하게 통제할 수 있는 자동화 진단 체계가 필수적이다.

---

## 2. 비즈니스 요구 사항 목록

### BR-01: 사용자별 토큰 및 요청 사용량 투명성 확보
- Cloud Logging의 `businessaicode.googleapis.com/inference_response` 원천 로그를 분석하여 개발자 계정(`user:`)별 총 토큰(Prompt + Candidate), 요청 수, 사용 클라이언트(VS Code, JetBrains, CLI) 현황을 산출해야 한다.

### BR-02: 일일/주간 쿼터 캡(Cap) 초과자 식별 및 위험도 판정
- 관리자가 지정한 기간별 토큰 캡(예: 1일 500,000 토큰)을 기준으로 초과 사용자를 즉시 식별하고, 전체 사용자 대비 통제 가능 비율(Coverage Ratio)을 도출해야 한다.

### BR-03: 안전한 읽기 전용 진단 및 마커 역할 기반 처방 제시
- 고객 운영 환경에 비인가 쓰기 작업을 가하지 않는 안전한 읽기 전용 스캔을 원칙으로 하되, 캡 초과자에 대해 프로젝트 IAM 레벨에서 제한 마커 역할(`CustomAntigravityCapBlocked`)을 적용하거나 복구할 수 있는 구체적인 처방 명령어를 제공해야 한다.

### BR-04: 엔터프라이즈 자동화 배치 도구와의 연계(Handoff) 지원
- 진단 이후 실제 15분 주기 자동 차단/복구 배치를 프로덕션 환경에 배포하고자 하는 고객을 위해 검증된 오픈소스 솔루션(`agy-admin-cli`)으로의 원활한 연계 가이드를 제공해야 한다.
