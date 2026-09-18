# 진단 및 분석 리포트: gce-future-reservation-checker

- **생성 모드**: 모의 실행 (Dry-run)
- **대상 프로젝트**: `sample-project-id`
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 진단 실행 콘솔 출력 결과

```text
Compute Engine GPU 및 특수 인스턴스 Future Reservation 상태 진단 시작 (프로젝트: sample-project-id)
--> 가상 실행 모드 (--dry-run) 활성화: 사전 시뮬레이션 데이터를 분석한다.

===============================================================================================
예약 이름                      영역               수량     상태                 심각도       
-----------------------------------------------------------------------------------------------
fr-g4-robotics-draft       us-south1-a      24     DRAFTING           CRITICAL  
fr-a3-training-pending     us-central1-a    8      PENDING_APPROVAL   WARNING   
fr-g2-inference-approved   asia-northeast3-a 16     APPROVED           WARNING   
===============================================================================================

[발견된 주요 결함 및 처방 조치]

* [심각] fr-g4-robotics-draft (영역: us-south1-a, 상태: DRAFTING)
  - 원인: 예약이 DRAFTING 상태에 머물러 있어 Capacity 심사 큐에 접수되지 않음
  - 원인: autoDeleteAutoCreatedReservations가 활성화되어 CUD 약정 연계 시 조기 소멸 위험 존재
  - 원인: 시작 시점까지 남은 리드 타임이 48.0시간으로 최소 권장 120시간(5일) 미만임
  - 원인: 활성 프로젝트(sample-project-id)와 예약 대상 프로젝트(example-corp-dev)가 일치하지 않음
  - 처방: 콘솔 상세 페이지에서 [제출/Submit] 버튼을 클릭하거나 다음 명령어를 실행한다: gcloud beta compute future-reservations submit fr-g4-robotics-draft --zone=us-south1-a --project=example-corp-dev
  - 처방: CUD 연결을 위해 생성 시 --no-auto-delete-auto-created-reservations 플래그를 필수로 지정해야 한다.
  - 처방: Future Reservation 사전 신청 쿼터 정책 기준에 맞추어 시작 일시를 최소 120시간(5일) 이후로 수정하여 재신청한다.
  - 처방: 조회 및 심사 요청 시 정확한 프로젝트 ID(example-corp-dev)를 일치시켜 전달한다.

* [주의] fr-a3-training-pending (영역: us-central1-a, 상태: PENDING_APPROVAL)
  - 원인: 활성 프로젝트(sample-project-id)와 예약 대상 프로젝트(example-corp-dev)가 일치하지 않음
  - 처방: 조회 및 심사 요청 시 정확한 프로젝트 ID(example-corp-dev)를 일치시켜 전달한다.

* [주의] fr-g2-inference-approved (영역: asia-northeast3-a, 상태: APPROVED)
  - 원인: 활성 프로젝트(sample-project-id)와 예약 대상 프로젝트(example-corp-dev)가 일치하지 않음
  - 처방: 조회 및 심사 요청 시 정확한 프로젝트 ID(example-corp-dev)를 일치시켜 전달한다.
```

---

## 2. 실습 안내 (실제 환경 실행 시 자동 덮어쓰기)

실제 Google Cloud 환경에서 본 진단을 수행하려면 아래 명령어를 실행한다.
실행 결과는 본 `report.md` 파일에 자동으로 갱신(덮어쓰기)된다:

```bash
python diagnose.py
```
