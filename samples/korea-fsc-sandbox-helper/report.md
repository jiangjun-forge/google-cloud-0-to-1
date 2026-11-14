<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
-->

# 금융위원회 혁신 금융 서비스(생성형 AI 망 분리 샌드박스) 사전 심사 및 반려 예방 리포트

- **진단 대상 프로젝트**: `sample-project-id`
- **금융 인프라 기준 리전**: `asia-northeast3` (대한민국 서울 리전 Data Boundary)
- **생성형 AI 블루프린트 엔진**: `Dry-Run Deterministic Blueprint (gemini-3.8-flash / global)`
- **실행 모드**: `Dry-Run (가상 시뮬레이션 모드)`
- **종합 심사 준비도 점수**: **98 / 121점 (81.0%)** — **사전 보완 필수 (High Rejection Risk)**
- **세부 항목 판정 요약**: 적격(`PASS`) 10건, 보완 권고(`WARN`) 2건, 반려 위험(`REJECT_RISK`) 3건

---

## 1. 4대 법정 심사 영역 및 15개 세부 카테고리 진단 요약

| 심사 영역 | 세부 항목 ID 및 명칭 | 판정 | 배점 (획득/만점) | 핵심 진단 결과 및 소명 상태 |
| :--- | :--- | :---: | :---: | :--- |
| 금융 소비자 편익 및 보호 대책 | `consumer_benefit.1` 정량화된 소비자 편익 증대 증명 | **PASS** | 9 / 9 | 표준 금융 보안 아키텍처 및 혁신 금융 서비스 신청 가이드라인 정합성 충족 |
| 금융 소비자 편익 및 보호 대책 | `consumer_benefit.2` 금융 사고 배상 책임 및 보상 체계 마련 | **WARN** | 5 / 8 | 배상 책임 보험(사고당 10억/연간 20억) 증권 사본 및 선보상 약관 조항 보완 필요 |
| 금융 소비자 편익 및 보호 대책 | `consumer_benefit.3` 개인 정보 및 개인 신용 정보 완전 보호 | **PASS** | 8 / 8 | 표준 금융 보안 아키텍처 및 혁신 금융 서비스 신청 가이드라인 정합성 충족 |
| 규제 특례 적용 필요성 및 실증 계획 | `regulatory_necessity.1` 면제 신청 대상 법령의 한계 한정 요건 | **PASS** | 8 / 8 | 표준 금융 보안 아키텍처 및 혁신 금융 서비스 신청 가이드라인 정합성 충족 |
| 규제 특례 적용 필요성 및 실증 계획 | `regulatory_necessity.2` 금융 시장 리스크 방지를 위한 실증 한도 설정 | **REJECT_RISK** | 3 / 8 | 실증 한도 90% 경보 및 비정상 응답 즉시 차단기(Circuit Breaker) 설계 누락 |
| 규제 특례 적용 필요성 및 실증 계획 | `regulatory_necessity.3` 지정 만료 이후 소비자 보호 및 출구 전략 | **WARN** | 4 / 7 | 특례 만료 30일 전 소비자 통지 및 온프레미스 전환 세부 일정 보완 필요 |
| 서비스의 혁신성 및 차별성 | `service_innovativeness.1` 기존 금융 서비스와의 본질적 차별성 입증 | **PASS** | 7 / 7 | 표준 금융 보안 아키텍처 및 혁신 금융 서비스 신청 가이드라인 정합성 충족 |
| 서비스의 혁신성 및 차별성 | `service_innovativeness.2` 결합된 기술적 실체 및 준비 성숙도 검증 | **PASS** | 7 / 7 | 표준 금융 보안 아키텍처 및 혁신 금융 서비스 신청 가이드라인 정합성 충족 |
| 서비스의 혁신성 및 차별성 | `service_innovativeness.3` 금융 시장 파급력 및 생태계 기여도 | **PASS** | 6 / 6 | 표준 금융 보안 아키텍처 및 혁신 금융 서비스 신청 가이드라인 정합성 충족 |
| 물적 설비, 기술 보안 및 논리적 망 분리 방안 | `technical_security.1` 환경 및 네트워크의 논리적 분리 의무 | **PASS** | 9 / 9 | 표준 금융 보안 아키텍처 및 혁신 금융 서비스 신청 가이드라인 정합성 충족 |
| 물적 설비, 기술 보안 및 논리적 망 분리 방안 | `technical_security.2` 외부 인터넷 차단 및 비공개 통신 요건 | **PASS** | 9 / 9 | 표준 금융 보안 아키텍처 및 혁신 금융 서비스 신청 가이드라인 정합성 충족 |
| 물적 설비, 기술 보안 및 논리적 망 분리 방안 | `technical_security.3` 데이터 유출 방지 및 가상 보안 경계 설정 | **REJECT_RISK** | 3 / 9 | VPC Service Controls 보안 경계가 Dry-run 상태이거나 Model Armor 필터 미결합 |
| 물적 설비, 기술 보안 및 논리적 망 분리 방안 | `technical_security.4` 관리자 단말망 격리 및 다차원 접근 통제 | **PASS** | 8 / 8 | 표준 금융 보안 아키텍처 및 혁신 금융 서비스 신청 가이드라인 정합성 충족 |
| 물적 설비, 기술 보안 및 논리적 망 분리 방안 | `technical_security.5` 데이터 암호화 및 금융회사 암호 키 직접 통제 | **PASS** | 9 / 9 | 표준 금융 보안 아키텍처 및 혁신 금융 서비스 신청 가이드라인 정합성 충족 |
| 물적 설비, 기술 보안 및 논리적 망 분리 방안 | `technical_security.6` 보안 관제 및 실시간 감사 로깅 위변조 방지 | **REJECT_RISK** | 3 / 9 | 프롬프트/감사 로그 저장소 Bucket Lock(2년 WORM 불변 잠금) 미적용 |

