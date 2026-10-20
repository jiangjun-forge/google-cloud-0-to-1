# Google Antigravity 사용자별 사용량 모니터링 및 쿼터 캡 진단 리포트

- **진단 일시**: `2026-10-20 01:20:58 UTC`
- **대상 프로젝트**: `sample-project-id`
- **집계 주기**: `daily` (UTC 기준)
- **토큰 상한 임계치(Cap)**: `5,000,000 토큰`
- **요청 상한 임계치(Cap)**: `1,000 회`
- **진단 모드**: `모의 실행 (Dry-run)`

---

## 1. 전사 Antigravity 사용량 및 쿼터 캡 요약 지표

- **활성 개발자 수**: 5명
- **총 토큰 소모량**: 22,600,000 토큰
- **총 API 요청 수**: 4,280회
- **쿼터 캡 초과 계정**: 3명 (전체의 60.0%)
  - **직접 통제 가능(IAM)**: 2명 (자동 차단/마커 역할 적용 가능)
  - **수동 조치 필요(Group)**: 1명 (그룹/상속 권한으로 개별 제어 불가)

---

## 2. 사용자별 토큰 소모량 및 쿼터 캡 진단 현황

| 사용자 계정 (Principal) | 소속 부서 | 요청수 | 총 토큰량 | 주 사용 클라이언트 | 판정 상태 | 통제성 분류 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `dev-lead@example.com` | Platform Core | 1,420회 | 7,300,000 T | VS Code | **[초과/차단대상]** | `ENFORCEABLE_ALLOWED` |
| `senior-eng@example.com` | Backend Service | 980회 | 5,200,000 T | JetBrains IntelliJ | **[초과/차단대상]** | `ENFORCEABLE_ALLOWED` |
| `arch-lead@example.com` | Architecture Office | 1,150회 | 6,200,000 T | Antigravity CLI | **[초과/차단대상]** | `NOT_ENFORCEABLE` |
| `frontend-dev@example.com` | Web Frontend | 510회 | 2,800,000 T | VS Code | [정상] | `ENFORCEABLE_ALLOWED` |
| `junior-eng@example.com` | Mobile App | 220회 | 1,100,000 T | Android Studio | [정상] | `ENFORCEABLE_ALLOWED` |

---

## 3. 실무자 조치 가이드 및 처방전

### 1단계: 직접 통제 가능 초과자 IAM 조건부 만료 적용 (익일 자동 복구)
기본 사용자 역할(`roles/discoveryengine.agentspaceUser`)을 해제하고, 익일 자정(`2026-10-21T00:00:00Z`) 자동 만료 조건식(`request.time < timestamp(...)`)이 결합된 차단 마커 역할을 부여하여 관리자 수동 개입 없는 무인 자율 복구를 구현한다:
```bash
# dev-lead@example.com 쿼터 캡 조건부 자동 만료 차단 조치
gcloud projects remove-iam-policy-binding sample-project-id --member=user:dev-lead@example.com --role=roles/discoveryengine.agentspaceUser
gcloud projects add-iam-policy-binding sample-project-id --member=user:dev-lead@example.com --role=roles/CustomAntigravityCapBlocked --condition='expression=request.time < timestamp("2026-10-21T00:00:00Z"),title=Daily_Cap_Expiry,description=Antigravity_Quota_Exceeded_Auto_Reset'
# senior-eng@example.com 쿼터 캡 조건부 자동 만료 차단 조치
gcloud projects remove-iam-policy-binding sample-project-id --member=user:senior-eng@example.com --role=roles/discoveryengine.agentspaceUser
gcloud projects add-iam-policy-binding sample-project-id --member=user:senior-eng@example.com --role=roles/CustomAntigravityCapBlocked --condition='expression=request.time < timestamp("2026-10-21T00:00:00Z"),title=Daily_Cap_Expiry,description=Antigravity_Quota_Exceeded_Auto_Reset'
```

### 2단계: 그룹 및 상속 권한 보유 초과자 수동 조치
- `NOT_ENFORCEABLE`로 분류된 계정은 프로젝트 레벨의 개별 바인딩을 수정해도 Google Group이나 상위 조직 권한으로 인해 접근이 유지된다.
- 사내 Google Workspace / Cloud Identity 관리 콘솔 ( https://admin.google.com )에서 해당 계정을 개발자 그룹에서 일시 제외 조치해야 한다.

### 3단계: Cloud Logging Log Analytics (BigQuery Linked Dataset) 초고속 집계 쿼리
- 대규모 개발 조직(수천 명 규모) 전수 조사는 Cloud Logging Log Analytics SQL 쿼리를 통해 초 단위로 집계할 수 있다:
```sql
-- Google Antigravity 개발자별 사용량 집계 (Cloud Logging Log Analytics SQL)
SELECT
  JSON_VALUE(json_payload.principalEmail) AS developer_email,
  JSON_VALUE(json_payload.clientInfo.clientType) AS client_type,
  COUNT(1) AS request_count,
  SUM(CAST(JSON_VALUE(json_payload.promptTokenCount) AS INT64)) AS total_prompt_tokens,
  SUM(CAST(JSON_VALUE(json_payload.candidatesTokenCount) AS INT64)) AS total_candidate_tokens,
  SUM(CAST(JSON_VALUE(json_payload.promptTokenCount) AS INT64) + CAST(JSON_VALUE(json_payload.candidatesTokenCount) AS INT64)) AS total_tokens
FROM
  `sample-project-id.global._Default._AllLogs`
WHERE
  log_name LIKE '%businessaicode.googleapis.com%2Finference_response%'
  AND timestamp >= TIMESTAMP('2026-10-16T00:00:00Z')
GROUP BY
  developer_email, client_type
ORDER BY
  total_tokens DESC;
```

### 4단계: 엔터프라이즈 운영 자동화(Batch Job) 및 4대 필수 라벨링 규약
- 프로덕션 환경에서 주기적인 자동 차단 및 복구를 수행하려면 Cloud Scheduler와 Cloud Run Job 또는 Cloud Functions를 연동하여 정기 배치 파이프라인으로 확장할 수 있다.
- 사내 거버넌스 및 자원 추적을 위해 배치 파이프라인 인프라 생성 시 4대 표준 라벨(`--labels=managed-by=google-cloud-0-to-1,scenario=antigravity-user-quota-cap,env=sample`)을 필수로 주입한다.
