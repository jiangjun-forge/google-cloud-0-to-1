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

# 제미나이 신뢰 스택 구간별 지연 시간 분석 가이드

엔터프라이즈 생성형 AI 파이프라인에서 발생하는 체감 지연 시간(Latency)의 원인을 전송 네트워크(DNS, TCP, TLS), 보안 가드레일(Model Armor, Sensitive Data Protection), 컨텍스트 증강(Search Grounding), 순수 LLM 추론(TTFT, 토큰 생성 속도) 구간별로 분해 계측하여 워터폴(Waterfall) 차트 및 병목 최적화 권고안을 제공하는 실측 진단 도구다. (As of 2026-09-10)

**Audience**: `#Architect`, `#Developer`, `#SecOps`
**Concern**: `#Performance`, `#Resilience`, `#Security`
**Service**: `#CloudMonitoring`, `#GeminiAPI`, `#ModelArmor`, `#VertexAI`

---

## 1. 이 가이드가 필요한 상황

- 사내 엔터프라이즈 제미나이 앱이나 Vertex AI 기반 서비스가 일반 컨슈머 웹앱(`gemini.google.com`) 대비 수백 ms 이상 느리다는 성능 불만이 제기되는 경우
- 지연 시간의 원인이 모델 자체의 추론 속도 문제인지, 보안 가드레일(Model Armor)의 동기 검사 오버헤드인지 객관적인 데이터로 입증해야 하는 경우
- 구글 검색 그라운딩(Search Grounding) 또는 사내 지식 검색(RAG) 도입으로 인해 추가되는 지연 시간을 구간별(Hop-by-hop)로 정량화해야 하는 경우
- 첫 번째 토큰 도달 시간(TTFT: Time To First Token)과 출력 스트리밍 전송 속도(TPS)를 분리 측정하여 UI/UX 렌더링 병목을 진단해야 하는 경우
- 온프레미스 전용선, VPC-SC, Private Service Connect(PSC) 등 사내 프라이빗 네트워크 경로의 TCP/TLS 핸드셰이크 오버헤드를 실측하고자 하는 경우

---

## 2. 진단 및 해결 흐름

```mermaid
flowchart TD
    A["프로파일러 실행 (diagnose.py / run.sh)"] --> B["네트워크 전송 계층 프로파일링 (DNS, TCP, TLS)"]
    B --> C["Model Armor 가드레일 인스펙션 실측"]
    C --> D["Vertex AI 첫 토큰 도달 시간 (TTFT) 실측"]
    D --> E["출력 스트리밍 완료 시간 및 토큰 속도 계측"]
    E --> F["워터폴(Waterfall) 차트 및 기여도 분석"]
    F --> G{"최대 병목 구간 판별"}
    G -- "보안 가드레일 병목" --> H["검사 필터 비동기화 및 신뢰도 임계치 최적화"]
    G -- "네트워크 전송 병목" --> I["Private Service Connect 및 엔드포인트 최적화"]
    G -- "모델 추론 병목" --> J["프롬프트 캐싱 및 Provisioned Throughput 도입 검토"]
```

---

## 3. 사전 준비 사항

본 도구 구동을 위해 필요한 최소 IAM 권한은 다음과 같다.

| 권한 역할 | 역할 명칭 | 필요 사유 |
| :--- | :--- | :--- |
| `roles/aiplatform.user` | Vertex AI 사용자 | Vertex AI Gemini 스트리밍 API 호출 및 TTFT 실측 |
| `roles/modelarmor.admin` (또는 뷰어) | Model Armor 관리자 | Model Armor 검사 엔드포인트 호출 및 필터링 지연 계측 |
| `roles/monitoring.viewer` | 모니터링 뷰어 | 엔드포인트 지연 메트릭 조회 |

---

## 4. 1분 퀵스타트

### 옵션 A: Google Cloud Shell에서 바로 실행

```bash
# 저장소 클론 및 폴더 이동
git clone https://github.com/jiangjun-forge/google-cloud-0-to-1.git
cd google-cloud-0-to-1/samples/gemini-trust-stack-latency-profiler

# 모의 가상 데이터 기반 스모크 테스트 (--dry-run)
./run.sh --dry-run

# 실제 사내 프로젝트 대상 엔드포인트 실측
./run.sh --project=example-corp --location=asia-northeast3 --model=gemini-2.5-flash
```

### 옵션 B: 로컬 파이썬 가상 환경에서 실행

```bash
# 가상 환경 생성 및 의존성 설치
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 프로파일러 실행
python3 diagnose.py --dry-run
```

---

## 5. 결과 출력 예시

