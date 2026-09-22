<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 비즈니스 요구 사항 명세서 (BRD): Gemini Enterprise 추가 과금 방어 및 비인가 API 호출 차단 가드

## 1. 배경 및 목적
Gemini Enterprise 전사 도입 환경에서 라이선스 일일 풀링 쿼터 초과 쓰로틀링(업무 중단) 위험뿐만 아니라, 임직원이 공식 계정으로 Google AI Studio 등에 접근하여 회사 결제 계정(Cloud Billing)으로 API 키를 발급하거나 유료 API를 호출하는 섀도우 과금 누수를 원천 차단하고, 계열사 중간 관리자 권한 거버넌스(RBAC)를 진단·처방한다.

사내 클라우드 운영 환경에서 인프라 담당자와 보안 및 FinOps 실무자가 수동 콘솔 점검에 의존할 경우 설정 누락, 비의도적 유료 과금 발생, 계열사 결제 권한 남용이 발생할 수 있다. 본 미니 프로젝트(`gemini-enterprise-overage-guard`)는 현장 실무에서 즉시 실행 가능한 자동화 진단 및 4대 기술적 조치 가이드를 제공하여 비용 통제 안정성을 체계적으로 확보한다.

---

## 2. 핵심 비즈니스 요구 사항 (Business Requirements)

| 요구 사항 ID | 요구 사항 명칭 | 상세 설명 | 우선순위 |
| :--- | :--- | :--- | :--- |
| **BR-01** | **Gemini Enterprise Overage 과금 및 쓰로틀링 위험 탐지** | 에디션별 일일 풀링 쿼터 소진율 및 Overage Toggle(ON/OFF) 상태를 점검하여 업무 중단과 초과 과금 위험을 동시 차단해야 하는 경우 | 필수 (P0) |
| **BR-02** | **Google AI Studio 비의도적 API 키 발급 차단 점검** | 일반 사용자가 AI Studio에서 회사 결제 계정 프로젝트를 선택해 API 키를 발급하지 못하도록 조직 정책 적용 상태를 검증해야 하는 경우 | 필수 (P0) |
| **BR-03** | **Generative Language API 활성화 및 백엔드 호출 제한** | 계열사 프로젝트 내 `generativelanguage.googleapis.com` 비활성화 및 제한 여부를 점검하여 유료 API 호출 경로를 원천 차단해야 하는 경우 | 필수 (P0) |
| **BR-04** | **계열사 위임 관리자 결제 권한(Billing RBAC) 거버넌스** | 계열사 IT 관리자에게 `roles/billing.admin` 또는 `roles/billing.user`가 과다 부여되지 않고 OU 맞춤 역할만 부여되었는지 점검해야 하는 경우 | 필수 (P0) |

---

## 3. 대상 독자 및 이해관계자 (Target Audience)
- **인프라 및 플랫폼 아키텍트 (`#Architect`)**: 전사 Gemini Enterprise 배포 표준 수립 및 조직 정책 정합성 검증
- **비용 및 거버넌스 관리자 (`#FinOps`)**: 섀도우 과금 누수 차단 및 Cloud Billing 지출 한도(Spend Cap) 관리
- **보안 및 규제 준수 실무자 (`#SecOps`)**: 최소 권한 원칙(PoLP) 및 API 키 발급 제한 통제 정책 검증
