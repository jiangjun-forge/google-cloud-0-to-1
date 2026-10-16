# 유출 의심 서비스 계정 감사 로그 역추적 및 침해 진단 리포트 (service-account-leak-investigator)

- **진단 모드**: `모의 실행 (Dry-run)`
- **대상 프로젝트**: `sample-project-id`
- **조사 기간**: 최근 7일
- **산출 목적**: 사전 예습, 실습 실행 결과 기록 및 사내 공유/복습용

---

## 1. 서비스 계정 활성 키(User-Managed Key) 현황 점검

| 서비스 계정 | 키 ID | 생성 일자 | 상태 | 권장 조치 |
| :--- | :--- | :--- | :--- | :--- |
| `app-backend-sa` | `7f8b9c0d1e2f...` | 2025-11-10 | ACTIVE | 즉시 비활성화(DISABLE) 및 영구 삭제 권장 |
| `app-backend-sa` | `a1b2c3d4e5f6...` | 2026-05-15 | ACTIVE | 침해 의심 시점 생성 키, 즉시 삭제 필요 |
| `data-pipeline-sa` | `7f8b9c0d1e2f...` | 2025-11-10 | ACTIVE | 즉시 비활성화(DISABLE) 및 영구 삭제 권장 |
| `data-pipeline-sa` | `a1b2c3d4e5f6...` | 2026-05-15 | ACTIVE | 침해 의심 시점 생성 키, 즉시 삭제 필요 |

---

## 2. 최근 7일간 Cloud Audit Logs 위험 활동 역추적

| 발생 시각 | 계정 | 서비스 | 메서드 | 호출 IP | 위험도 | 상세 내용 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-10-16 06:34:48 UTC | `app-backend-sa` | iam | `SetIamPolicy` | `198.51.100.45` | **HIGH** | 외부 미인가 계정에 roles/owner 권한 부여 시도 감지 |
| 2026-10-16 03:34:48 UTC | `data-pipeline-sa` | storage | `get` | `203.0.113.88` | **HIGH** | 비정상 해외 IP 대역에서 sensitive-customer-pii 버킷 대량 다운로드 |
| 2026-10-15 18:34:48 UTC | `app-backend-sa` | bigquery | `InsertJob` | `198.51.100.45` | **HIGH** | 외부 공개 스토리지 버킷으로 결제 및 사용자 테이블 추출 쿼리 실행 |
| 2026-10-15 08:34:48 UTC | `data-pipeline-sa` | storage | `list` | `203.0.113.88` | **MEDIUM** | 사내 백업 버킷 내부 객체 목록 전수 정찰(Enumeration) |
| 2026-10-14 08:34:48 UTC | `app-backend-sa` | storage | `get` | `192.0.2.10` | **LOW** | 정상 빌드 파이프라인 버킷 메타데이터 확인 |

**진단 요약**: 총 5건의 활동 중 고위험(HIGH) 이벤트 3건 탐지

---

## 3. 긴급 대응 조치 및 Workload Identity Federation 전환 처방

### 처방 1: 유출된 서비스 계정 키 즉시 비활성화(Disable)
```bash
gcloud iam service-accounts keys disable <KEY_ID> --iam-account=<SA_EMAIL>
```

### 처방 2: 악의적으로 부여된 비인가 IAM 바인딩 제거
```bash
gcloud projects remove-iam-policy-binding <PROJECT_ID> --member=<USER> --role=<ROLE>
```

### 처방 3: 영구 자격 증명 폐기 및 Workload Identity Federation 전환
- **깃허브 액션(GitHub Actions) 환경**: OIDC 연동 풀(Pool) 생성 후 단기 토큰 발급 체계로 전면 전환
- **온프레미스 서버 환경**: mTLS 기반 SPIFFE/SPIRE 또는 IdP SAML/OIDC 페더레이션 적용

---

## 4. 자원 정리 안내 (Teardown)
본 진단 도구는 읽기 전용 감사 로그 및 키 상태 점검만 수행하므로 별도의 클라우드 인프라 자원을 생성하지 않는다.