```text
========================================================================================
 제미나이 엔터프라이즈 신뢰 스택(Trust Stack) 구간별 지연 시간 분석 리포트
 프로젝트: example-corp | 리전: asia-northeast3 | 모델: gemini-2.5-flash
========================================================================================

엔드투엔드(E2E) 총 소요 시간: 1,754.0 ms
----------------------------------------------------------------------------------------
구간 ID    | 계층         | 소요 시간 (비중)           | 워터폴 차트
----------------------------------------------------------------------------------------
HOP-01   | 전송 계층      |   138.5 ms ( 7.9%)   | [==                                  ] 네트워크 전송 (DNS, TCP, TLS)
HOP-02   | 보안 통제      |   562.0 ms (32.0%)   | [===========                         ] Model Armor 보안 가드레일
HOP-03   | 컨텍스트 증강    |   325.4 ms (18.6%)   | [======                              ] 구글 검색 그라운딩 (Grounding)
HOP-04   | 모델 추론      |   245.8 ms (14.0%)   | [=====                               ] 순수 LLM 첫 토큰 도달 (TTFT)
HOP-05   | 토큰 생성      |   482.3 ms (27.5%)   | [=========                           ] 응답 토큰 스트리밍 생성
----------------------------------------------------------------------------------------

신뢰 스택 세부 진단 및 최적화 권고안:
========================================================================================
* HOP-01 [네트워크 전송 (DNS, TCP, TLS)] - 138.5 ms (7.9%)
  - 원인 분석: 클라이언트 단말에서 asia-northeast3 엔드포인트까지의 네트워크 악수 및 TLS 협상 시간
  - 최적화안: VPC 내부 Private Service Connect (PSC) 전용선 경유로 RTT를 단축하거나 글로벌 애니캐스트 활용 권장

* HOP-02 [Model Armor 보안 가드레일] - 562.0 ms (32.0%)
  - 원인 분석: 프롬프트 인젝션, 탈옥, Sensitive Data Protection (SDP) 민감 정보 실시간 인그레스 스캔 오버헤드
  - 최적화안: 모든 필터를 동기 실행하지 않고 필요도가 낮은 규칙의 비동기 감사 분리 또는 필터 신뢰도 임계치 튜닝 필요

* HOP-03 [구글 검색 그라운딩 (Grounding)] - 325.4 ms (18.6%)
  - 원인 분석: 실시간 구글 검색 쿼리 실행, 결과 파싱, 인라인 컨텍스트 주입에 소요된 추가 지연 시간
  - 최적화안: 반복되는 외부 데이터는 VPC-SC 외부 DMZ 프로젝트에서 사전 크롤링 후 사내 벡터 DB로 비동기 배치 적재 권장

* HOP-04 [순수 LLM 첫 토큰 도달 (TTFT)] - 245.8 ms (14.0%)
  - 원인 분석: Vertex AI gemini-2.5-flash 모델의 프롬프트 처리 및 첫 번째 토큰 생성 시간
  - 최적화안: 프롬프트 캐싱(Context Caching) 활성화 또는 Provisioned Throughput (PT) 도입으로 큐잉 지연 제거

* HOP-05 [응답 토큰 스트리밍 생성] - 482.3 ms (27.5%)
  - 원인 분석: 340개 출력 토큰의 순차적 스트리밍 전송 완료 시간 (약 70.5 토큰/초)
  - 최적화안: 사용자 화면에 스트리밍 청크(Chunk)를 즉각 렌더링하여 엔드유저 체감 지연(Perceived Latency) 최소화

========================================================================================
종합 요약:
현재 엔터프라이즈 파이프라인의 최대 지연 병목은 [Model Armor 보안 가드레일] (562.0 ms)이다.
컨슈머 제미나이 앱 대비 발생하는 체감 지연 격차는 보안 가드레일 및 거버넌스 스택의 동기적 개입에 기인한다.
안정적인 응답 시간을 확보하기 위해 스트리밍 즉시 렌더링 및 비동기 감사 로깅을 적용해야 한다.
========================================================================================
```

---

## 6. 결과 확인 후 즉각 조치 가이드

1. **Model Armor 가드레일 지연 완화**:
   - 실시간 인스펙션 오버헤드가 과도할 경우, 불필요하게 높은 민감도 설정을 튜닝하거나 응답 검사(Egress Filtering)를 스트리밍 후처리 미들웨어에서 비동기 감사로 전환한다.
   - [Model Armor 콘솔](https://console.cloud.google.com/security/model-armor )

2. **순수 추론 시간 단축 (Prompt Caching 및 PT 도입)**:
   - 반복되는 시스템 지침이나 사내 가이드라인 문서가 긴 경우, Vertex AI 프롬프트 캐싱(Context Caching)을 적용하여 첫 토큰 지연(TTFT)을 최대 80% 절감한다.
   - 프로덕션 환경의 예측 가능한 베이스로드 확보를 위해 Provisioned Throughput(PT)을 도입하여 멀티 테넌트 큐잉 지연을 제거한다.
   - [Vertex AI 콘솔](https://console.cloud.google.com/vertex-ai )

3. **엔드투엔드 네트워크 RTT 최적화**:
   - 사내 클라이언트와 구글 백본망 간의 통신 구간을 최적화하기 위해 Private Service Connect(PSC) 엔드포인트를 구축하여 퍼블릭 인터넷 경유에 따른 패킷 지연을 방어한다.
   - [Private Service Connect 콘솔](https://console.cloud.google.com/net-services/psc )

---

## 7. 자원 정리 가이드

본 도구는 지연 시간 측정용 단발성 API 호출만 수행하므로 영구 인프라 자원을 생성하지 않는다.
테스트 과정에서 발급된 임시 인증 토큰은 세션 종료 시 자동으로 만료된다.
