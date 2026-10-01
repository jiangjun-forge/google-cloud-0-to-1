<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

---
name: gke-multi-cluster-inference-gateway
description: >-
  Autopilot, hands-on diagnostics, and self-healing for gke-multi-cluster-inference-gateway:
  대규모 AI/LLM 서빙 환경에서 다중 리전 및 멀티 클라우드에 분산된 수십 개 GPU/TPU 쿠버네티스 클러스터 운영 시,
  기존 계층형 Istio 풀 메시(Full-mesh) 중계로 인한 지연 시간(TTFT) 증가와 GKE Fleet 라이선스 비용 누수를 진단하고,
  Global External ALB 및 Hybrid/Internet NEG 기반의 1홉 플랫 직결 L7 제어 평면 상태를 1분 만에 점검 및 처방하는 아키텍처 진단 도구다.
---

# GKE Multi-Cluster Inference Gateway Skill

본 스킬은 복수 GKE 및 멀티 클라우드 GPU 클러스터 간 트래픽 제어 평면을 진단하고 최적의 L7 직결 아키텍처 처방을 제공하는 엔지니어링 스킬이다.

---

## 1. 지원 명령 및 시나리오

1. **사전 가상 검증 (Dry-run)**:
   ```bash
   python3 samples/gke-multi-cluster-inference-gateway/diagnose.py --dry-run
   ```
2. **사내 운영 환경 실시간 진단**:
   ```bash
   python3 samples/gke-multi-cluster-inference-gateway/diagnose.py -p <PROJECT_ID>
   ```

---

## 2. 점검 핵심 항목 (8대 지표)
- **CHK-01**: 다계층 메시 중계 배제 및 Anycast 1홉 플랫 직결 여부
- **CHK-02**: 실시간 KV-cache 사용률 신호(임계치 40% 도달 시 자동 오버플로) 및 `LEAST_REQUEST` 지능형 부하 분산
- **CHK-03**: 스트리밍 응답 보장을 위한 백엔드 타임아웃 (`timeoutSec >= 600s`)
- **CHK-04**: 서킷 브레이커 및 이상치 탐지 (`outlierDetection`)
- **CHK-05**: 하이브리드/인터넷 NEG를 통한 타 클라우드 $0 라이선스 직결
- **CHK-06**: 관리형 GKE Inference Gateway의 동일 VPC 제약 준수 여부
- **CHK-07**: 백엔드 서비스당 최대 50개 NEG 할당 쿼터 한계 방어
- **CHK-08**: Model Armor 미지원에 따른 Cloud Armor L7 WAF 보완 결합 여부
