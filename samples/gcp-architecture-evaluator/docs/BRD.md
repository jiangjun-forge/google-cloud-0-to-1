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

# 비즈니스 요구 사항 명세서 (BRD): Google Cloud 아키텍처 명세 실전 루브릭 평가기 (As of 2026-11-19)

## 1. 배경 및 목적
AI 에이전트를 활용한 Spec-Driven Development(SDD) 환경에서는 문서의 문장과 형식은 유려하지만, 실제 엔터프라이즈 운영에 필수적인 비기능 요구 사항(보안 경계, 읽기 전용 에이전트 권한 분리, 비용 상한, 장애 격리)이 누락되거나 원시 자료에 없는 SLA 수치가 임의로 생성(환각)되는 문제가 빈번하다.

본 미니 프로젝트(`gcp-architecture-evaluator`)는 작성된 `BRD.md` 및 `SDD.md`(또는 `TDD.md`) 마크다운 문서를 입력받아 (1) 요구 사항 ID 추적성 및 모순 해소 여부, (2) 원문 근거 대비 미태깅 추정 수치 검출, (3) 에이전트 제어 경계(Read-Only vs 실행 서비스 분리, HITL, 양방향 마스킹), (4) Google Cloud Architecture Framework 및 SAIF 기반 7대 아키텍처 차원 실전 체크리스트, (5) 명세 내부 논리 모순, 가독성, 비식별화 및 정규 명칭 준수 여부를 25개 항목 100점 만점으로 자동 채점하여 평가 리포트(`report.md`)를 산출하는 정적 게이트 평가기다.

---

## 2. 핵심 비즈니스 요구 사항 (Business Requirements)

| 요구 사항 ID | 요구 사항 명칭 | 상세 설명 | 우선순위 |
| :--- | :--- | :--- | :--- |
| **BR-01** | **요구 사항 추적성 및 내부 논리 모순 검증** | BRD/Discovery 단계의 `BR-*`, `FR-*`, `NFR-*`, `CON-*` 식별자가 SDD/TDD 설계 문서에 누락 없이 매핑되는지 정적 검증하고, 명세 내부의 논리 모순(`Read-Only` vs 직접 DML, PII 마스킹 vs 원문 로깅 등)을 검출하여야 한다. | 필수 (P0) |
| **BR-02** | **수치 환각 방지 및 가독성 평가** | 문서 내 지연 시간, 비용, 동시성 목표 수치에 출처 또는 `(Proposed)`/`(추정)`/`(가정)` 근거 표기가 누락된 항목과 장문 만연체, 검증 불가 모호어를 탐지하여야 한다. | 필수 (P0) |
| **BR-03** | **Google Cloud 7대 아키텍처 차원 및 SAIF 거버넌스 채점** | 자율성 경계, Agent 토폴로지, SAIF 보안, 신뢰성 및 멱등성, 관측성 및 평가 파이프라인, 지연 및 토큰 경제성, ADR 트레이드오프 7대 차원을 정량 점수로 채점하여야 한다. | 필수 (P0) |
| **BR-04** | **가상 실행(Dry-run) 및 로컬 파일 직접 평가 지원** | 외부 API 호출이나 과금 없이 `--dry-run`으로 즉시 루브릭 채점을 시연하고, `--sdd`/`--brd` 인자로 임의의 설계 문서를 평가할 수 있어야 한다. | 필수 (P0) |
| **BR-05** | **비식별화, 구형 명칭 제거 및 거버넌스 안내** | 설계 문서 내 개인 식별 정보(PII), 시크릿 패턴, 구형 제품 명칭 잔존 여부를 검사하고, 표준 리소스 라벨링 적용 가이드를 제공하여야 한다. | 필수 (P0) |

---

## 3. 대상 독자 및 이해 관계자 (Target Audience)
- **클라우드 및 AI 아키텍트 (`#Architect`)**: 구현 착수 전 SDD/TDD 설계서의 엔터프라이즈 완성도 게이트 검증
- **보안 및 거버넌스 검토자 (`#SecOps`)**: 읽기 전용 에이전트 경계, 양방향 PII 마스킹, 감사 로그(WORM) 및 키 관리 통제 누락 점검
- **개발 리드 및 FinOps 담당자 (`#Developer`, `#FinOps`)**: 추적성 매트릭스 정합성 확인 및 토큰/스캔 비용 상한 및 라벨링 누락 사전 차단
