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

# 비즈니스 요구 사항 명세서 (BRD): 엔터프라이즈 AI 앱 생애 주기 및 콜드라인 냉동 거버넌스 (app-lifecycle-manager)

---

## 1. 배경 및 목적

### 1.1 엔터프라이즈 바이브 코딩의 96% 1회성 앱 역설
사내 AI 코딩 어시스턴트와 노코드 빌더가 확산되면서 현업 임직원은 연간 수만 개의 단일 페이지 웹앱(SPA), 커스텀 에이전트(`Agent Engine`), 단건 API(`Cloud Run`)를 생성한다. 실제 엔터프라이즈 호출 텔레메트리를 분석하면 생성된 AI 앱 중 약 4%만이 지속적인 핵심 업무에 안착하며, 나머지 96%는 임원 보고, 해커톤, 분기 리뷰 등 단발성 목적(`Hit Count <= 1`)을 달성한 직후 유휴 상태로 방치된다.

### 1.2 사내 운영 환경의 3대 구조적 난제
1. **중복 개발의 반복 (시맨틱 검색 부재)**: 기존에 생성되었거나 보관된 앱의 비즈니스 의도와 프롬프트가 임베딩으로 자산화되어 있지 않아, 타 부서에서 유사한 도구의 존재를 모른 채 수천 번 중복 개발한다.
2. **폐기 공포 (불투명한 인바운드 호출 경로와 블라스트 반경)**: 유휴 상태인 `Cloud Run` 서비스나 `Agent Engine` 엔드포인트를 발견하더라도, 업스트림의 `Cloud Scheduler`, `Eventarc`, `Workflows`, `Pub/Sub` 또는 타 에이전트(A2A)가 호출 중인지 알 수 없어 장애 우려로 정리하지 못한다.
3. **유실 공포 (유휴 컴퓨트 및 비인간 자격 증명 방치)**: 다음 분기나 감사 시점에 다시 필요할 때 찾지 못할까 봐 최소 인스턴스(`min-instances`) 유휴 컴퓨트와 비인간 서비스 계정(NHI)을 그대로 유지하여 클라우드 예산 낭비와 보안 공격 표면을 키운다.

---

## 2. 비즈니스 요구 사항 명세 (Business Requirements)

| 요구 사항 ID | 요구 사항 명칭 | 상세 설명 및 수용 기준 (Acceptance Criteria) | 우선순위 |
| :---: | :--- | :--- | :---: |
| **BR-01** | 개발 착수 전 시맨틱 중복 생성 방지 게이트 | 신규 AI 앱 생성 전 자연어 요구 사항을 BigQuery 벡터 검색(`VECTOR_SEARCH`, `gemini-embedding-001`)으로 조회하여 기존 활성 및 냉동 앱 중 코사인 유사도가 임계치 이상인 자산을 찾아 재사용(`REUSE_ACTIVE`) 또는 즉시 복원(`REHYDRATE_CRYO`)하도록 안내한다. | P0 |
| **BR-02** | 전사 통합 앱 카탈로그 및 거버넌스 Aspect 관리 | 전사 AI 앱을 Dataplex Universal Catalog(Knowledge Catalog)의 커스텀 엔트리로 등록하고, 수명 주기 상태(`ACTIVE`, `DRAINING`, `CRYO_ARCHIVED`, `GRADUATED`), 호출 수(`hit_count`), 보존 기한(`ttl_days`), 승격 임계치(`promote_at_hits`), 냉동 경로(`cryo_gcs_uri`)를 표준 Aspect로 관리한다. | P0 |
| **BR-03** | 호출 수 및 보존 기한 기반 96% 대 4% 자동 분류 | Cloud Monitoring 및 Cloud Logging의 실제 호출 수와 경과 일수를 스캔하여 96% 냉동 보관 대상(`hit_count <= 1` 및 `age_days >= ttl_days`), 4% 프로덕션 승격 대상(`hit_count >= promote_at_hits`), 활성 유지 대상을 자동 판별한다. | P0 |
| **BR-04** | BigQuery Graph(`GQL`) 멀티홉 호출 리니지 역추적 | 업스트림 호출자(`Cloud Scheduler`, `Eventarc`, `Pub/Sub`, `Workflows`, `A2A Agent`)와 다운스트림 리소스(`Service Account`, `Secret Manager`, `BigQuery`)를 `CREATE PROPERTY GRAPH`로 모델링하고 `GQL` 쿼리로 블라스트 반경을 전수 규명한다. | P0 |
| **BR-05** | 의존성 안전 차단 및 트래픽 드레이닝 자동화 | 그래프 역추적으로 식별된 업스트림 트리거 일시 중지, 이벤트 삭제, 트래픽 0% 전환(`--to-zero`) 및 IAM 권한 회수를 수행하는 결정론적 `gcloud` 명령어를 생성하고, 활성 호출처가 0건일 때만 냉동을 허용한다. | P0 |
| **BR-06** | 컴퓨트 제로화 및 Cloud Storage Coldline 타임캡슐 보관 | 만료된 1회성 앱의 유휴 컴퓨트(`min-instances`)와 서비스 계정 권한을 회수하되, 컨테이너 다이제스트, 프롬프트 요약, 시크릿이 살균된 환경 변수 템플릿(`<REDACTED_SECRET_MANAGER_REF>`)을 `Cloud Storage Coldline` 버킷에 타임캡슐로 보존한다. | P0 |
| **BR-07** | 자연어 시맨틱 복원 검색 및 60초 부활 스크립트 | 자연어 검색으로 냉동 타임캡슐을 즉시 찾고, 자동 생성된 부활 스크립트(`rehydrate.sh`) 실행 한 줄로 60초 이내에 서비스와 최소 권한을 원상 복구한다. | P0 |
| **BR-08** | 상위 4% 핵심 안착 앱의 프로덕션 승격 패키지 생성 | 호출 수가 승격 임계치 이상인 상위 4% 앱에 대해 Cloud Build 프로덕션 배포 파이프라인, Secret Manager 이관, Model Armor 가드레일 등 5대 보안 하드닝 체크리스트와 `GRADUATED` 상태 전이 명세를 생성한다. | P1 |
| **BR-09** | FinOps 비용 절감 및 SecOps 공격 표면 감축 영수증 산출 | 회수된 월간/연간 순 컴퓨트 절감액(콜드라인 보관료 월 `$0.02` 차감)과 회수된 서비스 계정(NHI), IAM 바인딩, 차단된 좀비 트리거 수를 `report.md` 영수증으로 자동 산출한다. | P0 |
| **BR-10** | 사내 거버넌스 4대 필수 라벨 준수 | 모든 생성 리소스 및 조치 가이드 명령어에 `managed-by=google-cloud-0-to-1`, `scenario=app-lifecycle-manager`, `env=sample`, `created-by=customer-engineer` 4대 표준 라벨을 100% 부여한다. | P1 |
