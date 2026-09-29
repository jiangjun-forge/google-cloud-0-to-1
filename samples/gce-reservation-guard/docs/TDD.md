<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 기술 상세 설계서 (TDD): Compute Engine 하드웨어 예약 및 CUD 용량 보장 통합 진단기

## 1. 아키텍처 개요 및 설계 원칙
본 도구는 Cloud Logging API, Compute Engine Commitments API, Reservations API, Future Reservations API를 종합 조회하여 CUD 용량 정합성과 사전 예약 승인 상태를 원클릭으로 검증하는 순수 파이썬 단일 실행 도구(`diagnose.py`)로 구성된다.

---

## 2. 기능 요구 사항 (Functional Requirements)

### FR-01: 스톡아웃 감사 로그 분석
- `jsonPayload.event_subtype="compute.instances.insert"` 및 `protoPayload.status.message:"ZONE_RESOURCE_POOL_EXHAUSTED"` 필터를 통해 최근 실패 이벤트를 추출한다.

### FR-02: CUD 약정 및 온디맨드 Reservation 대조 엔진
- `gcloud compute commitments list` 및 `gcloud compute reservations list` 결과를 파싱하여 CUD vCPU 총량과 Reservation vCPU 총량을 비교하고 커버리지를 계산한다.

### FR-03: Future Reservation 상태 파싱 및 미제출 탐지
- `gcloud compute future-reservations list` 결과를 분석하여 `status == "DRAFTING"`인 항목에 대해 즉시 실행 가능한 `gcloud compute future-reservations submit` 명령어를 생성한다.

### FR-04: 마크다운 리포트 (report.md) 자동 생성
- 터미널 출력과 완벽히 동기화된 표준 마크다운 리포트를 자동 생성 및 덮어쓰기한다.

---

## 3. 비기능 요구 사항 (Non-Functional Requirements)

### NFR-01: 최소 IAM 권한 준수
- 본 도구는 읽기 전용 진단 스크립트로서 `roles/compute.viewer` 및 `roles/logging.viewer` 권한만 요구한다.

### NFR-02: 순수 파이썬 단일 실행 및 가상 모드 지원
- 외부 의존성 없이 `python diagnose.py --dry-run` 가상 실행을 완벽히 지원한다.
