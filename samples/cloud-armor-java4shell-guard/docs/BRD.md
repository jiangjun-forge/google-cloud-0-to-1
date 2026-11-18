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

# 비즈니스 요구 사항 명세서 (BRD): Cloud Armor 기반 Java4Shell (CVE-2026-114938) 가상 패치 및 노출 진단기 (As of 2026-11-18)

## 1. 배경 및 목적
OpenJDK `17.0.6+`, `21.x`, `25.x`, `27.x`가 AVX-512 VBMI 명령어를 지원하는 x86-64 프로세서에서 실행될 때 발생하는 `CVE-2026-114938` (Java4Shell, 보안 공지 `GCP-2026-082`) 원격 코드 실행(RCE) 및 서비스 거부(DoS) 취약점은 고정 문자열 시그니처가 없어 Cloud Armor 기본 제공 WAF 규칙(`java-v422-stable` 등)으로 탐지하거나 차단할 수 없다. 또한 OpenJDK 보안 패치나 `JDK_JAVA_OPTIONS` JVM 플래그 적용 전까지 외부 노출 면적을 줄이기 위해 Cloud Armor Custom CEL 기반 가상 패치(Virtual Patching)를 적용하려 할 때, `base64Decode() == ''` 부분 디코딩 우회, `request.body`/`request.params` 정책 선연결 순서 오류, `.urlDecode()`의 `+` 공백 치환 오탐 등 실환경 제약으로 장애나 보안 공백이 발생하기 쉽다.

본 미니 프로젝트(`cloud-armor-java4shell-guard`)는 사내 GCP 프로젝트 내 AVX-512 VBMI 해당 머신 시리즈(Compute Engine, GKE) 및 Cloud Run 런타임 노출 현황과 Cloud Armor Security Policy의 Custom CEL 방어 구성을 1분 만에 교차 진단하고, 즉시 적용 가능한 가상 패치 CLI 명령어 및 워크로드 근본 조치 가이드를 제공한다.

---

## 2. 핵심 비즈니스 요구 사항 (Business Requirements)

| 요구 사항 ID | 요구 사항 명칭 | 상세 설명 | 우선순위 |
| :--- | :--- | :--- | :--- |
| **BR-01** | **노출 워크로드 및 WAF 방어 공백 사전 탐지** | 사내 프로젝트 내 AVX-512 VBMI 지원 x86-64 머신 시리즈(Compute Engine, GKE 노드풀)와 Cloud Armor Security Policy의 `CVE-2026-114938` 가상 패치 누락 또는 우회 가능 설정을 사전에 식별하여야 한다. | 필수 (P0) |
| **BR-02** | **Cloud Armor CEL 실환경 함정 정적 감사** | `base64Decode() == ''` 부분 디코딩 우회 패턴, `Cookie`/JSON/XML 본문 내 `.urlDecode()` 오탐 패턴, `application/x-www-form-urlencoded` 미분리 패턴 등 실환경 검증에서 확인된 CEL 오류를 자동 검출하여야 한다. | 필수 (P0) |
| **BR-03** | **가상 실행(Dry-run) 기반 무중단 사전 검증** | 실제 GCP API 조회나 정책 변경 없이 `--dry-run` 플래그로 안전하게 진단 로직과 리포트(`report.md`) 출력 서식을 검증할 수 있어야 한다. | 필수 (P0) |
| **BR-04** | **단계별 배포 순서 및 근본 조치 가이드 제공** | `request.body`/`request.params` 룰의 Backend Service 선연결 순서, 64KB 본문 검사 상한 설정, `--preview` 선적용 후 Enforce 전환 명령, `JDK_JAVA_OPTIONS` 적용 및 자원 정리(Teardown) 절차를 제공하여야 한다. | 권장 (P1) |
| **BR-05** | **자원 거버넌스 라벨링 표준 준수** | 테스트용 Cloud Armor 및 로드 밸런싱 리소스 생성 가이드에서 4대 표준 라벨(`managed-by=google-cloud-0-to-1`, `scenario=cloud-armor-java4shell-guard`, `env=sample`, `created-by=customer-engineer`)을 누락 없이 안내하여야 한다. | 필수 (P0) |

---

## 3. 대상 독자 및 이해관계자 (Target Audience)
- **클라우드 보안 및 SecOps 엔지니어 (`#SecOps`)**: 긴급 CVE 대응용 L7 WAF 가상 패치 정책 감사 및 Preview 로그 기반 무오탐 검증
- **인프라 및 플랫폼 아키텍트 (`#Architect`)**: GKE, Compute Engine, Cloud Run 워크로드의 AVX-512 VBMI 하드웨어 노출 범위 파악 및 근본 패치 계획 수립
- **애플리케이션 및 DevOps 실무자 (`#Developer`)**: `JDK_JAVA_OPTIONS` 임시 우회 플래그 적용 및 OpenJDK 베이스 이미지 업그레이드 이행
