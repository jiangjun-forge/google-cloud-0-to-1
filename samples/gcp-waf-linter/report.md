<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
-->

> [!IMPORTANT]
> **구글 (Google LLC) 참조용 샘플 고지 사항**:
> 본 리포트는 Google LLC 참조용 샘플 린터의 출력 결과다.

# Google Cloud Well-Architected Framework(WAF) 명세 린터 리포트

- **평가 일시**: 2026-11-19 19:02:24 UTC
- **실행 모드**: `DRY-RUN (모의 명세 시뮬레이션)`
- **참고 프로젝트**: `sample-project-id`
- **평가 대상**: 내장 모의 명세 표본 (sample-corp)
- **종합 점수**: **92 / 100점** (`FAIL` 1건, `WARN` 2건) -> **HOLD (보완 후 재평가 권장)**

---

## 1. 7대 아키텍처 차원 및 모순, 가독성 채점 결과

| 영역 | ID | 점검 항목 | 상태 | 배점 | 평가 상세 |
| :--- | :---: | :--- | :---: | :---: | :--- |
| 1. 자율성 경계 및 성공 기준 | `R-01` | 요구 사항 ID 교차 참조 완전성 | `PASS` | 4/4 | 전체 명세 내 4개 요구 사항 ID 전수 교차 참조됨 |
| 1. 자율성 경계 및 성공 기준 | `R-02` | 읽기 전용 Agent와 실행 평면 분리 | `PASS` | 4/4 | 읽기 전용 에이전트 권한과 상태 변경 실행 평면 분리 확인 |
| 1. 자율성 경계 및 성공 기준 | `R-03` | 고위험 작업 HITL 승인 게이트 | `PASS` | 4/4 | HITL 승인 임계치 및 게이트 명시됨 |
| 1. 자율성 경계 및 성공 기준 | `R-04` | SLA/비용 수치 근거 및 (Proposed) 태깅 | `WARN` | 2/4 | 정량 수치 3건 중 2건에 출처 ID 또는 (Proposed) 태깅 누락 |
| 2. Agent 토폴로지, 컴퓨트 및 도구 | `R-05` | 컴퓨트 런타임 및 Agent 토폴로지 명시 | `PASS` | 4/4 | Google Cloud 런타임 및 에이전트 토폴로지 정의됨 |
| 2. Agent 토폴로지, 컴퓨트 및 도구 | `R-06` | 도구 스키마 및 상태/메모리 경계 | `WARN` | 2/4 | 에이전트 도구 인터페이스 또는 메모리/세션 경계 설계가 부족하다. |
| 2. Agent 토폴로지, 컴퓨트 및 도구 | `R-07` | 아키텍처 시각화(Mermaid 다이어그램) | `PASS` | 4/4 | Mermaid 아키텍처 또는 시퀀스 다이어그램 포함됨 |
| 3. SAIF 보안, 프라이버시 및 컴플라이언스 | `R-08` | 양방향(Ingress+Egress) PII 마스킹 | `PASS` | 4/4 | 입출력 양방향 PII 비식별화 통제 확인 |
| 3. SAIF 보안, 프라이버시 및 컴플라이언스 | `R-09` | 적대적 입력 및 범위 외 질의 차단 | `PASS` | 4/4 | Model Armor 또는 범위 외 입력 차단 게이트 명시됨 |
| 3. SAIF 보안, 프라이버시 및 컴플라이언스 | `R-10` | 암호화(CMEK), 시크릿 및 네트워크 경계 | `PASS` | 4/4 | CMEK, Secret Manager 또는 VPC-SC 경계 통제 확인 |
| 3. SAIF 보안, 프라이버시 및 컴플라이언스 | `R-11` | 설계서 내 PII 및 시크릿 미노출 | `PASS` | 4/4 | 민감 시크릿 및 로컬 홈 경로 노출 없음 |
| 4. 신뢰성, 회복 탄력성 및 상태 무결성 | `R-12` | 다중 영역 가용성 및 RTO/RPO 기준 | `PASS` | 4/4 | 다중 리전/존 및 RTO/RPO 복구 기준 명시 |
| 4. 신뢰성, 회복 탄력성 및 상태 무결성 | `R-13` | 상태 변경 멱등성(Idempotency) 보장 | `PASS` | 4/4 | 재시도 및 중복 실행 방어용 멱등성 잠금 명시됨 |
| 4. 신뢰성, 회복 탄력성 및 상태 무결성 | `R-14` | 타임아웃, 백오프 및 예외 폴백 경로 | `PASS` | 4/4 | 타임아웃, 백오프 또는 예외 분기 경로 정의됨 |
| 5. 관측성, 감사 추적 및 평가 파이프라인 | `R-15` | OpenTelemetry 관측성 및 Eval CI/CD 게이트 | `PASS` | 4/4 | 트레이싱/구조화 로깅 및 평가 회귀 게이트 포함 |
| 5. 관측성, 감사 추적 및 평가 파이프라인 | `R-16` | 불변 감사 로그 보존 (WORM / Bucket Lock) | `PASS` | 4/4 | WORM 감사 로그 보존 정책 포함 |
| 5. 관측성, 감사 추적 및 평가 파이프라인 | `R-17` | FinOps 4대 표준 리소스 라벨링 | `PASS` | 4/4 | 4대 표준 라벨 또는 비용 추적 택소노미 명시됨 |
| 6. 지연 시간 최적화 및 토큰 경제성 | `R-18` | 종단간 지연(p95/TTFT) 및 스트리밍 목표 | `PASS` | 4/4 | E2E 또는 TTFT 레이턴시 목표 명시됨 |
| 6. 지연 시간 최적화 및 토큰 경제성 | `R-19` | 토큰/스캔 비용 상한 및 캐싱 전략 | `PASS` | 4/4 | 토큰 상한, 캐시 TTL 또는 스캔 절감 전략 명시됨 |
| 7. ADR, 모순 교차 검증 및 가독성 | `R-20` | 모순 해소, ADR 및 트레이드오프 근거화 | `PASS` | 4/4 | 아키텍처 트레이드오프 또는 모순 해소 기록 포함 |
| 7. ADR, 모순 교차 검증 및 가독성 | `R-21` | 단계적 출시 범위 분리 (MVP vs Scale) | `PASS` | 4/4 | MVP와 확장 단계 범위가 명시 분리됨 |
| 7. ADR, 모순 교차 검증 및 가독성 | `R-22` | 명세 내부 논리 모순 교차 검출 | `PASS` | 4/4 | Read-Only 경계, PII 로깅, SLA-타임아웃 간 내부 모순 없음 |
| 7. ADR, 모순 교차 검증 및 가독성 | `R-23` | 가독성: 장문 만연체 및 헤딩 계층 정합성 | `PASS` | 4/4 | 문장 호흡이 간결하고 헤딩 계층(H1->H2->H3)이 일관됨 |
| 7. ADR, 모순 교차 검증 및 가독성 | `R-24` | 명확성: 검증 불가 모호어(Weasel Words) 배제 | `PASS` | 4/4 | 검증 불가능한 모호한 형용, 부사 미사용 |
| 7. ADR, 모순 교차 검증 및 가독성 | `R-25` | Google Cloud 최신 서비스, 모델 및 SDK 버전 준수 | `FAIL` | 0/4 | 명칭 갱신(Vertex AI Agent Builder/GEAP -> Agent Platform / Agent Engine) |

---

## 2. 우선 보완 처방 (Action Items)

- **`[FAIL] R-25 (Google Cloud 최신 서비스, 모델 및 SDK 버전 준수)`**: 명칭 갱신(Vertex AI Agent Builder/GEAP -> Agent Platform / Agent Engine)
- **`[WARN] R-04 (SLA/비용 수치 근거 및 (Proposed) 태깅)`**: 정량 수치 3건 중 2건에 출처 ID 또는 (Proposed) 태깅 누락
- **`[WARN] R-06 (도구 스키마 및 상태/메모리 경계)`**: 에이전트 도구 인터페이스 또는 메모리/세션 경계 설계가 부족하다.

---

## 3. 사내 거버넌스 4대 필수 표준 라벨링 및 참고 문서

- **표준 라벨 규약**: `--labels=managed-by=google-cloud-0-to-1,scenario=gcp-waf-linter,env=sample,created-by=customer-engineer`
- Google Cloud Architecture Framework ( https://cloud.google.com/architecture/framework )
- Google Cloud Security Best Practices ( https://cloud.google.com/security/best-practices )
