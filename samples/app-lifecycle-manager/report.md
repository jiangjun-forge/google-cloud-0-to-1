<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

> [!IMPORTANT]
> **구글 (Google LLC) 참조용 샘플 고지 사항**:
> 본 프로젝트의 모든 소스 코드와 문서는 Google LLC의 소유이며, Apache-2.0 라이선스에 따라 오직 **참조용 샘플 (Sample / Reference Only)** 목적으로만 제공된다. 프로덕션 환경에 그대로 사용할 수 없으며, 사전 통지 없이 언제든 내용이 수정, 변경 또는 삭제될 수 있다.

# 엔터프라이즈 AI 앱 생애 주기 및 콜드라인 냉동 거버넌스 리포트 (app-lifecycle-manager)

- **대상 프로젝트**: `sample-project-id`
- **기준 리전**: `asia-northeast3` (대한민국 서울 리전 기본)
- **실행 모드**: `Dry-Run (가상 시뮬레이션 모드)`
- **표준 리소스 라벨**: `managed-by=google-cloud-0-to-1`, `scenario=app-lifecycle-manager`, `env=sample`, `created-by=customer-engineer`

---

## 1. 경영진 요약 지표 (FinOps 비용 절감 및 SecOps 보안 표면 감축)

| 지표 구분 | 거버넌스 핵심 측정 항목 | 실측 및 산출 결과 |
| :--- | :--- | :--- |
| **전사 앱 인벤토리** | 평가 대상 전체 AI 앱 수 | 총 `7`개 앱 |
| **냉동 보관 (96% 코호트)** | 만료된 1회성 앱 냉동 조치 (`Hit Count <= 1`) | 신규 냉동 `4`개 (기존 냉동 `1`개) |
| **프로덕션 승격 (4% 코호트)** | 고빈도 핵심 안착 앱 정식 승격 (`Hit Count >= 50`) | `1`개 앱 |
| **FinOps 컴퓨트 절감액** | 회수된 월간 유휴 컴퓨트 총 비용 | 월 `$245.50` 절감 |
| **FinOps 콜드라인 보관료** | GCS Coldline 타임캡슐 보관 비용 (`$0.02/캡슐`) | 월 `$0.08` 발생 |
| **FinOps 순 절감 효과** | **월간 및 연간 순 절감액 (Net Savings)** | **월 `$245.42` (연간 `$2,945.04` 절감)** |
| **SecOps 유휴 리소스 회수** | 상시 대기 인스턴스 (`min-instances`) 회수 수 | `4`개 인스턴스 회수 |
| **SecOps 자격 증명 위생** | 비인간 서비스 계정 (NHI) 및 IAM 권한 동결 | `4`개 서비스 계정 (`5`개 IAM 바인딩 해제) |
| **SecOps 블라스트 반경** | BigQuery Graph 기반 좀비 트리거 차단 및 엔드포인트 폐쇄 | `5`개 트리거 차단 (`4`개 외부 엔드포인트 폐쇄) |

---

## 2. 1단계: 개발 착수 전 시맨틱 중복 생성 방지 게이트 (Pre-Build Gate)

- **신규 개발 요청 아이디어**: `"재무팀 법인세 예규 및 조세심판원 판례 검색 웹앱"`
- **검색 엔진**: `BigQuery Vector Search` (`gemini-embedding-001`, 코사인 유사도) + `Dataplex Universal Catalog`

| 순위 | 기존 등록 앱 ID | 현재 수명 주기 상태 | 코사인 유사도 | 거버넌스 권고 조치 | 실행 및 1분 복원 명령어 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `tax-precedent-spa-001` | `CRYO_ARCHIVED` | `0.9800` | **REHYDRATE_CRYO** | `gcloud storage cat gs://sample-project-id-onetime-archive/tax-precedent-spa-001/rehydrate.sh | bash` |

---

## 3. 2단계: 호출 수(Hit-Count) 및 보존 기한(TTL) 전수 판별 결과

