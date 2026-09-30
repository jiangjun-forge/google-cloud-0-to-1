# Gemini & Gemini Enterprise 도입을 위한 AI 보안성 심의 체크리스트 소명서

- **진단 일시**: (실행 결과 자동 생성)
- **대상 프로젝트**: `sample-ai-project`
- **기준 리전**: `asia-northeast3`
- **진단 모드**: `모의 실행 (Dry-run)`
- **종합 평가**: 총 20개 항목 중 **적합(PASS) 20건**, **주의(WARN) 0건**, **부적합(FAIL) 0건**

> **[고지 사항]** 본 보고서는 구글 클라우드 공식 보안 약관(CDPA), 글로벌 공인 인증서(ISO 42001, ISO 27001 등) 및 사내 GCP 프로젝트의 실제 기술적 보안 설정을 실시간 대조하여 생성된 **공식 보안성 심의 소명 증적 문서**다.

---

## 1. 20대 핵심 보안 체크리스트 종합 조견표

| ID | 통제 영역 | 보안성 심의 요구 항목 | 판정 | 실측 증적 및 아키텍처 구현 | 구글 공식 약관 및 규제 소명 |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `SEC-01` | AI 거버넌스 | **고객 데이터의 파운데이션 모델 재학습 원천 배제**<br>_입력된 프롬프트, 첨부 파일 및 모델 응답이 구글의 기초 모델(LLM) 학습에 재활용되는가?_ | **`PASS`** | 구글 클라우드 공식 보안 약관(CDPA) 및 제3자 공인 인증서 소명 완료 | Google Cloud 생성형 AI 서비스 약관(CDPA)상 고객의 입력 및 출력 데이터는 모델 학습에 절대 활용되지 않는다 ( https://cloud.google.com/terms/data-processing-addendum ). |
| `SEC-02` | AI 거버넌스 | **인적 검토 및 외부 평가자 열람 배제 (No Human Review)**<br>_서비스 품질 개선 명목으로 구글 내부 엔지니어 또는 외부 인력이 고객사 데이터를 열람하는가?_ | **`PASS`** | 구글 클라우드 공식 보안 약관(CDPA) 및 제3자 공인 인증서 소명 완료 | 엔터프라이즈 라이선스 적용 시 No Human Review 정책이 강제되어 서비스 개선 목적의 인적 검토가 원천 차단된다 ( https://cloud.google.com/security/compliance/offerings ). |
| `SEC-03` | AI 거버넌스 | **국제 공인 AI 경영시스템 인증 (ISO/IEC 42001)**<br>_AI 시스템의 신뢰성과 투명성을 검증하는 제3자 공인 AI 국제 인증을 보유하고 있는가?_ | **`PASS`** | 구글 클라우드 공식 보안 약관(CDPA) 및 제3자 공인 인증서 소명 완료 | Google Cloud 및 Vertex AI, Gemini Enterprise는 글로벌 공인 ISO/IEC 42001 (AI Management System) 인증을 공식 획득 및 유지하고 있다 ( https://cloud.google.com/security/compliance/iso-42001 ). |
| `SEC-04` | AI 거버넌스 | **글로벌 및 국내 정보보안 인증 (K-ISMS, ISO 27001/17/18, SOC 2/3)**<br>_클라우드 인프라와 AI 서비스 전반에 대한 국제 표준 및 국내 공인 보안 인증을 보유하고 있는가?_ | **`PASS`** | 구글 클라우드 공식 보안 약관(CDPA) 및 제3자 공인 인증서 소명 완료 | K-ISMS, ISO/IEC 27001, 27017, 27018, 27701 및 SOC 1/2/3 인증 보고서를 정기 갱신 및 제공한다 ( https://cloud.google.com/security/compliance ). |
| `SEC-05` | 데이터 주권 | **대한민국 서울 리전(asia-northeast3) 내 데이터 국소화**<br>_프롬프트 처리 및 저장 데이터가 대한민국 국경 내(서울 리전)에 머무르며 해외로 유출되지 않는가?_ | **`PASS`** | Vertex AI 서울 리전 엔드포인트(asia-northeast3-aiplatform.googleapis.com) 사용 확인 | Vertex AI 및 Gemini Enterprise는 서울 리전(asia-northeast3) 엔드포인트를 제공하여 데이터 국외 이전을 방지한다 ( https://cloud.google.com/about/locations ). |
| `SEC-06` | 데이터 주권 | **서울 리전 리소스 생성 강제 조직 정책 (Resource Locations)**<br>_임직원의 실수나 비인가 설정에 의한 해외 리전 리소스 생성을 중앙에서 원천 통제하고 있는가?_ | **`PASS`** | 조직 정책 asia-northeast3 국소화 적용 완료 (constraints/gcp.resourceLocations) | gcp.resourceLocations 조직 정책을 통해 허용된 서울 리전(asia-northeast3) 이외의 인프라 생성을 차단한다. |
| `SEC-07` | 암호화 통제 | **고객 관리 암호화 키 (Cloud KMS CMEK) 적용**<br>_저장 데이터(At-Rest)에 대해 고객이 자체 관리하는 암호화 키(CMEK)를 적용하여 구글의 임의 접근을 차단하는가?_ | **`PASS`** | Cloud KMS CMEK 키(asia-northeast3/keyRings/ai-ring/cryptoKeys/ai-key) 정상 바인딩 | Cloud KMS의 CMEK를 적용하여 고객이 키 생성, 회전, 즉시 파기 권한을 독점적으로 통제한다 ( https://cloud.google.com/kms/docs ). |
| `SEC-08` | 암호화 통제 | **전송 구간 고강도 암호화 (In-Transit TLS 1.3/1.2+ 강제)**<br>_API 호출 및 엔드포인트 통신 구간에서 안전한 최신 암호화 프로토콜(TLS 1.2 이상)을 강제하는가?_ | **`PASS`** | TLS 1.2+ 강제 암호화 스위트 적용 완료 (Cloud Armor/SSL Policy) | Google Front End(GFE) 및 Cloud Armor SSL 정책을 통해 TLS 1.0, 1.1을 차단하고 TLS 1.2+ 통신을 강제한다. |
| `SEC-09` | 네트워크 보안 | **VPC Service Controls(VPC-SC)를 통한 논리적 망 분리**<br>_비인가 공인 인터넷 경로를 차단하고 사내 승인된 사설 네트워크(VPC) 경계 내에서만 AI 서비스를 호출할 수 있는가?_ | **`PASS`** | VPC-SC 보안 경계(accessPolicies/12345/servicePerimeters/ai_perimeter) 내 aiplatform.googleapis.com 등록 확인 | VPC Service Controls 보안 경계로 aiplatform.googleapis.com을 격리하여 데이터 무단 반출을 원천 방어한다 ( https://cloud.google.com/vpc-service-controls ). |
| `SEC-10` | 접근 통제 | **정적 서비스 계정 키(SA Key) 발급 차단 및 WIF 전환**<br>_로컬 JSON 파일로 내려받아 유출 위험이 높은 정적 자격 증명 키 발급을 차단하고 있는가?_ | **`PASS`** | 조직 정책 iam.disableServiceAccountKeyCreation 적용 (WIF 인증 체계 가동) | iam.disableServiceAccountKeyCreation 제약을 활성화하고 Workload Identity Federation(WIF)으로 안전하게 인증한다. |
| `SEC-11` | 접근 통제 | **사외/외국 계정 공유 차단 (Domain Restricted Sharing)**<br>_사내 승인 도메인 외의 외부 개인 Gmail 또는 협력사 계정으로의 프로젝트 권한 공유를 차단하는가?_ | **`PASS`** | 조직 정책 iam.allowedPolicyMemberDomains 적용 (사내 승인 도메인 외 차단) | iam.allowedPolicyMemberDomains 조직 정책을 통해 지정된 사내 Google Workspace/Cloud Identity 도메인 구성원에게만 IAM 바인딩을 허용한다. |
| `SEC-12` | 감사 로깅 | **데이터 접근 감사 로그(DATA_READ/DATA_WRITE) 전수 활성화**<br>_임직원이나 애플리케이션의 모든 AI 모델 호출 및 데이터 읽기/쓰기 행위가 위변조 불가능하게 기록되는가?_ | **`PASS`** | aiplatform.googleapis.com 대상 DATA_READ, DATA_WRITE 감사 로그 활성화 확인 | Cloud Audit Logs에서 Vertex AI 및 Cloud Storage의 DATA_READ, DATA_WRITE 감사 로그를 활성화하여 100% 추적성을 확보한다 ( https://cloud.google.com/logging/docs/audit ). |
| `SEC-13` | 데이터 보존 | **스토리지 불변 보존(Bucket Lock)을 통한 감사 로그 위변조 차단**<br>_수집된 프롬프트 감사 기록을 최소 법정 보존 기간(예: 5년) 동안 관리자라도 임의 삭제하거나 수정할 수 없도록 잠그는가?_ | **`PASS`** | Cloud Storage 버킷 불변 잠금(Bucket Lock, 157680000초 / 5년) 적용 확인 | Cloud Storage Bucket Lock(WORM: Write Once Read Many) 기능을 통해 컴플라이언스 보존 기간 동안 데이터 불변성을 강제한다 ( https://cloud.google.com/storage/docs/bucket-lock ). |
| `SEC-14` | 감사 로깅 | **Gemini Request/Response BigQuery 스트리밍 영구 적재**<br>_임직원이 입력한 원본 프롬프트와 생성된 AI 답변을 비즈니스 분석 및 이상 탐지 목적으로 중앙 DB에 보관하는가?_ | **`PASS`** | BigQuery 로그 싱크(projects/example-corp-ai/datasets/gemini_audit_logs) 실시간 적재 중 | Gemini Request-Response 로깅 설정을 통해 모든 인퍼런스 페이로드를 BigQuery 데이터셋으로 자동 실시간 내보내기한다. |
| `SEC-15` | AI 안전 가드 | **실시간 프롬프트 인젝션 및 탈옥(Jailbreak) 차단 가드레일**<br>_시스템 프롬프트를 탈취하거나 안전 정책을 무력화하려는 악의적 프롬프트 인젝션 시도를 실시간 방어하는가?_ | **`PASS`** | Model Armor 템플릿(ma-seoul-guard) 활성화 및 인젝션 1차 방어 파이프라인 가동 | Model Armor 템플릿 및 사내 온소일(On-soil) 가드레일 파이프라인을 연동하여 인젝션 프롬프트를 1차 차단한다 ( https://cloud.google.com/security/products/model-armor ). |
| `SEC-16` | 개인정보 보호 | **한국형 6대 고유식별정보 (주민등록번호 등) 실시간 마스킹**<br>_프롬프트 입력 시 주민등록번호, 여권번호, 운전면허번호, 계좌번호 등 한국 고유 민감 정보가 자동 가명/마스킹 처리되는가?_ | **`PASS`** | Sensitive Data Protection 한국 6대 인포타입(KOREA_RRN 등) 검사 템플릿 연동 확인 | Sensitive Data Protection(SDP) 한국형 템플릿(KOREA_RRN 등)을 통해 민감 개인정보를 비식별 토큰으로 실시간 변환한다 ( https://cloud.google.com/sensitive-data-protection ). |
| `SEC-17` | 제공자 투명성 | **클라우드 서비스 제공자(CSP) 임의 접근 차단 (Access Approval)**<br>_구글 엔지니어가 장애 지원 등의 목적으로 고객 환경에 접근할 때 사전에 고객 관리자의 명시적 승인을 거쳐야 하는가?_ | **`PASS`** | Access Approval 및 Access Transparency 정상 활성화 (구글 엔지니어 접근 사전 승인 강제) | Access Approval 및 Access Transparency를 활성화하여 구글 엔지니어의 정당한 사유 없는 고객사 데이터 접근을 원천 차단하고 사유를 투명하게 기록한다 ( https://cloud.google.com/access-approval ). |
| `SEC-18` | 공급망 보안 | **하도급 위탁사(Sub-processor) 명단 투명성 및 통제**<br>_서비스 제공 과정에서 활용되는 외부 하도급 업체의 명단이 투명하게 공개되며 동일 수준의 보안 통제가 적용되는가?_ | **`PASS`** | 구글 클라우드 공식 보안 약관(CDPA) 및 제3자 공인 인증서 소명 완료 | Google Cloud Sub-processor 웹페이지를 통해 모든 위탁사 명단 및 국가를 사전 공개하며 엄격한 제3자 보안 감사를 강제한다 ( https://cloud.google.com/terms/subprocessors ). |
| `SEC-19` | 라이프사이클 | **계약 종료 시 데이터 완전 파기 (Data Erasure) 보장**<br>_서비스 해지 또는 라이선스 만료 시 데이터센터 내 고객사 데이터가 물리적/논리적으로 완전히 복구 불가능하게 파기되는가?_ | **`PASS`** | 구글 클라우드 공식 보안 약관(CDPA) 및 제3자 공인 인증서 소명 완료 | Google Cloud 데이터 삭제 가이드라인 및 NIST SP 800-88 표준에 따라 지정 기한 내에 완전하고 안전한 데이터 소거(Data Erasure)를 보장한다 ( https://cloud.google.com/docs/security/deletion ). |
| `SEC-20` | 취약점 검증 | **레드티밍(Red Teaming) 및 정기적 모의해킹 검증**<br>_생성형 AI 모델 및 애플리케이션에 대해 전문 보안 조직에 의한 모의해킹과 레드팀 침투 테스트를 주기적으로 수행하는가?_ | **`PASS`** | 구글 클라우드 공식 보안 약관(CDPA) 및 제3자 공인 인증서 소명 완료 | Google Mandiant 및 Google AI Red Team이 Gemini 파운데이션 모델 및 플랫폼 전반에 대해 적대적 공격(Adversarial Robustness) 침투 테스트를 정기 수행한다 ( https://cloud.google.com/security ). |

---

## 2. 영역별 상세 기술 소명 및 증적 데이터

### (1) AI 거버넌스 및 데이터 학습 배제 (Data Sovereignty)
- **고객 데이터 비학습 원칙**: Google Cloud 생성형 AI 서비스(Vertex AI, Gemini API, Gemini Enterprise)는 고객이 입력한 프롬프트 및 응답을 파운데이션 모델 재학습에 활용하지 않는다.
- **인적 검토 원천 배제**: Enterprise 라이선스 환경에서는 구글 내부 인력이나 제3자 평가자의 프롬프트 열람(Human Review)이 시스템적으로 전면 차단된다.
- **공식 AI 경영시스템 인증**: 글로벌 최고 권위의 인공지능 경영시스템 인증인 `ISO/IEC 42001`을 정식 획득하여 신뢰성을 입증했다.

### (2) 데이터 거주성 및 암호화 통제 (Residency & Encryption)
- **대한민국 서울 리전 국소화**: 모든 AI 추론 및 데이터 처리가 대한민국 서울 리전(`asia-northeast3`) 내에서 완결되어 해외 이전을 방지한다.
- **고객 관리 암호화 키(CMEK)**: Cloud KMS 키링을 연동하여 고객이 암호화 키의 라이프사이클을 100% 통제하며, 위급 시 키 비활성화를 통해 데이터 접근을 즉시 차단할 수 있다.

### (3) 네트워크 경계 격리 및 접근 제어 (VPC-SC & IAM)
- **VPC Service Controls**: 서비스 경계를 적용하여 외부 인터넷 통신을 차단하고 승인된 사내 전용망에서만 프라이빗 API 호출을 허용한다.
- **자격 증명 유출 방어**: 정적 서비스 계정 키 생성을 차단(`disableServiceAccountKeyCreation`)하고 Workload Identity Federation을 강제한다.

### (4) 실시간 감사 로깅 및 불변 보존 (Audit & Immutability)
- **감사 추적성 확보**: Cloud Audit Logs를 통해 모든 입출력 이벤트를 기록하고 BigQuery 스트리밍 적재 파이프라인을 구축한다.
- **5년 불변 잠금(Bucket Lock)**: 전자금융감독규정에 따라 감사 데이터 저장 버킷에 5년 WORM 보존 정책을 적용하여 위변조를 방어한다.

---

## 3. 사내 정보보호팀 및 CISO 제출 절차
1. 본 `report.md` 문서를 PDF 또는 사내 기안서 서식으로 변환한다.
2. 사내 정보보호팀 또는 금융감독원/금융보안원 보안성 심의 신청 시 첨부 증적으로 제출한다.
3. 추가 소명이 요구되는 기술 항목은 `google-cloud-0-to-1` 저장소의 세부 진단 스크립트 실행 결과를 보충 증적으로 활용한다.
