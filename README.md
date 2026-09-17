<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# Google Cloud 0 to 1

> [!IMPORTANT]
> **구글 (Google LLC) 참조용 샘플 고지 사항 (Disclaimer)**:
> This is not an officially supported Google product.  
> 본 프로젝트의 모든 소스 코드와 문서는 Google LLC의 소유이며, Apache-2.0 라이선스에 따라 오직 **참조용 샘플 (Sample / Reference Only)** 목적으로만 제공된다. 프로덕션 환경에 그대로 사용할 수 없으며, 사전 통지 없이 언제든 내용이 수정, 변경 또는 삭제될 수 있다.

---

## 1. 저장소 디렉터리 구조

```text
.
├── samples/                                    # 주요 시나리오별 진단 및 실습 샘플
│   ├── bigquery-data-agent-semantic-enricher/  # BigQuery Data Agent NL2SQL 정확도 극대화를 위한 메타데이터 준비도 진단 및 지능형 보강
│   ├── bigquery-data-agent-starter/            # BigQuery Data Agent 45분 완성 스몰셋 핸즈온 스타터 키트 (Standalone 기본 및 GE App 선택 연동)
│   ├── cloud-nat-port-exhaustion-guard/        # Cloud NAT 동적 포트 할당(DPA) 확장 지연 및 사일런트 패킷 드롭 진단
│   ├── cloud-run-cud-optimizer/                # 서버리스 CUD 약정액 최적화 및 권장 엔진 과소 약정 트랩 분석
│   ├── cloud-run-direct-vpc-egress-checker/    # Direct VPC Egress 구성 및 서브넷 IP 고갈 위험 진단
│   ├── embedding-dimension-tradeoff-analyzer/  # 임베딩 차원 축소에 따른 용량 절감 및 정확도 비교
│   ├── fcm-push-quota-guard/                   # FCM 대량 푸시 쿼터 고갈 방어 및 429 쓰로틀링 복원력 진단
│   ├── gce-capacity-stockout-guard/            # 리전 용량 고갈 장애 방어 및 CUD/Reservation 정합성 진단
│   ├── gce-future-reservation-checker/         # GPU 및 특수 인스턴스 Future Reservation 사전 예약 진단
│   ├── gce-region-latency-probe/               # 서울 대체 GPU 및 인프라 리전 100ms RTT 프로브 및 추천
│   ├── gemini-billing-spike/                   # 감사 로그 부재 시 지표 기반 비용 급증 자격 증명 진단
│   ├── gemini-enterprise-governance-guard/     # 마켓플레이스 차단, 사내 승인 에이전트 통제 및 WIF SSO 진단
│   ├── gemini-enterprise-analytics-exporter/   # 사용자 채택률 및 유휴 라이선스 회수 분석
│   ├── gemini-enterprise-cross-org-agent-resolver/ # Cross-Org 커스텀 에이전트 연동 권한 및 조직 정책 진단
│   ├── gemini-enterprise-domain-in-use-resolver/ # 도메인 선점 충돌 진단 및 Cloud Identity 배포
│   ├── gemini-enterprise-fqdn-checker/         # 사내망 방화벽 허용용 Exact FQDN 및 443 연결성 진단
│   ├── gemini-enterprise-overage-guard/        # 일일 풀링 쿼터 초과 쓰로틀링 방어 및 Spend Cap 과금 가드
│   ├── gemini-enterprise-latency-profiler/     # 엔터프라이즈 신뢰 스택(네트워크, 가드레일, TTFT) 구간별 지연 시간 분석
│   ├── gemini-enterprise-usage-by-account/     # Model Armor 살균 감사 로그 기반 엔터프라이즈 토큰 추정
│   ├── gemini-legacy-sdk-scanner/              # 구형 SDK 코드 정적 탐색 및 google-genai 전환 처방
│   ├── gemini-quota-cost-alert/                # 예산 임계치 실시간 Pub/Sub 경보 및 쿼터 자동 차단
│   ├── gemini-request-response-logging/        # 파운데이션 모델 프롬프트 BigQuery 스트리밍 적재 및 토큰 분석
│   ├── gemini-resilience-checker/              # 429 장애 극복 복원력 패턴(백오프, 지터, 폴백) 진단
│   ├── gemini-vpc-sc-denial-resolver/          # VPC-SC 보안 경계 위반 감사 로그 역추적 및 처방
│   ├── gke-ingress-502-resolver/               # GKE Ingress/Gateway 502 Bad Gateway 4대 원인 체인 역추적
│   ├── gke-source-ip-snat-guard/               # GKE NLB 출발지 IP 보존 및 kube-proxy SNAT 부하 불균형 진단
│   ├── iam-permission-resolver/                # 403 권한 거부 감사 로그 분석 및 최소 권한 원클릭 처방
│   ├── kms-key-rotation-outage-guard/          # CMEK 키 자동 순환 후 구버전 비활성화 장애 예방
│   ├── korea-fsi-regulatory-perimeter-guard/   # 혁신 금융 서비스 논리적 망 분리, 5년 Bucket Lock 및 AI 규제 진단
│   ├── korea-nct-gen-ai-compliance-checker/    # 국가 핵심 기술 서울 리전 Data Boundary 및 IAM Deny 점검
│   ├── lro-polling-quota-guard/                # LRO 비동기 작업 폴링 쿼터 고갈 및 429 에러 진단
│   ├── model-armor-regional-compliance-guard/  # 서울 리전 Model Armor 기능 제약 진단 및 하이브리드 가드레일 처방
│   ├── org-policy-resolver/                    # 조직 정책 제약 조건 위반 역추적 및 정책 비활성화 처방
│   ├── service-account-leak-investigator/      # 침해 의심 서비스 계정 감사 로그 역추적 및 WIF 전환 진단
│   ├── storage-transfer-secure-uploader/       # 온프렘 대용량 영상 STS 전송 및 KMS/VPC-SC 보안 검증
│   ├── swg-tenant-access-guard/                # 사내 관문 SWG 헤더 주입 및 Context-Aware Access 인가 진단
│   └── vertex-search-grounding-validator/      # RAG 데이터 저장소 색인 누락 및 그라운딩 정합성 진단
├── notebooks/                                  # 레거시 실습 노트북 (2026-09-30 까지만 유지)
└── scripts/                                    # 레거시 진단 스크립트 (2026-09-30 까지만 유지)
```