| 앱 ID | 유형 | 소유 조직 | 호출 수 | 경과일 / TTL | 거버넌스 판정 | 판정 근거 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `tax-precedent-spa-001` | `SPA` | `finance-ai-guild@example.com` | `1` | `45일 / 14일` | **`ALREADY_ARCHIVED`** | 이미 클라우드 스토리지 콜드라인 볼트(gs://sample-project-id-onetime-archive/tax-precedent-spa-001/)에 냉동 보관되어 상시 컴퓨트 비용이 $0.00/월이다. |
| `q3-board-deck-kpi-visualizer` | `SPA` | `strategy-office@example.com` | `1` | `28일 / 14일` | **`CRYO_DISPOSAL`** | 1회성 사용 패턴(호출 수 1회 <= 1회) 및 보존 기한 만료(경과 28일 >= TTL 14일)가 확인되어 96% 콜드라인 냉동 타임캡슐 보관 대상이다. |
| `partner-hackathon-contract-summarizer` | `AGENT_ENGINE` | `legal-innovation@example.com` | `0` | `21일 / 14일` | **`CRYO_DISPOSAL`** | 1회성 사용 패턴(호출 수 0회 <= 1회) 및 보존 기한 만료(경과 21일 >= TTL 14일)가 확인되어 96% 콜드라인 냉동 타임캡슐 보관 대상이다. |
| `marketing-campaign-utm-tagger-api` | `CLOUD_RUN_API` | `growth-marketing@example.com` | `1` | `19일 / 14일` | **`CRYO_DISPOSAL`** | 1회성 사용 패턴(호출 수 1회 <= 1회) 및 보존 기한 만료(경과 19일 >= TTL 14일)가 확인되어 96% 콜드라인 냉동 타임캡슐 보관 대상이다. |
| `logistics-tariff-simulator-spa` | `SPA` | `supply-chain-ops@example.com` | `1` | `16일 / 14일` | **`CRYO_DISPOSAL`** | 1회성 사용 패턴(호출 수 1회 <= 1회) 및 보존 기한 만료(경과 16일 >= TTL 14일)가 확인되어 96% 콜드라인 냉동 타임캡슐 보관 대상이다. |
| `enterprise-it-helpdesk-triage-agent` | `AGENT_ENGINE` | `it-platform-core@example.com` | `412` | `30일 / 14일` | **`PRODUCTION_GRADUATION`** | 호출 수(412회)가 승격 임계치(50회) 이상으로 확인되어 상위 4% 엔터프라이즈 SDLC 프로덕션 승격 대상이다. |
| `new-hire-onboarding-buddy-spa` | `SPA` | `people-ops@example.com` | `6` | `4일 / 14일` | **`KEEP_ACTIVE`** | 보존 기한 유예 기간 이내(경과 4일 < TTL 14일)이거나 일반 사용 중(호출 수 6회)이므로 활성(ACTIVE) 상태를 유지한다. |

---

## 4. 3단계: 빅쿼리 그래프(`GQL`) 멀티홉 호출 리니지 및 안전 차단 내역

| 대상 앱 ID | 업스트림 호출자 ID | 호출자 유형 | 프로토콜 | 안전 폐기 검증 | 결정론적 차단 명령어 (Sever Command) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `q3-board-deck-kpi-visualizer` | `sched-q3-board-cache-warmer` | `CLOUD_SCHEDULER` | `CRON` | `True` | `gcloud scheduler jobs pause q3-board-cache-warmer --location=asia-northeast3 --project=sample-project-id` |
| `partner-hackathon-contract-summarizer` | `eventarc-gcs-nda-upload-trigger` | `EVENTARC` | `HTTPS` | `True` | `gcloud eventarc triggers delete gcs-nda-upload-trigger --location=asia-northeast3 --project=sample-project-id --quiet` |
| `partner-hackathon-contract-summarizer` | `a2a-procurement-router-agent` | `A2A_AGENT` | `A2A` | `True` | `gcloud run services remove-iam-policy-binding partner-hackathon-contract-summarizer --region=asia-northeast3 --project=sample-project-id --member='serviceAccount:sa-procurement-router@sample-project-id.iam.gserviceaccount.com' --role='roles/run.invoker'` |
| `marketing-campaign-utm-tagger-api` | `workflow-holiday-promo-dispatch` | `WORKFLOWS` | `HTTPS` | `True` | `gcloud run services update-traffic marketing-campaign-utm-tagger-api --to-zero --region=asia-northeast3 --project=sample-project-id` |
| `logistics-tariff-simulator-spa` | `pubsub-customs-rate-push` | `PUBSUB` | `PUBSUB_PUSH` | `True` | `gcloud pubsub subscriptions modify-push-config customs-rate-push-sub --push-endpoint='' --project=sample-project-id` |

---

## 5. 4A단계: 클라우드 스토리지 콜드라인 냉동 타임캡슐 및 1분 부활 스크립트

| 냉동 앱 ID | 콜드라인 캡슐 경로 (GCS URI) | 살균된 시크릿 키 | 월간 절감액 | 1분 원클릭 부활 명령어 (Rehydrate) |
| :--- | :--- | :--- | :--- | :--- |
| `q3-board-deck-kpi-visualizer` | `gs://sample-project-id-onetime-archive/q3-board-deck-kpi-visualizer/` | `ERP_BEARER_TOKEN` | 월 `$64.50` | `gcloud storage cat gs://sample-project-id-onetime-archive/q3-board-deck-kpi-visualizer/rehydrate.sh | bash` |
| `partner-hackathon-contract-summarizer` | `gs://sample-project-id-onetime-archive/partner-hackathon-contract-summarizer/` | `DOCUSIGN_CLIENT_SECRET` | 월 `$82.00` | `gcloud storage cat gs://sample-project-id-onetime-archive/partner-hackathon-contract-summarizer/rehydrate.sh | bash` |
| `marketing-campaign-utm-tagger-api` | `gs://sample-project-id-onetime-archive/marketing-campaign-utm-tagger-api/` | `AD_NETWORK_API_KEY` | 월 `$45.00` | `gcloud storage cat gs://sample-project-id-onetime-archive/marketing-campaign-utm-tagger-api/rehydrate.sh | bash` |
| `logistics-tariff-simulator-spa` | `gs://sample-project-id-onetime-archive/logistics-tariff-simulator-spa/` | `CUSTOMS_WEBHOOK_PASSWORD` | 월 `$54.00` | `gcloud storage cat gs://sample-project-id-onetime-archive/logistics-tariff-simulator-spa/rehydrate.sh | bash` |

---

## 6. 4B단계: 상위 4% 핵심 안착 앱 프로덕션 승격 (Graduation)

### 승격 대상 앱: `enterprise-it-helpdesk-triage-agent` (전사 IT 헬프데스크 및 권한 신청 자동 분류 에이전트, 누적 호출 `412`회)
- [x] 지식 카탈로그(Dataplex Universal Catalog) Aspect 상태를 `ACTIVE`(1회성)에서 `GRADUATED`(영구 운영)로 승격한다.
- [x] 환경 변수 내 시크릿을 시크릿 매니저(Secret Manager)로 이관하고 90일 자동 순환 정책을 적용한다.
- [x] 클라우드 아머(Cloud Armor) 및 모델 아머(Model Armor) 프롬프트 인젝션 방어 정책을 부착한다.
- [x] VPC 서비스 컨트롤(VPC Service Controls) 보안 경계와 프로덕션 전용 최소 권한 서비스 계정을 분리 적용한다.
- [x] 클라우드 모니터링(Cloud Monitoring) 가용성 SLO 알림(99.9% 가용성, P95 지연 시간 2.0초 미만)을 활성화한다.

---

## 7. 5단계: 자연어 시맨틱 복원 검색 (Search-to-Restore) 검증

- **자연어 복원 검색 질의**: `"조세심판원 법인세 판례 검색 웹앱"`

| 매칭된 냉동 앱 ID | 코사인 유사도 | 콜드라인 캡슐 경로 | 1분 원클릭 부활 명령어 |
| :--- | :--- | :--- | :--- |
| `tax-precedent-spa-001` | `0.9800` | `gs://sample-project-id-onetime-archive/tax-precedent-spa-001/` | `gcloud storage cat gs://sample-project-id-onetime-archive/tax-precedent-spa-001/rehydrate.sh | bash` |
| `logistics-tariff-simulator-spa` | `0.1947` | `gs://sample-project-id-onetime-archive/logistics-tariff-simulator-spa/` | `gcloud storage cat gs://sample-project-id-onetime-archive/logistics-tariff-simulator-spa/rehydrate.sh | bash` |
| `q3-board-deck-kpi-visualizer` | `0.1692` | `gs://sample-project-id-onetime-archive/q3-board-deck-kpi-visualizer/` | `gcloud storage cat gs://sample-project-id-onetime-archive/q3-board-deck-kpi-visualizer/rehydrate.sh | bash` |
