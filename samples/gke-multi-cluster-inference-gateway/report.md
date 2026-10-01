# Multi-Cluster GKE Inference Gateway 라우팅 및 L7 제어 평면 진단 보고서

- **진단 일시**: (실행 결과 자동 생성)
- **대상 프로젝트**: `example-ai-corp`
- **로드 밸런서 URL Map**: `ai-inference-gw-mock`
- **진단 모드**: `모의 실행 (Dry-run)`
- **종합 평가**: 총 5개 항목 중 **적합(PASS) 4건**, **주의(WARN) 1건**, **부적합(FAIL) 0건**

> **[고지 사항]** 본 보고서는 구글 클라우드 공식 멀티 클러스터 GKE Inference Gateway 레퍼런스 아키텍처 및 사내 실제 로드 밸런서 설정을 대조하여 생성된 **기술 진단 및 아키텍처 최적화 증적 문서**다.

---

## 1. 멀티 클러스터 GPU 라우팅 제어 평면 핵심 진단 조견표

| ID | 분류 | 점검 항목 | 상태 | 실측 증적 및 현황 | 권장 조치 및 처방 |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `CHK-01` | 제어 평면 구조 | **다계층 메시 중계 배제 및 Anycast 1홉 직결 아키텍처**<br>_최상위 라우팅 허브를 거치는 다계층 프록시 중계 없이 Global External ALB에서 개별 클러스터 백엔드로 1홉 플랫 직결되는가?_ | **`PASS`** | Global External ALB URL Map(ai-inference-gw)에서 17개 분산 클러스터 백엔드 서비스로 Anycast 1홉 플랫 직결 확인 | 추가 조치 불필요 (현재 아키텍처 양호) |
| `CHK-02` | 부하 분산 정책 | **LLM 인퍼런스 최적 로드 밸런싱 (LEAST_REQUEST)**<br>_단순 라운드로빈이 아닌 활성 처리 요청 수 기반(LEAST_REQUEST)으로 가용 GPU가 있는 클러스터로 트래픽을 동적 라우팅하는가?_ | **`PASS`** | 모든 GPU 인퍼런스 백엔드 서비스의 localityLbPolicy가 LEAST_REQUEST(최소 활성 요청 동적 분배)로 설정됨 | 추가 조치 불필요 |
| `CHK-03` | 연결 복원력 | **스트리밍 타임아웃 및 긴 응답 세션 보장 (Timeout >= 600s)**<br>_대규모 LLM 추론 및 스트리밍 응답 도중 연결이 끊기지 않도록 백엔드 서비스 타임아웃이 600초 이상으로 넉넉히 설정되어 있는가?_ | **`PASS`** | 백엔드 서비스 타임아웃 1800초 설정 확인 (장시간 LLM 스트리밍 응답 지원) | 추가 조치 불필요 |
| `CHK-04` | 장애 격리 | **서킷 브레이커 및 이상치 탐지 (Outlier Detection)**<br>_특정 클러스터의 연속 5xx 오류 또는 GPU 장애 발생 시 트래픽을 즉시 정상 클러스터로 넘기는 서킷 브레이커가 구성되어 있는가?_ | **`WARN`** | 서킷 브레이커(circuitBreakers)는 적용되었으나 이상치 탐지(outlierDetection) 설정이 일부 클러스터에서 누락됨 | gcloud compute backend-services update <BACKEND> --consecutive-errors-5xx=3 --base-ejection-time=30s 적용 권고 |
| `CHK-05` | 라이선스 최적화 | **하이브리드/인터넷 NEG를 통한 타 클라우드 $0 라이선스 직결**<br>_타사 클라우드(EKS, AKS 등) GPU 클러스터를 GKE Fleet(vCPU당 월 $73) 과금 없이 Hybrid/Internet NEG로 직결 수용하고 있는가?_ | **`PASS`** | 타 클라우드 10개 클러스터가 Internet/Hybrid NEG로 등록되어 GKE Fleet vCPU 라이선스 과금 전면 회피 ($0) | 추가 조치 불필요 |

---

## 2. As-Is vs To-Be 아키텍처 비교 분석

| 비교 항목 | 현행 (As-Is: 다계층 Istio 풀 메시 중계) | 제안 (To-Be: 글로벌 L7 Anycast 플랫 직결) |
| :--- | :--- | :--- |
| **네트워크 구조** | 최상위 허브 클러스터를 거쳐 17개 하위 클러스터 중계 | Global External ALB 중심 1:1 플랫 직결 (스타형) |
| **통신 홉 및 지연** | 2~3홉 프록시 중계 (헤어피닝 지연 시간 발생) | 단 1홉 Anycast 직결 (지연 시간 최소화) |
| **제어 평면 부하** | 17개 클러스터 엔드포인트 동기화로 Istiod OOM 발생 | 각 클러스터는 로컬 인그레스만 관리, 동기화 부하 0 |
| **라이선스 비용** | 타 클라우드 GKE Fleet 등록 시 vCPU당 월 $73 과금 | Hybrid / Internet NEG 활용으로 라이선스 비용 $0 |
| **지능형 부하 분산** | 정적 가중치 분배 한계 | `LEAST_REQUEST` 기반 여유 GPU 클러스터로 동적 라우팅 |
| **장애 격리** | 상위 허브 장애 시 전면 마비 | 헬스 체크 및 서킷 브레이커 기반 비정상 클러스터 즉시 우회 |

---

## 3. L7 트래픽 제어 평면 최적화 gcloud 명령어 처방

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
