<!--
Copyright 2026 Google LLC. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

NOTICE: This code/repository is owned by Google LLC and provided under the Apache-2.0 License.
It is strictly provided as an EXAMPLE/REFERENCE ONLY and is NOT INTENDED FOR PRODUCTION USE.
All contents, designs, and code examples are subject to change, modification, or removal at any time without notice.

[고지 사항] 본 저장소 및 문서는 구글 (Google LLC) 소유이며 Apache 2.0 라이선스 하에 예시 (Sample) 용도로 제공된다.
프로덕션 환경용이 아니며, 사전 통지 없이 언제든지 수정, 변경 또는 삭제될 수 있다.
-->

# 비즈니스 요구 사항 명세서 (BRD): Compute Engine & GKE 인스턴스 유연성 및 스톡아웃 방어 설계기

## 1. 비즈니스 배경 및 문제 정의
생성형 AI, 에이전트 워크로드 및 대규모 데이터 분석 트래픽이 급증하면서 클라우드 업계 전반에 물리적 컴퓨팅 용량 제약(Capacity Constraints)이 상시화되고 있다. 특정 리전이나 존에서 특정 단일 머신 타입(예: `n2-standard-8`)에 전적으로 의존하는 전통적인 인프라 아키텍처는 `ZONE_RESOURCE_POOL_EXHAUSTED` 장애 발생 시 신규 파드 배포 중단, 오토스케일링 확장 실패, 서비스 다운타임으로 직결된다.

따라서 사내 인프라 아키텍트와 FinOps 담당자는 단일 하드웨어에 고착되지 않고, 동등한 성능과 비용 효율성을 제공하는 복수의 머신 패밀리(N4, C4A, N2D, N2, C3)로 스마트하게 폴백(Fallback)할 수 있는 선언적 유연성 아키텍처(Design for Flexibility and Efficiency)를 사전에 체계적으로 설계하고 자동화해야 한다.

---

## 2. 비즈니스 요구 사항 목록

### BR-01: 사내 클러스터 및 인스턴스 그룹의 단일 머신 고착 취약점 진단
- GKE 노드 풀 및 Compute Engine MIG 설정을 분석하여, 단일 머신 패밀리나 단일 존에만 고착되어 용량 고갈 시 확장이 중단될 수 있는 고위험 인프라 리소스를 식별해야 한다.

### BR-02: 동등 사양 기반 최적 대체 머신 패밀리 랭킹 산출
- 기준 머신 사양(vCPU 및 메모리 비율)에 상응하는 최신 세대(N4 Emerald Rapids, C4A Axion ARM 등)부터 레거시 세대(N2D, N2)까지 성능 지수 및 상대 비용을 고려한 합리적인 우선순위 랭킹을 도출해야 한다.

### BR-03: GKE 컨테이너 환경을 위한 Custom ComputeClass(CCC) 자동 생성
- GKE 클러스터에서 용량 부족 시 차순위 머신으로 원활하게 폴백하고, 최상위 머신 자원이 복구되면 워크로드를 자동으로 복귀시키는 능동적 마이그레이션(`activeMigration`)이 포함된 선언적 `ComputeClass` 매니페스트를 즉시 생성해야 한다.

### BR-04: Compute Engine VM 환경을 위한 MIG instanceSelections 및 bulkInsert 정책 생성
- GCE Regional MIG에서 다중 머신 타입을 분산 프로비저닝할 수 있는 `instanceSelections` 정책과 대규모 단기 배치 연산에 필요한 `bulkInsert` API JSON 규격을 제공해야 한다.

### BR-05: FinOps 상업적 유연성(Flex CUD) 결합 가이드 제공
- 특정 머신 패밀리에 묶이는 자원 기반 CUD(Resource-based CUD)의 락인 한계를 극복하고, 전 리전/전 머신 패밀리에 교차 적용되는 금액 기반 Flex CUD 포트폴리오 최적화 방안을 제시해야 한다.