---

## 2. Google Cloud Shell 환경 퀵스타트 및 Antigravity CLI (`agy`) 가동 가이드

본 저장소의 모든 미니 프로젝트와 실습 스킬은 별도의 로컬 개발 도구 설치 없이 웹 브라우저 기반의 Google Cloud Shell ( https://shell.cloud.google.com ) 환경에서 즉시 가동할 수 있다.

### 2.1 저장소 복제 및 작업 디렉터리 이동
Google Cloud Shell 콘솔 상단 터미널을 열고 본 저장소를 복제한 뒤 해당 폴더로 이동한다:
```bash
git clone https://github.com/jiangjun-forge/google-cloud-0-to-1.git
cd google-cloud-0-to-1
```

### 2.2 Cloud Shell 환경 내 Antigravity CLI (`agy`) 공식 설치
Google Cloud Shell(리눅스 amd64 환경)에서 구글 공식 AI 코딩 에이전트 도구인 Antigravity CLI (`agy`)를 아래 공식 원라인 명령어로 설치한다:
```bash
# Antigravity CLI (agy) 리눅스 공식 설치 스크립트 실행
curl -fsSL https://antigravity.google/cli/install.sh | bash

# PATH 환경 변수 갱신 (설치 바이너리 ~/.local/bin 경로 인식)
source ~/.bashrc

# 정상 설치 확인
agy --version
```

### 2.3 에이전트 가동 및 미니 프로젝트 자율 실행 예시
저장소 루트(`google-cloud-0-to-1/`)에서 `agy`를 실행하면 `.agents/skills/`에 등록된 36개 실습 스킬을 에이전트가 자동으로 로드한다:
```bash
# 저장소 루트에서 Antigravity CLI 가동 (스킬 자동 인식)
agy
```

`agy` 대화창에서 원하는 미니 프로젝트 슬러그를 지정하여 질문하면 에이전트가 페어 프로그래밍을 수행한다:
- **예습 요청**: `bigquery-data-agent-starter 미니 프로젝트 욜로 모드로 먼저 시연해 줘`
- **장애 진단 요청**: `gemini-billing-spike 진단 실행하고 비용 급증 원인 분석해 줘`
- **수동 직접 실습**: 안내에 따라 터미널에서 `cd samples/<슬러그> && ./run.sh` 직접 실행

---

## 3. 실습 스킬 (`.agents/skills/`) 및 3단계 학습 가이드

본 저장소의 모든 미니 프로젝트는 고객 개발자가 AI 에이전트를 페어 프로그래머 삼아 자율 실행(YOLO Autopilot)부터 직접 실습, 아키텍처 복습까지 원활하게 진행할 수 있도록 `.agents/skills/<슬러그>/`에 스킬 명세서를 기본 탑재하고 있다:

1. **Stage 1: 예습 (YOLO Autopilot 모드)**:
   - "이 미니 프로젝트 욜로 모드로 먼저 시연해 줘"라고 요청하면, 에이전트가 환경 자동 감지부터 가상 실행(`--dry-run`), 예상 리포트 해석, 자가 치유 시연까지 화면에 실시간으로 중계하며 전체 흐름을 예습시켜 준다.
2. **Stage 2: 실습 (Developer Hands-on 단계)**:
   - 예습을 마친 후 각 샘플 디렉터리의 `README.md` 가이드에 따라 터미널에서 `./run.sh`를 직접 실행하며 실제 리소스 진단 및 결과 검증을 수행한다.
3. **Stage 3: 복습 (Deep-dive & Architecture)**:
   - `docs/BRD.md`(비즈니스 요구 사항)와 `docs/TDD.md`(기술 상세 아키텍처)를 대조하며 현업 시스템 적용 방안을 심층 분석한다.

> [!IMPORTANT]
> **실습 환경 보존 및 자동 정리 금지 원칙**:
> 실습 과정에서 구축되거나 진단된 클라우드 환경 및 데이터셋은 사용자가 직접 Google Cloud 콘솔 UI로 진입하여 생성 결과를 육안으로 확인하고 추가 검증을 이어갈 수 있도록 **절대로 에이전트가 임의로 자동 삭제하지 않는다**.
> 환경 보존 및 테스트가 모두 완료된 후 사용자가 명시적으로 정리를 요청할 때에만 안내에 따라 수동 정리를 진행한다.

---

## 4. 샘플 디렉터리 구성 및 세부 활용 안내

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
