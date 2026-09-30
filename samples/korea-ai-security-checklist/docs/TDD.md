<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 기술 상세 설계서 (TDD): Gemini 도입을 위한 한국형 AI 보안성 심의 체크리스트 진단기

## 1. 아키텍처 개요 및 설계 원칙
본 도구는 구글 클라우드 공식 보안 약관/인증 카탈로그(`CHECKLIST_ITEMS`)와 Cloud Resource Manager, Cloud Logging, Cloud KMS 등 GCP API의 실시간 감사 결과를 통합 대조하여 표준 마크다운 소명서(`report.md`)를 자동 산출하는 순수 파이썬 단일 실행 도구(`diagnose.py`)로 구성된다.

---

## 2. 기능 요구 사항 (Functional Requirements)

### FR-01: 20대 핵심 보안 체크리스트 카탈로그 내장
- AI 거버넌스(4문항), 데이터 주권(2문항), 암호화(2문항), 네트워크/접근통제(3문항), 감사로깅/보존(3문항), AI안전/개인정보(2문항), 공급망/라이프사이클(4문항) 등 총 20개 문항을 정규화한다.

### FR-02: 실시간 GCP 리소스 보안 감사
- `gcloud resource-manager org-policies list` 명령을 통해 핵심 보안 조직 정책 적용 여부를 실측 확인한다.
- 리전 엔드포인트 격리 및 Audit Logs 활성화 상태를 실시간 대조하여 PASS/WARN 판정을 내린다.

### FR-03: 공식 정책/인증 소명 자동 결합
- ISO/IEC 42001, No-Training, No-Human-Review 등 기술적으로 직접 쿼리하기 어려운 정책적 항목에 대해 구글 공식 보안 약관(CDPA) URL과 공인 소명 문구를 완벽히 자동 매핑한다.

### FR-04: CISO 제출용 완제품 소명서 (report.md) 생성
- 터미널 출력과 함께 표 서식의 마크다운 소명서(`report.md`)를 자동 덮어쓰기하여 즉시 사내 결재 및 제출 증적으로 활용할 수 있도록 지원한다.

---

## 3. 비기능 요구 사항 (Non-Functional Requirements)

### NFR-01: 최소 IAM 권한 준수
- 본 도구는 읽기 전용 진단 스크립트로서 자원을 변경하지 않으며, 최소 조회 권한만 요구한다.

### NFR-02: 가상 실행 모드 (--dry-run)
- 실제 GCP 프로젝트 연결 없이도 1초 만에 20대 전 항목 완제품 소명서가 즉시 생성되어 오프라인 환경에서도 활용할 수 있어야 한다.
