---
name: gce-reservation-guard
description: "Autopilot, hands-on diagnostics, and self-healing for gce-reservation-guard: Compute Engine 리전 용량 고갈(ZONE_RESOURCE_POOL_EXHAUSTED) 장애를 감사 로그로 역추적하고, CUD 약정 대비 물리적 Reservation 확보율 및 Future Reservation(FR) 신청/제출 상태를 통합 진단하는 도구다."
---

<!-- disableFinding(LINE_OVER_80) -->
<!-- disableFinding(WHITESPACE_TRAILING) -->

# GCE Reservation Guard Skill

본 스킬은 고객 및 파트너사 엔지니어가 Compute Engine 환경에서 CUD 약정에 대한 물리적 하드웨어 확보율(Coverage)을 점검하고, GPU 및 고사양 머신의 Future Reservation 미제출 문제를 원클릭으로 통합 진단할 수 있도록 돕는 실습 가이드다.

```
                   [고객 실습 워크플로우 (3단계)]
 ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
 │ 1. 예습 (Mock)  │ ──> │ 2. 실습 (Live)  │ ──> │ 3. 복습 (Action)│
 │  --dry-run 실행  │     │   실환경 진단   │     │  report.md 검토 │
 └─────────────────┘     └─────────────────┘     └─────────────────┘
```

> [!IMPORTANT]
> **실습 환경 보존 및 자동 정리(Teardown) 금지 안내**:
> 진단으로 파악된 결과와 처방 명령어는 사용자가 직접 검토하고 필요 시 적용할 수 있도록 절대로 에이전트가 임의로 실행하거나 삭제하지 않는다.

---

## 1. 사전 점검 (Preflight Checks)

1. **작업 디렉터리 확인**:
   ```bash
   pwd
   # /.../google-cloud-0-to-1/samples/gce-reservation-guard 경로 확인
   ```

2. **필수 API 활성화 상태 점검**:
   - `compute.googleapis.com`
   - `logging.googleapis.com`

3. **필요 최소 IAM 권한**:
   - `roles/compute.viewer`
   - `roles/logging.viewer`

---

## 2. 3단계 실습 실행 절차

### 1단계: 예습 (Dry-run 가상 모의 실행)
```bash
python diagnose.py --dry-run
```

### 2단계: 실습 (사내 실환경 통합 진단)
```bash
python diagnose.py -p <대상_프로젝트_ID> -r asia-northeast3
```

### 3단계: 복습 (산출물 검토 및 조치)
- `report.md`를 열어 무방비 CUD 비율과 Future Reservation DRAFTING 항목 확인
- 온디맨드 Reservation 생성 및 Future Reservation 제출 명령어 실행
