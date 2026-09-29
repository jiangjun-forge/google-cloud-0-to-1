<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 비즈니스 요구 사항 명세서 (BRD): Compute Engine 하드웨어 예약 및 CUD 용량 보장 통합 진단기

## 1. 비즈니스 배경 및 문제 정의
대규모 클라우드 인프라를 운영하는 기업에서 CUD(지속 사용 약정)는 비용 절감을 위한 핵심 수단이지만, 이는 요금 할인에 불과하며 물리적 하드웨어 가용성을 보장하지 않는다. CUD 약정만 체결하고 물리적 온디맨드 Reservation을 선점하지 않은 '무방비 약정(Unreserved CUD)' 상태에서 리전 스톡아웃(ZONE_RESOURCE_POOL_EXHAUSTED)이 발생하면 요금은 지속 청구되면서 인스턴스를 띄우지 못하는 심각한 FinOps 손실이 발생한다.

또한 GPU 및 고사양 특수 인스턴스의 안정적 공급을 위해 도입된 Future Reservation(FR) 역시 콘솔에서 신청서 작성 후 제출(Submit)을 누락하여 DRAFTING 상태로 방치되거나 최소 리드 타임(120시간)을 위반하여 신규 서비스 론칭이 지연되는 사고가 빈번하다.

따라서 온디맨드 예약 확보율과 Future Reservation 승인 상태를 단일 도구로 통합 진단하고 즉각적인 조치 처방을 제공하는 솔루션이 필수적이다.

---

## 2. 비즈니스 요구 사항 목록

### BR-01: 스톡아웃 감사 로그 정밀 역추적
- 최근 14일간 발생한 `ZONE_RESOURCE_POOL_EXHAUSTED` 에러 이벤트를 Cloud Audit Logs에서 조회하여 장애 발생 존과 머신 타입을 식별해야 한다.

### BR-02: CUD 약정 대비 온디맨드 Reservation 확보율 진단
- 리전 내 활성 CUD 코어 수와 온디맨드 Reservation 확보 코어 수를 대조하여 물리 용량 보호율(Coverage)을 산출하고, 무방비 약정 존재 여부를 경고해야 한다.

### BR-03: Future Reservation 신청 현황 및 DRAFTING 누락 검출
- 사내 등록된 모든 Future Reservation 신청 내역을 조회하고, DRAFTING(제출 누락) 상태인 항목에 대해 즉시 submit 명령어를 처방해야 한다.

### BR-04: 자동 리포트 생성 및 실무자 조치 처방 제공
- 표준 마크다운 리포트(`report.md`)를 자동 덮어쓰기하여 온디맨드 예약 생성 명령어 및 승인 완결 가이드를 제공해야 한다.
