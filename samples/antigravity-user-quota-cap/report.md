# Google Antigravity 사용자별 사용량 모니터링 및 쿼터 캡 진단 리포트

- **진단 일시**: (실행 결과 자동 생성)
- **대상 프로젝트**: `sample-project-id`
- **집계 주기**: `daily` (UTC 기준)
- **토큰 상한 임계치(Cap)**: `500,000 토큰`
- **요청 상한 임계치(Cap)**: `1,000 회`
- **진단 모드**: `모의 실행 (Dry-run)`

---

## 1. 전사 Antigravity 사용량 및 쿼터 캡 요약 지표

- **활성 개발자 수**: 5명
- **총 토큰 소모량**: 2,260,000 토큰
- **총 API 요청 수**: 4,280회
- **쿼터 캡 초과 계정**: 3명 (전체의 60.0%)
  - **직접 통제 가능(IAM)**: 2명 (자동 차단/마커 역할 적용 가능)
  - **수동 조치 필요(Group)**: 1명 (그룹/상속 권한으로 개별 제어 불가)

---

## 2. 사용자별 토큰 소모량 및 쿼터 캡 진단 현황

| 사용자 계정 (Principal) | 소속 부서 | 요청수 | 총 토큰량 | 주 사용 클라이언트 | 판정 상태 | 통제성 분류 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `dev-lead@example.com` | Platform Core | 1,420회 | 730,000 T | VS Code | **[초과/차단대상]** | `ENFORCEABLE_ALLOWED` |
| `senior-eng@example.com` | Backend Service | 980회 | 520,000 T | JetBrains IntelliJ | **[초과/차단대상]** | `ENFORCEABLE_ALLOWED` |
| `arch-lead@example.com` | Architecture Office | 1,150회 | 620,000 T | Antigravity CLI | **[초과/차단대상]** | `NOT_ENFORCEABLE` |
| `frontend-dev@example.com` | Web Frontend | 510회 | 280,000 T | VS Code | [정상] | `ENFORCEABLE_ALLOWED` |
| `junior-eng@example.com` | Mobile App | 220회 | 110,000 T | Android Studio | [정상] | `ENFORCEABLE_ALLOWED` |

---

## 3. 실무자 조치 가이드 및 처방전

### 1단계: 직접 통제 가능 초과자 IAM 마커 역할 적용 (임시 차단)
기본 사용자 역할(`roles/discoveryengine.agentspaceUser`)을 해제하고 차단 마커 역할(`CustomAntigravityCapBlocked`)을 임시 부여하여 당일 추가 토큰 소모를 차단한다:
```bash
# dev-lead@example.com 쿼터 캡 차단 조치
gcloud projects remove-iam-policy-binding sample-project-id --member=user:dev-lead@example.com --role=roles/discoveryengine.agentspaceUser
gcloud projects add-iam-policy-binding sample-project-id --member=user:dev-lead@example.com --role=roles/CustomAntigravityCapBlocked
# senior-eng@example.com 쿼터 캡 차단 조치
gcloud projects remove-iam-policy-binding sample-project-id --member=user:senior-eng@example.com --role=roles/discoveryengine.agentspaceUser
gcloud projects add-iam-policy-binding sample-project-id --member=user:senior-eng@example.com --role=roles/CustomAntigravityCapBlocked
```

### 2단계: 그룹 및 상속 권한 보유 초과자 수동 조치
- `NOT_ENFORCEABLE`로 분류된 계정은 프로젝트 레벨의 개별 바인딩을 수정해도 Google Group이나 상위 조직 권한으로 인해 접근이 유지된다.
- 사내 Google Workspace / Cloud Identity 관리 콘솔에서 해당 계정을 개발자 그룹에서 일시 제외 조치해야 한다.

### 3단계: 엔터프라이즈 운영 자동화(Batch Job) 연계
- 본 도구는 읽기 전용 진단 및 현황 보고를 지원한다.
- 프로덕션 환경에서 주기적인 자동 차단 및 복구를 수행하려면 Cloud Scheduler와 Cloud Run Job 또는 Cloud Functions를 연동하여 정기 배치 파이프라인으로 확장할 수 있다.
