<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 한국형 인공지능 보안성 심의 20대 핵심 체크리스트 명세서 (Security Checklist Catalog)

본 문서는 사내 정보보호팀, CISO 및 금융감독원/금융보안원의 생성형 AI 도입 보안성 심의에 대응하기 위해 대한민국 법령(개인정보보호법, 신용정보법, 산업기술보호법, 전자금융감독규정) 및 글로벌 보안 인증 기준(ISO/IEC 42001, ISO 27001)을 정밀 분석하여 표준화한 **20대 핵심 보안 통제 카탈로그**다.

---

## 1. 20대 핵심 보안 체크리스트 종합 명세표

| ID | 영역 | 통제 항목 | 점검 질의 (보안팀 관점) | 구글 공식 보안 약관 및 규제 소명 | 법적 / 규제 근거 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `SEC-01` | AI 거버넌스 | **파운데이션 모델 재학습 원천 배제** | 입력된 프롬프트, 첨부 파일 및 모델 응답이 구글의 기초 모델(LLM) 학습에 재활용되는가? | Google Cloud 생성형 AI 서비스 약관(CDPA) 및 Secure AI 백서에 따라 고객 데이터는 모델 재학습에 일절 활용되지 않는다 ( https://cloud.google.com/terms/data-processing-addendum , https://services.google.com/fh/files/misc/secure_ai_secure_data.pdf ). | 개인정보보호위원회 AI 프라이버시 리스크 관리 모델, K-ISMS |
| `SEC-02` | AI 거버넌스 | **인적 검토 배제 (No Human Review)** | 서비스 품질 개선 명목으로 구글 내부 엔지니어 또는 외부 인력이 고객사 데이터를 열람하는가? | 엔터프라이즈 라이선스 적용 시 No Human Review 정책이 강제되어 서비스 개선 목적의 사람 열람이 원천 차단된다 ( https://cloud.google.com/security/compliance/offerings ). | 정보통신망법 제28조, 금융보안원 SaaS 보안 가이드라인 |
| `SEC-03` | AI 거버넌스 | **국제 공인 AI 경영시스템 인증 (ISO/IEC 42001)** | AI 시스템의 신뢰성과 투명성을 검증하는 제3자 공인 AI 국제 인증을 보유하고 있는가? | Google Cloud 및 Vertex AI, Gemini Enterprise는 글로벌 공인 ISO/IEC 42001 인증을 공식 획득 및 유지하고 있다 ( https://cloud.google.com/security/compliance/iso-42001 ). | 국제 표준화 기구 ISO/IEC 42001:2023, EU AI Act |
| `SEC-04` | AI 거버넌스 | **국내외 정보보안 인증 (K-ISMS, ISO 27001 등)** | 클라우드 인프라와 AI 서비스 전반에 대한 국제 표준 및 국내 공인 보안 인증을 보유하고 있는가? | K-ISMS, ISO/IEC 27001, 27017, 27018, 27701 및 SOC 1/2/3 인증 보고서를 정기 갱신 및 제공한다 ( https://cloud.google.com/security/compliance ). | 정보보호관리체계(K-ISMS), 전자금융감독규정 |
| `SEC-05` | 데이터 주권 | **대한민국 서울 리전 내 데이터 국소화** | 프롬프트 처리 및 저장 데이터가 대한민국 국경 내(서울 리전)에 머무르며 해외로 유출되지 않는가? | 저장 데이터(At-Rest)는 서울 리전(asia-northeast3) 내 100% 보관되나, 모델 추론(Processing)은 글로벌 분산 인프라 특성상 국외 처리될 수 있다. 전송 암호화, 인메모리 휘발 및 사전 마스킹(SDP)을 통한 보완 소명이 필요하다 ( https://cloud.google.com/about/locations ). | 국가핵심기술보호법, 금융위 망 분리 개선 로드맵 |
| `SEC-06` | 데이터 주권 | **서울 리전 생성 강제 조직 정책 (Resource Locations)** | 임직원의 실수나 비인가 설정에 의한 해외 리전 리소스 생성을 중앙에서 원천 통제하고 있는가? | gcp.resourceLocations 조직 정책을 통해 허용된 서울 리전(asia-northeast3) 이외의 인프라 생성을 차단한다. | 전자금융감독규정 제15조, 개인정보보호법 |
| `SEC-07` | 암호화 통제 | **고객 관리 암호화 키 (Cloud KMS CMEK) 적용** | 저장 데이터(At-Rest)에 대해 고객이 자체 관리하는 암호화 키(CMEK)를 적용하여 구글의 임의 접근을 차단하는가? | Cloud KMS의 CMEK를 적용하여 고객이 키 생성, 회전, 즉시 파기 권한을 독점적으로 통제한다 ( https://cloud.google.com/kms/docs ). | 전자금융감독규정 제14조, 신용정보법 |
| `SEC-08` | 암호화 통제 | **전송 구간 고강도 암호화 (TLS 1.2+ 강제)** | API 호출 및 엔드포인트 통신 구간에서 안전한 최신 암호화 프로토콜(TLS 1.2 이상)을 강제하는가? | Google Front End(GFE) 및 Cloud Armor SSL 정책을 통해 TLS 1.0, 1.1을 차단하고 TLS 1.2+ 통신을 강제한다. | 전자금융감독규정 제14조, NIST SP 800-52 |
| `SEC-09` | 네트워크 보안 | **VPC Service Controls를 통한 논리적 망 분리** | 비인가 공인 인터넷 경로를 차단하고 사내 승인된 사설 네트워크(VPC) 경계 내에서만 AI 서비스를 호출할 수 있는가? | VPC Service Controls 보안 경계로 aiplatform.googleapis.com을 격리하여 데이터 무단 반출을 원천 방어한다 ( https://cloud.google.com/vpc-service-controls ). | 전자금융감독규정 제15조 (망 분리) |
| `SEC-10` | 접근 통제 | **정적 서비스 계정 키 발급 차단 및 WIF 전환** | 로컬 JSON 파일로 내려받아 유출 위험이 높은 정적 자격 증명 키 발급을 차단하고 있는가? | iam.disableServiceAccountKeyCreation 제약을 활성화하고 Workload Identity Federation(WIF)으로 안전하게 인증한다. | 전자금융감독규정 제13조, OWASP Top 10 |
| `SEC-11` | 접근 통제 | **사외/외국 계정 공유 차단 (Domain Restricted Sharing)** | 사내 승인 도메인 외의 외부 개인 Gmail 또는 협력사 계정으로의 프로젝트 권한 공유를 차단하는가? | iam.allowedPolicyMemberDomains 조직 정책을 통해 지정된 사내 Google Workspace/Cloud Identity 도메인 구성원에게만 IAM 바인딩을 허용한다. | 산업기술유출방지법 제10조 |
| `SEC-12` | 감사 로깅 | **데이터 접근 감사 로그(DATA_READ/WRITE) 전수 활성화** | 임직원이나 애플리케이션의 모든 AI 모델 호출 및 데이터 읽기/쓰기 행위가 위변조 불가능하게 기록되는가? | Cloud Audit Logs에서 Vertex AI 및 Cloud Storage의 DATA_READ, DATA_WRITE 감사 로그를 활성화하여 100% 추적성을 확보한다 ( https://cloud.google.com/logging/docs/audit ). | 전자금융거래법 제22조, 개인정보보호법 |
| `SEC-13` | 데이터 보존 | **스토리지 불변 보존(Bucket Lock) 위변조 차단** | 수집된 프롬프트 감사 기록을 최소 법정 보존 기간(예: 5년) 동안 관리자라도 임의 삭제하거나 수정할 수 없도록 잠그는가? | Cloud Storage Bucket Lock(WORM: Write Once Read Many) 기능을 통해 컴플라이언스 보존 기간 동안 데이터 불변성을 강제한다 ( https://cloud.google.com/storage/docs/bucket-lock ). | 전자금융감독규정 제63조 (5년 보존) |
| `SEC-14` | 감사 로깅 | **Gemini Request/Response BigQuery 스트리밍 적재** | 임직원이 입력한 원본 프롬프트와 생성된 AI 답변을 비즈니스 분석 및 이상 탐지 목적으로 중앙 DB에 보관하는가? | Gemini Request-Response 로깅 설정을 통해 모든 인퍼런스 페이로드를 BigQuery 데이터셋으로 자동 실시간 내보내기한다. | FSI 생성형 AI 가이드라인, 보안 감사 원칙 |
| `SEC-15` | AI 안전 가드 | **실시간 프롬프트 인젝션 및 탈옥 차단 가드레일** | 시스템 프롬프트를 탈취하거나 안전 정책을 무력화하려는 악의적 프롬프트 인젝션 시도를 실시간 방어하는가? | Model Armor의 서울 리전(asia-northeast3) 환경은 SDP 연동을 지원하며, 프롬프트 인젝션 및 악성 URL 검사는 글로벌 엔진 또는 사내 로컬 하이브리드 가드레일 계층으로 상호 보완해야 한다 ( https://cloud.google.com/security/products/model-armor ). | OWASP Top 10 for LLM (LLM01: Prompt Injection) |
| `SEC-16` | 개인정보 보호 | **한국형 6대 고유식별정보 (주민등록번호 등) 실시간 마스킹** | 프롬프트 입력 시 주민등록번호, 여권번호, 운전면허번호, 계좌번호 등 한국 고유 민감 정보가 자동 가명/마스킹 처리되는가? | Sensitive Data Protection(SDP) 한국형 템플릿(KOREA_RRN 등)을 통해 민감 개인정보를 비식별 토큰으로 실시간 변환한다 ( https://cloud.google.com/sensitive-data-protection ). | 신용정보법 제20조의2, 개인정보보호법 제24조 |
| `SEC-17` | 제공자 투명성 | **클라우드 제공자(CSP) 임의 접근 차단 (Access Approval)** | 구글 엔지니어가 장애 지원 등의 목적으로 고객 환경에 접근할 때 사전에 고객 관리자의 명시적 승인을 거쳐야 하는가? | Access Approval 및 Access Transparency를 활성화하여 구글 엔지니어의 정당한 사유 없는 고객사 데이터 접근을 원천 차단하고 사유를 투명하게 기록한다 ( https://cloud.google.com/access-approval ). | 금융보안원 CSP 안전성 평가 기준 |
| `SEC-18` | 공급망 보안 | **하도급 위탁사(Sub-processor) 명단 투명성 및 통제** | 서비스 제공 과정에서 활용되는 외부 하도급 업체의 명단이 투명하게 공개되며 동일 수준의 보안 통제가 적용되는가? | Google Cloud Sub-processor 웹페이지를 통해 모든 위탁사 명단 및 국가를 사전 공개하며 엄격한 제3자 보안 감사를 강제한다 ( https://cloud.google.com/terms/subprocessors ). | 개인정보보호법 제26조 (업무위탁에 따른 개인정보 처리 제한) |
| `SEC-19` | 라이프사이클 | **계약 종료 시 데이터 완전 파기 (Data Erasure) 보장** | 서비스 해지 또는 라이선스 만료 시 데이터센터 내 고객사 데이터가 물리적/논리적으로 완전히 복구 불가능하게 파기되는가? | Google Cloud 데이터 삭제 가이드라인 및 NIST SP 800-88 표준에 따라 지정 기한 내에 완전하고 안전한 데이터 소거(Data Erasure)를 보장한다 ( https://cloud.google.com/docs/security/deletion ). | 개인정보보호법 제21조 (개인정보의 파기) |
| `SEC-20` | 취약점 검증 | **레드티밍(Red Teaming) 및 정기적 모의해킹 검증** | 생성형 AI 모델 및 애플리케이션에 대해 전문 보안 조직에 의한 모의해킹과 레드팀 침투 테스트를 주기적으로 수행하는가? | Google Mandiant 및 Google AI Red Team이 Gemini 파운데이션 모델 및 플랫폼 전반에 대해 적대적 공격(Adversarial Robustness) 침투 테스트를 정기 수행한다 ( https://cloud.google.com/security ). | KISA AI 보안 가이드라인, OWASP Top 10 for LLM |

---

## 2. 영역별 상세 분류 체계 (7대 도메인)
1. **AI 거버넌스 및 신뢰성 (Governance & Certification)**: `SEC-01` ~ `SEC-04`
2. **데이터 거주성 및 주권 (Data Residency & Boundary)**: `SEC-05` ~ `SEC-06`
3. **암호화 및 키 관리 (Encryption & Key Management)**: `SEC-07` ~ `SEC-08`
4. **네트워크 격리 및 접근 통제 (Network Security & Access Control)**: `SEC-09` ~ `SEC-11`
5. **감사 추적 및 데이터 보존 (Audit Logging & Data Retention)**: `SEC-12` ~ `SEC-14`
6. **AI 안전성 및 한국형 개인정보 보호 (Guardrails & Privacy)**: `SEC-15` ~ `SEC-16`
7. **공급망 보안 및 제공자 투명성 (Supply Chain & Transparency)**: `SEC-17` ~ `SEC-20`
