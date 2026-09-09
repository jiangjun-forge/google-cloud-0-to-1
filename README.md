# Google Cloud 0 to 1

> **Disclaimer**: This is not an officially supported Google product.  
> 본 저장소에 제공되는 코드와 가이드는 상용 배포(프로덕션)를 목적으로 제작된 것이 아니며, 구글 클라우드(Google Cloud) 각 기술 요소에 대한 이해를 돕기 위해 각자의 독립된 환경에서 가볍게 실습 및 테스트해 보는 데모용 가이드다.  
> 또한, 본 소스 코드는 작성자의 의도에 따라 예고 없이 언제든지 수정되거나 삭제될 수 있다.

---

## 1. 저장소 디렉터리 구조

```text
.
├── samples/                                    # 주요 시나리오별 진단 및 실습 샘플
│   ├── cloud-run-direct-vpc-egress-checker/    # Direct VPC Egress 구성 및 서브넷 IP 고갈 위험 진단
│   ├── cloud-sql-iam-db-auth-resolver/         # Cloud SQL IAM DB 인증 전환 및 토큰 만료 장애 진단
│   ├── gemini-billing-spike/                   # 감사 로그 부재 시 지표 기반 비용 급증 자격 증명 진단
│   ├── gemini-enterprise-analytics-exporter/   # 사용자 채택률 및 유휴 라이선스 회수 분석
│   ├── gemini-enterprise-domain-in-use-resolver/# 도메인 선점 충돌 진단 및 Cloud Identity 배포
│   ├── gemini-enterprise-firewall-fqdn-checker/# 사내망 방화벽 허용용 Exact FQDN 및 443 연결성 진단
│   ├── gemini-enterprise-usage-by-account/     # Model Armor 살균 감사 로그 기반 엔터프라이즈 토큰 추정
│   ├── gemini-legacy-sdk-scanner/              # 구형 SDK 코드 정적 탐색 및 google-genai 전환 처방
│   ├── gemini-quota-cost-alert/                # 예산 임계치 실시간 Pub/Sub 경보 및 쿼터 자동 차단
│   ├── gemini-request-response-logging/        # 파운데이션 모델 프롬프트 BigQuery 스트리밍 적재
│   ├── gemini-resilience-checker/              # 429 장애 극복 복원력 패턴(백오프, 지터, 폴백) 진단
│   ├── gemini-sensitive-data-masking/          # 프롬프트 전송 전 Cloud DLP 실시간 개인정보 마스킹
│   ├── gemini-usage-by-account/                # BigQuery 로그 기반 계정별 토큰(생각 토큰 포함) 집계
│   ├── gemini-vpc-sc-denial-resolver/          # VPC-SC 보안 경계 위반 감사 로그 역추적 및 처방
│   ├── gpu-future-reservation-checker/         # GPU Future Reservation 상태 및 쿼터 정책 정밀 진단
│   ├── gpu-region-latency-probe/               # 서울 대체 GPU 리전 100ms RTT 프로브 및 가용성 추천
│   ├── iam-permission-resolver/                # 403 권한 거부 감사 로그 분석 및 최소 권한 원클릭 처방
│   ├── kms-key-rotation-outage-guard/          # CMEK 키 자동 순환 후 구버전 비활성화 장애 예방
│   ├── llm-pairwise-autorater/                 # 두 모델 간 병렬 배치 추론 및 교차 판사 자동 평가
│   ├── nct-gen-ai-compliance-checker/          # 국가 핵심 기술 서울 리전 Data Boundary 및 IAM Deny 점검
│   ├── org-policy-resolver/                    # 조직 정책 제약 조건 위반 역추적 및 정책 비활성화 처방
│   ├── service-account-leak-investigator/      # 침해 의심 서비스 계정 감사 로그 역추적 및 WIF 전환 진단
│   ├── storage-transfer-secure-on-prem-uploader/# 온프렘 대용량 영상 STS 전송 및 KMS/VPC-SC 보안 검증
│   └── vertex-search-datastore-grounding-validator/# RAG 데이터 저장소 색인 누락 및 그라운딩 정합성 진단
├── notebooks/                                  # 레거시 실습 노트북 (2026-09-30 까지만 유지)
└── scripts/                                    # 레거시 진단 스크립트 (2026-09-30 까지만 유지)
```

---

## 2. 샘플 디렉터리 구성 및 활용 안내

각 샘플은 독립적으로 실행 및 검증이 가능하도록 자체 완결형 구조로 제공된다:

1. **디렉터리 파일 구성**:
   - `.env.example`: 시나리오별 환경 변수 설정 템플릿
   - `README.md`: 문제 증상, 진단 및 조치 워크플로우 다이어그램, 필요 IAM 권한, 실행 방법 안내
   - `diagnose.py`: 시나리오별 진단 및 분석 핵심 로직
   - `requirements.txt`: 실행에 필요한 최소 파이썬 패키지 목록
   - `run.sh`: 가상 환경 구성 및 실행 원클릭 래퍼 스크립트
2. **사전 가상 검증 모드 (`--dry-run`)**:
   - 실제 GCP API 호출이나 권한 부여 없이도 모의 데이터를 통해 진단 결과와 조치 가이드를 사전 검증할 수 있다.
3. **독립 실행 환경**:
   - 상위 디렉터리 설정에 구애받지 않고, 각 샘플 폴더 내에서 바로 실행할 수 있도록 구성되어 있다.

---

## 3. 환경 실행 권장 안내

본 저장소의 모든 미니 프로젝트는 별도의 번거로운 로컬 도구 설치 과정 없이, 웹 브라우저 상에서 즉시 가동할 수 있는 Google Cloud Shell ( https://shell.cloud.google.com ) 환경에서 실행하는 것을 권장한다.
