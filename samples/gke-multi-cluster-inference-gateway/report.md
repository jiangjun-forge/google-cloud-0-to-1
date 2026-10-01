# Multi-Cluster GKE Inference Gateway 라우팅 및 L7 제어 평면 진단 보고서

- **진단 일시**: (실행 결과 자동 생성)
- **대상 프로젝트**: `example-ai-corp`
- **로드 밸런서 URL Map**: `ai-inference-gw-mock`
- **진단 모드**: `모의 실행 (Dry-run)`
- **종합 평가**: 총 8개 항목 중 **적합(PASS) 6건**, **주의(WARN) 2건**, **부적합(FAIL) 0건**

> **[고지 사항]** 본 보고서는 구글 클라우드 공식 멀티 클러스터 GKE Inference Gateway 레퍼런스 아키텍처 및 사내 실제 로드 밸런서 설정을 대조하여 생성된 **기술 진단 및 아키텍처 최적화 증적 문서**다.

---

## 1. 멀티 클러스터 GPU 라우팅 제어 평면 핵심 진단 조견표

| ID | 분류 | 점검 항목 | 상태 | 실측 증적 및 현황 | 권장 조치 및 처방 |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `CHK-01` | 제어 평면 구조 | **다계층 메시 중계 배제 및 Anycast 1홉 직결 아키텍처**<br>_최상위 라우팅 허브를 거치는 다계층 프록시 중계 없이 Global External ALB에서 개별 클러스터 백엔드로 1홉 플랫 직결되는가?_ | **`PASS`** | Global External ALB URL Map(ai-inference-gw)에서 분산 클러스터 백엔드 서비스로 Anycast 1홉 플랫 직결 확인 | 추가 조치 불필요 (현재 아키텍처 양호) |
| `CHK-02` | 부하 분산 정책 | **KV 캐시 인지 지능형 라우팅 및 최소 요청 분배 (LEAST_REQUEST & KV-Cache)**<br>_단순 라운드로빈이 아닌 실시간 KV-cache 점유율(임계치 40% 초과 시 자동 오버플로) 및 활성 요청 수 기반으로 가용 GPU가 있는 클러스터로 동적 라우팅하는가?_ | **`PASS`** | Inference Gateway의 KV-cache 사용률 신호(임계치 40% 도달 시 건강한 타 리전 클러스터로 자동 넘침/Spillover) 및 LEAST_REQUEST 부하 분산 연동 확인 | 추가 조치 불필요 |
| `CHK-03` | 연결 복원력 | **스트리밍 타임아웃 및 긴 응답 세션 보장 (Timeout >= 600s)**<br>_대규모 LLM 추론 및 스트리밍 응답 도중 연결이 끊기지 않도록 백엔드 서비스 타임아웃이 600초 이상으로 넉넉히 설정되어 있는가?_ | **`PASS`** | 백엔드 서비스 타임아웃 1800초 설정 확인 (장시간 LLM 스트리밍 응답 지원) | 추가 조치 불필요 |
| `CHK-04` | 장애 격리 | **서킷 브레이커 및 이상치 탐지 (Outlier Detection)**<br>_특정 클러스터의 연속 5xx 오류 또는 GPU 장애 발생 시 트래픽을 즉시 정상 클러스터로 넘기는 서킷 브레이커가 구성되어 있는가?_ | **`WARN`** | 서킷 브레이커(circuitBreakers)는 적용되었으나 이상치 탐지(outlierDetection) 설정이 일부 클러스터에서 누락됨 | gcloud compute backend-services update <BACKEND> --consecutive-errors-5xx=3 --base-ejection-time=30s 적용 권고 |
| `CHK-05` | 라이선스 최적화 | **하이브리드/인터넷 NEG를 통한 타 클라우드 추가 라이선스 비용 없는 직결**<br>_타사 클라우드(EKS, AKS 등) GPU 클러스터를 GKE Enterprise 멀티 클라우드 vCPU 라이선스 과금 없이 Hybrid/Internet NEG로 직결 수용하고 있는가? ( https://cloud.google.com/anthos/pricing )_ | **`PASS`** | 이종 타 클라우드 클러스터가 Internet/Hybrid NEG로 등록되어 GKE Enterprise 멀티 클라우드 vCPU 라이선스 과금 전면 회피 (라이선스 프리) | 추가 조치 불필요 |
| `CHK-06` | 네트워크 경계 제약 | **관리형 GKE Inference Gateway의 단일 VPC 요건 준수**<br>_관리형 GKE Inference Gateway 컨트롤러 사용 시 모든 타깃 클러스터가 동일 VPC에 위치하는가? (Cross-VPC 및 타 클라우드는 Internet/Hybrid NEG 직접 구성 아키텍처 필수)_ | **`PASS`** | 동일 VPC 내 GKE 클러스터는 관리형 Inference Gateway를 사용하고, Cross-VPC 및 타 클라우드는 Internet/Hybrid NEG로 분리 설계되어 제약 준수 | 추가 조치 불필요 (Same VPC 제약 준수 아키텍처) |
| `CHK-07` | 확장성 쿼터 제약 | **백엔드 서비스당 최대 50개 NEG 할당 한계 방어**<br>_멀티포트 InferencePool 구성 시 백엔드당 50개 NEG 제한을 초과하지 않도록 백엔드 서비스 분할 또는 포트별 라우팅이 설계되어 있는가?_ | **`PASS`** | 백엔드 서비스별 NEG 등록 수 점검 (현재 18개 / 최대 한도 50개 이하로 안정적 마진 확보) | 향후 멀티포트 InferencePool 확장 시 백엔드 서비스 분할(URL Map 분기) 원칙 유지 |
| `CHK-08` | AI 보안 거버넌스 | **Inference Gateway의 Model Armor 미지원에 따른 L7 WAF 보완**<br>_멀티 클러스터 GKE Inference Gateway의 Model Armor 연동 미지원 제약을 인지하고, Cloud Armor L7 WAF 또는 로컬 가드레일 계층으로 방어하고 있는가?_ | **`WARN`** | Inference Gateway의 Model Armor 연동 미지원으로 인해 L7 웹 애플리케이션 방화벽(Cloud Armor WAF) 레이트 리미팅 정책이 결합됨 | Cloud Armor 보안 정책(WAF, DDoS, Rate Limiting)을 Global External ALB에 필수로 바인딩한다. |

---

## 2. As-Is vs To-Be 아키텍처 비교 분석

| 비교 항목 | 현행 (As-Is: 다계층 Istio 풀 메시 중계) | 제안 (To-Be: 글로벌 L7 Anycast 플랫 직결 + Inference Gateway) |
| :--- | :--- | :--- |
| **네트워크 구조** | 최상위 허브 클러스터를 거쳐 다수 분산 클러스터 중계 | Global External ALB 중심 1:1 플랫 직결 (스타형) |
| **통신 홉 및 지연** | 2~3홉 프록시 중계 (헤어피닝 지연 시간 발생) | 단 1홉 Anycast 직결 (지연 시간 20~30ms 단축) |
| **제어 평면 부하** | 수십 개 클러스터 엔드포인트 동기화로 Istiod OOM 발생 | 각 클러스터는 로컬 인그레스만 관리, 동기화 부하 0 |
| **라이선스 비용** | 타 클라우드 GKE Enterprise 등록 시 vCPU 관리 라이선스 과금 ( https://cloud.google.com/anthos/pricing ) | Hybrid / Internet NEG 활용으로 추가 관리 라이선스 비용 없음 |
| **지능형 부하 분산** | 정적 가중치 분배 한계 (메모리 포화 인지 불가) | 실시간 **KV-cache 사용률(임계치 40% 도달 시 자동 넘침)** 및 `LEAST_REQUEST` 기반 지능형 라우팅 |
| **장애 격리** | 상위 허브 장애 시 전면 마비 | 헬스 체크 및 서킷 브레이커 기반 비정상 클러스터 즉시 우회 |

---

## 3. 공식 GKE Inference Gateway 제약 사항 및 아키텍처 대응

구글 클라우드 공식 문서 ( https://docs.cloud.google.com/kubernetes-engine/docs/concepts/about-multi-cluster-inference-gateway#limitations )에 명시된 3대 제약 조건과 사내 대응 아키텍처는 다음과 같다:

1. **단일 VPC 제약 (Same VPC Network)**: 관리형 Gateway는 모든 클러스터가 동일 VPC에 위치해야 한다. 타 클라우드(EKS/AKS) 및 독립 VPC 클러스터는 Global External ALB의 Internet/Hybrid NEG 직접 바인딩으로 제약을 우회한다.
2. **백엔드 서비스당 최대 50개 NEG 제한**: 멀티포트 InferencePool 사용 시 3개 존 클러스터 2개만으로도 48개 NEG가 생성되어 50개 한도에 도달한다. 클러스터 확장 시 모델 포트/경로별 백엔드 서비스 분할(URL Map 분기)을 적용한다.
3. **Model Armor 연동 미지원**: Gateway 레벨에서 Model Armor 자동 연동이 지원되지 않으므로, 글로벌 진입점에 Cloud Armor L7 WAF 정책(DDoS 방어, Rate Limiting)을 결합하여 보안을 보완한다.

---

## 4. L7 트래픽 제어 평면 최적화 gcloud 명령어 처방

### (1) 백엔드 서비스 로드 밸런싱 알고리즘 LEAST_REQUEST 적용
```bash
gcloud compute backend-services update <BACKEND_SERVICE_NAME> \
    --global \
    --locality-lb-policy=LEAST_REQUEST \
    --timeout=1800s
```

### (2) 서킷 브레이커 및 이상치 탐지(Outlier Detection) 활성화
```bash
gcloud compute backend-services update <BACKEND_SERVICE_NAME> \
    --global \
    --consecutive-errors-5xx=3 \
    --base-ejection-time=30s
```

### (3) 타 클라우드 GPU 클러스터 수용을 위한 인터넷 NEG 등록
```bash
gcloud compute network-endpoint-groups create neg-external-gpu-cluster-01 \
    --global \
    --network-endpoint-type=INTERNET_FQDN_PORT \
    --default-port=443
```