---

## 2. 역대 금융위원회/금융보안원 반려 사례 대조 및 사전 방어 처방

신청서 초안 및 아키텍처 상태에서 감지된 미비점과 직접 매칭되는 역대 심사 탈락/보완 요구 사례다. 지정 신청서 제출 전 반드시 아래 처방 조치를 반영하여야 한다.

| 반려 사례 ID | 관련 심사 항목 | 역대 주요 반려 사유 요약 | 필수 보완 처방 및 소명 가이드 | 참고 포털 및 문서 |
| :---: | :--- | :--- | :--- | :--- |
| `REJ-CB-02` | `consumer_benefit.2` 법정 한도(사고당 10억 원/연간 20억 원) 미달 및 외주 책임 전가 | 클라우드 및 외부 AI 모델 오류로 인한 소비자 피해 발생 시 클라우드 사업자 약관에 책임을 전가하거나, 시행령 제17조가 정한 배상 책임 보험 가입 증빙을 누락하여 심사에서 탈락했다. | 시행령 제17조 기준(사고당 10억 원, 연간 20억 원 이상)을 충족하는 배상 책임 보험 증권 또는 내부 적립금 확약서를 첨부하고, 외주/클라우드 장애 시에도 금융회사가 선보상함을 약관에 명시한다. | 공식 안내 ( https://www.fintech.or.kr ) |
| `REJ-RN-02` | `regulatory_necessity.2` 실증 한도(Cap) 미설정 및 이상 징후 서킷 브레이커 부재 | 실증 기간 중 대상 고객 수와 거래 한도를 제한하지 않고 전 고객 대상 전면 오픈을 계획하거나, AI 환각 급증 시 즉각 서비스를 차단하고 기존 시스템으로 복귀하는 차단기(Circuit Breaker)가 없어 반려되었다. | 실증 대상 고객 수 및 일일 토큰/트랜잭션 상한을 수치로 고정하고, 한도 90% 도달 시 Cloud Monitoring 경보 및 자동 서킷 브레이커 폴백 아키텍처를 설계도에 반영한다. | 공식 안내 ( https://www.fintech.or.kr ) |
| `REJ-RN-03` | `regulatory_necessity.3` 특례 만료 후 소비자 데이터 이관 및 출구 전략(Exit Plan) 누락 | 특례 지정 기간(2년) 종료 후 법령 개정이 지연되거나 정식 인허가를 받지 못할 경우의 30일 전 고객 통지, 데이터 무손실 백업 및 대체 절차 전환 계획이 전무하여 심사 보류 판정을 받았다. | 특례 만료 후 정식 법제화 불발 시에도 소비자 피해가 없도록 30일 전 사전 고지, 데이터 이관, 내부 대체 프로세스 전환을 포함한 단계별 출구 전략(Exit Strategy)을 수립한다. | 공식 안내 ( https://sandbox.fsc.or.kr ) |
| `REJ-TS-03` | `technical_security.3` VPC Service Controls(VPC-SC) 미설정 또는 감사 모드(Dry-run) 방치 | 클라우드 내부 데이터 유출을 막는 가상 보안 경계(VPC-SC)를 아예 구성하지 않거나 실제 차단 효력이 없는 Dry-run 모드로만 열어두어, 인가되지 않은 외부 프로젝트로의 데이터 반출 위험이 지적되었다. | VPC Service Controls를 감사 모드(Dry-run)가 아닌 강제 차단 모드(Enforced)로 활성화하여 Vertex AI, Cloud Storage, BigQuery 자산을 단일 보안 경계 내부에 가둔다. | 공식 안내 ( https://cloud.google.com/vpc-service-controls/docs/overview ) |
| `REJ-TS-06` | `technical_security.6` 감사 로그 WORM(Bucket Lock) 미적용 및 프롬프트 입출력 이력 누락 | Data Access 감사 로그와 AI 프롬프트/응답 로그를 일반 스토리지에만 보관하여 관리자에 의한 임의 삭제/위변조가 가능했고, 2년 이상 불변 보존(Bucket Lock) 정책이 빠져 보완 조치가 요구되었다. | Cloud Audit Logs(Data Access 포함)와 Gemini 입출력 로그를 Bucket Lock(Retention Policy 730일 이상)이 적용된 서울 리전 불변 버킷에 강제 싱크(Log Sink)한다. | 공식 안내 ( https://cloud.google.com/storage/docs/bucket-lock ) |

---

## 3. 서울 리전(`asia-northeast3`) 금융 AI 망 분리 샌드박스 참조 블루프린트

1. **망 분리 대체 논리적 격리 및 비공개 전용 통신 (`asia-northeast3`)**:
   - 사내 업무망/전산망(On-Premises)과 GCP 금융 샌드박스 프로젝트(`sample-project-id`) 간 Dedicated Interconnect 및 Private Service Connect(PSC) 엔드포인트를 구성하여 공중 인터넷 경로를 원천 배제한다.
   - 조직 정책(`constraints/compute.vmExternalIpAccess`)으로 모든 워크로드의 공인 IP 할당을 차단한다.
2. **가상 보안 경계(VPC-SC Enforced) 및 입출력 가드레일 결합**:
   - Vertex AI, BigQuery, Cloud Storage, Cloud KMS를 단일 VPC Service Controls(Enforced 모드) 보안 경계로 묶어 외부 프로젝트로의 데이터 반출을 차단한다.
   - 프롬프트 전송 전 Sensitive Data Protection(Cloud DLP)으로 개인 신용 정보를 가명/익명화하고, Model Armor로 프롬프트 인젝션 및 유해 응답을 실시간 살균한다.
3. **금융회사 직접 통제 암호화(Cloud HSM CMEK) 및 2년 불변 감사 로깅(WORM)**:
   - 서울 리전(`asia-northeast3`) Cloud HSM 기반 CMEK 키를 바인딩하여 전자금융감독규정 제37조 암호 키 통제권 요건을 충족한다.
   - 모든 관리자 행위, 데이터 접근(Data Access), Gemini 프롬프트/응답 이력을 Bucket Lock(730일 Retention)이 걸린 불변 스토리지에 강제 싱크하고, 실증 한도 90% 도달 시 자동 서킷 브레이커(Circuit Breaker)를 발동한다.

---

## 4. 신청서 인용 규제 기관 및 기술 레퍼런스 URL 도달성 검증 (Fact-Check)

혁신 금융 서비스 신청서 내 깨진 링크(404 Dead Link)나 환각 인용을 방지하기 위한 공식 레퍼런스 검증 결과다.

| 레퍼런스 명칭 | 검증 대상 URL | HTTP 응답 상태 | 정합성 판정 |
| :--- | :--- | :---: | :---: |
| Cloud KMS 고객 관리 암호화 키(CMEK) | ( https://cloud.google.com/kms/docs/cmek ) | `200 (Simulated)` | **VERIFIED** |
| Cloud Storage Bucket Lock (WORM) | ( https://cloud.google.com/storage/docs/bucket-lock ) | `200 (Simulated)` | **VERIFIED** |
| Sensitive Data Protection (Cloud DLP) | ( https://cloud.google.com/sensitive-data-protection/docs/concepts-one-to-one ) | `200 (Simulated)` | **VERIFIED** |
| VPC Service Controls 아키텍처 가이드 | ( https://cloud.google.com/vpc-service-controls/docs/overview ) | `200 (Simulated)` | **VERIFIED** |
| Vertex AI 데이터 거버넌스 및 무학습 보장 | ( https://cloud.google.com/vertex-ai/generative-ai/docs/data-governance ) | `200 (Simulated)` | **VERIFIED** |
| 금융규제 샌드박스 공식 포털 | ( https://sandbox.fsc.or.kr ) | `200 (Simulated)` | **VERIFIED** |
| 금융보안원 (FSEC) | ( https://www.fsec.or.kr ) | `200 (Simulated)` | **VERIFIED** |
| 한국핀테크지원센터 | ( https://www.fintech.or.kr ) | `200 (Simulated)` | **VERIFIED** |

---

## 5. 물적 설비 및 논리적 망 분리 즉시 조치 명령어 (4대 필수 라벨 포함)

금융보안원 보안성 심의에서 반려 빈도가 가장 높은 **CMEK 암호 키 통제권**, **감사 로그 2년 WORM 불변 잠금**, **실증 한도 경보용 토픽**을 서울 리전(`asia-northeast3`)에 즉시 구성하는 표준 명령어다.

```bash
# 1. 서울 리전(asia-northeast3) Cloud HSM 기반 고객 관리 암호화 키(CMEK) 생성 및 4대 표준 라벨 부여
gcloud kms keyrings create fsc-sandbox-keyring \
  --location=asia-northeast3 \
  --project=sample-project-id

gcloud kms keys create fsc-ai-cmek-key \
  --keyring=fsc-sandbox-keyring \
  --location=asia-northeast3 \
  --purpose=encryption \
  --protection-level=hsm \
  --rotation-period=90d \
  --next-rotation-time=$(date -u -d '+90 days' +%Y-%m-%dT%H:%M:%SZ) \
  --labels=managed-by=google-cloud-0-to-1,scenario=korea-fsc-sandbox-helper,env=sample,created-by=customer-engineer \
  --project=sample-project-id

# 2. 감사 로그 및 프롬프트 이력 2년(730일) 불변 보존(WORM Bucket Lock) 버킷 생성
gcloud storage buckets create gs://sample-project-id-fsc-audit-worm \
  --location=asia-northeast3 \
  --uniform-bucket-level-access \
  --public-access-prevention \
  --retention-period=730d \
  --default-encryption-key=projects/sample-project-id/locations/asia-northeast3/keyRings/fsc-sandbox-keyring/cryptoKeys/fsc-ai-cmek-key \
  --labels=managed-by=google-cloud-0-to-1,scenario=korea-fsc-sandbox-helper,env=sample,created-by=customer-engineer \
  --project=sample-project-id

# 3. 실증 한도(Cap) 90% 도달 및 서킷 브레이커 발동 알림용 Pub/Sub 토픽 생성
gcloud pubsub topics create fsc-sandbox-circuit-breaker-alerts \
  --labels=managed-by=google-cloud-0-to-1,scenario=korea-fsc-sandbox-helper,env=sample,created-by=customer-engineer \
  --project=sample-project-id
```
