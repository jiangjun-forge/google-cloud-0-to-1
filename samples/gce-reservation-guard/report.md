# Compute Engine 하드웨어 예약(Reservation) 및 CUD 용량 보장 통합 진단 리포트

- **진단 일시**: (실행 결과 자동 생성)
- **대상 프로젝트**: `sample-project-id`
- **점검 대상 리전**: `asia-northeast3`
- **진단 모드**: `모의 실행 (Dry-run)`

---

## 1. 최근 용량 고갈(ZONE_RESOURCE_POOL_EXHAUSTED) 장애 이력

- **식별된 용량 고갈 실패 이벤트 수**: 2건
- **[장애 감지]** 2026-09-27T23:23:11.742228+00:00 | 존: `asia-northeast3-a` | 머신: `n4-standard-8` | 호출자: `gke-nodepool-autoscaler@example.com`
- **[장애 감지]** 2026-09-24T23:23:11.742228+00:00 | 존: `asia-northeast3-b` | 머신: `g2-standard-8` | 호출자: `admin-deployer@example.com`

---

## 2. 활성 CUD 약정 vs 온디맨드 Reservation 하드웨어 물리 용량 대조

- **총 CUD 약정 코어 수**: 192 vCPU (요금 할인용)
- **온디맨드 예약 확보 코어 수**: 32 vCPU (물리 용량 보장용)
- **물리 용량 보호율(Coverage)**: 16.7%
- **[경고]** CUD 요금만 지출되고 실제 하드웨어 용량이 확보되지 않은 '무방비 약정(Unreserved CUD)'이 존재한다.

---

## 3. Compute Engine Future Reservation (GPU / 특수 머신 사전 예약) 현황

| 예약 이름 | 상태 | 존 | 머신 및 수량 |
| :--- | :--- | :--- | :--- |
| `fr-a3-training-pending` | `PENDING_APPROVAL` | `asia-northeast3-a` | `a3-highgpu-8g (8대)` |
| `fr-g2-robotics-draft` | `DRAFTING` | `asia-northeast3-c` | `g2-standard-16 (16대)` |

---

## 4. 실무자 통합 처방전 및 즉각 조치 가이드

### 1단계: 무방비 CUD에 대한 온디맨드 Reservation 선점
```bash
gcloud compute reservations create res-guaranteed-capacity \
    --zone=asia-northeast3-a \
    --vm-count=8 \
    --machine-type=n4-standard-8
```

### 2단계: DRAFTING 상태 Future Reservation 제출 완결
```bash
# 미제출된 Future Reservation 제출 승인 요청
gcloud compute future-reservations submit [FR_NAME] --zone=[ZONE]
```
