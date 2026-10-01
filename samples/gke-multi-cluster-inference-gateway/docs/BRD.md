<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 비즈니스 요구 사항 명세서 (BRD): Multi-Cluster GKE Inference Gateway 라우팅 진단기

## 1. 비즈니스 배경 및 문제 정의
대규모 언어 모델(LLM) 서빙 환경에서 전 세계적인 GPU/TPU 공급 부족(Resource Exhaustion)으로 인해, 엔터프라이즈 기업은 단일 데이터센터나 단일 클러스터에서 필요한 가속기 용량을 모두 확보할 수 없다. 이에 따라 여러 리전의 GKE 클러스터 및 타사 클라우드(AWS EKS, Azure AKS 등)에 걸쳐 수십 개의 분산 클러스터를 운영하는 멀티 클러스터 GPU 인프라 도입이 보편화되고 있다.

그러나 현행 쿠버네티스 서비스 메시(Istio Full-mesh) 기반의 다계층 중계 구조는 다음과 같은 심각한 비즈니스 및 기술적 한계를 유발한다:
1. **지연 시간(TTFT) 증가 및 사용자 경험 저하**: 최상위 라우팅 허브를 거쳐 중간 메시 프록시를 2~3홉 경유하면서 홉당 지연 시간과 지터(Jitter)가 누적되어 대화형 인공 지능의 첫 토큰 생성 시간(Time to First Token)이 악화된다.
2. **이중 데이터 전송(Egress) 및 클라우드 라이선스 비용 누수**: 타 클라우드 GPU 워커 노드에 대한 GKE Fleet 관리 라이선스(vCPU당 월 $73) 과금 및 클러스터 간 불필요한 크로스 리전 메시 트래픽으로 인한 네트워크 전송 비용이 발생한다.
3. **제어 평면(Istiod) 메모리 고갈(OOM) 및 라우팅 불균형**: 수십 개 클러스터의 엔드포인트를 실시간 동기화하는 메시 컨트롤 플레인의 부하로 인해 장애 전파 위험이 존재하며, 특정 클러스터에 부하가 몰려 GPU가 유휴 상태로 낭비되거나 요청이 드롭된다.

따라서 구글 클라우드의 글로벌 애니캐스트(Anycast) 기반 L7 트래픽 제어 평면(Global External Application Load Balancer 및 Hybrid/Internet NEG)과 GKE Inference Gateway 구성을 실시간 진단하고, 1홉 플랫 직결 아키텍처로의 전환 처방을 제공하는 진단 도구가 필수적이다.

---

## 2. 비즈니스 요구 사항 목록

### BR-01: 멀티 클러스터 GPU 라우팅 토폴로지 자동 진단
- 사내 운영 환경의 로드 밸런서(Global External ALB), URL Map, 백엔드 서비스 및 NEG(Network Endpoint Group) 구성을 조회하여 다계층 프록시 중계 병목 유무를 식별해야 한다.

### BR-02: GPU 인퍼런스 가중치 및 지능형 부하 분산 점검
- 17개 이상의 분산 클러스터 백엔드 간에 가중치 기반 라우팅(Weight-based Routing), 최소 요청 분배(LEAST_REQUEST), 타임아웃 및 이상치 탐지(Outlier Detection / Circuit Breaker)가 적절히 구성되었는지 검증해야 한다.

### BR-03: 지연 시간 단축 및 라이선스 비용 절감 수치 소명
- Istio 3홉 중계 대비 Anycast 1홉 플랫 직결 시의 예상 RTT 지연 개선 효과와 GKE Fleet 라이선스 회피 효과를 비교 리포트로 산출해야 한다.

### BR-04: CISO 및 인프라 아키텍트용 원클릭 완제품 리포트 생성
- 진단 즉시 사내 인프라 아키텍처 리뷰 및 개선 기안서로 활용할 수 있도록 표준 마크다운 리포트(`report.md`)와 최적화 `gcloud` 처방 스크립트를 자동 생성해야 한다.
