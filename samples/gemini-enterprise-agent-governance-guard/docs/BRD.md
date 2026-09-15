<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 비즈니스 요구 사항 명세서 (BRD): Gemini Enterprise 에이전트 마켓플레이스 차단 및 사내 거버넌스 진단기 (`gemini-enterprise-agent-governance-guard`)

## 1. 배경 및 목적
Gemini Enterprise 환경에서 외부 공개 에이전트 마켓플레이스 접근 차단, 사내 승인 커스텀 에이전트 강제 정책, 미승인 스킬 체이닝 위험 및 Microsoft Entra ID(Workforce Identity Federation) SSO 400 인증 오류를 1분 만에 자동 진단하고 복구 처방을 제공하는 도구다.

사내 클라우드 운영 환경에서 인프라 담당자와 보안 및 아키텍처 실무자가 수동 콘솔 점검에 의존할 경우 설정 누락, 장애 인지 지연, 불필요한 비용 누수가 발생할 수 있다. 본 미니 프로젝트(`gemini-enterprise-agent-governance-guard`)는 현장 실무에서 즉시 실행 가능한 자동화 진단 및 조치 가이드를 제공하여 운영 안정성을 체계적으로 확보한다.

---

## 2. 핵심 비즈니스 요구 사항 (Business Requirements)

| 요구 사항 ID | 요구 사항 명칭 | 상세 설명 | 우선순위 |
| :--- | :--- | :--- | :--- |
| **BR-01** | **현장 장애 및 리스크 사전 탐지** | Gemini Enterprise 에이전트 마켓플레이스 차단 및 사내 거버넌스 진단기 (`gemini-enterprise-agent-governance-guard`) 관련 운영 리스크 및 설정 누락을 사전에 식별해야 하는 경우 | 필수 (P0) |
| **BR-02** | **표준화된 자동 진단 체계 구축** | 수동 콘솔 점검에 따른 인적 오류와 장애 복구 지연 시간을 단축해야 하는 경우 | 필수 (P0) |
| **BR-03** | **가상 실행(Dry-run) 기반 무중단 사전 검증** | 실제 GCP 과금 발생 전 가상 실행(--dry-run)으로 안전하게 정책을 검증해야 하는 경우 | 필수 (P0) |
| **BR-04** | **실무자 조치 가이드 및 자원 정리(Teardown) 안내** | 비개발 직군과 운영 실무자가 즉시 참조할 수 있는 콘솔 조치 경로와 테스트 리소스 정리 절차를 제공한다. | 권장 (P1) |

---

## 3. 대상 독자 및 이해관계자 (Target Audience)
- **인프라 및 플랫폼 아키텍트 (`#Architect`)**: 멀티 프로젝트 아키텍처 표준 수립 및 설정 정합성 검증
- **클라우드 개발 및 운영 실무자 (`#Developer`)**: 배포 파이프라인 및 운영 리소스 상태 신속 점검
- **보안 및 비용 거버넌스 담당자 (`#FinOps`, `#SecOps`)**: 최소 권한 원칙(`roles/discoveryengine.viewer, roles/iam.workforcePoolViewer`) 준수 및 리소스 과금 누수 예방
