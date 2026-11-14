<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

> [!IMPORTANT]
> **구글 (Google LLC) 참조용 샘플 고지 사항**:
> 본 프로젝트의 모든 소스 코드와 문서는 Google LLC의 소유이며, Apache-2.0 라이선스에 따라 오직 **참조용 샘플 (Sample / Reference Only)** 목적으로만 제공된다. 프로덕션 환경에 그대로 사용할 수 없으며, 사전 통지 없이 언제든 내용이 수정, 변경 또는 삭제될 수 있다.

# 비즈니스 요구 사항 명세서 (BRD): 금융위원회 혁신 금융 서비스(생성형 AI 망 분리 샌드박스) 사전 심사 도구 (korea-fsc-sandbox-helper)

## 1. 배경 및 목적
대한민국 금융권에서 생성형 AI 및 SaaS를 내부 업무망이나 대고객 서비스에 연동하려면 금융위원회의 혁신 금융 서비스(규제 샌드박스) 지정 및 금융보안원의 보안성 심의를 통과해야 한다. 그러나 신청 기업들이 기술 기능 설명에만 치중하고 정량적 소비자 편익, 배상 책임 보험(사고당 10억 원/연간 20억 원), 실증 한도 차단기(Circuit Breaker), 논리적 망 분리 대체 통제(VPC-SC Enforced, CMEK, WORM 로그) 등 필수 법정 요건을 누락하여 서류 반려 및 수개월의 일정 지연을 겪는 문제를 해결한다.

## 2. 비즈니스 요구 사항 (Business Requirements)

| 요구 사항 ID | 요구 사항 명칭 | 상세 설명 및 수용 기준 (Acceptance Criteria) | 우선순위 |
| :---: | :--- | :--- | :---: |
| **BR-01** | 금융 소비자 편익 및 보호 대책 사전 검증 | 금융혁신지원 특별법 제13조 및 시행령 제17조에 따른 정량적 편익 수치, 배상 책임 보험(사고당 10억 원/연간 20억 원 이상) 확보, 개인 신용 정보 가명화 및 무학습 보장 요건을 점검한다. | P0 |
| **BR-02** | 규제 특례 필요성 및 실증 리스크 한도 검증 | 전자금융감독규정 제15조 핀포인트 특례 적시 여부, 실증 한도(고객 수/거래량 Cap) 90% 경보 및 서킷 브레이커, 특례 만료 30일 전 고지 및 출구 전략(Exit Plan) 수립 여부를 점검한다. | P0 |
| **BR-03** | 서비스 혁신성 및 PoC 기술 성숙도 검증 | 단순 외부 LLM API 래퍼 구조를 배제하고, 사내 금융 지식 베이스 결합 차별성, PoC 실측 정확도/환각 차단율 지표, 금융 생태계 파급 효과를 평가한다. | P0 |
| **BR-04** | 물적 설비 및 논리적 망 분리 6대 보안 통제 검증 | 개발/운영 VPC 분리, 공인 IP 차단 및 Private Service Connect(PSC), VPC-SC(Enforced), 관리자 VDI/Context-Aware Access, 서울 리전 Cloud HSM CMEK, 감사 로그 2년 WORM(Bucket Lock) 적용 상태를 진단한다. | P0 |
| **BR-05** | 역대 금융위/금보원 반려 사례 교차 대조 | 15개 세부 심사 카테고리별 역대 주요 불승인 및 보완 요구 사례를 현재 신청서/아키텍처 미비점과 자동 매칭하여 구체적인 사전 방어 논리를 제시한다. | P0 |
| **BR-06** | 서울 리전 참조 아키텍처 블루프린트 및 Fact-Check | `gemini-3.8-flash`(`global`) 기반으로 서울 리전(`asia-northeast3`) 금융 보안 참조 블루프린트를 생성하고, 인용된 규제/기술 URL의 HTTP 도달성을 검증하여 404 오인용을 차단한다. | P1 |
| **BR-07** | 무과금 가상 실행(`--dry-run`) 및 소명 리포트 생성 | 클라우드 권한이나 과금 없이 5초 안에 전체 심사 점수표와 `report.md` 소명서를 생성하여 보안심의위원회 및 금감원 사전 협의 자료로 즉시 활용할 수 있도록 지원한다. | P0 |
| **BR-08** | 사내 FinOps 및 거버넌스 4대 필수 라벨 준수 | 모든 조치 가이드 및 리소스 생성 명령어에 `managed-by`, `scenario`, `env`, `created-by` 4대 표준 라벨을 100% 반영한다. | P1 |
